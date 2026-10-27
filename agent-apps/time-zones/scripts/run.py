"""Writes the Time Zones page for the project in the current directory.

Reads time-zones.inputs.json from the current directory, copies site/ into out/time-zones/, writes config.js from the
inputs, and copies the chosen theme to theme.css. Two runs on the same inputs give the same files.

    cd <project> && python3 <agent-apps root>/time-zones/scripts/run.py
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

APP = "time-zones"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
MAX_PEOPLE = 12
NOTES = "_notes"  # the example's notes on each key; read by people, never by the page
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

TOP = {"home": dict, "people": list, "hourFormat": int, "theme": str}
HOME_REQUIRED = {"label": str, "zone": str}
HOME_OPTIONAL = {"workStart": (int, float), "workEnd": (int, float)}
PERSON_REQUIRED = {"name": str, "city": str, "zone": str, "workStart": (int, float), "workEnd": (int, float)}
PERSON_OPTIONAL = {"color": str}
WORDS = {str: "text", list: "a list", dict: "an object", int: "a whole number", (int, float): "a number of hours"}


def known_zones():
    """The zone names this machine knows, or None when it has no zone list to check against."""
    try:
        import zoneinfo

        names = zoneinfo.available_timezones()
    except Exception:
        return None
    return (names | {"UTC"}) if names else None


def type_ok(value, kind):
    if isinstance(value, bool):
        return False
    return isinstance(value, kind)


def check_keys(obj, required, optional, where, problems):
    for key, kind in required.items():
        if key not in obj:
            problems.append(f'{where} is missing the key "{key}".')
        elif not type_ok(obj[key], kind):
            problems.append(f'{where}: "{key}" must be {WORDS[kind]}.')
    for key, kind in optional.items():
        if key in obj and not type_ok(obj[key], kind):
            problems.append(f'{where}: "{key}" must be {WORDS[kind]}.')
    for key in obj:
        if key not in required and key not in optional:
            problems.append(f'{where} has a key this app does not read: "{key}".')


def check_hours(obj, where, problems):
    for key in ("workStart", "workEnd"):
        value = obj.get(key)
        if type_ok(value, (int, float)) and not (0 <= value <= 24 and float(value * 4).is_integer()):
            problems.append(f'{where}: "{key}" must be an hour from 0 to 24, like 9 or 17.5.')
    start, end = obj.get("workStart"), obj.get("workEnd")
    if type_ok(start, (int, float)) and type_ok(end, (int, float)) and start % 24 == end % 24:
        problems.append(f'{where}: "workStart" and "workEnd" must be different hours.')


def check_zone(obj, where, zones, problems):
    zone = obj.get("zone")
    if isinstance(zone, str) and zones is not None and zone not in zones:
        problems.append(f'{where}: "{zone}" is not a time zone name; use one like "America/New_York".')


def validate(inputs, theme_names):
    if not isinstance(inputs, dict):
        return [f"{APP}.inputs.json must hold one object with the keys home, people, hourFormat, and theme."]
    problems = []
    for key, kind in TOP.items():
        if key not in inputs:
            problems.append(f'{APP}.inputs.json is missing the key "{key}".')
        elif not type_ok(inputs[key], kind):
            problems.append(f'"{key}" must be {WORDS[kind]}.')
    for key in inputs:
        if key not in TOP and key != NOTES:
            problems.append(f'{APP}.inputs.json has a key this app does not read: "{key}".')

    zones = known_zones()
    home = inputs.get("home")
    if isinstance(home, dict):
        check_keys(home, HOME_REQUIRED, HOME_OPTIONAL, '"home"', problems)
        check_hours(home, '"home"', problems)
        check_zone(home, '"home"', zones, problems)

    people = inputs.get("people")
    if isinstance(people, list):
        if not 1 <= len(people) <= MAX_PEOPLE:
            problems.append(f'"people" must list one to {MAX_PEOPLE} people; it lists {len(people)}.')
        for n, person in enumerate(people, 1):
            where = f"Person {n}"
            if not isinstance(person, dict):
                problems.append(f"{where} must be an object with name, city, zone, workStart, and workEnd.")
                continue
            check_keys(person, PERSON_REQUIRED, PERSON_OPTIONAL, where, problems)
            check_hours(person, where, problems)
            check_zone(person, where, zones, problems)
            color = person.get("color")
            if isinstance(color, str) and not HEX.match(color):
                problems.append(f'{where}: "color" must be a color like "#3b82f6".')

    if type_ok(inputs.get("hourFormat"), int) and inputs["hourFormat"] not in (12, 24):
        problems.append('"hourFormat" must be 12 or 24.')
    theme = inputs.get("theme")
    if isinstance(theme, str) and theme not in theme_names:
        problems.append(f'"theme" must be one of {", ".join(theme_names)}; "{theme}" is not a theme here.')
    return problems


def main():
    argparse.ArgumentParser(description="Write the Time Zones page from time-zones.inputs.json.").parse_args()
    project = Path.cwd()
    inputs_path = project / f"{APP}.inputs.json"
    if not inputs_path.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"{APP}.inputs.json is not valid JSON: {err.msg} on line {err.lineno}.")
        return 2
    theme_names = sorted(p.stem for p in THEMES.glob("*.css"))
    problems = validate(inputs, theme_names)
    if problems:
        print("\n".join(problems))
        return 2

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    config = {key: value for key, value in inputs.items() if key != NOTES}
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8"
    )

    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
