#!/usr/bin/env python3
"""Generate the dev.to / social cover image (docs/cover.png, 1000x420).

Matches the repo hero style. Uses Pillow; falls back to a default font if no
TrueType face is found (so it still runs in CI), though a system font gives the
best result.

    python scripts/make_cover.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "cover.png"
W, H = 1000, 420

BG_TOP = (15, 20, 32)
BG_BOT = (20, 29, 51)
LINE = (42, 52, 80)
FG = (230, 235, 245)
MUTED = (139, 152, 184)
BLUE = (91, 157, 255)
GREEN = (87, 217, 163)
PALETTE = [(91, 157, 255), (87, 217, 163), (244, 183, 64), (255, 122, 144),
           (181, 140, 255), (77, 208, 225)]

_FONT_CANDIDATES = {
    "bold": ["arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "reg": ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def _font(kind: str, size: int):
    for name in _FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _vgradient(img: Image.Image) -> None:
    top, bot = BG_TOP, BG_BOT
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = row


def main() -> int:
    img = Image.new("RGB", (W, H), BG_TOP)
    _vgradient(img)
    d = ImageDraw.Draw(img)

    # Wordmark: "okf" in fg, "gen" in green.
    f_title = _font("bold", 92)
    x, y = 60, 60
    d.text((x, y), "okf", font=f_title, fill=FG)
    w_okf = d.textlength("okf", font=f_title)
    d.text((x + w_okf, y), "gen", font=f_title, fill=GREEN)

    # Tagline.
    f_tag = _font("bold", 34)
    d.text((62, 188), "Turn any repo, database, or open-data portal", font=f_tag, fill=FG)
    d.text((62, 230), "into an ", font=f_tag, fill=FG)
    w_into = d.textlength("into an ", font=f_tag)
    d.text((62 + w_into, 230), "AI-ready knowledge graph.", font=f_tag, fill=BLUE)

    # Subtitle.
    f_sub = _font("reg", 22)
    d.text((62, 300), "One command  ·  no LLM  ·  no API key  ·  no lock-in", font=f_sub, fill=MUTED)

    # Decorative knowledge graph on the right (kept clear of the tagline text).
    cx, cy = 890, 205
    nodes = [(cx, cy - 90, 15, 0), (cx - 78, cy, 11, 1), (cx + 78, cy - 35, 11, 2),
             (cx + 5, cy + 95, 12, 3), (cx - 55, cy - 95, 8, 4), (cx + 88, cy + 70, 8, 5)]
    edges = [(0, 1), (0, 2), (1, 3), (2, 3), (1, 2), (3, 5), (0, 4)]
    for a, b in edges:
        d.line([nodes[a][:2], nodes[b][:2]], fill=LINE, width=2)
    for nx, ny, r, ci in nodes:
        d.ellipse([nx - r, ny - r, nx + r, ny + r], fill=PALETTE[ci])

    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT, "PNG")
    print(f"wrote {OUT} ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
