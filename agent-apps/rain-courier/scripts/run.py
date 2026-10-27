"""Writes Rain Courier into out/rain-courier/ in the current folder, from rain-courier.inputs.json there.

Run it from the project folder:

    cd <project> && python3 <agent-apps root>/rain-courier/scripts/run.py

Standard library only. Two runs on the same inputs write byte-identical files.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "rain-courier"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
BADGE = HERE / "badge.js"

# Every key, its type, and whether it must be there.
KEYS = {
    "title": (str, True),
    "pilotName": (str, True),
    "cityName": (str, True),
    "theme": (str, True),
    "seed": (str, True),
    "shiftSeconds": (int, True),
}
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


def check(data):
    problems = []
    for key, (kind, required) in KEYS.items():
        if key not in data:
            if required:
                problems.append(f'{APP}.inputs.json is missing the key "{key}".')
            continue
        value = data[key]
        if kind is int:
            if isinstance(value, bool) or not isinstance(value, int):
                problems.append(f'{APP}.inputs.json has "{key}" as {json.dumps(value)}; it must be a whole number of seconds.')
            elif not 20 <= value <= 600:
                problems.append(f'{APP}.inputs.json has "{key}" as {value}; it must be from 20 to 600.')
        elif not isinstance(value, str) or not value.strip():
            problems.append(f'{APP}.inputs.json has "{key}" as {json.dumps(value)}; it must be text.')
    for key in data:
        if key not in KEYS and key not in IGNORED:
            problems.append(f'{APP}.inputs.json has the key "{key}", which this app does not use.')
    theme = data.get("theme")
    if isinstance(theme, str) and theme.strip():
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if theme not in names:
            problems.append(f'{APP}.inputs.json has "theme" as "{theme}"; the themes are {", ".join(names[:-1])}, and {names[-1]}.')
    if problems:
        fail(problems)


def main():
    project = Path.cwd()
    data = read_inputs(project)
    check(data)
    inputs = {key: data[key] for key in KEYS}

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
