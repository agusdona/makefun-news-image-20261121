#!/usr/bin/env python3
"""news-image-20261121 - "Missiles Over Poland".

A pure-stdlib Python 3.13 program that draws one 1024x1024 PNG newspaper
poster summing up the world news of Saturday 21 November 2026 and writes
it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Everything is drawn from scratch: a hand-made 5x7 bitmap font, simple
vector shapes (rects, lines, circles, polygons) and a hand-rolled PNG
encoder (zlib + struct + CRC). No network, no external files, no
timestamps anywhere in the output, so two runs produce byte-identical
files.

Layout (1024x1024, newspaper front page):
  masthead  : "21 NOVEMBER 2026" + "SATURDAY"
  hero      : Russian missiles fall on Poland (simple Europe map,
              Poland marked, missile arcs from the east)
  3 panels  : Myanmar rejects court verdict / Wall Street slides /
              Trump-Xi-Putin summit in Shenzhen
  ticker    : COP31 final stage / Saudi-led coalition intercepts
              Houthi missile over Riyadh / UK-EU deal
"""

import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PAPER = (251, 247, 236)   # warm newsprint
INK = (17, 17, 17)        # near-black
RED = (163, 22, 33)       # newspaper red
DARKRED = (120, 10, 20)
BLUE = (31, 78, 121)
LIGHTBLUE = (120, 170, 210)
GREY = (90, 90, 90)
LIGHTGREY = (220, 216, 205)
GOLD = (176, 141, 40)
GREEN = (34, 110, 60)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------------------
# 5x7 bitmap font, drawn from scratch.
# Each glyph is 7 rows of 5 characters; '#' is a set pixel.
# ---------------------------------------------------------------------------
FONT = {
    "A": (" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "B": ("#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "),
    "C": (" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"),
    "D": ("#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "),
    "E": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    "F": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    "G": (" ####", "#    ", "#    ", "# ###", "#   #", "#   #", " ### "),
    "H": ("#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "I": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"),
    "J": ("  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "),
    "K": ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    "N": ("#   #", "##  #", "##  #", "# # #", "#  ##", "#  ##", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    "Q": (" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"),
    "R": ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    "S": (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "V": ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "W": ("#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"),
    "X": ("#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"),
    "Y": ("#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    "Z": ("#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"),
    "0": (" ### ", "#  ##", "# # #", "##  #", "#   #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": ("#### ", "    #", "    #", " ### ", "    #", "    #", "#### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": (" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "   # ", "  #  ", "  #  ", "  #  "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "),
    " ": ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
    ".": ("     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "),
    ",": ("     ", "     ", "     ", "     ", "     ", " ##  ", " #   "),
    "'": ("     ", "  #  ", "  #  ", " #   ", "     ", "     ", "     "),
    "-": ("     ", "     ", "     ", " ### ", "     ", "     ", "     "),
    ":": ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", "     "),
    ";": ("     ", " ##  ", " ##  ", "     ", " ##  ", " #   ", "#    "),
    "%": ("##  #", "## # ", "   # ", "  #  ", " #   ", "# ## ", "#  ##"),
    "(": ("   ##", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   ##"),
    ")": ("##   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", "##   "),
    "/": ("    #", "   # ", "   # ", "  #  ", " #   ", " #   ", "#    "),
    "&": (" ### ", "#   #", "# #  ", " #   ", "# # #", "#  # ", " ## #"),
    "!": ("  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "),
    "?": (" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "),
    "+": ("     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "),
    "=": ("     ", "     ", "#####", "     ", "#####", "     ", "     "),
    '"': (" # # ", " # # ", "     ", "     ", "     ", "     ", "     "),
    "*": ("     ", " # # ", " ### ", " ### ", " # # ", "     ", "     "),
}

# ---------------------------------------------------------------------------
# Canvas: an RGB pixel buffer with simple vector drawing primitives.
# ---------------------------------------------------------------------------


class Canvas:
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def rect(self, x, y, w, h, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def hline(self, x, y, w, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)

    def vline(self, x, y, h, color, thickness=1):
        self.fill_rect(x, y, thickness, h, color)

    def line(self, x0, y0, x1, y1, color, thickness=1):
        """Bresenham line with square brush of the given thickness."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thickness // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, filled=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if filled:
                    if d2 <= r * r:
                        self.set(xx, yy, color)
                else:
                    if r * r - 2 * r <= d2 <= r * r:
                        self.set(xx, yy, color)

    def polygon(self, points, color):
        """Scanline fill of a simple polygon (list of (x, y))."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    if y1 != y0:
                        x = x0 + (y - y0) * (x1 - x0) // (y1 - y0)
                        xs.append(x)
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.hline(xs[j], y, xs[j + 1] - xs[j] + 1, color)

    def bezier(self, p0, p1, p2, color, thickness=3, steps=60):
        """Quadratic Bezier curve drawn as short line segments."""
        prev = p0
        for i in range(1, steps + 1):
            t = i / steps
            mt = 1 - t
            x = int(mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0])
            y = int(mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1])
            self.line(prev[0], prev[1], x, y, color, thickness)
            prev = (x, y)

    # -- text -------------------------------------------------------------
    def text_width(self, text, scale):
        return len(text) * (6 * scale) - scale

    def draw_text(self, x, y, text, color, scale=2):
        """Draw text with the built-in 5x7 font. The font holds capitals
        only, so lowercase letters are drawn as their capital form.
        Unknown chars -> space."""
        cx = x
        for ch in text:
            glyph = FONT.get(ch.upper(), FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "#":
                        self.fill_rect(
                            cx + col * scale, y + row * scale,
                            scale, scale, color)
            cx += 6 * scale
        return cx

    def draw_text_centered(self, cx, y, text, color, scale=2):
        w = self.text_width(text, scale)
        return self.draw_text(cx - w // 2, y, text, color, scale)

    def wrap_lines(self, text, scale, max_width):
        """Greedy word wrap; returns a list of lines that fit max_width."""
        lines = []
        for raw in text.split("\n"):
            words = raw.split(" ")
            cur = ""
            for word in words:
                trial = word if not cur else cur + " " + word
                if self.text_width(trial, scale) <= max_width or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = word
            if cur:
                lines.append(cur)
        return lines


# ---------------------------------------------------------------------------
# PNG encoder (hand-rolled: zlib + struct + CRC, no metadata chunks).
# ---------------------------------------------------------------------------


def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter type 0 (None) on every scanline
        start = y * stride
        raw += canvas.px[start:start + stride]
    idat = zlib.compress(bytes(raw), 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Small pictograms, drawn from scratch.
# ---------------------------------------------------------------------------


def starburst(cv, cx, cy, r_outer, r_inner, color, points=8):
    """Explosion star: alternating long/short spikes around a centre."""
    import math
    pts = []
    for i in range(points * 2):
        ang = math.pi * i / points - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang))))
    cv.polygon(pts, color)


def draw_arrow_head(cv, tip, angle_deg, size, color):
    import math
    a = math.radians(angle_deg)
    a1 = a + math.radians(150)
    a2 = a - math.radians(150)
    p1 = (int(tip[0] + size * math.cos(a1)), int(tip[1] + size * math.sin(a1)))
    p2 = (int(tip[0] + size * math.cos(a2)), int(tip[1] + size * math.sin(a2)))
    cv.polygon([tip, p1, p2], color)


def draw_europe_map(cv, x, y, w, h):
    """Very simple stylised Europe: landmass polygon, sea, Poland marked.

    Coordinates are relative to the box (x, y, w, h) so the map scales
    with its panel. Poland is a filled red square with a white border.
    """
    # Sea background.
    cv.fill_rect(x, y, w, h, LIGHTBLUE)
    # Landmass: rough outline of continental Europe.
    pts = [
        (x + int(w * 0.06), y + int(h * 0.72)),   # Iberia west
        (x + int(w * 0.10), y + int(h * 0.52)),   # France west
        (x + int(w * 0.16), y + int(h * 0.38)),   # Brittany
        (x + int(w * 0.24), y + int(h * 0.30)),   # Low countries
        (x + int(w * 0.30), y + int(h * 0.12)),   # Denmark
        (x + int(w * 0.38), y + int(h * 0.04)),   # S. Sweden
        (x + int(w * 0.52), y + int(h * 0.06)),   # Finland south
        (x + int(w * 0.62), y + int(h * 0.14)),   # Baltic
        (x + int(w * 0.82), y + int(h * 0.18)),   # Russia west
        (x + int(w * 0.96), y + int(h * 0.30)),   # Russia south
        (x + int(w * 0.97), y + int(h * 0.58)),   # Black Sea coast
        (x + int(w * 0.86), y + int(h * 0.66)),   # Balkans
        (x + int(w * 0.78), y + int(h * 0.86)),   # Greece
        (x + int(w * 0.62), y + int(h * 0.88)),   # Italy toe
        (x + int(w * 0.50), y + int(h * 0.80)),   # Italy boot
        (x + int(w * 0.38), y + int(h * 0.92)),   # Iberia south
        (x + int(w * 0.16), y + int(h * 0.92)),   # Iberia south-west
        (x + int(w * 0.08), y + int(h * 0.84)),   # Iberia west
    ]
    cv.polygon(pts, (226, 214, 178))
    # Britain: small island off the north-west coast.
    cv.polygon([
        (x + int(w * 0.10), y + int(h * 0.20)),
        (x + int(w * 0.15), y + int(h * 0.16)),
        (x + int(w * 0.18), y + int(h * 0.26)),
        (x + int(w * 0.13), y + int(h * 0.34)),
    ], (226, 214, 178))
    # Poland: red square in the centre-north of the landmass.
    px = x + int(w * 0.44)
    py = y + int(h * 0.30)
    pw = int(w * 0.13)
    ph = int(h * 0.13)
    cv.fill_rect(px, py, pw, ph, RED)
    cv.rect(px, py, pw, ph, WHITE, 3)
    return (px + pw // 2, py + ph // 2)  # centre of Poland


def draw_pagoda(cv, x, y, w, h, color):
    """Simple tiered pagoda (Myanmar) inside box (x, y, w, h)."""
    # Three stacked roofs, widest at the bottom.
    tiers = [(0.50, 0.78, 0.10), (0.36, 0.60, 0.30), (0.24, 0.42, 0.48)]
    for tw, th, ty in tiers:
        rw = int(w * tw)
        rh = int(h * 0.10)
        rx = x + (w - rw) // 2
        ry = y + int(h * ty)
        cv.polygon([
            (rx, ry + rh), (rx + rw // 2, ry), (rx + rw, ry + rh),
        ], color)
    # Spire.
    cv.vline(x + w // 2, y + int(h * 0.02), int(h * 0.40), color, 4)
    cv.circle(x + w // 2, y + int(h * 0.02), 5, color)
    # Base.
    cv.fill_rect(x + int(w * 0.18), y + int(h * 0.82), int(w * 0.64),
                 int(h * 0.14), color)


def draw_stock_chart(cv, x, y, w, h):
    """Falling stock chart: axes, grid, red line plunging down."""
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 2)
    # Grid lines.
    for i in range(1, 4):
        gy = y + int(h * i / 4)
        cv.hline(x + 4, gy, w - 8, LIGHTGREY, 1)
    # Axes.
    cv.vline(x + int(w * 0.10), y + 8, h - 16, INK, 2)
    cv.hline(x + int(w * 0.10), y + h - int(h * 0.14), w - int(w * 0.16),
             INK, 2)
    # The plunge: high top-left, sharp fall, brief bounce, final drop.
    pts = [
        (x + int(w * 0.12), y + int(h * 0.18)),
        (x + int(w * 0.28), y + int(h * 0.24)),
        (x + int(w * 0.40), y + int(h * 0.30)),
        (x + int(w * 0.52), y + int(h * 0.52)),
        (x + int(w * 0.62), y + int(h * 0.46)),
        (x + int(w * 0.74), y + int(h * 0.66)),
        (x + int(w * 0.88), y + int(h * 0.84)),
    ]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, 5)
    for p in pts:
        cv.circle(p[0], p[1], 5, RED)
    # Down arrow at the end.
    ex, ey = pts[-1]
    draw_arrow_head(cv, (ex + 16, ey + 16), 45, 18, RED)
    # Big red percent badge, top-right where the chart is empty.
    cv.draw_text(x + int(w * 0.62), y + 8, "-5%", RED, 3)


def draw_skyline(cv, x, y, w, h):
    """Shenzhen skyline: three towers with lit windows, red sun behind."""
    cv.fill_rect(x, y, w, h, (214, 232, 240))
    # Sun.
    cv.circle(x + int(w * 0.78), y + int(h * 0.26), int(h * 0.16), RED)
    # Towers.
    towers = [
        (0.06, 0.55, 0.20, 0.45),
        (0.30, 0.38, 0.22, 0.62),
        (0.56, 0.48, 0.20, 0.52),
        (0.78, 0.62, 0.16, 0.38),
    ]
    for tx, ty, tw, th in towers:
        bx = x + int(w * tx)
        by = y + int(h * ty)
        bw = int(w * tw)
        bh = int(h * th)
        cv.fill_rect(bx, by, bw, bh, BLUE)
        # Windows: small lit squares.
        for wy in range(by + 8, by + bh - 6, 14):
            for wx in range(bx + 6, bx + bw - 6, 14):
                if (wx + wy) % 28 == 0:
                    cv.fill_rect(wx, wy, 5, 5, GOLD)
    # Ground line.
    cv.hline(x, y + h - 4, w, INK, 3)


def draw_three_flags(cv, x, y, w, h):
    """Three small flags on poles: USA, China, Russia (abstract stripes)."""
    pole_h = int(h * 0.62)
    fw = w // 3
    flags = [
        [(RED, WHITE, BLUE)],          # USA: red-white-blue stripes
        [(RED, GOLD)],                 # China: red with gold star dot
        [(WHITE, BLUE, RED)],          # Russia: white-blue-red stripes
    ]
    for i, stripes in enumerate(flags):
        px = x + i * fw + fw // 2
        cv.vline(px, y, pole_h, INK, 3)
        fx = px + 3
        fy = y + 2
        fwid = fw - 14
        fhei = int(h * 0.30)
        n = len(stripes[0])
        for j, col in enumerate(stripes[0]):
            cv.fill_rect(fx, fy + j * (fhei // n), fwid, fhei // n + 1, col)
        cv.rect(fx, fy, fwid, fhei, INK, 2)
        if i == 1:
            cv.circle(fx + 8, fy + 8, 4, GOLD)


# ---------------------------------------------------------------------------
# Page layout.
# ---------------------------------------------------------------------------

MARGIN = 24


def draw_masthead(cv):
    # Top rule and date.
    cv.draw_text_centered(WIDTH // 2, 34, "21 NOVEMBER 2026", INK, 8)
    cv.hline(MARGIN, 116, WIDTH - 2 * MARGIN, INK, 4)
    # Saturday line with side rules.
    label = "SATURDAY"
    lw = cv.text_width(label, 3)
    cx = WIDTH // 2
    cv.hline(MARGIN, 140, cx - lw // 2 - MARGIN - 20, INK, 2)
    cv.hline(cx + lw // 2 + 20, 140, WIDTH - MARGIN - (cx + lw // 2 + 20),
             INK, 2)
    cv.draw_text_centered(cx, 128, label, RED, 3)
    cv.draw_text_centered(cx, 160, "WORLD NEWS IN ONE PAGE", GREY, 2)
    cv.hline(MARGIN, 188, WIDTH - 2 * MARGIN, INK, 4)


def draw_hero(cv):
    """Hero panel: map of Europe + missile arcs, headline on the right."""
    x0, y0 = MARGIN, 204
    x1, y1 = WIDTH - MARGIN, 566
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, WHITE)
    cv.rect(x0, y0, x1 - x0, y1 - y0, INK, 3)

    # Map on the left.
    map_x, map_y = x0 + 14, y0 + 14
    map_w, map_h = 400, 300
    poland_c = draw_europe_map(cv, map_x, map_y, map_w, map_h)
    cv.rect(map_x, map_y, map_w, map_h, INK, 2)
    cv.draw_text(map_x + 10, map_y + map_h - 26, "EUROPE", INK, 2)
    cv.draw_text(map_x + map_w - 92, map_y + 10, "RUSSIA", INK, 2)

    # Two missile arcs from the east (Russia) into Poland.
    px, py = poland_c
    cv.bezier((map_x + map_w - 8, map_y + 60),
              (map_x + map_w - 90, map_y - 10),
              (px + 18, py - 6), DARKRED, 4)
    cv.bezier((map_x + map_w - 8, map_y + 150),
              (map_x + map_w - 110, map_y + 60),
              (px + 20, py + 16), DARKRED, 4)
    # Explosion burst over Poland + drone dot.
    starburst(cv, px, py, 34, 16, GOLD, 8)
    cv.circle(px, py, 9, RED)
    cv.circle(px + 52, py - 34, 6, INK)
    cv.draw_text(px + 62, py - 44, "DRONE", INK, 2)
    # Poland label under the map.
    cv.draw_text(map_x + 10, map_y + map_h + 10, "POLAND", RED, 3)

    # Headline + sub-text on the right.
    tx = x0 + 440
    tw = x1 - tx - 14
    cv.draw_text(tx, y0 + 22, "MISSILES", RED, 6)
    cv.draw_text(tx, y0 + 22 + 48, "FALL ON", RED, 6)
    cv.draw_text(tx, y0 + 22 + 96, "POLAND", RED, 6)
    sub = ("Two Russian missiles and one drone land in Poland. "
           "Warsaw calls it a deliberate provocation. "
           "NATO calls it a grave violation of its airspace.")
    lines = cv.wrap_lines(sub, 2, tw)
    yy = y0 + 196
    for ln in lines:
        cv.draw_text(tx, yy, ln, INK, 2)
        yy += 26
    # Kicker line at the bottom of the hero.
    cv.hline(x0 + 14, y1 - 34, x1 - x0 - 28, LIGHTGREY, 2)
    cv.draw_text_centered((x0 + x1) // 2, y1 - 28,
                          "THE DAY'S TOP STORY", GREY, 2)


def draw_panel(cv, x, y, w, h, tag, headline_lines, sub, art):
    """One of the three middle panels. art is a draw callable
    taking (cv, ax, ay, aw, ah)."""
    cv.fill_rect(x, y, w, h, WHITE)
    cv.rect(x, y, w, h, INK, 3)
    # Tag strip.
    cv.fill_rect(x, y, w, 34, INK)
    cv.draw_text(x + 10, y + 8, tag, WHITE, 2)
    # Artwork box (shorter so headline + sub-text fit inside the panel).
    ax, ay, aw, ah = x + 12, y + 44, w - 24, 80
    art(cv, ax, ay, aw, ah)
    # Headline (two lines, scale 3).
    yy = y + 130
    for ln in headline_lines:
        cv.draw_text(x + 12, yy, ln, INK, 3)
        yy += 26
    # Sub-text (up to four wrapped lines, scale 2).
    sub_lines = cv.wrap_lines(sub, 2, w - 24)
    yy += 6
    for ln in sub_lines:
        cv.draw_text(x + 12, yy, ln, INK, 2)
        yy += 20


def draw_panels(cv):
    y0, y1 = 582, 856
    gap = 12
    w = (WIDTH - 2 * MARGIN - 2 * gap) // 3
    h = y1 - y0

    draw_panel(
        cv, MARGIN, y0, w, h,
        "MYANMAR",
        ["MYANMAR REJECTS", "COURT VERDICT"],
        "Malaysia to move 10,000 Rohingya refugees to Turkiye "
        "for job training.",
        lambda c, ax, ay, aw, ah: draw_pagoda(c, ax, ay, aw, ah, GOLD),
    )
    draw_panel(
        cv, MARGIN + w + gap, y0, w, h,
        "MARKETS",
        ["WALL ST SLIDES", "INTO CORRECTION"],
        "S&P 500 -3.7%. Nasdaq -5% as AI and chip stocks sell "
        "off. 2026 gains wiped out.",
        draw_stock_chart,
    )
    draw_panel(
        cv, MARGIN + 2 * (w + gap), y0, w, h,
        "SHENZHEN",
        ["TRUMP-XI-PUTIN", "SUMMIT ENDS THIN"],
        "First trilateral talks end thin: joint declaration on "
        "nuclear arms, oil, UN reform.",
        draw_skyline,
    )


def draw_ticker(cv):
    x0, y0 = MARGIN, 872
    x1, y1 = WIDTH - MARGIN, 984
    cv.fill_rect(x0, y0, x1 - x0, y1 - y0, INK)
    cv.draw_text(x0 + 12, y0 + 10, "ALSO TODAY", GOLD, 2)
    items = ("COP31 climate talks enter final stage  *  Saudi-led "
             "coalition intercepts Houthi missile over Riyadh  *  "
             "UK-EU sign food, carbon and youth mobility deal")
    lines = cv.wrap_lines(items, 2, x1 - x0 - 24)
    yy = y0 + 38
    for ln in lines:
        cv.draw_text(x0 + 12, yy, ln, WHITE, 2)
        yy += 26


def build_poster():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    # Outer frame.
    cv.rect(8, 8, WIDTH - 16, HEIGHT - 16, INK, 4)
    draw_masthead(cv)
    draw_hero(cv)
    draw_panels(cv)
    draw_ticker(cv)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    png = encode_png(build_poster())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
