"""run_mechanism.py - resumable driver for the criminal-removal mechanism scan.

Competing-hazards engine (engine_removal.py). Writes ONLY into this folder's
runs/ subdir; never touches the frozen dissuasion-only folder.

Usage
-----
  python3 run_mechanism.py            # resume: run missing points
  python3 run_mechanism.py --dry-run  # print what WOULD run, do nothing
  python3 run_mechanism.py --figures-only   # rebuild figures, no sims
  python3 run_mechanism.py --force    # rerun even points already present
  BUDGET=40 python3 run_mechanism.py  # exit cleanly after ~40 s of whole runs

Resume key = (mech, L, seed, g, h, delta, M_tot, eta_M, T_max), all rounded.
"""
import os, sys, time, json, hashlib, datetime
import numpy as np
import pandas as pd
from engine_removal import run_removal_sim, summarize

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
SNAP = os.path.join(RUNS, "snapshots")
os.makedirs(SNAP, exist_ok=True)
SUMMARY = os.path.join(RUNS, "summary.csv")
DAILY = os.path.join(RUNS, "daily.csv")
MANIFEST = os.path.join(RUNS, "manifest.csv")

START = time.time()
BUDGET = float(os.environ.get("BUDGET", "1e9"))
CODE_HASH = hashlib.md5(open(os.path.join(HERE, "engine_removal.py"), "rb").read()
                        ).hexdigest()[:10]

# ---------------- config: L=64, T=120, M_bar matched to frozen L=128 runs -----
L = 64
M_BAR = 500.0 / 128 ** 2
M_TOT = M_BAR * L ** 2          # = 125.0
T_MAX = 120
SEEDS = [0, 1]

# isolated removal sweeps (one channel at a time) at fixed chi (=g) slices
G_SLICES = [0.0, 1.0, 3.0]
H_VALS = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.0]
D_VALS = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2]

# FINAL POSTER MODEL: dissuasion + fixed home-exit delta (Jones et al. style).
# Sweep g across the three regimes at several fixed delta to (i) pick delta and
# (ii) show the three regimes survive while N stays bounded. delta candidates:
# 0 (none), A0=1/30, omega=1/15, 0.1.
DELTA_FIX = [0.0, 1 / 30, 1 / 15, 0.1]
G_REGIME = [0.0, 0.3, 0.7, 1.0, 1.5, 2.0, 3.0]


def grid():
    """Yield de-duplicated (mech, g, h, delta, snap) points."""
    raw = []
    # original demonstration points (kept so resume marks them done)
    raw.append(("base", 0.0, 0.0, 0.0, True))
    for g in [0.5, 1.0, 1.5, 3.0]:
        raw.append(("dissuasion", g, 0.0, 0.0, g == 3.0))
    for h in [0.5, 1.0, 1.5, 3.0]:
        raw.append(("arrest", 0.0, h, 0.0, h == 3.0))
    for gh in [0.5, 1.0, 1.5, 3.0]:
        raw.append(("both", gh, gh, 0.0, gh == 3.0))
    for d in [0.5, 1.0]:
        raw.append(("home", 1.0, 0.0, d, False))
    raw.append(("all", 1.0, 1.0, 0.5, False))
    # isolated removal sweeps at fixed chi slices
    for g in G_SLICES:
        for h in H_VALS:
            raw.append(("arrest", g, h, 0.0, False))
        for d in D_VALS:
            raw.append(("home", g, 0.0, d, False))
    # dissuasion + fixed home-exit (the poster model): vary g at each delta
    for dfix in DELTA_FIX:
        for g in G_REGIME:
            snap = (abs(dfix - 1 / 15) < 1e-9) and g in (0.0, 1.0, 3.0)
            raw.append(("dishome", g, 0.0, dfix, snap))
    seen = {}
    for mech, g, h, d, snap in raw:
        k = (mech, round(g, 6), round(h, 6), round(d, 6))
        if k not in seen:
            seen[k] = (mech, g, h, d, snap)
        elif snap:
            seen[k] = (mech, g, h, d, True)
    return list(seen.values())


def key(mech, seed, g, h, d):
    return (mech, L, seed, round(g, 6), round(h, 6), round(d, 6),
            round(M_TOT, 6), 0.1, T_MAX)


def load_done():
    if os.path.exists(SUMMARY) and os.path.getsize(SUMMARY) > 0:
        try:
            dd = pd.read_csv(SUMMARY)
        except Exception:
            return set()
        return set((r.mech, int(r.L), int(r.seed), round(r.g, 6), round(r.h, 6),
                    round(r.delta, 6), round(r.M_tot, 6), round(r.eta_M, 6),
                    int(r.T_max)) for r in dd.itertuples())
    return set()


def append_csv(path, df):
    empty = (not os.path.exists(path)) or os.path.getsize(path) == 0
    df.to_csv(path, mode="a", header=empty, index=False)


def planned():
    done = load_done()
    todo = []
    for mech, g, h, d, snap in grid():
        for seed in SEEDS:
            k = key(mech, seed, g, h, d)
            if "--force" in sys.argv or k not in done:
                todo.append((mech, g, h, d, snap, seed))
    return todo


def do_run(mech, g, h, d, snap, seed):
    chi = g / M_BAR
    kappa = h / M_BAR
    t0 = time.time()
    snap_days = [120] if (snap and seed == 0) else None
    df, snaps, fin = run_removal_sim(L=L, T_max=T_MAX, chi=chi, M_tot=M_TOT,
                                     kappa=kappa, delta=d, seed=seed,
                                     snapshot_days=snap_days)
    df["mech"] = mech
    s = summarize(df)
    s.update(mech=mech, L=L, seed=seed, chi=chi, kappa=kappa, delta=d,
             g=g, h=h, M_tot=M_TOT, eta_M=0.1, omega_M=1 / 15, T_max=T_MAX,
             M_final_sum=float(fin["M"].sum()), wall_s=time.time() - t0)
    append_csv(SUMMARY, pd.DataFrame([s]))
    append_csv(DAILY, df)
    if snap_days and snaps:
        fn = os.path.join(SNAP, "snap_%s_g%g_h%g_d%g_seed%d.npz" % (mech, g, h, d, seed))
        np.savez_compressed(fn, **{"d%d_%s" % (dd, kk): vv
                                   for dd, sd in snaps.items()
                                   for kk, vv in sd.items()
                                   if isinstance(vv, np.ndarray)})
    append_csv(MANIFEST, pd.DataFrame([dict(
        timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        code_hash=CODE_HASH, mech=mech, L=L, seed=seed, g=g, h=h, delta=d,
        chi=chi, kappa=kappa, M_tot=M_TOT, eta_M=0.1, omega_M=1 / 15, T_max=T_MAX,
        status="done", wall_s=round(time.time() - t0, 2), out="runs/summary.csv")]))
    print("done %-9s g=%4.1f h=%4.2f d=%5.3f seed=%d H=%.3f ncrim=%.0f "
          "crimes/d=%.2f home/d=%.2f wall=%.1fs" % (
              mech, g, h, d, seed, s.get("H", float("nan")),
              s.get("n_criminals", 0), s.get("crimes_that_day", 0),
              s.get("home_exits_that_day", 0), time.time() - t0), flush=True)


if __name__ == "__main__":
    if "--figures-only" in sys.argv:
        import analyze_mechanism  # noqa: F401
        sys.exit(0)
    todo = planned()
    if "--dry-run" in sys.argv:
        print("[dry-run] code_hash=%s  %d run(s) WOULD execute:" % (CODE_HASH, len(todo)))
        for mech, g, h, d, snap, seed in todo:
            print("  %-9s g=%4.1f h=%4.2f delta=%5.3f seed=%d%s" % (
                mech, g, h, d, seed, "  [+snap]" if (snap and seed == 0) else ""))
        print("[dry-run] estimated ~%.0fs compute. Nothing was run." % (2.0 * len(todo)))
        sys.exit(0)
    print("resuming: %d run(s) to do (BUDGET=%ss, hash=%s)" % (len(todo), BUDGET, CODE_HASH),
          flush=True)
    for i, (mech, g, h, d, snap, seed) in enumerate(todo):
        if time.time() - START > BUDGET:
            print("BUDGET_EXIT after %d run(s) (clean; re-run to resume)" % i, flush=True)
            sys.exit(0)
        do_run(mech, g, h, d, snap, seed)
    print("ALL DONE", flush=True)
