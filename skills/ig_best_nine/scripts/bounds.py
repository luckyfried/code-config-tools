"""The bounds check: what a board's frames hold when each shot comes to rest, measured from the board alone.

Every shot is read at its last frame, through the camera the studio composition applies (the view, its move and the
drift; words and fixed layers stay where they are set). The photographs, the type and the opaque pieces (tags, tape
and bars) are boxes on the frame, a line of type turned on its pivot is the four corners it is drawn at, and a cut's
photograph runs off the frame under its edge by design, so it is read as its edge, and a slice (a photograph inside a
four-sided piece of the frame, which may run off it) as its four corners. The check fails a board when, at rest:

- a photograph the frame shows whole is cut by it or sits closer than GUTTER px to its edge, or a slice shows less
  than SHOWN px on its short side;
- two photographs overlap, or a photograph comes within GUTTER px of free words (words marked `under` are set
  under the photographs on purpose);
- type leaves the safe area or is cut by the frame, two lines of type overlap, a line set on an object (a tag, a
  tub, a strip of tape) leaves it, free words run into a bar, or free words cross a cut's edge onto its photograph
  or run onto a slice;
- a tag, a strip of tape or a photograph drawn later covers a count that is not its own;
- a count is drawn smaller than the tone's floor;
- a strand of twine is not one, two or three square runs, two strands' lanes run closer than LANE px, a strand
  crosses free words, or a strand reaches a square the frame does not hold whole within HOLD frames of arriving.

Run as `python3 bounds.py <board.json>...`: prints the findings and exits 1 when there are any."""
import json
import math
import sys

from compose import FPS, Frame, framing, hull, pulse_of, text_box, to_screen, turned

GUTTER = 12
LANE = 24
HOLD = 15
COUNT_FLOOR = {"drive": 40, "film": 13, "calm": 34}
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

    def on(self, at, extra=0.0):
        return (at + extra) * self.pulse <= self.f

    def place(self, layer, box):
        if layer["kind"] in UNMOVED or layer.get("fixed"):
            return tuple(box)
        return to_screen(self.cam, self.frame, box)

    def scale_of(self, layer):
        return 1.0 if layer["kind"] in UNMOVED or layer.get("fixed") else self.cam[0]

    def add(self, kind, layer, n, box, **kw):
        self.items.append({"kind": kind, "layer": layer["kind"], "n": n, "box": box, **kw})

    def text(self, layer, n, line, parent=None, count=False, owner=None):
        line = dict(line)
        ink = turned(text_box(self.S, line, ink=True), line)
        em = hull(turned(text_box(self.S, line), line))
        quad = [self.place(layer, (x, y, x, y))[:2] for x, y in ink]
        self.add("text", layer, n, self.place(layer, em), ink=hull(quad), quad=quad, name=line.get("name") or line["text"], parent=parent,
                 local=hull(ink), count=count, owner=owner, size=line["size"] * self.scale_of(layer), free=layer["kind"] == "Words",
                 under=bool(layer.get("under")))

    def read(self, n, L):
        k = L["kind"]
        at = L.get("at", 0)
        if k == "Words":
            if self.on(at):
                for line in L["lines"]:
                    self.text(L, n, line, count=str(line.get("name", "")).startswith("count-"), owner=line.get("owner"))
        elif k == "Tile":
            if self.on(at) or L.get("empty"):
                self.add("photo", L, n, self.place(L, rect(L["box"])), owner=L.get("owner"), empty=not self.on(at))
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
        elif k == "Tub":
            b = rect(L["box"])
            self.add("photo", L, n, self.place(L, b), owner=L.get("rank"))
            if self.on(at, L["level"] * L.get("beatsPerFull", 4) + 0.25):
                x, y, w, h = L["box"]
                wall = max(6, w * 0.028)
                top = y + h * 0.045
                ih = y + h - wall - top
                cy = top + ih * (1 - L["level"]) - L.get("tapeH", 52) / 2 + 3
                th = L.get("tapeH", 52)
                tb = (L["tapeX"], cy - th / 2, L["tapeX"] + L["tapeW"], cy + th / 2)
                self.add("opaque", L, n + 0.5, self.place(L, tb), owner=L.get("rank"))
                for line in L.get("tape", []):
                    self.text(L, n + 0.6, line, parent=tb, count=str(line.get("name", "")).startswith("count-"), owner=L.get("rank"))
        elif k == "Tag":
            if self.on(at):
                px, py = L["pos"]
                w, h = L["w"], L["h"]
                ch = min(16, h * 0.25, w * 0.12)
                hx, hy = (w / 2, ch * 0.95) if L.get("hole") == "top" else (ch * 0.95, h / 2)
                x0, y0 = px - hx, py - hy
                b = (x0, y0, x0 + w, y0 + h)
                self.add("opaque", L, n, self.place(L, b), owner=L.get("owner"))
                for line in L["lines"]:
                    self.text(L, n + 0.5, dict(line, x=x0 + line["x"], y=y0 + line["y"]), parent=b,
                              count=str(line.get("name", "")).startswith("count-"), owner=L.get("owner"))
        elif k == "Tape":
            if self.on(at):
                b = (L["x"], L["y"] - L.get("h", 56) / 2, L["x"] + L["w"], L["y"] + L.get("h", 56) / 2)
                self.add("opaque", L, n, self.place(L, b), owner=None, free=True)
                for line in L.get("lines", []):
                    self.text(L, n + 0.5, line, parent=b)
        elif k == "YearRule":
            for m in L.get("months", []):
                self.text(L, n, {"text": m["label"], "x": m["x"] + 5, "y": L["y"] - 14, "size": L.get("labelSize", 20), "face": "text", "weight": 500,
                                 "tracking": 0.02})
            if L.get("next") and self.on(L.get("nextAt", 0)):
                self.text(L, n, {"text": L["next"]["label"], "x": L["x1"] + 8, "y": L["y"] - 14, "size": L.get("labelSize", 20), "face": "text",
                                 "weight": 700, "tracking": 0.02})
        elif k == "Scale":
            for r in L["rows"]:
                for j, q in enumerate((0.25, 0.5, 0.75, 1)):
                    if j < len(L["labels"]):
                        y = r["bottom"] + (r["top"] - r["bottom"]) * q
                        self.text(L, n, {"text": L["labels"][j], "x": L["x"], "y": y + L["size"] * 0.36, "size": L["size"], "face": "text",
                                         "weight": 500, "anchor": "end"})
        elif k == "Twine":
            if self.on(at):
                pts = [self.place(L, (p[0], p[1], p[0], p[1]))[:2] for p in L["points"]]
                self.add("strand", L, n, None, points=pts, scene=L["points"], dest=L.get("dest"), destBox=L.get("destBox"),
                         arrive=at + L.get("beats", 1))


def framebox(fr):
    return (0, 0, fr.W, fr.H)


def check_shot(sh, tone):
    """The findings for one shot at rest, as strings naming the beat and what is wrong."""
    out = []
    fr, bid = sh.frame, sh.beat["id"]
    F = framebox(fr)
    safe = fr.safe
    photos = [e for e in sh.items if e["kind"] == "photo"]
    texts = [e for e in sh.items if e["kind"] == "text"]
    opaque = [e for e in sh.items if e["kind"] == "opaque"] + photos

    def say(msg):
        out.append(f"{bid}: {msg}")

    for p in photos:
        b = p["box"]
        if not meets(b, F):
            continue
        what = f"{'empty square' if p.get('empty') else 'photograph'} {p.get('owner')}"
        if not inside(b, F):
            say(f"{what} is cut by the frame")
        elif min(b[0], b[1], fr.W - b[2], fr.H - b[3]) < GUTTER - 0.5:
            say(f"{what} is {min(b[0], b[1], fr.W - b[2], fr.H - b[3]):.0f} px from the frame edge")
    for i, a in enumerate(photos):
        for b in photos[i + 1:]:
            if area(a["box"], b["box"]) > 1:
                say(f"photographs {a.get('owner')} and {b.get('owner')} overlap")
    for p in photos:
        if not meets(p["box"], F):
            continue
        for t in texts:
            if t["free"] and not t["under"] and meets(p["box"], t["ink"], GUTTER):
                say(f"words {t['name']!r} come within {GUTTER} px of photograph {p.get('owner')}")
    for t in texts:
        e = t["box"]
        if not meets(e, F):
            continue
        if not inside(e, F):
            say(f"type {t['name']!r} is cut by the frame")
        elif not inside(e, safe, 2):
            say(f"type {t['name']!r} leaves the safe area")
        if t["parent"] and not inside(t["local"], t["parent"], 1):
            say(f"type {t['name']!r} leaves its {t['layer'].lower()}")
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
    strands = [e for e in sh.items if e["kind"] == "strand"]
    for s in strands:
        pts = s["scene"]
        segs = list(zip(pts, pts[1:]))
        if len(segs) > 3:
            say(f"strand to {s['dest']} turns {len(segs) - 1} times")
        if any(abs(a[0] - b[0]) > 0.5 and abs(a[1] - b[1]) > 0.5 for a, b in segs):
            say(f"strand to {s['dest']} runs on a slant")
        sp = s["points"]
        for a, b in zip(sp, sp[1:]):
            seg = (min(a[0], b[0]) - 2, min(a[1], b[1]) - 2, max(a[0], b[0]) + 2, max(a[1], b[1]) + 2)
            for t in texts:
                if t["free"] and area(seg, t["ink"]) > 0:
                    say(f"strand to {s['dest']} crosses {t['name']!r}")
    lanes = []
    for s in strands:
        for a, b in zip(s["scene"], s["scene"][1:]):
            if abs(a[1] - b[1]) < 0.5 and abs(a[0] - b[0]) > 0.5:
                lanes.append((s["dest"], a[1], min(a[0], b[0]), max(a[0], b[0])))
    for i, a in enumerate(lanes):
        for b in lanes[i + 1:]:
            if a[0] != b[0] and a[2] < b[3] and b[2] < a[3] and abs(a[1] - b[1]) < LANE:
                say(f"lanes to {a[0]} and {b[0]} run {abs(a[1] - b[1]):.0f} px apart")
    return out


def arrivals(board, i, sh):
    """Each strand that arrives inside the shot: its square must be whole in the frame HOLD frames on, in this shot or,
    when the shot ends first, in the next one."""
    out = []
    beat = board["beats"][i]
    for s in [e for e in Shot(board, i, beat["frames"] - 1).items if e["kind"] == "strand"]:
        fa = s["arrive"] * sh.pulse
        if fa < 0 or fa >= beat["frames"] or s["dest"] is None:
            continue
        fh = math.ceil(fa) + HOLD
        if fh < beat["frames"] or i + 1 == len(board["beats"]):
            later = Shot(board, i, min(fh, beat["frames"] - 1))
        else:
            later = Shot(board, i + 1, min(fh - beat["frames"], board["beats"][i + 1]["frames"] - 1))
        box = None
        if s["destBox"]:
            box = later.place({"kind": "Tile"}, rect(s["destBox"]))
        else:
            for e in later.items:
                if e["kind"] == "photo" and e.get("owner") == s["dest"] and e["layer"] == "Tile":
                    box = e["box"]
        if box is None or not inside(box, framebox(later.frame)):
            out.append(f"{beat['id']}: strand to {s['dest']} arrives at a square the frame does not hold whole")
    return out


def check(board):
    """Every finding on the board, at each shot's rest."""
    tone = board.get("tone", "")
    out = []
    for i in range(len(board["beats"])):
        sh = Shot(board, i)
        out += check_shot(sh, tone)
        out += arrivals(board, i, sh)
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
