"""The colors a board is set in: a style card's palette rule applied to the month's swatches (the photographs' own
dominant colors, or the swatches taste.json gives). `palette_of(rule, swatches)` returns the six roles (bg, ink, paper,
accent, accent2, muted), the swatches as the rule turned them, and `made`, every hex the rule produced; a board shows
those hexes and no others."""
import colorsys


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


# the swatches a run with no photographs' colors yet is colored from: a dark, a warm white, a gray and a yellow
NEUTRAL = ("#14161c", "#f3eee4", "#8f94a1", "#ffc93c")
ROLES = ("bg", "ink", "paper", "accent", "accent2", "muted")


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
