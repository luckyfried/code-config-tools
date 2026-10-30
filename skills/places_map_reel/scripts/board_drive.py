"""drive: one dot travels the year. The film opens wide on the whole route under the film's title, the dot on the first
place's pin, and comes down onto the first place as its photograph opens out of the pin. Every place the dot reaches
opens out of its pin into that place's card, laid out by the style card's photo layout: the photograph in its box on the
card's ground, the place's name as the label over the person's line about it (or, with no line, the name as the line
under its month). When the camera moves on it follows the dot along the next leg, the card folds into a small print on
its own pin, and the next place's card opens out of its pin. The film ends with the map resolving into the style's
closer: a poster (swiss-grid), a title card in the person's own words (cinematic-letterbox), or a book closing on it
(scrapbook), the map showing through the closer's window with every place named on its pin.
The map is a mercator crop of the region the route spans, north up, framed to the route's bounds with a margin, so a
stranger reads the country and its coast; the legs are great circles drawn in that space.
The look is the style card's: the faces, their case and tracking, the colors its palette rule makes from the
photographs (the map's sea, land, coast and route among them), the easing, the finish and the closer. Each beat's move
and the cut into it are chosen from that beat's content within the card's allowlist (look.pick).

build(source, fmt, bpm, style) solves the whole board in px of one format from the source alone (storyboard.py's
source.json: the places in route order, the graded photographs with their focus, line and look (grade.py), the
handle, the person's line for each visit (`moments`, from taste.json), and the taste's title and swatches):
  route      the map (the land in px over the whole frame), each stop's card (where its photograph stands in the frame,
             the words the layout sets, the pin it opens out of and the print it folds into), each leg's great-circle
             path, the hook's title and handle, the closer's window, title, sign-off and the places' names on their
             pins
  beats      one per stop and the closer, in musical beats at BPM (timing()), each with its form, its move, the cut into
             it, its words and label, and where its words stand (`words_at`, a share of the frame's height): each stop
             holds for what its photograph carries (its words, its detail, its change from the stop before) against its
             kind's pace, all scaled by one factor to the asked length as near as the stops make it (taste.json
             `seconds`, else the film's own pace inside LENGTH), never under the time its words take to come up and be
             read, the peak the curation marks holding the most; the closer closer_beats(bpm): the closer resolving,
             about two seconds, then still for a second or for as long as its words still need; a stop the camera
             leaves across a leap over the water adds LEAP for the camera's travel, never to its hold
  sound      the cues music.py mixes, one where each beat lands and the build into the peak, each with what it answers
             on the picture
  clips      the image-to-video shots the film would carry, one per stop, each written as a shot for its use, its
             camera move the beat's own move in camera words
  length     the band of seconds the film is held to (timing())
Every beat carries `reveals` (what its move shows) and `carries` (what crosses the cut into the next beat).
"""
import json
import math
import re
import statistics
from pathlib import Path

import look
import maps
import trip as trip_mod
from palette import contrast as _contrast, hex_rgb, lum as _lum

KIT = Path(__file__).resolve().parent.parent
SAFE = json.loads((KIT / "design" / "safe-areas.json").read_text())
LAND_FILE = KIT / "data" / "land.json"

BPM = 90
FPS = 30
# the film's length in seconds: the shortest and the longest reel the kit makes, the shortest only for a trip whose
# holds at their most reach it (a smaller trip runs as long as its holds reach); the longest leaves the second the film
# opens on the whole route on top of a 40 s run of places
LENGTH = (20, 42)
# a stop's hold in seconds by its kind (the hook, the peak the curation marks, a place with the person's line, a place
# with none): PACE at the film's own pace for a photograph that carries as much as the set's middle one, SEEN the least
# it holds and MOST the most; every hold is also at least as long as its words take to read. The hook paces as a place
# with a line, so the peak, not the hook, holds longest
PACE = {"hook": 2.0, "peak": 3.3, "new": 2.0, "quick": 1.3}
SEEN = {"hook": 2.5, "peak": 2.0, "new": 1.5, "quick": 1.0}
MOST = {"hook": 8.0, "peak": 8.0, "new": 6.5, "quick": 5.0}
# each word on a card holds it this share longer; a mean change of the light grid this small reads as the same view
CARRY, SAME = 0.04, 0.02
# the seconds a line of n words needs on screen: READ[0] + READ[1] * n
READ = (0.3, 0.12)
# beats a stop the camera leaves across a leap over the water adds for the camera's travel, never to its hold
LEAP = 2
# beats before the next stop's arrival that the camera leaves (a leap leaves earlier), and after it that it lands
# (a rise leaves earlier, RISE_GO); the camera lands on the closer later
GO, LEAP_GO, LAND, CLOSER_LAND = 0.45, 2.0, 0.15, 0.25
# beats the photograph takes to fold onto its print at most
FOLD = 0.75
# the film opens on the whole route, every pin set out and the dot on the first one, under the title; at HOOK_DIVE beats
# the title leaves and the camera dives onto the first photograph, settling at HOOK_SETTLE (route/camera.ts) as it
# opens out of its pin
HOOK_DIVE, HOOK_SETTLE = 1.4, 2.6
# beats from a stop's arrival to its words coming up: the photograph has the frame alone first
CUT = {"hook": HOOK_SETTLE - 0.3, "peak": 1.2, "new": 0.8, "quick": 0.5}
# beats from the hook's start that the first place's name and line come up, once the title has left
HOOK_NAME = CUT["hook"] + 0.2
# the share of a card's frame the camera holds as it leaves the card (route/camera.ts HOLD_PUSH): the hold's push in
HOLD_END = 0.955
# seconds the closer takes to resolve out of the map (ROUTE), and the least it holds still after it (STILL), longer
# only while its words still need reading: the closer is set in seconds, so a film the snap slows to half tempo does
# not hold its closer twice as long; RISEN is the beats from the closer's start until its words have risen
ROUTE, STILL, RISEN = 2.0, 1.0, 0.75
# how far each revisit's print is set across its place's first print, as a share of the print
STACK_STEP = 0.045
# the rise between two near stops (the camera leaves RISE_GO beats before the next arrival): it climbs over the map to
# show every near place and the route between them; a lift comes down onto the leg while the dot runs it. A rise never
# stands beside a leap or the closer, which show the map whole themselves, and never follows a rise
RISE_GO = 0.9
# the style card's moves that bring a photograph onto its page, as a stop's arrival (route/card.tsx draws each): dropped
# from above and settling, slapped down flat, popped out from its middle, slid in from the side
ARRIVES = ("polaroid-drop", "tape-slap", "sticker-pop", "paper-slide")
# a print's paper border at rest on the map, as a share of its frame's width (route/card.tsx), and its side on the map
# as a share of the frame's short side: a small print on its own pin
PAPER, PRINT = 0.0484, 0.05
# the region the map is cropped to: the route's span with MARGIN of it on every side, never under LEAST km across
MARGIN, LEAST = 0.2, 400
TILT = 12.0


# ------------------------------------------------------------------ the style
def map_colors(roles):
    """The map's colors from the six roles the card's palette rule made, every one of them a role: on a dark ground the
    sea is the ground and the land the second accent where it stands off it (else the muted ink), its coast in paper;
    on a light ground the sea is the second accent where it differs from the accent and stands off the paper (else the
    muted ink), the land paper, its coast in ink. The route is the accent where it reads on the land, else whichever of
    the ink and the paper reads on it more, on a casing of the color around it; the words over the map ("over") are
    whichever of the ink and the paper reads on both the land and the sea, and the handle under the title ("mark") the
    accent where it reads on both, else the same."""
    bg, paper, ink, accent, accent2, muted = (roles[k] for k in ("bg", "paper", "ink", "accent", "accent2", "muted"))
    lum = lambda h: _lum(hex_rgb(h))
    contrast = lambda a, b: _contrast(hex_rgb(a), hex_rgb(b))
    if lum(bg) < 0.18:
        land = accent2 if accent2 != accent and contrast(accent2, bg) >= 1.5 else muted
        out = {"sea": bg, "land": land, "coast": paper, "side": ink, "casing": bg}
    elif accent2 != accent and contrast(accent2, paper) >= 1.15:
        out = {"sea": accent2, "land": paper, "coast": ink, "side": muted, "casing": paper}
    else:
        out = {"sea": muted, "land": paper, "coast": ink, "side": muted, "casing": paper}
    out["route"] = accent if contrast(accent, out["land"]) >= 2.5 else max((ink, paper), key=lambda h: contrast(h, out["land"]))
    # the words set over the map (the hook's title, the closer's names): whichever of the ink and the paper reads on
    # both the land and the sea
    out["over"] = max((ink, paper), key=lambda h: min(contrast(h, out["land"]), contrast(h, out["sea"])))
    # the handle under the hook's title: the accent where it reads on both, else the words' own color
    out["mark"] = accent if min(contrast(accent, out["land"]), contrast(accent, out["sea"])) >= 3 else out["over"]
    return out


def closer_window(style, W, H):
    """The window [x, y, w, h] frame px the closer leaves open on the map, inside the type-safe area, as the kit's closer
    for the style draws it (route/closers.tsx): the poster's cell under its title (swiss-grid), the band between the
    letterbox bars under the title card (cinematic-letterbox), the die-cut window in the book's cover (scrapbook). A
    vertical frame opens the window a tenth of its height deeper, so its still last frame fills the frame down to the
    band rather than ending above an empty lower third."""
    deep = 0.10 * H if H > 1.2 * W else 0.0
    if style == "swiss-grid":
        m = 60 * W / 1080
        return [round(m, 1), round(0.36 * H, 1), round(W - 2 * m, 1), round(0.28 * H + deep, 1)]
    if style == "cinematic-letterbox":
        return [0.0, round(0.33 * H, 1), float(W), round(0.30 * H + deep, 1)]
    return [round(0.14 * W, 1), round(0.30 * H, 1), round(0.72 * W, 1), round(0.30 * H + deep, 1)]


def closer_words_at(style, W, H):
    """Where the closer's title stands, the middle of its line as a share of the frame's height: over the window
    (route/closers.tsx)."""
    return round(closer_window(style, W, H)[1] / H - 0.08, 3)


_FONTS = {}


def font(face):
    from PIL import ImageFont
    if face["file"] not in _FONTS:
        _FONTS[face["file"]] = ImageFont.truetype(str(KIT / face["file"]), 1000)
    return _FONTS[face["file"]]


def width(text, size, face):
    """The line's advance in px at `size` in `face`, in the face's case with its tracking after each letter, as the
    studio lays it (system/three/type.ts)."""
    text = look.cased(text, face)
    return (font(face).getlength(text) / 1000 + face.get("tracking", 0) * len(text)) * size


def cap(size, face):
    box = font(face).getbbox("H")
    return (box[3] - box[1]) / 1000 * size


def top(text, size, face):
    """How far the line's ink rises above its baseline at `size`: its cap height, or more where an accent stands over a capital."""
    box = font(face).getbbox(look.cased(text, face), anchor="ls")
    return max(cap(size, face), -box[1] / 1000 * size)


def drop(text, size, face):
    """How far the line's ink hangs below its baseline at `size`: its descenders and commas."""
    return max(0.0, font(face).getbbox(look.cased(text, face), anchor="ls")[3] / 1000 * size)


def fit(text, most, room, face):
    """The largest size up to `most` at which the line runs no wider than `room` px."""
    return round(min(most, room / max(1e-6, width(text, 1, face))), 1)


def line(text, x, y, size, face, color="ink", rotate=0.0, pivot=None, name=None):
    ln = {"text": look.cased(text, face), "x": round(x, 1), "y": round(y, 1), "size": size, "file": face["file"], "color": color}
    if face.get("tracking"):
        ln["tracking"] = face["tracking"]
    if rotate:
        ln["rotate"] = round(rotate, 3)
        ln["pivot"] = [round(pivot[0], 1), round(pivot[1], 1)]
    if name:
        ln["name"] = name
    return ln


# ------------------------------------------------------------------ the map
def slerp_path(a, b, km):
    """Points along the great circle from a to b (lat, lon), about one each 40 km."""
    n = max(6, min(160, int(km / 40)))
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    p = [math.cos(la1) * math.cos(lo1), math.cos(la1) * math.sin(lo1), math.sin(la1)]
    q = [math.cos(la2) * math.cos(lo2), math.cos(la2) * math.sin(lo2), math.sin(la2)]
    w = math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(p, q)))))
    out = []
    for i in range(n + 1):
        t = i / n
        if w < 1e-9:
            v = p
        else:
            k1, k2 = math.sin((1 - t) * w) / math.sin(w), math.sin(t * w) / math.sin(w)
            v = [k1 * x + k2 * y for x, y in zip(p, q)]
        out.append((math.degrees(math.atan2(v[2], math.hypot(v[0], v[1]))), math.degrees(math.atan2(v[1], v[0]))))
    return out


def land_rings(proj, wall, step=1.5):
    """The land's rings on the mercator map `proj` that reach the wall (x0, y0, x1, y1 in px), projected to px, a point
    kept once it is `step` px from the last; each ring is set whole on the side of the globe nearest the map's middle,
    and a ring wholly south of 60 S, or wholly outside the wall, is left out."""
    rings = json.loads(LAND_FILE.read_text())["rings"]
    (l0, _), sc, (ax, _) = proj["center"], proj["scale"], proj["at"]
    s_, _, n_, _ = maps.region(proj, wall)
    out = []
    for r in rings:
        bw, bs, be, bn = r["bbox"]
        if bn < -60 or bn < s_ or bs > n_:
            continue
        shift = 360 * round((l0 - (bw + be) / 2) / 360)
        flat, pts = r["ring"], []
        for i in range(0, len(flat), 2):
            x = ax + sc * math.radians(flat[i] + shift - l0)
            y = maps.px(proj, flat[i + 1], l0)[1]
            if not pts or math.hypot(x - pts[-2], y - pts[-1]) >= step:
                pts += [round(x, 1), round(y, 1)]
        xs, ys = pts[0::2], pts[1::2]
        if len(pts) >= 6 and max(xs) >= wall[0] and min(xs) <= wall[2] and max(ys) >= wall[1] and min(ys) <= wall[3]:
            out.append(pts)
    return out


# ------------------------------------------------------------------ a card
# a side of the card's picture box that stands on the frame's edge runs this share of the frame past it, so the camera's
# turn over the hold never shows the photograph's edge
REACH = 0.04
# a line breaks into at most ROWS rows, set down to half the card's size to keep to them, LEAD of its size apart; the
# label stands GAP of its own size above the line
ROWS, LEAD, GAP = 3, 1.12, 0.7
# the most a photograph is enlarged to cover its box: past it the picture goes soft on a phone
ENLARGE = 1.6


def layout_of(lay, ph, W, H):
    """The card's photo layout for photograph `ph` on a W x H frame: on a tall frame a photograph wider than it is tall
    takes the card's landscape box and line box, so it fills the frame's foot instead of leaving bare ground under it."""
    if H <= W or ph["w"] <= ph["h"] or not lay.get("landscape"):
        return lay
    land = lay["landscape"]
    return {**lay, "picture": {**lay["picture"], "box": land["box"]}, "line": {**lay["line"], "box": land["line"]}}


def picture_box(fr, pic):
    """Where the style card stands a stop's photograph on the frame, [x0, y0, x1, y1] px: its box, a side on the frame's
    edge run REACH past it."""
    W, H = fr["width"], fr["height"]
    x, y, w, h = pic["box"] if pic["show"] else (0, 0, 1, 1)
    out = (x * W if x > 0 else -REACH * W, y * H if y > 0 else -REACH * H,
           (x + w) * W if x + w < 1 else (1 + REACH) * W, (y + h) * H if y + h < 1 else (1 + REACH) * H)
    return [round(v, 1) for v in out]


def placed(ph, box):
    """The photograph laid over the picture box around its focus, enlarged ENLARGE times at most: its rectangle [x, y, w, h] frame px,
    the scale (frame px per photograph px), and the part of the box it covers [x0, y0, x1, y1] (all of it when it has the
    pixels to; a smaller photograph stands at its own size in the box's middle)."""
    bx0, by0, bx1, by1 = box
    bw, bh = bx1 - bx0, by1 - by0
    w, h = ph["w"], ph["h"]
    fu, fv = ph.get("focus") or (0.5, 0.5)
    sc = min(ENLARGE, max(bw / w, bh / h))
    pw, ph_ = w * sc, h * sc
    x = bx0 + (bw - pw) / 2 if pw < bw else min(bx0, max(bx1 - pw, (bx0 + bx1) / 2 - fu * pw))
    y = by0 + (bh - ph_) / 2 if ph_ < bh else min(by0, max(by1 - ph_, (by0 + by1) / 2 - fv * ph_))
    seen = [max(bx0, x), max(by0, y), min(bx1, x + pw), min(by1, y + ph_)]
    return [round(x, 1), round(y, 1), round(pw, 1), round(ph_, 1)], round(sc, 4), [round(v, 1) for v in seen]


def slope_of(ph):
    """The slope (px down per px across) of the photograph's own line (grade.py), kept within TILT of level; 0 for one
    with no line. A clip's truck runs along it."""
    ln = ph.get("line")
    if not ln:
        return 0.0
    du, dv = (ln[2] - ln[0]) * ph["w"], (ln[3] - ln[1]) * ph["h"]
    most = math.tan(math.radians(TILT))
    return round(max(-most, min(most, dv / du if abs(du) > 1e-6 else 0.0)), 4)


def crop_of(ph):
    """The square of the photograph the pin shows, around its subject, as [u0, v0, u1, v1] fractions (v from the top)."""
    w, h = ph["w"], ph["h"]
    fu, fv = ph.get("focus") or (0.5, 0.5)
    side = min(w, h)
    su, sv = side / w, side / h
    u0 = min(max(fu - su / 2, 0.0), 1 - su)
    v0 = min(max(fv - sv / 2, 0.0), 1 - sv)
    return [round(u0, 4), round(v0, 4), round(u0 + su, 4), round(v0 + sv, 4)]


def line_box(fr, lay):
    """The box the style card sets a stop's label and line in, [x0, y0, x1, y1] px: its shares of the type-safe area."""
    a = (fr["left"], fr["top"], fr["width"] - fr["right"], fr["height"] - fr["bottom"])
    x, y, w, h = lay["line"]["box"]
    return [round(a[0] + x * (a[2] - a[0]), 1), round(a[1] + y * (a[3] - a[1]), 1),
            round(a[0] + (x + w) * (a[2] - a[0]), 1), round(a[1] + (y + h) * (a[3] - a[1]), 1)]


def rows_of(text, sizes, room, tall, face):
    """`text` in the fewest rows of whole words (at most ROWS, the breaks balancing the rows) at the largest size from
    sizes[0] down to sizes[1] at which every row runs no wider than `room` px and the rows stand no taller than `tall`.
    Returns (rows, size); at the floor the fewest rows that fit the width, or ROWS rows."""
    words = text.split()
    best = None
    for n in range(1, min(ROWS, len(words)) + 1):
        cuts = [()]
        for _ in range(n - 1):
            cuts = [c + (k,) for c in cuts for k in range((c[-1] if c else 0) + 1, len(words))]
        cuts = [c for c in cuts if len(c) == n - 1]
        rows = min(([" ".join(words[a:b]) for a, b in zip((0,) + c, c + (len(words),))] for c in cuts),
                   key=lambda rs: max(width(r, 1, face) for r in rs))
        wide = max(width(r, 1, face) for r in rows)
        size = min(sizes[0], room / wide, tall / (LEAD * (n - 1) + 1.0))
        if size >= sizes[0] - 0.05:
            return rows, round(sizes[0], 1)
        if best is None or size > best[1]:
            best = (rows, size)
    rows, size = best
    return rows, round(max(size, sizes[1]), 1)


def photo_words(fr, lay, spec, label, text, name="said", keep=False):
    """A stop's words as the style card sets them in its line box: the label in the card's label face, size and color at
    the box's top, and the line under it broken into rows at the card's size (down to half of it), aligned as the card
    aligns them and turned by its angle about the box's middle. With `keep` the line stays at the card's size in as many
    rows as its width needs, and the words rise out of the box's top by whatever they need below its foot. Returns
    (lines, the middle of the inked box as a share of the frame's height)."""
    if not label and not text:
        return [], None
    W, H = fr["width"], fr["height"]
    k = min(W, H) / 1080
    box = line_box(fr, lay)
    ln, lab = lay["line"], lay["label"]
    lf, tf = spec[lab["face"]], spec[ln["face"]]
    room = box[2] - box[0]
    # the card's label size, never under the type floor (LABEL of the short side)
    ns = max(round(lab["size"] * k), round(LABEL * min(W, H), 1))
    gap = GAP * ns if label else 0.0
    out, y = [], box[1]
    deg = ln.get("rotate", 0) or 0
    pivot = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    def x_of(text_, size, face):
        w = width(text_, size, face)
        return box[0] if ln["align"] == "start" else box[2] - w if ln["align"] == "end" else (box[0] + box[2] - w) / 2

    if label:
        # a label too long for the box at the floor breaks where its parts meet (the name over the month), never under it
        least = round(LABEL * min(W, H), 1)
        fitted = round(min(ns, fit(label, ns, room, lf)), 1)
        parts = label.split(" · ")
        if fitted >= least - 0.05:
            labels, ns = [label], fitted
        elif len(parts) > 1 and all(width(q, ns, lf) <= room for q in parts):
            labels = parts
        else:
            labels, ns = rows_of(label, (ns, least), room, H, lf)
            ns = round(ns, 1)
        y += top(labels[0], ns, lf)
        for i, q in enumerate(labels):
            out.append(line(q, x_of(q, ns, lf), y + i * LEAD * ns, ns, lf, lab["color"], deg, pivot, name="label"))
        y += (len(labels) - 1) * LEAD * ns + drop(labels[-1], ns, lf) + gap
    if text:
        size0 = round(ln["size"] * k)
        least, tall = (size0, math.inf) if keep else (size0 / 2, box[3] - y - 0.28 * size0)
        rows, size = rows_of(text, (size0, least), room - 0.03 * size0, tall, tf)
        y += top(rows[0], size, tf)
        for i, r in enumerate(rows):
            out.append(line(r, x_of(r, size, tf), y + i * LEAD * size, size, tf, ln["color"], deg, pivot, name=name))
        y += (len(rows) - 1) * LEAD * size + drop(rows[-1], size, tf)
        over = y - (box[3] - 0.28 * size0) if keep else 0.0
        if over > 0:
            for o in out:
                o["y"] = round(o["y"] - over, 1)
                if "pivot" in o:
                    o["pivot"][1] = round(o["pivot"][1] - over, 1)
            return out, round(((box[1] - over + box[3] - 0.28 * size0) / 2) / H, 3)
    return out, round(((box[1] + y) / 2) / H, 3)


def title_words(fr, spec, title, handle, style):
    """The hook's words over the whole route, before the first photograph opens: the film's title in the display face,
    as large as the safe width allows up to a sixth of the short side, with the handle under it in the text face; set
    flush left on the foot of the safe area like a poster's headline (swiss-grid), centered in the lower third
    (cinematic-letterbox), or centered in the lower third and turned a little as if written there (scrapbook), so a
    stop's words over its photograph (the top third on a wide photograph) never stand where the title stood."""
    W, H = fr["width"], fr["height"]
    d, t = spec["display"], spec["text"]
    L, R = fr["left"], W - fr["right"]
    room = R - L
    deg = -2.0 if style == "scrapbook" else 0.0
    # a turned title's ends rise and fall by half its width times the turn's sine, so it is fitted to the room that leaves
    lean = abs(math.sin(math.radians(deg)))
    size = fit(title, min(W, H) / 6, room / (1 + lean), d)
    hs = round(0.032 * min(W, H))
    center = style != "swiss-grid"
    w0 = width(title, size, d)
    y = fr["top"] + top(title, size, d) + lean * w0 / 2 if style == "swiss-grid" else 0.62 * H
    hy = y + drop(title, size, d) + 0.9 * hs + cap(hs, t)
    # the lower-third title stands with its handle (and a turned title's lower end) inside the type-safe area's foot
    foot = (hy + drop(handle, hs, t) if handle else y + drop(title, size, d)) + lean * w0 / 2 - (H - fr["bottom"])
    if foot > 0 or style == "swiss-grid":
        y, hy = y - foot, hy - foot
    x = (lambda w: (W - w) / 2) if center else (lambda w: L)
    out = [line(title, x(w0), y, size, d, "over", deg, (W / 2, y), name="title")]
    if handle:
        out.append(line(handle, x(width(handle, hs, t)), hy, hs, t, "mark", deg, (W / 2, y), name="handle"))
    return out


# the type floor of a card's label: LABEL of the frame's short side
LABEL = 0.03
# a style card whose faces are lighter than a phone holds at caption size, as the route sets them: each face's file and
# weight, a static instance of the card's own family (fonts/route/), and its caption kept at the card's size
PHONE = {"cinematic-letterbox": {"display": ("fonts/route/cinematic-letterbox/Cinzel-SemiBold.ttf", 600),
                                 "text": ("fonts/route/cinematic-letterbox/Cormorant-Medium.ttf", 500)}}


# ------------------------------------------------------------------ the board
def kind_of(s, said, peak):
    if s["i"] == 0:
        return "hook"
    if peak:
        return "peak"
    return "new" if said else "quick"


def leaves_by_leap(tr, s, nxt):
    """The camera leaves the stop across a leap over the water: the next place or this one is a far place."""
    return nxt is not None and (nxt["place"] in tr.far or s["place"] in tr.far)


def sub_of(tr, s, last):
    """The word after the place's name: "home" on the first or last stop only when it is the home the person named
    (tr.home_said), never a home the kit inferred; "again" on a revisit; else the month."""
    month = (s["month"] or "").capitalize()
    if tr.home_said and s["place"] == tr.home and (last or s["i"] == 0):
        return f"{month}, home" if month else "home"
    if s["n"] > 1:
        return f"{month}, again" if month else "again"
    return month or None


def reading(words):
    """The seconds a line of `words` words needs on screen."""
    return READ[0] + READ[1] * words if words else 0.0


def carried(looks, words):
    """What each stop's photograph carries, as a multiple of its kind's pace: its words, its detail against the set's
    (a busy scene has more edges) and its change from the photograph before (a repeat of the same view changes least),
    from each photograph's `look` (grade.py: its lightness and edge strength per cell of a grid)."""
    cells = lambda look, key: [v for row in look[key] for v in row] if look else None
    light = [cells(lk, "light") for lk in looks]
    busy = [statistics.fmean(c) if (c := cells(lk, "busy")) else None for lk in looks]
    change = [None] + [statistics.fmean(abs(a - b) for a, b in zip(light[k], light[k - 1])) if light[k] and light[k - 1] else None
                       for k in range(1, len(looks))]

    def ratio(x, of):
        known = [v for v in of if v is not None]
        mid = statistics.median(known) if known else 0
        return min(2.0, max(0.5, x / mid)) if x is not None and mid > 0 else 1.0
    moved = [None if c is None else c + SAME for c in change]
    return [(1 + CARRY * words[k]) * math.sqrt(ratio(busy[k], busy) * ratio(moved[k], moved)) for k in range(len(looks))]


def scaled(least, pace, most, goal):
    """Every hold in seconds: each its pace, all scaled by one factor so they add up to `goal`, each kept between its
    least and its most."""
    at = lambda s: [min(hi, max(lo, s * p)) for lo, p, hi in zip(least, pace, most)]
    lo, hi = 0.0, 1.0
    while sum(at(hi)) < goal and hi < 1e4:
        hi *= 2
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if sum(at(mid)) < goal else (lo, mid)
    return at(hi)


def in_beats(holds, least, total):
    """The holds (seconds, at one beat a second) as whole beats adding up to `total`, each at least its `least` beats:
    the running sum rounded, so no stop drifts off the beat, then any stop under its least raised from the stops with
    the most to spare."""
    k = total / max(1e-9, sum(holds))
    out, run, at = [], 0.0, 0
    for h in holds:
        run += h * k
        out.append(round(run) - at)
        at = round(run)
    for i in range(len(out)):
        while out[i] < least[i]:
            j = max(range(len(out)), key=lambda j: out[j] - least[j])
            if out[j] - least[j] <= 0:
                break
            out[j] -= 1
            out[i] += 1
    return [max(b, f) for b, f in zip(out, least)]


def closer_beats(bpm, words=0):
    """(the beats the closer takes to resolve out of the map, the closer's beats in all) at `bpm`: ROUTE seconds to
    the nearest beat and two beats at least, then the map still for STILL seconds, or for as long as its `words` still
    need reading once they have risen, to the beat after."""
    sec = 60 / bpm
    route = max(2, round(ROUTE / sec))
    still = max(STILL, reading(words) - (route - RISEN) * sec)
    return route, route + math.ceil(still / sec - 1e-9)


class TooLong(ValueError):
    """The stops' words take longer to read than the longest film the kit makes."""


def first_clause(text):
    """A line's first clause: up to its first comma, semicolon, colon or dash; None when the line is one clause."""
    head = re.split(r"\s*[,;:\u2013\u2014]\s*|\s+-\s+", text.strip())[0].strip()
    return head if head and head != text.strip() else None


def peak_short(board):
    """Whether a stop holds more beats of its own than the peak (a leap's travel is the camera's, never a stop's)."""
    own = [(b["bars"] * 4 - (LEAP if c["go"] == LEAP_GO else 0), c["kind"]) for c, b in zip(board["route"]["cards"], board["beats"])]
    peak = [h for h, kind in own if kind == "peak"]
    return bool(peak) and peak[0] < max(h for h, _ in own)


def fit_lines(source, fmt="reel", style="swiss-grid"):
    """The source with the person's lines fitted to the longest film, with room for the peak to hold longest: while the stops'
    words take longer than LENGTH[1] to read, or leave the peak fewer beats than another stop, the longest of the lines
    that has more than one clause is set to its first clause; with none left, the longest line away from the hook and
    the peak is left out (the place keeps its name). Only a film too long to read goes on to the hook's and the peak's
    own lines. Each visit it changes is listed once in `trimmed` [{place, n, line, now}], `line` as the person wrote it and
    `now` what the film says; every place stays. A source that fits comes back as it is, with `trimmed` empty."""
    source = json.loads(json.dumps(source))
    source["trimmed"] = []
    moments = source.get("moments") or []
    first = next(((m["place"], m["n"]) for m in moments), None)
    while True:
        said = [m for m in moments if m.get("line")]
        longest = lambda ms: max(ms, key=lambda m: len(m["line"].split()), default=None)
        m = longest([m for m in said if first_clause(m["line"])]) or \
            longest([m for m in said if not m.get("peak") and (m["place"], m["n"]) != first])
        try:
            if not peak_short(build(source, fmt, style=style)) or m is None:
                return source
        except TooLong:
            m = m or longest(said)
            if m is None:
                raise
        now = first_clause(m["line"])
        was = next((t for t in source["trimmed"] if (t["place"], t["n"]) == (m["place"], m["n"])), None)
        if was:
            was["now"] = now
        else:
            source["trimmed"].append({"place": m["place"], "n": m["n"], "line": m["line"], "now": now})
        m["line"] = now


def timing(stops, bpm, asked=None):
    """Each stop's hold in whole beats at `bpm`, from what its photograph carries, scaled so the film runs as near
    `asked` seconds as these stops make (with none, its own pace inside LENGTH), and the band of lengths the film is
    held to: from LENGTH[0], or from the longest film the stops' holds reach when that is shorter, to LENGTH[1]. A trip
    too small to fill LENGTH[0] runs as long as its photographs carry; no hold is stretched past its kind's MOST. The
    peak the curation marks holds the most beats: until no stop holds more, it takes a beat from the longest stop that
    holds more than its floor, or, with none, a beat more while the film stays inside its band.
    `stops` are [{kind, words, look, need, leap, travel}], `need` the seconds from its arrival that its words take to
    come up and be read before the camera leaves, `travel` the beats a rise out of it takes beyond GO, which its
    pace and its most hold take on too, so a rise never eats the time a photograph carries; the closer's beats
    are stops[-1]["closer"]. Stops whose words alone take longer than LENGTH[1] to read are refused in one line."""
    sec = 60 / bpm
    closer = stops[-1]["closer"]
    stops = stops[:-1]
    least = [max(SEEN[s["kind"]], s["need"]) for s in stops]
    floor = [math.ceil(x / sec - 1e-9) for x in least]
    weight = carried([s["look"] for s in stops], [s["words"] for s in stops])
    # a stop's own pace is never under its floor, so the time one stop carries is never spent on another's floor
    pace = [max(PACE[s["kind"]] * w + s["travel"] * sec, f * sec) for s, w, f in zip(stops, weight, floor)]
    most = [max(lo, MOST[s["kind"]] + s["travel"] * sec) for lo, s in zip(least, stops)]
    fixed = (closer + LEAP * sum(1 for s in stops if s["leap"])) * sec
    lo, hi = sum(floor) * sec + fixed, max(sum(floor) * sec, sum(most)) + fixed
    if lo > LENGTH[1] + 1e-6:
        raise TooLong(f"these {len(stops)} stops take {math.ceil(lo - 1e-6)} s to read and the kit makes {LENGTH[1]} s at most; "
                      "drop places with places.py")
    top_ = min(hi, LENGTH[1])
    bottom = min(max(lo, LENGTH[0]), top_)
    goal = min(max(asked or sum(pace) + fixed, bottom), top_)
    holds = scaled(least, pace, most, goal - fixed)
    # whole beats: the goal's rounded down, never under the bottom's rounded up, never over the top's rounded down
    down = lambda g: max(sum(floor), math.floor((g - fixed) / sec + 1e-6))
    most_beats = down(top_)
    total = min(max(down(goal), math.ceil((bottom - fixed) / sec - 1e-6)), most_beats)
    band = [round(min(LENGTH[0], most_beats * sec + fixed), 3), LENGTH[1]]
    held = in_beats(holds, floor, total)
    for p in (i for i, s in enumerate(stops) if s["kind"] == "peak"):
        while max(held) > held[p]:
            give = [j for j in range(len(held)) if j != p and held[j] > floor[j]]
            if give:
                held[max(give, key=lambda j: held[j])] -= 1
            elif sum(held) >= most_beats:
                break
            held[p] += 1
    return held, band


def build(source, fmt="reel", bpm=None, style="swiss-grid"):
    sa = SAFE[fmt]
    W, H = sa["width"], sa["height"]
    # a card's type is laid where the camera holds it as it leaves, pushed in to HOLD_END of the card's frame, so a line
    # that ends its hold on the type-safe area's edge stands inside it the whole hold
    held = lambda m, side: round(side / 2 - (side / 2 - m) * HOLD_END, 1)
    fr = {"width": W, "height": H, "left": held(sa["left"], W), "right": held(sa["right"], W), "top": held(sa["top"], H),
          "bottom": held(sa["bottom"], H)}
    short = min(W, H)
    tr = trip_mod.Trip(source["places"], source["photos"])
    if not tr.mapped:
        miss = [q["name"] for q in tr.places.values() if not trip_mod.has_xy(q)]
        raise ValueError(f"the film runs on the map, and {', '.join(miss)} has no coordinates: add it with places.py "
                         f"--add \"NAME@lat,lon\" or drop it with --drop, then run storyboard.py draft again")
    handle = source["handle"]
    year = tr.year
    stops = tr.stops
    pin = round(0.08 * short)
    said_of = {(m["place"], m["n"]): m["line"] for m in source.get("moments") or [] if m.get("line")}
    # the one peak of the film, the moment the curation marks
    peak = next(((m["place"], m["n"]) for m in source.get("moments") or [] if m.get("peak")), None)
    taste = source.get("taste") or {}
    card_ = look.card(style)
    made = look.palette_of(card_["palette"], look.swatches_of(taste, taste.get("palette") or source.get("palette")))
    roles = made["roles"]
    spec = {f: dict(card_["faces"][f], **dict(zip(("file", "weight"), PHONE[style][f]))) if style in PHONE else card_["faces"][f]
            for f in ("display", "text")}
    t = spec["text"]

    # the map: the mercator crop of the route's region, fitted to the window the closer leaves open on it
    window = closer_window(style, W, H)
    proj = maps.fit_region([(s["lat"], s["lon"]) for s in stops], window, MARGIN, LEAST)

    def pin_of(s):
        x, y = maps.px(proj, s["lat"], s["lon"])
        return [round(x, 1), round(y, 1)]

    # the style card's photo layout: where a stop's photograph stands on its card, and where its words stand
    lay0 = card_["photo"]
    # a card stands large on the map: the camera's station frames it whole
    s_card = 0.16
    cards, legs, timed, steps = [], [], [], []
    used_m, used_c, prev_m, prev_c = {}, {}, None, None
    # the ways the style card's own moves bring a photograph onto its page; a stop arrives by the one used least so far,
    # never the way the stop before it did, and the hook opens out of its pin
    own = {o["id"] for o in card_["moves"]} | {o["id"] if isinstance(o, dict) else o for o in card_["transitions"]}
    arrives = [a for a in ARRIVES if a in own]
    used_e, prev_e = {}, None
    for s in stops:
        last = s["i"] == len(stops) - 1
        nxt = None if last else stops[s["i"] + 1]
        said = said_of.get((s["place"], s["n"]))
        kind = kind_of(s, said, (s["place"], s["n"]) == peak)
        leap = leaves_by_leap(tr, s, nxt)
        ph = tr.photo(s["place"], s["n"])
        lay = layout_of(lay0, ph, W, H)
        pbox = picture_box(fr, lay["picture"])
        p = pin_of(s)
        prev = stops[s["i"] - 1] if s["i"] else None
        # a place reached heading west drifts its photograph the way the dot came
        west = prev is not None and (s["lon"] - prev["lon"] + 540) % 360 - 180 < 0
        sub = sub_of(tr, s, last)
        # the beat's move and the cut into it, from what the beat holds: the hook is the title, every other stop a
        # photograph, each tagged by its words, its shape, the peak and the place; a move that lays a field over the
        # whole frame would hide the card's words, so a stop never takes one, and the hook never opens on black
        form = "title" if s["i"] == 0 else "photo"
        tags = {form, "place", "words" if said else "wordless", "portrait" if ph["h"] > ph["w"] else "landscape"}
        if kind == "peak":
            tags.add("peak")
        bar = look.COVERS | (look.DARK if s["i"] == 0 else set())
        opts = [o for o in card_["moves"] if o["id"] not in bar] or card_["moves"]
        move = look.pick(opts, tags, form, used_m, prev_m)
        cut = None if s["i"] == 0 else look.pick(card_["transitions"], tags, form, used_c, prev_c)
        prev_m, prev_c = move, cut or prev_c
        pool = [e for e in arrives if e != prev_e]
        entry = "pin" if s["i"] == 0 or not pool else min(pool, key=lambda e: (used_e.get(e, 0), ARRIVES.index(e)))
        used_e[entry], prev_e = used_e.get(entry, 0) + 1, entry
        # the card's layout sets the words: the place's name as the label over the person's line, or, on a stop with no
        # line, the name as the line under its month; a sticker carries the month itself
        sticker = move == "sticker-pop" and bool(sub)
        if said:
            label, text = (s["name"] if sticker or not sub else f"{s['name']} · {sub}"), said
        else:
            label, text = (None if sticker else sub), s["name"]
        words, words_at = photo_words(fr, lay, spec, label, text, name="said" if said else "name", keep=style in PHONE)
        photo, scale, seen = placed(ph, pbox)
        fu, fv = ph.get("focus") or (0.5, 0.5)
        bid = "hook" if s["i"] == 0 else f"stop-{s['i']}"
        # the camera's travel out of this stop: across a leap, into the closer, or between two near places a rise unless
        # the travel before was a rise or a leap, or a leap or the closer follows, where it is a lift
        before = cards[-1]["travel"] if cards else None
        beside = not last and (nxt["i"] == len(stops) - 1 or leaves_by_leap(tr, nxt, stops[nxt["i"] + 1]))
        travel = "leap" if leap else "closer" if last else "lift" if before in ("rise", "leap") or beside else "rise"
        c = {"id": bid, "i": s["i"], "kind": kind, "place": s["place"], "name": s["name"], "n": s["n"], "file": ph["file"],
             "west": west, "slope": slope_of(ph), "photo": photo, "box": seen, "scale": scale, "pin": p, "crop": crop_of(ph), "s": s_card,
             "o": [round(p[0] - s_card * W / 2, 2), round(p[1] - s_card * H / 2, 2)], "lines": words, "travel": travel, "entry": entry,
             "focus": [round(photo[0] + fu * photo[2], 1), round(photo[1] + fv * photo[3], 1)],
             "cut": CUT[kind], "go": LEAP_GO if leap else RISE_GO if travel == "rise" else GO, "said": said, "far": s["place"] in tr.far}
        cards.append(c)
        steps.append({"form": form, "move": move, "transition": cut, "words": "", "label": sub if sticker else "",
                      "peak": kind == "peak", "words_at": words_at})
        # the words come up at the cut (the hook's at HOOK_NAME, after the title has had the frame) and stand until the
        # camera leaves; across a leap the camera's travel takes LEAP beats of its LEAP_GO, the rest is the stop's own
        n_words = len((said or "").split()) + len(s["name"].split()) + len((sub or "").split())
        up = (HOOK_NAME if s["i"] == 0 else c["cut"]) + (LEAP_GO - LEAP if leap else c["go"])
        timed.append({"kind": kind, "words": n_words, "look": ph.get("look"), "leap": leap, "up": up, "said": reading(n_words),
                      "travel": c["go"] - GO if travel == "rise" else 0.0})
        if nxt is not None:
            pts = [maps.px(proj, la, lo) for la, lo in slerp_path((s["lat"], s["lon"]), (nxt["lat"], nxt["lon"]), nxt["leg"] or 1)]
            q = pin_of(nxt)
            pts[0], pts[-1] = tuple(p), tuple(q)
            legs.append({"from": s["i"], "to": nxt["i"], "far": nxt["place"] in tr.far or s["place"] in tr.far,
                         "pts": [[round(x, 1), round(y, 1)] for x, y in pts]})

    # each photograph folds into a small print on its own pin; a revisit lands on its place's first print, a little
    # across it, so the map holds one stack per place
    size = round(PRINT * short)
    first = {}
    for c in cards:
        f = first.setdefault(c["place"], c)
        k = sum(1 for d in cards[:c["i"]] if d["place"] == c["place"])
        c["slot"] = [round(f["pin"][0] + STACK_STEP * size * k, 1), round(f["pin"][1] - STACK_STEP * size * k, 1)]
        c["size"] = size

    # the closer: the title in the person's words (else the year), the places in the order they were first reached,
    # the handle, all set by the closer's shape around the map's window
    title = str(taste.get("title") or source.get("title") or year)
    signoff = " · ".join(dict.fromkeys(c["name"] for c in cards))
    kicker = title_words(fr, spec, title, handle, style)
    # the hook's words are its title and handle: where they stand is where the hook carries words
    k0, k1 = kicker[0], kicker[-1]
    k_face = lambda ln: spec["display"] if ln["name"] == "title" else spec["text"]
    steps[0]["words_at"] = round((k0["y"] - top(k0["text"], k0["size"], k_face(k0)) + k1["y"] + drop(k1["text"], k1["size"], k_face(k1))) / 2 / H, 3)

    bpm_ = bpm or BPM
    sec = 60 / bpm_
    route_beats, closer = closer_beats(bpm_, len(title.split()) + len(signoff.split()) + len((handle or "").split()))
    for x in timed:
        x["need"] = x["up"] * sec + x["said"]
    held, band = timing(timed + [{"closer": closer}], bpm_, source.get("seconds"))
    beats = [{"id": c["id"], "bars": (h + (LEAP if x["leap"] else 0)) / 4, "role": c["kind"], "layers": [], **st}
             for c, x, h, st in zip(cards, timed, held, steps)]
    tags = {"closer", "wall"}
    beats.append({"id": "closer", "bars": closer / 4, "role": "closer", "layers": [], "form": "closer",
                  "move": look.pick(card_["moves"], tags, "closer", used_m, prev_m),
                  "transition": look.pick(card_["transitions"], tags, "closer", used_c, prev_c),
                  "words": title, "label": handle or "", "peak": False, "words_at": closer_words_at(style, W, H)})

    safe = {k: {e: v[e] for e in ("top", "bottom", "left", "right")} for k, v in SAFE.items() if isinstance(v, dict)}
    board = {"id": f"places-{style}", "style": style, "name": f"{year} in places · {card_['name']}", "handle": handle, "year": year,
             "bpm": bpm_, "format": {"width": W, "height": H, "fps": FPS, "name": fmt},
             "system": look.system(card_, {**roles, "swatches": made["swatches"]}, safe), "length": band, "beats": beats,
             "route": {"W": W, "H": H, "pin": pin, "colors": {**roles, **map_colors(roles)}, "proj": proj, "box": window,
                       "land": land_rings(proj, (-W, -H, 2 * W, 2 * H)), "cards": cards, "legs": legs,
                       "hook": {"kicker": kicker, "name": HOOK_NAME, "dive": HOOK_DIVE, "settle": HOOK_SETTLE},
                       "closer": {"window": window, "title": title, "signoff": signoff, "route": route_beats,
                                  "paper": PAPER}}}
    board["sound"] = sound(board)
    board["clips"] = clips(board, {ph["file"]: ph for ph in source["photos"]})
    story(board)
    return board


# ------------------------------------------------------------------ timing, story, sound, clips
def starts(board):
    """Each beat's start in musical beats from the film's start, and the film's end."""
    out, t = {}, 0.0
    for b in board["beats"]:
        out[b["id"]] = t
        t += 4 * b["bars"]
    return out, t


# what each kit closer is, in plain words, for the story and the cues
CLOSERS = {"poster": "a poster", "title-card": "a title card", "book-cover": "a book closing on it"}


def sound(board):
    """The film's sound cues (`at` in beats from the film's start) for music.py to mix under the bed: one where each beat
    lands (each place's name coming up on its card), the
    build over the two beats into the peak (the one the curation marks, else the middle stop) and the impact where the
    peak's name lands, the impact as the map resolves into the closer, and the stop as the closer lands, where the bed
    cuts and the film holds silent. The camera's moves and the prints folding carry no sound of their own."""
    rt = board["route"]
    st, _ = starts(board)
    cards = rt["cards"]
    peak = next((c for c in cards if c["kind"] == "peak"), cards[len(cards) // 2])
    cues = []
    for i, c in enumerate(cards):
        at = rt["hook"]["name"] if i == 0 else round(st[c["id"]] + c["cut"], 3)
        what = f"{c['name']} lands" + (" under the person's line" if c.get("said") else "") + ("" if i else " as the title leaves")
        if c is peak:
            rise = max(0.0, round(at - 2.0, 3))
            cues.append({"kind": "riser", "at": rise, "beats": round(at - rise, 3), "beat": c["id"], "what": f"the build into {c['name']}" + (", the peak" if c["kind"] == "peak" else ", the middle stop")})
            cues.append({"kind": "impact", "at": at, "beat": c["id"], "what": what})
        else:
            cues.append({"kind": "hit", "at": at, "beat": c["id"], "what": what, "weight": 0.85 if c["far"] else 0.6, "bright": 0.8})
    C = st["closer"]
    shape = CLOSERS.get(board["system"]["closer"], "the closer")
    cues.append({"kind": "impact", "at": C + CLOSER_LAND, "beat": "closer", "what": f"the map resolves into {shape}"})
    cues.append({"kind": "stop", "at": C + rt["closer"]["route"], "beat": "closer", "what": "the closer lands; the picture and the music stop together"})
    return sorted(cues, key=lambda c: c["at"])


def story(board):
    rt = board["route"]
    cards = rt["cards"]
    shape = CLOSERS.get(board["system"]["closer"], "the closer")
    for i, b in enumerate(board["beats"]):
        if b["id"] == "closer":
            b["reveals"] = (f"the map resolving into {shape}, \"{rt['closer']['title']}\" over it: the route through every place, "
                            "each place named on its own print, the map showing through the closer's window")
            b["carries"] = "nothing: the picture and the music stop together and the closer holds still and silent to the end"
            continue
        c = cards[i]
        nxt = cards[i + 1]["name"] if i + 1 < len(cards) else None
        said = f"the line \"{c['said']}\"" if c.get("said") else "the name alone"
        if c["kind"] == "hook":
            b["reveals"] = (f"the whole route at once under the film's title, every pin set out and the dot on {c['name']}; the camera "
                            f"comes down onto {c['name']} as its photograph opens out of the pin, then {c['name']} with {said} ({b['move']})")
        else:
            b["reveals"] = (f"{c['name']} opening out of its pin into its card, its photograph laid out by the style, and {c['name']} "
                            f"with {said} ({b['move']})" + (" (the peak, held longest)" if c["kind"] == "peak" else ""))
        b["carries"] = (f"the dot: it runs the leg to {nxt} while {nxt} opens and this photograph folds to its print on its pin" if nxt else
                        "the dot: the photograph folds to its print and the camera rises to the whole map")


# the camera a clip asks for, by the beat's move, in a camera operator's words: each style's moves shot the way the style
# moves; a beat whose move has no camera of its own takes the move its photograph's line and focus call for
CAMERA = {"grid-snap": "a locked-off frame that steps in once, hard, on the beat",
          "cell-reveal": "a locked-off frame, the subject held square in the middle",
          "rule-draw": "a slow level push in, the horizon held dead straight",
          "crop-shift": "a crisp lateral slide to the {side} that stops exactly",
          "scale-to-cell": "a slow pull back, the subject held in the middle as the frame opens",
          "bars-open": "a slow crane down onto the subject",
          "anamorphic-push": "a slow push in toward the subject on an anamorphic lens, the background falling soft",
          "lateral-dolly": "a slow lateral dolly to the {side}, the foreground passing faster than the distance",
          "long-fade-title": "a near-still frame with the faintest drift",
          "match-cut": "a still frame that keeps the subject's shape where the shot before left it",
          "polaroid-drop": "a handheld frame settling as if just set down on a table",
          "tape-slap": "a quick handheld nudge to the {side} that settles",
          "doodle-draw-on": "a gentle handheld drift, as if looking over a page",
          "sticker-pop": "a small handheld bounce in toward the subject",
          "page-drift": "a slow handheld drift across the scene",
          "slow-push": "a slow, even push in toward the subject",
          "breath-hold": "a near-still frame that breathes in a touch and holds",
          "white-space-crop": "a slow pull back that leaves wide quiet space around the subject",
          "diptych": "a locked-off frame, the subject set to one side",
          "date-stamp": "a handheld home-movie frame with a slow, slightly unsteady drift",
          "gate-weave": "a handheld home-movie frame with a gentle film-gate weave",
          "light-leak": "a slow handheld drift toward the light",
          "roll-burn": "a slow handheld drift that holds on the light",
          "zoom-rocker": "a slow handheld zoom in and back out, the way a home-movie camera zooms",
          "word-per-beat-slam": "a hard punch in on the beat that holds",
          "stack-and-split": "a quick push in that stops hard on the beat",
          "marquee": "a fast lateral slide to the {side} that stops on the beat",
          "type-mask-reveal": "a slow push in, the subject held square",
          "line-by-line-type-rise": "a slow crane up toward the subject",
          "width-stretch": "a quick pull back that stops on the beat"}
CLIP_MOVES = {"truck": "a slow lateral truck to the {side} along the photograph's line, the foreground passing faster than the distance",
              "crane": "a gentle crane up toward the subject, revealing more of the place around it",
              "push": "a slow push in toward the subject",
              "pull": "a slow pull back, the frame opening around the subject"}
# a texture between chapters is the place's material close up, each in turn a different close camera on it
TEXTURE = ("a slow close-up slide across the surface, low to it, the light moving over its grain",
           "a locked-off macro frame, the focus pulling slowly from the near grain to the far",
           "a slow overhead drift straight down onto the surface, turning a few degrees as it goes")
# the camera's travel out of a stop, as a clip's stand-in names it
OUT = {"rise": "climbs over the map to show every near place",
       "lift": "comes down onto the leg as the photograph folds off the map, riding the dot",
       "leap": "crosses the water", "closer": "rises to the whole map"}
# the lightness of the top row of a photograph's look under which its light reads as low and over which as bright
LIGHT = (0.35, 0.65)


def clip_move(c, W, before):
    """A card's clip move, measured on its photograph, each 0 to 1: a truck by its line's tilt as a share of half of
    TILT, a crane by how high its focus stands, a push by how near the middle it stands and a pull by how near a side or
    the foot; the best that is not `before`, the move of the stop before. A truck runs the way the line falls, or the
    way the dot came along a level one. Returns (the move, its words)."""
    x, y, w, h = c["photo"]
    u, v = (c["focus"][0] - x) / w - 0.5, (c["focus"][1] - y) / h - 0.5
    slope = c["slope"]
    score = {"truck": min(1.0, abs(slope) / math.tan(math.radians(TILT / 2))), "crane": -2 * v, "push": 1 - 2 * max(abs(u), abs(v)),
             "pull": 2 * max(abs(u), v)}
    move = max((m for m in score if m != before), key=score.get)
    return move, CLIP_MOVES[move].format(side=side_of(c, W))


def side_of(c, W):
    slope = c["slope"]
    return "right" if slope > 0 or (slope == 0 and not c["west"]) else "left"


def light_of(ph):
    """The photograph's light in plain words, from the lightness of the top row of its look (grade.py): low, soft or
    bright, black and white for a black-and-white photograph."""
    lk = ph.get("look")
    if not lk:
        return "in the light the photograph was taken in"
    top_ = statistics.fmean(lk["light"][0])
    return f"in {'low' if top_ < LIGHT[0] else 'bright' if top_ > LIGHT[1] else 'soft'}{' black and white' if ph.get('gray') else ''} light"


def stand_in(c, W):
    """The layered move the film makes on a card's still photograph in its clip's place, in one sentence from the card:
    the ground below the photograph's line pushes toward the focus faster than the distance at the line, the picture
    drifts along the line the way the dot came, then the camera makes the stop's travel out."""
    deg = round(math.degrees(math.atan(c["slope"])))
    line_ = "level line" if deg == 0 else f"line, which {'falls' if deg > 0 else 'rises'} {abs(deg)} degree{'s' * (abs(deg) != 1)} to the east,"
    side = "left" if c["focus"][0] < W / 3 else "right" if c["focus"][0] > 2 * W / 3 else "middle"
    return (f"the ground below the photograph's {line_} pushes toward the focus at the {side} of the frame faster than the "
            f"distance at the line, and the picture drifts {'west' if c['west'] else 'east'} along the line; then the camera "
            f"{OUT[c['travel']]}")


def clips(board, photos):
    """The generated shots the film would carry, one per stop, each a shot for the platform's image-to-video model: its
    use (the hook's world on the first stop, the texture between chapters on a stop reached across a leap or left across
    one, a still brought to life on the rest); its subject and light as the person reading the cast wrote them for the
    photograph (`about`, else the person's line or the place in the photograph's own light), or for a texture the
    place's material close up (`texture`, else the place's water, stone and ground in that light, with no person and no
    landmark); its lens and height (`camera`, else the photograph's own); its camera move, the beat's own move in camera
    words (CAMERA) unless one of the two shots before already asked for it, else the move its photograph's line and focus
    call for, and for a texture a close camera of its own, each texture the next of TEXTURE; and a seamless loop.
    clips.py list writes each as one prompt at its beat's length. `stand_in` names the layered move the film makes in a
    clip's place when no clip has arrived."""
    cards, W = board["route"]["cards"], board["route"]["W"]
    out, before, recent, grazed = [], None, [], 0
    for k, (c, b) in enumerate(zip(cards, board["beats"])):
        ph = photos.get(c["file"]) or {}
        leap = c["travel"] == "leap" or (k > 0 and cards[k - 1]["travel"] == "leap")
        use = "the hook's world" if k == 0 else "texture between chapters" if leap else "a still brought to life"
        light = light_of(ph)
        if use == "texture between chapters":
            written = ph.get("texture")
            subject = written or f"the water, stone and ground of {c['name']} close up {light}, with no person and no landmark in the frame"
        else:
            written = ph.get("about")
            subject = written or (f"{c['said']}, in {c['name']}, {light}" if c.get("said") else f"{c['name']}, as the photograph shows it, {light}")
        if use == "texture between chapters":
            move, words = "texture", TEXTURE[grazed % len(TEXTURE)]
            grazed += 1
        elif b.get("move") in CAMERA and CAMERA[b["move"]] not in recent:
            move, words = b["move"], CAMERA[b["move"]].format(side=side_of(c, W))
        else:
            move, words = clip_move(c, W, before)
        before = move
        recent = (recent + [CAMERA.get(move)])[-2:]
        out.append({"id": f"{k:02d}", "beat": c["id"], "role": use, "seconds": 2.0 if k == 0 else 1.0 if c["kind"] == "quick" else 1.5,
                    "image": c["file"], "subject": subject,
                    "camera": ph.get("camera") or "the lens feel and the camera height the photograph was taken with",
                    "move": words, "from": move, "read": bool(written and ph.get("camera")), "stand_in": stand_in(c, W)})
    return out


def frames(board, fps=FPS):
    """The board with each beat's frames at the board's tempo (storyboard.py snap sets it from the track): every beat
    starts on the frame nearest its musical beat, so the cuts stay on the sound cues at any tempo."""
    pulse = fps * 60 / board["bpm"]
    t = 0.0
    for b in board["beats"]:
        b["frames"] = round((t + 4 * b["bars"]) * pulse) - round(t * pulse)
        t += 4 * b["bars"]
    return board
