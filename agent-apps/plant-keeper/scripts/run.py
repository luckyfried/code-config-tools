"""Writes Plant Keeper into out/plant-keeper/ from plant-keeper.inputs.json in the current folder.

Run it from the project folder:

    python3 <agent-apps root>/plant-keeper/scripts/run.py

It copies the page, writes theme.css from the chosen theme and config.js from the inputs, and prints how to
serve the folder. Two runs on the same inputs write the same bytes.
"""

import json
import shutil
import sys
from pathlib import Path

SLUG = "plant-keeper"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"
BADGE = APP / "badge.js"

TOP_KEYS = {"name": str, "plants": list, "rooms": list, "theme": str}
PLANT_KEYS = {"id": str, "name": str, "type": str, "intervalDays": int, "light": str, "room": str}
PLANT_OPTIONAL = {"wateredDaysAgo": (int, float), "notes": str}
TYPE_WORDS = {str: "text", list: "a list", int: "a whole number", (int, float): "a number"}


def problems_in(inputs):
    """Every problem with the inputs, one plain line each."""
    name = f"{SLUG}.inputs.json"
    if not isinstance(inputs, dict):
        return [f"{name} must hold one JSON object."]
    found = []
    for key, kind in TOP_KEYS.items():
        if key not in inputs:
            found.append(f'{name} is missing the key "{key}".')
        elif not isinstance(inputs[key], kind):
            found.append(f'In {name}, "{key}" must be {TYPE_WORDS[kind]}.')
    for key in inputs:
        if key not in TOP_KEYS and key != "_notes":
            found.append(f'{name} has the key "{key}", which this app does not use.')
    if isinstance(inputs.get("name"), str) and not inputs["name"].strip():
        found.append(f'In {name}, "name" is empty.')
    if isinstance(inputs.get("rooms"), list):
        for i, room in enumerate(inputs["rooms"]):
            if not isinstance(room, str) or not room.strip():
                found.append(f'In {name}, rooms[{i}] must be a room name.')
    if isinstance(inputs.get("plants"), list):
        if not inputs["plants"]:
            found.append(f'In {name}, "plants" has no plants in it.')
        seen = set()
        for i, plant in enumerate(inputs["plants"]):
            where = f"plants[{i}]"
            if not isinstance(plant, dict):
                found.append(f"In {name}, {where} must be an object.")
                continue
            for key, kind in PLANT_KEYS.items():
                value = plant.get(key)
                if key not in plant:
                    found.append(f'In {name}, {where} is missing the key "{key}".')
                elif not isinstance(value, kind) or isinstance(value, bool):
                    found.append(f'In {name}, {where}.{key} must be {TYPE_WORDS[kind]}.')
            for key, kind in PLANT_OPTIONAL.items():
                value = plant.get(key)
                if key in plant and (not isinstance(value, kind) or isinstance(value, bool)):
                    found.append(f'In {name}, {where}.{key} must be {TYPE_WORDS[kind]}.')
            for key in plant:
                if key not in PLANT_KEYS and key not in PLANT_OPTIONAL:
                    found.append(f'In {name}, {where} has the key "{key}", which this app does not use.')
            interval = plant.get("intervalDays")
            if isinstance(interval, int) and not isinstance(interval, bool) and interval < 1:
                found.append(f"In {name}, {where}.intervalDays must be 1 or more.")
            ago = plant.get("wateredDaysAgo")
            if isinstance(ago, (int, float)) and not isinstance(ago, bool) and ago < 0:
                found.append(f"In {name}, {where}.wateredDaysAgo can't be below 0.")
            pid = plant.get("id")
            if isinstance(pid, str):
                if not pid or not all(c.isalnum() or c in "-_" for c in pid):
                    found.append(f"In {name}, {where}.id must be letters, digits, hyphens, or underscores.")
                elif pid in seen:
                    found.append(f'In {name}, two plants have the id "{pid}"; each needs its own.')
                seen.add(pid)
    theme = inputs.get("theme")
    if isinstance(theme, str):
        names = sorted(p.stem for p in THEMES.glob("*.css"))
        if theme not in names:
            found.append(f'In {name}, "theme" is "{theme}"; the themes are {", ".join(names)}.')
    return found


def main():
    project = Path.cwd()
    source = project / f"{SLUG}.inputs.json"
    if not source.is_file():
        print(f"Make {SLUG}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{SLUG}.inputs.json is not readable JSON: {error}.")
        return 2
    found = problems_in(inputs)
    if found:
        print("\n".join(found))
        return 2

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    (out / "theme.css").write_bytes((THEMES / f"{config['theme']}.css").read_bytes())
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
        newline="\n",
    )
    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
