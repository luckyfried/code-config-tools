"""Build Fish Tank from fish-tank.inputs.json in the current folder.

Usage: cd <project> && python3 <agent-apps>/fish-tank/scripts/run.py

Reads the inputs, checks every key, copies site/ to out/fish-tank/, and writes theme.css and config.js there.
Two runs on the same inputs write the same bytes.
"""

import html
import json
import shutil
import sys
from pathlib import Path

APP = "fish-tank"
INPUTS = f"{APP}.inputs.json"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
CATALOG = SITE / "sim" / "catalog.json"

REQUIRED = {"title": str, "theme": str}
OPTIONAL = {"startingFish": list, "cycleMinutes": (int, float), "pearlRate": str, "sound": bool}
DEFAULTS = {"cycleMinutes": 60, "pearlRate": "normal", "sound": True}
TYPE_WORDS = {str: "text", list: "a list of fish names", (int, float): "a number", bool: "true or false"}


def fail(problems):
    for line in problems:
        print(line)
    sys.exit(2)


def check(inputs, catalog):
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
            problems.append(f'{INPUTS} has the key "{key}", which Fish Tank does not use.')
            continue
        if (isinstance(value, bool) and kind is not bool) or not isinstance(value, kind):
            problems.append(f'{INPUTS} needs "{key}" to be {TYPE_WORDS[kind]}.')
            continue
        if kind is str and not value.strip():
            problems.append(f'{INPUTS} has an empty "{key}".')
    if problems:
        return problems

    names = sorted(p.stem for p in THEMES.glob("*.css"))
    theme = inputs["theme"]
    if theme not in names:
        return [f'{INPUTS} names the theme "{theme}"; the themes are {", ".join(names)}.']
    if len(inputs["title"]) > 40:
        problems.append(f'{INPUTS} needs "title" to be 40 characters or fewer.')
    fish = [s["name"] for s in catalog["species"] if s["theme"] == theme]
    known = {name.lower(): name for name in fish}
    starting = inputs.get("startingFish")
    if starting is not None:
        if not 1 <= len(starting) <= 6:
            problems.append(f'{INPUTS} needs "startingFish" to name from 1 to 6 fish.')
        for name in starting:
            if not isinstance(name, str) or name.strip().lower() not in known:
                problems.append(f'{INPUTS} lists "{name}" in "startingFish"; the {theme} fish are {", ".join(fish)}.')
    cycle = inputs.get("cycleMinutes", DEFAULTS["cycleMinutes"])
    if not 5 <= cycle <= 1440:
        problems.append(f'{INPUTS} needs "cycleMinutes" to be from 5 to 1440.')
    rate = inputs.get("pearlRate", DEFAULTS["pearlRate"])
    if rate not in catalog["rates"]:
        problems.append(f'{INPUTS} needs "pearlRate" to be one of {", ".join(catalog["rates"])}.')
    return problems


def main():
    path = Path.cwd() / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    problems = check(inputs, catalog)
    if problems:
        fail(problems)

    config = {**DEFAULTS, **{k: v for k, v in inputs.items() if k != "_notes"}}
    fish = {s["name"].lower(): s["name"] for s in catalog["species"] if s["theme"] == config["theme"]}
    starting = config.get("startingFish") or catalog["themes"][config["theme"]]["starting"]
    config["startingFish"] = [fish[name.strip().lower()] for name in starting]
    config["title"] = config["title"].strip()

    out = Path.cwd() / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    page = out / "index.html"
    title = html.escape(config["title"])
    page.write_text(page.read_text(encoding="utf-8").replace(">Fish Tank<", f">{title}<"), encoding="utf-8")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, sort_keys=True)};\n", encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
