"""plot_order_parameters.py — transition order parameters vs g, on the EFFECTIVE
attractiveness Atilde = A0 + B e^{-chi M} (NOT on B alone).

Rationale: B is the latent repeat-victimization memory and does NOT contain the
police suppression e^{-chi M}; the field the criminals actually respond to, and the
one that shows the police effect, is Atilde. So all structural order parameters here
are computed on Atilde (engine columns H_At, f_hotA_2/3, At_q*, Gini_At, AtM_corr,
M_mass_on_hotA10, deterrence_hotA). The B-based columns remain in summary.csv for
reference but are not plotted.

Reads <output-dir>/runs/summary.csv, aggregates mean +/- SEM across seeds at each g,
writes runs/derived/order_parameters_vs_g.csv and four figures:
    order_parameters_vs_g    H_At, f_hotA_2/3, At_q{90,95,99}/<At>, Gini_At
    hotspot_overlap_vs_g     corr(At,M), corr(At,M)^2, M_mass_on_hotA10, deterrence
    transition_summary_vs_g  N, crimes/day, home/day, H_At  (headline)
    exit_channels_vs_g       frac exits by crime vs home, crimes/day, home/day

x-axis is g = chi*M_bar; a secondary axis shows chi. Colors: Lattice & Heat palette.
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
C.apply_style()
P = C.PALETTE

OBS = ["H_At", "f_hotA_2", "f_hotA_3", "At_q90_over_mean", "At_q95_over_mean",
       "At_q99_over_mean", "Gini_At", "Gini_M", "AtM_corr", "M_mass_on_hotA10",
       "deterrence_mean", "deterrence_hotA", "Atilde_mean",
       "n_criminals", "crimes_that_day", "home_exits_that_day", "inflow_that_day",
       "frac_exit_crime", "frac_exit_home", "crime_entropy", "mean_p_crime", "mean_p_home"]


def secondary_chi_axis(ax, gmean, chimean):
    if len(gmean) < 2:
        return
    sa = ax.secondary_xaxis("top")
    ticks = ax.get_xticks()
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

    tidy = pd.DataFrame({"g": x, "chi": chimean})
    for c in have:
        tidy[c + "_mean"] = m[c].values
        tidy[c + "_sem"] = s[c].values
    tidy["n_seeds"] = summ.groupby("g").size().reindex(x).values
    out_csv = os.path.join(C.derived_dir(output_dir), "order_parameters_vs_g.csv")
    tidy.to_csv(out_csv, index=False)
    print("wrote", out_csv)

    def eb(ax, col, label, marker="o", color=P["crime"]):
        if col not in m:
            return
        ax.errorbar(x, m[col], yerr=s[col], fmt=marker + "-", capsize=2, lw=1.8,
                    color=color, label=label)

    # ---- Fig 1: structural order parameters on Atilde ----
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    eb(axes[0, 0], "H_At", r"$H_{\tilde A}=\sigma_{\tilde A}/\langle\tilde A\rangle$",
       color=P["crime"])
    axes[0, 0].set_ylabel(r"$H_{\tilde A}$")
    eb(axes[0, 1], "f_hotA_2", r"$f_{hot}$ ($\tilde A\geq2\langle\tilde A\rangle$)",
       color=P["crime"])
    eb(axes[0, 1], "f_hotA_3", r"$f_{hot}$ ($\tilde A\geq3\langle\tilde A\rangle$)",
       marker="s", color=P["accent"])
    axes[0, 1].set_ylabel("hotspot area fraction"); axes[0, 1].legend(fontsize=8)
    eb(axes[1, 0], "At_q90_over_mean", r"$\tilde A_{90}/\langle\tilde A\rangle$", color=P["police"])
    eb(axes[1, 0], "At_q95_over_mean", r"$\tilde A_{95}/\langle\tilde A\rangle$",
       marker="s", color=P["accent"])
    eb(axes[1, 0], "At_q99_over_mean", r"$\tilde A_{99}/\langle\tilde A\rangle$",
       marker="^", color=P["crime"])
    axes[1, 0].set_ylabel(r"$\tilde A$ tail quantiles / mean"); axes[1, 0].legend(fontsize=8)
    eb(axes[1, 1], "Gini_At", r"Gini($\tilde A$)", color=P["navy_mid"])
    axes[1, 1].set_ylabel(r"Gini($\tilde A$)")
    for ax in axes.ravel():
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    secondary_chi_axis(axes[0, 0], x, chimean)
    fig.suptitle(r"Hotspot order parameters on $\tilde A$ vs g (return-home, "
                 r"$\delta=1/15$; mean $\pm$ SEM)", y=0.995)
    fig.tight_layout()
    C.save_fig(fig, "order_parameters_vs_g", output_dir)

    # ---- Fig 2: police-crime overlap (on Atilde) ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    eb(axes[0], "AtM_corr", r"corr$(\tilde A,M)$", color=P["police"])
    if "AtM_corr" in m:
        axes[0].plot(x, m["AtM_corr"].values ** 2, "s--", color=P["accent"],
                     label=r"corr$(\tilde A,M)^2$")
    axes[0].set_ylabel(r"police-$\tilde A$ correlation"); axes[0].legend(fontsize=8)
    eb(axes[1], "M_mass_on_hotA10", r"fraction of $M$ on top-10% $\tilde A$", color=P["police"])
    axes[1].set_ylabel("M mass on hot10")
    eb(axes[2], "deterrence_hotA", r"$\langle e^{-\chi M}\rangle$ on top-10% $\tilde A$",
       color=P["crime"])
    eb(axes[2], "deterrence_mean", r"$\langle e^{-\chi M}\rangle$ all sites",
       marker="s", color=P["navy_mid"])
    axes[2].set_ylabel("deterrence factor"); axes[2].legend(fontsize=8)
    for ax in axes:
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    fig.suptitle(r"Police-$\tilde A$ overlap and deterrence vs g", y=0.99)
    fig.tight_layout()
    C.save_fig(fig, "hotspot_overlap_vs_g", output_dir)

    # ---- Fig 3: headline transition summary ----
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    eb(axes[0, 0], "n_criminals", "criminal population N", color=P["ink"])
    axes[0, 0].set_ylabel("N (bounded by return-home)")
    eb(axes[0, 1], "crimes_that_day", "crimes / day", color=P["crime"])
    eb(axes[0, 1], "home_exits_that_day", "home exits / day", marker="s", color=P["police"])
    if "inflow_that_day" in m:
        axes[0, 1].plot(x, m["inflow_that_day"], ":", color=P["grid"], lw=1.2,
                        label=r"inflow $\Gamma L^2$")
    axes[0, 1].set_ylabel("exits / day"); axes[0, 1].legend(fontsize=8)
    eb(axes[1, 0], "H_At", r"$H_{\tilde A}=\sigma_{\tilde A}/\langle\tilde A\rangle$",
       color=P["crime"])
    axes[1, 0].set_ylabel(r"$H_{\tilde A}$")
    eb(axes[1, 1], "f_hotA_2", r"$f_{hot}$ on $\tilde A$", color=P["accent"])
    axes[1, 1].set_ylabel("hotspot area fraction")
    for ax in axes.ravel():
        ax.set_xlabel(r"$g=\chi\bar M$"); ax.grid(alpha=.3)
    fig.suptitle(r"Transition summary vs g (on $\tilde A$): bounded N, falling crime, "
                 r"hotspots dissolve", y=0.995)
    fig.tight_layout()
    C.save_fig(fig, "transition_summary_vs_g", output_dir)

    # ---- Fig 4: exit channels ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    eb(axes[0], "frac_exit_crime", "fraction of exits by crime", color=P["crime"])
    eb(axes[0], "frac_exit_home", "fraction of exits by home return", marker="s",
       color=P["police"])
    axes[0].set_ylabel("exit-channel fraction"); axes[0].set_ylim(-0.02, 1.02)
    axes[0].legend(fontsize=9)
    eb(axes[1], "crimes_that_day", "crimes / day", color=P["crime"])
    eb(axes[1], "home_exits_that_day", "home exits / day", marker="s", color=P["police"])
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
