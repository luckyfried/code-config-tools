"""Write Plate Log for the project in the current folder.

Reads plate-log.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/plate-log/, and writes config.js (the inputs) and theme.css (the chosen theme) beside index.html.
Two runs on the same inputs give the same files.

    cd <project> && python3 <agent-apps root>/plate-log/scripts/run.py
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

APP = "plate-log"
APP_DIR = Path(__file__).resolve().parents[1]
DIST = APP_DIR / "dist"
THEMES = APP_DIR / "src" / "themes"
USUAL = ("breakfast", "lunch", "dinner", "snack")
MACROS = ("calories", "protein", "carbs", "fat")
KEYS = {"name", "targets", "foods", "meals", "water", "theme", "startLog", "_notes"}
FOOD_KEYS = {"id", "name", "serving", "calories", "protein", "carbs", "fat", "usual"}
ENTRY_KEYS = {"daysAgo", "foodId", "servings", "meal"}


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def check(inputs, theme_names):
    problems = []
    src = f"{APP}.inputs.json"

    for key in sorted(set(inputs) - KEYS):
        problems.append(f'{src} has a key this app does not use: "{key}".')

    for key in ("name", "targets", "foods", "meals"):
        if key not in inputs:
            problems.append(f'{src} is missing the key "{key}".')

    if "name" in inputs and not is_text(inputs["name"]):
        problems.append(f'"name" in {src} must be some text, such as "Sam".')

    targets = inputs.get("targets")
    if targets is not None:
        if not isinstance(targets, dict):
            problems.append(f'"targets" in {src} must hold calories, protein, carbs, and fat.')
        else:
            for key in MACROS:
                if key not in targets:
                    problems.append(f'"targets" in {src} is missing "{key}".')
                elif not is_number(targets[key]) or targets[key] <= 0:
                    problems.append(f'"targets.{key}" in {src} must be a number above 0.')
            for key in sorted(set(targets) - set(MACROS)):
                problems.append(f'"targets" in {src} has a key this app does not use: "{key}".')

    food_ids = set()
    foods = inputs.get("foods")
    if foods is not None:
        if not isinstance(foods, list) or not foods:
            problems.append(f'"foods" in {src} must list at least one food.')
        else:
            for n, food in enumerate(foods, start=1):
                where = f"Food {n} in {src}"
                if not isinstance(food, dict):
                    problems.append(f"{where} must be an object with id, name, serving, and the numbers.")
                    continue
                label = food.get("id") if is_text(food.get("id")) else n
                where = f'Food "{label}" in {src}'
                for key in ("id", "name", "serving"):
                    if key not in food:
                        problems.append(f'{where} is missing "{key}".')
                    elif not is_text(food[key]):
                        problems.append(f'{where} needs some text for "{key}".')
                for key in MACROS:
                    if key not in food:
                        problems.append(f'{where} is missing "{key}".')
                    elif not is_number(food[key]) or food[key] < 0:
                        problems.append(f'{where} needs a number of 0 or more for "{key}".')
                if "usual" in food and food["usual"] not in USUAL:
                    problems.append(f'{where} has "usual" set to {json.dumps(food["usual"])}; use breakfast, lunch, dinner, or snack.')
                for key in sorted(set(food) - FOOD_KEYS):
                    problems.append(f'{where} has a key this app does not use: "{key}".')
                if is_text(food.get("id")):
                    if food["id"] in food_ids:
                        problems.append(f'Two foods in {src} share the id "{food["id"]}"; each needs its own.')
                    food_ids.add(food["id"])

    meals = inputs.get("meals")
    if meals is not None:
        if not isinstance(meals, list) or not meals or not all(is_text(m) for m in meals):
            problems.append(f'"meals" in {src} must list the meal names, such as ["Breakfast", "Lunch", "Dinner", "Snacks"].')
            meals = None
        elif len(set(meals)) != len(meals):
            problems.append(f'"meals" in {src} names a meal twice.')

    if "water" in inputs and not isinstance(inputs["water"], bool):
        problems.append(f'"water" in {src} must be true or false.')

    if "theme" in inputs and inputs["theme"] not in theme_names:
        problems.append(f'"theme" in {src} is {json.dumps(inputs["theme"])}; the themes are {", ".join(theme_names)}.')

    log = inputs.get("startLog")
    if log is not None:
        if not isinstance(log, list):
            problems.append(f'"startLog" in {src} must be a list of logged foods.')
        else:
            for n, entry in enumerate(log, start=1):
                where = f"Entry {n} of startLog in {src}"
                if not isinstance(entry, dict):
                    problems.append(f"{where} must be an object with daysAgo, foodId, servings, and meal.")
                    continue
                for key in sorted(ENTRY_KEYS - set(entry)):
                    problems.append(f'{where} is missing "{key}".')
                for key in sorted(set(entry) - ENTRY_KEYS):
                    problems.append(f'{where} has a key this app does not use: "{key}".')
                days = entry.get("daysAgo")
                if "daysAgo" in entry and (not isinstance(days, int) or isinstance(days, bool) or days < 0):
                    problems.append(f"{where} needs a whole number of 0 or more for daysAgo.")
                if "foodId" in entry and food_ids and entry["foodId"] not in food_ids:
                    problems.append(f'{where} names the food "{entry["foodId"]}", which is not in "foods".')
                if "servings" in entry and (not is_number(entry["servings"]) or entry["servings"] <= 0):
                    problems.append(f"{where} needs a number above 0 for servings.")
                if "meal" in entry and meals and entry["meal"] not in meals:
                    problems.append(f'{where} names the meal {json.dumps(entry["meal"])}, which is not in "meals".')

    return problems


def main():
    parser = argparse.ArgumentParser(description="Write Plate Log into out/plate-log/ from plate-log.inputs.json.")
    parser.parse_args()

    project = Path.cwd()
    inputs_path = project / f"{APP}.inputs.json"
    if not inputs_path.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"{APP}.inputs.json is not valid JSON: line {err.lineno}, column {err.colno}: {err.msg}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{APP}.inputs.json must be one object with the keys inputs.example.json shows.")
        return 2

    theme_names = sorted(p.stem for p in THEMES.glob("*.css"))
    problems = check(inputs, theme_names)
    if problems:
        print("\n".join(problems))
        return 2
    if not (DIST / "index.html").is_file():
        print(f"The built page is missing from {DIST}; build it with npm ci && npm run build in {APP_DIR}.")
        return 2

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    config.setdefault("theme", "auto")
    config.setdefault("water", False)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    (out / "theme.css").write_bytes((THEMES / f"{config['theme']}.css").read_bytes())
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
