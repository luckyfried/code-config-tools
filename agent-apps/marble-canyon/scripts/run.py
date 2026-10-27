"""Writes this person's Marble Canyon into out/marble-canyon/ in the current folder.

Run it from the project folder:

    cd <project> && python3 <agent-apps root>/marble-canyon/scripts/run.py

It reads marble-canyon.inputs.json from the current folder, checks every key, copies the page, and writes
config.js and theme.css. Standard library only; two runs on the same inputs give the same files.
"""

import json
import re
import shutil
import sys
from pathlib import Path

APP = "marble-canyon"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
BADGE = APP_DIR / "badge.js"

LENGTHS = ("short", "medium", "long")
HEX = re.compile(r"#[0-9a-fA-F]{6}")

# key: (required, type, what it should be when wrong)
KEYS = {
    "title": (True, str, "text, the name on the title card"),
    "racerName": (True, str, "text, your name"),
    "theme": (True, str, "the name of a theme"),
    "seed": (False, str, "a word"),
    "trackLength": (True, str, "short, medium, or long"),
    "marbleColor": (True, str, 'a color like "#2f6fdb"'),
}


def problems_in(inputs):
    problems = []
    for key, (required, kind, wording) in KEYS.items():
        if key not in inputs:
            if required:
                problems.append(f'{APP}.inputs.json is missing the key "{key}".')
            continue
        value = inputs[key]
        if not isinstance(value, kind) or (required and isinstance(value, str) and not value.strip()):
            problems.append(f'{APP}.inputs.json has "{key}" set to {json.dumps(value)}; it should be {wording}.')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f'{APP}.inputs.json has the key "{key}", which Marble Canyon does not use.')
    if problems:
        return problems
    if inputs["trackLength"] not in LENGTHS:
        problems.append(f'{APP}.inputs.json has "trackLength" set to {json.dumps(inputs["trackLength"])}; it should be short, medium, or long.')
    if not HEX.fullmatch(inputs["marbleColor"]):
        problems.append(f'{APP}.inputs.json has "marbleColor" set to {json.dumps(inputs["marbleColor"])}; it should be a color like "#2f6fdb".')
    themes = sorted(path.stem for path in THEMES.glob("*.css"))
    if inputs["theme"] not in themes:
        problems.append(f'{APP}.inputs.json has "theme" set to {json.dumps(inputs["theme"])}; the themes are {", ".join(themes)}.')
    if len(inputs["title"]) > 60:
        problems.append(f'{APP}.inputs.json has a "title" longer than 60 characters; the title card holds 60.')
    if len(inputs["racerName"]) > 40:
        problems.append(f'{APP}.inputs.json has a "racerName" longer than 40 characters.')
    if "seed" in inputs and len(inputs["seed"]) > 40:
        problems.append(f'{APP}.inputs.json has a "seed" longer than 40 characters; one word is enough.')
    return problems


def main():
    project = Path.cwd()
    source = project / f"{APP}.inputs.json"
    if not source.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{APP}.inputs.json is not valid JSON: {error}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{APP}.inputs.json should hold one JSON object with the keys inputs.example.json shows.")
        return 2
    problems = problems_in(inputs)
    if problems:
        for line in problems:
            print(line)
        return 2

    config = {
        "title": inputs["title"].strip(),
        "racerName": inputs["racerName"].strip(),
        "theme": inputs["theme"],
        "seed": (inputs.get("seed") or inputs["racerName"]).strip(),
        "trackLength": inputs["trackLength"],
        "marbleColor": inputs["marbleColor"].lower(),
    }

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8"
    )

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
