# transition_scan — how to rerun and resume

Reproducible police-extended Short et al. (2008) crime-hotspot transition scan.

## Layout
- `engine.py`     — the model (`run_police_sim`) + per-day metrics + `summarize`.
- `run_scans.py`  — phase driver (A sanity, B coarse, C focused, D snapshots,
                    F finite-size, E hysteresis, G arrest). Resume-safe.
- `analyze.py`    — reads `data/*.csv` + `snapshots/*.npz`, writes `figures/` and
                    `data/transition_estimates.csv`.

## Run from scratch
```bash
cd transition_scan_20260615_0330
pip install numpy pandas matplotlib scipy --break-system-packages
# one shot (may take ~25-30 min of compute):
PYTHONDONTWRITEBYTECODE=1 python3 run_scans.py all
PYTHONDONTWRITEBYTECODE=1 python3 analyze.py
```

## Run under a short per-call time cap (e.g. a 45 s sandbox)
The driver checkpoints to CSV after every completed run and skips runs already present,
so just call it repeatedly. `BUDGET` makes it exit cleanly after that many seconds of
whole runs:
```bash
# repeat until it prints "ALL DONE":
PYTHONDONTWRITEBYTECODE=1 BUDGET=24 python3 run_scans.py all
```

## Resume
Re-running `run_scans.py all` is always safe: it loads `data/all_runs_summary.csv`,
builds the set of completed (phase,L,chi,seed,M_tot,kappa,eta_M,branch,T_max) keys, and
skips them. To force a rerun of a point, remove its row from the summary CSV (the daily
CSV may keep a duplicate; `analyze.py` aggregates by group so duplicates average in).

Phase E (hysteresis) warm-starts each χ from the previous χ's final field; those states are
persisted to `snapshots/state_E_{up,down}_*.npz`, so the chain also resumes correctly.

## Run a single phase
```bash
PYTHONDONTWRITEBYTECODE=1 python3 run_scans.py B    # A,B,C,D,E,F,G or 'all'
```

## Control parameter
Always interpret results in g = chi * M_tot / L^2 (= chi * M_bar), not raw chi. Predicted
crossover near g ≈ 1; measured g_c ≈ 0.7–1.05.

## Notes / gotchas
- Run with `PYTHONDONTWRITEBYTECODE=1` if the working folder is a synced mount (stale .pyc).
- If a CSV is empty/locked, the driver still writes headers correctly (it checks file size).
- Outputs are deterministic given the seed list.
