"""drive, "tagged": the tag that marks each of the account's people in its photographs finds them one by one, and the
year's cut of each closes into one wall of them.

A board is this story laid out in one style (styles/<id>.json, read through style.py): the card's two faces set every
line, its palette rule makes every color from the photographs' swatches, and each beat's move and the transition into
it are chosen from what the beat shows, within the card's lists. The camera holds on each card and cuts to the next by
the beat's transition. The hook is the photograph of them together, cut by a level edge: a tag pops onto every head in
it, the title stands on the edge, and the tags gather into one that flies off to find the first of them. One by one, in
the order taste.json lists them, each person is a card: the photograph of the two of them lands the way its move says,
the tag lands on them with their handle, the blade cuts the photograph along an edge laid just over their head (rising
over the side of the frame they stand on), the stamp of where and when it was taken falls onto the edge, and their own
words rise over it, set into the photograph in the color the picture behind them reads in (on a thin strip where it is
too busy to read on), or on the style's ground where the move lays the card on the page. A landscape photograph is
mounted the way the card's photo layout says: taped to the page as a print in its rim, or, where the card lays a landscape
photograph on the whole frame, filling the frame from the edge down, cropped at its sides; never over a blurred copy of
itself. When the camera leaves, the card trims into its slice of the wall and the
tag flies on to the next person. The closer is the wall: the others in rows from its head (a row of four in 16:9, of
two in 9:16 and 1:1), the last across its foot, every print showing its face whole and at least half of its
photograph's shorter side, every slice meeting the next at a thin gutter and every stamp, the handle and the title set
into the photographs. The wall holds every person the film names: when its rows would stand under the format's floor
inside the frame, it grows downward past the frame's foot, each row over the last standing 280 px tall or taller, and
the camera runs down it with the tag. The wall settles with the impact, the tag runs it in the film's order, leaving a
tag beside each of them, and lands on the last; then the card's closer plays, and the picture and the music stop
together as it settles.

Every line of type is set from the card's face file, measured here, and carried on the board with its file. The
storyboard is format-free (a hook, a beat per person naming their line, the closer); board() lays it out in one format
with the sound cues, the clips and, per beat, its move, its transition, what its move reveals and what it carries across
the cut.
"""
import copy
import functools
import math
import re

import _env
import boards
import layout as L
import palette as P
import style as S

NAME = "tagged"
IDEA = ("the tag that marks each of the account's people in its photographs finds them one by one, and the year's cut "
        "of each closes into one wall of them")
BPM = 120
CAMERA = {}

# where the edge crosses the frame's middle column, px, as the cards prefer it, and on the hook
EDGE = {"reel": 860, "square": 560, "wide": 560}
HOOK_EDGE = {"reel": 840, "square": 520, "wide": 540}
# the tallest stamp, the words, the small type, a card's tag and a tag on the wall, the title, px
STAMP = {"reel": 150, "square": 120, "wide": 125}
WORDS = {"reel": 62, "square": 50, "wide": 54}
SMALL = {"reel": 42, "square": 42, "wide": 42}
TAG = {"reel": 42, "square": 42, "wide": 42}
WALL_TAG = {"reel": 42, "square": 42, "wide": 42}
TITLE = {"reel": 210, "square": 170, "wide": 180}
TITLE_LEAST = 80   # the hook's title never stands smaller
# how each look builds a person's frame (frame_of): the photograph edge to edge under the words, full-frame footage
# under a typed line and a date, or one print on the page; every other look stands its type on an edge over the photograph
FRAMES = {"kinetic-type": "bleed", "analog-home-movie": "footage", "scrapbook": "print"}
# a whole-frame card's edge stands ASIDE of the frame's height over its top, out of every framing
ASIDE = 0.13
# the name as a marquee band: its type size on a card and on the hook, its height as a share of that, and how far it
# runs past the frame's sides; the hook's band scrolls MARQUEE px a beat
BAND = {"reel": 64, "square": 56, "wide": 56}
BAND_HOOK = {"reel": 46, "square": 42, "wide": 42}
BAND_H = 1.7
BAND_OUT = 40
MARQUEE = 150
# the name as a sticker and as a stamp: type size, and height as a share of it
STICKER = {"reel": 40, "square": 36, "wide": 36}
STICKER_H = 1.75
STAMP_H = 1.6
# type keeps off the upper EYES of a named face's height (its eyes and nose)
EYES = 0.6
# the narrowest column the type takes beside a face too large to keep its words under the eyes
SIDE_LEAST = 300
# the scrim behind a whole-frame card's type starts SCRIM_IN px over its top
SCRIM_IN = 260
# a print is PRINT_W of the frame wide at most, cropped at its sides to stand up to PRINT_CROP times its uncropped
# height, its top PRINT_OVER px over the safe area's (the picture may stand under the app's top bar; its type never)
PRINT_W = 0.84
PRINT_CROP = 1.45
PRINT_OVER = 110
# a reel's page has a lower third under the safe area when the frame runs KEEPSAKE_ROOM px or more past it: the keepsake
# print stands there KEEPSAKE_GAP px under the caption's ink, KEEPSAKE_W of the frame wide, its height KEEPSAKE_ASPECT
# of its width, turned KEEPSAKE_TURN degrees; the month beside it is set KEEPSAKE_STAMP times the label's size, turned
# KEEPSAKE_STAMP_TURN degrees the other way, at least KEEPSAKE_PAD px in from the frame's side and the frame's middle
KEEPSAKE_ROOM = 400
# a home movie's typed lines: TYPED times the card's size, shrinking by TYPED_K only as far as keeping off the eyes
# takes, in at most TYPED_MOST lines; its date TYPED_DATE times the label's size;
# over a photograph lighter than TYPED_BRIGHT (CIE L*) behind them, their scrim is TYPED_DARK dark
TYPED = 1.45
TYPED_K = (1.0, 0.96, 0.93, 0.84, 0.76, 0.69, 0.62)
TYPED_MOST = 5
TYPED_DATE = 2.0
TYPED_BRIGHT = 55
TYPED_DARK = 0.85
# how the prints arrive on the page, one person after the next: taped down with a slap, slid in, dropped
PRINT_ENTRY = ("slap", "slide", "drop")
KEEPSAKE_GAP = 70
KEEPSAKE_W = 0.36
KEEPSAKE_ASPECT = 0.8
KEEPSAKE_TURN = 7
KEEPSAKE_STAMP = 2.0
KEEPSAKE_STAMP_TURN = 5
KEEPSAKE_PAD = 24
# the hook's whole-frame photograph overfills the frame by this much, so its opening pull-in never shows its edge
HOOK_OVER = 1.13
# the moves whose card zooms in from wide as it arrives (DRAWN entry "zoom")
ZOOMED = {"zoom-rocker"}
# the title on the closer's wall, "my people.", the largest type there, px at the wall's full stamp size
WALL_TITLE = {"reel": 150, "square": 120, "wide": 130}

# a head sits CLEAR to CLEAR + DROP px under the edge over it; with no face named, its top is HEAD of the photograph over its tip
CLEAR = 46
DROP = 160
HEAD = 0.09
# a card's type never stands on a head: the head runs CROWN of the face's height over the face the cast names
CROWN = 0.45
# the edge turns at most TILT degrees, rising over the side of the frame its person stands on
TILT = 9
# a photograph is enlarged at most MAXZ times past filling the frame under its edge
MAXZ = 2.6
# a framed photograph filling the frame is a band of a picture cast.py FRAMED_W wide, soft past FILLZ times filling
FILLZ = 1.8
# a print taped to the page stands TAPED px under its edge, room for the tape across its top corners
TAPED = 90
# a stamp's lowest ink stands LIFT px over the edge; words stand GAP px over the stamp's letters
LIFT = 6
GAP = 26
# a tag: its height, its side padding and its pointer, as shares of its type size
PILL_H, PILL_PAD, POINTER = 1.8, 0.62, 0.42
# a picture this near a line's own lightness (CIE L*) fights it; a line whose picture fights it this hard (tone_of)
# stands on a strip
NEAR = 45
BUSY = 14
STRIP = 0.6
# the closer: its people per row, the stamps hanging in their slices, the gutter between slices, the room over the
# last person's stamp, how far an outer slice runs off the frame, the least a slice shows on its short side, and how
# tall each row over the last stands on a wall grown past the frame's height, tried in turn
ACROSS = {"reel": 2, "square": 2, "wide": 4}
CHIP = {"reel": 96, "square": 80, "wide": 84}
GUT = 14
ROWGAP = 18
BLEED = 20
SHOWN = {"reel": 200, "square": 150, "wide": 150}
ROWS = (280, 360, 440, 520)
# the room between the last person's tag on the wall and the top of their head, px
FACE = 12
# the studio's camera holds a card at a LENS degree lens with its type DEPTH px in front of the photograph
# (motion/studio/drive/camera.ts and card.tsx), so it draws a card's type larger about the frame's middle than its px
LENS, DEPTH = 30, 100

# the beats each part of the film runs, and the beats after a card lands at which its moves happen (the studio's drive
# film times them the same way): the tag lands, the blade cuts and the stamp lands, the words rise; the camera
# leaves a card LEAVE before the next starts. On the hook the blade opens at once, the tags pop one every POP_STEP from POP, the
# title stands at TITLE_AT and the tags gather at GATHER. The closer's tag runs the wall from ROUTE_AT for ROUTE beats
# to the stop, and the wall holds silent for HOLD beats after it.
HOOK_BEATS = 4
DYS = (0, -40, 40, -80, 80, -120, 120, 160, -160, -200, 200, -240, 240, -280)   # a card's edge, tried this far off its place
# the tag leaves a card LEAVE before the cut to the next, the camera holding on the card until the cut
LAND, CUT, RISE, LEAVE = 0.6, 1.0, 0.35, 0.4
POP, POP_STEP, TITLE_AT, GATHER = 0.5, 0.25, 1.6, 2.9
# the closer: the wall settles ROUTE_AT after the cut into it (the impact), the tag runs it for ROUTE beats and lands on
# the last, the wall holds WALL_HOLD, the card's closer plays until it settles (settles, within SHAPE beats), and the
# picture holds still and silent for the rest of SHAPE and HOLD beats after that
ROUTE_AT, ROUTE, WALL_HOLD, SHAPE, HOLD = 0.9, 4.0, 1.0, 2.0, 2.0
SIGNOFF = "my people."
# the beats each shared closer (motion/system/moves/closer) moves for before it stands still, read from its last timed
# span: the stop lands on that beat, so the picture and the music stop together; a closer that never stands still
# (closing-flicker) plays SHAPE beats
SETTLES = {"book-cover": 1.6, "title-card": 1.5, "caption-alone": 1.4, "poster": 1.0}


def shaped(name):
    """True when the shared layer draws the card's closer `name` itself (motion/system/moves/closer), title and signoff
    with it: the wall then carries no title of its own, and its rows run to its foot."""
    return (L.Path(__file__).resolve().parent.parent / "motion" / "system" / "moves" / "closer" / f"{name}.tsx").is_file()


def settles(name, signoff=SIGNOFF):
    """The beats the card's closer `name` moves for before it stands still: letter-build slams in one letter after
    another, an eighth of a beat apart at most and the whole line inside a beat, each landing in a third of a beat."""
    if name == "letter-build":
        n = max(1, len(signoff.replace(" ", "")))
        return round((n - 1) * min(0.12, 1 / n) + 1 / 3, 3)
    return SETTLES.get(name, SHAPE)
BUILD = 2.0  # the beats the riser builds over into the wall's impact

# how the studio draws each of the cards' moves on a card (motion/studio/drive/card.tsx and words.tsx): the way the card
# enters, whether its type stands on the page over the photograph cut from the edge down (`page`) or in the photograph
# itself, and how its words arrive. A move the shared layer draws over
# the picture (motion/system/moves) needs no entry of its own.
DRAWN = {
    "polaroid-drop": {"entry": "drop", "page": True},
    "tape-slap": {"entry": "slap", "page": True},
    "doodle-draw-on": {"entry": "rise", "page": True, "words": "underline"},
    "sticker-pop": {"entry": "pop", "page": True},
    "page-drift": {"entry": "slide", "page": True},
    "gate-weave": {"entry": "cut"},
    "date-stamp": {"entry": "cut", "words": "date"},
    "zoom-rocker": {"entry": "zoom"},
    "light-leak": {"entry": "cut"},
    "roll-burn": {"entry": "cut"},
    "word-per-beat-slam": {"entry": "slam", "page": True, "words": "slam", "level": True},
    "type-mask-reveal": {"entry": "cut", "page": True, "level": True},
    "width-stretch": {"entry": "stretch", "page": True, "words": "stretch", "level": True},
    "marquee": {"entry": "slam", "page": True, "level": True},
    "stack-and-split": {"entry": "cut", "page": True, "level": True},
}


def drawn(move):
    return DRAWN.get(move, {"entry": "rise"})


# ------------------------------------------------------------------ the style a board is laid out in
def lab_hex(h):
    return lab(P.hex_rgb(h))


class Look:
    """The style a board is laid out in: its card, the six colors its palette rule made from the photographs'
    swatches, the ground the page and the wall stand on (the card's `bg`), the role that reads on that ground and the
    one that reads on the tags' accent, and the band of every framed photograph (the rows of its picture that hold the
    photograph itself)."""

    def __init__(self, style_id, swatches, bands=None):
        self.card = S.card(style_id)
        self.made = P.palette_of(self.card["palette"], swatches)
        self.colors = self.made["roles"]
        self.ground = "bg"
        self.on_ground = self.reads(self.colors["bg"])
        self.tag_text = self.reads(self.colors["accent"])
        self.bands = dict(bands or {})

    def reads(self, hexc):
        """Of ink and paper, the role that reads against `hexc` at the higher contrast."""
        return max(("ink", "paper"), key=lambda r: P.contrast(P.hex_rgb(self.colors[r]), P.hex_rgb(hexc)))

    def L(self, role):
        return lab_hex(self.colors[role])[0]

    def face(self, face):
        """The card face a board's face name is set in: the display face for "display", the text face for the rest."""
        return self.card["faces"]["display" if face == "display" else "text"]

    @property
    def mount(self):
        """How a landscape photograph is mounted in this style, from the card's photo layout: a print with a rim or tape
        is taped to the page, a picture that fills the frame on a dark ground is projected on the dark, and any other is
        laid flat on a field of the card's ground."""
        pic = self.card["photo"]["picture"]
        if pic["show"] and (pic["rim"] > 0 or pic["tape"] > 0):
            return "taped"
        ground = self.colors.get(self.card["photo"]["ground"], self.card["photo"]["ground"])
        if pic["show"] and list(pic["box"]) == [0, 0, 1, 1] and lab_hex(ground)[0] < 40:
            return "projected"
        return "flat"

    @property
    def fills(self):
        """True when the card lays a landscape photograph across the whole frame (its photo layout's landscape box is the
        frame): the photograph then fills the frame from the edge down, cropped at its sides, and no ground shows under
        it."""
        return list(self.card["photo"]["landscape"]["box"]) == [0, 0, 1, 1]


LOOK = None


def use(style_id, ctx=None, swatches=None):
    """Lays out the boards that follow in style `style_id`: the photographs' swatches from taste.json (else
    palette.json's year colors), the bands from the run's framed photographs."""
    global LOOK
    if swatches is None:
        swatches = P.swatches_of(_env.read_json("taste.json") or {}, _env.read_json("palette.json") or {})
    bands = {}
    if ctx is not None:
        photos = ctx.photos
        bands = {r: tuple(photos.band[r]) for r in photos.band if photos.framed(r)}
    LOOK = Look(style_id, swatches, bands)
    return LOOK


def look():
    if LOOK is None:
        raise RuntimeError("board_drive.use(style) names the style before a board is laid out")
    return LOOK


def lead(face):
    return look().face(face).get("lineHeight", 1.1)


def system():
    lk = look()
    s = S.system(lk.card, lk.colors)
    s["safe"] = L.system_safe()
    s["on_ground"], s["tag_text"], s["ground"] = lk.on_ground, lk.tag_text, lk.ground
    return s


# ------------------------------------------------------------------ type, measured from the card's faces
def file_of(face):
    return look().face(face)["file"]


@functools.lru_cache(maxsize=256)
def _font(file, size):
    from PIL import ImageFont
    return ImageFont.truetype(str(L.DESIGN.parent / file), max(1, round(size)))


def width(ln, text=None):
    s = ln["text"] if text is None else text
    return _font(ln["file"], ln["size"]).getlength(s, features=["kern", "liga"]) + (ln.get("tracking") or 0) * ln["size"] * len(s)


def box(ln, ink=False):
    """The px box a line takes in its own coordinates: its advance across, and the font's ascent to descent (with
    `ink`, the glyphs' own extent)."""
    f = _font(ln["file"], ln["size"])
    w = width(ln)
    x = ln["x"] - {"middle": w / 2, "end": w}.get(ln.get("anchor"), 0)
    if ink:
        b = f.getbbox(ln["text"], anchor="ls")
        return (x, ln["y"] + b[1], x + w, ln["y"] + b[3])
    asc, desc = f.getmetrics()
    return (x, ln["y"] - asc, x + w, ln["y"] + desc)


def turned(b, ln):
    """The corners of box `b` of `ln` as drawn: turned `rotate` degrees clockwise about its pivot."""
    x0, y0, x1, y1 = b
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    a = ln.get("rotate") or 0
    if not a:
        return pts
    px, py = ln.get("pivot") or (ln["x"], ln["y"])
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in pts]


def hull(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def ink(ln):
    """A line's ink over and under its baseline, px, upright."""
    b = box(ln, ink=True)
    return ln["y"] - b[1], b[3] - ln["y"]


def wrap(ln, room, most=4):
    """`ln`'s text in the fewest lines whose advance fits `room` px, as even as the words allow; None when none fits."""
    words = ln["text"].split()
    for n in range(1, min(most, len(words)) + 1):
        best = None
        for ls in L._breaks(words, n):
            ws = [width(ln, x) for x in ls]
            if max(ws) > room:
                continue
            cost = max(ws) - min(ws) + L.phrasing(ls, room) + (1e6 if L.hangs(ls) and n > 1 else 0)
            if best is None or cost < best[0]:
                best = (cost, ls)
        if best:
            return best[1]
    return None


def fit_size(ln, room, lo=24):
    size = ln["size"]
    while size > lo and width(dict(ln, size=size)) > room:
        size -= 1
    return size


def floor_size(face):
    """The smallest size, px, at which the card face `face` names stands at the floor's cap height."""
    return math.ceil(L.FLOOR * 100 / ink(line("H", face, 100, 0, 0))[0])


def line(text, face, size, x, y, color="ink", **kw):
    """A line in the card face `face` names ("display", else the text face), in that face's case and tracking."""
    f = look().face(face)
    return {"text": S.cased(text, f), "x": round(x, 1), "y": round(y, 1), "size": size, "file": f["file"],
            "face": "display" if face == "display" else "text", "tracking": f.get("tracking", 0), "color": color, **kw}


# ------------------------------------------------------------------ the edge and the photograph under it
class Edge:
    """A straight edge across the frame through the middle column at `yc` px, turned `tilt` degrees (positive falls to
    the right); `yl` and `yr` are where it meets the frame's left and right sides."""

    def __init__(self, F, yc, tilt):
        self.W, self.yc, self.tilt = F.W, yc, tilt
        t = math.tan(math.radians(tilt))
        self.yl, self.yr = yc - t * F.W / 2, yc + t * F.W / 2

    def y(self, x):
        return self.yl + (self.yr - self.yl) * x / self.W

    @property
    def line(self):
        return [round(self.yl, 1), round(self.yr, 1)]


def subject(photos, role):
    """(tip, head) of a photograph's person, as fractions of the photograph: where their tag points, and the top of their
    head (the face's top when the cast names a face)."""
    info = photos.info(role)
    tip = tuple(info.get("tip") or info["point"])
    face = info.get("face")
    if face:
        return tip, ((face[0] + face[2]) / 2, face[1])
    return tip, (tip[0], max(0.0, tip[1] - HEAD))


def cover(F, a, edge, head, x_to, top=None, clear=CLEAR, most=MAXZ, foot=0.0, band=None):
    """The px box [x, y, w, h] the whole photograph (aspect `a`, height over width) is laid in so it fills the frame
    from `top` down (from `edge` when unset), the head at `head` (fractions) on column `x_to` as far as its sides allow
    and between `clear` and `clear` + DROP px under the edge (as near its unenlarged place as that allows, and high
    enough that the `foot` of the photograph's height under the head, the rest of the face, stays in the frame),
    enlarged at most `most` times past filling (1 for a framed photograph, which then shows its whole width); and how
    far past filling that part of the frame it is enlarged. A framed photograph's box is its print (`band`, the
    fractions of the box's height the print spans) on its mount, and its unenlarged place is the print's top on the
    edge, so the print stands right under the type and never a mount's width below it."""
    top = min(edge.yl, edge.yr) if top is None else top
    b0 = band[0] if band else 0.0
    least = max(F.W, (F.H - top) / a)
    hu, hv = head
    iw = least

    def at(iw):
        ix = max(F.W - iw, min(0.0, x_to - hu * iw))
        e = edge.y(ix + hu * iw) + clear
        return ix, max(e, min(e + DROP, top + (hv - b0) * iw * a, F.H - CLEAR / 2 - foot * iw * a))

    for _ in range(8):
        ix, yh = at(iw)
        need = iw
        if hv < 0.98:
            need = max(need, (F.H - yh) / (1 - hv) / a)
        if hv > 0.02:
            need = max(need, (yh - top) / hv / a)
        need = min(need, least * most)
        if need <= iw + 0.5:
            break
        iw = need
    ih = iw * a
    ix, yh = at(iw)
    iy = max(F.H - ih, min(top, yh - hv * ih))
    return [round(ix, 1), round(iy, 1), round(iw, 1), round(ih, 1)], iw / least


def cover_band(F, a, band, edge, head, x_to, clear=CLEAR, foot=0.0):
    """cover() for a framed photograph in a look that fills the frame with it: the photograph itself (the `band` of its
    picture, whose aspect is `a`) fills the frame from the edge down, enlarged at most FILLZ times past filling, the head
    as cover() places it; returned as the box of the whole picture, so its band lands there."""
    b0, b1 = band
    k = b1 - b0
    hv = min(1.0, max(0.0, (head[1] - b0) / k))
    (x, y, w, h), zoom = cover(F, a * k, edge, (head[0], hv), x_to, clear=clear, most=FILLZ, foot=foot / k)
    tall = h / k
    return [x, round(y - b0 * tall, 1), w, round(tall, 1)], zoom


def print_place(F, a, band, top):
    """The box of the whole picture for a framed photograph taped to the page as a print: the photograph itself (the
    `band` of its picture, whose aspect is `a`) centred on the card's landscape box, as wide as the print, its white
    border and its turn at the card's tilt keep inside the box's width, its top `top` px down and its foot no lower than
    the box's; the paper shows round it."""
    b0, b1 = band
    k = b1 - b0
    x, y, w, h = look().card["photo"]["landscape"]["box"]
    pic = look().card["photo"]["picture"]
    r, turn = pic.get("rim", 0), math.radians(abs(pic.get("tilt", 0)))
    bw = w * F.W / ((1 + 2 * r) * math.cos(turn) + (a * k + 2 * r) * math.sin(turn))
    bh = min(bw * a * k, F.H * (y + h) - top)
    bw = bh / (a * k)
    tall = bh / k
    return [round(F.W * (x + w / 2) - bw / 2, 1), round(top - b0 * tall, 1), round(bw, 1), round(tall, 1)]


def lab(rgb):
    r, g, b = (((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in rgb)
    x, y, z = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.9505, r * 0.2126 + g * 0.7152 + b * 0.0722, (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.089
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])



@functools.lru_cache(maxsize=32)
def pixels(file):
    from PIL import Image
    with Image.open(L.Path("public") / file) as im:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        return im


def tone_of(F, file, place, lines, band=None):
    """The color `lines` are set in over a sharp photograph, and how hard the picture behind them is to read them on:
    of the style's ink and paper, the one whose lightness (CIE L*) stands farther from the middle of the picture behind
    the type; the cost is the share of the picture behind the type within NEAR of the type's own lightness, over a
    quarter, plus how far its lightness spreads past BUSY (a busy picture breaks the letters up whatever their tone).
    Off the photograph, or outside a framed photograph's `band` (the rows that hold the photograph itself), the type
    stands on the style's ground."""
    lk = look()
    ground = lk.L(lk.ground)
    try:
        im = pixels(file)
    except OSError:
        return lk.on_ground, 0.0
    v0, v1 = band or (0.0, 1.0)
    x, y, w, h = place
    iw, ih = im.size
    x0, y0, x1, y1 = hull([q for ln in lines for q in turned(box(ln, ink=True), ln)])
    step = max(4, min(x1 - x0, y1 - y0) / 8)
    ls = []
    X = x0
    while X < x1:
        Y = y0
        while Y < y1:
            u, v = (X - x) / w, (Y - y) / h
            ls.append(lab(im.getpixel((int(u * iw), int(v * ih))))[0] if 0 <= u < 1 and v0 <= v < v1 else ground)
            Y += step
        X += step
    if not ls:
        return lk.on_ground, 0.0
    ls.sort()
    mid = ls[len(ls) // 2]
    tone = max(("ink", "paper"), key=lambda r: abs(lk.L(r) - mid))
    own = lk.L(tone)
    mean = sum(ls) / len(ls)
    spread = (sum((v - mean) ** 2 for v in ls) / len(ls)) ** 0.5
    return tone, 4 * sum(abs(v - own) < NEAR for v in ls) / len(ls) + max(0.0, spread - BUSY) / 10


def toned(F, file, place, ln, band=None):
    """`ln` in the color the picture right behind it reads in; a line other than the stamp over a picture too busy to
    read it on stands on a thin strip of the other color (`strip`: its advance, px)."""
    tone, hard = tone_of(F, file, place, [ln], band)
    out = dict(ln, color=tone)
    if hard > STRIP and not ln.get("name", "").startswith("stamp-"):
        out["strip"] = round(width(ln), 1)
    return out


def photo(photos, role):
    """A photograph as the film draws it; a framed one (a landscape photograph laid whole in a taller frame) also names
    its band and how the style mounts it (Look.mount): taped to the page, projected on the dark, or laid flat."""
    face = photos.info(role).get("face") if role != "group" else None
    framed = {"band": photos.band[role], "mount": look().mount} if photos.framed(role) else {}
    return {"file": f"matched/{role}.jpg", "aspect": photos.aspect[role], "role": role, **({"face": face} if face else {}), **framed}


def face_cut(F, slice_):
    """True when a wall slice cuts the face its photograph's cast names: a corner of the face outside the slice or the
    frame."""
    face = slice_["photo"].get("face")
    if not face:
        return False
    x, y, w, h = slice_["place"]
    poly = slice_["poly"]
    corners = [(x + u * w, y + v * h) for u in (face[0], face[2]) for v in (face[1], face[3])]

    def inside(px, py):
        if not (0 <= px <= F.W and 0 <= py <= F.H):
            return False
        return all((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0) >= 0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))

    return not all(inside(*c) for c in corners)


def face_clear(F, face, place, boxes):
    """True when the `face` (fractions) of a photograph laid at `place` is whole in the frame and none of the px `boxes`
    overlaps it (always, when no face is named)."""
    if not face:
        return True
    x, y, w, h = place
    f = (x + face[0] * w, y + face[1] * h, x + face[2] * w, y + face[3] * h)
    whole = f[0] >= -0.5 and f[1] >= -0.5 and f[2] <= F.W + 0.5 and f[3] <= F.H + 0.5
    return whole and not any(b[0] < f[2] and f[0] < b[2] and b[1] < f[3] and f[1] < b[3] for b in boxes)


def crowned(face):
    """The `face` box (fractions) with the head over it: the hair or a hat stand CROWN of the face's height over its top."""
    if not face:
        return face
    return (face[0], max(0.0, face[1] - CROWN * (face[3] - face[1])), face[2], face[3])


def sliver(F, slice_):
    """True when a wall slice shows less than half of its photograph's shorter side, across or down: a band of the
    photograph, where the eye no longer reads the picture."""
    v0, v1 = slice_["photo"].get("band") or (0.0, 1.0)
    return shown(slice_["poly"], F.W, F.H) < 0.5 * min(slice_["place"][2], (v1 - v0) * slice_["place"][3]) - 0.5


class Unfit(ValueError):
    """No wall lays out; `roles` are the photographs a slice could not show: its named face cut, or only a band of it."""

    def __init__(self, message, roles):
        super().__init__(message)
        self.roles = roles


# ------------------------------------------------------------------ tags
def tag(F, text, tip, size, room=None, side="below", top=None):
    """A tag: a pill holding `text`, its pointer touching `tip` from below it (or above it), shifted along to stay inside
    `room` (x0, x1; the safe area's when unset), its top at `top` px when given (the pointer reaching up to the tip).
    Its `box` is the pill's px box."""
    ln = line(text, "text", size, 0, 0, color=look().tag_text)
    w = width(ln) + 2 * PILL_PAD * size
    h = PILL_H * size
    x0, x1 = room or (F.left, F.right)
    left = max(x0, min(x1 - w, tip[0] - w / 2))
    if top is None:
        top = tip[1] + POINTER * size if side == "below" else tip[1] - POINTER * size - h
    return {"text": text, "file": ln["file"], "size": size, "tip": [round(tip[0], 1), round(tip[1], 1)], "side": side,
            "box": [round(left, 1), round(top, 1), round(left + w, 1), round(top + h, 1)]}


def in_frame(F, t):
    """A tag's pill inside the safe area and its pointer's tip on the frame: a tip may reach past the safe area's side to
    a head standing there."""
    x0, y0, x1, y1 = t["box"]
    return x0 >= F.left - 0.5 and x1 <= F.right + 0.5 and 0 <= t["tip"][0] <= F.W and max(y1, t["tip"][1]) <= F.bottom + 0.5


def shaped_in(F, t):
    """A tag inside the safe area: a pointed tag as `in_frame` has it; a band runs the frame's width, so only its rows
    count; a sticker or a stamp has no pointer, so only its box counts."""
    shape = t.get("shape")
    if not shape:
        return in_frame(F, t)
    x0, y0, x1, y1 = t["box"]
    across = shape == "band" or (x0 >= F.left - 0.5 and x1 <= F.right + 0.5)
    return across and y0 >= F.top - 0.5 and y1 <= F.bottom + 0.5


def hook_tag_fits(F, t, clear, others):
    """A tag on the hook: in the frame, wholly under `clear` px, and clear of every tag laid before it."""
    x0, y0, x1, y1 = t["box"]
    return (in_frame(F, t) and min(y0, t["tip"][1]) >= clear
            and not any(x0 < o["box"][2] and o["box"][0] < x1 and y0 < o["box"][3] and o["box"][1] < y1 for o in others))


def tag_fits(F, t, edge):
    """A tag, its pointer's tip with it, inside the safe area and wholly under the edge."""
    x0, y0, x1, y1 = t["box"]
    sx0, sx1, sy1 = F.left, F.right, F.bottom
    reach = min(y0, t["tip"][1])
    return x0 >= sx0 - 0.5 and x1 <= sx1 + 0.5 and max(y1, t["tip"][1]) <= sy1 + 0.5 and reach >= max(edge.y(x0), edge.y(x1)) + 8


# ------------------------------------------------------------------ a person's card
def safe_box(F):
    return (F.left, F.top, F.right, F.bottom)


def tall(F, height):
    """Format `F` as the closer's wall `height` px tall: the frame grown downward, its safe area's foot moving down
    with it, since the camera's last framing is the wall's foot."""
    if height <= F.H:
        return F
    G = copy.copy(F)
    G.H, G.bottom = height, F.bottom + height - F.H
    return G


def wall_of(F, b):
    """The closer beat `b`'s wall in format `F`: as tall as its Route layer says."""
    route = next((L_ for L_ in b["layers"] if L_["kind"] == "Route"), {})
    return tall(F, route.get("height", F.H))


def lensed(F):
    """Format `F` with its safe area drawn in to where a card's type, standing in front of the photograph, stays inside
    the format's safe area as the camera's lens sees it from the card's station."""
    k = F.H / (F.H - 2 * DEPTH * math.tan(math.radians(LENS / 2)))
    G = copy.copy(F)
    G.left, G.right = F.W / 2 - (F.W / 2 - F.left) / k, F.W / 2 + (F.right - F.W / 2) / k
    G.top, G.bottom = F.H / 2 - (F.H / 2 - F.top) / k, F.H / 2 + (F.bottom - F.H / 2) / k
    return G


def fits(F, lines, edge):
    """Every line inside the safe area and on the field's side of the edge."""
    x0, y0, x1, y1 = safe_box(F)
    for ln in lines:
        e = hull(turned(box(ln), ln))
        if e[0] < x0 - 0.5 or e[1] < y0 - 0.5 or e[2] > x1 + 0.5 or e[3] > y1 + 0.5:
            return False
        if any(y > edge.y(x) - 2 for x, y in turned(box(ln, ink=True), ln)):
            return False
    return True


def stamp_lines(F, p, said, edge, k, tone="ink"):
    """The stamp of where and when the photograph of the two of them was taken standing on the edge, as tall as its
    words allow inside the frame; their words over it in the card's text face; every line level and in `tone`."""
    x0 = F.left + 2
    probe = line(p.stamp, "display", round(STAMP[F.kind] * k), 0, 0)
    size = fit_size(probe, F.right - x0 - 4, lo=max(40, L.FLOOR * 2))
    for _ in range(3):
        out = stack_at(F, p, said, edge, k, tone, size, x0)
        left = min(hull(turned(box(ln), ln))[0] for ln in out)
        if left >= F.left:
            break
        x0 += (F.left - left) + 1
    return out


def stack_at(F, p, said, edge, k, tone, size, x0):
    """stamp_lines' stack with the stamp's left side at `x0`, level, its descenders clear of the edge where it rises
    highest under the stamp."""
    probe = line(p.stamp, "display", size, x0, 0)
    base = min(edge.y(x0), edge.y(x0 + width(probe))) - LIFT - ink(probe)[1]
    stamp = line(p.stamp, "display", size, x0, base, color=tone, name=f"stamp-{p.rank}")
    out = [stamp]
    if said:
        cap = ink(line("H", "text", 100, 0, 0))[0] / 100
        ws = max(math.ceil(L.FLOOR / cap), round(WORDS[F.kind] * min(1.0, 0.4 + 0.6 * k)))
        probe = line(said, "text", ws, x0, 0)
        rows = wrap(probe, F.right - x0 - 4) or [probe["text"]]
        lead = ws * look().face("text").get("lineHeight", 1.15) * 1.05
        # the words stand a gap over the stamp's cap height, which a lowercase stamp's letters may not reach
        desc = max(ink(dict(probe, text=r))[1] for r in rows)
        y = base - max(ink(stamp)[0], ink(dict(stamp, text="H"))[0]) - GAP - desc
        for i, r in enumerate(reversed(rows)):
            out.append(line(r, "text", ws, x0, y - i * lead, color=tone, name=f"said-{p.rank}-{len(rows) - 1 - i}"))
    return out


def card(F, photos, p, said, i, move=None):
    """A person's card: (edge, role, layers, fit) on their first photograph, their moment's (the one the stamp names and
    their words are about), laid over the whole frame with their head just under an edge rising over their side, the
    stamp and words standing on the edge over the photograph, the tag on them: pointing up at its tip from under it,
    else down at the top of their head from over it (the head sits low enough under the edge for that when the cast
    names a face); when no edge leaves the face whole that way, the photograph fills the frame from the edge down and
    the stamp and words stand on the style's ground over it. A move that lays the card on the page (DRAWN `page`) tries
    the ground first, and a move that sets its type level (DRAWN `level`) keeps the edge level. A named face cut by
    the frame, or under type or a tag, makes a placement unfit. When their words find no place clear of the face, the
    card is laid without the words, so the stamp, the tag and the face stay whole."""
    if frame_of() != "edge":
        return whole_card(F, photos, p, said, i, move)
    how = drawn(move)
    lk = look()
    best = None
    role = f"{p.handle}-0"
    a = photos.aspect[role]
    tip, head = subject(photos, role)
    face = photos.info(role).get("face")
    over_at = (head[0], max(0.0, head[1] - 0.01))
    clear = CLEAR + (POINTER + PILL_H) * TAG[F.kind] + 8 if face else CLEAR
    x_to = F.W * (0.32 + 0.36 * head[0]) if F.kind != "wide" else F.W * (0.5 + 0.3 * head[0])
    tilt = 0.0 if how.get("level") else round(max(-TILT, min(TILT, -(x_to / F.W - 0.5) * 2 * TILT * 1.6)), 2)
    pref = EDGE[F.kind]
    band = photos.band[role] if photos.framed(role) else None
    # the move's own field first: the whole frame, or the photograph from the edge down with the type on the ground
    # over it; the other field only when no placement in the first is whole
    # (a framed photograph in a look that fills the frame with it fills it from the edge down, under the type on the ground)
    fill = band is not None and lk.fills
    taped = band is not None and lk.mount == "taped"
    order = (None,) if fill or taped else (None, 0) if how.get("page") else (0, None)
    for n, (top, dy) in enumerate((t, d) for t in order for d in DYS):
        if n == len(DYS) and best[-1]:
            break
        edge = Edge(F, pref + dy, tilt)
        foot = (face[3] - head[1]) if face else 0.0
        if fill:
            place, zoom = cover_band(F, a, band, edge, head, x_to, clear=clear, foot=foot)
        elif taped:
            place, zoom = print_place(F, a, band, max(edge.yl, edge.yr) + TAPED), 1.0
        else:
            place, zoom = cover(F, a, edge, head, x_to, top=top, clear=clear, most=1.0 if photos.framed(role) else MAXZ,
                                foot=foot, band=band)
        k, lines = 1.0, None
        for _ in range(14):
            lines = stamp_lines(F, p, said, edge, k)
            if fits(F, lines, edge):
                break
            k *= 0.94
        ok_type = fits(F, lines, edge)
        hx, hy = place[0] + head[0] * place[2], place[1] + head[1] * place[3]
        over = max(0.0, edge.y(hx) + CLEAR * 0.5 - hy)
        at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
        t = tag(F, f"@{p.handle}", at(*tip), TAG[F.kind])
        if not tag_fits(F, t, edge) or not face_clear(F, face, place, [t["box"]]):
            t = tag(F, f"@{p.handle}", at(*over_at), TAG[F.kind], side="above")
        ok_tag = tag_fits(F, t, edge)
        ok_face = (face_clear(F, face, place, [t["box"]])
                   and face_clear(F, crowned(face), place, [hull(turned(box(ln), ln)) for ln in lines]))
        # over the ground the type reads in the ground's own color; only over the photograph does the picture count
        hard = max(tone_of(F, f"matched/{role}.jpg", place, [ln], band)[1] for ln in lines) if top == 0 else 0.0
        ok = ok_type and ok_tag and ok_face
        score = (abs(dy) * 0.002 + max(0.0, zoom - 1.25) + (1 - k) * 2 + over / 40 + hard + (0 if ok_type else 20) + (0 if ok_tag else 10)
                 + (0 if ok_face else 20))
        if best is None or (not ok, score) < best[0]:
            best = ((not ok, score), edge, place, lines, t, "photo" if top == 0 else "paper", ok)
    _, edge, place, lines, t, field, ok = best
    if not ok and said:
        bare = card(F, photos, p, None, i, move)
        if bare[3]:
            return bare
    # type takes its color from the field it sits on: the ground's reading color on the ground, the photograph's own
    # tone over the photograph
    lines = [toned(F, f"matched/{role}.jpg", place, ln, band) if field == "photo" else dict(ln, color=lk.on_ground)
             for ln in lines]
    stamp, rest = lines[:1], lines[1:]
    if any("strip" in ln for ln in rest):   # a card's words read as one stack: on strips together or not at all
        rest = [dict(ln, color="ink", strip=round(width(ln), 1)) for ln in rest]
    return edge, role, [
        {"kind": "Cut", "at": 0, "line": edge.line, "field": lk.ground if field == "paper" else "photo",
         "photo": photo(photos, role), "place": place, "entry": how["entry"], "words": how.get("words", "rise")},
        {"kind": "Words", "at": CUT, "lines": stamp, "beats": 0.5},
        {"kind": "Words", "at": CUT + RISE, "lines": rest[::-1], "beats": 0.4, "step": 0.08},
        {"kind": "Tags", "at": LAND, "tags": [t]},
    ], ok


# ------------------------------------------------------------------ the looks that take the whole frame, or a print
def frame_of():
    """How the look builds a person's frame: `edge` (the photograph under an edge with the type over it on the page),
    `bleed` (the photograph edge to edge with the words over it), `footage` (the photograph as full-frame footage, the
    typed line and the date over it) or `print` (one tilted, taped print filling most of the page, its caption under it)."""
    return FRAMES.get(look().card["id"], "edge")


def entry_of(move):
    """How a card arrives in this look: a whole-frame card never travels in (that would bare the ground beside it), so
    it is slammed down from the lens or zoomed in from wide (`bleed` and `footage`), or simply there on the cut."""
    e = drawn(move)["entry"]
    frame = frame_of()
    if frame == "bleed":
        return e if e in ("slam", "cut") else "slam"
    if frame == "footage":
        return e if e in ("zoom", "cut") else "cut"
    return e


def aside(F):
    """The edge of a card whose photograph or page takes the whole frame: level, over the frame's top past the reach of
    every camera move, so no blade crosses the picture and nothing stands over it."""
    return Edge(F, -ASIDE * F.H, 0)


def whole_photo(photos, role):
    """A photograph that takes the whole frame, drawn as its whole picture: past the band a framed one spans, its
    blurred copy fills the frame wherever the camera's push carries it, so the ground never shows round it."""
    return {k: v for k, v in photo(photos, role).items() if k not in ("band", "mount")}


def bleed(F, photos, role, at, y_to, over=1.0, x_to=0.5):
    """The box of the whole picture that sets a photograph edge to edge: the photograph itself (its band, for a framed
    one) `over` times the frame on each axis, its point `at` (fractions) as near column `x_to` and row `y_to` (fractions
    of the frame) as its sides allow."""
    a = photos.aspect[role]
    b0, b1 = photos.band[role] if photos.framed(role) else (0.0, 1.0)
    iw = max(F.W * over, F.H * over / ((b1 - b0) * a))
    ih = iw * a
    mx, my = (over - 1) * F.W / 2, (over - 1) * F.H / 2
    ix = max(F.W + mx - iw, min(-mx, F.W * x_to - at[0] * iw))
    iy = max(F.H + my - b1 * ih, min(-my - b0 * ih, F.H * y_to - at[1] * ih))
    return [round(ix, 1), round(iy, 1), round(iw, 1), round(ih, 1)]


def focus_of(photos, role):
    """The point a whole-frame card centres on: the face the cast names, else the person's point."""
    face = photos.info(role).get("face") if role != "group" else None
    if face:
        return (face[0] + face[2]) / 2, (face[1] + face[3]) / 2
    info = photos.info(role)
    return tuple(info.get("point") or (0.5, 0.45))


def stacked(text, face, size, x, bottom, room, most=4, lo=40, color="ink", name="said", **kw):
    """`text` in the card face `face`, as large as `size` allows wrapping into `most` lines of `room` px, never under
    `lo`, its last baseline at `bottom` and each line a lead over the next: the lines top-down. A line's descent stays
    over `bottom` + its descent, so the block's foot is the baseline given."""
    lo = max(lo, floor_size(face))
    for s in range(size, lo - 1, -2):
        rows = wrap(line(text, face, s, x, 0), room, most)
        if rows or s - 2 < lo:
            break
    rows = rows or [line(text, face, s, x, 0)["text"]]
    lead_ = s * lead(face)
    n = len(rows)
    out = []
    for j, r in enumerate(rows):
        y = bottom - (n - 1 - j) * lead_
        extra = dict(kw)
        if extra.get("rotate"):
            extra["pivot"] = [round(x, 1), round(y, 1)]
        out.append(line(r, face, s, x, y, color=color, name=f"{name}-{j}", **extra))
    return out


def top_of(lines):
    return min(hull(turned(box(ln, ink=True), ln))[1] for ln in lines)


def foot_of(lines):
    return max(hull(turned(box(ln, ink=True), ln))[3] for ln in lines)


def beside(F, photos, role, face, y_to):
    """The picture moved across so the named `face` stands against the safe area's side it leans to, and the column the
    type takes on the other side: (place, x from, x to, the scrim along x), or None when the photograph is too narrow to
    leave a column of SIDE_LEAST px."""
    at = focus_of(photos, role)
    first = bleed(F, photos, role, at, y_to)
    fw = (face[2] - face[0]) * first[2]
    right = at[0] >= 0.5
    cx = F.right - fw / 2 if right else F.left + fw / 2
    place = bleed(F, photos, role, at, y_to, x_to=cx / F.W)
    fx0, fx1 = place[0] + face[0] * place[2], place[0] + face[2] * place[2]
    x0, x1 = (F.left + 2, fx0 - GAP) if right else (fx1 + GAP, F.right - 4)
    if x1 - x0 < SIDE_LEAST:
        return None
    # dark behind the column, clear again over the face's near side
    scrim = [round(fx0 + 40, 1), round(x1 - 60, 1)] if right else [round(fx1 - 40, 1), round(x0 + 60, 1)]
    return place, x0, x1, scrim


def boxes_of(lines):
    """The inked boxes of `lines`: what of each covers the picture under it."""
    return [hull(turned(box(ln, ink=True), ln)) for ln in lines]


def bright(lk, role):
    """The role a line stands in over a photograph darkened by its scrim: the card's own color when it is light enough
    to read on the dark, else paper."""
    return role if lk.L(role) >= 55 else max(("ink", "paper"), key=lk.L)


def band_tag(F, text, tip, size, foot):
    """The name as a marquee band: a strip of the accent across the whole frame, its foot at `foot` px, the name set in
    the card's text face from the safe area's left, no pointer. Its tip is the person, where the tag opens from."""
    h = BAND_H * size
    ln = line(text, "text", size, 0, 0)
    return {"text": ln["text"], "file": ln["file"], "size": size, "tip": [round(tip[0], 1), round(tip[1], 1)], "side": "below",
            "shape": "band", "inset": round(F.left + BAND_OUT, 1),
            "box": [-BAND_OUT, round(foot - h, 1), F.W + BAND_OUT, round(foot, 1)]}


def sticker_tag(F, text, tip, size, mid, turn):
    """The name as a sticker: a rounded label in the accent with a white edge, turned `turn` degrees, centred on `mid`
    and slid inside the safe area, no pointer."""
    ln = line(text, "text", size, 0, 0)
    w, h = width(ln) + 2 * PILL_PAD * size, STICKER_H * size
    x = max(F.left + 6, min(F.right - 6 - w, mid[0] - w / 2))
    y = max(F.top + 6, min(F.bottom - 6 - h, mid[1] - h / 2))
    return {"text": ln["text"], "file": ln["file"], "size": size, "tip": [round(tip[0], 1), round(tip[1], 1)], "side": "below",
            "shape": "sticker", "turn": turn, "box": [round(x, 1), round(y, 1), round(x + w, 1), round(y + h, 1)]}


def stamp_tag(F, text, tip, size, x, y):
    """The name as a small stamp in a corner: the name in the accent inside a thin accent frame, its top left at (x, y),
    no pointer and no fill."""
    ln = line(text, "text", size, 0, 0)
    w, h = width(ln) + 2 * PILL_PAD * size, STAMP_H * size
    return {"text": ln["text"], "file": ln["file"], "size": size, "tip": [round(tip[0], 1), round(tip[1], 1)], "side": "below",
            "shape": "stamp", "turn": -2, "ink": "accent", "box": [round(x, 1), round(y, 1), round(x + w, 1), round(y + h, 1)]}


def wall_shape(t):
    """A tag on the closer's wall in the look's own shape: a solid block where the cards carry bands, a stamp, a sticker
    turned the way its slice leans; a pill where the look points at people."""
    frame = frame_of()
    if frame == "bleed":
        return dict(t, shape="block")
    if frame == "footage":
        return dict(t, shape="stamp", ink="accent", turn=-2)
    if frame == "print":
        return dict(t, shape="sticker", turn=4 if int(t.get("owner", 0)) % 2 else -4)
    return t


def face_box(face, place):
    x, y, w, h = place
    return (x + face[0] * w, y + face[1] * h, x + face[2] * w, y + face[3] * h)


def eyes_clear(face, place, boxes):
    """True when none of `boxes` covers the upper part of the named `face` (its eyes and nose: EYES of its height from
    its top) laid at `place`; always, when no face is named."""
    if not face:
        return True
    f = face_box(face, place)
    f = (f[0], f[1] - CROWN * (f[3] - f[1]), f[2], f[1] + EYES * (f[3] - f[1]))
    return not any(b[0] < f[2] and f[0] < b[2] and b[1] < f[3] and f[1] < b[3] for b in boxes)


def typed_scrim(photos, role, place, lines, lk):
    """The dark behind a home movie's typed lines: scrim_over theirs, and where the photograph behind them is bright
    (its upper quartile lighter than TYPED_BRIGHT, CIE L*) at least TYPED_DARK dark, and dark already at the top
    line's cap, so every letter stands on it."""
    top = top_of(lines)
    clear, dark_at, dark = scrim_over(top, lk)
    try:
        im = pixels(f"matched/{role}.jpg")
    except OSError:
        return [clear, dark_at, dark]
    x, y, w, h = place
    iw, ih = im.size
    x0, y0, x1, y1 = hull([q for ln in lines for q in turned(box(ln, ink=True), ln)])
    ls = [lab(im.getpixel((min(iw - 1, max(0, int((X - x) / w * iw))), min(ih - 1, max(0, int((Y - y) / h * ih))))))[0]
          for X in [x0 + (x1 - x0) * i / 11 for i in range(12)] for Y in [y0 + (y1 - y0) * j / 7 for j in range(8)]]
    ls.sort()
    if ls[len(ls) * 3 // 4] < TYPED_BRIGHT:
        return [clear, dark_at, dark]
    return [clear, round(top - GAP, 1), max(dark, TYPED_DARK)]


def scrim_over(top, lk):
    """The dark that rises behind a whole-frame card's type: clear `SCRIM_IN` px over the type's top, as dark as the card
    says at its top and on down to the frame's foot."""
    dark = lk.card["photo"]["line"].get("scrim") or 0.6
    return [round(top - SCRIM_IN, 1), round(top + 40, 1), dark]


def whole_card(F, photos, p, said, i, move):
    """A person's card in a look whose photograph takes the whole frame (`bleed`, `footage`) or the page holds one print
    (`print`): (edge, role, layers, fit). Their words and stamp keep off the eyes the cast names, shrinking to the type's
    least size; a card that cannot keep them off is laid all the same, and says so in `fit`."""
    lk = look()
    frame = frame_of()
    role = f"{p.handle}-0"
    tip, head = subject(photos, role)
    face = photos.info(role).get("face")
    edge = aside(F)
    how = drawn(move)
    spec, label = lk.card["photo"]["line"], lk.card["photo"]["label"]
    words_mode = how.get("words", "rise")
    say = "rise"
    extra = {}
    if frame in ("bleed", "footage"):
        place = bleed(F, photos, role, focus_of(photos, role), 0.36 if frame == "bleed" else 0.4)
        at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
        ok = True
        if frame == "bleed":
            say = "slam"
            color = bright(lk, spec["color"])
            lab_size = max(round(label["size"] * 1.15), floor_size(label["face"]))
            lay = lambda x0, room, most, k: slam(F, p, said, spec, label, lab_size, color, base, x0, room, most, k)
            t = band_tag(F, f"@{p.handle}", at(*tip), BAND[F.kind], F.bottom)
            base = t["box"][1] - GAP
            for k in (1.0, 0.86, 0.74, 0.64, 0.55, 0.48, 0.42):
                stamp, rest = lay(F.left, F.right - F.left - 4, 4, k)
                ok = eyes_clear(face, place, boxes_of([stamp] + rest)) and top_of([stamp]) >= F.top
                if ok:
                    break
            extra["scrim"] = scrim_over(top_of([stamp]), lk)
            side = beside(F, photos, role, face, 0.36) if not ok and face and said else None
            if side:
                place, x0, x1, scrim = side
                at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
                t = band_tag(F, f"@{p.handle}", at(*tip), BAND[F.kind], F.bottom)
                for k in (1.0, 0.86, 0.74, 0.64, 0.55):
                    stamp, rest = lay(x0, x1 - x0, 7, k)
                    ok = eyes_clear(face, place, boxes_of([stamp] + rest)) and top_of([stamp]) >= F.top
                    if ok:
                        break
                extra["scrim"] = [*scrim, lk.card["photo"]["line"].get("scrim") or 0.6, "x"]
            if not ok and face and said:
                # a face too wide for a column beside it: the month heads the frame over the face and the words keep
                # under the eyes, shrinking as far as the type's least size
                for k in (0.42, 0.38, 0.34, 0.31, 0.28):
                    stamp_, rest_ = lay(F.left, F.right - F.left - 4, 5, k)
                    stamp_["y"] = round(F.top + ink(stamp_)[0], 1)
                    if eyes_clear(face, place, boxes_of([stamp_] + rest_)):
                        ok, stamp, rest = True, stamp_, rest_
                        extra["scrim"] = scrim_over(top_of(rest), lk)
                        break
            tags = [t]
        else:
            say = "type"
            words_mode = "date"
            color = bright(lk, spec["color"])
            date = line(p.stamp, label["face"], max(round(label["size"] * TYPED_DATE), floor_size(label["face"])), F.right - 2, 0,
                        color="accent", anchor="end", name=f"stamp-{p.rank}")
            date["y"] = round(F.bottom - ink(date)[1], 1)
            room = min(spec["box"][2] * F.W, F.right - F.left - 4)
            foot = date["y"] - ink(date)[0] - GAP

            def typed(x0, room, most, k):
                out = stacked(said, spec["face"], round(spec["size"] * TYPED * k), x0, foot, room, most,
                              lo=round(spec["size"] * TYPED_K[-1] * TYPED), color=color, name=f"said-{p.rank}") if said else []
                return [dict(ln, y=round(ln["y"] - ink(out[-1])[1], 1)) for ln in out]
            for k in TYPED_K:
                rest = typed(F.left + 2, room, TYPED_MOST, k)
                ok = eyes_clear(face, place, boxes_of([date] + rest))
                if ok:
                    break
            extra["scrim"] = typed_scrim(photos, role, place, [date] + rest, lk)
            side = beside(F, photos, role, face, 0.4) if not ok and face and said else None
            if side:
                place, x0, x1, scrim = side
                at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
                for k in TYPED_K:
                    rest = typed(x0, x1 - x0, 7, k)
                    ok = eyes_clear(face, place, boxes_of([date] + rest))
                    if ok:
                        break
                extra["scrim"] = [*scrim, lk.card["photo"]["line"].get("scrim") or 0.6, "x"]
            stamp = date
            # the name's stamp takes a top corner clear of the eyes, else the foot's free corner beside the date, else
            # stands over the typed line
            s_ = max(label["size"], floor_size("text"))
            corners = [stamp_tag(F, f"@{p.handle}", at(*tip), s_, F.left + 2, F.top + 4)]
            t0 = corners[0]
            corners.append(stamp_tag(F, f"@{p.handle}", at(*tip), s_, F.right - 2 - (t0["box"][2] - t0["box"][0]), F.top + 4))
            th = t0["box"][3] - t0["box"][1]
            corners.append(stamp_tag(F, f"@{p.handle}", at(*tip), s_, F.left + 2, F.bottom - th))
            over_type = top_of(rest or [date]) - GAP - th
            corners.append(stamp_tag(F, f"@{p.handle}", at(*tip), s_, rest[0]["x"] if rest else F.left + 2, over_type))
            inked = boxes_of([date] + rest)
            t = next((c for c in corners if eyes_clear(face, place, [c["box"]])
                      and not any(c["box"][0] < e[2] and e[0] < c["box"][2] and c["box"][1] < e[3] and e[1] < c["box"][3] for e in inked)),
                     None)
            if t is None:
                # the stamp takes the foot's corner beside the date, and the typed line rises over it
                low = stamp_tag(F, f"@{p.handle}", at(*tip), s_, F.left + 2, F.bottom - th)
                foot = low["box"][1] - GAP
                x0_ = rest[0]["x"] if rest else F.left + 2
                width = (x1 - x0) if side else room
                for k in TYPED_K:
                    risen = typed(x0_, width, 7 if side else TYPED_MOST, k)
                    d = boxes_of([date])[0]
                    beside_date = low["box"][2] < d[0]
                    if beside_date and eyes_clear(face, place, boxes_of(risen) + [low["box"]]):
                        rest, t = risen, low
                        extra["scrim"] = typed_scrim(photos, role, place, rest, lk) if not side else extra["scrim"]
                        break
            t = t or corners[0]
            tags = [t]
        photo_ = whole_photo(photos, role)
        field = "photo"
    else:
        place, crop, tags, stamp, rest, ok, keepsake = print_card(F, photos, p, said, i, spec, label)
        extra["crop"] = crop
        if keepsake:
            extra["keepsake"] = keepsake
        photo_ = photo(photos, role)
        field = lk.ground
    entry = PRINT_ENTRY[i % len(PRINT_ENTRY)] if frame == "print" else entry_of(move)
    return edge, role, [
        {"kind": "Cut", "at": 0, "line": edge.line, "field": field, "photo": photo_, "place": place, "entry": entry,
         "words": words_mode, "say": say, **extra},
        {"kind": "Words", "at": CUT, "lines": [stamp], "beats": 0.5},
        {"kind": "Words", "at": CUT + RISE, "lines": rest, "beats": 0.4, "step": 0.08},
        {"kind": "Tags", "at": LAND, "tags": tags},
    ], ok


def slam(F, p, said, spec, label, lab_size, color, base, x0, room, most, k):
    """A bleed card's month and words in a column from `x0`, `room` px wide, the words' last line on `base` and the
    month over them, at `k` of the card's size: (stamp, lines)."""
    rest = stacked(said, spec["face"], round(spec["size"] * k), x0, base, room, most, lo=48, color=color,
                   name=f"said-{p.rank}") if said else []
    if rest:
        rest = [dict(ln, y=round(ln["y"] - ink(rest[-1])[1], 1)) for ln in rest]
    stamp = line(p.stamp, label["face"], lab_size, x0 + 2, 0, color=color, name=f"stamp-{p.rank}")
    stamp["y"] = round((top_of(rest) if rest else base) - GAP - ink(stamp)[1], 1)
    return stamp, rest


def print_box(F, photos, role, top, foot, at):
    """The whole picture's box and the crop that make a photograph one print standing from `top` to `foot` px (or less,
    when its width runs out first), PRINT_W of the frame wide at most and centred across it, cropped at its sides around
    `at` (fractions) to that width: (place, crop, print height)."""
    a = photos.aspect[role]
    b0, b1 = photos.band[role] if photos.framed(role) else (0.0, 1.0)
    k = b1 - b0
    pw = PRINT_W * F.W
    ph = min(foot - top, pw * k * a * PRINT_CROP)
    ih = ph / k
    iw = ih / a
    w = min(pw, iw)
    x0 = F.W / 2 - w / 2
    ix = max(x0 + w - iw, min(x0, F.W / 2 - at[0] * iw))
    return [round(ix, 1), round(top - b0 * ih, 1), round(iw, 1), round(ih, 1)], [round(x0, 1), round(x0 + w, 1)], ph


def centred(F, mid, size, rot):
    """The width a line `size` px set on the frame's middle `mid` and turned `rot` degrees may take inside the safe area,
    which stands off the frame's middle: twice its nearer side, less what the turn carries its corners out."""
    return 2 * min(mid - F.left, F.right - mid) - 8 - 2 * size * math.sin(math.radians(abs(rot)))


def print_card(F, photos, p, said, i, spec, label):
    """A person's print on the page: the photograph as one tilted, taped print filling the page over its caption, the
    person's words hand-lettered under it and the month under them in the accent, their name a sticker on the print's
    corner on their side; on a page with a lower third the month is stamped there instead, beside a keepsake print
    (keepsake_of). The composition stands in the middle of the safe area when the print runs out of width before
    height: (place, crop, tags, month, words, fit, keepsake or None)."""
    role = f"{p.handle}-0"
    tip, head = subject(photos, role)
    face = photos.info(role).get("face")
    pic = look().card["photo"]["picture"]
    mid = F.W / 2
    rot = spec.get("rotate", 0) or 0
    size = spec["size"]
    low = F.H - F.bottom >= KEEPSAKE_ROOM
    month = line(p.stamp, label["face"], max(round(label["size"] * 1.3), floor_size(label["face"])), mid, 0, color="accent",
                 anchor="middle", name=f"stamp-{p.rank}")
    month["y"] = round(F.bottom - ink(month)[1], 1)
    foot = F.bottom if low else month["y"] - ink(month)[0] - GAP
    rest = stacked(said, spec["face"], size, mid, foot, centred(F, mid, size, rot), 3, lo=56,
                   color=look().on_ground, name=f"said-{p.rank}", anchor="middle", rotate=rot) if said else []
    if rest:
        rest = [dict(ln, y=round(ln["y"] - ink(rest[-1])[1], 1)) for ln in rest]
        for ln in rest:
            ln["pivot"] = [round(mid, 1), ln["y"]]
        # the hand's turn carries a line's corner under its baseline: the caption rises until its ink stands on the foot
        over = foot_of(rest) - foot
        if over > 0:
            rest = [dict(ln, y=round(ln["y"] - over, 1), pivot=[ln["pivot"][0], round(ln["pivot"][1] - over, 1)]) for ln in rest]
    keepsake = None
    if low:
        keepsake, month = keepsake_of(F, photos, p, i, label, foot_of(rest) if rest else F.bottom)
    words_top = top_of(rest if low and rest else [month] + rest)
    s = STICKER[F.kind]
    hang = STICKER_H * s / 2
    rim = pic.get("rim", 0) * PRINT_W * F.W
    # the sticker stands on the print's lower corner, half over the rim: its foot stays a gap over the words
    foot = words_top - GAP - rim - hang - 6
    top = F.top - PRINT_OVER
    place, crop, ph = print_box(F, photos, role, top, foot, focus_of(photos, role))
    slack = foot - (top + ph)
    if slack > 1:
        # the print ran out of width first: the whole composition moves down to the middle of what it leaves
        place = [place[0], round(place[1] + slack / 2, 1), place[2], place[3]]
        top += slack / 2
    pb = top + ph
    at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
    side = 0 if tip[0] * place[2] + place[0] < mid else 1
    corner = (crop[0] + 0.2 * (crop[1] - crop[0]), pb + rim) if side == 0 else (crop[1] - 0.2 * (crop[1] - crop[0]), pb + rim)
    turn = -6 if side == 0 else 6
    t = sticker_tag(F, f"@{p.handle}", at(*tip), s, corner, turn)
    ok = face_clear(F, face, place, [t["box"]]) if face else True
    return place, crop, [t], month, rest, ok, keepsake


def keepsake_of(F, photos, p, i, label, words_foot):
    """The page's lower third under a print's caption, where a reel has one: a second, smaller print of the person's
    year (their next photograph, else a close crop of the face in this one), taped on turned, on one side, and the month
    stamped low on the other, turned the other way and set larger than a caption's month. The sides swap from one
    person to the next. (keepsake for the Cut layer, the month's line)."""
    role = f"{p.handle}-1" if f"{p.handle}-1" in photos.aspect else f"{p.handle}-0"
    right = i % 2 == 0
    w = KEEPSAKE_W * F.W
    h = w * KEEPSAKE_ASPECT
    top = words_foot + KEEPSAKE_GAP
    cx = F.W * (0.69 if right else 0.31)
    a = photos.aspect[role]
    b0, b1 = photos.band[role] if photos.framed(role) else (0.0, 1.0)
    fx, fy = focus_of(photos, role)
    if role.endswith("-0"):
        face = photos.info(role).get("face")
        if face:
            fx, fy = (face[0] + face[2]) / 2, (face[1] + face[3]) / 2
    # the picture's own width over its height, and the window's
    r = 1 / (a * (b1 - b0))
    wr = w / h
    if role.endswith("-0"):
        # a close crop: half the picture's width round the face
        du = min(1.0, 0.5 * max(1.0, wr / r))
        dv = (b1 - b0) * du * r / wr
    elif r > wr:
        du, dv = wr / r, b1 - b0
    else:
        du, dv = 1.0, (b1 - b0) * r / wr
    u0 = min(1 - du, max(0.0, fx - du / 2))
    v0 = min(b1 - dv, max(b0, fy - dv / 2))
    keep = {"file": f"matched/{role}.jpg", "box": [round(cx - w / 2, 1), round(top, 1), round(cx + w / 2, 1), round(top + h, 1)],
            "uv": [round(u0, 4), round(v0, 4), round(u0 + du, 4), round(v0 + dv, 4)], "turn": KEEPSAKE_TURN if right else -KEEPSAKE_TURN}
    mx = F.W * (0.28 if right else 0.72)
    room = 0.5 * F.W - 2 * KEEPSAKE_PAD
    turn = -KEEPSAKE_STAMP_TURN if right else KEEPSAKE_STAMP_TURN
    size = round(label["size"] * KEEPSAKE_STAMP)
    while True:
        month = line(p.stamp, label["face"], size, mx, 0, color="accent", anchor="middle", name=f"stamp-{p.rank}", rotate=turn)
        if width(month) <= room or size <= floor_size(label["face"]):
            break
        size -= 2
    month["y"] = round(top + h * 0.5 + ink(month)[0] / 2, 1)
    month["pivot"] = [round(mx, 1), month["y"]]
    month["low"] = True
    return keep, month


def stamps_down(F, handles, tip, size):
    """Every name as a stamp from the safe area's top corner, in rows across the top of the frame, each stamp a gap from
    the last."""
    tags, x, y = [], F.left + 2, F.top + 4
    for h in handles:
        tg = stamp_tag(F, h, tip, size, x, y)
        if tg["box"][2] > F.right:
            x, y = F.left + 2, max(t["box"][3] for t in tags) + 10
            tg = stamp_tag(F, h, tip, size, x, y)
        tags.append(tg)
        x = tg["box"][2] + 12
    return tags


def whole_hook(F, ctx, move=None):
    """The hook in a look whose photograph takes the whole frame or whose page holds one print: the photograph of them
    together (the first person's when there is none) edge to edge, or as the print; the handle and the year, the title,
    and every person's name in the film's order in the look's shape: one marquee band carrying them all (`bleed`),
    stamps in rows from the top corner (`footage`), or stickers round the print (`print`)."""
    lk = look()
    frame = frame_of()
    photos = ctx.photos
    role = "group" if "group" in photos.aspect else photos.role(ctx.people[0].handle)
    edge = aside(F)
    spec = lk.card["photo"]["line"]
    label = lk.card["photo"]["label"]
    small = max(SMALL[F.kind], floor_size("text"))
    handles = [f"@{p.handle}" for p in ctx.people]
    focus = focus_of(photos, role)
    extra = {}
    if frame in ("bleed", "footage"):
        place = bleed(F, photos, role, focus, 0.36, over=HOOK_OVER)
        at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
        if frame == "bleed":
            t = band_tag(F, "  ·  ".join(handles), at(*focus), BAND_HOOK[F.kind], F.bottom)
            t["scroll"] = MARQUEE
            tags = [t]
            foot = t["box"][1] - GAP
            color = bright(lk, spec["color"])
            face = "display"
        else:
            tags = stamps_down(F, handles, at(*focus), max(label["size"], floor_size("text")))
            foot = F.bottom
            color = bright(lk, "paper")
            face = "display"
        size = fit_size(line("people.", face, TITLE[F.kind], F.left + 2, 0), F.right - F.left - 6, lo=TITLE_LEAST)
        title = line("people.", face, size, F.left + 2, 0, color=color, name="title-1")
        title["y"] = round(foot - ink(title)[1], 1)
        over = line("my", face, size, F.left + 2, round(title["y"] - size * lead(face), 1), color=color, name="title-0")
        kicker = line(said_by(ctx), "text", small, F.left + 2, 0, color=color)
        kicker["y"] = round(over["y"] - ink(dict(over, text="H"))[0] - GAP, 1)
        if frame == "footage":
            # the stamps run in rows from the top corner to the type's top: a long cast sets them smaller
            room = kicker["y"] - ink(dict(kicker, text="H"))[0] - GAP
            for s_ in range(max(label["size"], floor_size("text")), floor_size("text") - 1, -2):
                tags = stamps_down(F, handles, at(*focus), s_)
                if max(t["box"][3] for t in tags) <= room:
                    break
        extra["scrim"] = scrim_over(top_of([kicker]), lk)
        field = "photo"
        photo_ = whole_photo(photos, role)
    else:
        mid = F.W / 2
        kicker = line(said_by(ctx), label["face"], max(round(label["size"] * 1.2), floor_size(label["face"])), mid, 0,
                      color="accent", anchor="middle")
        kicker["y"] = round(F.bottom - ink(kicker)[1], 1)
        rot = spec.get("rotate", 0) or 0
        # a turned line reaches past its own width by its height times the turn
        size = fit_size(line("my people.", "display", TITLE[F.kind], 0, 0),
                        centred(F, mid, TITLE[F.kind], rot), lo=TITLE_LEAST)
        y = round(kicker["y"] - ink(kicker)[0] - GAP, 1)
        title = line("my people.", "display", size, mid, y, color=lk.on_ground, anchor="middle", name="title-1", rotate=rot,
                     pivot=[round(mid, 1), y])
        title["y"] = round(y - ink(title)[1], 1)
        title["pivot"] = [round(mid, 1), title["y"]]
        # the turn carries the line's top sideways: the turned line is set back on the frame's middle
        h_ = hull(turned(box(title, ink=True), title))
        dx = round(mid - (h_[0] + h_[2]) / 2, 1)
        title["x"], title["pivot"] = round(title["x"] + dx, 1), [round(mid + dx, 1), title["y"]]
        over = None
        pic = lk.card["photo"]["picture"]
        rim = pic.get("rim", 0) * PRINT_W * F.W
        s = STICKER[F.kind]
        foot = top_of([title]) - GAP - rim - 6
        top = F.top - PRINT_OVER
        place, crop, ph = print_box(F, photos, role, top, foot, focus)
        slack = foot - (top + ph)
        if slack > 1:
            place = [place[0], round(place[1] + slack / 2, 1), place[2], place[3]]
            top += slack / 2
        at = lambda u, v: (place[0] + u * place[2], place[1] + v * place[3])
        n = len(handles)
        per = -(-n // 2)
        tags = []
        for j, h in enumerate(handles):
            side, row = j % 2, j // 2
            v = 0.3 + 0.62 * (row / max(1, per - 1)) if per > 1 else 0.6
            x = crop[0] if side == 0 else crop[1]
            tg = sticker_tag(F, h, at(*focus), s, (x, top + v * ph), -6 if (j // 2 + side) % 2 else 6)
            hit = [o for o in tags if o["box"][0] < tg["box"][2] and tg["box"][0] < o["box"][2] and o["box"][1] < tg["box"][3] and tg["box"][1] < o["box"][3]]
            if hit:
                tg = sticker_tag(F, h, at(*focus), s, (x, max(o["box"][3] for o in hit) + STICKER_H * s / 2 + 8), tg["turn"])
            tags.append(tg)
        extra["crop"] = crop
        field = lk.ground
        photo_ = photo(photos, role)
    lines = [over, title] if over else [title]
    layers = [{"kind": "Cut", "at": -4, "line": edge.line, "field": field, "photo": photo_, "place": place,
               "entry": drawn(move).get("entry", "cut") if frame == "print" else "cut", **extra},
              {"kind": "Words", "at": 0, "lines": [kicker], "beats": 0.5},
              {"kind": "Words", "at": TITLE_AT, "lines": lines, "beats": 0.5, "step": 0.12},
              {"kind": "Tags", "at": POP, "step": POP_STEP, "gather": GATHER, "tags": tags, "roll": True}]
    return edge, role, layers


# ------------------------------------------------------------------ the hook
def roll_call(F, ctx, edge):
    """Every person's tag in the film's order, under the hook's edge in rows from the safe area's left, their pointers
    folded into their pills: the roll call the photograph of them together opens on when the cast names no head in it.
    None when the rows run past the safe area's foot."""
    size, gap = TAG[F.kind], 14
    tags, x, y = [], F.left, edge.yc + CLEAR
    for p in ctx.people:
        w = tag(F, f"@{p.handle}", (0, 0), size)["box"]
        w = w[2] - w[0]
        if x + w > F.right + 0.5:
            x, y = F.left, y + PILL_H * size + gap
        tags.append(tag(F, f"@{p.handle}", (x + w / 2, y), size, room=(x, x + w), top=y))
        x += w + gap
    return tags if tags and all(in_frame(F, t) for t in tags) else None


def hook(F, ctx, move=None):
    """The photograph of them together filling the frame, a tag on every head the frame shows, the handle and the year
    at the top (the year alone when the data names no username),
    and the title standing on a level edge: over the heads where the photograph leaves it room, else under the lowest
    tag; each in the color the picture behind it reads in. A framed group (cast.py match laid it whole over a blurred
    copy) is a print on the page where the look tapes one, else lies whole across the frame, or, in a look that fills
    the frame with it, stands on the frame's foot as wide as its heads allow; where its heads lie too high for the edge, the edge rises over them and the title shrinks to
    fit under the year. Where the cast names no head in it, the photograph opens on the roll call of every person's
    tag under the title."""
    if frame_of() != "edge":
        return whole_hook(F, ctx, move)
    photos = ctx.photos
    g = ctx.cast.get("group") or {}
    heads = {h: g["heads"][h] for h in ctx.heads()} if g.get("heads") else {}
    edge = Edge(F, HOOK_EDGE[F.kind], 0)
    called = roll_call(F, ctx, edge) if g and not heads and "group" in photos.aspect else None
    small = max(SMALL[F.kind], floor_size("text"))
    x = F.left + 2
    kicker = line(said_by(ctx), "text", small, x, F.top + small * 1.3)
    size = fit_size(line("people.", "display", TITLE[F.kind], x, 0), F.right - x - 4, lo=TITLE_LEAST)

    def stand(e):
        title = line("people.", "display", size, x, 0, name="title-1")
        title["y"] = round(e - LIFT - ink(dict(title, y=0))[1], 1)
        over = line("my", "display", size, x, 0, name="title-0")
        over["y"] = round(title["y"] - size * lead("display"), 1)
        return over, title

    over, title = stand(edge.yc)
    stack = edge.yc - hull(turned(box(over), over))[1]
    room = hull(turned(box(kicker), kicker))[3] + 12
    role = "group" if heads or called else (photos.role(ctx.people[0].handle) if ctx.people else None)
    if role == "group" and heads:
        a = photos.aspect["group"]
        us = [u for u, _ in heads.values()]
        crown = max(0.02, min(v for _, v in heads.values()) - 0.04)
        spread = max(us) - min(us) or 0.25
        cx = (max(us) + min(us)) / 2
        least = max(F.W, F.H / a)
        widest = (F.right - F.left) / spread
        want = min(widest, F.W * (0.62 if F.kind == "reel" else 0.4) / spread)
        # a framed group taped to the page is a print in the middle of the card's landscape box; in a look that fills
        # the frame with it, it stands on the frame's foot, as wide as filling the frame takes or as the heads allow
        # across the type area, whichever is narrower, its ground over it
        filled = None
        if photos.framed("group") and look().mount == "taped":
            b0, b1 = photos.band["group"]
            lb = look().card["photo"]["landscape"]["box"]
            tall = min(lb[2] * F.W * a * (b1 - b0), lb[3] * F.H)
            filled = print_place(F, a, (b0, b1), F.H * (lb[1] + lb[3] / 2) - tall / 2)
        elif photos.framed("group") and look().fills:
            b0, b1 = photos.band["group"]
            bw = max(F.W, min(F.H / (a * (b1 - b0)), widest))
            ih = bw * a
            ix = max(F.W - bw, min(0.0, F.W / 2 - cx * bw))
            filled = [round(ix, 1), round(F.H - b1 * ih, 1), round(bw, 1), round(ih, 1)]

        def laid(iw, crown_y, clear, low=False):
            # over the title the tags alternate under and over the heads; under it they stand over the heads where they
            # can, so the title stands as high as it may
            if filled:
                ix, iy, iw, ih = filled
            else:
                iw = least if photos.framed("group") else max(least, iw)
                ih = iw * a
                ix = max(F.W - iw, min(0.0, F.W / 2 - cx * iw))
                iy = max(F.H - ih, min(0.0, crown_y - crown * ih))
            place = [round(ix, 1), round(iy, 1), round(iw, 1), round(ih, 1)]
            tags = []
            for n, (h, (u, v)) in enumerate(sorted(heads.items(), key=lambda kv: kv[1][0])):
                sides = ("above", "below") if low or n % 2 else ("below", "above")
                tries = [tag(F, f"@{h}", (ix + u * iw, iy + (v + (0.03 if s == "below" else -0.03)) * ih), TAG[F.kind], side=s)
                         for s in sides]
                # crowded heads stagger: a tag under a head its neighbor's tag stands over hangs under that tag
                under = next(t for t in tries if t["side"] == "below")
                hit = [o["box"][3] for o in tags if o["box"][0] < under["box"][2] and under["box"][0] < o["box"][2]]
                if hit:
                    tries.append(tag(F, under["text"], tuple(under["tip"]), TAG[F.kind], side="below", top=max(hit) + 8))
                tags.append(next((t for t in tries if hook_tag_fits(F, t, clear, tags)), tries[0]))
            inside = all(hook_tag_fits(F, t, clear, tags[:i]) for i, t in enumerate(tags))
            return place, tags, inside

        # the title over the heads where the photograph leaves it room (the crown a tag's height under the edge, so a tag
        # over a head stays under it), else standing under the lowest tag
        crown_y = edge.yc + CLEAR + (POINTER + PILL_H) * TAG[F.kind]
        crown_at = filled[1] + crown * filled[3] if filled else crown * least * a
        if photos.framed("group") and crown_at < crown_y:
            # a framed group holds its heads where it lies: the edge rises over them and the title takes the height
            # left between the year and the edge, unless that leaves it smaller than the title's least size
            e = crown_at - (crown_y - edge.yc)
            fits = int(size * (e - room) / stack)
            if fits >= TITLE_LEAST:
                size, edge, crown_y = min(size, fits), Edge(F, e, 0), crown_at
                over, title = stand(e)
                stack = e - hull(turned(box(over), over))[1]
        place, tags, inside = laid(max(want, crown_y / crown / a), crown_y, edge.yc + 8)
        if not inside:
            low, low_tags, _ = laid(want, -F.H, room, low=True)
            short = room - min((min(t["box"][1], t["tip"][1]) for t in low_tags), default=room)
            low, low_tags, low_inside = laid(want, low[1] + max(0.0, short) + crown * low[3], room, low=True)
            under = max((t["box"][3] for t in low_tags), default=F.H) + CLEAR
            # the title shrinks to the room left under the tags, never under its least size
            fits = int(size * (F.bottom - under) / stack)
            if fits < size and fits >= TITLE_LEAST:
                size, stack = fits, stack * fits / size
            e = under + stack
            if low_inside and e <= F.bottom:
                place, tags = low, low_tags
                edge = Edge(F, e, 0)
                over, title = stand(e)
            else:   # no head the frame shows takes a tag: the first person's photograph opens the film
                role = photos.role(ctx.people[0].handle)
    if role != "group" or called:
        tip, head = subject(photos, role)
        if photos.framed(role) and look().mount == "taped":
            # the print stands below the roll call's tags, clear of them
            under = max([t["box"][3] for t in called or []] + [max(edge.yl, edge.yr)])
            place = print_place(F, photos.aspect[role], photos.band[role], under + TAPED)
        elif photos.framed(role) and look().fills:
            place, _ = cover_band(F, photos.aspect[role], photos.band[role], edge, head, F.W / 2)
        else:
            place, _ = cover(F, photos.aspect[role], edge, head, F.W / 2, top=0, most=1.0 if photos.framed(role) else MAXZ)
        tags = called or []
        face = photos.info(role).get("face") if role != "group" else None
        if face:
            # the title and the edge it stands on stay off the face: on the edge where it lies, else over the face,
            # else under it, the title shrinking to the room it has there, never under its least size
            fy0, fy1 = place[1] + face[1] * place[3], place[1] + face[3] * place[3]
            first = size
            over_face = min(first, int(first * (fy0 - CLEAR - room) / stack))
            under_face = min(first, int(first * (F.bottom - fy1 - CLEAR) / stack))
            for e, size in ((edge.yc, first), (fy0 - CLEAR, over_face), (fy1 + CLEAR + stack * under_face / first, under_face)):
                if size < TITLE_LEAST:
                    continue
                o, t_ = stand(e)
                if (hull(turned(box(o), o))[1] >= room - 0.5 and e <= F.bottom + 0.5 and not fy0 < e < fy1
                        and face_clear(F, face, place, [hull(turned(box(ln), ln)) for ln in (o, t_)])):
                    edge, over, title = Edge(F, e, 0), o, t_
                    break
            else:
                size = first
    file = f"matched/{role}.jpg"
    band = photos.band[role] if photos.framed(role) else None
    if photos.framed(role) and look().mount == "taped":
        # a print taped to the page: the page is the field, and the type reads in the ground's own color on it
        field = look().ground
        kicker, over, title = (dict(ln, color=look().on_ground) for ln in (kicker, over, title))
    else:
        field = "photo"
        kicker = toned(F, file, place, kicker, band)
        tone = tone_of(F, file, place, [over, title], band)[0]
        over, title = dict(over, color=tone), dict(title, color=tone)
    layers = [{"kind": "Cut", "at": -4, "line": edge.line, "field": field, "photo": photo(photos, role), "place": place,
               "entry": drawn(move).get("entry", "cut")},
              {"kind": "Words", "at": 0, "lines": [kicker], "beats": 0.5},
              {"kind": "Words", "at": TITLE_AT, "lines": [over, title], "beats": 0.5, "step": 0.12}]
    if tags:
        layers.append({"kind": "Tags", "at": POP, "step": POP_STEP, "gather": GATHER, "tags": tags, **({"roll": True} if called else {})})
    return edge, role, layers


# ------------------------------------------------------------------ the closer
def columns(F, k):
    w = (F.W + GUT) / k
    return [(-BLEED if j == 0 else round(j * w, 1), F.W + BLEED if j == k - 1 else round((j + 1) * w - GUT, 1)) for j in range(k)]


def piece(F, span, top, bottom):
    xa, xb = span
    over = abs(math.tan(math.radians((top or bottom).tilt))) * F.W + BLEED
    ya = (top.y(xa), top.y(xb)) if top else (-over, -over)
    yb = (bottom.y(xa), bottom.y(xb)) if bottom else (F.H + over, F.H + over)
    return [[round(x, 1), round(y, 1)] for x, y in ((xa, ya[0]), (xb, ya[1]), (xb, yb[1]), (xa, yb[0]))]


def shown(poly, W, H):
    (xa, ya), (xb, yb), (_, zb), (_, za) = poly
    x0, x1 = max(0.0, xa), min(float(W), xb)
    if x1 <= x0:
        return 0.0

    def tall(x):
        f = (x - xa) / (xb - xa)
        return min(H, za + (zb - za) * f) - max(0, ya + (yb - ya) * f)

    return min(x1 - x0, tall(x0), tall(x1))


def crossing(a, b, depth=1.0):
    for poly in (a, b):
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y0 - y1, x1 - x0
            k = math.hypot(nx, ny)
            if k < 1e-9:
                continue
            pa = [(x * nx + y * ny) / k for x, y in a]
            pb = [(x * nx + y * ny) / k for x, y in b]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) <= depth:
                return False
    return True


def band_of(photos, role):
    """The rows [v0, v1] of a photograph's picture that hold the photograph itself: a framed photograph's band (the
    rest is the blurred field it lies over), else the whole picture."""
    return tuple(photos.band[role]) if photos.framed(role) else (0.0, 1.0)


def slice_place(photos, role, poly, focus, F, to_y=None, to_x=None):
    """The picture laid so its photograph (a framed photograph's band, never its blurred field) fills the part of `poly`
    the frame shows, its `focus` (fractions of the picture) in its middle, or at height `to_y` and across at `to_x` px
    when given; never so
    large that the slice shows under half its shorter side or only part of the face its cast names, so where filling
    would do that it stands smaller, whole across the slice's paper. The place is the whole picture's."""
    xs, ys = [x for x, _ in poly], [y for _, y in poly]
    x0, y0, x1, y1 = max(-BLEED, min(xs)), max(-BLEED, min(ys)), min(F.W + BLEED, max(xs)), min(F.H + BLEED, max(ys))
    v0, v1 = band_of(photos, role)
    a = photos.aspect[role] * (v1 - v0)
    into = lambda v: (v - v0) / (v1 - v0)
    focus = (focus[0], into(focus[1]))
    iw = max(x1 - x0, (y1 - y0) / a)
    if to_y is not None:
        iw = max(iw, (y1 - to_y) / max(0.05, 1 - focus[1]) / a, (to_y - y0) / max(0.05, focus[1]) / a)
    seen = shown(poly, F.W, F.H)
    face = photos.info(role).get("face") if role != "group" else None
    face = [face[0], into(face[1]), face[2], into(face[3])] if face else None
    iw = min([iw, 2 * seen / min(1.0, a)] + ([(seen - 2 * FACE) / (face[2] - face[0]), (seen - 2 * FACE) / (face[3] - face[1]) / a] if face else []))
    ih = iw * a
    # a photograph narrower than the slice stands at its right, leaving the type hung at its left on the paper; one
    # shorter stands inside the part of it the frame shows
    inner = (max(0.0, x0), max(0.0, poly[0][1], poly[1][1]), min(float(F.W), x1), min(float(F.H), poly[2][1], poly[3][1]))
    ix = clamp((to_x if to_x is not None else (x0 + x1) / 2) - focus[0] * iw, *((x1 - iw, x0) if iw >= x1 - x0 else (inner[2] - iw, inner[2] - iw)))
    cy = (to_y if to_y is not None else (y0 + y1) / 2) - focus[1] * ih
    iy = clamp(cy, *((y1 - ih, y0) if ih >= y1 - y0 else (inner[1], max(inner[1], inner[3] - ih))))
    if face:   # the face stays whole inside the slice, the photograph leaving paper beside it where it has to
        ix = clamp(ix, inner[0] + FACE - face[0] * iw, inner[2] - FACE - face[2] * iw)
        iy = clamp(iy, inner[1] + FACE - face[1] * ih, inner[3] - FACE - face[3] * ih)
    whole = ih / (v1 - v0)
    return [round(ix, 1), round(iy - v0 * whole, 1), round(iw, 1), round(whole, 1)]


def shot(photos, role, pl):
    """The px box [x, y, w, h] the photograph itself takes in a picture laid at `pl`: its band, for a framed one."""
    v0, v1 = band_of(photos, role)
    return [pl[0], pl[1] + v0 * pl[3], pl[2], (v1 - v0) * pl[3]]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def trimmed(poly, pl):
    """The slice `poly` cut down to the photograph laid at `pl`: what of the slice the photograph covers."""
    (xa, ta), (xb, tb), (_, bb), (_, ba) = poly
    px, py, pw, ph = pl
    at = lambda u, v, x: u + (v - u) * (x - xa) / (xb - xa)
    l, r = max(xa, px), min(xb, px + pw)
    return [[round(x, 1), round(y, 1)] for x, y in ((l, max(at(ta, tb, l), py)), (r, max(at(ta, tb, r), py)),
                                                    (r, min(at(ba, bb, r), py + ph)), (l, min(at(ba, bb, l), py + ph)))]


def chip(F, p, span, edge, size, side="left"):
    """A person's stamp hanging under a closer edge in their slice, at its left or its right `side`: one line at the
    largest size down to the floor that fits the slice, else the place over the month, set flush to that side."""
    x0, x1 = max(F.left + 2, span[0] + 22), min(span[1] - 16, F.right - 2)
    lo = max(floor_size("display"), 32)
    parts = [p.stamp]
    if ", " in p.stamp and width(line(p.stamp, "display", max(lo, min(size, 40)), 0, 0)) > x1 - x0:
        place, when = p.stamp.split(", ", 1)
        parts = [place + ",", when]
    nums = [line(t, "display", size, 0, 0, name=f"stamp-{p.rank}") for t in parts]
    while nums[0]["size"] > lo and max(width(n) for n in nums) > x1 - x0:
        for n in nums:
            n["size"] -= 2
    lead = round(nums[0]["size"] * 1.08)
    x = x0 if side == "left" else x1
    for _ in range(3):
        for k, n in enumerate(nums):
            n.update(x=round(x if side == "left" else x - width(n), 1))
            # level, the first cap clear of the edge where it falls lowest over the stamp; the month a line under it
            y = max(edge.y(n["x"]), edge.y(n["x"] + width(n))) + LIFT + ink(n)[0] if not k else nums[0]["y"] + lead
            n.update(y=round(y, 1))
        h = hulls(nums)
        dx = max(0.0, F.left - h[0]) - max(0.0, h[2] - F.right)
        if not dx:
            break
        x += dx + (1 if dx > 0 else -1)
    return nums


def hulls(lns, ink_only=False):
    """The box around every line in `lns` as it stands turned."""
    hs = [hull(turned(box(ln, ink=ink_only), ln)) for ln in lns]
    return [min(h[0] for h in hs), min(h[1] for h in hs), max(h[2] for h in hs), max(h[3] for h in hs)]


def hung(F, photos, role, p, span, edge, size, pl):
    """A person's stamp hanging under `edge` in their slice at its left, or at its right where the left would cover the
    face its cast names over the photograph laid at `pl`; None when both would. Where no face is named (a back, a
    silhouette, hands) it hangs on the side clear of the point the cast keeps in view, else at the left."""
    info = photos.info(role) if role != "group" else {}
    face = info.get("face")
    u, v = info.get("point") or (0.5, 0.5)
    keep = face or [u - 0.06, v - 0.1, u + 0.06, v + 0.1]
    sides = [chip(F, p, span, edge, size, side) for side in ("left", "right")]
    for nums in sides:
        if face_clear(F, keep, pl, [hull(turned(box(n, ink=True), n)) for n in nums]):
            return nums
    return None if face else sides[0]


def reach(lines, edge, ink_only=True):
    lo = hi = 0.0
    for ln in lines:
        for x, y in turned(box(ln, ink=ink_only), ln):
            lo, hi = min(lo, y - edge.y(x)), max(hi, y - edge.y(x))
    return -lo, hi


def said_by(ctx):
    """The line that signs the film: the handle and the year, or the year alone when the data names no username."""
    return f"@{ctx.handle} · {ctx.year}" if ctx.handle else f"{ctx.year}"


def hero_lines(F, ctx, edge, q):
    """The handle and the year, and under them the title, "my people.", standing on the closer's last edge on the wall's
    ground at its left, as the title stands on the hook's edge: the largest type on the wall, at stamp size `q`."""
    x = F.left + 2
    on = look().on_ground
    size = fit_size(line("my people.", "display", round(WALL_TITLE[F.kind] * q), x, 0), F.right - x - 4, lo=TITLE_LEAST)
    title = line("my people.", "display", size, x, 0, color=on, name="handle-1")
    title["y"] = round(min(edge.y(x), edge.y(x + width(title))) - LIFT - ink(title)[1], 1)
    said = line(said_by(ctx), "text", max(SMALL[F.kind], floor_size("text")), x + 4, 0, color=on, name="handle-0")
    said["y"] = round(title["y"] - ink(title)[0] - GAP - ink(said)[1], 1)
    return [said, title]


def closer(F, ctx, roles, before):
    """The closer's wall: the people in the film's order in rows as even as the format's slices across allow, the last
    across its foot with the handle and the title standing on its edge (where the card's closer draws them, its own
    shape does); every slice cut along parallel edges turned to
    the edge the last person's card left. Every person the film names is on it: the wall is the frame's height when its rows
    lay out there, else it grows downward, its rows over the last ROWS tall in turn, and the Route layer carries its
    height."""
    people = ctx.people
    k = ACROSS[F.kind]
    rest = people[:-1]
    n = -(-len(rest) // k)
    rows = [rest[i * len(rest) // n:(i + 1) * len(rest) // n] for i in range(n)] + [[people[-1]]]
    tilt = max(-6, min(6, before.tilt))
    cut = set()
    # a level card leaves the wall level, and a wall that cannot lay out level turns a little either way
    turns = [round(tilt * f, 2) for f in (1.0, 0.5, 0.0)] + ([3.0, -3.0] if abs(tilt) < 1 else [])
    for row in (None,) + ROWS:
        for turn in turns:
            for q in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
                got = lay(F, ctx, rows, roles, q, turn, cut, row)
                if not got:
                    continue
                height, layers = got
                return [{"kind": "Cut", "at": 0, "line": [height, height], "from": before.line, "field": look().ground},
                        {"kind": "Route", "at": ROUTE_AT, "beats": ROUTE, "height": height}] + layers
    why = (f": every wall cuts the face in, shows only a band of, or has no room for the tag or the stamp on {', '.join(sorted(cut))}; in "
           "cast.json give that person a face box that holds the face alone, or give them another moment, its photograph in "
           "cast.json and its words and stamp in taste.json together") if cut else ""
    raise Unfit(f"the drive closer has no layout for {len(people)} people in {F.kind}{why}", cut)


def clear_of(ln):
    """The box a wall tag keeps out of around a line: its letters' ink and 8 px, since the line box of a face with deep
    metrics runs well past its letters."""
    h = hull(turned(box(ln, ink=True), ln))
    return [h[0] - 8, h[1] - 8, h[2] + 8, h[3] + 8]


def wall_tag(F, photos, role, handle, pl, poly, avoid):
    """A person's tag on the wall, never over their face nor over the `avoid` boxes: pointing up at their chin from
    under it inside their slice (`poly`, its paper beside a photograph narrower than the slice included), else down at the top of their head (their tag's point when no face is named) from over
    it inside their slice, else up at their chin from under the stamp it would cover inside their slice, else up at
    their chin hanging over the gutter under it, always inside the safe area, each slid along past the boxes it would
    cover while its pill stays over its tip; None when none of these is clear."""
    info = photos.info(role)
    face = info.get("face")
    tip, head = subject(photos, role)
    chin = (face[0] + face[2]) / 2 if face else tip[0], face[3] + 0.01 if face else tip[1]
    over = (head[0], max(0.0, head[1] - 0.01)) if face else tip
    at = lambda u, v: (pl[0] + u * pl[2], pl[1] + v * pl[3])
    xs, ys = [x for x, _ in poly], [y for _, y in poly]
    room = (max(F.left, min(xs) + 8), min(F.right, max(xs) - 8))
    size, text = WALL_TAG[F.kind], f"@{handle}"
    hits = lambda t: [b for b in avoid if t["box"][0] < b[2] and b[0] < t["box"][2] and t["box"][1] < b[3] and b[1] < t["box"][3]]

    def placed(pt, side="below", top=None):
        t = tag(F, text, at(*pt), size, room=room, side=side, top=top)
        hs = hits(t)
        for x0, x1 in ((max(room[0], max(b[2] for b in hs) + 8), room[1]), (room[0], min(room[1], min(b[0] for b in hs) - 8))) if hs else ():
            u = tag(F, text, at(*pt), size, room=(x0, x1), side=side, top=top)
            if u["box"][2] <= x1 + 0.5 and u["box"][0] + size <= u["tip"][0] <= u["box"][2] - size and not hits(u):
                return u
        return t

    below = placed(chin)
    above = placed(over, "above")
    # under the chin, inside the safe area, and under the stamp it would cover there, its pointer reaching up past the stamp
    first = tag(F, text, at(*chin), size, room=room)
    first = tag(F, text, at(*chin), size, room=room, top=max(first["box"][1], F.top))
    lower = placed(chin, top=max([first["box"][1]] + [b[3] + 8 for b in hits(first)]))
    for t, ok in ((below, below["box"][3] <= min(max(ys) - 6, F.bottom)), (above, above["box"][1] >= max(min(ys) + 6, F.top)),
                  (lower, lower["box"][3] <= min(max(ys) - 6, F.bottom)), (below, below["box"][3] <= F.bottom)):
        if ok and t["box"][1] >= F.top and F.left - 0.5 <= t["box"][0] and t["box"][2] <= F.right + 0.5 and not hits(t):
            return t
    return None


def lay(F, ctx, rows, roles, q, tilt, cut, row=None):
    """(height, layers): the wall at stamp size `q` and tilt `tilt`: rows of slices meeting at thin gutters, each
    person's stamp hanging in their own slice under its top edge, clear of their face, and the handle and the title
    standing on the paper on the last person's top edge (none where the card's closer is a shape the shared layer
    draws: the last row then meets the rows over it at a gutter). The wall is the frame's height when `row` is None (its rows
    over the last share what the frame leaves them), else it grows downward until each of them stands `row` px tall,
    and `height` is the wall's. None when the rows would stand under the format's floor, or `row` grows no wall, or a
    slice shows too little (under the format's floor), shows under half its photograph's shorter side, cuts the face
    its cast names, has no place for its stamp off that face or no room for its tag (the role joins `cut`), or a line
    leaves the safe area or its own slice."""
    n = len(rows)
    photos = ctx.photos
    floor = SHOWN[F.kind]
    spread = abs(math.tan(math.radians(tilt))) * F.W / 2
    size = max(40, floor_size("display"), round(CHIP[F.kind] * q))

    def hanging(row, e):
        return [ln for p, span in zip(row, columns(F, len(row))) for ln in chip(F, p, span, e, size)]

    z = Edge(F, 0, tilt)
    reach_tag = (POINTER + PILL_H) * WALL_TAG[F.kind] + 16
    titled = not shaped(look().card["closer"])
    # the paper the title stands on, over the last person's edge: how far the handle and title stand over it
    over_last = reach(hero_lines(F, ctx, z, q), z, ink_only=False)[0] + ROWGAP if titled else GUT
    # the last row stands at least as tall as an even share of the frame's rows, its tags inside the safe area over the
    # tops of their heads, and its faces whole in the frame under them (a face at least as tall as its photograph laid
    # across its column's width shows it, up to a third of the frame: a print whose face runs taller stands smaller on
    # the paper of its slice, so the rows over it stay in the frame)
    faces = [(info["face"][3] - info["face"][1]) * (x1 - x0) * photos.aspect[roles[p.handle]]
             for p, (x0, x1) in zip(rows[-1], columns(F, len(rows[-1]))) for info in [photos.info(roles[p.handle])] if info.get("face")]
    even = F.H - (F.H - F.top - over_last - GUT * max(0, n - 2)) / n
    c_last = min(F.bottom - reach_tag - FACE - 2 * spread, F.H - floor - spread, even,
                 F.H - spread - reach_tag - 2 * FACE - min(max(faces, default=0), F.H / 3))
    if row is not None:
        grow = (n - 1) * row + max(0, n - 2) * GUT + over_last - (c_last - F.top)
        if n < 2 or grow <= 0:
            return None
        F, c_last = tall(F, F.H + grow), c_last + grow
    W, H = F.W, F.H
    tops, bottoms = [None] * n, [None] * n
    tops[-1] = c_last
    if n > 1:
        # the rows over the last person's share the safe height left to them over the title; the top row also runs up
        # under the safe area's top
        h = (c_last - over_last - F.top - GUT * (n - 2)) / (n - 1)
        if h < floor:
            return None
        for i in range(n - 1):
            tops[i] = F.top + i * (h + GUT) if i else None
            bottoms[i] = F.top + i * (h + GUT) + h
    E = [(Edge(F, t, tilt) if t is not None else None, Edge(F, b, tilt) if b is not None else None) for t, b in zip(tops, bottoms)]
    out, lines, tagged, at = [], [], [], 0.0
    for i, row in enumerate(rows):
        te, be = E[i]
        e = te
        if e is None:   # the top row's stamps hang inside the safe area
            e = Edge(F, F.top + spread, tilt)
            e = Edge(F, e.yc + max(0.0, reach(hanging(row, e), e, ink_only=False)[0]), tilt)
        for p, span in zip(row, columns(F, len(row))):
            poly = piece(F, span, te, be)
            if shown(poly, W, H) < floor - 0.5:
                return None
            role, owner, handle = roles[p.handle], ctx.people.index(p) + 1, p.handle
            tip, head = subject(photos, role)
            face = photos.info(role).get("face")
            over = (head[0], max(0.0, head[1] - 0.01)) if face else tip   # the point a tag over the head points at
            focus = over if be is None else (tip[0], (tip[1] + head[1]) / 2)
            to_y = te.yc + spread + reach_tag + FACE if be is None else None
            pl = slice_place(photos, role, poly, focus, F, to_y)
            if be is not None and pl[1] + tip[1] * pl[3] < F.top + 8:   # the tag's tip comes down into the safe area
                pl = slice_place(photos, role, poly, tip, F, F.top + 8)
            stamp = hung(F, photos, role, p, span, e, size, pl)
            if stamp is None:   # the stamp covers the face wherever it hangs: the face goes under it, else beside it
                lb = hulls(chip(F, p, span, e, size), ink_only=True)
                for f, y, x in ((over, lb[3] + FACE, None), ((face[0], focus[1]), to_y, lb[2] + FACE)):
                    pl = slice_place(photos, role, poly, f, F, y, x)
                    stamp = hung(F, photos, role, p, span, e, size, pl)
                    if stamp:
                        break
            L_ = {"kind": "Slice", "at": round(at, 2), "poly": trimmed(poly, shot(photos, role, pl)), "photo": photo(photos, role),
                  "place": pl, "owner": owner, "beats": 0.4}
            if stamp is None or sliver(F, L_) or face_cut(F, L_):
                cut.add(role)
                return None
            out.append(L_)
            tagged.append((L_, role, handle, pl, poly))
            lines.append((stamp, L_))
            at += 0.04
    hero = hero_lines(F, ctx, E[-1][0], q) if titled else []
    lines.append((hero, None))
    sx0, sy0, sx1, sy1 = safe_box(F)
    for group, sl in lines:
        for ln in group:
            b = hull(turned(box(ln), ln))
            if b[0] < sx0 - 0.5 or b[1] < sy0 - 0.5 or b[2] > sx1 + 0.5 or b[3] > sy1 + 0.5:
                return None
            quad = turned(box(ln, ink=True), ln)
            if any(crossing(quad, o["poly"]) for o in out if o is not sl):
                return None
    avoid = [clear_of(ln) for group, _ in lines for ln in group]
    for L_, role, handle, pl, poly in tagged:
        t = wall_tag(F, photos, role, handle, pl, poly, avoid)
        if not t:
            cut.add(role)
            return None
        L_["tag"] = wall_shape(dict(t, owner=L_["owner"]))
        avoid.append(t["box"])
    stamps = [toned(F, sl["photo"]["file"], sl["place"], ln, sl["photo"].get("band")) for group, sl in lines[:-1] for ln in group]
    words = [{"kind": "Words", "at": round(at + 0.5, 2), "lines": stamps, "beats": 0.4, "step": 0.06}]
    if titled:
        said, title = hero
        words = [{"kind": "Words", "at": round(at + 0.1, 2), "lines": [title], "beats": 0.5},
                 {"kind": "Words", "at": round(at + 0.3, 2), "lines": [said], "beats": 0.4}] + words
    return H, out + words


# ------------------------------------------------------------------ the draft and the board
def printed(p, said):
    """`said` as the card prints it: a handle of the person's own at its start or end is the one their tag carries, so it
    is printed once, on the tag; the board keeps the line whole, as the person wrote it."""
    if not said:
        return said
    own = re.escape(f"@{p.handle}")
    out = re.sub(rf"^{own}\b[\s,:]*|[\s,:]*{own}$", "", said).strip()
    return out or said


def heard_line(p):
    """The line a person is heard by: the line taste.json settled for their moment (none when it left it without words),
    else their best line (people.json's pick; for a person who never comments, the account's own caption of them)."""
    return p.line


def pulses_for(line):
    """The beats a person's words need: four, five when their words run past three, six past seven, seven past twelve:
    the words land two beats in and the camera leaves as soon as they have been read."""
    n = len((line or "").split())
    return 4 if n <= 3 else 5 if n <= 7 else 6 if n <= 12 else 7


def lengths(people):
    """Each person's beat, in pulses: what their words need, a beat more where that would run as long as the beat before
    it (so the cuts never settle into a count), and the last person's, the one the film closes on, the longest of them
    all by a beat."""
    out = []
    for p in people:
        n = pulses_for(heard_line(p))
        out.append(n + 1 if out and n == out[-1] else n)
    if out:
        out[-1] = max(out) + 1
    return out


def draft(ctx):
    """The hook, a card per person in the order taste.json lists them, each as long as lengths() says, and the closer."""
    beats = [{"id": "hook", "comp": "hook", "pulses": HOOK_BEATS, "role": "hook"}]
    for i, (p, n) in enumerate(zip(ctx.people, lengths(ctx.people)), 1):
        beats.append({"id": f"person-{i}", "comp": "person", "person": p.handle, "line": heard_line(p), "pulses": n})
    beats.append({"id": "closer", "comp": "closer", "pulses": ROUTE_AT + ROUTE + WALL_HOLD + SHAPE + HOLD, "role": "closer"})
    return beats


def cards(ctx, beats):
    """The per-person still each person gets: the settled frame of their card."""
    return {b["person"]: b["id"] for b in beats if b["comp"] == "person"}


def layout(b, ctx, F):
    raise NotImplementedError("drive lays its whole board out at once: boards.layout calls board()")


def tags_of(ctx, b, last):
    """What a beat shows, in the words the cards' `fits` lists use: its form (title, photo, wall) and the rest."""
    photos = ctx.photos
    if b["comp"] == "hook":
        return "title", {"title", "people"} | ({"landscape"} if "group" in photos.aspect and photos.framed("group") else set())
    if b["comp"] == "closer":
        return "wall", {"wall", "closer", "people"}
    p = ctx.person(b["person"])
    role = f"{p.handle}-0"
    out = {"people", "photo", "words" if printed(p, b.get("line")) else "wordless",
           "landscape" if photos.framed(role) else "portrait"}
    if p.where:
        out.add("place")
    if last:
        out.add("peak")
    return "photo", out


def picks(ctx, beats_in):
    """Each beat's move, the transition into it, and its form, chosen from what the beat shows within the card's lists, never the
    same transition twice in a row (the hook has none: the film opens on it). On full-frame footage a person never
    arrives on a straight cut: their beat zooms in on its move (ZOOMED), or the roll burns into it."""
    c = look().card
    used_m, used_t, prev_m, prev_t, out = {}, {}, None, None, {}
    persons = [b for b in beats_in if b["comp"] == "person"]
    footage = frame_of() == "footage"
    for b in beats_in:
        form, tags = tags_of(ctx, b, persons and b is persons[-1])
        moves, cuts = c["moves"], c["transitions"]
        if footage and b["comp"] == "person":
            moves = [o for o in moves if o["id"] in ZOOMED or o["id"] == "light-leak"] or moves
        m = S.pick(moves, tags, form, used_m, prev_m)
        if footage and b["comp"] == "person":
            cuts = [o for o in cuts if o["id"] == "roll-burn"] if m not in ZOOMED else [o for o in cuts if o["id"] != "hard-cut"]
            cuts = cuts or c["transitions"]
        t = S.pick(cuts, tags, form, used_t, prev_t) if b["comp"] != "hook" else None
        out[b["id"]] = (m, t, form)
        prev_m, prev_t = m, t or prev_t
    return out


def board(sb, ctx, kind="reel", bpm=None):
    """The board the studio's drive film renders: the storyboard laid out in format `kind` at `bpm` in the style the
    storyboard names, with the sound cues, the clips, and per beat its move, the transition into it, what its move
    reveals and what it carries, and the frame each beat rests on."""
    if LOOK is None or LOOK.card["id"] != sb["style"]:
        use(sb["style"], ctx)
    F = L.Frame(kind)
    bpm = bpm or sb["bpm"]
    pulse = boards.FPS * 60 / bpm
    beats_in = sb["beats"]
    people = [ctx.person(b["person"]) for b in beats_in if b["comp"] == "person"]
    starts, t = {}, 0.0
    for b in beats_in:
        starts[b["id"]] = t
        t += b["pulses"]
    G = lensed(F)
    chosen = picks(ctx, beats_in)
    hook_edge, _, layers = hook(G, ctx, chosen["hook"][0])
    hooked = {"id": "hook", "layers": layers, "rest": TITLE_AT + 0.9}
    scenes, roles, edge = [hooked], {}, hook_edge
    persons = [b for b in beats_in if b["comp"] == "person"]
    for k, b in enumerate(persons):
        p = ctx.person(b["person"])
        edge, role, layers, _ = card(G, ctx.photos, p, printed(p, b.get("line")), k, chosen[b["id"]][0])
        roles[p.handle] = role
        scenes.append({"id": b["id"], "layers": layers, "rest": min(b["pulses"] - LEAVE - 0.4, CUT + RISE + 2.4)})
    ending = closer(F, ctx, roles, edge)
    shape_at, shape = ROUTE_AT + ROUTE + WALL_HOLD, settles(look().card["closer"])
    ending.append({"kind": "Shape", "at": shape_at, "beats": shape, "name": look().card["closer"]})
    scenes.append({"id": "closer", "layers": ending, "rest": shape_at + shape})
    out = []
    run = 0
    for sc, b in zip(scenes, beats_in):
        a = round(run)
        run += b["pulses"] * pulse
        frames = round(run) - a
        move, transition, form = chosen[sc["id"]]
        out.append({"id": sc["id"], "frames": frames, "camera": "none", "transition": transition, "move": move, "form": form,
                    "layers": sc["layers"], "comp": b["comp"],
                    "rest": min(frames - 2, round(sc["rest"] * pulse)), **({"person": b["person"]} if b.get("person") else {}),
                    **({"keep": kept(sc["layers"])} if sc["id"] != "closer" else {})})
    story(out, ctx, people)
    lk = look()
    board_ = {"id": f"people-{lk.card['id']}-{kind}", "name": sb["name"], "handle": sb["handle"], "year": sb["year"], "bpm": bpm,
              "style": lk.card["id"], "ground": lk.ground, "tag_text": lk.tag_text, "signoff": SIGNOFF, "said_by": said_by(ctx),
              "format": {"width": F.W, "height": F.H, "fps": boards.FPS, "kind": kind, "name": kind, "safe": list(safe_box(F))},
              "system": system(), "beats": out}
    board_["sound"] = sound(out, starts, ctx, people, F)
    board_["clips"] = clips(out, ctx, people)
    return board_


def kept(layers):
    """The box, in format px, that a card's type and tags fill: the camera's push keeps it inside the safe area. A month
    stamped low on the page beside its keepsake stands under the safe area and is not part of it."""
    boxes = [hull(turned(box(ln), ln)) for L_ in layers if L_["kind"] == "Words" for ln in L_["lines"] if not ln.get("low")]
    for L_ in layers:
        if L_["kind"] == "Tags":
            for t in L_["tags"]:
                x0, y0, x1, y1 = t["box"]
                if t.get("shape", "pill") == "pill":
                    boxes.append((x0, min(y0, t["tip"][1]), x1, max(y1, t["tip"][1])))
                elif t["shape"] == "band":   # a band runs past the frame's sides; its name is what has to stay in view
                    boxes.append((x0 + t["inset"], y0, x1 - t["inset"], y1))
                else:
                    boxes.append((x0, y0, x1, y1))
    return [round(f(b[i] for b in boxes), 1) for i, f in ((0, min), (1, min), (2, max), (3, max))] if boxes else None


def story(beats, ctx, people):
    """Each beat's `reveals` (what its move shows: this photograph's person, and where and when the two of them were) and
    `carries` (what crosses the cut into the next beat)."""
    ids = [b["id"] for b in beats]
    for i, b in enumerate(beats):
        nxt = ids[i + 1] if i + 1 < len(ids) else None
        if b["id"] == "hook":
            tl = next((L_ for L_ in b["layers"] if L_["kind"] == "Tags"), {})
            n = len(tl.get("tags", []))
            b["reveals"] = ("the photograph of them together, 'my people.' standing on its edge, and under it every person's tag pops in the "
                            "film's order, a roll call" if tl.get("roll") else
                            f"the photograph of them together: a tag pops onto each of the {n} heads in it, one after another, and 'my people.' stands on the edge"
                            if n else "the photograph under a level edge and 'my people.' standing on it")
            b["carries"] = "the tags gather into one, which flies out of the photograph to find the next person"
        elif b["id"].startswith("person-"):
            p = ctx.person(b["person"])
            file = next(L_ for L_ in b["layers"] if L_["kind"] == "Cut")["photo"]["file"]
            b["reveals"] = (f"@{p.handle} in the photograph {file}, brought in by {b['move']}: the tag lands on them, the blade cuts it "
                            f"along an edge just over their head, '{p.stamp}' falls onto the edge and their own words rise over it")
            b["carries"] = (f"the tag lifts off them and flies on; {beats[i + 1]['transition']} into the next person, where the card trims "
                            "into its slice of the wall" if nxt != "closer" else
                            f"{beats[i + 1]['transition']} into the whole wall, the last person's card at its foot")
        elif b["id"] == "closer":
            b["reveals"] = ("the wall of the film's people in its order, settling with the impact: the tag runs it, leaving a tag beside "
                            f"each of them, and lands on @{people[-1].handle if people else ctx.handle}; then {look().card['closer']} "
                            "closes the film on 'my people.'")
            b["carries"] = "nothing: the picture and the music stop together as the closer settles, and the frame holds still and silent to the end"


def sound(beats, starts, ctx, people, F):
    """The film's sound cues, one where each beat lands, for music.py to mix under the bed: the camera landing on the
    hook's photograph, the blade cutting each person's photograph as their stamp lands on its edge (one weight for
    everyone), the build into the wall and its impact on the frame the wall settles, the tag landing on the last face,
    and the stop as the card's closer settles. Tags pop, words rise and the camera cuts without a sound of their own."""
    cues = [{"kind": "hit", "at": 0.0, "beat": "hook", "what": "the camera lands on the photograph of them together", "weight": 0.9}]
    for b in beats:
        if b["id"].startswith("person-"):
            p = ctx.person(b["person"])
            cues.append({"kind": "hit", "at": round(starts[b["id"]] + CUT, 3), "beat": b["id"],
                         "what": f"the blade cuts @{p.handle}'s photograph and '{p.stamp}' lands on the edge", "weight": 0.7, "bright": 0.8})
    C = starts.get("closer")
    if C is not None:
        land = round(C + ROUTE_AT, 3)
        cues.append({"kind": "riser", "at": round(land - BUILD, 3), "beats": BUILD, "beat": "closer", "what": "the build into the wall"})
        cues.append({"kind": "impact", "at": land, "beat": "closer", "what": "the wall settles whole"})
        tagged = round(C + ROUTE_AT + ROUTE, 3)
        cues.append({"kind": "hit", "at": tagged, "beat": "closer", "what": f"the tag lands on @{people[-1].handle}, the last face", "weight": 0.85, "bright": 0.7})
        stop = round(C + ROUTE_AT + ROUTE + WALL_HOLD + settles(look().card["closer"]), 3)
        cues.append({"kind": "stop", "at": stop, "beat": "closer", "what": "the closer settles; the picture and the music stop together"})
    return sorted(cues, key=lambda c: c["at"])


# the camera's own move in a clip, chosen from the shot: a close face holds nearly still, a wide place opens up, a
# face seen from below gets the camera rising, a backlit picture gets an arc round its subject, a lit side a drift
# across from it
CLIP_MOVES = {
    "close": "the camera all but locked off, easing a few percent in toward them",
    "low": "the camera rising a hand's height on them, the horizon dropping a little",
    "behind": "the camera arcing a few degrees around them, the background turning slowly behind",
    "side": "the camera drifting slowly across them away from the light, a hand-held breath in it",
    "wide": "a gentle pull back from them, the place opening up around the frame",
    "high": "the camera settling down onto them from a touch above, as if just set on its legs",
    "level": "a slow push past the near edge of the frame onto them, the foreground sliding out of shot",
}


def clip_move(lens, height, light):
    """The camera's move in a clip, from its lens, its height and its light (lens_of, light_of)."""
    if lens.startswith("a close-up"):
        return CLIP_MOVES["close"]
    if "from behind" in light:
        return CLIP_MOVES["behind"]
    if "looking up" in height:
        return CLIP_MOVES["low"]
    if "falling from" in light:
        return CLIP_MOVES["side"]
    if lens.startswith("a wide"):
        return CLIP_MOVES["wide"]
    return CLIP_MOVES["high" if "looking down" in height else "level"]


def lens_of(photos, role):
    """The lens and the camera's height a clip of `role` is shot with, from its photograph: the face's share of its
    height gives the lens (a close face, a long lens); a person with no face in the cast is a figure dark against the
    light where the cast keeps its light, else a medium shot; where the face or the point sits gives the height."""
    info = photos.info(role)
    v0, v1 = photos.band.get(role, (0.0, 1.0))
    face = info.get("face")
    if face:
        share = (face[3] - face[1]) / (v1 - v0)
        lens = ("a close-up on an 85 mm lens, the background falling soft" if share > 0.28 else
                "a medium close-up on a 65 mm lens" if share > 0.18 else
                "a medium shot on a 50 mm lens" if share > 0.1 else "a wide shot on a 35 mm lens")
    elif role == "group":
        lens = "a wide shot on a 28 mm lens, deep focus"
    elif info.get("keep_light"):
        lens = "a wide shot on a 35 mm lens, the figure dark against the light"
    else:
        lens = "a medium shot on a 50 mm lens"
    v = ((face[1] + face[3]) / 2 if face else info["point"][1]) - v0
    v /= v1 - v0
    # a face near the top of its picture is seen from below it, one near the foot from above
    height = "the camera low, looking up" if v < 0.22 else "the camera high, looking down" if v > 0.62 else "the camera at eye level"
    return lens, height


HUES = (("warm amber", 30, 100), ("green", 100, 165), ("cool blue", 165, 290), ("magenta", 290, 345))


def hue_name(h):
    """A hue angle in CIE a*b* degrees, in words."""
    return next((n for n, lo, hi in HUES if lo <= h % 360 < hi), "warm red")


def hue_of(cells, chroma):
    """The color of a picture's light in words: black and white where it has almost none; else, when its colorful
    cells (CIE a*b* chroma over 10) cover a fifth of the picture or more, the named hue that most of their color falls
    in, and a second one with it where that one carries half as much or more (a stage lit violet with a warm spot is
    both, never their average); else neutral."""
    cells = list(cells)
    if chroma < 5:
        return "black-and-white"
    lit = [(a, b) for _, a, b in cells if math.hypot(a, b) > 10]
    if len(lit) < len(cells) / 5:
        return "neutral"
    weight = {}
    for a, b in lit:
        n = hue_name(math.degrees(math.atan2(b, a)))
        weight[n] = weight.get(n, 0.0) + math.hypot(a, b)
    (first, w1), *rest = sorted(weight.items(), key=lambda kv: -kv[1])
    return f"{first} and {rest[0][0]}" if rest and rest[0][1] >= w1 / 2 else first


def light_of(file, band):
    """The light of a photograph, in words, measured from the part of its picture it spans: its color (hue_of), how
    bright, where it comes from (behind the subject where the
    picture's rim outshines its middle on every side, else the brighter side, else above where the top outshines the
    rest, else all round) and how hard its contrast is."""
    im = pixels(file)
    w, h = im.size
    part = im.crop((0, int(band[0] * h), w, max(int(band[0] * h) + 1, int(band[1] * h)))).resize((16, 16))
    lab_ = {(i, j): lab(part.getpixel((i, j))) for i in range(16) for j in range(16)}
    mean = lambda cells: sum(lab_[c][0] for c in cells) / len(cells)
    every = list(lab_)
    L_ = mean(every)
    chroma = sum(math.hypot(c[1], c[2]) for c in lab_.values()) / len(lab_)
    spread = (sum((c[0] - L_) ** 2 for c in lab_.values()) / len(lab_)) ** 0.5
    # the rim's darkest side: a picture lit from behind has a bright rim on every side of a darker middle
    rim = min(mean([c for c in every if f(c) < 2]) for f in (lambda c: c[0], lambda c: c[1], lambda c: 15 - c[0], lambda c: 15 - c[1]))
    middle = mean([c for c in every if 5 <= c[0] <= 10 and 5 <= c[1] <= 10])
    left, right = mean([c for c in every if c[0] < 5]), mean([c for c in every if c[0] > 10])
    top = mean([c for c in every if c[1] < 5])
    color = hue_of(lab_.values(), chroma)
    level = "low" if L_ < 38 else "bright" if L_ > 64 else "soft"
    source = ("from behind, a rim of it round the subject" if rim - middle > 12 else
              "falling from the left" if left - right > 10 else "falling from the right" if right - left > 10 else
              "from above" if top - L_ > 10 else "even all round")
    contrast = "hard" if spread > 22 else "low" if spread < 12 else "moderate"
    return f"{level} {color} light {source}, {contrast} contrast"


def clips(beats, ctx, people):
    """The generated clips the film would carry, for the platform's image-to-video model, one shot each: the shot the
    agent wrote for the photograph in cast.json (who or what moves and how), the lens and the height from where the
    face sits, the light measured from the photograph, the camera's own small move chosen from the shot (clip_move),
    the beat's length and a loop that closes on its first frame; and `stand_in`, the move the film makes in a clip's
    place when no clip has arrived."""
    out = []
    photos = ctx.photos
    for b in beats:
        if b["id"] == "closer":
            continue
        cut = next(L_ for L_ in b["layers"] if L_["kind"] == "Cut")
        role = cut["photo"]["role"]
        info = photos.info(role)
        hook = b["id"] == "hook"
        who = "them together" if hook else f"@{ctx.person(b['person']).handle}"
        said = (info.get("shot") or "").strip().rstrip(".")
        if not said:
            said = ("the people in the photograph as they were in that moment, each moving a little in their own way" if hook else
                    f"{who} as in the photograph, a breath, a blink, the air moving their hair and clothes")
        lens, height = lens_of(photos, role)
        band = photos.band.get(role, (0.0, 1.0))
        light = light_of(cut["photo"]["file"], band)
        secs = round(b["frames"] / boards.FPS, 1)
        move = clip_move(lens, height, light)
        prompt = (f"{said}. {lens[0].upper()}{lens[1:]}, {height}, {light}. {move[0].upper()}{move[1:]}. {secs} seconds, a "
                  "seamless loop whose last frame is its first; the photograph's own people and place only, no text.")
        out.append({"id": f"{len(out):02d}", "beat": b["id"], "role": "the world the film opens in" if hook else "the person brought to life",
                    "seconds": secs, "image": cut["photo"]["file"], "prompt": prompt,
                    "stand_in": ("the photograph's layers moving apart under the camera's push: the print, the tags on "
                                 "every head" if hook else
                                 "the card's layers moving at their own depths as the camera pushes in on the tagged person: the print "
                                 "on its mount, the part above the edge lifted off the part under it")})
    return out


# ------------------------------------------------------------------ checks
def problems(board):
    """[(where, message)] for a laid-out drive board: a line of type running into another, type outside the safe area (on
    a card, as the lens sees it; a month stamped low on the page, outside the page's lower third) or under its edge, type
    under the floor,
    a tag outside the safe area, pointing out of it, or running into the type, a frame that cuts the face the cast names or lays type or a tag over it, a wall slice that shows less than half of its photograph's shorter side,
    and on the closer's wall a slice that cuts the face its cast names or has type over it, or a tag outside the safe
    area or running into the type or another tag."""
    F = L.Frame(board["format"]["kind"])
    G = lensed(F)
    out = []
    floor = L.FLOOR
    for b in board["beats"]:
        # each line's band from its baseline to its cap height: ascenders and descenders may interlock, the bands never
        lines = [ln for L_ in b["layers"] if L_["kind"] == "Words" for ln in L_["lines"] if ln["text"].strip()]
        bands = [turned((box(ln)[0], ln["y"] - ink(dict(ln, text="H"))[0], box(ln)[2], ln["y"]), ln) for ln in lines]
        for i in range(len(lines)):
            for j in range(i):
                if crossing(bands[i], bands[j]):
                    out.append((b["id"], f"{lines[i]['text'][:30]!r} runs into {lines[j]['text'][:30]!r}"))
        cut = next((L_ for L_ in b["layers"] if L_["kind"] == "Cut"), None)
        V = wall_of(F, b) if b["id"] == "closer" else F
        S = V if b["id"] == "closer" else G
        edge = None
        # a card whose photograph takes the whole frame or the page has no edge: its line lies over the frame's top
        if cut and b["id"] != "closer" and max(cut["line"]) >= 0:
            edge = Edge(F, sum(cut["line"]) / 2, math.degrees(math.atan2(cut["line"][1] - cut["line"][0], F.W)))
        for L_ in b["layers"]:
            if L_["kind"] == "Words":
                for ln in L_["lines"]:
                    e = hull(turned(box(ln, ink=True), ln))
                    x0, y0, x1, y1 = safe_box(S)
                    if ln.get("low"):
                        x0, y0, x1, y1 = KEEPSAKE_PAD, F.bottom, F.W - KEEPSAKE_PAD, F.H - KEEPSAKE_ROOM / 2
                    if e[0] < x0 - 0.5 or e[1] < y0 - 0.5 or e[2] > x1 + 0.5 or e[3] > y1 + 0.5:
                        out.append((b["id"], f"{ln['text'][:30]!r} runs outside the safe area" if not ln.get("low")
                                    else f"{ln['text'][:30]!r} runs off the page's lower third"))
                    cap = ink(dict(ln, text="H"))[0]
                    if cap < floor - 0.5:
                        out.append((b["id"], f"{ln['text'][:30]!r} is {cap:.0f} px cap height, under the {floor} px floor"))
                    if edge and any(y > edge.y(x) + 1 for x, y in turned(box(ln, ink=True), ln)):
                        out.append((b["id"], f"{ln['text'][:30]!r} runs under its edge onto the photograph"))
            if L_["kind"] == "Tags" and cut and b["id"] != "closer":
                type_ = [hull(turned(box(ln, ink=True), ln)) for W_ in b["layers"] if W_["kind"] == "Words" for ln in W_["lines"]]
                for t in L_["tags"]:
                    x0, y0, x1, y1 = t["box"]
                    if not shaped_in(S, t):
                        out.append((b["id"], f"the tag {t['text']} runs outside the safe area"))
                    if any(x0 < e[2] and e[0] < x1 and y0 < e[3] and e[1] < y1 for e in type_):
                        out.append((b["id"], f"the tag {t['text']} runs into the type"))
        if cut and cut.get("photo", {}).get("face"):
            over = [hull(turned(box(ln), ln)) for W_ in b["layers"] if W_["kind"] == "Words" for ln in W_["lines"]]
            over += [t["box"] for T_ in b["layers"] if T_["kind"] == "Tags" for t in T_["tags"]]
            # over a photograph that takes the whole frame the type may cross the face under its eyes
            inked = [hull(turned(box(ln, ink=True), ln)) for W_ in b["layers"] if W_["kind"] == "Words" for ln in W_["lines"]]
            inked += [t["box"] for T_ in b["layers"] if T_["kind"] == "Tags" for t in T_["tags"]]
            clear = (face_clear(F, cut["photo"]["face"], cut["place"], []) and eyes_clear(cut["photo"]["face"], cut["place"], inked)
                     if edge is None else face_clear(F, cut["photo"]["face"], cut["place"], over))
            if not clear:
                out.append((b["id"], f"the frame cuts the face in {cut['photo']['role']}, or type or a tag covers it"))
        type_ = [clear_of(ln) for W_ in b["layers"] if W_["kind"] == "Words" for ln in W_["lines"]]
        inked = [hull(turned(box(ln, ink=True), ln)) for W_ in b["layers"] if W_["kind"] == "Words" for ln in W_["lines"]]
        for L_ in b["layers"]:
            if L_["kind"] == "Slice" and sliver(V, L_):
                out.append((b["id"], f"the wall shows less than half of the shorter side of {L_['photo']['role']}"))
            if L_["kind"] == "Slice" and face_cut(V, L_):
                out.append((b["id"], f"the wall cuts the face in {L_['photo']['role']}"))
            elif L_["kind"] == "Slice" and not face_clear(V, L_["photo"].get("face"), L_["place"], inked):
                out.append((b["id"], f"the wall's type covers the face in {L_['photo']['role']}"))
        wall = [L_["tag"] for L_ in b["layers"] if L_["kind"] == "Slice" and L_.get("tag")]
        for i, t in enumerate(wall):
            x0, y0, x1, y1 = t["box"]
            if x0 < V.left - 0.5 or x1 > V.right + 0.5 or y0 < V.top - 0.5 or y1 > V.bottom + 0.5:
                out.append((b["id"], f"the tag {t['text']} runs outside the safe area"))
            if any(x0 < e[2] and e[0] < x1 and y0 < e[3] and e[1] < y1 for e in type_ + [o["box"] for o in wall[i + 1:]]):
                out.append((b["id"], f"the tag {t['text']} runs into the type or another tag"))
    return out
