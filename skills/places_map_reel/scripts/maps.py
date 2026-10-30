"""Map geometry for the board builder, in the same projections the studio's Atlas draws (d3-geo): where a place
lands on the frame, the camera that frames a set of places in a box, the lit land around the places reached, and
the sea and country names that fit the frame as texture.

  px(proj, lat, lon)            frame px of a point; proj {type mercator|ortho|home, center [lon, lat], scale, at, turn, c0, cmax}
  fit(points, box, pad)         the mercator camera that holds every (lat, lon) inside box [x, y, w, h], pad px inside it
  fit_region(points, box, margin, least)
                                the mercator crop of the region the points span, framed to their bounds with `margin` of
                                the span (and never under `least` km across) on every side, centered in box
  fit_home(points, center, box, pad)
                                the home camera (an azimuthal map about `center`, distance drawn on a log scale so the near
                                places keep their room and the far ones stand nearer the edge) that holds every point in box
  region(proj, box)             the (south, west, north, east) degrees a mercator box [x0, y0, x1, y1] px shows
  km(a, b)                      the great-circle distance between two (lat, lon) points
  lonlat(proj, x, y)            the inverse, mercator only
  lit(points, margin)           a GeoJSON polygon around the points, `margin` degrees out
  reached(points, km)           the land they reached: polygons out from each point over the land to the first sea
  is_land(lat, lon)             against the shipped land shapes
  ground(proj, panel, clear)    the names to print on a mercator panel: seas on open sea, countries at their anchor,
                                each kept only when its box sits inside the panel and clear of every rect in `clear`
"""
import functools
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
EARTH_KM = 6371.0
_LAND = None
_NAMES = None


def merc_y(lat):
    lat = max(-85.0, min(85.0, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _turn(proj, x, y):
    a = math.radians(proj.get("turn") or 0)
    if not a:
        return x, y
    cx, cy = proj["at"]
    dx, dy = x - cx, y - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


def px(proj, lat, lon):
    (l0, f0), s, (ax, ay) = proj["center"], proj["scale"], proj["at"]
    t = proj["type"]
    if t == "mercator":
        return ax + s * math.radians((lon - l0 + 180) % 360 - 180), ay - s * (merc_y(lat) - merc_y(f0))
    f0r, fr, dl = math.radians(f0), math.radians(lat), math.radians(lon - l0)
    if t == "ortho":
        x = s * math.cos(fr) * math.sin(dl)
        y = -s * (math.cos(f0r) * math.sin(fr) - math.sin(f0r) * math.cos(fr) * math.cos(dl))
        return _turn(proj, ax + x, ay + y)
    if t == "home":
        c = math.acos(max(-1.0, min(1.0, math.sin(f0r) * math.sin(fr) + math.cos(f0r) * math.cos(fr) * math.cos(dl))))
        if c < 1e-12:
            return float(ax), float(ay)
        th = math.atan2(math.sin(dl) * math.cos(fr), math.cos(f0r) * math.sin(fr) - math.sin(f0r) * math.cos(fr) * math.cos(dl))
        c0, cmax = proj.get("c0", 60) / EARTH_KM, proj.get("cmax", 12000) / EARTH_KM
        r = s * math.log(1 + c / c0) / math.log(1 + cmax / c0)
        return ax + r * math.sin(th), ay - r * math.cos(th)
    raise ValueError(f"unknown projection {t}")


def home_radius(proj, km):
    c0, cmax = proj.get("c0", 60) / EARTH_KM, proj.get("cmax", 12000) / EARTH_KM
    return proj["scale"] * math.log(1 + km / EARTH_KM / c0) / math.log(1 + cmax / c0)


def lonlat(proj, x, y):
    (l0, f0), s, (ax, ay) = proj["center"], proj["scale"], proj["at"]
    lon = l0 + math.degrees((x - ax) / s)
    m = merc_y(f0) - (y - ay) / s
    return math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2), lon


def fit(points, box, pad=0, most=None):
    """The mercator camera centered on the points' extent that holds them all inside box, `pad` px in from its
    edges; `most` caps the scale (a single place, or places a few km apart, would otherwise fill the frame)."""
    x, y, w, h = box
    lons = [p[1] for p in points]
    ys = [merc_y(p[0]) for p in points]
    dl = math.radians(max(lons) - min(lons)) or 1e-6
    dy = (max(ys) - min(ys)) or 1e-6
    s = min((w - 2 * pad) / dl, (h - 2 * pad) / dy)
    if most:
        s = min(s, most)
    mid = (max(ys) + min(ys)) / 2
    lat = math.degrees(2 * math.atan(math.exp(mid)) - math.pi / 2)
    return {"type": "mercator", "center": [round((max(lons) + min(lons)) / 2, 4), round(lat, 4)], "scale": round(s, 1),
            "at": [round(x + w / 2, 1), round(y + h / 2, 1)]}


def fit_region(points, box, margin=0.18, least=400):
    """The mercator crop of the region the points (lat, lon) span, the way a person reads a map of a country or a coast:
    north up, framed to the points' bounds with `margin` of their span on every side, the span never taken under `least`
    km across (so places a few km apart show their region, not a street), the whole of it fitted inside box [x, y, w, h]
    and centered there. Longitudes are read about the first point, so a route across the date line stays whole."""
    x, y, w, h = box
    l0 = points[0][1]
    lons = [l0 + (p[1] - l0 + 180) % 360 - 180 for p in points]
    ys = [merc_y(p[0]) for p in points]
    mid_y = (max(ys) + min(ys)) / 2
    lat = math.degrees(2 * math.atan(math.exp(mid_y)) - math.pi / 2)
    # the least span in radians of longitude at the middle latitude, and in mercator y
    floor = least / EARTH_KM / max(0.2, math.cos(math.radians(lat)))
    dl = max(math.radians(max(lons) - min(lons)), floor) * (1 + 2 * margin)
    dy = max(max(ys) - min(ys), floor) * (1 + 2 * margin)
    s = min(w / dl, h / dy)
    return {"type": "mercator", "center": [round((max(lons) + min(lons)) / 2, 4), round(lat, 4)], "scale": round(s, 2),
            "at": [round(x + w / 2, 1), round(y + h / 2, 1)]}


def region(proj, box):
    """The (south, west, north, east) degrees the mercator box [x0, y0, x1, y1] px of `proj` shows."""
    n, w = lonlat(proj, box[0], box[1])
    s_, e = lonlat(proj, box[2], box[3])
    return s_, w, n, e


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(h)))


def fit_home(points, center, box, pad=0, c0=60, least=100):
    """The home camera about `center` (lat, lon) that holds every point inside box [x, y, w, h], `pad` px in from its
    edges: the farthest point sets the log scale's end, and the points' extent is never taken under `least` km across, so
    places a few km apart do not fill the frame."""
    x, y, w, h = box
    cmax = max([km(center, p) for p in points] + [least])
    unit = {"type": "home", "center": [center[1], center[0]], "scale": 1.0, "at": [0.0, 0.0], "c0": c0, "cmax": cmax}
    xy = [px(unit, *p) for p in points]
    xs, ys = [a for a, _ in xy], [b for _, b in xy]
    floor = home_radius(unit, least)
    dx, dy = max(max(xs) - min(xs), floor), max(max(ys) - min(ys), floor)
    s = min((w - 2 * pad) / dx, (h - 2 * pad) / dy)
    return {"type": "home", "center": [round(center[1], 4), round(center[0], 4)], "scale": round(s, 2), "c0": c0, "cmax": round(cmax, 1),
            "at": [round(x + w / 2 - s * (max(xs) + min(xs)) / 2, 2), round(y + h / 2 - s * (max(ys) + min(ys)) / 2, 2)]}


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def lit(points, margin=2.5, n=16):
    """The land they reached: the convex hull of a disc `margin` degrees round each point, as a GeoJSON polygon
    (counter-clockwise in lon/lat, the winding the studio's other lit shapes use)."""
    ring = []
    for lat, lon in points:
        k = 1 / max(0.2, math.cos(math.radians(lat)))
        for j in range(n):
            a = 2 * math.pi * j / n
            ring.append((round(lon + margin * k * math.cos(a), 3), round(lat + margin * math.sin(a), 3)))
    h = _hull(ring)
    return {"type": "Polygon", "coordinates": [[list(p) for p in h + h[:1]]]}


def reached(points, km=420, n=72, step=6, res=0.02):
    """The land they reached: from each point, rays out over the land to the first sea and no farther than `km`, one
    GeoJSON polygon per point (counter-clockwise in lon/lat, like `lit`). A country across a strait stays dark, and so
    does the land past the reach. The rays read a mask of the land painted once at the shapes' own resolution."""
    if not points:
        return []
    from PIL import Image, ImageChops, ImageDraw
    k0 = 111 * max(0.2, min(math.cos(math.radians(lat)) for lat, _ in points))
    w, e = min(p[1] for p in points) - km / k0, max(p[1] for p in points) + km / k0
    s, nn = min(p[0] for p in points) - km / 111, max(p[0] for p in points) + km / 111
    size = (int((e - w) / res) + 1, int((nn - s) / res) + 1)
    mask = Image.new("1", size, 0)
    for (bw, bs, be, bn), ring in _land():
        if be < w or bw > e or bn < s or bs > nn:
            continue
        one = Image.new("1", size, 0)
        ImageDraw.Draw(one).polygon([((x - w) / res, (nn - y) / res) for x, y in ring], fill=1)
        mask = ImageChops.logical_xor(mask, one)
    px = mask.load()

    def land(lat, lon):
        i, j = int((lon - w) / res), int((nn - lat) / res)
        return 0 <= i < size[0] and 0 <= j < size[1] and px[i, j]

    out = []
    for lat, lon in points:
        k = 111 * max(0.2, math.cos(math.radians(lat)))
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            d = 0
            while d + step <= km and land(lat + (d + step) / 111 * math.sin(a), lon + (d + step) / k * math.cos(a)):
                d += step
            ring.append((round(lon + d / k * math.cos(a), 3), round(lat + d / 111 * math.sin(a), 3)))
        if len(set(ring)) >= 3:
            out.append({"type": "Polygon", "coordinates": [[list(p) for p in ring + ring[:1]]]})
    return out


def _land():
    global _LAND
    if _LAND is None:
        _LAND = []
        for r in json.loads((DATA / "land.json").read_text())["rings"]:
            f = r["ring"]
            _LAND.append((r["bbox"], [(f[i], f[i + 1]) for i in range(0, len(f), 2)]))
    return _LAND


def is_land(lat, lon):
    return _is_land(round(lat, 2), round(lon, 2))


@functools.lru_cache(maxsize=None)
def _is_land(lat, lon):
    inside = False
    for (w, s, e, n), ring in _land():
        if not (w <= lon <= e and s <= lat <= n):
            continue
        c = False
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi:
                c = not c
            j = i
        inside ^= c
    return inside


def _names():
    global _NAMES
    if _NAMES is None:
        _NAMES = json.loads((DATA / "names.json").read_text())
    return _NAMES


def overlaps(a, b, gap=0):
    return a[0] < b[0] + b[2] + gap and b[0] < a[0] + a[2] + gap and a[1] < b[1] + b[3] + gap and b[1] < a[1] + a[3] + gap


def _name_box(x, y, text, size, tracking, rotate):
    w = len(text) * size * (0.62 + tracking)
    h = size * 0.8
    return (x - h / 2, y - w / 2, h, w) if rotate else (x - w / 2, y - h, w, h)


def _nearest_sea(lat, lon):
    """The sea a water point belongs to: of the seas whose box holds it, the one whose anchor is nearest."""
    near = [(math.hypot(lon - c["at"][0], lat - c["at"][1]), i) for i, c in enumerate(_names()["seas"])
            if c["bbox"][0] <= lon <= c["bbox"][2] and c["bbox"][1] <= lat <= c["bbox"][3]]
    return _names()["seas"][min(near)[1]] if near else None


def ground(proj, panel, clear=(), size=22, tracking=0.42, most=3):
    """Sea names on open water (horizontal, or turned up a narrow strip of sea) at the sea point nearest each sea's
    anchor, on water that belongs to that sea (no other sea's anchor is nearer), and country names at their anchors, kept when inside the panel with a 24 px margin and clear of `clear`."""
    px0, py0, pw, ph = panel
    inner = (px0 + 24, py0 + 24, pw - 48, ph - 48)
    out, taken = [], list(clear)

    def inside(b):
        return b[0] >= inner[0] and b[1] >= inner[1] and b[0] + b[2] <= inner[0] + inner[2] and b[1] + b[3] <= inner[1] + inner[3]

    def sea_box(b, rotate):
        xs = [b[0] + b[2] * t for t in (0, 0.25, 0.5, 0.75, 1)]
        ys = [b[1] + b[3] * t for t in (0, 0.5, 1)]
        return all(not is_land(*lonlat(proj, x, y)) for x in xs for y in ys)

    lat0, lon0 = lonlat(proj, px0 + pw / 2, py0 + ph / 2)
    for sea in _names()["seas"]:
        w, s, e, n = sea["bbox"]
        best = None
        for gy in range(int(inner[1]), int(inner[1] + inner[3]), 40):
            for gx in range(int(inner[0]), int(inner[0] + inner[2]), 40):
                lat, lon = lonlat(proj, gx, gy)
                if not (w <= lon <= e and s <= lat <= n):
                    continue
                if is_land(lat, lon) or _nearest_sea(lat, lon) is not sea:
                    continue
                for rot in (0, -90):
                    b = _name_box(gx, gy, sea["name"], size, tracking, rot)
                    if not inside(b) or any(overlaps(b, c, 12) for c in taken) or not sea_box(b, rot):
                        continue
                    d = math.hypot(lon - sea["at"][0], lat - sea["at"][1]) + (4 if rot else 0)
                    if best is None or d < best[0]:
                        best = (d, gx, gy, rot, b)
        if best:
            _, gx, gy, rot, b = best
            taken.append(b)
            lat, lon = lonlat(proj, gx, gy)
            g = {"text": sea["name"], "at": [round(lon, 3), round(lat, 3)], "size": size}
            if rot:
                g["rotate"] = rot
            out.append(g)
    for c in _names()["countries"]:
        x, y = px(proj, c["at"][1], c["at"][0])
        b = _name_box(x, y, c["name"], size, tracking, 0)
        if inside(b) and not any(overlaps(b, t, 12) for t in taken):
            taken.append(b)
            out.append({"text": c["name"], "at": list(c["at"]), "size": size})
    return out[: most + 2]


def world(out):
    """The shipped land rings as one GeoJSON MultiPolygon for the studio's spherical projections (public/map/world.json),
    every ring wound so d3-geo takes its inside as land (counter-clockwise in lon/lat with north up). Rings wholly south
    of 60 degrees S are left out: no route reaches them and they would wrap the rim of an azimuthal map."""
    polys = []
    for r in json.loads((DATA / "land.json").read_text())["rings"]:
        flat = r["ring"]
        pts = [[flat[i], flat[i + 1]] for i in range(0, len(flat), 2)]
        if len(pts) < 4 or max(p[1] for p in pts) < -60:
            continue
        if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) < 0:
            pts.reverse()
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        polys.append([pts])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps({"type": "MultiPolygon", "coordinates": polys}, separators=(",", ":")))
    return len(polys)
