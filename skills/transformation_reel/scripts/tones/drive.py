'''drive: one camera walks the wall they built, from day one to the latest, in chapters told in their own captions.

The wall is there from the first frame: a wall in the board's ground color with a print for every post in calendar
order, laid in bands two cells tall that the camera walks one way and then back, under one plain course across the
wall's top where the closer's words are set, which no print's station frames. Day one opens the first band and the
latest closes the last, each four cells large; a milestone or a tall photograph stands in a cell two rows tall, and the
other posts stand two to a column, top and bottom in whichever order keeps the camera's steps from repeating. The tiles
the camera has not reached stand dim. At each post its print lifts out of its tile toward the lens and comes to light:
the photograph at its own proportions (cropped about its focal point only past ASPECT) in a paper border, with a label
under it that carries its date, their line and on a chapter their next line, so no word ever stands on a photograph; a
post with no line keeps a narrow strip for its date alone. It lands a little past its station and settles, stands off
the wall with its shadow on the wall under it, and the camera pushes in through its hold. Their words enter letter by
letter and are read before they leave; the print then drops back into its tile and the camera moves on, the empty
mount of its tile showing while it is out. The camera's path between two prints follows the step on the wall (a crane
up or down a column, a glide along a band, a sweep or a swing across it, a reveal of the wall so far into a chapter),
never the same path twice in a row, and runs as long as the distance it crosses on the reel's wall, so the three
formats keep one timing and one score. The film ends on the whole wall: day one and the latest at its two ends, their
first and latest dates and the ask (the call to action they asked for) on the course; then the style's closer.

A board is made in one style, a card in styles/ (compose.py reads it): the card's faces set every line, in their case,
tracking and line height; the card's palette rule makes the colors from their photographs' colors, and the film takes
its ground, paper, ink and words from those roles; the card's easing times the camera's travel, the prints' landing
and the letters, and its lean scales how far the camera banks and turns; every beat takes a move and the cut into it
from the card's allowlists, chosen by what the beat is (`pick`), and the cut decides whether the camera travels to
the next print or is there at the cut; the picture takes the card's finish (its grade, grain, bars), and the film ends
on the card's closer shape: the span in their own words ("fourteen months in", or their two dates) with the ask or
their handle. The tempo is the board's: the style's music recipe sets it, and every time below is in its beats.

`build(rows, fx, who, fmt, sizes, style, colors, bpm)` returns the board the 3D film (motion/studio/drive) renders:
every place in px of the closer's frame (the wall, y down), every time in musical beats from the film's start. Python
decides everything; the film only draws it. The board carries:
  film     the wall: one card per post (its print at its station, its photograph and its label there, its tile of the
           wall and the photograph's box in it, the windows onto the photograph each shows, its date, their line and,
           on a chapter, their next line, the camera's push through its hold and its path into it), the course with
           the dates and the ask, the closer shape with the span, the colors and the easing.
  beats    the opening, one per post, the wall and the closer, each with the move and the cut into it the card allows:
           the timeline, the strips and the critic read these.
  sound    every cue at the beat of the event it belongs to, with what it is for.
  clips    the six shots an image-to-video model would make for the film (the hook's world, the stills brought to
           life, the texture between chapters), each written from what its photograph measures as a request the agent
           sends; until a clip comes back, the print stands in with its own move and is never called a clip.
  scenes   per beat, its photograph, their line on it, what the move reveals and what it carries across the cut.
  stills   the rest moments the story cards and the vote's styleframes use.
'''
import math
import re
import statistics
from datetime import date
from functools import lru_cache
from pathlib import Path

import compose

FPS = 30
SIZES = {"reel": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080)}

LONGEST = 60.0     # the longest reel, in seconds
# a card's hold, in beats from its landing to the next card's landing (the hook's from the first frame): at the film's
# own pace before what its photograph carries is weighed, the least a card is on screen however short the film, and
# the most it holds however long; day one, the milestones and the latest are chapters
PACE = {"hook": 4.5, "ordinary": 2.0, "chapter": 4.0}
SEEN = {"ordinary": 1.5, "chapter": 2.25}
MOST = {"ordinary": 6.5, "chapter": 11.0}
CARRY = 0.04       # each word on a card holds it this share longer
SAME = 0.02        # a mean change of the light grid this small reads as the same view: a repeat holds shorter
# the camera's move between two stations, in beats: a base and a share per cell of the reel's wall it crosses, kept
# between a least and a most; into a chapter it takes CHAPTER_MORE longer
TRAVEL = (0.45, 0.55, 0.9, 2.75)
CHAPTER_MORE = 0.5
PEAK_MORE = 0.75   # the peak holds on screen at least this much longer than any other card
CLOSER_MOVE = 2.0  # the pull back from the latest to the whole wall
WALL_READ = 2.5    # from the camera settling on the whole wall to the closer shape: the dates and the ask land, the wall reads
# the closer shape, from its start to the stop: this many beats, and at a slow tempo no longer than CLOSER_MOST seconds,
# because a shape settles a little past the middle of its run and the picture never stands still a second before the stop
CLOSER_HOLD = 3.0
CLOSER_MOST = 1.7
HOLD = (2.0, 4.0, 6.0)  # the held, silent picture after the stop: its least, its pace and its most, in seconds
HELD = 0.45        # the least a card holds still under the camera
LETTERS = 0.75     # a chapter's line, from its first letter entering to its last landed
LAND = 0.55        # an ordinary card's line, the same
READ = (0.5, 0.17)  # the seconds a line of n words needs on screen once it has landed: READ[0] + READ[1] * n

HOOK_DIVE = 0.8    # the camera's dive from the whole wall of dim tiles onto day one, in seconds, as day one lifts out
MASK_HOLD = 4.0    # the beats a type mask holds the peak's line past the camera's arrival at its print, before the cut to it
HOOK_LINE = 0.75   # the hook's line, from its first letter entering as the dive lands to its last landed, in beats
OPEN_WORD = 1.0    # an opening move that sets the span word by word holds the whole wall this long a word before the dive
NEXT = 0.75        # their next line enters this long after the line it follows lands
EXIT = 0.25        # a card's lines leave letter by letter over this long, ending as its print starts to drop
RISE = 0.6         # the share of the camera's move into a print over which the print lifts out of its tile, as RISE in
                   # motion/studio/drive/plan.ts

# the wall: its margin, the gap between two tiles, and a print's paper border in its tile (a share of the tile's
# shorter side), all wall px; a cell's proportions come near the set's median photograph inside CELL
MARGIN = 12
GAP = 6
TILE_BORDER = 0.035
CELL = (0.8, 1.5)
# the course across the wall that the closer's dates and ask are set on: its height, the left and right edges of its
# type and its top and bottom (the safe lines), and the sizes of the dates and the ask. The course runs across the
# wall's top and reaches up past the top safe line, so the words have its whole height inside the safe lines, and
# every station frames the wall below it, so no print stands with the bare course filling its frame.
COURSE = {
    "reel": {"height": 180, "x": [72, 930], "words": [270, 1250], "date": 52, "call": 60},
    "square": {"height": 260, "x": [64, 1016], "words": [64, 1016], "date": 46, "call": 54},
    "landscape": {"height": 200, "x": [96, 1824], "words": [64, 1016], "date": 48, "call": 58},
}

# a print at its station, in px of the screen at the station's framing: the box it is centered in (its label's type
# inside the safe lines), the label's padding, the least share of the box's width a card takes (a tall photograph
# stands on a wider sheet, so their words have room), and the sizes of the date, their line and their next line. The
# photograph is shown CARD_K times its size in its tile, the camera framing at most FRAME_MOST of the wall's height,
# and the station keeps EDGE of its frame inside the wall's edge
STATION = {
    "reel": {"box": [72, 110, 930, 1252], "pad": 40, "wide": 0.62, "date": 42, "title": 112, "rest": 44},
    "square": {"box": [96, 64, 984, 1016], "pad": 34, "wide": 0.6, "date": 42, "title": 92, "rest": 42},
    "landscape": {"box": [400, 64, 1520, 1016], "pad": 36, "wide": 0.52, "date": 42, "title": 100, "rest": 42},
}
BORDER = 16        # the print's paper border at its station, px of the screen
ASPECT = (0.6, 1.8)  # a photograph is shown at its own proportions inside these; past them, cropped about its focal point
CARD_K = 1.6
FRAME_MOST = 0.78
EDGE = 0.03
INSET = 30         # the least a line of type stands inside its print's edge, px of the screen
TITLE_LINES = 3    # their line and their next line are each set in at most three lines, shrinking until they fit
LIFT = {"ordinary": 80, "chapter": 110}  # how far a card stands off the wall at its station, wall px
PUSH = {"ordinary": 0.03, "chapter": 0.05}  # how far the camera pushes in on a card through its hold
HAND = 0.009       # the most the operator's hand (motion/system/three/Stage.tsx) moves the picture, a share of its height
HOLD_FOV = 30
CLOSER_FOV = 18
# the camera's path into a post, by the step it takes on the wall: how far it pulls back at the path's middle (a share
# of the frame's height), how far it tips toward the way it travels up or down, and banks and turns toward the way it
# travels across (radians, at the fullest lean a card names, LEAN; a card with less lean banks and turns that much
# less). A step up or down a column cranes, along a band glides, across a band sweeps or swings, and into a chapter
# reveals the wall so far; a path that would repeat the one before takes its ALT
PATHS = {
    "crane": {"arc": 0.1, "pitch": 0.08, "bank": 0.0, "yaw": 0.0},
    "glide": {"arc": 0.06, "pitch": 0.0, "bank": 0.05, "yaw": 0.06},
    "sweep": {"arc": 0.18, "pitch": 0.05, "bank": 0.08, "yaw": 0.05},
    "swing": {"arc": 0.26, "pitch": 0.07, "bank": 0.1, "yaw": 0.04},
    "reveal": {"arc": 0.55, "pitch": 0.03, "bank": 0.02, "yaw": 0.0},
}
LEAN = 0.04
STEP = {(0, 1): "crane", (0, -1): "crane", (1, 0): "glide", (-1, 0): "glide", (0, 0): "glide",
        (1, 1): "sweep", (-1, -1): "sweep", (1, -1): "swing", (-1, 1): "swing"}
ALT = {"crane": "swing", "glide": "sweep", "sweep": "glide", "swing": "crane", "reveal": "swing"}
# a print is one photograph on a wall with their words on its label: a move that splits the frame in two, darkens or
# papers over the whole frame, lays a band of type over the picture, or opens the film from black never lands on one,
# so their words are never covered while they read
NOT_ON_A_PRINT = {"diptych", "long-fade-title", "white-space-crop", "line-by-line-type-rise", "word-per-beat-slam",
                  "type-mask-reveal", "width-stretch", "marquee", "bars-open"}
# a move that closes fields of the card's inks over the whole frame opens a chapter: it plays into day one, a milestone
# or the latest, and an ordinary print is reached by the camera alone, so the walk along the wall stays one shot
OVER_THE_FRAME = {"stack-and-split"}
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


# ------------------------------------------------------------------ the look
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _lum(h):
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in _rgb(h)]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def film_colors(roles, rule):
    """The film's colors, every one a role the card's palette rule made: the wall (ground) is the background; the
    print's sheet is the paper, or on a two-ink card whose paper is its background, the second ink; the label's words
    take the role that stands out most on the sheet; the words on the wall the accent where it reads on the ground, else
    the role that stands out most there; and the shadow the darkest role."""
    names = ("bg", "ink", "paper", "accent", "accent2", "muted")
    best = lambda on: max(names, key=lambda n: contrast(roles[n], on))
    ground = roles["bg"]
    sheet = roles["accent"] if rule == "two-inks" and contrast(roles["paper"], ground) < 1.5 else roles["paper"]
    words = roles["accent"] if contrast(roles["accent"], ground) >= 3 else roles[best(ground)]
    return {"ground": ground, "paper": sheet, "ink": roles[best(sheet)], "words": words, "line": roles[best(ground)],
            "shade": min((roles[n] for n in names), key=_lum)}


def short(d):
    d = date.fromisoformat(d)
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def leading(face):
    """The distance between two baselines of a face's lines, in sizes: the card's line height."""
    return compose.face_of(face)["lineHeight"]


def wrap(text, size, face, most):
    """`text` in lines no wider than `most` px at `size`, broken at spaces, as evenly as that many lines allow."""
    def lines_at(most):
        lines, cur = [], ""
        for w in text.split():
            nxt = f"{cur} {w}".strip()
            if cur and compose.width(nxt, size, face) > most:
                lines.append(cur)
                cur = w
            else:
                cur = nxt
        return lines + ([cur] if cur else [])

    best = lines_at(most)
    lo, hi = most * 0.4, most
    while hi - lo > 4:
        mid = (lo + hi) / 2
        if len(lines_at(mid)) == len(best):
            hi = mid
        else:
            lo = mid
    return lines_at(hi)


def fit(text, size, face, most, top, least=0.0):
    """`text` in at most `top` lines, each no wider than `most` px: its size shrinks until the widest line fits, a long
    word as much as a long line, but never under `least`, where it takes the lines it needs. The lines (in the face's
    case) and the size."""
    lines = wrap(text, size, face, most)
    while (len(lines) > top or any(compose.width(ln, size, face) > most for ln in lines)) and size > least:
        size = max(least, size * 0.88)
        lines = wrap(text, size, face, most)
    return [compose.cased(ln, face) for ln in lines], size


def set_line(face, **kw):
    """A line of type as the film sets it: in its face, with the face's tracking."""
    return {**kw, "face": face, "tracking": compose.face_of(face)["tracking"]}


def least_size():
    """The least size a line takes so its cap height stays over TYPE_FLOOR on screen."""
    return (TYPE_FLOOR + 0.5) / min(compose.cap("display"), compose.cap("text"))


def reading(words, bpm):
    """The beats a line of `words` words needs on screen once it has landed."""
    return (READ[0] + READ[1] * words) * bpm / 60 if words else 0.0


def window(aspect, sw, sh, focal):
    """The part of a photograph (aspect w/h) a box sw x sh shows, covering it about the focal point: [u0, v0, u1, v1]
    in the photograph's texture, v up."""
    if sw / sh > aspect:
        uw, vh = 1.0, aspect * sh / sw
    else:
        uw, vh = sw / sh / aspect, 1.0
    fx, fy = focal
    u0 = min(max(fx - uw / 2, 0.0), 1.0 - uw)
    v0 = min(max((1 - fy) - vh / 2, 0.0), 1.0 - vh)
    return [round(u0, 5), round(v0, 5), round(u0 + uw, 5), round(v0 + vh, 5)]


# ------------------------------------------------------------------ the wall
def talls(rows, units):
    """Which posts between day one and the latest stand in a tall cell, the rest two to a column, so that they fill
    `units` columns: per column, 1 (a tall cell) or 2 (a pair), in calendar order, never two tall cells side by side,
    the tall cells going first to milestones, then to tall photographs, last to wide ones."""
    mid = rows[1:-1]
    m = len(mid)
    want = 2 * units - m
    pr = [2.0 * bool(r.get("milestone")) + (1.0 if r["aspect"] < 0.9 else 0.0) - (0.5 if r["aspect"] > 1.2 else 0.0) for r in mid]

    @lru_cache(maxsize=None)
    def best(i, t, last):
        if i == m:
            return (0.0, ()) if t == 0 else (-math.inf, ())
        out = (-math.inf, ())
        if t > 0 and not last:
            v, rest = best(i + 1, t - 1, True)
            out = max(out, (v + pr[i], (1,) + rest))
        if i + 1 < m:
            v, rest = best(i + 2, t, False)
            out = max(out, (v, (2,) + rest))
        return out
    return list(best(0, want, False)[1])


def step_of(a, b, cell):
    """The direction of a step between two tiles' middles, each axis -1, 0 or 1 (under 0.3 of a cell is no step)."""
    sg = lambda d, dz: 0 if abs(d) < dz else (1 if d > 0 else -1)
    return (sg(b[0] - a[0], 0.3 * cell[0]), sg(b[1] - a[1], 0.3 * cell[1]))


def middle(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def wall(rows, fmt, W, H):
    """The wall in format `fmt` (W x H wall px, the closer's frame): its bands of two rows of cells and the course, and a
    tile per post in calendar order. The bands run left to right and then right to left in turn; day one fills the first
    band's first two columns and the latest the last band's last two; each column between holds a tall cell or a pair
    (`talls`), a pair's top and bottom in whichever order keeps two steps in a row from going the same way. The band and
    column counts are the ones whose cells come nearest the set's median photograph. The course runs across the wall's top,
    reaching up past the top safe line so their words have its whole height inside the safe lines. Returns {"tiles",
    "band" (per post), "course" [x0, y0, x1, y1], "cell" [w, h], "bands", "cols"}."""
    n = len(rows)
    spec = COURSE[fmt]
    hc = spec["height"]
    hc += max(0, spec["words"][0] - MARGIN)
    target = min(CELL[1], max(CELL[0], statistics.median(r["aspect"] for r in rows)))
    m = n - 2
    found = None
    for nb in range(1, 13):
        for nc in range(2, 17):
            units = nb * nc - 4
            if (nb == 1 and nc < 4) or units < 0 or not (m <= 2 * units and units <= m and 3 * units <= 2 * n - 3):
                continue
            bh = (H - 2 * MARGIN - hc - nb * GAP) / nb
            ch, cw = (bh - GAP) / 2, (W - 2 * MARGIN - (nc - 1) * GAP) / nc
            if ch <= 0 or cw <= 0:
                continue
            cost = abs(math.log(cw / ch / target))
            if found is None or cost < found[0] - 1e-9:
                found = (cost, nb, nc, bh, ch, cw)
    if found is None:
        raise ValueError(f"{n} posts make no wall")
    _, nb, nc, bh, ch, cw = found
    units = talls(rows, nb * nc - 4)
    top = lambda b: MARGIN + hc + GAP + b * (bh + GAP)
    col = lambda c: MARGIN + c * (cw + GAP)
    # each band's columns in the order the camera walks them, and what stands in each
    slots, k = [], 0
    for b in range(nb):
        here = nc - (2 if b == 0 else 0) - (2 if b == nb - 1 else 0)
        cols = list(range(nc)) if b % 2 == 0 else list(range(nc - 1, -1, -1))
        y0, y1 = top(b), top(b) + bh
        c = 0
        if b == 0:
            pair = sorted(cols[0:2])
            slots.append(("double", b, [col(pair[0]), y0, col(pair[1]) + cw, y1]))
            c = 2
        for u in units[k:k + here]:
            x0 = col(cols[c])
            if u == 1:
                slots.append(("tall", b, [x0, y0, x0 + cw, y1]))
            else:
                slots.append(("pair", b, [x0, y0, x0 + cw, y0 + ch], [x0, y0 + ch + GAP, x0 + cw, y1]))
            c += 1
        k += here
        if b == nb - 1:
            pair = sorted(cols[c:c + 2])
            slots.append(("double", b, [col(pair[0]), y0, col(pair[1]) + cw, y1]))
    cell = (cw, ch)

    # a pair's order, top first or bottom first: the orders whose steps never go the way the step before went, and
    # least often the way the step two before went
    options = [[[s[2]]] if s[0] != "pair" else [[s[2], s[3]], [s[3], s[2]]] for s in slots]
    best = {(None, None, None): (0, [])}
    for opts in options:
        nxt = {}
        for (last, s1, s2), (cost, path) in best.items():
            for o, boxes in enumerate(opts):
                c, pv, a1, a2 = cost, last, s1, s2
                for bx in boxes:
                    if pv is not None:
                        st = step_of(middle(pv), middle(bx), cell)
                        c += 100 * (st == a1) + 3 * (st == a2)
                        a1, a2 = st, a1
                    pv = bx
                key = (tuple(pv), a1, a2)
                if key not in nxt or c < nxt[key][0]:
                    nxt[key] = (c, path + [o])
        best = nxt
    chosen = min(best.values(), key=lambda v: v[0])[1]
    order = [(bx, s[1]) for s, opts, o in zip(slots, options, chosen) for bx in opts[o]]
    r2 = lambda bx: [round(v, 2) for v in bx]
    return {"tiles": [r2(bx) for bx, _ in order], "band": [b for _, b in order], "cell": [round(cw, 2), round(ch, 2)],
            "course": r2([0, MARGIN, W, MARGIN + hc]), "bands": nb, "cols": nc}


def paths_of(kinds, w, lean):
    """The camera's path into each post (none into day one, where the film opens), from its step on the wall: a reveal
    into a chapter, and otherwise the step's kind (STEP); never the same kind twice in a row (ALT). Its bank and turn
    are the card's `lean` over LEAN of PATHS'."""
    tiles = w["tiles"]
    out, was = [None], None
    k_lean = min(1.0, max(0.0, lean / LEAN))
    for k in range(1, len(kinds)):
        st = step_of(middle(tiles[k - 1]), middle(tiles[k]), w["cell"])
        kind = "reveal" if kinds[k] != "ordinary" else STEP[st]
        if kind == was:
            kind = ALT[kind]
        p = PATHS[kind]
        out.append({"kind": kind, "arc": p["arc"], "pitch": p["pitch"], "bank": round(p["bank"] * k_lean, 4), "yaw": round(p["yaw"] * k_lean, 4)})
        was = kind
    return out


def tags_of(kind, aspect, peak, words):
    """What a beat is, in the words a card's `fits` uses: a print is a photo, portrait or landscape, the peak, and
    wordless on the frame (its words stand on its label, never over the picture)."""
    tags = {"photo", "wordless", "portrait" if aspect < 1 else "landscape"}
    if peak:
        tags.add("peak")
    return tags


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once); between equals the
    one used least so far, then the card's order. The option `avoid` (the previous beat's) is never picked while another
    exists."""
    pool = [o for o in options if o["id"] != avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"]))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


# ------------------------------------------------------------------ a print at its station
def label(fmt, when, title, rest, width):
    """The label under a print at its station, `width` px of the screen wide: its lines as dicts (name, text, x from the
    label's left, baseline from its top, size, face, tracking), and its height. The date, then their line, then their
    next line, on the paper, each at least TYPE_FLOOR on screen, in the card's faces and line heights. A post with no
    line keeps a narrow strip under the photograph for its date alone."""
    T = STATION[fmt]
    pad, most = T["pad"], width - 2 * T["pad"]
    least = least_size()
    # the card's line alignment: flush left from the pad, or centered on the label
    mid = compose.in_use()["photo"]["line"]["align"] == "center"
    x, anchor = (width / 2, "middle") if mid else (pad, None)
    small = max(T["date"], least)
    when = compose.cased(when, "text")
    if not title:
        y = BORDER + compose.cap("text") * small
        return [set_line("text", name="date", text=when, x=x, y=y, size=small, anchor=anchor)], y + compose.descent("text") * small + 0.6 * INSET
    y = 0.8 * pad + compose.cap("text") * small
    out = [set_line("text", name="date", text=when, x=x, y=y, size=small, anchor=anchor)]
    last, was = small, "text"
    for name, text, size, face, gap in (("title", title, T["title"], "display", 0.42), ("rest", rest, max(T["rest"], least), "text", 0.5)):
        if not text:
            continue
        lines, size = fit(text, size, face, most, TITLE_LINES, least)
        y += compose.descent(was) * last + gap * size + compose.cap(face) * size
        for i, ln in enumerate(lines):
            out.append(set_line(face, name=name, text=ln, x=x, y=y + i * leading(face) * size, size=size, anchor=anchor))
        y += (len(lines) - 1) * leading(face) * size
        last, was = size, face
    return out, y + compose.descent(was) * last + pad


def held(fmt):
    """The lines a label's type stays inside at its station, in px of the screen: the safe lines (and the card's
    letterbox bars) brought in by the furthest the camera pushes in through a hold and the operator's hand, so the type
    is inside them at every frame of the hold."""
    W, H = SIZES[fmt]
    safe = compose._design("safe-areas.json")[fmt]
    bars = compose.in_use()["finish"].get("bars", 0.0) * H
    k, hand = 1 - max(PUSH.values()), HAND * H
    return [W / 2 - (W / 2 - safe["left"] - hand) * k, H / 2 - (H / 2 - max(safe["top"], bars) - hand) * k,
            W / 2 + (W / 2 - safe["right"] - hand) * k, H / 2 + (H / 2 - max(safe["bottom"], bars) - hand) * k]


def station(fmt, aspect, when, title, rest, above=False):
    """A print laid out at its station, in px of the screen: the card (paper), its photograph at its own proportions
    (inside ASPECT) under a BORDER of paper, and its label's lines, as large as STATION's box holds with the type inside
    the held lines, centered in it. `above` sets the label over the photograph instead of under it."""
    T = STATION[fmt]
    pad = T["pad"]
    hx0, hy0, hx1, hy1 = held(fmt)
    x0, y0, x1, y1 = T["box"]
    x0, x1 = max(x0, hx0 - pad), min(x1, hx1 + pad)
    y0, y1 = (max(y0, hy0 - 0.8 * pad), y1) if above else (y0, min(y1, hy1 + (0.6 * INSET if not title else pad)))
    bw, bh = x1 - x0, y1 - y0
    a = min(ASPECT[1], max(ASPECT[0], aspect))
    pw = bw - 2 * BORDER
    # the label is at least as wide as its longest word set at the least size, so no word stands past its pad
    least = least_size()
    need = 2 * pad + max([compose.width(w, least, face) for text, face in ((title, "display"), (rest, "text")) for w in (text or "").split()] or [0])
    for _ in range(30):
        cw = min(bw, max(pw + 2 * BORDER, T["wide"] * bw, need))
        lines, lh = label(fmt, when, title, rest, cw)
        ph = min(pw / a, bh - BORDER - lh)
        if ph * a >= pw - 0.5:
            break
        pw = ph * a
    pw = ph * a
    ch = BORDER + ph + lh
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    card = [cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2]
    top = card[1] + (lh if above else BORDER)
    photo = [cx - pw / 2, top, cx + pw / 2, top + ph]
    for ln in lines:
        ln["x"] += card[0]
        ln["y"] += card[1] if above else photo[3]
    return {"card": card, "photo": photo, "lines": lines}


def inner(tile):
    """A tile's photograph: the tile inside its paper border."""
    x0, y0, x1, y1 = tile
    b = TILE_BORDER * min(x1 - x0, y1 - y0)
    return [round(x0 + b, 2), round(y0 + b, 2), round(x1 - b, 2), round(y1 - b, 2)]


def framed(lay, tile, aspect, lift, W, H, floor):
    """The camera's station for a print laid out as `lay` that lifts out of `tile`: the wall point at the middle of the
    picture and the wall px the picture is tall at the print's depth. The photograph is CARD_K times its size in its tile
    (the frame at most FRAME_MOST of the wall, and no taller than the wall below the course, whose bottom is `floor`,
    while the print stays at least its tile's size) and stands over its tile, the frame kept EDGE inside the wall and
    below the course where it fits there."""
    ix0, iy0, ix1, iy1 = inner(tile)
    iw, ih = ix1 - ix0, iy1 - iy0
    a = min(ASPECT[1], max(ASPECT[0], aspect))
    fit_h = iw / a if a > iw / ih else ih
    px0, py0, px1, py1 = lay["photo"]
    reach = 2 * lift * math.tan(math.radians(HOLD_FOV) / 2)
    least = fit_h * H / (py1 - py0)
    h = min(FRAME_MOST * H, CARD_K * least, max(least, (H - floor) / (1 + 2 * EDGE) - reach))
    c = [(ix0 + ix1) / 2 - ((px0 + px1) / 2 - W / 2) * h / H, (iy0 + iy1) / 2 - ((py0 + py1) / 2 - H / 2) * h / H]
    # the frame on the wall itself, behind the print standing `lift` off it
    hh = (h + reach) * (1 + 2 * EDGE) / 2
    hw = hh * W / H
    keep = lambda v, half, size, top=0: size / 2 if 2 * half >= size else min(size - half, max(top + half, v))
    return [round(keep(c[0], hw, W), 2), round(keep(c[1], hh, H, floor), 2)], round(h, 2)


# ------------------------------------------------------------------ time
def carried(rows, words):
    """What each photograph carries, as a multiple of its kind's pace: its words, its detail against the set's (a wide
    or busy scene has more edges), and its change from the photograph before (a repeat of the same view changes least)."""
    def cells(r, key):
        return [v for row in r["look"][key] for v in row] if r.get("look") else None
    light = [cells(r, "light") for r in rows]
    busy = [statistics.fmean(c) if (c := cells(r, "busy")) else None for r in rows]
    change = [None] + [statistics.fmean(abs(a - b) for a, b in zip(light[k], light[k - 1])) if light[k] and light[k - 1] else None
                       for k in range(1, len(rows))]

    def ratio(x, of):
        known = [v for v in of if v is not None]
        mid = statistics.median(known) if known else 0
        return min(2.0, max(0.5, x / mid)) if x is not None and mid > 0 else 1.0
    return [(1 + CARRY * words[k]) * math.sqrt(ratio(busy[k], busy) * ratio(None if change[k] is None else change[k] + SAME,
                                                                             [None if c is None else c + SAME for c in change]))
            for k in range(len(rows))]


def plain(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def spoken(rows, said):
    """The rows with a line that only repeats their words for the span (`said`, which the closer sets) given way to its
    next line."""
    if not plain(said):
        return rows
    return [dict(r, line=r.get("next") or "", next="") if plain(r.get("line")) == plain(said) else r for r in rows]


def travels(rows, kinds):
    """The camera's move into each post, in beats, from the step it crosses on the reel's wall (TRAVEL), longer into a
    chapter; none into day one."""
    w = wall(rows, "reel", *SIZES["reel"])
    cw, ch = w["cell"]
    mids = [middle(t) for t in w["tiles"]]
    out = [0.0]
    for k in range(1, len(rows)):
        d = math.hypot((mids[k][0] - mids[k - 1][0]) / cw, (mids[k][1] - mids[k - 1][1]) / ch)
        out.append(round(min(TRAVEL[3], max(TRAVEL[2], TRAVEL[0] + TRAVEL[1] * d)) + (CHAPTER_MORE if kinds[k] != "ordinary" else 0.0), 3))
    return out


def timing(rows, bpm, opening=0.0, floors=None):
    """The rows' kinds, words and moves, and per hold (each card's, then the closer's held picture after the stop) its
    least, its pace and its most, in beats of `bpm`. A card's least is SEEN and as long as its words take to read once
    they have landed: their line, and their next line from its entering, plus the move out. `opening` is the beats the
    film holds the whole wall before the dive; `floors` the least move into each print, the window of the cut that
    plays over it (choose)."""
    n = len(rows)
    kinds = ["hook"] + ["milestone" if r["milestone"] else "ordinary" for r in rows[1:-1]] + ["latest"]
    titles = [(r.get("line") or "").strip() for r in rows]
    rests = [(r.get("next") or "").strip() if kinds[k] != "ordinary" and titles[k] else "" for k, r in enumerate(rows)]
    words = [len(t.split()) for t in titles]
    nexts = [len(t.split()) for t in rests]
    travel = [max(v, (floors or [0.0] * n)[k]) if k else v for k, v in enumerate(travels(rows, kinds))]
    weight = carried(rows, [a + b for a, b in zip(words, nexts)])
    least, pace, most = [], [], []
    for k in range(n):
        kind = "ordinary" if kinds[k] == "ordinary" else "chapter"
        go = travel[k + 1] if k < n - 1 else 0.0
        if k == 0:
            # the hook holds from the first frame: the dive, its line landing, both its lines read, and the move out
            need = dive_of(bpm) + HOOK_LINE + max(reading(words[0], bpm), NEXT + reading(nexts[0], bpm) if nexts[0] else 0.0) + EXIT + go
        else:
            land = LETTERS if kind == "chapter" else LAND
            need = go + EXIT + max(HELD, land + reading(words[k], bpm), land + NEXT + reading(nexts[k], bpm) if nexts[k] else 0.0)
        least.append(max(SEEN[kind], need))
        pace.append(PACE["hook" if k == 0 else kind] * weight[k])
        most.append(max(least[-1], MOST[kind]))
    # the peak, the last milestone (the latest when there is none), holds on screen longest
    peak = max((k for k in range(1, n - 1) if kinds[k] == "milestone"), default=n - 1)
    return {"kinds": kinds, "titles": titles, "rests": rests, "travel": travel, "peak": peak, "bpm": bpm, "opening": opening,
            "outs": [travel[k + 1] for k in range(n - 1)] + [0.0, 0.0],
            "least": least + [HOLD[0] * bpm / 60], "pace": pace + [HOLD[1] * bpm / 60], "most": most + [HOLD[2] * bpm / 60]}


def peaked(d, t):
    """The holds `d` with the peak's raised until it is on screen (its hold less the move out of it) PEAK_MORE longer
    than any other card's."""
    shown = [x - o for x, o in zip(d, t["outs"])]
    p = t["peak"]
    top = max((v for k, v in enumerate(shown[:-1]) if k != p), default=0.0)
    return [max(x, top + PEAK_MORE + t["outs"][p]) if k == p else x for k, x in enumerate(d)]


def dive_of(bpm):
    """The dive onto day one, in beats."""
    return HOOK_DIVE * bpm / 60


def seconds_of(beats, bpm):
    return beats * 60 / bpm


def to_stop(bpm):
    """From the start of the pull back to the stop, where picture and music stop, in beats: the pull back, the wall's
    read and the closer shape."""
    return CLOSER_MOVE + WALL_READ + min(CLOSER_HOLD, CLOSER_MOST * bpm / 60)


def length_of(t, d):
    """The film's length in seconds with the holds `d`: the opening, every hold, and the closer."""
    return seconds_of(t["opening"] + sum(d) + to_stop(t["bpm"]), t["bpm"])


def least_of(t):
    """The film's length in seconds with every hold at its least."""
    return length_of(t, peaked(t["least"], t))


def told(rows, said="", bpm=96.0, opening=0.0, floors=None):
    """The rows the film tells, and the posts whose line it leaves off: a line that only repeats their span gives way
    (`spoken`), and while the film with every hold at its least runs past LONGEST, an ordinary post's line is left off
    (its print passes over its date alone), first where the posts on both sides keep theirs, then the longest line,
    then the earliest. Day one, the milestones and the latest keep every word."""
    rows, left = spoken(rows, said), []
    has = lambda r: bool((r.get("line") or "").strip())
    while least_of(timing(rows, bpm, opening, floors)) > LONGEST:
        can = [k for k in range(1, len(rows) - 1) if not rows[k]["milestone"] and has(rows[k])]
        if not can:
            break
        k = max(can, key=lambda k: (has(rows[k - 1]) and has(rows[k + 1]), len(rows[k]["line"].split()), -k))
        rows = rows[:k] + [dict(rows[k], line="", next="")] + rows[k + 1:]
        left.append(rows[k]["id"])
    return rows, left


def lengths(rows, said="", bpm=96.0, opening=0.0, floors=None):
    """The shortest and the longest reel these rows make well at `bpm`, in seconds to the tenth: every hold at its
    least, and every hold at its most but never past LONGEST."""
    t = timing(told(rows, said, bpm, opening, floors)[0], bpm, opening, floors)
    lo, hi = least_of(t), min(LONGEST, length_of(t, peaked(t["most"], t)))
    return math.ceil(lo * 10) / 10, math.floor(hi * 10) / 10


def holds(t, seconds=None):
    """Every hold in beats: each its pace, all scaled by one factor so the film runs `seconds` (with none, its own pace
    and at most LONGEST), each kept between its least and its most, and the peak held longest."""
    def at(s):
        return peaked([min(hi, max(lo, s * p)) for lo, p, hi in zip(t["least"], t["pace"], t["most"])], t)

    def length(s):
        return length_of(t, at(s))
    goal = seconds if seconds else min(length(1.0), LONGEST)
    lo, hi = 0.0, 1.0
    while length(hi) < goal and hi < 1e4:
        hi *= 2
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if length(mid) < goal else (lo, mid)
    return at(hi)


def cut_of(name):
    """A cut's window in beats and whether the camera jumps at it, as its file in motion/system/moves/cut says."""
    if not name:
        return {"beats": 0.0, "jump": False}
    src = (compose.KIT / "motion" / "system" / "moves" / "cut" / f"{name}.tsx").read_text()
    m = re.search(r"beats:\s*([\d.]+),\s*jump:\s*(true|false)", src)
    return {"beats": float(m.group(1)), "jump": m.group(2) == "true"}


def opening_words(rows, said):
    """The words the opening may set: their words for the span, else the years (or months) the posts run between."""
    if said:
        return said
    a, b = date.fromisoformat(rows[0]["date"]), date.fromisoformat(rows[-1]["date"])
    return f"{a.year} – {b.year}" if a.year != b.year else f"{MONTHS[a.month - 1]} – {MONTHS[b.month - 1]} {b.year}"


def span_text(rows, said):
    """The span as the closer sets it: their own words for it, else their first and latest dates."""
    return said or f"{short(rows[0]['date'])} – {short(rows[-1]['date'])}"


def choose(rows, c, said):
    """The card's moves and cuts for this film, each chosen from the beat's content within the card's allowlists (pick):
    the opening as a title (holding the whole wall OPEN_WORD a word when its move sets words), each print as a photo
    (portrait or landscape, the peak), and the cuts into the whole wall and the closer; the whole wall and the closer take
    no move, so the dates on the course stand where the board checked them. A cut that dips the frame while the camera
    travels plays only into a milestone or the latest; an ordinary print is reached by the camera alone. A print whose only move is the previous
    print's takes none (the print and the camera alone), so no move plays on two beats in a row. Day one comes out of the opening's dive
    with no cut. Returns {"opening", "open", "prints" [(move, cut)], "wall" cut, "closer" cut, "floors", "peak"}: a print's
    floor is its cut's window, so the camera's move into it is never shorter than the cut that plays over it."""
    used_m, used_c = {}, {}
    words = opening_words(rows, said)
    om = pick(c["moves"], {"title", "words"}, "title", used_m, None)
    sets_words = "words" in next(m["fits"] for m in c["moves"] if m["id"] == om)
    on_print = [m for m in c["moves"] if m["id"] not in NOT_ON_A_PRINT]
    # a type mask sets the peak's line across a frame of the ground with the photograph inside its letters: when the
    # card has one it is the peak's move, and it plays nowhere else
    mask = "type-mask-reveal" if any(m["id"] == "type-mask-reveal" for m in c["moves"]) else None
    kinds = ["hook"] + ["milestone" if r["milestone"] else "ordinary" for r in rows[1:-1]] + ["latest"]
    peak = max((k for k in range(1, len(rows) - 1) if kinds[k] == "milestone"), default=len(rows) - 1)
    prints, prev = [], om
    for k, r in enumerate(rows):
        tags = tags_of(kinds[k], r["aspect"], k == peak, 0)
        pool = [m for m in on_print if kinds[k] != "ordinary" or m["id"] not in OVER_THE_FRAME]
        if k == peak and mask and (r.get("line") or "").strip():
            mv = mask
        else:
            mv = pick(pool, tags, "photo", used_m, prev) if pool else None
        # with one move left for this print and it the last print's, the print and the camera play alone
        mv = None if mv == prev else mv
        cut = None if k == 0 else pick(c["transitions"], tags, "photo", used_c, None)
        # a cut that dips the whole frame while the camera travels lets a chapter go: it plays into a milestone or the
        # latest, and an ordinary print is reached by the camera's travel alone, so the walk along the wall stays one shot
        if cut and kinds[k] == "ordinary" and not cut_of(cut)["jump"]:
            cut = None
        prints.append((mv, cut))
        prev = mv
    # the closer takes the cut that fits a closer; the pull back to the whole wall takes another, so the two never match
    cc = pick(c["transitions"], {"closer"}, "closer", used_c, None)
    wc = pick([t for t in c["transitions"] if t["id"] != cc] or c["transitions"], {"wall", "landscape"}, "wall", used_c, None)
    return {"opening": OPEN_WORD * len(words.split()) if sets_words else 0.0, "open": (om, words), "prints": prints,
            "wall": wc, "closer": cc, "floors": [cut_of(cut)["beats"] for _, cut in prints], "peak": peak}


def fitting(rows, said, c, bpm):
    """The rows the style `c` tells inside LONGEST at `bpm`, and the ids of the ordinary posts it leaves out: while the
    shortest film runs past LONGEST with every ordinary line left off (told), the ordinary post whose neighbors stand
    nearest in time leaves the film (the story loses least there), the earliest between equals. Day one, the
    milestones and the latest always stay."""
    out = []
    when = lambda r: date.fromisoformat(str(r["date"])[:10]).toordinal()
    while True:
        lo, hi = lengths_for(rows, said, c, bpm)
        can = [k for k in range(1, len(rows) - 1) if not rows[k]["milestone"]]
        if lo <= hi or not can:
            return rows, out
        k = min(can, key=lambda k: (when(rows[k + 1]) - when(rows[k - 1]), k))
        out.append(rows[k]["id"])
        rows = rows[:k] + rows[k + 1:]


def lengths_for(rows, said, c, bpm):
    """The shortest and the longest reel these rows make in the style `c` at `bpm` (lengths, with the card's opening and
    cuts)."""
    ch = choose(rows, c, said)
    return lengths(rows, said, bpm, ch["opening"], ch["floors"])


def build(rows, fx, who, fmt="reel", sizes=None, style=None, colors=None, bpm=None):
    """The drive board for `rows` (framing.py's measure rows: dated, oldest first, each with its photograph and focal
    point), `fx` (storyboard.facts) and `who` ({"name", "handle"}), in format `fmt`, made in the style card `style`
    with the colors its palette rule made (`colors`, compose.colors_of) at `bpm`."""
    c = style
    W, H = (sizes or SIZES)[fmt]
    pulse = FPS * 60 / bpm
    said = (fx.get("said") or "").strip()
    ch = choose(rows, c, said)
    opening, floors = ch["opening"], ch["floors"]
    rows, unsaid = told(rows, said, bpm, opening, floors)
    n = len(rows)
    tm = timing(rows, bpm, opening, floors)
    kinds, titles, rests, travel = tm["kinds"], tm["titles"], tm["rests"], tm["travel"]
    dur = holds(tm, fx.get("seconds"))
    hook, hold = dur[0], dur[-1]
    w = wall(rows, fmt, W, H)
    tiles = w["tiles"]
    ease = c["ease"]

    # landings: day one's card lands as the camera's dive from the whole wall reaches it, after the opening; every other
    # card lands when the camera reaches it
    dive = dive_of(bpm)
    arrive = [opening + dive]
    t = opening + hook
    for k in range(1, n):
        arrive.append(t)
        t += dur[k]
    C = arrive[-1] + dur[n - 1]  # the camera leaves the latest for the whole wall
    K = C + CLOSER_MOVE + WALL_READ  # the closer shape begins
    S = C + to_stop(bpm)         # picture and music stop together
    E = S + hold
    leave = [arrive[k + 1] - travel[k + 1] for k in range(n - 1)] + [C]
    # each print's cut falls in the middle of the camera's move into it; a cut that jumps puts the camera there at once
    # day one's beat starts as the dive does: after the opening's words when the opening sets them, else as it lands
    cut_at = [opening if opening > 0 else arrive[0]] + [leave[k - 1] + travel[k] / 2 for k in range(1, n)]

    paths = paths_of(kinds, w, ease.get("lean", 0.0))
    cards = []
    # the prints that carry their words take turns setting them under the photograph and over it, day one under, so
    # the words move about the frame from print to print instead of standing in one place
    worded = [k for k in range(len(rows)) if titles[k]]
    for k, r in enumerate(rows):
        aspect, focal = r["aspect"], r.get("focal") or [0.5, 0.5]
        chapter = kinds[k] != "ordinary"
        size = "chapter" if chapter else "ordinary"
        mv, cut = ch["prints"][k]
        # a type mask sets the peak's line across the whole frame, so its label sets the date with their next line as
        # its line, and the peak's line is set once
        mask = compose.cased(titles[k], "display") if mv == "type-mask-reveal" and titles[k] else ""
        title, rest = (rests[k], "") if mask else (titles[k], rests[k])
        lay = station(fmt, aspect, short(r["date"]), title, rest, above=bool(title) and k in worded and worded.index(k) % 2 == 1)
        cc, h = framed(lay, tiles[k], aspect, LIFT[size], W, H, w["course"][3])

        def on_wall(x, y):
            return [round(cc[0] + (x - W / 2) * h / H, 2), round(cc[1] + (y - H / 2) * h / H, 2)]

        def line(ln):
            x, y = on_wall(ln["x"], ln["y"])
            return {"text": ln["text"], "x": x, "y": y, "size": round(ln["size"] * h / H, 3), "face": ln["face"], "tracking": ln["tracking"], "color": "ink",
                    **({"anchor": ln["anchor"]} if ln.get("anchor") else {})}

        photo = on_wall(*lay["photo"][:2]) + on_wall(*lay["photo"][2:])
        tile_photo = inner(tiles[k])
        # their line enters as the print starts toward the lens (day one's as the dive onto it starts) and has landed
        # on the frame the camera arrives on, so no print is ever framed with a blank label
        approach = arrive[k] - (dive if k == 0 else RISE * travel[k])
        title_at = max(0.0, approach, arrive[k] - (HOOK_LINE if k == 0 else LETTERS if chapter else LAND))
        land = arrive[k]
        # how the print tips as it lifts out follows the camera's step into it: a step up or down tips it about its
        # bottom edge, a step along a band turns it about its middle, any other lifts it straight
        st = step_of(middle(tiles[k - 1]), middle(tiles[k]), w["cell"]) if k else (0, 0)
        entry = 1 if st[0] == 0 and st[1] != 0 else 2 if st[1] == 0 and st[0] != 0 else 0
        cards.append({
            "id": r["id"], "kind": kinds[k], "file": r["photo"], "tile_file": r.get("tile") or r["photo"], "aspect": round(aspect, 5),
            "date": r["date"], "rect": on_wall(*lay["card"][:2]) + on_wall(*lay["card"][2:]), "photo": photo,
            "tile": tiles[k], "tile_photo": tile_photo,
            "uv0": window(aspect, photo[2] - photo[0], photo[3] - photo[1], focal),
            "uv": window(aspect, tile_photo[2] - tile_photo[0], tile_photo[3] - tile_photo[1], focal),
            "focal": [round(v, 4) for v in focal], "lift": LIFT[size], "push": PUSH[size], "path": paths[k],
            "move": mv, "transition": cut, "cut": round(cut_at[k], 4), "jump": cut_of(cut)["jump"], "mask": mask,
            "arrive": arrive[k], "leave": leave[k], "travel": travel[k], "entry": entry,
            "dateLine": line(next(ln for ln in lay["lines"] if ln["name"] == "date")),
            "title": [line(ln) for ln in lay["lines"] if ln["name"] == "title"], "title_at": title_at, "land": land,
            "rest": [line(ln) for ln in lay["lines"] if ln["name"] == "rest"], "rest_at": land + NEXT,
            "station": {"c": cc, "h": h, "fov": HOLD_FOV},
            "box": [round(v, 2) for v in lay["photo"]], "type": type_box(lay["lines"]),
        })

    # the course, once the camera has settled on the whole wall: their first and latest dates at its two ends, and under
    # them the ask when they asked for one
    cs = COURSE[fmt]
    x0, x1 = cs["x"]
    course = w["course"]
    lo, hi = max(course[1], cs["words"][0]), min(course[3], cs["words"][1])
    call = (fx.get("call_to_action") or "").strip()
    least = least_size()
    ds = max(cs["date"], least)
    csz = fit(call, cs["call"], "text", x1 - x0, 1, least)[1] if call else 0.0
    cap_t, desc_t = compose.cap("text"), compose.descent("text")
    dy = cap_t * ds
    bottom = dy + desc_t * ds
    cy = bottom + 0.9 * csz + cap_t * csz if call else None
    bottom = cy + desc_t * csz if call else bottom
    off = lo + (hi - lo - bottom) / 2
    settled = C + CLOSER_MOVE
    # their own words for the span stand over their two dates; without them the closer's span is the two dates, said once
    on_course = [] if not said else [
        set_line("text", name="first", text=compose.cased(short(rows[0]["date"]), "text"), x=x0, y=round(off + dy, 2), size=ds, color="line", at=settled - 0.25),
        set_line("text", name="latest", text=compose.cased(short(rows[-1]["date"]), "text"), x=x1, y=round(off + dy, 2), size=ds, color="line", anchor="end", at=settled - 0.1),
    ]
    if call:
        on_course.append(set_line("text", name="call", text=compose.cased(call, "text"), x=x1, y=round(off + cy, 2), size=round(csz, 2), color="words",
                                  anchor="end", at=settled + 0.5))
    # the closer shape, the card's: the span in their own words (or their dates) with the ask, else their handle
    span = span_text(rows, said)
    handle = who.get("handle", "")
    handle = f"@{handle.lstrip('@')}" if handle else ""
    shape = c["closer"]
    look = closer_look(shape, span, call, handle)

    # the timeline the card's moves and cuts play on: the opening, each print, the whole wall and the closer
    om, owords = ch["open"]
    wc = ch["wall"]
    line_beats = [{"id": "open", "form": "title", "at": 0.0, "end": cut_at[0], "move": om, "transition": None, "words": owords, "label": owords, "peak": False}]
    for k, cd in enumerate(cards):
        end = cards[k + 1]["cut"] if k + 1 < n else C + CLOSER_MOVE / 2
        held = {"box": cd["box"], **({"type": cd["type"]} if cd["type"] else {}), "held": [round(cd["arrive"], 4), round(cd["leave"], 4)]}
        # a type mask sets the peak's own line across a frame of the ground, the photograph inside its letters, while
        # the camera reaches the print; then the frame cuts to the print standing whole with its date and their next
        # line already set, so the peak's line is on screen once
        if cd["mask"]:
            mask_end = min(cd["arrive"] + MASK_HOLD, (cd["arrive"] + cd["leave"]) / 2)
            line_beats.append({"id": cd["id"], "form": "title", "at": cd["cut"], "end": mask_end, "move": cd["move"], "transition": cd["transition"],
                               "words": cd["mask"], "label": "", "peak": k == tm["peak"]})
            line_beats.append({"id": f"{cd['id']}-print", "form": "photo", "at": mask_end, "end": end, "move": None, "transition": None,
                               "words": "", "label": "", "peak": k == tm["peak"], **held})
            continue
        # the print's label sets its date and line, so a move on it is handed no words
        line_beats.append({"id": cd["id"], "form": "photo", "at": cd["cut"], "end": end, "move": cd["move"], "transition": cd["transition"],
                           "words": "", "label": "", "peak": k == tm["peak"], **held})
    # the cut into the closer opens as the closer shape starts, so what it reveals is the shape and never the wall again
    into = K + cut_of(ch["closer"])["beats"] / 2
    line_beats.append({"id": "wall", "form": "wall", "at": C + CLOSER_MOVE / 2, "end": into, "move": None, "transition": wc, "words": "", "label": "", "peak": False})
    line_beats.append({"id": "closer", "form": "closer", "at": into, "end": E, "move": None, "transition": ch["closer"], "words": "", "label": "", "peak": False})
    timeline = {"beats": [{**b, "at": round(b["at"], 4), "end": round(b["end"], 4)} for b in line_beats],
                "cuts": [round(b["at"], 4) for b in line_beats]}

    film = {
        "W": W, "H": H, "pulse": pulse, "colors": film_colors(colors, c["palette"]["rule"]), "letters": LETTERS, "exit": EXIT,
        # enter: a letter or a print landing; move: the camera's travel; drop: a print going home into its tile
        "ease": {"enter": ease["enter"], "move": ease["move"], "drop": ease["exit"]},
        "cards": cards, "peak": tm["peak"], "course": course, "unsaid": unsaid, "opening": opening,
        "timeline": timeline, "look": look, "shape": shape,
        "closer": {"at": C, "move": CLOSER_MOVE, "shape": K, "still": S, "end": E, "span": span, "jump": cut_of(wc)["jump"], "cut": C + CLOSER_MOVE / 2,
                   "frame": {"c": [W / 2, H / 2], "h": H, "fov": CLOSER_FOV}, "lines": on_course},
    }

    # the beats: each starts when the camera leaves the one before (the hook at the first frame)
    bounds = [0.0] + [leave[k] for k in range(n)] + [E]
    ids = ["hook"] + [r["id"] for r in rows[1:]] + ["closer"]
    beats, f0 = [], 0
    for i, bid in enumerate(ids):
        f1 = round(bounds[i + 1] * pulse)
        beats.append({"id": bid, "bars": round((bounds[i + 1] - bounds[i]) / 4, 3), "frames": f1 - f0, "pulse": pulse, "layers": []})
        f0 = f1

    board = {"id": c["id"], "style": c["id"], "name": who.get("name", ""), "handle": who.get("handle", ""), "bpm": bpm,
             "format": {"name": fmt, "width": W, "height": H, "fps": FPS}, "beats": beats, "film": film,
             "sound": sound(film, kinds), "clips": clips(rows, film, kinds, tm["peak"], beats), "scenes": scenes(rows, film, kinds)}
    dense = next((cd for cd in cards if cd["kind"] == "milestone"), cards[-1])
    board["stills"] = {
        # day one's photograph with their first line landed and their next line risen
        "hook": round((cards[0]["rest_at"] + 0.6) * pulse),
        "ordinary": round((cards[min(2, n - 1)]["arrive"] + 0.4) * pulse),
        # the first milestone with its next line risen
        "dense": round((dense["rest_at"] + 0.6) * pulse),
        # the whole wall with the dates on its course, before the cut into the closer shape begins
        "closer": round((K - 0.4) * pulse),
        # the closer shape, settled
        "end": round((S - 0.2) * pulse),
    }
    return board


def type_box(lines):
    """Where a print's label lines stand at its station, [x0, y0, x1, y1] px of the screen, from their baselines, sizes
    and anchors; none when it has no lines."""
    if not lines:
        return None
    xs, ys = [], []
    for ln in lines:
        w = compose.width(ln["text"], ln["size"], ln["face"])
        x0 = ln["x"] - (w if ln.get("anchor") == "end" else w / 2 if ln.get("anchor") == "middle" else 0)
        xs += [x0, x0 + w]
        ys += [ln["y"] - compose.cap(ln["face"]) * ln["size"], ln["y"] + compose.descent(ln["face"]) * ln["size"]]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def closer_look(shape, span, call, handle):
    """The board's own words as the card's closer shape sets them: a title card sets the span as its title with the ask
    under it, every other shape sets the span as its closing line; the handle stands under either."""
    if shape == "title-card":
        return {"title": span, "signoff": call, "handle": handle}
    return {"title": "", "signoff": span, "handle": handle if not call else call}


def sound(film, kinds):
    """The board's sound cues: one where each beat lands (day one's photograph, each card after it, a run speeding up
    landing lighter on every other card, a milestone and the latest landing harder with a bright ring), their first line
    landing on day one, the build as the camera pulls back to the whole wall, the impact of the closer shape landing,
    and the stop. Words rise and the camera moves without a sound of their own."""
    cards, cl = film["cards"], film["closer"]
    h = cards[0]
    cues = [{"kind": "hit", "at": h["arrive"], "weight": 0.7, "bright": 0.2, "beat": "hook", "what": "day one's photograph lands"}]
    if h["title"]:
        cues.append({"kind": "hit", "at": h["land"], "weight": 1.0, "bright": 0.6, "beat": "hook", "what": "their first line lands on day one"})
    run = 0
    for k in range(1, len(cards)):
        c, kind = cards[k], kinds[k]
        run = run + 1 if kind == "ordinary" and kinds[k - 1] == "ordinary" else 0
        if kind == "ordinary":
            cues.append({"kind": "hit", "at": c["arrive"], "weight": 0.45 if run % 2 == 0 else 0.35, "bright": 0.12 if run % 2 == 0 else 0.0,
                         "beat": c["id"], "what": f"{c['id']} lands" + (" with their line under it" if c["title"] else "")})
        else:
            cues.append({"kind": "hit", "at": c["arrive"], "weight": 0.9 if kind == "milestone" else 1.0, "bright": 0.55 if kind == "milestone" else 0.4,
                         "beat": c["id"], "what": f"the {kind} lands" + (" and their line rises under it" if c["title"] else "")})
    C, text = cl["at"], cl["span"]
    cues += [
        {"kind": "riser", "at": C, "beats": cl["shape"] - C - 0.1, "beat": "closer",
         "what": "the camera pulls back to the whole wall and the dates land on its course"},
        {"kind": "impact", "at": cl["shape"] + 0.25, "beat": "closer", "what": f"the closer lands on \"{text}\""},
        {"kind": "stop", "at": cl["still"], "beat": "closer", "what": "picture and music stop together; the closer holds silent"},
    ]
    return sorted(cues, key=lambda c: c["at"])


# ------------------------------------------------------------------ clips and scenes
def measured(r):
    """What a photograph measures, in the words a cinematographer would use: its key (bright or dark), where its light
    comes from, its contrast, where its detail gathers and how far it spreads, its shape and its focal point."""
    light, busy = r["look"]["light"], r["look"]["busy"]
    rows_, cols = len(light), len(light[0])
    mean = lambda cells: statistics.fmean(cells) if cells else 0.0
    every = [v for row in light for v in row]
    left, right = mean([v for row in light for v in row[:cols // 2]]), mean([v for row in light for v in row[cols // 2:]])
    above, below = mean([v for row in light[:rows_ // 2] for v in row]), mean([v for row in light[rows_ // 2:] for v in row])
    dx, dy = right - left, below - above
    side = "from the right" if dx > 0.04 else "from the left" if dx < -0.04 else ""
    high = "from below" if dy > 0.06 else "from above" if dy < -0.06 else ""
    edges = [(v, i, j) for i, row in enumerate(busy) for j, v in enumerate(row)]
    total = sum(v for v, _, _ in edges) or 1.0
    cy = sum(v * (i + 0.5) for v, i, _ in edges) / total / rows_
    cx = sum(v * (j + 0.5) for v, _, j in edges) / total / cols
    spread = math.sqrt(sum(v * ((i + 0.5) / rows_ - cy) ** 2 + v * ((j + 0.5) / cols - cx) ** 2 for v, i, j in edges) / total)
    where = lambda x, y: ("upper " if y < 0.4 else "lower " if y > 0.6 else "") + ("left" if x < 0.4 else "right" if x > 0.6 else "middle" if 0.4 <= y <= 0.6 else "middle")
    a = r["aspect"]
    return {"key": mean(every), "contrast": statistics.pstdev(every), "from": " and ".join(x for x in (high, side) if x) or "evenly",
            "detail": where(cx, cy), "spread": spread, "busy": mean([v for v, _, _ in edges]),
            "shape": "tall" if a < 0.9 else "wide" if a > 1.15 else "square", "focal": where(*(r.get("focal") or [0.5, 0.5]))}


def lenses(m):
    """The lenses a shot of this photograph could take, best first: wide where the detail spreads, long where it gathers."""
    wide = ["a 24mm lens at the photograph's own height, everything sharp", "a 28mm lens a step back, deep focus",
            "a 35mm lens at eye level, deep focus"]
    middle = ["a 50mm lens at the photograph's distance, focus on the " + m["focal"], "a 40mm lens, focus held on the " + m["focal"]]
    long = ["an 85mm lens close on the " + m["detail"] + ", shallow focus", "a 100mm macro lens on the " + m["detail"] + ", the focus falling off fast",
            "a 135mm lens compressing the " + m["detail"]]
    if m["spread"] > 0.27:
        return wide + middle + long
    if m["spread"] < 0.22:
        return long + middle + wide
    return middle + wide + long


def lights(m):
    """The lights a shot could take, best first, from the light the photograph already has."""
    key = "bright, high key" if m["key"] > 0.62 else "dark, low key" if m["key"] < 0.38 else "middle key"
    hard = "hard, deep shadows" if m["contrast"] > 0.2 else "soft, open shadows" if m["contrast"] < 0.12 else "a gentle falloff"
    src = f"falling {m['from']}" if m["from"] != "evenly" else "even across the frame"
    return [f"the photograph's own light, {src}, {key}, {hard}", f"its own light {src}, a slow drift of it across the {m['detail']}",
            f"its {key} light held, a cloud's shadow passing once over the {m['detail']}", f"its light {src}, the shadows breathing a little deeper and back",
            f"its {hard.split(',')[0]} light, a thin bright edge travelling along the {m['focal']}", f"its light {src}, a slow flicker of warmth on the {m['detail']}"]


def clip_moves(m):
    """The camera moves a shot could take, best first: in toward the focal point on a gathered photograph, across its
    detail on a spread one, up or down a tall one."""
    toward = f"a slow push in toward the {m['focal']}, about a tenth of the frame"
    across = f"a slow lateral slide across the {m['detail']}, left to right"
    tall = f"a slow tilt up the {m['shape']} frame to the {m['focal']}"
    back = f"a slow pull back from the {m['focal']}, about a tenth of the frame"
    arc = f"a slow arc a few degrees around the {m['focal']}"
    held = "a locked frame, only the light and the air moving"
    if m["shape"] == "tall":
        return [tall, toward, arc, back, across, held]
    if m["spread"] > 0.27:
        return [across, back, arc, toward, held, tall]
    return [toward, arc, back, across, held, tall]


def first_free(options, used):
    """The first option nobody has taken yet (the first, when every one has been)."""
    got = next((o for o in options if o not in used), options[0])
    used.add(got)
    return got


PATH_WORDS = {"crane": "cranes", "glide": "glides", "sweep": "sweeps", "swing": "swings", "reveal": "reveals the wall and comes"}


def clips(rows, film, kinds, peak, beats):
    """The six shots an image-to-video model would make, each a request the agent sends (clips.py list writes them to
    RUN/clips/requests.json): the hook's world (day one, alive), the stills brought to life (the first milestone, the
    peak and the latest), and the texture between chapters (the two busiest ordinary posts, a chapter or more apart).
    Each is written from what its own photograph measures (`measured`): a lens, a light and a move no other shot of the
    six takes, their words for the photograph as its subject, a length that is its beat's, and a seamless loop. Until a
    clip comes back, the print stands in with its own move (`stand_in`), which is never called a clip."""
    cards = film["cards"]
    n = len(rows)
    first = next((k for k in range(1, n - 1) if kinds[k] == "milestone"), None)
    life = list(dict.fromkeys(k for k in (first, peak, n - 1) if k is not None and k > 0))
    busy = {k: measured(rows[k])["busy"] if rows[k].get("look") else 0.0 for k in range(1, n - 1) if kinds[k] == "ordinary"}
    texture = []
    for k in sorted(busy, key=lambda k: -busy[k]):
        if len(texture) < 6 - 1 - len(life) and all(abs(k - j) > 2 for j in texture):
            texture.append(k)
    used = {"lens": set(), "light": set(), "move": set()}
    out = []
    for role, k in sorted([("world", 0)] + [("life", k) for k in life] + [("texture", k) for k in texture], key=lambda x: x[1]):
        r, c = rows[k], cards[k]
        m = measured(r) if r.get("look") else {"key": 0.5, "contrast": 0.15, "from": "evenly", "detail": "middle", "spread": 0.25, "busy": 0.0, "shape": "square", "focal": "middle"}
        seconds = round(beats[k]["frames"] / FPS, 2)
        words = (r.get("line") or r.get("caption") or "").strip()
        about = f"the photograph posted on {short(r['date'])}" + (f" with the words \"{words}\"" if words else "")
        subject = {"world": f"{about}, alive: the first day, as it was",
                   "life": f"{about}, brought to life: the {m['focal']} it is framed on, still where it is",
                   "texture": f"{about}, close on its {m['detail']}, where its detail gathers"}[role]
        lens, light, move = first_free(lenses(m), used["lens"]), first_free(lights(m), used["light"]), first_free(clip_moves(m), used["move"])
        into = "dives from the whole wall" if k == 0 else f"{PATH_WORDS[c['path']['kind']]} in from {cards[k - 1]['id']}"
        stand = (f"the still print: the camera {into} as the print lifts out of its tile and lands, its shadow on the wall "
                 f"under it, then pushes in {round(c['push'] * 100)}% on the {m['focal']} through its {seconds} s")
        out.append({"id": f"clip-{r['id']}", "beat": "hook" if k == 0 else r["id"],
                    "role": {"world": "the hook's world", "life": "a still brought to life", "texture": "texture between chapters"}[role],
                    "seconds": seconds, "image": r["photo"], "lens": lens, "light": light, "move": move, "loop": True,
                    "prompt": f"{subject}. {lens}; {light}; {move}; {seconds} s; nothing new enters the frame, the framing "
                              f"and the colors of the photograph kept, the last frame matching the first so it loops seamlessly",
                    "stand_in": stand})
    return out


def scenes(rows, film, kinds):
    """Per beat: its photograph, the words under it (their line, and their next line after a slash), what the move
    reveals and what it carries across the cut."""
    cards = film["cards"]
    how = {"crane": "the camera cranes along the column to", "glide": "the camera glides along the band to",
           "sweep": "the camera sweeps across the band to", "swing": "the camera swings back across the band to",
           "reveal": "the camera draws back to show the wall so far and comes in on"}

    def said(c):
        return " / ".join(x for x in (c["mask"], " ".join(ln["text"] for ln in c["title"]), " ".join(ln["text"] for ln in c["rest"])) if x)

    def into(c):
        if c["jump"]:
            return f"the {c['transition']} cut puts the camera on"
        return how[c["path"]["kind"]]
    out = [{"beat": "hook", "photo": Path(rows[0]["photo"]).name, "line": said(cards[0]),
            "reveals": "the camera dives from the whole wall of dim tiles onto day one as its print lifts out of its tile and settles"
                       + (", and their first line enters under it letter by letter" if cards[0]["title"] else "") + ": where it started",
            "carries": f"day one drops back into the wall's first tile as the camera travels to {cards[1]['id']}"}]
    for k in range(1, len(rows)):
        c, r = cards[k], rows[k]
        chapter = kinds[k] != "ordinary"
        lands = (f"their line \"{c['mask']}\" fills the frame cut out of the ground with the photograph inside its letters, then the print stands whole" + (f" under \"{' '.join(ln['text'] for ln in c['title'])}\"" if c["title"] else "") if c["mask"] else
                 f"their line \"{' '.join(ln['text'] for ln in c['title'])}\" enters letter by letter under it"
                 + ((", their next line rises, and it holds" + (" longest of all" if k == film.get("peak") else "") if c["rest"] else " and it holds") if chapter else "")) \
            if c["title"] or c["mask"] else "it holds over its date" if chapter else "it passes over its date"
        nxt = "the latest drops into the last tile as the camera pulls back to the whole wall" if k == len(rows) - 1 else \
            "it drops back into its tile as the camera moves on"
        out.append({"beat": r["id"], "photo": Path(r["photo"]).name, "line": said(c),
                    "reveals": f"{into(c)} {c['id']}, whose print lifts out of its tile and settles {('under the ' + c['move'] + ' move') if c['move'] else 'with the camera alone'}: {lands}", "carries": nxt})
    cl = film["closer"]
    out.append({"beat": "closer", "photo": "the whole wall", "line": cl["span"],
                "reveals": "the whole wall: every photograph from day one to the latest, the two ends largest, their first and latest dates on its course"
                           + "".join(f" and \"{ln['text']}\" under them" for ln in cl["lines"] if ln["name"] == "call"),
                "carries": f"the {film['shape']} closer sets \"{cl['span']}\"; picture and music stop together and it holds silent"})
    return out


# ------------------------------------------------------------------ checks
TYPE_FLOOR = 28


def check(board, rows, allowed, safe):
    """The drive board's findings as sentences: type under the floor; type outside the safe lines (and the card's
    letterbox bars) with the camera pushed in to the end of its card's hold and the operator's hand at its furthest; a
    label's line nearer its print's edge than INSET or over its photograph; a station whose frame reaches past the wall,
    or whose print fills it edge to edge; a course line off its course; a number that is not a fact; and a first event
    later than frame 30."""
    film, fmt = board["film"], board["format"]
    W, H = fmt["width"], fmt["height"]
    bars = (board.get("system") or {}).get("finish", {}).get("bars", 0.0) * H
    top, bottom = max(safe["top"], bars), max(safe["bottom"], bars)
    bad = []

    def screen(st, x, y, push=0.0):
        k = H / (st["h"] * (1 - push))
        return (x - st["c"][0]) * k + W / 2, (y - st["c"][1]) * k + H / 2

    def box(ln):
        face = ln["face"]
        w = compose.width(ln["text"], ln["size"], face)
        x0 = ln["x"] - (w if ln.get("anchor") == "end" else w / 2 if ln.get("anchor") == "middle" else 0)
        return [x0, ln["y"] - ln["size"] * compose.cap(face), x0 + w, ln["y"] + compose.descent(face) * ln["size"]]

    def look(where, ln, st, push=0.0):
        x0, y0, x1, _ = box(ln)
        cap = ln["size"] * compose.cap(ln["face"])
        if cap * H / st["h"] < TYPE_FLOOR - 0.05:
            bad.append(f"type: {where} \"{ln['text'][:30]}\" is {cap * H / st['h']:.1f} px cap height on screen (at least {TYPE_FLOOR})")
        hand = HAND * H if push else 0.0
        (sx0, sy0), (sx1, sy1) = screen(st, x0, y0, push), screen(st, x1, ln["y"], push)
        if sx0 - hand < safe["left"] - 2 or sy0 - hand < top - 2 or sx1 + hand > W - safe["right"] + 2 or sy1 + hand > H - bottom + 2:
            bad.append(f"safe: {where} \"{ln['text'][:30]}\" {[round(v) for v in (sx0, sy0, sx1, sy1)]} reaches past the safe lines"
                       + (" or the letterbox bars" if bars else "") + (f" with the camera pushed in {push:.0%} and the hand at {hand:.0f} px" if push else ""))
        for n in re.findall(r"\d+", ln["text"].replace(board["handle"], "") if board["handle"] else ln["text"]):
            if n not in allowed:
                bad.append(f"numbers: {where} shows {n}, which is not a date or a span they would say")

    half = math.tan(math.radians(HOLD_FOV) / 2)
    for c in film["cards"]:
        st, push = c["station"], c["push"]
        lines = [c["dateLine"]] + c["title"] + c["rest"]
        (cx0, cy0), (cx1, cy1) = screen(st, *c["rect"][:2]), screen(st, *c["rect"][2:])
        (px0, py0), (px1, py1) = screen(st, *c["photo"][:2]), screen(st, *c["photo"][2:])
        for ln in lines:
            look(c["id"], ln, st, push)
            (qx0, qy0), (qx1, qy1) = screen(st, *box(ln)[:2]), screen(st, *box(ln)[2:])
            if qx0 < cx0 + INSET - 0.5 or qx1 > cx1 - INSET + 0.5 or qy1 > cy1 - INSET * 0.5:
                bad.append(f"inset: {c['id']} \"{ln['text'][:30]}\" stands within {INSET} px of its print's edge")
            if qy0 < py1 and qy1 > py0 and qx1 > px0 and qx0 < px1:
                bad.append(f"over: {c['id']} \"{ln['text'][:30]}\" stands on its photograph")
        if cx0 <= 0 or cy0 <= 0 or cx1 >= W or cy1 >= H:
            bad.append(f"edge: {c['id']}'s print {[round(v) for v in (cx0, cy0, cx1, cy1)]} fills its station's frame edge to edge: the wall does not show")
        fh = st["h"] + 2 * c["lift"] * half
        fw = fh * W / H
        if st["c"][0] - fw / 2 < -1 or st["c"][0] + fw / 2 > W + 1 or st["c"][1] - fh / 2 < -1 or st["c"][1] + fh / 2 > H + 1:
            bad.append(f"wall: {c['id']}'s station frames past the wall's edge")
    whole = {"c": [W / 2, H / 2], "h": H}
    cl, course = film["closer"], film["course"]
    for ln in cl["lines"]:
        look("closer", ln, whole)
        x0, y0, x1, y1 = box(ln)
        if y0 < course[1] + GAP or y1 > course[3] - GAP:
            bad.append(f"course: the closer's \"{ln['text'][:30]}\" reaches off the course onto the tiles")
    first = round((0.0 if film.get("opening") else film["cards"][0]["arrive"]) * film["pulse"])
    if first > 30:
        bad.append(f"beats: the first event is at frame {first} (at most 30)")
    return bad
