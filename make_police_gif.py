"""Generate GIFs of perceived attractiveness A_tilde and police field M (one run)."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import imageio.v2 as imageio

# ── parameters (must match the simulation) ──────────────────────────────────
L       = 128
dt      = 1 / 100
T_max   = 730
A0      = 1 / 30
omega   = 1 / 15
eta     = 0.03
theta   = 5.6
Gamma   = 0.002
chi     = 1.0
M_tot   = 500.0
eta_M   = 0.1
omega_M = 1 / 15
SEED    = 42

gif_every_days   = 2
gif_name_A_tilde = "police_attractiveness.gif"
gif_name_M       = "police_field_M.gif"
gif_name_M_log   = "police_field_M_log.gif"
fps              = 10

B_bar = theta * Gamma / omega
A_bar = A0 + B_bar

# ── core utilities ───────────────────────────────────────────────────────────

def initialize_state(L, B_bar, n_bar, rng):
    B = np.full((L, L), B_bar, dtype=np.float64)
    n0 = rng.poisson(n_bar * L * L)
    x = rng.integers(0, L, size=n0, dtype=np.int32)
    y = rng.integers(0, L, size=n0, dtype=np.int32)
    return B, x, y


def update_B(B, E, eta, omega, theta, dt):
    neigh_avg = (
        np.roll(B, 1, axis=0) + np.roll(B, -1, axis=0) +
        np.roll(B, 1, axis=1) + np.roll(B, -1, axis=1)
    ) / 4.0
    return ((1 - eta) * B + eta * neigh_avg) * (1 - omega * dt) + theta * E


def update_M(M, E, eta_M, omega_M, dt):
    neigh_avg = (
        np.roll(M, 1, axis=0) + np.roll(M, -1, axis=0) +
        np.roll(M, 1, axis=1) + np.roll(M, -1, axis=1)
    ) / 4.0
    M_patrol = (1 - eta_M) * M + eta_M * neigh_avg
    E_tot = E.sum()
    if E_tot == 0:
        return M_patrol
    f = omega_M * dt
    return (1 - f) * M_patrol + f * M.sum() * (E / E_tot)


def move_surviving_criminals(x, y, A, rng):
    if len(x) == 0:
        return x, y
    L = A.shape[0]
    x_up,   y_up   = (x - 1) % L, y
    x_down, y_down = (x + 1) % L, y
    x_left, y_left = x, (y - 1) % L
    x_right,y_right= x, (y + 1) % L
    weights = np.vstack([A[x_up, y_up], A[x_down, y_down],
                         A[x_left, y_left], A[x_right, y_right]]).T
    probs = weights / weights.sum(axis=1, keepdims=True)
    cumulative = np.cumsum(probs, axis=1)
    u = rng.random(len(x))
    choices = (u[:, None] > cumulative).sum(axis=1)
    x_new, y_new = x.copy(), y.copy()
    for k, (xd, yd) in enumerate([(x_up, y_up), (x_down, y_down),
                                   (x_left, y_left), (x_right, y_right)]):
        mask = choices == k
        x_new[mask], y_new[mask] = xd[mask], yd[mask]
    return x_new, y_new


def generate_new_criminals(L, Gamma, dt, rng):
    n_new = rng.poisson(Gamma * dt * L * L)
    return (rng.integers(0, L, size=n_new, dtype=np.int32),
            rng.integers(0, L, size=n_new, dtype=np.int32))


# ── simulation with frame capture ───────────────────────────────────────────

rng = np.random.default_rng(SEED)
n_bar = Gamma * dt / (1 - np.exp(-A_bar * dt))
B, x, y = initialize_state(L, B_bar, n_bar, rng)
M = np.full((L, L), M_tot / L**2, dtype=np.float64)

n_steps          = int(round(T_max / dt))
gif_every_steps  = max(1, int(round(gif_every_days / dt)))
progress_steps   = max(1, int(round(50 / dt)))  # print every 50 days

M_mean = M_tot / L**2
vmin_A, vmax_A = 0.0, 0.33          # same scale as baseline hotspots.gif
vmin_M, vmax_M = 0.0, 6 * M_mean   # up to 6× mean so hotspots are visible
log_norm = mcolors.LogNorm(vmin=1e-4 * M_tot, vmax=6 * M_mean)
frames_A, frames_M, frames_M_log = [], [], []

print(f"Running police simulation: {n_steps} steps, capturing every {gif_every_steps} steps …")

for step in range(1, n_steps + 1):
    t = step * dt
    A_tilde = A0 + B * np.exp(-chi * M)

    E = np.zeros((L, L), dtype=np.int16)
    if len(x) > 0:
        p = 1 - np.exp(-A_tilde[x, y] * dt)
        commits = rng.random(len(x)) < p
        if commits.any():
            np.add.at(E, (x[commits], y[commits]), 1)
        x, y = x[~commits], y[~commits]

    x, y = move_surviving_criminals(x, y, A_tilde, rng)
    xn, yn = generate_new_criminals(L, Gamma, dt, rng)
    if len(xn):
        x, y = np.concatenate([x, xn]), np.concatenate([y, yn])

    B = update_B(B, E, eta, omega, theta, dt)
    M = update_M(M, E, eta_M, omega_M, dt)

    if step % gif_every_steps == 0:
        # ── frame: A_tilde ──────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(6, 6), facecolor="0.92")
        im = ax.imshow(A_tilde, origin="lower", cmap="turbo",
                       vmin=vmin_A, vmax=vmax_A)
        ax.set_title(rf"Perceived attractiveness $\tilde{{A}}$ (police) | day {t:.0f}")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04,
                     label=r"$\tilde{A}_s = A^0 + B_s\,e^{-\chi M_s}$")
        plt.tight_layout()
        fig.canvas.draw()
        frames_A.append(np.asarray(fig.canvas.buffer_rgba()).copy())
        plt.close(fig)

        # ── frame: M ────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(6, 6), facecolor="0.92")
        im = ax.imshow(M, origin="lower", cmap="viridis",
                       vmin=vmin_M, vmax=vmax_M)
        ax.set_title(rf"Police field $M$ | day {t:.0f}")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04,
                     label=r"$M_s$ (police density)")
        plt.tight_layout()
        fig.canvas.draw()
        frames_M.append(np.asarray(fig.canvas.buffer_rgba()).copy())
        plt.close(fig)

        # ── frame: M (log scale) ────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(6, 6), facecolor="0.92")
        im = ax.imshow(np.clip(M, log_norm.vmin, None), origin="lower",
                       cmap="viridis", norm=log_norm)
        ax.set_title(rf"Police field $M$ (log scale) | day {t:.0f}")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04,
                     label=r"$M_s$ (log scale)")
        plt.tight_layout()
        fig.canvas.draw()
        frames_M_log.append(np.asarray(fig.canvas.buffer_rgba()).copy())
        plt.close(fig)

    if step % progress_steps == 0:
        print(f"  t = {t:7.1f} d | criminals = {len(x):5d} | "
              f"max M = {M.max():.2f} | M_sum = {M.sum():.2f}")

print(f"Saving {len(frames_A)} frames → {gif_name_A_tilde}")
imageio.mimsave(gif_name_A_tilde, frames_A, fps=fps)
print(f"Saving {len(frames_M)} frames → {gif_name_M}")
imageio.mimsave(gif_name_M, frames_M, fps=fps)
print(f"Saving {len(frames_M_log)} frames → {gif_name_M_log}")
imageio.mimsave(gif_name_M_log, frames_M_log, fps=fps)
print("Done.")
