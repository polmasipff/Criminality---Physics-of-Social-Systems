"""
analyze.py — build all figures + transition_estimates.csv from data/ CSVs.
Safe to re-run; uses whatever runs are present.
"""
import os, glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SNAP = os.path.join(HERE, "snapshots")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

summ = pd.read_csv(os.path.join(DATA, "all_runs_summary.csv"))
daily = pd.read_csv(os.path.join(DATA, "all_runs_daily.csv"))


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=160, bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def agg(df, by="chi"):
    """mean + sem across seeds, grouped."""
    g = df.groupby(by)
    m = g.mean(numeric_only=True)
    n = g.size()
    s = g.std(numeric_only=True)
    sem = s.div(np.sqrt(n), axis=0)
    return m, sem


# tanh / logistic crossover in log10(g)
def tanh_model(logg, lo, hi, gc, w):
    return lo + (hi - lo) * 0.5 * (1 - np.tanh((logg - gc) / w))


# ============================================================ Phase B/C order params
def fig_order_params():
    bc = summ[summ.phase.isin(["B", "C"])].copy()
    if bc.empty:
        return
    m, sem = agg(bc, "g")
    gs = m.index.values
    metrics = [("H", r"$H=\sigma_B/\langle B\rangle$"),
               ("f_hot_2", r"$f_{hot}$ ($B\geq2\bar B$)"),
               ("n_criminals", "criminals"),
               ("deterrence_hot", r"deterrence on hot10 $\langle e^{-\chi M}\rangle$"),
               ("MB_corr", r"corr$(B,M)$"),
               ("M_mass_on_hot10", "M mass on hot10")]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, (k, lab) in zip(axes.ravel(), metrics):
        ax.errorbar(gs, m[k], yerr=sem[k] if k in sem else None, fmt="o-",
                    ms=4, capsize=2)
        ax.set_xscale("log"); ax.set_xlabel("g = χ·M̄")
        ax.set_ylabel(lab); ax.grid(alpha=.3)
        ax.axvline(1.0, color="r", ls="--", lw=.8, alpha=.6)
    fig.suptitle("Transition order parameters vs g (B+C combined, mean±SEM over seeds)")
    fig.tight_layout()
    save(fig, "transition_order_parameters")


# ============================================================ focused + fit
def fig_focused_and_fit():
    bc = summ[summ.phase.isin(["B", "C"])].copy()
    if bc.empty:
        return None
    m, sem = agg(bc, "g")
    gs = m.index.values
    logg = np.log10(gs[gs > 0])
    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, k, lab in [(axes[0], "H", "H"),
                       (axes[1], "f_hot_2", r"$f_{hot}$")]:
        y = m[k].values[gs > 0]
        ye = (sem[k].values[gs > 0] if k in sem else np.full_like(y, np.nan))
        ax.errorbar(gs[gs > 0], y, yerr=ye, fmt="o", ms=5, capsize=2, label="data")
        try:
            p0 = [y.min(), y.max(), 0.0, 0.4]
            popt, pcov = curve_fit(tanh_model, logg, y, p0=p0, maxfev=20000)
            perr = np.sqrt(np.diag(pcov))
            xx = np.linspace(logg.min(), logg.max(), 200)
            ax.plot(10**xx, tanh_model(xx, *popt), "r-", lw=1.5,
                    label="tanh fit")
            gc = 10**popt[2]
            # width in decades -> multiplicative
            rows.append(dict(observable=k, g_c=gc, log10gc=popt[2],
                             log10gc_err=perr[2], width_decades=abs(popt[3]),
                             width_err=perr[3],
                             chi_c_Mtot500_L128=gc * 128**2 / 500))
            ax.axvline(gc, color="g", ls="--", lw=.8,
                       label=f"g_c={gc:.2f}")
        except Exception as e:
            print("fit failed", k, e)
        ax.set_xscale("log"); ax.set_xlabel("g = χ·M̄"); ax.set_ylabel(lab)
        ax.grid(alpha=.3); ax.legend()
    fig.suptitle("Focused transition: tanh crossover fit (mean±SEM over seeds)")
    fig.tight_layout()
    save(fig, "focused_transition_with_errorbars")
    if rows:
        est = pd.DataFrame(rows)
        est.to_csv(os.path.join(DATA, "transition_estimates.csv"), index=False)
        print(est.to_string(index=False))
        return est
    return None


# ============================================================ susceptibility proxy
def fig_susceptibility():
    bc = summ[summ.phase.isin(["B", "C"])].copy()
    if bc.empty:
        return
    # seed-to-seed std of H as susceptibility proxy + |dH/dlog g|
    g = bc.groupby("g")["H"]
    var = g.std()
    m = g.mean()
    gs = m.index.values
    dHdlogg = np.gradient(m.values, np.log10(np.maximum(gs, 1e-6)))
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    ax[0].plot(gs, var.values, "o-")
    ax[0].set_xscale("log"); ax[0].set_xlabel("g"); ax[0].set_ylabel("std_seed(H)")
    ax[0].set_title("seed-to-seed variance of H (susceptibility proxy)")
    ax[0].axvline(1, color="r", ls="--", lw=.8); ax[0].grid(alpha=.3)
    ax[1].plot(gs, np.abs(dHdlogg), "s-", color="purple")
    ax[1].set_xscale("log"); ax[1].set_xlabel("g")
    ax[1].set_ylabel("|dH/dlog g|"); ax[1].set_title("steepness of H(g)")
    ax[1].axvline(1, color="r", ls="--", lw=.8); ax[1].grid(alpha=.3)
    fig.tight_layout()
    save(fig, "susceptibility_proxy")


# ============================================================ field panels
def load_snap(phase, chi, L=128, seed=0, Mtot=500, kap=0):
    fn = os.path.join(SNAP, f"snap_{phase}_L{L}_chi{chi:g}_seed{seed}_"
                            f"Mtot{Mtot:g}_kap{kap:g}.npz")
    if not os.path.exists(fn):
        return None
    return np.load(fn)


def fig_field_panels():
    reps = [0, 10, 22, 36, 60, 100, 300]
    day = 365
    avail = [(c, load_snap("D", c)) for c in reps]
    avail = [(c, z) for c, z in avail if z is not None and f"d{day}_B" in z]
    if not avail:
        return
    fields = [("B", "B (dynamic attractiveness)", "hot"),
              ("M", "M (police field)", "viridis"),
              ("A_tilde", r"$\tilde A$ (effective attract.)", "hot"),
              ("deter", r"deterrence $e^{-\chi M}$", "cividis"),
              ("crime_accum", "crime density (last 50d)", "magma")]
    for fk, flab, cmap in fields:
        # fixed color scale across chi (per field)
        arrs = [z[f"d{day}_{fk}"] for _, z in avail]
        vmax = np.percentile(np.concatenate([a.ravel() for a in arrs]), 99)
        vmin = 0 if fk != "deter" else min(a.min() for a in arrs)
        if fk == "deter":
            vmax = 1.0
        n = len(avail)
        fig, axes = plt.subplots(1, n, figsize=(2.7 * n, 3.2))
        if n == 1:
            axes = [axes]
        for ax, (c, z) in zip(axes, avail):
            im = ax.imshow(z[f"d{day}_{fk}"], origin="lower", cmap=cmap,
                           vmin=vmin, vmax=vmax)
            ax.set_title(f"χ={c}\ng={c*500/128**2:.2f}", fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=axes, fraction=0.012, pad=0.01)
        fig.suptitle(f"{flab} — day {day}, fixed color scale")
        save(fig, f"field_panel_{fk}")


def fig_paper_style():
    cols = [(0, "pre (χ=0)"), (36, "transition (χ=36)"), (300, "post (χ=300)")]
    day = 365
    rows = [("B", "B", "hot"), ("M", "M", "viridis"),
            ("A_tilde", r"$\tilde A$", "hot"),
            ("crime_accum", "crime/mean (50d)", "magma")]
    snaps = {c: load_snap("D", c) for c, _ in cols}
    if any(s is None or f"d{day}_B" not in s for s in snaps.values()):
        return
    fig, axes = plt.subplots(len(rows), len(cols), figsize=(3.0 * len(cols),
                                                            3.0 * len(rows)))
    for ri, (fk, rlab, cmap) in enumerate(rows):
        rel = (fk == "crime_accum")
        arrs = []
        for c, _ in cols:
            a = snaps[c][f"d{day}_{fk}"].astype(float)
            if rel:
                a = a / a.mean() if a.mean() > 0 else a
            arrs.append(a)
        vmax = (4.0 if rel else
                np.percentile(np.concatenate([a.ravel() for a in arrs]), 99))
        for ci, (c, clab) in enumerate(cols):
            ax = axes[ri, ci]
            im = ax.imshow(arrs[ci], origin="lower", cmap=cmap,
                           vmin=0, vmax=vmax)
            if ri == 0:
                ax.set_title(clab, fontsize=11)
            if ci == 0:
                ax.set_ylabel(rlab, fontsize=12)
            ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=axes[ri, :].tolist(), fraction=0.012, pad=0.01)
    fig.suptitle("Hotspot → diffuse regime change (day 365, L=128, M_tot=500)",
                 y=0.995)
    save(fig, "field_panels_pre_transition_post")


# ============================================================ police-crime overlap
def fig_overlap():
    bc = summ[summ.phase.isin(["B", "C"])].copy()
    if bc.empty:
        return
    m, sem = agg(bc, "g")
    gs = m.index.values
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(gs, m["MB_corr"], yerr=sem["MB_corr"], fmt="o-", label="corr(B,M)")
    ax.errorbar(gs, m["M_mass_on_hot10"], yerr=sem["M_mass_on_hot10"], fmt="s-",
                label="M mass on hot10")
    ax.set_xscale("log"); ax.set_xlabel("g"); ax.grid(alpha=.3); ax.legend()
    ax.axvline(1, color="r", ls="--", lw=.8)
    ax.set_title("Police–crime spatial overlap vs g")
    fig.tight_layout()
    save(fig, "police_crime_overlap")


# ============================================================ hysteresis
def fig_hysteresis():
    e = summ[summ.phase == "E"].copy()
    if e.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for br, mk in [("up", "o-"), ("down", "s--")]:
        d = e[e.branch == br].sort_values("g")
        ax.plot(d.g, d.H, mk, label=f"{br} sweep")
    ax.set_xscale("log"); ax.set_xlabel("g"); ax.set_ylabel("H")
    ax.grid(alpha=.3); ax.legend(); ax.set_title("Hysteresis: H(g) up vs down")
    fig.tight_layout()
    save(fig, "hysteresis_loop")


# ============================================================ finite-size
def fig_finite_size():
    f = summ[summ.phase == "F"].copy()
    if f.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for L, c in [(64, "C0"), (128, "C1")]:
        d = f[f.L == L]
        if d.empty:
            continue
        m, sem = agg(d, "g")
        gs = m.index.values
        axes[0].errorbar(gs, m["H"], yerr=sem["H"], fmt="o-", color=c, label=f"L={L}")
        axes[1].errorbar(gs, m["f_hot_2"], yerr=sem["f_hot_2"], fmt="o-", color=c,
                         label=f"L={L}")
        dH = np.gradient(m["H"].values, np.log10(np.maximum(gs, 1e-6)))
        axes[2].plot(gs, np.abs(dH), "o-", color=c, label=f"L={L}")
    for ax, t in zip(axes, ["H(g)", "f_hot(g)", "|dH/dlog g| (sharpness)"]):
        ax.set_xlabel("g"); ax.set_title(t); ax.grid(alpha=.3); ax.legend()
        ax.axvline(1, color="r", ls="--", lw=.8)
    fig.suptitle("Finite-size comparison at matched g (M̄ fixed)")
    fig.tight_layout()
    save(fig, "finite_size_check")


# ============================================================ kappa mechanism
def fig_kappa():
    g = summ[summ.phase == "G"].copy()
    if g.empty:
        return
    def lab(r):
        if r.chi == 0 and r.kappa == 0: return "base"
        if r.chi > 0 and r.kappa == 0: return "dissuasion"
        if r.chi == 0 and r.kappa > 0: return "arrest"
        return "both"
    g["mech"] = g.apply(lab, axis=1)
    agg2 = g.groupby("mech").agg(H=("H", "mean"), Hsem=("H", "sem"),
                                 crim=("n_criminals", "mean"),
                                 crimsem=("n_criminals", "sem"),
                                 crimes=("crimes_that_day", "mean"),
                                 crimes_sem=("crimes_that_day", "sem"))
    order = ["base", "dissuasion", "arrest", "both"]
    agg2 = agg2.reindex([o for o in order if o in agg2.index])
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, col, semcol, t in [(axes[0], "H", "Hsem", "H (hotspot index)"),
                               (axes[1], "crim", "crimsem", "criminal population"),
                               (axes[2], "crimes", "crimes_sem", "crimes/day")]:
        ax.bar(agg2.index, agg2[col], yerr=agg2[semcol], capsize=4,
               color=["gray", "C0", "C1", "C2"][:len(agg2)])
        ax.set_title(t); ax.grid(alpha=.3, axis="y")
    fig.suptitle("Mechanism comparison: base / dissuasion / arrest / both")
    fig.tight_layout()
    save(fig, "optional_kappa_mechanism_comparison")


if __name__ == "__main__":
    fig_order_params()
    fig_focused_and_fit()
    fig_susceptibility()
    fig_field_panels()
    fig_paper_style()
    fig_overlap()
    fig_hysteresis()
    fig_finite_size()
    fig_kappa()
    print("ANALYZE DONE")
