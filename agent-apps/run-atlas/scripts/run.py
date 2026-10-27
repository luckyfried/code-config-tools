"""Run Atlas: turns a folder of GPX files into a wall of route drawings.

Run from the project folder:

    python3 <agent-apps root>/run-atlas/scripts/run.py

It reads run-atlas.inputs.json from the current folder, parses every GPX file in the folder its "activitiesDir"
names (the sample year that ships with the app when that is empty), and writes out/run-atlas/: the page, data.js
with one entry per activity, tracks/ with each full track, media/activities/ with the GPX files, theme.css, and
config.js. Python 3 standard library only. Two runs on the same inputs write the same bytes.
"""

import gzip
import json
import math
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

SLUG = "run-atlas"
INPUTS = f"{SLUG}.inputs.json"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"
SAMPLE = APP / "sample" / "activities"

SPORTS = ("run", "ride", "walk", "hike")
UNITS = {"km": 1000.0, "mi": 1609.344}
# The fastest a split can plausibly be, in meters a second; a faster one is a GPS jump and is flagged.
PLAUSIBLE_MAX = {"run": 7.0, "ride": 25.0, "walk": 3.2, "hike": 3.2}
# Below this speed a stretch counts as stopped, not moving.
MOVING_MIN = {"run": 0.5, "ride": 1.0, "walk": 0.35, "hike": 0.3}
# The best effort each sport is ranked on: fastest 5 km on foot, fastest 20 km on a bike.
EFFORT = {"run": 5000, "walk": 5000, "hike": 5000, "ride": 20000}
SMOOTH_S = 30
R_EARTH = 6371008.8
BOX = 1000


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


# ---------- inputs ----------

def read_inputs(project):
    path = project / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail([f"{INPUTS} is not valid JSON (line {error.lineno}, column {error.colno})."])
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must hold one JSON object."])

    problems = []
    known = {"activitiesDir", "units", "sports", "year", "theme", "_notes"}
    for key in ("activitiesDir", "units", "sports", "year", "theme"):
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    for key in inputs:
        if key not in known:
            problems.append(f'{INPUTS} has the key "{key}", which Run Atlas does not use.')

    if "activitiesDir" in inputs and not isinstance(inputs["activitiesDir"], str):
        problems.append(f'{INPUTS}: "activitiesDir" must be a folder name in quotes, or "" for the sample year.')
    if "units" in inputs and inputs["units"] not in UNITS:
        problems.append(f'{INPUTS}: "units" must be "km" or "mi".')
    if "sports" in inputs:
        sports = inputs["sports"]
        if not isinstance(sports, list) or any(s not in SPORTS for s in sports):
            problems.append(f'{INPUTS}: "sports" must be a list of "run", "ride", "walk", and "hike", or [] for all.')
    if "year" in inputs:
        year = inputs["year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1990 <= year <= 2100):
            problems.append(f'{INPUTS}: "year" must be a year such as 2026, or null for the latest.')
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    if "theme" in inputs and inputs["theme"] not in themes:
        problems.append(f'{INPUTS}: "theme" must be one of {", ".join(themes)}.')
    if problems:
        fail(problems)
    return inputs


# ---------- GPX ----------

def local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_time(text):
    if not text:
        return None
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def read_gpx(path):
    """Answers {name, kind, meta_time, segments: [[(lat, lon, ele, time)]]} for one GPX file."""
    opener = gzip.open if path.suffix == ".gz" else open
    name = kind = None
    meta_time = None
    track_segments, route_points = [], []
    current = None
    point = None
    stack = []
    with opener(path, "rb") as handle:
        for event, element in ET.iterparse(handle, events=("start", "end")):
            tag = local(element.tag)
            if event == "start":
                stack.append(tag)
                if tag == "trkseg":
                    current = []
                elif tag in ("trkpt", "rtept"):
                    try:
                        point = [float(element.get("lat")), float(element.get("lon")), None, None]
                    except (TypeError, ValueError):
                        point = None
                continue
            stack.pop()
            parent = stack[-1] if stack else ""
            text = (element.text or "").strip()
            if tag == "ele" and point is not None and parent in ("trkpt", "rtept"):
                try:
                    point[2] = float(text)
                except ValueError:
                    pass
            elif tag == "time" and point is not None and parent in ("trkpt", "rtept"):
                point[3] = parse_time(text)
            elif tag == "time" and parent == "metadata":
                meta_time = parse_time(text)
            elif tag == "name" and parent in ("trk", "metadata", "rte") and text and name is None:
                name = text
            elif tag == "type" and parent in ("trk", "rte") and text:
                kind = text
            elif tag == "trkpt" and point is not None and current is not None:
                current.append(tuple(point))
                point = None
            elif tag == "rtept" and point is not None:
                route_points.append(tuple(point))
                point = None
            elif tag == "trkseg" and current:
                track_segments.append(current)
                current = None
            if tag in ("trkpt", "rtept", "trkseg", "trk"):
                element.clear()
    segments = track_segments or ([route_points] if route_points else [])
    return {"name": name, "kind": kind, "meta_time": meta_time, "segments": segments}


def sport_of(kind, name, speed):
    text = (kind or "").lower()
    words = {"run": ("run", "jog"), "ride": ("ride", "cycl", "bik", "biking"), "walk": ("walk",), "hike": ("hik",)}
    numbers = {"9": "run", "1": "ride", "10": "walk", "4": "hike"}
    if text in numbers:
        return numbers[text]
    for sport, keys in words.items():
        if any(k in text for k in keys):
            return sport
    title = (name or "").lower()
    for sport, keys in words.items():
        if any(k in title for k in keys):
            return sport
    if speed is None:
        return "run"
    return "ride" if speed > 4.6 else "run" if speed > 2.0 else "walk"


def haversine(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(min(1.0, math.sqrt(h)))


def douglas_peucker(points, eps):
    """Keeps the points a line needs to stay within eps of the original; iterative, so long tracks are fine."""
    if len(points) < 3:
        return list(range(len(points)))
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        best, at = -1.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            if norm == 0:
                dist = math.hypot(px - ax, py - ay)
            else:
                dist = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if dist > best:
                best, at = dist, i
        if best > eps and at > 0:
            keep[at] = True
            stack.append((a, at))
            stack.append((at, b))
    return [i for i, k in enumerate(keep) if k]


def elevation_change(values):
    """Gain and loss with a 2 m hysteresis over a five-point mean, so GPS noise does not count as climbing."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return 0.0, 0.0
    smooth = []
    for i in range(len(vals)):
        window = vals[max(0, i - 2): i + 3]
        smooth.append(sum(window) / len(window))
    gain = loss = 0.0
    ref = smooth[0]
    for v in smooth[1:]:
        if v - ref >= 2.0:
            gain += v - ref
            ref = v
        elif ref - v >= 2.0:
            loss += ref - v
            ref = v
    return gain, loss


def utc_offset(lon):
    """The local clock's offset from UTC, estimated from longitude, so a 7 am run in Portland reads as morning."""
    return timedelta(hours=max(-12, min(14, round(lon / 15))))


def analyse(path, gpx, unit_m, ident):
    segments = [s for s in gpx["segments"] if s]
    flat = [p for s in segments for p in s]
    if len(flat) < 2:
        return None
    timed = all(p[3] is not None for p in flat)
    first_time = flat[0][3] if timed else gpx["meta_time"]

    # cumulative distance, moving time, and capped distance (a step faster than plausible counts at the cap)
    cum_d, cum_mt, cum_clean, ele = [0.0], [0.0 if timed else None], [0.0], [flat[0][2]]
    start_of_seg = set()
    k = 0
    for s in segments:
        start_of_seg.add(k)
        k += len(s)
    for i in range(1, len(flat)):
        a, b = flat[i - 1], flat[i]
        ds = 0.0 if i in start_of_seg else haversine(a, b)
        cum_d.append(cum_d[-1] + ds)
        ele.append(b[2])
        cum_mt.append(None)
        cum_clean.append(cum_clean[-1] + ds)
        if timed:
            cum_mt[-1] = cum_mt[-2]
    distance = cum_d[-1]
    if distance < 50:
        return None

    elapsed = (flat[-1][3] - flat[0][3]).total_seconds() if timed else None
    avg = distance / elapsed if timed and elapsed else None
    sport = sport_of(gpx["kind"], gpx["name"], avg)

    if timed:
        limit = PLAUSIBLE_MAX[sport] * 1.6
        floor = MOVING_MIN[sport]
        for i in range(1, len(flat)):
            dt = max(0.0, (flat[i][3] - flat[i - 1][3]).total_seconds())
            ds = cum_d[i] - cum_d[i - 1]
            moving = dt > 0 and ds / dt >= floor
            cum_mt[i] = cum_mt[i - 1] + (dt if moving else 0.0)
            cum_clean[i] = cum_clean[i - 1] + (min(ds, limit * dt) if dt > 0 else 0.0)
    duration = cum_mt[-1] if timed else None

    gain, loss = elevation_change(ele)

    # smoothed speed over a 30 s window of moving time
    speed = [None] * len(flat)
    if timed and duration:
        lo = hi = 0
        for i in range(len(flat)):
            while cum_mt[lo] < cum_mt[i] - SMOOTH_S / 2 and lo < i:
                lo += 1
            while hi < len(flat) - 1 and cum_mt[hi + 1] <= cum_mt[i] + SMOOTH_S / 2:
                hi += 1
            span = cum_mt[hi] - cum_mt[lo]
            speed[i] = (cum_d[hi] - cum_d[lo]) / span if span > 0 else None

    # splits by unit
    splits = []
    if distance > 0:
        bounds = []
        n_full = int(distance // unit_m)
        targets = [unit_m * (j + 1) for j in range(n_full)]
        if distance - unit_m * n_full >= 0.05 * unit_m or not targets:
            targets.append(distance)
        j = 0
        prev_d, prev_t, prev_i = 0.0, 0.0, 0
        for target in targets:
            while j < len(cum_d) - 1 and cum_d[j + 1] < target:
                j += 1
            if j >= len(cum_d) - 1:
                t_at = cum_mt[-1] if timed else None
                end_i = len(cum_d) - 1
            else:
                seg = cum_d[j + 1] - cum_d[j]
                f = (target - cum_d[j]) / seg if seg > 0 else 0
                t_at = cum_mt[j] + (cum_mt[j + 1] - cum_mt[j]) * f if timed else None
                end_i = j + 1
            sg, sl = elevation_change(ele[prev_i:end_i + 1])
            length = target - prev_d
            secs = (t_at - prev_t) if timed else None
            fast = bool(timed and secs and length / secs > PLAUSIBLE_MAX[sport])
            splits.append({
                "d": round(length),
                "t": round(secs) if secs is not None else None,
                "up": round(sg),
                "down": round(sl),
                "flag": fast,
            })
            bounds.append(end_i)
            prev_d, prev_t, prev_i = target, t_at, end_i

    # best effort over the sport's distance, on the capped distance
    best = None
    effort = EFFORT[sport]
    if timed and cum_clean[-1] >= effort:
        a = 0
        for b in range(len(flat)):
            if cum_clean[b] - cum_clean[0] < effort:
                continue
            while a + 1 < b and cum_clean[b] - cum_clean[a + 1] >= effort:
                a += 1
            secs = cum_mt[b] - cum_mt[a]
            if secs > 0:
                scaled = secs * effort / (cum_clean[b] - cum_clean[a])
                best = scaled if best is None or scaled < best else best
        best = round(best) if best else None

    # local projection and the square box every route is drawn in
    lat0 = sum(p[0] for p in flat) / len(flat)
    lon0 = sum(p[1] for p in flat) / len(flat)
    kx = R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    ky = R_EARTH * math.pi / 180
    xy = [((p[1] - lon0) * kx, (lat0 - p[0]) * ky) for p in flat]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    extent = max(w, h, 1.0)
    scale = BOX / extent
    ox = min(xs) - (extent - w) / 2
    oy = min(ys) - (extent - h) / 2
    box = [((x - ox) * scale, (y - oy) * scale) for x, y in xy]

    keep = douglas_peucker(box, BOX / 320)
    tile = []
    for i in keep:
        x, y = round(box[i][0]), round(box[i][1])
        if not tile or tile[-1] != [x, y]:
            tile.append([x, y])

    local_start = first_time + utc_offset(lon0) if first_time else None
    track = {
        "x": [round(p[0], 1) for p in box],
        "y": [round(p[1], 1) for p in box],
        "d": [round(v) for v in cum_d],
        "t": [round(v) for v in cum_mt] if timed else None,
        "e": [round(v, 1) if v is not None else None for v in ele] if any(v is not None for v in ele) else None,
        "v": [round(v, 1) if v is not None else None for v in speed] if timed else None,
        "splits": splits,
    }
    entry = {
        "id": ident,
        "name": gpx["name"] or default_name(sport, local_start),
        "sport": sport,
        "date": local_start.strftime("%Y-%m-%d") if local_start else None,
        "time": local_start.strftime("%H:%M") if local_start else None,
        "start": first_time.strftime("%Y-%m-%dT%H:%M:%SZ") if first_time else None,
        "distance": round(distance),
        "duration": round(duration) if duration is not None else None,
        "elapsed": round(elapsed) if elapsed is not None else None,
        "gain": round(gain),
        "best": best,
        "effort": effort,
        "span": round(extent),
        "flags": sum(1 for s in splits if s["flag"]),
        "points": tile,
        "track": f"tracks/{ident}.json",
        "file": f"media/activities/{path.name}",
    }
    return entry, track


def default_name(sport, moment):
    word = dict(run="Run", ride="Ride", walk="Walk", hike="Hike")[sport]
    if moment is None:
        return word
    hour = moment.hour
    part = "Morning" if hour < 11 else "Lunch" if hour < 14 else "Afternoon" if hour < 17 else "Evening" if hour < 21 else "Night"
    return f"{part} {word}"


def ident_of(stem, taken):
    base = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "activity"
    ident, n = base, 2
    while ident in taken:
        ident, n = f"{base}-{n}", n + 1
    taken.add(ident)
    return ident


# ---------- the run ----------

def main():
    project = Path.cwd()
    inputs = read_inputs(project)
    sample = inputs["activitiesDir"].strip() == ""
    source = SAMPLE if sample else (project / inputs["activitiesDir"]).resolve()
    if not source.is_dir():
        fail([f'{INPUTS}: the folder "{inputs["activitiesDir"]}" in "activitiesDir" is not there.'])
    files = sorted(p for p in source.iterdir() if p.is_file() and (p.name.lower().endswith(".gpx") or p.name.lower().endswith(".gpx.gz")))
    others = sorted(p for p in source.iterdir() if p.is_file() and re.search(r"\.(fit|tcx)(\.gz)?$", p.name.lower()))
    if not files:
        fail([f'The folder "{inputs["activitiesDir"]}" holds no GPX files yet; export your activities as GPX into it.'])

    unit_m = UNITS[inputs["units"]]
    wanted = set(inputs["sports"]) or set(SPORTS)
    activities, tracks, skipped, copies = [], {}, [], []
    taken = set()
    for path in files:
        try:
            gpx = read_gpx(path)
        except (ET.ParseError, OSError, EOFError):
            skipped.append(f"Skipped {path.name}: it is not a GPX file Run Atlas can read.")
            continue
        stem = path.name[: -len(".gpx.gz")] if path.name.lower().endswith(".gpx.gz") else path.stem
        result = analyse(path, gpx, unit_m, ident_of(stem, taken))
        if result is None:
            skipped.append(f"Skipped {path.name}: it has fewer than two points or almost no distance.")
            continue
        entry, track = result
        if entry["sport"] not in wanted:
            continue
        activities.append(entry)
        tracks[entry["id"]] = track
        copies.append(path)
    if not activities:
        fail([f'None of the GPX files in "{inputs["activitiesDir"] or "the sample"}" are of the sports in "sports".'])

    activities.sort(key=lambda a: (a["start"] is None, a["start"] or "", a["id"]), reverse=False)
    activities.reverse()
    activities.sort(key=lambda a: a["start"] is None)

    months = {}
    for a in activities:
        if a["date"]:
            slot = months.setdefault(a["date"][:7], {})
            slot[a["sport"]] = slot.get(a["sport"], 0) + a["distance"]
    months = {key: dict(sorted(months[key].items())) for key in sorted(months)}
    dated_total = sum(a["distance"] for a in activities if a["date"])
    month_total = sum(v for slot in months.values() for v in slot.values())
    if month_total != dated_total:
        print(f"The monthly totals ({month_total} m) do not add up to the activities ({dated_total} m).")
        sys.exit(1)

    years = sorted({int(a["date"][:4]) for a in activities if a["date"]}, reverse=True)
    data = {
        "sample": sample,
        "units": inputs["units"],
        "years": years,
        "sports": [s for s in SPORTS if any(a["sport"] == s for a in activities)],
        "months": months,
        "activities": activities,
    }

    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    if (APP / "badge.js").is_file():
        shutil.copyfile(APP / "badge.js", out / "badge.js")
    shutil.rmtree(out / "tracks", ignore_errors=True)
    (out / "tracks").mkdir()
    for ident in sorted(tracks):
        (out / "tracks" / f"{ident}.json").write_text(json.dumps(tracks[ident], separators=(",", ":")), encoding="utf-8")
    media = out / "media" / "activities"
    media.mkdir(parents=True)
    for path in copies:
        shutil.copyfile(path, media / path.name)

    (out / "data.js").write_text(
        "window.__RUN_ATLAS__ = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    config["activitiesDir"] = "media/activities"
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config)};\n", encoding="utf-8")

    for line in skipped:
        print(line)
    if others:
        files_word = "file" if len(others) == 1 else "files"
        print(f"Left out {len(others)} FIT or TCX {files_word}; Run Atlas reads GPX, so export those activities as GPX.")
    km = month_total / unit_m
    print(f"Read {len(activities)} activities, {km:,.1f} {inputs['units']} in all; the monthly bars add up to the same.")
    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
