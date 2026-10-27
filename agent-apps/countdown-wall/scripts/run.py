"""Builds the Countdown Wall page from the events in countdown-wall.inputs.json.

Run it from the project folder:

    python3 <agent-apps root>/countdown-wall/scripts/run.py

It reads countdown-wall.inputs.json from the current folder, checks every key, and writes out/countdown-wall/:
the page, theme.css from the chosen theme, config.js with the inputs, data.js with every event ready to draw,
and each event image under media/. Two runs on the same inputs write the same bytes.
"""

import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

SLUG = "countdown-wall"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"
SAMPLES = APP / "assets" / "samples"
BADGE = APP / "badge.js"
INPUTS = f"{SLUG}.inputs.json"

TOP_KEYS = {"title", "theme", "hourFormat", "events"}
EVENT_KEYS = {"id", "title", "date", "start", "color", "icon", "image", "repeat"}
REQUIRED_EVENT_KEYS = ("id", "title", "date")

# The colors an event takes by name, and in turn when it names none.
PALETTE = {
    "tangerine": "#ff5a24",
    "rose": "#ff3d7f",
    "gold": "#ffc21a",
    "violet": "#8b5cf6",
    "sky": "#38b6ff",
    "cobalt": "#3d63ff",
    "coral": "#ff6f61",
    "teal": "#14c4ae",
    "lime": "#9be22d",
    "amber": "#ff9f1c",
    "sage": "#8fbf8a",
    "magenta": "#e040fb",
}

ICONS = (
    "baby briefcase cake calendar flag gift graduation-cap guitar heart house key-round leaf mountain music "
    "party-popper pen-line plane rocket sparkles sprout star sun tent ticket trophy"
).split()

IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg"}
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
WHEN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?)?$")


def fail(problems):
    for line in problems:
        print(line)
    sys.exit(2)


def valid_when(text):
    if not isinstance(text, str) or not WHEN.match(text):
        return False
    try:
        if "T" in text:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            date.fromisoformat(text)
    except ValueError:
        return False
    return True


def hex_color(value):
    if value in PALETTE:
        return PALETTE[value]
    if value.startswith("#") and len(value) == 4:
        value = "#" + "".join(c * 2 for c in value[1:])
    return value.lower()


def find_image(name, project):
    """An image path is read beside the inputs first, then among this app's sample pictures."""
    for folder in (project, SAMPLES):
        path = (folder / name).resolve()
        if path.is_file():
            return path
    return None


def check(inputs, project):
    problems = []
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object."]
    for key in sorted(set(inputs) - TOP_KEYS - {"_notes"}):
        problems.append(f'{INPUTS} has the key "{key}", which this app does not use.')
    for key in ("theme", "hourFormat", "events"):
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')

    if "title" in inputs and (not isinstance(inputs["title"], str) or not inputs["title"].strip()):
        problems.append(f'{INPUTS}: "title" must be text.')
    if "hourFormat" in inputs and inputs["hourFormat"] not in (12, 24):
        problems.append(f'{INPUTS}: "hourFormat" must be 12 or 24.')
    if "theme" in inputs:
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'{INPUTS}: "theme" must be one of {", ".join(names)}.')

    events = inputs.get("events")
    if "events" in inputs and not isinstance(events, list):
        problems.append(f'{INPUTS}: "events" must be a list.')
        events = []
    seen = set()
    for i, ev in enumerate(events or []):
        where = f"{INPUTS}: events[{i}]"
        if not isinstance(ev, dict):
            problems.append(f"{where} must be an object.")
            continue
        for key in REQUIRED_EVENT_KEYS:
            if key not in ev:
                problems.append(f'{where} is missing the key "{key}".')
        for key in sorted(set(ev) - EVENT_KEYS):
            problems.append(f'{where} has the key "{key}", which this app does not use.')
        if "id" in ev:
            if not isinstance(ev["id"], str) or not ID.match(ev["id"]):
                problems.append(f'{where}: "id" must be lowercase letters, digits, and dashes, like "kyoto-trip".')
            elif ev["id"] in seen:
                problems.append(f'{where}: the id "{ev["id"]}" is used twice.')
            else:
                seen.add(ev["id"])
        if "title" in ev and (not isinstance(ev["title"], str) or not ev["title"].strip()):
            problems.append(f'{where}: "title" must be text.')
        for key in ("date", "start"):
            if key in ev and not valid_when(ev[key]):
                problems.append(f'{where}: "{key}" must be a date like 2026-12-25 or a date and time like 2026-12-25T19:30.')
        if "color" in ev:
            c = ev["color"]
            if not isinstance(c, str) or not (c in PALETTE or HEX.match(c)):
                problems.append(f'{where}: "color" must be a hex color like "#ff5a24" or one of {", ".join(PALETTE)}.')
        if "icon" in ev and ev["icon"] not in ICONS:
            problems.append(f'{where}: "icon" must be one of {", ".join(ICONS)}.')
        if "repeat" in ev and ev["repeat"] != "yearly":
            problems.append(f'{where}: "repeat" can only be "yearly".')
        if "image" in ev:
            img = ev["image"]
            if not isinstance(img, str) or Path(img).suffix.lower() not in IMAGE_TYPES:
                problems.append(f'{where}: "image" must be a picture file ({", ".join(sorted(IMAGE_TYPES))}).')
            elif find_image(img, project) is None:
                problems.append(f'{where}: the image "{img}" is not in this folder.')
    return problems


def main():
    project = Path.cwd()
    source = project / INPUTS
    if not source.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])

    problems = check(inputs, project)
    if problems:
        fail(problems)

    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    config["events"] = []
    drawn = []
    names = list(PALETTE)
    for i, ev in enumerate(inputs["events"]):
        ev = dict(ev)
        if "image" in ev:
            found = find_image(ev["image"], project)
            media = out / "media"
            media.mkdir(exist_ok=True)
            target = f"media/{ev['id']}{found.suffix.lower()}"
            shutil.copyfile(found, out / target)
            ev["image"] = target
        config["events"].append(ev)
        drawn.append(
            {
                "id": ev["id"],
                "title": ev["title"].strip(),
                "date": ev["date"],
                **({"start": ev["start"]} if "start" in ev else {}),
                "color": hex_color(ev["color"]) if "color" in ev else PALETTE[names[i % len(names)]],
                **({"icon": ev["icon"]} if "icon" in ev else {}),
                **({"image": ev["image"]} if "image" in ev else {}),
                **({"repeat": ev["repeat"]} if "repeat" in ev else {}),
            }
        )

    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, indent=2)};\n", encoding="utf-8")
    (out / "data.js").write_text(
        f"window.__APP_DATA__ = {json.dumps({'events': drawn}, indent=2)};\n", encoding="utf-8"
    )

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
