"""plot_stationary_snapshots.py — multi-panel stationary field snapshots vs g.

Reads <output-dir>/runs/snapshots/snap_g*_seed0.npz (saved by run_transition_scan.py)
and builds a paper-style panel:
    rows  = B, M, A_tilde = A0 + B exp(-chi M), deterrence exp(-chi M)
    cols  = selected g regimes (base/pre/transition/post)
Color scales are FIXED across columns within each row so regimes are comparable.

Snapshots are taken at the configured snapshot day(s) (default 'final', i.e. after
burn-in), NOT during the transient. If a field movie was saved (output.movie_every),
you may instead average over a stationary window with --avg-window LO HI.

Generates NO simulations. Usage:
    python3 scripts/plot_stationary_snapshots.py [--output-dir DIR] [--g 0,0.5,1,3]
"""
import os
import sys
import glob
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
C.apply_style()

ROW_SPEC = [("B", r"$B$  (attractiveness)", C.CMAP_CRIME),
            ("M", r"$M$  (police field)", C.CMAP_POLICE),
            ("A_tilde", r"$\tilde A = A_0 + B\,e^{-\chi M}$", C.CMAP_CRIME),
            ("deter", r"deterrence $e^{-\chi M}$", C.CMAP_DETER)]


def regime_label(g):
    if g == 0:
        return "base  (g=0)"
    if g < 0.6:
        return "pre  (g=%g)" % g
    if g <= 1.2:
        return "transition  (g=%g)" % g
    return "post  (g=%g)" % g


def find_snapshots(output_dir):
    snap = os.path.join(C.runs_dir(output_dir), "snapshots")
    out = {}
    for fn in sorted(glob.glob(os.path.join(snap, "snap_g*_seed0.npz"))):
        m = re.search(r"snap_g([-\d.]+)_seed0\.npz", os.path.basename(fn))
        if m:
            out[float(m.group(1))] = fn
    return out


def latest_day(npz):
    days = set()
    for k in npz.files:
        m = re.match(r"d(\d+)_", k)
        if m:
            days.add(int(m.group(1)))
    return max(days) if days else None


def main():
    output_dir = C.get_opt("--output-dir")
    want = C.get_opt("--g")
    snaps = find_snapshots(output_dir)
    if not snaps:
        print("no snapshots found under", C.runs_dir(output_dir),
              "- run the scan with output.save_fields: true first.")
        return
    gs = sorted(snaps)
    if want:
        wset = [float(x) for x in want.split(",")]
        gs = [g for g in gs if any(abs(g - w) < 1e-6 for w in wset)]
    # keep at most ~5 columns spanning the regimes
    if len(gs) > 5:
        idx = np.linspace(0, len(gs) - 1, 5).round().astype(int)
        gs = [gs[i] for i in sorted(set(idx))]

    loaded = {}
    for g in gs:
        z = np.load(snaps[g])
        day = latest_day(z)
        loaded[g] = (z, day)

    nrow, ncol = len(ROW_SPEC), len(gs)
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.0 * ncol, 3.0 * nrow), squeeze=False)
    for ri, (fk, rlab, cmap) in enumerate(ROW_SPEC):
        arrs = []
        for g in gs:
            z, day = loaded[g]
            key = "d%d_%s" % (day, fk)
            arrs.append(z[key].astype(float) if key in z.files else None)
        present = [a for a in arrs if a is not None]
        if not present:
            continue
        vmin = 0.0
        vmax = float(np.percentile(np.concatenate([a.ravel() for a in present]), 99.5))
        if fk == "deter":
            vmin, vmax = 0.0, 1.0
        for ci, g in enumerate(gs):
            ax = axes[ri][ci]
            a = arrs[ci]
            if a is None:
                ax.text(0.5, 0.5, "n/a", ha="center", va="center"); ax.axis("off"); continue
            im = ax.imshow(a, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
            if ri == 0:
                ax.set_title(regime_label(g), fontsize=11)
            if ci == 0:
                ax.set_ylabel(rlab, fontsize=11)
            ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=[axes[ri][c] for c in range(ncol)], fraction=0.012, pad=0.01)
    day0 = loaded[gs[0]][1]
    fig.suptitle("Stationary field snapshots (return-home model, $\\delta=1/15$, day %s)"
                 % day0, y=0.995, fontsize=13)
    C.save_fig(fig, "stationary_snapshots_vs_g", output_dir)


if __name__ == "__main__":
    main()
    print("PLOT_STATIONARY_SNAPSHOTS DONE")
