> ⚠️ **OBSOLETE — superseded by `return_home_model_design.md`.**
> This document proposed a police-dependent **arrest** channel (`κ M`, normalized `h`)
> and a competing-hazards engine with Options A/B/C. The current model keeps **only**
> the background **return-home** exit (`δ = 1/15`): there is **no arrest, no `κ`, no
> `h`, no Options B/C**. The engine described here (`engine_removal.py`) and its driver
> (`run_mechanism.py`) and the top-level `runs/`/`figures/` are kept **read-only** as
> the historical arrest-era record. For the live pipeline use `engine_return_home.py`,
> `scripts/`, `config/scan_config_template.yaml`, and `FIGURE_PIPELINE_GUIDE.md`.
> The sections below are retained only for provenance; ignore the arrest content.

---

# Proposal: a criminal removal / arrest channel  *(OBSOLETE — see banner above)*

*Scientific motivation, comparison of three modelling options, recommendation,
and the implementation that is now in `engine_removal.py`.*

---

## 1. The problem this fixes

In the original Short model a criminal exits the system **only by committing a
crime**. As shown in `transition_dynamics_explained.md` §4, this pins the
stationary total crime rate to the inflow `Γ L²` (independent of dissuasion χ) and
makes the criminal population blow up under strong dissuasion (`N: 69→~980`).
Total crime is therefore not an interpretable response variable in the
dissuasion-only model.

We want criminals to be able to **leave without offending**, via a genuine exit
channel, so that (i) the population stays bounded, (ii) total crime can actually
fall, and (iii) police can *drain* mature hotspots, not just displace them. The
modelling question is *how* to implement this exit.

Two conceptually distinct knobs must be kept separate:
- **χ (dissuasion)** modifies *perception*: `Ã = A0 + B e^(−χM)`. It changes where
  criminals go and whether they offend, but removes nobody.
- **κ / δ (removal)** *removes criminals*. Arrest hazard `∝ κ M` (police-dependent);
  background return hazard `δ` (police-independent).

Normalized controls (matching the existing `g`):
```
g = χ · M̄      (dissuasion strength)
h = κ · M̄      (arrest strength)
δ              (background return rate; already dimensionless as a rate × time)
M̄ = M_tot / L².
```

---

## 2. The three options

### Option A — background abandonment / "return home"
Each criminal leaves independently per step with
```
p_home = 1 − e^(−δ δt).
```
- **Pros**: simplest possible; police-independent; guarantees a bounded
  population (mean residence ≤ `1/δ`); this is literally the `δ` term of Jones,
  Brantingham & Chayes (2010).
- **Cons**: carries no policy content about *police* — it is a structural
  regularizer, not a deterrence mechanism. It cannot let police drain hotspots.
- **Role**: best as a small "leak" that keeps `N` finite and crime interpretable,
  combined with another channel — not as the main story.

### Option B — police-dependent arrest/removal
Each criminal at site `s` is removed per step with
```
p_arrest(s) = 1 − e^(−κ M_s δt).
```
- **Pros**: uses the police field directly; stronger presence ⇒ higher removal
  hazard; lets police actively empty mature cores (the thing dissuasion cannot
  do). Scientifically the most interesting single channel.
- **Cons**: as a *sequential* check (the form already present in the frozen
  `engine.py`, which tested arrest **before** crime) it introduces an **ordering
  artifact**: whichever event is checked first is slightly favoured, biasing the
  crime/arrest split at `O(δt)`. Small here (`δt=1/100`, per-step probabilities
  ~1%), but real and conceptually ugly.

### Option C — competing Poisson hazards (recommended)
At each step a criminal at `s` faces three independent hazards
```
λ_crime(s)  = Ã_s = A0 + B_s e^(−χ M_s)
λ_arrest(s) = κ M_s
λ_home      = δ
λ_total     = λ_crime + λ_arrest + λ_home
p_event     = 1 − e^(−λ_total δt).
```
If an event fires, its **type** is drawn proportional to the rates:
```
P(crime) = λ_crime/λ_total,  P(arrest) = λ_arrest/λ_total,  P(home) = λ_home/λ_total.
```
- crime → `E_s += 1`, criminal exits, `B` rises by `θ E_s` (as in Short);
- arrest → criminal exits, **no** `B` increase;
- home → criminal exits, **no** `B` increase;
- no event → the criminal moves by the usual `Ã`-biased rule.
- **Pros**: the physically correct way to combine simultaneous Poisson processes;
  **no ordering artifact** (the split is exact, not sequential); Options A and B
  are exact special cases (`κ=0` or `δ=0`); reduces *exactly* to the original
  model when `κ=δ=0`.
- **Cons**: marginally more code (one extra uniform draw for the type when a
  removal channel is active). Negligible cost.

---

## 3. Recommendation

**Adopt Option C as the engine, and treat A and B as its limits.** Your intuition
is right: competing hazards avoid the arrest-vs-crime ordering arbitrariness, and
because A (`κ=0,δ>0`) and B (`δ=0,κ>0`) fall out as special cases, you lose
nothing by implementing the general form. Option B alone would have been an
acceptable first step, but since the marginal complexity of C is one extra random
draw, there is no reason to settle.

For *interpretation*, the recommended division of labour is:
- **κ M (arrest)** is the policy-relevant channel: it couples removal to police
  presence and lets police drain mature cores.
- **δ (home)** is a small structural leak that keeps `N` finite even where police
  are absent (so crime stays interpretable everywhere, not only under police).

A natural default for production runs: `δ` small (a weak global leak) plus a `κ`
sweep as the main experiment, with `χ` as the orthogonal deterrence axis.

---

## 4. What was implemented (and verified)

`engine_removal.py` implements Option C with the following guarantees, all
checked by `test_engine_removal.py` (15/15 pass):

- **Exact reduction.** At `κ=δ=0` the engine is **bit-for-bit identical** to the
  frozen `engine.py` (same final `B`, `M`, and criminal positions). This is
  achieved by preserving the RNG draw sequence on a crime-only fast path: with one
  hazard, `p_event = 1 − e^(−Ã δt) = p_commit` and every event is a crime, so no
  extra random number is consumed. Dissuasion-only results are reproduced exactly,
  not merely "within noise."
- **χ and κ kept separate.** `χ` only enters `Ã`; `κ` only enters the arrest
  hazard. They are independent axes (`g` and `h`).
- **Mass balance closes every day, exactly**:
  `ΔN = inflow − crimes − arrests − home_exits`, asserted `balance_error == 0`
  (verified max `|balance_error| = 0` across all 32 scan runs).
- **M conserved**: `|ΣM − M_tot| < 1e-6 M_tot` (measured max deviation ~`4e-11`).
- **Guards**: no negative criminals, no NaN/inf, `Ã ≥ A0`, removal fractions sum
  to 1.
- **Outputs kept separate** from the dissuasion-only folder (new
  `transition_scan_removal_…/runs/`), so nothing old is overwritten.

### New metrics logged per day (`runs/daily.csv`, summarized in `runs/summary.csv`)
`n_criminals`, `crimes_that_day`, `arrests_that_day`, `home_exits_that_day`,
`inflow_that_day`, `balance_error`, `frac_removed_{crime,arrest,home}`,
`mean_p_crime`, `mean_p_arrest`, plus all the field/hotspot metrics
(`H`, `f_hot`, `deterrence_hot`, `MB_corr`, `M_mass_on_hot10`, `Gini_B/M`, …).

---

## 5. Cheap-test findings (L=64, T=120, 2 seeds, M̄ matched to the L=128 runs)

`runs/summary.csv` + `figures/mech_exit_balance.png`. Steady-state inflow ≈ 8.4
criminals/day in every case; the exit flux always equals it — only its
composition changes:

| mechanism | g | h | δ | N | crimes/day | arrests/day | home/day |
|---|---|---|---|---|---|---|---|
| base | 0 | 0 | 0 | 18 | 8.6 | 0 | 0 |
| dissuasion | 3 | 0 | 0 | 204 | 8.5 | 0 | 0 |
| arrest | 0 | 3 | 0 | 2.8 | 0.08 | 8.5 | 0 |
| both | 3 | 3 | 0 | 2.9 | 0.06 | 8.5 | 0 |
| home | 1 | 0 | 1 | 7.8 | 0.3 | 0 | 7.7 |
| all | 1 | 1 | .5 | 5.8 | 0.12 | 5.7 | 2.7 |

Reading: **dissuasion routes 100% of exits through crime** (so crime is pinned and
`N` inflates); **arrest/home re-route the exit flux**, so crime collapses (≈100×
lower) and `N` stays small. This is the quantitative resolution of the blow-up.

(Note: `H` rises under removal — an artifact of crime becoming sparse, not a
"hotspottier" state. For mechanism comparison use crimes/day and `N`, not `H`.)

---

## 6. Proposed next experiments (pending approval)

1. **Map the (g, h) plane** at L=64 first (full grid, e.g. 5×5, 2–3 seeds): is
   "dissuasion + arrest" merely additive, or is there interaction (does deterrence
   make arrests more/less efficient by changing where criminals dwell)?
2. **κ-sweep at L=128, T=365** to confirm the L=64 picture at the production size.
3. **δ as a regularizer**: a small fixed `δ` under a `χ` sweep — does a bounded
   population make the *transition* itself look different (does the H crossover
   sharpen or move)?
4. Re-examine whether, **with arrest active, total crime becomes a clean order
   parameter** with its own finite-size behaviour.

None of these are large; each is a few minutes at L=64 and ~tens of minutes at
L=128. They should be run through `run_mechanism.py` (extend `grid()`), which
keeps them resumable and non-destructive.
