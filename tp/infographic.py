"""Render an infographic PNG from a small JSON spec. Only use facts from sources.

Usage:
    python -m tp.infographic spec.json out.png

Spec shapes (all need "title" and "source"; "subtitle" optional):
    {"type": "stats",    "items": [{"label": "Distance from Earth", "value": "25.9 bn km"}, ...]}   2-6 items
    {"type": "bar",      "unit": "crore", "items": [{"label": "2024", "value": 120.5}, ...]}       2-10 items, numeric
    {"type": "timeline", "items": [{"label": "5 Sep 1977", "value": "Launched from Florida"}, ...]} 2-8 items
"""
import json
import os
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BG = "#0f172a"
CARD = "#1e293b"
FG = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#f97316"
ACCENT2 = "#38bdf8"
W, H = 12, 6.75  # inches, 16:9
SITE = os.environ.get("SITE_NAME", "")


def _frame(spec):
    fig = plt.figure(figsize=(W, H), dpi=150, facecolor=BG)
    fig.text(0.04, 0.91, textwrap.shorten(spec["title"], 70, placeholder="…"),
             color=FG, fontsize=24, fontweight="bold", va="center")
    if spec.get("subtitle"):
        fig.text(0.04, 0.845, textwrap.shorten(spec["subtitle"], 110, placeholder="…"),
                 color=MUTED, fontsize=13, va="center")
    fig.add_artist(plt.Line2D([0.04, 0.12], [0.80, 0.80], color=ACCENT, lw=4,
                              transform=fig.transFigure))
    footer = f"Source: {spec.get('source', '')}"
    fig.text(0.04, 0.04, textwrap.shorten(footer, 120, placeholder="…"), color=MUTED, fontsize=10)
    if SITE:
        fig.text(0.96, 0.04, SITE, color=ACCENT, fontsize=11, fontweight="bold", ha="right")
    return fig


def _stats(fig, items):
    items = items[:6]
    n = len(items)
    cols = 3 if n > 4 else n if n <= 3 else 2
    rows = (n + cols - 1) // cols
    top, bottom, left, right = 0.74, 0.12, 0.04, 0.96
    gap = 0.02
    cw = (right - left - gap * (cols - 1)) / cols
    ch = (top - bottom - gap * (rows - 1)) / rows
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x = left + c * (cw + gap)
        y = top - (r + 1) * ch - r * gap
        ax = fig.add_axes([x, y, cw, ch])
        ax.set_facecolor(CARD)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(0.07, 0.58, textwrap.shorten(str(it["value"]), 16, placeholder="…"),
                color=ACCENT if i % 2 == 0 else ACCENT2, fontsize=30 if rows == 1 else 26,
                fontweight="bold", transform=ax.transAxes, va="center")
        ax.text(0.07, 0.24, "\n".join(textwrap.wrap(str(it["label"]), 34)[:2]),
                color=FG, fontsize=12, transform=ax.transAxes, va="center")


def _bar(fig, items, unit):
    items = items[:10]
    labels = [textwrap.shorten(str(i["label"]), 28, placeholder="…") for i in items][::-1]
    vals = [float(i["value"]) for i in items][::-1]
    ax = fig.add_axes([0.24, 0.12, 0.68, 0.62], facecolor=BG)
    bars = ax.barh(labels, vals, color=ACCENT, height=0.6)
    vmax = max(vals) if vals else 1
    for b, v in zip(bars, vals):
        txt = f"{v:,.2f}".rstrip("0").rstrip(".") + (f" {unit}" if unit else "")
        ax.text(b.get_width() + vmax * 0.01, b.get_y() + b.get_height() / 2, txt,
                color=FG, va="center", fontsize=11)
    ax.set_xlim(0, vmax * 1.18)
    ax.tick_params(colors=FG, labelsize=12, length=0)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def _timeline(fig, items):
    items = items[:8]
    ax = fig.add_axes([0.04, 0.10, 0.92, 0.66], facecolor=BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis("off")
    n = len(items)
    ys = [1 - (i + 0.5) / n for i in range(n)]
    ax.plot([0.2, 0.2], [ys[-1], ys[0]], color=MUTED, lw=2, zorder=1)
    for y, it in zip(ys, items):
        ax.scatter([0.2], [y], s=120, color=ACCENT, zorder=2)
        ax.text(0.18, y, textwrap.shorten(str(it["label"]), 22, placeholder="…"),
                color=ACCENT2, fontsize=12, fontweight="bold", ha="right", va="center")
        ax.text(0.23, y, textwrap.shorten(str(it["value"]), 95, placeholder="…"),
                color=FG, fontsize=12, va="center")


def render(spec, out_path):
    if not spec.get("items") or len(spec["items"]) < 2:
        raise ValueError("an infographic needs at least 2 items")
    fig = _frame(spec)
    kind = spec.get("type")
    if kind == "stats":
        _stats(fig, spec["items"])
    elif kind == "bar":
        _bar(fig, spec["items"], spec.get("unit", ""))
    elif kind == "timeline":
        _timeline(fig, spec["items"])
    else:
        raise ValueError(f"unknown infographic type: {kind}")
    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        print(render(json.load(f), sys.argv[2]))
