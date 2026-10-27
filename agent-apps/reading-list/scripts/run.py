#!/usr/bin/env python3
"""Makes the Reading List page for the project in the current folder, and runs its inbox.

With no flag: reads reading-list.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/reading-list/, and writes config.js (the inputs) and theme.css (the chosen theme) beside its index.html.

  --serve [--port N]  make the page, then serve it and the inbox on 127.0.0.1 until stopped
  --check             print the app's health, one fact per line; exit 1 when it is not ok
  --work              take every pending choice once and print one line for each
  --add FILE          add or update articles from a JSON list in FILE

The articles, the topics, and the person's choices live in data/reading-list/ in the current folder. Standard
library only.
"""
import argparse
import json
import re
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

SLUG = "reading-list"
KIND = "articles"
TOPICS = "topics"
INPUTS = f"{SLUG}.inputs.json"
OUT = Path("out") / SLUG
ACTIONS = {"later": "local", "skip": "local", "more": "local", "deeper": "local"}
STATUSES = ("new", "later", "skipped")
EVENT_STATES = ("pending", "working", "completed", "failed", "cancelled")
REQUIRED = ["name", "topics", "theme", "sample"]
OPTIONAL = ["sources", "per_day", "_notes"]
FIELDS = ["id", "headline", "source", "link", "image", "color", "topic", "summary", "minutes", "published_at",
          "found_at", "status", "like", "deep", "agent_notes"]
TEXT_FIELDS = ["headline", "source", "link", "image", "color", "topic", "published_at", "found_at"]
NAME = re.compile(r"^[A-Za-z0-9_-]+$")
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
PLACED = {"later": ("later", "kept for later"), "skip": ("skipped", "skipped")}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_text_list(value):
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def deep_problems(deep, where):
    if deep is None:
        return []
    if not isinstance(deep, dict):
        return [f'{where} "deep" must be null or an object with paragraphs, coverage, and at.']
    problems = []
    if not (is_text_list(deep.get("paragraphs")) and deep["paragraphs"]):
        problems.append(f'{where} "deep" needs "paragraphs", a list of paragraphs.')
    coverage = deep.get("coverage", [])
    if not (isinstance(coverage, list) and all(
        isinstance(c, dict) and all(isinstance(c.get(k), str) for k in ("headline", "source", "link")) for c in coverage
    )):
        problems.append(f'{where} "deep" "coverage" must list stories, each with a headline, a source, and a link.')
    if not isinstance(deep.get("at"), str):
        problems.append(f'{where} "deep" needs "at", the time the brief was written.')
    for key in deep:
        if key not in ("paragraphs", "coverage", "at"):
            problems.append(f'{where} "deep" has the key "{key}", which Reading List does not use.')
    return problems


def article_problems(item, where, need_all):
    """Plain lines naming what is wrong with one article."""
    if not isinstance(item, dict):
        return [f"{where} must be an object with a headline, a source, a link, and a topic."]
    problems = []
    say = problems.append
    for key in item:
        if key not in FIELDS and key != "revision":
            say(f'{where} has the key "{key}", which Reading List does not use.')
    if "id" in item and not (isinstance(item["id"], str) and NAME.match(item["id"])):
        say(f'{where} "id" must be letters, digits, hyphens, or underscores.')
    for key in TEXT_FIELDS:
        if key in item and not isinstance(item[key], str):
            say(f'{where} "{key}" must be text.')
    if need_all:
        for key in ("id", "headline", "source", "link", "topic"):
            if not (isinstance(item.get(key), str) and item[key].strip()):
                say(f'{where} needs "{key}".')
    if "color" in item and isinstance(item["color"], str) and item["color"] and not COLOR.match(item["color"]):
        say(f'{where} "color" must be a color like "#2E8B57".')
    if "summary" in item and not (is_text_list(item["summary"]) and 1 <= len(item["summary"]) <= 3):
        say(f'{where} "summary" must be a list of up to three sentences.')
    if "agent_notes" in item and not is_text_list(item["agent_notes"]):
        say(f'{where} "agent_notes" must be a list of sentences.')
    if "minutes" in item and not (isinstance(item["minutes"], int) and not isinstance(item["minutes"], bool)
                                  and item["minutes"] > 0):
        say(f'{where} "minutes" must be a whole number of minutes to read it.')
    if "status" in item and item["status"] not in STATUSES:
        say(f'{where} "status" must be new, later, or skipped.')
    if "like" in item and not (item["like"] is None or isinstance(item["like"], str)):
        say(f'{where} "like" must be the id of the article that asked for more like it, or null.')
    if "deep" in item:
        problems += deep_problems(item["deep"], where)
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
            say(f'{INPUTS} has the key "{key}", which Reading List does not use.')
    if "name" in inputs and not isinstance(inputs["name"], str):
        say('"name" must be text: your first name, for the masthead.')
    topic_ids = set()
    if "topics" in inputs:
        topics = inputs["topics"]
        if not (isinstance(topics, list) and topics):
            say('"topics" must list your sections, each with an id, a name, and a color.')
        else:
            for n, t in enumerate(topics, 1):
                if not (isinstance(t, dict) and isinstance(t.get("id"), str) and NAME.match(t["id"])
                        and isinstance(t.get("name"), str) and t["name"].strip()
                        and isinstance(t.get("color"), str) and COLOR.match(t["color"]) and len(t) == 3):
                    say(f'"topics" item {n} must be {{"id", "name", "color"}}: an id of letters, digits, or hyphens, '
                        'a name, and a color like "#2E8B57".')
                elif t["id"] in topic_ids:
                    say(f'"topics" has the id "{t["id"]}" twice.')
                else:
                    topic_ids.add(t["id"])
    if "sources" in inputs:
        sources = inputs["sources"]
        if not (isinstance(sources, dict) and set(sources) <= {"favor", "leave_out"}
                and all(is_text_list(v) for v in sources.values())):
            say('"sources" must be {"favor": [...], "leave_out": [...]}, each a list of publication names.')
    if "per_day" in inputs and not (isinstance(inputs["per_day"], int) and not isinstance(inputs["per_day"], bool)
                                    and inputs["per_day"] > 0):
        say('"per_day" must be a whole number of stories a day.')
    if "theme" in inputs and not (isinstance(inputs["theme"], str) and inputs["theme"] in themes):
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')
    if "sample" in inputs:
        problems += sample_problems(inputs["sample"], topic_ids)
    return problems


def sample_problems(sample, topic_ids):
    if not isinstance(sample, dict):
        return ['"sample" must be an object with "articles", "inbox", and "landing", like inputs.example.json.']
    problems = []
    say = problems.append
    for key in sample:
        if key not in ("articles", "inbox", "landing"):
            say(f'"sample" has the key "{key}", which Reading List does not use.')
    articles = sample.get("articles", [])
    ids = set()
    if not isinstance(articles, list):
        say('"sample" "articles" must be a list of articles.')
        articles = []
    for n, item in enumerate(articles, 1):
        where = f'"sample" article {n}'
        problems += article_problems(item, where, need_all=True)
        if not isinstance(item, dict):
            continue
        for key in FIELDS:
            if key not in item:
                say(f'{where} needs "{key}".')
        if topic_ids and isinstance(item.get("topic"), str) and item["topic"] not in topic_ids:
            say(f'{where} "topic" must be the id of one of your "topics".')
        image = item.get("image")
        if isinstance(image, str) and image and not image.startswith("https://") and not (APP / "dist" / image).is_file():
            say(f'{where} "image" {image} is not in the page\'s files; use a file under media/ or an https address.')
        if isinstance(item.get("id"), str):
            ids.add(item["id"])
    inbox = sample.get("inbox", [])
    if not isinstance(inbox, list):
        say('"sample" "inbox" must be a list of choices.')
        inbox = []
    for n, e in enumerate(inbox, 1):
        where = f'"sample" choice {n}'
        if not isinstance(e, dict):
            say(f"{where} must be an object with an id, an action, a target, a status, and a time.")
            continue
        if not isinstance(e.get("id"), str):
            say(f'{where} needs "id".')
        if e.get("action") not in ACTIONS:
            say(f'{where} "action" must be one of: {", ".join(ACTIONS)}.')
        target = e.get("target")
        if not (isinstance(target, str) and target.startswith(f"{KIND}/") and target[len(KIND) + 1:] in ids):
            say(f'{where} "target" must be "{KIND}/<id>" for an article in "sample".')
        if e.get("status") not in EVENT_STATES:
            say(f'{where} "status" must be one of: {", ".join(EVENT_STATES)}.')
        if not isinstance(e.get("at"), str):
            say(f'{where} needs "at", a time like "2026-10-22T07:12:00Z".')
    landing = sample.get("landing")
    if landing is not None:
        if not (isinstance(landing, dict) and landing.get("id") in ids and isinstance(landing.get("deep"), dict)):
            say('"sample" "landing" must be null or {"id": <an article in "sample">, "deep": {...}}.')
        else:
            problems += deep_problems(landing["deep"], '"sample" "landing"')
    return problems


def make():
    """Writes out/reading-list/; returns (exit code, inputs)."""
    src = Path(INPUTS)
    if not src.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2, None
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{INPUTS} is not valid JSON: {e}.")
        return 2, None
    dist = APP / "dist"
    if not (dist / "index.html").is_file():
        print(f"The built page is missing from {dist}; run npm ci and npm run build in {APP}.")
        return 2, None
    themes = {p.stem for p in (APP / "src" / "themes").glob("*.css")}
    problems = check(inputs, themes)
    if problems:
        print("\n".join(problems))
        return 2, None
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
    return 0, inputs


def stop(signum, frame):
    """A stop by process id ends the server the way Ctrl+C does, so server.pid is removed."""
    raise KeyboardInterrupt


def runtime():
    return Runtime(app=SLUG, project=Path.cwd(), actions=ACTIONS)


def sync_topics(rt, topics):
    """Keeps the topic records the page reads the same as the inputs' topics."""
    for t in topics:
        current = rt.get(TOPICS, t["id"])
        if current is None or current["body"] != t:
            rt.put(TOPICS, t["id"], t, expect=current["revision"] if current else 0)


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
        raise Rejected(f"The article {event.get('target')} is not on the page.")
    story = record["body"]
    headline = story.get("headline") or id
    action = event["action"]
    if ACTIONS[action] == "external":
        return {"next": "ask the person, then act", "done_at": now()}, f"Ask before: {action} on {headline}"
    if action == "more":
        return {"next": "find more like this article", "done_at": now()}, f"More like: {headline} ({story.get('source', '')})"
    if action == "deeper":
        return {"next": "write a longer brief on this article", "done_at": now()}, f"Go deeper: {headline} ({story.get('link', '')})"
    status, words = PLACED[action]
    if story.get("status") != status:
        rt.put(KIND, id, {**story, "status": status}, expect=record["revision"])
    return {"status": status, "done_at": now()}, f"{headline}: {words}."


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
        print(f"{path} must hold a JSON list of articles.")
        return 2
    rt = runtime()
    code = 0
    for n, item in enumerate(items, 1):
        problems = article_problems(item, f"Item {n}", need_all=False)
        if isinstance(item, dict) and not item.get("id"):
            problems.append(f'Item {n} needs "id", so the page and your later changes can find it.')
        if problems:
            print("\n".join(problems))
            code = 2
            continue
        item = dict(item)
        id = item.pop("id")
        revision = item.pop("revision", None)
        try:
            current = rt.get(KIND, id)
            if current is None:
                missing = [k for k in ("headline", "source", "link", "topic") if not item.get(k)]
                if missing:
                    print(f"Item {n} is new, so it needs " + ", ".join(f'"{k}"' for k in missing) + ".")
                    code = 2
                    continue
                body = {"headline": "", "source": "", "link": "", "image": "", "color": "", "topic": "",
                        "summary": [], "minutes": 5, "published_at": now(), "found_at": now(), "status": "new",
                        "like": None, "deep": None, "agent_notes": [], **item}
                rt.put(KIND, id, body, expect=0)
                print(f"Added {body['headline']} ({KIND}/{id}).")
            else:
                expect = current["revision"] if revision is None else revision
                body = {**current["body"], **item}
                record = rt.put(KIND, id, body, expect=expect)
                print(f"Updated {body['headline']} ({KIND}/{id}, revision {record['revision']}).")
        except Conflict as conflict:
            print(f"Not changed: {conflict} Read it again and add the change to the newer revision.")
            code = 1
        except Rejected as refused:
            print(f"Item {n}: {refused}")
            code = 2
    return code


def main():
    parser = argparse.ArgumentParser(description="Make and run the Reading List page for the project in this folder.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="make the page, then serve it and the inbox")
    group.add_argument("--check", action="store_true", help="print the app's health")
    group.add_argument("--work", action="store_true", help="take every pending choice once")
    group.add_argument("--add", metavar="FILE", help="add or update articles from a JSON list")
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
            print(f"The page is already being served; its process id is in {rt.data / 'server.pid'}.")
            return 2
        code, inputs = make()
        if code or not args.serve:
            return code
        sync_topics(rt, inputs["topics"])
        print(f"Serving the page at http://127.0.0.1:{args.port}/ (Ctrl+C stops it).", flush=True)
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
