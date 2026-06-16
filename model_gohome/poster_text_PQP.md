# PQP poster — draft texts (scientific English)

Poster layout: 3 columns, structured as **Introduction · Methodology · Results ·
Conclusions**. The blocks below cover the Introduction, the Methodology, and the
inter-event-time / AIC paragraph. The PQP model is a police-extended version of the
Short et al. (2008) crime-hotspot model.

---

## Introduction

Urban crime is not spread uniformly: it concentrates into persistent **hotspots** in
space and clusters in time, a regularity captured by the empirical laws of **repeat and
near-repeat victimization** — once a site is hit, it and its neighbours are at elevated
risk for a short period. The statistical model of Short et al. (2008) reproduces this
behaviour from simple microscopic rules: a dynamic **attractiveness field** `B` encodes
the memory of recent crime, offenders move as biased random walkers that drift toward
more attractive sites, and every burglary deposits attractiveness back into the field.
This positive feedback spontaneously organizes mobile, finite-lifetime hotspots that
match observed crime maps.

A central open question is what a finite, mobile **police** resource does to this
self-organized state. Intuitively, police presence should suppress crime; but in a
deterrence-only coupling, where police merely lower the *perceived* attractiveness, the
model only **rearranges** crime in space without reducing its total amount, and — because
offenders can leave the system *only* by committing a crime — the offender population
grows without bound, a structural mass-balance pathology. The **PQP model** removes both
limitations: it represents police as a **conserved field** that deters crime, and it adds
a genuine non-criminal exit (offenders may simply **return home**). With these
ingredients the offender population stays bounded, total crime becomes a meaningful
response variable, and we can ask the physical question of interest: as deterrence
increases, does the system undergo a **hotspot-to-diffuse transition**, and how is that
transition imprinted on the spatial *and temporal* structure of crime?

---

## Methodology

**The PQP model.** On an `L×L` periodic lattice we evolve two fields: the dynamic
attractiveness `B` (the Short repeat-victimization memory) and a **conserved police
field** `M` with `Σ_s M_s = M_tot` fixed at all times. Offenders perceive the
**effective attractiveness**

$$\tilde A_s = A_0 + B_s\, e^{-\chi M_s},$$

where `A_0` is an intrinsic floor that police cannot patrol away and `e^{-\chi M_s}` is a
multiplicative deterrence factor. Both the probability of offending,
`p_crime = 1 − e^{−Ã dt}`, and the movement bias, `q_{s→s'} ∝ Ã_{s'}`, are governed by
`Ã`: police therefore act twice over, lowering the chance of a crime *and* steering
offenders away from well-policed cells.

**Exit mechanisms.** An offender leaves the system through one of two channels: by
**committing a crime** (which deposits `θ` into `B`, reinforcing the local hotspot) or by
**returning home** at a background rate `δ` (no deposit, no crime). These two channels
close the offender mass budget, `ΔN = inflow − crimes − home-exits`, and the **fraction
of exits carried by each channel** is itself a diagnostic of the regime: deterrence
shifts exits from crime toward home return.

**Order parameters (on `Ã`).** We quantify spatial organization with two scalars
computed on the perceived field `Ã` — the field offenders actually respond to and the
only one that carries the police suppression:
the **hotspot area fraction**
`f_hot = (1/L²) Σ_s 1[Ã_s ≥ 2⟨Ã⟩]`, i.e. the share of the lattice covered by hotspots,
and the **coefficient of variation**
`H = σ_{Ã}/⟨Ã⟩`, which is large for a spiky, concentrated field and small for a uniform,
diffuse one. Together they distinguish a hotspot state (high `H`, sizeable `f_hot`) from a
diffuse state (low `H`, small `f_hot`).

**Control parameter and transition region.** Deterrence enters only through the product
`χM`, whose spatial mean is fixed by conservation at `M̄ = M_tot/L²`. The natural
dimensionless control parameter is therefore

$$g \equiv \chi\,\bar M = \chi\,\frac{M_{tot}}{L^2},$$

and all observables are organized by `g` rather than by `χ`. As `g` increases through
order unity, `f_hot` and `H` fall and the crime field reorganizes from sharp, isolated
cores into a near-uniform field: a **hotspot-to-diffuse regime change**. We define the
**transition region** as the band of `g` over which the order parameters cross over
between their two plateaus.

---

## Inter-event times and model selection (AIC)

From the event log of individual crimes we extract **inter-event (waiting) times**: the
*global* inter-crime gaps (times between consecutive crimes anywhere on the lattice) and
the *per-cell* inter-crime gaps (times between successive crimes at the **same site**),
the latter being the repeat/near-repeat victimization clock; every cell with at least one
crime contributes. We also record **residence times** (entry-to-exit), separated by exit
channel. For each quantity we estimate the empirical **complementary cumulative
distribution** (CCDF, `P(T>t)`) and fit five candidate laws by maximum likelihood —
**exponential, Weibull (stretched exponential), lognormal, power-law, and truncated
power-law** (a power-law with an exponential cutoff).

Because these distributions are not nested, we compare them with the **Akaike Information
Criterion**, `AIC = 2k − 2 ln L̂`, where `ln L̂` is the maximized log-likelihood of a fit
and `k` its number of free parameters. AIC rewards goodness of fit while penalizing model
complexity, so the law with the **lowest AIC is preferred** and AIC differences provide a
principled, fair ranking across the candidate distributions; we report the Kolmogorov–
Smirnov distance alongside as an independent check.

---

*(Results and Conclusions to be completed from the production runs: the order-parameter
curves vs `g`, the bounded offender population and exit-channel split, and the waiting-time
fits — expected to show light-tailed global gaps, a truncated power-law for per-cell gaps
at small `g`, and a crossover toward an exponential at large `g` as the attractiveness
memory is erased.)*
