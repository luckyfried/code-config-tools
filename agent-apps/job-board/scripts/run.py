#!/usr/bin/env python3
"""Makes the Job Board page for the project in the current folder, and runs its inbox.

With no flag: reads job-board.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/job-board/, and writes config.js (the inputs) and theme.css (the chosen theme) beside its index.html.

  --serve [--port N]  make the page, then serve it and the inbox on 127.0.0.1 until stopped
  --check             print the app's health, one fact per line; exit 1 when it is not ok
  --work              take every pending choice once and print one line for each
  --add FILE          add or update openings from a JSON list in FILE

The openings and the person's choices live in data/job-board/ in the current folder. Standard library only.
"""
import argparse
import json
import shutil
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
sys.dont_write_bytecode = True  # the app folder holds only what ships
sys.path.insert(0, str(HERE))

from runtime import Conflict, Rejected, Runtime  # noqa: E402

SLUG = "job-board"
KIND = "opportunities"
INPUTS = f"{SLUG}.inputs.json"
OUT = Path("out") / SLUG
ACTIONS = {"yes": "local", "no": "local", "later": "local", "apply": "external"}
STATUSES = ("new", "yes", "no", "later")
EVENT_STATES = ("pending", "working", "completed", "failed", "cancelled")
REQUIRED = ["name", "ask", "columns", "theme", "sample"]
OPTIONAL = ["sampleInbox", "_notes"]
FIELDS = ["id", "role", "company", "link", "location", "pay", "remote", "facts", "found_at", "status", "agent_notes", "applied_at"]
TEXT_FIELDS = ["role", "company", "link", "location", "pay"]
DONE = {"yes": "Moved to yes.", "no": "Moved to no.", "later": "Kept for later."}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def opening_problems(item, where, need_all):
    """Plain lines naming what is wrong with one opening."""
    if not isinstance(item, dict):
        return [f"{where} must be an object with a role, a company, and a link."]
    problems = []
    say = problems.append
    for key in item:
        if key not in FIELDS and key != "revision":
            say(f'{where} has the key "{key}", which Job Board does not use.')
    for key in TEXT_FIELDS:
        if key in item and not isinstance(item[key], str):
            say(f'{where} "{key}" must be text.')
    if need_all:
        for key in ("id", "role", "company", "link"):
            if not (isinstance(item.get(key), str) and item[key].strip()):
                say(f'{where} needs "{key}".')
    if "remote" in item and item["remote"] not in (True, False, None):
        say(f'{where} "remote" must be true, false, or null.')
    for key in ("facts", "agent_notes"):
        if key in item and not (isinstance(item[key], list) and all(isinstance(x, str) for x in item[key])):
            say(f'{where} "{key}" must be a list of sentences.')
    if "status" in item and not (isinstance(item["status"], str) and item["status"] in STATUSES):
        say(f'{where} "status" must be new, yes, no, or later.')
    for key in ("found_at", "applied_at"):
        if key in item and not isinstance(item[key], str):
            say(f'{where} "{key}" must be a time like "2026-10-21T08:12:00Z".')
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
            say(f'{INPUTS} has the key "{key}", which Job Board does not use.')
    if "name" in inputs and not isinstance(inputs["name"], str):
        say('"name" must be text: your first name, for the board\'s title.')
    if "ask" in inputs and not isinstance(inputs["ask"], str):
        say('"ask" must be text: what you are looking for, in one sentence.')
    cols = inputs.get("columns")
    if "columns" in inputs and not (
        isinstance(cols, list) and cols and all(isinstance(c, str) and c in STATUSES for c in cols) and len(set(cols)) == len(cols)
    ):
        say('"columns" must list the columns to show, from "new", "yes", "later", and "no", each once.')
    if "theme" in inputs and not (isinstance(inputs["theme"], str) and inputs["theme"] in themes):
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')
    sample = inputs.get("sample")
    ids = set()
    if "sample" in inputs:
        if not isinstance(sample, list):
            say('"sample" must be a list of openings, like the one in inputs.example.json.')
        else:
            for n, item in enumerate(sample, 1):
                problems += opening_problems(item, f'"sample" item {n}', need_all=True)
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
                if not (isinstance(e.get("action"), str) and e["action"] in ACTIONS):
                    say(f'{where} "action" must be one of: {", ".join(ACTIONS)}.')
                if not (isinstance(e.get("target"), str) and e["target"] in ids):
                    say(f'{where} "target" must be the id of an opening in "sample".')
                if not (isinstance(e.get("status"), str) and e["status"] in EVENT_STATES):
                    say(f'{where} "status" must be one of: {", ".join(EVENT_STATES)}.')
                if not isinstance(e.get("at"), str):
                    say(f'{where} needs "at", a time like "2026-10-21T08:12:00Z".')
    return problems


def make():
    """Writes out/job-board/; returns the exit code."""
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


def handle(rt, event):
    """Does one claimed choice; returns (result, line)."""
    kind, _, id = (event.get("target") or "").partition("/")
    record = rt.get(kind, id) if kind == KIND and id else None
    if record is None:
        raise Rejected(f"The opening {event.get('target')} is not on the board.")
    job = record["body"]
    title = f"{job.get('role', id)} at {job.get('company', '')}".strip()
    if ACTIONS[event["action"]] == "external":
        return (
            {"next": "ask the person, then act", "done_at": now()},
            f"Ask before: {event['action']} to {title} ({job.get('link', '')})",
        )
    status = event["action"]
    if job.get("status") == status:
        return {"status": status, "note": DONE[status], "done_at": now()}, f"{title} was already {status}."
    rt.put(KIND, id, {**job, "status": status}, expect=record["revision"])
    return {"status": status, "note": DONE[status], "done_at": now()}, f"{title}: {DONE[status].lower()[:-1]}."


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
        print(f"{path} must hold a JSON list of openings.")
        return 2
    rt = runtime()
    code = 0
    for n, item in enumerate(items, 1):
        problems = opening_problems(item, f"Item {n}", need_all=False)
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
                body = {"role": "", "company": "", "link": "", "location": "", "pay": "", "remote": None,
                        "facts": [], "found_at": now(), "status": "new", "agent_notes": [], **item}
                record = rt.put(KIND, id, body, expect=0)
                print(f"Added {body['role'] or record['id']} at {body['company']} ({KIND}/{record['id']}).")
            else:
                expect = current["revision"] if revision is None else revision
                body = {**current["body"], **item}
                record = rt.put(KIND, id, body, expect=expect)
                print(f"Updated {body['role']} at {body['company']} ({KIND}/{id}, revision {record['revision']}).")
        except Conflict as conflict:
            print(f"Not changed: {conflict} Read it again and add the change to the newer revision.")
            code = 1
        except Rejected as refused:
            print(f"Item {n}: {refused}")
            code = 2
    return code


def main():
    parser = argparse.ArgumentParser(description="Make and run the Job Board page for the project in this folder.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="make the page, then serve it and the inbox")
    group.add_argument("--check", action="store_true", help="print the app's health")
    group.add_argument("--work", action="store_true", help="take every pending choice once")
    group.add_argument("--add", metavar="FILE", help="add or update openings from a JSON list")
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
