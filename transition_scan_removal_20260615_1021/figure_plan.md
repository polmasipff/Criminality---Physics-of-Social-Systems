# Figure plan — return-home transition study

For each planned figure: the scientific question, the data it needs, the script that
generates it, the files it reads/writes, and what a good vs bad result looks like.
All scripts live in `scripts/` and read from the output root (default
`out_return_home/`, override with `--output-dir`). None run a simulation; they read the
raw outputs produced by `scripts/run_transition_scan.py`.

Model reminder: `Ã = A0 + B e^{−χM}`, control `g = χM̄ = χ M_tot/L²`, single removal
channel `p_home = 1 − e^{−δ dt}`, `δ = 1/15`. No κ, no arrest.

---

## 1. Stationary field snapshots vs g

- **Question:** how do `B`, `M`, `Ã`, and deterrence `e^{−χM}` reorganize in space as
  deterrence rises from the base/pre regime, through the transition, to post?
- **Script:** `plot_stationary_snapshots.py` → `figures/stationary_snapshots_vs_g.{png,pdf}`
- **Reads:** `runs/snapshots/snap_g*_seed0.npz` (rows `B/M/Ã/deter`, cols = g regimes;
  color scales fixed across columns per row).
- **Needs:** scan run with `output.save_fields: true` and the g of interest in
  `output.snapshot_g`. Snapshots are taken at `snapshot_days` (default `final`, i.e.
  after burn-in), never during the transient.
- **Good result:** at small g, `B` shows sharp, well-separated hot cores; as g crosses
  ≈1 the cores soften/multiply and the field becomes diffuse; `deter` collapses toward
  0 on the hottest cells exactly where the cores dissolve. `M` tracks crime.
- **Bad result:** snapshots indistinguishable across g (transition absent or burn-in
  too short → re-check `T_max`/window), or `Ã < A0` anywhere (engine bug — it can't).
- **Base comparison:** the `g=0` column is the no-deterrence (χ=0) reference.

## 2. Animations / GIFs

- **Question:** how do the fields *evolve* — do new cores get aborted while old ones
  persist/drift, as the suppression-vs-displacement story predicts?
- **Script:** `make_gifs_from_snapshots.py` → `figures/gifs/{B,M,A_tilde,deter}_g<g>.gif`
  and `figures/gifs/combined_g<g>.gif` (B|M|Ã panel).
- **Reads:** `runs/movies/movie_g*_seed0.npz` (frame stacks). Built from SAVED frames,
  never by re-running. Color scales fixed per field across all g for comparability.
- **Needs:** scan run with `output.movie_every` set (e.g. 2) and g in `output.movie_g`.
- **Good result:** at small g, stable bright cores; near g≈1, flickering nascent cores
  that get extinguished where `M` lands; at large g, a uniform low field.
- **Bad result:** frozen frames (movie cadence too coarse) or color flchurn (scales not
  fixed — but the script fixes them, so this would signal a code regression).

## 3. Time series of N, crimes, home exits, inflow, balance error

- **Question:** does `N(t)` reach a bounded stationary value (no blow-up)? How is the
  exit flux split between crime and home over time? Does mass balance hold?
- **Script:** `plot_time_series.py` → `ts_n_criminals`, `ts_crimes`, `ts_home_exits`,
  `ts_inflow`, `ts_balance_error`, `ts_combined` (`.png/.pdf`).
- **Reads:** `runs/daily.csv` (one curve per g; mean ± SEM over seeds; burn-in /
  stationary windows shaded; optional `--smooth W`, raw data preserved).
- **Good result:** `N(t)` plateaus (bounded) for every g; `inflow` flat; crimes/day
  falls and home/day rises as g grows; **`balance_error ≡ 0`** at all times.
- **Bad result:** `N(t)` still climbing at `T_max` (extend `T_max`/burn-in), or any
  nonzero `balance_error` (accounting bug — should be impossible by construction).

## 4. Transition order parameters vs g

- **Question:** is there a hotspot→diffuse regime change, and at what `g_c`? Is it a
  sharp transition or a rounded crossover?
- **Script:** `plot_order_parameters.py` → `order_parameters_vs_g`,
  `hotspot_overlap_vs_g`, `transition_summary_vs_g`, `exit_channels_vs_g` (`.png/.pdf`)
  + tidy `runs/derived/order_parameters_vs_g.csv`.
- **Reads:** `runs/summary.csv` (stationary-tail averages per run), aggregated to
  mean ± SEM over seeds at each g. x-axis is `g`; secondary axis shows `χ`.
- **Observables:** `H = σ_B/⟨B⟩`, `f_hot_2/3 = P(B≥2⟨B⟩, ≥3⟨B⟩)`, `B_{90,95,99}/⟨B⟩`,
  `Gini(B)`, `corr(B,M)` and `corr(B,M)²`, `M_mass_on_hot10`, `deterrence_{mean,hot}`,
  `N`, crimes/day, home/day, exit fractions.
- **Good result:** `f_hot`, `Gini(B)`, tail quantiles all fall monotonically through a
  consistent `g_c ≈ 0.7–1.0`; `deterrence_hot` collapses there; crime falls while `N`
  stays bounded. Error bands tight enough to see the trend.
- **Bad result:** non-monotone or seed-band-dominated curves (need more seeds), or
  observables that disagree on `g_c` (then the "transition" is threshold-dependent →
  report as a crossover).

### Which order parameters to trust (opinion)
- **Primary (robust):** `f_hot_2`, `Gini(B)`, `B_{95,99}/⟨B⟩`. These measure spatial
  concentration of `B` directly and are insensitive to `δ` and to sparse crime.
- **Use with caveat:** `H = σ_B/⟨B⟩`. It is the classic order parameter and is fine for
  the *dissuasion* transition, BUT once crime gets sparse (large g, or with the home
  channel draining offenders) `B` becomes background-plus-rare-spikes and `H` can be
  **inflated** — a sparse-crime artifact, not a "hottier" state. Always read `H`
  alongside `N` and crimes/day.
- **Overlap:** `corr(B,M)` is meaningful; `corr(B,M)²` adds little (plotted for
  completeness). `M_mass_on_hot10` is the cleaner morphology measure.
- **Potentially misleading:** absolute `N` (depends on `δ`), total crime in the
  *dissuasion-only* limit (`δ=0` pins it to inflow). Spatial entropy/Gini are easy and
  informative; report Gini(B) as a concentration check on `f_hot`.

## 5. Waiting times & residence times vs g

- **Question:** does the transition change the *temporal* structure of crime — bursty
  repeat-victimization vs Poisson — and the residence times of criminals by exit type?
- **Script:** `analyze_waiting_times.py` → `waiting_times_ccdf`,
  `residence_by_exit_type`, `waiting_times_vs_g`, `exit_fraction_vs_g` (`.png/.pdf`)
  + tidy `runs/derived/waiting_times_summary.csv`.
- **Reads:** `runs/events/events_g*_seed*.csv.gz` (per-event log: crime/home with day,
  x, y, criminal_id, entry_day, residence). Pooled over seeds.
- **Measures:** (A) global inter-crime gaps, (B) per-cell inter-crime gaps (cells with
  ≥`--min-crimes`), (C) residence time entry→crime vs entry→home, (D) exit fractions.
- **Needs:** scan run with `output.save_event_logs: true` and g in `output.event_log_g`
  (a 3-g subset {0,1,3} with ~5 seeds is enough — events are the heavy output).
- **Good result:** per-cell inter-crime CV > 1 (bursty/clustered) in the hotspot phase,
  trending toward CV ≈ 1 (Poisson) in the diffuse phase; residence-by-crime lengthens
  with g (offending gets unattractive) while residence-by-home stays ~1/δ; exit
  fraction shifts from crime-dominated to home-dominated across `g_c`.
- **Bad result:** too few per-cell gaps (raise seeds or lower `--min-crimes`), or flat
  CV across g (then the transition is purely spatial, not temporal — itself a result).

### Most meaningful waiting-time definition (opinion)
The **per-cell (or within-hotspot) inter-crime gap** is the scientifically richest:
it is the repeat/near-repeat victimization clock that the `B` field is built to model,
and its dispersion (CV) is a clean burstiness diagnostic. The **global inter-crime
gap** has its *mean* pinned by the crime rate (≈ inflow minus home exits), so only its
*shape/CV* is informative — we report CV, not just the mean. **Residence time split by
exit type** is the best single diagnostic that the blow-up is fixed (entry→home caps
the residence that deterrence would otherwise inflate).

---

## File map (what each figure consumes)

| figure(s) | script | reads | writes (derived) |
|---|---|---|---|
| stationary_snapshots_vs_g | plot_stationary_snapshots.py | runs/snapshots/*.npz | — |
| gifs/* | make_gifs_from_snapshots.py | runs/movies/*.npz | — |
| ts_* | plot_time_series.py | runs/daily.csv | — |
| order_parameters_vs_g, hotspot_overlap_vs_g, transition_summary_vs_g, exit_channels_vs_g | plot_order_parameters.py | runs/summary.csv | runs/derived/order_parameters_vs_g.csv |
| waiting_times_ccdf, residence_by_exit_type, waiting_times_vs_g, exit_fraction_vs_g | analyze_waiting_times.py | runs/events/*.csv.gz | runs/derived/waiting_times_summary.csv |

Every run is traceable: `runs/manifest.csv` records params + engine MD5 + timestamp per
run, and `out_return_home/config_used.yaml` is the resolved config snapshot.
