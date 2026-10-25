"""Build Tiny Planet from tiny-planet.inputs.json in the current folder.

Usage: cd <project> && python3 <agent-apps>/tiny-planet/scripts/run.py

Reads the inputs, checks every key, copies site/ to out/tiny-planet/, and writes theme.css and config.js there.
Two runs on the same inputs write the same bytes.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "tiny-planet"
INPUTS = f"{APP}.inputs.json"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"

REQUIRED = {"planetName": str, "playerName": str, "theme": str, "seed": str}
OPTIONAL = {"title": str, "daySeconds": (int, float), "crystals": int}
DEFAULTS = {"title": "Tiny Planet", "daySeconds": 120, "crystals": 7}
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
            problems.append(f'{INPUTS} has the key "{key}", which Tiny Planet does not use.')
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
        crystals = inputs.get("crystals", DEFAULTS["crystals"])
        if not 1 <= crystals <= 24:
            problems.append(f'{INPUTS} needs "crystals" to be from 1 to 24.')
        day = inputs.get("daySeconds", DEFAULTS["daySeconds"])
        if not 30 <= day <= 1800:
            problems.append(f'{INPUTS} needs "daySeconds" to be from 30 to 1800.')
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
