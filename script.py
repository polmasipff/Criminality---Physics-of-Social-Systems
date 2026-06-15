import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# =============================================================================
# Parámetros del paper (Fig. 3c: stationary hotspots)
# =============================================================================
N      = 128        # grid 128x128 como en el paper
l      = 1.0        # espaciado de la grilla (house separations)
dt     = 1/100      # paso de tiempo (días) — CRÍTICO: faltaba en el código original
omega  = 1/15       # tasa de decaimiento del atractivo dinámico (días^-1)
A0_val = 1/30       # atractivo estático uniforme (días^-1)
eta    = 0.03       # parámetro de neighborhood effects — Fig. 3c
theta  = 0.56       # aumento de atractivo por crimen — Fig. 3c
Gamma  = 0.019      # tasa de generación de criminales por celda — Fig. 3c
z      = 4          # vecinos de Von Neumann (el paper usa z=4 para cuadrada)

# Para Fig. 3d (dynamic hotspots): eta=0.03, theta=5.6, Gamma=0.002
# Para Fig. 3a (homogeneous):      eta=0.2,  theta=0.56, Gamma=0.019
# Para Fig. 3b (dynamic hotspots): eta=0.2,  theta=5.6,  Gamma=0.002

# =============================================================================
# Valores de equilibrio homogéneo (Ec. 2.10 del paper)
# B_bar = theta * Gamma / omega
# n_bar = Gamma * dt / (1 - exp(-A_bar * dt))
# =============================================================================
B_bar = theta * Gamma / omega
A_bar = A0_val + B_bar
n_bar = Gamma * dt / (1 - np.exp(-A_bar * dt))

print(f"Equilibrio: B_bar={B_bar:.4f}, A_bar={A_bar:.4f}, n_bar={n_bar:.4f}")
print(f"Criminales totales esperados: {n_bar * N**2:.1f}")

# =============================================================================
# Inicialización en equilibrio homogéneo (como dice el paper)
# =============================================================================
Ao = np.ones((N, N)) * A0_val
B  = np.ones((N, N)) * B_bar          # FIX: inicializar en B_bar, no en 0
A  = Ao + B

# Número de criminales: Poisson con media n_bar por celda
rng = np.random.default_rng(42)
n   = rng.poisson(lam=n_bar, size=(N, N)).astype(int)

print(f"Criminales iniciales: {n.sum()}")

# =============================================================================
# Función de actualización de B (Ec. 2.6 del paper)
# B_s(t+dt) = [B_s + (eta*l^2/z) * LapB] * (1 - omega*dt) + theta*dt * E_s
#
# FIXES:
#   - (1 - omega*dt) en vez de (1 - omega)
#   - theta*dt*E en vez de theta*E   [porque theta*dt = epsilon del paper]
#   - Laplaciano correcto con l^2 en denominador
# =============================================================================
def update_B(B, E, omega, eta, theta, dt, l, z):
    # Laplaciano discreto (Ec. 2.7): suma vecinos - z*B_s, dividido l^2
    # Con condiciones de contorno periódicas
    neighbors_sum = (
        np.roll(B, 1, axis=0) + np.roll(B, -1, axis=0) +
        np.roll(B, 1, axis=1) + np.roll(B, -1, axis=1)
    )
    lap_B = (neighbors_sum - z * B) / (l**2)

    B_new = (B + eta * l**2 / z * lap_B) * (1 - omega * dt) + theta * dt * E
    return np.maximum(B_new, 0.0)   # B no puede ser negativo

# =============================================================================
# Función de actualización de criminales (Ec. 2.2, 2.3 del paper)
# Con vecinos de Von Neumann (z=4, como en el paper para grilla cuadrada)
# =============================================================================
def update_criminals(n, A, Gamma, dt, N):
    n_new = np.zeros((N, N), dtype=int)
    E     = np.zeros((N, N), dtype=int)

    # Precomputar probabilidades de burglary
    p = 1.0 - np.exp(-A * dt)   # FIX: multiplicar por dt

    # Índices de los 4 vecinos de Von Neumann (periódicos)
    di = [-1, 1, 0, 0]
    dj = [ 0, 0,-1, 1]

    for i in range(N):
        for j in range(N):
            num = n[i, j]
            if num == 0:
                continue
            pij = p[i, j]

            # Crímenes: binomial(num, pij)
            crimes = rng.binomial(num, pij)
            E[i, j] += crimes
            movers  = num - crimes

            # Los que se mueven: biased random walk hacia vecinos
            if movers > 0:
                ni_list = [(i + di[k]) % N for k in range(4)]
                nj_list = [(j + dj[k]) % N for k in range(4)]
                weights = np.array([A[ni_list[k], nj_list[k]] for k in range(4)])
                w_sum   = weights.sum()
                if w_sum > 0:
                    weights /= w_sum
                else:
                    weights = np.ones(4) / 4.0

                chosen = rng.choice(4, size=movers, p=weights)
                for k in chosen:
                    n_new[ni_list[k], nj_list[k]] += 1

    # Generar nuevos criminales (Poisson con tasa Gamma por celda por paso)
    new_criminals = rng.poisson(Gamma * dt, size=(N, N)).astype(int)
    n_new += new_criminals
    return n_new, E

# =============================================================================
# Versión vectorizada (más rápida) para el movimiento de criminales
# Aproximación: válida cuando n_bar es pequeño (la mayoría de celdas tiene ≤1)
# =============================================================================
def update_criminals_fast(n, A, Gamma, dt, N, rng):
    p = 1.0 - np.exp(-A * dt)

    # Crímenes
    crimes = rng.binomial(n, p)
    E      = crimes.copy()

    # Los que se mueven
    movers_count = n - crimes

    # Para cada celda, cada movedor elige un vecino proporcional a A
    # Aproximación vectorizada: distribuir movers usando proporciones
    A_up    = np.roll(A, 1, axis=0)
    A_down  = np.roll(A, -1, axis=0)
    A_left  = np.roll(A, 1, axis=1)
    A_right = np.roll(A, -1, axis=1)
    A_total = A_up + A_down + A_left + A_right
    A_total = np.where(A_total == 0, 1.0, A_total)

    # Fracción esperada de movers hacia cada dirección
    f_up    = A_up    / A_total
    f_down  = A_down  / A_total
    f_left  = A_left  / A_total
    f_right = A_right / A_total

    # Mover criminales según fracciones (redondeando con multinomial)
    # Para eficiencia, usamos floor + distribución del resto
    m = movers_count.astype(float)
    n_up    = (m * f_up).astype(int)
    n_down  = (m * f_down).astype(int)
    n_left  = (m * f_left).astype(int)
    n_right = m.astype(int) - n_up - n_down - n_left

    n_new  = np.zeros((N, N), dtype=int)
    n_new += np.roll(n_up,    -1, axis=0)   # los que van "arriba" llegan a fila-1
    n_new += np.roll(n_down,   1, axis=0)
    n_new += np.roll(n_left,  -1, axis=1)
    n_new += np.roll(n_right,  1, axis=1)

    # Nuevos criminales
    new_criminals = rng.poisson(Gamma * dt, size=(N, N)).astype(int)
    n_new += new_criminals

    return n_new, E

# =============================================================================
# Simulación principal
# =============================================================================
T_days    = 730      # días totales a simular
steps_per_day = int(1 / dt)
T         = T_days * steps_per_day   # pasos totales
save_at   = {10, 365, 730}           # días en los que guardar snapshot
snapshots  = {}

print(f"\nSimulando {T} pasos ({T_days} días)...")
print(f"Usando función vectorizada rápida\n")

for t in range(T):
    n, E = update_criminals_fast(n, A, Gamma, dt, N, rng)
    B    = update_B(B, E, omega, eta, theta, dt, l, z)
    A    = Ao + B

    day = int(t * dt)   # día actual
    if day in save_at and day not in snapshots:
        snapshots[day] = {
            'A': A.copy(),
            'n_total': n.sum()
        }
        print(f"  t={day} días — criminales: {n.sum()}, A_mean: {A.mean():.4f}, A_max: {A.max():.4f}")

# Guardar t=730 si no se guardó (último paso)
if 730 not in snapshots:
    snapshots[730] = {'A': A.copy(), 'n_total': n.sum()}

# =============================================================================
# Visualización — mismo estilo de colores que el paper
# =============================================================================
# El paper usa: verde = B_bar (equilibrio), violeta = 0, rojo = ≥ 2*B_bar
# Normalizamos A relativo a A_bar

fig, axes = plt.subplots(1, len(snapshots), figsize=(5 * len(snapshots), 5))
if len(snapshots) == 1:
    axes = [axes]

cmap = plt.cm.rainbow   # igual que el paper (violeta → verde → rojo)

for ax, (day, snap) in zip(axes, sorted(snapshots.items())):
    A_snap  = snap['A']
    A_norm  = A_snap / (2 * A_bar)   # 0 = violeta, 0.5 = verde (equilibrio), 1 = rojo
    im = ax.imshow(A_norm, cmap=cmap, vmin=0, vmax=1,
                   origin='lower', interpolation='nearest')
    ax.set_title(f't = {day} días\n{snap["n_total"]} criminales', fontsize=11)
    ax.set_xlabel('x (house separations)')
    ax.set_ylabel('y (house separations)')

# Colorbar con etiquetas en unidades físicas
cbar = fig.colorbar(im, ax=axes, fraction=0.03, pad=0.04)
cbar.set_ticks([0, 0.5, 1.0])
cbar.set_ticklabels(['0', f'A̅ = {A_bar:.3f}', f'2A̅ = {2*A_bar:.3f}'])
cbar.set_label('Attractiveness A(x,t)', fontsize=10)

fig.suptitle(
    f'Simulación discreta — η={eta}, θ={theta}, Γ={Gamma}\n'
    f'(equivale a Fig. 3c del paper de Short et al. 2008)',
    fontsize=12
)
plt.tight_layout()
plt.savefig('/mnt/user-data/outputs/crime_hotspots.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nGuardado: crime_hotspots.png")

# =============================================================================
# Diagnóstico: comparar con equilibrio teórico
# =============================================================================
print("\n--- Diagnóstico ---")
print(f"B_bar teórico:  {B_bar:.5f}")
print(f"A_bar teórico:  {A_bar:.5f}")
print(f"n_bar teórico:  {n_bar:.5f}")
print(f"B_mean final:   {B.mean():.5f}")
print(f"A_mean final:   {A.mean():.5f}")
print(f"n_mean final:   {n.mean():.5f}")
print(f"A_max/A_bar:    {A.max()/A_bar:.2f}x  (hotspots deben ser >>1)")