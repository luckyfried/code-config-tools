"""drive: the cut. A count beat cuts its post's photograph with one straight edge laid along the photograph's own
strongest line (picks.json `line`; level when it has none): a flat field above the edge (the paper, or the accent
where the picture under the edge is the paper's colour), the picture below it, running off the frame. The count
stands on the edge, turned to its angle, its size the square root of its share of the top post's likes, with the rank
and the caption small on the same baseline. The edge is what carries across every cut: it pivots from one
photograph's line to the next. The hook is the year's total counting up on a level edge over the top photograph; the
total breaks into the nine counts, and the counts run down from the lowest rank to the top post. The dense beat is the nine as bars in a panel whose lower edge is cut along the last photograph's line;
the closer cuts the nine along parallel edges at the angle the top post's line gives (the last beat's angle when it
has none), each slice laid by its own photograph's line: the top post across the foot of the frame under its count,
the eight in rows above it, each count hanging under its own slice.

The film is one camera travelling the closer's wall: every count beat is a card that lands in its slice's place, and
the storyboard says per beat what the move reveals and what it carries across the cut, the sound each move makes
(`sound`, placed at named beats for music.py), and the generated clips that would carry the wall's world (`clips`)."""
import math

from bounds import SHOWN, crossing, shown
from compose import fit_size, hull, photo, pixels, system, text_box, text_width, turned, wrap_measured

BPM = 120
COND = {"wdth": 62, "wght": 800}
# the edge runs this many px under a count's baseline
LIFT = 6
# an edge turns at most TILT degrees, and rises across the frame by at most RISE of the frame's height
TILT = 25
RISE = 0.3
# where the edge crosses the frame's middle column, px: on the hook and on a count beat
EDGE = {"reel": {"hook": 900, "count": 860}, "square": {"hook": 640, "count": 620}, "wide": {"hook": 660, "count": 640}}
# the top post's count, the year's total and the small type, px, in each format; the counts on bars and squares
HERO = {"reel": 360, "square": 320, "wide": 330}
TOTAL = {"reel": 440, "square": 400, "wide": 420}
SMALL = {"reel": 34, "square": 30, "wide": 32}
LABEL = 44
# small type's descenders reach this share of its size under the baseline; a caption is raised by it off the edge
DESCENT = 0.25
# a photograph is enlarged up to this much past filling the frame so that its line lands on the edge
REACH = 1.8
# the musical beats each shot runs: the hook a bar, held; the bars a bar, held after the run; the closer two bars, held to
# the end; a count beat's moves are laid for COUNT_PACE beats and quicken in a shorter one. Nine posts make eleven bars,
# inside the fifteen to thirty seconds a reel runs from 88 to 176 bpm, so snap finds a multiple of any heard tempo.
HOOK_BEATS, NINE_BEATS, CLOSER_BEATS, COUNT_PACE = 4, 4, 8, 3
# the closer: its slices per row in each format, its counts' size for the top post in each, the field between
# slices and between a row's type and the next row, how far an outer slice runs off the frame, the most its edges turn
# when they carry the last beat's angle; bounds.SHOWN is the least a slice shows on its short side
ACROSS = {"reel": 4, "square": 4, "wide": 8}
CHIP = {"reel": 120, "square": 96, "wide": 100}
GUT = 14
GAP = 18
BLEED = 20
LEAN = 12
# the colour distance (CIE76) under which the picture just under an edge reads as the field over it
MERGE = 30
# the beat the year's total lands on, counted up from the blade opening the top photograph
COUNT_UP = 2.0


def figure(n):
    """A count as drive sets it: thousands grouped by a narrow space, so nothing hangs under the edge it stands on."""
    return f"{n:,}".replace(",", "\u202f")


def sys_():
    return system("kinetic", {"bg": "#f2ece2", "ink": "#16120f", "accent": "#d8431d", "accent2": "#d8431d", "muted": "#8c8279", "paper": "#f2ece2"},
                  display={"family": "Archivo", "file": "fonts/Archivo/Archivo[wdth,wght].ttf", "weight": 800, "case": "none", "axes": COND},
                  texture={"grain": 0.04})


class Edge:
    """A straight edge across the frame through the middle column at `yc` px, turned `tilt` degrees (negative rises to
    the right); `yl` and `yr` are where it meets the frame's left and right sides."""

    def __init__(self, frame, yc, tilt):
        self.W, self.yc, self.tilt = frame.W, yc, tilt
        t = math.tan(math.radians(tilt))
        self.yl, self.yr = yc - t * frame.W / 2, yc + t * frame.W / 2

    def y(self, x):
        return self.yl + (self.yr - self.yl) * x / self.W

    @property
    def line(self):
        return [round(self.yl, 1), round(self.yr, 1)]


def tilt_of(p, frame):
    """The angle, in degrees, of the photograph's own line as the frame draws it (an even scale keeps angles), held
    inside the turn the format allows; 0 when the photograph has no line."""
    ln = p.get("line")
    if not ln:
        return 0.0
    u0, v0, u1, v1 = ln if ln[0] <= ln[2] else ln[2:] + ln[:2]
    a = math.degrees(math.atan2((v1 - v0) * p["aspect"], max(1e-6, u1 - u0)))
    lim = min(TILT, math.degrees(math.atan(RISE * frame.H / frame.W)))
    return round(max(-lim, min(lim, a)), 2)


def place(frame, p, edge, box=None):
    """The px box the whole photograph is laid in so it fills `box` (x0, y0, x1, y1; the frame under the edge when
    absent): centred on its focus across, and up or down, enlarged by up to REACH, so the middle of its own line lies
    on the edge; with no line, or a line the box does not show, its focus sits in the middle of the box."""
    x0, y0, x1, y1 = box or (0, min(edge.yl, edge.yr), frame.W, frame.H)
    a = p["aspect"]
    least = max(x1 - x0, (y1 - y0) / a)
    ln = p.get("line")
    um, vm = ((ln[0] + ln[2]) / 2, (ln[1] + ln[3]) / 2) if ln else (None, None)

    def across(iw):
        """At width `iw` px: the photograph's left side, and the column its line's middle falls on (None when it
        falls outside the box)."""
        ix = max(x1 - iw, min(x0, (x0 + x1) / 2 - p["focus"][0] * iw))
        x = ix + um * iw if ln else None
        return ix, (x if x is not None and x0 <= x <= x1 else None)

    iw = least
    for _ in range(3):
        x = across(iw)[1]
        if x is None or not 0.02 < vm < 0.98:
            break
        y = edge.y(x)
        # the line's middle on the edge needs the picture to reach the box's foot under it and its head over it
        iw = min(least * REACH, max(least, (y1 - y) / (1 - vm) / a, (y - y0) / vm / a))
    ih = iw * a
    ix, x = across(iw)
    iy = edge.y(x) - vm * ih if x is not None and 0.02 < vm < 0.98 else (y0 + y1) / 2 - p["focus"][1] * ih
    iy = max(y1 - ih, min(y0, iy))
    return [round(ix, 1), round(iy, 1), round(iw, 1), round(ih, 1)]


def lab(rgb):
    """An sRGB colour (0 to 255 per channel) in CIE L*a*b*."""
    r, g, b = (((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in rgb)
    x, y, z = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.9505, r * 0.2126 + g * 0.7152 + b * 0.0722, (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.089
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def field_for(S, frame, p, edge):
    """The field a count beat lays over its photograph: the paper, or the accent when the picture the frame shows just
    under the edge is so near the paper's colour that the edge would not read."""
    im = pixels(p["file"]) if p.get("file") else None
    if im is None:
        return "paper"
    x, y, w, h = place(frame, p, edge)
    iw, ih = im.size
    hexc = S["colors"]["paper"].lstrip("#")
    ref = lab(tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4)))
    far = []
    for X in range(0, frame.W, 12):
        for dy in range(8, 64, 8):
            u, v = (X - x) / w, (edge.y(X) + dy - y) / h
            if 0 <= u < 1 and 0 <= v < 1:
                far.append(math.dist(lab(im.getpixel((int(u * iw), int(v * ih)))), ref))
    return "accent" if far and sorted(far)[len(far) // 2] < MERGE else "paper"


def rested(L, frame):
    """The px box a Cut's photograph has come to as its shot ends, pushed in about the middle of its edge."""
    k = 1 + L.get("push", 0.04)
    x, y, w, h = L["place"]
    cx, cy = frame.W / 2, sum(L["line"]) / 2
    return [round(cx + (x - cx) * k, 1), round(cy + (y - cy) * k, 1), round(w * k, 1), round(h * k, 1)]


def cut(frame, p, edge, field, before=None, at=0):
    """The Cut layer: the field over the edge, the photograph under it, pivoting from the edge `before` it."""
    L = {"kind": "Cut", "at": at, "line": edge.line, "field": field, "beats": 0.5}
    if before:
        L["from"] = before.line
    if p:
        L["photo"] = photo(p)
        L["place"] = place(frame, p, edge)
    return L


def fits(S, frame, lines, edge):
    """Every line inside the safe area and on the field's side of the edge."""
    x0, y0, x1, y1 = frame.safe
    for ln in lines:
        e = hull(turned(text_box(S, ln), ln))
        if e[0] < x0 or e[1] < y0 or e[2] > x1 or e[3] > y1:
            return False
        if any(y > edge.y(x) for x, y in turned(text_box(S, ln, ink=True), ln)):
            return False
    return True


def count_lines(S, frame, p, top, edge, k, mark="accent"):
    """A post's count standing on the edge at `k` times its size, with its rank (in `mark`) and caption on the same
    baseline to its right, or over it when the caption has no room there."""
    small = SMALL[frame.name]
    size = max(40, round(HERO[frame.name] * math.sqrt(p["likes"] / top) * k))
    cos = math.cos(math.radians(edge.tilt))
    x0 = frame.left + 2
    for _ in range(2):
        base = edge.y(x0) - LIFT
        piv = [round(x0, 1), round(base, 1)]
        turn = {"rotate": edge.tilt, "pivot": piv}
        num = {"text": figure(p['likes']), "x": x0, "y": base, "size": size, "face": "display", "axes": COND, "tracking": -0.02, "color": "ink",
               "name": f"count-{p['rank']}", **turn}
        left = hull(turned(text_box(S, num), num))[0]
        if left >= frame.left:
            break
        x0 += (frame.left - left) + 1
    nw = text_width(S, num)
    gap = max(18, round(size * 0.07))
    cap = {"size": small, "face": "text", "weight": 500, "tracking": 0.0, "color": "ink"}
    room = (frame.W - frame.right - x0) / cos - nw - gap - 6
    lines = wrap_measured(S, dict(cap, text=p["caption"]), room) if p.get("caption") and room >= 6 * small else None
    if lines is not None or not p.get("caption"):
        cx, bottom = x0 + nw + gap, base - round(small * DESCENT)
    else:
        room = (frame.W - frame.right - x0) / cos - 6
        lines = wrap_measured(S, dict(cap, text=p["caption"]), room) or [p["caption"]]
        cx, bottom = x0 + 4, base - size * 0.74 - small * 0.9
    lines = lines or []
    out = [num]
    for i, t in enumerate(reversed(lines)):
        out.append(dict(cap, text=t, x=round(cx, 1), y=round(bottom - i * small * 1.25, 1), name=f"caption-{p['rank']}-{len(lines) - 1 - i}", **turn))
    out.append({"text": f"no. {p['rank']}", "x": round(cx, 1), "y": round(bottom - len(lines) * small * 1.25, 1), "size": small, "face": "text",
                "weight": 800, "tracking": 0.02, "color": mark, "name": f"rank-{p['rank']}", **turn})
    return out


def run_beats(n):
    """The beats each of `n` count beats runs, in film order (the countdown, the lowest rank first): three each, so the
    photograph holds before the blade and the count stands after it, the top post four and whatever fills the last bar."""
    out = [3] * n
    out[-1] = 4
    out[-1] += -sum(out) % 4
    return out


def rolls(i, n):
    """Whether the `i`th count beat of `n` in film order rolls its count up: the first two and the last three."""
    return i < 2 or i >= n - 3


def paced(layers, k):
    """The layers with every time in them (start, length, step) scaled by `k`."""
    return [dict(L, **{key: round(L[key] * k, 3) for key in ("at", "beats", "step") if key in L}) for L in layers]


def placed(layers, t):
    """The layers with their start times counted from the film's start, for a shot that starts at beat `t`."""
    return [dict(L, at=round(L.get("at", 0) + t, 4)) for L in layers]


def count_beat(S, frame, p, top, before):
    """A post's count beat: its photograph cut along its own line, its count on the edge, the field the paper unless
    the picture under the edge would merge with it."""
    edge = Edge(frame, EDGE[frame.name]["count"], tilt_of(p, frame))
    field = field_for(S, frame, p, edge)
    mark = "paper" if field == "accent" else "accent"
    k = 1.0
    lines = count_lines(S, frame, p, top, edge, k, mark)
    while not fits(S, frame, lines, edge) and lines[0]["size"] > 40:
        k *= 0.95
        lines = count_lines(S, frame, p, top, edge, k, mark)
    num, rest = lines[:1], lines[1:]
    return edge, [cut(frame, p, edge, field, before),
                  {"kind": "Words", "at": 0.25, "lines": num, "beats": 0.5},
                  {"kind": "Words", "at": 0.5, "lines": rest[::-1], "beats": 0.4, "step": 0.08}]


def hook(S, frame, p, words, handle, year, total):
    """The year's total counting up through the bar on a level edge over the top photograph, the handle and one line
    over it."""
    edge = Edge(frame, EDGE[frame.name]["hook"], 0)
    small = SMALL[frame.name]
    x = frame.left + 2
    kicker = {"text": f"{handle} · {year}", "x": x, "y": round(frame.top + small * 1.3), "size": small, "face": "text", "weight": 600, "tracking": 0.02,
              "color": "ink"}
    line = {"text": words["total"], "x": x, "y": round(kicker["y"] + small * 1.9), "size": round(small * 1.4), "face": "text", "weight": 600,
            "tracking": 0.0, "color": "ink"}
    line["size"] = fit_size(S, line, frame.W - frame.right - x)
    num = {"text": figure(total), "x": x, "y": round(edge.yc - LIFT), "size": TOTAL[frame.name], "face": "display", "axes": COND, "tracking": -0.03,
           "color": "ink", "name": "count-total"}
    num["size"] = fit_size(S, num, frame.W - frame.right - x - 4)
    while num["size"] > 40 and text_box(S, num, ink=True)[1] < line["y"] + small * 1.5:
        num["size"] -= 4
    num["count"] = [0, total, COUNT_UP]
    return edge, [cut(frame, p, edge, "accent", at=-4),
                  {"kind": "Words", "at": 0, "lines": [kicker, line], "beats": 0.5, "step": 0.15},
                  {"kind": "Words", "at": 0.25, "lines": [num], "beats": 0.5}]


def nine(S, frame, posts, words, before):
    """The nine as bars in rank order on the field, each its share of the top post's likes with its count at its end,
    the panel's lower edge cut along the last photograph's line, that photograph under it."""
    small = SMALL[frame.name]
    x0 = frame.left + 2
    top = posts[0]["likes"]
    head = {"text": words["head"], "x": x0, "y": round(frame.top + small * 1.3), "size": small, "face": "text", "weight": 600, "tracking": 0.0,
            "color": "ink"}
    head["size"] = fit_size(S, head, frame.W - frame.right - x0)
    y0 = head["y"] + small * 1.6
    pitch = min(68, (frame.H * 0.62 - y0) / len(posts))
    bh = round(pitch * 0.68)
    lab = {"size": LABEL, "face": "display", "axes": COND, "tracking": -0.01, "color": "ink"}
    longest = frame.W - frame.right - x0 - text_width(S, dict(lab, text=figure(top))) - 22
    bars, labels = [], []
    for i, p in enumerate(posts):
        y = round(y0 + i * pitch, 1)
        w = round(max(bh, longest * p["likes"] / top), 1)
        bars.append([x0, y, w, bh])
        labels.append(dict(lab, text=figure(p['likes']), x=round(x0 + w + 14, 1), y=round(y + bh / 2 + LABEL * 0.36, 1), name=f"count-{p['rank']}"))
    bottom = y0 + (len(posts) - 1) * pitch + bh
    tilt = tilt_of(posts[-1], frame)
    t = math.tan(math.radians(tilt))
    xm = frame.W - frame.right if t < 0 else frame.left
    edge = Edge(frame, bottom + 44 - t * (xm - frame.W / 2), tilt)
    return edge, [cut(frame, posts[-1], edge, "accent", before),
                  {"kind": "Words", "at": 0, "lines": [head], "beats": 0.4},
                  {"kind": "Bars", "at": 0.25, "bars": bars, "color": "ink", "beats": 0.5, "step": 0.08},
                  {"kind": "Words", "at": 0.5, "lines": labels, "beats": 0.4, "step": 0.08}]


def ink(S, ln):
    """A line's ink over and under its baseline, px, upright."""
    b = text_box(S, ln, ink=True)
    return ln["y"] - b[1], b[3] - ln["y"]


def columns(frame, k):
    """The px spans across the frame of `k` slices side by side, GUT apart, the outer two running off the frame."""
    w = (frame.W + GUT) / k
    return [(-BLEED if j == 0 else round(j * w, 1), frame.W + BLEED if j == k - 1 else round((j + 1) * w - GUT, 1)) for j in range(k)]


def piece(frame, span, top, bottom):
    """The four corners of the piece of the frame between x `span` and the edges `top` and `bottom`; a missing edge
    runs it off the frame."""
    xa, xb = span
    over = abs(math.tan(math.radians((top or bottom).tilt))) * frame.W + BLEED
    ya = (top.y(xa), top.y(xb)) if top else (-over, -over)
    yb = (bottom.y(xa), bottom.y(xb)) if bottom else (frame.H + over, frame.H + over)
    return [[round(x, 1), round(y, 1)] for x, y in ((xa, ya[0]), (xb, ya[1]), (xb, yb[1]), (xa, yb[0]))]


def slice_layer(frame, p, poly, edge, at):
    """A Slice layer: post `p`'s photograph inside `poly`, laid whole so the middle of its own line lies on `edge`,
    the edge the slice is cut along (on its focus when it has no line)."""
    xs, ys = [x for x, _ in poly], [y for _, y in poly]
    box = (max(0, min(xs)), max(0, min(ys)), min(frame.W, max(xs)), min(frame.H, max(ys)))
    return {"kind": "Slice", "at": round(at, 2), "poly": poly, "photo": photo(p), "place": place(frame, p, edge, box), "owner": p["rank"],
            "beats": 0.4}


def chip(S, frame, p, span, edge, size, hang):
    """A post's count turned to a closer edge, standing on it or hanging under it at its slice's left, sized down
    until it fits the slice and the safe area."""
    num = {"text": figure(p["likes"]), "y": 0, "size": size, "face": "display", "axes": COND, "tracking": -0.02, "color": "ink",
           "name": f"count-{p['rank']}"}
    x = max(frame.left + 2, span[0] + 22)
    for _ in range(3):
        room = (min(span[1] - 16, frame.W - frame.right - 2) - x) / math.cos(math.radians(edge.tilt))
        num.update(x=x, size=size)
        while num["size"] > 40 and text_width(S, num) > room:
            num["size"] -= 2
        base = edge.y(x) + (LIFT + ink(S, num)[0] if hang else -LIFT)
        num.update(y=round(base, 1), rotate=edge.tilt, pivot=[round(x, 1), round(base, 1)])
        left = hull(turned(text_box(S, num), num))[0]
        if left >= frame.left:
            break
        x += frame.left - left + 1
    return [num]


def reach(S, lines, edge, box=False):
    """How far the lines rise over the edge and fall under it, px, down the frame: their ink, or with `box` their em
    boxes."""
    lo = hi = 0.0
    for ln in lines:
        for x, y in turned(text_box(S, ln, ink=not box), ln):
            lo, hi = min(lo, y - edge.y(x)), max(hi, y - edge.y(x))
    return -lo, hi


def closer(S, frame, posts, words, handle, before):
    """The closer: the field sweeps down over the last photograph, and the nine are laid on it as slices along parallel
    edges, every line turned to them: along the top post's own line when it has one, and otherwise along the edge the
    nine left, turned no further than LEAN. The top post lies across the foot of the frame with its count, rank and
    caption standing on its edge and the handle over its rank; the other eight lie in rows over it, the top row running
    off the frame's head, and every one of their counts hangs under its own slice."""
    k = ACROSS[frame.name]
    rows = [posts[1 + i:1 + i + k] for i in range(0, len(posts) - 1, k)] + [posts[:1]]
    tilt = tilt_of(posts[0], frame) if posts[0].get("line") else max(-LEAN, min(LEAN, before.tilt))
    for f in (1.0, 0.66, 0.33, 0.0):
        for q in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
            L = lay(S, frame, rows, words, handle, posts[0]["likes"], q, round(tilt * f, 2))
            if L:
                return [{"kind": "Cut", "at": 0, "line": [frame.H, frame.H], "from": before.line, "field": "accent", "beats": 0.6}] + L
    raise ValueError(f"the drive closer has no layout for {len(posts)} posts in {frame.name}")


def hero_lines(S, frame, p, top, edge, k, handle, ask):
    """The top post's count standing on the closer's last edge with its rank and caption, and the handle and the ask
    over the rank in the room right of the count, on one line or the handle over the ask; over the count, on one line,
    when that room is too narrow for them."""
    said = f"{handle}  ·  {ask}"
    lines = count_lines(S, frame, p, top, edge, k, "paper")
    small = SMALL[frame.name]
    rank = next(ln for ln in lines if ln["name"].startswith("rank-"))
    tag = {"y": 0, "size": small, "face": "text", "weight": 700, "tracking": 0.01, "color": "ink"}
    if rank["x"] > lines[0]["x"] + 4:
        room = (frame.W - frame.right - rank["x"]) / math.cos(math.radians(edge.tilt)) - 6
        wrapped = next((ts for ts in ([said], [handle, ask]) if all(text_width(S, dict(tag, text=t)) <= room for t in ts)), None)
        if wrapped:
            y = rank["y"] - small * 1.25 - round(small * 0.4)
            for i, t in enumerate(reversed(wrapped)):
                lines.append(dict(tag, text=t, x=rank["x"], y=round(y - i * small * 1.25, 1), rotate=edge.tilt, pivot=rank["pivot"],
                                  name=f"handle-{len(wrapped) - 1 - i}"))
            return lines
    num = lines[0]
    x = num["x"]
    tu, td = ink(S, dict(tag, text=said, x=x))
    rise = reach(S, lines, edge)[0]
    for _ in range(3):
        base = edge.y(x) - rise - GAP - td
        line = dict(tag, text=said, x=x, y=round(base, 1), rotate=edge.tilt, pivot=[round(x, 1), round(base, 1)], name="handle")
        left = hull(turned(text_box(S, line), line))[0]
        if left >= frame.left:
            break
        x += frame.left - left + 1
    return lines + [line]


def lay(S, frame, rows, words, handle, top, q, tilt):
    """The closer's layers for `rows` (the eight in rows, then the top post) with counts at `q` of their size on edges
    turned `tilt`, or None when they do not fit: a slice showing less than SHOWN px on its short side, or type outside
    the safe area or over a photograph."""
    W, H, n = frame.W, frame.H, len(rows)
    floor = SHOWN[frame.name]
    spread = abs(math.tan(math.radians(tilt))) * W / 2
    def hero(e):
        return hero_lines(S, frame, rows[-1][0], top, e, math.sqrt(q), handle, words["ask"])

    def hanging(i, e):
        return [ln for p, span in zip(rows[i], columns(frame, len(rows[i])))
                for ln in chip(S, frame, p, span, e, max(40, round(CHIP[frame.name] * q * math.sqrt(p["likes"] / top))), True)]

    z = Edge(frame, 0, tilt)
    rise = reach(S, hero(z), z)[0]
    drops = [reach(S, hanging(i, z), z)[1] for i in range(n - 1)]
    # the top row's foot across the middle column: low enough that the row shows SHOWN px and its hanging counts
    # stay in the safe area
    foot = max(floor + spread, frame.top - min(y for ln in hanging(0, z) for _, y in turned(text_box(S, ln), ln))) if n > 1 else 0
    # the field under each of the eight's rows: its hanging counts, then the next row (or the top post's type)
    fields = [drops[i] + GAP + (rise + GAP if i == n - 2 else 0) for i in range(n - 1)]
    # the last row's top edge sits as low as its type stays in the safe area and the row still shows SHOWN px
    low = max(y for ln in hero(z) for _, y in turned(text_box(S, ln), ln))
    c_last = min(H - frame.bottom - low - 2, H - floor - spread)
    mids = max(0, n - 2)
    h = 0.0
    if mids:
        h = (c_last - sum(fields) - foot) / mids
        if h < floor:
            return None
    # bottom up: each row's top and bottom edge across the middle column (None runs it off the frame)
    tops, bottoms = [None] * n, [None] * n
    tops[-1] = c = c_last
    for i in range(n - 1, 0, -1):
        bottoms[i - 1] = c - fields[i - 1]
        if i - 1 > 0:
            c = bottoms[i - 1] - h
            tops[i - 1] = c
    if n > 1 and bottoms[0] < foot - 0.5:
        return None
    E = [(Edge(frame, t, tilt) if t is not None else None, Edge(frame, b, tilt) if b is not None else None) for t, b in zip(tops, bottoms)]
    L, counted, at = [], [], 0.0
    for i, row in enumerate(rows):
        te, be = E[i]
        for p, span in zip(row, columns(frame, len(row))):
            poly = piece(frame, span, te, be)
            if shown(poly, W, H) < floor - 0.5:
                return None
            L.append(slice_layer(frame, p, poly, te or be, at))
            at += 0.04
        counted += hanging(i, be) if i < n - 1 else []
    standing = hero(E[-1][0])
    sx0, sy0, sx1, sy1 = frame.safe
    for ln in counted + standing:
        b = hull(turned(text_box(S, ln), ln))
        if b[0] < sx0 - 0.5 or b[1] < sy0 - 0.5 or b[2] > sx1 + 0.5 or b[3] > sy1 + 0.5:
            return None
        quad = turned(text_box(S, ln, ink=True), ln)
        if any(crossing(quad, s["poly"]) for s in L):
            return None
    num, rest = standing[:1], standing[1:]
    return L + [{"kind": "Words", "at": round(at + 0.1, 2), "lines": num, "beats": 0.5},
                {"kind": "Words", "at": round(at + 0.3, 2), "lines": rest[::-1], "beats": 0.4, "step": 0.08},
                {"kind": "Words", "at": round(at + 0.5, 2), "lines": counted, "beats": 0.4, "step": 0.06}]


def build(posts, frame, words, handle, year, bpm=BPM):
    """The drive storyboard for `posts` (rank order) in `frame`: the hook over the top post, a count beat per post
    counting down from the lowest rank to the top post, the nine as bars, the closer. The bars and the closer are held
    by design, on downbeats. Rests: the hook, the densest beat (the bars), the closer and the ordinary count beat in the
    middle of the countdown."""
    S = sys_()
    top = posts[0]["likes"]
    total = sum(p["likes"] for p in posts)
    edge, hooked = hook(S, frame, posts[0], words, handle, year, total)
    scenes = [{"id": "hook", "t": 0.0, "layers": hooked}]
    scenes[0]["held"] = "the year's total counting up, the film's first figure"
    t = HOOK_BEATS
    countdown = posts[::-1]
    before = 0
    for i, (p, n) in enumerate(zip(countdown, run_beats(len(posts)))):
        edge, layers = count_beat(S, frame, p, top, edge)
        layers = paced(layers, min(1.0, n / COUNT_PACE))
        # the first two counts and the last three roll up from the one before and land on a hit; the middle of the
        # countdown slams its counts onto the edge with the blade
        if rolls(i, len(posts)):
            layers[1]["lines"][0]["count"] = [before, p["likes"], ROLL]
        before = p["likes"]
        scenes.append({"id": f"piece-{p['rank']}", "t": t, "layers": placed(layers, t)})
        t += n
    edge, layers = nine(S, frame, posts, words, edge)
    scenes.append({"id": "nine", "t": t, "layers": placed(layers, t), "held": "the nine as bars, the run's counts read together"})
    t += NINE_BEATS
    ending = closer(S, frame, posts, words, handle, edge)
    # the field sweeps down over the nine's photograph where the nine leave it, so the frame is never bare
    ending[0].update(photo=layers[0]["photo"], place=rested(layers[0], frame), push=0)
    scenes.append({"id": "closer", "t": t, "layers": placed(ending, t), "held": "the ending, made to be posted"})
    rests = {"hook": "hook", "dense": "nine", "closer": "closer", "ordinary": f"piece-{countdown[len(posts) // 2]['rank']}"}
    story(scenes, posts, total, handle)
    # the camera leaves a shot before it ends, so each rest is where its shot holds still: the hook's total landed, an
    # ordinary count standing on its edge, the bars standing in the graze, the closer settled
    rest_at = {"hook": COUNT_UP + 1.0, "ordinary": BLADE + SWEEP + 0.9, "dense": 1.2}
    return {"system": S, "scenes": scenes, "end": t + CLOSER_BEATS, "hook": 0.25, "rests": rests, "rest_at": rest_at, "drift": 0.0,
            "sound": sound(scenes, posts, frame, ending), "clips": clips(scenes, posts)}


# the beats after a shot's start at which the film's moves happen, as the studio's drive film times them: the
# photograph holds clean for a beat until the dot draws the blade's line across it (the hook's edge opens at once),
# the count rolls up, the camera leaves a card before the next one starts, the hook's total breaks, the bars stand,
# fold and give way to the wall
BLADE, HOOK_BLADE, ROLL, LEAVE, BREAK, STAND, FOLD = 1.0, 0.3, 0.6, 0.6, 2.75, 0.07, 2.0
# the dot's sweep along a count's edge before the blade cuts behind it
SWEEP = 0.3
# the beats the dot takes to run the countdown across the closer's wall, from the wall landing to the stop, where the
# picture and the sound stop together and the wall holds still and silent to the end
ROUTE = 4.0


def rolled(sc):
    """Whether a count scene rolls its count up (its count line carries a roll) or slams it onto the edge."""
    return any("count" in ln for L in sc["layers"] if L.get("kind") == "Words" for ln in L.get("lines") or [])


def short(caption, limit=6):
    words = (caption or "").replace("\n", " ").split()
    return " ".join(words[:limit]) + ("..." if len(words) > limit else "") if words else "the photograph"


def story(scenes, posts, total, handle):
    """Each scene's `reveals` (what its move shows: the photograph's subject or its actual count) and `carries` (what
    crosses the cut into the next scene), in the film's order."""
    by = {p["rank"]: p for p in posts}
    ids = [sc["id"] for sc in scenes]
    for i, sc in enumerate(scenes):
        nxt = ids[i + 1] if i + 1 < len(ids) else None
        if sc["id"] == "hook":
            sc["reveals"] = f"the year's total, {figure(total)} likes, counting up over the top photograph as the blade opens it"
            sc["carries"] = "the total breaks into the nine counts, which gather into the best-nine grid, hang there and burst at the lens; the camera lifts off the top photograph toward the wall"
        elif sc["id"].startswith("piece-"):
            p = by[int(sc["id"].split("-")[1])]
            verb = "rolls up on" if rolled(sc) else "slams onto"
            sc["reveals"] = (f"no. {p['rank']}, {short(p.get('caption'))}: the photograph holds clean for a beat, then the dot draws its own line across it, "
                             f"the blade cuts behind the dot and {figure(p['likes'])} {verb} the edge")
            sc["carries"] = ("the dot runs off the end of the edge and the camera follows it to the next photograph, where it draws the next line; "
                             "the count settles into its slice on the wall"
                             if nxt and nxt.startswith("piece-") else "the camera drops from the top post to graze the wall as the photographs stand up as bars, the counts on their faces")
        elif sc["id"] == "nine":
            sc["reveals"] = "the nine photographs standing out of the wall as bars, each as tall as its share of the top post's likes, its count on its face"
            sc["carries"] = "the bars fold flat into their slices and the camera rises to frame the whole wall"
        elif sc["id"] == "closer":
            sc["reveals"] = (f"the assembled wall, the nine cut and counted: the dot runs the countdown across it, landing after each count on the "
                             f"half beat, and comes to rest as the full stop of the ask as {handle} and the ask rise")
            sc["carries"] = "nothing: the picture and the music stop together on the last hit and the wall holds still and silent to the end"


def sound(scenes, posts, frame, ending):
    """The film's sound cues, each at a named beat (`at` in beats from the film's start) for music.py to synthesise and
    mix under the bed: a riser through the hook into the break, hits where the camera slams and the blade cuts,
    tick-ups under the counts that hold long enough to read, whooshes where the camera travels (panned the way it
    goes), a hit as each bar stands, an impact as the wall lands, a light hit each time the dot lands after a count
    across the wall, and the stop as it lands after the ask, where the bed cuts and the film holds silent. The middle of
    the countdown runs on the cut and the travel alone, so the film is dense at its open, sparse in its middle and
    densest at its close."""
    starts = {sc["id"]: sc["t"] for sc in scenes}
    ids = [sc["id"] for sc in scenes]
    end = {ids[i]: (starts[ids[i + 1]] if i + 1 < len(ids) else None) for i in range(len(ids))}
    slot = {L["owner"]: L["place"] for L in ending if L.get("kind") == "Slice"}
    x_of = lambda rank: (slot[rank][0] + slot[rank][2] / 2) / frame.W if rank in slot else 0.5
    top = posts[0]["likes"]
    likes = {p["rank"]: p["likes"] for p in posts}
    cues = [{"kind": "hit", "at": 0.0, "beat": "hook", "what": "the camera slams onto the top photograph", "weight": 0.9},
            {"kind": "hit", "at": 0.08, "beat": "hook", "what": "the slam's second strike", "weight": 0.5},
            {"kind": "riser", "at": 0.0, "beats": BREAK, "beat": "hook", "what": "the hook builds into the break"},
            {"kind": "hit", "at": HOOK_BLADE, "beat": "hook", "what": "the blade opens the top photograph", "weight": 0.45, "bright": 1.0},
            {"kind": "ticks", "at": HOOK_BLADE, "beats": COUNT_UP - HOOK_BLADE, "beat": "hook", "what": "the total counts up", "n": 14},
            {"kind": "hit", "at": COUNT_UP, "beat": "hook", "what": "the total lands", "weight": 0.7},
            {"kind": "hit", "at": BREAK, "beat": "hook", "what": "the total breaks into the nine", "weight": 1.0},
            {"kind": "whoosh", "at": BREAK + 0.8, "beats": 0.8, "beat": "hook", "what": "the nine counts fly at the lens as the camera lifts toward the wall",
             "pan": [0.0, 0.0]}]
    # the first count's travel rides the break's whoosh
    prev = None
    for sc in scenes:
        if not sc["id"].startswith("piece-"):
            continue
        rank, t = int(sc["id"].split("-")[1]), sc["t"]
        beats = end[sc["id"]] - t
        if prev is not None:
            cues.append({"kind": "whoosh", "at": round(t - LEAVE, 3), "beats": LEAVE + 0.3, "beat": sc["id"],
                         "what": f"the camera travels with the dot to no. {rank}", "pan": [round(x_of(prev) * 2 - 1, 2), round(x_of(rank) * 2 - 1, 2)]})
        weight = round(0.35 + 0.5 * math.sqrt(likes[rank] / top), 2)
        if rolled(sc):
            cues.append({"kind": "hit", "at": round(t + BLADE + SWEEP, 3), "beat": sc["id"], "what": f"the blade cuts no. {rank}", "weight": 0.3, "bright": 0.9})
            cues.append({"kind": "ticks", "at": round(t + BLADE + SWEEP, 3), "beats": ROLL, "beat": sc["id"], "what": f"no. {rank}'s count rolls up", "n": 8})
            cues.append({"kind": "hit", "at": round(t + BLADE + SWEEP + ROLL, 3), "beat": sc["id"], "what": f"no. {rank}'s count lands", "weight": weight})
        else:
            cues.append({"kind": "hit", "at": round(t + BLADE + SWEEP, 3), "beat": sc["id"], "what": f"the blade cuts no. {rank} and its count slams onto the edge",
                         "weight": weight, "bright": 0.8})
        prev = rank
    if "nine" in starts:
        R = starts["nine"]
        cues.append({"kind": "whoosh", "at": round(R - LEAVE, 3), "beats": 1.1, "beat": "nine", "what": "the camera drops to graze the wall", "pan": [0.4, -0.4]})
        for i, p in enumerate(posts):
            cues.append({"kind": "hit", "at": round(R + 0.05 + STAND * i, 3), "beat": "nine", "what": f"no. {p['rank']}'s bar stands",
                         "weight": round(0.2 + 0.25 * likes[p["rank"]] / top, 2), "bright": 0.6})
        cues.append({"kind": "hit", "at": round(R + FOLD, 3), "beat": "nine", "what": "the bars fold into the wall", "weight": 0.55})
        cues.append({"kind": "whoosh", "at": round(R + FOLD, 3), "beats": end["nine"] - R - FOLD, "beat": "nine", "what": "the camera rises to frame the wall",
                     "pan": [-0.3, 0.0]})
    if "closer" in starts:
        C = starts["closer"]
        # the dot lands after each count below the top post's, then after the ask
        down = list(reversed(posts))[:-1]
        cues.append({"kind": "impact", "at": C, "beat": "closer",
                     "what": f"the wall lands" + (f" and the dot rises after no. {down[0]['rank']}'s count" if down else "")})
        hops = len(down)
        for k in range(1, hops):
            cues.append({"kind": "hit", "at": round(C + ROUTE * k / hops, 3), "beat": "closer", "what": f"the dot lands after no. {down[k]['rank']}'s count",
                         "weight": 0.2, "bright": 0.9})
        cues.append({"kind": "hit", "at": C + ROUTE, "beat": "closer", "what": "the dot lands as the full stop of the ask, risen with the handle",
                     "weight": 0.8, "bright": 0.7})
        cues.append({"kind": "stop", "at": C + ROUTE, "beat": "closer", "what": "the picture and the music stop together; the wall holds silent"})
    return sorted(cues, key=lambda c: c["at"])


def clips(scenes, posts):
    """The generated clips the film would carry, for the platform's image-to-video model: the wall's world under the
    opener, each photograph brought to life under its count beat, the texture between the countdown and the bars.
    `stand_in` names the camera or depth move the film makes in a clip's place when no clip has arrived."""
    by = {p["rank"]: p for p in posts}
    out = [{"id": "00", "beat": "hook", "role": "the wall's world", "seconds": 2.0, "image": by[1]["file"],
            "prompt": f"slow push in over this photograph ({short(by[1].get('caption'), 10)}) as dust drifts through its own light, shallow depth of field, no text",
            "stand_in": "the hook's camera slam and push over the top photograph, with the dust field drifting through it"}]
    for sc in scenes:
        if sc["id"].startswith("piece-"):
            p = by[int(sc["id"].split("-")[1])]
            out.append({"id": f"{len(out):02d}", "beat": sc["id"], "role": "the photograph brought to life", "seconds": 1.5, "image": p["file"],
                        "prompt": f"the scene in this photograph ({short(p.get('caption'), 10)}) moves gently for a moment, camera still, natural light, no text",
                        "stand_in": "the card lifting toward the lens and the camera pushing in while the blade cuts it into two depth layers"})
    out.append({"id": f"{len(out):02d}", "beat": "nine", "role": "the texture between chapters", "seconds": 1.5, "image": by[1]["file"],
                "prompt": f"slow macro drift across the surfaces in this photograph ({short(by[1].get('caption'), 10)}), dust settling in its light, no text",
                "stand_in": "the camera grazing the bars with the dust field swept by the move"})
    return out
