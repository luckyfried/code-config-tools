"""The style cards a hype reel's look is read from, the design system the composition reads, and type measured from
the font files the film sets it in.

A style is a card, styles/<id>.json (its schema is styles/schema.json): two faces, a palette rule, the moves and
transitions a board may use, the easing, the finish, the music recipe, the closer shape, and six axis words. A board
names its style; everything about its look is read from that card and from nothing else.

The kit drafts three boards from three styles: by default TRIO, one board each; a person who names a style gets it and
the two styles of TRIO that share the fewest axes with it."""
import json
from pathlib import Path

import _env

SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
# the three styles a run's boards take by default, one per board in this order
TRIO = ("kinetic-type", "cinematic-letterbox", "swiss-grid")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
# the shared moves a hype reel adds to a card's own: the reveal or a photograph of the subject coming apart into its
# printed planes on the grid look, whose card names it nowhere else
MORE_MOVES = {"swiss-grid": [{"id": "exploded-layers", "fits": ["photo", "peak"]}]}
# where type may sit, per format, in px from each edge
SAFE = {k: v for k, v in json.loads((SKILL / "design" / "safe-areas.json").read_text()).items() if k != "about"}


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
    """The style card `style`, validated, with the moves MORE_MOVES adds to it, or SystemExit naming the styles there are and what the card breaks."""
    if style not in _CARDS:
        f = STYLES / f"{style}.json"
        if not f.is_file():
            raise SystemExit(f"no style named {style!r} (there are: {', '.join(styles())}); styles/catalog.md says what each looks like")
        c = json.loads(f.read_text())
        bad = validate(c)
        if bad:
            raise SystemExit(f"styles/{style}.json is not a style card: " + "; ".join(bad))
        have = {m["id"] for m in c["moves"]}
        _CARDS[style] = {**c, "moves": c["moves"] + [m for m in MORE_MOVES.get(style, []) if m["id"] not in have]}
    return _CARDS[style]


def styles():
    """Every style id there is a card for."""
    return sorted(f.stem for f in STYLES.glob("*.json") if f.stem != "schema")


def shared_axes(a, b):
    """The axes on which two styles' cards name the same word."""
    ca, cb = card(a), card(b)
    return [k for k in AXES if ca["axes"][k] == cb["axes"][k]]


def trio_for(named=None):
    """The three styles a run drafts: TRIO, or the style the person named and the two of TRIO that share the fewest axes
    with it (between equals, TRIO's order)."""
    if not named or named in TRIO:
        return list(TRIO) if not named else [named] + [s for s in TRIO if s != named]
    card(named)
    rest = sorted(TRIO, key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return [named] + rest[:2]


def ids(c, kind):
    """The move or transition ids a card allows (`kind` is "moves" or "transitions")."""
    return [m["id"] for m in c[kind]]


_STYLE = [TRIO[0]]


def use(style):
    """Measure type in `style`'s faces from now on (every measure reads the card in use)."""
    card(style)
    if _STYLE[0] != style:
        _STYLE[0] = style
        _FONTS.clear()


def in_use():
    return card(_STYLE[0])


def system(c, colors):
    """The design system the composition reads, from the style card `c`: the faces, the colors the card's palette rule
    made, the easing, the finish, the closer shape, the photo layout, the camera, and the safe areas."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"])), "camera": c["axes"]["camera"],
            "safe": {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in SAFE.items()}}


_FONTS = {}


def face_of(face):
    """The card face a line set in `face` ("display", else text) takes, from the style in use."""
    return in_use()["faces"]["display" if face == "display" else "text"]


def cased(text, face="display"):
    """A line's words in its face's case, as the film sets them."""
    case = face_of(face)["case"]
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def font(size, face="display"):
    """The face's font file at `size` px, at the weight the card names."""
    key = (size, face)
    if key not in _FONTS:
        _FONTS[key] = _env.pil_font(size, "display" if face == "display" else "text")
    return _FONTS[key]


def width(text, size, face="display"):
    """A line's advance in px at `size`, in its face's case and with its face's tracking (em after each letter)."""
    text = cased(text, face)
    f = font(200, face)
    return f.getlength(text) * size / 200 + face_of(face)["tracking"] * size * len(text)


def cap(face="display"):
    """The face's capital height in em."""
    b = font(200, face).getbbox("H", anchor="ls")
    return -b[1] / 200


def fit(text, want, room, face="display"):
    """The size `text` is set at: `want` px, smaller where that would run wider than `room`."""
    return min(want, want * room / max(1.0, width(text, want, face)))
