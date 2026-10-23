"""Render comparable per-player attack-loot histograms from stdin JSON."""
import json
import math
import sys
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, MultipleLocator, FuncFormatter
import numpy as np

BUCKET = 500_000


def distribution(rows):
    values = [float(value) for row in rows for value in row['attackLoot']]
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Loot must be finite and nonnegative')
    maximum = max(values, default=0)
    # Keep 0–6M stable for the observed range; expand without clipping outliers.
    upper = max(6_000_000, (math.floor(maximum / BUCKET) + 1) * BUCKET)
    edges = np.arange(0, upper + BUCKET, BUCKET)
    result = []
    for row in rows:
        attacks = np.asarray(row['attackLoot'], dtype=float)
        if len(attacks) != row['attacks']:
            raise ValueError('Histogram sample count does not match attack count')
        counts, _ = np.histogram(attacks, bins=edges)
        if int(counts.sum()) != len(attacks):
            raise ValueError('Histogram lost attacks')
        result.append((counts, counts * 100 / len(attacks) if len(attacks) else counts, attacks))
    return edges, result


def render(data, path):
    rows = data['rows']
    edges, results = distribution(rows)
    background, foreground, muted = '#17191f', '#f1f2f5', '#a8afbd'
    colors = ['#efbc64', '#73b4f2', '#7ed6b1', '#bc9cf2', '#ee98b0']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
                         'text.color': foreground, 'axes.labelcolor': muted,
                         'xtick.color': muted, 'ytick.color': muted})
    fig, axes = plt.subplots(max(len(rows), 1), 1, figsize=(11, max(4, 1.7 * len(rows) + 2.1)), squeeze=False)
    fig.patch.set_facecolor(background)
    fig.subplots_adjust(left=.08, right=.96, top=.82, bottom=.09, hspace=.65)
    fig.text(.08, .955, 'How much loot does each attack bring?', size=22, weight='bold')
    fig.text(.08, .920, 'TOP 5 BY TOTAL LOOT  ·  GOLD + ELIXIR + DARK ELIXIR', size=11, color=muted)
    fig.text(.08, .885, '500K-loot buckets  ·  Bar height = % of that player’s attacks', size=12, color=muted)
    peak = max((float(pct.max()) for _, pct, _ in results), default=10)
    ymax = max(20, math.ceil(peak / 10) * 10)
    for index, row in enumerate(rows):
        ax = axes[index][0]
        counts, pct, attacks = results[index]
        ax.set_facecolor(background)
        ax.bar(edges[:-1] / 1e6, pct, width=BUCKET / 1e6, align='edge', color=colors[index],
               edgecolor=background, linewidth=1.5, zorder=3)
        median = float(np.median(attacks)) if len(attacks) else 0
        ax.axvline(median / 1e6, color=foreground, linestyle=(0, (3, 3)), linewidth=1.2, zorder=4)
        name = row['name'].replace('\n', ' ')
        ax.set_title(f'{index + 1}. {name}', loc='left', size=15, weight='bold', pad=13, color=foreground)
        ax.set_title(f'{len(attacks):,} attacks   ·   Median {median / 1e6:.2f}M', loc='right', size=11, pad=13, color=muted)
        ax.set_xlim(0, edges[-1] / 1e6)
        ax.set_ylim(0, ymax)
        ax.yaxis.set_major_locator(MultipleLocator(10 if ymax <= 40 else 20))
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.xaxis.set_major_locator(MultipleLocator(max(1, math.ceil(edges[-1] / 1e6 / 8))))
        ax.xaxis.set_minor_locator(MultipleLocator(.5))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:g}M'))
        ax.grid(axis='y', color='#343944', linewidth=.6, zorder=0)
        ax.tick_params(axis='both', which='both', length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    if rows:
        axes[-1][0].set_xlabel('Total loot in one attack', labelpad=10)
    else:
        axes[0][0].set_axis_off()
        axes[0][0].text(.5, .5, 'No attacks recorded since the start yet.', ha='center')
    start = datetime.fromisoformat(data['countingFrom'].replace('Z', '+00:00'))
    fig.text(.08, .025, f'Since {start:%b %d, %Y · %H:%M:%S} UTC   ·   Dashed line = median', size=10, color=muted)
    fig.savefig(path, dpi=125, facecolor=background)
    plt.close(fig)


if __name__ == '__main__':
    render(json.load(sys.stdin), sys.argv[1])
