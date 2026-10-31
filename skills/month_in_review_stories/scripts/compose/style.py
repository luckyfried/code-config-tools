"""The styles a month's boards are drawn in. A style is a card, styles/<id>.json, copied in from video_studio: two
faces, a palette rule, the moves and transitions a board may use, the easing, the finish, the music recipe, the closer
shape, and six axis words. A board is this kit's story of the month drawn in one card's style, and everything about its
look is read from that card.

The three boards take TRIO, one style each; when the person names a style, it is the first board's and the other two
are the two of TRIO that share the fewest axes with it. Each beat's move, and the cut into it, is chosen from what the
beat shows (`pick`), within the card's allowlists, which take this kit's trailer moves (GRAMMAR) beside the card's
own."""
import json
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
STYLES = KIT / "styles"
TRIO = ("editorial-quiet", "scrapbook", "swiss-grid")
AXES = ("family", "palette", "camera", "transition", "finish", "music")

# the trailer moves this kit adds to a shared card's own (motion/system/moves/move): a look that wants energy takes them
# ahead of its own moves, as its grammar (a tunnel of the month's photographs, a wall of prints swinging flat, a
# photograph coming apart into its layers, the moment's name slammed in word by word, its figure counted up); a calm
# look takes the one its card marks `once`, so it plays on one beat of a film at most
GRAMMAR = {
    "swiss-grid": [{"id": "picture-tunnel", "fits": ["photo", "landscape", "place"]},
                   {"id": "exploded-layers", "fits": ["photo", "people", "portrait"]},
                   {"id": "tilted-wall", "fits": ["photo", "wall"]},
                   {"id": "slam-words", "fits": ["photo", "words", "peak"]},
                   {"id": "counter", "fits": ["photo", "peak"]}],
    "kinetic-type": [{"id": "picture-tunnel", "fits": ["photo", "landscape", "place"]},
                     {"id": "exploded-layers", "fits": ["photo", "people", "portrait"]},
                     {"id": "tilted-wall", "fits": ["photo", "wall"]},
                     {"id": "slam-words", "fits": ["photo", "words", "peak"]},
                     {"id": "counter", "fits": ["photo", "peak"]}],
    "cinematic-letterbox": [{"id": "picture-tunnel", "fits": ["photo", "peak", "place"]},
                            {"id": "tilted-wall", "fits": ["photo", "people", "wall"]}],
}

_CARDS = {}


def styles():
    """Every style id there is a card for."""
    return sorted(f.stem for f in STYLES.glob("*.json") if f.stem != "schema")


def moves_of(style, own):
    """The card's moves with this kit's trailer moves: GRAMMAR's after the first (the title's) and ahead of the rest, so
    they win a beat they fit as well as the card's own."""
    lead = [dict(m) for m in GRAMMAR.get(style, []) if m["id"] not in {o["id"] for o in own[:1]}]
    ids = {m["id"] for m in lead}
    return own[:1] + lead + [m for m in own[1:] if m["id"] not in ids]


def card(style):
    """The style card `style`, its moves with this kit's trailer moves (moves_of), or ValueError naming the styles there
    are."""
    if style not in _CARDS:
        f = STYLES / f"{style}.json"
        if not f.is_file():
            raise ValueError(f"no style named {style!r}; the styles are {', '.join(styles())}")
        c = json.loads(f.read_text())
        for k, face in c["faces"].items():
            if not (KIT / face["file"]).is_file():
                raise ValueError(f"styles/{style}.json: the {k} face's file {face['file']} is not in the kit")
        _CARDS[style] = {**c, "moves": moves_of(style, c["moves"])}
    return _CARDS[style]


def shared_axes(a, b):
    """The axes on which two styles' cards name the same word."""
    ca, cb = card(a), card(b)
    return [k for k in AXES if ca["axes"][k] == cb["axes"][k]]


def trio(named=None):
    """The three styles the boards are drawn in: TRIO, else the named style first and the two of TRIO that share the
    fewest axes with it (TRIO's order between equals)."""
    if not named:
        return TRIO
    card(named)
    rest = sorted((s for s in TRIO if s != named), key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return (named, *rest[:2])


def sentence(style):
    """The style in one plain sentence for the person, as styles/catalog.md says it."""
    for row in (STYLES / "catalog.md").read_text().splitlines():
        cells = [x.strip() for x in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return cells[1]
    return card(style)["name"]


def ids(c, kind):
    """The move or transition ids a card allows (`kind` is "moves" or "transitions")."""
    return [m["id"] for m in c[kind]]


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once); between equals the
    one used least so far, then the card's order. The option `avoid` (the previous beat's) is never picked while another
    exists, and an option marked `once` that has played is never picked again."""
    fresh = [o for o in options if not (o.get("once") and used.get(o["id"]))] or options
    pool = [o for o in fresh if o["id"] != avoid] or fresh
    score = lambda o: 2 * (form in o["fits"]) + len((set(tags) - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def cased(text, face):
    """Words in a card face's case, as the film sets them."""
    case = face.get("case")
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


def system(c, colors):
    """The design system the compositions read, from the card: its faces, the colors its palette rule made, the
    easing, the finish, the closer shape and the photo beat's layout."""
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"],
            "photo": json.loads(json.dumps(c["photo"]))}


def hexes_in(o):
    """Every hex color a board's lines and cards name."""
    if isinstance(o, dict):
        return [h for v in o.values() for h in ([v.lower()] if isinstance(v, str) and v.startswith("#") and len(v) == 7 else hexes_in(v))]
    if isinstance(o, list):
        return [h for v in o for h in hexes_in(v)]
    return []
