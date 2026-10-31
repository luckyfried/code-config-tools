"""What the board builder takes from the trip: the stops (the board's `source`), the distance and bearing between two
of them, and whether the trip carries coordinates.

A stop is one place on one day with the photograph that shows it: {name, place, photo (a file under public/),
aspect, long (px of the source's long side), date ("mon 14 sep"), time ("09:12"), caption (their words), day, lat,
lon, points}. `points` are the photograph's picked points in fractions of it (points.json; storyboard.py points):
near, where they stood, and far, what the photograph looks at.
"""
import math

COMPASS = ["n", "nne", "ne", "ene", "e", "ese", "se", "sse", "s", "ssw", "sw", "wsw", "w", "wnw", "nw", "nnw"]


def km_between(a, b):
    """Distance (km) and bearing (degrees) from stop a to stop b."""
    lat = math.radians((a["lat"] + b["lat"]) / 2)
    dx = (b["lon"] - a["lon"]) * 111.32 * math.cos(lat)
    dy = (b["lat"] - a["lat"]) * 111.2
    return math.hypot(dx, dy), (math.degrees(math.atan2(dx, dy)) + 360) % 360


def compass(deg):
    return COMPASS[round(deg / 22.5) % 16]


def mapped(src):
    return all(s.get("lat") is not None and s.get("lon") is not None for s in src["stops"])
