"""Writes the Weight Trend page for the project in the current directory.

Reads weight-trend.inputs.json from the current directory, copies site/ into out/weight-trend/, and writes config.js
from the inputs and theme.css from the chosen theme beside index.html.

    cd <project> && python3 <agent-apps root>/weight-trend/scripts/run.py
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

APP = "weight-trend"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
ICON = APP_DIR / "assets" / "icon.svg"
NOTES = "_notes"  # the example's notes on each key; read by people, never by the page

REQUIRED = {"name": str, "units": str, "goal": (int, float), "theme": str}
OPTIONAL = {"smoothing": (int, float), "showProjection": bool, "sample": bool}
TYPE_WORDS = {str: "text", (int, float): "a number", bool: "true or false"}
GOAL_RANGE = {"kg": (20, 400), "lb": (45, 880)}


def type_ok(value, kind):
    if kind == (int, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, kind)


def validate(inputs, theme_names):
    if not isinstance(inputs, dict):
        return [f"{APP}.inputs.json must hold one object with the keys name, units, goal, and theme."]
    problems = []
    for key, kind in REQUIRED.items():
        if key not in inputs:
            problems.append(f'{APP}.inputs.json is missing the key "{key}".')
        elif not type_ok(inputs[key], kind):
            problems.append(f'"{key}" must be {TYPE_WORDS[kind]}.')
    for key, kind in OPTIONAL.items():
        if key in inputs and not type_ok(inputs[key], kind):
            problems.append(f'"{key}" must be {TYPE_WORDS[kind]}.')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL and key != NOTES:
            problems.append(f'{APP}.inputs.json has a key this app does not read: "{key}".')

    units = inputs.get("units")
    if type_ok(units, str) and units not in GOAL_RANGE:
        problems.append('"units" must be "kg" or "lb".')
    goal = inputs.get("goal")
    if units in GOAL_RANGE and type_ok(goal, (int, float)):
        low, high = GOAL_RANGE[units]
        if not low <= goal <= high:
            problems.append(f'"goal" must be a weight from {low} to {high} {units}.')
    smoothing = inputs.get("smoothing")
    if type_ok(smoothing, (int, float)) and not 0.01 <= smoothing <= 0.5:
        problems.append('"smoothing" must be from 0.01 to 0.5; 0.1 is the usual.')
    theme = inputs.get("theme")
    if type_ok(theme, str) and theme not in theme_names:
        problems.append(f'"theme" must be one of {", ".join(theme_names)}; "{theme}" is not a theme here.')
    return problems


def main():
    argparse.ArgumentParser(description="Write the Weight Trend page from weight-trend.inputs.json.").parse_args()
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
    shutil.copyfile(ICON, out / "icon.svg")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    config = {key: value for key, value in inputs.items() if key != NOTES}
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config)};\n", encoding="utf-8")

    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
