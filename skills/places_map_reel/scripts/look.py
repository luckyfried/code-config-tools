"""The look a board is drawn in: the style cards (styles/<id>.json, copied in from video_studio), the colors a card's
palette rule makes from the person's photographs, the move and transition each beat takes from its card, the design
system the composition reads, and the checks that hold a set of boards to their cards.

A board names its style; every face, color, easing, finish value, move and closer it shows is read from that card and
from nothing else. A beat's move is the card's move that fits what the beat shows (pick); the travel between two places
is the kit's own and is read from the map.
"""
import json
import re
from pathlib import Path

from palette import contrast, from_hls, hex_rgb, hexc, hls, lum

SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
# the three styles a run's boards take by default, A, B and C
TRIO = ("swiss-grid", "cinematic-letterbox", "scrapbook")
AXES = ("family", "palette", "camera", "transition", "finish", "music")


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


def trio_for(named=None):
    """The three styles a run's boards take: the trio, or the style the person named and the two of the trio that share
    the fewest axes with it (the trio's order between equals)."""
    if not named:
        return TRIO
    card(named)
    rest = sorted((s for s in TRIO if s != named), key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return (named, *rest[:2])


def sentence(style):
    """The style's one sentence for the person, from styles/catalog.md."""
    for row in (STYLES / "catalog.md").read_text().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return cells[1]
    return card(style)["name"]


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


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once); between equals the
    one used least so far, then the card's order. The option `avoid` (the previous beat's) is never picked while another
    exists."""
    pool = [o for o in options if o["id"] != avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def system(c, colors, safe):
    """The design system the composition reads, from the style card `c`: its faces, the colors its palette rule made,
    its easing, its finish, its closer shape, how it lays out a photograph and its words, and the profiles' safe areas."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "scale": {"hero": 250, "h1": 150, "h2": 92, "h3": 60, "body": 40, "label": 30},
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"], "photo": json.loads(json.dumps(c["photo"])), "safe": safe}


def cased(text, face):
    """A line's words in the case of `face` (a card face), as the film sets them."""
    return text.upper() if face["case"] == "uppercase" else text.lower() if face["case"] == "lowercase" else text


# the moves whose overlay lays a field over the whole frame (a page, a margin, a print's frame, a fade to black): drawn
# over a stop's photograph they would hide the words the card's layout sets, so a stop never takes one
COVERS = {"polaroid-drop", "long-fade-title", "page-drift", "tape-slap"}
# the moves that open on a black frame: the hook shows the whole route and the dot in its first second, so it never takes one
DARK = {"bars-open"}


def hexes_in(o):
    """Every hex color a board's layers name (a role name is the system's own color)."""
    if isinstance(o, dict):
        return [h for k, v in o.items() for h in ([v.lower()] if k == "color" and isinstance(v, str) and v.startswith("#") else hexes_in(v))]
    if isinstance(o, list):
        return [h for v in o for h in hexes_in(v)]
    return []


def style_findings(boards, swatches):
    """The template tells and style breaks a set of boards ({name: board}) has, each one plain sentence naming the board
    and the rule: three boards whose styles share more than two of the six axes pairwise; a face not the card's; a move
    or transition outside the card's allowlist; a color the card's palette rule did not make from the photographs; every
    shot within 10 % of one length; words in one third of the frame on more than 70 % of the layouts that carry words (the hook, the closer, and the photo
    beats together as their card's one layout); the
    same move on consecutive beats."""
    out = []
    names = list(boards)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sa, sb = boards[a].get("style"), boards[b].get("style")
            if sa and sb:
                same = shared_axes(sa, sb)
                if len(same) > 2:
                    out.append(f"boards {a} and {b}: their styles ({sa}, {sb}) share {len(same)} of the six axes ({', '.join(same)}), "
                               "more than two; give one of them a style that differs more")
    for n, b in boards.items():
        if not b.get("style"):
            out.append(f"board {n}: it names no style; draft it again so it carries one")
            continue
        c = card(b["style"])
        s = b["system"]
        for k in ("display", "text"):
            if (s[k]["family"], s[k]["file"]) != (c["faces"][k]["family"], c["faces"][k]["file"]):
                out.append(f"board {n}: its {k} face {s[k]['family']} is not the {k} face of {c['id']} ({c['faces'][k]['family']})")
        moves, cuts = ids(c, "moves"), ids(c, "transitions")
        for bt in b["beats"]:
            if bt.get("move") not in moves:
                out.append(f"board {n}: beat {bt['id']} moves by {bt.get('move')!r}, which is not a move of {c['id']} ({', '.join(moves)})")
            if bt.get("transition") is not None and bt["transition"] not in cuts:
                out.append(f"board {n}: beat {bt['id']} is cut to by {bt['transition']!r}, which is not a transition of {c['id']} "
                           f"({', '.join(cuts)})")
        made = set(palette_of(c["palette"], swatches)["made"])
        shown = [v.lower() for k, v in s["colors"].items() if k != "swatches"] + [w.lower() for w in s["colors"].get("swatches") or []]
        shown += [v.lower() for v in (b.get("route") or {}).get("colors", {}).values()]
        for h in sorted(set(shown + hexes_in(b["beats"]) + hexes_in(b.get("route") or {})) - made):
            out.append(f"board {n}: it shows {h}, a color the {c['palette']['rule']} palette rule of {c['id']} did not make from the photographs")
        lengths = sorted(bt.get("frames") or round(bt["bars"] * 4 * 30 * 60 / b["bpm"]) for bt in b["beats"])
        if len(lengths) >= 3:
            mid = lengths[len(lengths) // 2]
            if all(abs(x - mid) <= 0.1 * mid for x in lengths):
                out.append(f"board {n}: every shot runs within 10 % of {mid} frames; vary the beats' lengths")
        H = b["format"]["height"]
        # every photo beat sets its words where the card's photo layout puts them, so the photo beats are one layout
        # and count once, in the third most of them take
        cells = [min(2, max(0, int(3 * bt["words_at"]))) for bt in b["beats"] if bt.get("words_at") is not None and bt.get("form") != "photo"]
        photos = [min(2, max(0, int(3 * bt["words_at"]))) for bt in b["beats"] if bt.get("words_at") is not None and bt.get("form") == "photo"]
        if photos:
            cells.append(max(set(photos), key=photos.count))
        if len(cells) >= 3:
            top = max(set(cells), key=cells.count)
            if cells.count(top) > 0.7 * len(cells):
                out.append(f"board {n}: the words sit in one place, the {('top', 'middle', 'bottom')[top]} of the frame, on "
                           f"{cells.count(top)} of the {len(cells)} beats that carry words; move them with what each beat shows")
        for x, y in zip(b["beats"], b["beats"][1:]):
            if x.get("move") and x.get("move") == y.get("move"):
                out.append(f"board {n}: beats {x['id']} and {y['id']} both move by {x['move']}; consecutive beats move differently")
    return out
