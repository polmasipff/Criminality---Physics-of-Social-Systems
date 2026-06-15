"""
run_scans.py — Driver for the transition-scan pipeline. Checkpoints to CSV after
every completed run and skips runs already present (resume-safe). Run in background:
    nohup python3 run_scans.py PHASE > log_PHASE.txt 2>&1 &
PHASE in {A,B,C,D,E,F,G,all}.
"""
import sys, os, time, itertools
import numpy as np
import pandas as pd
from engine import run_police_sim, summarize

START = time.time()
BUDGET = float(os.environ.get("BUDGET", "1e9"))  # seconds of wall-time before clean exit


class TimeUp(Exception):
    pass


def check_budget():
    if time.time() - START > BUDGET:
        raise TimeUp()

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SNAP = os.path.join(HERE, "snapshots")
os.makedirs(DATA, exist_ok=True); os.makedirs(SNAP, exist_ok=True)
MASTER = os.path.join(DATA, "all_runs_summary.csv")
DAILY = os.path.join(DATA, "all_runs_daily.csv")

KEY = ["phase", "L", "chi", "seed", "M_tot", "kappa", "eta_M", "branch", "T_max"]


def load_done():
    if os.path.exists(MASTER) and os.path.getsize(MASTER) > 0:
        try:
            d = pd.read_csv(MASTER)
        except Exception:
            return set()
        return set(tuple(r) for r in d[KEY].round(6).itertuples(index=False, name=None))
    return set()


def append_csv(path, df):
    empty = (not os.path.exists(path)) or os.path.getsize(path) == 0
    df.to_csv(path, mode="a", header=empty, index=False)


def do_run(phase, L, chi, seed, M_tot, T_max, kappa=0.0, eta_M=0.1,
           omega_M=1/15, branch="cold", init_state=None, snap_days=None,
           save_snap=False, done=None):
    k = (phase, L, round(chi, 6), seed, round(M_tot, 6), round(kappa, 6),
         round(eta_M, 6), branch, T_max)
    if done is not None and k in done:
        return None
    check_budget()
    t0 = time.time()
    df, snaps, final = run_police_sim(L=L, T_max=T_max, chi=chi, M_tot=M_tot,
                                      kappa=kappa, eta_M=eta_M, omega_M=omega_M,
                                      seed=seed, snapshot_days=snap_days,
                                      init_state=init_state)
    df["phase"] = phase; df["branch"] = branch; df["T_max"] = T_max
    s = summarize(df)
    s.update(phase=phase, L=L, chi=chi, seed=seed, M_tot=M_tot, kappa=kappa,
             eta_M=eta_M, omega_M=omega_M, branch=branch, T_max=T_max,
             g=chi * M_tot / L**2, h=kappa * M_tot / L**2,
             M_final_sum=float(final["M"].sum()), wall_s=time.time() - t0)
    append_csv(MASTER, pd.DataFrame([s]))
    append_csv(DAILY, df)
    if save_snap and snaps:
        fn = os.path.join(SNAP, f"snap_{phase}_L{L}_chi{chi:g}_seed{seed}_"
                                f"Mtot{M_tot:g}_kap{kappa:g}.npz")
        np.savez_compressed(fn, **{f"d{d}_{k2}": v
                                   for d, sd in snaps.items()
                                   for k2, v in sd.items()
                                   if isinstance(v, np.ndarray)})
    print(f"done {k} H={s.get('H', float('nan')):.3f} "
          f"ncrim={s.get('n_criminals', float('nan')):.0f} "
          f"wall={time.time()-t0:.1f}s", flush=True)
    if done is not None:
        done.add(k)
    return final


# ---------------------------------------------------------------- phases
def phase_A(done):
    L, M_tot = 64, 500.0
    gs = [0, 0.3, 0.7, 1.0, 1.5, 3.0]
    for g in gs:
        chi = g * L**2 / M_tot
        do_run("A", L, chi, 0, M_tot, 120, snap_days=[120],
               save_snap=True, done=done)


def phase_B(done):
    L, M_tot = 128, 500.0
    chis = [0, 3, 10, 16, 20, 24, 28, 32, 36, 42, 50, 60, 75, 100, 150, 300]
    for chi in chis:
        for seed in [0, 1]:
            do_run("B", L, chi, seed, M_tot, 365, done=done)


def phase_C(done):
    L, M_tot = 128, 500.0
    chis = [12, 22, 26, 40, 55, 90]
    for chi in chis:
        for seed in [0, 1]:
            do_run("C", L, chi, seed, M_tot, 365, done=done)


def phase_D(done):
    # field snapshots for representative regimes at L=128, seed 0
    L, M_tot = 128, 500.0
    reps = [0, 10, 22, 36, 60, 100, 300]
    for chi in reps:
        do_run("D", L, chi, 0, M_tot, 365, snap_days=[50, 185, 365],
               save_snap=True, done=done)


def _state_path(branch, idx):
    return os.path.join(SNAP, f"state_E_{branch}_{idx}.npz")


def _save_state(branch, idx, fin):
    np.savez_compressed(_state_path(branch, idx),
                        B=fin["B"], M=fin["M"], x=fin["x"], y=fin["y"])


def _load_state(branch, idx):
    p = _state_path(branch, idx)
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return dict(B=z["B"], M=z["M"], x=z["x"], y=z["y"])


def phase_E(done):
    # hysteresis: ramp chi up (warm-started from previous chi), then ramp down.
    # States persisted to disk so the warm-start chain survives resume.
    L, M_tot = 128, 500.0
    chis = [0, 10, 20, 30, 40, 60, 100, 300]
    # UP branch
    for i, chi in enumerate(chis):
        prev = _load_state("up", i - 1) if i > 0 else None
        fin = do_run("E", L, chi, 0, M_tot, 365, branch="up",
                     init_state=prev, done=done)
        if fin is not None:
            _save_state("up", i, fin)
    # DOWN branch: reverse order, warm-start from previous (higher) chi
    rchis = list(reversed(chis))
    for i, chi in enumerate(rchis):
        prev = _load_state("down", i - 1) if i > 0 else None
        fin = do_run("E", L, chi, 0, M_tot, 365, branch="down",
                     init_state=prev, done=done)
        if fin is not None:
            _save_state("down", i, fin)


def phase_F(done):
    # finite-size: match M_bar = 500/128^2, vary g
    Mbar = 500.0 / 128**2
    gs = [0, 0.3, 0.6, 1.0, 1.5, 2.0, 3.0]
    for L in [64, 128]:
        M_tot = Mbar * L**2
        for g in gs:
            chi = g / Mbar
            for seed in [0, 1]:
                do_run("F", L, chi, seed, M_tot, 365, done=done)


def phase_G(done):
    # arrest channel comparison at L=128, seed 0,1,2; T=365
    L, M_tot = 128, 500.0
    Mbar = M_tot / L**2
    configs = [
        ("base", 0.0, 0.0),
        ("dissuasion", 30.0, 0.0),      # g~1.46
        ("arrest", 0.0, 30.0),          # h~1.46
        ("both", 30.0, 30.0),
    ]
    for name, chi, kappa in configs:
        for seed in [0, 1]:
            do_run("G", L, chi, seed, M_tot, 365, kappa=kappa, done=done)


if __name__ == "__main__":
    ph = sys.argv[1] if len(sys.argv) > 1 else "all"
    done = load_done()
    fns = dict(A=phase_A, B=phase_B, C=phase_C, D=phase_D,
               E=phase_E, F=phase_F, G=phase_G)
    order = ["A", "B", "C", "D", "F", "E", "G"]
    todo = order if ph == "all" else [ph]
    try:
        for p in todo:
            print(f"===== PHASE {p} =====", flush=True)
            fns[p](done)
        print("ALL DONE", flush=True)
    except TimeUp:
        print("BUDGET_EXIT (clean, resume by re-running)", flush=True)
