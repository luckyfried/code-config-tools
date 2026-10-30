#!/usr/bin/env python3
"""The board builder: the film for one person, planned from what gather and research found, and laid out for every
format the studio composition renders, in one of the style cards in styles/.

USAGE (from the workspace root; storyboard.py calls it, and run alone it prints the three boards):
    python3 S/scripts/compose.py

plan(ctx, style)     the board storyboard.json holds: its length in seconds, its beats in order, each a form (the kind
                     of shot), its pulses of the tempo, the move and the cut its card allows for what it holds, and the
                     words and photographs it carries. Every word is one the two of them wrote (a caption) or the
                     closer's wish, name, number, date and sender; every photograph is one they share.
fit(board, bpm)      the board timed at a tempo: the same length, each card's share of it following its photograph.
lay(board, fmt, bpm) the studio board motion/studio renders: the same beats laid out for reel (1080x1920), feed
                     (1080x1080) or wide (1920x1080), each layout solved for its own frame, never one frame scaled into
                     another; type sits inside the format's safe area (design/safe-areas.json).
bounds(studio)       plain sentences, one per line or photograph that breaks a rule of the frame at rest.

The story is the year with you (scripts/wall.py): one card per moment of the year the two had (taste.json "moments",
which research.py drafts with draft_moments and the agent curates), each moment's name in its caption's own words
rising out of its photograph's own line beside its subject, the photographs building the wall the giant age is cut
through at the close. A board is that story in one style: the card names its faces, its palette rule (which turns the
photographs' own colors into the film's), its moves and cuts, its easing, its finish, its closer and its music recipe.
The three boards a run drafts take TRIO, or the style the person named and the two of TRIO that share the fewest axes
with it (`styles_for`).
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

FPS = 30
SKILL = Path(__file__).resolve().parents[1]
STYLES = SKILL / "styles"
# the three styles a run's boards take by default, one per board: A, B and C
TRIO = ("scrapbook", "analog-home-movie", "editorial-quiet")
AXES = ("family", "palette", "camera", "transition", "finish", "music")
LENGTH = (20, 60)  # seconds a film may run: the lengths the kit makes
FLOOR = 28  # px: the least cap height (figure height for numerals) a readable line is drawn at, at 1:1
FORMATS = {"reel": "reel", "feed": "feed", "wide": "wide"}
# the characters the studio's faces have no glyph for: emoji, their variation selector and joiner
UNSET = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U0000200D]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def refusal(seconds):
    """The sentence a length outside LENGTH is refused with; None for a length the kit makes."""
    lo, hi = LENGTH
    if lo <= seconds <= hi:
        return None
    return (f"not delivered: {seconds:g} s is outside the {lo}–{hi} s this kit makes, so nothing was made; "
            f"ask for a length from {lo} to {hi} s")


def shown(item):
    """How surely a shared post shows the one the film is for: 2 when it tags them or is their own post, 1 when its
    caption names or @mentions them, 0 when nothing in it names them."""
    why = item.get("why") or []
    if "tagged" in why or item.get("from") == "theirs":
        return 2
    return 1 if {"mentioned", "named"} & set(why) else 0




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


def styles_for(taste):
    """The three styles a run's boards take, A, B and C: taste.json's `style` when the person named one, then the two of
    TRIO that share the fewest axes with it; else TRIO."""
    named = (taste or {}).get("style")
    if not named:
        return list(TRIO)
    card(named)
    rest = sorted((s for s in TRIO if s != named), key=lambda s: (len(shared_axes(named, s)), TRIO.index(s)))
    return [named, *rest[:2]]


def name_of(style):
    """The style's name and the one plain sentence styles/catalog.md says it looks like."""
    for row in (STYLES / "catalog.md").read_text().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return card(style)["name"], cells[1]
    return card(style)["name"], ""


def tempo_range(style):
    """The tempo range, beats a minute, the style's music recipe plays in (music/recipes.json); snap folds the music's
    tempo into it."""
    book = json.loads((SKILL / "music" / "recipes.json").read_text())
    lo, hi = book["recipes"][card(style)["music"]]["tempo"]
    return lo, hi


def tempo_of(style):
    """The tempo a board in `style` is planned at: the middle of its recipe's range."""
    lo, hi = tempo_range(style)
    return round((lo + hi) / 2)

# ---------------------------------------------------------------- data

def day(iso):
    return dt.date.fromisoformat(str(iso)[:10])


def when(iso, weekday=True):
    d = day(iso)
    return (f"{d.strftime('%a').lower()} " if weekday else "") + f"{d.day} {d.strftime('%b').lower()}"


def ts_day(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()


def loud(s):
    """How loud a line is: exclamation marks, emoji, words in capitals, question marks."""
    caps = len([w for w in re.findall(r"[A-Za-z']+", s) if len(w) > 1 and w.isupper()])
    return s.count("!") + 0.8 * len(EMOJI.findall(s)) + 1.2 * caps + 0.5 * s.count("?")


def own_words(caption):
    """A caption as it is shown: the tags left at its end go when the sentence stands without them."""
    s = (caption or "").strip()
    bare = re.sub(r"(\s+@[\w.]+)+$", "", s)
    if bare != s and not re.search(r"\b(and|with|&|,|to|for|by)$", bare.strip(), re.I):
        return bare.strip()
    return s


def plain(caption):
    """A caption as it is set: its own words, the tags at its end gone when the sentence stands without them, no emoji."""
    return re.sub(r"\s+", " ", UNSET.sub("", own_words(caption))).strip()


NAME_WORDS = 5  # words a moment's name holds before its "with ..." or "and ..." goes to the line under it


def moment_name(caption):
    """What a moment is called, in its caption's own words: the caption's first clause, the tags it opens with gone, in
    lowercase ("first coffee of the year" from "first coffee of the year with @dani.reyes, same window, same order"). A
    clause longer than NAME_WORDS words ends before its last "with" that follows two words or more, so the name stays a
    title and the rest is its line ("front row in marrakech" from "front row in marrakech with my favorite travel
    partner"); with no such "with", before its first "and" that follows two words or more ("dani turns 30 on october
    24" from "dani turns 30 on october 24 and i'm already planning the table"). A point or a colon between two figures is part of a number ("6:30am", "50.5 km") and ends no clause."""
    s = re.sub(r"^(@[\w.]+[\s,:]*)+", "", plain(caption))
    name = re.split(r"\s+with\s+@|\s+@|[,;!?()]|(?<!\d)[.:]|[.:](?!\d)", s)[0].strip().lower()
    words = name.split()
    cut = [i for i, w in enumerate(words) if w == "with" and i >= 2][-1:] or [i for i, w in enumerate(words) if w == "and" and i >= 2][:1]
    return " ".join(words[:cut[0]]) if len(words) > NAME_WORDS and cut else name


def moment_words(line, name):
    """The rest of a moment's line after its name, the "with @them" that opens it (every tag it lists, "with @a and @b")
    and the hashtags that end it gone; empty when the name is the line or the line does not hold it."""
    i = line.lower().find(name.lower())
    if not name or i < 0:
        return ""
    rest = re.sub(r"^[\s,.;:!?]*(with\s+@[\w.]+(\s*(,|&|\band\b)\s*@[\w.]+)*)?[\s,.;:!?]*", "", line[i + len(name):],
                  flags=re.I)
    return re.sub(r"(\s*#\w+)+\s*$", "", rest).strip()


def draft_moments(shared):
    """The year's moments as research drafts them, by date: one per photograph post the two share, the occasion's post
    aside (it is the hook); a post with no caption is a wordless moment, its name and line empty. Each is its post and date, its name and its line in the caption's own words,
    its place, the people in it besides the person, and the first two comments the two left under it, oldest first."""
    me = shared.get("me")
    who = (shared.get("who") or {}).get("handle")
    told = (shared.get("occasion") or {}).get("from") or ""
    talk = {}
    for e in shared.get("exchanges") or []:
        if e.get("post"):
            talk.setdefault(e["post"], []).append({"by": e["by"], "text": e["text"]})
    out = []
    for x in sorted(shared.get("items") or [], key=lambda x: x["ts"]):
        cap = x.get("caption") or ""
        if x.get("kind") != "post" or x.get("video") or (cap and cap[:40] in told):
            continue
        people = {p.rstrip(".") for p in set(x.get("tagged") or []) | set(re.findall(r"@([\w.]+)", cap))} | ({who} if x.get("from") == "theirs" else set())
        people -= {me, None, ""}
        out.append({"post": x["id"], "date": x["date"], "name": moment_name(cap), "line": plain(cap), "place": x.get("place"),
                    "people": sorted(people), "talk": talk.get(x["id"], [])[:2], "peak": False})
    return out


class Ctx:
    """What gather and research found, as the board builder reads it: the shared posts, the pairs, the photos."""

    def __init__(self, B=None):
        B = B or _env.B
        self.B = Path(B)
        self.shared = _env.read_json(self.B / "shared.json") or {}
        self.picks = _env.read_json(self.B / "picks.json") or {}
        self.taste = _env.read_json(self.B / "taste.json") or {}
        self.ask = _env.read_json(self.B / "ask.json") or {}
        if not self.shared or not self.picks:
            sys.exit(f"{B}/shared.json or picks.json is missing: run research.py first")
        who = self.taste.get("for") or self.shared.get("who") or {}
        self.who = who.get("handle") or who.get("first") or "you"
        self.called = f"@{who['handle']}" if who.get("handle") else self.who  # how a line names them
        self.first = (who.get("first") or self.who).strip()
        self.me = self.taste.get("handle") or self.shared.get("me") or "me"
        self.occ = {**(self.shared.get("occasion") or {}), **{k: v for k, v in (self.taste.get("occasion") or {}).items() if v}}
        self.items = sorted(self.shared.get("items") or [], key=lambda x: x["ts"])
        self.pairs = self.shared.get("pairs") or []
        self.exchanges = self.shared.get("exchanges") or []
        rows, self.carousel = {}, {}
        for r in self.picks.get("items") or []:
            if r["id"] in rows:
                self.carousel.setdefault(r["id"], []).append(r)
            rows.setdefault(r["id"], r)
        for r in self.picks.get("videos") or []:
            rows.setdefault(r["id"], r)
        self.rows = rows
        self.caption_of = {x["id"]: x.get("caption") or "" for x in self.items}
        for r in rows.values():
            self.caption_of.setdefault(r["id"], r.get("caption") or "")

    def photo(self, pid):
        """The photograph a post is shown by, as the renderer names it, with its subject's place in the frame; `post#2`
        names the second photograph of a carousel."""
        base, _, n = pid.partition("#")
        rows = [self.rows[base], *self.carousel.get(base, [])] if base in self.rows else []
        r = rows[int(n or 1) - 1] if len(rows) >= int(n or 1) else None
        if not r:
            return None
        fx, fy = r.get("focal") or (0.5, 0.5)
        return {"post": base, "file": f"graded/{Path(r['photo']).name}", "focus": [round(fx, 3), round(fy, 3)], "aspect": aspect_of(self.B, r)}

    def occasion_post(self):
        src = self.occ.get("from") or ""
        for x in self.items:
            if x["from"] == "mine" and x.get("caption") and x["caption"][:40] in src:
                return x
        return None

    def wish(self):
        """The closer's wish: its title, the name, the number the occasion is counted by (a birthday's age, an
        anniversary's years, none for any other occasion), the day, the sender and the occasion's kind."""
        d = self.occ.get("date")
        kind = self.occ.get("kind") or "birthday"
        n = self.occ.get({"birthday": "age", "anniversary": "years"}.get(kind, ""))
        return {"title": self.occ.get("title") or f"for {self.first.lower()}", "name": self.first.lower(), "number": str(n) if n else "",
                "date": d, "from": f"@{self.me}", "kind": kind}

    def told_by_them(self):
        """The named one's own posts the person is in (tagged or named), by date."""
        return [x for x in self.items if x["from"] == "theirs" and self.rows.get(x["id"])]

    def pairs_by_post(self):
        out = {}
        for p in self.pairs:
            out.setdefault(p["post"], []).append(p)
        return out

    def their_posts(self):
        """Every post of the named one the builder can show: the ones the person is in and the ones the two talked under."""
        ids = {x["id"] for x in self.told_by_them()} | {p["post"] for p in self.pairs}
        rows = [self.rows[i] for i in ids if i in self.rows]
        return sorted(rows, key=lambda r: r["ts"])

    def captioned_mine(self):
        return [x for x in self.items if x["from"] == "mine" and (x.get("caption") or "").strip() and self.rows.get(x["id"])]

    def people(self, x):
        names = set(x.get("tagged") or []) | set(re.findall(r"@([\w.]+)", x.get("caption") or ""))
        names.discard(self.me)
        return 1 + max(1, len(names))


_ASPECT = {}


def aspect_of(B, row):
    """Height over width of the prepared photograph (the graded copy has the same shape)."""
    p = Path(row["photo"])
    if not p.is_absolute():
        p = Path(B).parent.parent / p if not p.exists() else p
    if str(p) not in _ASPECT:
        try:
            from PIL import Image
            with Image.open(p) as im:
                _ASPECT[str(p)] = round(im.height / im.width, 4)
        except Exception:
            _ASPECT[str(p)] = round((row.get("h") or 3) / (row.get("w") or 4), 4)
    return _ASPECT[str(p)]


# ---------------------------------------------------------------- frames

def safe_areas():
    d = _env.read_json(_env.SKILL / "design" / "safe-areas.json")
    return {k: v for k, v in d.items() if k != "about"}


class Frame:
    """A format's frame: its size and the box its type stays inside (l, t to r, b, in px)."""

    def __init__(self, name):
        a = safe_areas()[name]
        self.name = name
        self.W, self.H = a["width"], a["height"]
        self.l, self.t = a["left"], a["top"]
        self.r, self.b = self.W - a["right"], self.H - a["bottom"]
        self.wide = self.W > self.H * 1.2
        self.tall = self.H > self.W * 1.2

    @property
    def measure(self):
        return min(self.r - self.l, 1100)


# ---------------------------------------------------------------- the board

def plan(ctx, style):
    """The board in `style`: the year with you (wall.py), set in the style card's faces, colors, moves and cuts."""
    return wall.plan(ctx, style)


def seconds_of(beats, bpm):
    return sum(b["pulses"] for b in beats) * 60 / bpm


def fit(board, bpm):
    """The board timed at `bpm`: its length kept, every beat's pulses set at that tempo."""
    return wall.fit(board, bpm)


def lay(board, fmt="reel", bpm=None):
    """The studio board for one format, timed at `bpm`."""
    return wall.lay(board, fmt, bpm)


def bounds(studio, board):
    return wall.check(board, studio)


def hook_frame(board, bpm=None):
    return wall.hook_frame(board, bpm)


def rest_frames(studio, board):
    return wall.rest_frames(studio, board)


def hook_event(board):
    return wall.HOOK_EVENT


def story(board):
    return wall.story(board)


def posts_in(obj, acc=None):
    """Every post a plan's beats name."""
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "post" and isinstance(v, str):
                acc.add(v)
            else:
                posts_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            posts_in(v, acc)
    return acc


def system(c, colors):
    """The design system the composition reads, from the style card `c`: the faces, the type scale, the colors the
    card's palette rule made, the easing, the finish, the closer shape, the photo beat's layout, and the safe areas."""
    safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in safe_areas().items()}
    return {"style": c["id"], "display": dict(c["faces"]["display"]), "text": dict(c["faces"]["text"]),
            "scale": {"hero": 200, "h1": 120, "h2": 80, "h3": 56, "body": 40, "label": 26},
            "colors": dict(colors), "ease": dict(c["ease"]), "finish": dict(c["finish"]), "closer": c["closer"], "photo": json.loads(json.dumps(c["photo"])), "safe": safe}


def finish(ctx, board, bid):
    """The board's id, its photographs, and its colors: the style card's palette rule over the colors the two share
    (taste.json's together palette)."""
    import palette
    board["id"] = str(bid)
    board["photos"] = {p: ctx.photo(p) for p in sorted(posts_in(board["beats"])) if ctx.photo(p)}
    pal = (ctx.taste.get("palette") or {}).get("together") or []
    hexes = [s["hex"].lower() for s in pal[:5] if s.get("hex")] or list(palette.NEUTRAL)
    made = palette.palette_of(card(board["style"])["palette"], hexes)
    board["colors"] = made["roles"]
    board["swatches"] = made["swatches"]
    return wall.finish(ctx, board)


def main():
    ctx = Ctx()
    for i, style in enumerate(styles_for(ctx.taste), 1):
        b = finish(ctx, plan(ctx, style), i)
        secs = seconds_of(b["beats"], b["bpm"])
        print(f"{i} {style}: {len(b['beats'])} beats, {secs:.1f} s at {b['bpm']} bpm")
        for bt in b["beats"]:
            print(f"   {bt['id']:10s} {bt['form']:7s} {bt['pulses'] * 60 / b['bpm']:5.2f} s {bt.get('post') or ''} "
                  f"{bt.get('move') or ''}/{bt.get('transition') or ''} {bt.get('name', '')}")
    return 0

import wall  # noqa: E402  (wall reads this module's names when it runs)

if __name__ == "__main__":
    sys.exit(main())
