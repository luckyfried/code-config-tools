#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film of the same places, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, every place, assets, text, clips, 30-60 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (the travel palette, type direction, register, the places and their words),
then build/places.json (the places, the route, the legs and their distances), picks.json (each place's photos and
reels), stats.json and research.json. The three boards differ on structure, tone and how generated clips are used:
  1  the route        a map journey: the route draws itself leg by leg in their colors,      documentary
                      a photo pinned at each arrival, the whole map at the end               still-first; a generated
                                                                                             opener and a flyover on the far leg
  2  passport         one stamp per place, each stamp built from that place's photos,        editorial
                      the page filling up, the whole passport page at the end                still-first; generated
                                                                                             establishing shots of two places
  3  day to night     the year as one long day: dawn in the first place, night in the last,  kinetic
                      the sky turning across the places, the map lit up at the end           clip-first; their own reels
                                                                                             play in the places they were shot
Every beat names the places it shows (data.focus); every place has a beat of its own. Every board carries the
poster (1080x1350): the map of the year's places, the route and the count, in the board's palette and type. The
map is drawn from the places' coordinates over the land shapes in data/land.json (Natural Earth, public domain);
no map tile is fetched. The agent may edit any storyboard.json (text, order, photos, prompts) before sheets; check
validates it.
"""
import argparse
import datetime as dt
import math
import json
import re
import shutil
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import grade  # noqa: E402

DESIGN = _env.SKILL / "design"
BOARDS = Path("build/storyboards")
FPS = 30
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
LENGTH = (30, 60)
MAX_LEG_BEATS = 16
REEL = (1080, 1920)
POSTER = (1080, 1350)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728\uFE0F\u200D]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}


def design(name):
    return json.loads((DESIGN / name).read_text())


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, t):
    a, b = hex_rgb(a), hex_rgb(b)
    return rgb_hex([x + (y - x) * t for x, y in zip(a, b)])


def lum(h):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sat(h):
    r, g, b = (c / 255 for c in hex_rgb(h))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx


def readable(c, bg, need=3.0):
    """Move c toward black or white until it reads on bg."""
    target = "#000000" if lum(bg) > 0.4 else "#ffffff"
    for i in range(21):
        x = mix(c, target, i / 20)
        if contrast(x, bg) >= need:
            return x
    return target


def luma(h):
    r, g, b = hex_rgb(h)
    return 0.299 * r + 0.587 * g + 0.114 * b


def lift(sea, land, floor=46):
    """A dark sea moved toward the land until its luma reaches the floor (0-255), so a frame that is mostly open water
    never reads as black."""
    t = 0.0
    while luma(mix(sea, land, t)) < floor and t < 1:
        t += 0.05
    return mix(sea, land, min(t, 1))


def merc(lat, lon):
    lat = max(-85.0, min(85.0, lat))
    x = (lon + 180) / 360 * 1000
    y = (1 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / math.pi) / 2 * 1000
    return round(x, 3), round(y, 3)


def fit(points, w, h, pad=0.3, min_span=8.0):
    """A camera [cx, cy, span] (span: the frame's width in world units) that holds every point inside a w x h frame."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    span = max(bw * (1 + 2 * pad), bh * (1 + 2 * pad) * w / h, min_span)
    return [round((max(xs) + min(xs)) / 2, 3), round((max(ys) + min(ys)) / 2, 3), round(span, 3)]


def arc(a, b, n=28, bend=0.16):
    """A leg as a gentle curve from a to b in world units: a quadratic bend to the left of the direction of travel."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2 - dy * bend, (y0 + y1) / 2 + dx * bend
    out = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
        out.append([round(x, 3), round(y, 3)])
    return out


def project(cam, w, h, x, y):
    cx, cy, span = cam
    k = w / span
    return (x - cx) * k + w / 2, (y - cy) * k + h / 2


def label_sides(pins, cam, rect, size, text_w=0.56, blocks=(), bound=None):
    """Where each pin's label sits (right, left, above, below), greedily, so no two labels and no label and pin overlap
    and every label stays inside the map rect. pins: [(id, name, x, y, weight)] in world units; rect: [x, y, w, h] px."""
    rx, ry, rw, rh = rect
    placed, out = [], {}
    dots = []
    for pid, name, x, y, _ in pins:
        px, py = project(cam, rw, rh, x, y)
        dots.append((pid, px, py))
    pos = {pid: (px, py) for pid, px, py in dots}

    def box(pid, name, side):
        px, py = pos[pid]
        tw, th, g = len(name) * size * text_w + size * 0.3, size * 1.2, size * 0.55
        if side == "right":
            return (px + g, py - th / 2, px + g + tw, py + th / 2)
        if side == "left":
            return (px - g - tw, py - th / 2, px - g, py + th / 2)
        if side == "above":
            return (px - tw / 2, py - g - th, px + tw / 2, py - g)
        return (px - tw / 2, py + g, px + tw / 2, py + g + th)

    def overlap(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))

    b0 = bound or (0, 0, rw, rh)

    def cost(pid, bx, others):
        c = sum(overlap(bx, o) for o in others) * 6
        c += sum(overlap(bx, (dx - size * 0.4, dy - size * 0.4, dx + size * 0.4, dy + size * 0.4)) for q, dx, dy in dots if q != pid) * 3
        out_of = max(0, b0[0] - bx[0]) + max(0, bx[2] - b0[2]) + max(0, b0[1] - bx[1]) + max(0, bx[3] - b0[3])
        return c + out_of * size * 4 + sum(overlap(bx, k) * 2 for k in blocks)

    order = sorted(pins, key=lambda p: -p[4])
    boxes = {}
    for pid, name, x, y, _ in order:
        best = min((cost(pid, box(pid, name, sd), placed), i, sd) for i, sd in enumerate(SIDES))
        out[pid] = best[2]
        boxes[pid] = box(pid, name, best[2])
        placed.append(boxes[pid])
    for _ in range(4):
        moved = False
        for pid, name, x, y, _ in order:
            others = [v for k, v in boxes.items() if k != pid]
            best = min((cost(pid, box(pid, name, sd), others), i, sd) for i, sd in enumerate(SIDES))
            if best[2] != out[pid] and best[0] < cost(pid, boxes[pid], others):
                out[pid], boxes[pid], moved = best[2], box(pid, name, best[2]), True
        if not moved:
            break
    return out


SIDES = ("right", "left", "above", "below")


def nice_date(a, b=None):
    """mar 3, or mar 3 to 10, or mar 28 to apr 2."""
    if not a:
        return ""
    da = dt.date.fromisoformat(a[:10])
    s = f"{MON[da.month - 1]} {da.day}"
    if not b or b[:10] == a[:10]:
        return s
    db = dt.date.fromisoformat(b[:10])
    return s + (f" to {db.day}" if db.month == da.month else f" to {MON[db.month - 1]} {db.day}")


class Ctx:
    def __init__(self):
        self.taste = _env.read_json("build/taste.json")
        if not self.taste:
            sys.exit("build/taste.json is missing: run research.py and write the taste profile first")
        if not Path("build/taste.md").exists():
            sys.exit("build/taste.md is missing: write the taste profile (movement 1) before storyboards")
        self.pl = _env.read_json("build/places.json")
        if not self.pl or not self.pl.get("places"):
            sys.exit("build/places.json has no places: run research.py (places.py names what it found and why)")
        self.stats = _env.read_json("build/stats.json") or {}
        picks = _env.read_json("build/picks.json") or {}
        self.picks = picks.get("chapters", {})
        self.place_picks = picks.get("places", {})
        self.research = _env.read_json("build/research.json") or {}
        self.handle = self.stats.get("handle") or self.taste.get("handle") or "you"
        self.year = int(self.stats.get("year") or self.taste.get("year"))
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        self.places = sorted(self.pl["places"], key=lambda p: p.get("first") or "")
        self.by = {p["id"]: p for p in self.places}
        names = {x["id"]: x for x in self.taste.get("places") or [] if x.get("id")}
        for p in self.places:
            t = names.get(p["id"]) or {}
            if t.get("name"):
                p["name"] = t["name"]
            p["their_words"] = t.get("words") or p.get("words") or []
        self.home = self.pl.get("home")
        self.far = set(self.pl.get("far") or [])
        self.km = int(self.pl.get("total_km") or 0)
        self.n = len(self.places)

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def name(self, pid):
        return self.say(self.by[pid]["name"])

    def photo(self, src):
        """A library photo as the graded file the renderer reads (relative to build/)."""
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        if not p:
            return None
        return grade.graded_name(p)

    def photos_of(self, pid, n=3, start=0):
        """The place's photos, best first (picks.py puts one from each visit first)."""
        got = (self.place_picks.get(pid) or {}).get("photos") or []
        out = []
        for k in range(len(got)):
            p = self.photo(got[(start + k) % len(got)])
            if p and p not in out:
                out.append(p)
            if len(out) >= n:
                break
        return out

    def reel_of(self, pid):
        c = (self.place_picks.get(pid) or {}).get("clips") or []
        return c[0] if c else None

    def words(self, pid):
        """Their own line about the place, for the screen: the first caption that names it, cleaned."""
        for w in self.by[pid].get("their_words") or []:
            s = short(w, 48)
            if len(s) >= 6:
                return self.say(s)
        return None

    def opener_photo(self):
        o = self.picks.get("opener") or []
        p = self.photo(o[0]) if o else None
        if p:
            return p
        away = [p for p in self.places if not p.get("home")] or self.places
        got = self.photos_of(away[0]["id"], 1)
        return got[0] if got else None

    def count_line(self):
        return self.say(f"{self.year} in {self.n} places")

    def km_line(self):
        return self.say(f"{self.km:,} km along the way") if self.km else None

    def pal(self):
        p = self.taste.get("palette", {})
        return [s for s in (p.get(p.get("direction") or "travel") or p.get("year") or []) if s.get("hex")]

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        year = [s["hex"] for s in self.pal()] or ["#6b5440", "#b8a17f"]
        likes = [s["hex"] for s in self.taste.get("palette", {}).get("likes", []) if s.get("hex")]
        allc = year + likes
        darkest = min(allc, key=lum)
        lightest = max(allc, key=lum)
        vivid = sorted(likes or year, key=lambda h: -sat(h) * (0.4 + lum(h)))
        warm = max(year, key=lambda h: sat(h) * (0.3 + lum(h)))
        tex = self.taste.get("texture", {})
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.55)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(vivid[1] if len(vivid) > 1 else year[0], paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
            sea, land = mix(paper, year[0], 0.08), mix(paper, warm, 0.42)
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.6)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            accent = vivid[0]
            accent2 = vivid[1] if len(vivid) > 1 else year[0]
            if contrast(ink, accent) < 2.2:
                accent = mix(accent, "#000000", 0.25)
            if contrast(ink, accent2) < 2.2:
                accent2 = mix(accent2, "#000000", 0.35)
            texture = {"grain": round(tex.get("grain", 0) * 0.5, 3), "vignette": 0, "leaks": False}
            land = mix(bg, warm, 0.28)
            sea = lift(mix(bg, land, 0.3), land)
        else:
            bg = mix(darkest, "#000000", 0.7)
            ink = mix(lightest, "#ffffff", 0.5)
            paper = mix(lightest, "#f4ead8", 0.5)
            accent = readable(vivid[0], bg, 4)
            accent2 = vivid[1] if len(vivid) > 1 else year[0]
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
            land = mix(bg, warm, 0.5)
            sea = lift(bg, land)
        swatches = [{"hex": s["hex"], "name": self.say(s.get("name") or "")} for s in self.pal()][:5]
        if luma(sea) < 110 and luma(land) - luma(sea) < 24:
            land = lift(land, mix(warm, ink, 0.3), luma(sea) + 24)
        route = readable(accent, mix(sea, land, 0.5), 2.4)
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": swatches},
            "map": {"sea": sea, "land": land, "coast": mix(land, ink, 0.22), "route": route, "pin": route,
                    "label": readable(ink, land, 4.5), "halo": land if lum(land) < lum(ink) else sea},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, subject, direction, seconds):
        t = self.taste
        colors = [s.get("name") for s in t.get("palette", {}).get("likes", [])[:3] if s.get("name")] + \
                 [s.get("name") for s in self.pal()[:2] if s.get("name")]
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "a fast push-in and a whip pan, bold graphic framing",
                  "documentary": "a slow aerial drift, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no maps, no people's faces.")

    def map_data(self):
        """The shared map: every place as a pin, every leg of the route as a curve, in world units (web mercator,
        0 to 1000 across the world), and the cameras the poster uses."""
        if hasattr(self, "_map"):
            return self._map
        pins = []
        for p in self.places:
            x, y = p.get("x"), p.get("y")
            if x is None:
                x, y = merc(p["lat"], p["lon"])
            pins.append({"id": p["id"], "name": self.name(p["id"]), "x": x, "y": y, "far": p["id"] in self.far,
                         "home": bool(p.get("home")), "rows": p.get("rows", 1), "km_from_home": p.get("km_from_home")})
        at = {q["id"]: (q["x"], q["y"]) for q in pins}
        legs = []
        for lg in self.pl.get("legs") or []:
            if lg["from"] in at and lg["to"] in at:
                legs.append({"from": lg["from"], "to": lg["to"], "km": lg["km"], "far": bool(lg.get("far")),
                             "arc": arc(at[lg["from"]], at[lg["to"]], 40 if lg.get("far") else 28, 0.12 if lg.get("far") else 0.16)})
        self._map = {"land": "map/land.json", "pins": pins, "legs": legs, "route": self.pl.get("route") or []}
        return self._map

    def cam(self, ids, w, h, pad=0.3, min_span=8.0):
        at = {q["id"]: (q["x"], q["y"]) for q in self.map_data()["pins"]}
        pts = [at[i] for i in ids if i in at] or list(at.values())
        return fit(pts, w, h, pad, min_span)

    def near_ids(self):
        return [p["id"] for p in self.places if p["id"] not in self.far] or [p["id"] for p in self.places]

    def map_layout(self, fmt, direction):
        """The poster's map, laid out for one format: the map rect, the region camera, the inset for far places and
        each label's side. Pixel rects are [x, y, w, h]; the inset's rect is inside the map rect. The inset takes a
        strip on one side of the map (the side that leaves the region largest), and the region's pins are fitted to
        the rest, so no pin sits under the inset."""
        W, H = POSTER if fmt == "poster" else REEL
        rect = [0, 250, W, 900] if fmt == "poster" else [0, 210, W, 870]
        sa = design("safe-areas.json")[fmt]
        lo, hi = sa["left"] + 20, W - sa["right"] - 20
        near = self.near_ids()
        at = {q["id"]: (q["x"], q["y"]) for q in self.map_data()["pins"]}
        pts = [at[i] for i in near]
        far = [p["id"] for p in self.places if p["id"] in self.far]
        size = 30 if fmt == "poster" else 34
        face = design("type.json")[direction]["text"]["family"]
        text_w = 0.64 if "Mono" in face else 0.58
        m = 40
        subs = [("none", [lo, 40, hi - lo, rect[3] - 80], None)]
        if far:
            iw, ih = (330, 260) if fmt == "poster" else (300, 240)
            fx = sum(at[i][0] for i in far) / len(far)
            cx = sum(x for x, _ in pts) / len(pts)
            west = fx < cx
            ix = m if west else rect[2] - iw - m
            subs = [("side", [ix + iw + 30, 40, hi - (ix + iw + 30), rect[3] - 80] if west else [lo, 40, ix - 30 - lo, rect[3] - 80],
                     [ix, rect[3] - ih - m, iw, ih]),
                    ("bottom", [lo, 40, hi - lo, rect[3] - ih - 2 * m - 40], [ix, rect[3] - ih - m, iw, ih])]
        best = None
        for kind, sub, irect in subs:
            c = fit(pts, sub[2], sub[3], 0.08, 10)
            if best is None or c[2] * rect[2] / sub[2] < best[0]:
                best = (c[2] * rect[2] / sub[2], sub, irect, c)
        span, sub, irect, c = best
        k = rect[2] / span
        cam = [round(c[0] - (sub[0] + sub[2] / 2 - rect[2] / 2) / k, 3), round(c[1] - (sub[1] + sub[3] / 2 - rect[3] / 2) / k, 3), round(span, 3)]
        inset = {"rect": irect, "cam": self.cam(far, irect[2], irect[3], 0.5, 30), "ids": far} if irect else None
        pins = [(q["id"], q["name"], q["x"], q["y"], q["rows"]) for q in self.map_data()["pins"] if q["id"] in near]
        blocks = [(irect[0] - 10, irect[1] - 10, irect[0] + irect[2] + 10, irect[1] + irect[3] + 10)] if irect else []
        bound = (lo - rect[0], 0, hi - rect[0], rect[3])
        sides = label_sides(pins, cam, rect, size, text_w, blocks=blocks, bound=bound)
        if inset:
            ipins = [(q["id"], q["name"], q["x"], q["y"], q["rows"]) for q in self.map_data()["pins"] if q["id"] in far]
            sides.update(label_sides(ipins, inset["cam"], irect, round(size * 0.85), text_w))
        return {"rect": rect, "cam": cam, "inset": inset, "labels": sides, "size": size}


def focus(ids):
    return [i for i in ids if i]


def short(cap, limit=60):
    """A caption's lead line for the screen: no hashtags or emoji, cut at a clause or a word, never on a function word."""
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    c = re.sub(r"\s+", " ", c)
    for sep in (". ", ": ", "; ", " - "):
        if sep in c and len(c.split(sep)[0]) >= 14:
            c = c.split(sep)[0]
            break
    if len(c) > limit and ", " in c[:limit] and len(c[:limit].rsplit(", ", 1)[0]) >= 14:
        c = c[:limit].rsplit(", ", 1)[0]
    if len(c) > limit:
        c = c[:limit].rsplit(" ", 1)[0]
    w = c.split()
    while len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


def tr(preset, direction, d=None):
    f = design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))



def target_seconds(ctx):
    """The film's length grows with the places: about 2.2 s a place on an 18 s frame, inside 32-58 s."""
    return max(32.0, min(58.0, 18 + 2.2 * ctx.n))


def place_label(ctx, pid, visit=None):
    p = ctx.by[pid]
    v = visit or {}
    return {"name": ctx.name(pid), "country": ctx.say(p.get("country") or ""),
            "when": ctx.say(nice_date(v.get("from") or p.get("first"), v.get("to") or (p.get("last") if not visit else None))),
            "visits": p.get("visits", 1), "km_from_home": p.get("km_from_home", 0)}


def opener(ctx, headline, line, clip="01", kicker=None):
    return {"id": "opener", "kind": "Opener", "frames": sec(2.6), "transition": None, "photos": [ctx.opener_photo()],
            "text": {"kicker": kicker or f"@{ctx.handle}", "headline": headline, "line": line}, "clip": clip,
            "data": {"focus": []}}


def poster_beat(ctx, bid, frames, transition, direction, night=False, kicker=None):
    return {"id": bid, "kind": "Poster", "frames": frames, "transition": transition, "photos": [],
            "text": {"kicker": kicker or f"@{ctx.handle}", "headline": ctx.count_line(), "line": ctx.km_line()},
            "data": {"layout": {"poster": ctx.map_layout("poster", direction), "reel": ctx.map_layout("reel", direction)}, "night": night, "focus": []}}


def leg_groups(n):
    size = max(1, math.ceil(n / MAX_LEG_BEATS))
    return [list(range(i, min(n, i + size))) for i in range(0, n, size)]


def board_route(ctx):
    d = "documentary"
    m = ctx.map_data()
    legs = m["legs"]
    stops = ctx.pl.get("route_visits") or []
    W, H = REEL
    everyone = [p["id"] for p in ctx.places]
    first_cam = ctx.cam([legs[0]["from"], legs[0]["to"]], W, H, 0.6, 13) if legs else ctx.cam(everyone, W, H)
    beats = [opener(ctx, ctx.say("where the year went"), ctx.count_line()),
             {"id": "overview", "kind": "MapJourney", "frames": sec(2.6), "transition": tr("iris", d), "photos": [],
              "text": {"kicker": ctx.say(f"{ctx.year}"), "headline": ctx.say(f"{ctx.n} places on one map")},
              "data": {"mode": "overview", "cam0": ctx.cam(everyone, W, H, 0.12, 10), "cam1": first_cam, "done": 0, "legs": [], "focus": []}}]
    clips = [{"id": "01", "beat": "opener", "role": "the opener: the first place of the year, from above",
              "prompt": ctx.prompt(f"an establishing aerial shot drifting over the rooftops of {ctx.by[ctx.places[0]['id']]['name']}, "
                                   f"{ctx.by[ctx.places[0]['id']].get('country', '')}, at first light", d, 3), "seconds": 3, "image": None}]
    seen, cam0, flown, pinned = {}, first_cam, False, []
    for g in leg_groups(len(legs)):
        last = legs[g[-1]]
        to, frm = last["to"], legs[g[0]]["from"]
        k = seen.get(to, 0)
        seen[to] = k + 1
        visit = stops[g[-1] + 1] if g[-1] + 1 < len(stops) else None
        far = any(legs[i]["far"] for i in g)
        if far and not flown and to in ctx.far:
            flown = True
            clips.append({"id": "02", "beat": f"fly-{to}", "role": "the flyover on the far leg",
                          "prompt": ctx.prompt(f"a slow aerial flyover high above the open ocean and a sea of clouds, the coast of "
                                               f"{ctx.by[to].get('country') or ctx.by[to]['name']} rising on the horizon at golden hour", d, 2),
                          "seconds": 2, "image": None})
            beats.append({"id": f"fly-{to}", "kind": "ClipShot", "frames": sec(2.0), "transition": tr("dip", d), "clip": "02",
                          "photos": ctx.photos_of(to, 1), "text": {"kicker": ctx.say(f"{last['km']:,} km"), "headline": ctx.say(f"to {ctx.by[to]['name']}")},
                          "data": {"focus": [to]}})
        back = frm in ctx.far and to not in ctx.far
        cam1 = ctx.cam(ctx.near_ids(), W, H, 0.3, 13) if back else ctx.cam([frm] + [legs[i]["to"] for i in g], W, H, 0.45 if far else 0.6, 13)
        ph = ctx.photos_of(to, 1, start=k)
        home = to == ctx.home
        again = k > 0
        lab = place_label(ctx, to, visit)
        kicker = ctx.say(("home, " if home else "again, " if again else "") + (lab["when"] or ""))
        line = ctx.say(f"{'back home, ' if home else ''}{last['km']:,} km from {ctx.by[last['from']]['name']}")
        beats.append({"id": f"leg-{g[-1] + 1:02d}-{to}", "kind": "MapJourney", "frames": sec(2.9 if far else 2.3),
                      "transition": tr("fade", d), "photos": ph,
                      "text": {"kicker": kicker, "headline": ctx.name(to), "line": line},
                      "data": {"mode": "leg", "legs": g, "done": g[0], "cam0": cam0, "cam1": cam1, "arrive": to,
                               "card": {"photo": ph[0] if ph else None, "again": again, **lab},
                               "pinned": list(pinned), "focus": sorted({legs[i]["to"] for i in g})}})
        if ph and to not in {x["id"] for x in pinned}:
            pinned.append({"id": to, "photo": ph[0]})
        cam0 = cam1
    beats.append(poster_beat(ctx, "the-map", sec(3.6), tr("dip", d), d))
    return finish(ctx, {"id": "1", "name": ctx.say("the route"), "direction": d,
                        "structure": "a map journey: the route draws itself leg by leg, a photo pinned at each arrival, the whole map at the end",
                        "tone": "documentary",
                        "clip_use": "still-first: a generated aerial opener over the first place and a flyover on the far leg",
                        "idea": ctx.say("the year as a line on a map in their colors: it leaves home, draws itself to each place in "
                                        "the order they went, pins a photo of theirs at every arrival with the date and the distance, "
                                        "and pulls back to the whole map with the count."),
                        "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": beats, "clips": clips})


SHAPES = ["circle", "rect", "octagon", "oval"]


def stamp_of(ctx, i, pid):
    ph = ctx.photos_of(pid, 3)
    tilt = round(((zlib.crc32(pid.encode()) % 1000) / 1000 - 0.5) * 14, 1)
    return {"id": pid, "name": ctx.name(pid), "shape": SHAPES[i % len(SHAPES)], "tilt": tilt, "photos": ph,
            **{k: v for k, v in place_label(ctx, pid).items() if k != "name"}}


def board_passport(ctx):
    d = "editorial"
    home = ctx.by.get(ctx.home) or ctx.places[0]
    clips = [{"id": "01", "beat": "opener", "role": "the opener: home, before the year sets out",
              "prompt": ctx.prompt(f"an establishing shot of {home['name']}, {home.get('country', '')}: rooftops, a quiet street "
                                   f"and morning light through a window", d, 3), "seconds": 3, "image": None}]
    beats = [opener(ctx, ctx.say(f"{ctx.year}, stamped"), ctx.say(f"{ctx.n} places, one passport"))]
    away = [p for p in ctx.places if p["id"] != ctx.home]
    wanted = [p["id"] for p in away if p["id"] in ctx.far][:1]
    wanted += [p["id"] for p in sorted(away, key=lambda p: -p.get("rows", 0)) if p["id"] not in wanted][:2 - len(wanted)]
    stamps = []
    for i, p in enumerate(ctx.places):
        pid = p["id"]
        if pid in wanted:
            cid = f"{len(clips) + 1:02d}"
            clips.append({"id": cid, "beat": f"arrive-{pid}", "role": f"an establishing shot of {p['name']}",
                          "prompt": ctx.prompt(f"an establishing shot of {p['name']}, {p.get('country', '')}: its streets, rooftops "
                                               f"and light, seen the way a traveler first sees it", d, 2), "seconds": 2, "image": None})
            beats.append({"id": f"arrive-{pid}", "kind": "ClipShot", "frames": sec(1.8), "transition": tr("wipe", d, "from-right"),
                          "clip": cid, "photos": ctx.photos_of(pid, 1), "text": {"kicker": ctx.say(p.get("country") or "")},
                          "data": {"focus": [pid]}})
        st = stamp_of(ctx, i, pid)
        words = ctx.words(pid)
        beats.append({"id": f"stamp-{pid}", "kind": "Stamp", "frames": sec(2.5),
                      "transition": tr("wipe", d, "from-left") if beats[-1]["kind"] == "ClipShot" else tr("fade", d),
                      "photos": st["photos"],
                      "text": {"kicker": ctx.say(f"{i + 1} of {ctx.n} · {st['when']}"), "headline": st["name"],
                               "line": words or ctx.say(st["country"])},
                      "data": {"mode": "stamp", "stamp": st, "page": [dict(x, photos=x["photos"][:1]) for x in stamps], "focus": [pid]}})
        stamps.append(st)
    beats.append({"id": "the-page", "kind": "Stamp", "frames": sec(3.4), "transition": tr("dip", d), "photos": [],
                  "text": {"kicker": f"@{ctx.handle}", "headline": ctx.count_line(), "line": ctx.km_line()},
                  "data": {"mode": "page", "page": [dict(x, photos=x["photos"][:1]) for x in stamps], "focus": []}})
    return finish(ctx, {"id": "2", "name": ctx.say("passport"), "direction": d,
                        "structure": "a passport page filling up: one stamp per place, each built from that place's photos, then the whole page",
                        "tone": "quiet editorial",
                        "clip_use": "still-first: generated establishing shots of two places in their palette",
                        "idea": ctx.say("a passport page on warm paper: each place lands as an inked stamp made of its own photos, "
                                        "with the dates and their words, the earlier stamps staying on the page, until the page is full."),
                        "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"},
                        "beats": beats, "clips": clips})


def board_day(ctx):
    d = "kinetic"
    first = ctx.places[0]
    clips = [{"id": "01", "beat": "opener", "role": "the opener: first light",
              "prompt": ctx.prompt(f"first light over {first['name']}: dawn breaking over the rooftops, the sky turning from deep "
                                   f"blue to peach", d, 3), "seconds": 3, "image": None}]
    beats = [opener(ctx, ctx.say("one long day"), ctx.say(f"{ctx.n} places, dawn to night"))]
    n = ctx.n
    step = 0.86 / max(1, n)
    for i, p in enumerate(ctx.places):
        pid = p["id"]
        lab = place_label(ctx, pid)
        reel = ctx.reel_of(pid)
        b = {"id": f"day-{pid}", "kind": "DayNight", "frames": sec(3.0 if reel else 2.4),
             "transition": tr("whip", d, "from-right" if i % 2 == 0 else "from-left"), "photos": ctx.photos_of(pid, 2),
             "text": {"kicker": lab["when"], "headline": lab["name"], "line": ctx.words(pid)},
             "data": {"phase": [round(0.06 + i * step, 3), round(0.06 + (i + 1) * step, 3)], "label": lab, "focus": [pid]}}
        if reel:
            cid = f"{len(clips) + 1:02d}"
            b["clip"] = cid
            clips.append({"id": cid, "beat": b["id"], "role": f"their own reel from {p['name']}", "prompt": None,
                          "source": reel["video"], "seconds": 3, "image": ctx.photo(reel["poster"]) if reel.get("poster") else None})
        beats.append(b)
    beats.append(poster_beat(ctx, "lights", sec(3.4), tr("bars", d), d, night=True))
    return finish(ctx, {"id": "3", "name": ctx.say("day to night"), "direction": d,
                        "structure": "the year as one long day: dawn in the first place, night in the last, the map lit up at the end",
                        "tone": "kinetic",
                        "clip_use": "clip-first: their own reels play in the places they were shot, a generated dawn opens",
                        "idea": ctx.say("one day stretched across the year: the sun rises over the first place and sets somewhere "
                                        "near the last, the sky turning a little at every cut, and the night map comes up with every "
                                        "place lit."),
                        "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"},
                        "beats": beats, "clips": clips})


def shot_cuts(bt, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a beat with weights, snapped to the music's beats when given."""
    w = (bt.get("data") or {}).get("weights") or []
    if len(w) < 2:
        return None
    tot = sum(w)
    cuts, acc = [], 0
    for x in w[:-1]:
        acc += x
        ideal = bt["frames"] * acc / tot
        if grid_s:
            ideal = snap_to((start + ideal) / FPS, grid_s, tol) * FPS - start
        cuts.append(int(round(ideal)))
    lo = sec(0.25)
    out = []
    for c in cuts:
        c = max(lo + (out[-1] if out else 0), min(bt["frames"] - lo, c))
        out.append(c)
    return out if len(set(out)) == len(out) else None


def finish(ctx, board):
    """Fills the system and the map, drops empty beats, scales durations to the target, adds the poster."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "year": ctx.year, "format": {"width": REEL[0], "height": REEL[1], "fps": FPS},
                  "system": ctx.system(d), "map": ctx.map_data(), "count": ctx.n, "total_km": ctx.km})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        empty = bt["kind"] in ("Opener", "ClipShot", "DayNight") and not bt["photos"] and not bt.get("clip")
        if not empty:
            beats.append(bt)
    if beats:
        beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (target_seconds(ctx) * FPS + overlap) / whole if whole else 1
    for bt in beats:
        bt["frames"] = max(sec(1.2), int(round(bt["frames"] * k)))
        cuts = shot_cuts(bt)
        if cuts:
            bt["data"]["cuts"] = cuts
    board["beats"] = beats
    by = {b["id"]: b for b in beats}
    keep = [c for c in board["clips"] if c["beat"] in by]
    for c in keep:
        secs = max(1, round(by[c["beat"]]["frames"] / FPS))
        if c.get("prompt"):
            c["prompt"] = c["prompt"].replace(f"{c['seconds']} seconds", f"{secs} seconds")
        c["seconds"] = secs
    board["clips"] = keep
    board["poster"] = dict(poster_beat(ctx, "poster", sec(3), None, d, night=d == "kinetic"), settle=0)
    return board


def film_seconds(beats):
    frames = sum(b["frames"] for b in beats) - sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    return frames / FPS


def timeline(beats):
    out, start = [], 0
    for i, b in enumerate(beats):
        t = (b.get("transition") or {}).get("frames", 0) if i else 0
        start = start - t if i else 0
        out.append({"id": b["id"], "kind": b["kind"], "start": start, "frames": b["frames"], "transition": t,
                    "shots": [0] + list((b.get("data") or {}).get("cuts") or []) + [b["frames"]],
                    "focus": list((b.get("data") or {}).get("focus") or [])})
        start += b["frames"]
    return out


def write_md(board, path):
    s = board["system"]
    lines = [f"# storyboard {board['id']}: {board['name']}", "", board["idea"], "",
             f"- structure: {board['structure']}", f"- tone: {board['tone']}", f"- generated clips: {board['clip_use']}",
             f"- length: {film_seconds(board['beats']):.1f} s at {FPS} fps, 1080x1920",
             f"- places: {board['count']}, {board['total_km']:,} km along the route",
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines and numbers, {s['text']['family']} for labels and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, accent2 {s['colors']['accent2']}; "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])}",
             f"- map: sea {s['map']['sea']}, land {s['map']['land']}, route {s['map']['route']}, labels {s['map']['label']} "
             f"(land shapes from data/land.json, Natural Earth, public domain; no map tiles)",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             "", "## beats", "", "| # | time | beat | component | places | carried by | text | transition in |", "|---|---|---|---|---|---|---|---|"]
    names = {p["id"]: p["name"] for p in board["map"]["pins"]}
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        data = b.get("data") or {}
        if b["kind"] == "MapJourney":
            assets = f"the map ({data.get('mode')})" + (f", {Path(b['photos'][0]).name} pinned" if b.get("photos") else "")
        elif b["kind"] == "Poster":
            assets = "the whole map" + (" at night" if data.get("night") else "")
        elif b["kind"] == "Stamp" and data.get("mode") == "page":
            assets = f"the page of {len(data.get('page') or [])} stamps"
        else:
            assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:3])
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        tri = (b.get("transition") or {}).get("preset", "-")
        where = ", ".join(names.get(x, x) for x in data.get("focus") or []) or "-"
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {where} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        src = f" (their reel: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; their own footage'}")
    lines += ["", "The poster (1080x1350) is the map of the year's places, the route and the count, in this board's palette and type.", ""]
    path.write_text("\n".join(lines))


def all_photos(b):
    out = set()
    for x in b["beats"] + [b["poster"]]:
        out |= set(x.get("photos") or [])
        data = x.get("data") or {}
        card = data.get("card") or {}
        if card.get("photo"):
            out.add(card["photo"])
        out |= {x["photo"] for x in data.get("pinned") or [] if x.get("photo")}
        for st in (data.get("page") or []) + ([data["stamp"]] if data.get("stamp") else []):
            out |= set(st.get("photos") or [])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return {p for p in out if p}


def cmd_draft(a):
    ctx = Ctx()
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    boards = [make(ctx) for make in (board_route, board_passport, board_day)]
    referenced = sorted(set().union(*(all_photos(b) for b in boards)))
    grade.grade_photos([Path("build/photos") / Path(p).name for p in referenced])
    for b in boards:
        d = BOARDS / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        _env.write_json(d / "storyboard.json", b)
        write_md(b, d / "storyboard.md")
        print(f"board {b['id']} {b['name']}: {len(b['beats'])} beats, {film_seconds(b['beats']):.1f} s, {len(b['clips'])} clips -> {d}/storyboard.md")
    stage_assets()
    return 0 if cmd_check(a) == 0 else 1


def stage_assets():
    """Fonts, the grain tile and the land shapes inside build/public/, the folder the renderer serves."""
    dst = grade.PUBLIC / "fonts"
    if not dst.exists():
        shutil.copytree(_env.SKILL / "fonts", dst, ignore=shutil.ignore_patterns("*.md"))
    fx = grade.PUBLIC / "fx" / "grain.png"
    if not fx.exists():
        fx.parent.mkdir(parents=True, exist_ok=True)
        grade.grain_tile(fx)
    if not (grade.PUBLIC / "map" / "land.json").exists():
        sys.exit("build/public/map/land.json is missing: run research.py (places.py writes the land shapes)")


def load_boards():
    out = []
    for d in sorted(BOARDS.glob("*/storyboard.json")):
        out.append(_env.read_json(d))
    if not out:
        sys.exit("no storyboards: run storyboard.py draft first")
    return out


KINDS = {"Opener", "ClipShot", "MapJourney", "Stamp", "DayNight", "Poster"}
PRESETS = set(design("transitions.json")["presets"])


def board_issues(b, places=None):
    issues = []
    secs = film_seconds(b["beats"])
    if not LENGTH[0] <= secs <= LENGTH[1]:
        issues.append(f"length {secs:.1f} s is outside {LENGTH[0]}-{LENGTH[1]} s")
    clips = {c["id"] for c in b.get("clips", [])}
    ids = {p["id"] for p in (b.get("map") or {}).get("pins", [])}
    shown = set()
    for i, bt in enumerate(b["beats"]):
        if bt["kind"] not in KINDS:
            issues.append(f"{bt['id']}: unknown component {bt['kind']}")
        if bt["frames"] < sec(0.8):
            issues.append(f"{bt['id']}: {bt['frames']} frames is under 0.8 s")
        t = bt.get("transition")
        if i and not t:
            issues.append(f"{bt['id']}: no transition named (every cut is chosen)")
        if t and t["preset"] not in PRESETS:
            issues.append(f"{bt['id']}: unknown transition {t['preset']}")
        if bt.get("clip") and bt["clip"] not in clips:
            issues.append(f"{bt['id']}: clip {bt['clip']} is not in the clip list")
        f = (bt.get("data") or {}).get("focus")
        if f is None:
            issues.append(f"{bt['id']}: data.focus is missing (the places the beat shows)")
        for x in f or []:
            if x not in ids:
                issues.append(f"{bt['id']}: focus {x} is not a place on the map")
        shown |= set(f or [])
        if bt["kind"] == "MapJourney":
            for k in bt["data"].get("legs") or []:
                if not 0 <= k < len(b["map"]["legs"]):
                    issues.append(f"{bt['id']}: leg {k} is not on the route")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    want = set(places) if places is not None else ids
    missing = sorted(want - shown)
    if missing:
        issues.append(f"places with no beat of their own: {', '.join(missing)}")
    if not b.get("poster") or "poster" not in ((b["poster"].get("data") or {}).get("layout") or {}):
        issues.append("no poster (the 1080x1350 map poster comes from the board)")
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
    for c in b.get("clips", []):
        if not c.get("prompt") and not c.get("source"):
            issues.append(f"clip {c['id']}: no prompt and no source")
        if c.get("prompt") and "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text, no logos, no faces")
    faces = {b["system"]["display"]["family"], b["system"]["text"]["family"]}
    if len(faces) > 2:
        issues.append("more than two type faces")
    return issues


def cmd_check(a):
    bad = 0
    boards = load_boards()
    places = [p["id"] for p in (_env.read_json("build/places.json") or {}).get("places", [])]
    sigs = set()
    for b in boards:
        sigs.add((b["structure"], b["tone"], b["clip_use"]))
        iss = board_issues(b, places)
        bad += len(iss)
        print(f"board {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'} , {film_seconds(b['beats']):.1f} s")
        for i in iss:
            print("  -", i)
    if len(boards) != 3 or len(sigs) != 3:
        print("  - the three boards must differ on structure, tone and clip use")
        bad += 1
    return 1 if bad else 0


def sheet_frames(b):
    """Six frames that show the direction: settled moments spread across the film, the first and the last included."""
    cands = []
    for t in timeline(b["beats"]):
        sh = t["shots"]
        spans = list(zip(sh, sh[1:]))
        for lo, hi in spans:
            lo = max(lo, t["transition"])
            cands.append((t["id"], t["start"] + lo + int((hi - lo) * 0.7)))
    if len(cands) <= 6:
        return cands
    pick = sorted({round(i * (len(cands) - 1) / 5) for i in range(6)})
    return [cands[i] for i in pick]


def cmd_sheets(a):
    import film
    stage_assets()
    boards = load_boards()
    jobs = []
    for b in boards:
        props = film.props_for(b)
        fr = BOARDS / b["id"] / "frames"
        fr.mkdir(parents=True, exist_ok=True)
        for f in fr.glob("*.png"):
            f.unlink()
        for n, (bid, frame) in enumerate(sheet_frames(b), 1):
            out = (fr / f"{n:02d}.png").resolve()
            jobs.append({"type": "still", "composition": "Film", "props": props, "frame": frame, "scale": 0.5, "out": str(out)})
    rep = film.render_jobs(jobs, "build/sheets-report.json")
    _env.need("PIL")
    from PIL import Image
    for b in boards:
        frames = sorted((BOARDS / b["id"] / "frames").glob("*.png"))
        if not frames:
            continue
        ims = [Image.open(f).convert("RGB") for f in frames]
        w, h = ims[0].size
        sheet = Image.new("RGB", (w * 3 + 40, h * 2 + 30), "#111111")
        for i, im in enumerate(ims[:6]):
            sheet.paste(im, (10 + (i % 3) * (w + 10), 10 + (i // 3) * (h + 10)))
        sheet.save(BOARDS / b["id"] / "sheet.png")
        print(f"board {b['id']}: {len(frames)} frames -> {BOARDS / b['id'] / 'frames'}/, sheet {BOARDS / b['id'] / 'sheet.png'}")
    for f in rep.get("findings", []):
        print("finding:", f["text"][:300])
    return 0 if not rep.get("failed") else 1


def snap_to(t, grid, tol):
    best = min(grid, key=lambda g: abs(g - t)) if grid else t
    return best if abs(best - t) <= tol else t


def cmd_snap(a):
    win = _env.read_json("build/winner.json")
    bid = a.board or (win or {}).get("board")
    if not bid:
        sys.exit("no winner: run vote.py tally first (or pass --board N)")
    b = _env.read_json(BOARDS / str(bid) / "storyboard.json")
    music = _env.read_json("build/music.json") or {}
    grid_s = music.get("beats") or []
    down = music.get("downbeats") or grid_s
    beats = b["beats"]
    snapped = 0
    start = 0
    for i, bt in enumerate(beats):
        if i == 0:
            continue
        prev = beats[i - 1]
        t = (bt.get("transition") or {}).get("frames", 0)
        prev_start = start
        cut = (prev_start + prev["frames"] - t / 2) / FPS
        new_cut = snap_to(cut, down, 0.45)
        if new_cut == cut:
            new_cut = snap_to(cut, grid_s, 0.3)
        if new_cut != cut:
            snapped += 1
        prev["frames"] = max(sec(0.8), int(round(new_cut * FPS + t / 2 - prev_start)))
        start = prev_start + prev["frames"] - t
    last = beats[-1]
    end = (start + last["frames"]) / FPS
    if down:
        later = [g for g in down if g >= end - 0.4]
        if later and (later[0] * FPS - start) + sec(0.5) <= LENGTH[1] * FPS - start:
            last["frames"] = max(sec(2.5), int(round(later[0] * FPS - start)) + sec(0.5))
    for bt, t in zip(beats, timeline(beats)):
        cuts = shot_cuts(bt, grid_s, 0.25, t["start"])
        if cuts:
            bt["data"]["cuts"] = cuts
    b["beats"] = beats
    b["timeline"] = timeline(beats)
    b["seconds"] = film_seconds(beats)
    b["music"] = {**b.get("music", {}), **{k: music.get(k) for k in ("file", "bpm", "origin") if music.get(k)}}
    _env.write_json("build/film.json", b)
    print(f"board {bid}: {len(beats)} beats, {snapped} cuts moved onto the music, {b['seconds']:.1f} s -> build/film.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    ap.add_argument("--board")
    a = ap.parse_args()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
