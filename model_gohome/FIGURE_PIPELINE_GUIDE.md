# Figure pipeline guide — return-home model

How to generate the data and regenerate every figure for the crime-hotspot + police
field study with the **return-home** criminal-removal channel (`δ = 1/15`, no κ, no
arrest). Read this together with `return_home_model_design.md` (the science) and
`figure_plan.md` (what each figure means).

> The model here is return-home ONLY. There is no arrest, no `κ`, no `h`, no Options
> B/C. The older `engine_removal.py` + `run_mechanism.py` + `analyze_*.py` and the
> top-level `runs/` and `figures/` are the OBSOLETE arrest-era artifacts; they are kept
> read-only as a historical record and are not part of this pipeline.

---

## 0. What was added (this pipeline)

```
engine_return_home.py            return-home engine (sequential crime->home->move)
tests/test_engine_return_home.py 23 correctness checks (δ=0 bit-identity, balance, ...)
config/scan_config_template.yaml editable config; delta=1/15; g-grid; run-sets; NO kappa
scripts/common.py                shared helpers (config, paths, g<->chi, aggregation)
scripts/run_transition_scan.py   DATA GENERATOR (the only script that runs sims)
scripts/plot_stationary_snapshots.py
scripts/plot_time_series.py
scripts/plot_order_parameters.py
scripts/make_gifs_from_snapshots.py
scripts/analyze_waiting_times.py
```

Outputs go under a dedicated root `out_return_home/` (override `--output-dir`), so they
never collide with the legacy top-level `runs/`/`figures/`:

```
out_return_home/
  config_used.yaml               resolved config snapshot (traceability)
  runs/summary.csv               one stationary-tail row per run  (order params)
  runs/daily.csv                 per-day metrics, all runs        (time series)
  runs/manifest.csv              params + engine MD5 + timestamp per run
  runs/snapshots/snap_g*.npz     field snapshots (B,M,Ã,deter,crime_accum)
  runs/movies/movie_g*.npz       field movie stacks (for GIFs)    [if movie_every set]
  runs/events/events_g*.csv.gz   per-event log (crime/home)       [if save_event_logs]
  runs/derived/*.csv             tidy CSVs from the analysis scripts
  figures/*.{png,pdf}            all figures
  figures/gifs/*.gif             animations
```

---

## 1. Quick start (the exact commands to run later)

All commands assume you are in the project folder and prefix `PYTHONDONTWRITEBYTECODE=1`
(avoids stale `.pyc` on the synced mount). Nothing below is destructive.

```bash
cd transition_scan_removal_20260615_1021
export PYTHONDONTWRITEBYTECODE=1

# 0) validate the engine (tiny; ~20 s). Must print "0 check(s) failed".
python3 tests/test_engine_return_home.py

# 1) SEE the plan without running anything
python3 scripts/run_transition_scan.py --run-set pilot --dry-run

# 2) generate the PILOT data (L=64, 5 g, 3 seeds, ~30 s total)
python3 scripts/run_transition_scan.py --run-set pilot

# 3) build every figure from whatever data exists (no sims)
python3 scripts/run_transition_scan.py --figures-only
#    (equivalently, run the five scripts individually — see §4)

# 4) scale up when ready (edit the config first; see §5)
python3 scripts/run_transition_scan.py --run-set intermediate --dry-run
python3 scripts/run_transition_scan.py --run-set intermediate
python3 scripts/run_transition_scan.py --run-set final          # production
```

The default `--output-dir` is `out_return_home/`. Pass `--output-dir out_run_<date>`
to start a fresh, separately-tracked run set.

---

## 2. Dry-run mode (default-safe)

`--dry-run` prints exactly which `(g, seed)` points WOULD run (with `+snap/+events/
+movie` tags) and an estimate, and touches nothing. **Always dry-run before a real
run.** The driver's normal mode is RESUME (see §3), so even a real invocation only runs
missing points — but dry-run lets you confirm the grid and the engine hash first.

```bash
python3 scripts/run_transition_scan.py --run-set final --dry-run
```

## 3. Resume & not overwriting old results

- **Append-only raw outputs.** `summary.csv`/`daily.csv`/`manifest.csv` are appended,
  never rewritten. Field/event/movie files are written once per `(g, seed)`.
- **Resume is the default.** Re-running the driver loads `summary.csv`, builds the set
  of completed keys `(L, seed, g, δ, M_tot, eta_M, T_max)`, and runs only the missing
  ones. If all present it prints `ALL DONE` and does nothing.
- **`δ` is part of the key.** Changing `removal.delta` makes new points; they never
  collide with old ones.
- **Time-cap / checkpoint.** `BUDGET=<seconds> python3 scripts/run_transition_scan.py`
  checkpoints after each completed run and exits cleanly (`BUDGET_EXIT`). Re-run to
  pick up where it stopped. Useful for long `final` sets or sandbox time limits.
- **Separate output roots.** New runs default to `out_return_home/` and never touch the
  legacy `runs/`/`figures/`. For a clean parallel set, use `--output-dir`.
- **`--force`** reruns existing points; it **appends** duplicate rows (does not delete).
  If you want a clean replacement, copy the old `runs/` aside first (deletion is blocked
  on the mount): `cp -r out_return_home/runs out_return_home/runs_backup_$(date +%H%M)`.

## 4. Figures-only (regenerate pictures, no simulation)

```bash
python3 scripts/run_transition_scan.py --figures-only            # runs all five scripts
# or individually:
python3 scripts/plot_stationary_snapshots.py
python3 scripts/plot_time_series.py            [--smooth 7] [--g 0,1,3]
python3 scripts/plot_order_parameters.py
python3 scripts/analyze_waiting_times.py       [--min-crimes 5]
python3 scripts/make_gifs_from_snapshots.py    [--fps 8]
```

Each reads `out_return_home/runs/...` and overwrites only `out_return_home/figures/...`
and `out_return_home/runs/derived/*.csv`. They run zero simulations and never touch the
raw `runs/` data. All accept `--output-dir DIR` to point at an alternative output root.

## 5. Working with the config

Edit `config/scan_config_template.yaml`. Key fields:

- `removal.delta: 0.0666666667` (= 1/15). The return-home rate. **Fixed for all g.**
  Set to `0.0` to reproduce the dissuasion-only blow-up (sanity / comparison).
- `grid.g_values`, `grid.seeds`, `grid.L`, `grid.T_max` — the scan. `χ` is derived per
  run as `χ = g L²/M_tot`.
- `windows` — burn-in & stationary averaging window (the driver auto-adjusts for
  `T_max ≥ 365/730`).
- `output.save_fields / snapshot_g / snapshot_days` — field snapshots (Fig 1).
- `output.movie_every / movie_g` — field movie stacks for GIFs (Fig 2). `null` = off.
- `output.save_event_logs / event_log_g` — per-event logs for waiting-time analysis
  (Fig 5). Heavy; enable for a small g-subset only.
- `run_sets:` `pilot` / `intermediate` / `final` — pick one with `--run-set NAME`, or
  copy its values into `grid`. Cost estimates are in the comments and in §6.

There is intentionally **no κ / arrest / h** field. Do not add one to the main config.

## 6. Recommended ensemble (opinion) and cost

Runtime scales ≈ `L² · T · ⟨N⟩`. Measured: L=64,T=120 ≈ 2 s/run; expect L=128,T=365 ≈
1–2 min/run (more at large g where `N` is larger, though return-home keeps it bounded).

| set | L | g-grid | seeds | runs | ~time | supports |
|---|---|---|---|---|---|---|
| pilot | 64 | {0,.5,1,1.5,3} | 3 | 15 | ~30 s | pipeline check, snapshots, time series, exit channels |
| intermediate | 128 | {0,.5,.7,.85,1,1.2,1.5,3} | 8 | 64 | ~1–2 h | order params vs g with error bands |
| final | 128 | {0,.3,.5,.7,.85,1,1.2,1.5,2,3} | 15 | 150 | ~3–5 h | all figures, publication bands |

Recommended **g-grid** spanning the regimes: pre `{0, 0.3, 0.5}`, transition
`{0.7, 0.85, 1.0, 1.2}`, post `{1.5, 2.0, 3.0}`. For the **waiting-time** figures,
event logs on a 3-g subset `{0, 1, 3}` with ~5 seeds are enough (events are the heavy
output). To settle **crossover-vs-transition**, add a third size `L=256` and test for
finite-size sharpening of `H`/`f_hot` (decisive test; two sizes cannot distinguish a
sharp transition from a rounded crossover).

## 7. Validating / spotting stale results

- `tests/test_engine_return_home.py` must print `0 check(s) failed` after any engine
  edit.
- Every run records the engine MD5 in `runs/manifest.csv` (`code_hash`). Compare to the
  current engine; rows with a different hash were produced by a different model version:
  ```bash
  python3 -c "import hashlib;print(hashlib.md5(open('engine_return_home.py','rb').read()).hexdigest()[:10])"
  cut -d, -f2 out_return_home/runs/manifest.csv | sort -u
  ```
- `balance_error` is in `daily.csv` and `summary.csv`; it must be 0 everywhere.

## 8. Mount gotchas (carried over)

- Always prefix `PYTHONDONTWRITEBYTECODE=1`.
- File deletion is blocked on the mount; archive by copy, never rely on delete.
- Background processes don't survive between shell calls; use the `BUDGET=` resume loop
  for long sets.
