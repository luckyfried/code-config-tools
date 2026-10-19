#!/usr/bin/env python3
"""Movement 1, research: the year's places. Reads build/library.json and the kit's gazetteer; writes build/places.json
and the map's land shapes (build/public/map/land.json).

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/places.py [--home Lisbon] [--add "Sintra@38.80,-9.38"] [--add Coimbra] [--drop Madrid]
                                [--rename "Vila Nova de Gaia=Porto"] [--reset]

How a row (a post, reel, story or Facebook photo) gets its place, in order:
  1. Their own words: a place named in its caption, its album, its photo folder or a check-in, when that name is in
     the gazetteer (S/data/places.tsv, Natural Earth populated places) and, for a name that is also a common
     English word ("Nice", "Reading"), when it follows "in", "to", "from", "at" and the like or is a hashtag. A name
     several places share (Córdoba in Spain, Mexico and Argentina) is the one nearest the geotags posted within
     30 days, else nearest home. A named place within 80 km of the row's geotag replaces the geotag's town.
  2. The geotag: the most populous gazetteer place near it (within 40 km, nearer wins over bigger), else the
     nearest one within 150 km.
  3. A neighbor in time: a row with neither takes the place of the nearest placed row within two days.
A place named in one caption only, with no geotag, is listed under "mentioned" and left off the map (a caption can
name a place they only miss); --add puts it on. Home is the place in their bio, else the place with the most
months. Visits are runs of rows in one place; the route is the visits in order with the stays at home between trips
left out, so it reads as one journey that starts and ends at home. Places within 2,500 km of home are the region;
the rest are far. Distances are great-circle kilometers.
--home, --add (a gazetteer name, or NAME@lat,lon for a place it lacks), --drop and --rename are the person's word:
they are kept in build/places.args.json and applied on every later run (--reset clears them).

build/places.json: places [{id, name, country, lat, lon, x, y, home, far, rows, posts, stories, reels, photos,
clips, first, last, months, visits, source, words}], visits, route (place ids in order), legs [{from, to, km, far}],
total_km, home, region, far, mentioned, unplaced, rows ({"posts:3": id, ...}), assumptions.
x, y are Web Mercator in world units (0 to 1000 across the world), the map's coordinates.
"""
import argparse
import collections
import datetime as dt
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

DATA = _env.SKILL / "data"
KINDS = ("posts", "reels", "stories", "facebook")
LOCATIVE = {"in", "to", "from", "at", "visiting", "around", "through", "leaving", "near", "via", "toward", "towards",
            "into", "across", "outside", "landed", "arrived", "hello", "goodbye", "bye", "back"}
REGION_KM = 2500
WORLD = 1000.0


def plain(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() else " " for ch in s).lower().split())


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def merc(lat, lon):
    lat = max(-85.0, min(85.0, lat))
    x = (lon + 180.0) / 360.0 * WORLD
    y = (1 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / math.pi) / 2 * WORLD
    return round(x, 3), round(y, 3)


def load_gazetteer():
    rows = []
    for ln in (DATA / "places.tsv").read_text().splitlines():
        if not ln or ln.startswith("#"):
            continue
        f = ln.split("\t")
        rows.append({"name": f[0], "plain": f[1], "country": f[2], "region": f[3], "lat": float(f[4]), "lon": float(f[5]),
                     "pop": int(f[6]), "common": f[7] == "1", "alt": [x for x in (f[8] if len(f) > 8 else "").split("|") if x]})
    names = collections.defaultdict(list)
    for g in rows:
        for n in {g["plain"], *g["alt"]}:
            if len(n) >= 4:
                names[n].append(g)
    return rows, names


class Grid:
    """Gazetteer places bucketed by whole degree, for nearby lookups."""
    def __init__(self, rows):
        self.b = collections.defaultdict(list)
        for g in rows:
            self.b[(math.floor(g["lat"]), math.floor(g["lon"]))].append(g)

    def near(self, lat, lon, radius):
        r = int(radius / 80) + 1
        out = []
        for i in range(-r, r + 1):
            for j in range(-r - 1, r + 2):
                for g in self.b.get((math.floor(lat) + i, (math.floor(lon) + j + 180) % 360 - 180), []):
                    d = km((lat, lon), (g["lat"], g["lon"]))
                    if d <= radius:
                        out.append((d, g))
        return out


def town_of(grid, lat, lon):
    """The town a geotag is in: the most populous place nearby, nearer winning over bigger; else the nearest within 150 km."""
    close = grid.near(lat, lon, 40)
    if close:
        return max(close, key=lambda dg: dg[1]["pop"] / (1 + dg[0] / 8) ** 2)[1], None
    wide = grid.near(lat, lon, 150)
    if wide:
        d, g = min(wide, key=lambda dg: dg[0])
        return g, round(d)
    return None, None


def words_of(text):
    """(plain words, original words) of a text; a hashtag counts as a word and stays marked."""
    out = []
    for tok in re.findall(r"#?[^\W_][\w'’-]*", text or "", re.U):
        tag = tok.startswith("#")
        w = plain(tok.lstrip("#"))
        if w:
            for part in w.split():
                out.append((part, tag, tok.lstrip("#")[:1].isupper()))
    return out


def named_in(text, names, strong=False):
    """Gazetteer names in a text: [(plain name, how it was said)], longest match first, each word used once."""
    ws = words_of(text)
    hits, used = [], set()
    for n in (3, 2, 1):
        for i in range(len(ws) - n + 1):
            if any(k in used for k in range(i, i + n)):
                continue
            cand = " ".join(w for w, _, _ in ws[i:i + n])
            if cand not in names or len(cand) < 4:
                continue
            tag = any(t for _, t, _ in ws[i:i + n])
            cap = ws[i][2]
            loc = i > 0 and ws[i - 1][0] in LOCATIVE
            common = all(g["common"] for g in names[cand])
            if common and not (tag or loc or strong):
                continue
            hits.append((i, cand, "hashtag" if tag else "after '%s'" % ws[i - 1][0] if loc else "capitalized" if cap else "named"))
            used |= set(range(i, i + n))
    return [(c, how) for _, c, how in sorted(hits)]


def date(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", plain(s)).strip("-") or "place"


def land_for(places, out):
    """Land rings that touch the map's area (all places, padded), in world units, as SVG path data."""
    src = json.loads((DATA / "land.json").read_text())
    lats = [p["lat"] for p in places] or [0]
    lons = [p["lon"] for p in places] or [0]
    pad_lat = max(8, (max(lats) - min(lats)) * 0.6)
    pad_lon = max(12, (max(lons) - min(lons)) * 0.6)
    box = (min(lons) - pad_lon, min(lats) - pad_lat, max(lons) + pad_lon, max(lats) + pad_lat)
    paths = []
    for r in src["rings"]:
        b = r["bbox"]
        if b[2] < box[0] or b[0] > box[2] or b[3] < box[1] or b[1] > box[3]:
            continue
        pts = [merc(r["ring"][i + 1], r["ring"][i]) for i in range(0, len(r["ring"]), 2)]
        pts = [p for k, p in enumerate(pts) if k == 0 or (round(p[0], 1), round(p[1], 1)) != (round(pts[k - 1][0], 1), round(pts[k - 1][1], 1))]
        if len(pts) < 4:
            continue
        paths.append("M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "Z")
    bx0, by0 = merc(box[3], box[0])
    bx1, by1 = merc(box[1], box[2])
    _env.write_json(out, {"source": src["source"], "projection": "web mercator, 0 to 1000 across the world",
                          "box": [bx0, by0, bx1, by1], "paths": paths})
    return len(paths)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home")
    ap.add_argument("--add", action="append", default=[])
    ap.add_argument("--drop", action="append", default=[])
    ap.add_argument("--rename", action="append", default=[])
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    saved = {} if a.reset else (_env.read_json("build/places.args.json") or {})
    args = {"home": a.home or saved.get("home"), "add": list(dict.fromkeys(saved.get("add", []) + a.add)),
            "drop": list(dict.fromkeys(saved.get("drop", []) + a.drop)),
            "rename": list(dict.fromkeys(saved.get("rename", []) + a.rename))}
    _env.write_json("build/places.args.json", args)
    gaz, names = load_gazetteer()
    grid = Grid(gaz)
    assumptions = []
    rows = []
    for kind in KINDS:
        for i, r in enumerate(lib.get(kind) or []):
            if r.get("ts"):
                rows.append({"key": f"{kind}:{i}", "kind": kind, "ts": int(r["ts"]), "row": r})
    rows.sort(key=lambda x: x["ts"])

    # geotags first: each row's town
    for x in rows:
        r = x["row"]
        if r.get("lat") is not None and r.get("lon") is not None:
            g, far = town_of(grid, float(r["lat"]), float(r["lon"]))
            x["geo"] = (float(r["lat"]), float(r["lon"]))
            x["town"] = g
            x["town_km"] = far
    tagged = [x for x in rows if x.get("town")]

    def gid(g):
        return f"{g['plain']}|{g['country']}"

    months_at = collections.defaultdict(set)
    for x in tagged:
        months_at[gid(x["town"])].add(date(x["ts"]).month)
    home_g = None
    bio = lib.get("bio") or ""
    for c, how in named_in(bio, names, strong=True):
        cands = names[c]
        if tagged:
            cands = sorted(cands, key=lambda g: min(km((g["lat"], g["lon"]), t["geo"]) for t in tagged))
        else:
            cands = sorted(cands, key=lambda g: -g["pop"])
        home_g = cands[0]
        assumptions.append(f"Home is {home_g['name']}: your bio names it.")
        break
    if args["home"]:
        c = plain(args["home"])
        if names.get(c):
            home_g = max(names[c], key=lambda g: (len(months_at.get(gid(g), ())), g["pop"]))
            assumptions.append(f"Home is {home_g['name']}, as you said.")
    if not home_g and months_at:
        best = max(months_at, key=lambda k: (len(months_at[k]), sum(1 for x in tagged if gid(x["town"]) == k)))
        home_g = next(x["town"] for x in tagged if gid(x["town"]) == best)
        assumptions.append(f"Home is {home_g['name']}: you posted from there in {len(months_at[best])} months, more than anywhere else.")

    # their own words
    def resolve(c, ts):
        cands = names[c]
        if len(cands) == 1:
            return cands[0]
        near = [t for t in tagged if abs(t["ts"] - ts) <= 30 * 86400]
        if near:
            return min(cands, key=lambda g: min(km((g["lat"], g["lon"]), t["geo"]) + abs(t["ts"] - ts) / 86400 for t in near))
        if home_g:
            return min(cands, key=lambda g: km((g["lat"], g["lon"]), (home_g["lat"], home_g["lon"])))
        return max(cands, key=lambda g: g["pop"])

    for x in rows:
        r = x["row"]
        said = []
        for field, strong in (("place", True), ("album", True), ("folder", True), ("caption", False)):
            for c, how in named_in(r.get(field) or "", names, strong=strong):
                said.append((c, f"{field} ({how})" if field != "caption" else f"caption ({how})"))
        if said:
            c, how = said[0]
            g = resolve(c, x["ts"])
            x["said"], x["said_how"] = g, how
    for x in rows:
        g = None
        if x.get("said") and x.get("geo"):
            d = km((x["said"]["lat"], x["said"]["lon"]), x["geo"])
            g = x["said"] if d <= 80 else x["town"]
            x["source"] = "geotag and caption" if g is x["said"] and gid(g) == gid(x["town"]) else \
                "their words over the geotag" if g is x["said"] else "geotag"
        elif x.get("said"):
            g, x["source"] = x["said"], "their words"
        elif x.get("town"):
            g, x["source"] = x["town"], "geotag"
        x["place"] = g

    # a neighbor in time
    placed = [x for x in rows if x["place"]]
    for x in rows:
        if x["place"]:
            continue
        near = min(placed, key=lambda p: abs(p["ts"] - x["ts"]), default=None)
        if near and abs(near["ts"] - x["ts"]) <= 2 * 86400:
            x["place"], x["source"] = near["place"], "posted beside"

    # the person's word: renames, drops, adds
    def find(name):
        c = plain(name)
        return names.get(c) or []
    renames = {}
    for rr in args["rename"]:
        old, _, new = rr.partition("=")
        tgt = find(new)
        if tgt:
            renames[plain(old)] = tgt[0] if len(tgt) == 1 else min(tgt, key=lambda g: km((g["lat"], g["lon"]), (home_g or g)["lat"] and ((home_g or g)["lat"], (home_g or g)["lon"])))
    for x in rows:
        if x["place"] and x["place"]["plain"] in renames:
            x["place"], x["source"] = renames[x["place"]["plain"]], "renamed by you"
    dropped = {plain(d) for d in args["drop"]}
    by = collections.OrderedDict()
    for x in rows:
        if not x["place"]:
            continue
        k = gid(x["place"])
        by.setdefault(k, []).append(x)
    mentioned = []
    adds = {}
    for ad in args["add"]:
        nm, _, at = ad.partition("@")
        if at:
            lat, lon = (float(v) for v in at.split(","))
            g = {"name": nm.strip(), "plain": plain(nm), "country": "", "region": "", "lat": lat, "lon": lon, "pop": 0, "common": False, "alt": []}
        else:
            c = find(nm)
            if not c:
                assumptions.append(f"{nm} is not in the kit's gazetteer; add it as {nm}@lat,lon to put it on the map.")
                continue
            g = next((xs[0]["place"] for k, xs in by.items() if xs[0]["place"]["plain"] == plain(nm)), None) or resolve(plain(nm), rows[len(rows) // 2]["ts"] if rows else 0)
        adds[gid(g)] = g
    keep = collections.OrderedDict()
    for k, xs in by.items():
        g = xs[0]["place"]
        if g["plain"] in dropped:
            assumptions.append(f"{g['name']} is left off, as you said.")
            continue
        has_geo = any(x.get("geo") for x in xs)
        said = [x for x in xs if x.get("said") and gid(x["said"]) == k]
        if not has_geo and len(said) < 2 and k not in adds and not any("album" in (x.get("said_how") or "") or "folder" in (x.get("said_how") or "") for x in said):
            mentioned.append({"name": g["name"], "country": g["country"], "rows": len(xs),
                              "caption": ((said or xs)[0]["row"].get("caption") or "")[:120]})
            for x in xs:
                x["place"] = None
            continue
        keep[k] = xs
    for k, g in adds.items():
        if k not in keep:
            keep[k] = []
            assumptions.append(f"{g['name']} is on the map because you said you were there.")
        for xs in keep[k]:
            pass
    gaz_of = {k: (xs[0]["place"] if xs else adds[k]) for k, xs in keep.items()}
    if home_g and gid(home_g) not in gaz_of:
        gaz_of[gid(home_g)] = home_g
        keep[gid(home_g)] = []

    # ids
    ids, taken = {}, set()
    for k, g in gaz_of.items():
        i = slug(g["name"])
        if i in taken:
            i = slug(f"{g['name']} {g['country']}")
        taken.add(i)
        ids[k] = i
    hk = gid(home_g) if home_g else None

    # visits: runs of one place, in time
    seq = [x for x in rows if x["place"] and gid(x["place"]) in keep]
    visits = []
    for x in seq:
        k = gid(x["place"])
        if visits and visits[-1]["key"] == k:
            visits[-1]["rows"].append(x)
        else:
            visits.append({"key": k, "rows": [x]})
    for k in adds:
        if not keep.get(k):
            visits.append({"key": k, "rows": []})
    out_visits = []
    for v in visits:
        ts = [x["ts"] for x in v["rows"]]
        out_visits.append({"place": ids[v["key"]], "from": date(min(ts)).isoformat() if ts else None,
                           "to": date(max(ts)).isoformat() if ts else None, "rows": len(v["rows"])})
    route = [v["place"] for v in out_visits]
    home_id = ids.get(hk)
    if home_id:
        inner = [p for p in route[1:-1] if p != home_id]
        route = ([route[0]] if route else []) + inner + ([route[-1]] if len(route) > 1 else [])
        route = [p for i, p in enumerate(route) if i == 0 or p != route[i - 1]]
        stays = sum(1 for v in out_visits[1:-1] if v["place"] == home_id)
        if stays:
            assumptions.append(f"The route leaves out the {stays} stay{'s' if stays > 1 else ''} at home between trips, so it reads as one journey.")
    places = []
    hg = home_g
    for k, g in gaz_of.items():
        xs = keep.get(k) or []
        media = [m for x in xs for m in (x["row"].get("media") or [])]
        photos = [m for m in media if Path(m).suffix.lower() not in (".mp4", ".mov", ".m4v")]
        clips = [m for m in media if Path(m).suffix.lower() in (".mp4", ".mov", ".m4v")]
        srcs = collections.Counter(x.get("source") for x in xs)
        dk = round(km((g["lat"], g["lon"]), (hg["lat"], hg["lon"]))) if hg else 0
        words = []
        for x in xs:
            if x.get("said") and gid(x["said"]) == k and x["row"].get("caption"):
                words.append(x["row"]["caption"][:120])
        x0, y0 = merc(g["lat"], g["lon"])
        ts = [x["ts"] for x in xs]
        places.append({
            "id": ids[k], "name": g["name"], "country": g["country"], "region": g["region"], "lat": g["lat"], "lon": g["lon"],
            "x": x0, "y": y0, "home": k == hk, "far": dk > REGION_KM, "km_from_home": dk,
            "rows": len(xs), "posts": sum(1 for x in xs if x["kind"] == "posts"), "stories": sum(1 for x in xs if x["kind"] == "stories"),
            "reels": sum(1 for x in xs if x["kind"] == "reels"), "facebook": sum(1 for x in xs if x["kind"] == "facebook"),
            "photos": photos, "clips": clips,
            "first": date(min(ts)).isoformat() if ts else None, "last": date(max(ts)).isoformat() if ts else None,
            "months": sorted({date(t).month for t in ts}), "visits": sum(1 for v in out_visits if v["place"] == ids[k]),
            "source": ", ".join(s for s, _ in srcs.most_common()) or "added by you", "words": words[:3],
        })
    order = {p: i for i, p in enumerate(dict.fromkeys(route))}
    places.sort(key=lambda p: order.get(p["id"], 999))
    pos = {p["id"]: p for p in places}
    legs = []
    for a_, b_ in zip(route, route[1:]):
        d = km((pos[a_]["lat"], pos[a_]["lon"]), (pos[b_]["lat"], pos[b_]["lon"]))
        legs.append({"from": a_, "to": b_, "km": round(d), "far": pos[a_]["far"] or pos[b_]["far"]})
    for x in rows:
        if x.get("town_km") and x["place"] is x.get("town"):
            assumptions.append(f"A geotag {x['town_km']} km from the nearest town in the gazetteer is counted as {x['town']['name']}.")
            break
    unplaced = sum(1 for x in rows if not x["place"])
    rowmap = {x["key"]: ids[gid(x["place"])] for x in rows if x["place"] and gid(x["place"]) in ids}
    region = [p["id"] for p in places if not p["far"]]
    far = [p["id"] for p in places if p["far"]]
    revisited = [p["name"] for p in places if p["visits"] > 1 and not p["home"]]
    if revisited:
        assumptions.append(f"{', '.join(revisited)} {'was' if len(revisited) == 1 else 'were'} visited more than once; each counts as one place.")
    for m in mentioned:
        assumptions.append(f"{m['name']} is named in {m['rows']} caption{'s' if m['rows'] > 1 else ''} only, with no geotag, so it is not on the map "
                           f"(\"{m['caption'][:60]}\"); say so and it goes on.")
    words_only = [p["name"] for p in places if p["rows"] and "geotag" not in p["source"]]
    if words_only:
        assumptions.append(f"{', '.join(words_only)} carr{'ies' if len(words_only) == 1 else 'y'} no geotag: placed from your captions.")
    if unplaced:
        assumptions.append(f"{unplaced} posts and stories have no geotag and name no place; they are not counted at any place.")
    total = sum(l["km"] for l in legs)
    res = {"year": lib.get("year"), "count": len(places), "places": places, "visits": out_visits, "route": route, "legs": legs,
           "total_km": total, "home": home_id, "region": region, "far": far, "mentioned": mentioned, "unplaced": unplaced,
           "rows": rowmap, "assumptions": assumptions}
    _env.write_json("build/places.json", res)
    n = land_for(places, "build/public/map/land.json")
    print(f"{len(places)} places, {len(out_visits)} visits, route of {len(route)} stops, {total:,} km; home {home_id}; far {far}")
    for p in places:
        print(f"  {p['name']:<14} {p['country']:<10} rows {p['rows']:>3}  visits {p['visits']}  {p['first']} to {p['last']}  "
              f"{p['km_from_home']:>5} km from home  ({p['source']})")
    for m in mentioned:
        print(f"  mentioned only: {m['name']} ({m['rows']} rows)")
    print(f"unplaced rows: {unplaced}; land: {n} shapes -> build/public/map/land.json")
    for x in assumptions:
        print("assumption:", x)
    print("wrote build/places.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
