"""What the boards are built from: the run's people (in the film's order, each with the stamp of where and when the
photograph of the two of them was taken, their own lines and replies), their matched photographs, and the steps around
the builder (the draft of one style written to storyboards/<style>/storyboard.json, and the layout of a draft into one
format at the film's tempo).

A storyboard.json is the draft: format-free beats that name a composition, a person, a photograph and the words
(their own lines from people.json, never written for them), with a length in pulses (beats of the tempo), and the style
card it is made in. The agent edits the draft; layout() turns it into the board the studio's drive film renders,
re-solved per format, in the faces, colors, moves, cuts, finish and closer of its card (board_drive.py).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import layout as L  # noqa: E402

FPS = 30
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")


def said(t):
    """A line as the film says it: the person's words with their emoji taken off, since the type draws none, and the
    handles that trail it taken off, since the tag shows the person's handle; a line with a link in it, or with nothing
    left, is never said."""
    if not t or "http" in t:
        return None
    return re.sub(r"(\s*@[\w.]+)+\s*$", "", re.sub(r"\s+", " ", EMOJI.sub("", t)).strip()).strip() or None


class Person:
    """A person of the film: `told` is their entry in taste.json, which carries their moment (`when`, `where`, `what`:
    the month and place of the photograph of the two of them, and the person's caption of it) and `line`, the words the
    agent settled for that moment, which their card says; `stamp` is where and when as the card sets it, in the
    person's case."""

    def __init__(self, p, told=None, year=None, lowercase=True):
        self.handle, self.rank, self.raw = p["handle"], p["rank"], p
        self.comments = p.get("signals", {}).get("their_comments", 0)
        self.stretch = (p.get("stretch") or {}).get("label") or ""
        told = told or {}
        self.when = told.get("when") or self.stretch or (str(year) if year else "")
        self.where = told.get("where")
        self.what = told.get("what")
        text = ", ".join(x for x in (self.where, self.when) if x)
        self.stamp = text if lowercase else text.title()
        self.months = (p.get("stretch") or {}).get("months") or []
        picked = p.get("line") or {}
        self.line = said(told["line"]) if "line" in told else said(picked.get("text"))   # taste.json's, empty included
        self.line_from = told.get("line_from") or picked.get("from", "")
        self.replies = {}
        for x in p.get("exchanges", []):
            own = re.sub(r"^@[\w.]+\s*", "", x.get("own") or "").strip()
            if said(x.get("they")) and said(own):
                self.replies.setdefault(said(x["they"]), said(own))


class Ctx:
    """The run's people and photographs, read from people.json, taste.json and cast.json."""

    def __init__(self):
        stats = _env.read_json("people.json") or {}
        taste = _env.read_json("taste.json") or {}
        if not stats.get("people"):
            sys.exit("people.json is missing: run research.py first")
        told = {x["handle"]: x for x in taste.get("people", []) if x.get("handle")}
        order = list(told) or [p["handle"] for p in stats["people"]]
        by = {p["handle"]: p for p in stats["people"]}
        self.handle = stats.get("handle") or taste.get("handle")   # None when the data names no username
        self.year = stats.get("year") or taste.get("year")
        lowercase = (taste.get("register") or {}).get("lowercase", True)
        self.people = [Person(by[h], told.get(h), self.year, lowercase) for h in order if h in by]
        self.eras = stats.get("eras") if isinstance(stats.get("eras"), list) else []
        cast = _env.read_json("cast.json")
        if not cast:
            sys.exit("cast.json is missing: run cast.py draft and cast.py match first")
        cap = _env.per_person(len(cast["people"]))
        self.photos = L.Photos({**cast, "people": {h: rows[:cap] for h, rows in cast["people"].items()}}, "public")   # the photographs match carried
        self.cast = self.photos.cast
        self.by = {p.handle: p for p in self.people}

    def person(self, h):
        return self.by[h]

    def heads(self):
        """The people with a head in the group photograph, left to right."""
        hs = (self.cast.get("group") or {}).get("heads") or {}
        return sorted((h for h in hs if h in self.by), key=lambda h: hs[h][0])


BREATH = ("and", "but", "so", "then", "because", "when")


def builder():
    import board_drive
    return board_drive


def draft(style, ctx):
    """The storyboard of the film in style `style` (a style card id): the kit's one story, laid out in that card."""
    m = builder()
    m.use(style, ctx)
    sb = {"style": style, "name": m.NAME, "idea": m.IDEA, "bpm": m.BPM,
          "handle": ctx.handle, "year": ctx.year, "people": [p.handle for p in ctx.people]}
    ctx.sb = sb
    sb["beats"] = m.draft(ctx)
    sb["cards"] = m.cards(ctx, sb["beats"])
    return sb


def layout(sb, ctx, kind="reel", bpm=None):
    """The board the studio's drive film renders: the draft laid out in one format in its style, timed at `bpm`."""
    ctx.sb = sb
    return builder().board(sb, ctx, kind, bpm)


def read_words(layer):
    """The words a layer puts on screen to be read."""
    k = layer["kind"]
    if k == "Words" and not layer.get("texture"):
        return " ".join(x["text"] if isinstance(x, dict) else x for x in layer["lines"]).split()
    if k == "Tags":
        return [t["text"] for t in layer["tags"]]
    return []


def roles(board):
    """{hook, dense, closer}: the beat indices the swap test reads: the first, the one between them with the most words
    on screen, and the last."""
    n = [sum(len(read_words(l)) for l in b["layers"]) for b in board["beats"]]
    middle = range(1, len(n) - 1) if len(n) > 2 else range(len(n))
    return {"hook": 0, "dense": max(middle, key=lambda i: (n[i], -i)), "closer": len(n) - 1}


def hook_frame(board):
    """The frame of the film's first event: the first beat's first entrance after frame 0, or the first cut."""
    pulse = FPS * 60 / board["bpm"]
    first = board["beats"][0]
    ats = []
    for l in first["layers"]:
        at = l.get("at", 0) or 0
        if at > 0 or l.get("enter") not in (None, "cut"):
            ats.append(at)
    cand = [round(a * pulse) for a in ats] + [first["frames"]]
    return min(max(1, c) for c in cand)


def cuts_per_minute(board):
    n = len(board["beats"]) - 1
    total = sum(b["frames"] for b in board["beats"])
    return round(n / (total / FPS) * 60, 1), total / FPS


def rest_frame(board, i):
    """The settled frame of beat i: the frame its board names (`rest`), else two frames before its cut."""
    start = sum(b["frames"] for b in board["beats"][:i])
    b = board["beats"][i]
    return start + b.get("rest", b["frames"] - 2)
