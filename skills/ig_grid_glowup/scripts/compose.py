"""The style cards a board's look is read from, and type measured from the font files the film sets it in.

A style is a card, styles/<id>.json (its schema is styles/schema.json): two faces, a palette rule, the moves and
transitions a board may use, the easing, the finish, the music recipe, the closer shape, and six axis words. A board
names its style; everything about its look is read from that card and from nothing else. The kit's story (the grid
before, the next posts coming into it, the profile after) is the same in every style."""
import json
from pathlib import Path

import _env

SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
# the three boards a run drafts by default, A, B and C: a grid of hard cuts and one accent, type that slams on the
# beat, and a quiet editorial page; a named style takes A and the two of these that differ most from it take B and C
TRIO = ("swiss-grid", "kinetic-type", "editorial-quiet")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
LETTERS = "ABC"


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


def trio(style=None):
    """The three styles a run drafts, A first: the trio, or `style` and the two trio styles that share the fewest axes
    with it (the trio's order on a tie)."""
    if not style or style in TRIO:
        first = style or TRIO[0]
        return [first] + [s for s in TRIO if s != first]
    card(style)
    rest = sorted(TRIO, key=lambda s: (len(shared_axes(style, s)), TRIO.index(s)))
    return [style] + rest[:2]


def ids(c, kind):
    """The move or transition ids a card allows (`kind` is "moves" or "transitions")."""
    return [m["id"] for m in c[kind]]


_STYLE = [TRIO[0]]
_FONTS = {}


def use(style):
    """Measure type in `style`'s faces from now on (every measure reads the card in use)."""
    card(style)
    if _STYLE[0] != style:
        _STYLE[0] = style
        _FONTS.clear()


def in_use():
    return card(_STYLE[0])


def system(c, colors, safe):
    """The design system the composition reads, from the style card `c`: the faces, the colors the card's palette rule
    made, the easing, the finish, the closer shape, the photo beat's layout (the face, size, color and entrance of a
    post's caption), and the safe areas (`safe`, by format)."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"])), "safe": safe}


def pick(options, tags, form, used, avoid=None):
    """The move (or transition) of `options`, a card's allowlist, that fits what the beat shows: its form counts twice,
    each other tag of the beat once, then the one used least so far, then the card's own order; never `avoid` (the
    previous beat's) while another is left. Counts the choice in `used`."""
    pool = [o for o in options if o["id"] != avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((set(tags) - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def face_of(face):
    """The card face a line set in `face` ("display", else text) takes, from the style in use."""
    return in_use()["faces"]["display" if face == "display" else "text"]


def cased(text, face="display"):
    """A line's words in its face's case, as the film sets them."""
    case = face_of(face)["case"]
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def em(text, face="text"):
    """A line's advance width in em, from the font file the film sets it in, in its face's case and with its face's
    tracking (em after each letter)."""
    if face not in _FONTS:
        _FONTS[face] = _env.pil_font(1000, "display" if face == "display" else "text")
    text = cased(text, face)
    return _FONTS[face].getlength(text) / 1000 + face_of(face)["tracking"] * len(text)


def cap(face="text"):
    """The face's cap height in em."""
    key = ("cap", face)
    if key not in _FONTS:
        f = _env.pil_font(1000, "display" if face == "display" else "text")
        _FONTS[key] = -f.getbbox("H", anchor="ls")[1] / 1000
    return _FONTS[key]
