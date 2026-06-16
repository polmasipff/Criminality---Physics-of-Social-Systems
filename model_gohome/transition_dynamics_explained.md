# Transition dynamics explained

*A physicist's guide to the hotspot→diffuse regime change in the police-extended
Short model, and to the criminal-population pathology of the dissuasion-only
version.*

> **Scope note (current model).** The live model uses the **return-home** removal
> channel only (`δ = 1/15`); there is no arrest and no `κ`. Sections below that mention
> an arrest/`κ` channel (esp. §5's four-way distinction and its table) are kept as
> conceptual background — they correctly distinguish dissuasion from removal — but the
> arrest column is **not** part of the current pipeline. See `return_home_model_design.md`
> and `FIGURE_PIPELINE_GUIDE.md`. The blow-up analysis in §4 is exactly the pathology
> the return-home channel fixes.

This document is written for someone comfortable with statistical mechanics who
wants intuition for **this specific model**. It refers to the figures and data in
both run folders:
- baseline (dissuasion-only): `../transition_scan_20260615_0330/figures/` and `.../data/`
- removal mechanisms: `./figures/` and `./runs/`

---

## 1. The fields and what they mean

The model lives on an `L×L` periodic lattice, time step `δt`. Three lattice
fields and one particle population:

**B — dynamic attractiveness (repeat-victimization memory).**
A scalar field encoding how attractive a site currently is *because of recent
crime*. Each burglary deposits `θ` into `B` at that site; `B` then decays at rate
`ω` and diffuses to neighbours with weight `η`. `B` is the "near-repeat" memory
of the Short model: a burgled house and its neighbours stay attractive for ~`1/ω`
time units. It is the order-parameter field — hotspots **are** localized lumps of
high `B`.

**M — conserved police field.**
A scalar field representing where police attention/presence is allocated. It is
**not** agents; it is a density. Two design choices matter:
- `ΣM = M_tot` is conserved **exactly** at all times — police are neither created
  nor destroyed, only redistributed. `M_tot` is the police *budget*.
- `M` reacts only to **realized, observed crime E** (not to the latent `B`): it
  relaxes toward the spatial pattern of recent crime, `M ← (1−ω_M δt)·diffuse(M) +
  ω_M δt · M_tot · E/ΣE`. The diffusion is mass-preserving and the reallocation
  term sums to `M_tot`, so conservation is structural.

**Ã = A0 + B·e^(−χ M) — effective attractiveness perceived by criminals.**
This is the quantity a criminal actually responds to. It has two pieces:
- `A0`: the *intrinsic* baseline attractiveness (wealth, accessibility). **Police
  cannot patrol this away** — there is no `M` in front of it.
- `B·e^(−χ M)`: the *dynamic* part, suppressed by local police presence.

**e^(−χ M) — the local deterrence factor.**
A multiplicative discount in `[0,1]`. Where police density is high, the dynamic
attractiveness is exponentially suppressed. Crucially the suppression is
**multiplicative on B only**: deterrence can drive the dynamic part to zero but
returns crime to the intrinsic floor `A0`, never below. *Police make a place
ordinary, not crime-proof.*

**E — realized crime events.**
The 0/1 (per site, per step) field of actual burglaries. A criminal at site `s`
commits with probability `p_s = 1 − e^(−Ã_s δt)`; committing removes the criminal
from the system (in the original model) and deposits `θ` into `B_s`. `E` is what
police see; `B` is the latent memory they cannot directly measure.

Governing equations (baseline, dissuasion-only):

```
Ã_s      = A0 + B_s e^(−χ M_s)
p_s      = 1 − e^(−Ã_s δt)                         (commit probability)
q_{s→s'} ∝ Ã_{s'}                                   (movement bias toward attractive neighbours)
B_s(t+δt)= [(1−η)B_s + (η/z)Σ_nn B](1−ω δt) + θ E_s
M_s(t+δt)= (1−ω_M δt)[(1−η_M)M_s + (η_M/z)Σ_nn M] + ω_M δt M_tot E_s/ΣE
```
with inflow: each step, `Poisson(Γ δt L²)` new criminals appear at random sites.

Base parameters (Short Fig. 3(d) regime): `δt=1/100, ω=1/15, A0=1/30, η=0.03,
θ=5.6, Γ=0.002`. Police: `M_tot=500, η_M=0.1, ω_M=1/15`.

---

## 2. Why the control parameter is g = χ·M̄, not χ alone

`χ` never acts alone — it always appears as the product `χ M` inside `e^(−χ M)`.
`M` has units of "police per site", and its spatial mean is fixed by conservation:

```
M̄ = M_tot / L².
```

So the *typical* deterrence exponent is `χ M̄`, and the natural dimensionless
control parameter is

```
g ≡ χ · M̄ = χ · M_tot / L².
```

Two systems with the same `g` but different `(χ, M_tot, L)` sit at the same point
on the deterrence axis. This is why the report organizes everything by `g`: the
finite-size curves (different `L`, different `χ`, **same g**) line up in `g` and
not in `χ` (see `../transition_scan_20260615_0330/figures/finite_size_check.png`).

**Where does g≈1 come from?** Heuristically, hotspots survive as long as
deterrence cannot overcome the attractiveness contrast. A hotspot core has
`B_core/A0 ≫ 1`; killing it requires `χ M_core ≳ ln(B_core/A0) ≈ 3–5` *locally*.
But the relevant *average* control knob is `g = χ M̄`. The measured crossover
midpoint sits at `g_c ≈ 0.7–1.0` — i.e. the regime change happens once the
*mean-field* deterrence becomes order-one, even though killing an individual
mature core needs a locally larger `χM`. That gap between "mean-field order-one"
and "locally needs 3–5" is exactly why the transition is broad and why mature
cores are displaced rather than killed (next section).

---

## 3. The three regimes

The clean way to see the regime change is the order-parameter panel
`../transition_scan_20260615_0330/figures/transition_order_parameters.png` and
the field panels `.../figures/field_panels_pre_transition_post.png`. Numbers
below are from `data/all_runs_summary.csv` (L=128, M_tot=500, T=365, 2 seeds).

### Pre-transition (g ≲ 0.5, e.g. χ=0–16)
- **Hotspots survive.** `H = σ_B/⟨B⟩ ≈ 1.5`, hotspot-area fraction `f_hot ≈ 0.12`.
- `B` is **highly heterogeneous**: sharp, well-separated cores on a low background.
- Police **may concentrate** (M tracks crime through E), but deterrence is too
  weak: `χ M_core` is small, so `e^(−χ M)` barely dents `Ã` on the cores.
- Criminals are **trapped by the attractiveness landscape**: the movement bias
  `q ∝ Ã` funnels them into the cores faster than they leak out, and the cores
  are continuously refreshed by repeat victimization (`θ E` into `B`).

### Near the transition (g ≈ 0.7–1.0, χ ≈ 24–34)
This is where the morphology actually changes, and the mechanism is a feedback
loop, not a threshold:
- **Nascent hotspots can be aborted.** A new lump of `B` produces a few crimes
  `E`; police reallocate **onto exactly those cells** within the consolidation
  window `~1/ω ≈ 15` days; the deterrence factor there drops; repeat
  victimization is blocked before the core matures. New cores are killed; old
  cores are not (police `M ≈ const` over a wide mature core cancels in the
  movement ratio `q ∝ Ã`, so it displaces rather than expels — the
  suppression-vs-displacement result of Short et al. PNAS 2010).
- **B heterogeneity drops.** `H` falls through ≈1.1, `f_hot` through ≈0.08.
- **The B–M–Ã–movement feedback reshapes the pattern.** Because `M` chases `E`
  and `Ã` feeds back into both `p` and `q`, the cores soften, multiply, and drift.
- **Overlap matters.** `corr(B,M)` stays high (~0.83–0.90: police are
  everywhere crime is), but `M_mass_on_hot10 ≈ 0.11` — police never strongly
  *over*-concentrate on the hottest cells. Deterrence on the hottest 10% of sites,
  `deterrence_hot = ⟨e^(−χM)⟩_hot`, collapses from 1.0 toward 0 across this window
  (`.../figures/police_crime_overlap.png`). That collapse is the proximate cause
  of the morphology change.

### Post-transition (g ≳ 3, χ ≳ 100)
- `B` becomes **diffuse**: `H` plateaus at ≈0.83, `f_hot ≈ 0.044`. The lattice is
  near-uniform `B` with rare, short-lived spikes.
- Hotspots are **suppressed/smeared**, not concentrated.
- **Crime does NOT decrease** — see §5. Total crime is essentially flat across the
  whole sweep; only its *spatial concentration* changed.
- **The criminal population increases** (69 → ~980): criminals fail to commit and
  therefore fail to leave (§4).

So the transition is best read as **hotspot → diffuse**, i.e. a change in the
*spatial organization* of crime, not in its amount.

---

## 4. Why criminal population blows up in the dissuasion-only model

> This is the section you asked for specifically. It is a **structural
> consequence of the model**, not a code bug.

### The mass-balance argument

Track the number of criminals in the system, `N(t)`. Over one step,

```
N(t+δt) − N(t) = inflow − successful_crimes − other_removals.
```

In the **original Short model and the dissuasion-only extension**, a criminal
leaves the system **only by committing a crime**. There is no other exit:
`other_removals = 0`. So

```
ΔN ≈ Γ L² δt  −  (crimes that step).
```

In steady state `⟨ΔN⟩ = 0`, hence

```
⟨crime rate⟩  =  Γ L²   (the inflow).            (★)
```

**This is the key fact.** The stationary *total* crime rate is pinned to the
inflow `Γ L²` and is **independent of χ**. Dissuasion cannot change how much crime
happens in steady state; it can only change *where* and *how fast* equilibrium is
reached — i.e. the spatial pattern and the transient.

Now ask what `N` must do. The realized crime rate is, to leading order,

```
crime rate ≈ N · ⟨p_commit⟩ / δt ≈ N · ⟨Ã⟩,
```

where `⟨Ã⟩` is the population-averaged effective attractiveness *seen by the
criminals*. Dissuasion lowers `⟨Ã⟩` (it pushes `B e^(−χM)` down toward 0, leaving
roughly `A0`). But the crime rate is *fixed* at `Γ L²` by (★). The only free
variable left is `N`. Therefore

```
N_steady ≈ Γ L² / ⟨Ã⟩.                            (★★)
```

As `χ` rises, `⟨Ã⟩` falls (toward the floor set by `A0`), so **`N` must rise to
keep the product constant**. Criminals pile up precisely because each one is now
less likely to "discharge" by committing a crime, so each lingers longer, and the
inflow keeps topping up the reservoir.

### The data confirms it quantitatively

Dissuasion-only sweep (baseline folder, L=128, M_tot=500):

| g (=χM̄) | χ | H | criminals N | crimes/step |
|---|---|---|---|---|
| 0.00 | 0 | 1.54 | 69 | ~0.33 |
| 0.49 | 16 | 1.27 | 156 | ~0.34 |
| 0.98 | 32 | 1.03 | 294 | ~0.29 |
| 1.53 | 50 | 0.92 | 458 | ~0.33 |
| 3.05 | 100 | 0.84 | 814 | ~0.33 |
| 9.16 | 300 | 0.84 | 982 | ~0.34 |

Crimes/step is **flat** (≈0.33, the inflow) while `N` climbs by ~14×. Exactly the
behaviour predicted by (★) and (★★). The same thing reproduces at L=64 in this
folder's mechanism scan (`runs/summary.csv`): dissuasion `g=0→3` gives
`N: 18→204` while crimes/day stays ≈8.4 (the L=64 inflow).

### Why this makes total crime a bad diagnostic
Because (★) pins total crime to the inflow regardless of `χ`, **total crime is
not a clean order parameter in the dissuasion-only model**. Reporting "crime
barely changed" is true but uninformative — the model *cannot* change it. What
changes is the spatial structure of `B`, which is why the good order parameters
are structural (§6).

### The honest caveat
The blow-up is a faithful consequence of the modelling assumption "criminals only
leave by offending." Whether that assumption is *reasonable* is a separate
question — in reality, would-be offenders desist, move away, or are arrested.
That is the motivation for the removal channel (`removal_model_proposal.md`): it
is not patching a bug, it is **correcting an over-simplified accounting of how
criminals exit**.

---

## 5. Dissuasion vs arrest vs crime-suppression vs hotspot-suppression

These four are routinely conflated; the model forces us to separate them.

- **Dissuasion** (χ): lowers *perceived opportunity* `Ã`. Changes the spatial
  pattern and the criminal population, but **not** total crime (★).
- **Arrest / removal** (κ, δ): *removes criminals* from the system without a
  crime. Opens a second exit channel, so it **can** reduce total crime.
- **Crime suppression**: fewer crimes in total. Requires a removal channel; pure
  dissuasion cannot deliver it.
- **Hotspot suppression**: less *spatial concentration* of crime (lower `H`,
  lower `f_hot`). Dissuasion delivers this, **without** crime suppression.

The mechanism scan in this folder makes the dissociation visible. At matched
strength (L=64):

| mechanism | H | criminals N | crimes/day | who carries the exit flux |
|---|---|---|---|---|
| base | 1.59 | 18 | 8.6 | crime |
| dissuasion g=3 | 0.87 | 204 | 8.5 | crime (still!) |
| arrest h=3 | — | 2.8 | 0.08 | arrests |
| both g=h=3 | — | 2.9 | 0.06 | arrests |
| home δ=1 | — | 7.8 | 0.3 | home exits |

See `figures/mech_exit_balance.png` — every bar reaches the inflow line; only the
*composition* of the exit flux changes. Dissuasion routes 100% of exits through
crime (so crime can't fall); arrest/home re-route the flux, so crime falls.
(`H` under removal is not comparable to base — see the warning in §6.)

---

## 6. Order parameters: what to trust

Because total crime is pinned (§4), use **structural** measures of `B`:

- **H = σ(B)/⟨B⟩** — coefficient of variation of attractiveness. High = spiky
  (hotspots), low = uniform (diffuse). Clean, smooth, monotone in `g`. Primary.
- **f_hot = fraction of sites with B ≥ 2⟨B⟩ (and ≥3⟨B⟩)** — hotspot area fraction.
- **B quantiles over the mean** (`B_p90/⟨B⟩`, p95, p99) — tail sharpness.
- **Gini(B)** — inequality of attractiveness; another concentration measure.
- **deterrence_hot = ⟨e^(−χM)⟩** on the hottest 10% — the *proximate driver*.
- **corr(B,M)** and **M_mass_on_hot10** — police–crime spatial overlap / morphology.
- **finite-size behaviour of the above** — the decisive test (§7).

> ⚠️ **H is not comparable across mechanisms once a removal channel is on.** With
> arrest/home active, crime becomes so sparse that `B` is almost everywhere
> background with rare isolated spikes, which *inflates* `H` (to ~2.5–3.4 in the
> scan) even though the lattice is "calmer". So for the *transition* (dissuasion)
> `H` is the right order parameter; for *mechanism comparison* use crimes/day and
> `N`, not `H`.

---

## 7. Phase transition or crossover? What would settle it

The regime change is real and repeatable, but calling it a *thermodynamic phase
transition* requires evidence the present runs do **not** provide. Keep the
language at **"transition-like crossover"** / **"hotspot-to-diffuse regime
change"** / **"finite-size transition signature."**

**Evidence that would support a genuine (continuous) phase transition:**
- *Finite-size sharpening*: the slope `|dH/d log g|` at the midpoint **grows with
  L**. (A real transition steepens toward a step as `L→∞`.)
- *Susceptibility peak growing with L*: a fluctuation measure (e.g. sample-to-
  sample variance of `H`, or `L² Var(H)`) develops a peak at `g_c` that **grows**
  with `L`.
- *Data collapse in g*: curves for different `L` collapse onto one scaling
  function of `(g − g_c) L^{1/ν}`, yielding a consistent exponent `ν`.
- *Narrowing crossover width*: the transition region (in decades of `g`) shrinks
  with `L`.

**Evidence that it is only a smooth crossover:**
- No sharpening: `|dH/d log g|` at the midpoint is **L-independent** (or even
  decreases).
- Broad transition region (here ~0.3–0.4 decades in `g`).
- No susceptibility peak — flat sample-to-sample variance.
- Strong dependence on the **observation window** (stationary cut, T) or on
  arbitrary **thresholds** (the `2⟨B⟩` in `f_hot`): a crossover's apparent
  sharpness is an artefact of where you put the threshold.

**What the baseline run actually found** (two sizes only, 2 seeds, T=365):
- A **leftward shift** of the midpoint with `L` (real, see
  `../transition_scan_20260615_0330/figures/finite_size_check.png`).
- **No clear sharpening** — if anything L=64 drops more steeply than L=128.
- **No susceptibility peak** in the seed-to-seed variance proxy
  (`.../figures/susceptibility_proxy.png`).
- **No hysteresis** between up- and down-χ sweeps (`.../figures/hysteresis_loop.png`)
  → the change is continuous/supercritical, not first-order.

Net reading: a **finite-size-rounded crossover at g_c ≈ 0.7–1.0**, consistent
with Fig. 3(d) sitting in the supercritical regime. To upgrade or refute this,
the decisive next experiment is a **third lattice size (L=256)** with ≥3–5 seeds
and `T=730`, then test for sharpening / a growing susceptibility peak / a `g`-axis
data collapse. Two sizes simply cannot distinguish a sharp transition from a
rounded crossover.

---

## 8. One-paragraph summary

The police field deters by multiplicatively suppressing the *dynamic* part of
attractiveness, controlled by the dimensionless `g = χ M̄`. As `g` crosses ≈1 the
crime pattern reorganizes from sharp hotspots to a diffuse field (H: 1.5→0.83;
f_hot: 0.12→0.04) — a continuous, hysteresis-free, finite-size-rounded
**crossover**, not (on present evidence) a proven phase transition. Because
criminals exit only by offending, the stationary *total* crime rate is pinned to
the inflow `Γ L²` and is independent of `χ`; dissuasion therefore inflates the
criminal population (69→~980) instead of reducing crime. Adding a genuine removal
channel (arrest κ and/or background return δ) opens a second exit, restores total
crime as a meaningful response variable, and lets police actually *reduce* crime
rather than merely *rearrange* it.

---

### Figure index
Baseline (`../transition_scan_20260615_0330/figures/`):
`transition_order_parameters`, `focused_transition_with_errorbars`,
`susceptibility_proxy`, `field_panels_pre_transition_post`, `police_crime_overlap`,
`hysteresis_loop`, `finite_size_check`, `field_panel_{B,M,A_tilde,deter,crime_accum}`.

This folder (`./figures/`):
`mech_timeseries`, `mech_late_vs_control`, `mech_exit_balance`, `mech_field_panels`.

### References
Short et al., M3AS 18 (2008) — base model. Jones, Brantingham & Chayes, M3AS 20
(2010) — police as agents, deterrence, return-home δ. Short et al., PNAS 107
(2010) — suppression vs displacement. Zipkin, Short & Bertozzi, DCDS-B 19 (2014)
— cops on the dots. Jusup et al., Phys. Rep. 948 (2022), §8.2 — review.
