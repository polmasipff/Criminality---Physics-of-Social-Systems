"""engine_removal.py — police-extended Short et al. (2008) crime model with a
criminal *removal* channel implemented as COMPETING POISSON HAZARDS (Option C).

Each criminal at site s faces, per step dt, three independent hazards:

    lambda_crime(s)  = A_tilde_s = A0 + B_s e^{-chi M_s}   (commit a burglary)
    lambda_arrest(s) = kappa * M_s                         (removed by police)
    lambda_home      = delta                               (background return home)

    lambda_total = lambda_crime + lambda_arrest + lambda_home
    p_event      = 1 - exp(-lambda_total * dt)

If an event fires, its TYPE is drawn proportional to the rates:
    P(crime)  = lambda_crime  / lambda_total
    P(arrest) = lambda_arrest / lambda_total
    P(home)   = lambda_home   / lambda_total
crime  -> E_s += 1, criminal exits, B will rise by theta E_s (as in Short);
arrest -> criminal exits, NO B increase;
home   -> criminal exits, NO B increase.
If no event fires, the criminal MOVES by the usual A_tilde-biased rule.

Design guarantees
-----------------
* kappa == 0 and delta == 0  ->  BIT-IDENTICAL to engine.py (same RNG sequence:
  the single crime hazard reduces p_event to 1-exp(-A_tilde dt) and every event is
  a crime, so no extra random draw is consumed). The dissuasion-only physics and
  all previously published results are reproduced exactly.
* Option A (background return only): kappa = 0, delta > 0.
* Option B (police arrest only):     kappa > 0, delta = 0.
* Option C (both):                   kappa > 0, delta > 0.
* Competing hazards remove the arrest-before-crime ORDERING ARTIFACT of a
  sequential implementation: at O(dt) the event-type split is unbiased.

Mass balance (checked every step, asserted daily):
    N(t+dt) - N(t) = inflow - crimes - arrests - home_exits     (exact by construction)

Control parameters: g = chi * M_bar, h = kappa * M_bar, d = delta, M_bar = M_tot/L^2.
"""
import numpy as np
import pandas as pd


def neigh_avg(F):
    return (np.roll(F, 1, 0) + np.roll(F, -1, 0) +
            np.roll(F, 1, 1) + np.roll(F, -1, 1)) * 0.25


def gini(a):
    x = np.sort(a.ravel().astype(np.float64))
    n = x.size
    if x.sum() <= 0:
        return 0.0
    cum = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def spatial_entropy(field):
    f = field.ravel().astype(np.float64)
    s = f.sum()
    if s <= 0:
        return 0.0
    p = f / s
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def run_removal_sim(L=128, dt=1/100, T_max=365,
                    A0=1/30, omega=1/15, eta=0.03, theta=5.6, Gamma=0.002,
                    chi=0.0, M_tot=500.0, eta_M=0.1, omega_M=1/15,
                    kappa=0.0, delta=0.0,
                    seed=0, snapshot_days=None, init_state=None,
                    crime_accum_window=50, verbose=False):
    """Returns (daily_df, snaps_dict, final_state_dict).

    daily_df has one row per simulated day with field metrics AND the per-day
    removal accounting (crimes/arrests/home/inflow, balance_error, fractions,
    mean hazards). All counts are summed over the dt-steps within the day so the
    daily mass balance closes.
    """
    rng = np.random.default_rng(seed)
    B_bar = theta * Gamma / omega
    n_bar = Gamma * dt / (1 - np.exp(-(A0 + B_bar) * dt))
    M_bar = M_tot / (L * L)
    g = chi * M_bar
    h = kappa * M_bar
    only_crime = (kappa == 0.0 and delta == 0.0)   # fast path == engine.py
    snapshot_days = set(snapshot_days or [])

    if init_state is not None:
        B = init_state["B"].copy(); M = init_state["M"].copy()
        x = init_state["x"].copy(); y = init_state["y"].copy()
    else:
        B = np.full((L, L), B_bar, np.float64)
        M = np.full((L, L), M_bar, np.float64)
        n0 = rng.poisson(n_bar * L * L)
        x = rng.integers(0, L, n0, dtype=np.int64)
        y = rng.integers(0, L, n0, dtype=np.int64)

    n_steps = int(round(T_max / dt))
    steps_per_day = int(round(1 / dt))
    rows, snaps = [], {}
    crime_hist = []
    crime_accum = np.zeros((L, L), np.float64)

    # per-day accumulators (reset each day)
    day_crimes = day_arrests = day_home = day_inflow = 0
    sum_p_crime = sum_p_arrest = 0.0   # criminal-weighted, summed over steps
    sum_w = 0                          # number of (criminal*step) samples
    n_day_start = len(x)

    for step in range(1, n_steps + 1):
        deter = np.exp(-chi * M)
        A_tilde = A0 + B * deter
        nx = len(x)
        E = np.zeros((L, L), np.float64)

        if nx > 0:
            lam_c = A_tilde[x, y]
            if only_crime:
                p_event = 1.0 - np.exp(-lam_c * dt)         # == p_crime
                event = rng.random(nx) < p_event            # SAME draw as engine.py
                is_crime = event
                is_arrest = np.zeros(nx, dtype=bool)
                is_home = np.zeros(nx, dtype=bool)
                p_crime_mean = float(p_event.mean())
                p_arrest_mean = 0.0
            else:
                lam_a = kappa * M[x, y]
                lam_h = delta
                lam_t = lam_c + lam_a + lam_h
                p_event = 1.0 - np.exp(-lam_t * dt)
                event = rng.random(nx) < p_event
                # type assignment proportional to the rates
                u = rng.random(nx)
                frac_c = lam_c / lam_t
                frac_a = lam_a / lam_t
                is_crime = event & (u < frac_c)
                is_arrest = event & (u >= frac_c) & (u < frac_c + frac_a)
                is_home = event & ~(is_crime | is_arrest)
                # report the marginal per-step probabilities of each channel
                p_crime_mean = float((1.0 - np.exp(-lam_c * dt)).mean())
                p_arrest_mean = float((1.0 - np.exp(-lam_a * dt)).mean())

            if is_crime.any():
                np.add.at(E, (x[is_crime], y[is_crime]), 1.0)
            day_crimes += int(is_crime.sum())
            day_arrests += int(is_arrest.sum())
            day_home += int(is_home.sum())
            sum_p_crime += p_crime_mean * nx
            sum_p_arrest += p_arrest_mean * nx
            sum_w += nx

            # survivors = no event
            keep = ~event
            x = x[keep]; y = y[keep]

        # biased movement of survivors (identical rule to engine.py)
        if len(x) > 0:
            xu = (x - 1) % L; xd = (x + 1) % L
            yl = (y - 1) % L; yr = (y + 1) % L
            w = np.vstack([A_tilde[xu, y], A_tilde[xd, y],
                           A_tilde[x, yl], A_tilde[x, yr]]).T
            probs = w / w.sum(1, keepdims=True)
            cum = np.cumsum(probs, 1)
            u = rng.random(len(x))
            ch = (u[:, None] > cum).sum(1)
            xn = x.copy(); yn = y.copy()
            m = ch == 0; xn[m] = xu[m]
            m = ch == 1; xn[m] = xd[m]
            m = ch == 2; yn[m] = yl[m]
            m = ch == 3; yn[m] = yr[m]
            x, y = xn, yn

        # inflow (same as engine.py)
        n_new = rng.poisson(Gamma * dt * L * L)
        if n_new > 0:
            x = np.concatenate([x, rng.integers(0, L, n_new, dtype=np.int64)])
            y = np.concatenate([y, rng.integers(0, L, n_new, dtype=np.int64)])
        day_inflow += int(n_new)

        # field updates (B exactly as Short; M conserved exactly)
        B = ((1 - eta) * B + eta * neigh_avg(B)) * (1 - omega * dt) + theta * E
        Esum = E.sum()
        M_diff = (1 - eta_M) * M + eta_M * neigh_avg(M)
        if Esum > 0:
            M = (1 - omega_M * dt) * M_diff + omega_M * dt * M_tot * (E / Esum)
        else:
            M = M_diff

        if step % steps_per_day == 0:
            day = step // steps_per_day
            crime_hist.append(E.copy())
            if len(crime_hist) > crime_accum_window:
                crime_hist.pop(0)
            crime_accum = np.sum(crime_hist, axis=0)

            n_end = len(x)
            removals = day_crimes + day_arrests + day_home
            balance_error = (n_end - n_day_start) - (day_inflow - removals)
            tot_rem = max(removals, 1)
            Bm = B.mean()
            flat_M = M.ravel()
            Mtot_now = flat_M.sum()
            thr10 = np.percentile(B.ravel(), 90)
            hot10 = B >= thr10
            rec = dict(
                day=day, L=L, seed=seed,
                chi=chi, kappa=kappa, delta=delta,
                g=g, h=h, M_tot=M_tot, eta_M=eta_M, omega_M=omega_M,
                # --- removal accounting (per day) ---
                n_criminals=int(n_end),
                crimes_that_day=int(day_crimes),
                arrests_that_day=int(day_arrests),
                home_exits_that_day=int(day_home),
                inflow_that_day=int(day_inflow),
                balance_error=int(balance_error),
                frac_removed_crime=day_crimes / tot_rem,
                frac_removed_arrest=day_arrests / tot_rem,
                frac_removed_home=day_home / tot_rem,
                mean_p_crime=sum_p_crime / sum_w if sum_w else 0.0,
                mean_p_arrest=sum_p_arrest / sum_w if sum_w else 0.0,
                # --- field / hotspot metrics ---
                B_mean=float(Bm),
                B_std=float(B.std()),
                H=float(B.std() / Bm) if Bm > 0 else 0.0,
                f_hot_2=float((B >= 2 * Bm).mean()),
                f_hot_3=float((B >= 3 * Bm).mean()),
                Atilde_mean=float(A_tilde.mean()),
                deterrence_mean=float(np.exp(-chi * M).mean()),
                deterrence_hot=float(np.exp(-chi * M)[hot10].mean()),
                M_cv=float(flat_M.std() / flat_M.mean()) if flat_M.mean() > 0 else 0.0,
                MB_corr=float(np.corrcoef(B.ravel(), flat_M)[0, 1]) if flat_M.std() > 0 else 0.0,
                M_mass_on_hot10=float(M[hot10].sum() / Mtot_now) if Mtot_now > 0 else 0.0,
                crime_entropy=spatial_entropy(crime_accum if crime_accum.sum() > 0 else E),
                Gini_B=gini(B), Gini_M=gini(M),
            )
            rows.append(rec)
            assert balance_error == 0, f"mass balance broken on day {day}: {balance_error}"
            assert n_end >= 0, "negative criminals"

            if day in snapshot_days:
                snaps[day] = dict(B=B.copy(), M=M.copy(), A_tilde=A_tilde.copy(),
                                  deter=np.exp(-chi * M).copy(),
                                  crime_accum=crime_accum.copy(), n_criminals=n_end)
            if verbose and day % 30 == 0:
                print(f"  day {day:4d} g={g:5.2f} h={h:5.2f} d={delta:4.2f} "
                      f"H={rec['H']:.3f} ncrim={n_end:5d} "
                      f"cr/ar/hm={day_crimes}/{day_arrests}/{day_home} "
                      f"Msum={M.sum():.4f}")

            # reset per-day accumulators
            day_crimes = day_arrests = day_home = day_inflow = 0
            sum_p_crime = sum_p_arrest = 0.0
            sum_w = 0
            n_day_start = n_end

        if step % (steps_per_day * 30) == 0:
            assert abs(M.sum() - M_tot) < 1e-6 * max(1, M_tot), "M not conserved"
            assert np.isfinite(B).all() and np.isfinite(M).all(), "NaN/inf in fields"
            assert (B >= -1e-9).all(), "B negative"
            assert (A_tilde >= A0 - 1e-9).all(), "A_tilde < A0"

    df = pd.DataFrame(rows)
    return df, snaps, dict(B=B, M=M, x=x, y=y)


def summarize(df, frac_window=0.5):
    """Average the stationary tail. Default: last half of the run."""
    if len(df) == 0:
        return {}
    T = int(df.day.max())
    if T >= 730:
        lo, hi = 365, 730
    elif T >= 365:
        lo, hi = 185, 365
    else:
        lo, hi = int(T * frac_window), T
    sub = df[(df.day > lo) & (df.day <= hi)]
    if len(sub) == 0:
        sub = df
    s = sub.select_dtypes(include=[np.number]).mean().to_dict()
    s["stat_window"] = f"{lo}-{hi}"
    return s
