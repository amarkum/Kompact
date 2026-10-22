"""Build the VS Code extension's Kompactor icons from the K mark (docs/brand/kompactor-mark.svg):

    vscode/media/kompactor.svg    activity bar icon (monochrome, follows the theme)
    vscode/media/kompactor.woff   one-glyph icon font for $(kompactor) in the status bar

    python scripts/make_vscode_icons.py      (needs fonttools; only maintainers run this)
"""

import math
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "vscode" / "media"
# The mark on a 64-unit grid: a rounded bar and a round-capped chevron, both 7.5 wide.
BAR = (17, 14, 7.5, 36)            # x, y, width, height
CHEVRON = [(45, 15), (29, 32), (45, 49)]
W = 7.5
CODEPOINT = 0xE900


def arc(cx, cy, r, a0, a1, steps=10):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps), cy + r * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]


def bar_outline():
    x, y, w, h = BAR
    r = w / 2
    return arc(x + r, y + r, r, math.pi, 2 * math.pi) + arc(x + r, y + h - r, r, 0, math.pi)


def chevron_outline():
    (ax, ay), (bx, by), (cx, cy) = CHEVRON
    h = W / 2

    def unit(dx, dy):
        n = math.hypot(dx, dy)
        return dx / n, dy / n

    d1, d2 = unit(bx - ax, by - ay), unit(cx - bx, cy - by)
    n1, n2 = (-d1[1], d1[0]), (-d2[1], d2[0])

    def miter(sign):
        # where the two offset lines meet at the joint
        p1 = (ax + sign * n1[0] * h, ay + sign * n1[1] * h)
        p2 = (bx + sign * n2[0] * h, by + sign * n2[1] * h)
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        return p1[0] + d1[0] * t, p1[1] + d1[1] * t

    a1 = math.atan2(n2[1], n2[0])
    a0 = math.atan2(-n1[1], -n1[0])
    return ([(ax + n1[0] * h, ay + n1[1] * h), miter(1), (cx + n2[0] * h, cy + n2[1] * h)]
            + arc(cx, cy, h, a1, a1 - math.pi)                       # round end at the bottom tip
            + [miter(-1), (ax - n1[0] * h, ay - n1[1] * h)]
            + arc(ax, ay, h, a0, a0 - math.pi))                      # round end at the top tip


def svg():
    x, y, w, h = BAR
    pts = " ".join(f"{px:g},{py:g}" for px, py in CHEVRON)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 9 44 46" width="24" height="24">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w / 2}" fill="currentColor"/>'
            f'<polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="{W}" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>\n')


def font():
    em = 1000
    top, bottom = CHEVRON[0][1] - W / 2, CHEVRON[2][1] + W / 2         # 11.25 .. 52.75 on the grid
    left, right = BAR[0], CHEVRON[0][0] + W / 2
    scale = 760 / (bottom - top)          # about the size of VS Code's own codicons
    x0 = (em - (right - left) * scale) / 2

    def to_font(pt):                      # centred horizontally, vertically from -50 to 710
        return round((pt[0] - left) * scale + x0), round((bottom - pt[1]) * scale - 50)

    pen = TTGlyphPen(None)
    outlines = [[to_font(p) for p in o] for o in (bar_outline(), chevron_outline())]
    lsb = min(x for o in outlines for x, _ in o)
    for pts in outlines:
        if sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) < 0:
            pts.reverse()                 # TrueType wants clockwise outer contours
        pts.reverse()
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    fb = FontBuilder(em, isTTF=True)
    fb.setupGlyphOrder([".notdef", "kompactor"])
    fb.setupCharacterMap({CODEPOINT: "kompactor"})
    fb.setupGlyf({".notdef": TTGlyphPen(None).glyph(), "kompactor": pen.glyph()})
    fb.setupHorizontalMetrics({".notdef": (em, 0), "kompactor": (em, lsb)})
    fb.setupHorizontalHeader(ascent=850, descent=-150)
    fb.setupNameTable({"familyName": "kompactor-icons", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=850, sTypoDescender=-150, usWinAscent=850, usWinDescent=150)
    fb.setupPost()
    fb.font.flavor = "woff"
    return fb.font


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "kompactor.svg").write_text(svg())
    font().save(OUT / "kompactor.woff")
    print(f"wrote {OUT / 'kompactor.svg'} and {OUT / 'kompactor.woff'} (U+{CODEPOINT:04X})")
