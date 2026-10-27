"""Cook Mode: turns cook-mode.inputs.json in the current folder into a site.

Run it from the project folder:

    python3 <agent-apps root>/cook-mode/scripts/run.py

It reads the recipe book, checks every key, copies the built site from dist/
into out/cook-mode/, copies each recipe photo into out/cook-mode/media/,
writes theme.css from the chosen theme and config.js from the inputs, and
prints the line that serves it. Two runs on the same inputs write the same
bytes. Python 3 standard library only.
"""

import json
import re
import shutil
import sys
from pathlib import Path

APP = "cook-mode"
INPUTS = f"{APP}.inputs.json"
HERE = Path(__file__).resolve().parents[1]
DIST = HERE / "dist"
THEMES = HERE / "src" / "themes"
AUTO = "auto"
LIGHT, DARK = "butcher", "midnight"

TOP_KEYS = {"kitchen": str, "units": str, "theme": str, "pinned": str, "tags": list, "recipes": list}
RECIPE_KEYS = {
    "id": str,
    "title": str,
    "servings": int,
    "minutes": int,
    "cuisine": str,
    "tags": list,
    "ingredients": list,
    "steps": list,
}
RECIPE_OPTIONAL = {"image": str}
INGREDIENT_KEYS = {"amount", "unit", "name", "step"}
ID = re.compile(r"[a-z0-9][a-z0-9-]*")
TYPE_WORDS = {str: "text", int: "a whole number", list: "a list"}


def theme_names():
    return sorted([path.stem for path in THEMES.glob("*.css")] + [AUTO])


def theme_css(name):
    """The theme file's text; auto is butcher with midnight inside a dark-mode query."""
    if name != AUTO:
        return (THEMES / f"{name}.css").read_text(encoding="utf-8")
    light = (THEMES / f"{LIGHT}.css").read_text(encoding="utf-8").rstrip()
    dark = (THEMES / f"{DARK}.css").read_text(encoding="utf-8").rstrip()
    inner = "\n".join(("  " + line) if line else line for line in dark.splitlines())
    return f"{light}\n\n@media (prefers-color-scheme: dark) {{\n{inner}\n}}\n"


def is_type(value, kind):
    if kind is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, kind)


def check(inputs, project):
    """Every problem with the inputs, one plain line each; the media to copy."""
    problems = []
    media = []
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object."], media

    for key, kind in TOP_KEYS.items():
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
        elif not is_type(inputs[key], kind):
            problems.append(f'{INPUTS}: "{key}" must be {TYPE_WORDS[kind]}.')
    for key in inputs:
        if key not in TOP_KEYS and key != "_notes":
            problems.append(f'{INPUTS} has a key this app does not use: "{key}".')

    if isinstance(inputs.get("kitchen"), str) and not inputs["kitchen"].strip():
        problems.append(f'{INPUTS}: "kitchen" is empty; give the site a name.')
    if isinstance(inputs.get("units"), str) and inputs["units"] not in ("metric", "us"):
        problems.append(f'{INPUTS}: "units" must be "metric" or "us", not "{inputs["units"]}".')
    if isinstance(inputs.get("theme"), str) and inputs["theme"] not in theme_names():
        problems.append(f'{INPUTS}: there is no theme "{inputs["theme"]}"; the themes are {", ".join(theme_names())}.')
    if isinstance(inputs.get("tags"), list) and not all(isinstance(tag, str) for tag in inputs["tags"]):
        problems.append(f'{INPUTS}: "tags" must be a list of words.')

    recipes = inputs.get("recipes")
    ids = []
    if isinstance(recipes, list):
        if not recipes:
            problems.append(f'{INPUTS}: "recipes" is empty; add at least one recipe.')
        for number, recipe in enumerate(recipes, start=1):
            problems.extend(check_recipe(recipe, number, ids, project, media))
        if isinstance(inputs.get("pinned"), str) and ids and inputs["pinned"] not in ids:
            problems.append(f'{INPUTS}: "pinned" names "{inputs["pinned"]}", which is not the id of any recipe.')
    return problems, media


def check_recipe(recipe, number, ids, project, media):
    problems = []
    if not isinstance(recipe, dict):
        return [f"{INPUTS}: recipe {number} must be an object."]
    label = f'recipe "{recipe["id"]}"' if isinstance(recipe.get("id"), str) else f"recipe {number}"
    for key, kind in RECIPE_KEYS.items():
        if key not in recipe:
            problems.append(f'{INPUTS}: {label} is missing the key "{key}".')
        elif not is_type(recipe[key], kind):
            problems.append(f'{INPUTS}: {label}: "{key}" must be {TYPE_WORDS[kind]}.')
    for key in recipe:
        if key not in RECIPE_KEYS and key not in RECIPE_OPTIONAL:
            problems.append(f'{INPUTS}: {label} has a key this app does not use: "{key}".')

    rid = recipe.get("id")
    if isinstance(rid, str):
        if not ID.fullmatch(rid):
            problems.append(f'{INPUTS}: {label}: "id" must be lowercase letters, digits, and hyphens.')
        if rid in ids:
            problems.append(f'{INPUTS}: two recipes share the id "{rid}".')
        ids.append(rid)
    for key in ("servings", "minutes"):
        if is_type(recipe.get(key), int) and recipe[key] < 1:
            problems.append(f'{INPUTS}: {label}: "{key}" must be 1 or more.')

    steps = recipe.get("steps")
    if isinstance(steps, list):
        if not steps:
            problems.append(f'{INPUTS}: {label} has no steps.')
        elif not all(isinstance(step, str) and step.strip() for step in steps):
            problems.append(f'{INPUTS}: {label}: every step must be a line of text.')
    step_count = len(steps) if isinstance(steps, list) else 0

    ingredients = recipe.get("ingredients")
    if isinstance(ingredients, list):
        for place, item in enumerate(ingredients, start=1):
            where = f"{label}, ingredient {place}"
            if not isinstance(item, dict):
                problems.append(f"{INPUTS}: {where} must be an object.")
                continue
            for key in ("amount", "unit", "name"):
                if key not in item:
                    problems.append(f'{INPUTS}: {where} is missing the key "{key}".')
            for key in item:
                if key not in INGREDIENT_KEYS:
                    problems.append(f'{INPUTS}: {where} has a key this app does not use: "{key}".')
            amount = item.get("amount")
            if "amount" in item and amount is not None and (isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0):
                problems.append(f'{INPUTS}: {where}: "amount" must be a number, or null for "to taste".')
            if "unit" in item and not isinstance(item["unit"], str):
                problems.append(f'{INPUTS}: {where}: "unit" must be text; use "" for counted things.')
            if "name" in item and (not isinstance(item["name"], str) or not item["name"].strip()):
                problems.append(f'{INPUTS}: {where}: "name" must be text.')
            if "step" in item:
                step = item["step"]
                if not is_type(step, int) or not 1 <= step <= max(step_count, 1):
                    problems.append(f'{INPUTS}: {where}: "step" must be a step number from 1 to {step_count}.')

    image = recipe.get("image")
    if isinstance(image, str):
        source = (project / image).resolve()
        if not source.is_file():
            problems.append(f'{INPUTS}: {label}: the image "{image}" is not a file beside the inputs.')
        elif isinstance(rid, str):
            media.append((rid, source))
    return problems


def main():
    project = Path.cwd()
    source = project / INPUTS
    if not source.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"{INPUTS} is not valid JSON: line {error.lineno}, column {error.colno}: {error.msg}.")
        return 2

    problems, media = check(inputs, project)
    if problems:
        print("\n".join(problems))
        return 2
    if not (DIST / "index.html").is_file():
        print("This app's dist/ folder is missing; rebuild it with npm ci && npm run build in the app folder.")
        return 2

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    if media:
        (out / "media").mkdir()
        photos = {}
        for rid, path in media:
            name = f"{rid}{path.suffix.lower()}"
            shutil.copyfile(path, out / "media" / name)
            photos[rid] = f"./media/{name}"
        config["recipes"] = [
            {**recipe, "image": photos[recipe["id"]]} if recipe["id"] in photos else recipe for recipe in config["recipes"]
        ]

    (out / "theme.css").write_text(theme_css(inputs["theme"]), encoding="utf-8")
    payload = json.dumps(config, ensure_ascii=False, indent=2)
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {payload};\n", encoding="utf-8")

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
