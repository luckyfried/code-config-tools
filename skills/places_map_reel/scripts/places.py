#!/usr/bin/env python3
"""Movement 1, research: the year's places. Reads library.json and the kit's gazetteer; writes places.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/places.py [--home Lisbon] [--add "Sintra@38.80,-9.38"] [--add Coimbra] [--drop Madrid]
                                [--rename "Vila Nova de Gaia=Porto"] [--reset]

How a row (a post, reel, story or Facebook photo) gets its place, in order:
  1. Their own words: a place named in its caption, its album, its photo folder or file name, or a check-in, when that name is in
     the gazetteer (S/data/places.tsv, Natural Earth populated places) and, for a name that is also a common
     English word ("Nice", "Reading"), when it follows "in", "to", "from", "at" and the like or is a hashtag; a name of
     three letters ("Fes", "Ulm") counts as a hashtag, capitalized after one of those words, or as the whole text. A name
     several places share (Córdoba in Spain, Mexico and Argentina) is the one nearest the geotags posted within
     30 days, else nearest home. A named place within 80 km of the row's geotag replaces the geotag's town. A
     location the post carries that the gazetteer lacks (a village, a lake) is a place of its own at the row's
     geotag when the geotag's town is more than 15 km away; nearer, it is a venue inside that town.
  2. The geotag: the most populous gazetteer place near it (within 40 km, nearer wins over bigger), else the
     nearest one within 150 km.
  3. A neighbor in time: a row with neither takes the place of the nearest placed row within two days.
A place named in one caption only, with no geotag, is listed under "mentioned" and left off the map (a caption can
name a place they only miss); a check-in, an album, a folder or a file name says they were there and puts it on. A
check-in or file name the gazetteer lacks, on a row with no geotag, is listed in the assumptions with the --add that
puts it on; --add NAME@lat,lon makes the name one their rows can say, so the rows that name it are its photographs.
The pair is checked: the assumptions say the nearest town it lands by and how far from home, and a pair with latitude
and longitude swapped, or one far from home and from every other place of the route, is refused. Home is the place in their bio (or --home), else the place with the
most months; home_said records which, and only a home they named is ever called home on screen. Visits are runs of
rows in one place; the route is the visits in order with the stays at home between trips left out, so it reads as one
journey that starts and ends at home. Places within 2,500 km of home are the region;
the rest are far. Distances are great-circle kilometers.
A place keeps the name they spell it by in their own words ("Fes" where the gazetteer has "Fez"), on the map and in
every caption.
--home, --add (a gazetteer name, or NAME@lat,lon for a place it lacks), --drop and --rename are the person's word:
they are kept in places.args.json and applied on every later run (--reset clears them). --rename "Old=New" shows the
place as New, spelled as typed ("Fez=Fes"); the place moves only when New is another place in the gazetteer
("Vila Nova de Gaia=Porto").

places.json: places [{id, name, country, lat, lon, x, y, home, far, rows, posts, stories, reels, photos,
clips, first, last, months, visits, source, words}], visits, route (place ids in order), route_visits (the visit
behind each stop of the route, with its dates), legs [{from, to, far}],
home, home_said, region, far, mentioned, unplaced, rows ({"posts:3": id, ...}), assumptions.
x, y are Web Mercator in world units (0 to 1000 across the world), the map's coordinates.
"""
import argparse
import collections
import datetime as dt
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
VENUE_KM = 15
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
            if len(n) >= 3:
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


def coords(name, at):
    """The pair NAME@lat,lon names, refusing one that is not a latitude and a longitude."""
    try:
        lat, lon = (float(v) for v in at.split(","))
    except ValueError:
        sys.exit(f"--add \"{name}@{at}\": write the place as {name}@lat,lon, two numbers, latitude first.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        sys.exit(f"--add \"{name}@{at}\": {lat:g} is not a latitude or {lon:g} not a longitude; latitude comes first.")
    return lat, lon


def where_added(grid, g, home, others):
    """Where a place added by its coordinates lands, said plainly for the agent to check against what it knows of the
    place: the nearest town the kit knows and its country, and whether it stands in the route's region. A pair that
    lands outside the region while its swapped pair lands inside it is refused, latitude and longitude having been
    swapped; a pair nowhere near home or any other place of the route is refused too, since a far trip still has a
    place of the route within REGION_KM of it."""
    near = grid.near(g["lat"], g["lon"], 150)
    town = min(near, key=lambda dg: dg[0]) if near else None
    at = f"{g['name']} ({g['lat']:g},{g['lon']:g})"
    said = f"{at} lands {round(town[0])} km from {town[1]['name']}, {town[1]['country']}" if town else f"{at} lands more than 150 km from any town the kit knows"
    if not home:
        return said + "."
    d = km((g["lat"], g["lon"]), (home["lat"], home["lon"]))
    if d <= REGION_KM:
        return said + f", {round(d):,} km from home, inside the route's region."
    if -90 <= g["lon"] <= 90 and km((g["lon"], g["lat"]), (home["lat"], home["lon"])) <= REGION_KM:
        sys.exit(f"{said}, {round(d):,} km from home; {g['lon']:g},{g['lat']:g} lands inside the route's region: latitude and "
                 f"longitude look swapped. Add it as \"{g['name']}@{g['lon']:g},{g['lat']:g}\" if that is where it is.")
    if not any(km((g["lat"], g["lon"]), (o["lat"], o["lon"])) <= REGION_KM for o in others):
        sys.exit(f"{said}, {round(d):,} km from home and from every other place of the route. Check the coordinates.")
    return said + f", {round(d):,} km from home: a far trip, drawn on its own map."


def words_of(text):
    """The words of a text: (plain word, hashtag, capitalized, (start, end) of the word as written in the text); a
    hashtag counts as a word and stays marked."""
    out = []
    for m in re.finditer(r"#?[^\W_][\w'’-]*", text or "", re.U):
        tok = m.group(0)
        tag = tok.startswith("#")
        a = m.start() + tag
        parts = plain(tok[tag:]).split()
        runs = [(a + r.start(), a + r.end()) for r in re.finditer(r"[^\W_]+", tok[tag:], re.U)]
        if len(runs) != len(parts):
            runs = [(a, m.end())] * len(parts)
        for part, span in zip(parts, runs):
            out.append((part, tag, tok[tag:tag + 1].isupper(), span))
    return out


def named_in(text, names, strong=False):
    """Gazetteer names in a text: [(plain name, how it was said, the name as it is spelled in the text)], longest match
    first, each word used once."""
    ws = words_of(text)
    hits, used = [], set()
    for n in (3, 2, 1):
        for i in range(len(ws) - n + 1):
            if any(k in used for k in range(i, i + n)):
                continue
            cand = " ".join(w for w, _, _, _ in ws[i:i + n])
            if cand not in names:
                continue
            tag = any(t for _, t, _, _ in ws[i:i + n])
            cap = ws[i][2]
            loc = i > 0 and ws[i - 1][0] in LOCATIVE
            common = all(g["common"] for g in names[cand])
            if common and not (tag or loc or strong):
                continue
            if len(cand) == 3 and not (tag or (loc and cap) or len(ws) == 1):
                continue
            how = "hashtag" if tag else "after '%s'" % ws[i - 1][0] if loc else "capitalized" if cap else "named"
            hits.append((i, cand, how, text[ws[i][3][0]:ws[i + n - 1][3][1]]))
            used |= set(range(i, i + n))
    return [(c, how, spelt) for _, c, how, spelt in sorted(hits)]


def date(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", plain(s)).strip("-") or "place"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home")
    ap.add_argument("--add", action="append", default=[])
    ap.add_argument("--drop", action="append", default=[])
    ap.add_argument("--rename", action="append", default=[])
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    _env.enter_run()
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    saved = {} if a.reset else (_env.read_json("places.args.json") or {})
    args = {"home": a.home or saved.get("home"), "add": list(dict.fromkeys(saved.get("add", []) + a.add)),
            "drop": list(dict.fromkeys(saved.get("drop", []) + a.drop)),
            "rename": list(dict.fromkeys(saved.get("rename", []) + a.rename))}
    _env.write_json("places.args.json", args)
    gaz, names = load_gazetteer()
    at_coords = {}
    for ad in args["add"]:
        nm, _, at = ad.partition("@")
        if at:
            lat, lon = coords(nm, at)
            g = {"name": nm.strip(), "plain": plain(nm), "country": "", "region": "", "lat": lat, "lon": lon, "pop": 0,
                 "common": False, "alt": []}
            names[g["plain"]].append(g)
            at_coords[ad] = g
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
    # home_said: they named it themselves (their bio, or --home from their own words); the film says "home" only then
    home_g, home_said = None, False
    bio = lib.get("bio") or ""
    for c, how, _ in named_in(bio, names, strong=True):
        cands = names[c]
        if tagged:
            cands = sorted(cands, key=lambda g: min(km((g["lat"], g["lon"]), t["geo"]) for t in tagged))
        else:
            cands = sorted(cands, key=lambda g: -g["pop"])
        home_g, home_said = cands[0], True
        assumptions.append(f"Home is {home_g['name']}: your bio names it.")
        break
    if args["home"]:
        c = plain(args["home"])
        if names.get(c):
            home_g = max(names[c], key=lambda g: (len(months_at.get(gid(g), ())), g["pop"]))
            home_said = True
            assumptions.append(f"Home is {home_g['name']}, as you said.")
    if not home_g and months_at:
        best = max(months_at, key=lambda k: (len(months_at[k]), sum(1 for x in tagged if gid(x["town"]) == k)))
        home_g = next(x["town"] for x in tagged if gid(x["town"]) == best)
        assumptions.append(f"The map measures distance from {home_g['name']}: you posted from there in {len(months_at[best])} months, "
                           "more than anywhere else. The film never calls it home, as you did not say so.")

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
        # a location reads as "place, region, country": the place is its first part
        for field, strong in (("place", True), ("album", True), ("folder", True), ("file", True), ("caption", False)):
            text = (r.get(field) or "").split(",")[0] if field == "place" else r.get(field) or ""
            for c, how, spelt in named_in(text, names, strong=strong):
                said.append((c, f"{field} ({how})" if field != "caption" else f"caption ({how})", spelt))
        if said:
            c, how, spelt = said[0]
            g = resolve(c, x["ts"])
            x["said"], x["said_how"], x["spelt"] = g, how, spelt
        elif r.get("place") and x.get("geo") and (not x["town"] or km((x["town"]["lat"], x["town"]["lon"]), x["geo"]) > VENUE_KM):
            # a location the gazetteer lacks (a village, a lake) names its own place at its geotag; nearer a town than
            # VENUE_KM it is taken for a venue inside that town
            nm = r["place"].split(",")[0].strip()
            town = x["town"] or {}
            x["said"] = {"name": nm, "plain": plain(nm), "country": town.get("country", ""), "region": town.get("region", ""),
                         "lat": x["geo"][0], "lon": x["geo"][1], "pop": 0, "common": False, "alt": []}
            x["said_how"] = "place (its own location)"
        elif not x.get("geo") and (r.get("place") or r.get("file")):
            x["unknown"] = r["place"].split(",")[0].strip() if r.get("place") else r["file"]
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
    # a rename shows the place under the new name as they typed it; the place moves only when that name is another
    # place in the gazetteer, else it keeps its coordinates
    renames = {}
    for rr in args["rename"]:
        old, _, new = rr.partition("=")
        tgt = find(new)
        to = (tgt[0] if len(tgt) == 1 else min(tgt, key=lambda g: km((g["lat"], g["lon"]), ((home_g or g)["lat"], (home_g or g)["lon"])))) if tgt else None
        renames[plain(old)] = (to, new.strip())
    named = {}
    for x in rows:
        g = x["place"]
        if not g:
            continue
        own = plain(x["spelt"]) if x.get("spelt") and x.get("said") is g else None
        hit = next((renames[n] for n in (g["plain"], *g["alt"], own) if n in renames), None)
        if hit:
            to, name = hit
            if to and gid(to) != gid(g):
                x["place"] = to
            x["source"] = "renamed by you"
            named[gid(x["place"])] = name
    # the name as they spell it in their own words, the one they use most, wins over the gazetteer's
    spelt = collections.defaultdict(collections.Counter)
    for x in rows:
        if x.get("spelt") and x["place"] and x.get("said") is x["place"]:
            spelt[gid(x["place"])][x["spelt"]] += 1
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
            g = at_coords[ad]
        else:
            c = find(nm)
            if not c:
                assumptions.append(f"{nm} is not in the kit's gazetteer; add it as {nm}@lat,lon to put it on the map.")
                continue
            g = next((xs[0]["place"] for k, xs in by.items() if xs[0]["place"]["plain"] == plain(nm)), None) or resolve(plain(nm), rows[len(rows) // 2]["ts"] if rows else 0)
            if plain(nm) != plain(g["name"]):
                named.setdefault(gid(g), nm.strip())
        adds[gid(g)] = g

    def name_of(k, g):
        """The place's name on the map and in every caption: their rename, else their own spelling, else the gazetteer's."""
        if k in named:
            return named[k]
        said = spelt.get(k)
        if not said:
            return g["name"]
        votes = collections.Counter()
        for v, n in said.items():
            votes[plain(v)] += n
        top = max(votes, key=votes.get)
        if top == plain(g["name"]):
            return g["name"]
        forms = [v for v in said if plain(v) == top]
        v = max(forms, key=lambda v: (not v.islower(), said[v]))
        return " ".join(w[:1].upper() + w[1:] for w in v.split()) if v.islower() else v

    keep = collections.OrderedDict()
    for k, xs in by.items():
        g = xs[0]["place"]
        if g["plain"] in dropped or plain(name_of(k, g)) in dropped:
            assumptions.append(f"{name_of(k, g)} is left off, as you said.")
            continue
        has_geo = any(x.get("geo") for x in xs)
        said = [x for x in xs if x.get("said") and gid(x["said"]) == k]
        if not has_geo and len(said) < 2 and k not in adds and all((x.get("said_how") or "").startswith("caption") for x in said):
            mentioned.append({"name": g["name"], "country": g["country"], "rows": len(xs),
                              "caption": ((said or xs)[0]["row"].get("caption") or "")[:120]})
            for x in xs:
                x["place"] = None
            continue
        keep[k] = xs
    for k, g in adds.items():
        if k not in keep:
            keep[k] = []
            assumptions.append(f"{name_of(k, g)} is on the map because you said you were there.")
    gaz_of = {k: (xs[0]["place"] if xs else adds[k]) for k, xs in keep.items()}
    # a home is a stop only where they posted from it; with none there it still measures the distances
    if home_g and gid(home_g) not in gaz_of:
        assumptions.append(f"{home_g['name']} is not a stop on the map: you posted nothing from there.")
    gaz_of = {k: dict(g, name=name_of(k, g)) for k, g in gaz_of.items()}

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
    home_id = ids.get(hk)
    stops = list(out_visits)
    if home_id and len(stops) > 2:
        stops = [stops[0]] + [v for v in stops[1:-1] if v["place"] != home_id] + [stops[-1]]
    route_visits = []
    for v in stops:
        if route_visits and route_visits[-1]["place"] == v["place"]:
            route_visits[-1] = dict(route_visits[-1], to=v["to"] or route_visits[-1]["to"], rows=route_visits[-1]["rows"] + v["rows"])
        else:
            route_visits.append(dict(v))
    route = [v["place"] for v in route_visits]
    if home_id:
        stays = sum(1 for v in out_visits[1:-1] if v["place"] == home_id)
        if stays:
            where = "at home" if home_said else f"in {home_g['name']}"
            assumptions.append(f"The route leaves out the {stays} stay{'s' if stays > 1 else ''} {where} between trips, so it reads as one journey.")
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
            "x": x0, "y": y0, "home": k == hk, "far": dk > REGION_KM,
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
        legs.append({"from": a_, "to": b_, "far": pos[a_]["far"] or pos[b_]["far"]})
    for x in rows:
        if x.get("town_km") and x["place"] is x.get("town"):
            assumptions.append(f"A geotag {x['town_km']} km from the nearest town in the gazetteer is counted as {x['town']['name']}.")
            break
    for ad, g in at_coords.items():
        if gid(g) in ids:
            assumptions.append(where_added(grid, g, hg, [o for k, o in gaz_of.items() if k != gid(g)]))
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
        assumptions.append(f"{', '.join(words_only)} carr{'ies' if len(words_only) == 1 else 'y'} no geotag: placed from your own words.")
    unknown = collections.Counter(x["unknown"] for x in rows if not x["place"] and x.get("unknown"))
    for nm, n in unknown.items():
        assumptions.append(f"{nm} ({n} row{'s' if n > 1 else ''}) is not in the kit's gazetteer and has no geotag: "
                           f"places.py --add \"{nm}@lat,lon\" puts it on the map.")
    if unplaced:
        assumptions.append(f"{unplaced} posts and stories have no geotag and name no place the kit knows; they are not counted at any place.")
    res = {"year": lib.get("year"), "count": len(places), "places": places, "visits": out_visits, "route": route, "route_visits": route_visits, "legs": legs,
           "home": home_id, "home_said": home_said, "region": region, "far": far, "mentioned": mentioned, "unplaced": unplaced,
           "rows": rowmap, "assumptions": assumptions}
    _env.write_json("places.json", res)
    print(f"{len(places)} places, {len(out_visits)} visits, route of {len(route)} stops; home {home_id}; far {far}")
    for p in places:
        print(f"  {p['name']:<14} {p['country']:<10} rows {p['rows']:>3}  visits {p['visits']}  {p['first']} to {p['last']}  "
              f"({p['source']})")
    for m in mentioned:
        print(f"  mentioned only: {m['name']} ({m['rows']} rows)")
    print(f"unplaced rows: {unplaced}")
    for x in assumptions:
        print("assumption:", x)
    print("wrote places.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
