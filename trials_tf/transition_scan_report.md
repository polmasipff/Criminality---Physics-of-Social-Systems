# Police-as-conserved-field crime model — transition scan report

*Unattended scheduled run, 2026-06-15 (~03:30–06:00 Europe/Madrid). Output dir
`transition_scan_20260615_0330/`. Model: Short et al. (2008) Fig. 3(d) replication
extended with a conserved police field M.*

## Executive summary

A reproducible police-extension engine was (re)implemented from the base Short replication
notebook — **the previously-referenced `crime_model_police_extension.ipynb` and its CSVs were
not present in the project folder**, so the extension was rebuilt and re-validated. The new
engine reproduces the prior χ-sweep (χ=30 → H≈1.05, ~271 criminals vs the resumen's 1.05 / 275)
and conserves the police mass M exactly (ΣM = M_tot to 1e-6 across all runs).

Sweeping the dissuasion strength χ at fixed police budget (M_tot=500, L=128) reproduces a clear
**hotspot → diffuse regime change**. The hotspot index H = σ(B)/⟨B⟩ falls from ≈1.54 (χ=0) to a
plateau ≈0.83 (χ≳100), and the hotspot-core area fraction f_hot collapses from 0.124 to 0.044.
A tanh crossover fit places the midpoint at **g_c ≈ 0.72–1.05** depending on the observable
(H vs f_hot), i.e. **χ_c ≈ 24–34** for this L and budget — bracketing the predicted
g = χ·M̄ ≈ 1 (M̄ = M_tot/L²).

The change is best described as a **transition-like crossover**, not a proven thermodynamic phase
transition: (i) no hysteresis between up- and down-χ sweeps (the branches coincide), (ii) the
seed-to-seed variance of H shows no susceptibility peak at g_c, and (iii) the finite-size
comparison (L=64 vs L=128 at matched g) shows a **leftward shift** of the crossover with system
size but **no clear sharpening** — if anything L=64 transitions more steeply (but later). Together
these lean toward a finite-size-rounded crossover rather than a sharp transition.

As documented previously, **total crime is not a valid order parameter in the dissuasion-only
model** — criminals only exit by committing a crime, so strong χ inflates the criminal population
(69 → ~980) and spreads crime rather than reducing it. Adding an arrest channel
(p_rem = 1−e^{−κMδt}) restores total crime as a meaningful response variable: arrest-only cuts
the criminal population (69 → 34) and crimes/day (0.34 → 0.02) drastically, where dissuasion-only
does neither.

## Model equations

Effective attractiveness, burglary probability, movement bias:

-$ Ã_s = A0 + B_s · e^(−χ M_s) $  (dissuasion acts only on the dynamic part; intrinsic A0 cannot be patrolled)
- $p_s = 1 − e^(−Ã_s δt) $  (kept as Short, so χ=0 reproduces the base replication)
-$ q_{s→s'} ∝ Ã_{s'}$

Field updates (B exactly as Short; M conserved):

- $B_s(t+δt) = [(1−η)B_s + (η/z)Σ_nn B](1−ωδt) + θ E_s$
- $M_s(t+δt) = (1−ω_M δt)[(1−η_M)M_s + (η_M/z)Σ_nn M] + ω_M δt · M_tot · E_s/ΣE$
- optional arrest: $p_rem = 1 − e^(−κ M_s δt)$, removed criminals exit without raising B.

Base parameters: L=128, δt=1/100, ω=1/15, A0=1/30, η=0.03, θ=5.6, Γ=0.002.
Police: M_tot=500, η_M=0.1, ω_M=1/15. Control parameters g = χ·M̄, h = κ·M̄, M̄ = M_tot/L².

## Validation checks

- **M mass conservation**: ΣM == M_tot to <1e-6 in every run (asserted every 30 sim-days; the
  diffusion step is a convex combination and the reallocation term sums to M_tot).
- **χ=0 reproduces base Short**: H≈1.54, ~69 criminals, f_hot≈0.124 — matches the Fig. 3(d) regime.
- **Reproduction of prior sweep**: χ=10/30/100 give H≈1.39/1.03/0.84 and ~114/294/814 criminals,
  matching the resumen's 1.39/1.05/0.83 and 117/275/807.
- **No NaN/inf; B ≥ 0; Ã ≥ A0**: asserted throughout, all passed.
- **Sanity scan** (Phase A, L=64, T=120): H decreases monotonically with g, f_hot shrinks, no NaNs.

## What is the control parameter?

Organising by raw χ is misleading because χ multiplies M, and ⟨M⟩ = M̄ = M_tot/L² depends on both
budget and lattice size. The dimensionless **g = χ·M̄** is the right axis: the order-parameter
curves for the finite-size runs (different L, different χ, same g) line up far better in g than in χ,
and the predicted critical value is g ≈ 1. All results below report both χ and g.

## Coarse + focused scan results (L=128, M_tot=500, T=365, 2 seeds)

H(g) and f_hot(g) fall smoothly through the crossover; criminals rise monotonically; deterrence on
the hottest 10% of sites collapses toward 0; corr(B,M) stays high (~0.83–0.90, police track crime
everywhere) and M_mass_on_hot10 stays ~0.11 (police never strongly over-concentrate on cores).

| χ | g | H | f_hot | criminals | deterrence_hot |
|---|---|---|-------|-----------|----------------|
| 0 | 0.00 | 1.54 | 0.124 | 69 | 1.00 |
| 16 | 0.49 | 1.27 | 0.119 | 156 | 0.49 |
| 24 | 0.73 | 1.13 | 0.102 | 219 | 0.37 |
| 32 | 0.98 | 1.03 | 0.085 | 294 | 0.28 |
| 36 | 1.10 | 1.00 | 0.079 | 329 | 0.25 |
| 50 | 1.53 | 0.92 | 0.062 | 458 | 0.16 |
| 100 | 3.05 | 0.84 | 0.045 | 814 | 0.03 |
| 300 | 9.16 | 0.84 | 0.044 | 982 | 0.00 |

**tanh crossover fit** (`data/transition_estimates.csv`):
- H(g):  g_c = 0.72 (χ_c ≈ 23.7), width ≈ 0.39 decades
- f_hot(g): g_c = 1.05 (χ_c ≈ 34.3), width ≈ 0.28 decades

The two observables bracket g_c ∈ [0.7, 1.05], consistent with the g≈1 prediction. (Fits are a
compact descriptive summary, not evidence of criticality.)

## Field interpretation: pre / transition / post

See `figures/field_panels_pre_transition_post.{png,pdf}` and the per-field panels.

- **Pre (χ=0)**: B shows sharp, well-separated hotspot cores; M (homogeneous-seeded) tracks them
  via the E-reallocation; crime concentrates on cores.
- **Transition (χ≈36, g≈1.1)**: cores soften and multiply; deterrence e^(−χM) carves visible
  "holes" over the police-occupied cells; Ã is suppressed where M is high.
- **Post (χ=300, g≈9)**: B is nearly uniform at background; Ã is suppressed almost everywhere on
  the dynamic part; crime is diffuse but far more abundant in total (criminal population inflated).

## Hysteresis

Up-χ and down-χ sweeps (warm-started from the previous χ's final field) give H(g) branches that
coincide within noise (e.g. g=0.92: 1.056 up vs 1.062 down). **No hysteresis loop** → the regime
change is continuous/supercritical, consistent with Fig. 3(d) being in the supercritical regime.
See `figures/hysteresis_loop.{png,pdf}`.

## Finite-size check (L=64 vs L=128 at matched g, M̄ fixed)

See `figures/finite_size_check.{png,pdf}`. The L=128 H(g) curve lies below the L=64 curve through
the mid-range and its crossover midpoint sits at **lower g** (leftward shift with system size).
However, the maximum steepness |dH/dlog g| is **not** larger for L=128 — L=64 actually shows a
steeper (but later) drop. So this comparison gives **finite-size shift without clear sharpening**.
Two sizes cannot settle the question, but combined with the absent hysteresis and flat
susceptibility proxy, the evidence leans **crossover / finite-size-rounded transition** rather than
a sharp thermodynamic transition.

## Is this a phase transition or a crossover?

On the present evidence: a **transition-like crossover** at g_c ≈ 0.7–1.0. Arguments:
- *For "just a crossover"*: no hysteresis; no peak in seed-to-seed variance of H; no clear
  finite-size sharpening; H and f_hot vary smoothly over ~1 decade in g.
- *For "transition-like"*: a real, repeatable, fairly narrow regime change (~0.3 decades) with a
  well-defined midpoint near the predicted g≈1; finite-size shift of the midpoint.

This refines the resumen's tentative reading and keeps a critical tone: we do **not** claim a true
phase transition from one extra system size.

## Limitations

- Only 2 seeds per (χ,L) point (time budget) → the susceptibility proxy is noisy; a peak could be
  missed. 3–5 seeds and T=730 would tighten g_c and the variance estimate.
- Only two system sizes (64, 128); a proper finite-size-scaling analysis needs ≥3 sizes and a data
  collapse with a scaling exponent.
- T=365 with a 185–365 stationary window; some high-χ runs may not be fully stationary.
- H = σ(B)/⟨B⟩ is a convenient but non-unique order parameter; structure-factor / hotspot-count
  measures could be added.
- The arrest comparison (Phase G) uses a single (χ,κ)=(30,30) operating point and 2 seeds — it
  demonstrates the mechanism, not a full h-sweep.

## Optional: arrest mechanism comparison (Phase G, L=128, T=365)

| mechanism | H | criminals | crimes/day |
|-----------|---|-----------|-----------|
| base (χ=0,κ=0) | 1.54 | 69 | 0.34 |
| dissuasion (χ=30) | 1.06 | 270 | 0.38 |
| arrest (κ=30) | 3.69 | 34 | 0.02 |
| both | 4.08 | 35 | 0.01 |

Arrest removes criminals directly, so it cuts both the population and total crime; dissuasion-only
inflates the population and barely changes total crime. With arrest active, total crime becomes a
meaningful order/response variable again. (The high H under arrest is an artifact of very sparse
crime making B mostly background with rare spikes — H is not comparable across mechanisms with such
different crime levels.) See `figures/optional_kappa_mechanism_comparison.{png,pdf}`.

## Next steps

1. Re-run the focused grid at T=730 with 5 seeds to tighten g_c and the susceptibility estimate.
2. Add a third lattice size (L=256) for a real finite-size-scaling collapse.
3. Full κ (arrest) sweep in h = κ·M̄; map the (g,h) plane (dissuasion vs arrest).
4. Analytical χ_c: linear-stability of the homogeneous fixed point with the rescaling B→B·e^(−χM̄).
5. Structure-factor / hotspot-count order parameters alongside H.
