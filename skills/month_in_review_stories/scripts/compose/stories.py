"""The story cards: their month's moments told again as 15 s stories on the reel's system and in the month's look (its
colors, its type and its numbering), one card a moment in date order. Every card holds the moment's photograph on a
band of the frame, from under the plates of the title and the sign-off to above the moment's words, and no word stands
on it: the words sit on the ground above and below the band. The cards are drawn in the board's style: its faces, each in
its case and tracking, its colors, its easing and its finish.

  shot 1  the photograph is on its band from the card's first frame, in its color, so the card's first frame is its
          thumbnail, and the line rises across it from its foot to above its subject (the header names the series: <number> · my <month>, in <n> stories)
  shot 2  the camera moves in on the photograph's subject, framing its whole gesture with the band's foot, as the
          moment's day and their own caption land on a plate sized to the words, under the band
  shot 3  the whole card again: the line climbs on to the band's top
  shot 4  held whole, the handle (when their data carries one) signing the card off; the last card signs off with see
          you in <next month>

A moment with no photograph stands as big type on the shared ground instead: its count when the ask is for their
numbers, else its words; shot 2 moves in on that type. When the ask carries their numbers, each card's count stands
under its day on the plate and counts up from zero (`tally`). Each card's shot lengths follow its photograph and its
words (`lengths_of`): a busier photograph holds its close look longer, never more than CLOSE of the card, more words
hold the words' shot longer, and the last hold takes what is left, never more than HOLD of the card. `cards(month)`
returns (system, cards). Every place is frame px (1080x1920, y down), every time a beat of the board's pulse from the
card's start (`beats_of`: as many whole beats as a card's 15 s holds, the last shot running on to the card's end); each
card carries its shots (the
camera's framing per shot), what it draws, its sound cues and the beat its still is taken at. `bounds(card)` is the check that every line of
type sits wholly in view or wholly out of it wherever the camera holds, inside the safe area on a whole-frame hold, and
clear of every other line."""
import math

from .common import CARD, FPS, H, SAFE, W
from .month import Month, number
from . import look, style
from .reel import LABEL, LEADING, SPACE, big, busy_ratio, cover, label, legible, line, picture, plate, said_face, said_sizes, tally, wide, width, words_of

# a card's type stands INSET px inside the safe area's sides, so a hold's push in keeps every line inside it
INSET = 24
L0, R0 = SAFE["left"] + INSET, W - SAFE["right"] - INSET
# the camera's move into a shot runs from OUT beats before the shot's first beat to IN after it
OUT, IN = 0.35, 0.25
# the band a photograph fills: from HEAD, the foot of the title's and the sign-off's plates, to FOOT, the top of the
# plate under the moment's words, which a count row raises by ROW; and TOP, the height the line ends its climb at, its
# stroke clear of the plates above the band
HEAD, FOOT, TOP, ROW = 430, 1372, 436, 48
# the largest their words set under a card's band, px, so two rows stand inside the safe area
CAP = 50
# the most of a card, in beats, its last hold and its close look take, and the least any shot takes
HOLD, CLOSE, SHORT = 11, 8, 4
# the card's beats the shot lengths are set on: a 15 s card at 128 bpm
BASIS = 32
# how far about the photograph's subject its whole gesture reaches, px each way: the close look frames all of it
REACH = (400, 430)


def r1(x):
    return round(x, 1)


def view(cx, cy, h, yaw=0.0, pitch=0.0, roll=0.0):
    return {"c": [r1(cx), r1(cy)], "h": r1(h), "yaw": yaw, "pitch": pitch, "roll": roll}


WHOLE = view(W / 2, H / 2, H)


def track(*pts):
    """A value over beats: [beat, value, ease] points, the ease ("settle" or "smooth") the way the value
    travels from the point before."""
    return [[round(a, 3), round(v, 2), e] for a, v, *rest in pts for e in [rest[0] if rest else "smooth"]]


def beats_of(m):
    """A card's whole beats in the board's pulse: as many as its 15 s holds."""
    return math.floor(CARD * m.bpm / (FPS * 60))


def timed(ln, at, out=None, shadow=None):
    d = {**ln, "at": round(at, 3)}
    if out is not None:
        d["out"] = round(out, 3)
    if shadow:
        d["shadow"] = shadow
    return d


def box_of(ln):
    """The line's box [x0, y0, x1, y1] in frame px: its advance width from the font file, its cap height above the
    baseline and its descender below."""
    w = width(ln["text"], ln["size"], ln["file"], ln.get("tracking", 0.0))
    x = ln["x"] - (w if ln.get("anchor") == "end" else w / 2 if ln.get("anchor") == "middle" else 0)
    return [x, ln["y"] - 0.74 * ln["size"], x + w, ln["y"] + 0.22 * ln["size"]]


def band(pic, rect, **kw):
    rect = [r1(v) for v in rect]
    d = {"file": pic["file"] if pic else None, "rect": rect, "place": cover(pic["size"], pic["focus"], rect)[0] if pic else [0, 0, W, H]}
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


def starts(lengths):
    out, a = [], 0
    for n in lengths:
        out.append(a)
        a += n
    return out


def held(sh):
    """The framing a shot's hold ends on: its `to`, or its view pushed in by `push`."""
    if sh.get("to"):
        return sh["to"]
    v = sh["view"]
    return {**v, "h": r1(v["h"] * (1 - sh.get("push", 0.04)))}


def rect_of(v):
    hw, hh = v["h"] * W / H / 2, v["h"] / 2
    return [v["c"][0] - hw, v["c"][1] - hh, v["c"][0] + hw, v["c"][1] + hh]


def inside(b, r, m=0.0):
    return b[0] >= r[0] + m and b[1] >= r[1] + m and b[2] <= r[2] - m and b[3] <= r[3] - m


def apart(b, r):
    return b[2] <= r[0] or b[0] >= r[2] or b[3] <= r[1] or b[1] >= r[3]


def safe_of(v):
    """The part of framing `v` that lands inside the frame's safe area on screen."""
    r, k = rect_of(v), v["h"] / H
    return [r[0] + SAFE["left"] * k, r[1] + SAFE["top"] * k, r[2] - SAFE["right"] * k, r[3] - SAFE["bottom"] * k]


def frame_on(box, keep=(), during=None, within=(0, 0, W, H)):
    """The tightest framing at the frame's aspect that holds `box`, and every line in `keep` on screen `during` ([from,
    to] beats), inside its safe area (a line wholly out of view stays out), kept inside `within`."""
    box = list(box)
    wx0, wy0, wx1, wy1 = within
    if during:
        keep = [ln for ln in keep if visible(ln, *during)]
    most = min(wy1 - wy0, (wx1 - wx0) * H / W)
    grow = 1.0
    for _ in range(24):
        vh = min(most, grow * max(760, (box[2] - box[0]) * H / (W - SAFE["left"] - SAFE["right"]),
                                   (box[3] - box[1]) * H / (H - SAFE["top"] - SAFE["bottom"])))
        k, vw = vh / H, vh * W / H
        # the box in the middle of the safe area, which sits (top - bottom) / 2 above the frame's middle
        cx = min(wx1 - vw / 2, max(wx0 + vw / 2, (box[0] + box[2]) / 2 + (SAFE["right"] - SAFE["left"]) * k / 2))
        cy = min(wy1 - vh / 2, max(wy0 + vh / 2, (box[1] + box[3]) / 2 + (SAFE["bottom"] - SAFE["top"]) * k / 2))
        v = view(cx, cy, vh)
        sa, r = safe_of(v), rect_of(v)
        if not inside(box, sa):
            if vh >= most:
                return v
            grow *= 1.04
            continue
        cut = [b for b in (box_of(ln) for ln in keep) if not inside(b, sa) and not apart(b, r)]
        if not cut:
            return v
        box = [min([box[0]] + [b[0] for b in cut]), min([box[1]] + [b[1] for b in cut]),
               max([box[2]] + [b[2] for b in cut]), max([box[3]] + [b[3] for b in cut])]
    return v


def shot(beats, v, reveals, push=0.04, to=None, arc=None):
    d = {"beats": beats, "view": v, "push": push, "reveals": reveals}
    if to:
        d["to"] = to
    if arc is not None:
        d["arc"] = arc
    return d


def cue(kind, at, what, **kw):
    return {"kind": kind, "at": round(at, 3), "what": what, **{k: v for k, v in kw.items() if v is not None}}


def make(cid, idea, shots, still, beats, **parts):
    card = {"id": cid, "frames": CARD, "idea": idea, "shots": shots, "still": still, "move": [OUT, IN], "bank": parts.pop("bank", 1.0)}
    for k in ("bands", "rules", "strips", "lines", "bursts"):
        card[k] = parts.get(k) or []
    card["sound"] = sorted(parts.get("sound", []), key=lambda c: c["at"])
    total = sum(s["beats"] for s in shots)
    if total != beats:
        raise ValueError(f"card {cid}: its shots run {total} beats, a card is {beats}")
    return card


def fit_size(m, text, size, limit, kind="text"):
    return min(size, math.floor(limit / max(1e-6, wide(m, text, 1, kind))))


def shots_of(m, p):
    """One card's four shot lengths in whole beats, summing to a card: the slide in and the rise (a beat longer for the
    peak, whose rise is longer), the close look (longer on a busier photograph), the words (longer for more of them),
    and the last hold, what is left, between SHORT and HOLD and shorter on a busier photograph; the longest shot runs at least twice the shortest and a
    quarter over the card's median, so every card holds somewhere. The lengths are set on a card of BASIS beats and
    spread over the card's own beats (`spread`), so a faster pulse lengthens every shot alike."""
    words, busy, beats = len(p.said.split()), busy_ratio(m, p), BASIS
    s = [3 + round(2 * min(1.0, busy)) + (p is m.peak), min(CLOSE, max(SHORT, round(2 + 4 * busy))), min(9, max(SHORT, round(2 + 0.4 * words)))]
    s.append(beats - sum(s))
    # a calm photograph holds longer at the end than a busy one; what the last hold cannot take goes to the close look,
    # then the words, then the slide in
    hold = min(HOLD, max(7, round(HOLD + 1.5 - 3 * busy)))
    for k, most in ((1, CLOSE), (2, 10), (0, 8)):
        while s[3] > hold and s[k] < most:
            s[k] += 1
            s[3] -= 1
    while s[3] < SHORT + 1:
        k = max(range(3), key=lambda k: s[k])
        s[k] -= 1
        s[3] += 1
    holds(s, hold, CLOSE)
    n = beats_of(m)
    return holds(spread(s, n), round(hold * n / BASIS), round(CLOSE * n / BASIS))


def holds(s, hold, close):
    """Shot lengths moved a beat at a time, from the shortest to the longest that may grow (the last hold up to `hold`,
    the close look up to `close`), until the longest runs at least twice the shortest and a quarter over the median."""
    while max(s) < 2 * min(s) or max(s) < 1.25 * (sorted(s)[1] + sorted(s)[2]) / 2:
        up = max((k for k in range(4) if (k != 3 or s[3] < hold) and (k != 1 or s[1] < close)), key=lambda k: s[k])
        down = min((k for k in range(4) if k != up and s[k] > SHORT), key=lambda k: s[k])
        s[up] += 1
        s[down] -= 1
    return s


def spread(s, beats):
    """Shot lengths set on a card of BASIS beats over a card of `beats`: each but the last scaled and rounded, at least
    SHORT, and the last hold what is left."""
    t = [max(SHORT, round(x * beats / BASIS)) for x in s[:3]]
    return t + [beats - sum(t)]


def lengths_of(m):
    """Each card's shot lengths (shots_of)."""
    return [shots_of(m, p) for p in m.moments]


def moment(m, i, p, pic, lengths):
    """Moment i's card: its photograph, the line rising across it to above its subject, the subject's whole gesture up
    close as their words land under it, then the whole photograph as the line climbs on, signed off with the handle."""
    n = len(m.moments)
    last, peak = i == n - 1, p is m.peak
    s = starts(lengths)
    counted = m.counted and p.counted
    counts = [p.count()] if counted and pic else []
    foot = FOOT - ROW * len(counts)
    # the photograph's band, between the plates above it and the plate under it
    rect = [0, HEAD, W, foot] if pic else [0, 0, W, H]
    _, (sx, sy) = cover(pic["size"], pic["focus"], rect) if pic else ([0, 0, W, H], (W / 2, H / 2))
    # with no photograph the frame is big type, and its count or its words are said there, never again under it; the
    # type is up from the card's first frames, where a photograph would be sliding in, so the card never opens on bare ground
    a, rise = s[0] + 0.9, 2.4 if peak else 2.0
    typeset = [timed(x, s[0] + 0.1 + 0.1 * j) for j, x in enumerate(big(m, p, 470, foot - 80, R0 - L0, L0))] if not pic else []
    for x in typeset:
        if x["color"] == "line" and counted:
            x["tally"] = tally(x["at"], s[1] - x["at"])
    y_sub = r1(min(1100, max(520, sy - 260))) if pic else r1(max(440, min(box_of(x)[1] for x in typeset) - 40))
    b0, b1 = s[2] + 0.2, s[2] + 1.4
    lit = track([0, foot], [a, foot], [a + rise, y_sub, "settle"], [b0, y_sub], [b1, TOP, "settle"])
    # every card carries the same header, its number and the series' one line, so the cards read as one set
    title = f"{look.numbered(m.numbering, i + 1, n)} · my {m.name}, in {number(n)} stories"
    t_size = fit_size(m, title, 36, R0 - L0)
    out1 = s[1] - OUT - 0.1
    head = line(m, title, L0, 318, t_size)
    lines = [timed(head, 0.4, out=out1)]
    strips = [{"rect": plate([head], 262, 346), "at": 0.3, "len": 0.5, "out": out1}]
    # under the band the day in the text face, then their words in the card's photo line face, as the card captions a photograph
    small = label(m, p, LABEL, R0 - L0)
    size = min(CAP, said_sizes(m)[1])
    cap = [] if typeset and not counted else words_of(m, p, size, R0 - L0)
    day_y = foot + 36
    under = [timed(line(m, small, L0, day_y, LABEL, color="ink"), s[1] + 0.45)]
    under += [timed(line(m, x, L0, day_y + ROW * (j + 1), 40, color=legible(m), name="count"), s[1] + 0.55) for j, x in enumerate(counts)]
    first = day_y + ROW * len(counts) + SPACE + size
    under += [timed(line(m, x, L0, first + round(LEADING * size) * j, size, face_=said_face(m)), s[1] + 0.6 + 0.15 * j) for j, x in enumerate(cap)]
    # a count counts up from zero from the beat it lands to a beat into the last hold
    for x in under:
        if x.get("name") == "count":
            x["tally"] = tally(x["at"], s[3] + 1 - x["at"])
    lines += [timed(head, s[2] + 0.3)] + under + typeset
    strips += [{"rect": plate([head], 262, 346), "at": s[2] + 0.2, "len": 0.5},
               {"rect": plate(under, foot, max(x["y"] + 0.22 * x["size"] for x in under) + 28), "at": s[1] + 0.3, "len": 0.5}]
    # a sound where the line lands above its subject (the peak's built into and landing as an impact) and where it reaches the top
    sound = ([cue("riser", a, f"the build into {p.name}, the month's peak", beats=rise), cue("impact", a + rise, f"the line lands above {p.name}, the month's peak")]
             if peak else [cue("hit", a + rise, f"the line lands above {p.name}", weight=0.85, bright=0.4)])
    sound.append(cue("hit", b1, "the line reaches the top", weight=0.6, bright=0.35))
    end = f"{m.short} {p.day} held whole"
    # every card signs off with the handle; the last says see you in the next month with it
    sign = "  ·  ".join([f"see you in {m.next.name}."] + ([m.handle] if m.handle else [])) if last else m.handle
    if sign:
        sl = line(m, sign, L0, 404, fit_size(m, sign, 34, R0 - L0), color="line")
        lines.append(timed(sl, s[3] + 0.4))
        strips.append({"rect": plate([sl], 346, 430), "at": s[3] + 0.3, "len": 0.5})
        end += f", and see you in {m.next.name}" if last else f", signed {m.handle}"
    # the close look: the subject's whole gesture and the words landing under the band, in one framing
    gesture = box_of(typeset[0]) if typeset else [max(0, sx - REACH[0]), max(rect[1], sy - REACH[1]), min(W, sx + REACH[0]), min(rect[3], sy + REACH[1])]
    words_box = [min(b[0] for b in map(box_of, under)), min(b[1] for b in map(box_of, under)), max(b[2] for b in map(box_of, under)), max(b[3] for b in map(box_of, under))]
    held_box = [min(gesture[0], words_box[0]), gesture[1], max(gesture[2], words_box[2]), max(gesture[3], words_box[3])]
    close = frame_on(held_box, keep=lines, during=[s[1], s[2]])
    # the camera moves in to that framing over the shot, from a little wider
    wide = min(H, close["h"] * 1.06)
    ww = wide * W / H
    start = view(min(W - ww / 2, max(ww / 2, close["c"][0])), min(H - wide / 2, max(wide / 2, close["c"][1])), wide)
    said = " / ".join(x["text"] for x in typeset)
    shots = [shot(lengths[0], WHOLE, f"{m.short} {p.day}, {p.name}: " + (f"{said} lands in big type on the ground, the line rising to above it"
                  if typeset else "the photograph on its band from the first frame, the line rising across it to above its subject"), arc=-0.06),
             shot(lengths[1], start, f"{p.name} up close: the camera moves in on " + (f"'{typeset[0]['text']}'" if typeset else "the subject's whole gesture")
                  + ", their words landing under it: " + (" ".join(cap) if cap else small), to=close),
             shot(lengths[2], WHOLE, "the whole photograph again, the line climbing on to its top", arc=-0.06),
             shot(lengths[3], WHOLE, end, push=0.05, arc=-0.06)]
    band_ = band(pic, rect)
    n_beats = beats_of(m)
    return make(f"story-{i + 1}", f"{m.short} {p.day}: {p.name}", shots, still=n_beats - 1.0, beats=n_beats, bank=0.0, bands=[band_],
                rules=[{"x0": 0, "x1": W, "y": lit, "at": a - 0.3, "color": "line"}], lines=lines, strips=strips,
                bursts=[{"at": round(a + rise, 3), "x0": 0, "x1": W, "y": y_sub, "big": peak}], sound=sound)


def system(m):
    """The design system both films are drawn in: the style card's (style.system) with the frame's safe area."""
    return {**style.system(m.card, m.colors), "safe": dict(SAFE)}


def cards(month):
    m = month if isinstance(month, Month) else Month(month)
    lengths = lengths_of(m)
    return system(m), [moment(m, i, p, picture(p, f"photos/moment-{i + 1}.jpg"), lengths[i]) for i, p in enumerate(m.moments)]


def visible(ln, a, b):
    return ln["at"] < b and ("out" not in ln or ln["out"] > a)


def bounds(card):
    """What a card's camera does to its type: a line it cuts where it holds, a line outside the safe area on a whole-frame
    hold, and two lines on screen together that overlap."""
    bad = []
    s = starts([x["beats"] for x in card["shots"]])
    e = s[1:] + [sum(x["beats"] for x in card["shots"])]
    text = card["lines"]
    for i, sh in enumerate(card["shots"]):
        a, b = (s[i] + IN if i else 0), e[i] - (OUT if i + 1 < len(s) else 0)
        for v, t in ((sh["view"], a), (held(sh), b)):
            r = rect_of(v)
            sa = [x + d for x, d in zip(safe_of(v), (-2, -2, 2, 2))]
            for ln in text:
                if not visible(ln, t - 0.01, t + 0.01) or ln["at"] > t:
                    continue
                bx = box_of(ln)
                if apart(bx, r):
                    continue
                if not inside(bx, r):
                    bad.append(f"{card['id']} shot {i}: the camera cuts '{ln['text']}'")
                elif not inside(bx, sa):
                    bad.append(f"{card['id']} shot {i}: '{ln['text']}' stands outside the safe area")
        for x, p in enumerate(text):
            for q in text[x + 1:]:
                if visible(p, a, b) and visible(q, a, b) and p.get("z", 60) == q.get("z", 60) and not apart(box_of(p), box_of(q)):
                    bad.append(f"{card['id']} shot {i}: '{p['text']}' and '{q['text']}' overlap")
    return sorted(set(bad))
