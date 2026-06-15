# RUN_STATE — transition_scan_removal_20260615_1021

Interactive session, 2026-06-15. Extends the frozen dissuasion-only baseline
`../transition_scan_20260615_0330/` with a criminal-removal channel.
Status: **Stage 0 (docs) + Stage 1 (code) + Stage 2 (cheap test) COMPLETE.**

## What I inspected
- Frozen folder `../transition_scan_20260615_0330/`: `engine.py`, `run_scans.py`,
  `analyze.py`, `RUN_STATE.md`, `transition_scan_report.md` (9.6 KB, intact — the
  earlier "empty" reading was a `du` block-count artifact on the synced mount,
  not real truncation), `transition_scan_README.md`, and `data/*.csv` (109 runs).
- `../resumen_proyecto_policia.md` for model provenance and decisions.
- Key finding confirmed in data: dissuasion-only pins crimes/step at the inflow
  while `N` climbs 69→982 (the blow-up). The frozen `engine.py` already contained
  a **sequential** κ arrest channel (Option B); Phase G ran (χ,κ)=(30,30).

## What I created (this folder — nothing in the frozen folder was touched)
- `engine_removal.py` — Option C competing-hazards engine (crime/arrest/home).
  Bit-identical to `engine.py` at κ=δ=0; full mass-balance accounting + asserts.
- `test_engine_removal.py` — 15 checks (bit-identity, mass balance, conservation,
  limits). **All pass.**
- `run_mechanism.py` — resumable driver. Flags: `--dry-run`, `--figures-only`,
  `--force`, `BUDGET=<s>`. Resume key includes δ and mechanism label. Writes
  `runs/{summary,daily,manifest}.csv` + `runs/snapshots/`. Records engine MD5 in
  the manifest for staleness detection.
- `analyze_mechanism.py` — builds 4 figures from `runs/`.
- Docs: `RUN_GUIDE.md`, `transition_dynamics_explained.md` (incl. the blow-up
  mass-balance section), `removal_model_proposal.md`, this `RUN_STATE.md`.

## What I ran
- `test_engine_removal.py` → 0 failures.
- The cheap mechanism scan: **L=64, T=120, seeds [0,1]**, M̄ matched to the L=128
  baseline (M_tot=125). 16 (g,h,δ) points × 2 seeds = **32 runs**, ~2 s each.
  Run in two `BUDGET=38/40` chunks; resume verified idempotent (re-dry-run = 0).
- `analyze_mechanism.py` → 4 figures (PNG+PDF).

## Commands used
```bash
cd transition_scan_removal_20260615_1021
PYTHONDONTWRITEBYTECODE=1 python3 test_engine_removal.py
PYTHONDONTWRITEBYTECODE=1 python3 run_mechanism.py --dry-run
PYTHONDONTWRITEBYTECODE=1 BUDGET=38 python3 run_mechanism.py   # ×2 until ALL DONE
PYTHONDONTWRITEBYTECODE=1 python3 analyze_mechanism.py
```

## Key results (cheap test)
Steady-state exit flux = inflow (~8.4/day) in every case; only the composition
changes. Dissuasion g=3: N=204, crimes/day=8.5 (crime carries all exits — blow-up
reproduced). Arrest h=3: N=2.8, crimes/day=0.08 (arrests carry exits — crime
suppressed ~100×). Home δ=1 and "all" behave as expected. Mass balance error = 0
and ΣM=M_tot (max dev 4e-11) across all 32 runs.

## What is safe to rerun
- `python3 analyze_mechanism.py` or `run_mechanism.py --figures-only` — rebuilds
  figures only; never touches `runs/`. Always safe.
- `python3 run_mechanism.py` — resume; runs only missing points; safe.
- Frozen folder: treat as read-only; `python3 analyze.py` there only rebuilds its
  figures.

## What remains (pending your approval — Part V scaling)
1. Full (g,h) plane at L=64 (e.g. 5×5, 2–3 seeds) to test additivity vs
   interaction of dissuasion + arrest.
2. κ-sweep at L=128, T=365 (production size).
3. Small fixed δ under a χ sweep: does a bounded population change the H crossover?
4. With arrest on, test whether total crime becomes a clean order parameter with
   its own finite-size behaviour.
5. (From baseline next-steps) L=256 third size + T=730 / 5 seeds to settle
   crossover-vs-transition; analytical χ_c from linear stability with B→B e^(−χM̄).

## Gotchas (unchanged from baseline)
- Synced mount can truncate a file between write and immediate read → write code
  via shell heredoc, `sync; sleep 1`, verify with `ast.parse`. Use
  `PYTHONDONTWRITEBYTECODE=1`.
- File deletion blocked on the mount; archive by copy, never rely on delete.
- Background processes don't survive between shell calls → use `BUDGET` resume loop.

---

## Update — chi-sliced removal sweeps (first look)

Added isolated removal sweeps (one channel at a time) at fixed dissuasion slices
g ∈ {0,1,3}: arrest (κ varies, δ=0) and home (δ varies, κ=0), L=64, T=120, 2 seeds.
86 new runs, additive (`runs/summary.csv`); engine unchanged (hash 43d8a44465);
balance_error=0 and ΣM=M_tot in all. New figures: `sweep_mechanism_contrast`,
`sweep_arrest_chi_slices`, `sweep_home_chi_slices`, `sweep_arrest_vs_home`,
`sweep_M_defocus`. Analysis script: `analyze_sweeps.py` (includes f_hot).
Command: `BUDGET=40 python3 run_mechanism.py` ×6 → ALL DONE; `python3 analyze_sweeps.py`.

### Key finding (the f_hot panel)
Removal does **not** behave like dissuasion — it is the structural complement:
- Dissuasion (g: 0→3): f_hot collapses 0.126→0.050, crime flat ~8.5, N inflates 18→204.
- Arrest (h: 0→3, χ=0): **f_hot ≈ constant 0.10–0.12**, crime 7.3→0.08, N 17→2.8.
- Home (δ, χ=0): same as arrest (f_hot ≈ const, crime→0, N down).
So dissuasion **rearranges crime at fixed amount** (kills f_hot); removal **reduces
the amount at fixed spatial structure** (keeps f_hot). Both are smooth crossovers,
no sign of sharpening. Higher χ shifts the removal crossover to lower h/δ and a
small κ rescues the dissuasion blow-up (g=3: N 204→~34 by h=0.2). Arrest ≈ home at
equal mean hazard (focalisation bonus is small here). H rises under removal
(sparse-crime artifact) — use crimes/day, N, f_hot, not H.

---

## Update — return-home-only pipeline (2026-06-15, this session)

**Model decision (from you): keep ONLY the background return-home exit
`p_home = 1 − exp(−δ dt)`, `δ = ω = 1/15`. NO arrest, NO `κ`, NO `h`, NO Options B/C.
Event logic is SEQUENTIAL: crime → home(δ) → move.** The earlier competing-hazards
arrest engine is now obsolete (kept read-only).

### What I inspected
All of this folder: `engine_removal.py` (competing-hazards crime/arrest/home engine),
`run_mechanism.py`, `analyze_{mechanism,sweeps,dishome}.py`, `runs/` (174 summary rows;
mech ∈ base/dissuasion/arrest/both/home/dishome; `balance_error` max |·| = 0), the five
docs, and the snapshots. Confirmed the `dishome` mechanism already = return-home model.
The frozen baseline folder is **not mounted** in this session (only this folder is).

### What I added (nothing old was touched or overwritten)
- `engine_return_home.py` — clean return-home engine. Sequential crime-first; `δ=0`
  **bit-identical** to the dissuasion-only model (verified vs in-folder
  `engine_removal.py` at κ=δ=0). Opt-in per-event log (crime/home with day,x,y,
  criminal_id,entry_day,residence). Exact daily mass balance + M conservation asserts.
  Optional field-movie stacks for GIFs.
- `tests/test_engine_return_home.py` — **23 checks, 0 failures** (bit-identity, χ=0 no
  deterrence, mass balance, M conserved, B≥0, Ã≥A0, δ>0 fixes blow-up [N 55→20 at χ=30],
  event-log residence consistency).
- `config/scan_config_template.yaml` — `δ=1/15`, g-grid, derived `χ=gL²/M_tot`, seeds,
  windows, save flags, pilot/intermediate/final run-sets. **No κ.**
- `scripts/`: `common.py`, `run_transition_scan.py` (data generator;
  `--dry-run/--figures-only/--force/--output-dir`, `--run-set`, `BUDGET=` resume),
  `plot_stationary_snapshots.py`, `plot_time_series.py`, `plot_order_parameters.py`,
  `make_gifs_from_snapshots.py`, `analyze_waiting_times.py`.
- Docs: `FIGURE_PIPELINE_GUIDE.md`, `return_home_model_design.md`, `figure_plan.md`;
  obsolete banners on `removal_model_proposal.md` and a scope note on
  `transition_dynamics_explained.md`.

New outputs are isolated under `out_return_home/` (different schema from the legacy
`runs/`), so reruns can never clobber old data.

### What I ran (cheap/tiny only — NO model simulations/sweeps)
- The unit test (tiny L≤32, T≤80).
- Two throwaway pipeline validations in the sandbox `/tmp` (L=16,T=5 and L=24,T=40):
  confirmed the driver writes summary/daily/manifest/snapshots/events/movies, resume is
  idempotent, `balance_error=0`, and all five plotting/analysis scripts + `--figures-only`
  produce figures and tidy CSVs. These wrote to `/tmp`, never to your folder.

### What remains for YOU to run (I did not run any simulation)
```bash
cd transition_scan_removal_20260615_1021
export PYTHONDONTWRITEBYTECODE=1
python3 tests/test_engine_return_home.py                      # expect "0 check(s) failed"
python3 scripts/run_transition_scan.py --run-set pilot --dry-run
python3 scripts/run_transition_scan.py --run-set pilot        # ~30 s, L=64
python3 scripts/run_transition_scan.py --figures-only         # build all figures
# then scale up:
python3 scripts/run_transition_scan.py --run-set intermediate --dry-run
python3 scripts/run_transition_scan.py --run-set intermediate
python3 scripts/run_transition_scan.py --run-set final        # production (edit config first)
```
For the waiting-time figures, set `output.save_event_logs: true` (g-subset {0,1,3},
~5 seeds) before running; for GIFs set `output.movie_every`.

### Note
**Current model = return-home removal ONLY, `δ = 1/15`; no arrest, no `κ`, no `h`.**
