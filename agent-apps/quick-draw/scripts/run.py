"""Writes Quick Draw into out/quick-draw/ in the current folder, from quick-draw.inputs.json there.

Run it from the project folder:

    cd <project> && python3 <agent-apps root>/quick-draw/scripts/run.py

Standard library only. Two runs on the same inputs write byte-identical files.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "quick-draw"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
BADGE = HERE / "badge.js"

# Every key the page reads, in the order config.js writes them.
KEYS = ("title", "players", "townName", "theme", "bestOf")
IGNORED = {"_notes"}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def read_inputs(project):
    path = project / f"{APP}.inputs.json"
    if not path.is_file():
        fail([f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        fail([f"{APP}.inputs.json is not valid JSON: {error}."])
    if not isinstance(data, dict):
        fail([f"{APP}.inputs.json must hold one JSON object with the keys inputs.example.json shows."])
    return data


def text(value, limit):
    return isinstance(value, str) and value.strip() != "" and len(value.strip()) <= limit


def check(data):
    problems = []
    for key in KEYS:
        if key not in data:
            problems.append(f'{APP}.inputs.json is missing the key "{key}".')
    for key in data:
        if key not in KEYS and key not in IGNORED:
            problems.append(f'{APP}.inputs.json has the key "{key}", which this app does not use.')

    if "title" in data and not text(data["title"], 40):
        problems.append(f'{APP}.inputs.json has "title" as {json.dumps(data["title"])}; it must be text of 1 to 40 characters.')
    if "townName" in data and not text(data["townName"], 28):
        problems.append(f'{APP}.inputs.json has "townName" as {json.dumps(data["townName"])}; it must be text of 1 to 28 characters.')
    if "players" in data:
        players = data["players"]
        if not (isinstance(players, list) and len(players) == 2 and all(text(p, 14) for p in players)):
            problems.append(f'{APP}.inputs.json has "players" as {json.dumps(players)}; it must be two names, left then right, each 1 to 14 characters.')
    if "bestOf" in data:
        best = data["bestOf"]
        if isinstance(best, bool) or best not in (3, 5, 7):
            problems.append(f'{APP}.inputs.json has "bestOf" as {json.dumps(best)}; it must be 3, 5, or 7.')
    if "theme" in data:
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        theme = data["theme"]
        if theme not in names:
            listed = ", ".join(names[:-1]) + f", or {names[-1]}"
            problems.append(f'{APP}.inputs.json has "theme" as {json.dumps(theme)}; the themes are {listed}.')
    if problems:
        fail(problems)


def main():
    project = Path.cwd()
    data = read_inputs(project)
    check(data)
    inputs = {key: data[key] for key in KEYS}
    inputs["title"] = inputs["title"].strip()
    inputs["townName"] = inputs["townName"].strip()
    inputs["players"] = [p.strip() for p in inputs["players"]]

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")

    (out / "theme.css").write_bytes((THEMES / f"{inputs['theme']}.css").read_bytes())
    config = f"window.__APP_CONFIG__ = {json.dumps(inputs, ensure_ascii=False)};\n"
    (out / "config.js").write_text(config, encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
