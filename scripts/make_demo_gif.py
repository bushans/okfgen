#!/usr/bin/env python3
"""Generate the hero demo GIF (docs/demo.gif) — no screen recorder needed.

Renders an animated terminal running okfgen, then a knowledge graph settling
into place, entirely with Pillow. Deterministic, offline, free.

    python scripts/make_demo_gif.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "demo.gif"
W, H = 860, 500

BG = (15, 20, 32)
PANEL = (23, 30, 46)
LINE = (42, 52, 80)
FG = (230, 235, 245)
MUTED = (139, 152, 184)
GREEN = (87, 217, 163)
BLUE = (91, 157, 255)
DIM = (120, 140, 180)
PALETTE = [(91, 157, 255), (87, 217, 163), (244, 183, 64), (255, 122, 144),
           (181, 140, 255), (77, 208, 225)]

_MONO = ["consola.ttf", "CascadiaCode.ttf", "DejaVuSansMono.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
_SANS = ["arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(cands, size):
    for name in cands:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


MONO = _font(_MONO, 17)
MONO_S = _font(_MONO, 14)
SANS = _font(_SANS, 15)

# Terminal transcript: (text, color). Prompt lines are "typed"; others appear.
PROMPT = (GREEN, "$ ")
LINES = [
    ("cmd", "uvx okfgen generate . -o my-okf"),
    ("out", "[okfgen] source type: local"),
    ("out", "[okfgen] wrote 5 concepts to my-okf"),
    ("ok",  "[okfgen] CONFORMANT: 5 concepts, 0 errors"),
    ("cmd", "okfgen visualize my-okf -o graph.html"),
    ("out", "[okfgen] wrote interactive graph -> graph.html"),
]

# Graph nodes in the lower panel (relative positions + label + palette idx).
GX, GY, GW, GH = 20, 250, 820, 230
NODES = [
    (0.50, 0.28, "overview", 0, 14),
    (0.24, 0.55, "dependencies", 1, 10),
    (0.42, 0.82, "modules/okfgen", 2, 11),
    (0.68, 0.80, "modules/tests", 3, 10),
    (0.78, 0.45, "docs/readme", 4, 10),
    (0.62, 0.18, "log", 5, 8),
]
EDGES = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 2)]


def _npos(i):
    fx, fy = NODES[i][0], NODES[i][1]
    return GX + fx * GW, GY + fy * GH


def _panel(d, box, title=None):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=10, fill=PANEL, outline=LINE, width=1)
    if title:
        d.text((x0 + 14, y0 + 9), title, font=SANS, fill=MUTED)


def render(n_lines, partial, graph_t, caret):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header
    d.text((24, 18), "okf", font=SANS, fill=FG)
    wf = d.textlength("okf", font=SANS)
    d.text((24 + wf, 18), "gen", font=SANS, fill=GREEN)
    d.text((24 + wf + d.textlength("gen", font=SANS) + 12, 18),
           "— any source → an agent-ready knowledge graph", font=SANS, fill=MUTED)

    # Terminal panel
    term = (20, 48, 840, 236)
    _panel(d, term)
    for i, (dx, dy, r) in enumerate([(38, 62, 6), (58, 62, 6), (78, 62, 6)]):
        d.ellipse([dx - r, dy - r, dx + r, dy + r],
                  fill=[(255, 95, 86), (255, 189, 46), (39, 201, 63)][i])
    d.text((100, 56), "bash", font=MONO_S, fill=MUTED)

    y = 88
    for idx in range(n_lines):
        kind, text = LINES[idx]
        show = text if idx < n_lines - 1 else text[:partial]
        x = 40
        if kind == "cmd":
            d.text((x, y), "$ ", font=MONO, fill=GREEN)
            x += d.textlength("$ ", font=MONO)
            d.text((x, y), show, font=MONO, fill=FG)
            if idx == n_lines - 1 and caret:
                cx = x + d.textlength(show, font=MONO)
                d.rectangle([cx + 1, y + 2, cx + 9, y + 20], fill=FG)
        else:
            color = GREEN if kind == "ok" else DIM
            d.text((x, y), show, font=MONO, fill=color)
        y += 24

    # Graph panel
    gbox = (GX, GY, GX + GW, GY + GH)
    _panel(d, gbox, title="graph.html — interactive knowledge graph")
    if graph_t > 0:
        cx, cy = GX + GW / 2, GY + GH / 2 + 6
        ease = graph_t * graph_t * (3 - 2 * graph_t)  # smoothstep
        # edges
        for a, b in EDGES:
            ax, ay = _npos(a); bx, by = _npos(b)
            ax = cx + (ax - cx) * ease; ay = cy + (ay - cy) * ease
            bx = cx + (bx - cx) * ease; by = cy + (by - cy) * ease
            d.line([(ax, ay), (bx, by)], fill=LINE, width=2)
        # nodes
        for i, (_, _, label, ci, r) in enumerate(NODES):
            nx, ny = _npos(i)
            nx = cx + (nx - cx) * ease; ny = cy + (ny - cy) * ease
            d.ellipse([nx - r, ny - r, nx + r, ny + r], fill=PALETTE[ci])
            if graph_t > 0.75:
                d.text((nx + r + 5, ny - 8), label, font=MONO_S, fill=FG)
    return img


def build_frames():
    frames, durs = [], []

    def add(img, ms):
        frames.append(img); durs.append(ms)

    # Phase 1+2: type each cmd, reveal outputs.
    revealed = 0
    for idx, (kind, text) in enumerate(LINES):
        revealed = idx + 1
        if kind == "cmd":
            step = 2
            for c in range(0, len(text) + 1, step):
                add(render(revealed, c, 0, caret=True), 45)
            add(render(revealed, len(text), 0, caret=True), 500)
        else:
            add(render(revealed, len(text), 0, caret=False), 320)

    # Phase 3: graph settles in.
    for k in range(0, 15):
        add(render(len(LINES), len(LINES[-1][1]), k / 14, caret=False), 70)
    # Hold the finished frame.
    add(render(len(LINES), len(LINES[-1][1]), 1.0, caret=False), 2200)
    return frames, durs


def main() -> int:
    frames, durs = build_frames()
    # Quantize to a shared adaptive palette for a small, flicker-free GIF.
    pal = frames[-1].convert("P", palette=Image.ADAPTIVE, colors=128)
    qframes = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    OUT.parent.mkdir(exist_ok=True)
    qframes[0].save(OUT, save_all=True, append_images=qframes[1:],
                    duration=durs, loop=0, optimize=True, disposal=2)
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} — {len(frames)} frames, {kb:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
