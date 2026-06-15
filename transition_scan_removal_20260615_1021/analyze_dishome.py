"""analyze_dishome.py - figures for the dissuasion + fixed home-exit (delta) model.
(1) delta selection: N, f_hot, H, crimes vs g for delta in {0, A0, omega, 0.1}.
(2) three-regime field panels at the chosen delta = 1/15.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
SNAP = os.path.join(HERE, "runs", "snapshots")
d = pd.read_csv(os.path.join(HERE, "runs", "summary.csv"))
dh = d[d.mech == "dishome"].copy()


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


DELTAS = sorted(dh.delta.unique())
LAB = {0.0: "δ=0 (blow-up)", round(1/30,6): "δ=A₀=1/30",
       round(1/15,6): "δ=ω=1/15 ✓", 0.1: "δ=0.1"}
def lab(dv):
    return LAB.get(round(dv, 6), "δ=%.3f" % dv)
COL = {0.0: "C3", round(1/30,6): "C0", round(1/15,6): "C2", 0.1: "C1"}


def fig_delta_select():
    obs = [("n_criminals", "criminal population N", False),
           ("f_hot_2", r"hotspot fraction $f_{hot}$", False),
           ("crimes_that_day", "crimes / day", False),
           ("H", r"$H=\sigma_B/\langle B\rangle$ (fragile under δ)", False)]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (col, ylab, _) in zip(axes.ravel(), obs):
        for dv in DELTAS:
            sub = dh[np.isclose(dh.delta, dv)].groupby("g")[col].mean()
            ax.plot(sub.index, sub.values, "o-", color=COL.get(round(dv, 6), "k"),
                    label=lab(dv))
        ax.set_xlabel("dissuasion g = χ·M̄"); ax.set_ylabel(ylab); ax.grid(alpha=.3)
    axes[0, 0].legend(fontsize=9)
    fig.suptitle("Choosing the home-exit rate δ (L=64): δ=ω=1/15 bounds N while "
                 "keeping the f_hot regimes; H washes out", y=0.995)
    fig.tight_layout()
    save(fig, "dishome_delta_selection")


def load(g):
    fn = os.path.join(SNAP, "snap_dishome_g%g_h0_d%g_seed0.npz" % (g, 1/15))
    return np.load(fn) if os.path.exists(fn) else None


def fig_regimes():
    cols = [(0.0, "pre  (g=0)"), (1.0, "transition  (g=1)"), (3.0, "post  (g=3)")]
    snaps = {g: load(g) for g, _ in cols}
    if any(v is None for v in snaps.values()):
        print("dishome snapshots missing; skip field panel")
        return
    rows = [("B", "B (attractiveness)", "hot", False),
            ("A_tilde", r"$\tilde A$ effective", "hot", False),
            ("crime_accum", "crime / mean (50d)", "magma", True)]
    day = 120
    fig, axes = plt.subplots(len(rows), len(cols), figsize=(3*len(cols), 3*len(rows)))
    for ri, (fk, rlab, cmap, rel) in enumerate(rows):
        arrs = []
        for g, _ in cols:
            a = snaps[g]["d%d_%s" % (day, fk)].astype(float)
            if rel:
                a = a / a.mean() if a.mean() > 0 else a
            arrs.append(a)
        vmax = 4.0 if rel else np.percentile(np.concatenate([a.ravel() for a in arrs]), 99)
        for ci, (g, clab) in enumerate(cols):
            ax = axes[ri, ci]
            im = ax.imshow(arrs[ci], origin="lower", cmap=cmap, vmin=0, vmax=vmax)
            if ri == 0:
                ax.set_title(clab, fontsize=11)
            if ci == 0:
                ax.set_ylabel(rlab, fontsize=11)
            ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=axes[ri, :].tolist(), fraction=0.012, pad=0.01)
    fig.suptitle("Three regimes of the dissuasion + home-exit model (δ=ω=1/15, "
                 "L=64, day 120)", y=0.99)
    save(fig, "dishome_three_regimes")


if __name__ == "__main__":
    fig_delta_select()
    fig_regimes()
    print("ANALYZE_DISHOME DONE")
