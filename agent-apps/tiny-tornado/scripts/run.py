"""Build Tiny Tornado from tiny-tornado.inputs.json in the current folder.

Usage: cd <project> && python3 <agent-apps>/tiny-tornado/scripts/run.py

Reads the inputs (the app's inputs.example.json when the folder has no inputs file yet), checks every key, copies site/ to out/tiny-tornado/, and writes theme.css and config.js there.
Two runs on the same inputs write the same bytes.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "tiny-tornado"
INPUTS = f"{APP}.inputs.json"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"

REQUIRED = {"playerName": str, "townName": str, "theme": str}
OPTIONAL = {"title": str, "seed": str, "runSeconds": (int, float)}
DEFAULTS = {"title": "Tiny Tornado", "runSeconds": 60}
TYPE_WORDS = {str: "text", (int, float): "a number"}


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
            problems.append(f'{INPUTS} has the key "{key}", which Tiny Tornado does not use.')
            continue
        if isinstance(value, bool) or not isinstance(value, kind):
            problems.append(f'{INPUTS} needs "{key}" to be {TYPE_WORDS[kind]}.')
            continue
        if kind is str and not value.strip() and key != "seed":
            problems.append(f'{INPUTS} has an empty "{key}".')
    if not problems:
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'{INPUTS} names the theme "{inputs["theme"]}"; the themes are {", ".join(names)}.')
        seconds = inputs.get("runSeconds", DEFAULTS["runSeconds"])
        if not 15 <= seconds <= 600:
            problems.append(f'{INPUTS} needs "runSeconds" to be from 15 to 600.')
        if len(inputs["townName"]) > 24:
            problems.append(f'{INPUTS} needs "townName" to be 24 letters or fewer, so it fits on the water tower.')
    return problems


def main():
    path = Path.cwd() / INPUTS
    if not path.is_file():
        path = APP_DIR / "inputs.example.json"
        print(f"No {INPUTS} here, so this run uses inputs.example.json. Copy it here as {INPUTS} to make it yours.")
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{path.name} is not valid JSON: {error}."])
    problems = check(inputs)
    if problems:
        fail(problems)

    config = {**DEFAULTS, **{k: v for k, v in inputs.items() if k != "_notes"}}
    if not str(config.get("seed", "")).strip():
        config["seed"] = config["townName"]
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
