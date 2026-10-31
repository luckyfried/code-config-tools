#!/usr/bin/env python3
"""The looks a trip film is drawn in. A look is a style card, styles/<id>.json (its schema is styles/schema.json): two
faces, a palette rule, the moves and transitions a board may use and the beats each fits, the easing, the finish, the
music recipe, the closer, and six axis words. A board names its style; everything about how it looks is read from that
card and from nothing else.

A run drafts three boards in three looks. By default they are the trio below; when the person names a look, it is board
1's and boards 2 and 3 take the two of the trio that share the fewest axes with it."""
import json
from pathlib import Path

import palette

SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
TRIO = ("cinematic-letterbox", "analog-home-movie", "scrapbook")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
MOST_SHARED = 2  # two looks of one run may name the same word on at most this many axes
SAFE = {k: v for k, v in json.loads((SKILL / "design" / "safe-areas.json").read_text()).items() if k != "about"}

_CARDS = {}


def styles():
    """Every style id there is a card for."""
    return sorted(f.stem for f in STYLES.glob("*.json") if f.stem != "schema")


def missing(c):
    """What a card lacks that a board reads, as plain lines (empty when it is whole)."""
    out = [f"no {k}" for k in ("id", "faces", "palette", "moves", "transitions", "ease", "finish", "closer", "axes", "music")
           if k not in c]
    for k in ("display", "text"):
        f = (c.get("faces") or {}).get(k) or {}
        for path in [f.get("file")] + ([f["italic"]] if f.get("italic") else []):
            if not path or not (SKILL / path).is_file():
                out.append(f"the {k} face's file {path} is not on disk")
    return out


def card(style):
    """The style card `style`, or SystemExit naming the looks there are."""
    if style not in _CARDS:
        f = STYLES / f"{style}.json"
        if not f.is_file():
            raise SystemExit(f"no look named {style!r} (there are: {', '.join(styles())}); styles/catalog.md says what each looks like")
        c = json.loads(f.read_text())
        bad = missing(c)
        if bad:
            raise SystemExit(f"styles/{style}.json is not a whole style card: " + "; ".join(bad))
        _CARDS[style] = c
    return _CARDS[style]


def shared_axes(a, b):
    """The axes on which two looks' cards name the same word."""
    ca, cb = card(a), card(b)
    return [k for k in AXES if ca["axes"][k] == cb["axes"][k]]


def ids(c, kind):
    """The move or transition ids a card allows (`kind` is "moves" or "transitions")."""
    return [m["id"] for m in c[kind]]


def three(named=None):
    """The run's three looks: the trio, or the named look and the two of the trio that share fewest axes with it."""
    if not named:
        return list(TRIO)
    card(named)
    rest = sorted((s for s in TRIO if s != named), key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return [named] + rest[:2]


def too_close(looks):
    """Each pair of looks that shares more than MOST_SHARED axes, as plain lines."""
    out = []
    for i, a in enumerate(looks):
        for b in looks[i + 1:]:
            same = shared_axes(a, b)
            if len(same) > MOST_SHARED:
                out.append(f"the looks {a} and {b} share {len(same)} of the 6 axes ({', '.join(same)}); two looks of one run share at most {MOST_SHARED}")
    return out


def colors(c, swatches):
    """The board's colors from the card's palette rule and the photographs' swatches (palette.roles_of)."""
    return palette.roles_of(c["palette"], swatches)


def face_files(c):
    """Every font file the card names, relative to the skill folder."""
    return sorted({p for f in c["faces"].values() for p in [f["file"]] + ([f["italic"]] if f.get("italic") else [])})


def system(c, roles):
    """The design system the composition reads for a board in this look."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "colors": dict(roles), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"])), "safe": SAFE}


def tags_of(beat):
    """The words a beat answers to in a card's `fits` lists."""
    return {t for t in beat.get("tags", []) if t} | {beat["form"]}


def pick(options, tags, form, used, avoid):
    """The move or transition for a beat: the option whose `fits` best matches the beat's form and content, the one used
    least so far on a tie, never `avoid` (the previous beat's move) when another is allowed."""
    pool = [o for o in options if o["id"] != avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def sentence(style):
    """The look in one sentence, for the person, from styles/catalog.md."""
    for line in (STYLES / "catalog.md").read_text().splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return cells[1]
    return card(style).get("name") or style
