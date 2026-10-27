#!/usr/bin/env python3
"""Trail Replay: turns a folder of GPX and TCX exports into a replay page.

Run from the project folder:

    python3 <agent-apps root>/trail-replay/scripts/run.py

It reads trail-replay.inputs.json from the current folder, parses every GPX and
TCX file in the activities folder with xml.etree, works out distance, climb,
pace, heart rate, and splits, and writes one compact JSON per activity under
out/trail-replay/data/, so the page parses no XML. Terrain tiles for each route
come from the app's samples or from the keyless AWS terrain tiles, kept in
trail-replay-terrain/ beside the inputs so the next run reuses them.

Standard library only. Two runs on the same inputs write the same bytes.
"""

import json
import math
import os
import re
import shutil
import struct
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

APP = "trail-replay"
HERE = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd()
INPUTS = PROJECT / f"{APP}.inputs.json"
OUT = PROJECT / "out" / APP
DIST = HERE / "dist"
THEMES = HERE / "src" / "themes"
SAMPLES = HERE / "samples"
TERRAIN_CACHE = PROJECT / f"{APP}-terrain"
TERRAIN_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
TERRAIN_MAXZOOM = 13
STRAVA_ENV = "STRAVA_ACCESS_TOKEN"
STRAVA_API = "https://www.strava.com/api/v3"

KEYS = {
    "athlete": str,
    "activities": str,
    "units": str,
    "colorBy": str,
    "theme": str,
    "labels": bool,
    "strava": bool,
}
UNITS = ("km", "mi")
COLOR_BY = ("pace", "heart", "elevation")
EARTH_M = 6371008.8
SPLIT_M = {"km": 1000.0, "mi": 1609.344}
SPORT_WORDS = {
    "run": ("run", "running", "trail_running", "trailrun", "9", "treadmill"),
    "ride": ("ride", "cycling", "biking", "bike", "road_biking", "mountain_biking", "gravel_cycling", "1", "ebikeride"),
    "hike": ("hike", "hiking", "4", "walk", "walking", "10", "mountaineering"),
}
# Moving-speed floor in m/s: slower than this between two points counts as stopped.
MOVING_FLOOR = {"run": 0.6, "hike": 0.3, "ride": 1.2}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def read_inputs():
    if not INPUTS.exists():
        fail([f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    except ValueError as error:
        fail([f"{APP}.inputs.json is not valid JSON ({error.msg}, line {error.lineno})."])
    if not isinstance(inputs, dict):
        fail([f"{APP}.inputs.json must hold one object with the keys inputs.example.json shows."])
    problems = []
    for key, kind in KEYS.items():
        if key not in inputs:
            problems.append(f'{APP}.inputs.json is missing the key "{key}".')
        elif not isinstance(inputs[key], kind):
            word = "true or false" if kind is bool else "text"
            problems.append(f'{APP}.inputs.json has "{key}" as {json.dumps(inputs[key])}; it must be {word}.')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f'{APP}.inputs.json has the key "{key}", which this app does not read.')
    if isinstance(inputs.get("units"), str) and inputs["units"] not in UNITS:
        problems.append(f'"units" is "{inputs["units"]}"; it must be "km" or "mi".')
    if isinstance(inputs.get("colorBy"), str) and inputs["colorBy"] not in COLOR_BY:
        problems.append(f'"colorBy" is "{inputs["colorBy"]}"; it must be "pace", "heart", or "elevation".')
    themes = sorted(path.stem for path in THEMES.glob("*.css"))
    if isinstance(inputs.get("theme"), str) and inputs["theme"] not in themes:
        problems.append(f'"theme" is "{inputs["theme"]}"; the themes are {", ".join(themes)}.')
    if problems:
        fail(problems)
    return inputs


# ---------- geometry ----------


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_M * math.asin(min(1.0, math.sqrt(h)))


def mercator(lat, lon):
    x = (lon + 180.0) / 360.0
    s = math.sin(math.radians(max(-85.0, min(85.0, lat))))
    y = 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)
    return x, y


def tile_of(lat, lon, z):
    x, y = mercator(lat, lon)
    n = 2**z
    return min(n - 1, max(0, int(x * n))), min(n - 1, max(0, int(y * n)))


def simplify(points, tolerance):
    """Douglas-Peucker on (x, y) pairs."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        worst, index = 0.0, -1
        for i in range(first + 1, last):
            px, py = points[i]
            if length == 0:
                d = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
                d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > worst:
                worst, index = d, i
        if index >= 0 and worst > tolerance * tolerance:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [p for p, k in zip(points, keep) if k]


# ---------- parsing ----------


def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child(node, name):
    for item in node:
        if local(item.tag) == name:
            return item
    return None


def number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_time(text):
    if not text:
        return None
    text = text.strip().replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def find_ext(node, names):
    """The first number in any descendant whose local name is one of `names` (extensions vary by device)."""
    for item in node.iter():
        if local(item.tag).lower() in names:
            value = number(item.text)
            if value is not None:
                return value
    return None


def parse_gpx(root):
    name = kind = None
    points = []
    skipped = 0
    for trk in root.iter():
        if local(trk.tag) != "trk":
            continue
        if name is None and child(trk, "name") is not None:
            name = (child(trk, "name").text or "").strip() or None
        if kind is None and child(trk, "type") is not None:
            kind = (child(trk, "type").text or "").strip() or None
        for pt in trk.iter():
            if local(pt.tag) != "trkpt":
                continue
            lat, lon = number(pt.get("lat")), number(pt.get("lon"))
            if lat is None or lon is None:
                skipped += 1
                continue
            ele_node, time_node, ext = child(pt, "ele"), child(pt, "time"), child(pt, "extensions")
            points.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "ele": number(ele_node.text) if ele_node is not None else None,
                    "time": parse_time(time_node.text) if time_node is not None else None,
                    "hr": find_ext(ext, ("hr", "heartrate", "heart_rate")) if ext is not None else None,
                    "cad": find_ext(ext, ("cad", "cadence", "runcadence")) if ext is not None else None,
                }
            )
    if not points:
        for pt in root.iter():
            if local(pt.tag) == "rtept":
                lat, lon = number(pt.get("lat")), number(pt.get("lon"))
                if lat is not None and lon is not None:
                    ele_node = child(pt, "ele")
                    points.append({"lat": lat, "lon": lon, "ele": number(ele_node.text) if ele_node is not None else None, "time": None, "hr": None, "cad": None})
    if name is None:
        meta = next((n for n in root.iter() if local(n.tag) == "metadata"), None)
        if meta is not None and child(meta, "name") is not None:
            name = (child(meta, "name").text or "").strip() or None
    return name, kind, points, skipped


def parse_tcx(root):
    name = kind = None
    points = []
    skipped = 0
    for activity in root.iter():
        if local(activity.tag) not in ("Activity", "Course"):
            continue
        kind = kind or activity.get("Sport")
        notes = child(activity, "Notes")
        if notes is None:
            notes = child(activity, "Name")
        if name is None and notes is not None and (notes.text or "").strip():
            name = notes.text.strip()
        for tp in activity.iter():
            if local(tp.tag) != "Trackpoint":
                continue
            position = child(tp, "Position")
            if position is None:
                skipped += 1
                continue
            lat = number(getattr(child(position, "LatitudeDegrees"), "text", None))
            lon = number(getattr(child(position, "LongitudeDegrees"), "text", None))
            if lat is None or lon is None:
                skipped += 1
                continue
            hr_node = child(tp, "HeartRateBpm")
            hr = None
            if hr_node is not None:
                # Garmin writes <HeartRateBpm><Value>148</Value></HeartRateBpm>; some devices write the number bare.
                value = child(hr_node, "Value")
                hr = number(value.text) if value is not None else number(hr_node.text)
            cad_node = child(tp, "Cadence")
            cad = number(cad_node.text) if cad_node is not None else None
            ext = child(tp, "Extensions")
            if cad is None and ext is not None:
                cad = find_ext(ext, ("runcadence", "cadence"))
            points.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "ele": number(getattr(child(tp, "AltitudeMeters"), "text", None)),
                    "time": parse_time(getattr(child(tp, "Time"), "text", None)),
                    "hr": hr,
                    "cad": cad,
                }
            )
    return name, kind, points, skipped


def title_from_file(stem):
    words = re.sub(r"[_\-]+", " ", stem).strip()
    return words[:1].upper() + words[1:] if words else "Activity"


def sport_of(kind, median_speed):
    word = (kind or "").strip().lower().replace(" ", "_")
    for sport, words in SPORT_WORDS.items():
        if word in words or any(word.startswith(w) for w in words if len(w) > 3):
            return sport
    if median_speed > 5.0:
        return "ride"
    if median_speed > 2.0:
        return "run"
    return "hike"


# ---------- terrain tiles ----------


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(data):
    """Rows of bytes and the channel count of an 8-bit, non-interlaced PNG (the terrain tiles' shape)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, width = 8, [], 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or interlace != 0 or color not in (2, 6):
                raise ValueError("unsupported PNG")
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            idat.append(body)
        pos += 12 + length
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    rows, previous = [], bytearray(stride)
    for r in range(height):
        start = r * (stride + 1)
        mode = raw[start]
        row = bytearray(raw[start + 1 : start + 1 + stride])
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            up = previous[i]
            corner = previous[i - channels] if i >= channels else 0
            if mode == 1:
                row[i] = (row[i] + left) & 255
            elif mode == 2:
                row[i] = (row[i] + up) & 255
            elif mode == 3:
                row[i] = (row[i] + ((left + up) >> 1)) & 255
            elif mode == 4:
                row[i] = (row[i] + paeth(left, up, corner)) & 255
        rows.append(bytes(row))
        previous = row
    return rows, channels


class Terrain:
    """Terrain tiles from the app's samples and the project's cache, downloaded when missing."""

    def __init__(self, offline):
        self.offline = offline
        self.decoded = {}
        self.downloaded = 0
        self.failed = 0

    def path(self, z, x, y):
        sample = SAMPLES / "terrain" / str(z) / str(x) / f"{y}.png"
        if sample.exists():
            return sample
        cached = TERRAIN_CACHE / str(z) / str(x) / f"{y}.png"
        return cached if cached.exists() else None

    def fetch(self, key):
        z, x, y = key
        if self.path(z, x, y) is not None or self.offline:
            return
        target = TERRAIN_CACHE / str(z) / str(x) / f"{y}.png"
        try:
            request = urllib.request.Request(TERRAIN_URL.format(z=z, x=x, y=y), headers={"User-Agent": "trail-replay"})
            with urllib.request.urlopen(request, timeout=20) as answer:
                body = answer.read()
        except (urllib.error.URLError, OSError, TimeoutError):
            self.failed += 1
            if self.failed >= 6:
                self.offline = True
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".part")
        temp.write_bytes(body)
        os.replace(temp, target)
        self.downloaded += 1

    def ensure(self, keys):
        missing = sorted(k for k in keys if self.path(*k) is None)
        if missing and not self.offline:
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(self.fetch, missing))
        return sorted(k for k in keys if self.path(*k) is not None)

    def elevation(self, lat, lon):
        z = TERRAIN_MAXZOOM
        x, y = mercator(lat, lon)
        px, py = x * 2**z * 256, y * 2**z * 256
        tx, ty = int(px // 256), int(py // 256)
        key = (z, tx, ty)
        if key not in self.decoded:
            path = self.path(*key)
            if path is None:
                self.fetch(key)
                path = self.path(*key)
            try:
                self.decoded[key] = decode_png(path.read_bytes()) if path else None
            except (ValueError, zlib.error, struct.error):
                self.decoded[key] = None
        tile = self.decoded[key]
        if tile is None:
            return None
        rows, channels = tile
        ix, iy = min(255, int(px - tx * 256)), min(255, int(py - ty * 256))
        r, g, b = rows[iy][ix * channels : ix * channels + 3]
        return r * 256 + g + b / 256 - 32768


def tiles_for(routes):
    """The terrain tiles a route needs: the full zoom near the track, wider and coarser further out."""
    reach_km = {13: 2.5, 12: 9, 11: 22, 10: 45, 9: 90}
    keys = set()
    for lats, lons in routes:
        stride = max(1, len(lats) // 400)
        sample = list(zip(lats[::stride], lons[::stride]))
        for z in range(0, TERRAIN_MAXZOOM + 1):
            reach = reach_km.get(z, 90)
            for lat, lon in sample:
                dlat = reach / 111.32
                dlon = reach / (111.32 * max(0.2, math.cos(math.radians(lat))))
                x0, y0 = tile_of(lat + dlat, lon - dlon, z)
                x1, y1 = tile_of(lat - dlat, lon + dlon, z)
                for tx in range(x0, x1 + 1):
                    for ty in range(y0, y1 + 1):
                        keys.add((z, tx, ty))
    return keys


# ---------- the activity ----------


def build_activity(ident, name, sport_word, points, terrain, file_name):
    points = [p for p in points if -90 <= p["lat"] <= 90 and -180 <= p["lon"] <= 180]
    timed = sum(1 for p in points if p["time"] is not None) >= max(2, len(points) * 0.9)
    if timed:
        points = sorted((p for p in points if p["time"] is not None), key=lambda p: p["time"])
        unique = []
        for p in points:
            if unique and p["time"] <= unique[-1]["time"]:
                continue
            unique.append(p)
        points = unique
    if len(points) < 2:
        return None
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    dist = [0.0]
    for i in range(1, len(points)):
        dist.append(dist[-1] + haversine(lats[i - 1], lons[i - 1], lats[i], lons[i]))
    total = dist[-1]
    if total < 50:
        return None

    if timed:
        times = [p["time"] - points[0]["time"] for p in points]
        steps = [(dist[i] - dist[i - 1]) / max(0.5, times[i] - times[i - 1]) for i in range(1, len(points))]
        median_speed = sorted(steps)[len(steps) // 2]
    else:
        median_speed = 0
    sport = sport_of(sport_word, median_speed)
    if not timed:
        # A route with no clock: replay it at an easy pace for the sport.
        pace = {"run": 2.9, "hike": 1.2, "ride": 6.5}[sport]
        times = [d / pace for d in dist]

    has_ele = sum(1 for p in points if p["ele"] is not None) >= len(points) * 0.9
    ele_source = "file"
    if has_ele:
        ele = [p["ele"] for p in points]
        for i in range(len(ele)):
            if ele[i] is None:
                ele[i] = ele[i - 1] if i else next(e for e in ele if e is not None)
    else:
        ele = [terrain.elevation(lat, lon) for lat, lon in zip(lats, lons)]
        if all(e is not None for e in ele):
            ele_source = "terrain"
        else:
            ele, ele_source = None, "none"

    # Elevation smoothed over about 30 m before counting climb, with a 2 m step so noise does not add up.
    climb = descent = 0.0
    smooth = None
    if ele is not None:
        smooth = []
        for i in range(len(ele)):
            lo, hi = i, i
            while lo > 0 and dist[i] - dist[lo - 1] <= 15:
                lo -= 1
            while hi < len(ele) - 1 and dist[hi + 1] - dist[i] <= 15:
                hi += 1
            smooth.append(sum(ele[lo : hi + 1]) / (hi - lo + 1))
        anchor = smooth[0]
        for e in smooth[1:]:
            if e - anchor >= 2:
                climb += e - anchor
                anchor = e
            elif anchor - e >= 2:
                descent += anchor - e
                anchor = e

    # Speed over a window of about 20 s either side, so the pace chart reads like a watch.
    speed = []
    j0 = j1 = 0
    n = len(points)
    for i in range(n):
        while times[i] - times[j0] > 20:
            j0 += 1
        while j1 < n - 1 and times[j1 + 1] - times[i] <= 20:
            j1 += 1
        # A watch that records every 30 s or more still gets a pace: the window always reaches the neighbors.
        a, b = min(j0, max(0, i - 1)), max(j1, min(n - 1, i + 1))
        span = times[b] - times[a]
        speed.append((dist[b] - dist[a]) / span if span > 0 else 0.0)

    floor = MOVING_FLOOR[sport]
    moving = 0.0
    for i in range(1, n):
        dt = times[i] - times[i - 1]
        if dt > 0 and (dist[i] - dist[i - 1]) / dt >= floor and dt < 60:
            moving += dt

    hrs = [p["hr"] for p in points]
    has_hr = sum(1 for h in hrs if h) >= n * 0.5
    cads = [p["cad"] for p in points]
    has_cad = sum(1 for c in cads if c) >= n * 0.5

    split_len = SPLIT_M[UNITS_CHOSEN]
    splits = []
    edge, start_i = split_len, 0
    i = 1
    while start_i < n - 1:
        while i < n - 1 and dist[i] < edge:
            i += 1
        seg_d = dist[i] - dist[start_i]
        seg_t = times[i] - times[start_i]
        gain = loss = 0.0
        if smooth is not None:
            for k in range(start_i + 1, i + 1):
                step = smooth[k] - smooth[k - 1]
                gain += max(0.0, step)
                loss += max(0.0, -step)
        seg_hr = [h for h in hrs[start_i : i + 1] if h]
        splits.append(
            {
                "d": round(seg_d, 1),
                "t": round(seg_t, 1),
                "up": round(gain, 1),
                "down": round(loss, 1),
                "hr": round(sum(seg_hr) / len(seg_hr)) if has_hr and seg_hr else None,
            }
        )
        start_i = i
        edge += split_len
        if seg_d < 1:
            break
    if len(splits) > 1 and splits[-1]["d"] < split_len * 0.05:
        tail = splits.pop()
        splits[-1]["d"] = round(splits[-1]["d"] + tail["d"], 1)
        splits[-1]["t"] = round(splits[-1]["t"] + tail["t"], 1)

    xs = [mercator(lat, lon) for lat, lon in zip(lats, lons)]
    minx, maxx = min(x for x, _ in xs), max(x for x, _ in xs)
    miny, maxy = min(y for _, y in xs), max(y for _, y in xs)
    size = max(maxx - minx, maxy - miny) or 1e-9
    norm = [((x - minx) / size, (y - miny) / size) for x, y in xs]
    mini = simplify(norm, 0.004)

    hr_values = [h for h in hrs if h]
    summary = {
        "distance": round(total, 1),
        "elapsed": round(times[-1], 1),
        "moving": round(moving if timed else times[-1], 1),
        "climb": round(climb),
        "descent": round(descent),
        "maxEle": round(max(smooth)) if smooth else None,
        "minEle": round(min(smooth)) if smooth else None,
        "avgHr": round(sum(hr_values) / len(hr_values)) if has_hr else None,
        "maxHr": round(max(hr_values)) if has_hr else None,
        "avgSpeed": round(total / moving, 3) if timed and moving > 0 else round(total / max(1.0, times[-1]), 3),
    }
    start = datetime.fromtimestamp(points[0]["time"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if timed else None
    meta = {
        "id": ident,
        "name": name,
        "sport": sport,
        "start": start,
        "file": file_name,
        "summary": summary,
        "bbox": [round(min(lons), 6), round(min(lats), 6), round(max(lons), 6), round(max(lats), 6)],
        "mini": [[round(x, 4), round(y, 4)] for x, y in mini],
        "has": {"time": timed, "ele": ele_source, "hr": has_hr, "cad": has_cad},
    }
    track = dict(meta)
    track.update(
        {
            "t": [round(t, 1) for t in times],
            "lat": [round(v, 6) for v in lats],
            "lon": [round(v, 6) for v in lons],
            "d": [round(v, 1) for v in dist],
            "ele": [round(v, 1) for v in smooth] if smooth else None,
            "v": [round(v, 3) for v in speed],
            "hr": [round(h) if h else None for h in hrs] if has_hr else None,
            "cad": [round(c) if c else None for c in cads] if has_cad else None,
            "splits": splits,
        }
    )
    return meta, track, (lats, lons)


# ---------- Strava ----------


def strava_get(path, token):
    request = urllib.request.Request(f"{STRAVA_API}{path}", headers={"Authorization": f"Bearer {token}", "User-Agent": "trail-replay"})
    with urllib.request.urlopen(request, timeout=30) as answer:
        return json.loads(answer.read())


def strava_activities(token):
    """The last thirty activities with a route, as (name, sport word, points, id, label)."""
    found = []
    try:
        listing = strava_get("/athlete/activities?per_page=30", token)
    except urllib.error.HTTPError as error:
        fail([f"Strava turned the token away ({error.code}); set a fresh one with csc key set {STRAVA_ENV}."])
    except (urllib.error.URLError, OSError) as error:
        print(f"Strava could not be reached ({getattr(error, 'reason', error)}); the files in the activities folder are used alone.")
        return found
    for item in listing:
        if not (item.get("map") or {}).get("summary_polyline"):
            continue
        keys = "time,latlng,altitude,heartrate,cadence"
        try:
            streams = strava_get(f"/activities/{item['id']}/streams?keys={keys}&key_by_type=true", token)
        except (urllib.error.URLError, OSError):
            continue
        latlng = (streams.get("latlng") or {}).get("data") or []
        clock = (streams.get("time") or {}).get("data") or []
        alt = (streams.get("altitude") or {}).get("data") or []
        hr = (streams.get("heartrate") or {}).get("data") or []
        cad = (streams.get("cadence") or {}).get("data") or []
        start = parse_time(item.get("start_date"))
        points = []
        for i, pair in enumerate(latlng):
            points.append(
                {
                    "lat": pair[0],
                    "lon": pair[1],
                    "ele": alt[i] if i < len(alt) else None,
                    "time": start + clock[i] if start is not None and i < len(clock) else None,
                    "hr": hr[i] if i < len(hr) else None,
                    "cad": cad[i] if i < len(cad) else None,
                }
            )
        found.append((item.get("name") or "Strava activity", item.get("sport_type") or item.get("type"), points, f"strava-{item['id']}", "Strava"))
    return found


# ---------- output ----------


def slug(text):
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "activity"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def resolve_activities(value):
    """The activities folder: beside the inputs file first, then the app's own samples."""
    for base in (PROJECT, HERE):
        folder = (base / value).resolve()
        if folder.is_dir():
            return folder, base == HERE
    fail([f'"activities" is "{value}", and there is no folder by that name beside {APP}.inputs.json.'])


def main():
    global UNITS_CHOSEN
    inputs = read_inputs()
    UNITS_CHOSEN = inputs["units"]
    folder, from_app = resolve_activities(inputs["activities"])
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in (".gpx", ".tcx"))

    sources = []
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            print(f"Skipped {path.name}: it is not readable XML ({error}).")
            continue
        parse = parse_tcx if path.suffix.lower() == ".tcx" else parse_gpx
        name, kind, points, skipped = parse(root)
        if skipped:
            print(f"{path.name}: skipped {skipped} points with no position.")
        sources.append((name or title_from_file(path.stem), kind, points, slug(path.stem), path))

    if inputs["strava"]:
        token = os.environ.get(STRAVA_ENV, "").strip()
        if not token:
            fail([f'"strava" is true, and {STRAVA_ENV} is not set. Set it with csc key set {STRAVA_ENV}, or set "strava" to false.'])
        sources.extend(strava_activities(token))

    if not sources:
        fail([f'There are no GPX or TCX files in "{inputs["activities"]}". Strava, Garmin Connect, and Apple Fitness all export them.'])

    terrain = Terrain(offline=False)
    built, seen = [], set()
    for name, kind, points, ident, origin in sources:
        while ident in seen:
            ident += "-2"
        seen.add(ident)
        label = origin.name if isinstance(origin, Path) else origin
        result = build_activity(ident, name, kind, points, terrain, label)
        if result is None:
            print(f"Skipped {label}: it has fewer than two timed points or under 50 m of track.")
            continue
        built.append((result, origin))

    if not built:
        fail(["None of the activity files had a track to replay."])

    keys = tiles_for([route for (_, _, route), _ in built])
    ready = terrain.ensure(keys)

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(DIST, OUT)
    # The built page carries the samples for a look without a run; this run's activities replace them.
    for stale in ("data", "terrain"):
        if (OUT / stale).exists():
            shutil.rmtree(OUT / stale)
    media = OUT / "media"
    media.mkdir(parents=True, exist_ok=True)
    for (meta, track, _), origin in built:
        if isinstance(origin, Path):
            shutil.copyfile(origin, media / origin.name)
        write_json(OUT / "data" / f"{meta['id']}.json", track)
    metas = sorted((meta for (meta, _, _), _ in built), key=lambda m: (m["start"] or "", m["id"]), reverse=True)
    write_json(OUT / "data" / "index.json", {"activities": metas, "sample": from_app})

    for z, x, y in ready:
        target = OUT / "terrain" / str(z) / str(x) / f"{y}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(terrain.path(z, x, y), target)
    complete = len(ready) == len(keys)
    write_json(
        OUT / "terrain" / "tiles.json",
        {"maxzoom": TERRAIN_MAXZOOM, "tiles": [f"{z}/{x}/{y}" for z, x, y in ready], "online": not (from_app and complete)},
    )

    shutil.copyfile(THEMES / f"{inputs['theme']}.css", OUT / "theme.css")
    config = {key: inputs[key] for key in KEYS}
    config["activities"] = "media"
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    per = SPLIT_M[UNITS_CHOSEN]
    for meta in metas:
        s = meta["summary"]
        climb = f"{s['climb']} m" if UNITS_CHOSEN == "km" else f"{round(s['climb'] * 3.28084)} ft"
        print(f"{meta['name']}: {s['distance'] / per:.2f} {UNITS_CHOSEN}, {climb} climb.")
    note = f"{len(ready)} of {len(keys)} terrain tiles ready"
    if terrain.downloaded:
        note += f", {terrain.downloaded} downloaded into {TERRAIN_CACHE.name}/"
    if not complete:
        note += "; the page fetches the rest while it is online"
    print(note + ".")
    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


UNITS_CHOSEN = "km"

if __name__ == "__main__":
    main()
