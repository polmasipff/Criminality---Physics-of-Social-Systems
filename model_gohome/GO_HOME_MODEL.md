# The `go_home` model — full specification

*Short et al. (2008) crime-hotspot model, extended with a conserved police field `M`
and a single criminal-removal channel: the background "return-home" exit. This is the
authoritative description of the model implemented in `engine_return_home.py`: the
fields, the equations, the exact order of operations inside the time-step loop, the
conservation/balance guarantees, and the scientific reading of the results.*

There is **no arrest, no `κ`, no `h`, no Options B/C**. The only way a criminal leaves
the system without committing a crime is by returning home.

---

## 1. State variables

The model lives on an `L×L` periodic lattice with time step `dt`. There are three
lattice fields and one particle population.

| Symbol | Type | Meaning |
|---|---|---|
| `B_s(t)` | lattice field ≥ 0 | **dynamic attractiveness** (repeat-victimization memory): how attractive site `s` is *because of recent crime*. |
| `M_s(t)` | lattice field ≥ 0 | **police field**: a conserved density of police attention, `Σ_s M_s = M_tot` exactly. |
| `Ã_s(t)` | derived field | **effective (perceived) attractiveness** the criminal actually responds to. |
| `E_s(t)` | lattice field ∈ ℤ≥0 | **realized crimes** at site `s` during the step. |
| criminals | particle set | discrete agents with a position `(x,y)`, an id, and an entry time. |

The effective attractiveness couples `B` and `M` through an exponential deterrence:

$$\tilde A_s = A_0 + B_s\, e^{-\chi M_s}.$$

- `A_0` is the **intrinsic** attractiveness floor (wealth, accessibility). It carries no
  `M`, so **police cannot patrol it away**: deterrence returns crime to `A_0`, never to 0.
- `B_s\,e^{-\chi M_s}` is the **dynamic** part, suppressed multiplicatively by local police
  presence. `e^{-\chi M_s}\in(0,1]` is the **deterrence factor**.

Because `Ã` contains the suppression `e^{-\chi M}` and `B` does not, **`Ã` is the field
that shows the police effect**, and all structural order parameters in this pipeline are
computed on `Ã` (see §7).

---

## 2. Parameters

| Symbol | Code | Default | Meaning |
|---|---|---|---|
| `dt` | `dt` | `1/100` | time step (days) |
| `A_0` | `A0` | `1/30` | intrinsic attractiveness floor |
| `ω` | `omega` | `1/15` | `B` decay rate (≈15-day memory) |
| `η` | `eta` | `0.03` | `B` diffusion weight |
| `θ` | `theta` | `5.6` | `B` deposit per crime |
| `Γ` | `Gamma` | `0.002` | criminal inflow per site per unit time |
| `χ` | `chi` | swept | deterrence strength |
| `M_tot` | `M_tot` | `500` | police budget (conserved sum of `M`) |
| `η_M` | `eta_M` | `0.1` | `M` diffusion weight (patrol) |
| `ω_M` | `omega_M` | `1/15` | `M` redeployment rate toward observed crime |
| `δ` | `delta` | `ω = 1/15` | **return-home rate** (the only removal channel) |

The base parameters reproduce Short et al. Fig. 3(d) (the dynamic-hotspot regime).

### Control parameter

`χ` never acts alone; it always appears as `χM`. With `M` conserved, its spatial mean is
fixed at `\bar M = M_{tot}/L^2`, so the natural dimensionless control parameter is

$$g \equiv \chi\,\bar M = \chi\,\frac{M_{tot}}{L^2},\qquad\text{equivalently}\qquad \chi = \frac{g\,L^2}{M_{tot}}.$$

Two systems with the same `g` but different `(χ, M_tot, L)` sit at the same point on the
deterrence axis; this is why every figure is organized by `g`, not by `χ`.

---

## 3. Governing equations

Per criminal at site `s`, per step:

$$p_{\text{crime}}(s) = 1 - e^{-\tilde A_s\, dt}\quad(\text{commit a burglary}),$$
$$p_{\text{home}} = 1 - e^{-\delta\, dt}\quad(\text{return home, no crime}),$$
$$q_{s\to s'} \propto \tilde A_{s'}\quad(\text{biased nearest-neighbour movement}).$$

Field updates (identical to Short for `B`; mass-preserving for `M`):

$$B_s(t+dt) = \Big[(1-\eta)B_s + \tfrac{\eta}{z}\textstyle\sum_{\langle s'\rangle} B_{s'}\Big](1-\omega\,dt) + \theta\,E_s,$$

$$M_s(t+dt) = (1-\omega_M dt)\Big[(1-\eta_M)M_s + \tfrac{\eta_M}{z}\textstyle\sum_{\langle s'\rangle} M_{s'}\Big] + \omega_M\,dt\,M_{tot}\,\frac{E_s}{\sum_r E_r},$$

with `z = 4` neighbours. The `M` diffusion is a convex combination (mass-preserving on a
periodic lattice) and the reallocation term sums to `M_tot`, so `Σ_s M_s = M_tot` is
exact at every step. Inflow: each step, `Poisson(Γ\,dt\,L^2)` new criminals appear at
uniformly random sites.

---

## 4. Order of operations in the time-step loop

This is the precise sequence executed every step `dt` in `run_return_home_sim`. The
ordering is **sequential, crime-first**, exactly as specified for the model.

> **Step 0 — perceived field.** Compute the deterrence factor `D = e^{-χM}` and the
> effective attractiveness `Ã = A_0 + B·D` from the *current* `B`, `M`.

> **Step 1 — crime check (for every criminal at its current site `s`).**
> Draw `u₁ ~ U(0,1)`. If `u₁ < p_crime(s) = 1 − e^{−Ã_s dt}`:
> record a crime → `E_s += 1`, log a `crime` event, and the criminal **exits**.
> (Its `B` contribution enters via `θ E_s` in the field update below.)

> **Step 2 — return-home check (only for criminals that did NOT commit a crime).**
> If `δ > 0`, draw `u₂ ~ U(0,1)`. If `u₂ < p_home = 1 − e^{−δ dt}`:
> log a `home_exit` event and the criminal **exits**. **No `B` increase.**
> (If `δ = 0` this draw is skipped entirely, which is what makes `δ=0` reproduce the
> dissuasion-only model bit-for-bit — see §6.)

> **Step 3 — movement (survivors of Steps 1–2).**
> Move each surviving criminal to a nearest neighbour chosen with probability
> `q_{s→s'} ∝ Ã_{s'}` (the same `Ã` from Step 0).

> **Step 4 — inflow.** Add `Poisson(Γ\,dt\,L²)` new criminals at uniformly random
> sites; assign each a fresh id and entry time.

> **Step 5 — field updates.** Update `B` (Short rule, including `+θE`) and `M`
> (conserved rule using the crime pattern `E/ΣE`).

> **Step 6 — daily bookkeeping (once per `1/dt` steps = one day).**
> Accumulate the day's counts (`crimes`, `home_exits`, `inflow`), check the mass
> balance (§5), recompute `Ã` from the post-update `B`, `M`, and record the order
> parameters on `Ã` (§7), the field/police metrics, and optionally a snapshot/movie
> frame. Then reset the per-day accumulators.

Crucial consequences of this ordering:
- A criminal can do **at most one** thing per step (crime *or* home *or* move).
- Crime is checked before home; at `dt = 1/100` (per-step probabilities ~1%) this
  "crime-first" priority biases the crime/home split only at `O(dt^2)` and is
  physically negligible. (`engine_return_home.py` also offers `event_order="competing"`,
  which draws the exit type ∝ rates with no ordering bias, as a robustness option.)
- `B` rises **only** from crimes; home exits deposit nothing — that is the whole point.

---

## 5. Criminal mass balance (why `N` stays bounded)

Let `N(t)` be the number of active criminals. By construction of the loop,

$$\Delta N = N(t+dt) - N(t) = \text{inflow} - \text{crimes} - \text{home\_exits}.$$

The engine stores, per day,

$$\texttt{balance\_error} = \Delta N - (\text{inflow} - \text{crimes} - \text{home\_exits}),$$

and **asserts it is exactly 0** every day (bookkeeping closes by construction).

**Why this fixes the dissuasion-only pathology.** In the original model a criminal can
leave *only* by committing a crime, so in steady state `⟨crimes⟩ = inflow = Γ L²`,
independent of `χ`: total crime is pinned to the inflow and the population must inflate as
deterrence lowers `⟨Ã⟩`, `N ≈ Γ L² / ⟨Ã⟩` (the blow-up, `N: 69→~980` in the baseline).
The return-home channel adds a second sink:

$$\text{inflow} = \text{crimes} + \text{home\_exits},$$

so (i) each criminal has a finite expected residence `≤ 1/δ` and `N` stays bounded for any
`χ`, and (ii) `crimes = inflow − home_exits` is no longer pinned to the inflow, so **total
crime can actually fall** as `g` rises and the home channel takes a larger share of exits.

We set `δ = ω = 1/15`: tying the residence time to the existing memory timescale adds no
new free parameter, matches the Jones–Brantingham–Chayes (2010) background-return choice,
and was empirically sufficient (it bounds `N` while leaving the regime change intact).

`M` conservation is checked independently: `|Σ_s M_s − M_tot| < 10^{-6} M_tot` (measured
deviation ~`10^{-11}`).

---

## 6. Exact limits (sanity anchors)

- **`δ = 0` ⇒ dissuasion-only, bit-for-bit.** With `δ=0` the home draw in Step 2 is
  skipped, so the RNG stream is identical to the crime-only engine; final `B`, `M`, and
  criminal positions match exactly. Previously published dissuasion-only results are
  reproduced exactly, not "within noise".
- **`χ = 0` ⇒ no deterrence.** `e^{-χM} = 1` everywhere, so `Ã = A_0 + B`; the police
  field does not affect attractiveness at all.
- Guards asserted throughout: no negative criminals, no NaN/inf, `B ≥ 0`, `Ã ≥ A_0`.

These are checked in `tests/test_engine_return_home.py` (23 checks, 0 failures).

---

## 7. Why order parameters are computed on `Ã`, not `B`

`B` is the latent memory and does **not** contain the suppression `e^{-χM}`; two runs
with very different police strength can have similar `B` statistics while their *perceived*
landscapes differ enormously. The field criminals respond to — and the one that reveals
the police effect — is `Ã = A_0 + B e^{-χM}`. Therefore the structural order parameters
plotted by `plot_order_parameters.py` are computed on `Ã`:

- `H_{\tilde A} = \sigma_{\tilde A}/\langle\tilde A\rangle` — coefficient of variation
  (spiky hotspots vs uniform).
- `f_{hot} = P(\tilde A \ge 2\langle\tilde A\rangle)` and `\ge 3\langle\tilde A\rangle` —
  hotspot area fraction.
- `\tilde A_{90,95,99}/\langle\tilde A\rangle` — tail sharpness; `\mathrm{Gini}(\tilde A)`.
- `\mathrm{corr}(\tilde A, M)`, `M`-mass on the top-10% `Ã` cells, deterrence on those
  cells — police–attractiveness overlap.

The `B`-based columns remain in `summary.csv` for reference but are not the headline.
(Caveat: once the home channel makes crime sparse, any single concentration index can be
noisy; read `H_{\tilde A}` together with `f_{hot}`, `Gini`, `N`, and crimes/day.)

---

## 8. Event logging and observables

With `output.save_event_logs: true`, every `crime` and `home_exit` is logged with
`(type, day, x, y, criminal_id, entry_day, residence)`. This supports:

- **Residence times** split by exit type (`entry→crime` vs `entry→home`).
- **Global inter-crime waiting times** (gaps between consecutive crimes anywhere).
- **Per-cell inter-crime waiting times** (gaps between crimes on the same cell) — the
  repeat/near-repeat victimization clock. Cells must have `≥ min_crimes` crimes to
  contribute; the threshold is **per-`g`**: large `g` (≥2) uses `1` (see §9).

`analyze_waiting_times.py` fits each distribution by MLE on the whole sample and compares
exponential, Weibull (= stretched exponential), lognormal, power-law and truncated
power-law by AIC and KS.

---

## 9. Temporal structure: the truncated power-law and its mechanism

Empirically (events scan, `g∈{0,1,3}`):

- **Global inter-crime gaps are light-tailed (≈ exponential / Weibull).** Aggregating
  many weakly-dependent cells gives an approximately Poisson superposition
  (Palm–Khinchin), so the *global* gaps are exponential; their timescale lengthens with
  `g` because the home channel slows total crime.
- **Per-cell inter-crime gaps are heavy-tailed and best fit by a truncated power-law**
  (power-law body with an exponential cutoff), with the lognormal close behind and a pure
  exponential clearly rejected.

**Mechanism (a self-exciting / preferential-attachment reading).** A crime deposits `θ`
into `B` at that site, which raises `Ã` there, which makes the next crime *more likely and
sooner* — a rich-get-richer feedback (Hawkes-like self-excitation). Sites that are already
active attract disproportionately more crime, while low-activity sites have essentially no
memory. This positive feedback over a heterogeneous set of sites generates an
approximately scale-free body in the per-cell inter-event times — i.e. the power-law part.

**Why it is *truncated* (the cutoff).** The memory is not permanent: `B` decays at rate
`ω`, so a site stays "hot" only for `~1/ω ≈ 15` days, and the finite run length `T`
censors the longest gaps. Both impose an exponential cutoff on the heavy tail — hence a
**truncated** power-law rather than a pure one.

**Why `g=3` should look exponential.** At strong deterrence the dynamic part collapses,
`B e^{-χM}\to 0`, so `Ã \to A_0` becomes nearly uniform and **memoryless**: the
preferential-attachment feedback is switched off, every cell fires at the same low
intrinsic rate, and the per-cell inter-event times revert to a **Poisson/exponential**
law. To test this we drop the per-cell threshold to `min_crimes = 1` for `g≥2` (otherwise
no cell qualifies at `g=3`) and fit the exponential explicitly. Confirming an exponential
at `g=3` versus a truncated power-law at small `g` is direct evidence that the
hotspot→diffuse transition is also a **transition in the temporal organization of crime**:
from bursty, memory-driven repeat victimization to memoryless Poisson activity.

This is a hypothesis the pipeline is built to test, not a proven claim; the AIC/KS tables
in `waiting_times_fits.csv` are the evidence.

---

## 10. Numerical notes

- Time integration is explicit Euler with `dt = 1/100`; per-step event probabilities use
  the exact `1 - e^{-\lambda dt}` (not `\lambda dt`).
- The RNG draw order is fixed (crime uniform of size `N`, then the home uniform only when
  `δ>0`, then movement uniforms, then inflow Poisson) to guarantee the `δ=0` bit-identity.
- All raw outputs are append-only and keyed by `(L, seed, g, δ, M_tot, η_M, T_max)`; the
  engine MD5 is recorded per run for staleness detection.

---

## 11. References

Short, D'Orsogna, Pasour, Tita, Brantingham, Bertozzi & Chayes, *A statistical model of
criminal behavior*, M³AS 18 (2008) — base model. Jones, Brantingham & Chayes, M³AS 20
(2010) — police, deterrence, the background return rate `δ`. Short, Brantingham, Bertozzi
& Tita, PNAS 107 (2010) — suppression vs displacement. Zipkin, Short & Bertozzi, DCDS-B 19
(2014). Jusup et al., Phys. Rep. 948 (2022), §8.2 — review. Clauset, Shalizi & Newman,
*Power-law distributions in empirical data*, SIAM Rev. 51 (2009) — the fitting methodology.
