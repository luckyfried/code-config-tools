"""The parts every tone's storyboard is built from: the formats and their safe areas, the type system, the timed cut
as board beats, the camera's framing at any frame, and type measured the way the browser sets it.

A storyboard's times are musical beats from the film's start; its positions are px of the format's frame. The studio
composition (motion/studio) renders a board as it is written here."""
import functools
import json
import math
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
FPS = 30


def load(name):
    return json.loads((SKILL / "design" / f"{name}.json").read_text())


class Frame:
    """One output format: `name`, `W` x `H` px, and the safe area text stays inside (`top`, `bottom`, `left`, `right`
    px from each edge)."""

    def __init__(self, name):
        s = load("safe-areas")[name]
        self.name, self.W, self.H = name, s["width"], s["height"]
        self.top, self.bottom, self.left, self.right = s["top"], s["bottom"], s["left"], s["right"]

    @property
    def safe(self):
        return (self.left, self.top, self.W - self.right, self.H - self.bottom)

    @property
    def mid(self):
        return (self.W / 2, self.H / 2)


# the films a run renders: the reel is the post, the square and the wide are the same storyboard laid out for a feed
# post and a landscape screen
FORMATS = ("reel", "square", "wide")


def system(direction, colors, display=None, text=None, texture=None, hit=None):
    t = load("type")[direction]
    e = load("easing")[direction]
    safe = {k: {s: v[s] for s in ("top", "bottom", "left", "right")} for k, v in load("safe-areas").items() if k != "about"}
    return {
        "direction": direction,
        "display": {**t["display"], **(display or {})},
        "text": {**t["text"], **(text or {})},
        "scale": t["scale"],
        "colors": {"swatches": [], **colors},
        "texture": {"grain": 0.05, "vignette": 0.0, "leaks": False, **(texture or {})},
        "ease": {**{k: e[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "hit": hit or {"damping": 12, "stiffness": 200, "mass": 0.7}},
        "safe": safe,
    }


def photo(p, wall=False, zoom=None):
    """A post's photograph for a layer: placed by its focus point, or by its square crop on a wall."""
    d = {"file": p["file"], "aspect": p["aspect"], "focus": list(p["focus"])}
    if wall:
        d["crop"] = list(p["crop"])
    if zoom:
        d["zoom"] = zoom
    return d


@functools.lru_cache(maxsize=64)
def pixels(file):
    """A post's photograph as a small RGB image, for reading the colours a composition lays where, or None when the
    run holds no copy of it."""
    path = Path("public") / file
    if not path.is_file():
        return None
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        return im


# ------------------------------------------------------------------ type, measured
AXIS = {b"Weight": "wght", b"Width": "wdth", b"Optical Size": "opsz", b"Optical size": "opsz", b"Softness": "SOFT", b"Wonky": "WONK"}


@functools.lru_cache(maxsize=512)
def _font(file, size, axes):
    from PIL import ImageFont
    f = ImageFont.truetype(str(SKILL / file), max(1, round(size)))
    try:
        spec = f.get_variation_axes()
    except OSError:
        return f
    want = dict(axes)
    vals = []
    for a in spec:
        tag = AXIS.get(a["name"], "")
        v = want.get(tag)
        if v is None and tag == "opsz":
            v = size
        if v is None:
            v = a["default"]
        vals.append(max(a["minimum"], min(a["maximum"], v)))
    f.set_variation_by_axes(vals)
    return f


def face_of(system_, line):
    return system_["display"] if line.get("face") == "display" else system_["text"]


def font_for(system_, line):
    f = face_of(system_, line)
    axes = dict(line.get("axes") or f.get("axes") or {})
    axes.setdefault("wght", line.get("weight") or f.get("weight") or 400)
    return _font(f["file"], line["size"], tuple(sorted(axes.items())))


def text_width(system_, line, text=None):
    f = face_of(system_, line)
    s = line["text"] if text is None else text
    tr = line.get("tracking", f.get("tracking", 0)) or 0
    return font_for(system_, line).getlength(s, features=["kern", "liga", "tnum", "lnum"]) + tr * line["size"] * len(s)


def text_box(system_, line, ink=False):
    """The px box a line of type takes in its own coordinates: its advance across, and vertically the font's ascent to
    descent as the browser boxes it, or with `ink` the glyphs' own extent."""
    font = font_for(system_, line)
    w = text_width(system_, line)
    x = line["x"] - {"middle": w / 2, "end": w}.get(line.get("anchor"), 0)
    if ink:
        b = font.getbbox(line["text"], anchor="ls", features=["kern", "liga", "tnum", "lnum"])
        return (x, line["y"] + b[1], x + w, line["y"] + b[3])
    asc, desc = font.getmetrics()
    return (x, line["y"] - asc, x + w, line["y"] + desc)


def turned(box, line):
    """The four corners of a px box (x0, y0, x1, y1) of `line` as drawn: turned `rotate` degrees (clockwise on screen,
    as SVG turns) about its `pivot`, or about its own origin when it has none."""
    x0, y0, x1, y1 = box
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    a = line.get("rotate") or 0
    if not a:
        return pts
    px, py = line.get("pivot") or (line["x"], line["y"])
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in pts]


def hull(pts):
    """The upright px box (x0, y0, x1, y1) around points."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def fit_size(system_, line, width, lo=12):
    """The largest size (no larger than the line's) at which the line's advance fits `width` px."""
    size = line["size"]
    while size > lo and text_width(system_, dict(line, size=size)) > width:
        size -= 1
    return size


def wrap(text, width, size, k=0.5):
    """The fewest lines of `text` that fit `width` px at `size` px (by an average glyph width of `k` em), as even in
    length as the words allow."""
    words = text.split()
    n = max(1, int(width / (size * k)))
    for lines in range(1, len(words) + 1):
        def split(ws, m):
            if m == 1:
                yield [" ".join(ws)]
                return
            for i in range(1, len(ws) - m + 2):
                for rest in split(ws[i:], m - 1):
                    yield [" ".join(ws[:i])] + rest
        fits = [c for c in split(words, lines) if max(len(x) for x in c) <= n]
        if fits:
            return min(fits, key=lambda c: max(len(x) for x in c))
    return words


def wrap_measured(system_, line, width, max_lines=3):
    """`line`'s text broken into the fewest lines whose measured advance fits `width` px, as even as the words allow."""
    words = line["text"].split()
    for lines in range(1, min(max_lines, len(words)) + 1):
        def split(ws, m):
            if m == 1:
                yield [" ".join(ws)]
                return
            for i in range(1, len(ws) - m + 2):
                for rest in split(ws[i:], m - 1):
                    yield [" ".join(ws[:i])] + rest
        fits = [c for c in split(words, lines) if max(text_width(system_, line, x) for x in c) <= width]
        if fits:
            return min(fits, key=lambda c: max(text_width(system_, line, x) for x in c))
    return None


# ------------------------------------------------------------------ the timed cut
TIMES = ("at", "lightAt", "fullAt", "nextAt")


def shift(layer, t):
    """The layer with every time in it made relative to a shot starting at musical beat `t`."""
    l = dict(layer)
    for k in TIMES:
        if k in l:
            l[k] = round(l[k] - t, 4)
    if "knots" in l:
        l["knots"] = [dict(k, at=round(k["at"] - t, 4)) for k in l["knots"]]
    return l


def pulse_of(bpm):
    return FPS * 60 / bpm


def shots(scenes, end, bpm, drift=0.0):
    """A timed cut as board beats. `scenes` are the shots in order, {id, t, layers, view?, viewTo?, viewMove?, same?,
    drift?}, every time in musical beats from the film's start; each runs from its `t` to the next shot's (the last to
    `end`), with its layers' times made relative to its start. A shot marked `same` continues the framing before it,
    so its start is not a cut. Every shot pushes in by `drift` (or its own) over its length, and a `same` shot goes on
    from the scale the shot before it reached."""
    pulse = pulse_of(bpm)
    out = []
    reached = 0.0
    for i, sc in enumerate(scenes):
        t = sc["t"]
        tn = scenes[i + 1]["t"] if i + 1 < len(scenes) else end
        frames = round(tn * pulse) - round(t * pulse)
        b = {"id": sc["id"], "frames": frames, "bars": round(frames / (4 * pulse), 4), "layers": [shift(l, t) for l in sc["layers"]]}
        for k in ("view", "viewTo"):
            if k in sc:
                b[k] = sc[k]
        if "viewMove" in sc:
            b["viewMove"] = [round(sc["viewMove"][0] - t, 4), sc["viewMove"][1]]
        b["driftFrom"] = round(reached, 4) if sc.get("same") else 0.0
        b["drift"] = sc.get("drift", drift)
        reached = b["driftFrom"] + b["drift"]
        b["camera"] = "none"
        b["transition"] = None
        out.append(b)
    return out


def cuts_of(scenes, beats):
    """The planned cuts, in seconds: every shot start but the first and those marked `same`."""
    out, f = [], 0
    for i, b in enumerate(beats):
        if i and not scenes[i].get("same"):
            out.append(round(f / FPS, 3))
        f += b["frames"]
    return out


def board(story, frame, beats):
    """The board the studio composition renders: the storyboard's identity, the format and the beats."""
    return {"id": f"nine-{story['tone']}-{frame.name}", "name": f"best nine {story['tone']} {frame.name}", "handle": story["handle"],
            "year": story["year"], "bpm": story["bpm"], "tone": story["tone"],
            "format": {"width": frame.W, "height": frame.H, "fps": FPS, "name": frame.name}, "system": story["system"], "beats": beats}


# ------------------------------------------------------------------ the camera
def centre_of(v, mid):
    return (v["at"][0] + (mid[0] - v["to"][0]) / v["scale"], v["at"][1] + (mid[1] - v["to"][1]) / v["scale"])


def framing(beat, f, frame, bpm):
    """The camera at frame `f` of a beat, as (s, cx, cy): the scene is scaled by `s` and its point (cx, cy) sits at
    the middle of the frame; a beat with no view frames the whole scene about the middle."""
    pulse = pulse_of(bpm)
    dur = max(1, beat["frames"])
    k = 1 + beat.get("driftFrom", 0) + beat.get("drift", 0) * min(1, f / dur)
    mid = frame.mid
    v = beat.get("view")
    if not v:
        return (k, mid[0], mid[1])
    s = v["scale"] * k
    cx, cy = centre_of(v, mid)
    if beat.get("viewTo"):
        m0, mb = beat.get("viewMove") or [0, 1]
        t = max(0.0, min(1.0, (f - m0 * pulse) / max(1, mb * pulse)))
        e = 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
        dx, dy = centre_of(beat["viewTo"], mid)
        s = s * ((beat["viewTo"]["scale"] * k) / s) ** e
        cx += (dx - cx) * e
        cy += (dy - cy) * e
    return (s, cx, cy)


def to_screen(cam, frame, box):
    s, cx, cy = cam
    mx, my = frame.mid
    x0, y0, x1, y1 = box
    return (mx + (x0 - cx) * s, my + (y0 - cy) * s, mx + (x1 - cx) * s, my + (y1 - cy) * s)
