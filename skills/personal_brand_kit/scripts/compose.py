"""The parts every board is built from: the three formats and their safe areas, the style cards a board's look is read
from, the design system the composition reads, and type measured from the font files the film sets it in.

A board's times are musical beats from the film's start; its positions are px of the format's frame. The studio
composition (motion/studio) renders a board as it is written here.

A style is a card, styles/<id>.json (its schema is styles/schema.json): two faces, a palette rule, the moves and
transitions a board may use, the easing, the finish, the music recipe, the closer shape, and six axis words. A board
names its style; everything about its look is read from that card and from nothing else."""
import json
import math
from pathlib import Path

import _env

SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
# the three looks a run's boards take, board a first; a style the person names takes the place of the default that
# shares the most axes with it (trio)
TRIO = ("kinetic-type", "editorial-quiet", "swiss-grid")
LETTERS = ("a", "b", "c")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
FPS = 30


def _check(value, schema, where, out):
    """The subset of JSON Schema the card schema uses: type, required, additionalProperties false, properties, items,
    enum, pattern, minimum, maximum, minItems, maxItems."""
    import re
    t = schema.get("type")
    kinds = {"object": dict, "array": list, "string": str, "boolean": bool}
    if t == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif t == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif t:
        ok = isinstance(value, kinds[t])
    else:
        ok = True
    if not ok:
        out.append(f"{where} is {value!r}, which is not a {t}")
        return
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{where} is {value!r}, which is none of {', '.join(map(str, schema['enum']))}")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        out.append(f"{where} is {value!r}, which does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{where} is {value}, under its minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{where} is {value}, over its maximum {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            out.append(f"{where} has {len(value)} items, outside {schema.get('minItems', 0)} to {schema.get('maxItems', 'any')}")
        for i, v in enumerate(value):
            _check(v, schema.get("items") or {}, f"{where}[{i}]", out)
    if isinstance(value, dict):
        for k in schema.get("required") or []:
            if k not in value:
                out.append(f"{where} has no {k}")
        props = schema.get("properties") or {}
        for k, v in value.items():
            if k in props:
                _check(v, props[k], f"{where}.{k}", out)
            elif schema.get("additionalProperties") is False:
                out.append(f"{where} has {k}, which the schema does not name")


def validate(card):
    """Every way the card breaks styles/schema.json, and the rules the schema cannot state: a fixed palette names both
    its warm and its cool roles, every face file is on disk, and the music recipe is the style's own id."""
    out = []
    _check(card, json.loads((STYLES / "schema.json").read_text()), card.get("id", "card") if isinstance(card, dict) else "card", out)
    if out:
        return out
    pal = card["palette"]
    if pal["rule"] == "fixed" and not (pal.get("warm") and pal.get("cool") and pal.get("by") == "warmth"):
        out.append(f"{card['id']}: a fixed palette names its warm and cool roles and is chosen by warmth")
    for k, f in card["faces"].items():
        for path in [f["file"]] + ([f["italic"]] if f.get("italic") else []):
            if not (SKILL / path).is_file():
                out.append(f"{card['id']}: the {k} face's file {path} is not on disk")
    if card["music"] != card["id"]:
        out.append(f"{card['id']}: its music recipe is {card['music']!r}; a style's recipe is named for the style")
    return out


_CARDS = {}


def card(style):
    """The style card `style`, validated, or SystemExit naming the styles there are and what the card breaks."""
    if style not in _CARDS:
        f = STYLES / f"{style}.json"
        if not f.is_file():
            raise SystemExit(f"no style named {style!r} (there are: {', '.join(styles())}); styles/catalog.md says what each looks like")
        c = json.loads(f.read_text())
        bad = validate(c)
        if bad:
            raise SystemExit(f"styles/{style}.json is not a style card: " + "; ".join(bad))
        _CARDS[style] = c
    return _CARDS[style]


def styles():
    """Every style id there is a card for."""
    return sorted(f.stem for f in STYLES.glob("*.json") if f.stem != "schema")


def shared_axes(a, b):
    """The axes on which two styles' cards name the same word."""
    ca, cb = card(a), card(b)
    return [k for k in AXES if ca["axes"][k] == cb["axes"][k]]


def ids(c, kind):
    """The move or transition ids a card allows (`kind` is "moves" or "transitions")."""
    return [m["id"] for m in c[kind]]


def trio(named=None):
    """The three styles of a run's boards, in board order: the defaults, or the style the person named first, beside
    the two defaults that differ most from it (the default sharing the most axes with it gives way)."""
    if not named or named in TRIO:
        return list(TRIO)
    card(named)
    near = max(TRIO, key=lambda s: (len(shared_axes(named, s)), -TRIO.index(s)))
    return [named] + [s for s in TRIO if s != near]


_STYLE = [TRIO[0]]


def use(style):
    """Measure type in `style`'s faces from now on (every measure and box_of call reads the card in use)."""
    card(style)
    if _STYLE[0] != style:
        _STYLE[0] = style
        _FONTS.clear()


def in_use():
    """The card of the style type is measured in."""
    return card(_STYLE[0])


PROFILES = {k: v for k, v in json.loads((SKILL / "design" / "safe-areas.json").read_text()).items() if k != "about"}
FORMATS = tuple(PROFILES)


class Frame:
    """One format: `name`, `W` x `H` px at FPS, and the safe area type stays inside (`top`, `bottom`, `left`, `right` px
    from each edge)."""

    def __init__(self, name):
        if name not in PROFILES:
            raise SystemExit(f"no format named {name!r} in design/safe-areas.json (there are: {', '.join(PROFILES)})")
        s = PROFILES[name]
        self.name, self.W, self.H, self.fps = name, s["width"], s["height"], FPS
        self.top, self.bottom, self.left, self.right = s["top"], s["bottom"], s["left"], s["right"]

    @property
    def area(self):
        """The type area, [x0, y0, x1, y1] px."""
        return [self.left, self.top, self.W - self.right, self.H - self.bottom]

    @property
    def format(self):
        return {"width": self.W, "height": self.H, "fps": self.fps, "name": self.name}


def pulse_of(bpm, fps=FPS):
    """Frames per musical beat."""
    return fps * 60 / bpm


def system(c, colors):
    """The design system the composition reads, from the style card `c`: the faces, the type scale, the colors the
    card's palette rule made, the easing, the finish, the closer shape, the photo beat's layout, and the safe areas."""
    safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in PROFILES.items()}
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "scale": {"hero": 250, "h1": 150, "h2": 92, "h3": 60, "body": 40, "label": 30},
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"])), "safe": safe}


_FONTS = {}


def face_of(face):
    """The card face a line set in `face` ("display", else text) takes, from the style in use."""
    return in_use()["faces"]["display" if face == "display" else "text"]


def cased(text, face="display"):
    """A line's words in its face's case, as the film sets them."""
    case = face_of(face)["case"]
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def measure(text, size, face="display", weight=None):
    """A line's advance width, cap height and left side bearing in px, from the font file the film sets it in, in its
    face's case and with its face's tracking (em after each letter)."""
    key = (size, face, weight)
    if key not in _FONTS:
        _FONTS[key] = _env.pil_font(size, "display" if face == "display" else "text", weight=weight)
    f = _FONTS[key]
    text = cased(text, face)
    track = face_of(face)["tracking"] * size * len(text)
    return f.getlength(text) + track, -f.getbbox("H", anchor="ls")[1], f.getbbox(text, anchor="ls")[0] if text else 0


def set_lines(lines):
    """Every line in `lines` (any nesting of the board's layers) in its face's case and with its face's tracking, as
    measure and box_of read it and the film draws it."""
    if isinstance(lines, list):
        for v in lines:
            set_lines(v)
    elif isinstance(lines, dict):
        if isinstance(lines.get("text"), str) and "size" in lines and "face" in lines:
            lines["text"] = cased(lines["text"], lines["face"])
            if face_of(lines["face"])["tracking"]:
                lines["tracking"] = face_of(lines["face"])["tracking"]
        for v in lines.values():
            if isinstance(v, (dict, list)):
                set_lines(v)


def box_of(ln):
    """A line's box at rest in its frame, [x0, y0, x1, y1] px: ascender to descender, turned about its pivot."""
    f = _env.pil_font(ln["size"], "display" if ln.get("face") == "display" else "text", weight=ln.get("weight"))
    text = cased(ln["text"], ln.get("face", "display"))
    l, t, r, b = f.getbbox(text, anchor="ls")
    track = face_of(ln.get("face", "display"))["tracking"] * ln["size"]
    w = f.getlength(text) + track * len(text)
    # a tight face's negative tracking pulls the last letter's ink in by the tracking between the letters before it
    r = max(r + min(0.0, track) * max(0, len(text) - 1), w)
    x0, x1 = ln["x"] + min(0, l), ln["x"] + max(w, r)
    if ln.get("anchor") == "end":
        x0, x1 = x0 - w, x1 - w
    pts = [(x0, ln["y"] + t), (x1, ln["y"] + t), (x1, ln["y"] + b), (x0, ln["y"] + b)]
    deg = ln.get("rotate") or 0
    if deg:
        cx, cy = ln.get("pivot") or (ln["x"], ln["y"])
        a = math.radians(deg)
        pts = [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in pts]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]


def wrap(text, size, width, face="display"):
    """`text` broken into lines no wider than `width` px at `size`, balanced so the last line is never a lone short word
    when a fairer break exists."""
    words = text.split()
    if not words:
        return []
    fits = lambda ws: measure(" ".join(ws), size, face)[0] <= width
    lines = []
    for w in words:
        if lines and fits(lines[-1] + [w]):
            lines[-1].append(w)
        else:
            lines.append([w])
    # balance: move words down while the lines get more even and still fit
    for _ in range(len(words)):
        moved = False
        for i in range(len(lines) - 1):
            a, b = lines[i], lines[i + 1]
            if len(a) > 1 and fits([a[-1]] + b):
                wa, wb = measure(" ".join(a), size, face)[0], measure(" ".join(b), size, face)[0]
                na, nb = measure(" ".join(a[:-1]), size, face)[0], measure(" ".join([a[-1]] + b), size, face)[0]
                if max(na, nb) < max(wa, wb):
                    lines[i + 1] = [a.pop()] + b
                    moved = True
        if not moved:
            break
    return [" ".join(x) for x in lines]


def fit(text, width, most, least, lines=3, face="display"):
    """The largest size from `most` down to `least` at which `text` sets in at most `lines` lines inside `width`, with
    the lines; at `least` it takes as many lines as it needs."""
    size = most
    while size > least:
        got = wrap(text, size, width, face)
        if len(got) <= lines and all(measure(x, size, face)[0] <= width for x in got):
            return size, got
        size = int(size * 0.94)
    return least, wrap(text, least, width, face)
