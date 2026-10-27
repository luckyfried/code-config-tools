"""Writes the Deal Board page into out/deal-board/ from deal-board.inputs.json.

Run from the project folder (the one holding deal-board.inputs.json):

    python3 <agent-apps root>/deal-board/scripts/run.py

It copies the built page (dist/), the chosen theme as theme.css, and the inputs as config.js. Standard library only;
two runs on the same inputs write the same bytes.
"""

import json
import re
import shutil
import sys
from pathlib import Path

APP = "deal-board"
HERE = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd()
INPUTS = PROJECT / f"{APP}.inputs.json"
OUT = PROJECT / "out" / APP
DIST = HERE / "dist"
THEMES = HERE / "src" / "themes"
BADGE = HERE / "badge.js"

KEYS = {"name", "currency", "stages", "seedDeals", "theme"}
STAGE_KEYS = {"id", "label", "probability", "color"}
SEED_KEYS = {"company", "value", "stage", "contact", "nextStep", "date", "notes", "daysInStage", "openedDaysAgo", "from"}
CLOSED = {"won", "lost"}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def problems_in(inputs):
    """Every problem with the inputs, one plain sentence each."""
    name = f"{APP}.inputs.json"
    if not isinstance(inputs, dict):
        return [f"{name} must hold one JSON object."]
    found = []
    for key in sorted(KEYS - inputs.keys()):
        found.append(f'{name} is missing the key "{key}".')
    for key in sorted(inputs.keys() - KEYS):
        if not key.startswith("_"):
            found.append(f'{name} has a key this app does not read: "{key}".')

    if "name" in inputs and (not isinstance(inputs["name"], str) or not inputs["name"].strip()):
        found.append(f'"name" in {name} must be the board\'s title, as text.')
    if "currency" in inputs and not (isinstance(inputs["currency"], str) and re.fullmatch(r"[A-Za-z]{3}", inputs["currency"])):
        found.append(f'"currency" in {name} must be a three-letter code such as USD, EUR, or GBP.')

    stage_ids = set()
    stages = inputs.get("stages")
    if "stages" in inputs:
        if not isinstance(stages, list) or not stages:
            found.append(f'"stages" in {name} must be a list of at least one stage.')
        else:
            for i, stage in enumerate(stages, 1):
                where = f"Stage {i} in {name}"
                if not isinstance(stage, dict):
                    found.append(f"{where} must be an object with id, label, probability, and color.")
                    continue
                for key in sorted(STAGE_KEYS - stage.keys()):
                    found.append(f'{where} is missing the key "{key}".')
                for key in sorted(stage.keys() - STAGE_KEYS):
                    found.append(f'{where} has a key this app does not read: "{key}".')
                sid = stage.get("id")
                if "id" in stage:
                    if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", sid):
                        found.append(f'{where} needs an "id" of lowercase letters, digits, and hyphens.')
                    elif sid in CLOSED:
                        found.append(f'{where} cannot use the id "{sid}"; won and lost are the board\'s own.')
                    elif sid in stage_ids:
                        found.append(f'{where} repeats the id "{sid}".')
                    else:
                        stage_ids.add(sid)
                if "label" in stage and (not isinstance(stage["label"], str) or not stage["label"].strip()):
                    found.append(f'{where} needs a "label" as text.')
                if "probability" in stage and not (number(stage["probability"]) and 0 <= stage["probability"] <= 100):
                    found.append(f'{where} needs a "probability" from 0 to 100.')
                if "color" in stage and not (isinstance(stage["color"], str) and re.fullmatch(r"#[0-9a-fA-F]{6}", stage["color"])):
                    found.append(f'{where} needs a "color" written as #rrggbb.')

    seeds = inputs.get("seedDeals")
    if "seedDeals" in inputs:
        if not isinstance(seeds, list):
            found.append(f'"seedDeals" in {name} must be a list of deals (it can be empty).')
        else:
            for i, seed in enumerate(seeds, 1):
                where = f"Deal {i} in seedDeals"
                if not isinstance(seed, dict):
                    found.append(f"{where} must be an object with at least company, value, and stage.")
                    continue
                for key in ("company", "value", "stage"):
                    if key not in seed:
                        found.append(f'{where} is missing the key "{key}".')
                for key in sorted(seed.keys() - SEED_KEYS):
                    found.append(f'{where} has a key this app does not read: "{key}".')
                if "company" in seed and (not isinstance(seed["company"], str) or not seed["company"].strip()):
                    found.append(f'{where} needs a "company" as text.')
                if "value" in seed and not (number(seed["value"]) and seed["value"] >= 0):
                    found.append(f'{where} needs a "value" of zero or more.')
                if "stage" in seed and stage_ids and seed["stage"] not in stage_ids | CLOSED:
                    found.append(f'{where} names the stage "{seed["stage"]}"; use one of {", ".join(sorted(stage_ids))}, won, or lost.')
                if "from" in seed and stage_ids and seed["from"] not in stage_ids:
                    found.append(f'{where} names "from": "{seed["from"]}", which is not a stage.')
                for key in ("contact", "nextStep", "notes"):
                    if key in seed and not isinstance(seed[key], str):
                        found.append(f'{where} needs "{key}" as text.')
                for key in ("daysInStage", "openedDaysAgo"):
                    if key in seed and not (number(seed[key]) and seed[key] >= 0):
                        found.append(f'{where} needs "{key}" as a number of days, zero or more.')
                if "date" in seed:
                    date = seed["date"]
                    if not (number(date) or (isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date))):
                        found.append(f'{where} needs "date" as YYYY-MM-DD or a number of days from today.')

    themes = sorted(path.stem for path in THEMES.glob("*.css"))
    if "theme" in inputs and inputs["theme"] not in themes:
        found.append(f'"theme" in {name} must be one of {", ".join(themes)}.')
    return found


def main():
    if not INPUTS.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{APP}.inputs.json is not valid JSON: {error.msg} on line {error.lineno}.")
        return 2
    problems = problems_in(inputs)
    if problems:
        print("\n".join(problems))
        return 2
    if not (DIST / "index.html").is_file():
        print(f"The built page is missing from {DIST}; the app folder is incomplete.")
        return 2

    config = {key: value for key, value in inputs.items() if not key.startswith("_")}
    config["currency"] = config["currency"].upper()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(DIST, OUT)
    if BADGE.is_file():
        shutil.copyfile(BADGE, OUT / "badge.js")
    else:
        page = OUT / "index.html"
        page.write_text(page.read_text(encoding="utf-8").replace('<script src="./badge.js" defer></script>', ""), encoding="utf-8")
    shutil.copyfile(THEMES / f"{config['theme']}.css", OUT / "theme.css")
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    count = sum(1 for path in OUT.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
