"""Facility map: approximate India outline drawn from hand-entered (lon, lat) vertices."""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
from . import charts  # noqa: F401  (applies rc style)

# Approximate outline of India, clockwise from the north-west (lon, lat). Schematic only.
INDIA = [
    (74.4, 34.8), (75.6, 35.7), (77.8, 35.5), (78.9, 34.3), (78.6, 32.6), (79.3, 31.0), (80.2, 30.3),
    (81.0, 30.1), (80.2, 28.9), (81.8, 27.9), (83.3, 27.4), (84.7, 27.2), (86.0, 26.6), (87.3, 26.4),
    (88.1, 26.5), (88.4, 27.3), (88.9, 27.2), (89.8, 26.7), (91.5, 26.8), (92.1, 27.8), (93.4, 28.6),
    (94.8, 29.2), (96.0, 29.3), (97.3, 28.2), (96.9, 27.2), (95.6, 26.0), (95.0, 25.2), (94.5, 24.2),
    (94.1, 23.2), (93.4, 22.4), (93.0, 21.9), (92.4, 22.9), (92.2, 23.8), (91.5, 24.1), (91.9, 24.6),
    (91.1, 25.2), (90.2, 25.2), (89.8, 25.4), (89.8, 26.0), (89.0, 26.2), (88.3, 25.6), (88.1, 24.6),
    (88.6, 24.0), (88.7, 23.2), (89.0, 22.2), (88.6, 21.6), (87.1, 21.4), (86.8, 20.6), (85.9, 19.9),
    (84.8, 19.2), (83.5, 18.2), (82.3, 16.9), (81.2, 16.2), (80.3, 15.5), (80.1, 13.9), (80.3, 13.1),
    (79.8, 11.9), (79.8, 10.5), (79.2, 10.3), (78.9, 9.3), (78.2, 8.9), (77.5, 8.1), (76.8, 8.6),
    (76.3, 9.8), (75.9, 11.2), (75.0, 12.7), (74.6, 13.9), (74.0, 15.2), (73.5, 16.8), (73.0, 18.5),
    (72.8, 19.9), (72.8, 21.0), (72.6, 21.8), (72.2, 21.2), (71.4, 20.9), (70.2, 20.9), (69.2, 21.4),
    (68.97, 22.2), (69.9, 22.6), (70.3, 22.9), (69.5, 22.8), (68.6, 23.1), (68.2, 23.7), (68.8, 24.3),
    (70.0, 24.2), (70.5, 25.4), (70.0, 26.2), (69.5, 26.7), (70.2, 27.8), (71.0, 27.8), (71.9, 27.9),
    (72.9, 29.0), (73.8, 29.9), (74.6, 31.0), (74.6, 31.7), (74.0, 32.4), (74.6, 33.4), (73.8, 34.0),
]


def _outline(ax, fill="#eef0f3", edge="#9aa1ab", lw=0.9):
    ax.add_patch(Polygon(INDIA, closed=True, fc=fill, ec=edge, lw=lw, joinstyle="round", zorder=1))


def facility_map(path, facilities, pal, zoom=True, label_offsets=None, h=3.5):
    """Left: India outline; centre: zoom panel with numbered markers; right: numbered legend."""
    lons = np.array([f["lon"] for f in facilities]); lats = np.array([f["lat"] for f in facilities])
    fig = plt.figure(figsize=(charts.W, h))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 1.0, 1.0], wspace=0.03)
    ax = fig.add_subplot(gs[0])
    _outline(ax)
    ax.set_xlim(66, 99); ax.set_ylim(6, 37.5)
    ax.set_aspect(1.0 / np.cos(np.radians(22)))
    ax.axis("off")
    for f in facilities:
        ax.scatter(f["lon"], f["lat"], s=40, color=pal["brand"], edgecolor="white", lw=0.9, zorder=4)
    span = max(lons.max() - lons.min(), lats.max() - lats.min(), 0.8)
    half = max(span / 2 + 0.3 * span + 0.35, 1.3)
    cx, cy = (lons.min() + lons.max()) / 2, (lats.min() + lats.max()) / 2
    ax.add_patch(Rectangle((cx - half, cy - half), 2 * half, 2 * half, fill=False, ec=pal["sec"], lw=1.3, zorder=5))
    ax.text(66.5, 6.4, "Schematic outline, not to scale.", fontsize=5.8, color=pal["grey"])
    ax2 = fig.add_subplot(gs[1])
    _outline(ax2, fill="#f1f3f6")
    ax2.set_xlim(cx - half, cx + half); ax2.set_ylim(cy - half, cy + half)
    ax2.set_aspect(1.0 / np.cos(np.radians(cy)))
    ax2.set_xticks([]); ax2.set_yticks([])
    for sp in ax2.spines.values():
        sp.set_visible(True); sp.set_color(pal["sec"]); sp.set_linewidth(1.3)
    pts = [[f["lon"], f["lat"]] for f in facilities]
    mind = half * 0.2
    for _ in range(40):  # simple repulsion so numbered markers never overlap
        for a in range(len(pts)):
            for b in range(a + 1, len(pts)):
                dx, dy = pts[b][0] - pts[a][0], pts[b][1] - pts[a][1]
                d = (dx * dx + dy * dy) ** 0.5
                if d < mind:
                    ux, uy = (dx / d, dy / d) if d > 1e-9 else (1.0, 0.0)
                    k = (mind - d) / 2
                    pts[a][0] -= ux * k; pts[a][1] -= uy * k; pts[b][0] += ux * k; pts[b][1] += uy * k
    for i, f in enumerate(facilities, 1):
        f = dict(f, lon=pts[i - 1][0], lat=pts[i - 1][1])
        ax2.scatter(f["lon"], f["lat"], s=120, color=pal["brand"], edgecolor="white", lw=1.2, zorder=4)
        ax2.text(f["lon"], f["lat"], str(i), ha="center", va="center", color="white", fontsize=7, fontweight="bold", zorder=5)
    lg = fig.add_subplot(gs[2]); lg.axis("off"); lg.set_xlim(0, 1); lg.set_ylim(0, 1)
    n = len(facilities)
    for i, f in enumerate(facilities, 1):
        yy = 0.92 - (i - 1) * min(0.2, 0.8 / max(n, 1))
        lg.scatter([0.05], [yy], s=170, color=pal["brand"], zorder=3)
        lg.text(0.05, yy, str(i), ha="center", va="center", fontsize=6.5, color="white", fontweight="bold", zorder=4)
        lg.text(0.14, yy + 0.02, f["name"], va="center", fontsize=7.4, fontweight="bold", color=pal["ink"])
        lg.text(0.14, yy - 0.045, f"{f['district']}, {f['state']}", va="center", fontsize=6.6, color=pal["grey"])
    return charts._finish(fig, path)
