#!/usr/bin/env python3
"""Movement 1, research: which trip, its days, its places, its people and its clips. Reads build/library.json,
writes build/trip.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/trip.py [--place "lisbon"] [--from 2026-10-03 --to 2026-10-08] [--album "Amalfi coast"]
                              [--folder "DIR or folder name"]

The person's own words win over anything inferred: pass what they named (a place, a date range, an album, a folder
of clips). With none of those, the most recent trip is taken. A trip is a run of days away from home:
  1. geotags: home is the place their geotagged posts return to across the most months (when one exists); every
     day with a geotag more than 60 km from home is a day away, and days away no more than two apart are one trip
  2. without geotags: a Facebook album or a photo folder spanning at most three weeks, or a run of days whose
     captions share a word they use nowhere else (a place name)
A trip needs two days or five items. Every post, reel, story and photo dated inside it belongs to it.

Places: the trip's geotags gathered into stops (within 5 km of each other). Each stop is named by the place field
of its items when the data has one, else by the word its captions use most and the other stops' captions use least
(captions name places), else by its coordinates. No map service is asked anything: the route is drawn later from
these coordinates alone. Days: every date of the trip with its items, its stops and its captions; a day without a
geotag stays where the day before ended. People: everyone @mentioned or tagged on the trip at least twice. Clips:
the videos shot on the trip, with their length. Music: the track names on their travel posts when the data has
them. trip.json lists the other trips it found and why this one was chosen; every choice is under "assumptions".
"""
import argparse
import collections
import datetime as dt
import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

VIDEO = {".mp4", ".mov", ".m4v", ".webm"}
AWAY_KM = 60
STOP_KM = 5
STOP = set("""a an and are as at be been but by can day days did do for from get got had has have here i i'm im in into is
it its it's just last like little me more most my new next no not now of off on one only or our out over so some
still than that the their them then there these they this those to too two up very was we were what when where which
who will with you your all about after again also any back before being both each even every first few go going good
great how if just know lot made make much need never nice once other really right see should since such take thing
think three time today tomorrow way week well while why would yes yet four five six seven eight nine ten am pm""".split())
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]


def day_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def words(text):
    text = re.sub(r"[@#][\w.]+", " ", (text or "").lower())
    return [w for w in re.findall(r"[a-zà-ÿ][a-zà-ÿ'-]+", text) if len(w) >= 3 and w not in STOP]


def mentions(text):
    return [m.rstrip(".") for m in re.findall(r"@([\w.]+)", text or "")]


def items_of(lib):
    out = []
    for kind in ("posts", "reels", "stories", "facebook"):
        for r in lib.get(kind) or []:
            if not r.get("ts"):
                continue
            out.append({"kind": kind[:-1] if kind != "facebook" else "facebook", "ts": int(r["ts"]), "day": day_of(r["ts"]),
                        "caption": r.get("caption") or "", "media": r.get("media") or [], "geo": r.get("geo"),
                        "place": r.get("place") or "", "tagged": r.get("tagged") or [], "album": r.get("album") or "",
                        "folder": r.get("folder") or "", "music": r.get("music") or ""})
    out.sort(key=lambda x: x["ts"])
    return out


def find_home(items):
    """The 0.25-degree cell their geotags return to across the most months, when that is four months or more."""
    cells = collections.defaultdict(lambda: {"months": set(), "pts": []})
    for x in items:
        if x["geo"]:
            c = cells[(round(x["geo"][0] * 4), round(x["geo"][1] * 4))]
            c["months"].add((x["day"].year, x["day"].month))
            c["pts"].append(x["geo"])
    if not cells:
        return None
    best = max(cells.values(), key=lambda c: (len(c["months"]), len(c["pts"])))
    if len(best["months"]) < 4:
        return None
    pts = best["pts"]
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def runs(days, gap=2):
    """Sorted dates grouped into runs whose neighbors are at most gap days apart."""
    out = []
    for d in sorted(set(days)):
        if out and (d - out[-1][-1]).days <= gap:
            out[-1].append(d)
        else:
            out.append([d])
    return out


def candidate(items, lo, hi, why):
    inside = [x for x in items if lo <= x["day"] <= hi]
    return {"from": lo, "to": hi, "items": inside, "why": why}


def candidates(items, home):
    out = []
    away = [x for x in items if x["geo"] and (home is None or km(x["geo"], home) > AWAY_KM)]
    for r in runs([x["day"] for x in away]):
        out.append(candidate(items, r[0], r[-1], "geotags away from home" if home else "geotags"))
    for key, label in (("album", "the album"), ("folder", "the folder")):
        groups = collections.defaultdict(list)
        for x in items:
            if x[key]:
                groups[x[key]].append(x["day"])
        for name, ds in groups.items():
            if len(ds) >= 4 and (max(ds) - min(ds)).days <= 21:
                c = candidate(items, min(ds), max(ds), f"{label} \"{name}\"")
                c[key] = name
                out.append(c)
    if not away:
        # a run of days whose captions share a word used nowhere else in their captions: a place name
        by_word = collections.defaultdict(set)
        for x in items:
            for w in set(words(x["caption"])):
                by_word[w].add(x["day"])
        for w, ds in by_word.items():
            for r in runs(ds, 2):
                if len(r) >= 2 and len(ds) - len(r) <= 1 and (r[-1] - r[0]).days <= 21:
                    c = candidate(items, r[0], r[-1], f"captions on {len(r)} days naming \"{w}\"")
                    c["word"] = w
                    out.append(c)
    keep = []
    for c in sorted(out, key=lambda c: (c["from"], -(c["to"] - c["from"]).days)):
        days = len({x["day"] for x in c["items"]})
        if days < 2 and len(c["items"]) < 5:
            continue
        same = next((k for k in keep if c["from"] <= k["to"] and k["from"] <= c["to"]), None)
        if same:
            same["from"], same["to"] = min(same["from"], c["from"]), max(same["to"], c["to"])
            same["items"] = [x for x in items if same["from"] <= x["day"] <= same["to"]]
            for key in ("album", "folder", "word"):
                same.setdefault(key, c.get(key)) if c.get(key) else None
            continue
        keep.append(c)
    return keep


def text_of(x):
    return " ".join([x["caption"], x["place"], x["album"], x["folder"]]).lower()


def choose(items, cands, a):
    """The trip the person named, else the most recent one. Returns (trip, how it was chosen)."""
    if a.date_from or a.date_to:
        lo = dt.date.fromisoformat(a.date_from) if a.date_from else dt.date.fromisoformat(a.date_to) - dt.timedelta(days=6)
        hi = dt.date.fromisoformat(a.date_to) if a.date_to else lo + dt.timedelta(days=6)
        return candidate(items, lo, hi, "the dates you named"), f"the dates you named, {lo} to {hi}"
    for key, val in (("album", a.album), ("folder", a.folder)):
        if val:
            v = Path(val).name.lower()
            hits = [x["day"] for x in items if v and v in x[key].lower()]
            if hits:
                c = candidate(items, min(hits), max(hits), f"the {key} you named")
                c[key] = next(x[key] for x in items if v in x[key].lower())
                return c, f"the {key} you named, \"{c[key]}\""
    if a.place:
        v = a.place.lower().strip()
        named = [c for c in cands if any(v in text_of(x) for x in c["items"])]
        if named:
            c = max(named, key=lambda c: c["to"])
            return c, f"the place you named, {a.place}"
        hits = [x["day"] for x in items if v in text_of(x)]
        if hits:
            r = max(runs(hits, 2), key=lambda r: r[-1])
            return candidate(items, r[0], r[-1], f"posts naming {a.place}"), f"the place you named, {a.place}"
        if not cands:
            return None, f"nothing in the data names {a.place}"
    if not cands:
        return None, "no trip found"
    c = max(cands, key=lambda c: c["to"])
    how = "the most recent trip"
    if len(cands) > 1:
        how += f" of the {len(cands)} found"
    return c, how


def stops_of(trip_items, everyday_words):
    """Geotags gathered into stops, each named; ordered by first visit."""
    stops = []
    for x in trip_items:
        if not x["geo"]:
            continue
        s = next((s for s in stops if km(s["center"], x["geo"]) <= STOP_KM), None)
        if not s:
            s = {"center": list(x["geo"]), "items": []}
            stops.append(s)
        s["items"].append(x)
        n = len(s["items"])
        s["center"] = [s["center"][0] + (x["geo"][0] - s["center"][0]) / n, s["center"][1] + (x["geo"][1] - s["center"][1]) / n]
    counts = [collections.Counter(w for x in s["items"] for w in words(x["caption"]) if w not in everyday_words) for s in stops]
    for i, s in enumerate(stops):
        named = collections.Counter(x["place"] for x in s["items"] if x["place"])
        if named:
            s["name"], s["named_by"] = named.most_common(1)[0][0], "the place in the data"
            continue
        best = None
        for w, n in counts[i].items():
            elsewhere = sum(c.get(w, 0) for j, c in enumerate(counts) if j != i)
            key = (n >= 2, n / (1 + elsewhere), n)
            if n / (1 + elsewhere) >= 1 and (best is None or key > best[0]):
                best = (key, w)
        if best:
            s["name"], s["named_by"] = best[1], "its captions"
        else:
            s["name"], s["named_by"] = f"{s['center'][0]:.2f}, {s['center'][1]:.2f}", "its coordinates"
    seen = collections.Counter()
    for s in stops:
        seen[s["name"]] += 1
        if seen[s["name"]] > 1:
            s["name"] = f"{s['name']} {seen[s['name']]}"
    return stops


def duration(path):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 2)
    except ValueError:
        return None


def trip_name(trip, stops, a):
    if trip.get("album"):
        n = re.sub(r"\b(" + "|".join(MONTHS) + r")\b|\b(19|20)\d\d\b", "", trip["album"].lower())
        n = re.sub(r"[,.\-–/]+", " ", n).strip()
        if n:
            return re.sub(r"\s+", " ", n)
    if a.place:
        return a.place.lower().strip()
    if trip.get("folder"):
        return re.sub(r"[_\-]+", " ", trip["folder"]).lower()
    named = [s["name"] for s in sorted(stops, key=lambda s: -len(s["items"])) if s["named_by"] != "its coordinates"]
    if trip.get("word") and not named:
        return trip["word"]
    if len(named) >= 2:
        return f"{named[0]} and {named[1]}" if len(named) == 2 else f"{named[0]} and around"
    return named[0] if named else "the trip"


def short_item(x):
    return {"kind": x["kind"], "ts": x["ts"], "caption": x["caption"], "media": x["media"], "geo": x["geo"],
            "place": x.get("stop")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place", help="a place the person named")
    ap.add_argument("--from", dest="date_from", help="first day the person named (YYYY-MM-DD)")
    ap.add_argument("--to", dest="date_to", help="last day the person named (YYYY-MM-DD)")
    ap.add_argument("--album", help="an album the person named")
    ap.add_argument("--folder", help="a folder of photos or clips the person named")
    a = ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    items = items_of(lib)
    if not items:
        sys.exit("the library has no dated posts, stories or photos")
    home = find_home(items)
    cands = candidates(items, home)
    trip, how = choose(items, cands, a)
    notes = []
    if not trip:
        last = max(x["day"] for x in items)
        trip = candidate(items, last - dt.timedelta(days=6), last, "the last week of posts")
        notes.append(f"No trip stood out ({how}), so the recap covers the last week of posts, {trip['from']} to {trip['to']}.")
        how = "the last week of posts"
    else:
        notes.append(f"The trip is {how}: {trip['from']} to {trip['to']} ({trip['why']}).")
    others = [c for c in cands if not (c["from"] == trip["from"] and c["to"] == trip["to"])]
    tset = {id(x) for x in trip["items"]}
    everyday = [x for x in items if id(x) not in tset and not any(c["from"] <= x["day"] <= c["to"] for c in cands)]
    everyday_words = {w for w, n in collections.Counter(w for x in everyday for w in set(words(x["caption"]))).items() if n >= 2}
    stops = stops_of(trip["items"], everyday_words)
    for s in stops:
        for x in s["items"]:
            x["stop"] = s["name"]
    if not stops:
        notes.append("No geotags on the trip, so the route is drawn from the order of the places its captions name.")
    # days, each with its stops in visiting order; a day with no geotag stays where the day before ended
    days, where = [], None
    d = trip["from"]
    while d <= trip["to"]:
        xs = [x for x in trip["items"] if x["day"] == d]
        visited = list(dict.fromkeys(x["stop"] for x in xs if x.get("stop")))
        if not visited and not stops:
            caps = " ".join(x["caption"].lower() for x in xs)
            visited = [w for w in (trip.get("word"),) if w and w in caps]
        if not visited and where:
            visited = [where]
        where = visited[-1] if visited else where
        for x in xs:
            x.setdefault("stop", visited[0] if visited else None)
        days.append({"date": d.isoformat(), "n": len(xs), "places": visited,
                     "captions": [x["caption"] for x in xs if x["caption"].strip()],
                     "kinds": dict(collections.Counter(x["kind"] for x in xs)), "items": [short_item(x) for x in xs]})
        d += dt.timedelta(days=1)
    if not stops and trip.get("word"):
        stops = [{"name": trip["word"], "center": None, "items": trip["items"], "named_by": "its captions"}]
    route = []
    for x in trip["items"]:
        if x.get("stop") and x["geo"] and (not route or route[-1]["place"] != x["stop"]):
            s = next(s for s in stops if s["name"] == x["stop"])
            route.append({"place": s["name"], "lat": round(s["center"][0], 5), "lon": round(s["center"][1], 5),
                          "day": x["day"].isoformat()})
    places = [{"name": s["name"], "lat": round(s["center"][0], 5) if s.get("center") else None,
               "lon": round(s["center"][1], 5) if s.get("center") else None, "items": len(s["items"]),
               "named_by": s["named_by"], "days": sorted({x["day"].isoformat() for x in s["items"]})} for s in stops]
    me = (lib.get("handle") or "").lower()
    ppl = collections.Counter()
    pdays = collections.defaultdict(set)
    for x in trip["items"]:
        for h in set(mentions(x["caption"]) + x["tagged"]):
            if h.lower() != me:
                ppl[h] += 1
                pdays[h].add(x["day"].isoformat())
    people = [{"handle": h, "items": n, "days": len(pdays[h])} for h, n in ppl.most_common() if n >= 2]
    clips = []
    for x in trip["items"]:
        for m in x["media"]:
            if Path(m).suffix.lower() in VIDEO and Path(m).exists():
                clips.append({"file": m, "ts": x["ts"], "day": x["day"].isoformat(), "place": x.get("stop"),
                              "seconds": duration(m), "caption": x["caption"]})
    travel = [x for c in cands for x in c["items"]] or trip["items"]
    music = sorted({x["music"] for x in travel if x["music"]})
    name = trip_name(trip, stops, a)
    if home:
        notes.append(f"Home is near {home[0]:.2f}, {home[1]:.2f}; days more than {AWAY_KM} km away count as away.")
    if others:
        notes.append("Other trips found: " + "; ".join(f"{c['from']} to {c['to']} ({c['why']})" for c in others) + ".")
    unnamed = [s["name"] for s in stops if s["named_by"] == "its coordinates"]
    if unnamed:
        notes.append(f"{len(unnamed)} stops have no name in the captions or the data and are labeled by their coordinates.")
    if not music:
        notes.append("The data names no music on their travel posts; the music follows the pace of their travel reels.")
    out = {"name": name, "from": trip["from"].isoformat(), "to": trip["to"].isoformat(), "days_count": len(days),
           "chosen_by": how, "found_by": trip["why"], "album": trip.get("album"), "folder": trip.get("folder"),
           "home": home, "places": places, "route": route, "days": days, "people": people, "clips": clips,
           "music": {"seen": music, "from": "their travel posts" if music else None},
           "items": len(trip["items"]), "geotagged": sum(1 for x in trip["items"] if x["geo"]),
           "everyday_items": len(everyday),
           "others": [{"from": c["from"].isoformat(), "to": c["to"].isoformat(), "why": c["why"], "items": len(c["items"])} for c in others],
           "assumptions": notes}
    _env.write_json("build/trip.json", out)
    print(f"trip: {name}, {out['from']} to {out['to']} ({len(days)} days, {len(trip['items'])} items, {out['geotagged']} geotagged); {how}")
    print("places: " + ", ".join(f"{p['name']} ({p['items']}, by {p['named_by']})" for p in places))
    print("route: " + " -> ".join(r["place"] for r in route))
    print("people: " + ", ".join(f"@{p['handle']} ({p['items']})" for p in people))
    print(f"clips: {len(clips)}; music seen: {music or 'none'}")
    for n in notes:
        print("assumption:", n)
    print("wrote build/trip.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
