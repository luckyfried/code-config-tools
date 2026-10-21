"""The bounds check: what a board's frames hold when each shot comes to rest, measured from the board alone.

Every shot is read at its last frame, through the camera the studio composition applies (the view, its move and the
drift; words and fixed layers stay where they are set). The type and the bars are boxes on the frame, a line of type
turned on its pivot is the four corners it is drawn at, and a cut's photograph runs off the frame under its edge by
design, so it is read as its edge, and a slice (a photograph inside a four-sided piece of the frame, which may run
off it) as its four corners. The check fails a board when, at rest:

- a slice shows less than SHOWN px on its short side;
- type leaves the safe area or is cut by the frame, two lines of type overlap, free words run into a bar, or free
  words cross a cut's edge onto its photograph or run onto a slice (words marked `under` are set under the
  photographs on purpose);
- a bar drawn later covers a count;
- a count is drawn smaller than the tone's floor.

Run as `python3 bounds.py <board.json>...`: prints the findings and exits 1 when there are any."""
import json
import math
import sys

from compose import Frame, framing, hull, pulse_of, text_box, to_screen, turned

COUNT_FLOOR = {"drive": 40}
UNMOVED = ("Words",)
# the least a slice of a photograph shows on its short side, px, in each format
SHOWN = {"reel": 240, "square": 180, "wide": 180}


def inside(a, b, tol=0.0):
    return a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[2] <= b[2] + tol and a[3] <= b[3] + tol


def meets(a, b, pad=0.0):
    return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad


def area(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def shown(poly, W, H):
    """The short side, px, of the part of a slice (corners top left, top right, bottom right, bottom left, its sides
    upright) the frame shows: its width across, or its least height down."""
    (xa, ya), (xb, yb), (_, zb), (_, za) = poly
    x0, x1 = max(0.0, xa), min(float(W), xb)
    if x1 <= x0:
        return 0.0

    def tall(x):
        f = (x - xa) / (xb - xa)
        return min(H, za + (zb - za) * f) - max(0, ya + (yb - ya) * f)

    return min(x1 - x0, tall(x0), tall(x1))


def rect(b):
    return (b[0], b[1], b[0] + b[2], b[1] + b[3])


def crossing(a, b, depth=1.0):
    """Two convex outlines (corner lists) overlap by more than `depth` px across every axis that could separate them."""
    for poly in (a, b):
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y0 - y1, x1 - x0
            k = math.hypot(nx, ny)
            if k < 1e-9:
                continue
            pa = [(x * nx + y * ny) / k for x, y in a]
            pb = [(x * nx + y * ny) / k for x, y in b]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) <= depth:
                return False
    return True


class Shot:
    """One beat at one frame: the camera and the boxes on the frame."""

    def __init__(self, board, i, f=None):
        self.board, self.beat = board, board["beats"][i]
        self.frame = Frame(board["format"].get("name", "reel"))
        self.S, self.pulse = board["system"], pulse_of(board["bpm"])
        self.f = self.beat["frames"] - 1 if f is None else f
        self.cam = framing(self.beat, self.f, self.frame, board["bpm"])
        self.items = []
        for n, layer in enumerate(self.beat["layers"]):
            self.read(n, layer)

    def on(self, at):
        return at * self.pulse <= self.f

    def place(self, layer, box):
        if layer["kind"] in UNMOVED or layer.get("fixed"):
            return tuple(box)
        return to_screen(self.cam, self.frame, box)

    def scale_of(self, layer):
        return 1.0 if layer["kind"] in UNMOVED or layer.get("fixed") else self.cam[0]

    def add(self, kind, layer, n, box, **kw):
        self.items.append({"kind": kind, "layer": layer["kind"], "n": n, "box": box, **kw})

    def text(self, layer, n, line, count=False, owner=None):
        line = dict(line)
        ink = turned(text_box(self.S, line, ink=True), line)
        em = hull(turned(text_box(self.S, line), line))
        quad = [self.place(layer, (x, y, x, y))[:2] for x, y in ink]
        self.add("text", layer, n, self.place(layer, em), ink=hull(quad), quad=quad, name=line.get("name") or line["text"],
                 count=count, owner=owner, size=line["size"] * self.scale_of(layer), free=layer["kind"] == "Words",
                 under=bool(layer.get("under")))

    def read(self, n, L):
        k = L["kind"]
        at = L.get("at", 0)
        if k == "Words":
            if self.on(at):
                for line in L["lines"]:
                    self.text(L, n, line, count=str(line.get("name", "")).startswith("count-"), owner=line.get("owner"))
        elif k == "Cut":
            W = self.frame.W
            ends = [self.place(L, (x, y, x, y))[:2] for x, y in ((0, L["line"][0]), (W, L["line"][1]))]
            self.add("edge", L, n, None, ends=ends)
        elif k == "Slice":
            if self.on(at):
                poly = [self.place(L, (x, y, x, y))[:2] for x, y in L["poly"]]
                self.add("slice", L, n, hull(poly), poly=poly, owner=L.get("owner"))
        elif k == "Bars":
            if self.on(at):
                for b in L["bars"]:
                    self.add("opaque", L, n, self.place(L, rect(b)), owner=None, bar=True)


def framebox(fr):
    return (0, 0, fr.W, fr.H)


def check_shot(sh, tone):
    """The findings for one shot at rest, as strings naming the beat and what is wrong."""
    out = []
    fr, bid = sh.frame, sh.beat["id"]
    F = framebox(fr)
    safe = fr.safe
    texts = [e for e in sh.items if e["kind"] == "text"]
    opaque = [e for e in sh.items if e["kind"] == "opaque"]

    def say(msg):
        out.append(f"{bid}: {msg}")

    for t in texts:
        e = t["box"]
        if not meets(e, F):
            continue
        if not inside(e, F):
            say(f"type {t['name']!r} is cut by the frame")
        elif not inside(e, safe, 2):
            say(f"type {t['name']!r} leaves the safe area")
        if t["count"] and t["size"] < COUNT_FLOOR.get(tone, 0) - 0.5:
            say(f"count {t['name']!r} is drawn at {t['size']:.0f} px, under the {COUNT_FLOOR[tone]} px floor")
    vis = [t for t in texts if meets(t["box"], F) and not t["under"]]
    for i, a in enumerate(vis):
        for b in vis[i + 1:]:
            if crossing(a["quad"], b["quad"]):
                say(f"type {a['name']!r} and {b['name']!r} overlap")
    for e in [e for e in sh.items if e["kind"] == "edge"]:
        (xa, ya), (xb, yb) = e["ends"]
        for t in texts:
            if t["free"] and not t["under"] and any(y > ya + (yb - ya) * (x - xa) / (xb - xa) + 1 for x, y in t["quad"]):
                say(f"type {t['name']!r} crosses the cut onto its photograph")
    for s in [e for e in sh.items if e["kind"] == "slice"]:
        v = shown(s["poly"], fr.W, fr.H)
        if 0 < v < SHOWN.get(fr.name, 0) - 0.5:
            say(f"photograph {s['owner']} shows {v:.0f} px on its short side, under {SHOWN[fr.name]}")
        for t in texts:
            if t["free"] and not t["under"] and crossing(t["quad"], s["poly"]):
                say(f"type {t['name']!r} runs onto photograph {s['owner']}")
    for o in [e for e in sh.items if e.get("bar")]:
        for t in texts:
            if t["free"] and area(o["box"], t["ink"]) > 2:
                say(f"type {t['name']!r} runs into a bar")
    for c in texts:
        if not c["count"] or not meets(c["box"], F):
            continue
        for o in opaque:
            if o["n"] > c["n"] and o.get("owner") != c["owner"] and area(o["box"], c["ink"]) > 2:
                say(f"a {o['layer'].lower()} covers count {c['name']!r}")
    return out


def check(board):
    """Every finding on the board, at each shot's rest."""
    tone = board.get("tone", "")
    out = []
    for i in range(len(board["beats"])):
        out += check_shot(Shot(board, i), tone)
    return out


def main(argv):
    bad = 0
    for p in argv:
        found = check(json.load(open(p)))
        for x in found:
            print(f"{p}: {x}")
        bad += len(found)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
