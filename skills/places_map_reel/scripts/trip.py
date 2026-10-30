"""The year as the films tell it, computed from build/places.json and the graded photographs alone.

Trip(places, photos) holds:
  stops      one per stop of the route, in date order: {i, place, name, lat, lon, from, to, month, n (which visit to
             its place this is, 1 the first), leg (great-circle km from the stop before, which spaces the points the
             route is drawn through; None at the first stop), rows}
  count      the places of the year (a place visited twice counts once), the one number the film states
  home       home's id; far: the places farther from home than REGION_KM, nearest first, which the camera leaps to
  mapped     every place has coordinates (the film is drawn on the map)
  photos     photo(place, n, k): the k-th photograph of visit n to the place, the first the visit's own print
"""
import datetime as dt
import math

EARTH_KM = 6371.0
REGION_KM = 2500
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def haversine(a, b):
    """Great-circle km between two (lat, lon) points."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return EARTH_KM * 2 * math.asin(min(1.0, math.sqrt(h)))


def has_xy(p):
    return p.get("lat") is not None and p.get("lon") is not None


class Trip:
    def __init__(self, places, photos=()):
        self.year = places.get("year")
        self.places = {p["id"]: {"id": p["id"], "name": p["name"], "lat": p.get("lat"), "lon": p.get("lon")} for p in places["places"]}
        self.home = places.get("home") or places["places"][0]["id"]
        # they named their home themselves: only then does the film call a place home
        self.home_said = bool(places.get("home") and places.get("home_said"))
        self.mapped = all(has_xy(p) for p in self.places.values())
        visits = places.get("route_visits") or [{"place": k} for k in places["route"]]
        home = self.places[self.home]
        self.stops, seen = [], {}
        for i, v in enumerate(visits):
            p = self.places[v["place"]]
            seen[p["id"]] = seen.get(p["id"], 0) + 1
            leg = None
            if i and self.mapped:
                q = self.places[visits[i - 1]["place"]]
                leg = round(haversine((q["lat"], q["lon"]), (p["lat"], p["lon"])))
            a = dt.date.fromisoformat(v["from"]) if v.get("from") else None
            self.stops.append({"i": i, "place": p["id"], "name": p["name"], "lat": p["lat"], "lon": p["lon"],
                               "from": v.get("from"), "to": v.get("to"), "month": MONTHS[a.month - 1] if a else None,
                               "n": seen[p["id"]], "leg": leg, "rows": v.get("rows", 0)})
        self.count = len({s["place"] for s in self.stops})
        self.km_from_home = {k: round(haversine((home["lat"], home["lon"]), (p["lat"], p["lon"]))) for k, p in self.places.items()} if self.mapped else {}
        self.far = sorted((k for k, d in self.km_from_home.items() if d > REGION_KM), key=lambda k: self.km_from_home[k])
        self._photos = {}
        for ph in photos:
            self._photos.setdefault((ph["place"], ph["n"]), []).append(ph)
        for v in self._photos.values():
            v.sort(key=lambda ph: ph["k"])

    def photo(self, place, n=1, k=1):
        """The k-th photograph of visit n to the place; a visit with fewer falls back to the place's first visit."""
        got = self._photos.get((place, n)) or self._photos.get((place, 1)) or []
        return got[min(k, len(got)) - 1] if got else None
