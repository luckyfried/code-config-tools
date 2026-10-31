#!/usr/bin/env python3
"""Movement 1, research: the palette, from the person's own photos. Reads R/photo_index.json, writes R/palette.json.

USAGE (from the workspace root):
    python3 S/scripts/palette.py [--accent "#E8743B"]

The year's five dominant colors (weighted by how much of each photo they cover, kept distinct from each
other), each with a plain name ("sea blue", "sunset orange") and the photo that shows it best, and the card
roles drawn from them: bg (a deep tone of their darkest color), ink (warm white), accent (their most vivid
color, lifted until it reads on bg at 3:1 or more) and accent2. --accent overrides the accent role.
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
    "taupe": (150, 130, 115), "dusty mauve": (170, 130, 140),
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


NEUTRAL = ("#14161c", "#f3eee4", "#8f94a1", "#ffc93c")
ROLES = ("bg", "ink", "paper", "accent", "accent2", "muted")


def swatches_of(taste, palette=None):
    """The photographs' swatches a style's palette rule reads, as lowercase hexes: taste.json's `swatches` (hexes, or
    rows with a `hex`), else palette.json's year colors, else the neutral four."""
    rows = (taste or {}).get("swatches") or [c for c in (palette or {}).get("year") or []]
    out = [str(r["hex"] if isinstance(r, dict) else r).lower() for r in rows]
    return [h for h in out if len(h) == 7 and h.startswith("#")] or list(NEUTRAL)


def _hex(rgb):
    return hexc(rgb).lower()


def _mix(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def _toward(c, other, want, step=0.02):
    """`c` darkened or lightened (whichever reads more against `other`) until it reads against `other` at `want`:1."""
    h, l, s = hls(c)
    up = lum(other) < 0.18
    while contrast(from_hls(h, l, s), other) < want and 0.02 < l < 0.98:
        l += step if up else -step
    return from_hls(h, max(0.0, min(1.0, l)), s)


def warmth(swatches):
    """How warm the swatches are, red over blue, weighted by how vivid each is: above 0 is warm."""
    rgbs = [hex_rgb(h) for h in swatches]
    return sum((r - b) * (0.2 + hls((r, g, b))[2]) for r, g, b in rgbs) / max(1, len(rgbs))


def palette_of(rule, swatches):
    """The board's colors from a style card's palette rule and the photographs' swatches: {"roles": the six roles,
    "swatches": the swatches as the rule turned them, "made": every hex the rule produced}. A board may show these
    hexes and no others.

    photos: the swatches desaturated; paper the lightest of them lifted, bg the paper, ink the darkest, one muted
    accent. photos-plus-accent: pastel tints of the swatches; paper from their highlights, the most vivid tint the
    accent. two-inks: the most saturated hue and its complement as two flat fields that read against each other at the
    rule's contrast. mono-plus-one: black, white, and the swatches' most saturated hue. fixed: the card's warm or cool
    roles, chosen by the swatches' warmth."""
    rgbs = [hex_rgb(h) for h in swatches]
    vivid = sorted(rgbs, key=lambda c: -hls(c)[2] * (1 - abs(hls(c)[1] - 0.5)))
    kind = rule["rule"]
    turned = []
    if kind == "fixed":
        roles = dict(rule["warm"] if warmth(swatches) >= 0 else rule["cool"])
    elif kind == "photos":
        d = rule.get("desaturate", 0.25)
        turned = [from_hls(h, l, s * (1 - d)) for h, l, s in (hls(c) for c in rgbs)]
        light = max(turned, key=lum)
        h, l, s = hls(light)
        paper = from_hls(h, max(l, 0.94), min(s, 0.18))
        h, l, s = hls(min(turned, key=lum))
        ink = from_hls(h, min(l, 0.13), min(s, 0.25))
        h, l, s = hls(max(turned, key=lambda c: hls(c)[2]))
        accent = _toward(from_hls(h, 0.45, s * 0.6), paper, 3.0)
        accent2 = _toward(from_hls(h, 0.6, s * 0.4), paper, 1.6)
        roles = {"bg": paper, "ink": ink, "paper": paper, "accent": accent, "accent2": accent2, "muted": _mix(ink, paper, 0.55)}
    elif kind == "photos-plus-accent":
        t = rule.get("tint", 0.62)
        turned = [_mix(c, (255, 255, 255), t) for c in rgbs]
        h, l, s = hls(max(rgbs, key=lum))
        paper = from_hls(h, 0.93, min(max(s, 0.25), 0.45))
        h, l, s = hls(min(rgbs, key=lum))
        ink = from_hls(h, min(l, 0.16), min(s, 0.35))
        accent = _toward(_mix(vivid[0], (255, 255, 255), t * 0.45), paper, 2.2)
        accent2 = _mix(vivid[1] if len(vivid) > 1 else vivid[0], (255, 255, 255), t)
        roles = {"bg": paper, "ink": ink, "paper": paper, "accent": accent, "accent2": accent2, "muted": _mix(ink, paper, 0.5)}
    elif kind == "two-inks":
        want = rule.get("contrast", 4.5)
        h, l, s = hls(vivid[0])
        a = from_hls(h, 0.5, max(s, 0.85))
        b = _toward(from_hls((h + 0.5) % 1, 0.5, max(s, 0.85)), a, want)
        if contrast(a, b) < want:
            b = _toward(from_hls((h + 0.5) % 1, 0.9, 0.6), a, want)
        dark, light = sorted((a, b), key=lum)
        roles = {"bg": a, "ink": dark, "paper": light, "accent": b, "accent2": a, "muted": _mix(a, b, 0.5)}
    elif kind == "mono-plus-one":
        h, l, s = hls(vivid[0])
        white, black = (255, 255, 255), (10, 10, 10)
        accent = _toward(from_hls(h, 0.5, max(s, 0.8)), white, 3.0)
        roles = {"bg": white, "ink": black, "paper": white, "accent": accent, "accent2": accent, "muted": (138, 138, 138)}
    else:
        raise SystemExit(f"no palette rule named {kind!r}")
    roles = {k: (v if isinstance(v, str) else _hex(v)).lower() for k, v in roles.items()}
    turned = [_hex(c) for c in turned]
    return {"roles": roles, "swatches": turned, "made": sorted(set(roles.values()) | set(turned))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accent")
    a = ap.parse_args()
    _env.enter_run()
    idx = _env.read_json("photo_index.json")
    if not idx:
        sys.exit("photo_index.json missing: run picks.py first (research.py runs it)")
    # weighted color samples: each photo's dominant colors by the share of the photo they cover
    samples = [(tuple(c["rgb"]), c["share"]) for e in idx for c in e["colors"]]
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
            if len(chosen) < 5 and all(dist(rgb, c[0]) >= gap for c in chosen) and (rgb, w) not in chosen:
                chosen.append((rgb, w))
        if len(chosen) >= 5:
            break
    total = sum(w for _, w in chosen) or 1
    import picks  # noqa: E402  (same folder; prepares photos the same way)
    year, names = [], set()
    for rgb, w in chosen:
        nm = unique_name(rgb, names)
        names.add(nm)
        ex = min(idx, key=lambda e: min(dist(tuple(c["rgb"]), rgb) / (0.2 + c["share"]) for c in e["colors"]))
        year.append({"hex": hexc(rgb), "name": nm, "share": round(w / total, 3), "photo": picks.prepare(ex["src"])})
    year.sort(key=lambda c: -c["share"])

    rgbs = [hex_rgb(c["hex"]) for c in year]
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
    _env.write_json("palette.json", {"year": year, "roles": roles,
                                            "notes": {"accent_on_bg": round(contrast(accent, bg), 2),
                                                      "ink_on_bg": round(contrast(ink, bg), 2)}})
    print("year palette: " + ", ".join(f"{c['name']} {c['hex']} ({c['share']:.0%})" for c in year))
    print("roles: " + ", ".join(f"{k} {v}" for k, v in roles.items()))
    print(f"accent on bg {contrast(accent, bg):.1f}:1, ink on bg {contrast(ink, bg):.1f}:1")
    print("wrote R/palette.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
