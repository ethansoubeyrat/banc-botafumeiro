"""
Diagramme de Stabilité de Mathieu (Ince-Strutt)
================================================
Équation : θ̈ + ω₀²[1 + a·cos(2ωf·t)]·θ = 0

Méthode : Matrice de transition de Floquet (monodromy matrix)
Intégration : scipy.integrate.odeint (LSODA)

Paramètres du diagramme :
    - Axe X : ratio de fréquences ωf/ω₀ ∈ [0.1, 3]
    - Axe Y : amplitude de modulation a ∈ [0, 1.5]
    - Couleur : exposant de Floquet μ (rouge=instable, bleu=stable)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from scipy.integrate import odeint

print("Calcul du diagramme de stabilité de Mathieu (Ince-Strutt)...")
print("Équation : θ̈ + ω₀²[1 + a·cos(2ωf·t)]·θ = 0")

# ──────────────────────────────────────────────
# PARAMÈTRES DE LA GRILLE
# ──────────────────────────────────────────────
a_values    = np.linspace(0, 1.5, 80)    # amplitude de modulation
omega_ratio = np.linspace(0.1, 3, 100)  # ωf/ω₀

# Grille pour stocker μ
mu_grid = np.zeros((len(a_values), len(omega_ratio)))


# ──────────────────────────────────────────────
# CALCUL DE L'EXPOSANT DE FLOQUET
# ──────────────────────────────────────────────
def compute_floquet_exponent(a, omega_ratio_val, num_periods=1):
    """
    Calcul numérique de l'exposant de Floquet via la matrice de monodromy.

    Principe :
      1. Intégrer l'équation sur une période T avec deux CI orthogonales
      2. Construire la matrice de transition Φ(T) = [sol1_final | sol2_final]
      3. Calculer les valeurs propres λ de Φ(T)
      4. μ = max(Re(ln|λ|)) / T  →  μ>0 instable, μ<0 stable
    """
    omega_0 = 1.0                              # normalisé
    omega_f = omega_ratio_val * omega_0
    T_mod   = 2 * np.pi / omega_f             # période de la modulation
    T_total = num_periods * T_mod

    # Deux conditions initiales indépendantes
    y0_1 = [1.0, 0.0]   # θ(0)=1, θ̇(0)=0
    y0_2 = [0.0, 1.0]   # θ(0)=0, θ̇(0)=1

    t = np.linspace(0, T_total, 2000)

    # Système du 1er ordre : [θ, θ̇]
    def system(y, t):
        theta, theta_dot = y
        coeff      = omega_0**2 * (1 + a * np.cos(2 * omega_f * t))
        theta_ddot = -coeff * theta
        return [theta_dot, theta_ddot]

    # Intégration avec odeint (LSODA)
    sol1 = odeint(system, y0_1, t)
    sol2 = odeint(system, y0_2, t)

    # Matrice de transition Φ(T) — monodromy matrix
    y_final_1 = sol1[-1]
    y_final_2 = sol2[-1]
    Phi = np.column_stack([y_final_1, y_final_2])

    # Valeurs propres (multiplicateurs de Floquet)
    eigenvalues = np.linalg.eigvals(Phi)

    # Exposants caractéristiques : μ = ln|λ| / T
    mu_values = np.log(np.abs(eigenvalues) + 1e-10) / T_total
    return np.max(mu_values)   # on garde le plus grand (cas le plus instable)


# ──────────────────────────────────────────────
# REMPLISSAGE DE LA GRILLE
# ──────────────────────────────────────────────
print("\nCalcul en cours...")
for i, a in enumerate(a_values):
    if i % 10 == 0:
        print(f"  a = {a:.3f}  ({i+1}/{len(a_values)})")
    for j, ratio in enumerate(omega_ratio):
        try:
            mu_grid[i, j] = compute_floquet_exponent(a, ratio, num_periods=1)
        except Exception:
            mu_grid[i, j] = np.nan

print("✓ Calcul terminé")


# ──────────────────────────────────────────────
# TRACÉ DU DIAGRAMME
# ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 9))

# Colormap centrée sur μ=0 (rouge=instable, bleu=stable)
vmin = np.nanpercentile(mu_grid, 5)
vmax = np.nanpercentile(mu_grid, 95)
norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

im = ax.contourf(omega_ratio, a_values, mu_grid,
                 levels=50, cmap='RdBu_r', norm=norm)

# Frontière μ=0 (limite stabilité/instabilité)
contour = ax.contour(omega_ratio, a_values, mu_grid,
                     levels=[0], colors='black', linewidths=2.5)
ax.clabel(contour, inline=True, fontsize=10, fmt='μ=0')

# Lignes de résonance théoriques ωf/ω₀ = 2/n
for n in [1, 2, 3, 4]:
    omega_res = 2 / n
    if 0.1 < omega_res < 3:
        ax.axvline(omega_res, color='yellow', linestyle='--',
                   linewidth=1.5, alpha=0.6)
        ax.text(omega_res, a_values[-1] * 0.95,
                f'ωf/ω₀=2/{n}', rotation=90,
                verticalalignment='top', fontsize=9,
                color='yellow', fontweight='bold')

# Axes et titre
ax.set_xlabel('Ratio de fréquences : ωf/ω₀', fontsize=13, fontweight='bold')
ax.set_ylabel('Amplitude de modulation : a', fontsize=13, fontweight='bold')
ax.set_title(
    'DIAGRAMME DE STABILITÉ DE MATHIEU (INCE-STRUTT)\n'
    'θ̈ + ω₀²[1 + a·cos(2ωf·t)]·θ = 0',
    fontsize=14, fontweight='bold'
)

# Colorbar
cbar = plt.colorbar(im, ax=ax, pad=0.02)
cbar.set_label('Exposant de Floquet μ  (μ>0 instable, μ<0 stable)',
               fontsize=12, fontweight='bold')

# Grille
ax.grid(True, alpha=0.2, linestyle=':')
ax.set_xlim(0.1, 3)
ax.set_ylim(0, 1.5)

plt.tight_layout()
plt.savefig('digital_ince_strutt_stability_diagram.png', dpi=150, bbox_inches='tight')
print("\n✓ Diagramme sauvegardé : digital_ince_strutt_stability_diagram.png")

# Statistiques
pct_unstable = np.sum(mu_grid > 0.001) / mu_grid.size * 100
print(f"Zones d'instabilité (μ > 0) : {pct_unstable:.1f}% de la surface")