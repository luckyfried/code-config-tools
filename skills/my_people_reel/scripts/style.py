"""The film's styles: the style cards in styles/ (faces, palette rule, moves, transitions, easing, finish, music recipe
and closer), which three a run drafts, the system a board carries from its card, the choice of a beat's move and
transition from what the beat shows, and the checks that hold a board to its card.

The three a run drafts are the TRIO, in that order (A, B, C); when the person names a style (taste.json `style`, or
`storyboard.py draft --style`), it is board A and the two of the TRIO that share the fewest of the six axes with it
are B and C.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SKILL = Path(__file__).resolve().parent.parent
STYLES = SKILL / "styles"
TRIO = ("scrapbook", "analog-home-movie", "kinetic-type")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
NEEDS = ("id", "name", "faces", "palette", "moves", "transitions", "ease", "finish", "music", "closer", "axes")

_CARDS = {}


def styles():
    """Every style id there is a card for."""
    return sorted(f.stem for f in STYLES.glob("*.json") if f.stem != "schema")


def card(style):
    """The style card `style`, or SystemExit naming the styles there are and what the card lacks."""
    if style not in _CARDS:
        f = STYLES / f"{style}.json"
        if not f.is_file():
            raise SystemExit(f"no style named {style!r} (there are: {', '.join(styles())}); styles/catalog.md says what each looks like")
        c = json.loads(f.read_text())
        bad = [k for k in NEEDS if k not in c]
        bad += [f"the {k} face's file {v['file']}" for k, v in c.get("faces", {}).items() if not (SKILL / v["file"]).is_file()]
        if bad:
            raise SystemExit(f"styles/{style}.json is not a style card: it lacks " + ", ".join(bad))
        _CARDS[style] = c
    return _CARDS[style]


def shared_axes(a, b):
    """The axes on which two styles' cards name the same word."""
    ca, cb = card(a), card(b)
    return [k for k in AXES if ca["axes"][k] == cb["axes"][k]]


def ids(c, kind):
    """The move or transition ids a card allows (`kind` is "moves" or "transitions")."""
    return [m["id"] for m in c[kind]]


def trio_for(named=None):
    """The three styles a run drafts, A first: the TRIO, or the named style and the two of the TRIO that differ most
    from it (fewest shared axes, the TRIO's order between equals)."""
    if not named:
        return TRIO
    card(named)
    others = [s for s in TRIO if s != named]
    others.sort(key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return (named, *others[:2])


def system(c, colors):
    """The system a board carries from card `c`: its faces, the colors its palette rule made, its easing, its finish
    and its closer."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"]))}


def cased(text, face):
    """A line's words in the case its card face sets them in."""
    case = face.get("case")
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


SHAPES = {"landscape", "portrait"}


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once); between equals the
    one used least so far, then the card's order. The option `avoid` (the previous beat's) is never picked while another
    exists, nor one made for the other shape of photograph (a portrait's push on a landscape laid whole)."""
    shape = SHAPES & tags
    pool = [o for o in options if o["id"] != avoid] or options
    pool = [o for o in pool if not shape or not (SHAPES & set(o["fits"])) or shape & set(o["fits"])] or pool
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def hexes(board):
    """Every hex color a board's layers name."""
    out = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str) and v.startswith("#") and len(v) in (4, 7):
            out.add(v.lower())
    walk(board["beats"])
    return out


def findings(boards, swatches):
    """The ways a set of laid-out boards ({style: board}) breaks its cards, one plain sentence each naming the board:
    two styles sharing more than two of the six axes; a face not the card's; a move or transition outside the card's
    allowlist; a color the card's palette rule did not make; every shot within 10 % of one length; the same move on
    consecutive beats."""
    import palette
    out = []
    names = list(boards)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            same = shared_axes(a, b)
            if len(same) > 2:
                out.append(f"boards {a} and {b} share {len(same)} of the six axes ({', '.join(same)}), more than two")
    for n, b in boards.items():
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
                out.append(f"board {n}: beat {bt['id']} is cut to by {bt['transition']!r}, which is not a transition of {c['id']} ({', '.join(cuts)})")
        made = set(palette.palette_of(c["palette"], swatches)["made"])
        shown = {v.lower() for k, v in s["colors"].items() if isinstance(v, str)} | hexes(b)
        for h in sorted(shown - made):
            out.append(f"board {n}: it shows {h}, a color the {c['palette']['rule']} palette rule of {c['id']} did not make")
        lengths = sorted(bt["frames"] for bt in b["beats"])
        if len(lengths) >= 3:
            mid = lengths[len(lengths) // 2]
            if all(abs(x - mid) <= 0.1 * mid for x in lengths):
                out.append(f"board {n}: every shot runs within 10 % of {mid} frames; vary the beats' lengths")
        for x, y in zip(b["beats"], b["beats"][1:]):
            if x.get("move") and x.get("move") == y.get("move"):
                out.append(f"board {n}: beats {x['id']} and {y['id']} both move by {x['move']}; consecutive beats move differently")
    return out


def sentence(style):
    """The style in one plain sentence, for the person: its row in styles/catalog.md."""
    for row in (STYLES / "catalog.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return cells[1]
    return ""
