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


# --------------------------------------------------------------------------- #
#  Maximum-likelihood fits + Kolmogorov-Smirnov goodness, on the tail x >= xmin
# --------------------------------------------------------------------------- #
def _ks(x_sorted, cdf_model):
    """KS distance between the empirical CDF of x_sorted and a model CDF callable."""
    n = x_sorted.size
    emp_hi = np.arange(1, n + 1) / n
    emp_lo = np.arange(0, n) / n
    fm = cdf_model(x_sorted)
    return float(np.max(np.maximum(np.abs(emp_hi - fm), np.abs(fm - emp_lo))))


def fit_powerlaw(a, xmin=None, scan=False):
    """Continuous power-law MLE (Clauset-Shalizi-Newman):
        p(x) = (alpha-1)/xmin * (x/xmin)^{-alpha} on x >= xmin,
        alpha = 1 + n / sum ln(x_i / xmin).
    DEFAULT (scan=False, xmin=None): xmin = min(positive) => fit the WHOLE sample.
    scan=True: scan candidate xmin and keep the one minimizing KS (CSN tail method).
    Returns dict(model, alpha, xmin, ks, loglik, n).
    """
    a = np.asarray(a, float); a = a[a > 0]
    if a.size < 10:
        return dict(model="powerlaw", alpha=np.nan, xmin=np.nan, ks=np.nan,
                    loglik=np.nan, n=int(a.size))

    def _fit_at(xm):
        tail = np.sort(a[a >= xm])
        if tail.size < 10 or xm <= 0:
            return None
        s = np.sum(np.log(tail / xm))
        if s <= 0:
            return None
        alpha = 1.0 + tail.size / s
        ks = _ks(tail, lambda x: 1.0 - (x / xm) ** (-(alpha - 1.0)))
        loglik = float(tail.size * np.log((alpha - 1.0) / xm) - alpha * s)
        return alpha, xm, ks, loglik, tail.size

    if xmin is not None:
        r = _fit_at(float(xmin))
    elif scan:
        cand = np.unique(np.percentile(a, np.linspace(0, 90, 25)))
        best = None
        for xm in cand:
            rr = _fit_at(xm)
            if rr and (best is None or rr[2] < best[2]):
                best = rr
        r = best
    else:                                   # whole-sample fit
        r = _fit_at(float(a.min()))
    if r is None:
        return dict(model="powerlaw", alpha=np.nan, xmin=np.nan, ks=np.nan,
                    loglik=np.nan, n=0)
    alpha, xm, ks, loglik, n = r
    return dict(model="powerlaw", alpha=float(alpha), xmin=float(xm), ks=float(ks),
                loglik=float(loglik), n=int(n))


def main():
    output_dir = C.get_opt("--output-dir")
    min_crimes = int(C.get_opt("--min-crimes", "1"))
    ev = load_events(output_dir)
    if ev.empty:
        print("no event logs under", os.path.join(C.runs_dir(output_dir), "events"))
        print("set output.save_event_logs: true (and event_log_g) in the config, then re-run.")
        return
    gs = sorted(ev.g.unique())
    colors = plt.cm.viridis(np.linspace(0, 0.9, len(gs)))

    summary = []
    global_gaps, cell_gaps = {}, {}
    res_crime, res_home = {}, {}
    for g in gs:
        dfg = ev[np.isclose(ev.g, g)]
        gg = global_intercrime(dfg)
        cg = percell_intercrime(dfg, min_crimes)
        rc = dfg[dfg.type == "crime"].residence.values
        rh = dfg[dfg.type == "home_exit"].residence.values
        global_gaps[g], cell_gaps[g] = gg, cg
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
            residence_crime_mean=float(rc.mean()) if rc.size else np.nan,
            residence_crime_median=float(np.median(rc)) if rc.size else np.nan,
            residence_home_mean=float(rh.mean()) if rh.size else np.nan,
            residence_home_median=float(np.median(rh)) if rh.size else np.nan,
        ))
    tidy = pd.DataFrame(summary)
    out_csv = os.path.join(C.derived_dir(output_dir), "waiting_times_summary.csv")
    tidy.to_csv(out_csv, index=False)
    print("wrote", out_csv)

    # ---- Fig 1: CCDFs of waiting times (log-y) ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for g, c in zip(gs, colors):
        a, yv = ccdf(global_gaps[g])
        if a.size:
            axes[0].step(a, yv, where="post", color=c, label="g=%g" % g)
        a, yv = ccdf(cell_gaps[g])
        if a.size:
            axes[1].step(a, yv, where="post", color=c, label="g=%g" % g)
    axes[0].set_title("Global inter-crime gap (mean pinned by inflow; see shape)")
    axes[1].set_title("Per-cell inter-crime gap (repeat victimization, >=%d crimes)" % min_crimes)
    for ax in axes:
        ax.set_yscale("log"); ax.set_xscale("log"); ax.set_xlabel("waiting time (days)")
        ax.set_ylabel("CCDF  P(T > t)"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.tight_layout()
    C.save_fig(fig, "waiting_times_ccdf", output_dir)

    # ---- Fig 1b: PDFs (log-log) with power-law MLE fits (whole sample, xmin=min) ----
    fit_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    panels = [("global inter-crime", global_gaps, axes[0]),
              ("per-cell inter-crime", cell_gaps, axes[1])]
    for label, gapsdict, ax in panels:
        for g, c in zip(gs, colors):
            a = gapsdict.get(g, np.array([]))
            cen, dens, _ = pdf_hist(a, nbins=40, log_bins=True)
            if cen.size:
                ax.plot(cen, dens, "o", ms=3.5, color=c, alpha=0.8, label="g=%g" % g)
            pl = fit_powerlaw(a)                 # whole-sample power-law (xmin = min)
            fit_rows.append(dict(g=g, quantity=label, **pl))
            a_pos = np.asarray(a, float); a_pos = a_pos[a_pos > 0]
            if a_pos.size >= 10 and np.isfinite(pl["alpha"]):
                xs = np.logspace(np.log10(pl["xmin"]), np.log10(a_pos.max()), 100)
                frac = (a_pos >= pl["xmin"]).mean()
                norm = frac * (pl["alpha"] - 1.0) / pl["xmin"]
                ax.plot(xs, norm * (xs / pl["xmin"]) ** (-pl["alpha"]),
                        "--", lw=1.2, color=c, alpha=0.6)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("waiting time (days)"); ax.set_ylabel("PDF  f(t)")
        ax.set_title(label + r"  (• data, -- power-law $t^{-\alpha}$)")
        ax.grid(alpha=.3, which="both"); ax.legend(fontsize=8)
    fig.suptitle("Inter-crime PDFs with power-law MLE fits (see waiting_times_fits.csv)",
                 y=0.99)
    fig.tight_layout()
    C.save_fig(fig, "waiting_times_pdf_fits", output_dir)

    fits = pd.DataFrame(fit_rows)
    fits_csv = os.path.join(C.derived_dir(output_dir), "waiting_times_fits.csv")
    fits.to_csv(fits_csv, index=False)
    print("wrote", fits_csv)
    if not fits.empty:
        print(fits[["g", "quantity", "model", "alpha", "xmin", "ks", "loglik", "n"]]
              .to_string(index=False))

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

    # ---- Fig 3: mean/median/CV vs g ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    axes[0].plot(tidy.g, tidy.global_intercrime_mean, "o-", label="global mean", color="C0")
    axes[0].plot(tidy.g, tidy.percell_intercrime_mean, "s-", label="per-cell mean", color="C1")
    axes[0].set_ylabel("mean inter-crime gap (days)")
    axes[1].plot(tidy.g, tidy.residence_crime_mean, "o-", label="exit by crime", color="C3")
    axes[1].plot(tidy.g, tidy.residence_home_mean, "s-", label="exit by home", color="C0")
    axes[1].set_ylabel("mean residence time (days)")
    axes[2].plot(tidy.g, tidy.global_intercrime_cv, "o-", label="global gap CV", color="C0")
    axes[2].plot(tidy.g, tidy.percell_intercrime_cv, "s-", label="per-cell gap CV", color="C1")
    axes[2].axhline(1.0, color="k", ls=":", lw=1, label="CV=1 (Poisson)")
    axes[2].set_ylabel("coefficient of variation")
    for ax in axes:
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.suptitle("Waiting & residence times vs g (CV>1 = bursty/clustered; CV≈1 = Poisson)",
                 y=0.99)
    fig.tight_layout()
    C.save_fig(fig, "waiting_times_vs_g", output_dir)

    # ---- Fig 4: exit fraction vs g ----
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(tidy.g, tidy.frac_exit_crime, "o-", color="C3", label="exit by crime")
    ax.plot(tidy.g, tidy.frac_exit_home, "s-", color="C0", label="exit by home return")
    ax.set_xlabel(r"$g=\chi\bar M$"); ax.set_ylabel("fraction of exits")
    ax.set_ylim(-0.02, 1.02); ax.grid(alpha=.3); ax.legend()
    ax.set_title("Exit-channel split vs g (from the event log)")
    fig.tight_layout()
    C.save_fig(fig, "exit_fraction_vs_g", output_dir)


if __name__ == "__main__":
    main()
    print("ANALYZE_WAITING_TIMES DONE")
