"""The year's line: the months of one person's year in calendar order, each its own photograph and its own words, laid
the way the style card lays a photo beat, and the year's chapters closing onto the wall. The card gives every face,
color, easing, finish, move, cut and closer, and where the photograph and the line stand; this file gives the
composition and its times.

The film is one camera over one wall, the closer's frame (1080x1920, y down). Where the card lays its photographs full
frame, the wall lies on the first month's photograph, softened and dimmed; where it stands them in a box or shows none,
the wall is the card's photo ground, flat. The hook sets the year on the title's underline the way the card brings its
line on, drops the line open into a window where every month's photograph flashes, each as long as the next, dives
into it, and the montage cuts into the first month. Then the months come in calendar order. Each stands as the card
says: the photograph full frame over its own soft field, in the card's box on the card's ground, or not at all; the
month's name in the card's label face and their own line from the post under it in the card's line face, inside the
card's line box, entering the card's way and holding. Each month is cut to by one of the card's cuts and carries one
of the card's moves, each picked from what the month shows (a portrait or a landscape, people, a place, the story's
peak), never by its place in the year, and never the same move twice running. Across a cut that jumps, the camera
gathers itself before it and the next month lands a touch tight and settles. Under each month its line slides into the
month's row on the wall; the last one's into the last row, and the closer is the wall, the year's chapters whole, until
the card's closer takes the frame and holds the sign-off. One grade covers every frame: the card's grade, tilted toward
the darkest and lightest colors of the person's palette.

Type is set where it reads. A month's words take the card's color, on a plate of ink or paper as dense as holding
CONTRAST over the brightest or darkest tenth of what lies under them through the film's grade needs: the photograph
where they stand on it, else the card's ground. Each group set on the wall (the year, the handle, the rows' names, the
sign-off) takes ink or paper by the light of the ground under it, and where neither holds CONTRAST there, it stands on
a plate of the other color just dense enough that it does. A month's words move up or down the area they are set in
to stay off the photograph's subject box, the least way. That area is the type area drawn in by HOLD_REACH, so the
camera's push keeps them inside the type area. The rows' names and the sign-off are never set under their smallest
sizes.

Every place here is px of its frame: the wall for the title, the rows and the closer's lines; a month's piece frame
(the reel's frame, as the camera frames the month) for its photograph and its type. `T` maps a piece onto the wall.
Every time is musical beats from the film's start.
"""
import functools
import math
from pathlib import Path

W, H = 1080, 1920
# the reel's type area (design/safe-areas.json): everything a person reads sits inside it at its rest
SAFE = {"top": 270, "bottom": 670, "left": 72, "right": 150}
AREA = [SAFE["left"], SAFE["top"], W - SAFE["right"], H - SAFE["bottom"]]  # the type area, [x0, y0, x1, y1]
HOLD_REACH = 1.12      # the most the camera closes in on a month while its words stand (its push and its move's nudge)
# the area a month's words are set in: the type area drawn in toward the frame's middle by HOLD_REACH, so the camera's
# push keeps them inside the type area
WORDS_AREA = [round(W / 2 - (W / 2 - AREA[0]) / HOLD_REACH, 1), round(H / 2 - (H / 2 - AREA[1]) / HOLD_REACH, 1),
        round(W / 2 + (AREA[2] - W / 2) / HOLD_REACH, 1), round(H / 2 + (AREA[3] - H / 2) / HOLD_REACH, 1)]

# the wall
TITLE = 170            # the year, display px
RULE_Y = 455           # the title's underline, the line the hook draws
ROW_TOP = RULE_Y + 36  # the first row's top: the rows share the wall from here to over the sign-off
PITCH = 150            # the tallest a row is: a year of few months takes taller rows that fill the wall, twelve share it
BAR = 28               # a bar's thickness (wall px) as it slides into its row, before it spreads into the band
GAP = 4                # the dark between two bands, each side
LABEL = (48, 104)       # a row's month, display px: the smallest it is ever set at, and the largest
LABEL_FILL = 0.88      # a row's month as tall as this fraction of its row, inside those sizes
HANDLE = 40
SIGNOFF = (72, 84)     # the sign-off, display px: the smallest it is ever set at, and the largest, inside the type area's width
SIGNOFF_GAP = 36       # the ground between the last row and the sign-off's caps
CONTRAST = 4.5         # the least contrast type holds over the darkest tenth (ink) or the brightest tenth (paper) of the light under it
SET_TO = 4.6           # the contrast a plate is set to, a little over CONTRAST, since the read takes the light as a gray
PAD = 14               # how far a plate on the wall reaches past the type it lies under, wall px
PLATE_PAD = 28         # how far a month's plate reaches past its words on three sides, px of the piece frame
DIM = 0.16             # the wall's ground: the first month's photograph softened and mixed toward the card's background,
                       # keeping this share of its own light, so the wall's type holds CONTRAST over it on most photographs
BAND_LIGHT = 0.3       # the most light a row's band carries on the wall: a brighter slit is dimmed to it, never under
BAND_LEAST = 0.55      # this share of its own light, so a snowfield or a white wall sits in the year's rows like the rest
RULE_GAP = 40          # a month with no photograph: its accent line runs this far under its words, px
SCRIM_SOFT = 150       # how far the card's scrim fades in over a month's words on a full frame, px

# a month's piece frame
S = 0.3                # piece px to wall px while the camera is on the month
LIFT = 90 * S          # how far the first month's photograph stands off the wall, wall px
STACK = 6              # how much higher each month stands than the month before, so the next one and its field open over it
SAY_LINES = 5          # the most lines their line breaks into, as many as the card's line box holds

HOOK = 5.0
DIVE = (2.6, 0.8)      # the camera dives into the hook's window: from this beat, for this long; the year holds still over its
                       # window for a second before it, and the hook card rests just before
CLOSER = 6.0           # beats from the closer's start to the stop
CHAPTERS = 3.5         # beats the year's rows hold whole before the card's closer takes the frame for the stop
HOLD = 2.2             # seconds the picture holds still after the stop: the stop's ring, then two seconds of silence
SUBJECT = 0.15         # half the subject box around a photograph's focus, as a fraction of the frame
# the bands a move draws across the whole frame for its whole beat, each [top, height] as fractions of the frame's height,
# where motion/system/moves/move/<id>.tsx draws them; a month's words stand clear of its move's bands by BAND_CLEAR
MOVE_BANDS = {"marquee": [(0.1, 200 / 1920), (0.74, 200 / 1920)]}
# the bands a move draws at a picture in the card's box ([x0, y0, x1, y1], frame px), each [top, bottom] in frame px: the
# heavy rule over the picture's head and the hairline under its foot
PICTURE_BANDS = {"rule-draw": lambda pic: [(pic[1] - 36, pic[1] - 18), (pic[3] + 14, pic[3] + 17)]}
BAND_CLEAR = 32
# a boxed photograph's accent line keeps LINE_IN[1] of the box's height inside its edges, or LINE_IN[0] where it runs
# level past the subject, and stands LINE_CLEAR px clear of the subject box
LINE_IN = (0.06, 0.18)
LINE_CLEAR = 24
REACH = 0.06           # how far past the piece frame its halves run, as a fraction of the frame (month.tsx draws to it)
HEADING_GAP = 24       # the wall between the year's heading and an open month's photograph under it, px
TILT = 0.5             # how far the person's palette turns the card's grade: its darkest color into the shadows, its
                       # lightest into the highlights, its color into the saturation
FLASH_BEAT = 1.0       # the hook's second beat starts as its window drops open and the months flash


QUICK, HELD, PEAK = 5.0, 7.0, 10.0  # a month's length in beats: two quick months, then a held one; the peak longest


def month_beats(index, peak, stretch=1.0):
    """A month's length in beats: a run of two quick months and then a held one, over and over, so the beats vary and
    a fast run is always followed by a held composition, and the story's peak, which holds longest by a clear margin.
    `stretch` lengthens every month alike, so a year of few months still runs the length the person asked for. Their
    whole line stands within a second of the month's start, so even a quick month holds it to read."""
    return round((PEAK if peak else HELD if index % 3 == 2 else QUICK) * stretch, 3)


def _rgb(hx):
    return [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def grade(palette, card, colors=None):
    """The film's one grade: the card's grade (`card`, its finish's lift, gamma, gain and saturation), turned by the
    person's palette (taste.json `palette.year`, each color with its share): the shadows lift toward the palette's
    darkest color, the highlights take its lightest, saturation follows how colorful the year is and the midtones how
    light it is, each by TILT, and by less where the turn would take the board's ink and paper (`colors`) under
    CONTRAST against each other. Every frame takes it in the stage's last pass, in display values. No palette, the
    card's grade as it is."""
    base = {"lift": list(card["lift"]), "gamma": card["gamma"], "gain": list(card["gain"]), "saturation": card["saturation"]}
    if not palette:
        return base
    dark = _rgb(min(palette, key=lambda c: _lum(c["hex"]))["hex"])
    light = _rgb(max(palette, key=lambda c: _lum(c["hex"]))["hex"])
    total = sum(c.get("share") or 0 for c in palette) or 1
    mean = lambda f: sum((c.get("share") or 0) * f(_rgb(c["hex"])) for c in palette) / total
    chroma = mean(lambda v: max(v) - min(v))
    luma = mean(lambda v: 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2])
    top = max(light) or 1

    def turned(t):
        return {"lift": [round(base["lift"][i] + t * 0.12 * dark[i], 4) for i in range(3)],
                "gamma": round(base["gamma"] * (1 + t * 0.4 * (luma - 0.4)), 4),
                "gain": [round(base["gain"][i] * (1 - t * 0.4 * (1 - light[i] / top)), 4) for i in range(3)],
                "saturation": round(base["saturation"] * (1 + t * (chroma - 0.25)), 4)}

    def holds(g):
        if not colors:
            return True
        lit = {"dark": _lum(colors["paper"]), "bright": _lum(colors["ink"])}
        return all(held(k, 0, lit, g, colors) >= CONTRAST for k in ("ink", "paper"))
    return next((turned(TILT * k / 4) for k in range(4, 0, -1) if holds(turned(TILT * k / 4))), base)


def line(text, x, y, size, face="display", weight=None, color="paper", **kw):
    out = {"text": text, "x": round(x, 1), "y": round(y, 1), "size": size, "face": face, "color": color}
    if weight:
        out["weight"] = weight
    out.update(kw)
    return out


def cover(size, focus, w, h, over=1.06):
    """The photograph laid over a w by h frame, `over` larger than the frame's cover so a push never shows its edge,
    centered on the focus as far as the edges allow: [x, y, width, height] px. Where its line falls is the focus's to
    decide; whether that line lies in the type area with room for its words is fits' and the findings' to say."""
    pw, ph = size
    k = max(w / pw, h / ph) * over
    a, b = pw * k, ph * k
    x = min(0.0, max(w - a, w / 2 - focus[0] * a))
    y = min(0.0, max(h - b, h / 2 - focus[1] * b))
    return [round(x, 1), round(y, 1), round(a, 1), round(b, 1)]


def set_said(text, measure, face, weight, sizes, wide, tall, lead):
    """Their line broken for the screen: (size, [line, ...]), at the largest size in `sizes` (largest, smallest) where it
    breaks into at most SAY_LINES lines, none wider than `wide` and all of them standing no taller than `tall` (the first
    line's cap to the last baseline, a line every `lead` times the size), in as few lines as that size allows, each break
    where it leaves the widest line narrowest. A line that fits nowhere is set at the smallest size in the most lines,
    and the board's findings say so."""
    words = text.split()
    if not words:
        return sizes[0], []
    w = [measure(x, 100, face, weight)[0] for x in words]
    gap = measure("a b", 100, face, weight)[0] - measure("ab", 100, face, weight)[0]
    run = lambda i, j: sum(w[i:j]) + gap * (j - i - 1)

    def breaks(n):
        """The words in n lines whose widest is narrowest, or None where there are fewer words than lines."""
        if len(words) < n:
            return None
        best = {(0, 0): (0.0, [])}
        for k in range(1, n + 1):
            for j in range(k, len(words) - (n - k) + 1):
                best[(k, j)] = min(((max(best[(k - 1, i)][0], run(i, j)), best[(k - 1, i)][1] + [(i, j)])
                                    for i in range(k - 1, j) if (k - 1, i) in best), key=lambda r: r[0])
        return [" ".join(words[i:j]) for i, j in best[(n, len(words))][1]]
    arranged = {n: breaks(n) for n in range(1, SAY_LINES + 1)}
    for size in range(sizes[0], sizes[1] - 1, -2):
        cap = measure("H", size, face, weight)[1]
        for n, ls in arranged.items():
            if ls and cap + (n - 1) * lead * size <= tall and all(measure(t, size, face, weight)[0] <= wide for t in ls):
                return size, ls
    return sizes[1], next(ls for ls in reversed(arranged.values()) if ls)


def area_box(frac):
    """A card's line box ([x, y, width, height], fractions of the frame) laid over the reel's type area, px: the card
    draws its grid on the whole frame, and the reel keeps everything a person reads inside its type area."""
    x, y, w, h = frac
    aw, ah = WORDS_AREA[2] - WORDS_AREA[0], WORDS_AREA[3] - WORDS_AREA[1]
    return [round(WORDS_AREA[0] + x * aw, 1), round(WORDS_AREA[1] + y * ah, 1), round(WORDS_AREA[0] + (x + w) * aw, 1), round(WORDS_AREA[1] + (y + h) * ah, 1)]


def layout_of(photo, size):
    """The card's photo layout for a photograph of `size` px: one wider than it is tall takes the card's landscape box
    and line box, so it fills its own part of the frame instead of leaving bare ground under it."""
    if size[0] <= size[1]:
        return photo
    land = photo["landscape"]
    return {**photo, "picture": {**photo["picture"], "box": land["box"]}, "line": {**photo["line"], "box": land["line"]}}


def picture_box(photo):
    """Where the card stands a month's photograph, px of the piece frame, or None where it shows none: a full frame
    runs REACH past every edge, so a move never shows its edge; any other box is the card's own, on the whole frame."""
    p = photo["picture"]
    if not p["show"]:
        return None
    x, y, w, h = p["box"]
    if w >= 1 and h >= 1:
        return [round(-REACH * W, 1), round(-REACH * H, 1), round((1 + REACH) * W, 1), round((1 + REACH) * H, 1)]
    return [round(x * W, 1), round(y * H, 1), round((x + w) * W, 1), round((y + h) * H, 1)]


def shown(size, focus, ln):
    """Whether the photograph's line, laid full frame by cover, lies inside the type area's height at both of its sides,
    where the accent line it carries is read."""
    y0, y1 = piece_line(cover(size, focus, W, H), ln)
    yl = lambda x: y0 + (y1 - y0) * x / W
    return all(AREA[1] <= yl(X) <= AREA[3] for X in (AREA[0], AREA[2]))


def _linear(v):
    """An sRGB channel (0-1) in linear light."""
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


@functools.lru_cache(maxsize=None)
def _luminance(path):
    """A photograph as its relative luminance, each pixel 0-255 for 0-1."""
    from PIL import Image
    lut = [round(255 * _linear(v / 255)) for v in range(256)]
    rgb = Image.open(path).convert("RGB")
    return Image.merge("RGB", [c.point(lut) for c in rgb.split()]).convert("L", (0.2126, 0.7152, 0.0722, 0))


def light(file, place, boxes):
    """The photograph's light under type, read from the file the film draws: the relative luminance (0-1) of the darkest
    tenth and of the brightest tenth of the pixels under the type's boxes (px of the frame the photograph is laid over at
    `place`), and its spread (the luminance of its brightest quarter less that of its darkest)."""
    from PIL import Image, ImageDraw
    im = _luminance(str((Path("public") / file).resolve()))
    x, y, a, b = place
    u = lambda px, n, o, d: min(n, max(0, round((px - o) / d * n)))
    rects = [(u(bx[0], im.width, x, a), u(bx[1], im.height, y, b), u(bx[2], im.width, x, a), u(bx[3], im.height, y, b))
             for bx in boxes]
    rects = [r for r in rects if r[2] > r[0] and r[3] > r[1]]
    if not rects:
        return {"dark": 0.0, "bright": 0.0, "busy": 0.0}
    crop = around(rects)
    mask = Image.new("L", (crop[2] - crop[0], crop[3] - crop[1]), 0)
    draw = ImageDraw.Draw(mask)
    for r in rects:
        draw.rectangle([r[0] - crop[0], r[1] - crop[1], r[2] - crop[0] - 1, r[3] - crop[1] - 1], fill=255)
    h = im.crop(tuple(crop)).histogram(mask)
    n, seen, q = sum(h), 0, {}
    for v, c in enumerate(h):
        seen += c
        for k in (0.1, 0.25, 0.75, 0.9):
            if k not in q and seen >= k * n:
                q[k] = v / 255
    # each read half a step of the 8-bit read toward the side that is harder on the type
    return {"dark": max(0.0, q[0.1] - 0.5 / 255), "bright": min(1.0, q[0.9] + 0.5 / 255), "busy": q[0.75] - q[0.25]}


def _lum(color):
    """A #rrggbb color's relative luminance."""
    v = [_linear(int(color[i:i + 2], 16) / 255) for i in (1, 3, 5)]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def _contrast(a, b):
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def graded(lin, g):
    """The relative luminance of a color (linear light 0-1, per channel) as the film's grade (`grade`) leaves it, the
    way the stage's last pass grades it: encoded at gamma 2.2, lift and gain, then gamma, then saturation, decoded."""
    v = [max(0.0, c) ** (1 / 2.2) for c in lin]
    if g:
        v = [max(0.0, g["lift"][i] + (g["gain"][i] - g["lift"][i]) * v[i]) ** (1 / g["gamma"]) for i in range(3)]
        mid = 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
        v = [max(0.0, mid + g["saturation"] * (c - mid)) for c in v]
    return 0.2126 * v[0] ** 2.2 + 0.7152 * v[1] ** 2.2 + 0.0722 * v[2] ** 2.2


def held(color, alpha, lit, g, colors):
    """The contrast `color` type (ink or paper) holds over the light under it (`light`) with a plate of the other color
    at `alpha` between them, once the film's grade `g` has covered both. Ink is read against the darkest tenth of that
    light and paper against the brightest, each taken as a gray; the plate's own color is blended over it as the film
    blends it, in linear light, before the grade."""
    other = "paper" if color == "ink" else "ink"
    bare = lit["dark"] if color == "ink" else lit["bright"]
    rgb = lambda c: [_linear(int(colors[c][i:i + 2], 16) / 255) for i in (1, 3, 5)]
    return _contrast(graded(rgb(color), g), graded([bare + alpha * (v - bare) for v in rgb(other)], g))


def legible(lit, g, colors):
    """How the wall's type stands over the light under it (`light`): {color, plate, alpha, contrast}. The type takes the
    one of ink and paper that needs the lighter plate to hold CONTRAST there, and the plate under it is the other color
    at just that density, to the hundredth (alpha 0, none, where the type holds it bare). `contrast` is what the type
    holds with it, graded."""
    alpha = {k: next((a / 100 for a in range(101) if held(k, a / 100, lit, g, colors) >= SET_TO), 1.0) for k in ("ink", "paper")}
    color = min(alpha, key=lambda k: (alpha[k], -held(k, 0, lit, g, colors)))
    return {"color": color, "plate": "paper" if color == "ink" else "ink", "alpha": alpha[color],
            "contrast": round(held(color, alpha[color], lit, g, colors), 2)}


def holds(fg, plate, alpha, lit, g):
    """The contrast type in `fg` (#rrggbb) holds over the light under it (`light`) with a plate in `plate` at `alpha`
    between them, once the film's grade `g` has covered both: type lighter than its plate is read against the
    brightest tenth of that light, darker type against the darkest, each taken as a gray under the plate's own color,
    blended as the film blends it, in linear light, before the grade."""
    rgb = lambda c: [_linear(int(c[i:i + 2], 16) / 255) for i in (1, 3, 5)]
    bare = lit["bright"] if _lum(fg) > _lum(plate) else lit["dark"]
    return _contrast(graded(rgb(fg), g), graded([bare + alpha * (v - bare) for v in rgb(plate)], g))


def dressed(role, scrim, lit, g, colors):
    """How a month's words stand where the card sets them: in the card's color `role` on a plate of whichever of the
    background, ink and paper sets that color off most, at the card's scrim or as dense as CONTRAST over the light
    under them (`light`) needs; where the card's color holds CONTRAST at no density, the one of paper and ink that needs
    the lighter plate. {color, plate, alpha, contrast}."""
    def tried(c):
        plate = max(("bg", "ink", "paper"), key=lambda k: _contrast(_lum(colors[c]), _lum(colors[k])))
        alpha = next((k / 100 for k in range(round(scrim * 100), 101) if holds(colors[c], colors[plate], k / 100, lit, g) >= SET_TO), None)
        return {"color": c, "plate": plate, "alpha": alpha}
    own = tried(role)
    if own["alpha"] is None:
        own = min((tried(c) for c in ("paper", "ink") if c != role), key=lambda d: 2 if d["alpha"] is None else d["alpha"])
    own["alpha"] = 1.0 if own["alpha"] is None else own["alpha"]
    own["contrast"] = round(holds(colors[own["color"]], colors[own["plate"]], own["alpha"], lit, g), 2)
    return own


def dimmed(lit):
    """The light under type set on the ground, which the film draws softened and dimmed to DIM of the photograph's light:
    the photograph's own read, dimmed the same way. Softening only pulls the brightest and the darkest toward the middle,
    so the sharp read stays on the side that is harder on the type."""
    return {k: v * DIM for k, v in lit.items()}


def band_gain(file, place, ln, band):
    """How much of its light a month's band carries on the wall: the slit of the photograph around its line, as wide as
    the photograph and as tall as the band's shape allows (month.tsx spreads it so), dimmed to BAND_LIGHT where its mean
    light runs over it, never under BAND_LEAST."""
    x, y, a, b = place
    hb = min(b, (band[3] - band[1]) * a / (band[2] - band[0]))
    my = min(y + b - hb / 2, max(y + hb / 2, (ln[0] + ln[1]) / 2))
    mean = light_mean(file, place, [x, my - hb / 2, x + a, my + hb / 2])
    return round(max(BAND_LEAST, min(1.0, BAND_LIGHT / mean)) if mean > 0 else 1.0, 3)


def light_mean(file, place, box):
    """The mean relative luminance (0-1) of the photograph laid at `place` under `box` (px of that frame)."""
    im = _luminance(str((Path("public") / file).resolve()))
    x, y, a, b = place
    u = lambda px, n, o, d: min(n, max(0, round((px - o) / d * n)))
    crop = (u(box[0], im.width, x, a), u(box[1], im.height, y, b), u(box[2], im.width, x, a), u(box[3], im.height, y, b))
    if crop[2] <= crop[0] or crop[3] <= crop[1]:
        return 0.0
    h = im.crop(crop).histogram()
    return sum(v * c for v, c in enumerate(h)) / max(1, sum(h)) / 255


def pad_box(box, pad=PAD):
    return [round(box[0] - pad, 1), round(box[1] - pad, 1), round(box[2] + pad, 1), round(box[3] + pad, 1)]


def around(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def piece_line(place, ln):
    """The photograph's line in the piece frame, exactly where it lies on the photograph: its y at the frame's left and
    right edges."""
    x, y, a, b = place
    u0, v0, u1, v1 = ln
    p0 = (x + u0 * a, y + v0 * b)
    p1 = (x + u1 * a, y + v1 * b)
    slope = (p1[1] - p0[1]) / (p1[0] - p0[0] or 1e-6)
    mid = p0[1] + slope * (W / 2 - p0[0])
    return [round(mid - slope * W / 2, 1), round(mid + slope * W / 2, 1)]


def boxed_line(ln, pic, subject):
    """The accent line on a photograph in the card's box: inside the box, where it is seen on the photograph, and clear
    of the subject box across the box's width, so it never crosses a face. A line that would cross the subject runs
    level instead, at the nearer side of the subject with room inside the box, else along the box's foot."""
    h = pic[3] - pic[1]
    mid = (ln[0] + ln[1]) / 2
    to = min(pic[3] - LINE_IN[1] * h, max(pic[1] + LINE_IN[1] * h, mid))
    ln = [ln[0] + to - mid, ln[1] + to - mid]
    ys = [ln[0] + (ln[1] - ln[0]) * x / W for x in (max(pic[0], subject[0]), min(pic[2], subject[2]))]
    if max(ys) < subject[1] - LINE_CLEAR or min(ys) > subject[3] + LINE_CLEAR:
        return [round(v, 1) for v in ln]
    lo, hi = pic[1] + LINE_IN[0] * h, pic[3] - LINE_IN[0] * h
    room = [y for y in (subject[1] - LINE_CLEAR, subject[3] + LINE_CLEAR) if lo <= y <= hi]
    y = min(room, key=lambda v: abs(v - to)) if room else hi
    return [round(y, 1), round(y, 1)]


def laid_in(size, focus, box):
    """The photograph laid to cover `box` (px), centered on its focus as far as its edges allow: [x, y, width, height]."""
    x, y, a, b = cover(size, focus, box[2] - box[0], box[3] - box[1], 1.0)
    return [round(box[0] + x, 1), round(box[1] + y, 1), a, b]


def set_month(m, place, pic, photo, measure, box_of, g, colors, lead, move=None):
    """A month's words set the card's way (`photo`, the card's photo layout): the month's name in the card's label face,
    size and color at the top of the card's line box (area_box), and under it their line in the card's line face and
    color, at the card's size or as much smaller as fits the box in at most SAY_LINES lines, one Line a word, aligned as
    the card says. A wordless month's name takes the line's place, face, size and color. Where the words lie over the
    photograph they move up or down the type area, the least way, until they are clear of its subject (the SUBJECT box
    around its focus), or where no place clears it to the one covering it least, and always clear of the bands the
    month's `move` draws across the frame (MOVE_BANDS) or at the picture in the card's box (PICTURE_BANDS) where any
    place is. Their color and plate come from `dressed`, over the light under them: the photograph where they lie on
    it, else the card's ground. {name, said, plate, box, subject, on_subject}."""
    spec, lab = photo["line"], photo["label"]
    box = area_box(spec["box"])
    wide = box[2] - box[0]
    fit = lambda text, face, size: next((z for z in range(size, 23, -2) if measure(text, z, face)[0] <= wide), 24)
    if m["said"]:
        nface, ncolor = lab["face"], lab["color"]
        nsize = fit(m["short"], nface, lab["size"])
        ncap = measure("H", nsize, nface)[1]
        gap = round(0.6 * nsize)
        least = max(32, round(spec["size"] * 0.5))
        broken = lambda top: set_said(m["said"], measure, spec["face"], None, (top, least), wide,
                                      box[3] - box[1] - ncap - gap, lead[spec["face"]])
        size, said = broken(spec["size"])
    else:
        nface, ncolor = spec["face"], spec["color"]
        nsize = fit(m["short"], nface, spec["size"])
        ncap, gap, size, said = measure("H", nsize, nface)[1], 0, spec["size"], []
    scap = measure("H", size, spec["face"])[1] if said else 0
    pitch = lead[spec["face"]] * size
    space = measure("a b", size, spec["face"])[0] - measure("ab", size, spec["face"])[0] if said else 0
    rot = {"rotate": spec["rotate"], "pivot": [box[0], box[1]]} if spec.get("rotate") else {}

    def x_of(width, lsb):
        return (box[0] + box[2]) / 2 - width / 2 - lsb if spec["align"] == "center" else box[0] - lsb

    def set_at(top):
        nw, _, nl = measure(m["short"], nsize, nface)
        name = line(m["short"], x_of(nw, nl), top + ncap, nsize, face=nface, color=ncolor, name=f"label-{m['id']}", **rot)
        words = []
        for j, text in enumerate(said):
            tw, _, tl = measure(text, size, spec["face"])
            x = x_of(tw, tl)
            for w in text.split():
                words.append(line(w, x, top + ncap + gap + scap + j * pitch, size, face=spec["face"], color=spec["color"],
                                  name=f"said-{m['id']}", **rot))
                x += measure(w, size, spec["face"])[0] + space
        return name, words

    fx, fy = place[0] + m["focus"][0] * place[2], place[1] + m["focus"][1] * place[3]
    subject = [round(fx - SUBJECT * W, 1), round(fy - SUBJECT * H, 1), round(fx + SUBJECT * W, 1), round(fy + SUBJECT * H, 1)]
    overlap = lambda u, v: max(0, min(u[2], v[2]) - max(u[0], v[0])) * max(0, min(u[3], v[3]) - max(u[1], v[1]))
    on_picture = lambda bx: pic is not None and overlap(bx, pic) > 0

    def inside():
        ink = [box_of(t) for t in set_at(box[1])[1]]
        return max(b[2] for b in ink) <= box[2] and min(b[0] for b in ink) >= box[0]

    def smaller():
        nonlocal size, said, scap, pitch, space
        size, said = broken(size - 2)
        scap = measure("H", size, spec["face"])[1]
        pitch = lead[spec["face"]] * size
        space = measure("a b", size, spec["face"])[0] - measure("ab", size, spec["face"])[0]

    if said:
        # a line breaks by its words' advance widths; where the words' ink, set one by one, reaches past the card's
        # line box, the line is set a step smaller until every word's ink stays inside it
        while size > least and not inside():
            smaller()

    def tried(top):
        name, words = set_at(top)
        bx = around([box_of(t) for t in [name, *words]])
        return {"top": top, "name": name, "said": words, "box": bx, "on": overlap(bx, subject) if on_picture(bx) else 0}

    bands = [(a * H - BAND_CLEAR, (a + h) * H + BAND_CLEAR) for a, h in MOVE_BANDS.get(move, [])]
    if move in PICTURE_BANDS and pic is not None and pic[2] - pic[0] <= W:
        bands += [(a - BAND_CLEAR, b + BAND_CLEAR) for a, b in PICTURE_BANDS[move](pic)]
    clear = lambda r: all(r["box"][3] <= b0 or r["box"][1] >= b1 for b0, b1 in bands)

    def placed():
        first = tried(box[1])
        height = first["box"][3] - first["box"][1]
        tops = sorted(range(round(WORDS_AREA[1] + first["top"] - first["box"][1]), round(WORDS_AREA[3] - height + first["top"] - first["box"][1]) + 1, 8),
                      key=lambda v: abs(v - box[1]))
        if not first["on"] and clear(first):
            return first
        return min((tried(v) for v in tops), key=lambda r: (not clear(r), r["on"], abs(r["top"] - box[1])), default=first)
    best = placed()
    if (best["on"] or not clear(best)) and said:
        # where no place clears the subject and the move's bands at the line's size, the line is set a step smaller,
        # down to its least size, until one does; where none does even then, it keeps the largest size whose place
        # clears the bands, else its own size, at the place covering the subject least
        kept = (size, said, scap, pitch, space, best)
        banded = None if not clear(best) else kept
        while (best["on"] or not clear(best)) and size > least:
            smaller()
            if not inside():
                continue
            best = placed()
            if banded is None and clear(best):
                banded = (size, said, scap, pitch, space, best)
        if best["on"] or not clear(best):
            size, said, scap, pitch, space, best = banded or kept
    lines = [best["name"], *best["said"]]
    boxes = [box_of(t) for t in lines]
    ground = colors.get(photo["ground"], colors["bg"])
    lit = light(m["file"], place, [around(boxes)]) if on_picture(best["box"]) else {"dark": _lum(ground), "bright": _lum(ground)}
    scrim = spec.get("scrim") or 0
    look = dressed(spec["color"], scrim if on_picture(best["box"]) else 0, lit, g, colors)
    for t in best["said"]:
        t["color"], t["contrast"] = look["color"], look["contrast"]
    name = best["name"]
    plate_hex = colors[look["plate"]]
    if holds(colors.get(name["color"], name["color"]), plate_hex, look["alpha"], lit, g) >= CONTRAST:
        name["contrast"] = round(holds(colors.get(name["color"], name["color"]), plate_hex, look["alpha"], lit, g), 2)
    else:
        name["color"], name["contrast"] = look["color"], look["contrast"]
    x0, y0, x1, y1 = pad_box(around([box_of(dict(t, rotate=0)) for t in lines]), PLATE_PAD)
    if scrim and on_picture(best["box"]) and pic[2] - pic[0] > W:
        # the card's scrim over a full frame: a band from the frame's edge nearer the words across them, running past
        # the frame on its other three sides and fading over SCRIM_SOFT toward the frame's middle, so the photograph
        # shows whole beyond it
        if (y0 + y1) / 2 < H / 2:
            plate = {"box": [-SCRIM_SOFT, pic[1] - SCRIM_SOFT, W + SCRIM_SOFT, round(y1 + SCRIM_SOFT, 1)], "soft": SCRIM_SOFT}
        else:
            plate = {"box": [-SCRIM_SOFT, round(y0 - SCRIM_SOFT, 1), W + SCRIM_SOFT, pic[3] + SCRIM_SOFT], "soft": SCRIM_SOFT}
    else:
        plate = {"box": [x0, y0, x1, y1], "soft": 2}
    plate.update(rotate=spec.get("rotate") or 0, pivot=[box[0], box[1]], color=look["plate"], alpha=look["alpha"])
    return {"name": name, "said": best["said"], "plate": plate, "box": best["box"], "subject": subject, "on_subject": round(best["on"])}


def tags_of(m, peak):
    """What a month's photograph shows, as the card's moves and cuts name it: a portrait or a landscape, people, a
    place, the story's peak. Its words ride its line, set by this film, so a move never takes them."""
    w, h = m["size"]
    tags = {"photo", "portrait" if h > w else "landscape"}
    if peak:
        tags.add("peak")
    if m.get("people"):
        tags.add("people")
    if m.get("place"):
        tags.add("place")
    return tags


def build(run, measure, box_of, bpm, card, colors, stretch=1.0, rank=0):
    """The board's year: the wall, the months, the hook and the closer, with their times. `run` is storyboard.Run, its
    months in calendar order; `measure(text, size, face, weight)` gives a line's advance width, cap height and left side
    bearing in px, and `box_of(line)` a line's box at rest, turned about its pivot; `bpm` is the film's tempo, whose beats
    every time here counts; `card` is the style card and `colors` the six roles its palette rule made; `stretch`
    lengthens every month alike (month_beats); `rank` is the look's place among the drafted looks, which picks the
    photograph its hook's window opens on (leads)."""
    import style
    months = run.months
    # the film's one grade, the card's turned by the person's palette; the type's contrast is held through it. A card
    # that stands its photographs in a box, or shows none, keeps its own grade: its moves cut their mats and cells in
    # the card's ground over the graded film, and a turned ground would set them apart from the ground they cut into
    pb = picture_box(card["photo"])
    turns = pb is not None and pb[2] - pb[0] > W
    g = grade((run.taste.get("palette") or {}).get("year") or [] if turns else [], card["finish"]["grade"], colors)
    used, cuts_used = {}, {}
    prev = {"move": None, "cut": None}

    # the story's peak takes a move the card made for a peak wherever it has one
    peak_moves = lambda: [o for o in card["moves"] if "peak" in o["fits"]] or card["moves"]

    def choose(tags, form, cut=True, spare=None):
        pool = peak_moves() if form == "peak" else [o for o in card["moves"] if o["id"] != spare] or card["moves"]
        mv = style.pick(pool, tags, form, used, prev["move"])
        ct = style.pick(card["transitions"], tags, form, cuts_used, prev["cut"]) if cut else None
        prev.update(move=mv, cut=ct)
        return mv, ct
    # the window opens under the title in one shot: the flashes come on with no cut over them
    hook_moves = [choose({"title"}, "title", cut=False)[0], choose({"wall"}, "wall", cut=False)]
    photo = card["photo"]
    lead = {f: card["faces"][f].get("lineHeight", 1.0) for f in ("display", "text")}
    lower = run.lower
    fit = lambda s: s.lower() if lower else s

    # a line set flush with the type area's left edge: its ink, not its advance, starts there
    flush = lambda text, size, face="display", weight=None: SAFE["left"] - measure(text, size, face, weight)[2]
    # the wall
    title = line(str(run.year), flush(str(run.year), TITLE), RULE_Y - 35, TITLE, name="title")
    right = W - SAFE["right"]
    # the sign-off: as large as runs inside the type area's width, never under its smallest size, its foot on the type
    # area's foot
    say = fit(run.words["signoff"])
    size = next((s for s in range(SIGNOFF[1], SIGNOFF[0] - 1, -2) if measure(say, s, "display")[0] <= AREA[2] - AREA[0]), SIGNOFF[0])
    signoff = line(say, flush(say, size), 0, size, name="signoff")
    foot = box_of(signoff)
    signoff["y"] = round(AREA[3] - 1 - foot[3], 1)
    # the rows share the wall from under the title's underline to over the sign-off, none taller than PITCH; a row's
    # month is set as large as its row allows, never under its smallest size
    pitch = min(PITCH, (signoff["y"] + foot[1] - SIGNOFF_GAP - ROW_TOP) / len(months))
    label = max(LABEL[0], min(LABEL[1], round(LABEL_FILL * pitch)))
    # the bars start past the widest month label, so every label stands on the ground and none on a band, and every
    # bar runs to the type area's right edge: each row is a chapter of the year, all of them alike
    bar_x = SAFE["left"] + max(measure(m["short"], label, "display")[0] for m in months) + 36
    rows = []
    for i, m in enumerate(months):
        top = ROW_TOP + i * pitch
        yc = round(top + pitch / 2, 1)
        cap = measure(m["short"], label, "display")[1]
        # the band: the month's photograph across the wall from the label column to the spine, which closes the row
        # the row's accent line runs in the dark under its band, so the rows read as one ruled figure
        rows.append({"y": yc, "x0": round(bar_x, 1), "x1": round(right, 1), "rule": round(top + pitch, 1),
                     "band": [round(bar_x - 12, 1), round(top + GAP, 1), round(right, 1), round(top + pitch - GAP, 1)],
                     "label": line(m["short"], flush(m["short"], label), yc + cap / 2, label, name=f"label-{m['id']}")})
    # the handle only where the export's profile names one
    handle = line(run.handle, right, RULE_Y - 35, HANDLE, face="text", weight=700, name="handle", anchor="end") if run.handle else None

    # the year's heading, which no open month's photograph covers
    heading = box_of(title)
    # every month's piece frame lies at one place on the wall, so each month's photograph opens over the one before
    # where it lies and the picture is always a month's own photograph: the place where the last month's line lands on
    # the last row's bar, or lower when that would put its top over the year's heading, which the camera shows as it
    # pulls back from the last month to the wall
    last = months[-1]
    ln = piece_line(cover(last["size"], last["focus"], W, H), last["line"])
    T = {"s": S, "o": [round((rows[-1]["x0"] + rows[-1]["x1"]) / 2 - S * W / 2, 1),
                       round(max(rows[-1]["y"] - S * (ln[0] + ln[1]) / 2, heading[3] + HEADING_GAP + S * REACH * H), 1)]}

    # the months, each in the piece frame
    out = []
    t = HOOK
    for i, m in enumerate(months):
        L = month_beats(i, m["id"] == run.peak, stretch)
        # the story's peak is a form of its own, so it takes the move the card made for a peak, which the month before
        # it leaves alone so the peak's is never its own move twice running
        nxt = months[i + 1] if i + 1 < len(months) else None
        spare = style.pick(peak_moves(), tags_of(nxt, True), "peak", {}, None) if nxt and nxt["id"] == run.peak else None
        before = prev["move"]
        tags, form = tags_of(m, m["id"] == run.peak), "peak" if m["id"] == run.peak else "photo"
        move, cut = choose(tags, form, spare=spare)
        lay = layout_of(photo, m["size"])
        pic = picture_box(lay)
        full = pic is None or pic[2] - pic[0] > W
        place = cover(m["size"], m["focus"], W, H) if full else laid_in(m["size"], m["focus"], pic)
        ln = piece_line(place, m["line"])
        row = rows[i]
        b = BAR / 2 / S
        typed = set_month(m, place, pic, lay, measure, box_of, g, colors, lead, move)
        if not full:
            ln = boxed_line(ln, pic, typed["subject"])
        others = [o for o in (peak_moves() if form == "peak" else card["moves"]) if o["id"] not in (move, spare)]
        if typed["on_subject"] and (move in MOVE_BANDS or move in PICTURE_BANDS) and others:
            # a move whose bands leave the words no place clear of the photograph's subject gives way to the card's
            # next pick for the month
            used[move] -= 1
            move = style.pick(others, tags, form, used, before)
            prev["move"] = move
            typed = set_month(m, place, pic, lay, measure, box_of, g, colors, lead, move)
        if pic is None:
            # no photograph on the month: the accent line is the rule its words stand on
            foot = round(min(AREA[3], typed["box"][3] + RULE_GAP), 1)
            ln = [foot, foot]
        out.append({
            "id": m["id"], "month": m["month"], "short": m["short"], "file": m["file"], "size": m["size"],
            "focus": m["focus"], "scene": m["scene"], "text": m["said"], "peak": m["id"] == run.peak, "extra": m.get("extra", []),
            "place": place, "picture": pic, "full": full, "line": ln, "band": round(b, 1),
            "gain": band_gain(m["file"], place, ln, row["band"]), "T": T, "lift": round(LIFT + STACK * i, 1),
            "row": row, "name": typed["name"], "said": typed["said"], "plate": typed["plate"],
            "move": move, "transition": cut, "box": [round(v, 1) for v in typed["box"]], "subject": typed["subject"], "on_subject": typed["on_subject"],
            "start": t, "beats": L,
        })
        t += L
    closing = choose({"closer"}, "closer")
    closer = {"at": t, "card": t + CHAPTERS, "still": t + CLOSER, "end": t + CLOSER + round(HOLD * bpm / 60, 3), "move": closing[0], "transition": closing[1],
              "shape": card["closer"]}
    close = [3.8, 0.6]
    say = round(max(SAY_IN[1], TYPED * bpm / 60 - SAY_IN[0] - LAND), 3) if card["photo"]["line"].get("enter") == "type" else SAY_IN[1]
    for i, m in enumerate(out):
        m["at"] = phases(m, out[i + 1]["start"] if i + 1 < len(out) else None,
                         [m["start"] - 0.02, 0.02] if i == 0 else [m["start"] - CARD, CARD], say)
    # the hook's window: it drops open from the underline, as wide as the type area and the reel's shape, and the camera
    # goes into it, so the months' photographs flash full frame
    ww = right - SAFE["left"]
    window = [SAFE["left"], RULE_Y, right, RULE_Y + round(ww * H / W)]
    # the hook card is the year over its open window, a photograph in it, just before the camera dives in; the year
    # slams in from the first frame, so the reel never opens on bare ground
    lead = leads(months, window)
    lead = lead[rank % len(lead)]
    hook = {"window": window, "flash": flashes(months), "order": [(lead + i) % len(months) for i in range(len(months))],
            "close": close, "slam": [0.0, 0.33], "dive": list(DIVE),
            "rest": round(DIVE[0] - 0.1, 2), "moves": [hook_moves[0], hook_moves[1][0]], "transition": hook_moves[1][1],
            "split": FLASH_BEAT}
    # the wall's ground: the first month's photograph, where the year starts, from the frame's top to its foot (the box
    # runs past the frames that see it, the photograph centered on what they see), the title set into it from the first
    # frame, every row's band laid over it as its month slides in, and its foot under the sign-off
    first = out[0]
    ground = {"month": first["id"], "box": [-0.15 * W, -720, 1.15 * W, H + 180]}
    # a card that lays its photographs full frame lays the wall on one; a card that stands them in a box, or shows none,
    # lays the wall flat in its photo ground, the color its months stand on
    pb = picture_box(photo)
    ground["flat"] = None if pb is not None and pb[2] - pb[0] > W else photo["ground"]

    def laid(m, box):
        x, y, a, b = cover(m["size"], m["focus"], box[2] - box[0], box[3] - box[1], 1.0)
        return [x + box[0], y + box[1], a, b]
    under = laid(first, ground["box"])
    ground["place"] = [round(v, 1) for v in under]
    # type set straight on the ground takes one of ink and paper for each group read together, and its plate, by the
    # light of the softened, dimmed ground under the group: the year, the handle, the rows' names (their plate a column
    # that stops short of the bands), and the sign-off
    plates = []
    groups = [("title", [title]), ("handle", [handle] if handle else []), ("labels", [r["label"] for r in rows]), ("signoff", [signoff])]
    for of, group in groups:
        if not group:
            continue
        boxes = [box_of(ln) for ln in group]
        flat = colors.get(ground["flat"]) if ground["flat"] else None
        look = legible({"dark": _lum(flat), "bright": _lum(flat)} if flat else dimmed(light(first["file"], under, boxes)), g, colors)
        for ln in group:
            ln["color"], ln["contrast"] = look["color"], look["contrast"]
        box = pad_box(around(boxes))
        if of == "labels":
            box[2] = round(min(box[2], bar_x - 14), 1)
        plates.append({"of": of, "box": box, "color": look["plate"], "alpha": look["alpha"]})
    y = {"title": title, "heading": [round(v, 1) for v in heading], "ground": ground, "rule": [SAFE["left"], RULE_Y, right],
         "handle": handle, "signoff": signoff, "rows": rows, "months": out, "hook": hook, "plates": plates, "dim": DIM,
         "closer": closer, "colors": {k: v for k, v in colors.items() if k != "swatches"}, "grade": g,
         "reach": round(box_of(title)[2], 1)}
    closer["hops"] = route(y)
    return y


# ------------------------------------------------------------------ timing inside a month (beats from its start)
DRAW = (0.1, 0.35)     # the dot draws the line
PART = (0.45, 0.15)    # the line parts into the slit
OPEN = (0.55, 0.8)     # the photograph's two halves take it over, flat on the wall, ready to fold
CARD = 0.4             # every month but the first: its photograph opens over the month before from this many beats before its start
BREATH = 1.0           # every month but the last: the camera draws back off it from this many beats before its end until
                       # the next month's photograph opens over it, the anticipation of the push into the next month,
                       # which lands past it and settles
ARRIVE = 0.75          # the camera has landed on a month this many beats after its start
PULL = 1.0             # the last month: the camera pulls back from its photograph to the wall, the halves still open, ending as they fold
FOLD = (1.5, 0.5)      # the last month's halves close onto the slit: from this many beats before its end, for this long
UNDER = 0.3            # every other month's halves close this many beats after its end, under the next month
SLIDE_IN = (1.0, 0.7)  # the last month's slit slides into its row from this many beats before its end; every other month's
                       # from the moment its halves have closed; for this long
SAY_IN = (0.55, 0.35)  # their line rises word by word: from this beat, over this long, whole by its last word's LAND
LAND = 0.15            # a word stands whole this long after its beat (words.tsx rises it from 0.05 before, over 0.2)
TYPED = 0.95           # a card that types its line has it whole this many seconds into the month, typed at one pace


def phases(m, nxt, card, say=SAY_IN[1]):
    """A month's moves in film beats: card (its photograph opening over the month before, or over the hook's window),
    the camera's arrival, draw, part, open, say (their line rising word by word, or typed letter by letter
    over `say` beats, whole within a second at any tempo),
    pull (the month left: the camera draws back off it, the next month's photograph opening over it as it goes, and
    pushes into the next from `nxt`, the next month's start; from the last month the camera pulls back to the wall),
    fold and slide (into its row). Every month but the last folds and slides under the next one."""
    a, L = m["start"], m["beats"]
    if nxt is None:
        fold = a + L - FOLD[0]
        pull = [fold - PULL, PULL]
        slide = [a + L - SLIDE_IN[0], SLIDE_IN[1]]
    else:
        fold = nxt + UNDER
        pull = [nxt - BREATH, BREATH]
        slide = [fold + FOLD[1], SLIDE_IN[1]]
    return {"card": [round(v, 3) for v in card], "arrive": a + ARRIVE, "draw": [a + DRAW[0], DRAW[1]],
            "part": [a + PART[0], PART[1]], "open": [a + OPEN[0], OPEN[1]], "say": [a + SAY_IN[0], say],
            "pull": pull, "fold": [fold, FOLD[1]], "slide": slide, "end": a + L}


FLASH = (1.0, HOOK - 1.0)  # the hook's flashes: from this beat, this many beats in all, up to the cut into the first month


def leads(months, window):
    """The months the hook's window can open on, best first: a month whose focus was read from its photograph (its
    subject is known) before one whose focus was measured, then the one whose focus the window's crop keeps nearest
    its middle, then calendar order. The first month comes last, because the hook cuts into it. Each drafted look opens
    on the next of these, so the looks start on different photographs."""
    x0, y0, x1, y1 = window
    w, h = x1 - x0, y1 - y0

    def off(m):
        pw, ph = m["size"]
        k = max(w / pw, h / ph)
        uw, uh = w / (pw * k), h / (ph * k)
        fu, fv = m["focus"]
        u0 = min(1 - uw, max(0.0, fu - uw / 2))
        v0 = min(1 - uh, max(0.0, fv - uh / 2))
        return abs(u0 + uw / 2 - fu) + abs(v0 + uh / 2 - fv)
    rest = sorted(range(1, len(months)), key=lambda i: (not months[i].get("read"), round(off(months[i]), 3), i))
    return rest + [0]


def flashes(months):
    """The beats the hook's window changes photograph on, with the beat its last flash ends: every month holds the
    window as long as the next."""
    f0, total = FLASH
    n = len(months)
    return [round(f0 + total * i / n, 3) for i in range(n + 1)]


def story(y):
    """What each beat's move reveals, and what it carries across the cut."""
    ms = y["months"]
    rows = [{"id": "hook", "reveals": f"the year ({y['title']['text']}) on the line the dot draws under the {y['hook']['moves'][0]} move, the line opening under it into a window where every month flashes full frame under the {y['hook']['moves'][1]} move, each as long as the next",
             "carries": f"the dot: the title's full stop, it leaves for {ms[0]['short']}'s line as the montage cuts into it"}]
    for i, m in enumerate(ms):
        what = m["scene"] or "the month's photograph"
        said = f", and under it their line \"{m['text']}\" rising word by word" if m["text"] else ""
        nxt = ms[i + 1] if i + 1 < len(ms) else None
        carries = (f"the dot: it leaves the line's end for {nxt['short']}'s line as {nxt['short']}'s photograph opens over this one; "
                   f"under it the halves close onto the line and it slides into {m['short']}'s row") if nxt else \
                  f"the accent line: the halves close onto it as the film cuts to the wall, and it levels and slides into {m['short']}'s row, the dot riding its end"
        rows.append({"id": m["id"], "reveals": f"{m['short']}: cut to by {m['transition']}, its own photograph ({what}) full frame under the {m['move']} move, with the accent line drawn along its own line and staying on it, the photograph splitting on it into two layers under a slow push, {m['short']} entering on the line letter by letter{said}",
                     "carries": carries})
    rows.append({"id": "closer", "reveals": f"the year's chapters whole: a row of each month's photograph, the dot drawing one accent spine down the rows' ends, then the card's {y['closer'].get('shape', 'closer')} closer taking the frame",
                 "carries": f"the sign-off \"{y['signoff']['text']}\", where picture and music stop"})
    return rows


def sound(y):
    """The board's sound cues: one where each beat lands (the year slamming onto its line, each month rising on its
    line, the dot landing as the closer's full stop), the build into the story's peak, the peak's impact and the stop.
    Words rise and the camera moves without a sound of their own."""
    cues = []
    add = lambda kind, at, beat, what, **kw: cues.append({"kind": kind, "at": round(at, 3), "beat": beat, "what": what, **kw})
    h = y["hook"]
    add("impact", h["slam"][0] + h["slam"][1], "hook", f"{y['title']['text']} slams onto the line and the dot lands as its full stop")
    for m in y["months"]:
        p = m["at"]
        if m["peak"]:
            add("riser", p["part"][0] - 2.0, m["id"], f"the build into {m['short']}, the story's peak", beats=2.0)
            add("impact", p["part"][0], m["id"], f"the dot finishes {m['short']}'s line and {m['short']} rises on it")
        else:
            add("hit", p["part"][0], m["id"], f"the dot finishes {m['short']}'s line and {m['short']} rises on it", weight=0.8, bright=1.0)
    c = y["closer"]
    add("hit", c["card"], "closer", "the card's closer takes the frame", weight=0.8, bright=1.0)
    add("impact", c["still"], "closer", "the sign-off lands")
    add("stop", c["still"], "closer", "picture and music stop together; the frame holds silent")
    return sorted(cues, key=lambda q: q["at"])


def route(y):
    """When the dot lands at the end of each month's row in the closer: the first as the camera settles, the last just
    before the card's closer takes the frame."""
    c = y["closer"]
    a, b = c["at"] + 0.6, c["card"] - 0.3
    n = len(y["months"])
    return [round(a + (b - a) * j / max(1, n - 1), 3) for j in range(n)]


SHOT = {True: ("a slow push in toward the subject", "a 50mm prime, shallow depth of field, the subject sharp"),
        False: ("a slow push in, the subject held in the frame", "a 35mm prime at eye level, deep focus")}


def crop_of(size, place, frame):
    """The part of a photograph laid at `place` (x, y, width, height px of some frame) that `frame` (x0, y0, x1, y1 of
    that frame) shows: x, y, width, height in the photograph's own px, even."""
    pw, ph = size
    x, y, a, b = place
    ev = lambda v: int(v) - int(v) % 2
    u0, v0 = (frame[0] - x) / a * pw, (frame[1] - y) / b * ph
    return [ev(max(0, u0)), ev(max(0, v0)), ev(min(pw, (frame[2] - frame[0]) / a * pw)), ev(min(ph, (frame[3] - frame[1]) / b * ph))]


def lighting(file, crop):
    """The light in a part of a photograph, in a cinematographer's words, read from its pixels: its key (how bright),
    its color (warm, neutral or cool), its contrast, and the side it falls from."""
    from PIL import Image
    x, y, w, h = crop
    im = Image.open(Path("public") / file).convert("RGB").crop((x, y, x + w, y + h)).resize((36, 64))
    px = [im.getpixel((i, j)) for j in range(64) for i in range(36)]
    lum = [(0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 for r, g, b in px]
    mean = sum(lum) / len(lum)
    warm = sum(r - b for r, _, b in px) / len(px) / 255
    q = sorted(lum)
    spread = q[int(0.9 * len(q))] - q[int(0.1 * len(q))]
    at = lambda xs, ys: sum(lum[j * 36 + i] for j in ys for i in xs) / (len(xs) * len(ys))
    left, right = at(range(18), range(64)), at(range(18, 36), range(64))
    top, foot = at(range(36), range(32)), at(range(36), range(32, 64))
    side = ("upper " if top - foot > 0.04 else "lower " if foot - top > 0.04 else "") + \
           ("left" if left - right > 0.04 else "right" if right - left > 0.04 else "")
    key = "low-key" if mean < 0.3 else "high-key" if mean > 0.6 else "mid-key"
    tone = "warm" if warm > 0.06 else "cool" if warm < -0.03 else "neutral"
    quality = "hard" if spread > 0.6 else "soft, even" if spread < 0.3 else "directional"
    falls = f"falling from the {side.strip()}" if side.strip() else "wrapping round from every side"
    shadows = ", deep shadows" if spread > 0.6 else ""
    return f"{tone} {quality} light {falls}{shadows}, a {key} exposure"


def clips(y, bpm):
    """The shots an image-to-video model would make, each the length of its beat until the film moves on, framed as the
    film frames it (9:16), a seamless loop: the hook's world (the first month's photograph, the place the year starts,
    alive behind the year), each month's photograph brought to life under its hold, and the wall's texture under the
    closer (the same photograph, only its light moving). Until one arrives the film's own layered move carries the
    beat on the still photograph."""
    sec = lambda beats: round(beats * 60 / bpm, 1)
    first, ms = y["months"][0], y["months"]
    wall = crop_of(first["size"], y["ground"]["place"], [0, 0, W, H])
    hook = sec(ms[0]["start"])
    shown = y["ground"]["flat"] is None
    out = [{"id": "hook", "beat": "hook", "role": "the hook's world", "seconds": hook, "image": first["file"], "crop": wall,
            "prompt": f"The world the year starts in: {first['scene'] or 'the place in this photograph'}, alive. Camera: a slow "
                      f"push in over {hook} seconds, easing back to its first frame. Lens: a 24mm wide prime at eye level, "
                      f"deep focus, the whole place sharp. Light: {lighting(first['file'], wall)}. Only the motion the place "
                      "has (air, water, leaves, light), no cuts, no text, nothing added; vertical 9:16, a seamless loop, the "
                      "last frame matching the first.",
            "stand_in": "the still photograph under the year as the line drops open into the window and the camera dives in"}]
    for i, m in enumerate(ms):
        secs = sec(m["beats"])
        crop = crop_of(m["size"], m["place"], [0, 0, W, H])
        move, lens = SHOT[m["peak"]]
        out.append({"id": f"{i + 1:02d}", "beat": m["id"], "role": "a still brought to life", "seconds": secs,
                    "image": m["file"], "crop": crop,
                    "prompt": f"{m['scene'] or 'The moment in this photograph'}, brought to life. Camera: {move} over {secs} "
                              f"seconds, returning to where it started. Lens: {lens}. Light: {lighting(m['file'], crop)}. "
                              "The subject moves as it would in the moment it was taken; no cuts, no text, nothing added; "
                              "vertical 9:16, framed exactly as the image, a seamless loop, the last frame matching the first.",
                    "stand_in": f"the still photograph split on its line into two layers that move at different rates under {move}, "
                                "over its soft field, the accent line on the cut"})
    close = sec(CLOSER)
    out.append({"id": "closer", "beat": "closer", "role": "texture under the closer", "seconds": close,
                "image": first["file"], "crop": wall,
                "prompt": f"Texture for the wall the year closes onto: {first['scene'] or 'the place in this photograph'}, "
                          f"nothing in it moving but its light, which drifts slowly across it as a cloud passes. Camera: locked "
                          f"off for {close} seconds. Lens: an 85mm, focus pulled off the place, so its shapes are soft. Light: "
                          f"{lighting(first['file'], wall)}. No cuts, no text, nothing added; vertical 9:16, a seamless loop, "
                          "the last frame matching the first.",
                "stand_in": "the still photograph, softened and mixed toward the background under the rows, still"})
    # a wall laid flat shows no photograph under the hook or the closer, so neither gets a shot
    return out if shown else out[1:-1]
