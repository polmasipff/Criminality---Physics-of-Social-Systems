"""plot_order_parameters.py — transition order parameters vs g.

Reads <output-dir>/runs/summary.csv (one stationary-tail row per run), aggregates
mean +/- SEM across seeds at each g, writes a tidy CSV, and plots four figures:

    order_parameters_vs_g    H, f_hot_2, f_hot_3, Gini_B, B_q{90,95,99}/<B>
    hotspot_overlap_vs_g     corr(B,M), corr(B,M)^2, M_mass_on_hot10, deterrence_hot
    transition_summary_vs_g  N, crimes/day, home/day, H  (the headline panel)
    exit_channels_vs_g       frac exits by crime vs home, crimes/day, home/day

x-axis is g = chi*M_bar; a secondary axis shows chi. Tidy output:
    runs/derived/order_parameters_vs_g.csv

Scientific caveats (see figure_plan.md): with the home channel active, H can be
INFLATED when crime gets sparse, so H is read together with f_hot, Gini_B, and N.
corr(B,M)^2 adds little over corr(B,M).

Generates NO simulations. Usage: python3 scripts/plot_order_parameters.py [--output-dir DIR]
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402

OBS = ["H", "f_hot_2", "f_hot_3", "B_q90_over_mean", "B_q95_over_mean", "B_q99_over_mean",
       "Gini_B", "Gini_M", "MB_corr", "M_mass_on_hot10", "deterrence_mean", "deterrence_hot",
       "n_criminals", "crimes_that_day", "home_exits_that_day", "inflow_that_day",
       "frac_exit_crime", "frac_exit_home", "crime_entropy", "mean_p_crime", "mean_p_home"]


def secondary_chi_axis(ax, gmean, chimean):
    if len(gmean) < 2:
        return
    sa = ax.secondary_xaxis("top")
    ticks = ax.get_xticks()
    # map g->chi linearly (chi = g/M_bar, a constant factor at fixed L,M_tot)
    factor = np.nanmedian(np.divide(chimean, gmean, out=np.full_like(chimean, np.nan),
                                    where=gmean != 0))
    sa.set_xticks(ticks)
    sa.set_xticklabels(["%.0f" % (t * factor) for t in ticks], fontsize=8)
    sa.set_xlabel(r"$\chi$", fontsize=9)


def main():
    output_dir = C.get_opt("--output-dir")
    summ = C.load_summary(output_dir)
    if summ.empty:
        print("no summary.csv under", C.runs_dir(output_dir), "- run the scan first.")
        return
    have = [c for c in OBS if c in summ.columns]
    x, m, s = C.agg_by(summ, "g", have)
    chimean = summ.groupby("g")["chi"].mean().reindex(x).values

    # tidy CSV
    tidy = pd.DataFrame({"g": x, "chi": chimean})
    for c in have:
        tidy[c + "_mean"] = m[c].values
        tidy[c + "_sem"] = s[c].values
    tidy["n_seeds"] = summ.groupby("g").size().reindex(x).values
    out_csv = os.path.join(C.derived_dir(output_dir), "order_parameters_vs_g.csv")
    tidy.to_csv(out_csv, index=False)
    print("wrote", out_csv)

    def eb(ax, col, label, marker="o", color="C0"):
        if col not in m:
            return
        ax.errorbar(x, m[col], yerr=s[col], fmt=marker + "-", capsize=2,
                    color=color, label=label)

    # ---- Fig 1: structural order parameters ----
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    eb(axes[0, 0], "H", r"$H=\sigma_B/\langle B\rangle$")
    axes[0, 0].set_ylabel("H (read with caveat)")
    eb(axes[0, 1], "f_hot_2", r"$f_{hot}$ ($B\geq2\langle B\rangle$)", color="C1")
    eb(axes[0, 1], "f_hot_3", r"$f_{hot}$ ($B\geq3\langle B\rangle$)", marker="s", color="C3")
    axes[0, 1].set_ylabel("hotspot area fraction"); axes[0, 1].legend(fontsize=8)
    eb(axes[1, 0], "B_q90_over_mean", r"$B_{90}/\langle B\rangle$", color="C0")
    eb(axes[1, 0], "B_q95_over_mean", r"$B_{95}/\langle B\rangle$", marker="s", color="C2")
    eb(axes[1, 0], "B_q99_over_mean", r"$B_{99}/\langle B\rangle$", marker="^", color="C3")
    axes[1, 0].set_ylabel("B tail quantiles / mean"); axes[1, 0].legend(fontsize=8)
    eb(axes[1, 1], "Gini_B", "Gini(B)", color="C4")
    axes[1, 1].set_ylabel("Gini(B)")
    for ax in axes.ravel():
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    secondary_chi_axis(axes[0, 0], x, chimean)
    fig.suptitle("Hotspot order parameters vs g (return-home, $\\delta=1/15$; "
                 "mean $\\pm$ SEM over seeds)", y=0.995)
    fig.tight_layout()
    C.save_fig(fig, "order_parameters_vs_g", output_dir)

    # ---- Fig 2: police-crime overlap ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    eb(axes[0], "MB_corr", r"corr$(B,M)$", color="C0")
    if "MB_corr" in m:
        axes[0].plot(x, m["MB_corr"].values ** 2, "s--", color="C1", label=r"corr$(B,M)^2$")
    axes[0].set_ylabel("police-crime correlation"); axes[0].legend(fontsize=8)
    eb(axes[1], "M_mass_on_hot10", "fraction of M on top-10% B cells", color="C2")
    axes[1].set_ylabel("M mass on hot10")
    eb(axes[2], "deterrence_hot", r"$\langle e^{-\chi M}\rangle$ on top-10% B", color="C3")
    eb(axes[2], "deterrence_mean", r"$\langle e^{-\chi M}\rangle$ all sites", marker="s", color="C0")
    axes[2].set_ylabel("deterrence factor"); axes[2].legend(fontsize=8)
    for ax in axes:
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    fig.suptitle("Police-crime overlap and deterrence vs g", y=0.99)
    fig.tight_layout()
    C.save_fig(fig, "hotspot_overlap_vs_g", output_dir)

    # ---- Fig 3: headline transition summary ----
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    eb(axes[0, 0], "n_criminals", "criminal population N", color="C0")
    axes[0, 0].set_ylabel("N (bounded by return-home)")
    eb(axes[0, 1], "crimes_that_day", "crimes / day", color="C3")
    eb(axes[0, 1], "home_exits_that_day", "home exits / day", marker="s", color="C0")
    if "inflow_that_day" in m:
        axes[0, 1].plot(x, m["inflow_that_day"], "k:", lw=1, label=r"inflow $\Gamma L^2$")
    axes[0, 1].set_ylabel("exits / day"); axes[0, 1].legend(fontsize=8)
    eb(axes[1, 0], "H", r"$H=\sigma_B/\langle B\rangle$", color="C2")
    axes[1, 0].set_ylabel("H")
    eb(axes[1, 1], "f_hot_2", r"$f_{hot}$", color="C1")
    axes[1, 1].set_ylabel("hotspot area fraction")
    for ax in axes.ravel():
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    fig.suptitle("Transition summary vs g: bounded N, falling crime, hotspots dissolve",
                 y=0.995)
    fig.tight_layout()
    C.save_fig(fig, "transition_summary_vs_g", output_dir)

    # ---- Fig 4: exit channels ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    eb(axes[0], "frac_exit_crime", "fraction of exits by crime", color="C3")
    eb(axes[0], "frac_exit_home", "fraction of exits by home return", marker="s", color="C0")
    axes[0].set_ylabel("exit-channel fraction"); axes[0].set_ylim(-0.02, 1.02)
    axes[0].legend(fontsize=9)
    eb(axes[1], "crimes_that_day", "crimes / day", color="C3")
    eb(axes[1], "home_exits_that_day", "home exits / day", marker="s", color="C0")
    axes[1].set_ylabel("criminals / day"); axes[1].legend(fontsize=9)
    for ax in axes:
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    fig.suptitle("Exit channels vs g: as deterrence rises, crime gives way to home exits",
                 y=0.99)
    fig.tight_layout()
    C.save_fig(fig, "exit_channels_vs_g", output_dir)


if __name__ == "__main__":
    main()
    print("PLOT_ORDER_PARAMETERS DONE")
