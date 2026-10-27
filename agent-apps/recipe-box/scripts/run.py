#!/usr/bin/env python3
"""Makes the Recipe Box page for the project in the current folder, and runs its inbox.

With no flag: reads recipe-box.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/recipe-box/, and writes config.js (the inputs) and theme.css (the chosen theme) beside its index.html.

  --serve [--port N]  make the page, then serve it and the inbox on 127.0.0.1 until stopped
  --check             print the app's health, one fact per line; exit 1 when it is not ok
  --work              take every pending choice once and print one line for each
  --add FILE          add or update recipes from a JSON list in FILE

The recipes, the shopping lists, and the person's choices live in data/recipe-box/ in the current folder.
Standard library only.
"""
import argparse
import json
import shutil
import signal
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
sys.dont_write_bytecode = True  # the app folder holds only what ships
sys.path.insert(0, str(HERE))

from runtime import Conflict, Rejected, Runtime  # noqa: E402

SLUG = "recipe-box"
KIND = "recipes"
LISTS = "lists"
INPUTS = f"{SLUG}.inputs.json"
OUT = Path("out") / SLUG
ACTIONS = {"keep": "local", "skip": "local", "week": "local", "plan-week": "local"}
STATUSES = ("new", "kept", "skipped", "week")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES = dict(zip(DAYS, ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")))
EVENT_STATES = ("pending", "working", "completed", "failed", "cancelled")
AISLES = ("produce", "bakery", "meat & fish", "dairy & eggs", "pantry", "spices", "frozen", "other")
REQUIRED = ["name", "ask", "household", "week_start", "theme", "sample"]
OPTIONAL = ["sampleInbox", "copy", "_notes"]
FIELDS = ["id", "title", "image", "source", "color", "minutes", "servings", "ingredients", "steps", "tags", "why",
          "status", "day", "found_at", "agent_notes"]
TEXT_FIELDS = ["title", "image", "source", "color", "why", "found_at"]
LIST_FIELDS = ["id", "week_of", "recipes", "items", "made_at"]
WHOLE_UNITS = ("g", "ml")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_whole(value, low=1):
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def is_words(value):
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def ingredient_problems(item, where):
    if not isinstance(item, dict):
        return [f"{where} must be an object with a name, an amount, a unit, and an aisle."]
    problems = []
    if not (isinstance(item.get("name"), str) and item["name"].strip()):
        problems.append(f'{where} needs "name".')
    if item.get("amount") is not None and not (is_number(item["amount"]) and item["amount"] > 0):
        problems.append(f'{where} "amount" must be a number above zero, or null.')
    if item.get("unit") is not None and not isinstance(item["unit"], str):
        problems.append(f'{where} "unit" must be text, like "g" or "cup", or null.')
    if not (isinstance(item.get("aisle"), str) and item["aisle"].strip()):
        problems.append(f'{where} needs "aisle", one of: {", ".join(AISLES)}.')
    return problems


def recipe_problems(item, where, need_all):
    """Plain lines naming what is wrong with one recipe."""
    if not isinstance(item, dict):
        return [f"{where} must be an object with a title, an image, and its ingredients."]
    problems = []
    say = problems.append
    for key in item:
        if key not in FIELDS and key != "revision":
            say(f'{where} has the key "{key}", which Recipe Box does not use.')
    for key in TEXT_FIELDS:
        if key in item and not isinstance(item[key], str):
            say(f'{where} "{key}" must be text.')
    if need_all:
        for key in ("id", "title", "image", "color"):
            if not (isinstance(item.get(key), str) and item[key].strip()):
                say(f'{where} needs "{key}".')
    for key in ("minutes", "servings"):
        if key in item and not is_whole(item[key]):
            say(f'{where} "{key}" must be a whole number above zero.')
        elif need_all and key not in item:
            say(f'{where} needs "{key}".')
    if "ingredients" in item:
        if not isinstance(item["ingredients"], list):
            say(f'{where} "ingredients" must be a list.')
        else:
            for n, ing in enumerate(item["ingredients"], 1):
                problems += ingredient_problems(ing, f"{where} ingredient {n}")
    for key in ("steps", "tags", "agent_notes"):
        if key in item and not is_words(item[key]):
            say(f'{where} "{key}" must be a list of text.')
    if "status" in item and item["status"] not in STATUSES:
        say(f'{where} "status" must be new, kept, skipped, or week.')
    if "day" in item and item["day"] is not None and item["day"] not in DAYS:
        say(f'{where} "day" must be one of {", ".join(DAYS)}, or null.')
    if "revision" in item and not is_whole(item["revision"]):
        say(f'{where} "revision" must be a whole number.')
    return problems


def list_problems(item, where, ids):
    if not isinstance(item, dict):
        return [f"{where} must be a shopping list object."]
    problems = []
    for key in LIST_FIELDS:
        if key not in item:
            problems.append(f'{where} needs "{key}".')
    if not (isinstance(item.get("recipes"), list) and all(r in ids for r in item.get("recipes", []))):
        problems.append(f'{where} "recipes" must list ids of recipes in "sample".')
    if not isinstance(item.get("items"), list):
        problems.append(f'{where} "items" must be a list.')
    else:
        for n, line in enumerate(item["items"], 1):
            problems += ingredient_problems(line, f"{where} item {n}")
    return problems


def check(inputs, themes):
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object, like inputs.example.json."]
    problems = []
    say = problems.append
    for key in REQUIRED:
        if key not in inputs:
            say(f'{INPUTS} is missing the key "{key}".')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL:
            say(f'{INPUTS} has the key "{key}", which Recipe Box does not use.')
    if "name" in inputs and not isinstance(inputs["name"], str):
        say('"name" must be text: your first name, for the box\'s title.')
    if "ask" in inputs and not isinstance(inputs["ask"], str):
        say('"ask" must be text: what you like to cook, in one sentence.')
    if "household" in inputs and not is_whole(inputs["household"]):
        say('"household" must be a whole number: how many people you cook for.')
    if "week_start" in inputs and inputs["week_start"] not in ("monday", "sunday"):
        say('"week_start" must be "monday" or "sunday".')
    if "theme" in inputs and not (isinstance(inputs["theme"], str) and inputs["theme"] in themes):
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')
    if "copy" in inputs and not (isinstance(inputs["copy"], dict) and all(isinstance(v, str) for v in inputs["copy"].values())):
        say('"copy" must be an object of words by key, like {"planWeek": "Plan the week"}.')
    ids = set()
    if "sample" in inputs:
        sample = inputs["sample"]
        if not (isinstance(sample, dict) and isinstance(sample.get(KIND), list) and isinstance(sample.get(LISTS), list)):
            say('"sample" must be an object with "recipes" and "lists", like the one in inputs.example.json.')
        else:
            for n, item in enumerate(sample[KIND], 1):
                problems += recipe_problems(item, f'"sample" recipe {n}', need_all=True)
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ids.add(item["id"])
            for n, item in enumerate(sample[LISTS], 1):
                problems += list_problems(item, f'"sample" list {n}', ids)
    if "sampleInbox" in inputs:
        box = inputs["sampleInbox"]
        if not isinstance(box, list):
            say('"sampleInbox" must be a list of choices.')
        else:
            for n, e in enumerate(box, 1):
                where = f'"sampleInbox" item {n}'
                if not isinstance(e, dict):
                    say(f"{where} must be an object with an action, a target, a status, and a time.")
                    continue
                if not (isinstance(e.get("action"), str) and e["action"] in ACTIONS):
                    say(f'{where} "action" must be one of: {", ".join(ACTIONS)}.')
                if e.get("target") is not None and e["target"] not in ids:
                    say(f'{where} "target" must be the id of a recipe in "sample", or null.')
                if e.get("status") not in EVENT_STATES:
                    say(f'{where} "status" must be one of: {", ".join(EVENT_STATES)}.')
                if not isinstance(e.get("at"), str):
                    say(f'{where} needs "at", a time like "2026-10-21T08:12:00Z".')
    return problems


def read_inputs():
    """The checked inputs, or (None, the lines saying what is wrong)."""
    src = Path(INPUTS)
    if not src.is_file():
        return None, [f"Make {INPUTS} in this folder first; inputs.example.json shows every key."]
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return None, [f"{INPUTS} is not valid JSON: {e}."]
    themes = {p.stem for p in (APP / "src" / "themes").glob("*.css")}
    problems = check(inputs, themes)
    return (None, problems) if problems else (inputs, [])


def make():
    """Writes out/recipe-box/; returns the exit code."""
    inputs, problems = read_inputs()
    if problems:
        print("\n".join(problems))
        return 2
    dist = APP / "dist"
    if not (dist / "index.html").is_file():
        print(f"The built page is missing from {dist}; run npm ci and npm run build in {APP}.")
        return 2
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(dist, OUT)
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (OUT / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8"
    )
    shutil.copyfile(APP / "src" / "themes" / f"{inputs['theme']}.css", OUT / "theme.css")
    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT.as_posix()}/ ({files} files). Serve it: python3 -m http.server 8000 --directory {OUT.as_posix()}")
    return 0


# The shopping list -------------------------------------------------------------------------------------------------

def week_start_day(week_start, today=None):
    """The first day of the current week, Monday or Sunday."""
    today = today or date.today()
    back = today.weekday() if week_start == "monday" else (today.weekday() + 1) % 7
    return today - timedelta(days=back)


def week_id(first_day):
    """The ISO week, like "2026-W43", of the Monday inside the week that starts on first_day."""
    monday = first_day if first_day.weekday() == 0 else first_day + timedelta(days=(7 - first_day.weekday()) % 7)
    return monday.strftime("%G-W%V")


def tidy(amount, unit):
    """Grams and milliliters to the nearest 5, everything else to the nearest quarter."""
    if amount is None:
        return None
    if unit in WHOLE_UNITS:
        return max(5, int(round(amount / 5.0)) * 5)
    quarters = max(1, round(amount * 4))
    value = quarters / 4
    return int(value) if value == int(value) else value


def shopping_list(recipes, household, first_day):
    """The list record for the given recipe bodies (each with its "id"), scaled to household people."""
    merged = {}
    for recipe in recipes:
        scale = household / max(1, recipe.get("servings") or 1)
        for ing in recipe.get("ingredients", []):
            name = ing["name"].strip()
            unit = ing.get("unit")
            key = (name.lower(), unit)
            line = merged.setdefault(key, {"name": name, "amount": None, "unit": unit,
                                           "aisle": ing.get("aisle") or "other", "from": []})
            if ing.get("amount") is not None:
                line["amount"] = (line["amount"] or 0) + ing["amount"] * scale
            if recipe["id"] not in line["from"]:
                line["from"].append(recipe["id"])
    order = {aisle: n for n, aisle in enumerate(AISLES)}
    items = []
    for line in merged.values():
        line["amount"] = tidy(line["amount"], line["unit"])
        items.append(line)
    items.sort(key=lambda x: (order.get(x["aisle"], len(AISLES)), x["aisle"], x["name"].lower(), x["unit"] or ""))
    return {
        "id": week_id(first_day),
        "week_of": first_day.isoformat(),
        "recipes": [r["id"] for r in recipes],
        "items": items,
        "made_at": now(),
    }


# The runtime ------------------------------------------------------------------------------------------------------

def stop(signum, frame):
    """A stop by process id ends the server the way Ctrl+C does, so server.pid is removed."""
    raise KeyboardInterrupt


def runtime():
    return Runtime(app=SLUG, project=Path.cwd(), actions=ACTIONS)


def check_health():
    report = runtime().health()
    for key, value in report.items():
        if isinstance(value, dict):
            value = ", ".join(f"{n} {k}" for k, n in value.items())
        elif isinstance(value, bool):
            value = "yes" if value else "no"
        print(f"{key}: {value}")
    return 0 if report["ok"] else 1


def plan_week(rt):
    inputs, problems = read_inputs()
    if problems:
        raise Rejected("The week needs " + INPUTS + " for the household size: " + problems[0])
    week = [{**r["body"], "id": r["id"]} for r in rt.list(KIND) if r["body"].get("status") == "week"]
    if not week:
        raise Rejected("No recipe is on this week yet.")
    week.sort(key=lambda r: (DAYS.index(r["day"]) if r.get("day") in DAYS else len(DAYS), r["title"]))
    first_day = week_start_day(inputs["week_start"])
    body = shopping_list(week, inputs["household"], first_day)
    list_id = body.pop("id")
    current = rt.get(LISTS, list_id)
    rt.put(LISTS, list_id, body, expect=current["revision"] if current else 0)
    count = len(body["items"])
    when = first_day.strftime("%B %-d")
    return (
        {"list": list_id, "items": count, "note": f"{count} items for the week of {when}.", "done_at": now()},
        f"Shopping list for the week of {body['week_of']}: {count} items from {len(week)} "
        + ("recipe" if len(week) == 1 else "recipes"),
    )


def handle(rt, event):
    """Does one claimed choice; returns (result, line)."""
    action = event["action"]
    if ACTIONS[action] == "external":
        return {"next": "ask the person, then act", "done_at": now()}, f"Ask before: {action} {event.get('target')}"
    if action == "plan-week":
        return plan_week(rt)
    kind, _, id = (event.get("target") or "").partition("/")
    record = rt.get(kind, id) if kind == KIND and id else None
    if record is None:
        raise Rejected(f"The recipe {event.get('target')} is not in the box.")
    recipe = record["body"]
    title = recipe.get("title", id)
    if action == "week":
        day = (event.get("payload") or {}).get("day")
        if day not in DAYS:
            raise Rejected(f'A week choice needs a day, one of {", ".join(DAYS)}.')
        status, note = "week", f"On {DAY_NAMES[day]}."
    else:
        day = None
        status, note = ("kept", "Kept.") if action == "keep" else ("skipped", "Skipped.")
    result = {"status": status, "day": day, "note": note, "done_at": now()}
    if recipe.get("status") == status and recipe.get("day") == day:
        return result, f"{title} was already {note[0].lower()}{note[1:-1]}."
    rt.put(KIND, id, {**recipe, "status": status, "day": day}, expect=record["revision"])
    return result, f"{title}: {note[0].lower()}{note[1:-1]}."


def work():
    rt = runtime()
    count = 0
    while (event := rt.claim("run.py --work")) is not None:
        count += 1
        try:
            result, line = handle(rt, event)
        except (Conflict, Rejected) as problem:
            rt.fail(event["id"], str(problem), event["attempts"])
            print(f"Could not {event['action']} {event.get('target') or 'the week'}: {problem}")
            continue
        rt.complete(event["id"], result, event["attempts"])
        print(line)
    if count == 0:
        print("No choices are waiting.")
    return 0


def add(path):
    try:
        items = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        print(f"Could not read {path}: {e.strerror}.")
        return 2
    except ValueError as e:
        print(f"{path} is not valid JSON: {e}.")
        return 2
    if not isinstance(items, list):
        print(f"{path} must hold a JSON list of recipes.")
        return 2
    rt = runtime()
    code = 0
    for n, item in enumerate(items, 1):
        problems = recipe_problems(item, f"Item {n}", need_all=False)
        if isinstance(item, dict) and item.get("id") is not None and not isinstance(item.get("id"), str):
            problems.append(f'Item {n} "id" must be text.')
        if problems:
            print("\n".join(problems))
            code = 2
            continue
        item = dict(item)
        id = item.pop("id", None)
        revision = item.pop("revision", None)
        try:
            current = rt.get(KIND, id) if id else None
            if current is None:
                body = {"title": "", "image": "", "source": "", "color": "#c8b8a0", "minutes": 30, "servings": 2,
                        "ingredients": [], "steps": [], "tags": [], "why": "", "status": "new", "day": None,
                        "found_at": now(), "agent_notes": [], **item}
                record = rt.put(KIND, id, body, expect=0)
                print(f"Added {body['title'] or record['id']} ({KIND}/{record['id']}).")
            else:
                expect = current["revision"] if revision is None else revision
                body = {**current["body"], **item}
                record = rt.put(KIND, id, body, expect=expect)
                print(f"Updated {body['title']} ({KIND}/{id}, revision {record['revision']}).")
        except Conflict as conflict:
            print(f"Not changed: {conflict} Read it again and add the change to the newer revision.")
            code = 1
        except Rejected as refused:
            print(f"Item {n}: {refused}")
            code = 2
    return code


def main():
    parser = argparse.ArgumentParser(description="Make and run the Recipe Box page for the project in this folder.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="make the page, then serve it and the inbox")
    group.add_argument("--check", action="store_true", help="print the app's health")
    group.add_argument("--work", action="store_true", help="take every pending choice once")
    group.add_argument("--add", metavar="FILE", help="add or update recipes from a JSON list")
    parser.add_argument("--port", type=int, default=8000, help="the port for --serve (8000)")
    args = parser.parse_args()
    try:
        if args.check:
            return check_health()
        if args.work:
            return work()
        if args.add:
            return add(args.add)
        rt = runtime()
        if args.serve and rt.health()["server_running"]:
            print(f"The box is already being served; its process id is in {rt.data / 'server.pid'}.")
            return 2
        code = make()
        if code or not args.serve:
            return code
        print(f"Serving the box at http://127.0.0.1:{args.port}/ (Ctrl+C stops it).", flush=True)
        signal.signal(signal.SIGTERM, stop)
        try:
            rt.serve(OUT.resolve(), args.port)
        except KeyboardInterrupt:
            pass
        return 0
    except Rejected as refused:
        print(refused)
        return 2
    except OSError as e:
        print(f"{e.filename or 'A file'}: {e.strerror}.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
