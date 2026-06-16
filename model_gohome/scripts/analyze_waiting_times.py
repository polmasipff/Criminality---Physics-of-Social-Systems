"""analyze_waiting_times.py — waiting-time & residence-time analysis vs g.

Reads the per-event logs <output-dir>/runs/events/events_g*_seed*.csv.gz (written when
output.save_event_logs is true) and analyzes the TEMPORAL structure of crime and
criminal residence as g varies.

Computed (pooled over seeds at each g):
  A. Global inter-crime waiting times: gaps between consecutive crime events anywhere.
     NOTE: the MEAN global gap is pinned by the inflow (≈ 1/crime-rate), so only its
     SHAPE / dispersion (CV, tail) is informative — we report the CV, not just the mean.
  B. Per-cell inter-crime waiting times: gaps between crimes on the SAME cell, pooled
     over cells with >= --min-crimes events. This is the near-repeat / repeat-
     victimization clock and is (scientifically) the most meaningful local measure.
  C. Residence times split by exit type: entry->crime vs entry->home_exit.
  D. Exit-channel fractions: crime vs home.

Outputs:
  runs/derived/waiting_times_summary.csv   tidy per-g summary
  figures/waiting_times_ccdf.{png,pdf}     CCDFs (log-y) of global & per-cell gaps
  figures/residence_by_exit_type.{png,pdf} residence-time distributions by exit type
  figures/waiting_times_vs_g.{png,pdf}     mean/median/CV vs g
  figures/exit_fraction_vs_g.{png,pdf}     crime vs home exit fraction vs g

Generates NO simulations. Usage:
    python3 scripts/analyze_waiting_times.py [--output-dir DIR] [--min-crimes 5]
"""
import os
import sys
import glob
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
C.apply_style()


def min_crimes_for_g(g, base, highg=2.0, highg_min=1):
    """Per-g threshold of crimes-per-cell. For large g (>= highg, e.g. g=3) deterrence
    kills repeat victimization, so very few cells reach `base`; we drop the threshold
    to `highg_min` (=1) so we can still see the (expected) EXPONENTIAL per-cell gaps."""
    return highg_min if g >= highg else base


def load_events(output_dir):
    ed = os.path.join(C.runs_dir(output_dir), "events")
    files = sorted(glob.glob(os.path.join(ed, "events_g*_seed*.csv.gz")))
    rows = []
    for fn in files:
        m = re.search(r"events_g([-\d.]+)_seed(\d+)\.csv\.gz", os.path.basename(fn))
        if not m:
            continue
        g = float(m.group(1)); seed = int(m.group(2))
        d = pd.read_csv(fn)
        d["g"] = g; d["seed"] = seed
        rows.append(d)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def global_intercrime(dfg):
    """Per seed, sort crime events by time, diff; pool gaps across seeds."""
    gaps = []
    cr = dfg[dfg.type == "crime"]
    for seed, sub in cr.groupby("seed"):
        t = np.sort(sub.day.values)
        if t.size > 1:
            gaps.append(np.diff(t))
    return np.concatenate(gaps) if gaps else np.array([])


def percell_intercrime(dfg, min_crimes):
    gaps = []
    cr = dfg[dfg.type == "crime"]
    for (seed, x, y), sub in cr.groupby(["seed", "x", "y"]):
        if len(sub) >= min_crimes:
            t = np.sort(sub.day.values)
            gaps.append(np.diff(t))
    return np.concatenate(gaps) if gaps else np.array([])


def ccdf(a):
    a = np.sort(a)
    if a.size == 0:
        return a, a
    y = 1.0 - np.arange(a.size) / a.size
    return a, y


def cv(a):
    a = np.asarray(a, float)
    return float(a.std() / a.mean()) if a.size and a.mean() > 0 else np.nan


# --------------------------------------------------------------------------- #
#  PDF estimation (log-spaced bins, proper density normalization)
# --------------------------------------------------------------------------- #
def pdf_hist(a, nbins=40, log_bins=True):
    """Empirical PDF of a positive sample.

    Returns (centers, density, edges). With log_bins=True the bins are
    logarithmically spaced (essential for heavy-tailed / multi-scale data such as
    the per-cell inter-crime gaps): density = count / (N * bin_width) so it
    integrates to 1 and can be overlaid directly with a fitted f(t).
    Non-positive values are dropped (gaps of exactly 0 = two crimes the same step).
    """
    a = np.asarray(a, float)
    a = a[a > 0]
    if a.size < 2:
        return np.array([]), np.array([]), np.array([])
    if log_bins:
        edges = np.logspace(np.log10(a.min()), np.log10(a.max()), nbins + 1)
    else:
        edges = np.linspace(a.min(), a.max(), nbins + 1)
    counts, edges = np.histogram(a, bins=edges)
    widths = np.diff(edges)
    dens = counts / (a.size * widths)
    centers = np.sqrt(edges[:-1] * edges[1:]) if log_bins else 0.5 * (edges[:-1] + edges[1:])
    return centers, dens, edges


import math

# --------------------------------------------------------------------------- #
#  CCDF distribution fits (pure numpy MLE; no scipy / no external pkg needed).
#  Models fitted on the WHOLE positive sample (xmin = min for the power-laws):
#    - exponential                f(x)=lam e^{-lam x}              CCDF e^{-lam x}
#    - Weibull (= stretched exp)  CCDF e^{-(x/lam)^k}
#    - lognormal                  CCDF = 1/2 erfc((ln x - mu)/(sqrt2 sig))
#    - power-law                  p~x^{-alpha}, CCDF (x/xmin)^{-(alpha-1)}
#    - truncated power-law        p~x^{-alpha} e^{-lam x}  (PL with exp cutoff)
#  Each fitter returns a dict with a model CCDF callable plus loglik / AIC / KS so
#  the panels can plot the best few. AIC = 2k - 2 loglik (lower = better).
# --------------------------------------------------------------------------- #
_ERFC = np.vectorize(math.erfc)


def _ks_cdf(x_sorted, cdf_vals):
    n = x_sorted.size
    hi = np.arange(1, n + 1) / n
    lo = np.arange(0, n) / n
    return float(np.max(np.maximum(np.abs(hi - cdf_vals), np.abs(cdf_vals - lo))))


def _result(model, label, ccdf, loglik, k, ks, n, xmin=np.nan, **params):
    aic = 2 * k - 2 * loglik if np.isfinite(loglik) else np.inf
    d = dict(model=model, label=label, ccdf=ccdf, loglik=float(loglik), k=int(k),
             aic=float(aic), ks=float(ks), n=int(n), xmin=float(xmin))
    d.update(params)
    return d


def fit_exponential(a):
    a = np.sort(np.asarray(a, float)); a = a[a > 0]
    n = a.size
    if n < 5:
        return None
    lam = 1.0 / a.mean()
    loglik = n * np.log(lam) - lam * a.sum()
    ks = _ks_cdf(a, 1.0 - np.exp(-lam * a))
    return _result("exponential", r"exp ($\lambda$=%.3g)" % lam,
                   lambda x: np.exp(-lam * np.asarray(x, float)), loglik, 1, ks, n, rate=lam)


def fit_weibull(a):
    a = np.sort(np.asarray(a, float)); a = a[a > 0]
    n = a.size
    if n < 5:
        return None
    lnx = np.log(a)

    def g(k):                       # MLE score for the shape k (root => k_hat)
        xk = a ** k
        return (xk * lnx).sum() / xk.sum() - 1.0 / k - lnx.mean()
    lo, hi = 0.05, 50.0
    if g(lo) * g(hi) > 0:
        k = 1.0
    else:
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if g(lo) * g(mid) <= 0:
                hi = mid
            else:
                lo = mid
        k = 0.5 * (lo + hi)
    lam = (np.mean(a ** k)) ** (1.0 / k)
    z = (a / lam) ** k
    loglik = n * np.log(k / lam) + (k - 1) * np.sum(np.log(a / lam)) - np.sum(z)
    ks = _ks_cdf(a, 1.0 - np.exp(-z))
    return _result("weibull", r"Weibull ($k$=%.2f)" % k,
                   lambda x: np.exp(-(np.asarray(x, float) / lam) ** k),
                   loglik, 2, ks, n, shape=k, scale=lam)


def fit_lognormal(a):
    a = np.sort(np.asarray(a, float)); a = a[a > 0]
    n = a.size
    if n < 5:
        return None
    lx = np.log(a)
    mu = lx.mean(); sig = lx.std(ddof=0)
    if sig <= 0:
        return None
    loglik = float(np.sum(-np.log(a * sig * np.sqrt(2 * np.pi)) - (lx - mu) ** 2 / (2 * sig ** 2)))
    ks = _ks_cdf(a, 0.5 * _ERFC(-(lx - mu) / (sig * np.sqrt(2))))
    return _result("lognormal", r"lognormal ($\mu$=%.2f,$\sigma$=%.2f)" % (mu, sig),
                   lambda x: 0.5 * _ERFC((np.log(np.asarray(x, float)) - mu) / (sig * np.sqrt(2))),
                   loglik, 2, ks, n, mu=mu, sigma=sig)


def fit_powerlaw(a):
    a = np.sort(np.asarray(a, float)); a = a[a > 0]
    n = a.size
    if n < 10:
        return None
    xmin = a.min()
    s = np.sum(np.log(a / xmin))
    if s <= 0:
        return None
    alpha = 1.0 + n / s
    loglik = n * np.log((alpha - 1.0) / xmin) - alpha * s
    ks = _ks_cdf(a, 1.0 - (a / xmin) ** (-(alpha - 1.0)))
    return _result("powerlaw", r"power-law ($\alpha$=%.2f)" % alpha,
                   lambda x: np.where(np.asarray(x, float) >= xmin,
                                      (np.asarray(x, float) / xmin) ** (-(alpha - 1.0)), 1.0),
                   loglik, 1, ks, n, xmin=xmin, alpha=alpha)


def fit_truncated_powerlaw(a):
    """power-law with exponential cutoff: p(x) ~ x^{-alpha} e^{-lam x}, x >= xmin.
    Normalization Z and the CCDF are computed by numerical integration (no special
    functions needed); (alpha, lam) by coarse grid + coordinate-descent refine."""
    a = np.sort(np.asarray(a, float)); a = a[a > 0]
    n = a.size
    if n < 10:
        return None
    xmin = a.min(); xmax = a.max()
    xs = np.logspace(np.log10(xmin), np.log10(xmax * 5.0), 4000)
    sum_lnx = float(np.sum(np.log(a))); sum_x = float(a.sum())

    def nll(alpha, lam):
        if lam < 0:
            return np.inf
        Z = np.trapz(xs ** (-alpha) * np.exp(-lam * xs), xs)
        if not np.isfinite(Z) or Z <= 0:
            return np.inf
        return alpha * sum_lnx + lam * sum_x + n * np.log(Z)

    best = (np.inf, 1.0, 0.0)
    for alpha in np.linspace(0.0, 3.0, 31):
        for lam in np.r_[0.0, np.logspace(-3, 1, 25)]:
            f = nll(alpha, lam)
            if f < best[0]:
                best = (f, alpha, lam)
    f0, alpha, lam = best
    da, dl = 0.1, 0.5
    for _ in range(80):
        improved = False
        trials = [(alpha + da, lam), (alpha - da, lam),
                  (alpha, lam + dl), (alpha, max(lam - dl, 0.0)), (alpha, lam * 0.7)]
        for aa, ll in trials:
            f = nll(aa, ll)
            if f < f0:
                f0, alpha, lam, improved = f, aa, ll, True
        if not improved:
            da *= 0.5; dl *= 0.5
            if da < 1e-3 and dl < 1e-3:
                break
    loglik = -f0
    pdf = xs ** (-alpha) * np.exp(-lam * xs)
    pdf /= np.trapz(pdf, xs)
    cdf_grid = np.r_[0.0, np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(xs))]
    ks = _ks_cdf(a, np.interp(a, xs, cdf_grid))
    return _result("trunc_powerlaw",
                   r"trunc PL ($\alpha$=%.2f,$\lambda$=%.3g)" % (alpha, lam),
                   lambda x: np.clip(1.0 - np.interp(np.asarray(x, float), xs, cdf_grid), 0, 1),
                   loglik, 2, ks, n, xmin=xmin, alpha=alpha, rate=lam)


ALL_FITTERS = [fit_exponential, fit_weibull, fit_lognormal,
               fit_powerlaw, fit_truncated_powerlaw]


def fit_all_models(a):
    """Fit every model to sample a; return a list sorted by AIC (best first)."""
    out = []
    for f in ALL_FITTERS:
        try:
            r = f(a)
        except Exception:
            r = None
        if r is not None and np.isfinite(r["aic"]):
            out.append(r)
    out.sort(key=lambda d: d["aic"])
    for i, d in enumerate(out):
        d["rank"] = i + 1
    return out


def main():
    output_dir = C.get_opt("--output-dir")
    # uniform threshold across ALL g by default (= 1 crime/cell); the per-g override
    # remains available via --min-crimes-highg / --highg if ever needed.
    base_min = int(C.get_opt("--min-crimes", "1"))
    highg_min = int(C.get_opt("--min-crimes-highg", str(base_min)))
    highg = float(C.get_opt("--highg", "2"))
    ev = load_events(output_dir)
    if ev.empty:
        print("no event logs under", os.path.join(C.runs_dir(output_dir), "events"))
        print("set output.save_event_logs: true (and event_log_g) in the config, then re-run.")
        return
    gs = sorted(ev.g.unique())
    colors = C.g_colors(len(gs))

    summary, perseed = [], []
    global_gaps, cell_gaps, mc_used = {}, {}, {}
    res_crime, res_home = {}, {}
    for g in gs:
        mc = min_crimes_for_g(g, base_min, highg, highg_min)
        mc_used[g] = mc
        dfg = ev[np.isclose(ev.g, g)]
        gg = global_intercrime(dfg)
        cg = percell_intercrime(dfg, mc)
        rc = dfg[dfg.type == "crime"].residence.values
        rh = dfg[dfg.type == "home_exit"].residence.values
        global_gaps[g], cell_gaps[g] = gg, cg
        # per-seed scalars -> uncertainties (SEM across seeds) for the vs-g panels
        for seed, sub in dfg.groupby("seed"):
            gg_s = global_intercrime(sub); cg_s = percell_intercrime(sub, mc)
            rc_s = sub[sub.type == "crime"].residence.values
            rh_s = sub[sub.type == "home_exit"].residence.values
            ncr = int((sub.type == "crime").sum()); nhm = int((sub.type == "home_exit").sum())
            tot_s = max(ncr + nhm, 1)
            perseed.append(dict(
                g=g, seed=int(seed),
                global_intercrime_mean=float(gg_s.mean()) if gg_s.size else np.nan,
                global_intercrime_cv=cv(gg_s),
                percell_intercrime_mean=float(cg_s.mean()) if cg_s.size else np.nan,
                percell_intercrime_cv=cv(cg_s),
                residence_crime_mean=float(rc_s.mean()) if rc_s.size else np.nan,
                residence_home_mean=float(rh_s.mean()) if rh_s.size else np.nan,
                frac_exit_crime=ncr / tot_s, frac_exit_home=nhm / tot_s))
        res_crime[g], res_home[g] = rc, rh
        n_cr = int((dfg.type == "crime").sum()); n_hm = int((dfg.type == "home_exit").sum())
        tot = max(n_cr + n_hm, 1)
        summary.append(dict(
            g=g, n_crime=n_cr, n_home=n_hm,
            frac_exit_crime=n_cr / tot, frac_exit_home=n_hm / tot,
            global_intercrime_mean=float(gg.mean()) if gg.size else np.nan,
            global_intercrime_median=float(np.median(gg)) if gg.size else np.nan,
            global_intercrime_cv=cv(gg),
            percell_intercrime_mean=float(cg.mean()) if cg.size else np.nan,
            percell_intercrime_median=float(np.median(cg)) if cg.size else np.nan,
            percell_intercrime_cv=cv(cg), n_cell_gaps=int(cg.size),
            min_crimes_percell=int(mc),
            residence_crime_mean=float(rc.mean()) if rc.size else np.nan,
            residence_crime_median=float(np.median(rc)) if rc.size else np.nan,
            residence_home_mean=float(rh.mean()) if rh.size else np.nan,
            residence_home_median=float(np.median(rh)) if rh.size else np.nan,
        ))
    tidy = pd.DataFrame(summary)
    out_csv = os.path.join(C.derived_dir(output_dir), "waiting_times_summary.csv")
    tidy.to_csv(out_csv, index=False)
    print("wrote", out_csv)

    # per-seed -> mean +/- SEM across seeds (uncertainties for the vs-g panels)
    ps = pd.DataFrame(perseed)
    vs_cols = ["global_intercrime_mean", "global_intercrime_cv", "percell_intercrime_mean",
               "percell_intercrime_cv", "residence_crime_mean", "residence_home_mean",
               "frac_exit_crime", "frac_exit_home"]
    gx, mvs, svs = C.agg_by(ps, "g", vs_cols)
    vs_tidy = pd.DataFrame({"g": gx, "n_seeds": ps.groupby("g").size().reindex(gx).values})
    for c in vs_cols:
        vs_tidy[c + "_mean"] = mvs[c].values
        vs_tidy[c + "_sem"] = svs[c].values
    vs_csv = os.path.join(C.derived_dir(output_dir), "waiting_times_vs_g.csv")
    vs_tidy.to_csv(vs_csv, index=False)
    print("wrote", vs_csv)

    # ---- Fig 1: CCDFs of waiting times (log-y) ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for g, c in zip(gs, colors):
        a, yv = ccdf(global_gaps[g])
        if a.size:
            axes[0].step(a, yv, where="post", color=c, label="g=%g" % g)
        a, yv = ccdf(cell_gaps[g])
        if a.size:
            axes[1].step(a, yv, where="post", color=c, label="g=%g" % g)
    axes[0].set_title("Global inter-crime gap (gaps lengthen as g rises: crime slows)")
    if base_min == highg_min:
        _pc = r"$\geq$%d crime/cell" % base_min
    else:
        _pc = r"per-g min crimes/cell, g$\geq$%g uses %d" % (highg, highg_min)
    axes[1].set_title("Per-cell inter-crime gap (repeat victimization; %s)" % _pc)
    for ax in axes:
        ax.set_yscale("log"); ax.set_xscale("log"); ax.set_xlabel("waiting time (days)")
        ax.set_ylabel("CCDF  P(T > t)"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout()
    C.save_fig(fig, "waiting_times_ccdf", output_dir)

    # ---- Fig 1b: CCDF with best-fit laws (grid: rows = quantity, cols = g) ----
    #   Candidate laws fit by MLE on the WHOLE sample: exponential, Weibull
    #   (= stretched exponential), lognormal, power-law, truncated power-law
    #   (power-law with exponential cutoff). The best 3 by AIC are drawn over the
    #   empirical CCDF; the full ranking goes to waiting_times_fits.csv.
    fit_rows = []
    quantities = [("global inter-crime", global_gaps), ("per-cell inter-crime", cell_gaps)]
    nrow, ncol = len(quantities), len(gs)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7 * ncol, 4.2 * nrow), squeeze=False)
    mcolors = C.MODEL_COLORS
    for ri, (label, gapsdict) in enumerate(quantities):
        for ci, g in enumerate(gs):
            ax = axes[ri][ci]
            a = np.asarray(gapsdict.get(g, np.array([])), float); a = a[a > 0]
            if ri == 0:
                ax.set_title("g=%g" % g)
            else:
                ax.set_title("g=%g  ($\\geq$%d crimes/cell)" % (g, mc_used.get(g, 0)))
            if ci == 0:
                ax.set_ylabel(label + "\nCCDF  P(T>t)")
            ax.set_xlabel("waiting time (days)")
            if a.size < 10:
                ax.text(0.5, 0.5, "n/a\n(insufficient data)", ha="center", va="center",
                        transform=ax.transAxes); ax.set_xticks([]); ax.set_yticks([])
                continue
            xs_sorted, yv = ccdf(a)
            ax.step(xs_sorted, yv, where="post", color=C.PALETTE["ink"], lw=1.6, label="data")
            models = fit_all_models(a)
            for d in models:                       # record ALL models for the CSV
                fit_rows.append(dict(g=g, quantity=label, model=d["model"],
                                     params=d["label"], loglik=d["loglik"], aic=d["aic"],
                                     ks=d["ks"], k=d["k"], n=d["n"], rank=d["rank"]))
            xgrid = np.logspace(np.log10(a.min()), np.log10(a.max()), 200)
            for d in models[:3]:                   # overlay best 3 by AIC
                ax.plot(xgrid, d["ccdf"](xgrid), "--", lw=1.7,
                        color=mcolors.get(d["model"], "k"),
                        label="%s  AIC=%.0f" % (d["label"], d["aic"]))
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_ylim(max(1e-4, 0.5 / a.size), 1.3)
            ax.grid(alpha=.3, which="both"); ax.legend(fontsize=7, loc="lower left")
    fig.suptitle("Inter-crime CCDFs with best-fit laws (dashed = top-3 by AIC; "
                 "full ranking in waiting_times_fits.csv)", y=0.997)
    fig.tight_layout()
    C.save_fig(fig, "waiting_times_ccdf_fits", output_dir)

    fits = pd.DataFrame(fit_rows)
    fits_csv = os.path.join(C.derived_dir(output_dir), "waiting_times_fits.csv")
    fits.to_csv(fits_csv, index=False)
    print("wrote", fits_csv)
    if not fits.empty:
        best = fits[fits["rank"] == 1][["g", "quantity", "model", "params", "aic", "ks"]]
        print("best model (lowest AIC) per panel:")
        print(best.to_string(index=False))

    # ---- Fig 2: residence-time distributions by exit type ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for g, c in zip(gs, colors):
        for ax, data in zip(axes, [res_crime[g], res_home[g]]):
            if data.size:
                ax.hist(data, bins=40, histtype="step", density=True, color=c, label="g=%g" % g)
    axes[0].set_title("Residence time | exit by CRIME")
    axes[1].set_title("Residence time | exit by HOME return")
    for ax in axes:
        ax.set_xlabel("residence time (days)"); ax.set_ylabel("density")
        ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout()
    C.save_fig(fig, "residence_by_exit_type", output_dir)

    # ---- Fig 3: mean/CV vs g, mean +/- SEM across seeds ----
    def ebar(ax, col, label, marker="o", color=C.PALETTE["police"]):
        ax.errorbar(gx, mvs[col], yerr=svs[col], fmt=marker + "-", capsize=3, lw=1.8,
                    color=color, label=label)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    ebar(axes[0], "global_intercrime_mean", "global mean", "o", C.PALETTE["police"])
    ebar(axes[0], "percell_intercrime_mean", "per-cell mean", "s", C.PALETTE["crime"])
    axes[0].set_ylabel("mean inter-crime gap (days)")
    ebar(axes[1], "residence_crime_mean", "exit by crime", "o", C.PALETTE["crime"])
    ebar(axes[1], "residence_home_mean", "exit by home", "s", C.PALETTE["police"])
    axes[1].set_ylabel("mean residence time (days)")
    ebar(axes[2], "global_intercrime_cv", "global gap CV", "o", C.PALETTE["police"])
    ebar(axes[2], "percell_intercrime_cv", "per-cell gap CV", "s", C.PALETTE["crime"])
    axes[2].axhline(1.0, color=C.PALETTE["accent_dark"], ls=":", lw=1.2, label="CV=1 (Poisson)")
    axes[2].set_ylabel("coefficient of variation")
    for ax in axes:
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.legend(fontsize=8)
    fig.suptitle("Waiting & residence times vs g (mean $\\pm$ SEM over seeds; "
                 "CV>1 = bursty, CV$\\approx$1 = Poisson)", y=0.99)
    fig.tight_layout()
    C.save_fig(fig, "waiting_times_vs_g", output_dir)

    # ---- Fig 4: exit fraction vs g, mean +/- SEM across seeds ----
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(gx, mvs["frac_exit_crime"], yerr=svs["frac_exit_crime"], fmt="o-",
                capsize=3, color=C.PALETTE["crime"], label="exit by crime")
    ax.errorbar(gx, mvs["frac_exit_home"], yerr=svs["frac_exit_home"], fmt="s-",
                capsize=3, color=C.PALETTE["police"], label="exit by home return")
    ax.set_xlabel(r"$g=\chi\bar M$"); ax.set_ylabel("fraction of exits")
    ax.set_ylim(-0.02, 1.02); ax.legend()
    ax.set_title("Exit-channel split vs g (mean $\\pm$ SEM over seeds)")
    fig.tight_layout()
    C.save_fig(fig, "exit_fraction_vs_g", output_dir)


if __name__ == "__main__":
    main()
    print("ANALYZE_WAITING_TIMES DONE")
