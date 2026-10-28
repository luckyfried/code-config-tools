"""Builds Shard Storm into out/shard-storm/ from shard-storm.inputs.json in the current folder.

Run it from the project folder:

    python3 <agent-apps root>/shard-storm/scripts/run.py

It checks the inputs, copies the site, writes theme.css from the chosen theme
and config.js from the inputs, and prints how to serve the result. Standard
library only; two runs on the same inputs write identical files.
"""

import json
import re
import shutil
import sys
from pathlib import Path

SLUG = "shard-storm"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"
INPUTS = f"{SLUG}.inputs.json"
PATTERNS = ["Lotus", "Vortex", "Rain", "Twin Spirals", "Comb", "Pulse Rings", "Scatter", "Wall"]
REQUIRED = ["playerName", "theme", "shipColor"]
OPTIONAL = {"title": "Shard Storm", "runSeconds": 60, "patterns": PATTERNS}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def check(inputs):
    problems = []
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    known = set(REQUIRED) | set(OPTIONAL) | {"_notes"}
    for key in inputs:
        if key not in known:
            problems.append(f'{INPUTS} has a key this app does not use: "{key}".')

    def text(key, longest):
        value = inputs.get(key)
        if key in inputs and (not isinstance(value, str) or not value.strip() or len(value) > longest):
            problems.append(f'{INPUTS}: "{key}" must be text of 1 to {longest} characters.')

    text("title", 40)
    text("playerName", 24)
    if "shipColor" in inputs and not (isinstance(inputs["shipColor"], str) and re.fullmatch(r"#[0-9a-fA-F]{6}", inputs["shipColor"])):
        problems.append(f'{INPUTS}: "shipColor" must be a hex color like "#3dff8b".')
    if "theme" in inputs:
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'{INPUTS}: "theme" must be one of {", ".join(names)}.')
    if "runSeconds" in inputs:
        seconds = inputs["runSeconds"]
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 20 <= seconds <= 600:
            problems.append(f'{INPUTS}: "runSeconds" must be a number from 20 to 600.')
    if "patterns" in inputs:
        chosen = inputs["patterns"]
        if not isinstance(chosen, list) or not chosen or any(name not in PATTERNS for name in chosen):
            problems.append(f'{INPUTS}: "patterns" must list one or more of {", ".join(PATTERNS)}.')
    return problems


def main():
    source = Path.cwd() / INPUTS
    if not source.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must hold one JSON object."])
    problems = check(inputs)
    if problems:
        fail(problems)

    config = {key: inputs.get(key, default) for key, default in OPTIONAL.items()}
    config.update({key: inputs[key] for key in REQUIRED})
    config = {key: config[key] for key in ["title", "playerName", "theme", "shipColor", "runSeconds", "patterns"]}

    out = Path.cwd() / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(APP / "badge.js", out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=True)};\n", encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
