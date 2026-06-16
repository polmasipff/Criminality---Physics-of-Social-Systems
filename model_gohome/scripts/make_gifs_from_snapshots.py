"""make_gifs_from_snapshots.py — animations of the fields, from SAVED movie stacks.

Reads <output-dir>/runs/movies/movie_g*_seed0.npz (written by run_transition_scan.py
when output.movie_every is set) and renders GIFs WITHOUT re-running any simulation.
Each movie npz holds frames of shape (n_frames, 4, L, L) for fields [B, M, A_tilde, deter].

Produces, into <output-dir>/figures/gifs/:
    <field>_g<g>.gif            one GIF per field per g
    combined_g<g>.gif           a B|M|A_tilde multi-panel GIF per g

Color scales are FIXED per field across ALL g (computed once over every movie) so the
animations are directly comparable between regimes.

If no movie stacks exist, prints guidance (you must set output.movie_every in the
config and re-run the scan, or pass --movie-every to a future run). Generates NO
simulations. Usage:
    python3 scripts/make_gifs_from_snapshots.py [--output-dir DIR] [--fps 8]
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

try:
    import imageio.v2 as imageio
except Exception:
    import imageio

FIELDS = ["B", "M", "A_tilde", "deter"]
CMAP = {"B": "hot", "M": "viridis", "A_tilde": "hot", "deter": "cividis"}
FLABEL = {"B": r"$B$", "M": r"$M$", "A_tilde": r"$\tilde A$", "deter": r"$e^{-\chi M}$"}


def find_movies(output_dir):
    md = os.path.join(C.runs_dir(output_dir), "movies")
    out = {}
    for fn in sorted(glob.glob(os.path.join(md, "movie_g*_seed0.npz"))):
        m = re.search(r"movie_g([-\d.]+)_seed0\.npz", os.path.basename(fn))
        if m:
            out[float(m.group(1))] = fn
    return out


def fig_to_rgb(fig):
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    rgba = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4)
    return rgba[..., :3].copy()


def global_scales(movies):
    """Per-field (vmin, vmax) over all g, for comparable color scales."""
    sc = {}
    for fi, f in enumerate(FIELDS):
        vals = []
        for fn in movies.values():
            z = np.load(fn)
            fr = z["frames"]
            if fr.size:
                vals.append(fr[:, fi].ravel())
        if not vals:
            sc[f] = (0.0, 1.0)
            continue
        cat = np.concatenate(vals)
        sc[f] = (0.0, 1.0) if f == "deter" else (0.0, float(np.percentile(cat, 99.5)))
    return sc


def main():
    output_dir = C.get_opt("--output-dir")
    fps = float(C.get_opt("--fps", "8"))
    movies = find_movies(output_dir)
    if not movies:
        print("no movie stacks under", os.path.join(C.runs_dir(output_dir), "movies"))
        print("set output.movie_every (and movie_g) in the config, then re-run the scan.")
        return
    gifdir = C.ensure_dir(os.path.join(C.figures_dir(output_dir), "gifs"))
    sc = global_scales(movies)

    for g, fn in movies.items():
        z = np.load(fn)
        frames = z["frames"]; days = z["days"]
        if frames.size == 0:
            continue
        chi = float(z["chi"]) if "chi" in z.files else float("nan")

        # one GIF per field
        for fi, f in enumerate(FIELDS):
            vmin, vmax = sc[f]
            imgs = []
            for t in range(frames.shape[0]):
                fig, ax = plt.subplots(figsize=(3.6, 3.6))
                ax.imshow(frames[t, fi], origin="lower", cmap=CMAP[f], vmin=vmin, vmax=vmax)
                ax.set_title("%s  g=%g  day %d" % (FLABEL[f], g, days[t]), fontsize=11)
                ax.set_xticks([]); ax.set_yticks([])
                fig.tight_layout()
                imgs.append(fig_to_rgb(fig)); plt.close(fig)
            out = os.path.join(gifdir, "%s_g%g.gif" % (f, g))
            imageio.mimsave(out, imgs, fps=fps, loop=0)
            print("saved", os.path.relpath(out, output_dir or C.DEFAULT_OUT))

        # combined B | M | A_tilde panel GIF
        imgs = []
        trio = ["B", "M", "A_tilde"]
        for t in range(frames.shape[0]):
            fig, axes = plt.subplots(1, 3, figsize=(10, 3.6))
            for ax, f in zip(axes, trio):
                fi = FIELDS.index(f)
                vmin, vmax = sc[f]
                ax.imshow(frames[t, fi], origin="lower", cmap=CMAP[f], vmin=vmin, vmax=vmax)
                ax.set_title(FLABEL[f], fontsize=11); ax.set_xticks([]); ax.set_yticks([])
            fig.suptitle("g=%g  (chi=%.1f)  day %d" % (g, chi, days[t]), fontsize=11)
            fig.tight_layout()
            imgs.append(fig_to_rgb(fig)); plt.close(fig)
        out = os.path.join(gifdir, "combined_g%g.gif" % g)
        imageio.mimsave(out, imgs, fps=fps, loop=0)
        print("saved", os.path.relpath(out, output_dir or C.DEFAULT_OUT))


if __name__ == "__main__":
    main()
    print("MAKE_GIFS DONE")
