"""The transformation film's composition: one storyboard per style, laid out for one format, from the framed posts.

Used by storyboard.py (draft, check, sheets, the other formats), film.py and vote.py. Nothing on screen is typed: every
number is a date or a number in their own captions, and every word comes from their captions, the call to action they
asked for, or their handle.

The story is the kit's own (scripts/tones/drive.py): one camera walks the wall they built from day one to the latest,
in chapters told in their own captions, each photograph lifting out of the wall as a print with their line entering on
it and dropping back into its tile when the camera moves on, so the photographs add up, in calendar order, to the wall
the film ends on. motion/studio/drive renders it.

A style is a card, styles/<id>.json (its schema is styles/schema.json; styles/catalog.md says what each looks like):
two faces, a palette rule, the moves and transitions a board may use, the easing, the finish, the music recipe, and
the closer shape. A board names its style, and everything about its look is read from that card: its type is set in
the card's faces, in their case and tracking; its colors are the ones the card's palette rule makes from their
photographs' colors; the camera's travel takes the card's easing and lean; each beat's move and the cut into it come
from the card's allowlists, chosen by the beat's content; the picture takes the card's finish and ends on its closer.

Three boards are drafted: the trio (TRIO), one board per style, or, when taste.json names a `style`, that style and
the two of the trio whose cards share the fewest axes with it.

Formats: reel (1080x1920), square (1080x1080), landscape (1920x1080). The same posts, beats and timing in every
format; the wall, the stations and the type are solved for each format's own frame and safe lines.
"""
import json
import re
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
STYLES = KIT / "styles"
FPS = 30
FORMATS = ("reel", "square", "landscape")
# the three styles a run's boards take by default, in board order A, B, C
TRIO = ("cinematic-letterbox", "editorial-quiet", "kinetic-type")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
# the colors a run with no photograph colors yet is colored from: a dark, a warm white, a gray and a yellow
NEUTRAL = ("#14161c", "#f3eee4", "#8f94a1", "#ffc93c")


def _design(name):
    return json.loads((KIT / "design" / name).read_text())


# ------------------------------------------------------------------ the cards
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
            if not (KIT / path).is_file():
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
    """The three styles a run's boards take: TRIO, or the style `named` (taste.json `style`) and the two styles of TRIO
    whose cards share the fewest axes with it, in TRIO's order between equals."""
    if not named:
        return list(TRIO)
    card(named)
    rest = sorted((s for s in TRIO if s != named), key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return [named] + rest[:2]


# ------------------------------------------------------------------ type in the card's faces
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


def face_of(face):
    """The card face a line set in `face` ("display", else text) takes, from the style in use."""
    return in_use()["faces"]["display" if face == "display" else "text"]


def cased(text, face="display"):
    """A line's words in its face's case, as the film sets them."""
    case = face_of(face)["case"]
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def font(face, size=200):
    """The PIL font a line in `face` is set in, at `size` px, from the card in use."""
    key = (face == "display", size)
    if key not in _FONTS:
        from PIL import ImageFont
        _FONTS[key] = ImageFont.truetype(str(KIT / face_of(face)["file"]), size)
    return _FONTS[key]


def width(text, size, face="display"):
    """A line's advance in px at `size`, in its face's case and with its face's tracking (em after each letter)."""
    text = cased(text, face)
    return font(face).getlength(text) * size / 200 + face_of(face)["tracking"] * size * len(text)


def cap(face="display"):
    """The face's cap height, in sizes."""
    return -font(face).getbbox("H", anchor="ls")[1] / 200


def descent(face="display"):
    """How far below a baseline the face's descenders reach, in sizes."""
    return font(face).getbbox("gjpqy", anchor="ls")[3] / 200


# ------------------------------------------------------------------ colors and the system
def swatches_of(look):
    """The photographs' colors the card's palette rule reads, as lowercase hexes: their subject's palette and their
    likes' (facts `look`), else the neutral four."""
    out = [str(h).lower() for h in list((look or {}).get("palette") or []) + list((look or {}).get("likes") or [])]
    return [h for h in out if re.fullmatch(r"#[0-9a-f]{6}", h)] or list(NEUTRAL)


def colors_of(c, look):
    """The board's colors: the six roles the card's palette rule made from the photographs' colors, and the turned
    swatches."""
    import palette
    made = palette.palette_of(c["palette"], swatches_of(look))
    return {**made["roles"], "swatches": [{"hex": h, "name": f"swatch {i + 1}"} for i, h in enumerate(made["swatches"])]}


def system(c, colors):
    """The design system the composition reads, from the style card `c`: the faces, the type scale, the colors the
    card's palette rule made, the easing, the finish, the closer shape, the photo layout, and the safe areas."""
    safe = _design("safe-areas.json")
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "scale": {"hero": 250, "h1": 150, "h2": 92, "h3": 60, "body": 40, "label": 30},
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"], "photo": json.loads(json.dumps(c["photo"])),
            "safe": {k: {s: v[s] for s in ("top", "bottom", "left", "right")} for k, v in safe.items() if k != "about"}}


def frame_size(fmt):
    s = _design("safe-areas.json")[fmt]
    return s["width"], s["height"]


def bpm_of(c, seed=""):
    """The board's tempo: the one the music engine plays the style's recipe at for the run `seed`."""
    import music_engine
    return music_engine.tempo(music_engine.recipes()["recipes"][c["music"]], None, None, seed)


def board(style, posts, facts, person, fmt="reel", seed=""):
    """The storyboard of `style` in one format: posts are framing.py's measure rows (dated, oldest first, at least two),
    facts are storyboard.facts(posts), person is {"name", "handle"}, `seed` the run's name (the tempo's)."""
    from tones import drive
    c = card(style)
    use(style)
    colors = colors_of(c, facts.get("look"))
    b = drive.build(posts, facts, person, fmt, {f: frame_size(f) for f in FORMATS}, style=c, colors=colors, bpm=bpm_of(c, seed))
    b["system"] = system(c, colors)
    return b
