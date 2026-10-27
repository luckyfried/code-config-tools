"""Writes the Mental Math page into out/mental-math/ from mental-math.inputs.json in the current folder.

    cd <project> && python3 <agent-apps root>/mental-math/scripts/run.py

Standard library only. Two runs on the same inputs write byte-identical files.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "mental-math"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
OPERATIONS = ("add", "subtract", "multiply", "divide", "percent", "squares")
KEYS = {"players", "operations", "seconds", "theme"}
PLAYER_KEYS = {"name", "level", "kid"}
INPUTS = f"{APP}.inputs.json"


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def problems_in(inputs):
    problems = []
    for key in sorted(KEYS - inputs.keys()):
        problems.append(f'{INPUTS} is missing the key "{key}".')
    for key in sorted(inputs.keys() - KEYS - {"_notes"}):
        problems.append(f'{INPUTS} has the key "{key}", which Mental Math does not use.')

    players = inputs.get("players")
    if "players" in inputs:
        if not isinstance(players, list) or not players:
            problems.append(f'{INPUTS}: "players" must be a list with at least one player.')
        else:
            seen = set()
            for n, player in enumerate(players, 1):
                where = f'{INPUTS}: player {n}'
                if not isinstance(player, dict):
                    problems.append(f"{where} must be an object with a name, a level, and kid.")
                    continue
                for key in sorted(PLAYER_KEYS - player.keys()):
                    problems.append(f'{where} is missing the key "{key}".')
                for key in sorted(player.keys() - PLAYER_KEYS):
                    problems.append(f'{where} has the key "{key}", which Mental Math does not use.')
                name = player.get("name")
                if "name" in player and (not isinstance(name, str) or not name.strip()):
                    problems.append(f'{where}: "name" must be some text.')
                elif isinstance(name, str):
                    if name.strip() in seen:
                        problems.append(f'{where}: the name "{name.strip()}" is used twice.')
                    seen.add(name.strip())
                level = player.get("level")
                if "level" in player and (not is_int(level) or not 1 <= level <= 10):
                    problems.append(f'{where}: "level" must be a whole number from 1 to 10.')
                if "kid" in player and not isinstance(player.get("kid"), bool):
                    problems.append(f'{where}: "kid" must be true or false.')

    operations = inputs.get("operations")
    if "operations" in inputs:
        if not isinstance(operations, list) or not operations:
            problems.append(f'{INPUTS}: "operations" must be a list with at least one of {", ".join(OPERATIONS)}.')
        else:
            for op in operations:
                if op not in OPERATIONS:
                    problems.append(f'{INPUTS}: "{op}" is not an operation; use any of {", ".join(OPERATIONS)}.')
            if len(set(map(str, operations))) != len(operations):
                problems.append(f'{INPUTS}: "operations" names an operation twice.')

    secs = inputs.get("seconds")
    if "seconds" in inputs and (not is_int(secs) or not 0 <= secs <= 600):
        problems.append(f'{INPUTS}: "seconds" must be a whole number from 0 (untimed) to 600.')

    theme = inputs.get("theme")
    names = sorted(path.stem for path in THEMES.glob("*.css"))
    if "theme" in inputs and (not isinstance(theme, str) or theme not in names):
        problems.append(f'{INPUTS}: "theme" must be one of {", ".join(names)}.')
    return problems


def main():
    project = Path.cwd()
    source = project / INPUTS
    if not source.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{INPUTS} is not valid JSON: {error}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{INPUTS} must hold one JSON object; inputs.example.json shows every key.")
        return 2
    problems = problems_in(inputs)
    if problems:
        print("\n".join(problems))
        return 2

    config = {key: inputs[key] for key in ("players", "operations", "seconds", "theme")}
    config["players"] = [
        {"name": p["name"].strip(), "level": p["level"], "kid": p["kid"]} for p in inputs["players"]
    ]

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(HERE / "badge.js", out / "badge.js")
    shutil.copyfile(HERE / "assets" / "icon.svg", out / "icon.svg")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config)};\n", encoding="utf-8")

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
