"""run_transition_scan.py — resumable data generator for the RETURN-HOME transition scan.

Reads config/scan_config_template.yaml (or --config FILE, optionally --run-set NAME),
runs the return-home engine over the (g, seed) grid, and writes append-only raw
outputs under the output root (default: out_return_home/). NEVER touches the legacy
top-level runs/ or figures/.

This script GENERATES DATA (it runs simulations). The default mode is SAFE:
with no flags it RESUMES — it runs only the (g, seed) points not already present.
Use --dry-run first to see exactly what would run.

Usage
-----
  python3 scripts/run_transition_scan.py --dry-run            # show plan, run nothing
  python3 scripts/run_transition_scan.py                      # resume: run missing points
  python3 scripts/run_transition_scan.py --run-set pilot      # use a named run-set
  python3 scripts/run_transition_scan.py --force              # rerun even existing points
  python3 scripts/run_transition_scan.py --figures-only       # rebuild all figures, no sims
  python3 scripts/run_transition_scan.py --output-dir out_run_2026xxxx   # fresh output root
  BUDGET=60 python3 scripts/run_transition_scan.py            # checkpoint+exit after ~60 s

Resume key = (L, seed, g, delta, M_tot, eta_M, T_max), all rounded. delta is part of
the key, so changing delta makes new points (never collides with old ones).

Outputs (under <output-dir>/runs/):
  summary.csv   one row per completed run (stationary-tail averages + config)
  daily.csv     per-day metrics for every run (time-series source)
  manifest.csv  provenance: params + engine MD5 + timestamp + status, one row/run
  snapshots/    *.npz field snapshots (only for g in output.snapshot_g)
  events/       *.csv.gz per-event logs (only if output.save_event_logs and g in event_log_g)
  movies/       *.npz field movie stacks (only if output.movie_every set, g in movie_g)
  config_used.yaml   a copy of the resolved config for traceability
"""
import os
import sys
import time
import json
import hashlib
import shutil
import datetime
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import common as C                                  # noqa: E402
from engine_return_home import run_return_home_sim, summarize  # noqa: E402

START = time.time()
BUDGET = float(os.environ.get("BUDGET", "1e18"))
CODE_HASH = hashlib.md5(
    open(os.path.join(ROOT, "engine_return_home.py"), "rb").read()).hexdigest()[:10]


def resolve_snapshot_days(spec, T_max):
    days = []
    for s in (spec or []):
        if isinstance(s, str) and s.lower() == "final":
            days.append(int(T_max))
        else:
            days.append(int(s))
    return sorted(set(days))


def key(L, seed, g, delta, M_tot, eta_M, T_max):
    return (int(L), int(seed), round(float(g), 6), round(float(delta), 6),
            round(float(M_tot), 6), round(float(eta_M), 6), int(T_max))


def load_done(summary_path):
    if os.path.exists(summary_path) and os.path.getsize(summary_path) > 0:
        try:
            dd = pd.read_csv(summary_path)
        except Exception:
            return set()
        out = set()
        for r in dd.itertuples():
            out.add(key(r.L, r.seed, r.g, r.delta, r.M_tot, r.eta_M, r.T_max))
        return out
    return set()


def append_csv(path, df):
    empty = (not os.path.exists(path)) or os.path.getsize(path) == 0
    df.to_csv(path, mode="a", header=empty, index=False)


def build_plan(cfg):
    L = cfg["grid"]["L"]
    M_tot = cfg["police"]["M_tot"]
    eta_M = cfg["police"]["eta_M"]
    T_max = cfg["grid"]["T_max"]
    delta = cfg["removal"]["delta"]
    pts = []
    snap_g = set(round(float(x), 6) for x in cfg["output"].get("snapshot_g", []))
    ev_g = set(round(float(x), 6) for x in cfg["output"].get("event_log_g", []))
    mov_g = set(round(float(x), 6) for x in cfg["output"].get("movie_g", []))
    for g in cfg["grid"]["g_values"]:
        gr = round(float(g), 6)
        for seed in cfg["grid"]["seeds"]:
            pts.append(dict(
                L=L, M_tot=M_tot, eta_M=eta_M, T_max=T_max, delta=delta,
                g=float(g), seed=int(seed),
                chi=C.chi_from_g(g, L, M_tot),
                want_snap=(gr in snap_g),
                want_event=(gr in ev_g) and bool(cfg["output"].get("save_event_logs", False)),
                want_movie=(gr in mov_g) and (cfg["output"].get("movie_every") is not None),
            ))
    return pts


def do_run(cfg, p, paths):
    m = cfg["model"]; pol = cfg["police"]
    snap_days = resolve_snapshot_days(cfg["output"].get("snapshot_days"), p["T_max"]) \
        if (p["want_snap"] and cfg["output"].get("save_fields", True)) else None
    movie_every = cfg["output"].get("movie_every") if p["want_movie"] else None
    t0 = time.time()
    df, snaps, fin, events = run_return_home_sim(
        L=p["L"], dt=m["dt"], T_max=p["T_max"],
        A0=m["A0"], omega=m["omega"], eta=m["eta"], theta=m["theta"], Gamma=m["Gamma"],
        chi=p["chi"], M_tot=p["M_tot"], eta_M=pol["eta_M"], omega_M=pol["omega_M"],
        delta=p["delta"], seed=p["seed"],
        snapshot_days=snap_days, movie_every=movie_every,
        event_log=p["want_event"],
        event_order=cfg["removal"].get("event_order", "sequential"))

    # stationary-tail summary (+ provenance)
    s = summarize(df)
    s.update(L=p["L"], seed=p["seed"], chi=p["chi"], delta=p["delta"], g=p["g"],
             M_tot=p["M_tot"], eta_M=pol["eta_M"], omega_M=pol["omega_M"], T_max=p["T_max"],
             M_bar=C.m_bar(p["L"], p["M_tot"]), M_final_sum=float(fin["M"].sum()),
             code_hash=CODE_HASH, wall_s=round(time.time() - t0, 3))
    df["g"] = p["g"]; df["seed"] = p["seed"]
    append_csv(paths["summary"], pd.DataFrame([s]))
    if cfg["output"].get("save_daily", True):
        append_csv(paths["daily"], df)

    if snap_days and snaps:
        fn = os.path.join(paths["snap"], "snap_g%g_seed%d.npz" % (p["g"], p["seed"]))
        np.savez_compressed(fn, **{"d%d_%s" % (dd, kk): vv
                                   for dd, sd in snaps.items()
                                   for kk, vv in sd.items()
                                   if isinstance(vv, np.ndarray)})
    if p["want_event"] and len(events):
        fn = os.path.join(paths["events"], "events_g%g_seed%d.csv.gz" % (p["g"], p["seed"]))
        events.to_csv(fn, index=False, compression="gzip")
    if movie_every and "movie" in fin and fin["movie"].size:
        fn = os.path.join(paths["movies"], "movie_g%g_seed%d.npz" % (p["g"], p["seed"]))
        np.savez_compressed(fn, frames=fin["movie"], days=fin["movie_days"],
                            fields=fin["movie_fields"], g=p["g"], chi=p["chi"], seed=p["seed"])

    append_csv(paths["manifest"], pd.DataFrame([dict(
        timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
        code_hash=CODE_HASH, L=p["L"], seed=p["seed"], g=p["g"], chi=p["chi"],
        delta=p["delta"], M_tot=p["M_tot"], eta_M=pol["eta_M"], omega_M=pol["omega_M"],
        T_max=p["T_max"], snap=bool(snap_days), event_log=p["want_event"],
        status="done", wall_s=round(time.time() - t0, 3))]))
    print("done g=%5.2f seed=%d  N=%.0f crimes/d=%.2f home/d=%.2f H=%.3f bal=%d wall=%.1fs"
          % (p["g"], p["seed"], s.get("n_criminals", 0), s.get("crimes_that_day", 0),
             s.get("home_exits_that_day", 0), s.get("H", float("nan")),
             int(round(s.get("balance_error", 0))), time.time() - t0), flush=True)


def rebuild_figures(output_dir):
    """--figures-only: invoke each plotting/analysis script in turn."""
    import subprocess
    scripts = ["plot_stationary_snapshots.py", "plot_time_series.py",
               "plot_order_parameters.py", "analyze_waiting_times.py",
               "make_gifs_from_snapshots.py"]
    od = ["--output-dir", output_dir] if output_dir else []
    for sc in scripts:
        path = os.path.join(HERE, sc)
        if os.path.exists(path):
            print("--- %s ---" % sc, flush=True)
            subprocess.run([sys.executable, path, *od])


if __name__ == "__main__":
    cfg = C.load_config(C.get_opt("--config"), C.get_opt("--run-set"))
    output_dir = C.get_opt("--output-dir") or C.DEFAULT_OUT
    runs = C.runs_dir(output_dir)
    paths = dict(
        runs=runs, summary=os.path.join(runs, "summary.csv"),
        daily=os.path.join(runs, "daily.csv"), manifest=os.path.join(runs, "manifest.csv"),
        snap=os.path.join(runs, "snapshots"), events=os.path.join(runs, "events"),
        movies=os.path.join(runs, "movies"))

    if C.has_flag("--figures-only"):
        rebuild_figures(output_dir)            # reads only; creates no run dirs
        sys.exit(0)

    plan = build_plan(cfg)
    done = set() if C.has_flag("--force") else load_done(paths["summary"])
    todo = [p for p in plan
            if C.has_flag("--force")
            or key(p["L"], p["seed"], p["g"], p["delta"], p["M_tot"], p["eta_M"], p["T_max"])
            not in done]

    rs = cfg.get("_active_run_set", "config grid")
    if C.has_flag("--dry-run"):              # touch nothing on disk
        print("[dry-run] run-set=%s  output=%s  engine_hash=%s" % (rs, output_dir, CODE_HASH))
        print("[dry-run] L=%d T=%d delta=%.5f M_tot=%g  |  %d of %d point(s) WOULD run:"
              % (cfg["grid"]["L"], cfg["grid"]["T_max"], cfg["removal"]["delta"],
                 cfg["police"]["M_tot"], len(todo), len(plan)))
        for p in todo:
            tags = "".join([" +snap" if p["want_snap"] else "",
                            " +events" if p["want_event"] else "",
                            " +movie" if p["want_movie"] else ""])
            print("   g=%5.2f chi=%8.3f seed=%d%s" % (p["g"], p["chi"], p["seed"], tags))
        print("[dry-run] nothing was run.")
        sys.exit(0)

    # real run: NOW it is safe to create output dirs and snapshot the resolved config
    for d in (paths["snap"], paths["events"], paths["movies"]):
        C.ensure_dir(d)
    try:
        import yaml
        with open(os.path.join(output_dir, "config_used.yaml"), "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
    except Exception:
        pass

    print("resuming: %d of %d point(s) to do (run-set=%s, BUDGET=%ss, hash=%s)"
          % (len(todo), len(plan), rs, BUDGET, CODE_HASH), flush=True)
    for i, p in enumerate(todo):
        if time.time() - START > BUDGET:
            print("BUDGET_EXIT after %d run(s) (clean; re-run to resume)" % i, flush=True)
            sys.exit(0)
        do_run(cfg, p, paths)
    print("ALL DONE", flush=True)
