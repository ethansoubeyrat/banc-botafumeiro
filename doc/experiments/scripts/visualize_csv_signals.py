"""
CSV Signal Visualization - Botafumeiro Bench
=============================================
Reads a CSV file recorded by the measurement bench and produces:
    Figure 1 — Full-duration subplots (angle, angular velocity, motor power)
    Figure 2 — 30 s zoom
    Figure 3 — Combined overlay (3 y-axes)

CSV format:
    time,AccX,AccY,AccZ,AsX,AsY,AsZ,AngleX,AngleY,AngleZ,vMotor,iMotor,pMotor

Usage:
    python3 visualize_csv.py <path_to_csv>
    python3 visualize_csv.py data.csv
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
CSV_FILE        = 'data.csv'          # default filename (override via CLI)
SKIP_SAMPLES    = 300                 # ignore first N samples (IMU warm-up)
ZOOM_DURATION   = 30                  # seconds shown in zoom figures
ENVELOPE_WINDOW = 50                  # samples for moving-max power envelope


# ──────────────────────────────────────────────
# TIME PARSING
# ──────────────────────────────────────────────
def parse_time(time_str):
    """
    Parse custom timestamp: '2026-5-18 1:4:32:784'
    Format: YYYY-M-D H:M:S:ms  → seconds (float)
    """
    date, time_part = time_str.split(' ')
    _, _, _ = date.split('-')                     # year, month, day (unused)
    h, m, s, ms = time_part.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


# ──────────────────────────────────────────────
# LOAD & PREPARE DATA
# ──────────────────────────────────────────────
filename = sys.argv[1] if len(sys.argv) > 1 else CSV_FILE

df = pd.read_csv(filename)
df['t'] = df['time'].apply(parse_time)
df['t'] -= df['t'].iloc[0]                       # normalise to t = 0

# Drop initial warm-up transient
df = df.iloc[SKIP_SAMPLES:].copy()
df['t'] -= df['t'].iloc[0]                       # re-normalise

time             = df['t'].values
angle            = df['AngleY'].values
angular_velocity = df['AsY'].values
power            = df['pMotor'].values

# Power envelope (moving maximum)
half = ENVELOPE_WINDOW
power_envelope = np.array([
    power[max(0, i - half): min(len(power), i + half)].max()
    for i in range(len(power))
])

dt = np.mean(np.diff(time))
fs = 1.0 / dt

print(f'Loaded: {filename}')
print(f'  Samples   : {len(time)} (after skipping {SKIP_SAMPLES})')
print(f'  Duration  : {time[-1]:.2f} s')
print(f'  Sample rate: {fs:.1f} Hz  (dt = {dt * 1000:.1f} ms)')


# ──────────────────────────────────────────────
# FIGURE 1 — FULL DURATION (3 subplots)
# ──────────────────────────────────────────────
fig1, axes = plt.subplots(3, 1, figsize=(14, 10))
fig1.suptitle('Botafumeiro — Sensor signals (full duration)', fontsize=15, fontweight='bold')

axes[0].plot(time, angle, 'r-', lw=1, alpha=0.85)
axes[0].set_ylabel('Angle θ (°)', fontsize=12)
axes[0].set_title('Pendulum angle (AngleY)', fontsize=13, fontweight='bold')
axes[0].axhline(0, color='k', ls='--', lw=0.8, alpha=0.5)
axes[0].grid(True, alpha=0.3)

axes[1].plot(time, angular_velocity, 'b-', lw=1, alpha=0.85)
axes[1].set_ylabel('Angular velocity (°/s)', fontsize=12)
axes[1].set_title('Angular velocity (AsY)', fontsize=13, fontweight='bold')
axes[1].axhline(0, color='k', ls='--', lw=0.8, alpha=0.5)
axes[1].grid(True, alpha=0.3)

axes[2].plot(time, power, 'g-', lw=0.5, alpha=0.6, label='Power')
axes[2].plot(time, power_envelope, 'b-', lw=2, label='Envelope (moving max)')
axes[2].fill_between(time, 0, power_envelope, alpha=0.2, color='blue')
axes[2].set_xlabel('Time (s)', fontsize=12)
axes[2].set_ylabel('Motor power (W)', fontsize=12)
axes[2].set_title('Motor power and envelope', fontsize=13, fontweight='bold')
axes[2].legend(fontsize=10, loc='upper right')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('signals_full.png', dpi=150, bbox_inches='tight')
print('✓ signals_full.png')


# ──────────────────────────────────────────────
# FIGURE 2 — ZOOM (first ZOOM_DURATION seconds)
# ──────────────────────────────────────────────
mask  = time <= min(ZOOM_DURATION, time[-1])

fig2, axes2 = plt.subplots(3, 1, figsize=(14, 10))
fig2.suptitle(f'Botafumeiro — Sensor signals (first {ZOOM_DURATION} s)', fontsize=15, fontweight='bold')

axes2[0].plot(time[mask], angle[mask], 'r-', lw=1.5)
axes2[0].set_ylabel('Angle θ (°)', fontsize=12)
axes2[0].set_title('Pendulum angle (AngleY)', fontsize=13, fontweight='bold')
axes2[0].axhline(0, color='k', ls='--', lw=0.8, alpha=0.5)
axes2[0].grid(True, alpha=0.3)

axes2[1].plot(time[mask], angular_velocity[mask], 'b-', lw=1.5)
axes2[1].set_ylabel('Angular velocity (°/s)', fontsize=12)
axes2[1].set_title('Angular velocity (AsY)', fontsize=13, fontweight='bold')
axes2[1].axhline(0, color='k', ls='--', lw=0.8, alpha=0.5)
axes2[1].grid(True, alpha=0.3)

axes2[2].plot(time[mask], power[mask], 'g-', lw=1, alpha=0.7, label='Power')
axes2[2].plot(time[mask], power_envelope[mask], 'b-', lw=2.5, label='Envelope')
axes2[2].fill_between(time[mask], 0, power_envelope[mask], alpha=0.25, color='blue')
axes2[2].set_xlabel('Time (s)', fontsize=12)
axes2[2].set_ylabel('Motor power (W)', fontsize=12)
axes2[2].set_title('Motor power and envelope', fontsize=13, fontweight='bold')
axes2[2].legend(fontsize=10, loc='upper right')
axes2[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('signals_zoom.png', dpi=150, bbox_inches='tight')
print('✓ signals_zoom.png')


# ──────────────────────────────────────────────
# FIGURE 3 — COMBINED (3 y-axes, zoom duration)
# ──────────────────────────────────────────────
fig3, ax1 = plt.subplots(figsize=(16, 7))
fig3.suptitle(f'Botafumeiro — Combined view: angle, velocity, motor power  (first {ZOOM_DURATION} s)',
              fontsize=14, fontweight='bold')

# Angle  (left y-axis)
c1 = 'tab:red'
ax1.set_xlabel('Time (s)', fontsize=13)
ax1.set_ylabel('Angle θ (°)', color=c1, fontsize=13)
ax1.plot(time[mask], angle[mask], color=c1, lw=2, alpha=0.85, label='Angle')
ax1.tick_params(axis='y', labelcolor=c1)
ax1.grid(True, alpha=0.25)

# Angular velocity  (right y-axis 1)
ax2 = ax1.twinx()
c2  = 'tab:blue'
ax2.set_ylabel('Angular velocity (°/s)', color=c2, fontsize=13)
ax2.plot(time[mask], angular_velocity[mask], color=c2, lw=1.5, alpha=0.7, label='Angular velocity')
ax2.tick_params(axis='y', labelcolor=c2)

# Motor power envelope  (right y-axis 2, offset)
ax3 = ax1.twinx()
ax3.spines['right'].set_position(('outward', 70))
c3  = 'tab:green'
ax3.set_ylabel('Motor power (W)', color=c3, fontsize=13)
ax3.plot(time[mask], power_envelope[mask], color=c3, lw=2.5, alpha=0.9, label='Power envelope')
ax3.fill_between(time[mask], 0, power_envelope[mask], alpha=0.12, color=c3)
ax3.tick_params(axis='y', labelcolor=c3)

# Combined legend
lines  = (ax1.get_lines() + ax2.get_lines() + ax3.get_lines())
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, fontsize=11, loc='upper left')

plt.tight_layout()
plt.savefig('signals_combined.png', dpi=150, bbox_inches='tight')
print('✓ signals_combined.png')


# ──────────────────────────────────────────────
# STATISTICS
# ──────────────────────────────────────────────
print('\n' + '=' * 50)
print('STATISTICS')
print('=' * 50)
print(f'\nAngle (AngleY):')
print(f'  Min   : {angle.min():.2f}°')
print(f'  Max   : {angle.max():.2f}°')
print(f'  Amplitude: {(angle.max() - angle.min()) / 2:.2f}°')

print(f'\nAngular velocity (AsY):')
print(f'  Min   : {angular_velocity.min():.2f} °/s')
print(f'  Max   : {angular_velocity.max():.2f} °/s')
print(f'  Std   : {angular_velocity.std():.2f} °/s')

print(f'\nMotor power:')
print(f'  Mean  : {power.mean():.3f} W')
print(f'  Max   : {power.max():.3f} W')
print(f'  Envelope max: {power_envelope.max():.3f} W')
print('=' * 50)
