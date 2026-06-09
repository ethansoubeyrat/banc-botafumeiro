"""
CSV Signal Cleaning - Botafumeiro Bench
========================================
Removes unwanted segments (transients, motor-off periods, artefacts)
from angle signals by specifying sample index ranges to suppress.

Workflow:
    1. Define zones_to_remove per CSV file (sample index ranges)
    2. Script applies mask, saves cleaned CSV, and plots before/after

The zone boundaries are identified interactively by inspecting the
angle signal with find_peaks() — the script also includes an
auto-detection helper for first pass.

Usage:
    1. Run the auto-detection step to get candidate zones
    2. Adjust zones_to_remove manually based on the visual output
    3. Run the cleaning step to produce *_clean.csv files
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks


# ──────────────────────────────────────────────
# CONFIGURATION — adjust for your files
# ──────────────────────────────────────────────

# Map: label → CSV filename
FILE_MAPPING = {
    'phase_40':  'log_20260529_090856.csv',
    'phase_45':  'log_20260529_091944.csv',
    'phase_90':  'log_20260529_101610.csv',
    'phase_95':  'log_20260529_102020.csv',
}

# Zones to remove: list of (start_sample, end_sample) per file
# Leave empty list [] to skip cleaning for that file.
# Tip: use STEP 1 (auto-detection) to find candidate ranges,
#      then refine visually.
ZONES_TO_REMOVE = {
    'phase_40':  [(103, 9269)],
    'phase_45':  [],                           # no cleaning needed
    'phase_90':  [(5, 1769), (2103, 2324)],
    'phase_95':  [(105, 7265)],
}

# Peak detection parameters
PEAK_DISTANCE = 10    # minimum samples between successive minima


# ──────────────────────────────────────────────
# STEP 1 — AUTO-DETECTION (first-pass helper)
# Detects candidate zones based on amplitude threshold.
# Run once to get initial zones, then adjust manually.
# ──────────────────────────────────────────────
def auto_detect_zones(angles, amplitude_threshold=5.0, min_gap=100):
    """
    Identify segments where |angle| stays below threshold (inactive pendulum).

    Returns list of (start, end) tuples.
    """
    active = np.abs(angles) > amplitude_threshold
    zones  = []
    in_zone = False
    start   = 0

    for i, a in enumerate(active):
        if not a and not in_zone:
            in_zone = True
            start   = i
        elif a and in_zone:
            if (i - start) >= min_gap:
                zones.append((start, i))
            in_zone = False

    if in_zone and (len(angles) - start) >= min_gap:
        zones.append((start, len(angles)))

    return zones


# ──────────────────────────────────────────────
# STEP 2 — APPLY MASK AND SAVE CLEANED FILES
# ──────────────────────────────────────────────
def clean_file(label, filename, zones):
    """
    Apply zone mask to CSV and save *_clean.csv.

    Returns (df_original, df_clean).
    """
    df     = pd.read_csv(filename)
    angles = df['AngleY'].values

    if not zones:
        print(f'{label}: no cleaning  ({len(df)} samples kept)')
        df_clean = df.copy()
    else:
        mask          = np.ones(len(df), dtype=bool)
        total_removed = 0

        for start, end in zones:
            mask[start:end]  = False
            total_removed   += (end - start)

        df_clean = df[mask].reset_index(drop=True)
        pct      = 100.0 * total_removed / len(df)
        print(f'{label}: {len(df)} → {len(df_clean)} samples  '
              f'({pct:.1f}% removed)')
        for s, e in zones:
            print(f'  removed [{s} : {e}]  ({e - s} pts)')

    out_file = filename.replace('.csv', '_clean.csv')
    df_clean.to_csv(out_file, index=False)
    print(f'  ✓ saved: {out_file}\n')

    return df['AngleY'].values, df_clean['AngleY'].values


# ──────────────────────────────────────────────
# STEP 3 — BEFORE / AFTER VISUALISATION
# ──────────────────────────────────────────────
def plot_before_after(results):
    """
    Plot before/after angle signals for all files in a grid.
    Marks minima and highlights removed zones.
    """
    n     = len(results)
    fig, axes = plt.subplots(n, 2, figsize=(18, 4 * n))
    fig.suptitle('Signal Cleaning — Before / After', fontsize=16, fontweight='bold')

    for row, (label, data) in enumerate(results.items()):
        angles_raw   = data['raw']
        angles_clean = data['clean']
        zones        = data['zones']

        # ── Before ──
        ax_b = axes[row, 0]
        ax_b.plot(angles_raw, 'b-', lw=1.2, alpha=0.75, label='Original')

        for s, e in zones:
            ax_b.axvspan(s, e, alpha=0.25, color='red',
                         label='Removed' if s == zones[0][0] else '')

        minima, _ = find_peaks(-angles_raw, distance=PEAK_DISTANCE)
        ax_b.scatter(minima, angles_raw[minima], s=40, color='darkred',
                     alpha=0.6, zorder=5)

        ax_b.set_title(f'{label} — BEFORE', fontsize=12, fontweight='bold')
        ax_b.set_ylabel('Angle (°)', fontsize=10)
        ax_b.grid(True, alpha=0.3)
        if zones:
            ax_b.legend(fontsize=9)

        # ── After ──
        ax_a = axes[row, 1]
        ax_a.plot(angles_clean, 'g-', lw=1.2, alpha=0.75, label='Cleaned')

        minima_c, _ = find_peaks(-angles_clean, distance=PEAK_DISTANCE)
        ax_a.scatter(minima_c, angles_clean[minima_c], s=40, color='darkgreen',
                     alpha=0.6, zorder=5)

        ax_a.set_title(f'{label} — AFTER  ({len(angles_clean)} pts)',
                       fontsize=12, fontweight='bold')
        ax_a.set_ylabel('Angle (°)', fontsize=10)
        ax_a.grid(True, alpha=0.3)
        ax_a.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig('cleaning_before_after.png', dpi=150, bbox_inches='tight')
    print('✓ cleaning_before_after.png')


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
print('=== SIGNAL CLEANING ===\n')

# Optional: print auto-detected zones for first-pass inspection
print('--- Auto-detected candidate zones (for reference) ---')
for label, filename in FILE_MAPPING.items():
    df     = pd.read_csv(filename)
    angles = df['AngleY'].values
    auto   = auto_detect_zones(angles)
    print(f'{label}: {auto}')
print()

# Apply manual zones and save cleaned files
print('--- Applying manual zones ---')
results = {}

for label, filename in FILE_MAPPING.items():
    zones            = ZONES_TO_REMOVE.get(label, [])
    raw, clean       = clean_file(label, filename, zones)
    results[label]   = {'raw': raw, 'clean': clean, 'zones': zones}

# Before/after plots
plot_before_after(results)

print('\n✓ All done.')
