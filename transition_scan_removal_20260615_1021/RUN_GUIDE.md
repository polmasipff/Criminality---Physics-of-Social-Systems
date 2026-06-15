# RUN_GUIDE — how to rerun safely without destroying or duplicating results

This project now has **two independent, self-contained run folders**. Neither
script ever writes into the other folder, so you cannot accidentally overwrite
old results by running new ones.

| Folder | What it is | Status |
|---|---|---|
| `transition_scan_20260615_0330/` | Dissuasion-only transition scan (χ sweep, finite-size, hysteresis). **Frozen baseline.** | Do **not** modify. Read-only reference. |
| `transition_scan_removal_20260615_1021/` | Criminal-removal mechanism scan (competing-hazards engine: crime/arrest/home). **Active.** | This is where new work happens. |

The golden rule: **raw simulation outputs are append-only; figures are
disposable and rebuilt from the raw outputs.** If you only want new pictures,
never touch a simulation script.

---

## 1. What each file is

### Frozen baseline — `transition_scan_20260615_0330/`
- `engine.py` — dissuasion-only model (`run_police_sim`). **Raw-output producer.**
- `run_scans.py` — phase driver A–G. **Raw-output producer.** Resume-safe.
- `analyze.py` — builds `figures/` + `data/transition_estimates.csv`. **Figure producer (derived).**
- `data/all_runs_summary.csv`, `data/all_runs_daily.csv` — **raw outputs** (one-row-per-run; daily).
- `data/transition_estimates.csv` — **derived** (tanh-fit, rebuilt by `analyze.py`).
- `snapshots/*.npz` — **raw** field snapshots + Phase-E warm-start states.
- `figures/*` — **derived** (12 figures × PNG+PDF).

### Active — `transition_scan_removal_20260615_1021/` (this folder)
- `engine_removal.py` — competing-hazards model (`run_removal_sim`). **Raw-output producer.**
- `run_mechanism.py` — mechanism-scan driver. **Raw-output producer.** Resume-safe, flagged.
- `analyze_mechanism.py` — builds `figures/`. **Figure producer (derived).**
- `test_engine_removal.py` — sanity test (bit-identity, mass balance, conservation).
- `runs/summary.csv` — **raw** (one row per completed run, stationary-tail averages).
- `runs/daily.csv` — **raw** (daily metrics, all runs concatenated).
- `runs/manifest.csv` — **raw** provenance log: every run's params + code hash + timestamp + status.
- `runs/snapshots/*.npz` — **raw** field snapshots (seed 0, representative configs).
- `figures/*` — **derived** (rebuilt by `analyze_mechanism.py`).

Quick rule of thumb: **`runs/` and `snapshots/` are precious; `figures/` are
cheap.** Back up `runs/` if you care; never hand-edit it.

---

## 2. The commands, by what you actually want to do

All commands assume `cd transition_scan_removal_20260615_1021` and
`PYTHONDONTWRITEBYTECODE=1` prefixed (avoids stale `.pyc` on the synced mount).

### (a) Rerun ONLY the figures from existing data — no simulation
```bash
PYTHONDONTWRITEBYTECODE=1 python3 analyze_mechanism.py
# or equivalently, through the driver:
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py --figures-only
```
This reads `runs/*.csv` + `runs/snapshots/` and overwrites `figures/`. It runs
**zero** simulations and never touches `runs/`. Safe to run anytime.
(Frozen folder equivalent: `python3 analyze.py`.)

### (b) Run ONLY the missing simulations (normal resume)
```bash
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py
```
The driver loads `runs/summary.csv`, builds the set of completed keys, and runs
**only** the points not already present. If everything is done it prints
`ALL DONE` and does nothing. This is the default behaviour — re-running is
always safe and never duplicates a completed point.

### (c) See what WOULD run, without running it
```bash
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py --dry-run
```
Prints the list of pending (mech, g, h, δ, seed) points and a compute estimate.
Touches nothing. Use this before every real run to confirm the plan.

### (d) Resume an interrupted scan / run under a per-call time cap
```bash
# repeat until it prints "ALL DONE":
PYTHONDONTWRITEBYTECODE=1 BUDGET=40 python3 run_mechanism.py
```
`BUDGET=<seconds>` makes the driver checkpoint after each completed run and exit
cleanly (`BUDGET_EXIT`) once that many seconds of whole runs have elapsed. Every
finished run is already written to `runs/`, so the next call picks up exactly
where it stopped. (This is how the scan is run inside the 45 s sandbox shell.)

### (e) Add NEW parameter values without overwriting previous results
Edit the `grid()` function in `run_mechanism.py` and add points (new g, new h,
a new δ, a new mechanism label). Then:
```bash
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py --dry-run   # confirm only the NEW points appear
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py
```
The resume key is `(mech, L, seed, g, h, delta, M_tot, eta_M, T_max)`, all
rounded. Because **δ and the mechanism label are part of the key**, new points
never collide with old ones — they are simply appended. Existing rows are left
untouched.

> ⚠️ If you add a brand-new *parameter* to the engine (beyond g/h/δ), you must
> also add it to the key in `load_done()` and `key()`, or runs that differ only
> in that parameter will be silently skipped as "already done". This is the
> single most important gotcha when extending the model.

### (f) Force a rerun of points that already exist
```bash
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py --force
```
Reruns every grid point even if present. This **appends** new rows to
`runs/summary.csv` and `runs/daily.csv` (it does not delete the old ones).
Because `analyze_mechanism.py` aggregates by group mean, duplicate rows average
in. If you want a clean replacement instead of a duplicate, archive the old
`runs/` folder first (see §4).

### (g) Run a single mechanism / a quick test
The grid is small; the cleanest "single run" is the sanity test, which also
validates the engine:
```bash
PYTHONDONTWRITEBYTECODE=1 python3 test_engine_removal.py
```

---

## 3. How to identify stale results

A result is **stale** if the engine changed after it was computed. Two cheap
checks:

1. **Code hash.** Every run records the MD5 of `engine_removal.py` in
   `runs/manifest.csv` (`code_hash`). Compare against the current code:
   ```bash
   python3 -c "import hashlib;print(hashlib.md5(open('engine_removal.py','rb').read()).hexdigest()[:10])"
   cut -d, -f2 runs/manifest.csv | sort -u     # hashes present in the data
   ```
   If a row's `code_hash` differs from the current engine, that row was produced
   by a different model version → treat it as stale and rerun it (`--force` after
   archiving, or delete its rows from a working copy).

2. **Timestamps.** `runs/manifest.csv` has an ISO timestamp per run. Any run
   older than your last engine edit is suspect.

> The frozen folder has **no** code hash in its CSVs (it predates this
> convention). Its provenance is the fixed `engine.py` in that folder plus
> `RUN_STATE.md`. Treat the whole folder as one immutable snapshot.

---

## 4. How to archive / snapshot before a risky change

File **deletion is blocked** on this mount (`Operation not permitted`); you can
only truncate or copy. To preserve a set of raw outputs before a `--force` or a
model change, copy them aside:
```bash
cp -r runs runs_backup_$(date +%Y%m%d_%H%M)
```
Then it is safe to experiment. Figures need no backup — rebuild them anytime.

---

## 5. Mount gotchas (carried over from the baseline run)

- Always prefix `PYTHONDONTWRITEBYTECODE=1` so a stale `.pyc` from a previous
  edit is never imported.
- The Windows↔Linux sync can **truncate a file between writing it and reading it
  back**. When editing code from the shell, write via a heredoc, then
  `sync; sleep 1`, then `python3 -c "import ast; ast.parse(open(F).read())"` to
  verify before running.
- Background/`nohup` processes do **not** survive between sandbox shell calls.
  Use the foreground `BUDGET=…` loop (§2d), which is what the resume mechanism is
  built for.

---

## 6. One-screen cheat sheet

```bash
cd transition_scan_removal_20260615_1021
export PYTHONDONTWRITEBYTECODE=1

python3 test_engine_removal.py            # validate engine (bit-identity, mass balance)
python3 run_mechanism.py --dry-run        # what would run
BUDGET=40 python3 run_mechanism.py        # run/resume missing points (repeat to ALL DONE)
python3 run_mechanism.py --figures-only   # rebuild figures only
python3 run_mechanism.py --force          # rerun everything (appends; archive runs/ first)
```
