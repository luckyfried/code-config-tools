"""The board: one camera, one crop frame, and the grid it rebuilds, drawn in a style card's look.

The film is the grid's before and after. Their old posts stand muted on the wall, so the new ones carry the color.
The hook opens on the film's hook line, set over the picture by the card's move for words; as it gives way the frame
lands on the first of the posts of theirs that break the first screen and hops across the others while the camera
draws back over the whole first screen. Then each of the next posts comes into the grid by the move its photograph
asks for: the frame closes on a post it holds (the first, the middle and the last), from the whole photograph onto
its 4:5 crop while the rest of the picture recedes behind it, its caption on the frame's band, and carries it down
into the top of the grid as a 3:4 cell, the middle post the peak that holds longest; a landscape photograph slides in
along the top row to the frame waiting on the grid's first cell, the camera trucking with it; a portrait or square
one falls from above the view straight into the frame waiting there; each time every older post steps one place
along. The closer is the profile's first screen whole, as it will look the day the last post goes up, the frame round
it and its band the profile's header: their handle and their bio as they wrote it, emoji and line breaks kept. The
profile holds, then the card's closing card takes the frame with the film's ask, and the picture and the music stop
together on it. No count and no date is ever on screen.

The style card supplies everything about the look: the faces every line is measured and set in, the colors its
palette rule makes from their photographs, the easing of every camera move, the finish, the move each beat makes and
the cut into it (chosen from what the beat shows, within the card's allowlists), the closer, and the pace: a snap
camera reads at the base length, a slam camera shorter, a slow camera longer. Every beat starts on a beat of the music.

The sound is one cue where each beat lands, under the music: a hit as the frame lands on the hook's first post
and as each post seats in the grid, the build into the closer and its impact as the frame locks round the first
screen, the closing card, and the stop. The frame and the words move silently.

Every time here is a unit of half a second from the film's start (`bpm` 120 on the board); the timeline the card's
moves read is in beats of the music (`tempo`). Every place is px of the format's frame, y down. The board carries the
choreography as keys (`Frame`, `Camera`) and per-post times (`Post`), so the composition only draws.
"""
import datetime as dt
import math
import re

import _env
import compose
import palette as palette_rules
from plan import EMOJI, bare, crop as crop_box_of, held_posts

BPM = 120
FPS = 30
PULSE = FPS * 60 / BPM

# the band's own px at an inner frame width of BAND_W (it scales with the frame), its frame's thickness and its margin
BAND_W = 620
FT = 16
PAD = 30
# lengths at the card's base pace: a post that falls into the grid from above, one that slides along the top row (a
# post the frame closes on takes full_length)
DROP = 2
SLIDE = 2.5
# a post that falls is seen in a view this many first cells tall, the first cell at the view's top left
DROP_NEAR = 2.4
# the still after the stop: two seconds
HOLD_AFTER = 2.0
# a word enters over this many beats; a held post holds its caption whole this long after its last word enters, and
# the film's peak, the middle post the frame holds, holds it longest of any still in the film, longer than the
# closer's still after the stop
RISE = 0.45
READ = 2.0
PEAK_READ = 4.4
# a caption that enters letter by letter starts its letters LETTER beats apart
LETTER = 0.05
# how far off the wall a post the frame holds stands, px
LIFT = 220
# how far their posts on the wall are taken toward a gray print of themselves in the card's light: far enough that a
# cold outlier of the old grid never shows through beside the new posts
MUTE = 0.85
WALL_Z = 3
HOLD_FOV = 30
# the subject box: the 3:4 box round the photograph's subject, as a share of the largest 3:4 box the photograph holds
SUBJECT = 0.6
# how much wider than the frame and its band the hook's camera stands, so the posts round each loud one are in view
HOOK_WIDE = 1.35
CLOSER_FOV = 18
# the closer's words on screen, px: the handle (the text face, bold), the bio (the text face), each over the type
# floor with room to spare (the ask is the card's closing card's)
CLOSER_SIZES = {"reel": {"handle": 72, "bio": 58, "ask": 80}, "square": {"handle": 60, "bio": 58, "ask": 72},
                "landscape": {"handle": 72, "bio": 60, "ask": 88}}
# the cap height in px under which a line meant to be read fails (read on a phone held at arm's length)
FLOOR = 40
# the moves a held post never takes: crop-shift and scale-to-cell take a column of the frame's grid off the
# photograph, and a held post's page already stands it in the card's own picture box, which the card means whole
NOT_HELD = {"crop-shift", "scale-to-cell"}
# each format's wall width (the frame's width when None)
LAYOUT = {"reel": {"wall": None}, "square": {"wall": None}, "landscape": {"wall": 2100}}


def em(text, face="text", weight=None, tracking=0.0):
    """A line's width in em, as the composition sets it: the card face's advances, in its case, with its tracking."""
    return compose.em(text, face)


class _Cap(dict):
    """The cap height in em of the card face in use, by face ("display", else text)."""
    def __missing__(self, face):
        return compose.cap(face)


CAP = _Cap()


def line(text, x, y, size, face="text", weight=600, color="ink", tracking=0.0, written=False, **kw):
    """A line of type; `written` keeps the words as the person wrote them (a handle, a bio), never in the face's case."""
    return {"text": text if written else compose.cased(text, face), "x": round(x, 1), "y": round(y, 1), "size": size, "face": face, "weight": weight, "color": color,
            "tracking": tracking, **kw}


def halves(text, weight=500, face="text"):
    """`text` in two lines split where the longer line is shortest."""
    words = text.split()
    return min((([" ".join(words[:i]), " ".join(words[i:])]) for i in range(1, len(words))),
               key=lambda p: max(em(x, face, weight) for x in p))


def wrap(text, size, width, weight=500, most=2, face="text"):
    """Lines of `text` at `size` no wider than `width` px, never a cut word, two or three lines balanced so none is a
    lone word; None when it needs more than `most`."""
    words = text.split()
    wide = lambda t: em(t, face, weight) * size > width
    if wide(text) and len(words) > 1:
        two = halves(text, weight, face)
        if not any(wide(x) for x in two):
            return two if most >= 2 else None
    if wide(text) and most >= 3 and len(words) > 2:
        # three lines split where the longest is shortest, so the last line is never a lone short word
        three = min(([" ".join(words[:i]), " ".join(words[i:j]), " ".join(words[j:])]
                     for i in range(1, len(words) - 1) for j in range(i + 1, len(words))),
                    key=lambda p: max(em(x, face, weight) for x in p))
        if not any(wide(x) for x in three):
            return three
    out, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if not wide(t) or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    if len(out) > most or any(wide(x) for x in out):
        return None
    return out


# ------------------------------------------------------------------ color
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(h):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _chroma(h):
    r, g, b = _rgb(h)
    return (max(r, g, b) - min(r, g, b)) / 255


def colors_of(card, taste, palette):
    """The film's colors: the card's palette rule applied to their photographs' swatches (palette.py palette_of)."""
    made = palette_rules.palette_of(card["palette"], palette_rules.swatches_of(taste, palette))
    return dict(made["roles"], swatches=made["swatches"][:6])


# a style's pace from its camera word: the peak's read, the quick moves and the hook take this share of their base
# length; a held caption's read is never shorter than its base, whatever the pace
PACE = {"snap": 1.0, "slam": 0.8, "slow": 1.15}


def pace_of(card):
    return PACE.get(card["axes"]["camera"], 1.0)


# ------------------------------------------------------------------ geometry
def geometry(fmt):
    """The wall (the profile grid at 3:4 cells, edge to edge across the frame), the station a post is read at, and the
    safe area, in px of `fmt`."""
    s = _env.read_json(_env.SKILL / "design" / "safe-areas.json")[fmt]
    W, H = s["width"], s["height"]
    safe = {k: s[k] for k in ("top", "bottom", "left", "right")}
    lay = LAYOUT[fmt]
    g = 8
    ww = lay["wall"] or W
    cw = (ww - 2 * g) / 3
    ch = cw * 4 / 3
    # the wall stands centered on the frame, as wide as the layout says
    x0 = round((W - ww) / 2, 1) if lay["wall"] else 0
    y0 = 500
    return {"W": W, "H": H, "safe": safe, "layout": lay, "grid": {"x0": x0, "y0": y0, "cw": cw, "ch": ch, "g": g, "cols": 3},
            "station": {"x": round((W - BAND_W) / 2), "y": 0, "w": BAND_W}}


def wall_sides(G):
    """The wall's left and right sides, px of the frame."""
    g = G["grid"]
    return g["x0"], g["x0"] + 3 * g["cw"] + 2 * g["g"]


def band_point(box, hb, side, bx, by, bw=BAND_W):
    """Where a point of a band's own px (bx, by from its top left) stands on the plane of an open band `bw` px wide, px
    of the frame: above the picture and centered on it (top), or beside the frame with its top at the frame's top (left,
    right)."""
    s = box[2] / BAND_W
    ft = FT * s
    if side == "right":
        return box[0] + box[2] + ft + (bx + FT) * s, box[1] - ft + by * s
    if side == "left":
        return box[0] - ft + (bx - BAND_W - FT) * s, box[1] - ft + by * s
    return box[0] + (bx + (BAND_W - bw) / 2) * s, box[1] - ft - hb * s + by * s


def frame_block(box, hb, side, bw=BAND_W):
    """The rectangle [x0, y0, x1, y1] the frame and its open band cover, px of the frame."""
    s = box[2] / BAND_W
    ft = FT * s
    x0, y0 = band_point(box, hb, side, -FT, 0, bw)
    x1, y1 = band_point(box, hb, side, bw + FT, hb, bw)
    return [min(x0, box[0] - ft), min(y0, box[1] - ft), max(x1, box[0] + box[2] + ft), max(y1, box[1] + box[3] + ft)]


def cell(G, slot):
    g = G["grid"]
    c, r = slot % g["cols"], slot // g["cols"]
    return [g["x0"] + c * (g["cw"] + g["g"]), g["y0"] + r * (g["ch"] + g["g"]), g["cw"], g["ch"]]


def first_screen(G, rows=3):
    """The grid's top `rows` whole rows (the first screen at 3), px of the frame."""
    g = G["grid"]
    return [g["x0"], g["y0"], 3 * g["cw"] + 2 * g["g"], rows * g["ch"] + (rows - 1) * g["g"]]


def _camera(f, W, H):
    """The camera the composition builds from a framing (`camera.ts` poseOf, then three's lookAt with the roll): its
    position, its right, up and back axes, and the tangent of half its vertical field of view."""
    tx, ty, tz = f["c"][0] - W / 2, H / 2 - f["c"][1], f["z"]
    half = math.tan(math.radians(f["fov"]) / 2)
    D = f["h"] / 2 / half
    cp = math.cos(f["pitch"])
    P = (tx + D * math.sin(f["yaw"]) * cp, ty - D * math.sin(f["pitch"]), tz + D * math.cos(f["yaw"]) * cp)

    def unit(v):
        n = math.sqrt(sum(c * c for c in v))
        return [c / n for c in v]

    def cross(u, v):
        return [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    zc = unit([P[0] - tx, P[1] - ty, P[2] - tz])
    # the up vector turned by the roll about the line of sight (Rodrigues)
    a, k = -f["roll"], [-v for v in zc]
    kxu = cross(k, [0.0, 1.0, 0.0])
    up = [(0.0, 1.0, 0.0)[i] * math.cos(a) + kxu[i] * math.sin(a) + k[i] * k[1] * (1 - math.cos(a)) for i in range(3)]
    xc = unit(cross(up, zc))
    return P, xc, cross(zc, xc), zc, half


def project(f, W, H, x, y, z):
    """Where a point (px of the frame, y down, at depth z) lands on the screen under a framing, in px."""
    P, xc, yc, zc, half = _camera(f, W, H)
    v = [x - W / 2 - P[0], H / 2 - y - P[1], z - P[2]]
    depth = -sum(v[i] * zc[i] for i in range(3))
    sx = sum(v[i] * xc[i] for i in range(3)) / (depth * half * W / H)
    sy = sum(v[i] * yc[i] for i in range(3)) / (depth * half)
    return W / 2 * (1 + sx), H / 2 * (1 - sy), H / 2 / (depth * half)


def footprint(f, W, H, zp=WALL_Z):
    """The rectangle [x0, y0, x1, y1] of the plane at depth `zp` that a framing's view covers, in px of the frame:
    the camera's four corner rays met with the plane."""
    P, xc, yc, zc, half = _camera(f, W, H)
    xs, ys = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = [-zc[i] + sx * half * W / H * xc[i] + sy * half * yc[i] for i in range(3)]
            u = (zp - P[2]) / d[2]
            xs.append(P[0] + u * d[0] + W / 2)
            ys.append(H / 2 - (P[1] + u * d[1]))
    return [min(xs), min(ys), max(xs), max(ys)]


def inside(f, W, H, top, margin=10, sides=None):
    """The framing moved, and narrowed when it has to be, until the wall fills its view: the view's footprint on the
    wall stays within the wall's two sides (`sides`, the frame's when None) and below its top `top`, so the ground
    behind the wall is never in frame."""
    f = dict(f)
    left, right = sides or (0, W)
    for _ in range(20):
        x0, y0, x1, y1 = footprint(f, W, H)
        if x1 - x0 > right - left - 2 * margin:
            f["h"] *= (right - left - 2 * margin) / (x1 - x0) * 0.995
            x0, y0, x1, y1 = footprint(f, W, H)
        dx = max(0.0, left + margin - x0) - max(0.0, x1 - (right - margin))
        dy = max(0.0, top + margin - y0)
        if abs(dx) < 0.5 and dy < 0.5:
            break
        f["c"] = [f["c"][0] + dx, f["c"][1] + dy]
    f["c"] = [round(f["c"][0], 1), round(f["c"][1], 1)]
    f["h"] = round(f["h"], 1)
    return f


def travel_at(a, b, u, arc):
    """The framing part way (`u`, eased) through a move from `a` to `b` that pulls back by `arc` at its middle and
    banks along the travel (`camera.ts` travel)."""
    m = {k: a[k] + (b[k] - a[k]) * u for k in ("z", "fov", "yaw", "pitch", "roll")}
    m["c"] = [a["c"][j] + (b["c"][j] - a["c"][j]) * u for j in (0, 1)]
    m["h"] = a["h"] * (b["h"] / a["h"]) ** u
    if arc <= 0:
        return m
    bell = math.sin(math.pi * u)
    scale = max(a["h"], b["h"])
    lx = max(-1.0, min(1.0, (b["c"][0] - a["c"][0]) / scale))
    ly = max(-1.0, min(1.0, (b["c"][1] - a["c"][1]) / scale))
    return {**m, "h": m["h"] * (1 + arc * bell), "yaw": m["yaw"] - 0.42 * lx * bell, "pitch": m["pitch"] - 0.3 * ly * bell,
            "roll": m["roll"] + 0.1 * lx * bell, "fov": m["fov"] + 10 * arc * bell}


def calm_arc(a, b, W, H, top, sides=None):
    """The largest share of `b`'s arc whose move keeps the wall filling the view (nothing past its sides, the frame's
    when `sides` is None, or above `top`) at every point of the move; 0 when even a straight move would show the ground."""
    left, right = sides or (0, W)

    def fits(arc):
        for u in (0.15, 0.3, 0.5, 0.7, 0.85):
            x0, y0, x1, y1 = footprint(travel_at(a, b, u, arc), W, H)
            if x0 < left - 1 or x1 > right + 1 or y0 < top - 1:
                return False
        return True
    arc = b["arc"]
    while arc > 0.02 and not fits(arc):
        arc *= 0.7
    return round(arc, 3) if arc > 0.02 else 0.0


def uv_of(size, crop, aspect):
    """A crop [x, y, w] (fractions of the photo) at height/width `aspect` as texture coordinates [u0, v0, u1, v1],
    v up from the photo's bottom."""
    iw, ih = size
    x, y, w = crop
    h = w * iw * aspect / ih
    return [round(x, 4), round(1 - (y + h), 4), round(x + w, 4), round(1 - y, 4)]


def center_uv(size, aspect):
    iw, ih = size
    if ih / iw > aspect:
        h = iw * aspect / ih
        return [0, round(0.5 - h / 2, 4), 1, round(0.5 + h / 2, 4)]
    w = ih / aspect / iw
    return [round(0.5 - w / 2, 4), 0, round(0.5 + w / 2, 4), 1]


# ------------------------------------------------------------------ the page
# a page's words step down from the card's size, a step at a time, to half of it and on to the type floor; a gutter
# of GUTTER times the line's size stands between the photograph and words set under or beside it; the label's baseline
# stands a fifth over its cap height under the line box's top, and LABEL_GAP times its size over the first line's caps
GUTTER = 0.5
LABEL_GAP = 0.6
# how long a page's paper takes to close in round the photograph, and to open out again, beats
OPEN_OUT = 0.5
# beats the film holds on their grid, settled, before the hook's paper closes in round it
OPENING = 0.3
# a caption that enters word by word starts its words this many beats apart; a whole line fades in over FADE beats
PAGE_WORD = 0.09
FADE = 0.5
# a page sets its words in this many lines at most
MOST = 5
# the share of the crop's width the camera keeps outside a held page's picture box on each side
INSET = 0.035
# where an ungridded page's block centres, as a share of the type area's height from its top
OPTICAL = 0.46


def type_area(G):
    """The type area, [x0, y0, x1, y1] px: the frame inside its safe margins."""
    s = G["safe"]
    return [s["left"], s["top"], G["W"] - s["right"], G["H"] - s["bottom"]]


def page_boxes(G, photo, size):
    """Where the card's page sets the photograph and its words, [x0, y0, x1, y1] px each: the picture box (shares of
    the frame) and the line box (shares of the type area), turned a quarter on a frame wider than it is tall so the
    photograph stands in the frame's middle with its words in a column beside it. Words the card sets under, over or
    beside the photograph run from a gutter past its edge to the type area's edge, so they never touch it; words the
    card sets on the photograph keep the card's box."""
    W, H = G["W"], G["H"]
    a = type_area(G)
    px, py, pw, ph = photo["picture"]["box"] if photo["picture"]["show"] else (0, 0, 1, 1)
    lx, ly, lw, lh = photo["line"]["box"]
    turn = W > H and not (pw >= 1 and ph >= 1)
    if turn:
        px, py, pw, ph = py, px, ph, pw
        lx, ly, lw, lh = ly, lx, lh, lw
    pic = [round(px * W, 1), round(py * H, 1), round((px + pw) * W, 1), round((py + ph) * H, 1)]
    ln = [a[0] + lx * (a[2] - a[0]), a[1] + ly * (a[3] - a[1]), a[0] + (lx + lw) * (a[2] - a[0]), a[1] + (ly + lh) * (a[3] - a[1])]
    mid = [(ln[0] + ln[2]) / 2, (ln[1] + ln[3]) / 2]
    if not (pic[0] < mid[0] < pic[2] and pic[1] < mid[1] < pic[3]):
        g = GUTTER * size
        i = 0 if turn else 1
        if (ln[i] + ln[i + 2]) / 2 > (pic[i] + pic[i + 2]) / 2:
            ln[i], ln[i + 2] = max(pic[i + 2] + g, a[i]), a[i + 2]
        else:
            ln[i], ln[i + 2] = a[i], min(pic[i] - g, a[i + 2])
    return pic, [round(v, 1) for v in ln]


def even(words, span, n, cap):
    """`words` in `n` lines none wider than `cap`, the lines as near one width as they go (least sum of squared
    widths)."""
    near = cap * (1 + 1e-9)
    best = {0: (0.0, [])}
    for _ in range(n):
        best = {z: min(((c + span(a, z) ** 2, ls + [" ".join(words[a:z])]) for a, (c, ls) in best.items()
                        if a < z and span(a, z) <= near), default=None, key=lambda c: c[0]) for z in range(1, len(words) + 1)}
        best = {z: v for z, v in best.items() if v}
    return best[len(words)][1]


def set_page(text, size, floor, most, tall, wide, upper=False):
    """`text` broken for the page in the display face: (size, [line, ...]) at the largest size from `size` down to
    `floor` px, two px at a time, where it breaks into the fewest lines (`most` at most) none wider than `wide` and all
    of them no taller than `tall` from the first line's caps to the last baseline, each break where it leaves the
    widest line narrowest and the lines as near one width as they go; None when it fits at no size."""
    words = (text.upper() if upper else text).split()
    if not words:
        return size, []
    lead = compose.face_of("display")["lineHeight"]
    measure = lambda t: em(t, "display")
    span = lambda a, z: measure(" ".join(words[a:z]))
    # widest[n][z]: the narrowest the widest line can be setting the first z words in n lines
    widest = [{z: span(0, z) for z in range(1, len(words) + 1)}]
    for n in range(2, min(most, len(words)) + 1):
        widest.append({z: min(max(widest[-1][a], span(a, z)) for a in range(n - 1, z)) for z in range(n, len(words) + 1)})
    arranged = [even(words, span, n, w[len(words)]) for n, w in enumerate(widest, 1)]
    s = size
    while s >= floor:
        for ls in arranged:
            if CAP["display"] * s + (len(ls) - 1) * lead * s <= tall and all(measure(x) * s <= wide for x in ls):
                return s, ls
        s -= 2
    return None


def page(G, card, colors, text, label, at, sink, close, open_):
    """A page of the card's photo layout: the photograph in its picture box on the card's ground, `text` in the
    card's display face at the card's size in its line box (in caps on a card that sets its words on the photograph),
    under `label` in the card's label face; the paper closes in round the photograph over `close` ([from, to] beats;
    None when it is there from the first frame) and opens out from `open_`, the words enter from `at` on the card's
    entrance and leave at `sink`. None when the words fit no size the type floor allows."""
    photo = card["photo"]
    W, H = G["W"], G["H"]
    k = min(W, H) / 1080
    ln_card, lab_card = photo["line"], photo["label"]
    size = round(ln_card["size"] * k)
    pic, box = page_boxes(G, photo, size)
    over = pic[0] <= 0 and pic[1] <= 0 and pic[2] >= W and pic[3] >= H
    lab_size = round(lab_card["size"] * k)
    lab_text = compose.cased(label, lab_card["face"]) if label and not over else ""
    drop = round(1.2 * lab_size * CAP[lab_card["face"]]) if lab_text else 0
    gap = round(LABEL_GAP * lab_size) if lab_text else 0
    floor = math.ceil(FLOOR / CAP["display"])
    tall = box[3] - box[1] - drop - gap - 0.28 * size
    fit = set_page(text, size, floor, MOST, tall, box[2] - box[0] - 0.03 * size, upper=over)
    if not fit:
        return None
    size, said = fit
    lead = compose.face_of("display")["lineHeight"] * size
    if not over and photo["grid"]["rules"] == "none" and H >= W:
        # a page with no grid to hold it sets the photograph and its words as one block on the type area's optical
        # middle, so the paper round them balances instead of pooling under the words
        a = type_area(G)
        top = min(pic[1], box[1])
        bottom = max(pic[3], box[1] + drop + gap + CAP["display"] * size + (len(said) - 1) * lead + 0.28 * size)
        dy = a[1] + OPTICAL * (a[3] - a[1]) - (top + bottom) / 2
        dy = max(a[1] - top, min(a[3] - bottom, dy))
        pic = [pic[0], round(pic[1] + dy, 1), pic[2], round(pic[3] + dy, 1)]
        box = [box[0], round(max(a[1], box[1] + dy), 1), box[2], round(min(a[3], box[3] + dy), 1)]
    y = box[1] + drop + gap + CAP["display"] * size
    enter = ln_card["enter"]
    lines, t = [], at
    for i, s in enumerate(said):
        words, x, wx = s.split(), box[0], []
        for w in words:
            wx.append(round(x, 1))
            x += em(w + " ", "display") * size
        lines.append({"text": s, "x": box[0], "y": round(y + i * lead, 1), "size": size, "at": round(t, 3),
                      "words": [{"text": w, "x": x_, "at": round(t + j * PAGE_WORD, 3)} for j, (w, x_) in enumerate(zip(words, wx))]})
        t += (len(words) * PAGE_WORD if enter in ("slam", "rise") else len(s) * LETTER if enter == "type" else 0.12)
    tone = lambda role: colors.get(role, role)
    face = lambda f: "display" if f == "display" else "text"
    return {"pic": pic, "box": box, "ground": tone(photo["ground"]), "over": over, "enter": enter,
            "color": tone(ln_card["color"]), "scrim": ln_card.get("scrim", 0) if over else 0, "scrimColor": tone("ink"),
            "weight": compose.face_of("display")["weight"], "tracking": compose.face_of("display")["tracking"], "lines": lines,
            "label": {"text": lab_text, "x": box[0], "y": box[1] + drop, "size": lab_size, "face": face(lab_card["face"]),
                      "weight": compose.face_of(lab_card["face"])["weight"], "color": tone(lab_card["color"]),
                      "tracking": compose.face_of(lab_card["face"])["tracking"], "at": round(at, 3)} if lab_text else None,
            "rules": photo["grid"]["rules"] != "none", "close": [round(v, 3) for v in close] if close else None,
            "open": [round(open_, 3), round(open_ + OPEN_OUT, 3)], "sink": round(sink, 3)}


def page_words(pg):
    """The words a page sets, as one line of text."""
    return " ".join(ln["text"] for ln in pg["lines"]) if pg else ""


def page_landed(pg):
    """The beat the last word of a page has entered."""
    return max(w["at"] for ln in pg["lines"] for w in ln["words"]) + RISE if pg and pg["lines"] else None


# ------------------------------------------------------------------ the band's words
def bio_em(text):
    """A bio line's width in em in the text face, each emoji (which the text face has no glyph for) a square em and a
    little."""
    marks = EMOJI.findall(text)
    return em(EMOJI.sub("", text)) + 1.15 * len(marks)


def bio_wrap(text, size, width, most):
    """`text` in the fewest lines no wider than `width` px at `size`, emoji counted (bio_em), split where the longest
    line is shortest, so no line is a lone word or a lone emoji when the words could share; None when it needs more
    than `most`."""
    words = text.split()
    if not words:
        return []
    fits = lambda t: bio_em(t) * size <= width
    from itertools import combinations
    for n in range(1, min(most, len(words)) + 1):
        best = None
        for cuts in combinations(range(1, len(words)), n - 1):
            edges = (0, *cuts, len(words))
            lines_ = [" ".join(words[a:b]) for a, b in zip(edges, edges[1:])]
            if all(fits(x) for x in lines_):
                wide = max(bio_em(x) for x in lines_)
                if best is None or wide < best[0]:
                    best = (wide, lines_)
        if best:
            return best[1]
    return None


def bio_lines(bio, size, width, most):
    """Their bio as they wrote it, emoji kept, in lines no wider than `width` px at `size`: each of their lines on lines
    of its own, one that needs two broken after its ' /' first, never a line that runs from one of theirs into the next;
    their lines from the first that fit in `most` lines, None when the first does not."""
    out = []
    for ph in [" ".join(x.split()) for x in (bio or "").split("\n")]:
        if not ph:
            continue
        parts = [x.strip() + " /" for x in ph.split(" / ")[:-1]] + [ph.split(" / ")[-1].strip()]
        if bio_wrap(ph, size, width, 1):
            lines_ = [ph]
        elif len(parts) > 1 and all(bio_wrap(x, size, width, 1) for x in parts):
            lines_ = parts
        else:
            lines_ = bio_wrap(ph, size, width, most) or [None] * (most + 1)
        if len(out) + len(lines_) > most:
            break
        out += lines_
    return out or None


def closer_layout(G, fmt, handle, bio, ask):
    """The closer: the frame round the whole first screen with its band as the profile's header, above the frame in a
    picture as tall as wide or taller, beside it otherwise, carrying their handle, their bio and the film's ask, each
    set at its CLOSER_SIZES px on screen once the camera has stopped (the handle smaller where it is wider than the
    column, never under the type floor; the bio as they wrote it (bio_lines), on up to four lines above the frame and
    six beside it, where the band is as tall as the grid). The camera's stop view takes in the frame and its band whole as
    one card: above the frame, the card as wide as it can stand with the handle's caps just inside the type area's top
    and its bottom bar on the picture's bottom edge, so no wall shows under it, and the words inside the type area's
    sides; beside it, the card 24 px inside the picture's side edges and its bottom bar on the bottom edge, and the
    words in the middle of the band. Returns
    the band's lines and height (band px), its side, the stop view's center and height (px of the wall), and whether
    every line fits."""
    W, H, safe = G["W"], G["H"], G["safe"]
    size = CLOSER_SIZES[fmt]
    side = "top" if H >= W else "left"
    most = 4 if side == "top" else 6
    for rows in (3, 2, 1):
        got = _closer_at(G, first_screen(G, rows), size, side, most, handle, bio, ask)
        if got[-1] or rows == 1:
            return got


def _closer_at(G, box, size, side, most, handle, bio, ask):
    """closer_layout round the grid rows `box`, with whether every line of the bio is set (the box last)."""
    W, H, safe = G["W"], G["H"], G["safe"]
    s = box[2] / BAND_W
    ft = FT * s

    def lay(q, top, left, right):
        """The header at q screen px per band px, the handle's caps `top` band px down, its column from `left` to
        `right` band px: the lines and the last baseline, None when a line does not fit the column."""
        col = right - left
        hs = min(max(size["handle"], (FLOOR + 2) / CAP["display"]), col * q / em(handle, "display")) / q
        ls, az = size["bio"] / q, size["ask"] / q
        if hs * q * CAP["display"] < FLOOR:
            return None
        y = top + hs * CAP["display"]
        out = [line(handle, left, y, round(hs, 1), face="display", weight=700, name="handle", written=True)]
        said = bio_lines(bio, ls, col, most) if bio else []
        if said is not None and bio and len(said) < len(bio_lines(bio, ls, col, 99) or []):
            return None
        if said is None:
            return None
        for i, w in enumerate(said):
            y += 26 / q + ls * CAP["text"] if i == 0 else ls * 1.3
            out.append(line(w, left, y, round(ls, 1), weight=500, name=f"bio-{i}", written=True))
        asks = wrap(ask, az, col, weight=800, most=2, face="display") if ask else []
        if asks is None:
            return None
        for i, w in enumerate(asks):
            y += 50 / q + az * CAP["display"] if i == 0 else az * 1.06
            out.append(line(w, left, y, round(az, 1), face="display", weight=800, name=f"ask-{i}"))
        return [dict(ln, x=round(ln["x"], 1), y=round(ln["y"], 1)) for ln in out], y

    if side == "left":
        hb = (box[3] + 2 * ft) / s
        x0, y0, x1, y1 = frame_block(box, hb, side)
        K = min((H - 48) / (y1 - y0), (W - 48) / (x1 - x0))
        got = lay(s * K, 0.0, PAD, BAND_W - PAD)
        if got is None or got[1] + PAD > hb:
            return [], round(hb, 1), side, [(x0 + x1) / 2, (y0 + y1) / 2], H / K, box, False
        lines_, last = got
        shift = (hb - last - lines_[0]["y"] + lines_[0]["size"] * CAP["display"]) / 2
        # the card sits with its bottom bar on the picture's bottom edge, so no wall shows under it
        cy = y1 - (H / 2 + 2) / K
        return ([dict(ln, y=round(ln["y"] + shift, 1)) for ln in lines_], round(hb, 1), side,
                [(x0 + x1) / 2, cy], H / K, box, True)
    K = (W - 32) / (box[2] + 2 * ft)
    while K > 0.3:
        q = s * K
        bl = W / 2 - box[2] * K / 2
        got = lay(q, PAD, max(PAD, (safe["left"] + 12 - bl) / q), min(BAND_W - PAD, (W - safe["right"] - 12 - bl) / q))
        if got:
            lines_, last = got
            hb = round(last + PAD)
            top = safe["top"] + 12 - PAD * q
            if top + (hb * s + 2 * ft + box[3]) * K <= H + 2:
                # the card's bottom bar on the picture's bottom edge
                cy = box[1] + box[3] + ft - (H / 2 + 2) / K
                return lines_, hb, side, [box[0] + box[2] / 2, cy], H / K, box, True
        K *= 0.99
    return [], 2 * PAD, side, [box[0] + box[2] / 2, box[1] + box[3] / 2], H / 0.6, box, False


def width_of(ln):
    return em(ln["text"], ln["face"], ln["weight"], ln["tracking"]) * ln["size"]


# ------------------------------------------------------------------ the hook's posts
def hook_slots(audit, breaks, covered=None):
    """The posts the hook visits, every one a post with its cover on the wall (`covered`, the slots that have one; all
    when None): the research's lead finding that names at least two posts on rows two to four (the frame's band stands
    above its post, so a first-row post would put it over the profile's header), else the posts that break the first
    screen."""
    on = (lambda s: True) if covered is None else (lambda s: s in covered)
    for f in (audit or {}).get("findings") or []:
        pos = [p for p in f.get("positions") or [] if 3 <= p < 12 and on(p)]
        if len(pos) >= 2:
            return sorted(pos)
    slots = [p - 1 for p in breaks if on(p - 1)]
    return sorted([s for s in slots if s >= 3] or slots)


# a held post's times from its beat's start: the frame meets the photograph, closes onto its subject and locks; the
# hook's camera settles on the frame OPEN beats after it lands
MEET, LOCK, OPEN = 0.25, 0.85, 0.4


def full_length(entering, read=READ):
    """A held post's beats, on the half beat: the caption enters 0.15 after the lock and takes `entering` beats from its
    first word's start to its last word landed; it holds whole for `read`; the words leave 0.35 before the drop (0.8),
    and the seat (0.6)."""
    return math.ceil((LOCK + 0.15 + entering + read + 0.35 + 0.8 + 0.6) * 2) / 2


# the places a caption can name, which a held post's label carries in the caption's own words
PLACES = ["lisbon", "porto", "lyon", "paris", "palermo", "ortigia", "sicily", "oaxaca", "marrakech", "marseille", "rome",
          "london", "tokyo", "mexico city", "new york", "berlin", "barcelona", "madrid", "naples", "athens", "istanbul",
          "kyoto", "seoul", "bali", "los angeles", "san francisco", "chicago", "amsterdam", "provence", "sintra",
          "copenhagen", "vienna", "prague", "budapest", "seville", "granada"]


def place_in(caption):
    """The first place from PLACES the caption names, as it is written there, else ""."""
    low = (caption or "").lower()
    hits = [(m.start(), caption[m.start():m.end()]) for p in PLACES for m in [re.search(rf"\b{re.escape(p)}\b", low)] if m]
    return min(hits)[1] if hits else ""


def day_of(iso):
    return dt.date.fromisoformat(iso)


# ------------------------------------------------------------------ the board
def build(fmt, before, nine, plan, audit, breaks, taste, palette, handle, bio=None, frames=None, style=None, tempo=None):
    """One format's board in the style `style` (a card id; the trio's first when None), its beats starting on beats of
    music at `tempo` bpm. `frames` are the beat frames of the hook and each post (the reel's, so every format cuts on
    the same frames); with none, they come from this format's own bands."""
    card = compose.card(style or compose.TRIO[0])
    compose.use(card["id"])
    tempo = float(tempo or BPM)
    G = geometry(fmt)
    W, H = G["W"], G["H"]
    lay = G["layout"]
    sides = wall_sides(G)
    colors = colors_of(card, taste, palette)
    pace = pace_of(card)
    read, peak_read, drop_len, slide_len = READ * max(pace, 1.0), PEAK_READ * pace, DROP * pace, SLIDE * pace
    # half-second units per beat of the music
    per_beat = BPM / tempo
    # the card's curves for every camera settle and the caption's entrance from the card's photo layout
    SETTLE = card["ease"]["move"]
    enter = card["photo"]["line"]["enter"]
    m = len(nine)
    covered = {b["pos"] - 1 for b in before if b.get("file") and b.get("size")}
    slots = hook_slots(audit, breaks, covered)
    words_of = {b["pos"] - 1: b.get("caption") or "" for b in before}

    # the bands' words: the hook's band carries the film's hook, the line the plan writes for the glow-up (with none,
    # the words of the post the frame rests on); each held post's band its own caption; the closer's band the
    # profile's header with the film's ask. The frame comes to rest on the post nearest the grid's middle column among
    # those that have words, where its band sits square in the frame with the wall on both sides of it
    film = plan.get("film") or {}
    bands = {}
    # with no post of theirs on the wall the hook has no frames and the film opens on the first new post
    rest_slot = min(slots, key=lambda s: (not words_of.get(s), abs(s % 3 - 1), s)) if slots else None
    hook_words = bare(film.get("hook")) or words_of.get(rest_slot, "")
    bands["hook"] = {"lines": [], "h": 0}
    unfit = {}
    # the hook's title: the card's page sets the line in its line box with a window onto their grid in its picture
    # box, on whole beats of the music, for as long as it takes to read (a quarter second a word and 0.9 s to take it
    # in, two beats or more). Then the paper opens out, the frame lands and hops across the posts that break the screen
    n_hook = len(hook_words.split())
    title_beats = max(2, round((0.25 * n_hook + 0.9) * 2 / per_beat))
    title_len = title_beats * per_beat if hook_words else 0.0
    hook_len = (title_len + 2.5 * pace) if slots else 0.0
    # the posts the frame holds on read whole with their caption on the band; between them each post comes into the
    # grid by a quick move, falling from above the view and sliding along the top row by turns, so no two posts in a
    # row share a move
    held = [i in held_posts(m) for i in range(m)]
    # how each post comes in follows its photograph: a post the frame holds is closed on, a landscape one slides in
    # along the row, a portrait or square one falls into its cell
    wide_of = lambda p: p["size"][0] / p["size"][1] > 1.05
    moves = ["close" if held[i] else "slide" if wide_of(p) else "drop" for i, p in enumerate(nine)]
    # the film's peak: the middle post the frame holds, read longest
    peak = sorted(held_posts(m))[1] if len(held_posts(m)) >= 3 else None
    # each post the frame holds is set as the card's page: its photograph in the card's picture box on the card's
    # ground, its caption under the day it goes up in the card's line box; a caption that fits no size the type floor
    # allows is reported as unfit and its page carries the photograph alone
    dates = [day_of(s["date"]) for s in plan["slots"]][:m]
    day = lambda i: f"{dates[i]:%A} {dates[i].day} {dates[i]:%B}" if i < len(dates) else ""
    said, entering = {}, {}
    for i, (p, h) in enumerate(zip(nine, held)):
        if h and p["caption"]:
            pg = page(G, card, colors, p["caption"], day(i), 0, 0, None, 0)
            if pg:
                said[i], entering[i] = p["caption"], page_landed(pg)
            else:
                unfit[f"post-{p['n']}"] = p["caption"]
    # the closer's band is the profile's header round the whole first screen
    ask = bare(film.get("ask"))
    at_handle = "@" + handle.lstrip("@")
    header_lines, closer_hb, closer_side, closer_c, closer_h, closer_box, fits = closer_layout(G, fmt, at_handle, bio or "", "")
    # the header's paper opens in the picture; its words are set over it as type a browser sets, so their bio keeps its
    # emoji and its line breaks
    bands["closer"] = {"lines": [], "h": closer_hb}
    if not fits:
        unfit["closer"] = " ".join(x for x in (at_handle, bio or "") if x)

    # beats and their starts, on whole frames
    if frames is None:
        lengths = [hook_len] + [full_length(entering.get(i, RISE), peak_read if i == peak else read) if mv == "close"
                                else drop_len if mv == "drop" else slide_len for i, (p, mv) in enumerate(zip(nine, moves))]
        # every beat starts on a beat of the music
        beat_frames = PULSE * per_beat
        bounds = [round(round(sum(lengths[:i]) * PULSE / beat_frames) * beat_frames) for i in range(len(lengths) + 1)]
        frames = [b - a for a, b in zip(bounds, bounds[1:])]
    lengths = [f / PULSE for f in frames]
    starts = [sum(frames[:i]) / PULSE for i in range(len(frames))]
    C = sum(frames) / PULSE

    sound, story, keys, cam, band_keys, posts = [], [], [], [], [], []

    def cue(kind, at, beat, what, **kw):
        sound.append({"kind": kind, "at": round(at, 3), "beat": beat, "what": what, **kw})

    def framing(c, h, z=0.0, fov=HOLD_FOV, yaw=0.0, pitch=0.0, roll=0.0):
        return {"c": [round(c[0], 1), round(c[1], 1)], "h": round(h, 1), "z": round(z, 1), "fov": fov, "yaw": round(yaw, 3),
                "pitch": round(pitch, 3), "roll": round(roll, 3)}

    walled_keys = []

    def camkey(t, f, arc=0.0, walled=True, ease=None, **travel):
        if walled:
            f = inside(f, W, H, G["grid"]["y0"], sides=sides)
        cam.append({"t": round(t, 3), **f, "arc": arc, **({"ease": ease} if ease else {}), **({"travel": travel} if travel else {})})
        walled_keys.append(walled)

    def fkey(t, box, z, ease="move"):
        keys.append({"t": round(t, 3), "box": [round(v, 1) for v in box], "z": round(z, 1), "ease": ease})

    def bkey(t, open_, band, side="top"):
        band_keys.append({"t": round(t, 3), "open": open_, "band": band, **({"side": side} if side != "top" else {})})

    def station_framing(box, z, yaw=0.0, wide=1.0):
        """The camera on a frame at rest: its top at the type area's top plus a margin, the whole frame in, as far as
        the view stays on the wall; `wide` stands the camera that much further back with the frame's top where it
        was."""
        x0, top, x1, bottom = frame_block(box, 0, "top")
        h = max((bottom - top) * 1.3, (x1 - x0) * 1.18 * H / W)

        def at(h, hv):
            cy = top + (G["safe"]["top"] + 30 - H / 2) * h / -H
            return framing([(x0 + x1) / 2, cy], hv, z, yaw=yaw)
        hv = round(h, 1) * wide
        f = at(h, hv)
        # a view wider than the wall narrows to it, the frame's top kept at the type area's top
        n = inside(f, W, H, G["grid"]["y0"], sides=sides)["h"]
        return at(min(h, n), n) if n < hv - 0.5 else f

    # ---------------- the hook
    # the card's move for words sets the hook line over the picture; as it gives way the frame lands on the post the
    # line speaks for, the camera settling on it, then hops across the other posts that break the first screen, in
    # reading order, while the camera draws back over the whole first screen
    bkey(0, 0.0, "hook")
    gscreen = first_screen(G)
    wide_h = max(gscreen[2] * 1.12 * H / W, gscreen[3] * 1.05)
    if slots:
        hook_end = lengths[0]
        title_end = min(title_len, max(0.0, hook_end - 1.2)) if title_len else 0.0
        land_t = title_end + 0.15 if title_len else 0.35
        # the title is the card's page: the film opens on their grid, the paper closes in round a window onto it in the
        # picture box, the hook line enters under their handle; its words leave and its paper opens out onto the wall
        # as the frame lands
        shut = [OPENING, OPENING + OPEN_OUT]
        title_page = page(G, card, colors, hook_words, at_handle, shut[1] + 0.1, title_end - 0.3, shut,
                          title_end - 0.25) if title_len else None
        if title_len and not title_page:
            unfit["hook"] = hook_words
        others = [s for s in slots if s != rest_slot]
        rest_box = cell(G, rest_slot)
        big = [rest_box[0] - rest_box[2] * 0.6, rest_box[1] - rest_box[3] * 0.6, rest_box[2] * 2.2, rest_box[3] * 2.2]
        fkey(0, big, 600, "move")
        if title_end > 0.35:
            fkey(title_end - 0.35, big, 600, "move")
        fkey(land_t, rest_box, WALL_Z + 8, "land")
        cue("hit", land_t, "hook", "the frame lands on the first post that breaks the grid", weight=0.55, bright=0.6)
        hook_rest = max(0.0, title_end - max(0.6, 0.25 * title_end)) if title_len else land_t + 0.9
        # the hops run from half a second after the landing to 0.6 before the hook's end, a quarter apart or more
        last_hop = hook_end - 0.6
        room = max(0.0, last_hop - (land_t + 0.5))
        others = others[:int(room / 0.25) + 1]
        gap = min(0.5, room / (len(others) - 1)) if len(others) > 1 else 0.0
        hop_t = [last_hop - gap * (len(others) - 1 - j) for j in range(len(others))]
        prev = rest_box
        for s, t in zip(others, hop_t):
            fkey(t - max(0.2, min(gap, 0.5) * 0.8), prev, WALL_Z + 8)
            fkey(t, cell(G, s), WALL_Z + 8, "land")
            prev = cell(G, s)
        last_box = prev
        story.append({"beat": "hook", "reveals": (f"'{hook_words}', set by the style's move for words, then " if title_len else "")
                      + "the frame landing on a post that breaks the first screen"
                      + (", then hopping across the others that break it" if others else ""),
                      "carries": "the frame lifting off the wall"})
        # the hook's camera: low and turned on the wall, settling on the frame as it lands, then drawing back over the
        # first screen while the frame hops
        f = station_framing(rest_box, WALL_Z, yaw=-0.06, wide=HOOK_WIDE)
        f["pitch"] = 0.2
        camkey(0, {**f, "h": round(f["h"] * 1.12, 1), "pitch": 0.26, "yaw": -0.1})
        if title_end > 0.35:
            camkey(title_end - 0.35, {**f, "h": round(f["h"] * 1.1, 1), "pitch": 0.25, "yaw": -0.09})
        camkey(land_t + OPEN, f, ease=SETTLE)
        if others:
            camkey(max(land_t + OPEN + 0.05, hop_t[0] - 0.15), {**f, "h": round(f["h"] * 0.97, 1)})
            camkey(hop_t[min(1, len(others) - 1)] + 0.1, framing([W / 2, gscreen[1] + gscreen[3] / 2 - 40], wide_h, 0, yaw=0.06, pitch=0.12), ease=SETTLE)
        prev_slot_box, prev_free = last_box, (hop_t[-1] if others else land_t + 0.9) + 0.05
    else:
        story.append({"beat": "hook", "reveals": "no grid of theirs to show: the film opens on the first new post",
                      "carries": "nothing"})
        prev_slot_box, prev_free = None, 0.0
        title_end = 0.0
        title_page = None

    # ---------------- the posts
    for i, p in enumerate(nine):
        a = starts[i + 1]
        L = lengths[i + 1]
        full = held[i]
        bid = f"post-{p['n']}"
        iw, ih = p["size"]
        c34 = p["crop34"]
        focal = p.get("focal") or [c34[0] + c34[2] / 2, c34[1] + c34[2] * iw * 4 / 3 / ih / 2]
        # each move turns toward the side of the photograph its subject is on
        side = 1 if focal[0] < 0.5 else -1
        # the crop at the station, BAND_W wide at the wall's top: a held post's at the shape of the card's picture box,
        # round its focal point (the cell crop's center in a plan without one), as close on its subject as SUBJECT
        # where the photograph has the pixels for the box, else wider; a passing post's the 3:4 box round its subject.
        # The whole photograph is scaled to match
        cw = G["station"]["w"]
        pic = page_boxes(G, card["photo"], 0)[0]
        pw, ph = pic[2] - pic[0], pic[3] - pic[1]
        ratio = pw / ph if full else 3 / 4
        widest = min(1.0, ratio * ih / iw)
        subj = crop_box_of(iw, ih, focal, ratio, min(1.0, max(SUBJECT, 0.9 * pw / (widest * iw))) if full else SUBJECT)
        scale = cw / (subj[2] * iw)
        crop_h = cw / ratio
        cx0, cy0 = G["station"]["x"], G["grid"]["y0"]
        crop_box = [cx0, cy0, cw, crop_h]
        whole = [cx0 - subj[0] * iw * scale, cy0 - subj[1] * ih * scale, iw * scale, ih * scale]
        seat = a + L - 0.6
        slot0 = cell(G, 0)
        move = moves[i]
        step = G["grid"]["cw"] + G["grid"]["g"]
        if move == "close":
            # the whole photograph tips up in, the frame lands round it and closes onto the subject
            meet, close, lock = a + MEET, a + MEET + 0.05, a + LOCK
            drop = seat - 0.8
            fly = [a - 0.4, meet - (a - 0.4)]
            reflow = [drop + 0.1, seat - 0.05 - (drop + 0.1)]
        elif move == "slide":
            # the frame waits on the grid's first cell; the 3:4 cell slides in along the row from the left on the curve
            # the row steps along on, so it pushes the row along, and seats in it, the camera trucking with it
            meet = close = lock = drop = seat
            fly = [a + 0.2, seat - (a + 0.2)]
            reflow = fly
            row = lambda dx: framing([slot0[0] + slot0[2] / 2 + dx, slot0[1] + slot0[3] / 2], slot0[3] * DROP_NEAR, 0, yaw=-0.05, pitch=0.14)
        else:
            # the 3:4 cell falls from above the camera's view close on the grid's first cell straight into the frame
            # waiting there
            meet = close = lock = drop = seat
            fly = [a + 0.1, seat - (a + 0.1)]
            # the row makes room as the cell comes down, so the first cell stands empty only for its last moment
            reflow = [seat - 0.9, 0.85]
            near = inside(framing([slot0[0] + slot0[2] / 2, slot0[1] + slot0[3] / 2], slot0[3] * DROP_NEAR, 0, yaw=0.06 * side, pitch=0.16,
                                  roll=-0.01 * side), W, H, G["grid"]["y0"], sides=sides)
        # the page: the paper closes in round the photograph as the frame locks on it, the caption enters, then sinks
        # and the paper opens out as the crop draws back to drop into the grid
        pg = page(G, card, colors, said.get(i, ""), day(i), lock + 0.15, drop - 0.35, [close, lock + 0.1], drop - 0.15) if full else None
        posts.append({"n": p["n"], "beat": bid, "file": p["file"], "size": p["size"], "uvSubject": uv_of(p["size"], subj, 1 / ratio),
                      "uv34": uv_of(p["size"], p["crop34"], 4 / 3),
                      "uvFocal": [round(focal[0], 4), round(1 - focal[1], 4)], "whole": [round(v, 1) for v in whole],
                      "crop": [round(v, 1) for v in crop_box], "z": LIFT, "slot": slot0, "move": move, "side": side, "full": full,
                      "times": {"fly": [round(fly[0], 3), round(fly[1], 3)], "close": [round(close, 3), round(lock - close, 3)],
                                "drop": [round(drop, 3), round(seat - drop, 3)], "seat": round(seat, 3),
                                "reflow": [round(reflow[0], 3), round(reflow[1], 3)]},
                      **({"peak": True} if i == peak else {}), **({"page": pg} if pg else {}),
                      **({"from": [round(near["c"][0], 1), round(near["c"][1] - near["h"] / 2 - slot0[3] * 0.7, 1)]} if move == "drop" else {})})
        # the camera's framings: square on the station, the crop a little past the page's picture box on every side
        # (INSET), so the paper's window cuts the photograph and the frame round the crop stands under the paper, and on
        # the photograph whole as it lands
        hv = H * cw / pw * (1 - 2 * INSET)
        if pg:
            pic = pg["pic"]
        st = framing([cx0 + cw / 2 - ((pic[0] + pic[2]) / 2 - W / 2) * hv / H, cy0 + crop_h / 2 - ((pic[1] + pic[3]) / 2 - H / 2) * hv / H], hv, LIFT)
        if move == "close":
            tall = max(whole[3], whole[2] * H / W) * 1.12
            wf = framing([whole[0] + whole[2] / 2, whole[1] + whole[3] / 2], max(tall, st["h"] * 1.05), LIFT, yaw=0.14 * side, roll=-0.03 * side)
        # the frame: off the last slot, round the part of the photograph the camera sees as it lands, onto the crop,
        # down into slot 0. For a post that slides in, it reaches the station at the crop's own size before the card
        # sets off, so the card seats in it with no second border, and it flashes as the card seats; for a post that
        # falls, it waits on slot 0, rising a little toward the card, and lands with it
        if prev_slot_box:
            fkey(prev_free, prev_slot_box, WALL_Z + 8)
        if move == "close":
            # it rises off the slot as the photograph starts to come in, so it is in sight over the photograph
            # the whole way to its landing
            if prev_slot_box and fly[0] > prev_free + 0.01:
                fkey(fly[0], prev_slot_box, WALL_Z + 8)
            x0, y0, x1, y1 = footprint(inside(wf, W, H, G["grid"]["y0"], sides=sides), W, H, LIFT + 6)
            inset = 0.08 * (x1 - x0)
            lx0, ly0 = max(whole[0], x0 + inset), max(whole[1], y0 + inset)
            lx1, ly1 = min(whole[0] + whole[2], x1 - inset), min(whole[1] + whole[3], y1 - inset)
            land = [lx0, ly0, lx1 - lx0, ly1 - ly0]
            fkey(meet, land, LIFT + 6, "land")
            fkey(close, land, LIFT + 6)
            fkey(lock, crop_box, LIFT + 6, "close")
        elif move == "slide":
            g = 0.04
            fkey(fly[0] + 0.3, [slot0[0] - slot0[2] * g, slot0[1] - slot0[3] * g, slot0[2] * (1 + 2 * g), slot0[3] * (1 + 2 * g)], WALL_Z + 24)
            fkey(seat, slot0, WALL_Z + 8, "spring")
        if move == "drop":
            g = 0.03
            fkey(seat - 0.55, [slot0[0] - slot0[2] * g, slot0[1] - slot0[3] * g, slot0[2] * (1 + 2 * g), slot0[3] * (1 + 2 * g)], WALL_Z + 40)
            fkey(seat, slot0, WALL_Z + 8, "fall")
        elif move == "close":
            fkey(drop, crop_box, LIFT + 6)
            fkey(seat, slot0, WALL_Z + 8, "drop")
        # the post's one sound is its landing in the grid; the frame and the words move silently
        cue("hit", seat, bid, f"post {p['n']} seats at the top left of the grid", weight=0.95, bright=0.45)
        # the camera: on the photograph whole, then pushed onto the subject, then back over the grid as it drops; for a
        # post that falls, close on the grid's first cell as the card falls into it, holding on it as it seats
        gscreen = first_screen(G)
        wide_h = max(gscreen[2] * 1.12 * H / W, gscreen[3] * 1.05)
        wide = framing([W / 2, gscreen[1] + gscreen[3] / 2 - 40], wide_h if full else wide_h * 0.92, 0, yaw=-0.08 * side, pitch=0.1 * side, roll=0.015 * side)
        if move == "close":
            camkey(meet + 0.05, wf, 0.3 if i == 0 else 0.22, ease=SETTLE)
            camkey(lock + 0.1, st, 0.0, walled=False, ease=SETTLE)
        elif move == "slide":
            camkey(fly[0] + 0.3, row(-0.4 * step), ease=SETTLE)
            camkey(seat + 0.2, row(0.3 * step), ease=SETTLE)
        if move == "drop":
            camkey(seat - 0.05, near)
            camkey(seat + 0.35, {**near, "h": round(near["h"] * 1.04, 1)})
        elif move == "close":
            camkey(drop, st, walled=False)
            camkey(seat + 0.1, wide, 0.08)
        caption = page_words(pg)
        story.append({"beat": bid, "reveals": ((f"post {p['n']}'s subject: the frame closes from the whole photograph onto it as the card's page closes in round it"
                                                + (f", and the page says '{caption}' under the day it goes up" if caption else ", wordless")) if move == "close"
                                               else f"post {p['n']} sliding in along the top row from the left, pushing the row along, into the frame waiting on the grid's first cell, wordless" if move == "slide"
                                               else f"post {p['n']} falling from the lens into the frame on the grid's first cell, wordless")
                                              + (f" (the moment: '{p['moment']}')" if p.get("moment") else ""),
                      "carries": (f"the frame, carrying post {p['n']}'s subject down into the top of the grid, opening to its cell as it lands" if move == "close"
                                  else f"the frame on the first cell, landing with post {p['n']}")
                                 + (", while the older posts step along" if before else ", while the new posts before it step along" if i else "")})
        prev_slot_box = slot0
        prev_free = seat + (0.35 if move == "drop" else 0.2 if move == "slide" else 0.1)

    if not slots:
        hook_rest = posts[0]["times"]["drop"][0] - 0.1

    # ---------------- the closer
    # the frame opens round the first screen (fewer whole rows where the header needs the room) and its band unfolds as the profile's header; the handle enters
    # letter by letter as the band opens, the bio word by word, then the ask letter by letter, and the camera, settled
    # on the card as the frame locks, stops with the music once the ask has landed
    gscreen = closer_box
    lock_c = C + 0.6
    fkey(prev_free, prev_slot_box, WALL_Z + 8)
    fkey(lock_c, gscreen, WALL_Z + 8, "close")
    bkey(prev_free, 0.0, "closer", closer_side)
    bkey(prev_free + 0.15, 0.0, "closer", closer_side)
    bkey(lock_c, 1.0, "closer", closer_side)
    # the header's words appear as the frame locks: their handle, then their bio; the profile holds, then the card's
    # closer takes the frame with the film's ask, and the picture and the music stop together on it
    header_at = lock_c
    closer_at = lock_c + 0.8 + 2.6 * pace
    # the closing card settles inside a second or a beat and a half of the music, then holds still a moment before the
    # stop: never a second, which reads as a frozen frame with the music still playing
    stop = round(math.ceil((closer_at + max(2.4, 1.6 * per_beat)) * PULSE - 1e-6) / PULSE, 3)
    end = stop + HOLD_AFTER
    cue("riser", C - 1.0, "closer", "the frame opens out over the whole first screen", beats=1.6)
    cue("impact", lock_c, "closer", "the frame locks round the first screen")
    cue("hit", closer_at, "closer", "the style's closing card takes the frame", weight=0.7, bright=0.5)
    cue("stop", stop, "closer", "picture and music stop together on the closing card")
    camkey(lock_c + 0.2, framing(closer_c, closer_h, 0, fov=CLOSER_FOV), 0.05, walled=False, ease=SETTLE)
    still_f = framing(closer_c, closer_h, 0, fov=CLOSER_FOV)
    s_c = gscreen[2] / BAND_W
    plane = WALL_Z + 8 + 10 * s_c
    header = {"at": round(header_at, 3), "lines": []}
    for k, ln in enumerate(header_lines):
        x, y, scale = project(still_f, W, H, *band_point(gscreen, closer_hb, closer_side, ln["x"], ln["y"]), plane)
        header["lines"].append({"text": ln["text"], "x": round(x, 1), "y": round(y, 1), "size": round(ln["size"] * s_c * scale, 1),
                                "face": ln["face"], "bold": ln["weight"] >= 700, "name": ln["name"],
                                "at": round(header_at + 0.12 * k, 3)})
    camkey(stop, framing(closer_c, closer_h, 0, fov=CLOSER_FOV), walled=False)
    story.append({"beat": "closer", "reveals": "the profile's first screen whole as it will look the day the last post goes up, under their handle and their own bio, "
                             + ("the posts the hook visited pushed off it" if before else "the new posts alone on it")
                             + (f", and the ask '{ask}'" if ask else ""),
                  "carries": "the frame, opened round the whole first screen, its band now the profile's header"})

    # a move between two framings on the wall pulls back and banks only as far as keeps the wall filling the view
    for i in range(1, len(cam)):
        if walled_keys[i] and walled_keys[i - 1]:
            cam[i]["arc"] = calm_arc(cam[i - 1], cam[i], W, H, G["grid"]["y0"], sides=sides)

    # ---------------- the wall's posts: theirs at their slots, then each new one from its seat
    # their posts stand muted beside the new ones, so the film's grade is the new grid's alone
    wall = [{"key": f"before-{b['pos']}", "file": b["file"], "uv": center_uv(b["size"], 4 / 3), "slot": b["pos"] - 1, "from": 0, "mute": MUTE}
            for b in before if b.get("file") and b.get("size")]
    for pp in posts:
        wall.append({"key": f"post-{pp['n']}", "file": pp["file"], "uv": pp["uv34"], "slot": 0, "from": pp["times"]["seat"]})
    reflows = [pp["times"]["reflow"] for pp in posts]

    frames = frames + [round((end - C) * PULSE)]
    ids = ["hook"] + [f"post-{p['n']}" for p in nine] + ["closer"]
    beats = []
    for bid, fr in zip(ids, frames):
        layers = []
        if bid == "hook":
            layers = [{"kind": "Wall", "cells": wall, "reflows": reflows, "grid": G["grid"]},
                      {"kind": "Frame", "keys": keys, "bands": band_keys, "words": bands},
                      {"kind": "Camera", "keys": sorted(cam, key=lambda k: k["t"])}]
        elif bid.startswith("post-"):
            layers = [{"kind": "Post", **next(pp for pp in posts if pp["beat"] == bid)}]
        else:
            layers = [{"kind": "Closer", "box": gscreen, "lock": lock_c, "still": stop}]
        beats.append({"id": bid, "bars": round(fr / PULSE / 4, 3), "frames": fr, "layers": layers})

    # the shots a video model would make, each written from the plan's own shot for it: the hook's world on the post
    # the frame rests on, a still brought to life on each post the frame holds, and a texture on each post it passes;
    # each names the camera move its beat makes and its length, and loops seamlessly (clips.py normalize loops a clip
    # short of its beat)
    moving = {"close": "a slow push in", "slide": "a slow truck {}", "drop": "a slow tilt down"}
    loop = lambda sec: f"{sec} s, a seamless loop: the last frame matches the first"
    clips = []
    if slots:
        sec = round(frames[0] / FPS, 1)
        world = (film.get("world") or "").strip().rstrip(".") or "the street and the light of the post the frame rests on"
        clips.append({"id": "00", "beat": "hook", "role": "world", "seconds": sec,
                      "image": next(b["file"] for b in before if b["pos"] - 1 == rest_slot),
                      "prompt": f"{world}; a slow dolly forward; {loop(sec)}",
                      "stand_in": "the wall of their posts under the frame's hops, the low camera passing over it and the frame and its band standing off the wall"})
    for i, pp in enumerate(posts):
        sec = round(frames[i + 1] / FPS, 1)
        mv = pp["move"]
        shot = (nine[i].get("shot") or "").strip().rstrip(".") or "the scene this photograph shows, at the photograph's own lens and light"
        clips.append({"id": f"{i + 1:02d}", "beat": pp["beat"], "role": "still" if mv == "close" else "texture", "seconds": sec,
                      "image": pp["file"], "prompt": f"{shot}; {moving[mv].format('left' if pp['side'] > 0 else 'right')}; {loop(sec)}",
                      "stand_in": {"close": "the layered move: the subject's crop held forward of its own photograph, which recedes and dims behind it, the crop drifting toward the focal point while the camera pushes in",
                                   "slide": "the crop sliding in forward of the wall, light wrapping its edges, the camera trucking across the two layers",
                                   "drop": "the card falling from the lens into its cell, its shadow on the wall sharpening as it lands"}[mv]})

    # the timeline the card's moves read, in beats of the music: the hook's title, the wall the camera travels along
    # (the hook's wall and every post that only passes into its cell, one beat until the frame holds again), each post
    # the frame holds, and the closer. The film is one take, the camera never jumps, so no beat change is a cut and no
    # card transition covers one; each move is the card's for what its beat shows
    to_beats = lambda u: round(u / per_beat, 3)
    tl, used, prev_move = [], {}, None

    def beat_on(bid, form, at, end_, words="", label="", tags=(), peak_=False):
        nonlocal prev_move
        if form == "wall" and tl and tl[-1]["form"] == "wall":
            tl[-1]["end"] = to_beats(end_)
            return
        tags = set(tags) | {"words" if words or label else "wordless"}
        options = [o for o in card["moves"] if not (form == "photo" and o["id"] in NOT_HELD)] or card["moves"]
        mv = compose.pick(options, tags, form, used, prev_move)
        prev_move = mv
        tl.append({"id": bid, "form": form, "at": to_beats(at), "end": to_beats(end_), "move": mv, "transition": None,
                   "words": words, "label": label, "peak": peak_})
    if slots and title_end > 0:
        # the title's page sets the hook line, so no move draws over it
        tl.append({"id": "hook-title", "form": "words", "at": 0.0, "end": to_beats(title_end), "move": None, "transition": None,
                   "words": hook_words, "label": "", "peak": False})
        beat_on("hook", "wall", title_end, starts[1] if len(starts) > 1 else C, label=at_handle)
    elif slots:
        beat_on("hook", "wall", 0.0, starts[1] if len(starts) > 1 else C, label=at_handle)
    for i, (p, pp) in enumerate(zip(nine, posts)):
        a0, a1 = starts[i + 1], starts[i + 1] + lengths[i + 1]
        if not pp["full"]:
            beat_on(pp["beat"], "wall", a0, a1)
            continue
        # the post's caption stands on its band, so the move is handed no words and moves the picture alone: it is
        # chosen for what the picture shows
        tags = {"landscape" if wide_of(p) else "portrait"} | ({"peak"} if pp.get("peak") else set()) \
            | ({"people"} if re.search(r"@[A-Za-z0-9._]{2,}", p.get("moment") or p.get("caption") or "") else set())
        beat_on(pp["beat"], "photo", a0, a1, tags=tags, peak_=bool(pp.get("peak")))
    # the closer's words are the header's and the card's closing card's, and the header is laid for a camera that has
    # stopped, so its beat has no move: nothing draws over the profile and nothing turns the camera
    tl.append({"id": "closer", "form": "closer", "at": to_beats(C), "end": to_beats(end), "move": None, "transition": None,
               "words": "", "label": "", "peak": False})
    timeline = {"beats": tl, "cuts": [b["at"] for b in tl]}
    faces = card["faces"]
    look = {"W": W, "H": H, "fps": FPS, "pulse": round(FPS * 60 / tempo, 4), "colors": colors,
            "display": faces["display"]["family"], "text": faces["text"]["family"], "italic": bool(faces["display"].get("italic")),
            "title": hook_words, "handle": at_handle, "signoff": ask or at_handle}
    closer_shape = {"name": card["closer"], "at": to_beats(closer_at), "still": to_beats(stop)}

    system = compose.system(card, colors, {fmt: G["safe"]})
    return {"id": f"{card['id']}-{fmt}", "style": card["id"], "name": f"the next {m}", "handle": handle,
            "year": dates[0].year if dates else dt.date.today().year, "bpm": BPM, "tempo": tempo,
            "format": {"width": W, "height": H, "fps": FPS, "name": fmt}, "system": system,
            "beats": beats, "timeline": timeline, "look": look, "header": header, "closerShape": closer_shape, "page": title_page,
            "sound": sorted(sound, key=lambda c: c["at"]), "clips": clips, "story": story,
            "seconds": round(end * 60 / BPM, 3), "stop_seconds": round(stop * 60 / BPM, 3), "unfit": unfit,
            "hook": {"slots": slots, "rest": round(hook_rest, 3), "title": round(title_end, 3)}}


def rests(board):
    """The settled frames: the hook with its words in, the densest post (its page's words in), the closer."""
    def at(beat):
        return round(beat * PULSE)
    posts = [b for b in board["beats"] if b["id"].startswith("post-")]
    # the densest post: the one whose page carries the most lines, the one nearest the middle on a tie, held just
    # before its words leave
    lines = lambda b: len((b["layers"][0].get("page") or {"lines": []})["lines"])
    mid = min(posts, key=lambda b: (-lines(b), abs(posts.index(b) - len(posts) // 2))) if posts else None
    stop = board["beats"][-1]["layers"][0]["still"]
    out = {"hook": at(board["hook"]["rest"]), "closer": at(stop) + 3}
    if mid:
        pg = mid["layers"][0].get("page")
        out["dense"] = at(pg["sink"] - 0.1 if pg else mid["layers"][0]["times"]["drop"][0] - 0.1)
    return out


def planned_cuts(board):
    """The film's shot changes in seconds: every camera move between two framings starts one."""
    keys = board["beats"][0]["layers"][2]["keys"]
    out = []
    for a, b in zip(keys, keys[1:]):
        if a["c"] != b["c"] or abs(a["h"] - b["h"]) > 0.08 * a["h"]:
            out.append(round(a["t"] * 60 / BPM, 2))
    return sorted(set(out))
