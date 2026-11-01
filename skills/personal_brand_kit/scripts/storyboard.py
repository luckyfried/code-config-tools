#!/usr/bin/env python3
"""The three looks of the person's film, each a board laid out for the reel, the square and the wide; the board the
person picks is cut to the music.

USAGE (from the workspace root; S = this skill's folder; every script works in the run build/run names):
    python3 S/scripts/storyboard.py draft    # material.py, then storyboards/{a,b,c}/board-{reel,square,wide}.json,
                                             # plan.json and storyboard.md; a new draft starts a new pick (winner.json,
                                             # vote/scores.json and the cut go)
    python3 S/scripts/storyboard.py check    # every board: type inside the safe area and inside the card's line box,
                                             # every caption legible on a phone over what is behind it, the length,
                                             # the hook, and each board against its style card (faces, moves,
                                             # transitions, colors) and the three looks against each other
    python3 S/scripts/storyboard.py sheets   # storyboards/<n>/sheet.png (the hook, a middle beat and the closer at rest)
                                             # and out/boards.png, the three looks side by side, to show the person
    python3 S/scripts/storyboard.py snap     # the picked board (winner.json) at the music's tempo -> film.json

The three looks are three style cards (styles/<id>.json; styles/catalog.md says what each looks like): kinetic-type,
editorial-quiet and swiss-grid, or, when taste.json `style` names another card, that style beside the two of those that
differ most from it (the default that shares the most axes with it gives way). The story is the kit's and the same in
all three: the opening line, the moments (studio.json `story`, which material.py writes), the question to the reader
and the sign-off. Each look takes its faces, colors, easing, finish, closer, photo layout and music from its card.

The words are the person's own. The opening line is taste.json `hook`, else the first phrase of the bio, else the first
moment's line; the question is taste.json `question`, else the question from the best-liked caption that asks one; the
sign-off is taste.json `signoff`, else the name, else the handle. A moment shows its pillar as its label and its own
caption line, set in the card's line box in the card's faces, sizes and colors. Words laid over a photograph read on a
phone (legible.py): a label that does not read in its own color takes the line's, and light words the photograph
under them outshines lie under a scrim as deep as they need, up to legible.SCRIM_MOST.

Each beat's move, and the cut into it, is chosen from what the beat shows (its form, words or none, portrait or
landscape, the peak, people, a place) among the card's allowlists, never the previous beat's move. Each beat lasts the
card's pace in musical beats at the card's tempo (the middle of its music recipe's range until the music exists; snap
uses the music's), and the moments the story cannot fit in 28 seconds are left out, the least liked first, the peak
always kept.

check fails a board on: a line outside the type area or outside the card's line box, a line set under the size a
phone shows legibly, a label or line that does not read against the photograph or panel under it at the contrast its
size needs on a phone, a length outside 12 to 30 s, a hook event after frame 30, a face, move, transition or color the
card does not name, the same move twice in a row, or two looks sharing more than two axes.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import legible  # noqa: E402

BOARDS = Path("storyboards")
FPS = compose.FPS
HOOK_FRAMES = 30
LENGTH = (12, 30)
MOST_SECONDS = 28
# a shot's length in seconds by the card's camera axis; the hook, the peak, the question and the closer take more
PACE = {"slam": 2.4, "snap": 2.6, "handheld": 3.0, "drift": 3.2, "dolly": 3.6, "slow": 3.8}
SHOT = 3.0
HOLD = 2.0
# the beats the first moment before the peak holds past the card's shot, each next moment one fewer
QUICKEN = 2
# the moves that set a hook's or a words beat's own words themselves; on any other move the kit sets them in the card's
# line box
SETS_WORDS = {"word-per-beat-slam", "line-by-line-type-rise", "type-mask-reveal", "rule-draw", "slam-words", "counter"}
# the moves that size the words they set by the measure's width alone (motion/system/moves/move/rule-draw.tsx): on a
# frame wider than it is tall their lines run past its foot, so there the kit sets the words in the card's line box
WIDTH_SIZED = {"rule-draw"}
# the moves that cut one word out of a field over a photo beat's photograph; the field lifts over the beat's last
# quarter onto the photograph and the card's line
MASKS = {"type-mask-reveal"}
LABEL_LEAST = legible.LEAST  # px on a 1080 frame: the smallest label that still reads on a phone held at arm's length
# how much closer the film's slow push under every photograph has come by a beat's last frame (Film.tsx)
PUSH = 1.05
# the scrim a hook's words lie under where the card's colors do not read on the photograph under them, at least
TITLE_SCRIM = 0.62
# the moves that draw the frame's grid in hairlines over the picture (motion/system/moves/move/grid-snap.tsx): the
# opening line stands on a panel whose edges are grid lines, so no hairline runs through a letter
HAIRLINES = {"grid-snap"}
# the moves that run bands across the frame (motion/system/moves/move/marquee.tsx): each band's top as a share of the
# frame's height, and the bands' height in px on a 1080-wide frame; a photo beat's line stands between them
BANDS = {"marquee": ((0.1, 0.74), 200)}
# the moves that set the picture in a window of the card's ground (motion/system/moves/move/white-space-crop.tsx): the
# window's top and foot margins, open, as shares of the frame's height; the opening line stands inside the window
WINDOWS = {"white-space-crop": (0.16, 0.26)}
# the moves that draw a rule across a photograph's head (motion/system/moves/move/rule-draw.tsx): the rule's height and
# the gap it leaves above the picture, px on a 1080-wide frame; a photo beat's line ends that same gap above the rule
HEADS = {"rule-draw": (18, 18)}
# the most lines a moment's line takes where its card sets it at display size
BIG_LINES = 5
# the moves in motion/system/moves/move/: a move that draws through ../arrival takes the whole frame for its spectacle
# and hands it back to the photograph; it holds the frame for its arrivalOf landing (seconds), or COUNTED for a move
# that counts or slams its own words first, then HANDBACK while the photograph clears back in
MOVES = _env.SKILL / "motion" / "system" / "moves" / "move"
COUNTED = 1.8
HANDBACK = 0.4
# the camera axes of the looks that take the frame-taking moves as their grammar, on every other photo beat back from
# the peak; every other look is calm and takes one, once, on its peak
ENERGETIC = {"slam", "snap"}
# the moves that set a photo beat's line themselves, over the photograph, before they hand the frame back to it: the
# kit sets no line of its own on that beat
OWN_LINE = {"slam-words", "counter"}
# a number in a line, in figures or as a word up to twelve: the counter move counts up to it, so it plays only on a
# line that says one
NUMBER = re.compile(r"\b(\d[\d,.]*|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", re.I)
# the photograph framed a little inside its box, so a move that pulls back never shows its edge
ZOOM = 1.1
# the card finishes (axes.finish) that show a photograph as it was posted, under nothing but the card's own finish
AS_POSTED = {"flat", "clean"}
# how much bigger than a moment's line the opening line and the question are set
TITLE_K = 1.6
ASK_K = 1.3
EMOJI = re.compile("[←-⯿☀-➿\U0001f000-\U0001faff️‍]")
PUNCT = ".,;:!?…\"'‘’“”()"
# the cut as QA, the critic and film render read it: the render reports vouch for out/ and cut.mp4 as the set of one
# cut, cut.json certifies cut.mp4 (or the half-size proof, proof-cut.mp4, with its own report); a step that replaces
# the cut removes them in this order before it changes the cut
CUT_SET = (Path("render/cut-report.json"), Path("render/film-report.json"), Path("cut.json"), Path("cut.mp4"),
           Path("render/proof-report.json"), Path("proof-cut.mp4"))


def mask_word(say):
    """The word a mask cuts out of the frame: the longest word of the line, so the photograph shows through a word that
    carries the line ("season", never "what's")."""
    words = [w.strip(".,!?:;\"'()") for w in say.split()]
    words = [w for w in words if w.isalpha()]
    return max(words, key=len, default="")


def clean(text):
    return " ".join(EMOJI.sub(" ", str(text or "")).split())


def phrase(text, most=8):
    """The first phrase of `text`: up to its first sentence end or emoji, at most `most` words, cut at a comma when
    longer."""
    head = re.split(r"[.!?\n|·]|" + EMOJI.pattern, str(text or ""))[0]
    words = clean(head).split()
    if len(words) > most:
        cut = [i + 1 for i, w in enumerate(words[:most]) if w.endswith(",")]
        words = words[:cut[-1]] if cut else words[:most]
    return " ".join(words).strip(PUNCT + " ")


class Run:
    """What every board is drafted from: studio.json (material.py), the taste and the palette."""

    def __init__(self, d=None):
        self.d = d or _env.read_json("studio.json")
        if not self.d:
            sys.exit("studio.json is missing: run storyboard.py draft (it runs material.py) after research.py and brand.py")
        self.taste = _env.read_json("taste.json") or {}
        self.lib = _env.read_json("library.json") or {}
        self.handle = "@" + (self.d.get("handle") or "").lstrip("@") if self.d.get("handle") else ""
        import palette
        self.swatches = palette.swatches_of(self.taste, _env.read_json("palette.json"))
        self.trio = compose.trio(self.taste.get("style"))
        self.story = [m for m in self.d.get("story") or [] if m.get("photo") in self.d["photos"]]
        if not self.story:
            sys.exit("studio.json has no moment with a photograph: the film needs at least one; see material.py")
        self.hook = clean(self.taste.get("hook")) or phrase(self.d.get("bio")) or \
            next((phrase(m["line"]) for m in self.story if m.get("line")), "") or self.d.get("name") or self.handle
        self.question = clean(self.taste.get("question")) or self.asked()
        self.signoff = clean(self.taste.get("signoff")) or clean(self.d.get("name")) or self.handle

    def asked(self):
        """The question from the best-liked caption that asks the reader one, in its own words (3 to 9 words)."""
        rows = sorted((self.lib.get("posts") or []), key=lambda r: -(r.get("likes") or 0))
        for r in rows:
            for s in re.findall(r"[^.!?\n]*\?", clean(r.get("caption") or r.get("text") or "")):
                s = " ".join(w for w in s.split() if not w.startswith(("#", "@"))).strip()
                if 3 <= len(s.split()) <= 9:
                    return s
        return ""

    def colors(self, c):
        import palette
        return palette.palette_of(c["palette"], self.swatches)["roles"]


# ------------------------------------------------------------------ layout
def role(colors, c):
    return colors.get(c, c)


def picture_box(fr, pic):
    """Where the card stands the photograph, [x0, y0, x1, y1] px; a side on the frame's edge runs past it."""
    x, y, w, h = pic["box"] if pic["show"] else (0, 0, 1, 1)
    R = 0.06
    out = (x * fr.W if x > 0 else -R * fr.W, y * fr.H if y > 0 else -R * fr.H,
           (x + w) * fr.W if x + w < 1 else (1 + R) * fr.W, (y + h) * fr.H if y + h < 1 else (1 + R) * fr.H)
    return [round(v, 1) for v in out]


def layout_of(lay, photo, fr):
    """The card's picture and line for `photo` on frame `fr`. A photograph wider than it is tall takes the card's
    landscape box and line box, so it fills the frame's width instead of leaving bare ground beside it. On a frame at
    least as wide as it is tall, an upright photograph takes them too where the landscape box's shape is nearer its own,
    so it is not cut to a thin strip with its line far below."""
    land = lay["landscape"]
    flat = dict(lay["picture"], box=land["box"]), dict(lay["line"], box=land["line"])
    if photo["aspect"] < 1:
        return flat
    if fr.W >= fr.H:
        def off(pic):
            x0, y0, x1, y1 = picture_box(fr, pic)
            return abs(math.log((y1 - y0) / (x1 - x0) / photo["aspect"]))
        if off(flat[0]) < off(lay["picture"]):
            return flat
    return lay["picture"], lay["line"]


def line_box(fr, box):
    a = fr.area
    x, y, w, h = box
    return [round(a[0] + x * (a[2] - a[0]), 1), round(a[1] + y * (a[3] - a[1]), 1),
            round(a[0] + (x + w) * (a[2] - a[0]), 1), round(a[1] + (y + h) * (a[3] - a[1]), 1)]


def set_text(fr, words, box, face, size, align, label=None, lab=None, bottom=False, most=3, least=None):
    """`words` set in `box` in `face`, from `size` down to `least` (half of `size` when None) and never under the size a
    phone shows legibly (legible.LEAST), in at most `most` lines that fit under the label: {lines [{text, x, y}], size,
    face, tracking, label, box}. Sizes are px at 1080. y is each line's baseline; `bottom` sets the lines on the box's
    foot rather than under its top."""
    k = min(fr.W, fr.H) / 1080
    size = round(size * k)
    floor = max(round(least * k) if least else size // 2, min(size, round(legible.LEAST * k)))
    f = compose.face_of(face)
    lead = f.get("lineHeight", 1.1)
    out_label = None
    top = box[1]
    if label and lab:
        ns = round(max(lab["size"], LABEL_LEAST) * k)
        ncap = compose.measure("H", ns, lab["face"])[1]
        text = compose.cased(label, lab["face"])
        x = box[0] if align == "start" else (box[0] + box[2]) / 2 - compose.measure(label, ns, lab["face"])[0] / 2
        out_label = {"text": text, "x": round(x, 1), "y": round(box[1] + 1.2 * ncap, 1), "size": ns, "face": lab["face"],
                     "tracking": compose.face_of(lab["face"])["tracking"], "color": lab["color"]}
        top = box[1] + 1.2 * ncap + 0.6 * ns
    width = box[2] - box[0]
    tall = box[3] - top
    s = size
    while True:
        lines = compose.wrap(words, s, width - 0.03 * s, face)
        cap = compose.measure("H", s, face)[1]
        need = cap + (len(lines) - 1) * lead * s + 0.28 * s
        # a word alone on a line of a set of several lines reads as a break in the sentence: the size comes down until
        # every line holds two words or more
        alone = len(lines) > 1 and any(len(x.split()) < 2 for x in lines)
        if (len(lines) <= most and need <= tall and not alone
                and all(compose.measure(x, s, face)[0] <= width - 0.03 * s for x in lines)) or s <= floor:
            break
        s = max(floor, int(s * 0.94))
    cap = compose.measure("H", s, face)[1]
    y0 = top + cap if not bottom else box[3] - 0.28 * s - (len(lines) - 1) * lead * s
    out = []
    for j, ln in enumerate(lines):
        w, _, lsb = compose.measure(ln, s, face)
        x = box[0] - lsb if align == "start" else (box[0] + box[2]) / 2 - w / 2
        out.append({"text": compose.cased(ln, face), "x": round(x, 1), "y": round(y0 + j * lead * s, 1)})
    if bottom and out_label:
        out_label["y"] = round(y0 - cap - 0.6 * out_label["size"], 1)
    return {"lines": out, "size": s, "face": face, "tracking": f["tracking"], "label": out_label, "box": box}


def grid_of(fr, g):
    """The card's grid `g` on the frame, as the moves draw it: its margin, and the lines of its columns and rows."""
    m = g["margin"] * fr.W
    return (m, [m + i * (fr.W - 2 * m) / g["cols"] for i in range(g["cols"] + 1)],
            [m + i * (fr.H - 2 * m) / g["rows"] for i in range(g["rows"] + 1)])


def on_panel(fr, g, b, t, box, ln, lab, colors, italic):
    """The opening line set again on a panel of the card's grid `g`: the label at the panel's top, the lines on its foot,
    the panel in the darker of ink and paper and the type in the other."""
    m, cols, rows = grid_of(fr, g)
    pad = round(0.045 * fr.W)
    # the panel is two rows of cells, so the line keeps the opening line's size; its foot is the grid row nearest the
    # line's box whose panel, a pad inside it, stays in the type area
    feet = [r for i, r in enumerate(rows) if i >= 2 and r - pad <= fr.area[3] and rows[i - 2] + pad >= fr.area[1]]
    foot = min(feet or [r for r in rows if r - pad <= fr.area[3]], key=lambda r: abs(r - box[3]))
    fi = rows.index(foot)
    above = rows[max(0, fi - 2)]
    size = ln["size"] * TITLE_K * (1.0 if ln["size"] >= 100 else 1.4)
    # the panel's head is the grid row above the label; a line too long for the panel's rows inside the type area takes
    # the next row down while the panel stays in the type area, then sets smaller until it fits
    for _ in range(16):
        inner = [m + pad, above + pad, min(fr.W - m - pad, fr.area[2]), rows[fi] - pad]
        t = set_text(fr, b["say"], inner, ln["face"], size, "start", b["label"] or None, lab, bottom=True)
        top = (t["label"] or t["lines"][0])["y"] - (t["label"] or t)["size"] - pad
        heads = [r for r in rows if r <= top]
        if heads and heads[-1] + pad >= fr.area[1]:
            break
        if fi + 1 < len(rows) and rows[fi + 1] - pad <= fr.area[3]:
            fi += 1
        else:
            size *= 0.9
    foot = rows[fi]
    head = max([r for r in rows if r <= top] or [rows[0]])
    right = max(compose.box_of(dict(x, size=t["size"], face=t["face"]))[2] for x in t["lines"]) + pad
    edge = min([c for c in cols if c >= right] or [cols[-1]])
    dark, light = sorted(("ink", "paper"), key=lambda r: legible.lum(role(colors, r)))
    if t["label"]:
        t["label"]["y"] = round(head + pad + t["label"]["size"], 1)
        keep = (legible.ratio(legible.lum(role(colors, lab["color"])), legible.lum(role(colors, dark)))
                >= legible.need(t["label"]["size"], min(fr.W, fr.H)))
        t["label"]["color"] = lab["color"] if keep else light
    return dict(t, color=light, italic=italic, enter=ln["enter"], at=0.5,
                panel={"box": [round(m, 1), round(head, 1), round(edge, 1), round(foot, 1)], "color": dark})


def text_boxes(t):
    """Every line of a beat's text as box_of measures it."""
    if not t:
        return []
    lns = [dict(x, size=t["size"], face=t["face"]) for x in t["lines"]]
    if t.get("label"):
        lns.append({"text": t["label"]["text"], "x": t["label"]["x"], "y": t["label"]["y"], "size": t["label"]["size"],
                    "face": t["label"]["face"]})
    return [compose.box_of(ln) for ln in lns]


# ------------------------------------------------------------------ captions a phone shows legibly
def around(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def place_of(pic, push=1.0):
    """Where a beat's photograph lies in the frame, [x, y, w, h] px, as the film lays it (Film.tsx cropOf and
    placeOf): the photograph covering its box, `zoom` times closer and `push` times closer again, around its subject."""
    x0, y0, x1, y1 = pic["box"]
    rb = (y1 - y0) / (x1 - x0)
    su, sv = (1.0, rb / pic["aspect"]) if pic["aspect"] > rb else (pic["aspect"] / rb, 1.0)
    z = pic["zoom"] * push
    su, sv = su / z, sv / z
    s = pic.get("subject") or []
    cx, cy = s[:2] if len(s) >= 2 else (0.5, 0.45)
    u0, t0 = min(1 - su, max(0, cx - su / 2)), min(1 - sv, max(0, cy - sv / 2))
    w, h = (x1 - x0) / su, (y1 - y0) / sv
    return [x0 - u0 * w, y0 - t0 * h, w, h]


def quarters_under(fr, pic, boxes):
    """The quarters (legible.quarters) of the photograph `pic` under words whose boxes are `boxes`, where they cover it
    inside the frame, as it lies on the beat's first frame and on its last, the film's slow push between; [] where the
    words stand off it."""
    a, b = around(boxes), pic["box"]
    box = [max(a[0], b[0], 0), max(a[1], b[1], 0), min(a[2], b[2], fr.W), min(a[3], b[3], fr.H)]
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return []
    return [q for q in (legible.under(pic["file"], place_of(pic, push), box) for push in (1.0, PUSH)) if q]


def shade_at(scrim, y, H):
    """How deep the beat's scrim is at height `y` px: from nothing at its top to its depth over a sixth of the frame,
    nothing outside it (Film.tsx Shade)."""
    if not scrim or not scrim["from"] <= y <= scrim["to"]:
        return 0.0
    return scrim["dark"] * min(1.0, (y - scrim["from"]) / min(H / 6, max(1, scrim["to"] - scrim["from"])))


def under_words(fr, pic, t, line, label):
    """A beat's label in `label` and its lines in `line` over the photograph `pic`: [(which, text, color role, size px,
    top px, quarters)], the label first; words that stand off the photograph are left out."""
    sets = [("label", t["label"]["text"], label, t["label"]["size"], [compose.box_of(t["label"])])] if t.get("label") else []
    if t["lines"]:
        sets.append(("line", " ".join(x["text"] for x in t["lines"]), line, t["size"],
                     [compose.box_of(dict(x, size=t["size"], face=t["face"])) for x in t["lines"]]))
    out = []
    for which, text, color, size, boxes in sets:
        q = quarters_under(fr, pic, boxes)
        if q:
            out.append((which, text, color, size, around(boxes)[1], q))
    return out


def reading(color, q, scrim):
    """The contrast words of `color` read at over every one of quarters `q` under a black scrim of depth `scrim`,
    the worst: the scrim is drawn over the photograph in the page's encoded color, so it blends in sRGB."""
    return min(legible.contrast(color, x, scrim, linear=False) for x in q)


def deepest(color, q, want, least):
    """The shallowest scrim, `least` or deeper, under which words of `color` read at `want` over every one of
    quarters `q`; None when legible.SCRIM_MOST does not."""
    s = [legible.scrim_for(color, x, want, least, linear=False) for x in q]
    return None if None in s else max(s)


def on_black(color, want):
    """Whether words of `color` read at `want` on black: the only words a black scrim helps."""
    return legible.ratio(legible.lum(color), 0.0) >= want


def shade_words(fr, pic, t, dark, line, label, colors):
    """The scrim depth a beat's words lie under over the photograph `pic` and its label's color role, so its label and
    its line each read on the photograph under them at the contrast their size needs on a phone (legible.py): the
    card's depth `dark` and colors where they read; a label that does not read in its own color takes the line's; light
    words that still do not read deepen the scrim, up to legible.SCRIM_MOST. A black scrim never helps dark words, so the
    check names those, and anything past the deepest scrim."""
    wide = min(fr.W, fr.H)
    for which, _, color, size, _, q in under_words(fr, pic, t, line, label):
        want = legible.need(size, wide)
        if which == "label" and reading(role(colors, color), q, dark) < want:
            label = color = line
        if on_black(role(colors, color), want) and reading(role(colors, color), q, dark) < want:
            dark = deepest(role(colors, color), q, want, dark) or legible.SCRIM_MOST
    return round(dark, 2), label


def legibility(fr, x, colors):
    """What of beat `x`'s words a phone does not show legibly: a line set under legible.LEAST, and a label or line
    that does not read at the contrast its size needs against what stands behind it: its panel, else the photograph
    under it at the beat's scrim, on the beat's first frame and on its last."""
    t = x.get("text")
    if not t:
        return []
    wide = min(fr.W, fr.H)
    lab = t.get("label")
    out = [f'{x["id"]}: "{text}" is set at {size:g} px, under the {legible.LEAST} px a phone shows legibly'
           for text, size in ([(lab["text"], lab["size"])] if lab else []) + [(ln["text"], t["size"]) for ln in t["lines"]]
           if size < round(legible.LEAST * wide / 1080)]
    if t.get("panel"):
        back = legible.lum(role(colors, t["panel"]["color"]))
        for text, color, size in ([(lab["text"], lab["color"], lab["size"])] if lab else []) + [
                (" ".join(ln["text"] for ln in t["lines"]), t["color"], t["size"])]:
            r, want = legible.ratio(legible.lum(role(colors, color)), back), legible.need(size, wide)
            if r < want:
                out.append(f'{x["id"]}: "{text}" reads {r:.1f}:1 on its panel, under the {want:g}:1 a {size:g} px line needs on '
                           "a phone: set it in the card's other ink")
        return out
    if not x.get("picture"):
        return out
    for _, text, color, size, top, q in under_words(fr, x["picture"], t, t["color"], lab and lab["color"]):
        s, want, hexc = round(shade_at(x.get("scrim"), top, fr.H), 2), legible.need(size, wide), role(colors, color)
        r = reading(hexc, q, s)
        if r >= want:
            continue
        deeper = deepest(hexc, q, want, s)
        why = ("a black scrim never helps dark words: set them in the card's light color" if not on_black(hexc, want)
               else "even the deepest scrim does not make them read: give the beat a photograph that is darker under its words"
               if deeper is None else f"under a scrim of {deeper:g} they read: draft the board again")
        out.append(f'{x["id"]}: "{text}" reads {r:.1f}:1 over the photograph under it (scrim {s:g}), under the {want:g}:1 '
                   f"a {size:g} px line needs on a phone: {why}")
    return out


# ------------------------------------------------------------------ the story as beats
def tags_of(b):
    """What a beat is, in the words a card's `fits` uses: its form, words or wordless, and for a photograph portrait or
    landscape, the story's peak, people in it, a place named."""
    tags = {b["form"]}
    if b.get("photo"):
        tags.add("photo")
        tags.add("portrait" if b["photo"]["aspect"] > 1 else "landscape")
    tags.add("words" if b.get("say") else "wordless")
    if b.get("peak"):
        tags.add("peak")
    if b.get("people"):
        tags.add("people")
    if b.get("place"):
        tags.add("place")
    return tags


def frame_taken(move):
    """Seconds `move` holds the whole frame before the photograph is back in view, 0 for a move that leaves the
    photograph in view."""
    f = MOVES / f"{move}.tsx"
    text = f.read_text() if move and f.is_file() else ""
    if "'../arrival'" not in text:
        return 0.0
    m = re.search(r"arrivalOf\(p,\s*([0-9.]+)\)", text)
    return (float(m.group(1)) if m else COUNTED) + HANDBACK


def lands_at(move, seconds):
    """Seconds into a beat of `seconds` its photograph lands: a frame-taking move flies it in and lands it at its
    arrivalOf time, or within the first part of a short beat (arrival.tsx); any other move cuts to it."""
    f = MOVES / f"{move}.tsx"
    m = re.search(r"arrivalOf\(p,\s*([0-9.]+)\)", f.read_text()) if move and f.is_file() else None
    return min(float(m.group(1)), 0.55 * seconds) if m else 0.0


def pick(options, tags, form, used, avoid, prefer=()):
    """The option whose `fits` matches the beat best: one in `prefer` made for the beat (it fits the beat's form, or
    the peak and the beat is the peak) first, then one that fits the beat's form before any that does not, then the
    most of its other tags; between equals the one used least so far, then the card's order. The options in `avoid`
    are never picked while another exists."""
    avoid = set(avoid or ())
    pool = [o for o in options if o["id"] not in avoid] or options
    made = lambda o: form in o["fits"] or ("peak" in tags and "peak" in o["fits"])
    score = lambda o: (o["id"] in prefer and made(o), form in o["fits"], len((tags - {form}) & set(o["fits"])))
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def story(run, c, bpm):
    """The beats of the film in `c`'s look, before layout: [{id, form, say, label, photo, peak, people, place, beats,
    move, transition}]. Lengths are in musical beats at `bpm`."""
    shot = PACE.get(c["axes"]["camera"], SHOT)
    nb = lambda sec: max(2, round(sec * bpm / 60))
    ph = run.d["photos"]
    hook_photo = ph.get(run.d.get("hook")) or ph[run.story[0]["photo"]]
    moments = list(run.story)
    peak = moments[-1]
    beats = [{"id": "hook", "form": "title", "say": run.hook, "label": run.handle, "photo": hook_photo, "peak": False}]
    for i, m in enumerate(moments):
        beats.append({"id": f"p{i + 1:02d}", "form": "photo", "say": clean(m.get("line")), "label": clean(m.get("pillar")),
                      "photo": ph[m["photo"]], "peak": m is peak, "people": m.get("people"), "place": m.get("place"),
                      "likes": m.get("likes") or 0})
    if run.question:
        beats.append({"id": "ask", "form": "words", "say": run.question, "label": "", "photo": ph[peak["photo"]], "peak": False})
    beats.append({"id": "closer", "form": "closer", "say": run.signoff, "label": run.handle, "photo": None, "peak": False})

    takes = {o["id"] for o in c["moves"] if frame_taken(o["id"])}
    energetic = c["axes"]["camera"] in ENERGETIC

    def give(beats):
        """Each beat's move and its cut in, in order, never the move of the beat before, and never the one move that
        fits the next beat's form: a move made for another form draws nothing on that beat. The peak takes a move that
        takes the frame when the card has one for it; an energetic look takes one on every other photo beat back from
        the peak too, and a calm look on no other beat. Each move that takes the frame plays once a film, and the one
        the peak takes is kept for the peak, so an energetic look whose card has one such move plays it on the peak
        alone. A move the card marks `once` plays at most once a film and wins the peak: the peak takes the `once`
        move made for a photograph when the card has one, and no beat before it plays that move. The counter plays only
        on a line that says a number, and a move that sets the beat's words only on a beat that has some."""
        moves, cuts, prev = {}, {}, None
        top = next((i for i, b in enumerate(beats) if b["peak"]), len(beats))
        once = {o["id"] for o in c["moves"] if o.get("once")}
        held = [o["id"] for o in c["moves"] if o["id"] in once and "photo" in o["fits"]]
        kept = pick(c["moves"], tags_of(beats[top]), "photo", {}, None, held or takes) if top < len(beats) else None
        for i, b in enumerate(beats):
            tags = tags_of(b)
            nxt = [o["id"] for o in c["moves"] if i + 1 < len(beats) and beats[i + 1]["form"] in o["fits"]]
            avoid = {prev, *nxt[:1]} if len(nxt) == 1 else {prev}
            if not NUMBER.search(b["say"] or ""):
                avoid.add("counter")
            if not (b["say"] or "").strip():
                avoid.add("slam-words")
            wants = b["form"] == "photo" and (i == top or (energetic and (top - i) % 2 == 0))
            if not (wants or energetic):
                avoid |= takes
            elif i != top:
                avoid |= {t for t in takes if t == kept or t in moves}
            avoid |= {o for o in once if o in moves or (o == kept and i != top)}
            b["move"] = kept if i == top and kept else pick(c["moves"], tags, b["form"], moves, avoid, takes if wants else ())
            if i == top and kept:
                moves[kept] = moves.get(kept, 0) + 1
            b["transition"] = None if i == 0 else pick(c["transitions"], tags, b["form"], cuts, None)
            prev = b["move"]

    # the cuts quicken into the peak: the first moment before it holds QUICKEN beats longer than the card's shot, the
    # next one a beat less, down to the shot; the extra beats go before any moment is left out, and come back to the
    # moments that stay once one is
    quicken = QUICKEN
    def length(b):
        if b["form"] == "title":
            return max(nb(shot * 1.2), len(b["say"].split()) + 2) if b["move"] in SETS_WORDS else nb(shot * 1.3)
        if b["form"] == "photo":
            n = len(b["say"].split())
            own = nb(shot * (1.4 if b["peak"] else 1.0) + (0.3 * max(0, n - 6)))
            if not b["peak"]:
                middle = [x for x in beats if x["form"] == "photo" and not x["peak"]]
                own += max(0, quicken - middle.index(b))
            # a move that takes the frame holds its beat past the landing, long enough to read the line after it
            taken = frame_taken(b["move"])
            return max(own, nb(taken + max(1.6, 0.9 + 0.3 * n))) if taken else own
        if b["form"] == "words":
            # the question holds as long as it takes to read twice, never a fixed count of beats: at a slow tempo a
            # count of beats leaves a short question alone on the ground for seconds after it is read
            return nb(max(2.4, 1.2 + 0.3 * len(b["say"].split())))
        # the closer is their name and handle: a slow card's pace never stretches it past the default shot's hold, so
        # the time goes to a moment instead
        return nb(min(shot, SHOT) * 1.2 + HOLD)
    def fit():
        give(beats)
        for b in beats:
            b["beats"] = length(b)
    fit()
    # the moments the story cannot fit go, the least liked first; the peak stays. The moves are given again to the
    # beats that stay, so the beats either side of a dropped moment never repeat one, and every length follows its move
    while sum(b["beats"] for b in beats) * 60 / bpm > MOST_SECONDS:
        if quicken:
            quicken -= 1
            fit()
            continue
        middle = [b for b in beats if b["form"] == "photo" and not b["peak"]]
        if not middle:
            break
        beats.remove(min(middle, key=lambda b: (b["likes"], b["id"])))
        quicken = QUICKEN
        fit()
    return beats


def shown(c, photo):
    """`photo` as a card shows it: a card whose finish is flat or clean shows the photograph as it was posted, its own
    finish the only treatment over it; any other card shows it under the film's grade."""
    if photo and photo.get("posted") and c["axes"]["finish"] in AS_POSTED:
        return dict(photo, file=photo["posted"])
    return photo


def lay(run, c, colors, fr, b):
    """One beat's picture, ground, scrim and text, as the film draws them."""
    lay = c["photo"]
    # the picture is the photograph (a clip's still); the clip itself is the beat's own record (board_for)
    photo = {k: v for k, v in (shown(c, b.get("photo")) or {}).items() if k != "clip"} or None
    pic, ln, lab = lay["picture"], lay["line"], lay["label"]
    out = {"picture": None, "ground": role(colors, lay["ground"]), "scrim": None, "text": None}
    if b["form"] == "photo":
        pic, ln = layout_of(lay, b["photo"], fr)
        box = picture_box(fr, pic)
        if pic["show"]:
            out["picture"] = dict(photo, box=box, zoom=ZOOM)
        lb = line_box(fr, ln["box"])
        if b["move"] in BANDS:
            (above, below), h = BANDS[b["move"]]
            pad = 0.03 * fr.H
            lb = [lb[0], round(max(lb[1], above * fr.H + h * fr.W / 1080 + pad), 1), lb[2], round(min(lb[3], below * fr.H - pad), 1)]
        if b["move"] in HEADS and pic["show"]:
            heavy, gap = HEADS[b["move"]]
            lb = [lb[0], lb[1], lb[2], round(min(lb[3], box[1] - (heavy + 2 * gap) * fr.W / 1080), 1)]
        ground, line, label = lay["ground"], ln["color"], lab["color"]
        if not pic["show"] and b.get("turn", 0) % 2:
            # type alone: every other moment turns the ground and the line round, so the beats read as a sequence
            ground, line = line, ground
            label = line if legible.ratio(legible.lum(role(colors, label)), legible.lum(role(colors, ground))) < 3 else label
            out["ground"] = role(colors, ground)
        # a line the card sets at display size keeps its size over more lines: a poster's words, not a caption's; a
        # moment's line starts from the film's caption size when one is given (board_for)
        t = set_text(fr, b["say"], lb, ln["face"], b.get("caption") or ln["size"], ln["align"], b["label"] or None, lab,
                     most=BIG_LINES if ln["size"] >= 100 else 3)
        if b["move"] in OWN_LINE:
            return out
        dark = ln["scrim"]
        if pic["show"] and t["lines"]:
            # the words read on the photograph under them: the card's scrim and colors where they do, else the label
            # in the line's color and the scrim as deep as the words need
            dark, label = shade_words(fr, out["picture"], t, dark, line, label, colors)
        if t["label"]:
            t["label"]["color"] = label
        out["text"] = dict(t, color=line, enter=ln["enter"], at=0.25)
        if pic["show"] and dark > 0 and t["lines"]:
            # the scrim reaches its depth at the words' top
            top = min(bx[1] for bx in text_boxes(t)) - fr.H / 6
            out["scrim"] = {"from": round(top, 1), "to": round(min(fr.H, box[3]), 1), "dark": dark}
        return out
    if b["form"] == "title":
        full = [-0.06 * fr.W, -0.06 * fr.H, 1.06 * fr.W, 1.06 * fr.H]
        out["picture"] = dict(photo, box=[round(v, 1) for v in full], zoom=ZOOM)
        if sets_words(b, fr):
            return out
        a = fr.area
        lb = line_box(fr, ln["box"])
        if b["move"] in WINDOWS:
            top, foot = WINDOWS[b["move"]]
            pad = 0.03 * fr.H
            lb = [lb[0], max(lb[1], top * fr.H + pad), lb[2], min(lb[3], (1 - foot) * fr.H - pad)]
        box = [a[0], max(min(lb[1], lb[3] - 0.32 * (a[3] - a[1])), a[1]), a[2], lb[3]]
        italic = bool(compose.face_of("display").get("italic")) and ln["face"] == "display"
        # a hook too long for its box at half its size comes down as far as half the card's line, so no word of it
        # stands alone on a line
        t = set_text(fr, b["say"], box, ln["face"], ln["size"] * TITLE_K * (1.0 if ln["size"] >= 100 else 1.4),
                     ln["align"], b["label"] or None, lab, bottom=True, least=ln["size"] / 2)
        if b["move"] in HAIRLINES:
            out["text"] = on_panel(fr, lay["grid"], b, t, box, ln, lab, colors, italic)
            return out
        color, label_color = ln["color"], lab["color"]
        wide = min(fr.W, fr.H)
        if any(reading(role(colors, c), q, 0.0) < legible.need(size, wide)
               for _, _, c, size, _, q in under_words(fr, out["picture"], t, color, label_color)):
            # the card's colors do not read on the photograph under the words: the lightest of its line color, paper
            # and ink, over a scrim as deep as the words need, from TITLE_SCRIM; the scrim reaches its depth at the
            # words' top
            color = label_color = max((ln["color"], "paper", "ink"), key=lambda r: legible.lum(role(colors, r)))
            dark, label_color = shade_words(fr, out["picture"], t, TITLE_SCRIM, color, label_color, colors)
            top = min(bx[1] for bx in text_boxes(t)) - fr.H / 6
            out["scrim"] = {"from": round(top, 1), "to": round(fr.H * 1.06, 1), "dark": dark}
        if t["label"]:
            t["label"]["color"] = label_color
        out["text"] = dict(t, color=color, italic=italic, enter=ln["enter"], at=0.5)
        return out
    if b["form"] == "words":
        if b["move"] in MASKS:
            # the photograph the mask shows inside its letters
            out["picture"] = dict(photo, box=[round(-0.06 * fr.W, 1), round(-0.06 * fr.H, 1), round(1.06 * fr.W, 1),
                                                   round(1.06 * fr.H, 1)], zoom=ZOOM)
        if sets_words(b, fr):
            return out
        if b["move"] in SETS_WORDS:
            # where the move would have set the words as a poster across the measure it draws nothing, so the kit sets
            # them across the type area's measure, as large as its upper part holds, from the beat's first frame
            a = fr.area
            t = set_text(fr, b["say"], [a[0], a[1], a[2], a[1] + 0.7 * (a[3] - a[1])], ln["face"], ln["size"] * TITLE_K * 1.4, "start")
            out["text"] = dict(t, color=ln["color"], enter=ln["enter"], at=0)
            return out
        lb = line_box(fr, ln["box"])
        t = set_text(fr, b["say"], lb, ln["face"], ln["size"] * ASK_K, ln["align"])
        out["text"] = dict(t, color=ln["color"], enter=ln["enter"], at=0.4)
        return out
    return out


def sets_words(b, fr):
    """Whether beat `b`'s move sets its words itself on frame `fr`: every move in SETS_WORDS does but one that sizes them
    by the measure's width alone on a frame wider than it is tall; there the kit sets them and the move draws none."""
    return b["move"] in SETS_WORDS and not (b["move"] in WIDTH_SIZED and fr.W > fr.H)


def board_for(run, letter, style, fmt, bpm=None):
    """Board `letter` in `style` for format `fmt`, and its plan: {board, seconds, frames, cuts, hook_frame, rests}."""
    c = compose.card(style)
    compose.use(style)
    lo, hi = music_tempo(c)
    bpm = bpm or round((lo + hi) / 2)
    fr = compose.Frame(fmt)
    colors = run.colors(c)
    beats = story(run, c, bpm)
    pulse = compose.pulse_of(bpm)
    out, at = [], 0
    for b in beats:
        f0, f1 = round(at * pulse), round((at + b["beats"]) * pulse)
        rec = {"id": b["id"], "form": b["form"], "start": at, "beats": b["beats"], "bars": b["beats"] / 4, "frames": f1 - f0,
               "pulse": round(pulse, 4), "move": b["move"], "transition": b["transition"], "peak": b["peak"],
               "words": b["say"] if (sets_words(b, fr) and b["form"] in ("title", "words")) else "",
               "label": mask_word(b["say"]) if (b["move"] in MASKS and b["form"] == "photo") else "", "say": b["say"], "pillar": b["label"] if b["form"] == "photo" else ""}
        rec.update(lay(run, c, colors, fr, dict(b, turn=sum(1 for x in out if x["form"] == "photo"))))
        clip = (b.get("photo") or {}).get("clip") if b["form"] == "photo" else None
        if clip:
            # a moment from a reel plays its recorded clip as the beat's one shot from its strongest second; the move
            # and the arrival are the photograph's, and a move that takes the frame flies in the clip's first frame
            # (the still) and hands the frame back to it, so the clip runs from the hand back to the beat's end
            import material
            hold = min(rec["frames"] - 1, round(frame_taken(b["move"]) * FPS))
            rec["clip"] = dict(material.clip_frames(clip, (rec["frames"] - hold) / FPS, FPS, posted=c["axes"]["finish"] in AS_POSTED),
                               hold=hold)
        taken = frame_taken(b["move"]) * bpm / 60
        if taken and rec["text"] and b["form"] == "photo":
            # a move that takes the frame hands the photograph back before its line comes on, so the line reads after it
            rec["text"]["at"] = round(max(rec["text"]["at"], taken), 3)
        rec["layers"] = []
        out.append(rec)
        at += b["beats"]
    # every moment's line is set at one size, the size the longest line came down to, so the captions read as one set;
    # a look of the type family keeps each line at its own scale, where the type is the picture
    k = min(fr.W, fr.H) / 1080
    sized = [(b, r) for b, r in zip(beats, out) if b["form"] == "photo" and r["text"] and c["axes"]["family"] != "type"]
    cap = min((r["text"]["size"] for _, r in sized), default=None)
    for b, r in sized:
        if r["text"]["size"] != cap:
            again = lay(run, c, colors, fr, dict(b, turn=sum(1 for x in out[:out.index(r)] if x["form"] == "photo"), caption=cap / k))
            r["text"] = dict(again["text"], at=r["text"]["at"])
            r["scrim"] = again["scrim"]
    frames = round(at * pulse)
    closer = out[-1]
    shot = PACE.get(c["axes"]["camera"], SHOT)
    still = closer["start"] + max(1, round(shot * 1.2 * bpm / 60))
    for i, b in enumerate(out):
        # a beat rests before the cut out of it begins to cover it
        clear = b["beats"] - 0.2 - (cut_beats(out[i + 1]["transition"]) / 2 if i + 1 < len(out) else 0)
        if b["form"] == "title":
            words = len(b["say"].split())
            settle = (words + 0.6) if b["words"] else (b["text"] or {}).get("at", 0) + 1.2
        elif b["form"] == "closer":
            settle = still - b["start"] + 0.5
        else:
            settle = b["beats"] - 0.4
        b["rest"] = max(0, min(b["frames"] - 1, round(min(settle, clear) * pulse)))
    # the effects are the shared sound layer's, laid from the beats themselves (effects_board); the board's own cue is
    # the stop, where a look whose cuts are hard cuts its music
    sound = []
    if c["axes"]["transition"] == "cut":
        sound.append({"kind": "stop", "at": still, "beat": "closer", "what": "the music stops on the sign-off"})
    for q in sound:
        q["frame"] = round(q["at"] * pulse)
    board = {"id": f"{letter}-{fmt}", "letter": letter, "style": style, "name": c["name"], "title": run.hook,
             "handle": run.handle, "signoff": run.signoff, "bpm": bpm, "format": fr.format, "fps": FPS,
             "system": compose.system(c, colors), "closer": {"at": closer["start"], "still": still}, "sound": sound, "beats": out}
    compose.set_lines(board["beats"])
    starts = [round(b["start"] * pulse) for b in out]
    first = out[0]
    hook_at = 0.15 if first["words"] else (first.get("text") or {}).get("at", 0.5)
    rests = {"hook": starts[0] + first["rest"], "closer": starts[-1] + closer["rest"]}
    mids = [i for i, b in enumerate(out) if b["form"] == "photo"]
    if mids:
        k = mids[len(mids) // 2]
        rests["middle"] = starts[k] + out[k]["rest"]
        top = next((i for i in mids if out[i]["peak"]), k)
        rests["peak"] = starts[top] + out[top]["rest"]
    return {"board": board, "seconds": round(frames / FPS, 2), "frames": frames, "cuts": [round(s / FPS, 2) for s in starts[1:]],
            "hook_frame": round(hook_at * pulse), "rests": rests}


def effects_board(board):
    """`board` as the shared sound effects read it (sfx.py): each beat one layer of its kind (Title, Photo, Words,
    Closer) with the moments its picture lands, in musical beats from the film's start. The title lands where its words
    land, a photograph where its move lands it, and the words slammed by a move are the beat's line."""
    sec = 60 / board["bpm"]
    beats = []
    for b in board["beats"]:
        s, e = b["start"], b["start"] + b["beats"]
        kind = {"title": "Title", "photo": "Photo", "words": "Words", "closer": "Closer"}.get(b["form"], "Photo")
        ly = {"kind": kind, "at": {"arrive": round(s + lands_at(b["move"], b["beats"] * sec) / sec, 4), "start": s, "end": e}}
        if kind == "Title":
            ly["title"] = {"text": b["say"]}
            ly["slam"] = [s, 0.25 if b.get("words") or not b.get("text") else b["text"]["at"]]
        elif kind == "Photo":
            ly["label"] = b["say"]
        elif kind == "Words":
            ly["text"] = b["say"]
        else:
            ly["signoff"] = {"text": b["say"]}
        beats.append({"id": b["id"], "form": b["form"], "start": s, "move": b["move"], "transition": b["transition"], "layers": [ly]})
    return {"id": board["id"], "bpm": board["bpm"], "beats": beats}


def cut_beats(name):
    """How many musical beats the cut `name` plays over, centered on the moment of the cut (its `beats` in
    motion/system/moves/cut/<name>.tsx)."""
    if not name:
        return 0.0
    f = _env.SKILL / "motion" / "system" / "moves" / "cut" / f"{name}.tsx"
    m = re.search(r"beats:\s*([0-9.]+)", f.read_text()) if f.is_file() else None
    return float(m.group(1)) if m else 0.0


def music_tempo(c):
    book = json.loads((_env.SKILL / "music" / "recipes.json").read_text())
    r = book["recipes"].get(c["music"]) or book["recipes"][book["default"]]
    return r["tempo"]


def board_hash(boards):
    return hashlib.sha256(json.dumps(boards, sort_keys=True).encode()).hexdigest()[:16]


def write_board(run, letter, style, bpm=None):
    d = BOARDS / letter
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.json").unlink(missing_ok=True)
    plans = {fmt: board_for(run, letter, style, fmt, bpm) for fmt in compose.FORMATS}
    for fmt, p in plans.items():
        _env.write_json(d / f"board-{fmt}.json", p["board"])
    write_md(d, plans["reel"])
    _env.write_json(d / "plan.json", {"style": style, **{fmt: {k: v for k, v in p.items() if k != "board"} for fmt, p in plans.items()}})
    return plans


def write_md(d, p):
    b = p["board"]
    sec = 60 / b["bpm"]
    L = [f"# {b['letter'].upper()}: {b['name']}", "",
         f"{len(b['beats'])} beats, {b['bpm']} bpm, {p['seconds']} s, {len(p['cuts'])} cuts, the hook at frame {p['hook_frame']}.", "",
         "| beat | starts | seconds | move | cut in | words |", "|---|---|---|---|---|---|"]
    for x in b["beats"]:
        said = " / ".join(ln["text"] for ln in (x.get("text") or {}).get("lines", [])) or x["words"]
        L.append(f"| {x['id']} | {x['start'] * sec:.2f} s | {x['beats'] * sec:.2f} | {x['move']} | {x['transition'] or ''} | {said[:80]} |")
    music = _env.read_json("music.json") or {}
    import sfx
    fx = sfx.events(effects_board(b), sfx.music_of(b, music)[0])[0]
    L += ["", "Music: " + (music.get("origin") or "not made yet (music.py make)") + ".",
          "Mixed: " + (f"bed {music['bed_lufs']} LUFS, effects {music['fx_lufs']} LUFS, master {music['master_lufs']} LUFS"
                       if music.get("master_lufs") is not None and music.get("bed_lufs") is not None else "not yet") + ".",
          "", f"Sound ({len(fx)} effects on the music's grid): " + ", ".join(f"{k} at {t:.2f} s" for t, k in fx)
          + "".join(f"; the music {q['what'].split('music ', 1)[-1]} at {q['at'] * sec:.2f} s" for q in b["sound"])]
    _env.write_text(d / "storyboard.md", "\n".join(L) + "\n")


def load_plans(letter):
    d = BOARDS / letter
    meta = _env.read_json(d / "plan.json")
    if not meta:
        sys.exit(f"{d}/plan.json is missing: run storyboard.py draft")
    return {fmt: dict(meta[fmt], board=_env.read_json(d / f"board-{fmt}.json")) for fmt in compose.FORMATS}


def letters():
    return [l for l in compose.LETTERS if (BOARDS / l / "plan.json").exists()]


# ------------------------------------------------------------------ check
def hexes_in(o):
    if isinstance(o, dict):
        return [h for v in o.values() for h in hexes_in(v)]
    if isinstance(o, list):
        return [h for v in o for h in hexes_in(v)]
    return [o.lower()] if isinstance(o, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", o) else []


def findings(run, plans):
    out = []
    lo, hi = LENGTH
    for fmt, p in plans.items():
        b = p["board"]
        c = compose.card(b["style"])
        compose.use(b["style"])
        fr = compose.Frame(fmt)
        a = fr.area
        made = set(__import__("palette").palette_of(c["palette"], run.swatches)["made"])
        colors = b["system"]["colors"]
        if not lo <= p["seconds"] <= hi:
            out.append(f"{fmt}: {p['seconds']} s is outside {lo}-{hi} s")
        if p["hook_frame"] > HOOK_FRAMES:
            out.append(f"{fmt}: the hook lands at frame {p['hook_frame']}, after frame {HOOK_FRAMES}")
        for k in ("display", "text"):
            if b["system"][k]["file"] != c["faces"][k]["file"]:
                out.append(f"{fmt}: the {k} face is not the card's")
        bad = sorted(set(hexes_in(b["beats"]) + hexes_in(b["system"]["colors"])) - made)
        if bad:
            out.append(f"{fmt}: colors the card's palette rule did not make: {', '.join(bad)}")
        prev = None
        for x in b["beats"]:
            if x["move"] not in compose.ids(c, "moves"):
                out.append(f"{fmt} {x['id']}: the move {x['move']} is not the card's")
            if x["transition"] and x["transition"] not in compose.ids(c, "transitions"):
                out.append(f"{fmt} {x['id']}: the cut {x['transition']} is not the card's")
            if x["move"] == prev:
                out.append(f"{fmt} {x['id']}: the same move as the beat before ({prev})")
            prev = x["move"]
            out += [f"{fmt} {f}" for f in legibility(fr, x, colors)]
            for bx in text_boxes(x.get("text")):
                if bx[0] < a[0] - 1 or bx[2] > a[2] + 1 or bx[1] < a[1] - 1 or bx[3] > a[3] + 1:
                    out.append(f"{fmt} {x['id']}: a line runs outside the type area ({', '.join(f'{v:.0f}' for v in bx)})")
                    break
            if x["form"] == "photo" and x.get("text"):
                lb = x["text"]["box"]
                for bx in text_boxes(x["text"]):
                    if bx[0] < lb[0] - 2 or bx[2] > lb[2] + 2 or bx[3] > lb[3] + 2:
                        out.append(f"{fmt} {x['id']}: the line overruns the card's line box")
                        break
                if len(x["text"]["lines"]) > (BIG_LINES if c["photo"]["line"]["size"] >= 100 else 3):
                    out.append(f"{fmt} {x['id']}: the line is too long for the card's line box")
    return out


def style_findings(boards):
    """The three looks against each other: two axes shared at most between any two."""
    out = []
    for i, a in enumerate(boards):
        for b in boards[i + 1:]:
            shared = compose.shared_axes(a, b)
            if len(shared) > 2:
                out.append(f"{a} and {b} share {len(shared)} axes ({', '.join(shared)})")
    return out


# ------------------------------------------------------------------ commands
def cmd_draft(a, run):
    import material
    olds = [*CUT_SET, Path("winner.json"), Path("vote/scores.json"), Path("film.json"), Path("out/boards.png")]
    olds += [BOARDS / l / n for l in compose.LETTERS for n in ("plan.json", "sheet.png")]
    for old in olds:
        if old.exists():
            old.unlink()
    run = Run(material.build())
    for letter, style in zip(compose.LETTERS, run.trio):
        plans = write_board(run, letter, style)
        bad = findings(run, plans)
        r = plans["reel"]
        print(f"{letter.upper()} {style}: {r['seconds']} s, {len(r['board']['beats'])} beats, {len(r['cuts'])} cuts, "
              f"{len(bad)} findings -> {BOARDS / letter}/")
        for x in bad[:8]:
            print("   ", x)
    for x in style_findings(run.trio):
        print("   ", x)
    print("next: storyboard.py sheets, then show out/boards.png and ask which look")
    return 0


def cmd_check(a, run):
    bad = 0
    styles = []
    for letter in letters():
        plans = load_plans(letter)
        styles.append(plans["reel"]["board"]["style"])
        f = findings(run, plans)
        bad += len(f)
        print(f"{'PASS' if not f else 'FAIL'}  {letter.upper()} {styles[-1]}: {len(f)} findings")
        for x in f[:20]:
            print("   ", x)
    s = style_findings(styles)
    for x in s:
        print("FAIL ", x)
    return 1 if bad or s or not styles else 0


def cmd_sheets(a, run):
    import studio
    _env.need("PIL")
    from PIL import Image, ImageDraw
    jobs, picks = [], {}
    for letter in letters():
        (BOARDS / letter / "sheet.png").unlink(missing_ok=True)
        p = load_plans(letter)["reel"]
        picks[letter] = p
        for k in ("hook", "middle", "closer"):
            if k in p["rests"]:
                jobs.append(studio.still(p["board"], p["rests"][k], BOARDS / letter / "frames" / f"{k}.png", scale=0.5))
    Path("out/boards.png").unlink(missing_ok=True)
    rep = studio.render(jobs, "sheets")
    if rep["failed"]:
        studio.publish_report("sheets")
        print(f"a frame did not render; see render/sheets.log and {studio.report_of('sheets')}", file=sys.stderr)
        return 1
    rows = []
    for letter, p in picks.items():
        ims = [Image.open(BOARDS / letter / "frames" / f"{k}.png").convert("RGB") for k in ("hook", "middle", "closer") if k in p["rests"]]
        w, h = ims[0].size
        sheet = Image.new("RGB", (len(ims) * w + (len(ims) + 1) * 12, h + 24), "white")
        for i, im in enumerate(ims):
            sheet.paste(im, (12 + i * (w + 12), 12))
        tmp = _env.part(BOARDS / letter / "sheet.png")
        sheet.save(tmp)
        os.replace(tmp, BOARDS / letter / "sheet.png")
        rows.append((letter, p["board"], ims))
    # the person's sheet: the three looks side by side, each named by its letter and its plain name
    w, h = rows[0][2][0].size
    head = 96
    gap = 24
    page = Image.new("RGB", (len(rows) * w + (len(rows) + 1) * gap, head + 3 * h + 4 * gap), "#f4f2ee")
    d = ImageDraw.Draw(page)
    for i, (letter, b, ims) in enumerate(rows):
        x = gap + i * (w + gap)
        compose.use(b["style"])
        d.text((x, 24), f"{letter.upper()}  {b['name']}", fill="#141414", font=_env.pil_font(40, "display"))
        for j, im in enumerate(ims):
            page.paste(im, (x, head + gap + j * (h + gap)))
    Path("out").mkdir(exist_ok=True)
    tmp = _env.part(Path("out/boards.png"))
    page.save(tmp)
    os.replace(tmp, "out/boards.png")
    studio.publish_report("sheets")
    print(f"out/boards.png: the three looks, {', '.join(f'{l.upper()} {b['name']}' for l, b, _ in rows)}; "
          "show it and ask which look (vote.py pick <letter>)")
    return 0


def cmd_snap(a, run):
    letter = (_env.read_json("winner.json") or {}).get("board")
    if letter not in letters():
        sys.exit("no look picked: show out/boards.png, then vote.py pick <letter>")
    style = load_plans(letter)["reel"]["board"]["style"]
    base = load_plans(letter)["reel"]["board"]["bpm"]
    music = _env.read_json("music.json") or {}
    lo, hi = LENGTH
    bpm, why = base, f"the look's tempo, {base} bpm (no music tempo)"
    if music.get("bpm"):
        best = None
        for k in (0.5, 1, 2):
            cand = round(music["bpm"] * k, 2)
            p = board_for(run, letter, style, "reel", cand)
            if lo <= p["seconds"] <= hi and (best is None or abs(cand - base) < abs(best - base)):
                best = cand
        if best:
            bpm, why = best, f"the music's {music['bpm']} bpm" + (f" at {best / music['bpm']:g}x" if best != music["bpm"] else "")
    for old in (*CUT_SET, Path("film.json")):
        old.unlink(missing_ok=True)
    plans = write_board(run, letter, style, bpm)
    import material
    # the clips' frames the drafts cut at their own tempo go; the film's are the ones its boards name
    keep = {x["clip"]["dir"] for p in plans.values() for x in p["board"]["beats"] if x.get("clip")}
    for d in material.CLIPS.glob("*") if material.CLIPS.is_dir() else ():
        if d.relative_to(material.PUB).as_posix() not in keep:
            shutil.rmtree(d, ignore_errors=True)
    bad = findings(run, plans)
    reel = plans["reel"]
    downs = music.get("downbeats") or []
    film = {"board": letter, "style": style, "name": reel["board"]["name"], "bpm": bpm, "tempo": why, "seconds": reel["seconds"],
            "frames": reel["frames"], "music_start": downs[0] if downs else 0.0, "hook_frame": reel["hook_frame"],
            "cuts": reel["cuts"], "rests": {fmt: p["rests"] for fmt, p in plans.items()},
            "boards": {fmt: str(BOARDS / letter / f"board-{fmt}.json") for fmt in compose.FORMATS}, "findings": bad,
            "hash": board_hash({fmt: p["board"] for fmt, p in plans.items()})}
    _env.write_json("film.json", film)
    print(f"{letter.upper()} {style} at {bpm} bpm ({why}): {reel['seconds']} s, {len(reel['cuts'])} cuts, hook at frame "
          f"{reel['hook_frame']}, {len(bad)} findings -> film.json")
    for x in bad[:10]:
        print("   ", x)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    a = ap.parse_args()
    _env.enter()
    run = Run() if a.cmd != "draft" else None
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
