"""common.py — shared helpers for the return-home figure pipeline.

Config loading, g<->chi conversions, paths, figure saving, seed aggregation, and
field-level order-parameter computations used by the plotting/analysis scripts.

Nothing here runs a simulation.
"""
import os
import sys
import numpy as np
import pandas as pd

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # the project folder
DEFAULT_CONFIG = os.path.join(ROOT, "config", "scan_config_template.yaml")
# New return-home outputs live under their OWN root so they never collide with the
# legacy top-level runs/ + figures/ (which were produced by the obsolete arrest engine
# and have a different CSV schema). Override with --output-dir.
DEFAULT_OUT = os.path.join(ROOT, "out_return_home")


# --------------------------------------------------------------------------- #
#  config + parameter conversions
# --------------------------------------------------------------------------- #
def load_config(path=None, run_set=None):
    """Load the YAML config. If run_set is given, its keys override grid/windows."""
    if yaml is None:
        raise RuntimeError("pyyaml not available; pip install pyyaml")
    path = path or DEFAULT_CONFIG
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if run_set:
        rs = cfg.get("run_sets", {}).get(run_set)
        if rs is None:
            raise KeyError("run_set %r not in config (have %s)"
                           % (run_set, list(cfg.get("run_sets", {}))))
        for k in ("L", "g_values", "seeds", "T_max"):
            if k in rs:
                cfg["grid"][k] = rs[k]
        if "windows" in rs:
            cfg["windows"].update(rs["windows"])
        cfg["_active_run_set"] = run_set
    return cfg


def chi_from_g(g, L, M_tot):
    """chi = g * L^2 / M_tot  =  g / M_bar."""
    return g * (L * L) / M_tot


def g_from_chi(chi, L, M_tot):
    return chi * M_tot / (L * L)


def m_bar(L, M_tot):
    return M_tot / (L * L)


# --------------------------------------------------------------------------- #
#  paths
# --------------------------------------------------------------------------- #
def runs_dir(output_dir=None):
    return os.path.join(output_dir or DEFAULT_OUT, "runs")


def figures_dir(output_dir=None):
    d = os.path.join(output_dir or DEFAULT_OUT, "figures")
    os.makedirs(d, exist_ok=True)
    return d


def derived_dir(output_dir=None):
    """Tidy CSVs derived by the analysis scripts (order params, waiting times)."""
    d = os.path.join(output_dir or DEFAULT_OUT, "runs", "derived")
    os.makedirs(d, exist_ok=True)
    return d


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
#  Colorblind-safe palette (Okabe & Ito 2008), with role names kept.
#  All categorical colors are drawn from the Okabe-Ito set, which is mutually
#  distinguishable under deuteranopia / protanopia / tritanopia. Heat maps are
#  single-hue (light->dark) ramps, which are inherently colorblind-safe; the
#  deterrence map uses cividis (CVD-optimized). No gridlines are drawn.
# --------------------------------------------------------------------------- #
# Okabe-Ito base
_OI = dict(black="#000000", orange="#E69F00", skyblue="#56B4E9", green="#009E73",
           yellow="#F0E442", blue="#0072B2", vermillion="#D55E00", purple="#CC79A7")

PALETTE = dict(
    ink="#1B2A4A",            # dark navy for text (non-data)
    paper="#F4F1EA",          # light background (non-data)
    crime=_OI["vermillion"],  # crime / B / Atilde  (warm)
    police=_OI["blue"],       # police field M      (cool)  -> orange/blue is the safest pair
    accent=_OI["orange"],     # secondary highlight
    grid="#6B6A64",           # axis spines / ticks (no gridlines are drawn)
    crime_light="#F2C0A4",    # light vermillion (cmap endpoint)
    police_light="#9EC9E6",   # light blue (cmap endpoint)
    accent_dark="#9C6B00",    # dark orange (reference lines)
    navy_mid=_OI["skyblue"],  # sky blue (distinct line color)
    green=_OI["green"], purple=_OI["purple"], yellow=_OI["yellow"],
)
# categorical cycle (all mutually CVD-distinct)
CYCLE = [_OI["vermillion"], _OI["blue"], _OI["orange"], _OI["green"],
         _OI["purple"], _OI["skyblue"]]
# fixed colors for the candidate waiting-time laws (5 distinct Okabe-Ito hues)
MODEL_COLORS = {
    "exponential": _OI["blue"], "weibull": _OI["orange"], "lognormal": _OI["green"],
    "powerlaw": _OI["vermillion"], "trunc_powerlaw": _OI["purple"],
}


def _segmap(name, colors):
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(name, colors)


# single-hue sequential heat maps (light -> saturated -> dark) = colorblind-safe
CMAP_CRIME = _segmap("cb_crime", ["#FFF7F2", PALETTE["crime_light"],
                                  PALETTE["crime"], "#5A2600"])
CMAP_POLICE = _segmap("cb_police", ["#F2F8FC", PALETTE["police_light"],
                                    PALETTE["police"], "#022A44"])


def _get_cmap(name):
    import matplotlib
    try:
        return matplotlib.colormaps[name]            # modern API (mpl >= 3.6)
    except Exception:
        import matplotlib.cm as _cm
        return _cm.get_cmap(name)


CMAP_DETER = _get_cmap("cividis")   # deterrence e^{-chi M}: CVD-optimized sequential


def g_colors(n):
    """n colors along the colorblind-safe perceptually-uniform viridis ramp, for
    curves ordered by g (dark = low g, bright = high g)."""
    if n <= 1:
        return [PALETTE["crime"]]
    vir = _get_cmap("viridis")
    return [vir(t) for t in np.linspace(0.05, 0.92, n)]


def apply_style():
    """Apply the colorblind-safe look and DISABLE all gridlines (call once)."""
    import matplotlib as mpl
    import matplotlib.axes as _maxes
    mpl.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": PALETTE["grid"],
        "axes.labelcolor": PALETTE["ink"],
        "axes.titlecolor": PALETTE["ink"],
        "text.color": PALETTE["ink"],
        "xtick.color": PALETTE["grid"],
        "ytick.color": PALETTE["grid"],
        "axes.grid": False,
        "axes.prop_cycle": mpl.cycler(color=CYCLE),
        "font.size": 11,
        "axes.titlesize": 12,
    })
    # Force every ax.grid(...) call to a no-op so NO gridlines appear anywhere,
    # regardless of explicit calls in the plotting scripts.
    if not getattr(_maxes.Axes, "_grid_disabled", False):
        _maxes.Axes.grid = lambda self, *a, **k: None
        _maxes.Axes._grid_disabled = True


def save_fig(fig, name, output_dir=None, dpi=150):
    import matplotlib.pyplot as plt
    fd = figures_dir(output_dir)
    fig.savefig(os.path.join(fd, name + ".png"), dpi=dpi, bbox_inches="tight")
    fig.savefig(os.path.join(fd, name + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print("saved", os.path.join("figures", name + ".{png,pdf}"))


# --------------------------------------------------------------------------- #
#  data loading + seed aggregation
# --------------------------------------------------------------------------- #
def load_summary(output_dir=None):
    p = os.path.join(runs_dir(output_dir), "summary.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def load_daily(output_dir=None):
    p = os.path.join(runs_dir(output_dir), "daily.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def agg_by(df, xcol, cols):
    """Group by xcol, return (x, mean_df, sem_df) with SEM across seeds."""
    g = df.groupby(xcol)
    m = g[cols].mean()
    n = g[cols].count().clip(lower=1)
    s = g[cols].std(ddof=1).div(np.sqrt(n))
    return m.index.values, m, s


# --------------------------------------------------------------------------- #
#  field-level order parameters (computed from a single B (and optional M) array)
# --------------------------------------------------------------------------- #
def gini(a):
    x = np.sort(np.asarray(a, float).ravel())
    n = x.size
    if x.sum() <= 0:
        return 0.0
    cum = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def spatial_entropy(field):
    f = np.asarray(field, float).ravel()
    s = f.sum()
    if s <= 0:
        return 0.0
    p = f[f > 0] / s
    return float(-np.sum(p * np.log(p)))


def field_order_params(B, M=None, chi=None):
    """Structural order parameters from a stationary B field (and optional M).

    Returns a dict. Designed so the analysis script can compute the same quantities
    either from a saved snapshot or from a time-averaged stationary field.
    """
    B = np.asarray(B, float)
    Bm = B.mean()
    flat = B.ravel()
    out = dict(
        B_mean=float(Bm),
        H=float(B.std() / Bm) if Bm > 0 else 0.0,
        f_hot_2=float((B >= 2 * Bm).mean()),
        f_hot_3=float((B >= 3 * Bm).mean()),
        B_q90_over_mean=float(np.percentile(flat, 90) / Bm) if Bm > 0 else 0.0,
        B_q95_over_mean=float(np.percentile(flat, 95) / Bm) if Bm > 0 else 0.0,
        B_q99_over_mean=float(np.percentile(flat, 99) / Bm) if Bm > 0 else 0.0,
        Gini_B=gini(B),
        crime_entropy_B=spatial_entropy(B),
    )
    if M is not None:
        M = np.asarray(M, float)
        fM = M.ravel()
        thr = np.percentile(flat, 90)
        hot = B >= thr
        out.update(
            MB_corr=float(np.corrcoef(flat, fM)[0, 1]) if fM.std() > 0 else 0.0,
            MB_corr_sq=float(np.corrcoef(flat, fM)[0, 1] ** 2) if fM.std() > 0 else 0.0,
            M_mass_on_hot10=float(M[hot].sum() / fM.sum()) if fM.sum() > 0 else 0.0,
            Gini_M=gini(M),
        )
        if chi is not None:
            deter = np.exp(-chi * M)
            out.update(
                deterrence_mean=float(deter.mean()),
                deterrence_hot=float(deter[hot].mean()),
            )
    return out


# --------------------------------------------------------------------------- #
#  small CLI helpers
# --------------------------------------------------------------------------- #
def has_flag(name):
    return name in sys.argv


def get_opt(name, default=None):
    """--name value  ->  value (string). Returns default if absent."""
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    for a in sys.argv:
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default
