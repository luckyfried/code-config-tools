"""film: tied to the day. The nine arrive in the order they were posted; baker's twine runs from each day on the
year's rule to the post's square on the ranked wall, one drop to its own lane, one run along it, one drop to the
tag."""
import math

from compose import fit_size, photo, shift, system, text_width, wrap_measured

BPM = 96
TILE_REEL, GAP = 276, 30
LANE, HOLE_DY = 25, 24
OFF = {0: 9, 1: 0, 2: -9}
ROT = [-2, 1.5, -1, 2, -1.5, 1, -2, 1.5, -1]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MSTART = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
FACE = {"opsz": 144, "SOFT": 50, "WONK": 1}
TAGFACE = {"opsz": 72, "SOFT": 50, "WONK": 1}
# every shot eases back this much over its length: the wall fills the safe area, so it settles inward, never out
DRIFT = -0.02
# the rule's height in each format, and the hook's own layout: the first post's square, the headline above it and
# the caption under the headline, the tag's size
RULE_Y = {"reel": 330, "square": 100, "wide": 120}
HOOK = {
    "reel": {"tile": [72, 664, 936, 936], "x": 140, "y": [432, 502, 572], "size": 68, "cap": 630, "capsize": 30, "big": 1.9},
    "square": {"tile": [205, 370, 670, 670], "x": 273, "y": [186, 242, 298], "size": 54, "cap": 340, "capsize": 26, "big": 1.4},
    "wide": {"tile": [966, 182, 858, 858], "x": 140, "y": [430, 530, 630], "size": 92, "cap": 712, "capsize": 36, "big": 1.8},
}


def sys_():
    return system("editorial", {"bg": "#efe7da", "ink": "#2a211b", "accent": "#b3302a", "accent2": "#d8c7ab", "muted": "#a89a86", "paper": "#fbf7ef"},
                  display={"axes": {"opsz": 144, "SOFT": 50, "WONK": 0}}, texture={"grain": 0.05})


class Wall:
    """The rule, the lanes and the ranked wall in one format. The rule runs from `X0` to `X1` at `rule_y`, the lanes
    under it, one per post in the order they were posted, and the wall's squares under the lanes, three across in rank
    order."""

    def __init__(self, posts, frame):
        self.posts, self.frame = posts, frame
        n = len(posts)
        self.n, self.rows = n, math.ceil(n / 3)
        self.rule_y = RULE_Y[frame.name]
        self.LANE0 = self.rule_y + 22
        # the lanes need one row each; under few lanes the wall still leaves room for the ask's tag under the rule
        self.WY = max(self.LANE0 + (n - 1) * LANE + 32, self.rule_y + 160)
        if frame.name == "reel":
            self.tile = TILE_REEL
        else:
            self.tile = math.floor((frame.H - frame.bottom - self.WY - (self.rows - 1) * GAP) / max(3, self.rows))
        self.wall_w = 3 * self.tile + 2 * GAP
        if frame.name == "reel":
            self.WX = 96
        elif frame.name == "wide":
            self.WX = frame.W - frame.right - 40 - self.wall_w
        else:
            self.WX = round((frame.W - self.wall_w) / 2)
        self.X0 = 140 if frame.name == "wide" else self.WX - 24
        self.X1 = self.WX + self.wall_w - 144
        self.XN = self.X1 + 90
        self.tagk = 1.0 if frame.name == "reel" else max(0.9, round(self.tile / TILE_REEL, 2))
        self.by_rank = {p["rank"]: p for p in posts}
        self.by_date = sorted(posts, key=lambda p: (p["doy"], p["rank"]))
        self.order = {p["rank"]: k for k, p in enumerate(self.by_date)}

    def dx(self, doy):
        return round(self.X0 + (doy - 0.5) / 365 * (self.X1 - self.X0), 1)

    def slot(self, rank):
        c, r = (rank - 1) % 3, (rank - 1) // 3
        return c, r, [self.WX + c * (self.tile + GAP), self.WY + r * (self.tile + GAP), self.tile, self.tile]

    def route(self, p):
        """Down from the post's day to its lane, along it to the gutter left of the post's column, down the gutter to
        the tag's hole on the square's top-left corner. The strands sharing a gutter stand 9 px apart."""
        c, r, box = self.slot(p["rank"])
        d = self.dx(p["doy"])
        lane = self.LANE0 + self.order[p["rank"]] * LANE
        hole = [self.WX + c * (self.tile + GAP) - GAP / 2 + OFF[r], box[1] + HOLE_DY]
        return [[d, self.rule_y], [d, lane], [hole[0], lane], hole], hole


def tag(p, at, hole, k=1.0):
    return {"kind": "Tag", "at": at, "pos": hole, "w": round(160 * k), "h": round(60 * k), "rotate": ROT[(p["rank"] - 1) % 9], "owner": p["rank"],
            "lines": [
                {"text": str(p["rank"]), "x": round(40 * k), "y": round(46 * k), "size": round(44 * k), "face": "display", "anchor": "middle", "weight": 500, "axes": TAGFACE},
                {"text": f"{p['likes']} likes", "x": round(68 * k), "y": round(26 * k), "size": round(18 * k), "face": "text", "weight": 700, "tracking": 0, "name": f"count-{p['rank']}"},
                {"text": p["date"], "x": round(68 * k), "y": round(48 * k), "size": round(17 * k), "face": "text", "weight": 500, "tracking": 0, "color": "accent"},
            ]}


def screen(v, pt):
    if not v:
        return pt
    return [v["to"][0] + (pt[0] - v["at"][0]) * v["scale"], v["to"][1] + (pt[1] - v["at"][1]) * v["scale"]]


def label_ok(Wl, x, views, size=20):
    """A month label is set in a framing when it sits inside the safe area in every view the shot holds; a label the
    frame would cut is left out of that shot."""
    l, t, r, b = Wl.frame.safe
    for v in views:
        (a, bb), (c, d) = screen(v, [x + 5, Wl.rule_y - 14 - size]), screen(v, [x + 5 + size * 1.9, Wl.rule_y - 10])
        if a < l or bb < t or c > r or d > b:
            return False
    return True


def rule(Wl, knots, views=(None,), nxt_at=None):
    months = [{"x": round(Wl.X0 + (m - 1) / 365 * (Wl.X1 - Wl.X0), 1), "label": n} for m, n in zip(MSTART, MONTHS)]
    L = {"kind": "YearRule", "at": 0, "x0": Wl.X0, "x1": Wl.X1, "y": Wl.rule_y, "beats": 0.8, "labelSize": 20, "color": "ink", "twine": "accent",
         "months": [m for m in months if label_ok(Wl, m["x"], views)], "knots": knots}
    if nxt_at is not None:
        L.update({"next": {"x": Wl.XN, "label": str(Wl.year + 1)}, "nextAt": nxt_at, "nextBeats": 0.5})
    return L


def wall(Wl, ties, full):
    """Every post's square, twine and tag on the film's clock: knotted on its day at its beat, the twine paid out over
    0.9 beats, the square dropping in as it arrives and the tag swinging on; each strand goes light when the next is
    tied and all of them come up to full red together."""
    tiles = {p["rank"]: {"kind": "Tile", "at": 99, "box": Wl.slot(p["rank"])[2], "photo": photo(p, wall=True), "empty": True, "emptyColor": "muted",
                         "beats": 0.4, "owner": p["rank"]} for p in Wl.posts}
    knots, tw, tags = [], [], []
    for k, p in enumerate(Wl.by_date):
        t = ties[p["rank"]]
        pts, hole = Wl.route(p)
        knots.append({"x": Wl.dx(p["doy"]), "at": t})
        s = {"kind": "Twine", "at": round(t + 0.15, 4), "points": pts, "beats": 0.9, "width": 5, "radius": 8, "color": "accent", "fullAt": full,
             "dest": p["rank"]}
        if k + 1 < len(Wl.by_date):
            s["lightAt"] = ties[Wl.by_date[k + 1]["rank"]]
        tw.append(s)
        tiles[p["rank"]]["at"] = round(t + 0.9, 4)
        tags.append(tag(p, round(t + 1.05, 4), hole, Wl.tagk))
    return [tiles[r] for r in sorted(tiles)] + tw + tags, knots


def hook_layers(S, Wl, words):
    """Close on the first post of the year: the rule draws, its day is knotted on it and the twine drops to its square,
    large, where its tag swings on and is tied, the headline set above the photograph."""
    h = HOOK[Wl.frame.name]
    p = Wl.by_date[0]
    x = Wl.dx(p["doy"])
    tile = h["tile"]
    hole_y = tile[1] + 70
    if tile[0] + 12 <= x < tile[0] + 48:
        pts = [[x, Wl.rule_y], [x, hole_y]]
    else:
        pts = [[x, Wl.rule_y], [x, Wl.LANE0], [tile[0] + 24, Wl.LANE0], [tile[0] + 24, hole_y]]
    hole = pts[-1]
    room = Wl.frame.W - Wl.frame.right - h["x"]
    head = [{"text": t, "x": h["x"], "y": y, "size": h["size"], "face": "display", "weight": 400, "axes": FACE, **({"italic": True} if i == 1 else {})}
            for i, (t, y) in enumerate(zip(words["head"], h["y"]))]
    size = min(fit_size(S, l, room) for l in head)
    for l in head:
        l["size"] = size
    cap = {"text": p["caption"], "x": h["x"], "y": h["cap"], "size": h["capsize"], "face": "text", "weight": 500, "tracking": 0}
    cap["size"] = fit_size(S, cap, room, lo=18)
    L = [rule(Wl, [{"x": x, "at": 0.25}]),
         {"kind": "Tile", "at": 0.05, "box": list(tile), "photo": photo(p, wall=True), "beats": 0.5, "owner": p["rank"]},
         {"kind": "Twine", "at": 0.3, "points": pts, "beats": 0.7, "width": 7, "color": "accent", "dest": p["rank"], "destBox": list(tile)},
         tag(p, 1.0, hole, h["big"]),
         {"kind": "Words", "at": 0.45, "lines": head, "beats": 0.6, "step": 0.18}]
    if p.get("caption"):
        L.append({"kind": "Words", "at": 1.3, "lines": [cap], "beats": 0.4})
    return L


def close_view(Wl, rank):
    """A top-row square whole, from just left of its tag to its right edge, the lanes above it and the gutter below,
    centred across a frame wider than it."""
    box = Wl.slot(rank)[2]
    f = Wl.frame
    s = round(min(f.W / (Wl.tile + 25), f.H / (box[1] + Wl.tile + 15 - (Wl.LANE0 - 12))), 2)
    # the caption sits over the square inside the safe area, so a square close under the rule is framed lower
    down = max(0, f.top + 96 - (box[1] - (Wl.LANE0 - 12)) * s)
    down = min(down, max(0, f.H - 14 - (box[1] + Wl.tile - (Wl.LANE0 - 12)) * s))
    return {"scale": s, "at": [box[0] - 23, Wl.LANE0 - 12], "to": [round(max(0, (f.W - (Wl.tile + 25) * s) / 2)), round(down)]}


def visible(v, f):
    """The scene's px box a view shows."""
    return (v["at"][0] - v["to"][0] / v["scale"], v["at"][1] - v["to"][1] / v["scale"],
            v["at"][0] + (f.W - v["to"][0]) / v["scale"], v["at"][1] + (f.H - v["to"][1]) / v["scale"])


def caption_words(S, Wl, p, v):
    """The close-up's caption, set on the frame just above the square as the view shows it."""
    f = Wl.frame
    box = Wl.slot(p["rank"])[2]
    x0, y0 = screen(v, box[:2])
    x = max(f.left + 24, round(x0))
    line = {"text": p["caption"], "x": x, "y": round(y0 - 56), "size": 38, "face": "text", "weight": 500, "tracking": 0}
    room = f.W - f.right - x
    line["size"] = fit_size(S, line, room, lo=28)
    if text_width(S, line) <= room:
        return {"kind": "Words", "at": -4, "lines": [line]}
    two = wrap_measured(S, line, room, 2) or [p["caption"]]
    return {"kind": "Words", "at": -4, "lines": [dict(line, text=t, y=round(line["y"] - (len(two) - 1 - i) * line["size"] * 1.2)) for i, t in enumerate(two)]}


def insert(layers, v, f, keep):
    """A close-up shows only what it holds whole: the rule, and the squares, strands and tags of the posts `keep`."""
    return [l for l in layers if l["kind"] == "YearRule" or l.get("owner", l.get("dest")) in keep]


def tag_box(l):
    px, py = l["pos"]
    w, h = l["w"], l["h"]
    ch = min(16, h * 0.25, w * 0.12)
    hx, hy = (w / 2, ch * 0.95) if l.get("hole") == "top" else (ch * 0.95, h / 2)
    return (px - hx - 4, py - hy - 4, px - hx + w + 4, py - hy + h + 4)


def whole(layers, v, f, margin=4):
    """The layers a view holds: every square and tag it shows whole, `margin` px inside the frame as the shot opens (the
    drift then eases it further in); a square or tag the frame would cut is left out of the shot, and so is a square's
    strand when its square is."""
    x0, y0, x1, y1 = visible(v, f)
    m = margin / v["scale"]
    room = (x0 + m, y0 + m, x1 - m, y1 - m)

    def box(l):
        if l["kind"] == "Tile":
            b = l["box"]
            return (b[0], b[1], b[0] + b[2], b[1] + b[3])
        return tag_box(l)

    def held(b):
        return b[0] >= room[0] and b[1] >= room[1] and b[2] <= room[2] and b[3] <= room[3]

    def apart(b):
        return b[2] <= x0 or b[0] >= x1 or b[3] <= y0 or b[1] >= y1
    gone = {l.get("owner") for l in layers if l["kind"] == "Tile" and not held(box(l))}
    out = []
    for l in layers:
        if l["kind"] in ("Tile", "Tag") and not held(box(l)):
            if l["kind"] == "Tag" or not apart(box(l)):
                continue
        if l["kind"] == "Twine" and l.get("dest") in gone and not held(box(next(t for t in layers if t["kind"] == "Tile" and t.get("owner") == l["dest"]))):
            if not apart(box(next(t for t in layers if t["kind"] == "Tile" and t.get("owner") == l["dest"]))):
                continue
        out.append(l)
    return out


def build(posts, frame, words, handle, year, bpm=BPM):
    """The film storyboard for `posts` (rank order) in `frame`: (system, scenes, end, hook beat, rests). Hook, then
    wide, rule and knot shots that follow the ties, each top-row post's close-up straight after it is tied; a knot
    tied close pulls back to the whole wall as its strand runs down, so a strand always runs toward a square in frame;
    the closing wide holds the whole wall, brings the strands up to full red and makes room for the promise and the
    ask."""
    S = sys_()
    Wl = Wall(posts, frame)
    Wl.year = year
    f = frame
    WIDE = {"scale": 1, "at": [f.W / 2, f.H / 2], "to": [f.W / 2, f.H / 2]}
    first = Wl.by_date[0]
    top = [p for p in Wl.by_date if p["rank"] <= 3 and p is not first]
    ties = {first["rank"]: 0.25}
    plan = []
    t = 4.0
    queue = [p for p in Wl.by_date[1:]]
    after_rule = False
    for T in top:
        chunk = queue[:queue.index(T) + 1]
        queue = queue[queue.index(T) + 1:]
        while chunk:
            if len(chunk) >= 3:
                a, b = chunk[0], chunk[1]
                v = rule_view(Wl, a, b)
                if v:
                    ties[a["rank"]], ties[b["rank"]] = t + 0.25, t + 1.0
                    plan.append({"id": f"rule-{a['date'].split()[-1]}-{b['date'].split()[-1]}", "t": t, "view": v})
                    after_rule = True
                else:
                    ties[a["rank"]], ties[b["rank"]] = t + 0.3, t + 1.0
                    plan.append({"id": f"wide-{a['date'].split()[-1]}-{b['date'].split()[-1]}", "t": t})
                    after_rule = False
                chunk = chunk[2:]
                t += 2
            elif len(chunk) == 2:
                a, b = chunk
                kv = {"scale": 6, "at": [round(Wl.dx(a["doy"]) - 62, 1), Wl.rule_y - 82], "to": [0, 0]}
                ties[a["rank"]], ties[b["rank"]] = t + 0.25, t + 2.6
                plan.append({"id": f"knots-{a['date'].split()[-1]}", "t": t, "view": kv, "viewTo": WIDE, "viewMove": [t + 0.3, 1.3]})
                chunk, after_rule = [], False
                t += 4
            else:
                a = chunk[0]
                ties[a["rank"]] = t + (0.6 if after_rule else 0.3)
                plan.append({"id": f"wide-{a['date'].split()[-1]}", "t": t})
                chunk, after_rule = [], False
                t += 2
        plan.append({"id": f"close-{T['rank']}", "t": t, "view": close_view(Wl, T["rank"]), "close": T})
        t += 2
    cx0 = t
    for i, p in enumerate(queue):
        ties[p["rank"]] = cx0 + 0.3 + i
    full = round((cx0 + 0.3 + len(queue) - 1) + 1.9 if queue else cx0 + 1.2, 4)
    extra_at = round(full + 1.8, 4)
    end = extra_at + 5
    W, knots = wall(Wl, ties, full)
    scenes = [{"id": "hook", "t": 0, "layers": hook_layers(S, Wl, words)}]
    for sc in plan:
        views = [v for v in (sc.get("view"), sc.get("viewTo")) if v] or [None]
        layers = [rule(Wl, knots, views)] + W
        T = sc.pop("close", None)
        if T:
            layers = insert(layers, sc["view"], f, {T["rank"]}) if f.name != "reel" else whole(layers, sc["view"], f)
            if T.get("caption"):
                layers.append(caption_words(S, Wl, T, sc["view"]))
        scenes.append({**sc, "layers": layers})
    closer, pull, back = closer_layers(S, Wl, words, handle, extra_at)
    views = [pull, back]
    scenes.append({"id": "wide-closer", "t": cx0, "view": pull, "viewTo": back, "viewMove": [round(extra_at - 1, 4), 1.5],
                   "layers": [rule(Wl, knots, views, round(extra_at + 0.2, 4))] + W + closer})
    wides = [s for s in scenes[:-1] if not s.get("view")] or scenes[-1:]
    dense = max(wides, key=lambda s: (sum(1 for r, at in ties.items() if at + 1.05 <= s["t"] + 2), s["t"]))
    return {"system": S, "scenes": scenes, "end": end, "hook": 1.0, "rests": {"hook": "hook", "dense": dense["id"], "closer": "wide-closer"}, "drift": DRIFT}


def rule_view(Wl, a, b):
    """A close on the rule over one column's top square, whole with its tag, holding both days: the column whose view
    holds both dates 20 px inside its edges, or none (also none when the rule's labels would sit above the safe
    area)."""
    f = Wl.frame
    s = f.W / (Wl.tile + 96)
    y_top = Wl.WY + Wl.tile + 12 - f.H / s
    if (Wl.rule_y - 30 - y_top) * s < f.top:
        return None
    for c in range(3):
        x0 = Wl.WX + c * (Wl.tile + GAP) - 76
        lo, hi = x0 + 20, x0 + f.W / s - 20
        if all(lo <= Wl.dx(p["doy"]) <= hi for p in (a, b)):
            return {"scale": round(s, 2), "at": [x0, round(y_top, 1)], "to": [0, 0]}
    return None


def closer_layers(S, Wl, words, handle, at):
    """The promise and the ask: the rule runs on into the next year, a tag on it says the ask, and the camera pulls
    back to make room above the rule for the handle and the promise (in the wide they sit in the room left of the
    wall)."""
    f = Wl.frame
    ry = Wl.rule_y
    tx = Wl.XN - 50
    pull = {"scale": 1, "at": [f.W / 2, ry], "to": [f.W / 2, ry]}
    L = [{"kind": "Twine", "at": round(at + 0.6, 4), "points": [[tx, ry], [tx, ry + 54]], "beats": 0.4, "width": 5, "color": "accent"},
         {"kind": "Tag", "at": round(at + 1.0, 4), "pos": [tx, ry + 54], "hole": "top", "w": 230, "h": 80, "rotate": -3, "lines": [
             {"text": words["ask"], "x": 115, "y": 56, "size": 32, "face": "text", "weight": 700, "anchor": "middle", "color": "accent"}]}]
    if f.name == "wide":
        back = dict(pull)
        x = f.left + 44
        room = Wl.WX - 60 - x
        promise = {"text": words["promise"], "x": x, "y": 720, "size": 96, "face": "display", "weight": 400, "italic": True, "axes": FACE}
        promise["size"] = fit_size(S, promise, room)
        lines = [{"text": handle, "x": x + 2, "y": 600, "size": 36, "face": "text", "weight": 600, "tracking": 0.01}, promise]
    else:
        band = 164 if f.name == "reel" else 150
        to_y = f.top + band + 36
        bottom = Wl.WY + Wl.rows * Wl.tile + (Wl.rows - 1) * GAP
        s = 0.84 if f.name == "reel" else round(min(0.9, (f.H - 30 - to_y) / (bottom - ry)), 2)
        back = {"scale": s, "at": [f.W / 2, ry], "to": [f.W / 2, to_y]}
        x = f.left
        promise = {"text": words["promise"], "x": x, "y": f.top + band - 32, "size": 64 if f.name == "reel" else 56, "face": "display", "weight": 400, "italic": True, "axes": FACE}
        promise["size"] = fit_size(S, promise, f.W - f.right - x)
        lines = [{"text": handle, "x": x + 2, "y": f.top + 46, "size": 30 if f.name == "reel" else 26, "face": "text", "weight": 600, "tracking": 0.01}, promise]
    L.append({"kind": "Words", "at": at, "lines": lines, "beats": 0.5, "step": 0.25})
    return L, pull, back
