"""The best nine's story, drawn in any style card: the nine they love most as a countdown with no number on screen.

The film opens on the first of the countdown (taste.json `order`, the strongest first; the likes when it names none):
the photograph full in the frame and their title over it. Then the nine, from the ninth of that order to the first, one
beat each, every beat in a layout of its own (LAYOUTS: never one layout twice), the photograph laid in the layout's box
by its focus, their own caption line and its day set in the card's faces beside it or over it. Then the nine as they
are posted, a three by three grid, the first at its top left, with the year and the handle; the reel's and the wide's
with the ask, the square's the grid alone. The film ends on the card's closer shape with their title and their promise.

Each beat's move comes from what the beat shows (its form, the photograph's shape, whether it carries words, the peak,
people in it) within the card's allowlist (`pick`), and the cut into it the same way. A move that frames the picture
in a window of its own (any move whose file draws a Window) is that beat's layout, so it runs at most once in the nine;
the photograph behind it is placed by its focus, so the window frames its subject, and a move that writes a label
writes the caption on its print. On every other beat the board sets the caption and the day in the card's faces and
hands the move no words, so a move whose only act is to set words is chosen there only when the card has no other.
A move that flies the photograph in before it lands (any move whose file times itself by the shared arrival: the
tunnel of their photographs, the wall that swings flat) takes the whole frame until it hands it back, so it plays on the
top of the countdown (one the card fits to the wall on the grid) and nowhere else, never on the hook, and the beat's
words stand only once it has handed the frame back; the top of the countdown holds that much longer (timing).

Each piece holds as long as its post asks (reads): a captioned post for its words, a wordless one less, a post that
repeats a photograph or a line already shown least, and the first a quarter longer than the most any of them asks;
the holds share what the asked length leaves after the hook, the grid and the closer, so the film runs the length asked
(timing). taste.json `beats` changes one beat: `{"piece-3": {"layout": "band", "move": "tape-slap", "seconds": 3}}`."""
import math
import re
from pathlib import Path

import compose
import palette
from compose import cased, fit_size, ink, text_box, text_width, wrap_measured

BPM = 120
# the musical beats the hook runs; the closer runs from a downbeat to the film's end
HOOK_BEATS = 4
# the wall: its tiles land TILE beats apart, each in LANDS beats, the first standing from the cut (all nine standing
# from the cut under a move that flies a photograph in, which lands every tile in its cell); once the ninth has landed
# the whole wall holds WALL seconds clear of the cut out of it, whose half window is at most EDGE beats. A film that
# would leave its pieces less than ROOMY times their shortest runs the wall SHORT_NINE beats.
TILE, LANDS, WALL, EDGE, SHORT_NINE, ROOMY = 0.2, 0.5, 2.0, 1.2, 4, 1.25
# the grid's middle tile, where a move that flies a photograph in onto the grid lands it
MIDDLE = 4
# the closer settles SETTLE beats after it lands, where the picture and the sound stop together, then holds still at
# least HOLD seconds; it takes an eighth of the film when that is longer
SETTLE, HOLD = 2.0, 2.5
# a piece runs at least SHORTEST beats; what a post asks to be read, seconds: a captioned one CAPTIONED and A_WORD a
# word up to LONGEST_READ, a wordless one WORDLESS, one that repeats a photograph or a line shown before it REPEAT; the
# first holds FIRST times the most any of the nine asks
SHORTEST = 2.0
CAPTIONED, A_WORD, LONGEST_READ, WORDLESS, REPEAT = 0.6, 0.15, 2.4, 0.5, 0.3
FIRST = 1.6
# two photographs are the same scene when their difference hashes (picks.json `look`) differ in at most SAME bits
SAME = 10
TEMPO = (60, 200)
# a piece's photograph holds clean for up to CLEAN beats before its words land, they have landed LAND beats later, and
# they stand their read before the cut, LEAVE beats before the next beat
CLEAN, LAND, LEAVE = 0.6, 1.0, 0.6
# the ways a caption may enter in each card's type, its own first: each caption takes the first of them that neither
# of the two captions before it took (the first that the one before it did not, on a card with two), so no two
# captions in a row arrive the same way
ENTRANCES = {"type": ("type", "slam", "rise"), "cut": ("cut", "rise", "slam"), "fade": ("fade", "rise"),
             "rise": ("rise", "fade", "slam"), "slam": ("slam", "rise", "cut")}
# a piece's hold is a whole number of GRID-ths of a beat, so every cut lands on the music's grid, where the effects land
GRID = 4
# a move that flies the photograph in hands the frame back this many seconds after it lands (the shared arrival's own
# fade, arrivalOf), lands within this share of its room, and leaves this many seconds before the pull
HAND_BACK, LAND_SHARE, BEFORE_PULL = 0.38, 0.55, 0.12
# the hook event (the title landing) at this beat
HOOK_AT = 0.25
# px between the grid's tiles
GUT = 12
# the small type, a caption line at most, the title at most, and the year on the grid, px, in each format
SMALL = {"reel": 34, "square": 30, "wide": 32}
HEAD = {"reel": 104, "square": 84, "wide": 96}
TITLE = {"reel": 150, "square": 120, "wide": 132}
CLOSER_YEAR = {"reel": 180, "square": 0, "wide": 300}
# the least px a caption line is set at, in each format
FLOOR = {"reel": 40, "square": 34, "wide": 36}
# a photograph whose box meets the frame's edge reaches past it by this share, so a move that turns the camera never
# shows the frame's edge
OVER = 0.07
MOVES_DIR = compose.SKILL / "motion" / "system" / "moves" / "move"


def _source(move):
    f = MOVES_DIR / f"{move}.tsx"
    return f.read_text() if f.is_file() else ""


def arrives(move):
    """The seconds a move that flies the photograph in asks of the shared arrival before it lands (its `arrivalOf(p, s)`),
    or None for a move that does not take the frame."""
    m = re.search(r"arrivalOf\(\s*p\s*(?:,\s*([\d.]+))?\s*\)", _source(move))
    return (float(m.group(1)) if m.group(1) else 1.0) if m else None


def flight(move, beats, bpm):
    """(lands, hands back) in beats from the cut for a move that flies the photograph in on a beat of `beats` beats at
    `bpm`, the way the shared arrival times it (arrivalOf: it lands within the first part of a short beat and has gone
    before the pull, LEAVE beats before the cut out); (0, 0) for any other move."""
    want = arrives(move)
    if want is None:
        return 0.0, 0.0
    per = 60 / bpm
    room = max(0.3, (beats - LEAVE) * per)
    land = min(want, room * LAND_SHARE)
    return round(land / per, 3), round(min(land + HAND_BACK, room - BEFORE_PULL) / per, 3)


def on_box(move):
    """True when the move reads the photograph's box (the beat's `box`): it crops, mats or marks the photograph where the
    board laid it, so it plays on any layout."""
    return "beat.box" in _source(move)


def frames_picture(move):
    """True when the move draws the picture in a window of its own whatever the beat: the window is the beat's layout."""
    return "<Window" in _source(move) and not on_box(move)


def writes_unseen(move, frame, title=False):
    """True when a framing move writes its words beside its window outside the format's safe area (the wide margin
    under a crop): the reel's interface covers them there and the square and the wide cut them off, so the board sets
    those words itself, at its own sizes, and hands the move none. `title`: the beat is the hook."""
    if not frames_picture(move) or not (sets_words(move) or sets_label(move)):
        return False
    _, y0, _, y1 = frame.safe
    return any(m[1] < y0 or m[3] > y1 for m in window(move, frame.W, frame.H, frame.safe, title)[1])


def covers(move):
    """True when the move covers part of the frame with the card's ground: a window, or a mat on the photograph's box
    (or, on a beat with no photograph's box, a window in the card's margins)."""
    src = _source(move)
    return "<Window" in src or "<Mat" in src


def mats(move):
    """True when the move mats the photograph's box: it covers part of the box with the card's ground."""
    return on_box(move) and "<Mat" in _source(move)


def sets_words(move):
    """True when the move sets the beat's words itself (its text reads the words before the label)."""
    return bool(re.search(r"beat\.words\s*\|\|\s*beat\.label", _source(move)))


def sets_label(move):
    """True when the move sets the beat's label (the day) itself."""
    return "beat.label" in _source(move)


def still(move):
    """True when the move puts no push and no effect on the picture: once its overlay settles, the beat holds a still
    composition."""
    return not re.search(r"\b(nudge|fx)\s*:", _source(move))


def only_says(move):
    """True when all the move does is set words: no window, no mark on the photograph, no push on the picture, no
    effect. On a beat the card or the board lays, the move is handed no words, so such a move would leave the beat
    still."""
    return sets_label(move) and not frames_picture(move) and not on_box(move) and still(move)


def window(move, W, H, safe=None, title=False):
    """The window [x0, y0, x1, y1] px a framing move shows the picture through once it has come to rest (for a crop that
    moves, the part it shows throughout), and the boxes
    the move writes its words in beside it, as its file draws them. `safe` is the format's safe area [x0, y0, x1, y1]
    (absent: the whole frame) and `title` whether the beat is the hook, for a move that lays itself out from them."""
    px = lambda v: v * W / 1080
    if move == "white-space-crop":
        side = px(120)
        return (side, 0.16 * H, W - side, 0.74 * H), [(side, 0.74 * H, W - side, 0.74 * H + px(150))]
    if move == "page-drift":
        return (px(70), 0.12 * H, W - px(70), 0.8 * H), []
    if move == "polaroid-drop":
        # the instant print laid out from the safe area: no taller than it, standing in the middle of its height and
        # over the middle of its width; on the hook it is as wide as the frame allows (polaroid-drop.tsx)
        sx0, sy0, sx1, sy1 = safe or (0, 0, W, H)
        w = min(W * (0.96 if title else 0.78), (sy1 - sy0) / 1.31)
        h, foot, rim = 1.05 * w, 0.26 * w, w * (0.035 if title else 0.05)
        y = sy0 + max(0.0, (sy1 - sy0 - 1.31 * w) / 2)
        x = min(W - w / 2, max(w / 2, (sx0 + sx1) / 2)) - w / 2
        return (x + rim, y + rim, x + w - rim, y + h - rim), [(x, y + h, x + w, y + h + foot)]
    if move == "tape-slap":
        return (px(90), 0.16 * H, W - px(90), 0.78 * H), []
    return (0, 0, W, H), []


def writes(move, box, W):
    """Where a move that marks the photograph draws on it or beside it, [x0, y0, x1, y1] px, for the photograph's `box`
    [x, y, w, h] (doodle-draw-on.tsx, sticker-pop.tsx, rule-draw.tsx, and the moves that mat it); None for a move that
    draws nothing there. A sticker may take either top corner, so the band spans both, and the board's own words keep
    out of it; the doodle is given the same band, and rings the photograph's focus, keeping its loop off the words."""
    px = lambda v: v * W / 1080
    x, y, w, h = box
    if move == "doodle-draw-on":
        r = px(110)
        return (x - 2.1 * r, y - 2.0 * r, x + w + 2.1 * r, y + 1.2 * r)
    if move == "sticker-pop":
        d = min(px(300), 0.36 * w)
        return (x - d, y - 0.5 * d, x + w + d, y + 0.7 * d)
    if move == "rule-draw":
        return (x, y - px(56), x + w, y + h + px(30))
    if "<Mat" in _source(move) or move == "cell-reveal":
        # a move that mats part of the photograph in the card's ground would cover words set on the photograph
        return (x, y, x + w, y + h)
    return None


# the layout a move reads best over: rule-draw draws its rule over the photograph's head, which the small layout keeps
# inside the frame with the words well below; long-fade-title veils the whole picture
PREFERS = {"rule-draw": "small", "long-fade-title": "bleed"}
# the moves that open on a covered frame and lift the cover off the picture (cell-reveal the card's ground, bars-open
# the letterbox bars): the cut into one is the card's hard cut, since a wipe, a dissolve or the bars closing into a
# cover would show the cover twice, an empty frame between two pictures
OPENS_ON_GROUND = {"cell-reveal", "bars-open"}


def cut_into(c, move, cut):
    """The cut into a beat under `move`: `cut`, or the card's hard cut when the move opens on the ground."""
    hard = [t["id"] for t in c["transitions"] if t["id"] == "hard-cut"]
    return hard[0] if move in OPENS_ON_GROUND and hard else cut


# the layouts of a piece: where its photograph lies and where its words stand, each a function of the frame's safe
# area; `fits` names the photographs and beats each suits best
LAYOUTS = {
    "card": {"fits": set()},
    "bleed": {"fits": {"peak", "wordless", "landscape"}},
    "high": {"fits": {"landscape", "words"}},
    "low": {"fits": {"landscape", "words", "place"}},
    "inset": {"fits": {"portrait", "people"}},
    "split": {"fits": {"portrait", "words"}},
    "offset": {"fits": {"portrait", "people"}},
    "square": {"fits": {"wordless", "portrait", "landscape"}},
    "small": {"fits": {"words"}},
    "band": {"fits": {"landscape", "place", "wordless"}},
}


def geometry(name, frame, photo=None, landscape=False):
    """Layout `name` in `frame`: {photo: [x, y, w, h] px, zone: [x0, y0, x1, y1] where the words stand, valign, align,
    over (the words stand on the photograph), square (the post's own square crop)}. "card" is the style card's own photo
    layout (`photo`, the board system's): its picture box in shares of the frame, its line box in shares of the safe
    area, the line set from the box's top; a `landscape` photograph on a tall frame takes the card's landscape box and line
    box, so it fills the frame's foot instead of leaving bare ground under it."""
    W, H = frame.W, frame.H
    x0, y0, x1, y1 = frame.safe
    aw, ah = x1 - x0, y1 - y0
    g = round(0.03 * min(aw, ah))
    # type stays inside the safe area, a photograph only inside the frame's margin: under a tall frame's caption band
    # a picture laid at the foot runs on to that margin instead of stopping at the band over bare ground
    foot = H - x0 if H - y1 > 0.2 * H else y1
    if name == "card":
        land = photo.get("landscape") if landscape else None
        bx, by, bw, bh = land["box"] if land else photo["picture"]["box"]
        lx, ly, lw, lh = land["line"] if land else photo["line"]["box"]
        box = [bx * W, by * H, bw * W, bh * H]
        zone = [x0 + lx * aw, y0 + ly * ah, x0 + (lx + lw) * aw, y0 + (ly + lh) * ah]
        over = box[0] <= zone[0] and box[1] <= zone[1] and box[0] + box[2] >= zone[2] and box[1] + box[3] >= zone[3]
        if not over and zone[1] < box[1] < zone[3]:
            # a line box drawn for a tall frame reaches into the picture on a wide one: it ends above the picture
            zone[3] = box[1] - g
        return {"photo": box, "zone": zone, "valign": "top", "align": "middle" if photo["line"]["align"] == "center" else "start",
                "over": over}
    if name == "bleed":
        return {"photo": [0, 0, W, H], "zone": [x0, y0 + 0.5 * ah, x1, y1], "valign": "bottom", "align": "start", "over": True}
    if foot > y1 and name in ("high", "small", "band"):
        # a tall frame keeps its words above its caption band, so a picture set over the words would leave the frame's
        # lower third bare paper: here the words stand at the head and the picture fills the picture area under them,
        # its edges on the card's grid rows, a small picture centred in it
        a0, a1 = rows(frame, photo, y0 + 0.36 * ah), rows(frame, photo, y1 + 0.5 * (foot - y1))
        if name == "high":
            return {"photo": [0, a0, W, a1 - a0], "zone": [x0, y0, x1, a0 - g], "valign": "bottom", "align": "start"}
        if name == "small":
            w = 0.68 * aw
            h = min(1.25 * w, a1 - a0)
            return {"photo": [(W - w) / 2, a1 - h, w, h], "zone": [x0, y0, x1, a1 - h - g], "valign": "bottom", "align": "start", "big": True}
        h = 0.5 * (a1 - a0)
        return {"photo": [0, a1 - h, W, h], "zone": [x0, y0, x1, a1 - h - g], "valign": "bottom", "align": "start"}
    if name == "high":
        b = y0 + 0.58 * ah
        return {"photo": [0, 0, W, b], "zone": [x0, b + g, x1, y1], "valign": "top", "align": "start"}
    if name == "low":
        t = y0 + 0.42 * ah
        return {"photo": [0, t, W, H - t], "zone": [x0, y0, x1, t - g], "valign": "bottom", "align": "start"}
    if name == "inset":
        t = y1 - 0.64 * ah
        return {"photo": [x0, t, aw, foot - t], "zone": [x0, y0, x1, t - g], "valign": "bottom", "align": "start"}
    if name == "split":
        c = x0 + 0.44 * aw
        return {"photo": [c, 0, W - c, H], "zone": [x0, y0, c - g, y1], "valign": "middle", "align": "start"}
    if name == "offset":
        l, t = x0 + 0.22 * aw, y1 - 0.6 * ah
        return {"photo": [l, t, W - l, foot - t], "zone": [x0, y0, x1, t - g], "valign": "top", "align": "end"}
    if name == "square":
        side = min(W - 2 * x0, foot - y0 - 0.34 * ah) if foot > y1 else min(aw, 0.66 * ah)
        return {"photo": [(W - side) / 2, foot - side, side, side], "zone": [x0, y0, x1, foot - side - g], "valign": "bottom", "align": "middle",
                "square": True}
    if name == "small":
        w = 0.44 * aw
        h = min(w * 1.25, 0.46 * ah)
        return {"photo": [x1 - w, y0, w, h], "zone": [x0, y0 + h + g, x1, y1], "valign": "bottom", "align": "start", "big": True}
    if name == "band":
        t, h = y0 + 0.3 * ah, 0.36 * ah
        return {"photo": [0, t, W, h], "zone": [x0, t + h + g, x1, y1], "valign": "top", "align": "start", "above": [x0, y0, x1, t - g]}
    raise SystemExit(f"no layout named {name!r} (there are: {', '.join(LAYOUTS)})")


def rows(frame, photo, y):
    """The card's grid row line nearest `y` px (the rows of `photo`'s grid, as the film draws them); `y` itself when the
    card draws no grid."""
    grid = (photo or {}).get("grid")
    if not grid:
        return y
    m = grid["margin"] * frame.W
    return min((m + i * (frame.H - 2 * m) / grid["rows"] for i in range(grid["rows"] + 1)), key=lambda r: abs(r - y))


def framed(move, frame):
    """The geometry of a beat whose move frames the picture: the photograph behind the move's window, seen through it;
    the words in the band of the safe area the window and the move's own marks leave that holds them largest, or on the
    window's foot over a shade when no band holds them."""
    W, H = frame.W, frame.H
    x0, y0, x1, y1 = frame.safe
    (wx0, wy0, wx1, wy1), marks = window(move, W, H, frame.safe)
    top = max([wy0] + [m[1] for m in marks if m[1] < wy0 + 1])
    foot = max([wy1] + [m[3] for m in marks])
    bands = [b for b in ([x0, y0, x1, min(top, wy0) - 16], [x0, foot + 16, x1, y1]) if b[3] - b[1] >= 1.6 * FLOOR[frame.name]]
    g = {"photo": [0, 0, W, H], "window": [round(wx0, 1), round(wy0, 1), round(wx1 - wx0, 1), round(wy1 - wy0, 1)], "valign": "middle",
         "align": "start", "bands": bands}
    g["zone"] = [max(x0, wx0 + 24), max(y0, wy0 + 0.45 * (wy1 - wy0)), min(x1, wx1 - 24), min(y1, wy1 - 24)]
    g["foot"] = dict(zone=g["zone"], valign="bottom", over=True)
    return g


# ------------------------------------------------------------------ the photograph in its box
def overscan(box, frame):
    """The box reaching OVER past every frame edge it meets."""
    x, y, w, h = box
    ox, oy = OVER * frame.W, OVER * frame.H
    l = ox if x <= 0 else 0
    t = oy if y <= 0 else 0
    r = ox if x + w >= frame.W else 0
    b = oy if y + h >= frame.H else 0
    return [round(x - l, 1), round(y - t, 1), round(w + l + r, 1), round(h + t + b, 1)]


def through(p, win, frame, most=1.6):
    """The photograph's box [x, y, w, h] behind a move's window `win` [x, y, w, h]: the whole picture at its own
    proportions, covering the window and the reach past each of its sides (the turn a print lands with), placed so its
    focus stands at the window's middle; it grows up to `most` times the size that only covers, then sits as near as
    that size allows. The move covers the frame around its window with the card's ground, so no more of the picture is
    ever seen, and a print that drops in carries the picture down with it (Film.tsx)."""
    a = p["aspect"]
    ox, oy = OVER * frame.W, OVER * frame.H
    X0, Y0, X1, Y1 = win[0] - ox, win[1] - oy, win[0] + win[2] + ox, win[1] + win[3] + oy
    cx, cy = win[0] + win[2] / 2, win[1] + win[3] / 2
    fx, fy = (min(0.99, max(0.01, v)) for v in p["focus"])
    base = max(X1 - X0, (Y1 - Y0) / a)
    w = min(most * base, max(base, (cx - X0) / fx, (X1 - cx) / (1 - fx), (cy - Y0) / (fy * a), (Y1 - cy) / ((1 - fy) * a)))
    h = w * a
    x = min(X0, max(X1 - w, cx - fx * w))
    y = min(Y0, max(Y1 - h, cy - fy * h))
    return [round(x, 1), round(y, 1), round(w, 1), round(h, 1)]


def cover(p, box, square=False):
    """The part of the photograph [u0, v0, u1, v1] (shares of its width and height, from its top left) that fills `box`
    at its own proportions, centered on its focus; the post's square crop when `square`."""
    a = p["aspect"]
    if square and p.get("crop"):
        x, y, s = p["crop"]
        return [round(x, 4), round(y, 4), round(x + s, 4), round(min(1, y + s / a), 4)]
    r = box[3] / max(1, box[2])
    fx, fy = p["focus"]
    if a > r:
        vh = r / a
        v0 = max(0.0, min(1 - vh, fy - vh / 2))
        return [0, round(v0, 4), 1, round(v0 + vh, 4)]
    uw = a / r
    u0 = max(0.0, min(1 - uw, fx - uw / 2))
    return [round(u0, 4), 0, round(u0 + uw, 4), 1]


def photo_layer(p, box, frame, at=0.0, square=False, beats=0.5):
    b = overscan(box, frame)
    return {"kind": "Photo", "photo": {"file": p["file"], "aspect": p["aspect"]}, "box": b, "uv": cover(p, b, square), "focus": p["focus"],
            "owner": p["rank"], "at": at, "beats": beats}


# ------------------------------------------------------------------ type
def roles(S):
    """The color words stand in on the ground, the color of their day, and on a photograph the words' color and the
    shade under them: each the role of the card's palette that reads best."""
    c = S["colors"]
    rgb = {k: palette.hex_rgb(v) for k, v in c.items() if isinstance(v, str) and v.startswith("#")}
    on = max(("ink", "paper"), key=lambda k: palette.contrast(rgb[k], rgb["bg"]))
    day = "accent" if palette.contrast(rgb["accent"], rgb["bg"]) >= 3 else on
    light = max(("ink", "paper", "bg"), key=lambda k: palette.lum(rgb[k]))
    dark = min(("ink", "paper", "bg"), key=lambda k: palette.lum(rgb[k]))
    return {"on": on, "day": day, "over": light, "shade": dark}


def line_pitch(S, face, size):
    return size * max(1.0, S["display" if face == "display" else "text"].get("lineHeight", 1.1))


def block(S, frame, zone, caption, day, valign="top", align="start", big=False, color="ink", day_color="ink", head=None, above=None,
          face="display", day_face="text", day_size=None):
    """The caption in the display face broken into at most three lines that fit the zone, with the day small in the
    text face over it (or in `above` when given); [] when nothing fits at the floor. Lines stand on their baselines,
    each a line pitch under the last, and the block's ink, measured, stands inside the zone where `valign` puts it."""
    x0, y0, x1, y1 = zone
    width, room = x1 - x0, y1 - y0
    small = SMALL[frame.name]
    ax = {"start": x0, "middle": (x0 + x1) / 2, "end": x1}[align]
    anchor = {"start": {}, "middle": {"anchor": "middle"}, "end": {"anchor": "end"}}[align]
    dl = None
    if day:
        dl = {"text": cased(S, day_face, day), "size": round(day_size or small * 1.15), "face": day_face, "color": day_color, "x": round(ax, 1),
              "y": 0.0, **anchor}
        if text_width(S, dl) > width:
            return []
    text = cased(S, face, caption) if caption else ""

    def at(size):
        """The block at `size` with its first ink at 0, and its ink's height; None when the caption does not break into
        three lines that fit the width."""
        out, y = [], 0.0
        if dl is not None and not above:
            d = dict(dl)
            d["y"] = ink(S, d)[0]
            out.append(d)
            y = d["y"] + dl["size"] * 1.1
        if text:
            got = wrap_measured(S, {"text": text, "size": size, "face": face}, width, 3)
            if not got:
                return None
            pitch = line_pitch(S, face, size)
            first = {"text": got[0], "size": size, "face": face, "x": round(ax, 1), "y": 0.0, **anchor}
            base = y + ink(S, first)[0]
            out += [dict(first, text=t, color=color, y=base + i * pitch) for i, t in enumerate(got)]
        boxes = [text_box(S, ln, ink=True) for ln in out]
        return out, max(b[3] for b in boxes) - min(b[1] for b in boxes), min(b[1] for b in boxes)

    size = round((head or HEAD[frame.name]) * (1.35 if big else 1))
    while True:
        r = at(size)
        if r and r[1] <= room:
            break
        if size <= FLOOR[frame.name] or not text:
            return []
        size -= 2
    out, tall, top_ink = r
    top = {"top": y0, "middle": y0 + (room - tall) / 2, "bottom": y1 - tall}[valign] - top_ink
    for ln in out:
        ln["y"] = round(ln["y"] + top, 1)
    if dl is not None and above:
        d = dict(dl, x=round({"start": above[0], "middle": (above[0] + above[2]) / 2, "end": above[2]}[align], 1))
        d["y"] = round(above[3] - ink(S, d)[1] - 4, 1)
        out.insert(0, d)
    return out


def shade_of(lines, S, frame, color, strength=0.6, within=None):
    """The shade under words that stand on a photograph: clear well above their ink, darkening to them and held to the
    photograph's foot, across the photograph's width (`within`, its [x, y, w, h]; the whole frame when not given), so
    the words read on it at its densest and no edge of it stands on the picture or past it."""
    x, y, w, h = within or [0, 0, frame.W, frame.H]
    boxes = [text_box(S, ln, ink=True) for ln in lines]
    y0, y1 = min(b[1] for b in boxes), max(b[3] for b in boxes)
    pad = 0.5 * (y1 - y0) + 80
    top, bot = max(0.0, y, y0 - pad), min(float(frame.H), y + h)
    left, right = max(0.0, x), min(float(frame.W), x + w)
    return {"kind": "Shade", "box": [round(left, 1), round(top, 1), round(right - left, 1), round(bot - top, 1)], "color": color,
            "strength": strength}


# ------------------------------------------------------------------ timing
def reads(story):
    """The seconds each post asks to be read, in film order: a post whose photograph or caption line the film has
    already shown REPEAT, a captioned one CAPTIONED and A_WORD a word up to LONGEST_READ, a wordless one WORDLESS."""
    out, looks, said = [], [], set()
    for p in story:
        line = " ".join((p.get("caption") or "").lower().split())
        look = p.get("look")
        if (line and line in said) or (look and any(bin(int(look, 16) ^ int(o, 16)).count("1") <= SAME for o in looks)):
            out.append(REPEAT)
        else:
            out.append(min(LONGEST_READ, CAPTIONED + A_WORD * len(line.split())) if line else WORDLESS)
        looks += [look] if look else []
        said |= {line} if line else set()
    return out


def timing(story, seconds, bpm=BPM, asked=None, moves=None, wall=None):
    """The film's beats at `bpm` for a film of `seconds`: {holds, reads, nine, grid, end}, the beats each piece holds in
    film order, what each asks to be read, the beat the grid starts on, the beats it runs and the film's end; None when the nine do not fit.
    `asked` maps a piece's id to the seconds taste.json `beats` gives it; the others share what is left. `moves` are
    the pieces' moves in film order: a move that flies the photograph in holds its flight, then its words' landing,
    read and leaving. `wall` is the grid's move: one that flies a photograph in holds its flight before the other tiles
    land. Every hold is a whole number of GRID-ths of a beat."""
    end = seconds * bpm / 60
    # the grid's tiles land one after another; a wall's move that flies a photograph in lands all nine, and the wall is
    # whole once it hands the frame back
    tiles = (arrives(wall) + HAND_BACK) * bpm / 60 if wall and arrives(wall) else TILE * (len(story) - 1) + LANDS
    for grid, roomy in ((math.ceil(tiles + WALL * bpm / 60 + EDGE), ROOMY), (SHORT_NINE, 1)):
        room = math.floor(end - HOOK_BEATS - grid - max(SETTLE + HOLD * bpm / 60, end / 8))
        if room >= roomy * SHORTEST * len(story):
            break
    if not TEMPO[0] <= bpm <= TEMPO[1] or room < SHORTEST * len(story):
        return None
    r = reads(story)
    want = [CLEAN + LAND + LEAVE + x * bpm / 60 for x in r]
    most = max(want)
    want = [FIRST * most if p.get("pick", p["rank"]) == 1 else w for p, w in zip(story, want)]
    fixed = {i: max(SHORTEST, s * bpm / 60) for i, p in enumerate(story) for s in [(asked or {}).get(f"piece-{p['rank']}")] if s}
    # a beat whose move flies the photograph in holds its flight until the frame is handed back, then its words'
    # landing, their read and their leaving, on the grid
    for i, m in enumerate(moves or []):
        if m and arrives(m):
            fly = ((arrives(m) + HAND_BACK) * bpm / 60 + LAND + r[i] * bpm / 60 + LEAVE)
            fixed[i] = max(fixed.get(i, 0.0), math.ceil(fly * GRID) / GRID)
    free = [i for i in range(len(story)) if i not in fixed]
    left = room - sum(fixed.values())
    if left < SHORTEST * len(free):
        return None
    past = {i: max(0.0, want[i] - SHORTEST) for i in free}
    k = (left - SHORTEST * len(free)) / (sum(past.values()) or 1)
    on_grid = lambda x: round(x * GRID) / GRID
    raw = [fixed[i] if i in fixed else SHORTEST + k * past[i] for i in range(len(story))]
    holds = [on_grid(x) for x in raw]
    last = free[-1] if free else len(story) - 1
    # on the grid a repeat still holds shortest and a wordless post shorter than any captioned one, by a grid step
    rank = [0 if x == REPEAT else 1 if x == WORDLESS else 2 for x in r]
    for step in (1, 2):
        under = [holds[i] for i in free if rank[i] < step]
        for i in free:
            if i != last and rank[i] == step and under:
                holds[i] = max(holds[i], max(under) + 1 / GRID)
    holds[last] = on_grid(room - sum(h for i, h in enumerate(holds) if i != last))
    return {"holds": holds, "reads": r, "nine": HOOK_BEATS + room, "grid": grid, "end": end}


def fits(posts, seconds, bpm=BPM, asked=None):
    """The nine fit a film of `seconds` at `bpm`."""
    return timing(film_order(posts), seconds, bpm, asked) is not None


def film_order(posts):
    """The nine in the film's order: the ninth of the countdown first, the first last."""
    return sorted(posts, key=lambda p: -p.get("pick", p["rank"]))


# ------------------------------------------------------------------ moves and layouts
def tags_of(p, captioned):
    w, h = 1, p["aspect"]
    t = {"photo", "portrait" if h > w * 1.05 else "landscape", "words" if captioned else "wordless"}
    if p.get("pick", p["rank"]) == 1:
        t.add("peak")
    if p.get("people"):
        t.add("people")
    if p.get("place"):
        t.add("place")
    return t


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once, and each time it has
    already run in the film costs it one), then the one used least, then the card's order. An option `avoid` names (the
    previous beat's, or the next beat's when that beat has no other) is never picked while another exists."""
    pool = [o for o in options if o["id"] not in avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"])) - used.get(o["id"], 0)
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def inside(name, frame):
    """True when layout `name`'s picture box lies inside `frame`: a mat on a box that runs off the frame leaves a bare
    stripe at the frame's edge."""
    x, y, w, h = geometry(name, frame)["photo"]
    return x > 0 and y > 0 and x + w < frame.W and y + h < frame.H


def bare_foot(name, frame):
    """True when layout `name` stops its picture at a tall frame's caption band, leaving bare ground under it."""
    y1 = frame.safe[3]
    return frame.H - y1 > 0.2 * frame.H and sum(geometry(name, frame)["photo"][1::2]) <= y1


def layout_for(tags, free, frame=None, move=None):
    """The free layout that suits the beat best, then the first free in LAYOUTS' order. A move that mats the
    photograph's box takes a box inside the frame; a layout that leaves bare ground under its picture, or whose words
    would stand where the move draws beside the photograph (`writes`), only when every free one would."""
    names = [n for n in LAYOUTS if n in free and n != "card"]
    if frame:
        if move and mats(move):
            names = [n for n in names if inside(n, frame)] or names
        names = [n for n in names if not bare_foot(n, frame)] or names
    if move and frame:
        def clear_of(n):
            g = geometry(n, frame)
            w = writes(move, g["photo"], frame.W)
            return w is None or not any(_meets(z, w) for z in [g["zone"]] + ([g["above"]] if g.get("above") else []))
        names = [n for n in names if clear_of(n)] or names
    return max(names, key=lambda n: (len(tags & LAYOUTS[n]["fits"]), -names.index(n)))


def choose(c, story, levers, frame, prev=None, then=()):
    """Each piece's move, the cut into it, and its layout, in film order: a lever's own where taste.json `beats` names
    one, else the move picked from the piece's content (a framing move at most once in the nine, a move that flies the
    photograph in on the top of the countdown alone, and never one the card fits to the wall, which the grid right after
    it takes; the last piece clear of the moves `then` names, which the beat after the nine takes) and the free layout that suits it best, clear of where the move writes; a framing move is its
    own layout."""
    used, cuts, taken, out = {}, {}, set(), []
    # the top of the countdown is kept a large picture: inset for a portrait, low for a landscape, which no other piece
    # takes unless its lever names it
    peak = next((p for p in story[1:] if p.get("pick", p["rank"]) == 1 and not (levers.get(f"piece-{p['rank']}") or {}).get("layout")), None)
    keep = ("inset" if "portrait" in tags_of(peak, False) else "low") if peak else None
    for p in story:
        bid = f"piece-{p['rank']}"
        lv = levers.get(bid) or {}
        tags = tags_of(p, bool(p.get("caption")))
        allowed = compose.ids(c, "moves")
        if lv.get("move") and lv["move"] not in allowed:
            raise SystemExit(f"taste.json beats.{bid}.move is {lv['move']!r}, which is not a move of {c['id']} ({', '.join(allowed)})")
        if lv.get("layout") and lv["layout"] not in LAYOUTS:
            raise SystemExit(f"taste.json beats.{bid}.layout is {lv['layout']!r}; the layouts are {', '.join(LAYOUTS)}")
        # the first piece the countdown shows stands in the card's own photo layout, so the look is set at once
        home = not out and not lv.get("layout") and not (lv.get("move") and frames_picture(lv["move"]))
        if lv.get("move"):
            move = lv["move"]
            used[move] = used.get(move, 0) + 1
        else:
            opts = [o for o in c["moves"] if not (frames_picture(o["id"]) and (home or o["id"] in taken or lv.get("layout")))
                    and not (arrives(o["id"]) and (home or p.get("pick", p["rank"]) != 1 or "wall" in o["fits"]))]
            if not home and not lv.get("layout") and not any(inside(n, frame) for n in ({keep} if p is peak and keep not in taken else set(LAYOUTS) - taken - {"card"})):
                # a move that mats the photograph's box plays only in a free box inside the frame
                opts = [o for o in opts if not mats(o["id"])] or opts
            acting = [o for o in opts if frames_picture(o["id"]) or not only_says(o["id"])]
            # a move that only sets words stays only while the card offers no other move for a laid beat
            if any(not frames_picture(o["id"]) for o in acting):
                opts = acting
            move = pick(opts or c["moves"], tags, "photo", used, {prev, *(then if p is story[-1] else ())})
        if home:
            layout = "card"
        elif frames_picture(move) and not lv.get("layout"):
            layout = move
        else:
            free = (set(LAYOUTS) - taken - {"card"}) or set(LAYOUTS) - {"card"}
            if keep in free:
                free = {keep} if p is peak else (free - {keep}) or free
            want = PREFERS.get(move)
            layout = lv.get("layout") or (want if want in free else layout_for(tags, free, frame, move))
        taken.add(layout)
        cut = cut_into(c, move, pick(c["transitions"], tags, "photo", cuts, ()))
        out.append({"move": move, "layout": layout, "transition": cut, "tags": tags})
        prev = move
    return out


# ------------------------------------------------------------------ the beats
def hook_beat(S, frame, p, words, handle, move):
    """The first of the countdown full in the frame, their title over it at the foot of the safe area and the handle
    small above it, on a shade; a move that sets the title itself sets it alone, where the person can read it."""
    R = roles(S)
    x0, y0, x1, y1 = frame.safe
    small = SMALL[frame.name]
    layers = [photo_layer(p, [0, 0, frame.W, frame.H], frame, at=-0.5, beats=1.0)]
    if frames_picture(move):
        (wx0, wy0, wx1, wy1), _ = window(move, frame.W, frame.H, frame.safe, True)
        layers[0].update(box=through(p, [wx0, wy0, wx1 - wx0, wy1 - wy0], frame), uv=[0, 0, 1, 1])
    if (sets_words(move) or sets_label(move)) and not writes_unseen(move, frame, True):
        return layers
    text = cased(S, "display", words["title"])
    if frames_picture(move):
        # over a print the title keeps clear of its edges by the small size
        x0, x1 = x0 + small, x1 - small
    size, got = TITLE[frame.name], None
    while size > FLOOR[frame.name]:
        got = wrap_measured(S, {"text": text, "size": size, "face": "display"}, x1 - x0, 3)
        if got and (len(got) - 1) * line_pitch(S, "display", size) + size <= 0.4 * (y1 - y0):
            break
        size -= 4
    got = got or [text]
    pitch = line_pitch(S, "display", size)
    last = y1 - size * 0.25
    lines = [{"text": t, "size": size, "face": "display", "x": x0, "y": round(last - (len(got) - 1 - i) * pitch, 1), "color": R["over"]}
             for i, t in enumerate(got)]
    if handle:
        hl = {"text": cased(S, "text", handle), "size": round(small * 1.15), "face": "text", "x": x0, "color": R["over"]}
        hl["y"] = round(lines[0]["y"] - ink(S, lines[0])[0] - small * 1.2, 1)
        lines.insert(0, hl)
    layers.append(shade_of(lines, S, frame, R["shade"]))
    layers.append({"kind": "Words", "at": HOOK_AT, "lines": lines, "beats": LAND, "over": True})
    return layers


def piece_beat(S, frame, p, ch, read, beats, bpm):
    """A piece: its photograph in its layout on the card's ground, printed the card's way where it stands inside the
    frame (its rim, tilt and tape), its caption line set in the card's line face and its day in the card's label face,
    landing once the photograph holds clean."""
    R = roles(S)
    look = S["photo"]
    move, layout = ch["move"], ch["layout"]
    g = framed(move, frame) if layout == move else geometry(layout, frame, look, landscape=p["aspect"] < 1 and frame.H > frame.W)
    at = round(max(0.3, min(CLEAN, beats - LEAVE - LAND - read * bpm / 60), flight(move, beats, bpm)[1]), 3)
    box = list(g["photo"])
    pic = look["picture"]
    inset = not g.get("window") and not (box[0] <= 0 and box[1] <= 0 and box[0] + box[2] >= frame.W and box[1] + box[3] >= frame.H)
    rim = round(pic["rim"] * frame.W) if inset else 0
    if rim:
        # the rim stands inside the layout's box, so the print with its border fills the place the layout gave it
        box = [box[0] + rim, box[1] + rim, box[2] - 2 * rim, box[3] - 2 * rim]
    # a card that shows no photograph sets the line alone on its ground
    layers = [photo_layer(p, box, frame, square=g.get("square", False))] if pic.get("show", True) else []
    if layers and g.get("window"):
        # the picture behind a window is placed by its focus, so the window frames its subject
        layers[0].update(window=g["window"], box=through(p, g["window"], frame), uv=[0, 0, 1, 1])
    if layers and inset and (rim or pic["tilt"] or pic["tape"]):
        layers[0]["print"] = {"rim": rim, "rimColor": pic["rimColor"], "tilt": pic["tilt"], "tape": pic["tape"], "tapeColor": pic["tapeColor"]}
    # what the move draws on the print and the print's tape never lands on the words: each place the words may stand
    # keeps to the side of their reach that holds more
    s = min(box[2], box[3])
    reach = [r for r in (writes(move, box, frame.W) if marks(move) else None,
                         [box[0] - 0.2 * s, box[1] - 0.4 * rim - 0.16 * s, box[0] + box[2] + 0.2 * s, box[1] + 0.16 * s]
                         if layers and layers[0].get("print", {}).get("tape") else None) if r]
    g["zone"] = outside(g["zone"], reach)
    if g.get("above"):
        # the day over the picture joins the words when the reach leaves it no room of its own
        above = outside(g["above"], reach)
        g["above"] = above if above[3] - above[1] >= 1.6 * FLOOR[frame.name] else None
    g["bands"] = [outside(b, reach) for b in g.get("bands") or []]
    # a layout the board lays sets the caption and the day by the card; a move that frames the picture writes them
    says_caption, says_day, _ = speaks(move) if layout == move and not writes_unseen(move, frame) else (True, True, None)
    caption = (p.get("caption") or "") if says_caption else ""
    day = p["date"] if says_day else ""
    if not (caption or day):
        return layers, at
    line, label = look["line"], look["label"]
    ground = S["colors"].get(look["ground"], look["ground"]) if not look["ground"].startswith("#") else look["ground"]
    rgb = {k: palette.hex_rgb(v) for k, v in S["colors"].items() if isinstance(v, str) and v.startswith("#")}
    reads_on = lambda role: palette.contrast(rgb[role], palette.hex_rgb(ground)) >= 4.5 if role in rgb else False
    on = line["color"] if reads_on(line["color"]) else R["on"]
    day_on = label["color"] if palette.contrast(rgb.get(label["color"], rgb["ink"]), palette.hex_rgb(ground)) >= 3 else on
    # the card's sizes are px at 1080 on the frame's short side
    k = min(frame.W, frame.H) / 1080
    face, day_face = line["face"], label["face"]
    day_size = max(SMALL[frame.name] * 1.15, label["size"] * k * 1.3, FLOOR[frame.name] if day_face == "display" else 0)
    set_ = dict(face=face, day_face=day_face, day_size=day_size, head=max(FLOOR[frame.name], line["size"] * k * (1.6 if layout != "card" else 1.25)))
    lines, over = [], False
    for band in g.get("bands") or []:
        lines = block(S, frame, band, caption, day, "middle", g.get("align", "start"), False, on, day_on, **set_)
        if lines and min(ln["size"] for ln in lines if ln["face"] == face or not caption) >= 0.7 * set_["head"]:
            break
        lines = []
    if not lines and "window" not in g:
        over = g.get("over", False)
        color, day_color = (R["over"], R["over"]) if over else (on, day_on)
        lines = block(S, frame, g["zone"], caption, day, g["valign"], g["align"], g.get("big", False), color, day_color, above=g.get("above"), **set_)
    if not lines:
        # the words take the photograph's foot over a shade when the layout's zone cannot hold them at the floor, clear
        # of what the move draws on it
        x0, y0, x1, y1 = frame.safe
        zone = g["foot"]["zone"] if g.get("foot") else outside(
            [max(x0, box[0] + 24), max(y0, box[1] + 0.45 * box[3]), min(x1, box[0] + box[2] - 24), min(y1, box[1] + box[3] - 24)], reach)
        over = True
        lines = block(S, frame, zone, caption, day, "bottom", "start", False, R["over"], R["over"], **set_)
    if lines:
        if over:
            # a move's window covers what lies outside it with the card's ground, the shade with the picture, so the
            # shade spans the frame's width at the window's height and its sides are the window's however it moves
            win = g.get("window")
            within = [0, win[1], frame.W, win[3]] if win else box
            layers.append(shade_of(lines, S, frame, R["shade"], max(0.6, line["scrim"]), within))
        layers.append({"kind": "Words", "at": at, "lines": lines, "beats": LAND, "enter": line["enter"], "rotate": line["rotate"],
                       **({"over": True} if over else {})})
    return layers, at


def outside(zone, reach, gap=16):
    """`zone` [x0, y0, x1, y1] cut to the part above or below each box in `reach` it meets, whichever holds more."""
    for r in reach:
        if _meets(zone, r):
            zone = max([zone[0], zone[1], zone[2], min(zone[3], r[1] - gap)], [zone[0], max(zone[1], r[3] + gap), zone[2], zone[3]],
                       key=lambda z: z[3] - z[1])
    return zone


def marks(move):
    """True when the move marks the print's corner or its head (a doodle, a sticker, a rule) and leaves the rest of it
    bare: on the grid, it marks the grid's corner."""
    return move in ("doodle-draw-on", "sticker-pop", "rule-draw")


def grid_beat(S, frame, posts, words, handle, year, move=None, after=0.0):
    """The nine as they are posted: a three by three grid of equal square tiles GUT apart, the first of the countdown at
    its top left. The reel sets the year and the handle with the ask over the grid, its block centered down the frame
    and never above the safe area; the wide sets them to the grid's left; the square is the grid alone. Returns the
    layers and the box a `move` that marks a corner marks: on the reel the room right of the year, so the mark stands
    beside the year and off every tile, the tiles starting below its reach; elsewhere the grid's own box. The words
    land a beat in, or `after` beats in when the move holds the frame until then."""
    R = roles(S)
    W, H, g = frame.W, frame.H, GUT
    sx0, sy0, sx1, sy1 = frame.safe
    small = SMALL[frame.name]
    year_ = {"text": cased(S, "display", str(year)), "size": CLOSER_YEAR[frame.name], "face": "display", "color": R["on"]}
    tag = {"text": cased(S, "text", f"{handle}  ·  {words['ask']}" if handle else words["ask"]), "size": round(small * 1.5), "face": "text",
           "color": R["day"]}

    def stacked(x, top, width):
        yr = dict(year_, x=x, y=0)
        yr["size"] = fit_size(S, yr, width)
        yr["y"] = round(top + ink(S, yr)[0], 1)
        tg = dict(tag, x=x, y=0)
        tg["size"] = fit_size(S, tg, width)
        tg["y"] = round(yr["y"] + ink(S, yr)[1] + small * 0.9 + ink(S, tg)[0], 1)
        return [yr, tg], tg["y"] + ink(S, tg)[1]

    if frame.name == "square":
        side = (W - 4 * g) // 3
        x0, y0, lines = g, (H - 3 * side - 2 * g) // 2, []
    elif frame.name == "reel":
        side = (W - 2 * 54 - 2 * g) // 3
        x0 = (W - 3 * side - 2 * g) // 2
        x = max(sx0, x0) + 2
        span_ = 3 * side + 2 * g

        def beside(yr):
            # the room right of the year, its left edge moved until the mark's reach clears the year by the small size
            a, d = ink(S, yr)
            clear, right = yr["x"] + text_width(S, yr) + small, x0 + span_
            box = [clear, yr["y"] - a, right - clear, a + d]
            for _ in range(3):
                box[0] += clear - writes(move, box, W)[0]
                box[2] = right - box[0]
            return [round(v, 1) for v in box]

        lines, foot = stacked(x, 0, sx1 - x)
        gap = small * 1.4
        if marks(move):
            gap += max(0, writes(move, beside(lines[0]), W)[3] - foot)
        head = foot + gap
        top = max(sy0, (H - head - 3 * side - 2 * g) / 2)
        lines, foot = stacked(x, top, sx1 - x)
        y0 = round(foot + gap)
        mark = beside(lines[0]) if marks(move) else None
    else:
        side = (sy1 - sy0 - 2 * g) // 3
        x0, y0 = sx1 - 3 * side - 2 * g, sy0
        x = sx0 + 2
        lines, foot = stacked(x, 0, x0 - 4 * g - x)
        lines, _ = stacked(x, (H - foot) / 2, x0 - 4 * g - x)
    tiles = []
    # the first tile stands from the cut, so the wall never opens on bare ground; the rest land after it. A move that
    # flies a photograph in lands it on the middle tile and every other tile in its own cell, so all nine stand from the
    # cut under the move, and the frame it hands back is the whole wall
    for i, p in enumerate(sorted(posts, key=lambda p: p.get("pick", p["rank"]))):
        box = [x0 + (i % 3) * (side + g), y0 + (i // 3) * (side + g), side, side]
        tiles.append({"kind": "Slice", "photo": {"file": p["file"], "aspect": p["aspect"]}, "box": box, "uv": cover(p, box, True),
                      "owner": p["rank"], "at": 0 if after else round(TILE * i, 2), "beats": 0 if after or not i else LANDS})
    words_ = [{"kind": "Words", "at": max(1.0, after), "lines": lines, "beats": LAND}] if lines else []
    if frame.name != "reel" or not marks(move):
        mark = [x0, y0, 3 * side + 2 * g, 3 * side + 2 * g]
    return tiles + words_, mark


def build(c, posts, frame, words, handle, year, bpm=BPM, seconds=30, swatches=None, levers=None):
    """The storyboard of the nine in style card `c` and `frame`: {system, beats, sound, clips, end, rests, hook, cuts}.
    Each beat is {id, form, at (its first musical beat), beats, move, transition, layout, words, label, peak, layers};
    its layers' times are beats from its own start."""
    levers = levers or {}
    made = palette.palette_of(c["palette"], swatches or list(palette.NEUTRAL))
    names = {h: f"swatch {i + 1}" for i, h in enumerate(made["swatches"])}
    S = compose.system(c, {**made["roles"], "swatches": [{"hex": h, "name": names[h]} for h in made["swatches"]]})
    compose.use(c["id"])
    story = film_order(posts)
    first = story[-1]
    asked = {k: v["seconds"] for k, v in levers.items() if isinstance(v, dict) and v.get("seconds")}
    moves_used = {}
    hook_tags = {"title", "words", "peak"}
    # the hook's photograph has the whole frame and no box of its own, so a move that mats a box has nothing to mat
    # the hook's title lands a quarter beat in, so a move that holds the frame for its flight has no place there
    hook_opts = [o for o in c["moves"] if (frames_picture(o["id"]) or not covers(o["id"])) and not arrives(o["id"])]
    hook_move = pick(hook_opts or c["moves"], hook_tags, "title", moves_used, ())
    # a move that would write the title where it cannot be read is handed nothing; the board sets the title
    unseen = writes_unseen(hook_move, frame, True)
    beats = [{"id": "hook", "form": "title", "at": 0.0, "beats": HOOK_BEATS, "move": hook_move, "transition": None, "layout": "bleed",
              "words": "" if unseen else words["title"],
              # a move that writes its label before the words would write the handle in the title's place
              "label": "" if unseen or sets_label(hook_move) and not sets_words(hook_move) else handle, "peak": True,
              "layers": hook_beat(S, frame, first, words, handle, hook_move),
              "held": "their title over the photograph at the top of the countdown"}]
    wall_opts = [o for o in c["moves"] if not covers(o["id"]) and not sets_words(o["id"])]
    chosen = choose(c, story, levers, frame, hook_move, [o["id"] for o in wall_opts] if len(wall_opts) == 1 else ())
    wall_move = pick(wall_opts or c["moves"], {"wall", "photo"}, "wall", moves_used, {chosen[-1]["move"]})
    plan = timing(story, seconds, bpm, asked, [ch["move"] for ch in chosen], wall_move)
    if plan is None:
        raise ValueError(f"the nine do not fit {seconds} s at {bpm} bpm")
    t = HOOK_BEATS
    word_at = {}
    turns = ENTRANCES.get(S["photo"]["line"]["enter"], (S["photo"]["line"]["enter"],))
    entered = []
    for p, n, read, ch in zip(story, plan["holds"], plan["reads"], chosen):
        layers, at = piece_beat(S, frame, p, ch, read, n, bpm)
        for L in layers:
            if L["kind"] == "Words":
                L["enter"] = next((e for e in turns if e not in entered[-2:]), next((e for e in turns if e not in entered[-1:]), turns[0]))
                entered.append(L["enter"])
        bid = f"piece-{p['rank']}"
        word_at[bid] = at
        beats.append({"id": bid, "form": "photo", "at": round(t, 3), "beats": n, "move": ch["move"], "transition": ch["transition"],
                      "layout": ch["layout"], **handed(p, ch, frame), "peak": p.get("pick", p["rank"]) == 1,
                      "lands": flight(ch["move"], n, bpm)[0], "layers": layers})
        t += n
    t = plan["nine"]
    wall_layers, wall_mark = grid_beat(S, frame, story, words, handle, year, wall_move, flight(wall_move, plan["grid"], bpm)[1])
    beats.append({"id": "grid", "form": "wall", "at": t, "beats": plan["grid"], "move": wall_move,
                  "transition": cut_into(c, wall_move, pick(c["transitions"], {"wall"}, "wall", {}, ())), "layout": "grid", "words": "",
                  # the grid sets the year itself; a move handed it would write it a second time over the tiles
                  "label": "",
                  "peak": False, "layers": wall_layers, "lands": flight(wall_move, plan["grid"], bpm)[0],
                  "held": "the best nine as a three by three grid, made to be posted"})
    if marks(wall_move):
        beats[-1]["marks"] = wall_mark
    if arrives(wall_move):
        # a move that flies a photograph in lands on the grid's middle tile, where it stands once the frame is handed back
        beats[-1]["landing"] = MIDDLE
    t += plan["grid"]
    # every closer comes up over the last picture (a matte dims it, a page or a ground rises over it), so the wall
    # stays under the closer, every tile standing from the cut
    wall = [{**L, "at": 0, "beats": 0} for L in beats[-1]["layers"] if L["kind"] == "Slice"]
    closer_moves = [o for o in c["moves"] if o["id"] != wall_move]
    closer_move = pick(closer_moves or c["moves"], {"closer"}, "closer", moves_used, {wall_move})
    beats.append({"id": "closer", "form": "closer", "at": t, "beats": round(plan["end"] - t, 3), "move": closer_move,
                  "transition": cut_into(c, closer_move, pick(c["transitions"], {"closer"}, "closer", {}, ())), "layout": c["closer"], "words": words["promise"],
                  "label": handle, "peak": False, "layers": wall, "held": "the closer with their title and their promise"})
    middle = story[len(story) // 2]["rank"]
    rest_at = {"hook": ("hook", HOOK_AT + LAND + 0.6), "ordinary": (f"piece-{middle}", word_at[f"piece-{middle}"] + LAND + 0.3),
               "dense": ("grid", max(TILE * (len(story) - 1) + LANDS, flight(wall_move, plan["grid"], bpm)[1] + LAND) + 0.3), "closer": ("grid", plan["grid"] - EDGE - 0.2), "card": ("closer", SETTLE + 0.25)}
    return {"system": S, "beats": beats, "end": plan["end"], "hook": HOOK_AT, "rest_at": rest_at, "settle": t + SETTLE,
            "sound": sound(beats, story), "clips": clips(beats, story, bpm)}


def sound(beats, story):
    """The board's one sound cue for music.py: the stop, where the closer settles, the bed cuts and the film holds
    silent. Every effect is the shared layer's (sfx.py), laid at render from the board itself (fx_board)."""
    C = next(b for b in beats if b["id"] == "closer")["at"]
    return [{"kind": "stop", "at": C + SETTLE, "beat": "closer", "what": "the picture and the music stop together; the closer holds silent"}]


def landed(words):
    """The beat, from its beat's start, a Words layer's first line has landed on: on its cut for one that cuts or types
    in, halfway through its entrance for one that slams down, at its end for one that rises or fades (the film's Words:
    an entrance of 0.6 of the layer's beats, at least 0.3)."""
    at, n = words.get("at", 0), max(0.3, words.get("beats", 1) * 0.6)
    how = words.get("enter") or "rise"
    return at if how in ("cut", "type") else at + (0.5 * n if how == "slam" else n)


def fx_board(board):
    """The board as the shared effects (sfx.py) read it: each beat's form, move, the cut into it and its start, and one
    layer naming its kind and its moments. A photo beat is a Photo arriving where its photograph lands (on the cut, or
    where a move that flies it in lands it); the hook is a Title whose words slam on their landing (on the cut when its
    move sets them), and the grid one whose year does; the closer is a Closer arriving where it settles, so the riser builds through its rise and the impact
    lands where the picture and the music stop together."""
    out = []
    for b in board["beats"]:
        start = b.get("start", b.get("at", 0))
        words = next((L for L in b["layers"] if L["kind"] == "Words"), None)
        said = " ".join(ln["text"] for ln in (words or {}).get("lines") or [])
        if b["form"] == "photo":
            layer = {"kind": "Photo", "at": {"arrive": round(start + (b.get("lands") or 0), 3)}, "label": said}
        elif b["form"] == "closer":
            settle = (board.get("closer") or {}).get("still", start)
            layer = {"kind": "Closer", "signoff": {"text": board.get("signoff", "")}}
            start = settle
        elif words:
            layer = {"kind": "Title", "title": {"text": said}, "slam": [round(start + landed(words), 3), 0]}
        elif b.get("words") or b.get("label"):
            # a move that sets the beat's words itself lands them with its picture, on the cut
            layer = {"kind": "Title", "title": {"text": b.get("words") or b.get("label")}, "slam": [start, 0]}
        else:
            layer = {"kind": "Wall", "text": ""}
        out.append({"id": b["id"], "form": b["form"], "move": b.get("move"), "transition": b.get("transition"), "start": start,
                    "layers": [layer]})
    return {"id": board.get("id"), "bpm": board.get("bpm"), "beats": out}


def _short(caption, limit=10):
    words = (caption or "").replace("\n", " ").split()
    return " ".join(words[:limit]) + ("..." if len(words) > limit else "") if words else "the photograph"


def clip_move(p, prev=None):
    """The clip's own camera move, from what the photograph is: the top of the countdown pulled back from, a landscape
    dollied into, a portrait tracked along or craned up; a move the clip before it made gives way to the next one the
    photograph allows, so no two clips in a row move the same way."""
    if p.get("pick", p["rank"]) == 1:
        return "a slow pull back from it"
    ways = (["a slow dolly in toward it", "a slow lateral track along it", "a slow crane up over it"] if p["aspect"] > 1.05
            else ["a slow lateral track along it", "a slow crane up over it", "a slow dolly in toward it"])
    return next(w for w in ways if w != prev)


def clips(beats, story, bpm=BPM):
    """The clips the film carries. A piece the person gave as a recorded clip plays that clip, `role` "their own clip",
    `source` the file, `from` its strongest second, for `seconds` the length of its beat, on its photograph (the clip's
    poster), so the beat keeps the arrival and the move a photograph would have; nothing is generated for it. The
    others are generated clips for the platform's image-to-video model: the photograph at the top of the countdown
    under the hook (none when that is a recorded clip, which plays on its own beat), each photograph brought to life
    under its piece, and the grid's texture. Each prompt is a shot as a cinematographer writes it: the subject, the
    camera move, the lens, the light; `clips.py list` adds the beat's length and the loop. `stand_in` names what the
    film shows in a generated clip's place when it has not arrived."""
    by = {p["rank"]: p for p in story}
    top = story[-1]
    light = "the photograph's own light, soft and directional, its highlights held"
    out = [] if top.get("video") else [
        {"id": "00", "beat": "hook", "role": "the top of the countdown, alive", "seconds": 2.0, "image": top["file"],
         "prompt": f"{_short(top.get('caption'))}, as in this photograph: a slow push in, 35 mm lens, deep focus, {light}, no text",
         "stand_in": "the photograph held full in the frame under the card's move"}]
    prev = None
    for b in beats:
        if b["form"] != "photo":
            continue
        p = by[int(b["id"].split("-")[1])]
        if p.get("video"):
            out.append({"id": f"{len(out):02d}", "beat": b["id"], "role": "their own clip", "source": p["video"],
                        "from": float(p.get("clip_at") or 0.0), "seconds": round(b["beats"] * 60 / bpm, 2), "image": p["file"],
                        "prompt": None, "stand_in": None})
            continue
        prev = clip_move(p, prev)
        out.append({"id": f"{len(out):02d}", "beat": b["id"], "role": "the photograph brought to life", "seconds": 1.5, "image": p["file"],
                    "prompt": f"{_short(p.get('caption'))}, as in this photograph: {prev}, 50 mm lens at eye level, shallow depth of field, {light}, small natural motion in the scene, nothing added, no text",
                    "stand_in": f"the photograph in its {b['layout']} layout under the card's {b['move']} move"})
    out.append({"id": f"{len(out):02d}", "beat": "grid", "role": "the texture of the grid", "seconds": 1.5, "image": top["file"],
                "prompt": f"the surfaces of {_short(top.get('caption'))}, as in this photograph: a slow macro drift across them, 100 mm macro lens, raking light, no text",
                "stand_in": "the whole grid standing under the move that flies a photograph onto it"
                if any("landing" in b for b in beats if b["form"] == "wall") else "the grid landing tile by tile"})
    return out


def _meets(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def handed(p, ch, frame):
    """The words a photo beat hands its move: none when the board lays the picture (the card's line and label set the
    caption and the day) or when the move would write them outside the safe area, the caption and its label when the
    move frames the picture itself."""
    if ch["layout"] != ch["move"] or writes_unseen(ch["move"], frame):
        return {"words": "", "label": ""}
    return {"words": p.get("caption") or "", "label": (p.get("caption") or p["date"]) if speaks(ch["move"])[2] == "caption" else p["date"]}


def speaks(move):
    """What a beat's words become under `move`: (the board sets the caption, the board sets the day, the label the
    move is handed). A move that sets the words itself takes the caption and the day; a framing move that writes a
    label writes the caption on its print or in its margin; any other move that writes a label writes the day."""
    if sets_words(move):
        return False, False, "day"
    if sets_label(move):
        return (False, False, "caption") if frames_picture(move) else (True, False, "day")
    return True, True, "day"
