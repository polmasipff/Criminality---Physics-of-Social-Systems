# Return-home removal model — design note

*Why the dissuasion-only criminal population blows up, why a background "return-home"
exit fixes the structural mass-balance problem, why we set `δ = ω = 1/15`, the
limitations of the choice, and how it differs from arrest-based removal (which we do
NOT use).*

This is the **current** model. It supersedes `removal_model_proposal.md`, which is now
obsolete (it proposed a police-dependent arrest channel `κM` and competing hazards;
we keep no arrest, no `κ`, no `h`, no Options B/C).

---

## 1. The pathology: why N blows up in the dissuasion-only model

In the original Short et al. (2008) model and its dissuasion-only police extension, a
criminal can leave the system in exactly one way: **by committing a crime**. There is
no other exit. Track the number of active criminals `N(t)`. Over one step,

```
N(t+dt) − N(t) = inflow − crimes − (other exits) ,   other exits = 0 .
```

In steady state ⟨ΔN⟩ = 0, so

```
⟨crime rate⟩ = inflow = Γ L²        (★)
```

The stationary total crime rate is **pinned to the inflow** and is **independent of
χ**. Dissuasion cannot change *how much* crime happens in steady state — only *where*
and *how concentrated* it is. Now, the realized crime rate is approximately

```
crime rate ≈ N · ⟨Ã⟩ ,     Ã = A0 + B e^{−χM}  (perceived attractiveness),
```

and dissuasion lowers ⟨Ã⟩ (it drives the dynamic part `B e^{−χM}` toward 0, leaving
roughly the floor `A0`). But the crime rate is fixed by (★). The only free variable
is `N`, so

```
N_steady ≈ Γ L² / ⟨Ã⟩ .             (★★)
```

As χ rises, ⟨Ã⟩ falls toward the `A0` floor, so **N must rise** to keep the product
constant. Criminals pile up because each is now less likely to "discharge" by
offending, so each lingers longer while the inflow keeps refilling the reservoir.
The frozen baseline shows this quantitatively: `N: 69 → ~980` across the χ sweep while
crimes/step stays flat at the inflow. It is a faithful structural consequence of the
assumption "criminals only leave by offending," not a bug.

This also makes **total crime a useless order parameter** in the dissuasion-only
model: (★) pins it regardless of χ.

---

## 2. The fix: a background "return-home" exit

Give criminals a second way out that does **not** require offending. Each criminal,
each step, independently returns home with probability

```
p_home = 1 − exp(−δ dt) .
```

Now the mass balance has a second sink:

```
N(t+dt) − N(t) = inflow − crimes − home_exits .
```

In steady state the exit flux still equals the inflow, but it is now **split** between
crime and home return:

```
inflow = crimes + home_exits .
```

Two things change, both desirable:

1. **N is bounded.** Each criminal has a finite expected residence time `≤ 1/δ`
   regardless of how strongly deterrence suppresses crime. The reservoir can no longer
   inflate without limit — (★★) is replaced by a balance where the home channel
   absorbs the criminals that deterrence prevents from offending.
2. **Total crime can actually fall.** Because some criminals now exit via home instead
   of crime, the stationary crime rate `crimes = inflow − home_exits` is no longer
   pinned to the inflow. As χ rises and offending becomes unattractive, the home
   channel takes a larger share of exits and **total crime decreases** — so crime
   becomes a meaningful response variable again.

The transition we care about (hotspot → diffuse, controlled by `g = χM̄`) is still
present in the *spatial* structure of `B`; the return-home channel simply removes the
population artifact that contaminated the dissuasion-only accounting.

### Event logic (as implemented in `engine_return_home.py`)

At each step, for a criminal at site `s` (SEQUENTIAL, crime-first):

1. **crime** with `p_crime(s) = 1 − exp(−Ã_s dt)` → record crime, `E_s += 1`,
   criminal exits (and `B` later rises by `θ E_s`, as in Short).
2. else **home** with `p_home = 1 − exp(−δ dt)` → record home exit, criminal exits,
   **no** `B` increase.
3. else **move** by the usual `Ã`-biased nearest-neighbour rule.

> Implementation note on ordering. Because crime and home are two competing
> per-step Poisson clocks, a "crime-first" sequential check privileges crime at
> `O(dt²)`. At `dt = 1/100` (per-step probabilities ~1%) this bias is ~0.5% and
> physically negligible. The engine also offers `event_order="competing"` (draw the
> exit type ∝ rates, no ordering bias) purely as a robustness check; results differ
> by `O(dt²)`. Production uses `sequential`, the model as specified.

---

## 3. Why δ = ω = 1/15

`δ` sets the criminal residence time `~1/δ`. We tie it to the existing model
time-scale `ω = 1/15` (the `B` decay / "memory" rate, ≈ 15 days), for three reasons:

- **No new free parameter.** The model already commits to `1/ω ≈ 15` days as the
  characteristic repeat-victimization window. Setting the criminal residence time to
  the same scale means a would-be offender lingers about as long as the attractiveness
  memory it could reinforce — there is no separate, tunable knob to over-fit.
- **It is the natural Jones–Brantingham–Chayes (2010) choice.** Their agent model
  includes exactly this background return rate; `δ = ω` keeps us in a regime they
  already studied.
- **It is empirically sufficient.** In this folder's earlier `dishome` exploration
  (`δ ∈ {0, 1/30, 1/15, 0.1}` swept across the three `g` regimes), `δ = 1/15` bounded
  `N` while leaving the `f_hot` regime change intact, whereas `δ = 0` blew up and even
  smaller `δ` only weakly capped the population. `δ = 1/15` is the smallest tie-to-an-
  existing-scale value that does the job.

`δ = 0` must (and does, bit-for-bit) recover the dissuasion-only model; `δ = 1/15` is
the production value.

---

## 4. Limitations of this modelling choice

Be explicit about what return-home is and is not:

- **It carries no policy content about police.** `δ` is a constant, police-independent
  leak. It keeps `N` finite and crime interpretable, but it cannot let police
  *actively drain* a mature hotspot — high-`M` cells return criminals home at the same
  rate as empty cells. So return-home explains *crime reduction via desistance/relocation*,
  not *crime reduction via enforcement*.
- **It is memoryless / exponential.** A constant per-step hazard gives exponentially
  distributed residence times. Real desistance is not memoryless (it depends on time
  in system, age, opportunity). If residence-time *shape* becomes a headline result,
  this assumption should be revisited (e.g. an age-dependent `δ(t_in_system)`).
- **It does not couple to space.** Because `δ` is uniform, the home channel cannot by
  itself create or destroy spatial structure; all spatial structure still comes from
  the `B`–`M`–`Ã`–movement feedback. That is intended (we want a clean regularizer),
  but it means return-home is not a substitute for a spatial enforcement mechanism.
- **One scalar sets a population scale.** Since `N ~ inflow/(⟨Ã⟩ + δ)` roughly, the
  absolute `N` depends on `δ`; only ratios and spatial measures are `δ`-robust. Report
  structural order parameters (which are `δ`-insensitive) as primary, and treat
  absolute `N` as `δ`-dependent.

---

## 5. How this differs from arrest-based removal (which we are NOT using)

An earlier proposal added a **police-dependent arrest** hazard `λ_arrest = κ M_s`
(normalized `h = κ M̄`), removing criminals faster where police density is high. We are
**not** using it. The contrasts:

| | return-home `δ` (USED) | arrest `κM` (NOT used) |
|---|---|---|
| couples to police field `M`? | no (uniform leak) | yes (∝ local `M`) |
| can drain mature hotspots? | no | yes |
| free parameters | one, tied to `ω` | one (`κ`), plus the `κ`–`χ` interaction plane |
| interpretation | desistance / relocation | enforcement / incapacitation |
| extra control axis | none | `h`, doubling the parameter space |
| risk | underclaims police effect | overlaps/entangles with `χ`; harder to attribute |

We drop arrest deliberately: it doubles the parameter space (`g`×`h`), entangles the
removal effect with the deterrence axis we are trying to isolate, and is not needed to
fix the structural blow-up. The single, minimal, scale-tied return-home channel is the
cleanest correction to the mass-balance pathology while keeping `g = χM̄` as the one
control parameter of interest. **No `κ`, no `h`, no arrest, no Options B/C.**

---

### References
Short et al., M3AS 18 (2008) — base model. Jones, Brantingham & Chayes, M3AS 20 (2010)
— police as agents, deterrence, the background return rate `δ`. Short et al., PNAS 107
(2010) — suppression vs displacement. Jusup et al., Phys. Rep. 948 (2022), §8.2 — review.
