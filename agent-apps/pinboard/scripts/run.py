"""Pinboard: makes the board's page and keeps its pins and the person's choices.

Run from the project folder:

    python3 <app folder>/scripts/run.py               writes out/pinboard/ from pinboard.inputs.json
    python3 <app folder>/scripts/run.py --serve       writes it, then serves the page and the inbox on 127.0.0.1
    python3 <app folder>/scripts/run.py --check       prints the data folder's health; exit 1 when it is not ok
    python3 <app folder>/scripts/run.py --work        works through the person's pending choices once
    python3 <app folder>/scripts/run.py --add f.json  adds or updates the pins listed in f.json

Python 3 standard library only. Pins and choices live in <project>/data/pinboard/, never in the app folder.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import Conflict, Rejected, Runtime  # noqa: E402

APP = "pinboard"
ACTIONS = {"keep": "local", "reject": "local", "move": "local", "find-more": "local"}
FOLDER = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd()
INPUTS = PROJECT / f"{APP}.inputs.json"
OUT = PROJECT / "out" / APP
THEMES = FOLDER / "src" / "themes"
MEDIA_PREFIX = "media/"
STATUSES = ("new", "kept", "rejected")
ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
PIN_KEYS = {"id", "title", "image", "source", "note", "tags", "board", "color", "status", "agent_notes", "found_for", "added"}
INPUT_KEYS = {"name", "boards", "theme", "sample"}


class Stop(Exception):
    """A plain problem to print, one line each, before exiting 2."""

    def __init__(self, lines):
        super().__init__("\n".join(lines))
        self.lines = lines


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:64] or "board"


def is_text_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def pin_body(item):
    """A pin with every key a pin takes, each one the item leaves out at its default."""
    body = {"id": None, "title": "", "image": "", "source": "", "note": "", "tags": [], "board": None,
            "color": "#d9d4cc", "status": "new", "agent_notes": [], "found_for": None}
    body.update(item)
    return body


def pin_problems(pin, where, boards, local_image_ok):
    """The plain problems with one pin, each naming `where`."""
    problems = []
    if not isinstance(pin, dict):
        return [f"{where} must be an object."]
    for key in sorted(set(pin) - PIN_KEYS - {"revision"}):
        problems.append(f'{where} has the key "{key}", which a pin does not take.')
    if "id" in pin and (not isinstance(pin["id"], str) or not ID.fullmatch(pin["id"])):
        problems.append(f'{where} "id" must be letters, digits, hyphens, or underscores.')
    if not isinstance(pin.get("title"), str) or not pin.get("title", "").strip():
        problems.append(f'{where} is missing the key "title".')
    image = pin.get("image")
    if not isinstance(image, str) or not image:
        problems.append(f'{where} is missing the key "image".')
    elif not (image.startswith("https://") or image.startswith(MEDIA_PREFIX) or local_image_ok):
        problems.append(f'{where} "image" must be an https address or a file under {MEDIA_PREFIX}.')
    source = pin.get("source", "")
    if not isinstance(source, str) or (source and not re.match(r"https?://", source)):
        problems.append(f'{where} "source" must be a link starting with https://.')
    if not isinstance(pin.get("note", ""), str):
        problems.append(f'{where} "note" must be text.')
    for key in ("tags", "agent_notes"):
        if not is_text_list(pin.get(key, [])):
            problems.append(f'{where} "{key}" must be a list of text.')
    board = pin.get("board")
    if board is not None and (not isinstance(board, str) or board not in boards):
        known = ", ".join(sorted(boards)) or "none yet"
        problems.append(f'{where} "board" is "{board}", which is not a board here ({known}).')
    if "color" in pin and (not isinstance(pin["color"], str) or not COLOR.fullmatch(pin["color"])):
        problems.append(f'{where} "color" must look like #c4673f.')
    if pin.get("status", "new") not in STATUSES:
        problems.append(f'{where} "status" must be new, kept, or rejected.')
    found_for = pin.get("found_for")
    if found_for is not None and (not isinstance(found_for, str) or not ID.fullmatch(found_for)):
        problems.append(f'{where} "found_for" must be the id of a pin, or null.')
    return problems


def load_inputs():
    if not INPUTS.exists():
        raise Stop([f"Make {INPUTS.name} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    except ValueError as bad:
        raise Stop([f"{INPUTS.name} is not valid JSON: {bad}."])
    if not isinstance(inputs, dict):
        raise Stop([f"{INPUTS.name} must hold one JSON object."])
    problems = []
    for key in sorted(INPUT_KEYS - set(inputs)):
        problems.append(f'{INPUTS.name} is missing the key "{key}".')
    for key in sorted(set(inputs) - INPUT_KEYS - {"_notes"}):
        problems.append(f'{INPUTS.name} has the key "{key}", which this app does not take.')
    if "name" in inputs and (not isinstance(inputs["name"], str) or not inputs["name"].strip()):
        problems.append(f'{INPUTS.name} "name" must be text, like "Maya".')
    boards = {}
    if "boards" in inputs:
        if not is_text_list(inputs["boards"]) or not inputs["boards"]:
            problems.append(f'{INPUTS.name} "boards" must be a list of board names, like ["Kitchen"].')
        else:
            for name in inputs["boards"]:
                boards[slug(name)] = name.strip()
    if "theme" in inputs:
        names = sorted(path.stem for path in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'{INPUTS.name} "theme" is "{inputs["theme"]}"; the themes are {", ".join(names)}.')
    if "sample" in inputs:
        if not isinstance(inputs["sample"], list):
            problems.append(f'{INPUTS.name} "sample" must be a list of pins.')
        else:
            for n, pin in enumerate(inputs["sample"], 1):
                problems += pin_problems(pin, f'{INPUTS.name} sample pin {n}', boards, local_image_ok=True)
    if problems:
        raise Stop(problems)
    return inputs, boards


def build(inputs):
    """Writes out/pinboard/ from dist/, the inputs, and the chosen theme. Two runs on the same inputs are
    byte-identical."""
    dist = FOLDER / "dist"
    if not (dist / "index.html").exists():
        raise Stop([f"{dist} has no index.html; build it with npm ci && npm run build in {FOLDER}."])
    sample = []
    copies = []
    problems = []
    for n, pin in enumerate(inputs["sample"], 1):
        pin = pin_body(pin)
        image = pin["image"]
        if not image.startswith("https://") and not (dist / image).is_file():
            local = (PROJECT / image).resolve()
            try:
                inside = local.relative_to(PROJECT.resolve()).as_posix()
            except ValueError:
                inside = None
            if inside is None:
                problems.append(f'{INPUTS.name} sample pin {n} names the image "{image}", which is outside this folder.')
            elif not local.is_file():
                problems.append(f'{INPUTS.name} sample pin {n} names the image "{image}", which is not there.')
            else:
                pin["image"] = f"{MEDIA_PREFIX}{inside}"
                copies.append((local, OUT / pin["image"]))
        sample.append(pin)
    if problems:
        raise Stop(problems)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(dist, OUT)
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    config = {key: inputs[key] for key in ("name", "boards", "theme")}
    config["sample"] = sample
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, indent=2)};\n", encoding="utf-8")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", OUT / "theme.css")
    return sum(1 for path in OUT.rglob("*") if path.is_file())


def runtime():
    return Runtime(app=APP, project=PROJECT, actions=ACTIONS)


def ensure_boards(rt, boards):
    """Makes a board record for each starting board that has none; an existing board is left as it is."""
    for id, name in boards.items():
        if rt.get("boards", id) is None:
            rt.put("boards", id, {"id": id, "name": name}, expect=0)


def board_name(rt, id):
    record = rt.get("boards", id) if id else None
    return record["body"]["name"] if record else (id or "no board")


def check(rt):
    health = rt.health()
    inbox = health.get("inbox") or {}
    print(f"ok: {'yes' if health['ok'] else 'no'}")
    print(f"data folder: {health['data']}")
    print(f"writable: {'yes' if health['writable'] else 'no'}")
    print(f"schema version: {health['schema_version']}")
    print(f"inbox readable: {'yes' if health['inbox_readable'] else 'no'}")
    print("inbox: " + ", ".join(f"{count} {state}" for state, count in inbox.items()))
    print(f"pins: {len(rt.list('pins'))}, boards: {len(rt.list('boards'))}")
    print(f"server running: {'yes' if health['server_running'] else 'no'}")
    print(f"mode: {health['mode']}. {health['says']}")
    return 0 if health["ok"] else 1


def handle(rt, event):
    """Takes one claimed event through this app's handler for its action. Returns (result, line)."""
    action = event["action"]
    if ACTIONS.get(action) == "external":
        return {"next": "ask the person, then act"}, f"Ask before: {action} on {event['target']}"
    kind, _, id = (event["target"] or "").partition("/")
    pin = rt.get("pins", id) if kind == "pins" else None
    if pin is None:
        raise Rejected(f"There is no pin {event['target']}.")
    body = dict(pin["body"])
    title = body["title"]
    if action == "find-more":
        return {"next": "find more like this pin"}, f"Find more like: {title} ({body.get('source') or 'no link'})"
    if action in ("keep", "reject"):
        body["status"] = "kept" if action == "keep" else "rejected"
        rt.put("pins", id, body, expect=pin["revision"])
        said = "Kept" if action == "keep" else "Set aside"
        return {"status": body["status"], "said": said}, f"{said}: {title}"
    if action == "move":
        payload = event["payload"] or {}
        board = payload.get("board")
        if not isinstance(board, str) or not ID.fullmatch(board):
            raise Rejected("A move needs a board id in its payload.")
        if rt.get("boards", board) is None:
            name = payload.get("name") if isinstance(payload.get("name"), str) and payload["name"].strip() else board
            rt.put("boards", board, {"id": board, "name": name.strip()}, expect=0)
        body["board"] = board
        rt.put("pins", id, body, expect=pin["revision"])
        name = board_name(rt, board)
        return {"board": board, "said": f"Now on {name}"}, f"Moved: {title} to {name}"
    raise Rejected(f"Pinboard has no handler for {action}.")


def work(rt):
    done = 0
    while True:
        event = rt.claim("pinboard-agent")
        if event is None:
            break
        done += 1
        try:
            result, line = handle(rt, event)
        except (Rejected, Conflict) as refused:
            rt.fail(event["id"], str(refused), event["attempts"])
            print(f"Could not {event['action']} {event['target']}: {refused}")
            continue
        result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rt.complete(event["id"], result, event["attempts"])
        print(line)
    if done == 0:
        print("No choices are waiting.")
    return 0


def add(rt, file):
    path = Path(file)
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        print(f"There is no file {path}.")
        return 2
    except ValueError as bad:
        print(f"{path} is not valid JSON: {bad}.")
        return 2
    if not isinstance(items, list):
        print(f"{path} must hold a JSON list of pins.")
        return 2
    boards = {record["id"] for record in rt.list("boards")}
    status = 0
    for n, item in enumerate(items, 1):
        where = f"{path.name} pin {n}"
        problems = pin_problems(item, where, boards, local_image_ok=False)
        if problems:
            for line in problems:
                print(line)
            status = 1
            continue
        item = dict(item)
        stated = item.pop("revision", None)
        id = item.get("id")
        current = rt.get("pins", id) if id else None
        if current is None:
            body = pin_body({"added": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **item})
            record = rt.put("pins", id, body)
            if id is None:
                body["id"] = record["id"]
                record = rt.put("pins", record["id"], body, expect=record["revision"])
            print(f"Added: {body['title']} (pins/{record['id']})")
            continue
        body = dict(current["body"])
        body.update(item)
        expect = stated if stated is not None else current["revision"]
        try:
            record = rt.put("pins", id, body, expect=expect)
        except Conflict as conflict:
            print(f"Conflict: {item['title']}: {conflict} Read it again and add it with that revision.")
            status = 1
            continue
        print(f"Updated: {body['title']} (pins/{id}, revision {record['revision']})")
    return status


def main():
    parser = argparse.ArgumentParser(description="Pinboard: the board's page, its pins, and the person's choices.")
    parser.add_argument("--serve", action="store_true", help="write the page, then serve it and the inbox")
    parser.add_argument("--port", type=int, default=8765, help="the port --serve listens on (default 8765)")
    parser.add_argument("--check", action="store_true", help="print the data folder's health")
    parser.add_argument("--work", action="store_true", help="work through the pending choices once")
    parser.add_argument("--add", metavar="FILE", help="add or update the pins listed in FILE")
    args = parser.parse_args()
    try:
        if args.check:
            return check(runtime())
        if args.work:
            return work(runtime())
        if args.add:
            rt = runtime()
            if INPUTS.exists():
                ensure_boards(rt, load_inputs()[1])
            return add(rt, args.add)
        inputs, boards = load_inputs()
        count = build(inputs)
        if not args.serve:
            print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
            return 0
        rt = runtime()
        ensure_boards(rt, boards)
        print(f"Wrote out/{APP}/ ({count} files). Serving it and the inbox at http://127.0.0.1:{args.port}/")
        print(f"Pins and choices are kept in {rt.data}. Stop the server with Ctrl+C.", flush=True)
        try:
            rt.serve(OUT, args.port)
        except KeyboardInterrupt:
            print("Stopped.")
        return 0
    except Stop as stop:
        for line in stop.lines:
            print(line)
        return 2
    except Rejected as refused:
        print(refused)
        return 1
    except OSError as failed:
        print(f"Could not do that: {failed}.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
