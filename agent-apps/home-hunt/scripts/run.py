#!/usr/bin/env python3
"""Makes the Home Hunt page for the project in the current folder, and runs its inbox.

With no flag: reads home-hunt.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/home-hunt/, and writes config.js (the inputs) and theme.css (the chosen theme) beside its index.html.

  --serve [--port N]  make the page, then serve it and the inbox on 127.0.0.1 until stopped
  --check             print the app's health, one fact per line; exit 1 when it is not ok
  --work              take every pending choice once and print one line for each
  --add FILE          add homes, or add to homes already there, from a JSON list in FILE

The homes and the person's choices live in data/home-hunt/ in the current folder. Standard library only.
"""
import argparse
import json
import shutil
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
APP = HERE.parent
sys.dont_write_bytecode = True  # the app folder holds only what ships
sys.path.insert(0, str(HERE))

from runtime import Conflict, Rejected, Runtime  # noqa: E402

SLUG = "home-hunt"
KIND = "homes"
INPUTS = f"{SLUG}.inputs.json"
OUT = Path("out") / SLUG
ACTIONS = {"yes": "local", "no": "local", "maybe": "local", "note": "local", "ask": "external"}
STATUSES = ("new", "yes", "no", "maybe")
EVENT_STATES = ("pending", "working", "completed", "failed", "cancelled")
COMPARE_ROWS = ("price", "price_per_area", "rooms", "baths", "area", "commute", "place")
REQUIRED = ["name", "ask", "currency", "units", "compare_rows", "theme", "sample"]
OPTIONAL = ["sampleInbox", "_notes"]
FIELDS = ["id", "title", "image", "photos", "source", "color", "price", "period", "rooms", "baths", "area", "place",
          "commute", "checked", "status", "notes", "questions", "found_at", "agent_notes"]
TEXT_FIELDS = ["title", "image", "source", "color", "place", "found_at"]
LONGEST = 2000
DONE = {"yes": "Marked yes.", "no": "Marked no.", "maybe": "Kept as a maybe."}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def pictures(home):
    """Every picture a home names, the main one first."""
    found = [home.get("image")] + list(home.get("photos") or [])
    return [p for p in dict.fromkeys(found) if isinstance(p, str) and p]


def home_problems(item, where, need_all):
    """Plain lines naming what is wrong with one home."""
    if not isinstance(item, dict):
        return [f"{where} must be an object with an id, a title, and a price."]
    problems = []
    say = problems.append
    for key in item:
        if key not in FIELDS and key != "revision":
            say(f'{where} has the key "{key}", which Home Hunt does not use.')
    for key in TEXT_FIELDS:
        if key in item and not isinstance(item[key], str):
            say(f'{where} "{key}" must be text.')
    if need_all:
        for key in ("id", "title"):
            if not (isinstance(item.get(key), str) and item[key].strip()):
                say(f'{where} needs "{key}".')
        if "price" not in item:
            say(f'{where} needs "price".')
    for key in ("price", "rooms", "baths"):
        if key in item and not is_number(item[key]):
            say(f'{where} "{key}" must be a number.')
    if "area" in item and item["area"] is not None and not is_number(item["area"]):
        say(f'{where} "area" must be a number, or null when it is not known.')
    if "commute" in item and item["commute"] is not None and not isinstance(item["commute"], str):
        say(f'{where} "commute" must be text, like "24 min by bus", or null.')
    if "period" in item and item["period"] not in ("sale", "month"):
        say(f'{where} "period" must be "sale" or "month".')
    if "status" in item and item["status"] not in STATUSES:
        say(f'{where} "status" must be new, yes, no, or maybe.')
    if "photos" in item and not (isinstance(item["photos"], list) and all(isinstance(p, str) for p in item["photos"])):
        say(f'{where} "photos" must be a list of picture paths or https addresses.')
    if "agent_notes" in item and not (isinstance(item["agent_notes"], list) and all(isinstance(x, str) for x in item["agent_notes"])):
        say(f'{where} "agent_notes" must be a list of sentences.')
    if "checked" in item and not (
        isinstance(item["checked"], list)
        and all(isinstance(c, dict) and isinstance(c.get("fact"), str) and isinstance(c.get("source"), str) for c in item["checked"])
    ):
        say(f'{where} "checked" must be a list of {{"fact": ..., "source": <link>}}.')
    if "notes" in item and not (
        isinstance(item["notes"], list)
        and all(isinstance(n, dict) and isinstance(n.get("text"), str) and isinstance(n.get("at"), str) for n in item["notes"])
    ):
        say(f'{where} "notes" must be a list of {{"text": ..., "at": <time>}}.')
    if "questions" in item and not (
        isinstance(item["questions"], list)
        and all(isinstance(q, dict) and isinstance(q.get("question"), str) for q in item["questions"])
    ):
        say(f'{where} "questions" must be a list of {{"question": ..., "answer": ...}}.')
    if "revision" in item and (not isinstance(item["revision"], int) or isinstance(item["revision"], bool)):
        say(f'{where} "revision" must be a whole number.')
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
            say(f'{INPUTS} has the key "{key}", which Home Hunt does not use.')
    if "name" in inputs and not isinstance(inputs["name"], str):
        say('"name" must be text: whose hunt this is, for the board\'s title.')
    if "ask" in inputs and not isinstance(inputs["ask"], str):
        say('"ask" must be text: where, buy or rent, the budget, the rooms, and the must-haves.')
    if "currency" in inputs and not (isinstance(inputs["currency"], str) and len(inputs["currency"]) == 3 and inputs["currency"].isalpha()):
        say('"currency" must be a three-letter code such as "USD", "EUR", or "GBP".')
    if "units" in inputs and inputs["units"] not in ("sqft", "m2"):
        say('"units" must be "sqft" or "m2".')
    rows = inputs.get("compare_rows")
    if "compare_rows" in inputs and not (
        isinstance(rows, list) and rows and all(isinstance(r, str) and r in COMPARE_ROWS for r in rows) and len(set(rows)) == len(rows)
    ):
        say(f'"compare_rows" must list the facts compare shows, each once, from: {", ".join(COMPARE_ROWS)}.')
    if "theme" in inputs and not (isinstance(inputs["theme"], str) and inputs["theme"] in themes):
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')
    sample = inputs.get("sample")
    ids = set()
    if "sample" in inputs:
        if not isinstance(sample, list):
            say('"sample" must be a list of homes, like the one in inputs.example.json.')
        else:
            for n, item in enumerate(sample, 1):
                problems += home_problems(item, f'"sample" home {n}', need_all=True)
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ids.add(item["id"])
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
                if e.get("action") not in ACTIONS:
                    say(f'{where} "action" must be one of: {", ".join(ACTIONS)}.')
                if e.get("target") not in ids:
                    say(f'{where} "target" must be the id of a home in "sample".')
                if e.get("status") not in EVENT_STATES:
                    say(f'{where} "status" must be one of: {", ".join(EVENT_STATES)}.')
                if not isinstance(e.get("at"), str):
                    say(f'{where} needs "at", a time like "2026-10-21T08:12:00Z".')
    return problems


def local_pictures(inputs, dist):
    """The relative picture paths the sample names that the built page does not ship, and which of them are missing."""
    wanted = []
    for item in inputs.get("sample") or []:
        for p in pictures(item):
            if urlparse(p).scheme or p.startswith("/") or ".." in Path(p).parts:
                continue
            if not (dist / p).is_file():
                wanted.append(p)
    return wanted, [p for p in wanted if not Path(p).is_file()]


def make():
    """Writes out/home-hunt/; returns the exit code."""
    src = Path(INPUTS)
    if not src.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{INPUTS} is not valid JSON: {e}.")
        return 2
    themes = {p.stem for p in (APP / "src" / "themes").glob("*.css")}
    problems = check(inputs, themes)
    dist = APP / "dist"
    if not problems and not (dist / "index.html").is_file():
        problems.append(f"The built page is missing from {dist}; run npm ci and npm run build in {APP}.")
    if not problems:
        wanted, missing = local_pictures(inputs, dist)
        problems += [f'The sample names the picture "{p}", which is not in this folder or the app.' for p in missing]
    if problems:
        print("\n".join(problems))
        return 2
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(dist, OUT)
    for p in wanted:
        (OUT / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, OUT / p)
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (OUT / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8"
    )
    shutil.copyfile(APP / "src" / "themes" / f"{inputs['theme']}.css", OUT / "theme.css")
    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT.as_posix()}/ ({files} files). Serve it: python3 -m http.server 8000 --directory {OUT.as_posix()}")
    return 0


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


def site(home):
    return urlparse(home.get("source") or "").hostname or "the listing"


def text_of(event, field):
    value = (event.get("payload") or {}).get(field)
    if not (isinstance(value, str) and value.strip()):
        raise Rejected(f"The {event['action']} has no {field}.")
    if len(value) > LONGEST:
        raise Rejected(f"The {field} is longer than {LONGEST:,} characters.")
    return value.strip()


def handle(rt, event):
    """Does one claimed choice; returns (result, line)."""
    kind, _, id = (event.get("target") or "").partition("/")
    record = rt.get(kind, id) if kind == KIND and id else None
    if record is None:
        raise Rejected(f"The home {event.get('target')} is not on the board.")
    home = record["body"]
    title = home.get("title") or id
    action = event["action"]
    if action == "ask":
        question = text_of(event, "question")
        asked = home.get("questions") or []
        if not any(q.get("question") == question and q.get("asked_at") == event["at"] for q in asked):
            entry = {"question": question, "asked_at": event["at"], "answer": None, "answered_at": None}
            rt.put(KIND, id, {**home, "questions": asked + [entry]}, expect=record["revision"])
        return (
            {"next": "ask the person, then act", "done_at": now()},
            f"Ask before: asking {site(home)} about {title}: {question}",
        )
    if action == "note":
        text = text_of(event, "text")
        notes = home.get("notes") or []
        if not any(n.get("text") == text and n.get("at") == event["at"] for n in notes):
            rt.put(KIND, id, {**home, "notes": notes + [{"text": text, "at": event["at"]}]}, expect=record["revision"])
        return {"note": "Note kept.", "done_at": now()}, f"{title}: kept the note \"{text[:80]}\"."
    if home.get("status") == action:
        return {"status": action, "note": DONE[action], "done_at": now()}, f"{title} was already {action}."
    rt.put(KIND, id, {**home, "status": action}, expect=record["revision"])
    return {"status": action, "note": DONE[action], "done_at": now()}, f"{title}: {DONE[action].lower()[:-1]}."


def work():
    rt = runtime()
    count = 0
    while (event := rt.claim("run.py --work")) is not None:
        count += 1
        try:
            result, line = handle(rt, event)
        except (Conflict, Rejected) as problem:
            rt.fail(event["id"], str(problem), event["attempts"])
            print(f"Could not {event['action']} {event.get('target')}: {problem}")
            continue
        rt.complete(event["id"], result, event["attempts"])
        print(line)
    if count == 0:
        print("No choices are waiting.")
    return 0


def merge(current, item):
    """The stored home with the agent's additions on top. The person's status and notes stay as they are; checked
    facts and agent notes are added to; a question already there takes its answer, and a new one is added."""
    body = {**current, **{k: v for k, v in item.items() if k not in ("status", "notes", "checked", "agent_notes", "questions")}}
    seen = {(c["fact"], c["source"]) for c in current.get("checked") or []}
    body["checked"] = list(current.get("checked") or []) + [
        c for c in item.get("checked") or [] if (c["fact"], c["source"]) not in seen
    ]
    body["agent_notes"] = list(dict.fromkeys(list(current.get("agent_notes") or []) + list(item.get("agent_notes") or [])))
    questions = [dict(q) for q in current.get("questions") or []]
    for q in item.get("questions") or []:
        match = next(
            (old for old in questions if old.get("question") == q["question"] and q.get("asked_at") in (None, old.get("asked_at"))),
            None,
        )
        if match is None:
            questions.append({"question": q["question"], "asked_at": q.get("asked_at") or now(),
                              "answer": q.get("answer"), "answered_at": q.get("answered_at") or (now() if q.get("answer") else None)})
        elif q.get("answer"):
            match["answer"] = q["answer"]
            match["answered_at"] = q.get("answered_at") or match.get("answered_at") or now()
    body["questions"] = questions
    return body


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
        print(f"{path} must hold a JSON list of homes.")
        return 2
    rt = runtime()
    code = 0
    for n, item in enumerate(items, 1):
        problems = home_problems(item, f"Item {n}", need_all=False)
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
                missing = [k for k in ("title", "price") if k not in item]
                if missing:
                    print(f"Item {n} is a new home and needs {' and '.join(missing)}.")
                    code = 2
                    continue
                body = {"title": "", "image": "", "photos": [], "source": "", "color": "#9aa59b", "price": 0,
                        "period": "sale", "rooms": 0, "baths": 0, "area": None, "place": "", "commute": None,
                        "checked": [], "status": "new", "notes": [], "questions": [], "found_at": now(),
                        "agent_notes": [], **item}
                if not body["image"] and body["photos"]:
                    body["image"] = body["photos"][0]
                record = rt.put(KIND, id, body, expect=0)
                print(f"Added {body['title']} ({KIND}/{record['id']}).")
            else:
                expect = current["revision"] if revision is None else revision
                body = merge(current["body"], item)
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
    parser = argparse.ArgumentParser(description="Make and run the Home Hunt page for the project in this folder.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="make the page, then serve it and the inbox")
    group.add_argument("--check", action="store_true", help="print the app's health")
    group.add_argument("--work", action="store_true", help="take every pending choice once")
    group.add_argument("--add", metavar="FILE", help="add homes, or add to homes already there, from a JSON list")
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
            print(f"The board is already being served; its process id is in {rt.data / 'server.pid'}.")
            return 2
        code = make()
        if code or not args.serve:
            return code
        print(f"Serving the board at http://127.0.0.1:{args.port}/ (Ctrl+C stops it).", flush=True)
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
