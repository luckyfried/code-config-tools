"""The parts every storyboard is built from: the formats and their safe areas, the style cards a board's look is read
from, the design system the composition reads, and type measured from the font files the film sets it in.

A storyboard's times are musical beats from the film's start; its positions are px of the format's frame. The studio
composition (motion/studio) renders a board as it is written here.

A style is a card, styles/<id>.json (its schema is styles/schema.json): two faces, a palette rule, the moves and
transitions a board may use, the easing, the finish, the music recipe, the closer shape, and six axis words. A board
names its style; everything about its look is read from that card and from nothing else."""
import functools
import json
import math
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
FPS = 30
# the three styles a run's boards take when the person names none, one per board: A, B and C
TRIO = ("swiss-grid", "scrapbook", "cinematic-letterbox")
AXES = ("family", "palette", "camera", "transition", "finish", "music")


def load(name):
    return json.loads((SKILL / "design" / f"{name}.json").read_text())


# ------------------------------------------------------------------ style cards
def _check(value, schema, where, out):
    """The subset of JSON Schema the card schema uses: type, required, additionalProperties false, properties, items,
    enum, pattern, minimum, maximum, minItems, maxItems."""
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


def three(named=None):
    """The three styles a run's boards are drawn in: the trio, or the style the person named and the two trio styles
    that share the fewest axes with it (and with each other, between equals), in trio order."""
    if not named:
        return list(TRIO)
    card(named)
    rest = [s for s in TRIO if s != named]
    pairs = [(a, b) for i, a in enumerate(rest) for b in rest[i + 1:]]
    a, b = min(pairs, key=lambda p: (len(shared_axes(named, p[0])) + len(shared_axes(named, p[1])), len(shared_axes(*p))))
    return [named, a, b]


_STYLE = [TRIO[0]]


def use(style):
    """Measure type in `style`'s faces from now on."""
    card(style)
    _STYLE[0] = style


def in_use():
    return card(_STYLE[0])


def system(c, colors):
    """The design system the composition reads, from the style card `c`: the faces, the colors the card's palette rule
    made, the easing, the finish, the closer shape, the photo beat's layout, and the safe areas."""
    safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in load("safe-areas").items() if k != "about"}
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"])), "safe": safe}


# ------------------------------------------------------------------ formats
class Frame:
    """One output format: `name`, `W` x `H` px, and the safe area text stays inside (`top`, `bottom`, `left`, `right`
    px from each edge). With `bars` (a share of the height, the card's letterbox) type also stays clear of the bars."""

    def __init__(self, name, bars=0.0):
        s = load("safe-areas")[name]
        self.name, self.W, self.H = name, s["width"], s["height"]
        self.top, self.bottom, self.left, self.right = s["top"], s["bottom"], s["left"], s["right"]
        self.bars = bars
        if bars:
            clear = math.ceil(bars * self.H) + 24
            self.top, self.bottom = max(self.top, clear), max(self.bottom, clear)

    @property
    def safe(self):
        return (self.left, self.top, self.W - self.right, self.H - self.bottom)

    @property
    def mid(self):
        return (self.W / 2, self.H / 2)


# the films a run renders: the reel is the post, the square and the wide are the same storyboard laid out for a feed
# post and a landscape screen
FORMATS = ("reel", "square", "wide")


@functools.lru_cache(maxsize=64)
def pixels(file):
    """A post's photograph as a small RGB image, for reading the colours a composition lays where, or None when the
    run holds no copy of it."""
    path = Path("public") / file
    if not path.is_file():
        return None
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        return im


# ------------------------------------------------------------------ type, measured
AXIS = {b"Weight": "wght", b"Width": "wdth", b"Optical Size": "opsz", b"Optical size": "opsz", b"Softness": "SOFT", b"Wonky": "WONK"}


@functools.lru_cache(maxsize=512)
def _font(file, size, axes):
    from PIL import ImageFont
    f = ImageFont.truetype(str(SKILL / file), max(1, round(size)))
    try:
        spec = f.get_variation_axes()
    except OSError:
        return f
    want = dict(axes)
    vals = []
    for a in spec:
        tag = AXIS.get(a["name"], "")
        v = want.get(tag)
        if v is None and tag == "opsz":
            v = size
        if v is None:
            v = a["default"]
        vals.append(max(a["minimum"], min(a["maximum"], v)))
    f.set_variation_by_axes(vals)
    return f


def face_of(system_, line):
    return system_["display"] if line.get("face") == "display" else system_["text"]


def cased(system_, face, text):
    """Words in the case the face sets them in, as the film shows them."""
    case = system_["display" if face == "display" else "text"].get("case")
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def font_for(system_, line):
    f = face_of(system_, line)
    axes = dict(f.get("axes") or {})
    axes.setdefault("wght", f.get("weight") or 400)
    return _font(f["file"], line["size"], tuple(sorted(axes.items())))


def text_width(system_, line, text=None):
    f = face_of(system_, line)
    s = line["text"] if text is None else text
    tr = f.get("tracking", 0) or 0
    return font_for(system_, line).getlength(s, features=["kern", "liga"]) + tr * line["size"] * len(s)


def text_box(system_, line, ink=False):
    """The px box a line of type takes: its advance across, and vertically the font's ascent to descent as the browser
    boxes it, or with `ink` the glyphs' own extent."""
    font = font_for(system_, line)
    w = text_width(system_, line)
    x = line["x"] - {"middle": w / 2, "end": w}.get(line.get("anchor"), 0)
    if ink:
        b = font.getbbox(line["text"], anchor="ls", features=["kern", "liga"])
        return (x, line["y"] + b[1], x + w, line["y"] + b[3])
    asc, desc = font.getmetrics()
    return (x, line["y"] - asc, x + w, line["y"] + desc)


def ink(system_, line):
    """A line's ink over and under its baseline, px."""
    b = text_box(system_, line, ink=True)
    return line["y"] - b[1], b[3] - line["y"]


def turned(box, line):
    """The four corners of a px box (x0, y0, x1, y1) of `line` as drawn: turned `rotate` degrees (clockwise on screen)
    about its `pivot`, or about its own origin when it has none."""
    x0, y0, x1, y1 = box
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    a = line.get("rotate") or 0
    if not a:
        return pts
    px, py = line.get("pivot") or (line["x"], line["y"])
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in pts]


def hull(pts):
    """The upright px box (x0, y0, x1, y1) around points."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def fit_size(system_, line, width, lo=12):
    """The largest size (no larger than the line's) at which the line's advance fits `width` px."""
    size = line["size"]
    while size > lo and text_width(system_, dict(line, size=size)) > width:
        size -= 1
    return size


def wrap_measured(system_, line, width, max_lines=3):
    """`line`'s text broken into the fewest lines whose measured advance fits `width` px, as even as the words allow."""
    words = line["text"].split()
    for lines in range(1, min(max_lines, len(words)) + 1):
        def split(ws, m):
            if m == 1:
                yield [" ".join(ws)]
                return
            for i in range(1, len(ws) - m + 2):
                for rest in split(ws[i:], m - 1):
                    yield [" ".join(ws[:i])] + rest
        fits = [c for c in split(words, lines) if max(text_width(system_, line, x) for x in c) <= width]
        if fits:
            return min(fits, key=lambda c: max(text_width(system_, line, x) for x in c))
    return None


def pulse_of(bpm):
    return FPS * 60 / bpm
