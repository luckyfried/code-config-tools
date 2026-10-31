"""The hype reel's board in one style: the subject (a product, a drop, an event, a friend, an idea, or a thing the
person follows) built up in its own pictures and the person's, to the subject itself.

The story is the kit's and every style tells it the same way: the hook (the hook line over their photograph, or the
subject's hero still framed close under the hook line or the subject's name), the build (their photographs in the order
they took them, each with the line they wrote with it, the subject's other stills and its footage between them, each
still with its own words or one of the subject's facts, and close framings of the hero still where the build is short),
the reveal (the hero still whole under the subject's name, the peak), and the closer the style's card draws (the name,
the date as they wrote it for a launch or the punchline for anything else, the handle). The subject's own pictures fill
most of the time before the closer (SUBJECT_SHARE). The tone (TONES) sets how many beats the build has, how long each
holds, the case of the words and the cut the card reaches for first.

The style card decides everything else: the faces and their case, the colors (the card's palette rule over the
swatches), the move each beat makes and the cut into it (chosen from the beat's content within the card's allowlists,
never two beats running on one move), the camera, the finish, the closer, and the pace (the card's music recipe sets the
tempo, the card's family how long a beat holds). A photograph of the build whose words the kit sets is laid out the way
the card's photo layout says: the photograph in the card's box on the card's ground (or no photograph), the label and the
words in the card's line box, faces, sizes, colors and entrance, the card's shade under them. The hook covers the
frame, its words set in the family's grammar (FAMILY); the reveal sets its name off the picture where the card gives it
a place (a grid card's ground, a letterbox's lower matte) and over it elsewhere. Where a beat's move sets words of its
own, the kit sets none, except a move that lands them one a beat: the kit slams those itself, every word at one size
and whole in the frame. Every word on screen is theirs, the subject's name, the handle, or the date as they wrote it.

Every place on the board is px of the frame; every time is musical beats from the start of the beat. Beat lengths are
whole musical beats, so every cut, every landing and every hit falls on a beat of the music.
"""
import itertools
import math
import re
from pathlib import Path

import compose
import palette

W, H = 1080, 1920
CUTS = Path(__file__).resolve().parent.parent / "motion" / "system" / "moves" / "cut"
# seconds a part holds before its cut, by part; FAMILY's pace multiplies them
SECONDS = {"hook": 2.4, "build": 1.3, "build-words": 2.0, "detail": 1.1, "clip": 2.6, "made": 3.0, "closer": 3.4}
# the share of the time before the closer the subject's own pictures fill, at least
SUBJECT_SHARE = 0.55
# the close framings of a still where the build is short: DETAIL's zoom of covering the frame, closer for each next one,
# round points of the still's subject box
DETAIL = {"zoom": 1.9, "step": 0.25}
DETAIL_AT = ((0.34, 0.38), (0.66, 0.62), (0.5, 0.3))
BUILD_LEAST = 3
# each tone: `pace` multiplies every hold, `build` is the most beats the build has, `case` sets the words' case
# ("upper", or None for the person's own), `cuts` are the card's cuts it reaches for first where the card allows them
TONES = {
    "default": {"pace": 1.0, "build": 6, "case": None, "cuts": ("hard-cut", "slide", "flash-frame"), "say": "playful and clean"},
    "polished": {"pace": 1.25, "build": 4, "case": None, "cuts": ("long-dissolve", "long-fade", "dissolve"),
                 "say": "restrained, with slow fades"},
    "yc-parody": {"pace": 1.1, "build": 5, "case": None, "cuts": ("hard-cut",),
                  "say": "a deadpan startup launch, played completely straight"},
    "chaotic": {"pace": 0.7, "build": 8, "case": "upper", "cuts": ("flash-frame", "hard-cut", "slide"),
                "say": "fast and loud, all capitals, flash cuts"},
    "deadpan": {"pace": 1.35, "build": 3, "case": None, "cuts": ("hard-cut",), "say": "calm, with big empty space"},
    "cinematic": {"pace": 1.2, "build": 5, "case": "upper", "cuts": ("bars-close", "long-dissolve", "long-fade"),
                  "say": "trailer scale, big type"},
    "app-store": {"pace": 1.0, "build": 4, "case": None, "cuts": ("slide", "grid-wipe", "paper-slide", "hard-cut"),
                  "say": "clean feature cards, one claim each"},
}


def tone_of(ctx):
    """The film's tone from the plan (ctx `tone`), the default where it names none or one the kit does not have."""
    return TONES.get((ctx or {}).get("tone") or "default", TONES["default"])


HOOK_ZOOM = 1.3
LEADING = {"on", "off", "from", "in", "into", "with", "for", "out", "a", "an", "the", "to", "of", "and", "my", "your", "our"}
# moves that set words of their own (the beat's words, else its label): the kit sets none over them, and a beat with
# neither words nor a label never takes one. A move whose words fly with the photograph and leave as it lands
# (exploded-layers) is not one: the kit sets the beat's line once it has landed
SETS_WORDS = {"word-per-beat-slam", "type-mask-reveal", "width-stretch", "marquee", "stack-and-split", "long-fade-title",
              "rule-draw", "line-by-line-type-rise", "date-stamp", "doodle-draw-on", "polaroid-drop",
              "sticker-pop", "white-space-crop", "slam-words", "counter"}
# moves that count up to a number: one is taken only by a beat whose own words or label hold a number (in figures, or a
# word up to twelve), since with none the move would count to a number nobody said
COUNTS = {"counter"}
NUMBER = re.compile(r"\b(\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", re.I)
# moves that set the beat's label, else its first words, at most this many, and drop the rest: a beat whose words
# would not all reach the screen (words beside a label, or more words than the move sets) never takes one
SHORT = {"width-stretch": 2, "sticker-pop": 2}
# moves drawn on the photograph's box (a mat, its cells, a rule over its head): a beat of the build under one is laid
# out by the card's photo layout, words or none, and the kit sets its words in the card's line box; the hook and the
# reveal, which cover the frame, never take one
BOXED = {"crop-shift", "scale-to-cell", "cell-reveal", "rule-draw"}
# moves whose words leave as the move opens, under the cut into the beat, so they never read: a beat with words or a
# label never takes one, and its words stay on screen while it holds
PASSING = {"stack-and-split"}
# the least shade under words set over a whole-frame photograph
SHADE = 0.55
# moves whose field covers the picture for their whole beat: their time is not the subject's on screen
# the moves that never open the film: one that opens on a black frame (its first frame is its cover in the feed), and
# one that holds its words nearly still while their light comes up, so nothing arrives inside the first second
NOT_FIRST = {"bars-open", "long-fade-title"}
COVERS = {"word-per-beat-slam", "long-fade-title", "type-mask-reveal"}
# each family's words grammar: the face of the beat's words, the size wanted (px), where they sit, how many lines at
# most, the beats between one line landing and the next
FAMILY = {
    "type": {"face": "display", "want": 210, "lines": 4, "step": 0.25, "align": "left", "pace": 0.8},
    "cinema": {"face": "display", "want": 66, "lines": 2, "step": 0.5, "align": "center", "pace": 1.35},
    "grid": {"face": "display", "want": 168, "lines": 3, "step": 0.25, "align": "left", "pace": 1.0},
}


def family(card):
    return card["axes"]["family"] if card["axes"]["family"] in FAMILY else "type"


# ------------------------------------------------------------------ pictures
def focus_of(photo):
    l, t, r, b = photo.get("subject") or (0.3, 0.3, 0.7, 0.7)
    return photo.get("focus") or ((l + r) / 2, (t + b) / 2)


def cover_box(photo, frame=(W, H)):
    """The photograph laid to cover a box of `frame` px at its zoom, its focus moved as near the box's middle as covering
    allows: [x, y, w, h] in the box's px."""
    fw, fh = frame
    a = photo["aspect"]
    w = max(fw, fh / a) * photo.get("zoom", 1)
    h = w * a
    fx, fy = focus_of(photo)
    x = min(0.0, max(fw - w, fw / 2 - fx * w))
    y = min(0.0, max(fh - h, fh / 2 - fy * h))
    return [round(x, 1), round(y, 1), round(w, 1), round(h, 1)]


def picture_of(photo, box):
    """The photograph in its box [x, y, w, h] (frame px): where it lies in the box (`place`, box px) and the point the
    camera's moves center on (`focus`, box px)."""
    place = cover_box(photo, (box[2], box[3]))
    fx, fy = focus_of(photo)
    out = {"file": photo["file"], "box": [round(v, 1) for v in box], "place": place,
           "focus": [round(place[0] + fx * place[2], 1), round(place[1] + fy * place[3], 1)]}
    if photo.get("clip"):
        out["clip"] = photo["clip"]
    return out


def whole_in(photo, box, margin=0.06):
    """A subject still in a box too short to cover with it whole: scaled so its piece stands whole in the box's height
    (`margin` of the height free above and below it), in the middle of the box, the box around it filled with the
    still's own ground, top to foot (`fill`, the two colors at the box's top and foot). A still that covers the box with
    its piece whole is laid as picture_of lays it."""
    out = picture_of(photo, box)
    ground = photo.get("ground")
    if not ground:
        return out
    bw, bh = box[2], box[3]
    a = photo["aspect"]
    l, t, r, b = photo.get("subject") or (0.15, 0.15, 0.85, 0.85)
    h = min(out["place"][3], bh * (1 - 2 * margin) / max(0.05, b - t))
    if h >= out["place"][3]:
        return out
    w = h / a
    fx = (l + r) / 2
    x = (bw - w) / 2 if w < bw else min(0.0, max(bw - w, bw / 2 - fx * w))
    y = min(0.0, max(bh - h, bh / 2 - (t + b) / 2 * h)) if h >= bh else (bh - h) / 2
    top, foot = (palette.hex_rgb(c) for c in ground)
    at = lambda u: "#%02x%02x%02x" % tuple(round(p + (q - p) * min(1, max(0, u))) for p, q in zip(top, foot))
    return {**out, "place": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)],
            "focus": [round(x + fx * w, 1), round(y + (t + b) / 2 * h, 1)], "fill": [at(-y / h), at((bh - y) / h)]}


def subject_in_frame(photo, frame=(W, H)):
    """The subject's box [top, bottom] in the frame's px, the photograph covering the frame."""
    x, y, w, h = cover_box(photo, frame)
    _, t, _, b = photo.get("subject") or (0.3, 0.3, 0.7, 0.7)
    return y + t * h, y + b * h


def detail(photo, k):
    """The `k`th close framing of a still: DETAIL's zoom of covering the frame round a point of its subject box."""
    l, t, r, b = photo["subject"]
    fx, fy = DETAIL_AT[k % len(DETAIL_AT)]
    return {**photo, "zoom": DETAIL["zoom"] + DETAIL["step"] * k, "focus": (l + fx * (r - l), t + fy * (b - t)), "detail": k + 1}


def card_box(card, frame=(W, H)):
    """Where the card stands a photo beat's photograph, [x, y, w, h] frame px; None where the card shows none."""
    pic = card["photo"]["picture"]
    if not pic["show"]:
        return None
    x, y, w, h = pic["box"]
    return [x * frame[0], y * frame[1], w * frame[0], h * frame[1]]


# ------------------------------------------------------------------ words
def said_lines(text, most, face):
    """Their words on up to `most` lines (more than two words make two, more than five three, more than nine four),
    broken where the widest line is narrowest and never after a word that leads the next."""
    ws = text.split()
    n = min(most, 1 if len(ws) <= 2 else 2 if len(ws) <= 5 else 3 if len(ws) <= 9 else 4, len(ws)) or 1
    best = None
    for cuts in itertools.combinations(range(1, len(ws)), n - 1):
        rows = [ws[a:b] for a, b in zip((0,) + cuts, cuts + (len(ws),))]
        if any(r[-1].lower() in LEADING for r in rows[:-1]):
            continue
        widths = [compose.width(" ".join(r), 100, face) for r in rows]
        key = (round(max(widths)), -min(widths))
        if best is None or key < best[0]:
            best = (key, rows)
    return [" ".join(r) for r in (best[1] if best else [ws])]


def area_of(fmt):
    """The type area of a format, [x0, y0, x1, y1] px: the frame inside its safe margins."""
    sf = compose.SAFE[fmt]
    return [sf["left"], sf["top"], sf["width"] - sf["right"], sf["height"] - sf["bottom"]]


def set_rows(text, sizes, most, tall, wide, face):
    """`text` broken into at most `most` rows at the largest size of `sizes` (largest, smallest, in px) where every row
    is no wider than `wide` and the rows no taller than `tall`: (size, rows, fits)."""
    lh = compose.face_of(face)["lineHeight"]
    for size in range(int(sizes[0]), int(sizes[1]) - 1, -2):
        for n in range(1, most + 1):
            rows = said_lines(text, n, face) if n > 1 else [text]
            if len(rows) * lh * size <= tall and all(compose.width(r, size, face) <= wide for r in rows):
                return size, rows, True
    return int(sizes[1]), said_lines(text, most, face), False


def card_lines(card, text, label, fmt, t0=0.0, sizes=None):
    """A photo beat's label and words set in the card's line box (its shares of the type area), in the card's faces,
    sizes, colors and alignment: the label on the box's first row, the words under it in at most three rows at the
    card's size or down to half of it (a label with no words is set as the words); `sizes` (label px, words px) sets
    them larger than the card's own, the words still allowed down to half the card's own size. A centered card hangs
    its rows from the box's foot (a subtitle), any other
    from its top. Returns the lines and whether the words fit the box."""
    lay = card["photo"]
    a = area_of(fmt)
    if label and not text:
        text, label = label, ""
    k = compose.SAFE[fmt]["width"] / W
    bx, by, bw, bh = lay["line"]["box"]
    x0, y0 = a[0] + bx * (a[2] - a[0]), a[1] + by * (a[3] - a[1])
    x1, y1 = x0 + bw * (a[2] - a[0]), y0 + bh * (a[3] - a[1])
    lab, ln = lay["label"], lay["line"]
    rows = []
    if label:
        ls = round(sizes[0] if sizes else lab["size"] * k)
        rows.append({"text": label, "size": ls, "face": lab["face"], "role": "label", "color": lab["color"],
                     "lead": ls * compose.face_of(lab["face"])["lineHeight"] + 0.5 * ls})
    fits = True
    if text:
        room = y1 - y0 - sum(r["lead"] for r in rows)
        own = round(ln["size"] * k)
        want = round(sizes[1]) if sizes else own
        size, said, fits = set_rows(text, (want, max(20, own // 2)), 3, room, x1 - x0, ln["face"])
        lead = size * compose.face_of(ln["face"])["lineHeight"]
        rows += [{"text": r, "size": size, "face": ln["face"], "role": "words", "color": ln["color"], "lead": lead} for r in said]
    tall = sum(r["lead"] for r in rows)
    align = "center" if ln["align"] == "center" else "left"
    y = y1 - tall if align == "center" else y0
    out = []
    for i, r in enumerate(rows):
        out.append({"text": r["text"], "top": round(y, 1), "x": round((x0 + x1) / 2 if align == "center" else x0, 1),
                    "align": align, "size": r["size"], "face": r["face"], "role": r["role"], "color": r["color"],
                    "t": round(t0 + (0 if r["role"] == "label" else 0.5 + 0.25 * (i - (1 if label else 0))), 3),
                    "w": round(compose.width(r["text"], r["size"], r["face"]), 1), "box": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]})
        y += r["lead"]
    return out, fits


def words_over(card, text, label, band, fmt, t0, want=None):
    """The beat's words set over a whole-frame picture in the family's grammar (at `want` px, else the family's), in
    the frame's px: each line's text, its box top, left or middle, size, face, color, and the beat it lands on. `band`
    is "top" or "foot": where the subject is not."""
    fam = FAMILY[family(card)]
    sf = compose.SAFE[fmt]
    fw, fh = sf["width"], sf["height"]
    left, right = sf["left"], sf["right"]
    room = fw - left - right
    face = fam["face"]
    rows = said_lines(text, fam["lines"], face)
    size = min(compose.fit(r, want or fam["want"], room, face) for r in rows)
    lead = compose.face_of(face)["lineHeight"] * size
    lab = card["photo"]["label"]
    lab_color = lab["color"] if lab["color"].startswith("accent") else "paper"
    out = []
    if family(card) == "grid" and label:
        lsize = round(lab["size"] * 1.75)
        out.append({"text": label, "size": lsize, "face": lab["face"], "role": "label", "lead": lsize * 1.6, "color": lab_color})
    out += [{"text": r, "size": round(size, 1), "face": face, "role": "words", "lead": lead, "color": "paper"} for r in rows]
    if family(card) == "cinema" and label and label != text:
        lsize = round(size * 0.55, 1)
        out.append({"text": label, "size": lsize, "face": lab["face"], "role": "label", "lead": lsize * 1.6, "color": lab_color})
    tall = sum(x["lead"] for x in out)
    bars = card["finish"].get("bars", 0) * fh
    top_room, foot_room = max(sf["top"], bars + 60), fh - max(sf["bottom"], bars + 60)
    y = top_room + 20 if band == "top" else foot_room - 20 - tall
    lines = []
    for i, x in enumerate(out):
        lines.append({"text": x["text"], "top": round(y, 1), "x": round((left + fw - right) / 2 if fam["align"] == "center" else left, 1),
                      "align": fam["align"], "size": x["size"], "face": x["face"], "role": x["role"], "color": x["color"],
                      "t": round(t0 + fam["step"] * i, 3), "w": round(compose.width(x["text"], x["size"], x["face"]), 1)})
        y += x["lead"]
    return lines


def slammed(card, text, fmt):
    """The words of a beat whose move lands them one a musical beat, as the kit sets them on the card's flat color:
    every word at one size, the size its longest word takes to sit inside the safe area at rest and inside the frame,
    whole, at the slam's oversize start; each word in the middle of the safe area from its beat (`t`) until the next
    lands (`until`), the last to the cut, the card's accent on its ground and every second word the ground on the
    accent (`ground`, the field it lands on), so each word arrives as the whole frame turning over. And the same words,
    the accent on the ground, stacked one a row at that size
    (smaller where the rows would run taller than the safe area), all at rest from the beat's start: the line as the
    beat's still shows it."""
    sf = compose.SAFE[fmt]
    face = FAMILY[family(card)]["face"]
    lh = compose.face_of(face)["lineHeight"]
    words = text.split()
    x0, x1 = sf["left"], sf["width"] - sf["right"]
    y0, y1 = sf["top"], sf["height"] - sf["bottom"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = min(cx - SLAM["edge"], sf["width"] - SLAM["edge"] - cx)
    room = min(x1 - x0, 2 * half / SLAM["from"])
    size = math.floor(min(compose.fit(w, SLAM["want"], room, face) for w in words))

    def line(w, top, sz, t):
        return {"text": w, "top": round(top, 1), "x": round(cx, 1), "align": "center", "size": sz, "face": face,
                "role": "words", "color": "accent", "t": t, "w": round(compose.width(w, sz, face), 1)}

    one = [line(w, cy - size / 2, size, i) for i, w in enumerate(words)]
    for x in one[1::2]:
        x.update(color="bg", ground="accent")
    for a, b in zip(one, one[1:]):
        a["until"] = b["t"]
    tall = (len(words) - 1) * lh + 1
    rows = min(size, math.floor((y1 - y0) / tall))
    top = cy - tall * rows / 2
    stacked = [line(w, top + i * lh * rows, rows, 0) for i, w in enumerate(words)]
    return one, stacked


# ------------------------------------------------------------------ the beats
def tags_of(b):
    """What a beat is, in the words a card's `fits` uses."""
    t = {b["form"]}
    if b["form"] in ("photo", "clip"):
        t.add(b["form"])
    t.add("words" if b["words"] else "wordless")
    if b["form"] == "photo" and b["part"] == "build" and not (b["words"] or b["label"]):
        # a photograph of the build with nothing to say stands as one of the set: a move made for a wall of them fits it
        t.add("wall")
    if b.get("aspect"):
        t.add("portrait" if b["aspect"] > 1.05 else "landscape")
    if b["peak"]:
        t.add("peak")
    c = b.get("classes") or {}
    if c.get("people"):
        t.add("people")
    if c.get("place"):
        t.add("place")
    return t


def pick(options, tags, form, used, avoid):
    """The option whose `fits` matches the beat best (its form counts twice, each other tag once, and every earlier beat
    on it one less, so a film keeps reaching for the card's other options); between equals the one used least so far,
    then the card's order. The option `avoid` (the previous beat's) is never picked while another
    exists."""
    pool = [o for o in options if o["id"] != avoid] or options
    score = lambda o: 2 * (form in o["fits"]) + len((tags - {form}) & set(o["fits"])) - used.get(o["id"], 0)
    best = max(pool, key=lambda o: (score(o), -used.get(o["id"], 0), -options.index(o)))
    used[best["id"]] = used.get(best["id"], 0) + 1
    return best["id"]


def cut_beats(name):
    """How many musical beats a cut's window lasts (centred on the cut), read from the cut's own file; 0 for none."""
    f = CUTS / f"{name}.tsx"
    m = re.search(r"beats:\s*([\d.]+)", f.read_text()) if name and f.exists() else None
    return float(m.group(1)) if m else 0.0


def choose(card, beats):
    """Each beat's move from its content within the card's allowlist; a beat with no words and no label takes no move
    that sets words while the card has another, the first beat none that opens on black or settles in slowly, and no
    beat that shows the subject after the hook (the reveal, a subject photograph, its footage) takes a move that covers
    its picture. The hook and the reveal never take a move drawn on the photograph's box (the closer's shape covers
    whatever its move would draw). The reveal takes a move made for its form however often the film has used it. A beat with words or a label never takes a move
    whose words leave as it opens, a beat whose words hold no number never takes a move that counts, and a beat whose
    words run longer than a move sets never takes that move."""
    def allowed_of(b):
        boxed = b["form"] in ("photo", "clip") and b["part"] in ("build", "detail")
        said = b["words"] or b["label"]
        base = [m for m in card["moves"] if (boxed or b["form"] == "closer" or m["id"] not in BOXED)
                and not (b is beats[0] and m["id"] in NOT_FIRST)
                and not ((b["peak"] or b["form"] == "clip" or (b["own"] and b["part"] != "hook")) and m["id"] in COVERS)
                and not (said and m["id"] in PASSING)
                and not (m["id"] in COUNTS and not NUMBER.search(f"{b['words']} {b['label']}"))
                and not (m["id"] in SHORT and ((b["words"] and b["label"])
                                               or len((b["label"] or b["words"]).split()) > SHORT[m["id"]]))
                ] or card["moves"]
        allowed = [m for m in base if said or m["id"] not in SETS_WORDS - (BOXED if boxed else set())] or base
        if b["peak"]:
            allowed = [m for m in allowed if b["form"] in m["fits"]] or allowed
        return allowed

    # the reveal's move is chosen first, and no other beat makes it while the card has another for that beat besides
    # the move just made: the reveal's move is its own, and one that sets words never sets the film's title in a beat
    # before the reveal; two beats running never move alike, which matters more
    peak = next((b for b in beats if b["peak"]), None)
    ahead = pick(allowed_of(peak), tags_of(peak), peak["form"], {}, None) if peak else None
    moves, prev = {}, None
    for b in beats:
        if b is peak:
            b["move"] = ahead
            moves[ahead] = moves.get(ahead, 0) + 1
        else:
            allowed = allowed_of(b)
            fresh = [m for m in allowed if m["id"] != ahead]
            if any(m["id"] != prev for m in fresh):
                allowed = fresh
            b["move"] = pick(allowed, tags_of(b), b["form"], moves, prev)
        prev = b["move"]


def cut_jumps(name):
    """Whether a cut jumps from one picture to the next (true) or carries both pictures through each other (a
    crossfade), read from the cut's own file."""
    f = CUTS / f"{name}.tsx"
    m = re.search(r"jump:\s*(true|false)", f.read_text()) if name and f.exists() else None
    return not m or m.group(1) == "true"


def carries_words(b):
    """Whether a beat shows words of its own: its words or label, or the closer's end card."""
    return bool(b["words"] or b["label"]) or b["form"] == "closer"


def cuts_of(card, beats, tone=None):
    """The cut into each beat from its content within the card's allowlist, once the beats have their lengths: a cut
    whose window would take more than three eighths of either beat it joins is never picked while another fits, so a
    beat's two cuts leave at least a quarter of it whole. Between two beats that both carry words a crossfade is never
    picked while the card has a cut that jumps, so two layouts of words never show through each other. Among what fits,
    the tone's cuts come first. The first beat has no cut; the closer's cut fits `closer`."""
    used = {}
    liked = (tone or TONES["default"])["cuts"]
    beats[0]["transition"] = None
    for a, b in zip(beats, beats[1:]):
        room = min(a["len"], b["len"]) * 0.75
        fit = [c for c in card["transitions"] if cut_beats(c["id"]) <= room] or \
            [min(card["transitions"], key=lambda c: cut_beats(c["id"]))]
        if carries_words(a) and carries_words(b):
            fit = [c for c in fit if cut_jumps(c["id"])] or [c for c in card["transitions"] if cut_jumps(c["id"])] or fit
        fit = [c for c in fit if c["id"] in liked] or fit
        b["transition"] = pick(fit, tags_of(b) | ({"closer"} if b["form"] == "closer" else set()), b["form"], used, None)


def beats_of(ctx):
    """The story's beats before timing: their part, form, picture, words and label. The build holds at most the tone's
    count of beats (the footage among them), and never fewer than BUILD_LEAST where the hero still can give close
    framings."""
    name = ctx["name"]
    hero = ctx["hero"]
    beats = []
    hook = ctx.get("hook")
    hook_pic = hook or ({**hero, "zoom": HOOK_ZOOM} if hero else None)
    lead = ctx.get("hook_label", ctx["date_label"])
    beats.append({"id": "hook", "part": "hook", "form": "title", "photo": hook_pic, "words": ctx["hook_line"] or name,
                  "label": lead, "peak": False, "own": hook is None})
    theirs = list(ctx["build"])
    stills = list(ctx["stills"][1:]) if hero else []
    footage = ctx.get("footage")
    build = []
    # the subject's other stills and its footage play between their photographs of the making, in the order they made it
    while theirs or stills:
        if theirs:
            build.append(("theirs", theirs.pop(0)))
        if stills:
            build.append(("subject", stills.pop(0)))
    most = max(BUILD_LEAST, tone_of(ctx)["build"])
    build = build[:most - 1 if footage else most]
    if footage:
        build.insert(min(len(build), max(1, len(build) // 2 + 1)), ("clip", footage))
    k = 0
    while hero and len(build) < BUILD_LEAST:
        build.append(("detail", detail(hero, k)))
        k += 1
    shown = 0
    for i, (kind, p) in enumerate(build, 1):
        line = p.get("line") or ""
        label = ""
        if kind in ("subject", "clip"):
            # the subject's first picture carries its name; the rest play without words, so the name and the date land
            # once each before the reveal says them together
            label = "" if shown else name
            shown += 1
        beats.append({"id": f"detail-{p['detail']}" if kind == "detail" else f"build-{i}", "part": "detail" if kind == "detail" else "build",
                      "form": "clip" if kind == "clip" else "photo", "photo": p, "words": line,
                      "label": label, "peak": False, "own": kind != "theirs", "classes": p.get("classes")})
    if hero:
        beats.append({"id": "made", "part": "made", "form": "photo", "photo": hero, "words": name, "label": lead,
                      "peak": True, "own": True})
    beats.append({"id": "closer", "part": "closer", "form": "closer", "photo": hero or hook_pic, "words": "", "label": "",
                  "peak": False, "own": bool(hero)})
    for b in beats:
        b["aspect"] = (b["photo"] or {}).get("aspect")
    return beats


def seconds_of(b):
    if b["part"] == "build":
        if b["form"] == "clip":
            return SECONDS["clip"]
        n = len(b["words"].split())
        return SECONDS["build-words"] + 0.15 * max(0, n - 4) if n else SECONDS["build"]
    return SECONDS[b["part"]]


# seconds a line on screen takes to read: a start, and each word
READ = {"start": 0.6, "word": 0.3}
# moves that fly the beat's photograph in before it lands (the seconds their flight asks of the shared arrival, and the
# words' settle after it): the beat's words show only once it has landed, so the beat holds that long before its read
ARRIVES = {"picture-tunnel": 1.1, "exploded-layers": 1.15, "tilted-wall": 1.2}
SETTLE = 0.3
# moves that land the words one a musical beat: the kit sets those words itself (slammed), so every word fits the frame
ONE_A_BEAT = {"word-per-beat-slam"}
# a slammed word: the oversize it lands from (the slam entrance of HypeFilm's Words), the px it keeps from the frame's
# edge even at that oversize, and the most px it is set at
SLAM = {"from": 1.45, "edge": 40, "want": 330}
# px of the matte between the reveal's picture and its name on a letterboxed card, and the name's size there, a share
# over the family's: the peak's title on a matte of its own
MATTE_GAP = 84
MATTE_TITLE = 1.5


def least(b, per):
    """The fewest musical beats a beat holds: one, or the flight of a move that flies its photograph in and its settle,
    then what its words take to read, or one a word and a beat to land the last where its move sets them one a beat."""
    said = (b["words"] or b["label"]).split() if b["form"] != "closer" else []
    if said and b.get("move") in ONE_A_BEAT:
        return len(said) + 1
    fly = ARRIVES[b["move"]] + SETTLE if b.get("move") in ARRIVES and b["form"] != "closer" else 0
    read = READ["start"] + READ["word"] * len(said) if said else 0
    return max(1, math.ceil((fly + read) / per))


def ctx_of(beats):
    """The tone the beats were drawn in (each carries ctx `tone`), as a context tone_of reads."""
    return {"tone": next((b.get("tone") for b in beats if b.get("tone")), None)}


def lengths(beats, card, bpm, asked=None):
    """Each beat's length in whole musical beats at `bpm`, from its part, its words and the family's pace; with a
    length asked, the beats before the closer hold longer or shorter in proportion so the film runs it; then, where
    the subject's own pictures fill less than SUBJECT_SHARE of the time before the closer, their photographs shorten
    and the subject's hold longer; then the reveal takes time from the longest beats that can spare it until none holds longer. No beat is
    ever shorter than its words take to read (least)."""
    pace = FAMILY[family(card)]["pace"] * tone_of(ctx_of(beats))["pace"]
    per = 60 / bpm
    for b in beats:
        b["least"] = least(b, per)
        b["len"] = max(b["least"], round(seconds_of(b) * pace / per))
    body = beats[:-1]
    if asked:
        want = max(len(body), round(asked / per) - beats[-1]["len"])
        have = sum(b["len"] for b in body)
        run = given = 0
        for b in body:
            run += b["len"]
            n = max(b["least"], round(want * run / have) - given)
            given += n
            b["len"] = n
    shown = lambda: sum(b["len"] for b in body if b["own"] and b.get("move") not in COVERS)
    total = sum(b["len"] for b in body)
    guard = 0
    while total and shown() < SUBJECT_SHARE * total and guard < 200:
        guard += 1
        mine = [b for b in body if not b["own"] and b["len"] > b["least"]]
        prod = [b for b in body if b["own"] and b.get("move") not in COVERS]
        if not prod:
            break
        if mine:
            max(mine, key=lambda b: b["len"])["len"] -= 1
        min(prod, key=lambda b: b["len"])["len"] += 1
    peak = next((b for b in body if b["peak"]), None)
    while peak:
        rest = [b for b in body if b is not peak]
        give = max((b for b in rest if b["len"] > b["least"]), key=lambda b: b["len"], default=None)
        if not give or peak["len"] > max(b["len"] for b in rest):
            break
        give["len"] -= 1
        peak["len"] += 1
    return sum(b["len"] for b in beats)


def sound(beats):
    """The film's sound cues, every one on a whole beat: a hit at every cut (an impact where the hook opens), the riser
    into the reveal and its impact as the reveal cuts in, and the closer's last hit where the picture and the music stop
    together."""
    cues = []
    for i, b in enumerate(beats):
        t0 = b["start"]
        if b["part"] == "hook":
            cues.append({"kind": "impact", "at": t0, "weight": 0.8})
        elif b["part"] == "made":
            rise = min(4, beats[i - 1]["len"] + (beats[i - 2]["len"] if i > 1 else 0))
            cues.append({"kind": "riser", "at": t0 - rise, "beats": rise})
            cues.append({"kind": "impact", "at": t0, "weight": 1.0})
        elif b["part"] == "closer":
            cues.append({"kind": "hit", "at": t0, "weight": 0.7, "bright": 0.6})
            cues.append({"kind": "hit", "at": t0 + b["stop"], "weight": 1.0, "bright": 0.5})
            cues.append({"kind": "stop", "at": t0 + b["stop"]})
        else:
            cues.append({"kind": "hit" if b["own"] else "bright", "at": t0, "weight": 0.55 if b["own"] else 0.45})
    return sorted(cues, key=lambda c: c["at"])


STORY = {
    "hook": "the hook line, over {pic}",
    "build": "{pic}{said}",
    "detail": "a close look at the subject in its hero still",
    "made": "the reveal: the subject's hero still whole under its name",
    "closer": "the closer: the name, the date for a launch or the punchline, and the handle; the picture and the music stop together",
}


def story(beats):
    out = []
    for b in beats:
        pic = ("the subject's footage" if b["form"] == "clip" else "a still of the subject" if b["own"]
               else "their photograph")
        said = f", with their words \"{b['words']}\"" if b["words"] and b["part"] == "build" else ""
        out.append({"beat": b["id"], "reveals": STORY[b["part"]].format(pic=pic, said=said), "move": b["move"],
                    "cut": b["transition"]})
    return out


def band_of(b, fmt_frame):
    """Where a beat's words go: away from the subject (the foot when the subject sits high in the frame, else the top)."""
    if not b["photo"]:
        return "foot"
    top, bot = subject_in_frame(b["photo"], fmt_frame)
    return "foot" if (top + bot) / 2 < fmt_frame[1] * 0.5 else "top"


def layout_of(b, card):
    """"field" where the beat's move lands its words one a beat: the card's ground covers the frame and the kit slams
    the words onto it. On the reveal with words the kit sets, the name stands off the picture: "card" on a grid card
    (the photograph in the card's box, the name on the card's ground) and "matte" on a letterboxed one (the picture
    above, the name in the lower matte, in the bars' own tone). Else "card" where the beat is laid out by the card's
    photo layout (a photo of the build under a move drawn on its box, or with words the kit sets under a move that sets
    none), else "frame": the picture covers the frame. A photo with no words and no move on its box has nothing for the
    card's layout to hold, so it covers the frame."""
    said = b["words"] or b["label"]
    if b["move"] in ONE_A_BEAT and said and b["form"] != "closer":
        return "field"
    if b["part"] == "made" and b.get("photo") and b["words"] and b["move"] not in SETS_WORDS:
        if family(card) == "grid" and card["photo"]["picture"]["show"]:
            return "card"
        if family(card) == "cinema" and card["finish"].get("bars", 0) > 0:
            return "matte"
    if b["form"] not in ("photo", "clip") or b["part"] not in ("build", "detail"):
        return "frame"
    if b["move"] in BOXED:
        return "card"
    if b["move"] in SETS_WORDS or not (b["words"] or b["label"]):
        return "frame"
    return "card"


def landscaped(card, photo):
    """The card with the photo layout a photograph takes: one wider than it is tall takes the card's landscape box and
    line box, so it fills the frame's foot instead of leaving bare ground under it."""
    if not photo or photo.get("aspect", 1) >= 1:
        return card
    lay = card["photo"]
    land = lay["landscape"]
    return {**card, "photo": {**lay, "picture": {**lay["picture"], "box": land["box"]}, "line": {**lay["line"], "box": land["line"]}}}


def lay(b, card, fmt=(W, H)):
    """The beat's picture, ground, words and shade."""
    b["layout"] = layout_of(b, card)
    draws = (b["move"] in SETS_WORDS and b["layout"] != "card") or b["form"] == "closer"
    b["fits"] = True
    if b["layout"] == "field":
        box = [0, 0, fmt[0], fmt[1]]
        b["ground"] = "bg"
        b["lines"], b["still"] = slammed(card, b["words"] or b["label"], "reel")
        b["scrim"] = 0
    elif b["layout"] == "matte":
        b["lines"] = words_over(card, b["words"], b["label"], "foot", "reel", 0, FAMILY["cinema"]["want"] * MATTE_TITLE)
        bar = round(card["finish"]["bars"] * fmt[1], 1)
        box = [0, bar, fmt[0], round(min(l["top"] for l in b["lines"]) - MATTE_GAP - bar, 1)]
        b["ground"] = card["finish"]["matte"]
        b["scrim"] = 0
    elif b["layout"] == "card":
        card = landscaped(card, b["photo"])
        box = card_box(card, fmt)
        b["ground"] = card["photo"]["ground"]
        big = None
        if b["part"] == "made":
            # the reveal's name is a title: set at the size the family gives a title, across the type area's whole
            # measure from the top of the card's line box
            ln = card["photo"]["line"]
            card = {**card, "photo": {**card["photo"], "line": {**ln, "box": [0, ln["box"][1], 1, ln["box"][3]]}}}
            big = (round(card["photo"]["label"]["size"] * 1.75), FAMILY[family(card)]["want"])
        b["lines"], b["fits"] = card_lines(card, b["words"], b["label"], "reel", sizes=big)
        b["scrim"] = card["photo"]["line"]["scrim"] if box and b["lines"] else 0
    else:
        box = [0, 0, fmt[0], fmt[1]]
        b["ground"] = "bg"
        b["lines"] = [] if draws or not b["words"] else words_over(card, b["words"], b["label"], band_of(b, fmt), "reel", 0)
        b["scrim"] = max(SHADE, card["photo"]["line"]["scrim"]) if b["lines"] and b["photo"] else 0
    b["picture"] = (whole_in if b["layout"] == "matte" else picture_of)(b["photo"], box) if b["photo"] and box else None
    b["enter"] = card["photo"]["line"]["enter"]


KEYS = ("id", "part", "form", "len", "bars", "start", "words", "label", "peak", "own", "move", "transition", "layout",
        "picture", "ground", "lines", "still", "scrim", "enter", "fits", "tags", "hits_at")


def build(ctx, card, bpm, asked=None):
    """The board's beats, sound and story in `card`'s style at `bpm`."""
    compose.use(card["id"])
    beats = beats_of(ctx)
    for b in beats:
        b["tone"] = ctx.get("tone")
    choose(card, beats)
    lengths(beats, card, bpm, asked)
    cuts_of(card, beats, tone_of(ctx))
    at = 0
    for b in beats:
        b["start"] = at
        at += b["len"]
    closer = beats[-1]
    closer["stop"] = max(1, closer["len"] - 2)
    for b in beats:
        lay(b, card)
        b["bars"] = b["len"] / 4
        b["tags"] = sorted(tags_of(b))
    cues = sound(beats)
    for b in beats:
        b["hits_at"] = sorted({round(c["at"] - b["start"], 3) for c in cues if c["kind"] in ("hit", "impact", "bright")
                               and b["start"] <= c["at"] < b["start"] + b["len"]})
    out = [{k: b[k] for k in KEYS if k in b} for b in beats]
    out[-1]["stop"] = closer["stop"]
    return {"beats": out, "sound": cues, "story": story(beats)}


def feed(ctx, card):
    """The feed post: the closer alone at 1080x1350, on the hero still."""
    compose.use(card["id"])
    pic = ctx["hero"] or ctx.get("hook")
    frame = (1080, 1350)
    return [{"id": "closer", "part": "closer", "form": "closer", "len": 8, "bars": 2, "start": 0, "words": "", "label": "",
             "peak": False, "own": True, "move": None, "transition": None, "layout": "frame",
             "picture": picture_of(pic, [0, 0, *frame]) if pic else None, "ground": "bg", "lines": [], "scrim": 0,
             "enter": card["photo"]["line"]["enter"], "fits": True, "tags": ["closer"], "hits_at": [0], "stop": 6}]
