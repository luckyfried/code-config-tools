#!/usr/bin/env python3
"""Builds the Week Board page for the project in the current folder.

Reads week-board.inputs.json from the current folder, checks it, copies the built page from dist/ into out/week-board/,
and writes config.js (the inputs) and theme.css (the chosen theme) beside its index.html. Standard library only.
"""
import json
import shutil
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
INPUTS = "week-board.inputs.json"
OUT = Path("out") / "week-board"
REQUIRED = ["name", "weekStart", "columns", "later", "seedTasks", "theme"]
OPTIONAL = ["_notes"]
DAY_WORDS = {"mon", "monday", "tue", "tues", "tuesday", "wed", "wednesday", "thu", "thur", "thurs", "thursday",
             "fri", "friday", "sat", "saturday", "sun", "sunday", "today", "tomorrow", "later"}


def check(inputs, themes):
    problems = []
    say = problems.append
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object, like inputs.example.json."]
    for key in REQUIRED:
        if key not in inputs:
            say(f'{INPUTS} is missing the key "{key}".')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL:
            say(f'{INPUTS} has the key "{key}", which Week Board does not use.')

    if "name" in inputs and not (isinstance(inputs["name"], str) and inputs["name"].strip()):
        say('"name" must be text for the board\'s title, such as "Dana\'s week".')
    if "weekStart" in inputs and inputs["weekStart"] not in ("mon", "sun"):
        say('"weekStart" must be "mon" or "sun".')
    if "columns" in inputs and (inputs["columns"] not in (5, 7) or isinstance(inputs["columns"], bool)):
        say('"columns" must be 7 for every day or 5 for workdays.')
    if "later" in inputs and not isinstance(inputs["later"], bool):
        say('"later" must be true to show the Later rail or false to hide it.')
    if "theme" in inputs and inputs["theme"] not in themes:
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')

    seeds = inputs.get("seedTasks")
    if "seedTasks" in inputs:
        if not isinstance(seeds, list):
            say('"seedTasks" must be a list of tasks, each with a title and a day, or [] for an empty board.')
        else:
            for n, t in enumerate(seeds, 1):
                where = f'"seedTasks" item {n}'
                if not isinstance(t, dict):
                    say(f"{where} must be an object with a title and a day.")
                    continue
                for key in t:
                    if key not in ("title", "day"):
                        say(f'{where} has the key "{key}", which Week Board does not use.')
                if not (isinstance(t.get("title"), str) and t["title"].strip()):
                    say(f'{where} needs a "title", the words on the card.')
                day = t.get("day")
                if not (isinstance(day, str) and day.strip().lower() in DAY_WORDS):
                    say(f'{where} needs a "day": mon to sun, today, tomorrow, or later.')
    return problems


def main():
    src = Path(INPUTS)
    if not src.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{INPUTS} is not valid JSON: {e}.")
        return 2
    themes = {p.stem for p in (APP / "src" / "themes").glob("*.css")}
    problems = check(inputs, themes)
    if problems:
        print("\n".join(problems))
        return 2

    dist = APP / "dist"
    if not (dist / "index.html").is_file():
        print(f"The built page is missing from {dist}; in {APP} run: npm ci && npm run build")
        return 2
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(dist, OUT)
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")
    shutil.copyfile(APP / "src" / "themes" / f"{inputs['theme']}.css", OUT / "theme.css")
    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT}/ ({count} files). Serve it: python3 -m http.server 8000 --directory {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
