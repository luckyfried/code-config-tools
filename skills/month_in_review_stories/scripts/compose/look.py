"""The look every card and the reel are set in: the style's faces and colors, and the numbering.

A board is drawn in one style card (compose/style.py). Its faces are the card's two faces, each in its case and with
its tracking. Its colors are the card's palette rule applied to the month's swatches (compose/palette.py): taste.json's
`swatches` when it gives them, else the photographs' own dominant colors, each in the set's one grade (photos.graded),
else the neutral four for a month with no photographs. The kit's roles are read from the rule's: bg the ground, ink the
words, line the accent, high the second accent, column and dim the muted tone; the rule's paper, accent, accent2 and
muted stand beside them for the shared moves.

A look the person gives is a template.json in either of two shapes: theirs (`palette` a list of colors, `font` a family
name, `numbering` such as "1/4", `cards` a count) or the kit's own build/template.json (`palette` that list, `colors` the
named roles, `font`, `numbering`, `cards` a list). Its palette's colors then take the roles on every board, and its
numbering opens every card's title. Its font is set where a board's card has a face of that family; elsewhere the
board keeps its card's faces, and the substitution is named (`note`).

`find(path)` reads the given look (the named file, else template.json in the workspace, else build/template.json);
`read(d)` normalizes either shape; `measure(month)` measures the month's photographs once; `dress(month, card)` sets the
month's colors, faces and numbering for one card."""
import json
import re
import statistics
from pathlib import Path

from . import photos

ROLES = ("bg", "ink", "line", "high", "column", "dim")
# the numbering a card's title opens with when no look names one: its place, two digits
NUMBERING = "01"
HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, round(c)))) for c in rgb)


def rgb_of(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb_of(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, k):
    """a moved k of the way to b."""
    return hexc([x + (y - x) * k for x, y in zip(rgb_of(a), rgb_of(b))])


def chroma(h):
    r, g, b = rgb_of(h)
    return (max(r, g, b) - min(r, g, b)) / 255


def read(d, source=None):
    """A look in either shape as {"palette", "colors", "font", "numbering", "cards", "source", "keep"}, every field None
    the look leaves out; None when it names no palette, no font and no numbering. `keep` carries its other fields."""
    if not isinstance(d, dict):
        return None
    pal = d.get("palette")
    colors = None
    if isinstance(pal, dict):
        colors = {k: "#" + v.lstrip("#").lower() for k, v in pal.items() if k in ROLES and isinstance(v, str) and HEX.match(v)}
        palette = list(colors.values())
    else:
        palette = ["#" + v.lstrip("#").lower() for v in pal or [] if isinstance(v, str) and HEX.match(v)]
    if isinstance(d.get("colors"), dict):
        colors = {k: "#" + v.lstrip("#").lower() for k, v in d["colors"].items() if k in ROLES and isinstance(v, str) and HEX.match(v)}
    font = d.get("font")
    if not font and isinstance(d.get("type"), dict):
        font = d["type"].get("family")
    numbering = d.get("numbering") if isinstance(d.get("numbering"), str) and d.get("numbering").strip() else None
    cards = d.get("cards")
    cards = cards if isinstance(cards, int) and not isinstance(cards, bool) else len(cards) if isinstance(cards, list) and cards else None
    if not palette and not font and not numbering:
        return None
    ours = {"series", "style", "finish", "bpm", "month", "palette", "colors", "font", "type", "numbering", "cards", "texture", "reel", "axis",
            "format", "source", "keep", "font_used", "note"}
    keep = d.get("keep") if isinstance(d.get("keep"), dict) else {k: v for k, v in d.items() if k not in ours}
    return {"palette": palette or None, "colors": colors or None, "font": font.strip() if isinstance(font, str) and font.strip() else None,
            "numbering": numbering, "cards": cards, "source": d.get("source") or source, "keep": keep}


def find(path=None):
    """The look the person gave: the named file, else template.json in the workspace, else last month's
    build/template.json; None when none of them is a look."""
    for p in [path] if path else ["template.json", "build/template.json"]:
        f = Path(p)
        if f.is_file():
            try:
                d = json.loads(f.read_text())
            except ValueError:
                continue
            got = read(d, str(p))
            if got:
                return got
    return None


def faces_of(card, font=None):
    """The faces a board is set in, the card's display and text faces, and the words that tell the person a font they
    named is not one the card sets (None when they named none, or one of the card's)."""
    f = card["faces"]
    faces = {"family": f["display"]["family"], "display_face": dict(f["display"]), "text_face": dict(f["text"])}
    if not font:
        return faces, None
    want = font.lower().replace(" ", "")
    if any(want == x["family"].lower().replace(" ", "") for x in f.values()):
        return faces, None
    return faces, f"{font} is not a font this style sets, so the type is {f['display']['family']} and {f['text']['family']}, the faces of {card['name'].lower()}"


def numbered(fmt, i, n):
    """The card's number in the look's numbering: the first figure of `fmt` is the card's place (zero-padded as `fmt`
    pads it) and the second, when there is one, is the count of cards, so "1/4" numbers the third card "3/4"."""
    nums = list(re.finditer(r"\d+", fmt or NUMBERING))
    fmt = fmt or NUMBERING
    if not nums:
        return f"{i}"
    out, last = [], 0
    for k, m in enumerate(nums[:2]):
        v = str(i).zfill(len(m.group(0)) if m.group(0).startswith("0") else 1) if k == 0 else str(n)
        out.append(fmt[last:m.start()] + v)
        last = m.end()
    return "".join(out) + fmt[last:]


def roles_of(look):
    """The six roles from a given look: its named roles where it has them; from a list, the line is its most colorful
    color, the ground the first of the rest and the ink the one of the rest that reads best on it; high a fourth color,
    else the line; column and dim the ground and the ink mixed."""
    c = dict(look.get("colors") or {})
    pal = list(look.get("palette") or [])
    if not {"bg", "ink", "line"} <= set(c):
        rest = list(pal)
        line = c.get("line") or (max(rest, key=chroma) if len(rest) >= 3 else None)
        if line in rest:
            rest.remove(line)
        bg = c.get("bg") or (rest.pop(0) if rest else "#10141c")
        if bg in rest:
            rest.remove(bg)
        ink = c.get("ink") or (max(rest, key=lambda x: contrast(x, bg)) if rest else ("#111111" if luminance(bg) > 0.4 else "#f5f2ea"))
        if ink in rest:
            rest.remove(ink)
        if not line:
            line = rest.pop(0) if rest else mix(ink, bg, 0.25)
        c.update(bg=bg, ink=ink, line=line)
        if rest and "high" not in c:
            c["high"] = rest[0]
    c.setdefault("high", c["line"])
    c.setdefault("column", mix(c["bg"], c["ink"], 0.18))
    c.setdefault("dim", mix(c["ink"], c["bg"], 0.45))
    return {k: c[k] for k in ROLES}


def swatches(m, given=None):
    """The month's swatches: the ones taste.json gives, else up to five of the photographs' dominant colors (each
    photograph's weighted by the share it covers, kept apart from each other), else the neutral four."""
    from . import palette
    if given:
        out = [str(h).lower() for h in given if isinstance(h, str) and HEX.match(h)]
        if out:
            return ["#" + h.lstrip("#") for h in out]
    rows = sorted(((h, w) for x in m.measures.values() for h, w in x.get("swatches") or []), key=lambda r: -r[1])
    out = []
    for gap in (60, 40, 20, 0):
        for h, _ in rows:
            if len(out) < 5 and h not in out and all(_far(h, o) >= gap for o in out):
                out.append(h)
        if len(out) >= 5:
            break
    return out or list(palette.NEUTRAL)


def _far(a, b):
    return sum(abs(x - y) for x, y in zip(rgb_of(a), rgb_of(b)))


def colors_of(card, sw):
    """The kit's roles and the card's from the card's palette rule over the swatches, and every hex the rule made."""
    from . import palette
    made = palette.palette_of(card["palette"], sw)
    r = made["roles"]
    colors = {"bg": r["bg"], "ink": r["ink"], "line": r["accent"], "high": r["accent2"], "column": r["muted"], "dim": r["muted"],
              "paper": r["paper"], "accent": r["accent"], "accent2": r["accent2"], "muted": r["muted"]}
    return colors, made["made"]


def source(lk, whose="their"):
    """Where a board's look came from, in words: the look the person gave, else their photographs, else the kit's own
    colors for a month with no photographs."""
    given = lk.get("given") or {}
    if given.get("source") and given.get("palette"):
        return given["source"]
    if (lk.get("theme") or {}).get("from") == "kit":
        return f"the kit's own colors, as {whose} month has no photographs"
    return f"{whose} photographs"


def measure(m):
    """The month's photographs measured once: the posts with a photograph (m.shown), the set's grade target and cast,
    and each photograph's measures in that grade."""
    m.shown = [p for p in m.posts if p.photo and Path(p.photo).exists()]
    m.target = photos.median_lightness([p.photo for p in m.shown]) if m.shown else None
    m.cast = photos.median_cast([p.photo for p in m.shown]) if m.shown else None
    m.measures = {p: photos.measure(p.photo, m.target, m.cast) for p in m.shown}
    return m


def dress(m, card, given=None, given_swatches=None):
    """The month's look in one card's style: its colors (the given palette's when there is one, else the card's rule
    over the swatches), its faces and its numbering."""
    m.card = card
    m.look = given
    m.swatches = swatches(m, given_swatches)
    colors, m.made = colors_of(card, m.swatches)
    if given and given.get("palette"):
        mine = roles_of(given)
        colors.update(mine)
        colors.update(accent=mine["line"], accent2=mine["high"], muted=mine["dim"])
        m.made = sorted(set(m.made) | set(mine.values()))
        m.theme = {"from": given.get("source") or "template.json"}
    else:
        m.theme = {"from": "photographs" if m.shown else "kit", "rule": card["palette"]["rule"], "swatches": m.swatches}
    m.colors = colors
    m.faces, m.font_note = faces_of(card, (given or {}).get("font"))
    m.numbering = (given or {}).get("numbering") or NUMBERING
    return m
