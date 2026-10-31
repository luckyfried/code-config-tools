"""The styles a year is drawn in, and the type measured in them.

A style is a card, styles/<id>.json (its schema is styles/schema.json): two faces, a palette rule, the moves and
transitions a board may use, the easing, the finish, the music recipe, the closer shape and six axis words. A board
names its style; everything about its look is read from that card and from nothing else. styles/catalog.md says in
one sentence what each looks like.

The kit draws three boards: the TRIO by default, or the style the person named and the two styles whose cards share
the fewest axes with it. A beat's move and the cut into it are chosen from what the beat shows, within the card's
allowlists (`pick`); `findings` names every way a set of boards breaks its cards or reads like a template."""
import json
import math
import re
from pathlib import Path

import _env

STYLES = _env.SKILL / "styles"
# the three styles a run's boards take when the person names none, one per board in this order
TRIO = ("analog-home-movie", "kinetic-type", "swiss-grid")
AXES = ("family", "palette", "camera", "transition", "finish", "music")


def validate(c):
    """The rules a card must keep for this kit to draw it: its two faces on disk, its palette rule, its moves,
    transitions and closer named, its music recipe named for the style."""
    out = []
    for k in ("id", "faces", "palette", "moves", "transitions", "ease", "finish", "music", "closer", "axes"):
        if k not in c:
            out.append(f"it has no {k}")
    if out:
        return out
    for k in ("display", "text"):
        f = c["faces"].get(k) or {}
        for path in [f.get("file")] + ([f["italic"]] if f.get("italic") else []):
            if not path or not (_env.SKILL / path).is_file():
                out.append(f"the {k} face's file {path} is not on disk")
    if c["music"] != c["id"]:
        out.append(f"its music recipe is {c['music']!r}; a style's recipe is named for the style")
    return out


_CARDS = {}


def card(style):
    """The style card `style`, or SystemExit naming the styles there are and what the card breaks."""
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


def trio_for(named=None):
    """The three styles a run draws: the TRIO, or the style the person named first and then the two styles that share
    the fewest axes with it and with each other (between equals, the TRIO's order, then the catalog's)."""
    if not named:
        return TRIO
    card(named)
    order = [s for s in TRIO if s != named] + [s for s in styles() if s not in TRIO and s != named]
    second = min(order, key=lambda s: (len(shared_axes(named, s)), order.index(s)))
    rest = [s for s in order if s != second]
    third = min(rest, key=lambda s: (len(shared_axes(named, s)) + len(shared_axes(second, s)), rest.index(s)))
    return (named, second, third)


def sentence(style):
    """The style in one plain sentence, for the person: its row in styles/catalog.md."""
    for row in (STYLES / "catalog.md").read_text().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return cells[1]
    return ""


def title_of(style):
    """The style's name as a person reads it: its id in words."""
    return style.replace("-", " ").capitalize()


_STYLE = [TRIO[0]]
_FONTS = {}


def use(style):
    """Measure type in `style`'s faces from now on (every measure and box_of call reads the card in use)."""
    card(style)
    if _STYLE[0] != style:
        _STYLE[0] = style
        _FONTS.clear()


def in_use():
    return card(_STYLE[0])


def system(c, colors, safe):
    """The design system the composition reads, from the style card `c`: the faces, the type scale, the colors the
    card's palette rule made, the easing, the finish, the closer shape, the photo layout and the safe areas."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "scale": {"hero": 250, "h1": 150, "h2": 92, "h3": 60, "body": 40, "label": 30},
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"])), "safe": safe}


def colors_of(c, swatches):
    """A board's colors: the six roles the card's palette rule made from the photographs' swatches, and the swatches
    as the rule turned them."""
    import palette
    made = palette.palette_of(c["palette"], swatches)
    return {**made["roles"], "swatches": [{"hex": h, "name": f"swatch {i + 1}"} for i, h in enumerate(made["swatches"])]}


def face_of(face):
    """The card face a line set in `face` ("display", else text) takes, from the style in use."""
    return in_use()["faces"]["display" if face == "display" else "text"]


def cased(text, face="display"):
    """A line's words in its face's case, as the film sets them."""
    case = face_of(face).get("case", "none")
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def _font(size, face):
    key = (size, face)
    if key not in _FONTS:
        from PIL import ImageFont
        _FONTS[key] = ImageFont.truetype(str(_env.SKILL / face_of(face)["file"]), size)
    return _FONTS[key]


def measure(text, size, face="display", weight=None):
    """A line's advance width, cap height and left side bearing in px, from the font file the film sets it in, in its
    face's case and with its face's tracking (em after each letter)."""
    f = _font(size, "display" if face == "display" else "text")
    text = cased(text, face)
    track = face_of(face).get("tracking", 0) * size * len(text)
    return f.getlength(text) + track, -f.getbbox("H", anchor="ls")[1], f.getbbox(text, anchor="ls")[0] if text else 0


def box_of(ln):
    """A line's box at rest in its frame, [x0, y0, x1, y1] px: ascender to descender, turned about its pivot."""
    face = "display" if ln.get("face") == "display" else "text"
    f = _font(ln["size"], face)
    text = cased(ln["text"], face)
    l, t, r, b = f.getbbox(text, anchor="ls")
    w = f.getlength(text) + face_of(face).get("tracking", 0) * ln["size"] * len(text)
    r = max(r, w)
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


def set_lines(lines):
    """Every line in `lines` (any nesting of the board's year) in its face's case and with its face's tracking, as
    measure and box_of read it and the film draws it."""
    if isinstance(lines, list):
        for v in lines:
            set_lines(v)
    elif isinstance(lines, dict):
        if isinstance(lines.get("text"), str) and "size" in lines and "face" in lines:
            lines["text"] = cased(lines["text"], lines["face"])
            if face_of(lines["face"]).get("tracking"):
                lines["tracking"] = face_of(lines["face"])["tracking"]
        for v in lines.values():
            if isinstance(v, (dict, list)):
                set_lines(v)


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once); between equals the
    one used least so far, then the card's order. The option `avoid` (the previous beat's) is never picked while
    another exists."""
    pool = [o for o in options if o["id"] != avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def hexes_in(o):
    """Every hex color a board's year names (a role name is the system's own color)."""
    if isinstance(o, dict):
        return [h for k, v in o.items() for h in ([v.lower()] if k == "color" and isinstance(v, str) and v.startswith("#") else hexes_in(v))]
    if isinstance(o, list):
        return [h for v in o for h in hexes_in(v)]
    return []


HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def findings(boards, swatches, shown_of):
    """The template tells and style breaks a set of boards ({style: board}) has, each one plain sentence naming the
    board and the rule: two styles sharing more than two of the six axes; a face not in the board's card; a move or
    transition outside the card's allowlist; a color the card's palette rule did not make; every shot within 10 % of
    one length; the words in one place on more than 70 % of the beats that carry words; the same move on consecutive
    beats. `shown_of(board, beat)` gives the boxes of the words a beat shows at rest."""
    import palette
    out = []
    names = list(boards)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            same = shared_axes(a, b)
            if len(same) > 2:
                out.append(f"{a} and {b} share {len(same)} of the six axes ({', '.join(same)}), more than two; draw one of them in a "
                           "style that differs more")
    for n, b in boards.items():
        c = card(b.get("style") or n)
        use(c["id"])
        s = b["system"]
        for k in ("display", "text"):
            if (s[k]["family"], s[k]["file"]) != (c["faces"][k]["family"], c["faces"][k]["file"]):
                out.append(f"{n}: its {k} face {s[k]['family']} is not the {k} face of {c['id']} ({c['faces'][k]['family']})")
        moves, cuts = ids(c, "moves"), ids(c, "transitions")
        for bt in b["beats"]:
            if bt.get("move") not in moves:
                out.append(f"{n}: beat {bt['id']} moves by {bt.get('move')!r}, which is not a move of {c['id']} ({', '.join(moves)})")
            if bt.get("transition") is not None and bt["transition"] not in cuts:
                out.append(f"{n}: beat {bt['id']} is cut to by {bt['transition']!r}, which is not a transition of {c['id']} ({', '.join(cuts)})")
        made = set(palette.palette_of(c["palette"], swatches)["made"])
        shown = [v.lower() for k, v in s["colors"].items() if k != "swatches"] + [w["hex"].lower() for w in s["colors"].get("swatches") or []]
        for h in sorted(set(shown + hexes_in(b["year"])) - made):
            out.append(f"{n}: it shows {h}, a color the {c['palette']['rule']} palette rule of {c['id']} did not make from the photographs")
        lengths = sorted(bt["frames"] for bt in b["beats"])
        if len(lengths) >= 3:
            mid = lengths[len(lengths) // 2]
            if all(abs(x - mid) <= 0.1 * mid for x in lengths):
                out.append(f"{n}: every shot runs within 10 % of {mid} frames; vary the beats' lengths")
        W, H = b["format"]["width"], b["format"]["height"]
        # every month sets its words where the card's photo layout puts them, so the months count as one layout
        cells, photos = [], []
        for bt in b["beats"]:
            boxes = shown_of(b, bt)
            if boxes:
                cx = (min(x[0] for x in boxes) + max(x[2] for x in boxes)) / 2
                cy = (min(x[1] for x in boxes) + max(x[3] for x in boxes)) / 2
                (photos if bt["form"] == "photo" else cells).append((min(2, max(0, int(3 * cx / W))), min(2, max(0, int(3 * cy / H)))))
        if photos:
            cells.append(max(set(photos), key=photos.count))
        if len(cells) >= 3:
            top = max(set(cells), key=cells.count)
            if cells.count(top) > 0.7 * len(cells):
                where = ("top", "middle", "bottom")[top[1]] + " " + ("left", "center", "right")[top[0]]
                out.append(f"{n}: the words sit in one place, the {where} of the frame, on {cells.count(top)} of the {len(cells)} "
                           "beats that carry words; move them with what each beat shows")
        for x, y in zip(b["beats"], b["beats"][1:]):
            if x.get("move") and x.get("move") == y.get("move"):
                out.append(f"{n}: beats {x['id']} and {y['id']} both move by {x['move']}; consecutive beats move differently")
    return out
