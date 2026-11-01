"""Captions a phone reads (motion/system/standards.md R3), measured where the studio draws them and remedied on the
board before the film renders.

A stop's words stand on its card: over the photograph (the card's line box inside the picture's box) under the
scrim the layout lays there (route/card.tsx), or on the card's ground. Each group of them (the label, the line) stands
at the contrast its size needs on a phone (legible.need) against the brightest quarter of the photograph under it
(the darkest under dark type) after the scrim, or against the ground. The studio lays the scrim in WebGL, so it
blends in linear light: black under light words, the card's paper under dark ones.

lay(card, layout, colors, short) is the remedy, run as the board lays each card out: a label that does not read in its
own color takes the line's color, and words that still do not read deepen the card's scrim (`scrim` on the card, which
route/card.tsx draws) up to legible.SCRIM_MOST. findings(board) is the storyboard check's half: every caption that
still does not read, every closer line set under legible.LEAST, and, on a board cut to the music's tempo (the film's
timing; the kit's own tempo only lays the draft out), timing(board): every stop whose words stand whole for less time
than they take to read or whose headline settles more than board_drive.SETTLED seconds after its beat.
"""
import math
from pathlib import Path

import legible

# the least depth route/card.tsx gives a scrim the layout asks for (card.tsx SCRIM_DEPTH)
SCRIM_DEPTH = 0.86


def luma(c):
    """A hex color's luma, 0 to 1, as route/card.tsx weighs it to pick the scrim's color."""
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def hexof(colors, role):
    return colors.get(role, role)


def base_scrim(layout):
    """The scrim route/card.tsx lays under a card's words when the board names none."""
    s = layout["line"].get("scrim", 0) or 0
    return max(s, SCRIM_DEPTH) if s > 0 else 0.0


def veil_of(lines, colors):
    """The scrim's color: black under light words, the card's paper under dark ones (route/card.tsx)."""
    ink = hexof(colors, lines[-1]["color"]) if lines else hexof(colors, "paper")
    return "#000000" if luma(ink) > 0.5 else hexof(colors, "paper")


def reads(color, q, scrim, veil):
    """The contrast of `color` over a photograph whose gray quarters are `q`, under a scrim `scrim` deep in `veil`,
    blended in linear light: against the brightest quarter under light type, the darkest under dark type. Under a black
    veil it is legible.contrast(color, q, scrim, linear=True)."""
    c, v = legible.lum(color), legible.lum(veil)
    back = lambda g: legible.lum(g) * (1 - scrim) + v * scrim
    return legible.ratio(c, back(q[2] if c > back(q[1]) else q[0]))


def deepen(color, q, want, scrim, veil):
    """The least scrim from `scrim` up to legible.SCRIM_MOST at which `color` reads at `want`, or None."""
    s = scrim
    while s <= legible.SCRIM_MOST + 1e-9:
        if reads(color, q, s, veil) >= want:
            return round(s, 2)
        s += 0.01
    return None


def on_photo(card, ln):
    """Whether a line stands on the card's photograph, as route/words.tsx decides it (onPhoto)."""
    x0, y0, x1, y1 = card["box"]
    return ln["y"] > y0 and ln["y"] - ln["size"] < y1 and x0 - ln["size"] < ln["x"] < x1


def ink_box(ln):
    """The box of a line's ink, frame px (bounds.box)."""
    import bounds
    return bounds.box(ln)


def around(boxes, clip):
    x0, y0 = max(min(b[0] for b in boxes), clip[0]), max(min(b[1] for b in boxes), clip[1])
    x1, y1 = min(max(b[2] for b in boxes), clip[2]), min(max(b[3] for b in boxes), clip[3])
    return [x0, y0, x1, y1]


def seen(file):
    """Whether the photograph's pixels are on disk (under the run's public/), so it can be measured."""
    return (Path(file) if Path(file).is_absolute() else Path("public") / file).is_file()


def groups(card):
    """A card's words as the groups that read together: its label's rows, then its line's rows."""
    label = [ln for ln in card["lines"] if ln.get("name") == "label"]
    line = [ln for ln in card["lines"] if ln.get("name") != "label"]
    return [g for g in (label, line) if g]


def measure(card, g, color, scrim, veil, ground, short):
    """(contrast, wanted, the photograph's gray quarters under the group or None on the ground) for group `g` of a
    card's words in `color`: over the photograph under it after the scrim, or on the card's ground; None when the
    photograph is not on disk."""
    want = legible.need(min(ln["size"] for ln in g), short)
    if any(on_photo(card, ln) for ln in g):
        if not seen(card["file"]):
            return None
        q = legible.under(card["file"], card["photo"], around([ink_box(ln) for ln in g], card["box"]))
        return (reads(color, q, scrim, veil), want, q) if q else None
    return legible.ratio(legible.lum(color), legible.lum(ground)), want, None


def lay(card, layout, colors, short):
    """The remedy, on a card laid out by board_drive: a label that does not read in its own color takes the line's
    color, and light words over the photograph that still do not read deepen the card's scrim, up to SCRIM_MOST. Sets
    `scrim` on a card whose layout lays one."""
    if not card["lines"]:
        return
    ground = hexof(colors, layout["ground"])
    scrim = base_scrim(layout)
    veil = veil_of(card["lines"], colors)
    line_color = card["lines"][-1]["color"]
    for g in groups(card):
        got = measure(card, g, hexof(colors, g[0]["color"]), scrim, veil, ground, short)
        if got is None:
            continue
        r, want, q = got
        if r < want and g[0].get("name") == "label" and g[0]["color"] != line_color:
            for ln in g:
                ln["color"] = line_color
            r, want, q = measure(card, g, hexof(colors, line_color), scrim, veil, ground, short)
        if r < want and q and scrim > 0:
            scrim = deepen(hexof(colors, g[0]["color"]), q, want, scrim, veil) or legible.SCRIM_MOST
    if base_scrim(layout) > 0:
        card["scrim"] = round(scrim, 2)


def halo_back(fill, ground, colors):
    """What a hook line's letters stand on over `ground`: its halo (route/words.tsx haloOf, at its 0.8 opacity), the
    card's color furthest in lightness from the line's own, over the map, blended in sRGB as SVG paints it."""
    tones = sorted((c for c in colors.values() if isinstance(c, str) and c.startswith("#") and len(c) >= 7), key=luma)
    halo = tones[0] if luma(fill) > 0.6 else tones[-1]
    mix = [0.8 * int(halo[i:i + 2], 16) + 0.2 * int(ground[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(v):02x}" for v in mix)


def kicker_reads(ln, colors, short):
    """(contrast, wanted) of a hook line over the map's land and sea, under its halo: the worse of the two."""
    fill = hexof(colors, ln["color"])
    r = min(legible.ratio(legible.lum(fill), legible.lum(halo_back(fill, hexof(colors, k), colors))) for k in ("land", "sea"))
    return r, legible.need(ln["size"], short)


def lay_kicker(kicker, colors, short):
    """The hook's handle takes the title's color when its own does not read over the map."""
    if len(kicker) > 1:
        r, want = kicker_reads(kicker[-1], colors, short)
        if r < want and kicker_reads({**kicker[-1], "color": kicker[0]["color"]}, colors, short)[0] >= want:
            kicker[-1]["color"] = kicker[0]["color"]


# ------------------------------------------------------------------ the closer's words
def _measure(text, file, size, tracking=0.0):
    import board_drive as bd
    return bd.font({"file": file}).getlength(text) / 1000 * size + max(0, len(text) - 1) * tracking * size


def _fit(rows, file, width, tracking=0.0, most=math.inf):
    return min(most, 100 * width / max(1.0, max(_measure(r, file, 100, tracking) for r in rows)))


def _balance(text, n):
    """The text in `n` rows balanced by their length in letters, or fewer (moves/kit.tsx balance)."""
    ws = text.split()
    for k in range(min(max(n, 1), len(ws)), 1, -1):
        cuts = [()]
        for _ in range(k - 1):
            cuts = [c + (j,) for c in cuts for j in range((c[-1] if c else 0) + 1, len(ws))]
        sets = [[" ".join(ws[a:b]) for a, b in zip((0,) + c, c + (len(ws),))] for c in cuts if len(c) == k - 1]
        score = lambda s: (max(map(len, s)), max(map(len, s)) - min(map(len, s)))
        best = min(sets, key=score)
        if min(map(len, best)) * 2 >= max(map(len, best)):
            return best
    return [" ".join(ws)]


def _carry(rows):
    out = []
    for i, r in enumerate(rows):
        r = r[2:] if i > 0 and r.startswith("· ") else r
        out.append(r + (" ·" if i < len(rows) - 1 and rows[i + 1].startswith("· ") else ""))
    return out


def _rows(text, file, width, size):
    for n in (1, 2):
        rows = _carry(_balance(text, n))
        if _fit(rows, file, width) >= size:
            return rows
    return _carry(_balance(text, 3))


def closer_lines(board):
    """The closer's places and handle at the sizes its shape sets them at rest (route/closers.tsx), each held at the
    board's `least` where it carries one: [(what, text, size px)]."""
    import board_drive as bd
    sy, cl, f = board["system"], board["route"]["closer"], board["format"]
    W, H, style = f["width"], f["height"], board["style"]
    u = lambda v: v * min(W, H) / 1080
    least = cl.get("least", 0.0)
    text = bd.PHONE[style]["text"][0] if style in bd.PHONE else sy["text"]["file"]
    display = bd.PHONE[style]["display"][0] if style in bd.PHONE else sy["display"]["file"]
    safe = sy["safe"][f.get("name", "reel")]
    x, y, w, h = cl["window"]
    handle, signoff = board.get("handle") or "", cl["signoff"]
    shape = sy["closer"]
    if shape == "title-card":
        bars = (sy.get("finish") or {}).get("bars", 0) * H
        top, bottom = max(safe["top"], bars), H - max(safe["bottom"], bars)
        l0, r0 = max(u(100), safe["left"]), min(W - u(100), W - safe["right"])
        room = (r0 - l0) / 1.03
        title = cl["title"].upper()
        lines = _balance(title, 2 if len(title) > 16 else 1)
        said = _rows(signoff, text, room * 0.9, max(u(36), least))
        want_t = min(u(120), _fit(lines, display, room, 0.14))
        want_s = max(least, min(u(40), _fit(said, text, room * 0.9)))
        want_h = max(least, u(30))
        credit = bool(handle) and bottom - (y + h) > want_h * 1.2 + u(120)
        tall = len(lines) * want_t * 1.05 + len(said) * want_s * 1.2 + u(30) + (want_h * 1.1 + u(26) if handle and not credit else 0)
        k = min(1.0, (y - top - u(40)) / tall)
        sizes = max(least, want_s * k), want_h if credit else max(least, want_h * k)
    elif shape == "poster":
        m = sy["photo"]["grid"]["margin"] * W
        said = _rows(signoff, text, W - 2 * m, max(u(30), least))
        low = y + h + u(40)
        sizes = max(least, min(u(30), _fit(said, text, W - 2 * m))), max(least, u(32) if min(u(220), H - low - m) > u(40) else u(28))
    else:
        inner = W - 2 * u(48) - 4 * u(30)
        said = _rows(signoff, text, inner, max(u(36), least))
        sizes = max(least, min(u(36), _fit(said, text, inner))), max(least, u(32))
    out = [("places", signoff, round(sizes[0], 1))]
    return out + [("handle", handle, round(sizes[1], 1))] if handle else out


# ------------------------------------------------------------------ the check
def timing(board):
    """Every stop on the board whose words stand whole for less time than they take to read, or whose headline settles
    past board_drive.SETTLED seconds after its beat, as route/words.tsx plays them at the board's tempo."""
    import board_drive as bd
    out = []
    for t in bd.word_times(board):
        if t["whole"] < t["need"] - 1 / bd.FPS:
            out.append(f"{t['id']}: \"{t['words']}\" stands whole for {t['whole']:.2f} s, under the {t['need']:.2f} s its "
                       f"{t['n']} words take to read")
        if t["settled"] is not None and t["settled"] > bd.SETTLED + 1 / bd.FPS:
            out.append(f"{t['id']}: the headline \"{t['head']}\" settles {t['settled']:.2f} s after its beat, past the "
                       f"{bd.SETTLED:g} s a viewer gives it")
    return out


def findings(board):
    """Every caption on the board a phone does not read: a stop's label or line under the contrast its size needs over
    the photograph or the ground under it, a hook line over the map, a closer line under legible.LEAST, and, on a board
    cut to the music's tempo, timing(board)."""
    import board_drive as bd
    rt, f = board["route"], board["format"]
    short = min(f["width"], f["height"])
    colors = rt["colors"]
    out = []
    for c in rt["cards"]:
        layout = bd.layout_of(board["system"]["photo"], {"w": c["photo"][2], "h": c["photo"][3]}, f["width"], f["height"])
        scrim = c.get("scrim", base_scrim(layout))
        veil = veil_of(c["lines"], colors)
        for g in groups(c):
            got = measure(c, g, hexof(colors, g[0]["color"]), scrim, veil, hexof(colors, layout["ground"]), short)
            if got and got[0] < got[1]:
                r, want, q = got
                words = " ".join(ln["text"] for ln in g)
                size = min(ln["size"] for ln in g)
                if q:
                    out.append(f"{c['id']}: \"{words}\" reads {r:.1f}:1 over the photograph under it (scrim {scrim:g}), under the "
                               f"{want:g}:1 a {size:g} px line needs on a phone: give the beat a photograph that is darker under its words")
                else:
                    out.append(f"{c['id']}: \"{words}\" reads {r:.1f}:1 on the card's ground, under the {want:g}:1 a {size:g} px "
                               "line needs on a phone: the palette sets its color too near the ground")
    for ln in rt["hook"]["kicker"]:
        r, want = kicker_reads(ln, colors, short)
        if r < want:
            out.append(f"hook: \"{ln['text']}\" reads {r:.1f}:1 over the map, under the {want:g}:1 a {ln['size']:g} px line "
                       "needs on a phone")
    floor = legible.LEAST * short / 1080
    for what, text, size in closer_lines(board):
        if size < floor - 0.05:
            out.append(f"closer: the {what} \"{text}\" is set at {size:g} px, under the {legible.LEAST} px a phone shows legibly")
    return out + (timing(board) if board.get("to_music") else [])
