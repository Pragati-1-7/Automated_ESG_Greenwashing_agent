"""Matplotlib chart helpers. All figures are drawn from scratch; no external images."""
from __future__ import annotations
import math
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Polygon, Circle, FancyArrowPatch
import numpy as np

_names = {f.name for f in font_manager.fontManager.ttflist}
FONT = "Inter" if "Inter" in _names else "DejaVu Sans"
plt.rcParams.update({
    "font.family": FONT, "font.size": 8.5, "axes.edgecolor": "#c5cad2", "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "xtick.color": "#4b5159",
    "ytick.color": "#4b5159", "axes.labelcolor": "#4b5159", "figure.dpi": 100, "savefig.dpi": 220,
})
W = 6.7  # inches, full text width


def _finish(fig, path):
    fig.savefig(path, bbox_inches="tight", pad_inches=0.06, facecolor="white")
    plt.close(fig)
    return path


def _style(ax, pal, grid=True):
    if grid:
        ax.yaxis.grid(True, color=pal["rule"], lw=0.6)
        ax.set_axisbelow(True)
    ax.tick_params(length=0)


def bar_chart(path, labels, values, pal, ylabel="", fmt="{:,.0f}", h=2.5, highlight_last=True, ylim=None, color=None):
    fig, ax = plt.subplots(figsize=(W, h))
    cols = [pal["tint2"]] * len(values)
    base = color or pal["brand"]
    cols = [pal["mid"]] * len(values)
    if highlight_last:
        cols[-1] = base
    bars = ax.bar(labels, values, color=cols, width=0.58)
    top = max(values)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + top * 0.015, fmt.format(v), ha="center", va="bottom", fontsize=8, color="#1f2328")
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    else:
        ax.set_ylim(0, top * 1.14)
    _style(ax, pal)
    return _finish(fig, path)


def line_chart(path, labels, series: dict, pal, ylabel="", fmt="{:,.0f}", h=2.6, colors=None, ylim=None, annotate=True):
    fig, ax = plt.subplots(figsize=(W, h))
    colors = colors or [pal["brand"], pal["sec"], pal["grey"], pal["mid"]]
    allv = [v for s in series.values() for v in s]
    span = max(allv) - min(allv) or 1
    for (name, vals), c in zip(series.items(), colors):
        ax.plot(labels, vals, color=c, lw=2.2, marker="o", ms=5, label=name)
        if annotate:
            for x, v in zip(labels, vals):
                ax.text(x, v + span * 0.06, fmt.format(v), ha="center", fontsize=7.5, color=c)
    if ylim:
        ax.set_ylim(*ylim)
    else:
        ax.set_ylim(min(allv) - span * 0.25, max(allv) + span * 0.22)
    ax.set_ylabel(ylabel)
    if len(series) > 1:
        ax.legend(frameon=False, loc="upper center", ncol=len(series), bbox_to_anchor=(0.5, 1.12), fontsize=8)
    _style(ax, pal)
    return _finish(fig, path)


def hbar_chart(path, labels, values, pal, xlabel="", fmt="{:,.0f}", h=2.6):
    fig, ax = plt.subplots(figsize=(W, h))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=[pal["brand"] if i == 0 else pal["mid"] for i in range(len(values))], height=0.58)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    m = max(values)
    for yi, v in zip(y, values):
        ax.text(v + m * 0.012, yi, fmt.format(v), va="center", fontsize=8)
    ax.set_xlim(0, m * 1.12)
    ax.set_xlabel(xlabel)
    ax.xaxis.grid(True, color=pal["rule"], lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    return _finish(fig, path)


def stacked_bar(path, labels, parts: dict, pal, ylabel="", h=2.6, colors=None):
    fig, ax = plt.subplots(figsize=(W, h))
    colors = colors or [pal["brand"], pal["sec"], pal["mid"], pal["grey"], pal["tint2"]]
    bottom = np.zeros(len(labels))
    for (name, vals), c in zip(parts.items(), colors):
        ax.bar(labels, vals, bottom=bottom, color=c, width=0.58, label=name)
        bottom += np.array(vals)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False, ncol=len(parts), loc="upper center", bbox_to_anchor=(0.5, 1.14), fontsize=8)
    _style(ax, pal)
    return _finish(fig, path)


def materiality(path, topics, pal, h=4.7):
    """topics: list of (label, x_business, y_stakeholder, size). Numbered bubbles + legend."""
    fig = plt.figure(figsize=(W, h))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1], wspace=0.06)
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axvspan(6.5, 10, ymin=0.65, ymax=1, color=pal["tint2"], zorder=0)
    ax.axhline(6.5, color=pal["rule"], lw=0.8, ls="--")
    ax.axvline(6.5, color=pal["rule"], lw=0.8, ls="--")
    for i, (lab, x, y, s) in enumerate(topics, 1):
        hi = x >= 6.5 and y >= 6.5
        ax.scatter(x, y, s=130 + s * 60, color=pal["brand"] if hi else pal["mid"], alpha=0.92, edgecolor="white", lw=1.2, zorder=3)
        ax.text(x, y, str(i), ha="center", va="center", color="white", fontsize=7.5, fontweight="bold", zorder=4)
    ax.set_xlabel("Importance to business success  →")
    ax.set_ylabel("Importance to stakeholders  →")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(True)
        ax.spines[sp].set_color("#c5cad2")
    ax.text(9.9, 9.75, "Priority topics", ha="right", va="top", fontsize=8, color=pal["dark"], fontweight="bold")
    lg = fig.add_subplot(gs[1])
    lg.axis("off")
    n = len(topics)
    for i, (lab, x, y, s) in enumerate(topics, 1):
        yy = 1 - (i - 0.5) / n
        lg.add_patch(Circle((0.04, yy), 0.028, transform=lg.transAxes, color=pal["brand"] if (x >= 6.5 and y >= 6.5) else pal["mid"]))
        lg.text(0.04, yy, str(i), ha="center", va="center", fontsize=6.5, color="white", fontweight="bold", transform=lg.transAxes)
        lg.text(0.12, yy, lab, va="center", fontsize=8, transform=lg.transAxes)
    return _finish(fig, path)


def timeline(path, phases, pal, h=2.7):
    """phases: list of (period, name, [bullets])."""
    fig, ax = plt.subplots(figsize=(W, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 30)
    ax.axis("off")
    n = len(phases)
    wph = 100 / n
    for i, (period, name, bullets) in enumerate(phases):
        x0 = i * wph
        shade = [pal["dark"], pal["brand"], pal["mid"], pal["sec"], pal["grey"]][i % 5]
        poly = Polygon([(x0, 22), (x0 + wph - 3, 22), (x0 + wph, 26), (x0 + wph - 3, 30), (x0, 30), (x0 + 3, 26)] if i else
                       [(x0, 22), (x0 + wph - 3, 22), (x0 + wph, 26), (x0 + wph - 3, 30), (x0, 30)], closed=True, color=shade)
        ax.add_patch(poly)
        ax.text(x0 + wph / 2 + 1.2, 26, period, ha="center", va="center", color="white", fontsize=7.6, fontweight="bold")
        ax.text(x0 + 1.2, 19.3, name, ha="left", va="center", fontsize=9, fontweight="bold", color=pal["ink"])
        ax.plot([x0 + 1.2, x0 + wph - 3], [17.4, 17.4], color=shade, lw=1.4)
        yy = 14.8
        for b in bullets:
            lines = textwrap.wrap(b, 21)
            ax.text(x0 + 1.2, yy, "\u2022 " + "\n   ".join(lines), ha="left", va="top", fontsize=7.2, color="#2f343b", linespacing=1.25)
            yy -= 2.0 * len(lines) + 1.3
    return _finish(fig, path)


def cover_art(path, kind, pal, size=(8.27, 11.69)):
    """Full-page abstract cover background. kind in steel|cement|thread|solar."""
    brand, dark, sec = pal["brand"], pal["dark"], pal["sec"]
    fig = plt.figure(figsize=size)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 141.4)
    ax.axis("off")
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    from matplotlib.colors import LinearSegmentedColormap
    cm = LinearSegmentedColormap.from_list("g", [dark, brand])
    ax.imshow(grad, extent=[0, 100, 0, 141.4], cmap=cm, aspect="auto", origin="lower", zorder=0)
    rng = np.random.default_rng(7)
    if kind == "steel":
        # concentric hexagonal forging rings, glowing arcs
        for k in range(26):
            r = 8 + k * 4.2
            ang = np.linspace(0, 2 * np.pi, 7) + 0.07 * k
            xs = 72 + r * np.cos(ang); ys = 103 + r * np.sin(ang)
            ax.plot(xs, ys, color="white", alpha=max(0.05, 0.42 - k * 0.015), lw=0.9)
        for k in range(9):
            th = np.linspace(0.2, 1.4 + 0.12 * k, 80)
            ax.plot(72 + (20 + 6 * k) * np.cos(th * 3.1), 103 + (20 + 6 * k) * np.sin(th * 3.1), color=sec, alpha=0.75 - 0.06 * k, lw=1.8)
        for _ in range(60):
            x, y = rng.uniform(0, 100), rng.uniform(70, 141)
            ax.scatter(x, y, s=rng.uniform(2, 14), color=sec, alpha=rng.uniform(0.2, 0.8), lw=0)
    elif kind == "cement":
        # stratified ridges (Western Ghats feel)
        x = np.linspace(0, 100, 400)
        for k in range(18):
            base = 62 + k * 4.3
            y = base + 6 * np.sin(x / 9 + k * 0.7) + 3.2 * np.sin(x / 3.7 + k) + 2 * np.sin(x / 17 + k * 0.3)
            ax.fill_between(x, y, 141.4, color=mix(dark, brand, k / 18), alpha=0.95, zorder=1 + k * 0.01)
            ax.plot(x, y, color="white", alpha=0.18 + 0.01 * k, lw=0.8, zorder=2 + k * 0.01)
        ax.add_patch(Circle((78, 118), 9, color=sec, alpha=0.9, zorder=3))
    elif kind == "thread":
        # woven grid of threads
        for k in range(36):
            xs = np.linspace(0, 100, 300)
            ys = 70 + k * 2.1 + 3.2 * np.sin(xs / 5 + k * 0.5) * np.exp(-((xs - 55) / 55) ** 2)
            ax.plot(xs, ys, color="white", alpha=0.35, lw=0.9, zorder=2)
        for k in range(46):
            ys = np.linspace(66, 142, 300)
            xs = 4 + k * 2.15 + 2.8 * np.sin(ys / 4 + k * 0.45)
            ax.plot(xs, ys, color=sec if k % 7 == 0 else "white", alpha=0.85 if k % 7 == 0 else 0.28, lw=1.3 if k % 7 == 0 else 0.8, zorder=3)
    else:  # solar
        # perspective array of panels + sun
        ax.add_patch(Circle((74, 118), 14, color=sec, alpha=0.95, zorder=2))
        for k in range(14):
            ax.add_patch(Circle((74, 118), 14 + k * 2.4, fill=False, ec=sec, alpha=0.5 - k * 0.035, lw=1.0, zorder=2))
        horizon = 84
        for row in range(11):
            t = row / 10
            y0 = horizon - (t ** 1.5) * 52
            y1 = horizon - ((row + 0.85) / 10) ** 1.5 * 52
            for col in range(-14, 15):
                xa = 50 + col * (4.4 + t * 11)
                xb = xa + (3.9 + t * 10)
                ax.add_patch(Polygon([(xa, y0), (xb, y0), (xb + 0.4, y1), (xa + 0.4, y1)], closed=True, fc=mix(dark, "#9bb6d6", 0.25 + 0.3 * (1 - t)), ec="white", lw=0.4, alpha=0.9, zorder=3))
    # soft bottom block for text legibility
    ax.add_patch(plt.Rectangle((0, 0), 100, 60, color=dark, alpha=0.0, zorder=5))
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def mix(a, b, w):
    from .data import mix as _m
    return _m(a, b, w)
