# RUN_STATE — transition_scan_20260615_0330

Unattended scheduled run, 2026-06-15 ~03:30 → ~05:35 Europe/Madrid (hard stop 06:00).
Status at write: **ALL PHASES COMPLETE** (109 runs in data/all_runs_summary.csv).

## Output directory
`Crime/transition_scan_20260615_0330/`
- `engine.py` — reusable police-extended Short model + metrics + assertions.
- `run_scans.py` — phase driver A–G; checkpoints to data/ after every run; resume-safe;
  honours env BUDGET=<seconds> to exit cleanly under the 45 s shell cap.
- `analyze.py` — builds all figures + data/transition_estimates.csv from data/.
- `data/all_runs_summary.csv` — one row/run (stationary-window averages, 37 cols).
- `data/all_runs_daily.csv` — daily metrics, all runs concatenated.
- `data/transition_estimates.csv` — tanh-fit g_c / χ_c / width.
- `snapshots/*.npz` — saved fields (Phase A, D) and Phase-E warm-start states.
- `figures/` — 12 figures, each PNG + PDF.
- `transition_scan_report.md`, `transition_scan_README.md`.

## Completed tasks
- [x] Inspect repo; read resumen + base notebook.
- [x] Reimplement + validate police extension (prior notebook was MISSING).
- [x] Phase A sanity (L=64,T=120).
- [x] Phase B coarse scan (L=128, 16 χ, 2 seeds, T=365).
- [x] Phase C focused densification (6 extra χ, 2 seeds).
- [x] Phase D field snapshots (7 χ, days 50/185/365).
- [x] Phase F finite-size (L=64 & 128, 7 g, 2 seeds).
- [x] Phase E hysteresis (up + down χ sweeps).
- [x] Phase G arrest channel (base/dissuasion/arrest/both, 2 seeds).
- [x] All figures + transition_estimates.csv.
- [x] Report + README + RUN_STATE.

## Running assumptions / decisions
- Police-extension notebook & its CSVs were absent → rebuilt engine from base replication;
  validated against the resumen's χ-sweep (matches within noise).
- Homogeneous initial M = M̄ everywhere; M update = pure diffusion on crime-free steps.
- Control variable g = χ·M̄ reported alongside χ everywhere.
- T_max=365 (not 730) and 2 seeds (not 3) for B/C/F to fit all phases in the time budget;
  documented as a limitation. Stationary window days 185–365.
- Deterministic seeds. Runs skipped if their key already present in the summary CSV.

## Commands used
```
# grind all phases, ~3 L128 runs per 45 s shell call, resume-safe:
PYTHONDONTWRITEBYTECODE=1 BUDGET=24 python3 run_scans.py all     # repeat until "ALL DONE"
# build figures + estimates:
PYTHONDONTWRITEBYTECODE=1 python3 analyze.py
```

## Files generated
- 12 figures (PNG+PDF): transition_order_parameters, focused_transition_with_errorbars,
  susceptibility_proxy, field_panel_{B,M,A_tilde,deter,crime_accum},
  field_panels_pre_transition_post, police_crime_overlap, hysteresis_loop,
  finite_size_check, optional_kappa_mechanism_comparison.
- CSVs: all_runs_summary, all_runs_daily, transition_estimates.

## Key results (see report)
- Crossover midpoint g_c ≈ 0.72 (H) to 1.05 (f_hot) → χ_c ≈ 24–34 (M_tot=500, L=128).
- No hysteresis; flat susceptibility proxy; finite-size SHIFT but no clear sharpening
  → "transition-like crossover", not a proven phase transition.
- Dissuasion-only inflates criminals (69→~980); arrest cuts criminals (→34) and crime (→0.02).

## Known bugs / gotchas (resolved)
- The connected folder intermittently truncates files between a write and a later read
  (async Windows↔Linux sync). Mitigation: write code via shell heredoc + `sync; sleep 1` +
  in-call `ast.parse` verify; run Python with PYTHONDONTWRITEBYTECODE=1 to avoid stale .pyc.
- File deletion on the mount is blocked ("Operation not permitted"); truncate instead (`: > f`).
- Background/nohup processes do NOT survive between shell calls → use BUDGET-limited foreground
  calls and the resume-skip mechanism.
- summarize() clamps the stationary window to the second half for T<365 (sanity runs).

## Pending / next best tasks (priority order)
1. Re-run focused grid at T=730, 5 seeds (tighten g_c, susceptibility).
2. Third lattice size L=256 for a real finite-size-scaling collapse.
3. Full κ (arrest) sweep; map the (g,h) plane.
4. Analytical χ_c from linear stability with B→B·e^(−χM̄).
