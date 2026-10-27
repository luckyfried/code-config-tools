"""Write Lift Log for the project in the current folder.

Reads lift-log.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/lift-log/, and writes config.js (the inputs) and theme.css (the chosen theme) beside index.html.
Two runs on the same inputs give the same files.

    cd <project> && python3 <agent-apps root>/lift-log/scripts/run.py
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

APP = "lift-log"
APP_DIR = Path(__file__).resolve().parents[1]
DIST = APP_DIR / "dist"
THEMES = APP_DIR / "src" / "themes"
KEYS = {"name", "units", "exercises", "restSeconds", "plates", "barWeight", "theme", "_notes"}
REQUIRED = ("units", "exercises")
EXERCISE_KEYS = {"id", "label", "muscles", "equipment"}
EQUIPMENT = ("barbell", "dumbbell", "machine", "bodyweight")
MUSCLES = (
    "chest", "shoulders", "biceps", "triceps", "forearms", "traps", "lats",
    "abs", "obliques", "lower-back", "glutes", "quads", "hamstrings", "calves",
)
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
DEFAULT_PLATES = {"kg": [25, 20, 15, 10, 5, 2.5, 1.25], "lb": [45, 35, 25, 10, 5, 2.5]}
DEFAULT_BAR = {"kg": 20, "lb": 45}


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def check_exercise(n, ex, src, seen):
    problems = []
    if not isinstance(ex, dict):
        return [f"Exercise {n} in {src} must be an object with id, label, and muscles."]
    label = ex.get("id") if is_text(ex.get("id")) else n
    where = f'Exercise "{label}" in {src}'
    for key in ("id", "label", "muscles"):
        if key not in ex:
            problems.append(f'{where} is missing "{key}".')
    if "id" in ex:
        if not isinstance(ex["id"], str) or not ID.match(ex["id"]):
            problems.append(f'{where} needs an id of lowercase letters, digits, and dashes, such as "bench-press".')
        elif ex["id"] in seen:
            problems.append(f'Two exercises in {src} share the id "{ex["id"]}"; each needs its own.')
        else:
            seen.add(ex["id"])
    if "label" in ex and not is_text(ex["label"]):
        problems.append(f'{where} needs some text for "label", such as "Bench press".')
    if "muscles" in ex:
        muscles = ex["muscles"]
        if not isinstance(muscles, list) or not muscles:
            problems.append(f'{where} must list at least one muscle in "muscles".')
        else:
            for m in muscles:
                if m not in MUSCLES:
                    problems.append(f'{where} names the muscle {json.dumps(m)}; the muscles are {", ".join(MUSCLES)}.')
    if "equipment" in ex and ex["equipment"] not in EQUIPMENT:
        problems.append(f'{where} has "equipment" set to {json.dumps(ex["equipment"])}; use {", ".join(EQUIPMENT)}.')
    for key in sorted(set(ex) - EXERCISE_KEYS):
        problems.append(f'{where} has a key this app does not use: "{key}".')
    return problems


def check(inputs, theme_names):
    problems = []
    src = f"{APP}.inputs.json"

    for key in sorted(set(inputs) - KEYS):
        problems.append(f'{src} has a key this app does not use: "{key}".')
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{src} is missing the key "{key}".')

    if "name" in inputs and not isinstance(inputs["name"], str):
        problems.append(f'"name" in {src} must be some text, such as "Sam".')
    if "units" in inputs and inputs["units"] not in ("kg", "lb"):
        problems.append(f'"units" in {src} is {json.dumps(inputs["units"])}; use "kg" or "lb".')

    exercises = inputs.get("exercises")
    if exercises is not None:
        if not isinstance(exercises, list) or not exercises:
            problems.append(f'"exercises" in {src} must list at least one lift.')
        else:
            seen = set()
            for n, ex in enumerate(exercises, start=1):
                problems.extend(check_exercise(n, ex, src, seen))

    rest = inputs.get("restSeconds")
    if "restSeconds" in inputs and (not isinstance(rest, int) or isinstance(rest, bool) or not 10 <= rest <= 900):
        problems.append(f'"restSeconds" in {src} must be a whole number of seconds from 10 to 900, such as 120.')

    plates = inputs.get("plates")
    if "plates" in inputs and (not isinstance(plates, list) or not plates or not all(is_number(p) and p > 0 for p in plates)):
        problems.append(f'"plates" in {src} must list the plate sizes as numbers, such as [25, 20, 15, 10, 5, 2.5, 1.25].')
    if "barWeight" in inputs and (not is_number(inputs["barWeight"]) or inputs["barWeight"] < 0):
        problems.append(f'"barWeight" in {src} must be a number of 0 or more, such as 20.')

    if "theme" in inputs and inputs["theme"] not in theme_names:
        problems.append(f'"theme" in {src} is {json.dumps(inputs["theme"])}; the themes are {", ".join(theme_names)}.')

    return problems


def main():
    parser = argparse.ArgumentParser(description="Write Lift Log into out/lift-log/ from lift-log.inputs.json.")
    parser.parse_args()

    project = Path.cwd()
    inputs_path = project / f"{APP}.inputs.json"
    if not inputs_path.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"{APP}.inputs.json is not valid JSON: line {err.lineno}, column {err.colno}: {err.msg}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{APP}.inputs.json must be one object with the keys inputs.example.json shows.")
        return 2

    theme_names = sorted(p.stem for p in THEMES.glob("*.css"))
    problems = check(inputs, theme_names)
    if problems:
        print("\n".join(problems))
        return 2
    if not (DIST / "index.html").is_file():
        print(f"The built page is missing from {DIST}; build it with npm ci && npm run build in {APP_DIR}.")
        return 2

    units = inputs["units"]
    config = {
        "name": inputs.get("name", "").strip(),
        "units": units,
        "restSeconds": inputs.get("restSeconds", 120),
        "barWeight": inputs.get("barWeight", DEFAULT_BAR[units]),
        "plates": sorted(inputs.get("plates", DEFAULT_PLATES[units]), reverse=True),
        "theme": inputs.get("theme", "auto"),
        "exercises": [
            {"id": e["id"], "label": e["label"].strip(), "muscles": e["muscles"], "equipment": e.get("equipment", "barbell")}
            for e in inputs["exercises"]
        ],
    }

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    (out / "theme.css").write_bytes((THEMES / f"{config['theme']}.css").read_bytes())
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
