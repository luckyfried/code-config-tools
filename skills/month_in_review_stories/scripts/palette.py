#!/usr/bin/env python3
"""Movement 1, research: the month's palette against the year's, from the person's own photos. Reads
build/photo_index.json and build/stats.json, writes build/palette.json.

USAGE (from the workspace root):
    python3 S/scripts/palette.py [--accent "#E8743B"]

The month's five dominant colors and the rest of the year's five (weighted by how much of each photo they cover,
kept distinct from each other), each with a plain name ("cobalt", "sunset orange") and the photo that shows it
best; "shift", the month's colors that sit far from every color of the year (what is new this month); and the card
roles drawn from the month: bg (a deep tone of its darkest color), ink (warm white), accent (its most vivid color,
lifted until it reads on bg at 3:1 or more) and accent2. --accent overrides the accent role.
"""
import argparse
import colorsys
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

NAMES = {
    "snow white": (244, 244, 240), "cream": (240, 228, 200), "sand": (220, 196, 150), "wheat": (232, 210, 160),
    "stone gray": (150, 150, 145), "slate": (90, 100, 112), "charcoal": (48, 50, 54), "ink black": (20, 20, 24),
    "sky blue": (140, 190, 225), "sea blue": (40, 120, 170), "deep navy": (28, 40, 80), "ice blue": (196, 214, 228),
    "teal": (30, 130, 130), "mint": (170, 220, 190), "sage": (150, 175, 130), "leaf green": (90, 150, 70),
    "forest green": (40, 80, 50), "olive": (120, 120, 60), "mustard": (210, 170, 50), "sunshine yellow": (250, 215, 80),
    "peach": (245, 180, 140), "apricot": (245, 160, 90), "sunset orange": (240, 120, 60), "rust": (170, 80, 40),
    "terracotta": (200, 100, 70), "brick red": (160, 50, 40), "coral": (240, 110, 100), "tomato red": (210, 60, 50),
    "blush pink": (235, 180, 185), "rose": (200, 100, 120), "berry": (130, 40, 70), "plum": (100, 50, 90),
    "lavender": (180, 160, 210), "dusk violet": (90, 70, 120), "chocolate": (90, 60, 40), "caramel": (190, 130, 70),
    "taupe": (150, 130, 115), "dusty mauve": (170, 130, 140), "cobalt": (38, 84, 178), "indigo": (40, 46, 98),
    "saffron": (226, 160, 44),
}


def to_lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def dist(a, b):
    return math.dist(to_lab(a), to_lab(b))


def name_of(rgb):
    return min(NAMES, key=lambda n: dist(NAMES[n], rgb))


def unique_name(rgb, taken):
    """The nearest plain name not yet used; a close second name, then a qualifier, when the nearest is taken."""
    ranked = sorted(NAMES, key=lambda n: dist(NAMES[n], rgb))
    best = dist(NAMES[ranked[0]], rgb)
    for n in ranked:
        if n not in taken and dist(NAMES[n], rgb) <= max(1.6 * best, best + 8):
            return n
    h, l, s = hls(rgb)
    warm = "warm " if (h < 0.09 or h > 0.92) and s > 0.25 else ""
    for q in (warm, "deep " if lum(rgb) < lum(NAMES[ranked[0]]) else "light ", "dusty ", "soft "):
        if q and q + ranked[0] not in taken:
            return q + ranked[0]
    return f"{ranked[0]} {len(taken) + 1}"


def hexc(rgb):
    return "#%02X%02X%02X" % tuple(int(max(0, min(255, c))) for c in rgb)


def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hls(rgb):
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))


def from_hls(h, l, s):
    return tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))


def hex_rgb(h):
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette_of(entries, n=5):
    """The n dominant colors of a set of photo-index entries, each {hex, name, share, photo}."""
    if not entries:
        return []
    samples = [(tuple(c["rgb"]), c["share"]) for e in entries for c in e["colors"]]
    clusters = []  # [rgb_sum, weight]
    for rgb, w in sorted(samples, key=lambda s: -s[1]):
        best = min(clusters, key=lambda c: dist(tuple(v / c[1] for v in c[0]), rgb), default=None)
        if best and dist(tuple(v / best[1] for v in best[0]), rgb) < 14:
            best[0] = [best[0][i] + rgb[i] * w for i in range(3)]
            best[1] += w
        else:
            clusters.append([[v * w for v in rgb], w])
    cols = sorted(((tuple(v / c[1] for v in c[0]), c[1]) for c in clusters), key=lambda c: -c[1])
    chosen = []
    for gap in (32, 24, 16, 8, 0):
        for rgb, w in cols:
            if len(chosen) < n and all(dist(rgb, c[0]) >= gap for c in chosen) and (rgb, w) not in chosen:
                chosen.append((rgb, w))
        if len(chosen) >= n:
            break
    total = sum(w for _, w in chosen) or 1
    import picks  # noqa: E402  (same folder; prepares photos the same way)
    out, names = [], set()
    for rgb, w in chosen:
        nm = unique_name(rgb, names)
        names.add(nm)
        ex = min(entries, key=lambda e: min(dist(tuple(c["rgb"]), rgb) / (0.2 + c["share"]) for c in e["colors"]))
        out.append({"hex": hexc(rgb), "name": nm, "share": round(w / total, 3), "photo": picks.prepare(ex["src"])})
    return sorted(out, key=lambda c: -c["share"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accent")
    a = ap.parse_args()
    idx = _env.read_json("build/photo_index.json")
    st = _env.read_json("build/stats.json")
    if not idx or not st:
        sys.exit("build/photo_index.json or build/stats.json missing: run stats.py and picks.py first (research.py runs them)")
    mk = st["month"]["key"]
    month = palette_of([e for e in idx if e["month"] == mk]) or palette_of(idx)
    year = palette_of([e for e in idx if e["month"] != mk])
    shift = [dict(c, nearest_year=min((y["name"] for y in year), key=lambda n: dist(hex_rgb(c["hex"]), hex_rgb(next(y["hex"] for y in year if y["name"] == n))), default=None),
                  distance=round(min((dist(hex_rgb(c["hex"]), hex_rgb(y["hex"])) for y in year), default=99), 1))
             for c in month]
    shift = [c for c in shift if c["distance"] >= 22]

    rgbs = [hex_rgb(c["hex"]) for c in month]
    darkest = min(rgbs, key=lum)
    h, l, s = hls(darkest)
    bg = from_hls(h, min(l, 0.11), min(s, 0.45))
    ink = (250, 246, 238)
    vivid = sorted(rgbs, key=lambda c: -(hls(c)[2] * (1 - abs(hls(c)[1] - 0.55))))
    def lift(c):
        hh, ll, ss = hls(c)
        while contrast(from_hls(hh, ll, ss), bg) < 3.2 and ll < 0.92:
            ll += 0.03
        return from_hls(hh, ll, max(ss, 0.45))
    accent = hex_rgb(a.accent) if a.accent else lift(vivid[0])
    accent2 = lift(next((c for c in vivid[1:] if dist(c, vivid[0]) > 25), vivid[-1]))
    roles = {"bg": hexc(bg), "ink": hexc(ink), "accent": hexc(accent), "accent2": hexc(accent2),
             "muted": hexc(tuple(int(ink[i] * 0.72 + bg[i] * 0.28) for i in range(3)))}
    _env.write_json("build/palette.json", {"month": month, "year": year, "shift": shift, "roles": roles,
                                            "notes": {"accent_on_bg": round(contrast(accent, bg), 2),
                                                      "ink_on_bg": round(contrast(ink, bg), 2)}})
    print(f"{st['month']['name']} palette: " + ", ".join(f"{c['name']} {c['hex']} ({c['share']:.0%})" for c in month))
    print("rest of the year: " + ", ".join(f"{c['name']} {c['hex']} ({c['share']:.0%})" for c in year))
    print("new this month: " + (", ".join(f"{c['name']} (nearest in the year: {c['nearest_year']}, {c['distance']} apart)" for c in shift) or "none"))
    print("roles: " + ", ".join(f"{k} {v}" for k, v in roles.items()))
    print(f"accent on bg {contrast(accent, bg):.1f}:1, ink on bg {contrast(ink, bg):.1f}:1")
    print("wrote build/palette.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
