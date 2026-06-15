"""analyze_mechanism.py — figures for the criminal-removal mechanism scan.
Reads runs/*.csv + runs/snapshots/*.npz, writes figures/ (PNG+PDF). Safe to re-run.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
SNAP = os.path.join(RUNS, "snapshots")
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

summ = pd.read_csv(os.path.join(RUNS, "summary.csv"))
daily = pd.read_csv(os.path.join(RUNS, "daily.csv"))


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(FIG, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


# representative strong configs (seed 0) for time series / fields
REP = [("base", 0.0, 0.0, 0.0, "k"),
       ("dissuasion", 3.0, 0.0, 0.0, "C0"),
       ("arrest", 0.0, 3.0, 0.0, "C1"),
       ("both", 3.0, 3.0, 0.0, "C2"),
       ("home", 1.0, 0.0, 1.0, "C3")]


def sel(df, mech, g, h, d, seed=0):
    return df[(df.mech == mech) & (np.isclose(df.g, g)) & (np.isclose(df.h, h))
              & (np.isclose(df.delta, d)) & (df.seed == seed)].sort_values("day")


# ----- Fig 1: time series of the four key observables -----
def fig_timeseries():
    obs = [("n_criminals", "criminal population N(t)"),
           ("crimes_that_day", "crimes / day"),
           ("arrests_that_day", "arrests / day"),
           ("H", r"hotspot index $H=\sigma_B/\langle B\rangle$")]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (k, lab) in zip(axes.ravel(), obs):
        for mech, g, h, d, c in REP:
            s = sel(daily, mech, g, h, d)
            if s.empty:
                continue
            tag = {"base": "base", "dissuasion": "dissuasion g=3",
                   "arrest": "arrest h=3", "both": "both g=h=3",
                   "home": "home δ=1"}[mech]
            ax.plot(s.day, s[k], color=c, lw=1.6, label=tag)
        ax.set_xlabel("day"); ax.set_ylabel(lab); ax.grid(alpha=.3)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Mechanism comparison over time (L=64, T=120, seed 0)")
    fig.tight_layout()
    save(fig, "mech_timeseries")


# ----- Fig 2: late-time response vs control parameter -----
def fig_late_vs_control():
    m = summ.groupby(["mech", "g", "h"]).agg(
        H=("H", "mean"), ncrim=("n_criminals", "mean"),
        crimes=("crimes_that_day", "mean")).reset_index()
    dis = m[m.mech == "dissuasion"].sort_values("g")
    arr = m[m.mech == "arrest"].sort_values("h")
    both = m[m.mech == "both"].sort_values("g")
    base = m[m.mech == "base"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, k, lab in [(axes[0], "ncrim", "late-time criminal population"),
                       (axes[1], "crimes", "late-time crimes / day"),
                       (axes[2], "H", "late-time H")]:
        ax.plot(dis.g, dis[k], "o-", color="C0", label="dissuasion (x=g)")
        ax.plot(arr.h, arr[k], "s-", color="C1", label="arrest (x=h)")
        ax.plot(both.g, both[k], "^-", color="C2", label="both (x=g=h)")
        if not base.empty:
            ax.axhline(base[k].values[0], color="k", ls=":", lw=1, label="base")
        ax.set_xlabel("control parameter g or h"); ax.set_ylabel(lab)
        ax.grid(alpha=.3); ax.legend(fontsize=8)
    axes[1].axhline(summ[summ.mech == "base"].inflow_that_day.mean(), color="r",
                    ls="--", lw=1, alpha=.7)
    axes[1].text(0.05, summ[summ.mech == "base"].inflow_that_day.mean() * 1.02,
                 "inflow Γ·L²", color="r", fontsize=8)
    fig.suptitle("Late-time response vs control: dissuasion inflates N at fixed crime; "
                 "arrest cuts both")
    fig.tight_layout()
    save(fig, "mech_late_vs_control")


# ----- Fig 3: exit-flux balance (the conservation argument made visible) -----
def fig_exit_balance():
    pts = [("base", 0, 0, 0), ("dissuasion", 3, 0, 0), ("arrest", 0, 3, 0),
           ("both", 3, 3, 0), ("home", 1, 0, 1), ("all", 1, 1, 0.5)]
    labels, cr, ar, hm, inf = [], [], [], [], []
    for mech, g, h, d in pts:
        s = summ[(summ.mech == mech) & np.isclose(summ.g, g) & np.isclose(summ.h, h)
                 & np.isclose(summ.delta, d)]
        if s.empty:
            continue
        labels.append({"base": "base", "dissuasion": "dissuasion\ng=3",
                       "arrest": "arrest\nh=3", "both": "both\ng=h=3",
                       "home": "home\nδ=1", "all": "all\ng=h=1,δ=.5"}[mech])
        cr.append(s.crimes_that_day.mean()); ar.append(s.arrests_that_day.mean())
        hm.append(s.home_exits_that_day.mean()); inf.append(s.inflow_that_day.mean())
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(x, cr, label="crimes", color="C3")
    ax.bar(x, ar, bottom=cr, label="arrests", color="C1")
    ax.bar(x, hm, bottom=np.array(cr) + np.array(ar), label="home exits", color="C0")
    ax.plot(x, inf, "k_", ms=22, mew=2.5, label="inflow Γ·L²")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("criminals / day"); ax.grid(alpha=.3, axis="y"); ax.legend()
    ax.set_title("Steady-state exit flux = inflow in every case.\n"
                 "Dissuasion routes all exit through crime; arrest/home re-route it, "
                 "so crime falls.")
    fig.tight_layout()
    save(fig, "mech_exit_balance")


# ----- Fig 4: field panels -----
def load(mech, g, h, d):
    fn = os.path.join(SNAP, f"snap_{mech}_g{g:g}_h{h:g}_d{d:g}_seed0.npz")
    return np.load(fn) if os.path.exists(fn) else None


def fig_fields():
    cols = [("base", 0, 0, 0, "base"), ("dissuasion", 3, 0, 0, "dissuasion g=3"),
            ("arrest", 0, 3, 0, "arrest h=3"), ("both", 3, 3, 0, "both g=h=3")]
    snaps = {c[4]: load(c[0], c[1], c[2], c[3]) for c in cols}
    if any(v is None for v in snaps.values()):
        print("field snapshots missing, skipping fig_fields")
        return
    rows = [("B", "B (attractiveness)", "hot", False),
            ("A_tilde", r"$\tilde A$ (effective)", "hot", False),
            ("crime_accum", "crime density / mean (50d)", "magma", True)]
    fig, axes = plt.subplots(len(rows), len(cols), figsize=(3 * len(cols), 3 * len(rows)))
    day = 120
    for ri, (fk, rlab, cmap, rel) in enumerate(rows):
        arrs = []
        for c in cols:
            a = snaps[c[4]][f"d{day}_{fk}"].astype(float)
            if rel:
                a = a / a.mean() if a.mean() > 0 else a
            arrs.append(a)
        vmax = 4.0 if rel else np.percentile(np.concatenate([a.ravel() for a in arrs]), 99)
        for ci, c in enumerate(cols):
            ax = axes[ri, ci]
            im = ax.imshow(arrs[ci], origin="lower", cmap=cmap, vmin=0, vmax=vmax)
            if ri == 0:
                ax.set_title(c[4], fontsize=10)
            if ci == 0:
                ax.set_ylabel(rlab, fontsize=11)
            ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=axes[ri, :].tolist(), fraction=0.012, pad=0.01)
    fig.suptitle("Fields at day 120 (L=64): dissuasion smears hotspots but keeps crime; "
                 "arrest empties the lattice", y=0.99)
    save(fig, "mech_field_panels")


if __name__ == "__main__":
    fig_timeseries()
    fig_late_vs_control()
    fig_exit_balance()
    fig_fields()
    print("ANALYZE_MECH DONE")
