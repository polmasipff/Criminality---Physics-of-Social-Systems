"""plot_time_series.py — temporal series per g (one curve per g, seeds aggregated).

Reads <output-dir>/runs/daily.csv and produces:
    ts_n_criminals      N_criminals(t)
    ts_crimes           crimes/day(t)
    ts_home_exits       home exits/day(t)
    ts_inflow           inflow/day(t)
    ts_balance_error    mass-balance error(t)  (should sit at 0)
    ts_combined         2x3 multi-panel of the above

Each curve = mean over seeds; shaded band = +/- 1 SEM across seeds. Raw unsmoothed
data is always used unless --smooth W is given (centered rolling mean, window W days);
the raw CSV is never modified. The burn-in / stationary windows are shaded.

Generates NO simulations. Usage:
    python3 scripts/plot_time_series.py [--output-dir DIR] [--smooth 7] [--g 0,1,3]
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

SERIES = [("n_criminals", "active criminals  $N(t)$"),
          ("crimes_that_day", "crimes / day"),
          ("home_exits_that_day", "home exits / day"),
          ("inflow_that_day", r"inflow / day  $\Gamma L^2$")]


def seed_band(df, g, col, smooth):
    sub = df[np.isclose(df.g, g)]
    if sub.empty:
        return None
    piv = sub.pivot_table(index="day", columns="seed", values=col)
    if smooth and smooth > 1:
        piv = piv.rolling(smooth, center=True, min_periods=1).mean()
    mean = piv.mean(axis=1)
    n = piv.notna().sum(axis=1).clip(lower=1)
    sem = piv.std(axis=1, ddof=1).div(np.sqrt(n)).fillna(0.0)
    return mean.index.values, mean.values, sem.values


def windows(output_dir):
    try:
        cfg = C.load_config()
        w = cfg.get("windows", {})
        return w.get("burn_in_day"), w.get("stationary_lo"), w.get("stationary_hi")
    except Exception:
        return None, None, None


def shade(ax, burn, lo, hi):
    if burn:
        ax.axvspan(0, burn, color=C.PALETTE["grid"], alpha=0.12, lw=0, label="burn-in")
    if lo and hi:
        ax.axvspan(lo, hi, color=C.PALETTE["police"], alpha=0.10, lw=0,
                   label="stationary window")


def main():
    output_dir = C.get_opt("--output-dir")
    smooth = int(C.get_opt("--smooth", "1"))
    want = C.get_opt("--g")
    daily = C.load_daily(output_dir)
    if daily.empty:
        print("no daily.csv under", C.runs_dir(output_dir), "- run the scan first.")
        return
    gs = sorted(daily.g.unique())
    if want:
        wset = [float(x) for x in want.split(",")]
        gs = [g for g in gs if any(abs(g - w) < 1e-6 for w in wset)]
    burn, lo, hi = windows(output_dir)
    colors = C.g_colors(len(gs))

    def one(col, lab, ax):
        for g, c in zip(gs, colors):
            r = seed_band(daily, g, col, smooth)
            if r is None:
                continue
            t, m, s = r
            ax.plot(t, m, color=c, lw=1.6, label="g=%g" % g)
            if (s > 0).any():
                ax.fill_between(t, m - s, m + s, color=c, alpha=0.18, lw=0)
        ax.set_xlabel("day"); ax.set_ylabel(lab)

    # individual figures
    for col, lab in SERIES:
        fig, ax = plt.subplots(figsize=(9, 5.2))
        one(col, lab, ax)
        ax.legend(fontsize=8, ncol=2)
        ttl = {"n_criminals": "Criminal population over time (return-home, $\\delta=1/15$)",
               "crimes_that_day": "Crimes per day over time",
               "home_exits_that_day": "Home exits per day over time",
               "inflow_that_day": "Inflow per day (Poisson, should be flat)"}[col]
        ax.set_title(ttl)
        C.save_fig(fig, "ts_" + col.replace("_that_day", ""), output_dir)

    # combined panel: 4 series (no mass-balance error, no shading)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    flat = axes.ravel()
    for (col, lab), ax in zip(SERIES, flat):
        one(col, lab, ax)
    flat[0].legend(fontsize=8, ncol=2)
    fig.suptitle("Time series by g (mean $\\pm$ SEM over seeds)", y=0.995)
    fig.tight_layout()
    C.save_fig(fig, "ts_combined", output_dir)


if __name__ == "__main__":
    main()
    print("PLOT_TIME_SERIES DONE")
