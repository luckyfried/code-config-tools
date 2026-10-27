"""Writes the Meal Week page for the plan in ./meal-week.inputs.json.

Run from the project folder:
    python3 <agent-apps root>/meal-week/scripts/run.py

Reads  ./meal-week.inputs.json
Writes ./out/meal-week/ (the page, config.js, theme.css)
"""

import datetime as dt
import json
import shutil
import sys
from pathlib import Path

APP = "meal-week"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
FILE = f"{APP}.inputs.json"

KEYS = {
    "weekOf": str,
    "name": str,
    "people": int,
    "slots": list,
    "days": list,
    "aisles": list,
    "pantry": list,
    "otherWeeks": list,
    "theme": str,
}
REQUIRED = ("weekOf", "days", "aisles")
DEFAULTS = {"people": 2, "slots": ["breakfast", "lunch", "dinner"], "pantry": [], "otherWeeks": [], "theme": "auto"}
TYPE_WORDS = {str: "text", int: "a whole number", list: "a list"}
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_KEYS = ("name", "cuisine", "minutes", "ingredients")
INGREDIENT_KEYS = ("amount", "unit", "name", "aisle")


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def key_of(name):
    return " ".join(name.split()).lower()


def load_inputs(path):
    if not path.exists():
        fail([f"Make {FILE} in this folder first; inputs.example.json shows every key."])
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail([f"{FILE} is not valid JSON (line {err.lineno}, column {err.colno}): {err.msg}."])
    if not isinstance(raw, dict):
        fail([f"{FILE} must hold one object with the keys inputs.example.json shows."])
    return raw


def is_kind(value, kind):
    return isinstance(value, kind) and not isinstance(value, bool)


def check_week_of(text, where, problems):
    try:
        day = dt.date.fromisoformat(text) if len(text) == 10 else None
    except ValueError:
        day = None
    if day is None:
        problems.append(f'{where} "weekOf" must be a date written YYYY-MM-DD, like 2026-10-26; it is "{text}".')
        return None
    if day.weekday() != 0:
        monday = day - dt.timedelta(days=day.weekday())
        problems.append(f'{where} "weekOf" is {text}, a {DAY_NAMES[day.weekday()]}; '
                        f"use the Monday, {monday.isoformat()}.")
        return None
    return day


def check_days(days, slots, aisles, where, problems):
    """Checks one week's seven days; returns the ingredient names that week puts on the list."""
    names = set()
    if not is_kind(days, list) or len(days) != 7:
        problems.append(f'{where} "days" must list seven days, mon to sun.')
        return names
    for n, day in enumerate(days):
        label = f"{where} day {n + 1}"
        if not isinstance(day, dict):
            problems.append(f"{label} must be an object with day and meals.")
            continue
        for key in day:
            if key not in ("day", "meals"):
                problems.append(f'{label} has the key "{key}"; a day takes day and meals.')
        if str(day.get("day", "")).strip().lower()[:3] != DAYS[n]:
            problems.append(f'{label} must be "{DAYS[n]}"; the days run mon to sun in order.')
            continue
        label = f"{where} {DAY_NAMES[n]}"
        meals = day.get("meals", {})
        if not isinstance(meals, dict):
            problems.append(f'{label} "meals" must be an object with a key for each slot it fills.')
            continue
        for slot, meal in meals.items():
            if slot not in slots:
                problems.append(f'{label} has the meal "{slot}", which is not in slots ({", ".join(slots)}).')
                continue
            if meal is None:
                continue
            spot = f"{label} {slot}"
            if not isinstance(meal, dict):
                problems.append(f"{spot} must be an object with name, cuisine, minutes, and ingredients.")
                continue
            for key in meal:
                if key not in MEAL_KEYS:
                    problems.append(f'{spot} has the key "{key}"; a meal takes {", ".join(MEAL_KEYS)}.')
            if not is_kind(meal.get("name"), str) or not meal["name"].strip():
                problems.append(f'{spot} is missing its "name".')
            if "cuisine" in meal and not is_kind(meal["cuisine"], str):
                problems.append(f'{spot} "cuisine" must be text, like "Italian".')
            if "minutes" in meal and (not is_kind(meal["minutes"], int) or meal["minutes"] < 0):
                problems.append(f'{spot} "minutes" must be a whole number of minutes.')
            ingredients = meal.get("ingredients", [])
            if not is_kind(ingredients, list):
                problems.append(f'{spot} "ingredients" must be a list.')
                continue
            for i, item in enumerate(ingredients, start=1):
                at = f"{spot} ingredient {i}"
                if not isinstance(item, dict):
                    problems.append(f"{at} must be an object with amount, unit, name, and aisle.")
                    continue
                for key in item:
                    if key not in INGREDIENT_KEYS:
                        problems.append(f'{at} has the key "{key}"; an ingredient takes {", ".join(INGREDIENT_KEYS)}.')
                name = item.get("name")
                if not is_kind(name, str) or not name.strip():
                    problems.append(f'{at} is missing its "name".')
                    continue
                at = f'{spot} "{name.strip()}"'
                amount = item.get("amount")
                if not (is_kind(amount, int) or is_kind(amount, float)) or amount <= 0:
                    problems.append(f'{at} needs an "amount" above zero, like 2 or 0.5.')
                if not is_kind(item.get("unit", ""), str):
                    problems.append(f'{at} "unit" must be text: "g", "cup", or "" for a count.')
                aisle = item.get("aisle")
                if aisle not in aisles:
                    problems.append(f'{at} has the aisle "{aisle}", which is not in aisles ({", ".join(aisles)}).')
                names.add(key_of(name))
    return names


def validate(raw):
    problems = []
    inputs = {k: v for k, v in raw.items() if k != "_notes"}
    for key in inputs:
        if key not in KEYS:
            problems.append(f'{FILE} has the key "{key}", which this app does not read. The keys are: {", ".join(KEYS)}.')
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{FILE} is missing the key "{key}".')
    for key, kind in KEYS.items():
        if key in inputs and not is_kind(inputs[key], kind):
            problems.append(f'"{key}" in {FILE} must be {TYPE_WORDS[kind]}.')
    if problems:
        fail(problems)

    plan = {**DEFAULTS, **inputs}
    if plan["people"] < 1:
        problems.append(f'"people" in {FILE} is how many the amounts feed, 1 or more; it is {plan["people"]}.')
    for key in ("slots", "aisles", "pantry"):
        if not all(is_kind(v, str) and v.strip() for v in plan[key]):
            problems.append(f'"{key}" in {FILE} must be a list of names.')
    if not plan["slots"]:
        problems.append(f'"slots" in {FILE} needs at least one meal name, like "dinner".')
    if not plan["aisles"]:
        problems.append(f'"aisles" in {FILE} needs at least one aisle, like "Produce".')
    if "name" in plan and not plan["name"].strip():
        problems.append(f'"name" in {FILE} is empty; leave it out for "Week of" and the date.')

    themes = sorted(p.stem for p in (SITE / "themes").glob("*.css"))
    if plan["theme"] not in themes:
        problems.append(f'"theme" is "{plan["theme"]}"; the themes are {", ".join(themes)}.')
    if problems:
        fail(problems)

    check_week_of(plan["weekOf"], "The plan's", problems)
    names = check_days(plan["days"], plan["slots"], plan["aisles"], "The plan's", problems)
    seen = {plan["weekOf"]}
    for n, week in enumerate(plan["otherWeeks"], start=1):
        where = f"otherWeeks entry {n}"
        if not isinstance(week, dict):
            problems.append(f"{where} must be an object with weekOf, name, and days.")
            continue
        for key in week:
            if key not in ("weekOf", "name", "days"):
                problems.append(f'{where} has the key "{key}"; a week takes weekOf, name, and days.')
        if not is_kind(week.get("weekOf"), str):
            problems.append(f'{where} is missing its "weekOf".')
            continue
        where = f"The week of {week['weekOf']}"
        check_week_of(week["weekOf"], f"{where}:", problems)
        if week["weekOf"] in seen:
            problems.append(f"{where} is in the plan twice; each week appears once.")
        seen.add(week["weekOf"])
        if "name" in week and (not is_kind(week["name"], str) or not week["name"].strip()):
            problems.append(f'{where} "name" must be text; leave it out for "Week of" and the date.')
        check_days(week.get("days"), plan["slots"], plan["aisles"], where, problems)
    if problems:
        fail(problems)

    pantry = {key_of(p) for p in plan["pantry"]}
    return plan, len(names - pantry)


def write(plan):
    out = Path.cwd() / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out, ignore=shutil.ignore_patterns("config.js", "theme.css"))
    shutil.copyfile(SITE / "themes" / f"{plan['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(plan, ensure_ascii=False, sort_keys=True)};\n", encoding="utf-8")
    return out, sum(1 for p in out.rglob("*") if p.is_file())


def main():
    raw = load_inputs(Path.cwd() / FILE)
    plan, items = validate(raw)
    out, count = write(plan)
    monday = dt.date.fromisoformat(plan["weekOf"])
    print(f"The week of {monday.strftime('%B')} {monday.day} needs {items} items from the store "
          f"(every ingredient name, less the pantry).")
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
