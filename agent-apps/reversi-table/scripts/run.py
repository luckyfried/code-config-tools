"""Make the Reversi Table page from the person's inputs.

Run from the project folder:

    python3 <agent-apps root>/reversi-table/scripts/run.py

It reads reversi-table.inputs.json from the current folder, copies the page into
out/reversi-table/, writes the chosen table as theme.css and the inputs as
config.js, and prints how to serve it. Standard library only; two runs on the
same inputs give the same files.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "reversi-table"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
BADGE = APP_DIR / "badge.js"
INPUTS = f"{APP}.inputs.json"

# Each key: (type check, plain words for the type, required)
KEYS = {
    "title": (lambda v: isinstance(v, str) and v.strip() != "", "a name in quotes", True),
    "players": (lambda v: isinstance(v, dict), 'an object like {"black": "Ada", "white": "computer"}', True),
    "strength": (lambda v: isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 3, "1, 2, or 3", True),
    "theme": (lambda v: isinstance(v, str), "a table name in quotes", True),
    "sound": (lambda v: isinstance(v, bool), "true or false", False),
}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def read_inputs(project):
    path = project / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])
    if not isinstance(data, dict):
        fail([f"{INPUTS} must hold one object of keys and values."])
    return data


def check(data):
    problems = []
    for key, (ok, words, required) in KEYS.items():
        if key not in data:
            if required:
                problems.append(f'{INPUTS} is missing the key "{key}".')
            continue
        if not ok(data[key]):
            problems.append(f'In {INPUTS}, "{key}" must be {words}.')
    for key in data:
        if key not in KEYS and key != "_notes":
            problems.append(f'{INPUTS} has a key this app does not use: "{key}".')
    players = data.get("players")
    if isinstance(players, dict):
        for side in ("black", "white"):
            name = players.get(side)
            if side not in players:
                problems.append(f'In {INPUTS}, "players" is missing "{side}".')
            elif not isinstance(name, str) or name.strip() == "":
                problems.append(f'In {INPUTS}, "players"."{side}" must be a name, or "computer".')
        for side in players:
            if side not in ("black", "white"):
                problems.append(f'In {INPUTS}, "players" has a side this game does not have: "{side}".')
        names = [players.get("black"), players.get("white")]
        if all(isinstance(n, str) and n.strip().lower() == "computer" for n in names):
            problems.append(f'In {INPUTS}, at most one side of "players" can be "computer".')
    theme = data.get("theme")
    if isinstance(theme, str):
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if theme not in names:
            problems.append(f'In {INPUTS}, "theme" must be one of: {", ".join(names)}.')
    if problems:
        fail(problems)


def config_from(data):
    players = data["players"]
    return {
        "title": data["title"].strip(),
        "players": {"black": players["black"].strip(), "white": players["white"].strip()},
        "strength": data["strength"],
        "theme": data["theme"],
        "sound": data.get("sound", True),
    }


def main():
    project = Path.cwd()
    data = read_inputs(project)
    check(data)
    config = config_from(data)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False) + ";\n", encoding="utf-8"
    )

    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
