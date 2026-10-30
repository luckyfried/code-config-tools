#!/usr/bin/env python3
"""Builds the kit's two map data files from Natural Earth (public domain, naturalearthdata.com).

USAGE:
    python3 data/build_data.py NE_DIR

NE_DIR holds ne_50m_land.geojson and ne_10m_populated_places_simple.geojson as published in
github.com/nvkelso/natural-earth-vector (geojson/). Writes, beside this file:
    land.json    every land ring of the 50 m land layer, simplified (Douglas-Peucker, 0.02 degrees) and rounded
                 to 0.01 degree, as flat [lon, lat, lon, lat, ...] lists with their bounding boxes
    places.tsv   the populated places layer: name, plain name, country, region, lat, lon, population, whether
                 the plain name is also a common English word (such a name counts from a caption only after "in",
                 "to", "from" and the like, or as a hashtag), and the place's other plain names (local or
                 longer forms such as "lisboa" or "oaxaca de juarez"), separated by "|"; then, in the same columns,
                 every town of towns.tsv (beside this file) whose plain name the layer does not already hold: the
                 towns a ski, hiking or travel year often reaches that the layer leaves out
The kit reads only these two files; nothing is fetched when it runs.
"""
import json
import math
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMON = set("""
a able about above across after again against age ago air all also always am among an and angel any april arrival art as
at august autumn away baby back bad bag bait bakery ball bank bar base basin bath bay beach bear beauty bed bee bell
belle best big bird black blue boat body bone book born bottle bound box boy bread bridge bright brook brown burn
bush butter cake call calm camp can canal cape capital car care carpet castle cat cave center central chance change
chapel charm cherry chester chief child church circle city clay clear cliff close cloud club coal coast coffee cold
colony columbia comfort common concord content cook copper coral cork corner cotton country court cove cozy crane
creek cross crown crystal cup dale dam dawn day deal dear december deep delight desert diamond dinner dock dog door
dove down dream drive dry dune dust eagle early earth east easy eden edge egg elk elm end energy enterprise eureka
evening every eye fair faith fall false farm fast father february felt field fig fine fire fish five flat flower fog
folk food foot ford forest fort fortune fountain four fox free french friday friend frost fruit fun garden gate gem
giant girl glacier glass glen globe gold golden good grace grain grand grant grape grass gray great green grove guard
gulf hall hamburger happy harbor harbour hard hat haven hay head heart heaven hello help hermit hidden high hill holly
home honey hope horse hot hour house hull hunter ice idle independence iron island ivory jade january joy july june
just justice key kind king kitchen lake lamb land lane large last late laurel lead leaf left lemon liberty light lime
lion little live lodge long lost love low lucky lunch magnolia main male mall man mango manor maple marble march
market marsh may meadow medina melon mercy mesa middle mile mill mine mint mission mobile monday moon morning moss most
mount mountain mouth music narrow nation navy needle new nice night noble north november oak oasis ocean october odd
office oil old olive one open orange orchard oxford pace palm paradise park pass patience peace peach peak pearl
pebble pepper perfect pine pink place plain plate pleasant plenty point pond poplar port post prairie pride prince
progress prospect providence pure quarry queen quiet rain range ranch reading real red reef rest rice rich ridge right
ring rio river road rock rome rose round royal ruby rural rush sable saint sale salt sand sandy saturday savanna sea
second september seven shade shell shore silver six sky slow small snow soda south spa spring spruce square star
station steel stone story strand street success sugar summer summit sun sunday sunny sunrise sunset superior sweet
table tea temple ten the thursday tide tiger timber today top tower town trail tree trinity triumph tuesday union
unity university valley vernon victoria victory view villa village vine vista wall war warm water wave way wednesday
well wells west white wild willow wind window winter wolf wood worth yard year yellow york young zion
""".split())


def plain(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    return " ".join("".join(ch for ch in s if ch.isalnum() or ch in " -'").lower().replace("-", " ").split())


def dp(pts, tol):
    """Douglas-Peucker on a list of (x, y)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1e-12
        best, at = -1, -1
        for k in range(i + 1, j):
            x, y = pts[k]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / n
            if d > best:
                best, at = d, k
        if best > tol:
            keep[at] = True
            stack += [(i, at), (at, j)]
    return [p for p, k in zip(pts, keep) if k]


def town_rows(seen):
    """towns.tsv as places.tsv rows, leaving out every town whose plain name is in `seen`."""
    rows = []
    for ln in (HERE / "towns.tsv").read_text().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, country, region, lat, lon, pop, alt = (ln.split("\t") + [""] * 7)[:7]
        pl = plain(name)
        if pl in seen:
            continue
        rows.append("\t".join([name, pl, country, region, f"{float(lat):.4f}", f"{float(lon):.4f}", str(int(pop or 0)),
                               "1" if pl in COMMON else "0", "|".join(sorted({plain(v) for v in alt.split("|") if v}))]))
    return rows


def main():
    ne = Path(sys.argv[1])
    land = json.loads((ne / "ne_50m_land.geojson").read_text())
    rings = []
    for f in land["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            ring = poly[0]
            pts = [(round(x, 4), round(y, 4)) for x, y in ring]
            far = max(range(len(pts)), key=lambda k: math.dist(pts[0], pts[k]))
            s = dp(pts[:far + 1], 0.02)[:-1] + dp(pts[far:], 0.02)
            s = [(round(x, 2), round(y, 2)) for x, y in s]
            s = [p for i, p in enumerate(s) if i == 0 or p != s[i - 1]]
            if len(s) < 4:
                continue
            xs, ys = [p[0] for p in s], [p[1] for p in s]
            rings.append({"bbox": [min(xs), min(ys), max(xs), max(ys)], "ring": [v for p in s for v in p]})
    (HERE / "land.json").write_text(json.dumps({
        "source": "Natural Earth 1:50m land (public domain), simplified to 0.02 degrees",
        "rings": rings}, separators=(",", ":")))
    pp = json.loads((ne / "ne_10m_populated_places_simple.geojson").read_text())
    rows = ["# Natural Earth 1:10m populated places (public domain). name\tplain\tcountry\tregion\tlat\tlon\tpop\tcommon\talt"]
    for f in pp["features"]:
        p = f["properties"]
        name = (p.get("name") or "").replace("‎", "").replace("‏", "").strip()
        if not name:
            continue
        pl = plain(p.get("nameascii") or name)
        alt = sorted({plain(v) for v in (name, p.get("namepar"), p.get("namealt"))
                      if v and len(plain(v)) >= 4 and plain(v) != pl and "?" not in v})
        rows.append("\t".join([name, pl, p.get("adm0name") or "", p.get("adm1name") or "", f"{p['latitude']:.4f}",
                               f"{p['longitude']:.4f}", str(int(p.get("pop_max") or 0)), "1" if pl in COMMON else "0",
                               "|".join(alt)]))
    rows += town_rows({r.split("\t")[1] for r in rows[1:]})
    (HERE / "places.tsv").write_text("\n".join(rows) + "\n")
    print(f"land.json: {len(rings)} rings; places.tsv: {len(rows) - 1} places")


if __name__ == "__main__":
    main()
