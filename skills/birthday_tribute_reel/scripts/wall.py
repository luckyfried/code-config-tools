"""The year with you, the kit's story. One card per moment of the year the two had, each settling into its place on one wall.

The film is one camera travelling a wall of the year's photographs, the hook first and then the year's moments in
order to the last one before the day (taste.json "moments", research's draft of them where the agent kept none). Each
photograph arrives whole as a print standing off the wall, its shadow under it, and as it lands a streak of light
runs along its own strongest line (or, when that line would cut the subject, just past the subject on its quiet side)
and the moment's name, in its caption's own words, rises out of that line letter by letter, turned to its angle. The
name casts its shadow on the photograph; under it, two lines at most, rise the rest of the caption in the voice that
wrote it (the sender's in the style card's text face, the named one's in its display face, in its italic where the
card has one), or, where the two commented under the post, their comments there, each in its writer's voice. Each
card holds as long as its photograph asks (`hold_of`): the time to take the picture in, a little more for each person
in it and for a photograph that shows the one the film is for, and the time to read its words; the moment the agent
marks as the year's peak holds longest, and the RUN cards before it run fast, FAST seconds each with their names
alone. The film runs the length the person asked for, or, with none asked, the sum of those
holds inside the kit's 20 to 60 s; the cards share what the hook and the closer leave of it in proportion to their
holds (`fit`), so the cuts follow the photographs, not a grid of beats. The type is the
paper's color over light taken out of the picture under it, or ink over light given to it where the picture is
bright there. When the camera leaves, the photograph trims into its cell of the wall and the name lifts off toward the
lens; every travel crosses the wall, dimmed, before its cells are filled. The photographs
that show the one the film is for (a post that tags them, their own post of the two, then a caption that names them;
`compose.shown`) lead and close the film: the hook is the post taste.json `hook` names (`post:N`, or `post:N#K` for a
carousel's K-th photograph), else the occasion post's photograph when it shows them, else the latest one before the
day that shows them most surely, and when the last moment's photograph does not show them, the
latest one that does moves to the end. The hook carries the age on its line when the person gave one, else the name
they call them, with its tag before it and the day after it ("dani turns 30", "sat 24 oct") and no caption, and a
line that states an age the person did not give is left off the screen. At the closer the camera pulls back to the wall, a sheet of the style's
dark ground, carrying the wall's photographs dimmed into it, the age cut out of it in giant figures with a lit rim, falls
shut over the wall, the camera landing on the whole wall as it slams; its shadow is gone before the figures can be read,
so the age reads one way from the first frame it can be read, the photographs lit through clear figures; on the last
hit the age's last figure punches through the sheet; then the style card's closer takes the frame with the wish (the
person's own line when they gave one) and its sender, and the picture and the sound stop together.
The day is the one the person or their captions gave; with none, no line states a day. The wall holds exactly the
year's photographs, row under row, each row's cells filling the frame's width. The age is a birthday's figure and an
anniversary's is its years, each only when the person said it; a birthday or an anniversary without that number, and a
farewell, a graduation, a retirement or a tribute, have none, so the name takes its place and the hook's small line
names the occasion. A year with more moments than the length holds at LEAST seconds a card keeps the ones spread
across it, the photographs that show the one the film is for first.

Every word is set in the style card's faces, every color is one the card's palette rule made from the photographs' own
colors, and every beat moves by one of the card's moves and enters by one of its cuts, each chosen from what the beat
holds: the hook is the title, a photograph is portrait or landscape, with people or a place, wordless or not, the
year's peak, and the closer is the wall (`choose`). The storyboard says per beat what the move reveals and what it carries across the cut (`story`), the sound where each
beat lands (`sound`, placed at named beats for music.py), and the requests for the generated clips that would carry a photograph's own motion for the hook's world, texture
between chapters and a still brought to life (`clips`), each in the shape motion/system/standards.md gives a clip
request; a clip is in the film only once a video model has made it."""
import copy
import datetime as dt
import math
import re
from pathlib import Path

import _env
import compose
import shared

NAME = "the year with you"
IDEA = ("The year's moments with them, one card each: each photograph lands whole as the moment's name, in its "
        "caption's own words, rises out of its own line with the line they wrote or traded under it, each photograph "
        "settles into its place on a wall, and the wall becomes the giant age the whole year fills, and the wish rises.")
STRUCTURE = ("the age on the occasion photograph; one card per moment of the year, its name on the edge and their words "
             "beside it; the wall; the sheet over the wall with the age cut through it; its last figure punched home; the wish")
MUSIC = ("their music; a hit where the age and each moment's name land, the build as the sheet falls over the wall, its "
         "impact, a hit as the last figure punches home, the stop on the wish")
HOOK_EVENT = "the age rises out of the occasion photograph's own line as the photograph lands"

# beats: the hook's length, the closer's length and where its stop falls inside it (the hit, the fall and the punch
# land on the music's beats)
HOOK_BEATS, CLOSER_BEATS, STOP_AT = 3, 9, 6.0
# a card's hold, seconds: the least any card holds; the time to take a photograph in; what each person in it beyond the
# one the film is for adds, up to CROWD of them; what a photograph that tags them or is their own adds; the words read
# a second, of at most WORDS shown; how much longer than the longest other card the year's peak holds
LEAST, LOOK, PERSON, CROWD, SHOWS, READ, WORDS, PEAK = 2.0, 1.6, 0.3, 3, 0.4, 3.0, 24, 1.25
# the cards just before the year's peak that run fast, and the seconds each of them takes
RUN, FAST = 3, 1.3
# beats from a card's arrival to its landing on its lift, where its name starts to rise out of its line and its hit
# falls (the hook's, as it falls flat)
LIFT, HOOK_LIFT = 0.25, 0.3
# beats a card's leave starts before the next card arrives
LEAVE = 0.6
# beats before a card's end the camera's move to the next card starts (the camera's GO), and twice that before the last
# card's end, where the pull back onto the whole wall starts; a card is at rest only before its move
GO = 0.8
# the age's size on the hook, a moment's name's size, the caption's size, the wish's size, px, per format; the small
# type is at least SMALL px on a SMALL_STEP pitch (`small_px`), and a block of words is set LEAD times its size apart
AGE = {"reel": 500, "feed": 300, "wide": 300}
HEAD = {"reel": 120, "feed": 92, "wide": 96}
CAPTION = {"reel": 46, "feed": 40, "wide": 42}
WISH = {"reel": 96, "feed": 72, "wide": 80}
SMALL, SMALL_STEP, LEAD = 42, 54, 1.3
# the hook's tag and day beside the figure are set up to TAG_SHARE of the figure's height, as large as the room at its
# right lets them and never under SMALL, so the lockup reads as one title
TAG_SHARE = 0.27
# where the edge crosses the frame's middle column, px from the top: the target, the highest and the lowest it may sit,
# with the type over the edge (EDGE) and, for a subject in the photograph's top part, hanging under it (UNDER)
EDGE = {"reel": (860, 700, 1150), "feed": (500, 400, 700), "wide": (440, 380, 640)}
UNDER = {"reel": (760, 420, 840), "feed": (560, 300, 660), "wide": (560, 300, 660)}
# the name's baseline sits this many px over the edge; the subject sits at least GAP px under it; the words keep
# APART px from the name
RAISE, GAP, APART = 6, 24, 40
# the most an edge turns, degrees; a photograph is enlarged up to REACH past filling the frame
TILT, REACH = 12, 1.8
# the most of a subject's height that may stand on the type's side of its edge; the least of it the frame must show
COVERED, FRAMED = 0.5, 0.4
# the color distance (CIE76) under which the picture just under an edge reads as the field over it
MERGE = 30
# the least and the most light taken out of the photograph under the type (a dark picture takes the least)
SHADE = (0.22, 0.62)
# the picture's light (0 to 1) above which the type is set in ink, over a veil of the paper's light this strong
INK_OVER, VEIL = 0.58, 0.5
# the paper between the wall's cells, px; the margin the wall and the giant age keep from the frame's sides
GUTTER, MARGIN = 8, 24
# the most moments the wall holds beside the hook
MOST = 15
# how far the solid core of the band under the wish's lines reaches past them, px
BAND = 24
# the camera at rest on a card: how far it has pushed in (camera.ts), its lens, degrees, and how far the type stands
# over the print (card.tsx), px of the card's frame
PUSH, HOLD_FOV, HELD = 0.08, 30, 120
# the card face each voice is set in: the figures, the names and the wish in the display face; the sender's words and
# the small lines in the text face; the named one's words in the display face's italic where the card has one
VOICES = {"display": "display", "mine": "text", "theirs": "italic", "wish": "display", "small": "text"}
_style = [None]


def use(style):
    """Set and measure every voice in `style`'s card faces from now on."""
    if _style[0] != style:
        compose.card(style)
        _style[0] = style
        _fonts.clear()


def face_of(voice):
    """The card face (family, file, weight, tracking, case) `voice` is set in, in the style in use."""
    faces = compose.card(_style[0])["faces"]
    k = VOICES[voice]
    if k == "italic":
        d = faces["display"]
        return {**d, "file": d["italic"], "style": "italic"} if d.get("italic") else d
    return faces[k]


def cased(text, voice):
    """`text` in its voice's case, as the film sets it."""
    case = face_of(voice)["case"]
    return text.upper() if case == "uppercase" else text.lower() if case == "lowercase" else text


_fonts = {}
plain = compose.plain


def font(face):
    from PIL import ImageFont
    if face not in _fonts:
        _fonts[face] = ImageFont.truetype(str(_env.SKILL / face_of(face)["file"]), 1000)
    return _fonts[face]


def width(text, size, face):
    """The px the studio sets `text` in at `size`, in its voice's case: the font's advances plus its tracking (opentype.js
    lays it the same)."""
    text = cased(text, face)
    return (font(face).getlength(text) / 1000 + face_of(face)["tracking"] * len(text)) * size


def cap(face, figures=False):
    """The face's cap height (figure height for numerals) in em, read from its own outlines."""
    b = font(face).getbbox("0" if figures else "H", anchor="ls")
    return -b[1] / 1000


def small_px():
    """The small lines' size, px: SMALL, or larger where the card's text face is short enough that SMALL would draw its
    capitals under the floor."""
    return max(SMALL, math.ceil(compose.FLOOR / cap("small") + 0.5))


def small_pitch():
    """The small lines' pitch, px: SMALL_STEP grown with their size."""
    return round(SMALL_STEP * small_px() / SMALL)


def fold(s):
    """Words as storyboard.py's words check compares them: lowercase, no emoji, one space between them."""
    return " ".join(compose.UNSET.sub("", s or "").split()).lower()


# ---------------------------------------------------------------- the photograph's own line

def lines_of(path, n=4):
    """The photograph's strongest near-level lines, strongest first: [angle in degrees (clockwise, as the frame draws
    it), v (its height at the photograph's middle column, a fraction of its height), strength (its step over the
    photograph's mean edge)]. A Sobel pass over a 96 px wide grey copy, then every line within TILT degrees of level
    scored by the mean signed step in light across it, so an edge between two regions (a horizon, a sill, a roofline)
    adds up and texture (branches, leaves, gravel) cancels, and the type over the line stands on one of the regions."""
    from PIL import Image
    try:
        with Image.open(path) as im:
            g = im.convert("L")
            W = 96
            H = max(8, round(W * g.height / g.width))
            g = g.resize((W, H), Image.BILINEAR)
            px = list(g.tobytes())
    except Exception:
        return []
    at = lambda x, y: px[min(H - 1, max(0, y)) * W + min(W - 1, max(0, x))]
    gy = [[(at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x, y - 1) + at(x + 1, y - 1))
           for x in range(W)] for y in range(H)]
    mean = sum(abs(g) for row in gy for g in row) / (W * H) or 1
    found = []
    for deg in range(-TILT, TILT + 1, 2):
        k = math.tan(math.radians(deg)) * 1.0  # rise in rows per column (pixels are square)
        for v in range(2, H - 2):
            s, m = 0.0, 0
            for x in range(2, W - 2):
                y = v + k * (x - W / 2)
                y0 = int(math.floor(y))
                if 1 <= y0 < H - 2:
                    f = y - y0
                    s += gy[y0][x] * (1 - f) + gy[y0 + 1][x] * f
                    m += 1
            if m > W * 0.6:
                found.append((abs(s) / m / mean, deg, v / H))
    found.sort(reverse=True)
    out = []
    for score, deg, v in found:
        if all(abs(v - o[1]) > 0.08 for o in out):
            out.append([deg, round(v, 3), round(score, 2)])
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- the plan

def moments_of(ctx, skip, day):
    """The moments the year is told by, by date: taste.json's `moments` as the agent curated them (research's draft
    where it kept none), each with a photograph of its own, before the day, the hook's post aside. A name stands only
    in its caption's own words, else the moment takes the name its caption gives it, none for a post with no caption
    (a wordless card); a comment stands only as one of the two wrote it under that post."""
    seen, out = set(), []
    for m in ctx.taste.get("moments") or compose.draft_moments(ctx.shared):
        r = ctx.rows.get(m.get("post"))
        if not still(r) or m["post"] == skip or r["photo"] in seen or compose.day(m["date"]) >= day:
            continue
        line = plain(ctx.caption_of.get(m["post"]) or "")
        name = str(m.get("name") or "").strip()
        if not name or fold(name) not in fold(line):
            name = compose.moment_name(line)
        said = {(e["by"], e["text"]) for e in ctx.exchanges if e.get("post") == m["post"]}
        talk = [t for t in m.get("talk") or [] if (t.get("by"), t.get("text")) in said and plain(t["text"])]
        seen.add(r["photo"])
        out.append({**m, "name": name, "line": line, "talk": talk, "peak": bool(m.get("peak"))})
    return sorted(out, key=lambda m: m["date"])


def still(r):
    """Whether a photograph row is one the film can show: a still photograph."""
    return bool(r) and not r.get("video")


def spread(ms, want, shows=lambda m: 0):
    """`want` of the moments, spread across the year (the one nearest each even step from the first to the last), the
    peak always among them, and the ones that show the one the film is for (`shows` over 0) before the rest."""
    if len(ms) <= want:
        return ms
    seen = [m for m in ms if shows(m) or m["peak"]]
    if len(seen) >= want:
        return across(seen, want)
    return sorted(seen + across([m for m in ms if m not in seen], want - len(seen)), key=lambda m: m["date"])


def across(ms, want):
    """`want` of the moments, the one nearest each even step from the first to the last, the peak always among them."""
    if len(ms) <= want:
        return ms
    t = lambda m: compose.day(m["date"]).toordinal()
    out = [m for m in ms if m["peak"]][:1]
    left = [m for m in ms if m not in out]
    n = want - len(out)
    for i in range(n):
        aim = t(ms[0]) + (t(ms[-1]) - t(ms[0])) * i / max(1, n - 1)
        best = min(left, key=lambda m: abs(t(m) - aim))
        left.remove(best)
        out.append(best)
    return sorted(out, key=lambda m: m["date"])


def hold_of(m, shows):
    """The seconds a moment's photograph asks for: LOOK to take it in, PERSON for each person in it beyond the one the
    film is for (up to CROWD), SHOWS when it tags them or is their own post (`shows` 2), and the time to read its name
    and the words beside it at READ words a second (at most WORDS of them)."""
    said = " ".join(t["text"] for t in m["talk"]) or compose.moment_words(m["line"], m["name"])
    words = min(WORDS, len(f"{m['name']} {said}".split()))
    crowd = min(CROWD, max(0, len(m.get("people") or []) - 1))
    return round(LOOK + PERSON * crowd + (SHOWS if shows == 2 else 0) + words / READ, 2)


def frame_seconds(bpm):
    """The seconds the hook and the closer take at `bpm`."""
    return (HOOK_BEATS + CLOSER_BEATS) * 60 / bpm


def room(length, style):
    """How many cards a film of `length` seconds holds at LEAST seconds each at the slowest tempo snap folds into."""
    return max(0, math.floor((length - frame_seconds(compose.tempo_range(style)[0])) / LEAST))


def plan(ctx, style):
    use(style)
    bpm = compose.tempo_of(style)
    occ = ctx.occasion_post()
    date = ctx.occ.get("date")
    day = compose.day(date) if date else dt.date.max
    wish = ctx.wish()
    number = wish["number"] or wish["name"]
    by_id = {x["id"]: x for x in ctx.items}
    shows = lambda x: compose.shown(x) if x else 0
    # the hook: the occasion post when it shows the one the film is for, else the latest post before the day that shows
    # them most surely, else the occasion post or the last post before the day, with a still photograph, the same rows
    # the cards are shown from; of its photographs the one whose picture is darkest, where the field and the age read
    # strongest
    stills = [x for x in ctx.items if still(ctx.rows.get(x["id"])) and compose.day(x["date"]) < day]
    best = max([shows(x) for x in stills], default=0)
    pick = str(ctx.taste.get("hook") or "").strip()
    base, _, n = pick.partition("#")
    if pick and (base not in by_id or not still(ctx.rows.get(base))):
        raise SystemExit(f"taste.json hook {pick!r} is not a still photograph the two share: name one of shared.json's posts "
                         "as post:N, or post:N#K for a carousel's K-th photograph")
    if pick:
        hook_src = by_id[base]
    elif occ and still(ctx.rows.get(occ["id"])) and (shows(occ) or not best):
        hook_src = occ
    else:
        hook_src = next(x for x in reversed(stills) if shows(x) == best)
    shots = [(f"{hook_src['id']}#{i + 1}", r) for i, r in enumerate([ctx.rows[hook_src["id"]], *ctx.carousel.get(hook_src["id"], [])])]
    if pick and n:
        if not n.isdigit() or not 1 <= int(n) <= len(shots) or not still(shots[int(n) - 1][1]):
            raise SystemExit(f"taste.json hook {pick!r}: {base} has {len(shots)} photograph(s); name one of them as {base}#K")
        hook_pid = shots[int(n) - 1][0]
    else:
        hook_pid = min([sr for sr in shots if still(sr[1])], key=lambda sr: sr[1].get("bright", 0.5))[0]
    # the moments, up to MOST beside the hook and as many as the length holds, each holding what its photograph asks
    shows_m = lambda m: shows(by_id.get(m["post"]))
    year = spread(moments_of(ctx, hook_src["id"], day), MOST, shows_m)
    asked = ctx.ask.get("seconds")
    if asked:
        length, length_from = float(asked), "the length you asked for"
        year = spread(year, room(length, style), shows_m)
    holds = {m["post"]: hold_of(m, shows_m(m)) for m in year}
    for m in year:
        if m["peak"]:
            holds[m["post"]] = round(max(holds[m["post"]], PEAK * max([h for p, h in holds.items() if p != m["post"]], default=0)), 2)
    if not asked:
        lo, hi = compose.LENGTH
        length = round(min(hi, max(lo, frame_seconds(bpm) + sum(holds.values()))), 1)
        length_from = "the photographs' own holds" if lo < length < hi else f"the photographs' own holds, kept inside {lo}–{hi} s"
        year = spread(year, room(length, style), shows_m)
    # the last card before the closer shows them: when the last moment's photograph does not, the latest one that does
    # moves there
    if year and not shows_m(year[-1]) and any(map(shows_m, year)):
        last = next(m for m in reversed(year) if shows_m(m))
        year = [m for m in year if m is not last] + [last]
    # the cards just before the peak run fast, their names alone
    pk = next((i for i, m in enumerate(year) if m["peak"]), 0)
    run = {m["post"] for m in year[max(0, pk - RUN):pk]}
    voice = lambda who: "theirs" if who == ctx.who else "mine"
    # a line that states an age the person did not give stays off the screen
    said = lambda text: "" if not wish["number"].isdigit() and shared.age_in(text) else plain(text)
    beats = [{"id": "hook", "form": "hook", "pulses": HOOK_BEATS, "post": hook_pid, "date": hook_src["date"], "name": number,
              "words": "", "talk": [], "peak": False,
              "voice": "mine" if hook_src["from"] == "mine" else "theirs"}]
    for i, m in enumerate(year):
        x = by_id.get(m["post"]) or {}
        fast = m["post"] in run
        beats.append({"id": f"card-{i + 1}", "form": "moment", "post": m["post"], "date": m["date"], "name": m["name"],
                      "hold": holds[m["post"]], "pulses": 0, "words": "" if fast else said(compose.moment_words(m["line"], m["name"])),
                      "talk": [] if fast else [{"by": t["by"], "text": said(t["text"]), "voice": voice(t["by"])} for t in m["talk"] if said(t["text"])],
                      "peak": m["peak"], "run": fast, "voice": "mine" if x.get("from") == "mine" else "theirs"})
    beats.append({"id": "closer", "form": "closer", "pulses": CLOSER_BEATS, "stop": STOP_AT})
    peak = next((b["id"] for b in beats if b.get("peak")), beats[len(beats) // 2]["id"])
    c = compose.card(style)
    choose(c, beats, {x["post"]: ctx.photo(x["post"]) for x in beats if x.get("post")}, {m["post"]: m for m in year}, ctx.who)
    board = {"id": None, "style": style, "name": NAME, "idea": IDEA, "structure": STRUCTURE,
             "footage": "the photographs, still; each clip below is a request, in the film only once a video model makes it",
             "for": ctx.called, "handle": ctx.me, "occasion": ctx.occ.get("label"), "year": compose.day(ctx.items[-1]["date"]).year,
             "music": {"recipe": c["music"], "direction": MUSIC}, "bpm": bpm,
             "wish": {**wish, "number": number}, "day": date, "length": length, "length_from": length_from,
             "rest": ["hook", peak, "closer"], "beats": beats}
    return fit(board, bpm)


def tags_of(b, photo, moment, who):
    """What a beat holds, as the style card's `fits` name it: the hook is the title; a photograph is portrait or
    landscape, with people beside `who` (the one the film is for), at a named place, carrying words (its caption's line
    or the lines the two traded under it) or wordless, the year's peak; the closer is the wall."""
    if b["form"] == "closer":
        return {"closer", "wall"}
    tags = {"title"} if b["form"] == "hook" else {"photo"}
    if photo:
        tags.add("portrait" if photo["aspect"] > 1.05 else "landscape")
    if set((moment or {}).get("people") or []) - {who}:
        tags.add("people")
    if (moment or {}).get("place"):
        tags.add("place")
    if b["form"] == "moment":
        tags.add("words" if b.get("words") or b.get("talk") else "wordless")
    if b.get("peak"):
        tags.add("peak")
    return tags


# how much a matched tag counts: the hook's and the closer's own forms outweigh everything, any photograph's form
# counts least, and each thing a beat holds counts between them
WEIGHT = {"title": 5, "closer": 5, "photo": 1}
# the tags that say what a beat's words are, which a cut never reads
WORD_TAGS = {"words", "wordless"}
# the tags a cut kept for the film's turning points fits, which never stands in for another cut
KEPT = {"peak", "wall", "closer"}


def pick(options, tags, avoid):
    """The option whose `fits` matches the beat's tags best (`WEIGHT`, 2 for a tag it does not name); between equals
    the one the card lists first. The option `avoid` (the previous beat's) is never picked while another that fits the
    beat exists, and one that fits nothing in the beat only when nothing does."""
    score = lambda o: sum(WEIGHT.get(t, 2) for t in tags & set(o["fits"]))
    fits = [o for o in options if score(o)] or options
    pool = [o for o in fits if o["id"] != avoid] or fits
    return max(pool, key=lambda o: (score(o), -options.index(o)))["id"]


def choose(c, beats, photos, moments, who):
    """Each beat's move and the cut into it, chosen from what it holds (`tags_of`) within the card's allowlists; the
    hook has no cut into it. The move sets the beat's words, so it reads them; the cut changes one picture for the
    next, so it reads the picture and where the beat stands in the film and never its words (`WORD_TAGS`): a slow
    fade meant for the peak and the closer is never spent on every card that has a line. Outside the fast run before
    the peak no cut follows itself: where the best cut is the one into the beat before, the card's next best cut that is
    not kept for the peak, the wall and the closer (`KEPT`) takes its place, so a card that jumps in is followed by one
    the camera travels to and the year changes pace from card to card."""
    prev = cut = None
    for i, b in enumerate(beats):
        tags = tags_of(b, photos.get(b.get("post")), moments.get(b.get("post")), who)
        b["move"] = pick(c["moves"], tags, prev)
        seen = tags - WORD_TAGS
        b["transition"] = None if i == 0 else pick(c["transitions"], seen, None)
        if b["transition"] and b["transition"] == cut and not b.get("run"):
            other = [o for o in c["transitions"] if o["id"] != cut and not KEPT & set(o["fits"])]
            if other:
                score = lambda o: sum(WEIGHT.get(t, 2) for t in seen & set(o["fits"]))
                b["transition"] = max(other, key=lambda o: (score(o), -c["transitions"].index(o)))["id"]
        prev, cut = b["move"], b["transition"]


def fit(board, bpm):
    """The board timed at `bpm`: the hook and the closer keep their pulses (their hits land on the music's beats), the
    run before the peak takes FAST seconds a card, and the other cards share the rest of the board's length, each LEAST
    seconds and the remainder in proportion to its hold, so the film runs `length` seconds at any tempo."""
    cards = [b for b in board["beats"] if b["form"] == "moment"]
    rest = board["length"] - sum(b["pulses"] for b in board["beats"] if b["form"] != "moment") * 60 / bpm
    run = [b for b in cards if b.get("run")]
    slow = [b for b in cards if not b.get("run")]
    fast = min(FAST, rest / len(cards)) if cards else 0
    rest -= fast * len(run)
    least = min(LEAST, rest / len(slow)) if slow else 0
    total = sum(b["hold"] for b in slow) or 1
    secs = lambda b: fast if b.get("run") else least + (rest - least * len(slow)) * b["hold"] / total
    beats = [{**b, "pulses": round(secs(b) * bpm / 60, 4)} if b["form"] == "moment" else b for b in board["beats"]]
    return {**board, "bpm": bpm, "beats": beats}


def finish(ctx, board):
    """The photographs' own lines, read once from the run's copies, beside the subject boxes the storyboard records."""
    for pid, r in board["photos"].items():
        if r and "lines" not in r:
            r["lines"] = lines_of(Path(ctx.B) / "photos" / Path(r["file"]).name)
    return board


# ---------------------------------------------------------------- one card's frame

class Edge:
    """The edge across a frame: y at the frame's middle column `yc`, turned `tilt` degrees clockwise."""

    def __init__(self, W, yc, tilt):
        self.W, self.yc, self.tilt = W, yc, tilt
        self.k = math.tan(math.radians(tilt))

    def y(self, x):
        return self.yc + self.k * (x - self.W / 2)

    @property
    def line(self):
        return [round(self.y(0), 1), round(self.y(self.W), 1)]


def subject_of(p):
    """The subject box; a subject that runs to the photograph's top edge is read from just under it, so the line
    can run through the sliver above it."""
    s = p.get("subject") or [0.3, 0.3, 0.7, 0.7]
    return [s[0], max(s[1], 0.06), s[2], max(s[3], max(s[1], 0.06) + 0.05)]


def framed(f, p, fmt):
    """The photograph with its subject box cut to what the frame can hold, for a card whose whole subject no edge
    clears: a subject taller, at the size that covers the frame, than the room under the format's highest edge keeps
    its top part (never less than FRAMED of it); a subject that fits is unchanged."""
    s = subject_of(p)
    room = (f.H - EDGE[fmt][1] - 2 * GAP) / (max(f.W, f.H / p["aspect"]) * p["aspect"])
    if s[3] - s[1] <= room:
        return p
    return {**p, "subject": [s[0], s[1], s[2], s[1] + max(room, FRAMED * (s[3] - s[1]))]}


def fits(f, p, edge, box, side):
    """Whether a card's layout keeps at most COVERED of the subject on the type's side and FRAMED of it in the frame."""
    s = subject_of(p)
    ix, iy, iw, ih = box
    top, bot = iy + s[1] * ih, iy + s[3] * ih
    seen = (min(bot, f.H) - max(top, 0)) / max(1.0, bot - top)
    return covered(edge, box, s, side) <= COVERED + 0.005 and seen >= FRAMED


def covered(edge, box, s, side):
    """How much of the subject (a fraction of its height) stands within GAP of the edge on the side the type is set."""
    ix, iy, iw, ih = box
    sx0, sx1 = ix + s[0] * iw, ix + s[2] * iw
    top, bot = iy + s[1] * ih, iy + s[3] * ih
    ys = (edge.y(sx0), edge.y(sx1))
    over = max(ys) + GAP - top if side == "over" else bot - (min(ys) - GAP)
    return max(0.0, min(over, bot - top)) / max(1.0, bot - top)


def place(f, p, edge, line, side="over"):
    """(box, covered): the px box [x, y, w, h] the whole photograph is laid in, filling the frame with its subject whole
    inside it and as much of the subject off the type's side of `edge` as the photograph allows, and how much of the
    subject is left on that side; None when no box keeps the subject in the frame. The photograph covers the frame,
    centred across on its subject, enlarged up to REACH; with `line` [deg, v] the photograph's own line lies on the
    edge, without one the subject sits GAP px clear of the edge, or as near that as the photograph at its least size
    can put it. With the type over the edge the subject stands under it; with the type under, over it."""
    a = p["aspect"]
    s = subject_of(p)
    least = max(f.W, f.H / a)
    best = None
    for k in range(9 if line else 1):
        iw = least * (1 + (REACH - 1) * k / 8)
        ih = iw * a
        su = (s[0] + s[2]) / 2
        ix = max(f.W - iw, min(0, f.W / 2 - su * iw))
        sx0, sx1 = max(0, ix + s[0] * iw), min(f.W, ix + s[2] * iw)
        ys = (edge.y(sx0), edge.y(sx1))
        if line:
            iy = edge.y(ix + iw / 2) - line[1] * ih
        else:
            iy = max(ys) + GAP - s[1] * ih if side == "over" else min(ys) - GAP - s[3] * ih
        iy = max(f.H - ih, min(0, iy))
        if line and abs((iy + line[1] * ih) - edge.y(ix + iw / 2)) > 3:
            continue
        if iy + s[3] * ih > f.H + 1 or iy + s[1] * ih < -1:
            continue
        box = [round(ix, 1), round(iy, 1), round(iw, 1), round(ih, 1)]
        c = covered(edge, box, s, side)
        if best is None or c < best[1] - 1e-6:
            best = (box, c)
        if c == 0:
            break
    return best


def lay_photo(f, p, fmt):
    """(edge, box, line, side) for one card. The type stands over the edge with the subject under it: the edge on the
    photograph's strongest line above its subject when that line can lie in the format's band, else level with that
    line just over the subject, nearest the band's target. A subject in the photograph's top part, which no edge in
    that band clears, takes the type hanging under the edge instead (the edge then on a line under the subject, or
    just under it). Failing both, the edge that leaves the least of the subject on the type's side, the photograph's
    own line first; the check names it when more than COVERED of the subject is."""
    s = subject_of(p)
    tried = []
    first = (p.get("lines") or [[0, 0, 0]])[0]
    tilt = first[0] if first[2] >= 1.6 else 0
    for side, band in (("over", EDGE[fmt]), ("under", UNDER[fmt])):
        target, lo, hi = band
        ys = sorted(range(lo, hi + 1, 10), key=lambda y: (abs(y - target), y))
        own = [l for l in p.get("lines") or [] if l[2] >= 1.6 and (l[1] < s[1] - 0.02 if side == "over" else l[1] > s[3] + 0.02)]
        for ln, deg in [(l, l[0]) for l in own] + [(None, t) for t in dict.fromkeys((tilt, 0))]:
            for yc in ys:
                e = Edge(f.W, yc, deg)
                got = place(f, p, e, ln, side)
                if got and got[1] == 0:
                    return e, got[0], ln, side
                if got:
                    tried.append((round(got[1], 2), side != "over", ln is None, e, got[0], ln, side))
    if tried:
        r = min(tried, key=lambda r: r[:3])
        return r[3], r[4], r[5], r[6]
    target, lo, hi = EDGE[fmt]
    a = p["aspect"]
    iw = max(f.W, f.H / a)
    return Edge(f.W, lo, 0), [round((f.W - iw) / 2, 1), round(f.H - iw * a, 1), round(iw, 1), round(iw * a, 1)], None, "over"


def lab(rgb):
    """An sRGB color (0 to 255 per channel) in CIE L*a*b*."""
    r, g, b = (((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in rgb)
    x, y, z = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.9505, r * 0.2126 + g * 0.7152 + b * 0.0722, (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.089
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


_pix = {}


def pixels(B, file):
    from PIL import Image
    path = Path(B) / "public" / file
    if not path.exists():
        path = Path(B) / "photos" / Path(file).name
    if str(path) not in _pix:
        try:
            with Image.open(path) as im:
                _pix[str(path)] = im.convert("RGB").resize((160, max(1, round(160 * im.height / im.width))))
        except Exception:
            _pix[str(path)] = None
    return _pix[str(path)]


def field_for(B, colors, f, p, edge, box):
    """The color a card's light takes (the dust it lights, how bright its hit rings): the paper, or the accent when the
    picture just under the edge is so near the paper's color that the paper's light would not set it apart."""
    im = pixels(B, p["file"])
    if im is None:
        return "paper"
    x, y, w, h = box
    iw, ih = im.size
    hexc = colors["paper"].lstrip("#")
    ref = lab(tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4)))
    far = []
    for X in range(0, f.W, 12):
        for dy in range(8, 64, 8):
            u, v = (X - x) / w, (edge.y(X) + dy - y) / h
            if 0 <= u < 1 and 0 <= v < 1:
                far.append(math.dist(lab(im.getpixel((int(u * iw), int(v * ih)))), ref))
    return "accent" if far and sorted(far)[len(far) // 2] < MERGE else "paper"


def type_light(B, f, p, box, lines):
    """(the type's color, how much light the picture under it is given or loses, 0 to 1), read from the picture's light
    under the type: where even its darker quarter is above INK_OVER the type is set in ink over a veil of the paper's
    light, otherwise in the paper's color over shade that deepens with the light of its brighter quarter. Paper
    carries its shadow and the shade, so it holds over a few bright patches; ink has no halo, so a dark patch under it
    would lose the letters there."""
    im = pixels(B, p["file"])
    lum = []
    pts = [q for ln in lines for q in hull(ln)]
    if im is not None and pts:
        x, y, w, h = box
        iw, ih = im.size
        y0, y1 = max(0, min(q[1] for q in pts)), min(f.H, max(q[1] for q in pts))
        x0, x1 = max(0, min(q[0] for q in pts)), min(f.W, max(q[0] for q in pts))
        for X in range(int(x0), int(x1), 12):
            for Y in range(int(y0), int(y1), 12):
                u, v = (X - x) / w, (Y - y) / h
                if 0 <= u < 1 and 0 <= v < 1:
                    r, g, b = im.getpixel((int(u * iw), int(v * ih)))
                    lum.append((0.2126 * r + 0.7152 * g + 0.0722 * b) / 255)
    dark, bright = quarters(lum)
    if dark > INK_OVER:
        return "ink", VEIL
    return "paper", round(max(SHADE[0], min(SHADE[1], SHADE[0] + (SHADE[1] - SHADE[0]) * (bright - 0.2) / (INK_OVER - 0.2))), 2)


def quarters(lum):
    """The light of a picture's darker and brighter quarter: the 25th and 75th percentiles of `lum` (0.5 when empty)."""
    if not lum:
        return 0.5, 0.5
    q = sorted(lum)
    return q[len(q) // 4], q[(3 * len(q)) // 4]


# the words a phrase starts with, which a two-row break goes before, and how much longer than the most balanced break's
# longer row a break between phrases may make its own
PHRASE = {"in", "of", "at", "on", "with", "and", "to", "for", "from", "but", "until", "after", "before", "by", "under", "over"}
BALANCE = 1.3


def wrap(text, size, face, measure):
    """`text` in rows of at most `measure` px. Text that takes two rows breaks between phrases, before a word in
    `PHRASE`, where the longer row is shortest, unless that row is more than BALANCE times the longest row of the
    most balanced break, which it takes instead ("the whole crew / in sicily", "the grill was going / until 2am"); longer
    text fills each row in turn, and a last row of one word takes the word before it down with it."""
    words = text.split()
    if len(words) > 1 and width(text, size, face) > measure:
        longer = lambda r: max(width(x, size, face) for x in r)
        fits = [r for r in ((" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))) if longer(r) <= measure]
        if fits:
            even = min(fits, key=longer)
            phrased = [r for r in fits if r[1].split()[0] in PHRASE and longer(r) <= longer(even) * BALANCE]
            return list(min(phrased, key=longer) if phrased else even)
    out, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}" if cur else w
        if cur and width(t, size, face) > measure:
            out.append(cur)
            cur = w
        else:
            cur = t
    out += [cur] if cur else []
    if len(out) > 1 and len(out[-1].split()) == 1 and len(out[-2].split()) >= 2:
        *head, w = out[-2].split()
        down = f"{w} {out[-1]}"
        if width(down, size, face) <= measure:
            out[-2:] = [" ".join(head), down]
    return out


def line(text, x, y, size, face, color="paper", anchor=None, name=None, **kw):
    v = face_of(face)
    out = {"text": cased(text, face), "x": round(x, 1), "y": round(y, 1), "size": round(size, 1), "file": v["file"], "face": face,
           "family": v["family"], "tracking": v["tracking"], "color": color}
    if anchor:
        out["anchor"] = anchor
    if name:
        out["name"] = name
    out.update(kw)
    return out


def rest(f):
    """The safe area a card's type is laid out in: the frame's safe area drawn in about the frame's middle by what the
    camera at rest enlarges the type by (its push, and the type standing HELD px nearer the lens than the photograph),
    so the type the camera shows at rest stays inside the frame's safe area."""
    D = f.H / 2 / math.tan(math.radians(HOLD_FOV / 2))
    m = D / (D - HELD) / (1 - PUSH)
    a = copy.copy(f)
    a.l, a.r = f.W / 2 - (f.W / 2 - f.l) / m, f.W / 2 + (f.r - f.W / 2) / m
    a.t, a.b = f.H / 2 - (f.H / 2 - f.t) / m, f.H / 2 + (f.b - f.H / 2) / m
    return a


def tag(wish):
    """The hook's small line over the day: "<name> turns" beside a birthday's age, "<name> · <occasion>" on a birthday
    the person gave no age for and on any other occasion."""
    kind = wish.get("kind") or "birthday"
    return f"{wish['name']} turns" if kind == "birthday" and wish["number"].isdigit() else f"{wish['name']} · {kind}"


def figure(wish):
    """What the hook's and the closer's giant figure is: the age, the years, or the name when the occasion has no number."""
    kind = wish.get("kind") or "birthday"
    return {"birthday": "the age", "anniversary": "the years"}.get(kind, "the name") if wish["number"].isdigit() else "the name"


def card_lines(f, edge, beat, wish, fmt, side="over"):
    """(head, lines): the moment's name in the display face, two rows at most, and under it its words, all turned to the
    edge's angle about the edge's left end. With the type over the edge the words stand on it and the name over them;
    with the type under, the name hangs from it and the words are under the name; so on every card the name reads first
    and its words after it. The words are the comments the two left under the post, each in its writer's voice and two
    rows at most, or else the rest of the caption in the voice that wrote it, two rows at most: one block, LEAD apart,
    in the film's lowercase. On the hook the occasion's figure
    stands on the edge at its full size with its tag (`tag`) beside it level with its top and, when the day was given,
    the day beside it on its baseline, both as large as the room at its right lets them (up to TAG_SHARE of the figure),
    so the hook reads "30" with "dani turns" over "sat 24 oct" at its right, and
    nothing stands above the figure. A wordless card has no name, and its words, if the two traded any, stand on
    the edge. The type shrinks together until every line, turned, is no wider than the safe area at rest (`rest`) and
    the block stays inside its top and bottom, and
    on the hook until the figure and the small lines beside it fit inside its sides; a
    card whose words still leave it at the smallest size sets its name alone."""
    hook = beat["form"] == "hook"
    f = rest(f)
    pivot = [round(f.l, 1), round(edge.y(f.l), 1)]
    rot = dict(rotate=edge.tilt, pivot=pivot)
    t = math.radians(abs(edge.tilt))
    if beat["talk"]:
        said = [(x["text"].lower(), x["voice"]) for x in beat["talk"]]
        stem = "talk"
    else:
        said = [(beat["words"].lower(), beat["voice"])] if beat["words"] else []
        stem = "words"
    head, lines = [], []
    for step in range(0, 26):
        if step == 13:
            said = []
        least = max(math.ceil(compose.FLOOR / cap(v)) for _, v in said) if said else 0
        k = 1 - 0.04 * (step % 13)
        cs = max(round(CAPTION[fmt] * k), least)
        measure = (f.r - f.l) / math.cos(t) - math.tan(t) * cs * 1.18 * 4 - 8
        x = f.l
        if hook:
            hs = AGE[fmt] * k
            fig = hs * cap("display", beat["name"].isdigit())
            rows = [beat["name"]]
        else:
            hs = HEAD[fmt] * k
            fig = hs * cap("display")
            # a turned row spans its advance times cos(t) plus its height times sin(t)
            rows = wrap(beat["name"], hs, "display", (f.r - f.l - (cap("display") + 0.25) * hs * math.sin(t)) / math.cos(t) - 8)
        lead = hs * 1.02
        block = []
        for text, voice in said:
            block += [(r, voice) for r in wrap(text, cs, voice, measure)[:2]]
        if side == "over":
            # the words stand on the edge and the name over them
            ws = [pivot[1] - RAISE - (len(block) - 1 - j) * cs * LEAD for j in range(len(block))]
            y0 = ws[0] - cap(block[0][1]) * cs - APART - 0.25 * hs if block and rows else pivot[1] - RAISE
            ys = [y0 - (len(rows) - 1 - j) * lead for j in range(len(rows))]
        else:
            # the name hangs from the edge and the words under it
            y0 = pivot[1] + RAISE + fig
            ys = [y0 + j * lead for j in range(len(rows))]
            first = (ys[-1] + 0.25 * hs + APART if rows else y0 - fig) + cap(block[0][1]) * cs if block else 0
            ws = [first + j * cs * LEAD for j in range(len(block))]
        head = [line(r, x, y, hs, "display", name=f"head-{j + 1}", **rot) for j, (r, y) in enumerate(zip(rows, ys))]
        small = []
        if hook:
            beside = x + width(beat["name"], hs, "display") + 24
            said_beside = [tag(wish)] + ([compose.when(wish["date"])] if wish.get("date") else [])
            room = f.r - beside - 8
            ss = max(small_px(), min([round(fig * TAG_SHARE)] + [math.floor(small_px() * room / width(s, small_px(), "small")) for s in said_beside]))
            small = [line(said_beside[0], beside, y0 - fig + cap("small") * ss, ss, "small", name="tag", **rot)]
            if wish.get("date"):
                small.append(line(said_beside[1], beside, y0, ss, "small", name="date", **rot))
        lines = small + [line(r, f.l, y, cs, v, name=f"{stem}-{j + 1}", **rot) for j, ((r, v), y) in enumerate(zip(block, ws))]
        pts = [q for ln in head + lines for q in hull(ln)]
        whole = all(len(wrap(text, cs, voice, measure)) <= 2 for text, voice in said) and len(rows) <= 2
        across = max((q[0] for ln in head + small for q in hull(ln)), default=f.l) <= f.r  # the figure and the small lines beside it
        narrow = all(max(q[0] for q in hull(ln)) - min(q[0] for q in hull(ln)) <= f.r - f.l - 2 for ln in head + lines)
        if not pts or whole and across and narrow and min(q[1] for q in pts) >= f.t and max(q[1] for q in pts) <= f.b:
            break
    # a turned line moves sideways as it turns: each is slid back inside the safe area's sides, its pivot with it, so it
    # moves level and keeps its height
    for ln in head + lines:
        xs = [p[0] for p in hull(ln)]
        dx = f.l - min(xs) + 1 if min(xs) < f.l else f.r - max(xs) - 1 if max(xs) > f.r else 0
        if dx:
            ln["x"] = round(ln["x"] + dx, 1)
            ln["pivot"] = [round(ln["pivot"][0] + dx, 1), ln["pivot"][1]]
    return head, lines


def hull(ln):
    """The corners of a line's box as the frame draws it: its advance by its cap height (figure height for numerals)
    over its baseline and a quarter of its size under it, turned about its pivot."""
    w = width(ln["text"], ln["size"], ln["face"])
    x0 = ln["x"] - w if ln.get("anchor") == "end" else ln["x"]
    c = cap(ln["face"], ln["text"].isdigit()) * ln["size"]
    pts = [(x0, ln["y"] - c), (x0 + w, ln["y"] - c), (x0 + w, ln["y"] + 0.25 * ln["size"]), (x0, ln["y"] + 0.25 * ln["size"])]
    a = math.radians(ln.get("rotate", 0))
    cx, cy = ln.get("pivot") or (ln["x"], ln["y"])
    return [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in pts]


def baseline(ln):
    """The two ends of a line's baseline as the frame draws it."""
    w = width(ln["text"], ln["size"], ln["face"])
    x0 = ln["x"] - w if ln.get("anchor") == "end" else ln["x"]
    a = math.radians(ln.get("rotate", 0))
    cx, cy = ln.get("pivot") or (ln["x"], ln["y"])
    return [(cx + (x - cx) * math.cos(a) - (ln["y"] - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (ln["y"] - cy) * math.cos(a)) for x in (x0, x0 + w)]


def keep_rect(f, p, box, edge, side, asp):
    """The part of the card that stays on the wall: the largest box of its cell's shape (`asp`, width over height) on
    the subject's side of the edge that holds the subject (grown past the edge when the subject needs it), inside the
    photograph."""
    ix, iy, iw, ih = box
    s = subject_of(p)
    sx0, sy0, sx1, sy1 = ix + s[0] * iw, iy + s[1] * ih, ix + s[2] * iw, iy + s[3] * ih
    kh = f.H - max(edge.y(0), edge.y(f.W)) if side == "over" else min(edge.y(0), edge.y(f.W))
    kw = kh * asp
    kw = max(kw, (sx1 - sx0) * 1.08, (sy1 - sy0) * 1.08 * asp)
    kw = min(kw, iw, ih * asp)
    kh = kw / asp
    kx = max(ix, min(ix + iw - kw, (sx0 + sx1) / 2 - kw / 2))
    if side == "over":
        ky = max(iy, min(iy + ih - kh, min(f.H, iy + ih) - kh))
        ky = min(ky, max(iy, sy0 - 0.04 * kh))
    else:
        ky = max(iy, 0)
        ky = min(iy + ih - kh, max(ky, sy1 + 0.04 * kh - kh))
    return [kx, ky, kw, kh]


def cells(f, n):
    """The wall's n cells, row by row, GUTTER px of paper between them and MARGIN px of it round the wall, so every
    photograph at the closer's rest is whole inside the frame: the square root of n rows, rounded, of the frame's
    height, the later rows one cell longer where n does not divide, each row's cells filling the frame's width inside
    the margin, so every cell holds a photograph and the cells keep near the frame's own shape."""
    rows = max(1, round(math.sqrt(n)))
    ch = (f.H - 2 * MARGIN - (rows - 1) * GUTTER) / rows
    out = []
    for r in range(rows):
        k = n // rows + (r >= rows - n % rows)
        cw = (f.W - 2 * MARGIN - (k - 1) * GUTTER) / k
        out += [[MARGIN + c * (cw + GUTTER), MARGIN + r * (ch + GUTTER), cw, ch] for c in range(k)]
    return out


# ---------------------------------------------------------------- the studio board

def frames_at(beats, bpm):
    """Each beat's first frame and length, rounded so the beats add up to the film exactly."""
    pulse = compose.FPS * 60 / bpm
    out, acc = [], 0.0
    for b in beats:
        a = round(acc * pulse)
        acc += b["pulses"]
        out.append((a, round(acc * pulse) - a))
    return out


def lay(board, fmt="reel", bpm=None):
    """The studio board for one format: every card's photograph, edge, field, name, words and cell on the wall; the
    closer's giant age and wish; the beats' frames, the board fitted to `bpm` (`fit`); the sound cues and the clips."""
    f = compose.Frame(fmt)
    bpm = bpm or board["bpm"]
    board = fit(board, bpm)
    use(board["style"])
    colors = board["colors"]
    refs = board.get("photos") or {}
    B = _env.B
    beats = [b for b in board["beats"]]
    cards_src = [b for b in beats if b["form"] in ("hook", "moment")]
    order = sorted(range(len(cards_src)), key=lambda i: (cards_src[i]["date"], i))
    cell_of = {cards_src[i]["id"]: j for j, i in enumerate(order)}
    grid = cells(f, len(cards_src))
    cards = []
    for b in cards_src:
        p = refs.get(b["post"]) or {}
        if not p:
            continue
        edge, box, ln, side = lay_photo(f, p, fmt)
        if not fits(f, p, edge, box, side):
            p = framed(f, p, fmt)
            edge, box, ln, side = lay_photo(f, p, fmt)
        head, lines = card_lines(f, edge, b, board["wish"], fmt, side)
        ink, shade = type_light(B, f, p, box, [*head, *lines])
        for ln in [*head, *lines]:
            ln["color"] = ink
        xs = [q[0] for ln in [*head, *lines] for q in hull(ln)]
        cell = grid[cell_of[b["id"]]]
        kr = keep_rect(f, p, box, edge, side, cell[2] / cell[3])
        s = cell[2] / kr[2]
        T = {"s": round(s, 5), "o": [round(cell[0] - s * kr[0], 2), round(cell[1] - s * kr[1], 2)]}
        x0, y0, cw, ch = cell
        sub = subject_of(p)
        cards.append({"key": b["id"], "post": b["post"], "hook": b["form"] == "hook", "file": p["file"], "place": box, "line": edge.line,
                      "tilt": edge.tilt, "along": bool(ln), "side": side, "field": field_for(B, colors, f, p, edge, box), "T": T,
                      "slot": [[round(x0, 1), round(y0, 1)], [round(x0 + cw, 1), round(y0, 1)], [round(x0 + cw, 1), round(y0 + ch, 1)], [round(x0, 1), round(y0 + ch, 1)]],
                      "head": head, "lines": lines, "type": ink, "shade": shade, "type_x": [round(min(xs), 1), round(max(xs), 1)] if xs else None,
                      "subject": [round(box[0] + sub[0] * box[2], 1), round(box[1] + sub[1] * box[3], 1), round(box[0] + sub[2] * box[2], 1), round(box[1] + sub[3] * box[3], 1)]})
    closer = closer_lines(f, board, fmt)
    at = frames_at(beats, bpm)
    entries(cards)
    # each beat under the form the moves know it by: the hook is the title, a moment a photograph, the closer the wall
    forms = {"hook": "title", "moment": "photo", "closer": "closer"}
    subjects = {c["key"]: c["subject"] for c in cards}
    studio_beats = [{"id": b["id"], "form": forms[b["form"]], "frames": n, "bars": round(b["pulses"] / 4, 4), "move": b.get("move"), "transition": b.get("transition"),
                     "label": label_of(f, b, subjects.get(b["id"])), "peak": bool(b.get("peak"))}
                    for b, (a, n) in zip(beats, at)]
    st = {"id": f"tribute-{board['style']}-{fmt}", "name": f"{board['name']} ({fmt})", "handle": board["handle"], "year": board["year"], "bpm": bpm,
          "style": board["style"], "format": {"name": fmt, "width": f.W, "height": f.H, "fps": compose.FPS},
          "system": compose.system(compose.card(board["style"]), colors),
          "beats": studio_beats, "film": {"cards": cards, "closer": closer}}
    st["sound"] = sound(board, st)
    st["clips"] = clips(board, st)
    return st


# the share of the frame's height, top to foot, that the looks' moves print a beat's label in: the sticker, the pen
# loop, the date stamp, the band, the foot line all sit in the frame's lower part
LABEL_BAND = (0.6, 0.9)


def label_of(f, b, subject):
    """A moment's date for the move to print, only where it lands clear of the people: a photograph whose subject reaches
    into the band the moves print a label in (`LABEL_BAND`) gets none, so no sticker or pen loop is ever drawn over a
    face, and its move shows the print alone. The hook and the closer have no label."""
    if b["form"] != "moment" or not subject:
        return ""
    top, foot = LABEL_BAND[0] * f.H, LABEL_BAND[1] * f.H
    if subject[3] > top and subject[1] < foot:
        return ""
    return compose.when(b["date"], False)


def entries(cards):
    """How each card's print comes onto the wall, from its own shape: one whose line is steep hinges about it, a wide one
    slides along it, any other rises from below; never the way the card before it came. The hook falls flat."""
    prev = None
    for c in cards:
        if c["hook"]:
            c["entry"] = prev = "fall"
            continue
        wide = c["place"][2] > c["place"][3] * 1.25
        want = ["hinge" if abs(c["tilt"]) >= 6 else "slide" if wide else "rise", "rise", "slide", "hinge"]
        c["entry"] = prev = next(e for e in want if e != prev)


def closer_lines(f, board, fmt):
    """The giant age cut out of the cover, centred, as large as the safe area allows under the wish's title and over
    its date (when the day was given) and sender; its last figure, set alone where it stands in the age; the wish's
    lines in the paper's color; and `bands`, the top and bottom of the solid core of the band of the ground's dark
    laid across the wall under the title and under the date and sender, BAND px past their lines, so the wish reads
    over any photograph."""
    w = board["wish"]
    title = w["title"]
    ts = WISH[fmt]
    while ts > 40 and width(title, ts, "wish") > f.r - f.l:
        ts -= 2
    num = w["number"]
    small = ([compose.when(w["date"])] if w.get("date") else []) + [f"from {w['from']}"]
    room_top = f.t + cap("wish") * ts + 0.3 * ts + 56
    room_bot = f.b - 56 - cap("small") * small_px() - (len(small) - 1) * small_pitch() - 0.25 * small_px()
    fig = cap("display", num.isdigit())
    em = min((room_bot - room_top) / fig, (f.W - 2 * MARGIN) / (width(num, 1, "display")))
    gw = width(num, em, "display")
    base = room_top + fig * em + ((room_bot - room_top) - fig * em) / 2
    x = (f.W - gw) / 2
    big = line(num, x, base, em, "display", name="big")
    # centred on the frame, held inside the safe area's sides where they sit off the middle (the reel's right)
    tx = min(max((f.W - width(title, ts, "wish")) / 2, f.l), f.r - width(title, ts, "wish"))
    lines = [line(title, tx, base - fig * em - 56, ts, "wish", name="title")]
    for j, t in enumerate(small):
        lines.append(line(t, (f.W - width(t, small_px(), "small")) / 2, base + 56 + cap("small") * small_px() + j * small_pitch(), small_px(), "small", name=f"wish-{j + 1}"))
    last = line(num[-1], x + gw, base, em, "display", anchor="end", name="last")
    span = lambda group: [round(min(q[1] for ln in group for q in hull(ln)) - BAND, 1),
                          round(max(q[1] for ln in group for q in hull(ln)) + BAND, 1)]
    return {"big": big, "last": last, "lines": lines, "bands": [span(lines[:1]), span(lines[1:])], "stop": None}


# ---------------------------------------------------------------- times, sound, story, clips

def times(board):
    """Every beat's start in musical beats, and per card its arrival, its landing and its leave."""
    out, at = {}, 0.0
    beats = board["beats"]
    for i, b in enumerate(beats):
        nxt = at + b["pulses"]
        out[b["id"]] = {"at": at, "end": nxt, "cut": at + (HOOK_LIFT if b["form"] == "hook" else LIFT), "leave": nxt - LEAVE}
        at = nxt
    return out


def sound(board, st):
    """The cues, at musical beats from the film's start: a hit where each card lands (the hook with its age, each
    moment's card with its name), the build as the closer's sheet falls over the wall, the impact of its slam (the film's
    peak), a hit as the last figure punches home, and the stop on the wish. Words rise and the camera moves without a
    sound of their own."""
    tm = times(board)
    cues = []
    for c in st["film"]["cards"]:
        cues.append({"kind": "hit", "at": round(tm[c["key"]]["cut"], 3), "weight": 1.0 if c["hook"] else 0.7,
                     "bright": 0.3 if c["hook"] else 0.45 if c["field"] == "paper" else 0.2})
    C = tm["closer"]["at"]
    cues += [{"kind": "riser", "at": round(C + 0.3, 3), "beats": 0.95},
             {"kind": "impact", "at": round(C + 1.25, 3)},
             {"kind": "hit", "at": round(C + 3.0, 3), "weight": 1.0, "bright": 0.1},
             {"kind": "stop", "at": round(C + STOP_AT, 3)}]
    return sorted(cues, key=lambda c: c["at"])


def story(board):
    """Per beat, one line on what its move reveals and what it carries across its cut."""
    out = {}
    beats = board["beats"]
    w = board["wish"]
    for i, b in enumerate(beats):
        nxt = beats[i + 1] if i + 1 < len(beats) else None
        on = (f"the wall, as the camera flies on to {nxt['name'] or 'the next photograph'}" if nxt and nxt["form"] == "moment"
              else "the wall, as the camera pulls back to it whole")
        if b["form"] == "hook":
            out[b["id"]] = (f"reveals: the occasion photograph lands and {w['number']}, {figure(w)}, rises out of its own line after "
                            f"\"{tag(w)}\"" + (f", the day after it" if w.get("date") else "") + f"; carries: {on}")
        elif b["form"] == "moment":
            said = (f"the line they traded under it, \"{b['talk'][0]['text'][:48]}\"" + (f" and \"{b['talk'][1]['text'][:48]}\"" if len(b["talk"]) > 1 else "")
                    if b["talk"] else f"\"{b['words'][:48]}\"" if b["words"] else "no other words")
            told = (f"{b['name']}: the photograph lands whole and its name rises out of its line beside its subject" if b["name"]
                    else "a photograph with no caption: it lands whole, its line lit beside its subject")
            out[b["id"]] = (f"reveals: {compose.when(b['date'])}, {told}" + (", its name alone, one of the fast run before the peak" if b.get("run") else f" with {said}")
                            + (", the year's peak, held longest" if b["peak"] else "")
                            + f"; the photograph trims into its cell of the wall; carries: {on}")
        else:
            out[b["id"]] = (f"reveals: the whole wall of the year, then a sheet carrying the wall with {w['number']} cut out of it falls shut over it, its shadow "
                            f"on the photographs through the figures; on the last hit the last figure punches through it; \"{w['title']}\" "
                            "rises; carries: nothing, the picture and the sound stop together and hold")
    return out


def clips(board, st):
    """The three clips an image-to-video model would make, one for each use a generated shot has in the film: the hook's
    world (the hook's photograph), texture between chapters (the card after the widest gap in the year's dates) and a
    still brought to life (the year's peak). Each is written from its beat's `shot`, what the agent saw in the
    photograph (`subject`, and what `moves` in it, every motion one that returns to where it began), with the camera's
    move its use asks for, the lens feel and the camera's height read from the photograph (`lens_of`, `height_of`), its
    light read from its pixels about its subject (`light_of`), the part of it the card's frame shows (`frame_of`), the
    beat's length and a seamless loop. Each record is a clip request in the shape motion/system/standards.md gives one:
    its use, subject, move, lens, light, duration and loop, and the prompt that says all of them. A beat with no `shot`
    yet has no subject and no prompt; storyboard.py check names it. A request is never a clip: until a video model makes
    it, the film shows the photograph still."""
    beats = board["beats"]
    cards = [b for b in beats if b["form"] == "moment"]
    laid = {c["key"]: c for c in st["film"]["cards"]}
    W, H = st["format"]["width"], st["format"]["height"]
    peak = next((b for b in cards if b.get("peak")), None)
    gap = lambda i: (compose.day(cards[i]["date"]) - compose.day(cards[i - 1]["date"])).days
    texture = next((cards[i] for i in sorted(range(1, len(cards)), key=lambda i: -gap(i)) if cards[i] is not peak), None)
    uses = [(USES[0], beats[0]), (USES[1], texture), (USES[2], peak)]
    out, seen = [], set()
    for (use, camera), b in uses:
        if not b or b["id"] in seen:
            continue
        seen.add(b["id"])
        p = (board.get("photos") or {}).get(b["post"]) or {}
        secs = round(b["pulses"] * 60 / board["bpm"], 1)
        shot = b.get("shot") or {}
        hook = b["form"] == "hook"
        subject = f"{shot['subject'].rstrip('.')}; {shot['moves'].rstrip('.')}" if shot.get("subject") and shot.get("moves") else None
        rec = {"id": f"{len(out) + 1:02d}", "beat": b["id"], "use": use, "image": p.get("file"),
               "subject": subject, "move": camera, "lens": f"{lens_of(p)}, {height_of(p)}", "light": light_of(p),
               "duration": secs, "loop": LOOP,
               "frame": ("the whole photograph, full frame" if hook else frame_of(laid[b["id"]]["place"], W, H)) if b["id"] in laid else None,
               "prompt": None}
        if subject:
            rec["prompt"] = (f"{subject}. Camera: {camera}. Lens: {rec['lens']}. Light: {rec['light']}. "
                             f"Frame: {rec['frame'] or 'the whole photograph'}. {secs} s. {LOOP}")
        out.append(rec)
    return out


# the uses a generated clip has, and the camera's move each asks for
USES = [("the hook's world", "a slow push in toward the subject, the place around them alive and opening past the photograph's edges"),
        ("texture between chapters", "a slow sideways drift close across the subject, holding on its surfaces and the light on them"),
        ("a still brought to life", "locked off, breathing a little, only what moves in the scene moving")]
# the loop part every clip request ends on
LOOP = ("one continuous shot with no cut, a seamless loop: every motion in it a cycle that returns to where it began, so "
        "its last frame is its first")


def frame_of(box, W, H):
    """The part of a photograph laid at `box` (x, y, width, height in the frame's px) that a W x H card shows, in words."""
    x0, x1 = max(0.0, -box[0] / box[2]), min(1.0, (W - box[0]) / box[2])
    y0, y1 = max(0.0, -box[1] / box[3]), min(1.0, (H - box[1]) / box[3])
    k = math.gcd(W, H)
    shape = "portrait" if H > W else "landscape" if W > H else "square"
    return (f"a {shape} {W // k}:{H // k} card showing {round(100 * x0)}% to {round(100 * x1)}% of the photograph across and "
            f"{round(100 * y0)}% to {round(100 * y1)}% down; the subject and all its motion inside that part")


def lens_of(p):
    """The lens feel a photograph was taken with, read from how much of it its subject fills."""
    s = subject_of(p)
    area = (s[2] - s[0]) * (s[3] - s[1])
    if area > 0.35:
        return "an 85 mm portrait lens, shallow focus, the background soft"
    if area > 0.12:
        return "a 50 mm lens at a natural perspective"
    return "a 28 mm wide lens, deep focus, the place around the subject in frame"


def tones_of(im):
    """(mean luminance, its spread, the warmth of the brightest tenth, the mean step between neighboring pixels) of an
    image, each 0 to 1: the light's color shows in the highlights, never in the colors of the things it falls on."""
    px = list(im.getdata())
    lum = [(0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 for r, g, b in px]
    mean = sum(lum) / len(lum)
    spread = (sum((v - mean) ** 2 for v in lum) / len(lum)) ** 0.5
    top = sorted(range(len(px)), key=lambda i: -lum[i])[:max(1, len(px) // 10)]
    warm = sum(px[i][0] - px[i][2] for i in top) / len(top) / 255
    w = im.size[0]
    step = sum(abs(lum[i] - lum[i + 1]) for i in range(len(lum) - 1) if (i + 1) % w) / max(1, len(lum) - len(lum) // w)
    return mean, spread, warm, step


def height_of(p):
    """The camera's height, read from the photograph's horizon: its strongest level line with open sky over it (the
    part above brighter and smoother than the part below). With no horizon the camera keeps the photograph's own
    height and angle."""
    ln = next((l for l in p.get("lines") or [] if abs(l[0]) <= 4 and l[2] >= 1.6), None)
    im = pixels(_env.B, p.get("file") or "")
    if ln and im is not None and 0.05 < ln[1] < 0.95:
        w, h = im.size
        cut = round(ln[1] * h)
        above, below = tones_of(im.crop((0, 0, w, cut))), tones_of(im.crop((0, cut, w, h)))
        if above[0] > below[0] + 0.05 and above[3] < below[3]:
            if ln[1] < 0.33:
                return "the camera high and looking down a little, the horizon near the top of the frame"
            if ln[1] > 0.67:
                return "the camera low and looking up a little, the horizon near the bottom of the frame"
            return "the camera at eye height, the horizon level across the frame"
    return "the camera at the photograph's own height and angle"


def light_of(p):
    """The photograph's light in words, read from its pixels: a subject much darker than the frame around it stands
    against the light, in silhouette; otherwise how bright the frame is, how warm its highlights and how hard."""
    im = pixels(_env.B, p.get("file") or "")
    if im is None:
        return "the photograph's own light"
    w, h = im.size
    s = subject_of(p)
    box = (round(s[0] * w), round(s[1] * h), max(round(s[2] * w), round(s[0] * w) + 1), max(round(s[3] * h), round(s[1] * h) + 1))
    mean, spread, warm, _ = tones_of(im)
    lit = tones_of(im.crop(box))[0]
    if lit < 0.6 * mean and mean > 0.2:
        sun = "the low sun" if warm > 0.06 else "the open sky"
        return f"backlit by {sun} behind the subject, the subject in silhouette with its edges rimmed in light, the sky the brightest part"
    if mean < 0.3:
        base = "low warm lamplight" if warm > 0.04 else "dim cool night light"
    elif mean > 0.62:
        base = "bright warm sun" if warm > 0.06 else "bright open daylight"
    else:
        base = "warm low sun" if warm > 0.06 else "cool daylight" if warm < -0.02 else "even daylight"
    return f"{base}, {'hard, with deep shadows' if spread > 0.24 else 'soft, with open shadows'}"


# ---------------------------------------------------------------- checks

def check(board, st):
    """Plain sentences, one per break of the frame's rules: a card's line outside the safe area at rest (`rest`) or under
    the floor, a subject cut by its edge or by the frame, the giant age outside the frame."""
    fmt = st["format"]["name"]
    f = compose.Frame(fmt)
    a = rest(f)
    out = []
    for c in st["film"]["cards"]:
        for ln in [*c["head"], *c["lines"]]:
            pts = hull(ln)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            if min(xs) < a.l - 1 or max(xs) > a.r + 1 or min(ys) < a.t - 1 or max(ys) > a.b + 1:
                out.append(f"{fmt} {c['key']}: '{ln['text'][:30]}' leaves the safe area ({round(min(xs))}, {round(min(ys))}, {round(max(xs))}, {round(max(ys))})")
            if cap(ln["face"], ln["text"].isdigit()) * ln["size"] < compose.FLOOR - 0.05:
                out.append(f"{fmt} {c['key']}: '{ln['text'][:30]}' is drawn under the {compose.FLOOR} px floor")
            yl, yr = c["line"]
            base = baseline(ln)
            under = c.get("side") == "under"
            if any((y < yl + (yr - yl) * x / f.W - 1) if under else (y > yl + (yr - yl) * x / f.W + 1) for x, y in base):
                out.append(f"{fmt} {c['key']}: '{ln['text'][:30]}' sits on the subject's side of its edge")
        sx0, sy0, sx1, sy1 = c["subject"]
        yl, yr = c["line"]
        ey = lambda x: yl + (yr - yl) * x / f.W
        e = Edge(f.W, (yl + yr) / 2, c.get("tilt", 0))
        part = covered(e, [0, 0, 1, 1], [sx0, sy0, sx1, sy1], c.get("side", "over"))
        if part > COVERED + 0.005:
            out.append(f"{fmt} {c['key']}: the edge cuts the subject of {c['post']} ({round(100 * part)}% of it stands on the type's side)")
        seen = min((min(sx1, f.W) - max(sx0, 0)) / max(1, sx1 - sx0), (min(sy1, f.H) - max(sy0, 0)) / max(1, sy1 - sy0))
        if seen < FRAMED:
            out.append(f"{fmt} {c['key']}: the frame cuts the subject of {c['post']} (only {round(100 * seen)}% of it is in the frame)")
    cl = st["film"]["closer"]
    for ln in cl["lines"]:
        pts = hull(ln)
        if min(p[0] for p in pts) < f.l - 1 or max(p[0] for p in pts) > f.r + 1 or min(p[1] for p in pts) < f.t - 1 or max(p[1] for p in pts) > f.b + 1:
            out.append(f"{fmt} closer: '{ln['text'][:30]}' leaves the safe area")
    big = hull(cl["big"])
    if min(p[0] for p in big) < MARGIN - 1 or max(p[0] for p in big) > f.W - MARGIN + 1:
        out.append(f"{fmt} closer: the age runs past the frame's margin")
    return out


def hook_frame(board, bpm=None):
    """The frame the hook's event lands on: the age risen out of the photograph's line as it lands."""
    return round(HOOK_LIFT * compose.FPS * 60 / (bpm or board["bpm"]))


def rest_frames(st, board):
    """(beat, frame) of each rest moment: a card at rest with its words up, just before the camera's move off it starts;
    the closer at its stop."""
    tm = times(board)
    pulse = compose.FPS * 60 / st["bpm"]
    last = board["beats"][-2]["id"]
    out = []
    for bid in board["rest"]:
        t = tm[bid]
        at = t["at"] + STOP_AT + 0.5 if bid == "closer" else t["end"] - (2 * GO if bid == last else GO) - 0.1
        out.append((bid, round(at * pulse)))
    return out
