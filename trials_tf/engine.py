"""engine.py — police-extended Short et al. (2008) crime hotspot model."""
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


def daily_metrics(B, M, A_tilde, crime_today, n_criminals, chi, kappa,
                  crime_accum, B_bar):
    Bm = B.mean()
    flat_B = B.ravel()
    flat_M = M.ravel()
    f_hot_2 = float((B >= 2 * Bm).mean())
    f_hot_3 = float((B >= 3 * Bm).mean())
    p90, p95, p99 = np.percentile(flat_B, [90, 95, 99])
    thr10 = np.percentile(flat_B, 90)
    hot10 = B >= thr10
    deter = np.exp(-chi * M)
    Mtot = flat_M.sum()
    Atm = A_tilde.mean()
    cd = crime_accum if crime_accum.sum() > 0 else crime_today
    return {
        "n_criminals": int(n_criminals),
        "crimes_that_day": int(crime_today.sum()),
        "B_mean": float(Bm),
        "B_std": float(B.std()),
        "H": float(B.std() / Bm) if Bm > 0 else 0.0,
        "f_hot_2": f_hot_2,
        "f_hot_3": f_hot_3,
        "B_p90_over_mean": float(p90 / Bm) if Bm > 0 else 0.0,
        "B_p95_over_mean": float(p95 / Bm) if Bm > 0 else 0.0,
        "B_p99_over_mean": float(p99 / Bm) if Bm > 0 else 0.0,
        "Atilde_mean": float(Atm),
        "Atilde_cv": float(A_tilde.std() / Atm) if Atm > 0 else 0.0,
        "deterrence_mean": float(deter.mean()),
        "deterrence_hot": float(deter[hot10].mean()),
        "M_mean": float(flat_M.mean()),
        "M_cv": float(flat_M.std() / flat_M.mean()) if flat_M.mean() > 0 else 0.0,
        "MB_corr": float(np.corrcoef(flat_B, flat_M)[0, 1]) if flat_M.std() > 0 else 0.0,
        "M_mass_on_hot10": float(M[hot10].sum() / Mtot) if Mtot > 0 else 0.0,
        "crime_entropy": spatial_entropy(cd),
        "Gini_B": gini(B),
        "Gini_M": gini(M),
    }


def run_police_sim(L=128, dt=1/100, T_max=365,
                   A0=1/30, omega=1/15, eta=0.03, theta=5.6, Gamma=0.002,
                   chi=0.0, M_tot=500.0, eta_M=0.1, omega_M=1/15, kappa=0.0,
                   seed=0, snapshot_days=None, init_state=None,
                   crime_accum_window=50, verbose=False):
    rng = np.random.default_rng(seed)
    B_bar = theta * Gamma / omega
    n_bar = Gamma * dt / (1 - np.exp(-(A0 + B_bar) * dt))
    M_bar = M_tot / (L * L)
    g = chi * M_bar
    h = kappa * M_bar
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
    for step in range(1, n_steps + 1):
        deter = np.exp(-chi * M)
        A_tilde = A0 + B * deter
        if kappa > 0 and len(x) > 0:
            p_rem = 1 - np.exp(-kappa * M[x, y] * dt)
            removed = rng.random(len(x)) < p_rem
            x = x[~removed]; y = y[~removed]
        E = np.zeros((L, L), np.float64)
        if len(x) > 0:
            p_crime = 1 - np.exp(-A_tilde[x, y] * dt)
            commit = rng.random(len(x)) < p_crime
            if commit.any():
                np.add.at(E, (x[commit], y[commit]), 1.0)
            x = x[~commit]; y = y[~commit]
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
        n_new = rng.poisson(Gamma * dt * L * L)
        if n_new > 0:
            x = np.concatenate([x, rng.integers(0, L, n_new, dtype=np.int64)])
            y = np.concatenate([y, rng.integers(0, L, n_new, dtype=np.int64)])
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
            rec = daily_metrics(B, M, A_tilde, E, len(x), chi, kappa,
                                crime_accum, B_bar)
            rec.update(day=day, L=L, seed=seed, chi=chi, g=g, M_tot=M_tot,
                       eta_M=eta_M, omega_M=omega_M, kappa=kappa, h=h)
            rows.append(rec)
            if day in snapshot_days:
                snaps[day] = dict(B=B.copy(), M=M.copy(), A_tilde=A_tilde.copy(),
                                  deter=np.exp(-chi * M).copy(),
                                  crime_accum=crime_accum.copy(), n_criminals=len(x))
            if verbose and day % 50 == 0:
                print(f"  day {day:4d} chi={chi:6.1f} g={g:5.2f} H={rec['H']:.3f} "
                      f"ncrim={len(x):5d} Msum={M.sum():.3f}")
        if step % (steps_per_day * 30) == 0:
            assert abs(M.sum() - M_tot) < 1e-6 * max(1, M_tot), "M not conserved"
            assert np.isfinite(B).all() and np.isfinite(M).all(), "NaN/inf"
            assert (B >= -1e-9).all(), "B negative"
            assert (A_tilde >= A0 - 1e-9).all(), "A_tilde < A0"
    df = pd.DataFrame(rows)
    return df, snaps, dict(B=B, M=M, x=x, y=y)


def window_avg(df, lo, hi):
    sub = df[(df.day > lo) & (df.day <= hi)]
    if len(sub) == 0:
        return {}
    return sub.select_dtypes(include=[np.number]).mean().to_dict()


def summarize(df):
    T = df.day.max()
    if T >= 730:
        lo, hi = 365, 730
    elif T >= 365:
        lo, hi = 185, 365
    else:
        lo, hi = T // 2, T
    s = window_avg(df, lo, hi)
    s["stat_window"] = f"{lo}-{hi}"
    return s
