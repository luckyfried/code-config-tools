"""Every caption the film sets over a photograph, measured where the film draws it before the film renders (the shared
rule, motion/system/standards.md R3, through legible.py): each stop's label and line, the hook's title and its dates,
and the title card's words, each against the photograph under it (their clip's poster for a clip) as the camera frames
it while the words read, after the scrim, and every one of them at least legible.LEAST px on a 1080 px wide frame.

Where a caption stands is motion/studio/words.tsx and plan.ts laid out again (the card's line box in the type area, a
whole-frame photograph's words taking the end of the type area their anchor names, the line broken to fit at the
card's size, the camera settling from where they stood toward what the photograph looks at), and the title card's words
are motion/system/moves/closer/title-card.tsx's block between its closed bars: where either side sets its words, this
module sets them too. The words' scrim is a CSS gradient over the picture, so it darkens the encoded value
(linear=False).

The remedy goes on the beat, where words.tsx reads it: a label (or the hook's dates) that does not read in the card's
label color takes the line's color (`labelColor`); light words that still do not read deepen the beat's scrim
(`scrim`), up to legible.SCRIM_MOST under the words; the closer's `scrim` is a veil the film lays over the last
photograph under the title card's own matte. A black scrim never lifts dark words, so the check names those, anything
the deepest scrim leaves under, and every line under legible.LEAST px.
"""
import math
from functools import lru_cache
from pathlib import Path

import _env
import board_trip
import legible

# motion/studio/plan.ts: the moves that set the label or the line themselves
LABELS = {"date-stamp", "polaroid-drop", "sticker-pop"}
LINES = {"long-fade-title", "slam-words"}
# motion/studio/words.tsx: the title at TITLE times the card's line size, its dates at KICKER of it (or the label's
# size, the larger), a whole-frame line given ROOM of the type area's height, the label's line and DROP of its size
# above the line, the title's band of scrim BAND deep, and the words gone FADE beats before they leave
TITLE, KICKER, ROOM, DROP, BAND, FADE = 2.2, 0.75, 0.42, 0.45, 0.7, 0.6
# motion/system/moves/closer/title-card.tsx: the bars at the stop, the matte over the last still, the band under the
# closing line, the push, the handle's size, and the block's margins and gaps, px on a 1080 px frame
SHUT, MATTE, CARD_BAND, PUSH, HANDLE = 0.32, 0.6, 0.55, 0.035, 44
MARGIN, MOST, SAID, GAP_SAID, GAP_HANDLE = 100, 210, 64, 40, 50


def bezier(p):
    """The CSS cubic-bezier curve [x1, y1, x2, y2] as a function of progress."""
    x1, y1, x2, y2 = p
    at = lambda t, a, b: 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t * t * b + t ** 3

    def f(u):
        if u <= 0 or u >= 1:
            return float(u >= 1)
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if at(mid, x1, x2) < u else (lo, mid)
        return at((lo + hi) / 2, y1, y2)
    return f


@lru_cache(maxsize=None)
def _font(file, weight):
    from PIL import ImageFont
    path = _env.SKILL / file
    return _env.at_weight(ImageFont.truetype(str(path), 100), path, weight)


def width_of(face, size, text, tracking=None, weight=None):
    """The width a line takes set in `face` at `size`, its tracking included, as words.tsx measures it."""
    t = face["tracking"] if tracking is None else tracking
    return _font(face["file"], weight or face["weight"]).getlength(text) * size / 100 + t * size * len(text)


def cased(face, text):
    return text.upper() if face["case"] == "uppercase" else text.lower() if face["case"] == "lowercase" else text


def set_lines(face, text, most, width, lines, tall):
    """words.tsx setLines: the words broken into lines no wider than `width`, at the largest size from `most` down to half
    of it that takes at most `lines` lines within `tall`."""
    words = cased(face, text).split()
    size = most
    while True:
        out = []
        for w in words:
            if out and width_of(face, size, f"{out[-1]} {w}") <= width:
                out[-1] = f"{out[-1]} {w}"
            else:
                out.append(w)
        fits = len(out) <= lines and all(width_of(face, size, x) <= width for x in out) and len(out) * size * face["lineHeight"] <= tall
        if fits or size <= most / 2:
            return size, out
        size = math.floor(size * 0.94)


def balance(text, n):
    """title-card's break of `text` into at most `n` lines: the break whose longest line is shortest, then the most even,
    taken when its shortest line is half its longest or more."""
    ws = text.split()
    for k in range(min(max(n, 1), len(ws)), 1, -1):
        sets = []
        cuts = [[]]
        for _ in range(k - 1):
            cuts = [c + [i] for c in cuts for i in range((c[-1] if c else 0) + 1, len(ws))]
        for c in cuts:
            edges = [0, *c, len(ws)]
            sets.append([" ".join(ws[a:b]) for a, b in zip(edges, edges[1:])])
        score = lambda ls: (max(map(len, ls)), max(map(len, ls)) - min(map(len, ls)))
        best = min(sets, key=score)
        if min(map(len, best)) * 2 >= max(map(len, best)):
            return best
    return [" ".join(ws)]


def frame_of(board):
    """The frame's width, height and type area (the frame less the format's safe margins), as plan.ts takes them."""
    f = board["format"]
    W, H = f["width"], f["height"]
    s = board["system"]["safe"].get(f.get("name") or "reel") or board["system"]["safe"]["reel"]
    return W, H, [s["left"], s["top"], W - s["right"], H - s["bottom"]]


def within(of, share):
    a0, b0, a1, b1 = of
    x, y, w, h = share
    return [a0 + x * (a1 - a0), b0 + y * (b1 - b0), a0 + (x + w) * (a1 - a0), b0 + (y + h) * (b1 - b0)]


def shot_of(board, beat, stop, area):
    """plan.ts planOf for one beat: where its picture stands (frame px), whether that is the whole frame, and its line box."""
    W, H, _ = frame_of(board)
    lay = board["system"]["photo"]
    title = beat["form"] == "title"
    wide = not title and stop["aspect"] < 1 and H > W and lay.get("landscape")
    box, line = (lay["landscape"]["box"], lay["landscape"]["line"]) if wide else (lay["picture"]["box"], lay["line"]["box"])
    bx, by, bw, bh = box if not title and lay["picture"]["show"] else [0, 0, 1, 1]
    return [bx * W, by * H, (bx + bw) * W, (by + bh) * H], (bx, by, bw, bh) == (0, 0, 1, 1), within(area, line)


def place_of(board, beat, stop, box, u):
    """Where the whole photograph lies in the frame ([x, y, width, height] px) when the beat is `u` of its way through,
    the camera framing the box the way plan.ts cropAt does (the move's own nudge of a few percent left out)."""
    A = stop["aspect"]
    r = (box[3] - box[1]) / (box[2] - box[0])
    e = bezier(board["system"]["ease"]["move"])(u)
    peak = bool(beat.get("peak"))
    k = min(1.0, max(0.0, (1 if peak else 0.96) + ((0.8 if peak else 0.86) - (1 if peak else 0.96)) * e))
    cw = min(1.0, A / r) * k
    ch = cw * r
    s = 0.35 + 0.5 * e
    x = stop["near"][0] + (stop["far"][0] - stop["near"][0]) * s
    y = (stop["near"][1] + (stop["far"][1] - stop["near"][1]) * s) * A
    x, y = min(1 - cw / 2, max(cw / 2, x)), min(A - ch / 2, max(ch / 2, y))
    scale = (box[2] - box[0]) / cw
    return [box[0] - (x - cw / 2) * scale, box[1] - (y - ch / 2) * scale, scale, A * scale]


def _lines_box(face, size, lines, x0, x1, top, align):
    """The box a set of lines covers, frame px: each line's own width, set from the left or about the middle."""
    w = max(width_of(face, size, ln) for ln in lines)
    left = x0 if align != "center" else (x0 + x1) / 2 - w / 2
    return [left, top, left + w, top + len(lines) * size * face["lineHeight"]]


def _times(board, i, at, end):
    """The beats a stop's words are on from (once the cut in has played its half and a flown-in photograph has landed
    and settled; a title a beat later) to when they start to fade, as words.tsx times them."""
    beats, bpm = board["beats"], board["bpm"]
    b = beats[i]
    landed = (b["fly"] + board_trip.SETTLE) * bpm / 60 if b.get("fly") else 0.0
    nxt = beats[i + 1].get("transition") if i + 1 < len(beats) else None
    leave = end - max(0.5, board_trip.cut_beats(nxt) / 2) - FADE
    start = at + (max(1.0, landed) if b["form"] == "title" else max(0.25, board_trip.cut_beats(b.get("transition")) / 2, landed))
    return start, max(start, leave)


def captions(board):
    """Every caption of the board where the film sets it: one record per set of lines (a stop's label, its line, the
    hook's title, its dates, each of the title card's words) with its beat, its part, its text, its size (px), the color
    role the card gives it, the box it covers (frame px), what is under it (`under`: the photograph file and its place
    at each moment the words are measured, or None for words the film sets on the card's ground), the share of the
    beat's scrim that lies under it (`share`), the card's own scrim (`base`) and, for the closer, the matte over the
    picture under it (`dim`)."""
    W, H, area = frame_of(board)
    k = min(W, H) / 1080
    sys_, r, beats = board["system"], board["route"], board["beats"]
    lay = sys_["photo"]
    face = lambda which: sys_["display"] if which == "display" else sys_["text"]
    aw, ah = area[2] - area[0], area[3] - area[1]
    out, at, last = [], 0.0, None
    for i, b in enumerate(beats):
        start, end = at, at + 4 * b["bars"]
        at = end
        if b["form"] == "closer":
            if sys_["closer"] == "title-card" and last:
                out += _closer(board, b, *last)
            continue
        stop = r["stops"][b["stops"][0]]
        box, full, line = shot_of(board, b, stop, area)
        from_, leave = _times(board, i, start, end)
        moments = sorted({from_, (from_ + leave) / 2, leave})
        under = [(stop["photo"], place_of(board, b, stop, box, min(1.0, max(0.0, (t - start) / max(0.5, end - start)))))
                 for t in moments] if full else None
        last = (stop, box)
        move = b.get("move") or ""
        rec = lambda part, text, size, role, bx, share: {"beat": b, "part": part, "text": text, "size": size, "role": role,
                                                         "box": bx, "under": under, "share": share, "base": lay["line"]["scrim"]}
        if b["form"] == "title":
            if move in LABELS and move != "date-stamp":
                continue
            disp, text = sys_["display"], sys_["text"]
            ts, tl = set_lines(disp, r["title"], round(TITLE * lay["line"]["size"] * k), aw, 2, ah * 0.4)
            ks, kl = set_lines(text, r["kicker"], round(max(lay["label"]["size"], KICKER * lay["line"]["size"]) * k), aw, 1, ah * 0.2)
            tall = len(tl) * ts * disp["lineHeight"] + 0.5 * ks + ks * text["lineHeight"]
            anchor = b.get("anchor") or "bottom"
            top = area[1] + 0.06 * ah if anchor == "top" else area[1] + (ah - tall) / 2 if anchor == "middle" else line[3] - tall
            align = "center" if anchor == "middle" or lay["line"]["align"] == "center" else "start"
            band = lambda y: max(0.0, min(1.0, (lambda p: p / 0.35 if p < 0.35 else 1.0 if p <= 0.65 else (1 - p) / 0.35)(
                (y - top + H / 5) / (tall + 2 * H / 5))))
            tb = _lines_box(disp, ts, tl, area[0], area[2], top, align)
            kb = _lines_box(text, ks, kl, area[0], area[2], top + len(tl) * ts * disp["lineHeight"] + 0.5 * ks, align)
            out.append(rec("title", " ".join(tl), ts, lay["line"]["color"], tb, BAND * min(band(tb[1]), band(tb[3]))))
            out.append(rec("kicker", " ".join(kl), ks, lay["label"]["color"], kb, BAND * min(band(kb[1]), band(kb[3]))))
            continue
        lf, nf = face(lay["label"]["face"]), face(lay["line"]["face"])
        show_label = not (move in LABELS and move != "date-stamp") and move != "long-fade-title"
        show_line = move not in LINES and bool(b.get("words"))
        low = (line[1] + line[3]) / 2 > (area[1] + area[3]) / 2
        flip = full and ((b.get("anchor") == "top" and low) or (b.get("anchor") == "bottom" and not low))
        if flip:
            line = [line[0], max(area[1] + 0.06 * ah, area[1] + area[3] - line[3]), line[2], area[1] + area[3] - line[1]]
        up = (not low) if flip else low
        ls = round(lay["label"]["size"] * k)
        drop = ls * lf["lineHeight"] + DROP * ls if show_label else 0
        room = max(line[3] - line[1], ROOM * ah) if full else line[3] - line[1]
        size, lines = set_lines(nf, b.get("words") or "", round(lay["line"]["size"] * k), line[2] - line[0], 3, room - drop)
        tall = drop + (len(lines) * size * nf["lineHeight"] if show_line else 0)
        bh = line[3] - line[1]
        top = (line[1] + max(0, (bh - tall) / 2) if not full or not up else line[3] - max(tall, (bh + tall) / 2))
        if show_label:
            out.append(rec("label", cased(lf, stop["name"]), ls, lay["label"]["color"],
                           _lines_box(lf, ls, [cased(lf, stop["name"])], line[0], line[2], top, lay["line"]["align"]), 1.0))
        if show_line:
            out.append(rec("line", " ".join(lines), size, lay["line"]["color"],
                           _lines_box(nf, size, lines, line[0], line[2], top + drop, lay["line"]["align"]), 1.0))
    return out


def _closer(board, beat, stop, box):
    """title-card's words over the last photograph at the stop: the title in the display face's capitals fitted across
    the block's measure, the closing line under it on the band, the handle at the foot, in the ink the card's matte
    takes, the picture under them dimmed by the matte."""
    W, H, _ = frame_of(board)
    sys_, r = board["system"], board["route"]
    px = lambda v: v * W / 1080
    s = sys_["safe"].get(board["format"].get("name") or "reel") or sys_["safe"]["reel"]
    l0, r0 = max(px(MARGIN), s["left"]), min(W - px(MARGIN), W - s["right"])
    width = (r0 - l0) / (1 + PUSH)
    side = (l0 + r0) / 2 - width / 2
    disp, text = sys_["display"], sys_["text"]
    title = (r["title"] or r["signoff"]).upper()
    lines = balance(title, 2 if len(title) > 16 else 1)
    said = balance(r["signoff"], 2 if len(r["signoff"]) > 26 else 1) if r["title"] else []
    fit = lambda ls, f, w, tr=0.0: 100 * w / max(1.0, max(width_of(f, 100, ln, tracking=0, weight=400) + tr * 100 * max(0, len(ln) - 1) for ln in ls))
    said_size = min(px(SAID), fit(said, text, width * 0.9)) if said else 0
    hand_h = px(HANDLE) * 1.12 if r.get("handle") else 0
    rest = (px(GAP_SAID) + len(said) * said_size * 1.2 if said else 0) + (px(GAP_HANDLE) + hand_h if r.get("handle") else 0)
    room = H * (1 - 2 * SHUT) - 2 * px(40)
    size = min(fit(lines, disp, width, 0.14), px(MOST), (room - rest) / (len(lines) * 1.05))
    colors = {k: v for k, v in sys_["colors"].items() if k != "swatches"}
    matte, light = sys_["finish"]["matte"], sys_["finish"]["light"]
    matte = colors.get(matte, matte)
    lum_of = lambda h: (0.2126 * int(h[1:3], 16) + 0.7152 * int(h[3:5], 16) + 0.0722 * int(h[5:7], 16)) / 255
    ink = max([colors["paper"], light, colors["ink"]], key=lambda c: abs(lum_of(c) - lum_of(matte)))
    hand = light if lum_of(matte) < 0.4 else ink
    top = (H - (len(lines) * size * 1.05 + rest)) / 2
    said_top = top + len(lines) * size * 1.05 + px(GAP_SAID)
    hand_top = (said_top + len(said) * said_size * 1.2 if said else top + len(lines) * size * 1.05) + px(GAP_HANDLE)
    mid = (l0 + r0) / 2
    dy = H / 2 - (box[1] + box[3]) / 2
    under = [(stop["photo"], place_of(board, beat, stop, [box[0], box[1] + dy, box[2], box[3] + dy], 1.0))]
    gray = sum(int(matte[i:i + 2], 16) for i in (1, 3, 5)) / 765
    wide = lambda f, sz, ls, tr, wt=None: max(width_of(f, sz, ln, tracking=tr, weight=wt) for ln in ls)
    rec = lambda part, txt, sz, color, w, y, h, dim: {"beat": beat, "part": part, "text": txt, "size": round(sz), "role": color,
                                                      "box": [mid - w / 2, y, mid + w / 2, y + h], "under": under, "share": 1.0,
                                                      "base": 0.0, "dim": (dim, gray)}
    out = [rec("closer", " ".join(lines), size, ink, wide(disp, size, lines, 0.14, 400), top, len(lines) * size * 1.05, MATTE)]
    if said:
        out.append(rec("closer", " ".join(said), said_size, ink, wide(text, said_size, said, 0.0, 400), said_top,
                       len(said) * said_size * 1.2, 1 - (1 - MATTE) * (1 - CARD_BAND)))
    if r.get("handle"):
        out.append(rec("closer", r["handle"], px(HANDLE), hand, wide(text, px(HANDLE), [r["handle"]], 0.2, 400), hand_top, hand_h, MATTE))
    return out


def _grounds(board, c):
    """The quarters of the picture under a caption at each moment its words are measured; None for words on the card's
    ground. Raises FileNotFoundError when a photograph is not in the run's public/."""
    if not c["under"]:
        return None
    out = []
    for file, place in c["under"]:
        if not (Path(file) if Path(file).is_absolute() else Path("public") / file).exists():
            raise FileNotFoundError(file)
        q = legible.under(file, place, c["box"])
        if q is not None:
            out.append(q)
    return out or None


def _seen(c, q, s):
    """Quarters `q` as a caption's words see them: under a black scrim of `s` (a CSS gradient, so on the encoded value),
    and on the closer under the title card's matte, which the film draws over the veil."""
    a, g = c.get("dim") or (0.0, 0.0)
    return tuple(v * (1 - s) * (1 - a) + a * g for v in q)


def _contrast(c, color, q, s):
    return legible.contrast(color, _seen(c, q, s), 0.0, False)


def _light(c, color, q, s):
    """Whether words of `color` are lighter than the middle of what they see: a deeper scrim lifts only those."""
    return legible.lum(color) > legible.behind(_seen(c, q, s)[1], 0.0, False)


def _hex(board, role):
    return board["system"]["colors"].get(role, role)


def _role(c):
    """The color role the film sets a caption in: the beat's label color for a label and the hook's dates."""
    return (c["beat"].get("labelColor") or c["role"]) if c["part"] in ("label", "kicker") else c["role"]


def _scrim(c):
    """The scrim under a caption: the beat's (on the closer, its veil) or the card's, by the share of it that lies there."""
    s = c["beat"].get("scrim")
    return (c["base"] if s is None else s) * c["share"]


def _reads(board, c, qs, role=None):
    """A caption's contrast at its worst moment, the quarters it is read against then, and whether its type is light."""
    color = _hex(board, role or _role(c))
    got, q = min((_contrast(c, color, q, _scrim(c)), q) for q in qs)
    return got, q, _light(c, color, q, _scrim(c))


def remedy(board):
    """Each beat's remedy, on the beat: `labelColor` the line's color where the label's own does not read over the card's
    scrim, and `scrim` deep enough that every light caption on the beat reads, where the card's is not and a scrim up to
    SCRIM_MOST under the words is. A beat whose words read keeps the card's own; every draft and check measures the
    beats again, so a remedy never outlives the picture it was measured on."""
    W = frame_of(board)[0]
    line_role = board["system"]["photo"]["line"]["color"]
    for b in board["beats"]:
        b.pop("labelColor", None)
        b.pop("scrim", None)
    caps = captions(board)
    for b in board["beats"]:
        try:
            mine = [(c, _grounds(board, c)) for c in caps if c["beat"] is b]
        except FileNotFoundError:
            continue
        mine = [(c, qs) for c, qs in mine if qs]
        for c, qs in mine:
            if c["part"] in ("label", "kicker") and _reads(board, c, qs, c["role"])[0] < legible.need(c["size"], W):
                b["labelColor"] = line_role
        deepest = None
        for c, qs in mine:
            want = legible.need(c["size"], W)
            for q in qs:
                color = _hex(board, _role(c))
                if not _light(c, color, q, _scrim(c)) or _contrast(c, color, q, _scrim(c)) >= want:
                    continue
                s = _deepen(c, color, q, want)
                if s is not None:
                    deepest = max(deepest or 0.0, s)
        if deepest is not None:
            b["scrim"] = deepest


def _deepen(c, color, q, want):
    """The shallowest beat scrim from the card's up, in steps of 0.01, under which caption `c`'s light words of `color`
    read at `want` over quarters `q`, the caption's share of it lying under them; None when that takes more than
    legible.SCRIM_MOST under the words or more than the whole scrim."""
    s = math.ceil(round(c["base"] * 100, 6)) / 100
    while s <= 1 and s * c["share"] <= legible.SCRIM_MOST + 1e-9:
        if _contrast(c, color, q, s * c["share"]) >= want:
            return s
        s = round(s + 0.01, 2)
    return None


def findings(board):
    """Every caption the film sets that a phone does not show legibly, with the remedy on the board: words under the
    contrast their size needs over the picture under them, a line under legible.LEAST px, and words over a photograph
    the run's public/ does not hold."""
    W = frame_of(board)[0]
    out = []
    for c in captions(board):
        name = c["beat"]["id"]
        if c["size"] * 1080 / W < legible.LEAST:
            out.append(f'legible: {name}: "{c["text"]}" is set at {c["size"]:g} px, under the {legible.LEAST} px a phone shows '
                       "legibly: give its words more room")
        try:
            qs = _grounds(board, c)
        except FileNotFoundError as e:
            out.append(f"legible: {name}: its photograph {e.args[0]} is not in public/, so the words over it are not measured")
            continue
        if not qs:
            continue
        want = legible.need(c["size"], W)
        got, q, light = _reads(board, c, qs)
        if got >= want:
            continue
        fix = ("even the deepest scrim leaves it under: give the beat a photograph that is darker under its words" if light
               else "a scrim never lifts dark words: give the beat a photograph that is lighter under its words")
        out.append(f'legible: {name}: "{c["text"]}" reads {got:.1f}:1 over the photograph under it (scrim {_scrim(c):.2f}), '
                   f"under the {want:g}:1 a {c['size']:g} px line needs on a phone: {fix}")
    return out
