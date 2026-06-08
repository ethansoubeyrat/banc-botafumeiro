"""
Analytical Ince-Strutt Stability Diagram - Mathieu Equation
============================================================
Equation: θ̈ + ω₀²[1 - a·sin(ωf·t)]·θ = 0

Method: Analytical approximation of instability band boundaries.
        No numerical integration required.

Instability condition for band of order n:
    |ωf/ω₀ - 2/n| < a / (2n)

Instability bands are centred at: ωf/ω₀ = 2/n  (n = 1, 2, 3, ...)
Band width: Δ(ωf/ω₀) ≈ a/n  (proportional to a, decreasing with order n)

Limitations:
    - No actual µ quantification (qualitative only)
    - Approximate band boundaries (valid for small a)
    - Does not account for damping

Parameters:
    a     : modulation amplitude (y-axis)  ∈ [0, 2]
    ωf/ω₀ : frequency ratio    (x-axis)  ∈ [0.05, 3.5]
"""

import numpy as np
import matplotlib.pyplot as plt


# ──────────────────────────────────────────────
# GRID PARAMETERS
# ──────────────────────────────────────────────
a_values    = np.linspace(0, 2.0, 150)
omega_ratio = np.linspace(0.05, 3.5, 200)

A, RATIO = np.meshgrid(a_values, omega_ratio)


# ──────────────────────────────────────────────
# ANALYTICAL INSTABILITY CRITERION
# ──────────────────────────────────────────────
def is_unstable(a, ratio, n_max=5):
    """
    Returns True if point (a, ωf/ω₀) lies within an instability band.

    Instability condition for band n:
        |ωf/ω₀ - 2/n| < a / (2n)

    Parameters
    ----------
    a     : modulation amplitude
    ratio : frequency ratio ωf/ω₀
    n_max : number of bands to check (default: 5)
    """
    for n in range(1, n_max + 1):
        omega_resonance = 2.0 / n          # band centre
        half_width      = a / (2 * n)      # half-width ∝ a/n

        if abs(ratio - omega_resonance) < half_width:
            return True
    return False


# ──────────────────────────────────────────────
# BUILD STABILITY MAP
# ──────────────────────────────────────────────
# Z = +1 → unstable (µ > 0)
# Z = -1 → stable   (µ < 0)
Z = np.where(
    np.vectorize(is_unstable)(A, RATIO),
    1.0, -1.0
)


# ──────────────────────────────────────────────
# FIGURE 1: COMPLETE DIAGRAM
# ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(15, 9))

# Colour regions
ax.contourf(RATIO, A, Z,
            levels=[-1, 0, 1],
            colors=['lightblue', 'salmon'],
            alpha=0.7)

# Analytical band boundaries
for n in range(1, 6):
    omega_res   = 2.0 / n
    omega_lower = omega_res - a_values / (2 * n)
    omega_upper = omega_res + a_values / (2 * n)

    ax.plot(omega_lower, a_values, 'k-', linewidth=2, alpha=0.8)
    ax.plot(omega_upper, a_values, 'k-', linewidth=2, alpha=0.8)
    ax.axvline(omega_res, color='darkred', linestyle='--',
               linewidth=1.5, alpha=0.4)

# Band labels on x-axis
for n in range(1, 6):
    omega_res = 2.0 / n
    if 0.05 < omega_res < 3.5:
        ax.text(omega_res, -0.15,
                f'$\\omega_f/\\omega_0 = 2/{n}$',
                ha='center', fontsize=11,
                fontweight='bold', color='darkred')

# Zone labels
ax.text(0.3, 1.7, 'UNSTABLE\n(µ > 0)',
        fontsize=13, ha='center', color='darkred',
        bbox=dict(boxstyle='round', facecolor='salmon', alpha=0.8),
        fontweight='bold')
ax.text(1.8, 1.7, 'STABLE\n(µ < 0)',
        fontsize=13, ha='center', color='darkblue',
        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
        fontweight='bold')

# Botafumeiro operating point
ax.plot(2.0, 0.1, 'g*', markersize=20, zorder=10,
        label='Botafumeiro (a≈0.1, ωf/ω₀=2)')
ax.legend(fontsize=11, loc='upper right')

ax.set_xlabel('Frequency ratio: $\\omega_f / \\omega_0$',
              fontsize=14, fontweight='bold')
ax.set_ylabel('Modulation amplitude: $a$',
              fontsize=14, fontweight='bold')
ax.set_title(
    'INCE-STRUTT STABILITY DIAGRAM — ANALYTICAL METHOD\n'
    r'$\ddot{\theta} + \omega_0^2[1 - a\sin(\omega_f t)]\theta = 0$'
    '\nRED = UNSTABLE (µ > 0) | BLUE = STABLE (µ < 0)',
    fontsize=14, fontweight='bold', pad=20
)

ax.grid(True, alpha=0.3, linestyle=':')
ax.set_xlim(0.05, 3.5)
ax.set_ylim(0, 2.0)

plt.tight_layout()
plt.savefig('analytical_ince_strutt_stability_diagram.png',
            dpi=150, bbox_inches='tight')
print('✓ analytical_ince_strutt_stability_diagram.png')


# ──────────────────────────────────────────────
# FIGURE 2: FULL VIEW + ZOOM ON PRIMARY BAND
# ──────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

# --- Left panel: full diagram ---
ax1.contourf(RATIO, A, Z,
             levels=[-1, 0, 1],
             colors=['lightblue', 'salmon'], alpha=0.7)

for n in range(1, 6):
    omega_res   = 2.0 / n
    omega_lower = omega_res - a_values / (2 * n)
    omega_upper = omega_res + a_values / (2 * n)
    ax1.plot(omega_lower, a_values, 'k-', linewidth=2)
    ax1.plot(omega_upper, a_values, 'k-', linewidth=2)
    ax1.axvline(omega_res, color='darkred', linestyle='--',
                linewidth=1, alpha=0.3)

ax1.set_xlabel('$\\omega_f / \\omega_0$', fontsize=12, fontweight='bold')
ax1.set_ylabel('Modulation amplitude $a$', fontsize=12, fontweight='bold')
ax1.set_title('Full diagram', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_xlim(0.05, 3.5)
ax1.set_ylim(0, 2.0)

# --- Right panel: zoom on primary band (ωf/ω₀ = 2) ---
ax2_xlim = (1.5, 2.5)
ax2_ylim = (0, 0.5)

omega_zoom = np.linspace(*ax2_xlim, 100)
a_zoom     = np.linspace(*ax2_ylim, 100)
A2, R2 = np.meshgrid(a_zoom, omega_zoom)
Z2 = np.where(np.vectorize(is_unstable)(A2, R2), 1.0, -1.0)

ax2.contourf(R2, A2, Z2,
             levels=[-1, 0, 1],
             colors=['lightblue', 'salmon'], alpha=0.7)

# Primary band boundaries
omega_lower = 2.0 - a_zoom / 2
omega_upper = 2.0 + a_zoom / 2
ax2.plot(omega_lower, a_zoom, 'k-', linewidth=2.5)
ax2.plot(omega_upper, a_zoom, 'k-', linewidth=2.5)

# Botafumeiro markers
ax2.axvline(2.0, color='darkred', linestyle='-', linewidth=3,
            label='$\\omega_f/\\omega_0 = 2$ (Botafumeiro)', alpha=0.7)
ax2.fill_between([1.9, 2.1], 0, 0.5,
                 color='gold', alpha=0.3, label='Actual pumping zone')
ax2.plot(2.0, 0.1, 'g*', markersize=20, zorder=10,
         label='Operating point (a≈0.1)')

ax2.set_xlabel('$\\omega_f / \\omega_0$', fontsize=12, fontweight='bold')
ax2.set_ylabel('Modulation amplitude $a$', fontsize=12, fontweight='bold')
ax2.set_title('ZOOM: Primary band (1st order)\n'
              '$\\omega_f/\\omega_0 = 2$ (Botafumeiro)',
              fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(fontsize=10, loc='upper right')
ax2.set_xlim(*ax2_xlim)
ax2.set_ylim(*ax2_ylim)

plt.tight_layout()
plt.savefig('analytical_ince_strutt_stability_diagram_detail.png',
            dpi=150, bbox_inches='tight')
print('✓ analytical_ince_strutt_stability_diagram_detail.png')

# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────
print('\n' + '='*55)
print('ANALYTICAL INSTABILITY BANDS SUMMARY')
print('='*55)
for n in range(1, 6):
    print(f'  Band n={n}: ωf/ω₀ = 2/{n} = {2/n:.3f}  '
          f'(width ∝ a/{n})')
print('\nBotafumeiro: a ≈ 0.1, ωf/ω₀ = 2  →  PRIMARY BAND ✓')
print('='*55)
