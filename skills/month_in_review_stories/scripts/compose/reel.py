"""The reel: their month as a walk through its diary, each moment shown once, told as one idea: my <month>, in <n>
stories. That line stands whole on the ground above the first photograph on the first frame, the reel's thumbnail, and the closer
says it again under the wall where every moment stands out lit. The month's peak opens the reel (the first moment by
date when there is no peak), on screen from the first frame; then each other moment follows in date order: it flies
onto the wall, its photograph a print on a band of the card floating over its field (the same photograph past the
band, soft and dim), the line acts on it (`act_of`: it falls from the top of the frame onto the peak, rides in along the top of a wide
photograph, else climbs from the foot of its post's cell to the cell's top, never the same act twice in a row), their own
words land on the field beside the band, and as
the camera leaves the words go, the camera winds up and goes, and the photograph trims into its post's cell of the
wall; the closer pulls back to the whole wall: the month's posts with a photograph, every one of
them, each in a cell with its day beneath it, the other posts rising out of the wall one after another and the moments
standing out furthest, the line run out under the wall as its foot and the month's line landing under it; then the
style's closing page comes over the wall with the ask, and picture and music stop together as it lands, held still and
silent after it.

Each hold moves the way its shot moves (`hold_of`: a push in, a pull back, a crane rising; with no shot written, a
tall photograph rises, a wide one pulls back, any other pushes in), never the way the beat before it held, each turning about the print; the camera never pushes further in than ZOOM, and every word on a card
stands INSET inside the safe area's sides, so a hold never carries a word out of it. Every line of type lands word by
word from its beat `at` (ENTER: a word every `step` beats, each settled in `beats`) and leaves in reverse from `out`,
gone before the camera's move (`move`, LEAVE beats before the next card's beat to SETTLE after it) starts. Every
photograph lands in its color. A moment with no photograph is big type on the band instead, its count when the ask is
for their numbers, else its words, and it has no cell: it leaves as the camera does. A month with no photograph has no
wall: its closer is the line running out across the ground and the words.

No word stands on a photograph: a moment's words sit on the field beside its band, which darkens softly behind them
(`strip`, the rect they take, card px): under it on the first card, whose month line stands over it, and on another card
on the side away from the photograph's subject, so the subject sits nearer the middle of the frame, and never under three cards in a row (`side_of`). Each
beat's move and the cut into it come from what it shows, within the style card's allowlists (`style.pick`); a cut that
jumps (`JUMPS`) takes the camera to the next card on the beat, any other carries it there. The type is the card's two
faces, each in its own case and tracking, set as the card sets a photograph's caption: the month's line in the display
face at HOOK_SIZE, each moment's day in the text face at LABEL, and their words under it in the face and at the size of
the card's photo line (at most SAID_MOST) when they fit one row there, else a fifth smaller and smaller again until they
fit two rows (`said_size`). When the ask carries their numbers, each moment's count stands under its day and
counts up from zero over its hold (`tally`). Each moment holds as long as what its photograph carries: its words and how
busy the photograph is against the moments' median (`carried`), every hold scaled together to fill the reel's length
(`holds`): the length asked, met to the frame, else LENGTH.

`reel(month)` returns the plan the Reel composition (motion/studio/climb) draws, every place in px of the closer's
frame (the wall, 1080x1920, y down) and every time in musical beats from the film's start, with the sound cues the
master mixes under the music (one where each beat lands, the build into the peak and the stop) and the clips an
image-to-video model would make: one a moment, each the shot the agent wrote for its photograph (taste.json
`moments[].shot`: subject, move, lens, height, light), the first the hook's world and the others a still brought to
life, and one at every seam between two moments, texture between chapters drawn from the outgoing photograph's light;
each runs as long as its window of the film, in the 1080x1920 frame, and loops. Nothing here is drawn by hand: the wall's grid fits the count of the month's
photographs, each photograph sits on its band and in its cell by its own subject, and each beat is as long as its words
take to read, scaled together to the length."""
import math
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from . import photos, style
from .common import FPS, H, SAFE, W
from .month import LENGTH, Month, fit, number, wrap

KIT = Path(__file__).resolve().parents[2]
L0, R0 = SAFE["left"], W - SAFE["right"]
# the moves that lay paper over part of the frame at rest (a gutter and margins, a ground from the middle down, a window
# smaller than the frame), which would cut through the closer's wall and its month line
COVERS = {"diptych", "rule-draw", "crop-shift", "scale-to-cell"}
# the closer's wall of the month's photographs: its top and its foot, the gap between two cells, and the room under a
# cell for its day, set at DAY px clear of the rim a standing moment shows (climb/wall.tsx RIM, under half the gap)
TOP = SAFE["top"]
# the wall's photographs run up into the top margin, where nothing has to read; the days under its rows stay inside
# the safe area; the foot leaves the month line under the wall, descenders and all, above four fifths of the frame, where
# a wall move's paper foot begins
WALL_TOP = 120
FLOOR = 1330
GAP = 28
RIM = 10
DAY = 32
UNDER = RIM + 12 + DAY + 8
# the band of a card (card px) its photograph fills and the line climbs, with the ground above it for the month's line on
# the first card and room on the ground below it for the moment's words
LO, HI = 400, 1320
# the first card's band, nearer the middle: its month line over it and its words under it stand inside the window every
# style's title move leaves the picture (the margin of white-space-crop, the print of polaroid-drop)
TITLE_LO, TITLE_HI = 620, 1160
# a card whose words stand over its band has the band SHIFT px lower and its words from ABOVE, a row apart
SHIFT, ABOVE = 160, 320
# how far in from the safe area's sides a card's words stand, px: the most a hold's camera carries them
INSET = 24
TX = L0 + INSET
# the furthest a hold's camera pushes in on its card, and the ways a hold moves
ZOOM = 1.045
HOLDS = ("push", "pull", "crane")
# what a shot's move says, read for the hold that plays it on the still photograph
MOVES = {"push": ("push", "dolly in", "closer", "toward", "in on"), "pull": ("pull", "back", "away", "out from", "reveal"),
         "crane": ("crane", "rise", "rising", "tilt", "boom", "lift", "up ", "drift up", "pan")}
# the camera's move from a card to the next: it starts LEAVE beats before the next card's beat (the words gone before
# it) and lands SETTLE beats after it; the words leave from EXIT beats before the move, the last line first
LEAVE, SETTLE, EXIT = 1.1, 0.35, 1.0
# the line's acts on a card: climbing from the foot of the cell to its top, falling from the top of the frame onto the
# top, or riding in along the top with the photograph
ACTS = ("climb", "fall", "ride")
# a line lands word by word: a word every `step` beats, each settled in `beats`, from below its baseline with its
# letters spaced out and closing
ENTER = {"step": 0.08, "beats": 0.4}
# how many beats before the film's first frame the first beat's move starts, so its first frame, the reel's thumbnail,
# shows the move landed and the month's line whole
LEAD = 1.2
# the type's scale (card px): the month's line in the display face, at most HOOK_SIZE; under a band the day in the
# text face at LABEL, a count at COUNT, each SPACE under the line above, and their words (`said_sizes`) LEADING of their
# size apart; a count row is ROW; the closer's month line at most CLOSE_SIZE
HOOK_SIZE, LABEL, COUNT, SPACE, LEADING, ROW, CLOSE_SIZE = 96, 34, 40, 22, 1.12, 50, 80
# the largest a moment's words set at, px, in one row and in two: a card's photo line size is for a photograph's own
# page, and the words under a band end above the safe area's foot as a pull back brings them toward it
SAID_MOST, TWO_MOST = 76, 52
# the first card's flight in from the film's start, in beats
OPEN = 0.5
# the last move, as shares of it: the line has drawn back into its cell's corner by the first and has dropped under the
# wall by the second, where it starts to run out along the wall's foot (climb/plan.ts LINE_OUT)
LINE_OUT = (0.8, 0.88)
# the closer's other posts rise out of the wall one after another from RISE[0] beats into the pull back, once the top of
# the wall is in the picture, RISE[1] beats apart, all of them within RISE[2] beats
RISE = (0.45, 0.06, 1.4)
# the closer, from the pull back's start: the land, LAND beats in, where the moments stand out of the wall and the
# month's line starts to land under it; the style's closing page, READ seconds later (at least READ_BEATS), coming over
# the wall with the ask; the stop, as the page's own build ends (BUILD), where picture and music stop together; and the
# end, held still and silent for HELD seconds after the stop
LAND = 1.4
READ, READ_BEATS = 1.4, 2.5
HELD = 1.5
# the beats each closing page takes to build: motion/system/moves/closer/<name>.tsx draws its build on its progress
# from its start to the stop, so it lands as picture and music stop; a page not named here takes BUILD_BEATS
BUILD = {"caption-alone": 1.4, "book-cover": 1.6, "poster": 1.0, "closing-flicker": 0.9, "title-card": 1.5}
BUILD_BEATS = 1.8
# the moves that mark the print's top corner (a sticker, a drawn loop), where the words over a band stand
MARKS = {"sticker-pop", "doodle-draw-on"}
# the cuts that jump: the camera is on the next card at the cut. Read from the shared cuts themselves, so a cut's
# jump is said once, where the cut is drawn.
CUTS = KIT / "motion" / "system" / "moves" / "cut"
JUMPS = frozenset(f.stem for f in CUTS.glob("*.tsx") if "jump: true" in f.read_text())
# the shortest hold a moment takes when the reel is fitted to a length (its line's rise and a beat to read) and the longest
LEAST, MOST = 3.2, 18.0
# the room the field's darkening leaves around the words, px
PAD = 24


@lru_cache(maxsize=None)
def _font(file, size):
    return ImageFont.truetype(str(KIT / file), size)


def width(text, size, file, tracking=0.0):
    """The advance width of `text` at `size` px in a font file, as opentype lays it out in the composition, its letters
    spaced `tracking` em apart."""
    return _font(file, 200).getlength(text) * size / 200 + tracking * size * len(text)


def half(x):
    return round(x * 2) / 2


def face(m, kind="text"):
    """The card's face a line is set in: its display face, else its text face."""
    return m.faces["display_face" if kind == "display" else "text_face"]


def wide(m, text, size, kind="text"):
    """How wide `text` sets at `size` px in the card's `kind` face, in that face's case and tracking."""
    f = face(m, kind)
    return width(style.cased(text, f), size, f["file"], f.get("tracking", 0.0))


def line(m, text, x, y, size, face_="text", color="ink", anchor="start", name=None):
    f = face(m, face_)
    d = {"text": style.cased(text, f), "x": round(x, 1), "y": round(y, 1), "size": round(size, 1), "face": face_,
         "weight": f.get("weight", 400), "tracking": f.get("tracking", 0.0), "color": color, "anchor": anchor, "file": f["file"]}
    if name:
        d["name"] = name
    return d


def edges(ln):
    """The line's left and right, px, from its anchor."""
    w = width(ln["text"], ln["size"], ln["file"], ln["tracking"])
    x = ln["x"] - {"middle": 0.5, "end": 1.0}.get(ln.get("anchor"), 0.0) * w
    return x, x + w


def plate(lines, y0, y1, x0=None):
    """The rect a group of words takes, [x0, y0, x1, y1]: PAD around the widest of them, from x0 when it is given."""
    spans = [edges(ln) for ln in lines]
    left = min([s[0] for s in spans] or [L0]) - PAD if x0 is None else x0
    right = max([left + 2 * PAD] + [s[1] + PAD for s in spans])
    return [round(max(0, left), 1), round(y0, 1), round(min(W, right), 1), round(y1, 1)]


def column(m, shape=None):
    """Where a moment's words stand across the frame, from the card's photo line (a landscape photograph's own line box
    when `shape` is "landscape"): the anchor, its x and the room the words have, px, inside the safe area less the
    hold's inset. A centred line stands on the frame's middle; a line set from its start stands at its box's left, so
    the swiss grid sets its words in its own column, and ends two insets short of the safe area, where the hold's
    push and the ink a letter runs past its advance both stay inside it."""
    ln = m.card["photo"]["line"]
    box = m.card["photo"]["landscape"]["line"] if shape == "landscape" else ln["box"]
    x0, bw = box[0] * W, box[2] * W
    if ln.get("align") == "center":
        return "middle", W / 2, min(bw, R0 - L0 - 2 * INSET)
    left = max(TX, x0)
    return "start", left, min(R0 - 2 * INSET, x0 + bw) - left


def said_at(m, post, shape=None):
    """Where one moment's words stand (`column`), and their size and rows there: a column too narrow for its whole
    words in two rows, or for its count, gives them the page's width from the left margin, so a narrow column never
    cuts what they said or the count they had."""
    anchor, x, room = column(m, shape)
    size = said_size(m, post, room)
    rows = words_of(m, post, size, room)
    full = R0 - L0 - 2 * INSET
    cut = " ".join(rows) != " ".join(post.said.lower().split())
    cut = cut or bool(m.counted and post.counted and wide(m, post.count(), COUNT) > room)
    if anchor == "start" and room < full and cut:
        room, x = full, TX
        size = said_size(m, post, room)
        rows = words_of(m, post, size, room)
    return anchor, x, room, size, rows


def timed(ln, at, out=None, step=None):
    """The line landing word by word from beat `at` (a word every `step` beats, else ENTER's) and leaving from `out`."""
    ln["at"] = round(at, 3)
    if out is not None:
        ln["out"] = round(out, 3)
    if step is not None:
        ln["step"] = round(step, 3)
    return ln


# what the film does with a photograph when its clip did not arrive: the hold's move on the print floating over its
# field, the two sliding apart as the camera turns, and at a seam the field drifting under the camera's move
STAND_IN = {
    "push": "the camera pushes in on the print and swings from its right to its left, the soft field sliding the other way "
            "behind it, while the photograph eases back about its subject",
    "pull": "the camera pulls back from the print and swings from its left to its right, rising, the soft field sliding "
            "the other way behind it, while the photograph eases in about its subject",
    "crane": "the camera rises up the print and tips from looking up to looking down, the soft field sliding the other way "
             "behind it, while the photograph eases back about its subject",
    "texture": "the outgoing photograph's soft field drifts under the camera's move as its print sets into its cell",
}
MOVED = {"push": "the camera pushing in", "pull": "the camera pulling back", "crane": "the camera rising"}
FRAME = "a vertical 9:16 frame, 1080x1920"
LOOP = "a seamless loop: the move goes out and comes back, so its last frame is its first"


SHOT = ("subject", "move", "lens", "height", "light")


def shot_of(p):
    """The shot the agent wrote for the post's photograph (taste.json `moments[].shot`), each field as written."""
    shot = getattr(p, "shot", None) or {}
    return {f: str(shot.get(f) or "").strip() for f in SHOT}


def shape_of(pic):
    """A photograph's shape: "portrait" when it stands taller than wide, else "landscape"; None with no photograph."""
    if not pic:
        return None
    w, h = pic["size"]
    return "portrait" if h > w else "landscape"


def hold_of(shot, before, shape):
    """The hold that plays a shot's move on the still photograph: the move its words name first (a move written out and
    back names its way out first), else the photograph's own: a tall one rises up it, a wide one pulls back to take in
    its width, a card of type pushes in; never the hold of the beat `before` it (then the next of HOLDS after it)."""
    said = f" {shot.get('move', '').lower()} "
    at = {h: min((said.find(w) for w in MOVES[h] if w in said), default=len(said)) for h in HOLDS}
    named = min(HOLDS, key=at.get) if min(at.values()) < len(said) else {"portrait": "crane", "landscape": "pull"}.get(shape, "push")
    return named if named != before else HOLDS[(HOLDS.index(named) + 1) % len(HOLDS)]


def act_of(peak, shape, before):
    """The line's act on a card: it falls onto the month's peak, rides in along a wide photograph's top, else climbs;
    never the act of the card `before` it (then the next of ACTS after it)."""
    act = "fall" if peak else "ride" if shape == "landscape" else "climb"
    return act if act != before else ACTS[(ACTS.index(act) + 1) % len(ACTS)]


def side_of(k, focus_y, band, sides):
    """Where a card's words stand: under its band on the first card, whose month line stands over it; over the band
    when the photograph's subject sits in its upper half, so the band moved down brings the subject nearer the middle of
    the frame, or when the two cards `sides` before it both stood their words under, so the words never sit in one
    place reel-long; else under it."""
    if not k:
        return "under"
    upper = focus_y is not None and focus_y < (band[0] + band[1]) / 2
    return "over" if upper or sides[-2:] == ["under", "under"] else "under"


def tags_of(k, post, pic, peak):
    """What a beat shows, in the words a card's `fits` uses: its form (the first card is the film's title), photo or
    words, words or wordless, portrait or landscape, the peak, a place named."""
    form = "title" if k == 0 else "photo" if pic else "words"
    tags = {form, "photo" if pic else "words", "words" if post.said else "wordless"}
    tags |= {shape_of(pic)} - {None}
    tags |= {"peak"} if peak else set()
    tags |= {"place"} if post.place else set()
    return form, tags


def request(cid, key, use, said, window, pic, stand_in, bpm):
    """One clip request: its shot written out as one prompt, the 9:16 frame, as long as its window of the film and looping."""
    seconds = round((frame(window[1], bpm) - frame(window[0], bpm)) / FPS, 1)
    prompt = ". ".join(x.rstrip(".") for x in [*said.values(), f"{seconds:g} s", FRAME, LOOP] if x) + "."
    return {"id": cid, "beat": key, "use": use, **said, "seconds": seconds, "frame": FRAME, "loop": LOOP, "at": [round(window[0], 3), round(window[1], 3)],
            "image": pic["file"] if pic else None, "prompt": prompt, "stand_in": stand_in}


def seam(said):
    """Texture between two chapters, from the outgoing shot: its light, close and soft, drifting across and back."""
    light = said.get("light") or "the photograph's own light"
    subject = said.get("subject") or "the photograph"
    return {"subject": f"the light and color of {subject.rstrip('.')}, so close it is only texture, catching and moving",
            "move": "a slow drift across the texture and back", "lens": "macro, shallow focus, everything soft",
            "height": said.get("height") or "", "light": light}


def legible(m, role="high", least=4.5):
    """The color a count is set in: `role`, else the line color, else the ink, the first that reads on the ground at
    `least` contrast."""
    from .look import contrast
    return next((r for r in (role, "line") if contrast(m.colors[r], m.colors["bg"]) >= least), "ink")


def tally(at, beats):
    """A count's figures counting up from zero, from beat `at` over `beats`."""
    return {"at": round(at, 3), "beats": round(max(1.0, beats), 3)}


def cover(size, focus, rect=(0, 0, W, H)):
    """The photograph laid over `rect` [x0, y0, x1, y1] to cover it (place [x, y, w, h] in px) with its subject as near
    the rect's middle as the edges allow, and the subject's point in px."""
    x0, y0, x1, y1 = rect
    pw, ph = size
    c = max((x1 - x0) / pw, (y1 - y0) / ph)
    dw, dh = pw * c, ph * c
    x = min(x0, max(x1 - dw, (x0 + x1) / 2 - focus[0] * dw))
    y = min(y0, max(y1 - dh, (y0 + y1) / 2 - focus[1] * dh))
    return [round(x, 1), round(y, 1), round(dw, 1), round(dh, 1)], (x + focus[0] * dw, y + focus[1] * dh)


def picture(post, file):
    """The post's photograph as `file` in the run's public folder: where it came from, its size and its subject; None
    when the post has none."""
    src = getattr(post, "photo", None)
    if not src or not Path(src).exists():
        return None
    im = photos.open_image(src)
    return {"file": file, "source": str(Path(src).resolve()), "size": list(im.size), "focus": photos.focus_of(im)}


def crop(pic, cell):
    """The part of the photograph [x, y, w, h], fractions of it from its top left, that covers `cell` with its subject
    as near the middle as the edges allow."""
    (pw, ph), (fx, fy) = pic["size"], pic["focus"]
    cw, ch = cell[2] - cell[0], cell[3] - cell[1]
    c = max(cw / pw, ch / ph)
    w, h = cw / (pw * c), ch / (ph * c)
    return [round(min(1 - w, max(0.0, fx - w / 2)), 4), round(min(1 - h, max(0.0, fy - h / 2)), 4), round(w, 4), round(h, 4)]


def frame(beat, bpm):
    """A time in beats of `bpm` from the film's start as the film frame the composition draws it on."""
    return round(beat * FPS * 60 / bpm)


def label(m, post, size, limit):
    """The day and place a moment is set under, fitted to `limit` at `size` px."""
    small = f"{m.short} {post.day}" + (f" · {post.place}" if post.place else "")
    return fit(small, lambda t: wide(m, t, size), limit)


def said_sizes(m):
    """The sizes a moment's words set at: the card's photo line size, at most SAID_MOST, when the whole line fits one
    row, else a fifth smaller."""
    size = min(SAID_MOST, m.card["photo"]["line"]["size"])
    return size, min(TWO_MOST, round(0.82 * size))


def said_size(m, post, limit):
    """The size a moment's words set at under its band (`said_sizes`): one row at the first size, else two rows at the
    second, and a line too long for two rows there set smaller until it fits them, down to half the card's photo line
    size."""
    one, two = said_sizes(m)
    text = post.said.lower()
    if wide(m, text, one, said_face(m)) <= limit:
        return one
    size, least = two, min(two, round(0.5 * m.card["photo"]["line"]["size"]))
    while size > least and len(wrap(text, lambda t: wide(m, t, size, said_face(m)), limit)) > 2:
        size -= 2
    return size


def said_face(m):
    """The face a moment's words are set in: the card's photo line face."""
    return m.card["photo"]["line"]["face"]


def words_of(m, post, size, limit, rows=2):
    """The post's line as it sets under the photograph: at most `rows` lines; when it runs on, its whole sentences
    that fit, and only a first sentence too long for them is cut at a word."""
    text = post.said.lower()
    if not text:
        return []
    w = lambda t: wide(m, t, size, said_face(m))
    lines = wrap(text, w, limit)
    if len(lines) <= rows:
        return lines
    ends = [j + 1 for j, x in enumerate(text.split()) if x.endswith((".", "!", "?", ";"))]
    for k in reversed(ends):
        whole = wrap(" ".join(text.split()[:k]), w, limit)
        if len(whole) <= rows:
            return whole
    return lines[:rows - 1] + [fit(" ".join(lines[rows - 1:]), w, limit)]


def big(m, post, y0, y1, limit=R0 - L0, x0=L0):
    """A moment with no photograph as big type centred in the band [y0, y1] (card px): its count when the ask is for their
    numbers, the figure large in the line's color over the words it counts, else its own words in the display face."""
    if m.counted and post.counted:
        hero, *rest = post.count().split("  ·  ", 1)
        n, word = hero.split(" ", 1)
        under = "  ·  ".join([word, *rest])
        rows = [(n, min(320, int(limit / wide(m, n, 1, "display"))), "line"), (under, min(84, int(limit / wide(m, under, 1, "display"))), "ink")]
    else:
        text = (post.said or post.name).lower()
        for size in range(180, 59, -10):
            got = wrap(text, lambda t: wide(m, t, size, "display"), limit)
            if len(got) <= 5 and len(got) * size <= 0.8 * (y1 - y0):
                break
        if len(got) > 5:
            got = got[:4] + [fit(" ".join(got[4:]), lambda t: wide(m, t, size, "display"), limit)]
        rows = [(x, size, "ink") for x in got]
    gap = lambda s: 0.18 * s
    tall = sum(0.96 * s for _, s, _ in rows) + sum(gap(s) for _, s, _ in rows[1:])
    y, out = (y0 + y1) / 2 - tall / 2, []
    for j, (text, size, color) in enumerate(rows):
        y += (gap(size) if j else 0) + 0.74 * size
        out.append(line(m, text, x0, y, size, face_="display", color=color, name="big"))
        y += 0.22 * size
    return out


def busy_ratio(m, post):
    """How busy the post's photograph is against the moments' median, 0.5 to 2; 1 for a moment with no photograph."""
    have = [m.measures[p]["busy"] for p in m.moments if p in m.measures]
    if post not in m.measures or not have:
        return 1.0
    mid = sorted(have)[len(have) // 2] or 1e-6
    return min(2.0, max(0.5, m.measures[post]["busy"] / mid))


def carried(m, caps):
    """Each moment's natural hold in beats, in the order of the walk: as long as its words take to read, longer on a
    busier photograph and shorter on a calmer one, the peak the longest."""
    walk = m.walk
    base = [min(9.0, max(5.0, 2.5 + 0.55 * sum(len(x.split()) for x in cap))) * math.sqrt(busy_ratio(m, p))
            for p, cap in zip(walk, caps)]
    if m.peak is not None:
        top = max(b for p, b in zip(walk, base) if p is not m.peak) if len(base) > 1 else base[0]
        base = [max(b, top + 1.5) if p is m.peak else b for p, b in zip(walk, base)]
    return base


def length_of(m):
    """The reel's end in beats: the length asked, else LENGTH."""
    return (m.seconds or LENGTH) * m.bpm / 60


def closing(bpm, closer=None):
    """The closer's times in beats of `bpm` from the pull back's start: the land, the closing page, the stop as the
    page `closer` finishes its build, the end."""
    b = bpm / 60
    page = LAND + max(READ * b, READ_BEATS)
    stop = page + BUILD.get(closer, BUILD_BEATS)
    return LAND, page, stop, stop + HELD * b


def holds(spans, end, closer):
    """Each moment's hold in beats, filling what the first card's flight in and the closer leave of `end` exactly: one
    factor scales every natural hold, each kept between LEAST and MOST, and the last takes the rounding."""
    room = end - OPEN - closer
    if abs(room - sum(spans)) < 1e-9:
        return list(spans)
    fill = lambda k: sum(min(MOST, max(LEAST, x * k)) for x in spans)
    lo, hi = 0.0, 64.0
    for _ in range(80):
        k = (lo + hi) / 2
        lo, hi = (k, hi) if fill(k) < room else (lo, k)
    k = (lo + hi) / 2
    out = [round(min(MOST, max(LEAST, x * k)), 3) for x in spans]
    out[-1] = round(room - sum(out[:-1]), 3)
    return out


def wall(n, wide=()):
    """The closer's n cells [x0, y0, x1, y1], row by row from WALL_TOP to FLOOR with UNDER px for a day under each row, on one
    grid of columns every row shares: the square root of n columns, rounded up, and as many rows as that takes. The grid's
    spare slots go to the cells named in `wide` (indices, in order), each taking the slot after it in its row so it spans
    two columns, and any spare left over widens the last cell, so every cell holds a photograph and none is left empty;
    a month with no photograph has no wall."""
    if not n:
        return []
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    spare = rows * cols - n
    ch = (FLOOR - WALL_TOP - rows * UNDER - (rows - 1) * GAP) / rows
    cw = (R0 - L0 - (cols - 1) * GAP) / cols
    span = [1] * n
    for i in wide:
        # a cell widens only when the slot after it is in its row
        at = sum(span[:i])
        if spare and at % cols < cols - 1:
            span[i] += 1
            spare -= 1
    span[-1] += spare
    out, slot = [], 0
    for k in span:
        r, c = divmod(slot, cols)
        y0 = WALL_TOP + r * (ch + UNDER + GAP)
        x0 = L0 + c * (cw + GAP)
        out.append([round(x0, 1), round(y0, 1), round(x0 + k * cw + (k - 1) * GAP, 1), round(y0 + ch, 1)])
        slot += k
    return out


def landing(c):
    return {"climb": "lands in color and the line climbs across it to above its subject",
            "fall": "lands in color and the line falls onto it from above, landing above its subject",
            "ride": "lands in color with the line riding in along its top, above its subject"}[c["act"]]


def storyboard(m, cards, tiles, C, end):
    """The reel's beats as the storyboard reads them: each one's span, what its move reveals, and what it carries
    across the cut into the next. The first runs from the film's first frame, as its card flies in."""
    walk = m.walk
    said = lambda c, p: " ".join(x["text"] for x in c["lines"][1:] if x.get("name") is None) or p.name
    out = []
    for k, (c, p) in enumerate(zip(cards, walk)):
        last = k == len(cards) - 1
        opens = ("the month's peak opens the reel: " if p is m.peak else "the reel opens on the month's first moment: ") if k == 0 else ""
        shows = (f"the photograph {landing(c)}, {MOVED[c['hold']]}, their words landing on the field under it" if c["stays"]
                 else f"their words big on the band, {MOVED[c['hold']]}")
        if k == 0:
            shows = f"my {m.name}, in {number(len(cards))} stories lands word by word over it in the first second; " + shows
        under = "under the wall" if tiles else "across the ground"
        out.append({"key": c["key"], "from": 0.0 if k == 0 else c["arrive"], "to": c["leave"],
                    "reveals": f"{m.short} {p.day}, {said(c, p)}: {opens}{shows}",
                    "carries": (f"the line, which runs out {under} as "
                                f"{'the photograph sets into its cell' if c['stays'] else 'the type leaves'} and the camera pulls back"
                                if last else f"the line, onto {m.short} {walk[k + 1].day}, as "
                                f"{'this photograph sets into its cell on the wall' if c['stays'] else 'the type leaves'}")})
    n = number(len(cards))
    wall_ = (f"the wall of the month's {number(tiles)} photographs, each its post's with its day beneath it: the other posts rise "
             f"out of the wall one after another, all {n} moments stand out furthest, lit in the line's color, "
             f"the line under the wall, and " if tiles else "the ground, the line running out across it, and ")
    out.append({"key": "closer", "from": C, "to": end,
                "reveals": f"{wall_}my {m.name}, in {n} stories, said again under it; then the closing page comes over the wall: "
                           f"see you in {m.next.name}.",
                "carries": "nothing: picture and music stop together as the closing page lands, and hold still and silent"})
    return out


def reel(month):
    m = month if isinstance(month, Month) else Month(month)
    c = m.card
    # the closer's wall: every one of the month's posts that has a photograph, in date order, one cell each
    shown = m.shown
    # the moments in the order the reel shows them: the peak first, then the others in date order
    walk = m.walk
    # each moment's photograph under the name the story cards give it, its place in date order
    pics = [picture(p, f"photos/moment-{m.moments.index(p) + 1}.jpg") for p in walk]
    # the wall's spare slots go to the moments, the peak first
    cells = wall(len(shown), [shown.index(p) for p, pic in zip(walk, pics) if pic])
    cards, at, sound, clips, track, steps, cuts = [], OPEN, [], [], [], [], []
    # each beat as long as what its photograph carries, every hold scaled together to the reel's length
    room = R0 - L0 - 2 * INSET
    placed = [said_at(m, p, shape_of(pic)) for p, pic in zip(walk, pics)]
    sizes = [x[3] for x in placed]
    caps = [x[4] for x in placed]
    n = number(len(walk))
    month_line = f"my {m.name}, in {n} stories"
    end = length_of(m)
    land, page, stop, last = closing(m.bpm, c["closer"])
    spans = holds(carried(m, caps), end, last)
    # one frame, in beats: a cut that jumps takes the camera to the next card inside it
    tick = m.bpm / (60 * FPS)
    # the band's foot: a count row under the day raises it one row, so the words end where they do without it
    hi = HI - ROW if m.counted else HI
    hi0 = TITLE_HI - ROW if m.counted else TITLE_HI
    before, acted, moved, used_moves, used_cuts = None, None, None, {}, {}
    for k, p in enumerate(walk):
        pic = pics[k]
        shape = shape_of(pic)
        peak = p is m.peak
        length = spans[k]
        key = f"moment-{k + 1}"
        # the beat's move and the cut into it, from what it shows, within the card's allowlists; the cut into the next
        # card is chosen with the next card's beat
        form, tags = tags_of(k, p, pic, peak)
        # the card's band: its words under it, or over it with the band moved down (side_of)
        lo, hi_ = (TITLE_LO, hi0) if k == 0 else (LO, hi)
        focus_y = cover(pic["size"], pic["focus"], (0, lo, W, hi_))[1][1] if pic else None
        side = side_of(k, focus_y, (lo, hi_), [x["side"] for x in cards])
        # a move that marks the print's top corner never plays on a card whose words stand just over it
        moves = [o for o in c["moves"] if side == "under" or o["id"] not in MARKS] or c["moves"]
        move_name = style.pick(moves, tags, form, used_moves, moved)
        moved = move_name
        cut_name = None if k == 0 else style.pick(c["transitions"], tags, form, used_cuts, None)
        lo_k, hi_k = (lo, hi_) if side == "under" else (lo + SHIFT, hi_ + SHIFT)
        # a photograph sets into its post's cell; a moment with none is held over the wall on the band
        x0, y0, x1, y1 = cells[shown.index(p)] if pic else [0, lo_k, W, hi_k]
        s = max((x1 - x0) / W, (y1 - y0) / (hi_k - lo_k))
        place, (fx, fy) = cover(pic["size"], pic["focus"], (0, lo_k, W, hi_k)) if pic else ([0, 0, W, H], (W / 2, H / 2))
        hc = (y1 - y0) / s
        cy = min(hi_k - hc / 2, max(lo_k + hc / 2, fy))
        T = {"s": round(s, 5), "o": [round((x0 + x1) / 2 - s * W / 2, 2), round((y0 + y1) / 2 - s * cy, 2)]}
        # with no photograph the band is big type; its count or its words are said there, never again beside it
        typeset = big(m, p, lo_k + 40, hi_k - 40, room, TX) if not pic else []
        counts = [p.count()] if m.counted and p.counted and pic else []
        cap = [] if typeset and not (m.counted and p.counted) else caps[k]
        rise = 2.0 if peak else 1.5
        r0 = at + 0.5
        said = shot_of(p)
        hold = hold_of(said, before, shape)
        before = hold
        act = act_of(peak, shape, acted)
        acted = act
        # the camera's move to the next card: carried there over the move, or, when the cut into the next card jumps,
        # there on the beat; the last card's move is the pull back to the closer, always carried
        move = [round(at + length - LEAVE, 3), round(at + length + (SETTLE if k + 1 < len(walk) else land), 3)]
        steps.append({"k": k, "p": p, "pic": pic, "form": form, "move": move_name, "transition": cut_name, "peak": peak})
        out = move[0] - EXIT
        # the words on the field beside the band, never on the photograph, each landing word by word after the one above
        # and leaving in reverse, the last line first
        top = hi_k + 80 if side == "under" else ABOVE
        anchor, sx, said_room = placed[k][:3]
        backed = [line(m, label(m, p, LABEL, said_room), sx, top, LABEL, color="ink", anchor=anchor, name="small")]
        y = top
        for x in counts:
            y += SPACE + COUNT
            backed.append(line(m, x, sx, y, COUNT, color=legible(m), anchor=anchor, name="count"))
        for j, x in enumerate(cap):
            y += round(LEADING * sizes[k]) if j else SPACE + sizes[k]
            backed.append(line(m, x, sx, y, sizes[k], face_=said_face(m), anchor=anchor))
        # the first card says what the reel is, on the field over its photograph, whole on the first frame
        # its baseline stands far enough above the print that its descenders clear the print's edge as the camera banks
        hs = min(HOOK_SIZE, int(room / max(1e-6, wide(m, month_line, 1, "display"))))
        hook = [line(m, month_line, TX, lo_k - 28 - round(0.3 * hs), hs, face_="display", color="ink", name="hook")] if k == 0 else []
        rows = hook + backed + typeset
        whole = -(ENTER["step"] * len(month_line.split()) + ENTER["beats"])
        lines = [timed(x, whole if x.get("name") == "hook" else at + 0.35 + 0.1 * j, out + 0.1 * (len(rows) - 1 - j)) for j, x in enumerate(rows)]
        under = backed[-1]["y"]
        # every count counts up from zero from the beat its line lands and stands whole as the rise lands, on its impact
        for x in lines:
            if x.get("name") == "count" or (x.get("name") == "big" and x["color"] == "line" and m.counted and p.counted):
                x["tally"] = tally(x["at"], round(r0, 2) + rise - x["at"])
        strip_y = (hi_k + 16, under + 30) if side == "under" else (top - 0.74 * LABEL - PAD, under + 30)
        cards.append({
            "key": key, "day": p.day, "type": p.type, "peak": peak, "cell": [x0, y0, x1, y1], "stays": bool(pic), "line": [y1, y0],
            "file": pic["file"] if pic else None, "source": pic["source"] if pic else None, "size": pic["size"] if pic else None, "place": place,
            "band": [lo_k, hi_k], "side": side, "T": T, "arrive": at, "leave": at + length, "rise": [round(r0, 2), rise], "lines": lines,
            "hold": hold, "act": act, "move": move,
            # the photograph's subject, card px: a hold's photograph eases about it
            "focus": [round(fx, 1), round(fy, 1)],
            # where the words stand, card px: the field darkens softly behind them
            "strip": plate(backed, *strip_y),
        })
        # the line's act: climbing from the cell's foot to its top, falling from the top of the frame (at the safe
        # margin, so the landing's tilt never takes it out of the picture) onto the top, or riding in along the top; it
        # travels with the camera through the move that brings it to the card (climb/plan.ts lineYAt) and reaches where
        # its act starts as the camera lands
        start = {"climb": y1, "fall": T["o"][1] + T["s"] * TOP, "ride": y0}[act]
        track.append([0.0 if k == 0 else cards[k - 1]["move"][1], start, "smooth"])
        track += [[round(r0, 3), start, "smooth"], [round(r0 + rise, 3), y0, "settle"], [move[0], y0, "smooth"]]
        # the moment's sound: one where its line lands above its subject, and for the peak the build into it and its impact
        if peak:
            sound.append({"kind": "riser", "at": r0, "beats": rise, "beat": key, "what": f"the build into {p.name}, the month's peak"})
            sound.append({"kind": "impact", "at": round(r0 + rise, 3), "beat": key, "what": f"the line lands above {p.name}, the month's peak"})
        else:
            sound.append({"kind": "hit", "at": round(r0 + rise, 3), "weight": 0.6, "bright": 0.35, "beat": key, "what": f"the line lands above {p.name}"})
        at += length
    # the cut into each card after the first: a jump takes the camera there on the card's beat, any other carries it
    # over the move; the cut plays about the middle of the move either way
    for k in range(1, len(cards)):
        prev = cards[k - 1]
        if steps[k]["transition"] in JUMPS:
            b = prev["leave"]
            prev["move"] = [round(b - tick / 2, 4), round(b + tick / 2, 4)]
            track_fix(track, k, prev["move"])
        cuts.append((prev["move"][0] + prev["move"][1]) / 2)
    # each photograph's clip runs over its hold, from the film's first frame for the first, to its move; the seam to the
    # next moment asks for texture over the move; a type card has none
    for k, (cd, st) in enumerate(zip(cards, steps)):
        if st["pic"]:
            said = shot_of(st["p"])
            clips.append(request(f"{len(clips) + 1:02d}", cd["key"], "hook" if k == 0 else "still", said,
                                 (0.0 if k == 0 else cd["arrive"], cd["move"][0]), st["pic"], STAND_IN[cd["hold"]], m.bpm))
            if k + 1 < len(cards) and cd["move"][1] - cd["move"][0] > 2 * tick:
                clips.append(request(f"{len(clips) + 1:02d}", cd["key"], "texture", seam(said), tuple(cd["move"]), st["pic"], STAND_IN["texture"], m.bpm))
    C = at
    end = round(C + last, 6)
    # the closer: the camera pulls back to the wall; the other posts rise out of it one after another, the moments
    # stand out on the land, the line runs out under the wall and the month's line lands under it; then the style's
    # closing page comes over the wall with the ask, and picture and music stop together as it lands
    land_at, page_at, stop_at = C + land, C + page, C + stop
    # the line rides the top of the last photograph while it trims into its cell and draws back into the cell's corner
    # (climb/plan.ts lineSpanAt), drops under the wall unseen, and runs out along the wall's foot from there
    if cards:
        a = cards[-1]["move"][0]
        track.append([round(a + LINE_OUT[0] * (land_at - a), 3), cards[-1]["cell"][1], "smooth"])
        track.append([round(a + LINE_OUT[1] * (land_at - a), 3), FLOOR + 8, "smooth"])
    track.append([round(land_at, 3), FLOOR + 8, "smooth"])
    # the wall's beat: its move and the cut into it, chosen as a card's are, the move from those that leave the whole
    # wall and its month line in view at rest (COVERS lay paper over part of the frame)
    open_ = [o for o in c["moves"] if o["id"] not in COVERS] or c["moves"]
    wall_move = style.pick(open_, {"wall"}, "wall", used_moves, moved)
    wall_cut = style.pick(c["transitions"], {"wall", "closer", "words"}, "wall", used_cuts, None)
    if cards:
        cuts.append((cards[-1]["move"][0] + cards[-1]["move"][1]) / 2)
    ls = min(CLOSE_SIZE, int((R0 - L0) / max(1e-6, wide(m, month_line, 1, "display"))))
    tiles, named = [], set()
    for j, (p, cell) in enumerate(zip(shown, cells)):
        moment = p in m.moments
        # a day is named once, under its first photograph
        day = "" if p.day in named else f"{m.short} {p.day}"
        named.add(p.day)
        size = min(DAY, (cell[2] - cell[0]) / max(1e-6, wide(m, day or "0", 1)))
        tile = {"day": p.day, "cell": cell, "moment": moment, "at": round(C + RISE[0] + min(RISE[1], RISE[2] / len(shown)) * j, 2),
                "label": line(m, day, cell[0], cell[3] + RIM + 12 + 0.74 * size, size, color="ink" if moment else "dim")}
        if not moment:
            pic = picture(p, f"photos/post-{j + 1}.jpg")
            tile |= {"file": pic["file"], "source": pic["source"], "crop": crop(pic, cell)}
        tiles.append(tile)
    signoff = f"see you in {m.next.name}."
    display = face(m, "display")
    closer = {
        "at": C, "top": WALL_TOP, "land": round(land_at, 3), "words": round(land_at, 3), "sign": round(page_at, 3), "still": round(stop_at, 3),
        "rule": [L0 - 6, R0 + 6],
        "lines": [timed(line(m, month_line, L0, FLOOR + 92, ls, face_="display", color="ink"), land_at)],
        "tiles": tiles,
        # the style's closing page, over the wall from `at` to the stop
        "page": {"name": c["closer"], "at": round(page_at, 3), "still": round(stop_at, 3)},
    }
    sound += [
        {"kind": "hit", "at": round(land_at, 2), "weight": 1.0, "bright": 0.35, "beat": "closer", "what": f"all {n} moments stand out of the wall, lit"},
        {"kind": "hit", "at": round(page_at, 2), "weight": 0.7, "bright": 0.5, "beat": "closer", "what": "the closing page comes over the wall"},
        {"kind": "hit", "at": round(stop_at, 2), "weight": 1.0, "bright": 0.7, "beat": "closer", "what": "the ask lands and the picture stops"},
        {"kind": "stop", "at": round(stop_at, 2), "beat": "closer", "what": "picture and sound stop together"},
    ]
    beats = storyboard(m, cards, len(tiles), C, end)
    # the film's beats as the style's moves read them: each card from its cut to the next, then the wall; their words
    # stay the kit's own, drawn on the cards, so a move draws none of them
    marks = [0.0] + cuts
    timeline = {"beats": [{"id": cd["key"], "form": st["form"], "at": round(marks[k] - (LEAD if k == 0 else 0), 3), "end": round(marks[k + 1], 3), "move": st["move"],
                           "transition": st["transition"], "words": "", "label": "", "peak": st["peak"], **held_of(cd)}
                          for k, (cd, st) in enumerate(zip(cards, steps))]
                + [{"id": "closer", "form": "wall", "at": round(marks[-1], 3), "end": round(end, 3), "move": wall_move,
                    "transition": wall_cut if cards else None, "words": "", "label": "", "peak": False}],
                "cuts": [round(x - (LEAD if k == 0 else 0), 3) for k, x in enumerate(marks)]}
    # the closing page's title is the month alone, so a page that sets it on one line (a cover) sets it large
    look_ = {"title": style.cased(f"my {m.name}", display), "handle": m.handle or "", "signoff": style.cased(signoff, display),
             "display": display["family"], "text": face(m)["family"], "italic": bool(display.get("italic"))}
    return {
        "bpm": m.bpm, "fps": FPS, "W": W, "H": H, "safe": dict(SAFE), "zoom": ZOOM, "enter": ENTER, "frames": round(end * FPS * 60 / m.bpm), "end": end,
        "colors": dict(m.colors), "floor": FLOOR, "line": track, "cards": cards, "closer": closer, "sound": sound, "clips": clips, "beats": beats,
        "cuts": [frame(b["from"], m.bpm) for b in beats[1:]], "grade": {"target": None if m.target is None else round(m.target, 4), "cast": m.cast},
        "timeline": timeline, "look": look_,
    }


def held_of(cd):
    """A card's photograph as the moves see it while the camera holds on it, frame px (the card's own px at its
    station): its `box` [x0, y0, x1, y1], the band across the frame; its words' `type` box, from their baselines and
    sizes; and `held`, the beats from its arrival to its words starting to leave, EXIT beats before the camera's move, so a
    mark on the photograph goes with the words and is gone before the camera winds up. None for a card with no
    photograph."""
    if not cd["file"]:
        return {}
    lines = [ln for ln in cd["lines"] if ln["text"].strip()]
    out = {"box": [0, cd["band"][0], W, cd["band"][1]], "held": [cd["arrive"], round(cd["move"][0] - EXIT, 3)]}
    if lines:
        xs = [x for ln in lines for x in edges(ln)]
        ys = [y for ln in lines for y in (ln["y"] - ln["size"], ln["y"] + 0.3 * ln["size"])]
        out["type"] = [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]
    return out


def track_fix(track, k, move):
    """The line's track for a card the camera jumps to: its travel point moves to the jump's end, where the camera is."""
    # the track holds four points a card, the first where the camera lands on it
    track[4 * k][0] = move[1]
