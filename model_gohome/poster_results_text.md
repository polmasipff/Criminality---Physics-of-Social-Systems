# PQP poster — Results, captions & Conclusions (with the production numbers)

Production run: L = 128, 15 seeds, T = 365, δ = 1/15. Inflow ΓL² ≈ 32.8 crimes/day.
Numbers below are stationary-tail means.

---

## RESULTS (poster text — concise)

**Police now reduce crime, and the population stays bounded.** As deterrence rises
(g = 0 → 3) the offender population grows but **saturates** (N: 68 → 320), instead of
the unbounded blow-up of the deterrence-only model (69 → ~980). Crucially, **total
crime falls** (28.0 → 11.4 crimes/day) because the new exit opens: home-returns rise
(4.5 → 21.4/day) and overtake crime as the dominant exit near **g ≈ 1.2**
(frac_crime: 0.86 → 0.35; frac_home: 0.14 → 0.65). The two channels always sum to the
inflow ΓL², so the mass balance closes exactly.

**A spatial hotspot → diffuse transition.** Computed on the *perceived* field
Ã = A₀ + B e^{−χM}, every concentration measure collapses monotonically through a
transition region g ≈ 0.3–1.5 (midpoint g ≈ 0.7): the spikiness **H_Ã** falls
1.32 → 0.04, the hotspot area fraction **f_hot** 0.11 → 0.00, and **Gini(Ã)**
0.46 → 0.02. The snapshots (Fig 2) show sharp, isolated cores at g = 0 dissolving into a
near-uniform field by g = 3. Meanwhile **corr(Ã, M)** weakens from 0.89 to 0.39: as
deterrence smears the attractiveness landscape, police presence and perceived
attractiveness spatially **decouple**.

**The transition is imprinted on time.** The *global* inter-crime times stay
Poissonian at every g (CV ≈ 1.0). The signal lives at the **cell** level: the per-cell
inter-crime coefficient of variation falls **1.75 → 1.11 → 0.75** (g = 0, 1, 3) —
from bursty, clustered repeat-victimization (CV > 1) toward regular, memoryless firing
(CV ≤ 1). Model selection by AIC (Fig 7) agrees: per-cell gaps are best described by a
**truncated power-law** (heavy tail + exponential cutoff) at g = 0 and g = 1, and the
best fit **switches to a Weibull at g = 3**, where the attractiveness memory is erased.
The hotspot → diffuse change is therefore also a transition in the **temporal
organization of crime**, from self-exciting / heavy-tailed to near-Poisson.

---

## FIGURE CAPTIONS (drop-in, poster length)

**Fig 2 — Field snapshots across deterrence regimes.** Rows: dynamic attractiveness
B, conserved police field M, and perceived attractiveness Ã = A₀ + B e^{−χM}. Columns:
g = 0 (base), g = 1 (transition), g = 3 (post-transition). Sharp, isolated cores at
g = 0 dissolve into a near-uniform field by g = 3; M tracks realized crime. **QR →
full time-lapse GIFs.**

**Fig 3 — Stationary order parameters vs deterrence g = χM̄** (mean ± SEM, 15 seeds,
L = 128). Coefficient of variation H_Ã (top-left) and hotspot area fraction f_hot
(top-right) collapse through the transition region g ≈ 0.3–1.5; daily crimes fall while
home-return exits rise and cross near g ≈ 1.2, with the total exit flux pinned to the
inflow ΓL² (dotted, bottom-left); Gini(Ã) (bottom-right) confirms the loss of spatial
concentration.

**Fig 4 — Police–attractiveness overlap vs g.** corr(Ã, M) (solid) and corr(Ã, M)²
(dashed). Strong overlap (≈ 0.89) at low g weakens to ≈ 0.39 by g = 3: deterrence
smears the attractiveness landscape and decouples it from the police field.

**Fig 5 — Time evolution for several g** (mean ± SEM over seeds): active criminals
N(t) (top-left, bounded for every g), daily crimes (top-right), daily home-returns
(bottom-left), and the net criminal flux ΔN/day = inflow − crimes − home-exits
(bottom-right), positive during the transient and → 0 at steady state.

**Fig 5b — As Fig 5 with a logarithmic time axis,** expanding the early transient in
which the population equilibrates (slower and larger for higher g).

**Fig 6 — CCDF of inter-crime waiting times for several g:** globally (left) and
per-cell (right). Global gaps stay near-exponential (CV ≈ 1) at all g; per-cell gaps
are heavy-tailed and bursty at small g and shorten and regularize as g rises.

**Fig 7 — Per-cell inter-crime CCDF vs candidate laws** (MLE, ranked by AIC;
exponential, Weibull, lognormal, power-law, truncated power-law). A **truncated
power-law** (heavy tail with exponential cutoff) best describes the bursty
repeat-victimization at low g; at high g the best fit **switches to a Weibull** as the
attractiveness memory is erased and the timing becomes near-Poissonian.

---

## CONCLUSIONS (poster text)

- A **conserved police field plus a non-criminal exit** cures the deterrence-only
  pathology: the offender population stays **bounded** and total crime becomes a real
  response variable that police can **reduce** (28 → 11 crimes/day).
- Increasing deterrence g drives a **continuous hotspot → diffuse crossover** in the
  perceived attractiveness Ã (H_Ã, f_hot, Gini all collapse through g ≈ 0.7), while
  police and crime spatially **decouple** (corr(Ã, M): 0.89 → 0.39).
- The transition is written in **time** as well as space: per-cell repeat-victimization
  goes from **bursty / heavy-tailed** (truncated power-law, CV > 1) to **regular /
  light-tailed** (Weibull, CV ≤ 1), while global crime timing stays Poissonian.
- **Outlook:** a single system size — finite-size scaling (L = 64/128/256) would settle
  crossover vs genuine transition; and a likelihood-ratio (Vuong) test would sharpen the
  truncated-power-law vs lognormal call at small g.

---

### Quick reference — numbers behind the text

| g | H_Ã | f_hot | Gini(Ã) | corr(Ã,M) | N | crimes/d | home/d | frac_crime | per-cell CV | best per-cell law |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 1.32 | 0.105 | 0.46 | 0.89 | 68 | 28.0 | 4.5 | 0.86 | 1.75 | trunc. power-law |
| 1.0 | 0.37 | 0.023 | 0.17 | 0.64 | 226 | 17.9 | 15.0 | 0.54 | 1.11 | trunc. power-law |
| 3.0 | 0.04 | 0.000 | 0.02 | 0.39 | 320 | 11.4 | 21.4 | 0.35 | 0.75 | Weibull |
