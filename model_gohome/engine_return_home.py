"""engine_return_home.py — police-extended Short et al. (2008) crime hotspot model
with a single criminal-removal channel: the background **return-home** mechanism.

This is the CURRENT model. It deliberately contains NO arrest channel, NO kappa,
NO police-dependent removal hazard, and NO competing-hazard machinery. The only
way a criminal leaves the system *without committing a crime* is by returning home
with probability  p_home = 1 - exp(-delta*dt),  delta = omega = 1/15.

(The older `engine_removal.py` in this folder is OBSOLETE: it carried an arrest
hazard `kappa*M` and a competing-hazard event split. Keep it only as the historical
record that produced the old `runs/` data. New work uses THIS engine.)

Effective (perceived) attractiveness
------------------------------------
    A_tilde_s = A0 + B_s * exp(-chi * M_s)

Event logic per criminal at site s, each step dt  (SEQUENTIAL, crime-first):
    1. crime:  p_crime(s) = 1 - exp(-A_tilde_s * dt)
                 -> record crime at s, E_s += 1, criminal EXITS (B rises by theta*E).
    2. else home: p_home = 1 - exp(-delta * dt)
                 -> record home exit, criminal EXITS, NO B increase.
    3. else: criminal MOVES by the usual A_tilde-biased nearest-neighbour rule.

Design guarantees (all checked in tests/test_engine_return_home.py)
-------------------------------------------------------------------
* delta == 0  ->  BIT-IDENTICAL to the dissuasion-only model. With delta=0 the home
  branch never draws a random number, so the RNG stream is exactly that of the old
  crime-only engine (`engine_removal.py` with kappa=delta=0, itself bit-identical to
  the frozen `engine.py`). Previously published dissuasion-only results reproduce
  exactly, not "within noise".
* chi == 0   ->  exp(-chi*M) == 1 everywhere, so police presence does not affect
  attractiveness at all (A_tilde = A0 + B).
* M is conserved exactly: |sum(M) - M_tot| stays at machine precision.
* No NaN/inf; B >= 0; A_tilde >= A0.
* Daily criminal mass balance closes exactly, by construction:
      Delta N = inflow - crimes - home_exits
  and we save  balance_error = Delta N - (inflow - crimes - home_exits)  (== 0).

Control parameters
------------------
    M_bar = M_tot / L^2
    g     = chi * M_bar          (normalized deterrence; the main x-axis)
    delta                        (home-exit rate; already a rate, dimensionless * time)

Author note: `event_order` defaults to "sequential" (the model as specified). A
"competing" option is provided ONLY for robustness checks; it changes results by
O(dt^2) and is not the production setting.
"""
import numpy as np
import pandas as pd

# ---- base parameters (Short Fig. 3(d) regime), exposed as module defaults ----
DEFAULTS = dict(
    L=128, dt=1 / 100, T_max=365,
    A0=1 / 30, omega=1 / 15, eta=0.03, theta=5.6, Gamma=0.002,
    chi=0.0, M_tot=500.0, eta_M=0.1, omega_M=1 / 15,
    delta=1 / 15,
)


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


def run_return_home_sim(L=128, dt=1 / 100, T_max=365,
                        A0=1 / 30, omega=1 / 15, eta=0.03, theta=5.6, Gamma=0.002,
                        chi=0.0, M_tot=500.0, eta_M=0.1, omega_M=1 / 15,
                        delta=1 / 15,
                        seed=0, snapshot_days=None, init_state=None,
                        crime_accum_window=50, movie_every=None,
                        event_log=False, event_log_types=("crime", "home_exit"),
                        event_order="sequential", verbose=False):
    """Run one return-home simulation.

    Returns (daily_df, snaps_dict, final_state_dict, events_df).

    daily_df : one row per day, with field metrics AND per-day mass-balance
               accounting (crimes/home/inflow, balance_error, fractions, mean probs).
    snaps    : {day: dict(B, M, A_tilde, deter, crime_accum, n_criminals)} for days in
               snapshot_days.
    final_state : dict(B, M, x, y, cid, ent) — warm-start handle for --resume chaining.
    events_df : per-event log (empty if event_log=False). Columns:
               type, day, x, y, cid, entry_day, residence.  `type` in {crime, home_exit}.
               Supports residence-time-by-exit-type AND per-cell inter-crime waiting times.

    Parameters of note
    ------------------
    delta : home-exit rate. delta=0 -> dissuasion-only (bit-identical).
    movie_every : if an int, also collect downsampled (B, M, A_tilde, deter) frames
                  every `movie_every` days into final_state['movie'] for make_gifs
                  (avoids re-running the simulation just to animate). None = off.
    event_log : if True, append rows to events_df for the types in event_log_types.
    event_order : "sequential" (default, crime-first) or "competing" (robustness only).
    """
    if event_order not in ("sequential", "competing"):
        raise ValueError("event_order must be 'sequential' or 'competing'")
    rng = np.random.default_rng(seed)
    B_bar = theta * Gamma / omega
    n_bar = Gamma * dt / (1 - np.exp(-(A0 + B_bar) * dt))
    M_bar = M_tot / (L * L)
    g = chi * M_bar
    snapshot_days = set(snapshot_days or [])
    log_crime = event_log and ("crime" in event_log_types)
    log_home = event_log and ("home_exit" in event_log_types)

    if init_state is not None:
        B = init_state["B"].copy(); M = init_state["M"].copy()
        x = init_state["x"].copy(); y = init_state["y"].copy()
        cid = init_state.get("cid")
        ent = init_state.get("ent")
        next_id = int(init_state.get("next_id", len(x)))
        if cid is None:
            cid = np.arange(len(x), dtype=np.int64); next_id = len(x)
        else:
            cid = cid.copy()
        ent = (np.zeros(len(x)) if ent is None else ent.copy())
    else:
        B = np.full((L, L), B_bar, np.float64)
        M = np.full((L, L), M_bar, np.float64)
        n0 = rng.poisson(n_bar * L * L)
        x = rng.integers(0, L, n0, dtype=np.int64)
        y = rng.integers(0, L, n0, dtype=np.int64)
        cid = np.arange(n0, dtype=np.int64)
        ent = np.zeros(n0, dtype=np.float64)
        next_id = n0

    n_steps = int(round(T_max / dt))
    steps_per_day = int(round(1 / dt))
    rows, snaps, ev_rows = [], {}, []
    crime_hist = []
    crime_accum = np.zeros((L, L), np.float64)
    movie_frames = [] if movie_every else None
    movie_days = [] if movie_every else None

    # per-day accumulators (reset each day)
    day_crimes = day_home = day_inflow = 0
    sum_p_crime = sum_p_home = 0.0   # criminal-weighted, summed over steps
    sum_w = 0
    n_day_start = len(x)

    for step in range(1, n_steps + 1):
        t_now = step * dt                    # continuous time in days
        deter = np.exp(-chi * M)
        A_tilde = A0 + B * deter
        nx = len(x)
        E = np.zeros((L, L), np.float64)

        if nx > 0:
            lam_c = A_tilde[x, y]
            p_crime = 1.0 - np.exp(-lam_c * dt)
            p_home_scalar = 1.0 - np.exp(-delta * dt)

            if event_order == "sequential":
                # ---- step 1: crime (single draw of size nx == old engine) ----
                u_crime = rng.random(nx)
                is_crime = u_crime < p_crime
                # ---- step 2: home, only for crime survivors, only if delta>0 ----
                is_home = np.zeros(nx, dtype=bool)
                if delta > 0.0:
                    surv = ~is_crime
                    ns = int(surv.sum())
                    if ns > 0:
                        u_home = rng.random(ns)
                        home_among = u_home < p_home_scalar
                        idx_surv = np.flatnonzero(surv)
                        is_home[idx_surv[home_among]] = True
            else:  # competing hazards (robustness only)
                lam_h = delta
                lam_t = lam_c + lam_h
                p_event = 1.0 - np.exp(-lam_t * dt)
                fired = rng.random(nx) < p_event
                if delta > 0.0:
                    u = rng.random(nx)
                    frac_c = lam_c / lam_t
                    is_crime = fired & (u < frac_c)
                    is_home = fired & ~is_crime
                else:
                    is_crime = fired
                    is_home = np.zeros(nx, dtype=bool)

            # record crime field + per-day counts
            if is_crime.any():
                np.add.at(E, (x[is_crime], y[is_crime]), 1.0)
            day_crimes += int(is_crime.sum())
            day_home += int(is_home.sum())
            sum_p_crime += float(p_crime.mean()) * nx
            sum_p_home += float(p_home_scalar) * nx
            sum_w += nx

            # event logging (before removing exited criminals)
            if log_crime and is_crime.any():
                ii = np.flatnonzero(is_crime)
                for j in ii:
                    ev_rows.append(("crime", t_now, int(x[j]), int(y[j]),
                                    int(cid[j]), float(ent[j]), float(t_now - ent[j])))
            if log_home and is_home.any():
                ii = np.flatnonzero(is_home)
                for j in ii:
                    ev_rows.append(("home_exit", t_now, int(x[j]), int(y[j]),
                                    int(cid[j]), float(ent[j]), float(t_now - ent[j])))

            # survivors = neither crime nor home
            keep = ~(is_crime | is_home)
            x = x[keep]; y = y[keep]; cid = cid[keep]; ent = ent[keep]

        # biased movement of survivors (identical rule to the dissuasion-only engine)
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

        # inflow (same as dissuasion-only engine: Poisson(Gamma*dt*L^2))
        n_new = rng.poisson(Gamma * dt * L * L)
        if n_new > 0:
            x = np.concatenate([x, rng.integers(0, L, n_new, dtype=np.int64)])
            y = np.concatenate([y, rng.integers(0, L, n_new, dtype=np.int64)])
            cid = np.concatenate([cid, np.arange(next_id, next_id + n_new, dtype=np.int64)])
            ent = np.concatenate([ent, np.full(n_new, t_now, dtype=np.float64)])
            next_id += n_new
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
            removals = day_crimes + day_home
            balance_error = (n_end - n_day_start) - (day_inflow - removals)
            tot_rem = max(removals, 1)
            Bm = B.mean()
            flat_B = B.ravel()
            flat_M = M.ravel()
            Mtot_now = flat_M.sum()
            thr10 = np.percentile(flat_B, 90)
            hot10 = B >= thr10
            deterf = np.exp(-chi * M)
            A_tilde_now = A0 + B * deterf      # consistent with post-update B, M
            rec = dict(
                day=day, L=L, seed=seed,
                chi=chi, delta=delta, g=g, M_tot=M_tot, eta_M=eta_M, omega_M=omega_M,
                # --- mass-balance accounting (per day) ---
                n_criminals=int(n_end),
                crimes_that_day=int(day_crimes),
                home_exits_that_day=int(day_home),
                inflow_that_day=int(day_inflow),
                balance_error=int(balance_error),
                frac_exit_crime=day_crimes / tot_rem,
                frac_exit_home=day_home / tot_rem,
                mean_p_crime=sum_p_crime / sum_w if sum_w else 0.0,
                mean_p_home=sum_p_home / sum_w if sum_w else 0.0,
                # --- field / hotspot metrics ---
                B_mean=float(Bm),
                B_std=float(B.std()),
                H=float(B.std() / Bm) if Bm > 0 else 0.0,
                f_hot_2=float((B >= 2 * Bm).mean()),
                f_hot_3=float((B >= 3 * Bm).mean()),
                B_q90_over_mean=float(np.percentile(flat_B, 90) / Bm) if Bm > 0 else 0.0,
                B_q95_over_mean=float(np.percentile(flat_B, 95) / Bm) if Bm > 0 else 0.0,
                B_q99_over_mean=float(np.percentile(flat_B, 99) / Bm) if Bm > 0 else 0.0,
                Atilde_mean=float(A_tilde_now.mean()),
                deterrence_mean=float(deterf.mean()),
                deterrence_hot=float(deterf[hot10].mean()),
                M_cv=float(flat_M.std() / flat_M.mean()) if flat_M.mean() > 0 else 0.0,
                MB_corr=float(np.corrcoef(flat_B, flat_M)[0, 1]) if flat_M.std() > 0 else 0.0,
                M_mass_on_hot10=float(M[hot10].sum() / Mtot_now) if Mtot_now > 0 else 0.0,
                crime_entropy=spatial_entropy(crime_accum if crime_accum.sum() > 0 else E),
                Gini_B=gini(B), Gini_M=gini(M),
            )
            rows.append(rec)
            assert balance_error == 0, f"mass balance broken on day {day}: {balance_error}"
            assert n_end >= 0, "negative criminals"

            if day in snapshot_days:
                snaps[day] = dict(B=B.copy(), M=M.copy(), A_tilde=A_tilde_now.copy(),
                                  deter=deterf.copy(),
                                  crime_accum=crime_accum.copy(), n_criminals=n_end)
            if movie_every and (day % movie_every == 0):
                movie_frames.append(np.stack([B, M, A_tilde, deterf]).astype(np.float32))
                movie_days.append(day)
            if verbose and day % 30 == 0:
                print(f"  day {day:4d} g={g:5.2f} d={delta:6.4f} "
                      f"H={rec['H']:.3f} N={n_end:5d} "
                      f"cr/hm={day_crimes}/{day_home} Msum={M.sum():.4f}")

            # reset per-day accumulators
            day_crimes = day_home = day_inflow = 0
            sum_p_crime = sum_p_home = 0.0
            sum_w = 0
            n_day_start = n_end

        if step % (steps_per_day * 30) == 0:
            assert abs(M.sum() - M_tot) < 1e-6 * max(1, M_tot), "M not conserved"
            assert np.isfinite(B).all() and np.isfinite(M).all(), "NaN/inf in fields"
            assert (B >= -1e-9).all(), "B negative"
            assert (A_tilde >= A0 - 1e-9).all(), "A_tilde < A0"

    df = pd.DataFrame(rows)
    final = dict(B=B, M=M, x=x, y=y, cid=cid, ent=ent, next_id=next_id)
    if movie_every:
        final["movie"] = np.stack(movie_frames) if movie_frames else np.empty((0,))
        final["movie_days"] = np.array(movie_days, dtype=int)
        final["movie_fields"] = np.array(["B", "M", "A_tilde", "deter"])
    events = pd.DataFrame(ev_rows,
                          columns=["type", "day", "x", "y", "cid", "entry_day", "residence"])
    return df, snaps, final, events


def summarize(df, frac_window=0.5):
    """Average the stationary tail. Default: last half of the run; for long runs use
    a fixed late window so different T_max are comparable."""
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
