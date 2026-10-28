"""Sky Tonight: writes the planetarium page for one place into out/sky-tonight/.

Run from the project folder, the one holding sky-tonight.inputs.json:

    python3 <agent-apps root>/sky-tonight/scripts/run.py

It checks every key, copies the page, the star catalog, and the textures into
out/sky-tonight/, writes theme.css and config.js from the inputs, prints how
high Polaris stands over the place at the chosen time (it matches the
latitude), and prints the line that serves the folder. Standard library only;
two runs on the same inputs write the same bytes.
"""

import json
import math
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP = "sky-tonight"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"

CHOICES = {
    "horizon": ("hill", "sea", "city", "flat"),
    "labels": ("names", "bayer", "none"),
    "constellations": ("lines", "art", "none"),
}
KEYS = ("place", "lat", "lon", "timezone", "when", "horizon", "labels", "constellations", "theme")
WHEN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$")


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def zone(name):
    """The zone for an IANA name, None when the name is unknown, and False when this machine has no zone data."""
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:
        return False
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        try:
            ZoneInfo("UTC")
        except ZoneInfoNotFoundError:
            return False
        return None


def check(inputs):
    problems = []
    name = f"{APP}.inputs.json"
    if not isinstance(inputs, dict):
        fail([f"{name} must hold one JSON object with the keys inputs.example.json shows."])
    for key in KEYS:
        if key not in inputs:
            problems.append(f'{name} is missing the key "{key}".')
    for key in inputs:
        if key not in KEYS and not key.startswith("_"):
            problems.append(f'{name} has the key "{key}", which Sky Tonight does not use.')
    if "place" in inputs and (not isinstance(inputs["place"], str) or not inputs["place"].strip()):
        problems.append(f'{name}: "place" must be the place\'s name, like "Flagstaff, Arizona".')
    if "lat" in inputs and not (is_number(inputs["lat"]) and -90 <= inputs["lat"] <= 90):
        problems.append(f'{name}: "lat" must be a number from -90 to 90.')
    if "lon" in inputs and not (is_number(inputs["lon"]) and -180 <= inputs["lon"] <= 180):
        problems.append(f'{name}: "lon" must be a number from -180 to 180.')
    if "timezone" in inputs:
        tz = inputs["timezone"]
        if not isinstance(tz, str) or zone(tz) is None:
            problems.append(f'{name}: "timezone" must be a time zone name like "America/Phoenix" or "Europe/London".')
    if "when" in inputs:
        when = inputs["when"]
        if not isinstance(when, str) or (when != "now" and not WHEN.match(when)):
            problems.append(f'{name}: "when" must be "now" or a local date and time like "2027-03-12T20:45".')
    for key, allowed in CHOICES.items():
        if key in inputs and inputs[key] not in allowed:
            listed = ", ".join(f'"{a}"' for a in allowed)
            problems.append(f'{name}: "{key}" must be one of {listed}.')
    if "theme" in inputs:
        themes = sorted(p.stem for p in THEMES.glob("*.css"))
        if not isinstance(inputs["theme"], str) or inputs["theme"] not in themes:
            listed = ", ".join(f'"{t}"' for t in themes)
            problems.append(f'{name}: "theme" must name one of the themes: {listed}.')
    if problems:
        fail(problems)


def moment(inputs):
    """The chosen moment in UTC, and how it reads locally."""
    tz = zone(inputs["timezone"])
    if inputs["when"] == "now":
        now = datetime.now(timezone.utc)
        local = now.astimezone(tz) if tz else now
        return now, local.strftime("%Y-%m-%d %H:%M")
    y, mo, d, h, mi = (int(x) for x in WHEN.match(inputs["when"]).groups())
    if tz:
        utc = datetime(y, mo, d, h, mi, tzinfo=tz).astimezone(timezone.utc)
    else:
        utc = datetime(y, mo, d, h, mi, tzinfo=timezone.utc) - timedelta(hours=inputs["lon"] / 15)
    return utc, inputs["when"].replace("T", " ")


def polaris_altitude(utc, lat, lon):
    """Polaris (HIP 11767) above the horizon, in degrees: J2000 place precessed to the date, then local sidereal time."""
    jd = utc.timestamp() / 86400 + 2440587.5
    t = (jd - 2451545.0) / 36525
    ra0 = math.radians(37.95456067)
    dec0 = math.radians(89.26410897)
    arc = math.pi / (180 * 3600)
    zeta = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) * arc
    z = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) * arc
    theta = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) * arc
    a = math.cos(dec0) * math.sin(ra0 + zeta)
    b = math.cos(theta) * math.cos(dec0) * math.cos(ra0 + zeta) - math.sin(theta) * math.sin(dec0)
    c = math.sin(theta) * math.cos(dec0) * math.cos(ra0 + zeta) + math.cos(theta) * math.sin(dec0)
    ra = math.atan2(a, b) + z
    dec = math.asin(c)
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t - t ** 3 / 38710000
    hour_angle = math.radians((gmst + lon) % 360) - ra
    phi = math.radians(lat)
    alt = math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(hour_angle))
    return math.degrees(alt)


def main():
    project = Path.cwd()
    source = project / f"{APP}.inputs.json"
    if not source.is_file():
        fail([f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{APP}.inputs.json is not readable JSON: {error}."])
    check(inputs)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    badge = APP_DIR / "badge.js"
    if badge.is_file():
        shutil.copyfile(badge, out / "badge.js")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    config = {key: inputs[key] for key in KEYS}
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config)};\n", encoding="utf-8")

    utc, local = moment(inputs)
    polaris = polaris_altitude(utc, inputs["lat"], inputs["lon"])
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Polaris stands {polaris:.2f} degrees above the north horizon at {inputs['place']} on {local}; the latitude is {inputs['lat']:.2f}.")
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
