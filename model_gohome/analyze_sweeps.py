"""analyze_sweeps.py - figures for the isolated chi-sliced removal sweeps.
Reads runs/summary.csv; writes figures/sweep_*. Safe to re-run.
Order parameters include the hotspot-area fraction f_hot (f_hot_2 = sites with B>=2<B>).
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
d = pd.read_csv(os.path.join(HERE, "runs", "summary.csv"))
M_BAR = 500.0 / 128 ** 2


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def agg(sub, xcol):
    g = sub.groupby(xcol)
    m = g.mean(numeric_only=True)
    s = g.std(numeric_only=True).div(np.sqrt(g.size()), axis=0)
    return m.index.values, m, s


# reference (no-removal) anchors at each chi slice: g=0 -> base, g>0 -> dissuasion
def anchor(g, col):
    r = d[(d.mech.isin(["base", "dissuasion"])) & np.isclose(d.g, g)
          & np.isclose(d.h, 0) & np.isclose(d.delta, 0)]
    return r[col].mean() if len(r) else np.nan


OBS = [("crimes_that_day", "crimes / day"),
       ("n_criminals", "criminal population N"),
       ("f_hot_2", r"hotspot fraction $f_{hot}$ ($B\geq2\langle B\rangle$)"),
       ("H", r"$H=\sigma_B/\langle B\rangle$")]


# ===== Fig 1: mechanism contrast at chi=0 (dissuasion-g vs arrest-h vs home-delta)
def fig_contrast():
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    # dissuasion series (x=g): base + dissuasion, h=delta=0
    dis = d[(d.mech.isin(["base", "dissuasion"])) & np.isclose(d.h, 0)
            & np.isclose(d.delta, 0)]
    # arrest chi=0 (x=h): include h=0 anchor (base)
    arr = d[(d.mech == "arrest") & np.isclose(d.g, 0) & np.isclose(d.delta, 0)]
    hom = d[(d.mech == "home") & np.isclose(d.g, 0) & np.isclose(d.h, 0)]
    for ax, (col, lab) in zip(axes.ravel(), OBS):
        x, m, s = agg(dis, "g")
        ax.errorbar(x, m[col], yerr=s[col], fmt="o-", color="C0", capsize=2,
                    label="dissuasion (x=g)")
        x, m, s = agg(arr, "h")
        x = np.r_[0.0, x]; y = np.r_[anchor(0, col), m[col].values]
        ax.plot(x, y, "s-", color="C1", label="arrest (x=h), χ=0")
        x, m, s = agg(hom, "delta")
        x = np.r_[0.0, x]; y = np.r_[anchor(0, col), m[col].values]
        ax.plot(x, y, "^-", color="C2", label="home (x=δ), χ=0")
        ax.set_xlabel("control parameter (g, h, or δ)"); ax.set_ylabel(lab)
        ax.grid(alpha=.3)
    axes[0, 0].axhline(anchor(0, "inflow_that_day"), color="r", ls="--", lw=1,
                       alpha=.7, label="inflow Γ·L²")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Mechanism contrast at χ=0 (L=64): dissuasion only rearranges; "
                 "arrest/home suppress crime")
    fig.tight_layout()
    save(fig, "sweep_mechanism_contrast")


# ===== Fig 2: chi slices for arrest, then home =====
def fig_chi_slices(mech, xcol, xlabel, fname):
    cols = [("crimes_that_day", "crimes / day"),
            ("n_criminals", "criminal population N"),
            ("f_hot_2", r"hotspot fraction $f_{hot}$")]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for gslice, c in [(0.0, "C0"), (1.0, "C1"), (3.0, "C2")]:
        sub = d[(d.mech == mech) & np.isclose(d.g, gslice)]
        if sub.empty:
            continue
        x, m, s = agg(sub, xcol)
        x = np.r_[0.0, x]
        for ax, (col, lab) in zip(axes, cols):
            y = np.r_[anchor(gslice, col), m[col].values]
            ax.plot(x, y, "o-", color=c, label=f"g={gslice:g}")
    for ax, (col, lab) in zip(axes, cols):
        ax.set_xlabel(xlabel); ax.set_ylabel(lab); ax.grid(alpha=.3); ax.legend()
    fig.suptitle(f"{mech} sweep at fixed dissuasion slices "
                 f"(higher χ shifts the crossover to lower {xlabel})")
    fig.tight_layout()
    save(fig, fname)


# ===== Fig 3: arrest vs home on the mean-removal-hazard axis (chi=0) =====
def fig_arrest_vs_home():
    cols = [("crimes_that_day", "crimes / day"),
            ("n_criminals", "criminal population N"),
            ("f_hot_2", r"hotspot fraction $f_{hot}$")]
    arr = d[(d.mech == "arrest") & np.isclose(d.g, 0)]
    hom = d[(d.mech == "home") & np.isclose(d.g, 0)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    # mean removal hazard: arrest -> h (=kappa*M_bar); home -> delta
    xa, ma, sa = agg(arr, "h")
    xh, mh, sh = agg(hom, "delta")
    for ax, (col, lab) in zip(axes, cols):
        ya = np.r_[anchor(0, col), ma[col].values]
        yh = np.r_[anchor(0, col), mh[col].values]
        ax.plot(np.r_[0, xa], ya, "s-", color="C1", label="arrest (h)")
        ax.plot(np.r_[0, xh], yh, "^-", color="C2", label="home (δ)")
        ax.set_xlabel("mean removal hazard (h or δ)"); ax.set_ylabel(lab)
        ax.grid(alpha=.3); ax.legend()
    fig.suptitle("Arrest vs home at equal MEAN hazard (χ=0): arrest is spatially "
                 "targeted on hotspots, so it should bite earlier")
    fig.tight_layout()
    save(fig, "sweep_arrest_vs_home")


# ===== Fig 4: does arrest de-focus M as crime collapses? =====
def fig_M_defocus():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for gslice, c in [(0.0, "C0"), (1.0, "C1"), (3.0, "C2")]:
        sub = d[(d.mech == "arrest") & np.isclose(d.g, gslice)]
        if sub.empty:
            continue
        x, m, s = agg(sub, "h")
        axes[0].plot(x, m["M_mass_on_hot10"], "o-", color=c, label=f"g={gslice:g}")
        axes[1].plot(x, m["M_cv"], "o-", color=c, label=f"g={gslice:g}")
    axes[0].set_ylabel("M mass on hot10"); axes[1].set_ylabel("M CV = σ_M/⟨M⟩")
    for ax in axes:
        ax.set_xlabel("arrest h"); ax.grid(alpha=.3); ax.legend()
    fig.suptitle("Arrest feedback: as crime collapses, police field M de-concentrates "
                 "→ arrest tends to uniform")
    fig.tight_layout()
    save(fig, "sweep_M_defocus")


if __name__ == "__main__":
    fig_contrast()
    fig_chi_slices("arrest", "h", "h", "sweep_arrest_chi_slices")
    fig_chi_slices("home", "delta", "δ", "sweep_home_chi_slices")
    fig_arrest_vs_home()
    fig_M_defocus()
    print("ANALYZE_SWEEPS DONE")
