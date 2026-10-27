"""Make the Pack List page from pack-list.inputs.json in the current folder.

Run from the project folder:

    python3 <agent-apps root>/pack-list/scripts/run.py

It reads pack-list.inputs.json, checks every key, copies the built page into
out/pack-list/, and writes theme.css and config.js there. Two runs on the same
inputs give the same files, byte for byte. Standard library only.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "pack-list"
APP_DIR = Path(__file__).resolve().parents[1]
DIST = APP_DIR / "dist"
THEMES = APP_DIR / "src" / "themes"
BADGE = APP_DIR / "badge.js"
LIGHT, DARK, AUTO = "canvas", "night-flight", "auto"

KEYS = {"templates", "always", "limitKg", "trip", "theme", "_notes"}


def theme_names():
    return sorted([p.stem for p in THEMES.glob("*.css")] + [AUTO])


def theme_css(name):
    """The chosen theme file; auto is canvas with night-flight for devices set to dark."""
    if name != AUTO:
        return (THEMES / f"{name}.css").read_text(encoding="utf-8")
    light = (THEMES / f"{LIGHT}.css").read_text(encoding="utf-8")
    dark = (THEMES / f"{DARK}.css").read_text(encoding="utf-8")
    inner = "".join(f"  {line}" if line.strip() else line for line in dark.splitlines(keepends=True))
    return f"{light}\n@media (prefers-color-scheme: dark) {{\n{inner}}}\n"


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def item_problems(item, where):
    if isinstance(item, str):
        return [] if item.strip() else [f'{where} is an empty name.']
    if not isinstance(item, dict):
        return [f"{where} must be a name or an object with a name."]
    problems = []
    if not isinstance(item.get("name"), str) or not item["name"].strip():
        problems.append(f'{where} is missing the key "name".')
    if "weight" in item and (not is_number(item["weight"]) or item["weight"] < 0):
        problems.append(f'{where} has a "weight" that is not a number of kilograms.')
    for key in sorted(set(item) - {"name", "weight"}):
        problems.append(f'{where} has a key it does not take: "{key}".')
    return problems


def problems_of(inputs):
    name = f"{APP}.inputs.json"
    if not isinstance(inputs, dict):
        return [f"{name} must hold one JSON object."]
    problems = []
    for key in ("templates", "theme"):
        if key not in inputs:
            problems.append(f'{name} is missing the key "{key}".')
    for key in sorted(set(inputs) - KEYS):
        problems.append(f'{name} has a key it does not take: "{key}".')

    templates = inputs.get("templates", [])
    ids = set()
    if not isinstance(templates, list) or ("templates" in inputs and not templates):
        if "templates" in inputs:
            problems.append(f'{name} needs at least one trip in "templates".')
        templates = []
    for t_index, template in enumerate(templates):
        where = f'{name} templates[{t_index}]'
        if not isinstance(template, dict):
            problems.append(f"{where} must be an object.")
            continue
        for key in ("id", "label", "groups"):
            if key not in template:
                problems.append(f'{where} is missing the key "{key}".')
        if "id" in template:
            if not isinstance(template["id"], str) or not template["id"].strip():
                problems.append(f'{where} has an "id" that is not text.')
            elif template["id"] in ids:
                problems.append(f'{where} uses the id "{template["id"]}" a second time.')
            else:
                ids.add(template["id"])
        if "label" in template and not isinstance(template["label"], str):
            problems.append(f'{where} has a "label" that is not text.')
        groups = template.get("groups", [])
        if not isinstance(groups, list):
            problems.append(f'{where} has "groups" that is not a list.')
            groups = []
        for g_index, group in enumerate(groups):
            g_where = f"{where}.groups[{g_index}]"
            if not isinstance(group, dict):
                problems.append(f"{g_where} must be an object.")
                continue
            if not isinstance(group.get("label"), str) or not group["label"].strip():
                problems.append(f'{g_where} is missing the key "label".')
            items = group.get("items")
            if not isinstance(items, list):
                problems.append(f'{g_where} is missing the key "items".')
                continue
            for i_index, item in enumerate(items):
                problems.extend(item_problems(item, f"{g_where}.items[{i_index}]"))

    always = inputs.get("always", [])
    if not isinstance(always, list):
        problems.append(f'{name} has "always" that is not a list.')
    else:
        for index, item in enumerate(always):
            problems.extend(item_problems(item, f"{name} always[{index}]"))

    if "limitKg" in inputs and inputs["limitKg"] is not None:
        if not is_number(inputs["limitKg"]) or inputs["limitKg"] <= 0:
            problems.append(f'{name} has a "limitKg" that is not a number of kilograms above 0.')

    trip = inputs.get("trip")
    if trip is not None:
        if not isinstance(trip, dict):
            problems.append(f'{name} has a "trip" that is not an object.')
        else:
            for key in sorted(set(trip) - {"name", "templates", "packed"}):
                problems.append(f'{name} trip has a key it does not take: "{key}".')
            if "name" in trip and not isinstance(trip["name"], str):
                problems.append(f'{name} trip has a "name" that is not text.')
            for key in ("templates", "packed"):
                if key in trip and (
                    not isinstance(trip[key], list) or not all(isinstance(v, str) for v in trip[key])
                ):
                    problems.append(f'{name} trip has "{key}" that is not a list of text.')
            for template_id in trip.get("templates", []) if isinstance(trip.get("templates"), list) else []:
                if isinstance(template_id, str) and ids and template_id not in ids:
                    problems.append(f'{name} trip names the template "{template_id}", which is not in "templates".')

    theme = inputs.get("theme")
    if "theme" in inputs and theme not in theme_names():
        problems.append(f'{name} has the theme "{theme}"; the themes are {", ".join(theme_names())}.')
    return problems


def count_files(folder):
    return sum(1 for p in folder.rglob("*") if p.is_file())


def main():
    inputs_path = Path.cwd() / f"{APP}.inputs.json"
    if not inputs_path.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"{APP}.inputs.json is not valid JSON: line {error.lineno}, column {error.colno}.")
        return 2
    problems = problems_of(inputs)
    if problems:
        for line in problems:
            print(line)
        return 2
    if not (DIST / "index.html").is_file():
        print(f"The built page is missing from {APP}/dist; rebuild it with npm ci && npm run build in the app folder.")
        return 2

    out = Path.cwd() / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    (out / "theme.css").write_text(theme_css(inputs["theme"]), encoding="utf-8")
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False, sort_keys=True)};\n", encoding="utf-8"
    )

    print(
        f"Wrote out/{APP}/ ({count_files(out)} files). "
        f"Serve it: python3 -m http.server 8000 --directory out/{APP}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
