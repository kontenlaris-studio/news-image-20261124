#!/usr/bin/env python3
"""Render the 24 November 2026 world-news poster as a 1024x1024 PNG.

Pure Python standard library: a small 5x7 bitmap font, a software canvas,
and a hand-rolled PNG encoder (zlib + CRC). No network, no third-party
packages. Deterministic: same input stories, same bytes out.
"""

import binascii
import os
import struct
import zlib

W, H = 1024, 1024

NAVY = (10, 25, 49)
PAPER = (245, 240, 225)
GOLD = (255, 122, 0)
MUTED = (168, 188, 208)
DARK_GOLD = (184, 88, 0)

# 5x7 bitmap font: each glyph is 7 rows of 5 bits ("1" = ink).
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
}

STORIES = [
    ("NO DEAL AT COP31",
     "Antalya climate talks stall on fossil fuels; a deal may wait until next year. - BBC"),
    ("FACTORY FIRE KILLS 24 IN INDONESIA",
     "Blaze at a Banten candy plant; rescuers still hunt for missing workers. - TOI"),
    ("RUSSIAN SHIP BURNS AFTER DRONE HIT",
     "Cargo vessel Sparta II ablaze in the Gulf of Finland. - TOI"),
    ("HUANG RETURNS TO NVIDIA",
     "Chip giant gains almost $1tn as tech stocks rally on the comeback. - NYT"),
    ("BEPICOLOMBO REACHES MERCURY",
     "European-Japanese probe enters orbit after an eight-year cruise. - ESA"),
    ("ALCARAZ WINS ATP FINALS",
     "Spaniard beats Zverev in Turin for his maiden season-ending title. - TOI"),
]


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * w * h)

    def rect(self, x, y, w, h, color):
        for yy in range(max(0, y), min(self.h, y + h)):
            base = (yy * self.w + max(0, x)) * 3
            for xx in range(max(0, x), min(self.w, x + w)):
                i = (yy * self.w + xx) * 3
                self.px[i:i + 3] = bytes(color)

    def text(self, x, y, s, scale, color):
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_width(self, s, scale):
        return len(s) * 6 * scale


def wrap(text, max_chars):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    return out + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)


def encode_png(canvas):
    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)
        raw.extend(canvas.px[y * canvas.w * 3:(y + 1) * canvas.w * 3])
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def render():
    c = Canvas(W, H, NAVY)
    # gold frame
    c.rect(0, 0, W, 10, GOLD)
    c.rect(0, H - 10, W, 10, GOLD)
    c.rect(0, 0, 10, H, GOLD)
    c.rect(W - 10, 0, 10, H, GOLD)
    # masthead
    title = "THE WORLD IN A DAY"
    tw = c.text_width(title, 6)
    c.text((W - tw) // 2, 52, title, 6, PAPER)
    date = "TUESDAY, 24 NOVEMBER 2026"
    dw = c.text_width(date, 3)
    c.text((W - dw) // 2, 118, date, 3, GOLD)
    c.rect(48, 168, W - 96, 4, GOLD)
    # stories
    y = 206
    for i, (head, sub) in enumerate(STORIES, 1):
        # number tile
        c.rect(48, y, 52, 52, GOLD)
        num = str(i)
        nw = c.text_width(num, 4)
        c.text(48 + (52 - nw) // 2, y + 12, num, 4, NAVY)
        # headline, up to two lines
        lines = wrap(head, 46)
        ly = y + 2
        for line in lines[:2]:
            c.text(120, ly, line, 3, PAPER)
            ly += 26
        # sub-line
        sub_lines = wrap(sub, 70)
        sy = y + 58
        for line in sub_lines[:2]:
            c.text(120, sy, line, 2, MUTED)
            sy += 18
        y += 118
        if i < len(STORIES):
            c.rect(48, y - 14, W - 96, 2, DARK_GOLD)
    # footer
    foot = "SIX STORIES - ONE DAY - 24 NOV 2026"
    fw = c.text_width(foot, 2)
    c.text((W - fw) // 2, 936, foot, 2, GOLD)
    src = "SOURCES: BBC - TIMES OF INDIA - NYT - ESA"
    sw = c.text_width(src, 2)
    c.text((W - sw) // 2, 964, src, 2, MUTED)
    return c


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    png = encode_png(render())
    with open(os.path.join(here, "artwork.png"), "wb") as f:
        f.write(png)
    print("wrote artwork.png (%d bytes, %dx%d)" % (len(png), W, H))


if __name__ == "__main__":
    main()
