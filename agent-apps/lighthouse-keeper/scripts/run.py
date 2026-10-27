"""Build Lighthouse Keeper from lighthouse-keeper.inputs.json in the current folder.

Usage: cd <project> && python3 <agent-apps>/lighthouse-keeper/scripts/run.py

Reads the inputs, checks every key, copies site/ to out/lighthouse-keeper/, and writes theme.css and config.js
there. Two runs on the same inputs write the same bytes.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "lighthouse-keeper"
INPUTS = f"{APP}.inputs.json"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"

REQUIRED = {"lighthouseName": str, "playerName": str, "theme": str}
OPTIONAL = {"title": str, "shipsToLose": int, "nightMinutes": (int, float)}
DEFAULTS = {"title": "Lighthouse Keeper", "shipsToLose": 3, "nightMinutes": 5}
TYPE_WORDS = {str: "text", int: "a whole number", (int, float): "a number"}


def fail(problems):
    for line in problems:
        print(line)
    sys.exit(2)


def check(inputs):
    problems = []
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object with the keys inputs.example.json shows."]
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    for key, value in inputs.items():
        if key == "_notes":
            continue
        kind = REQUIRED.get(key) or OPTIONAL.get(key)
        if kind is None:
            problems.append(f'{INPUTS} has the key "{key}", which Lighthouse Keeper does not use.')
            continue
        if isinstance(value, bool) or not isinstance(value, kind):
            problems.append(f'{INPUTS} needs "{key}" to be {TYPE_WORDS[kind]}.')
            continue
        if kind is str and not value.strip():
            problems.append(f'{INPUTS} has an empty "{key}".')
    if not problems:
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'{INPUTS} names the theme "{inputs["theme"]}"; the themes are {", ".join(names)}.')
        ships = inputs.get("shipsToLose", DEFAULTS["shipsToLose"])
        if not 1 <= ships <= 10:
            problems.append(f'{INPUTS} needs "shipsToLose" to be from 1 to 10.')
        minutes = inputs.get("nightMinutes", DEFAULTS["nightMinutes"])
        if not 1 <= minutes <= 30:
            problems.append(f'{INPUTS} needs "nightMinutes" to be from 1 to 30.')
        if len(inputs["lighthouseName"]) > 40:
            problems.append(f'{INPUTS} needs "lighthouseName" to be 40 characters or fewer, to fit on the tower.')
    return problems


def main():
    path = Path.cwd() / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])
    problems = check(inputs)
    if problems:
        fail(problems)

    config = {**DEFAULTS, **{k: v for k, v in inputs.items() if k != "_notes"}}
    config = {k: v.strip() if isinstance(v, str) else v for k, v in config.items()}
    out = Path.cwd() / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, sort_keys=True)};\n", encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
