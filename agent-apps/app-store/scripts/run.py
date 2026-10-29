#!/usr/bin/env python3
"""Makes the App Store page for the project in the current folder, and runs the store's check.

With no flag: reads app-store.inputs.json from the current folder, checks it, copies site/ into out/app-store/, and
writes theme.css (the chosen theme) and config.js (the inputs) beside its index.html.

  --serve [--port N]       read the store, make the page, then serve it and the inbox on 127.0.0.1 until stopped
  --refresh                read the store with `csc app store --json` and mark every app Muse installed as done
  --work                   the check: take every Get, grab each app, and print the install line of every app waiting
  --failed APP --reason R  record that the app APP did not install, and why
  --check                  print the app's health, one fact per line; exit 1 when it is not ok

The store as last read and the person's Gets live in data/app-store/ in the current folder. Standard library only.
"""
import argparse
import json
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
SITE = APP / "site"
THEMES = SITE / "themes"
sys.dont_write_bytecode = True  # the app folder holds only what ships
sys.path.insert(0, str(HERE))

from runtime import Rejected, Runtime  # noqa: E402

SLUG = "app-store"
INPUTS = f"{SLUG}.inputs.json"
OUT = Path("out") / SLUG
ACTIONS = {"get": "local"}
KIND = "store"
CURRENT = "current"
REQUIRED = ["theme", "sample"]
OPTIONAL = ["sampleInbox", "_notes"]
SAMPLE_KEYS = ["apps", "waiting", "installed"]
EVENT_STATES = ("pending", "working", "completed", "failed", "cancelled")
# A Get stays with Muse while it installs the app; a check that finds it still waiting lists it again.
LEASE_SECONDS = 7 * 24 * 3600
CSC_SECONDS = 120


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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
            say(f'{INPUTS} has the key "{key}", which the App Store does not use.')
    if "theme" in inputs and not (isinstance(inputs["theme"], str) and inputs["theme"] in themes):
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')
    sample = inputs.get("sample")
    if "sample" in inputs:
        if not isinstance(sample, dict) or not all(isinstance(sample.get(key), list) for key in SAMPLE_KEYS):
            say('"sample" must be a store like the one in inputs.example.json, with "apps", "waiting", and "installed" lists.')
        else:
            for n, app in enumerate(sample["apps"], 1):
                if not isinstance(app, dict) or not all(isinstance(app.get(k), str) for k in ("id", "title", "iconUrl")):
                    say(f'"sample" app {n} needs "id", "title", and "iconUrl".')
    if "sampleInbox" in inputs:
        box = inputs["sampleInbox"]
        if not isinstance(box, list):
            say('"sampleInbox" must be a list of Gets.')
        else:
            for n, event in enumerate(box, 1):
                if not (isinstance(event, dict) and event.get("action") in ACTIONS and event.get("status") in EVENT_STATES
                        and isinstance(event.get("payload"), dict) and isinstance(event["payload"].get("appId"), str)):
                    say(f'"sampleInbox" item {n} needs "action" "get", a "status", and a "payload" with the "appId".')
    return problems


def make():
    """Writes out/app-store/; returns the exit code."""
    src = Path(INPUTS)
    if not src.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{INPUTS} is not valid JSON: {e}.")
        return 2
    themes = {p.stem for p in THEMES.glob("*.css")}
    problems = check(inputs, themes)
    if problems:
        print("\n".join(problems))
        return 2
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT)
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (OUT / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False, indent=2)};\n", encoding="utf-8", newline="\n"
    )
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", OUT / "theme.css")
    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT.as_posix()}/ ({files} files). Serve it with its inbox: python3 {Path(__file__).as_posix()} --serve")
    return 0


def runtime():
    return Runtime(app=SLUG, project=Path.cwd(), actions=ACTIONS)


def csc(*words):
    """csc's --json answer as (result, None), or (None, the sentence csc gave for refusing)."""
    command = shutil.which("csc")
    if command is None:
        return None, "csc is not on this computer's PATH."
    try:
        done = subprocess.run([command, *words, "--json"], capture_output=True, text=True, timeout=CSC_SECONDS)
    except subprocess.TimeoutExpired:
        return None, f"csc {' '.join(words)} did not answer in {CSC_SECONDS} seconds."
    try:
        envelope = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        reason = done.stderr.strip().splitlines()[-1] if done.stderr.strip() else f"csc {' '.join(words)} answered nothing."
        return None, reason
    if envelope.get("ok") is True:
        return envelope.get("result") or {}, None
    error = envelope.get("error") or {}
    return None, error.get("message") or f"csc {' '.join(words)} refused."


def gets(rt):
    """Every Get in the inbox, oldest first."""
    return [event for event in rt._events() if event.get("action") == "get"]


def refresh(rt):
    """Reads the store and writes it as the record store/current; a read that fails keeps the last apps with the
    reason. Every Get Muse holds for an app now installed is completed with its link. Returns the store or None."""
    store, problem = csc("app", "store")
    current = rt.get(KIND, CURRENT)
    if store is None:
        body = dict(current["body"]) if current else {"apps": [], "waiting": [], "installed": [], "readAt": None}
        body["problem"] = problem
        rt.put(KIND, CURRENT, body)
        print(f"The store could not be read: {problem}")
        return None
    rt.put(KIND, CURRENT, {**store, "readAt": now(), "problem": None})
    installed = {entry["appId"]: entry for entry in store.get("installed", [])}
    for event in gets(rt):
        app_id = event["payload"].get("appId")
        if event["status"] == "working" and app_id in installed:
            entry = installed[app_id]
            rt.complete(event["id"], {"address": entry["address"], "done_at": now()}, event["attempts"])
            print(f"{entry['title']} is installed: {entry['address']}")
    return store


def work():
    rt = runtime()
    store = refresh(rt)
    if store is None:
        return 1
    # An app the person already got here, whatever became of it, is never added again from the web store's list:
    # one that failed waits for the person's Try again.
    held = {event["payload"].get("appId") for event in gets(rt) if event["status"] != "cancelled"}
    for entry in store.get("waiting", []):
        if entry["appId"] not in held:
            rt.enqueue("get", None, {"appId": entry["appId"], "title": entry["title"]}, f"web-{entry['toolkitId']}")
    have = {entry["appId"] for entry in store.get("waiting", []) + store.get("installed", [])}
    while (event := rt.claim("run.py --work", lease_seconds=LEASE_SECONDS)) is not None:
        app_id = event["payload"].get("appId")
        title = event["payload"].get("title") or app_id
        if app_id in have:
            continue
        _, problem = csc("app", "grab", str(app_id))
        if problem is not None:
            rt.fail(event["id"], problem, event["attempts"])
            print(f"Could not get {title}: {problem} Tell the person once, and ask whether to try it again later.")
            continue
        have.add(app_id)
    store = refresh(rt)
    if store is None:
        return 1
    waiting = {entry["appId"]: entry for entry in store.get("waiting", [])}
    installed = {entry["appId"] for entry in store.get("installed", [])}
    failed_last = {}
    for event in gets(rt):
        if event["status"] != "cancelled":
            failed_last[event["payload"].get("appId")] = event["status"] == "failed"
    for event in gets(rt):
        app_id = event["payload"].get("appId")
        if event["status"] == "working" and app_id not in waiting and app_id not in installed:
            rt.fail(event["id"], "Its toolkit is no longer in your toolkits.", event["attempts"])
    to_install = [entry for app_id, entry in waiting.items() if not failed_last.get(app_id)]
    if not to_install:
        print("Nothing is waiting to be installed.")
        return 0
    me = Path(__file__).resolve().as_posix()
    print("Install each app in turn:")
    for entry in to_install:
        print(f"  {entry['title']} (app {entry['appId']}): csc toolkit export --toolkit {entry['toolkitId']} --to {entry['folder']}")
    print(
        "For each: follow the README in its folder to run the app in a folder of its own, run `csc app deploy` in "
        f"that folder, and tell the person the link. Then run `python3 {me} --refresh` here, and the store shows it "
        f"as Installed. If one does not install, run `python3 {me} --failed <appId> --reason \"<what failed>\"` "
        "here and tell the person once what failed and why."
    )
    return 0


def failed(app_id, reason):
    rt = runtime()
    for event in gets(rt):
        if event["status"] == "working" and event["payload"].get("appId") == app_id:
            rt.fail(event["id"], reason, event["attempts"])
            print(f"{event['payload'].get('title') or app_id} shows as not installed, with the reason.")
            return 0
    print(f"No Get for the app {app_id} is with Muse now.")
    return 2


def check_health():
    report = runtime().health()
    for key, value in report.items():
        if isinstance(value, dict):
            value = ", ".join(f"{n} {k}" for k, n in value.items())
        elif isinstance(value, bool):
            value = "yes" if value else "no"
        print(f"{key}: {value}")
    return 0 if report["ok"] else 1


def stop(signum, frame):
    """A stop by process id ends the server the way Ctrl+C does, so server.pid is removed."""
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description="Make and run the App Store for the project in this folder.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="read the store, make the page, then serve it and the inbox")
    group.add_argument("--refresh", action="store_true", help="read the store and mark installed apps as done")
    group.add_argument("--work", action="store_true", help="the check: take every Get and list what to install")
    group.add_argument("--failed", metavar="APP", help="record that the app APP did not install")
    group.add_argument("--check", action="store_true", help="print the app's health")
    parser.add_argument("--reason", help="with --failed: what failed, in one sentence")
    parser.add_argument("--port", type=int, default=8765, help="the port for --serve (8765)")
    args = parser.parse_args()
    try:
        if args.check:
            return check_health()
        if args.refresh:
            return 0 if refresh(runtime()) is not None else 1
        if args.work:
            return work()
        if args.failed:
            if not args.reason:
                print("Give --reason with what failed, in one sentence.")
                return 2
            return failed(args.failed, args.reason)
        rt = runtime()
        if args.serve and rt.health()["server_running"]:
            print(f"The store is already being served; its process id is in {rt.data / 'server.pid'}.")
            return 2
        code = make()
        if code or not args.serve:
            return code
        refresh(rt)
        print(f"Serving the store at http://127.0.0.1:{args.port}/ (Ctrl+C stops it).", flush=True)
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
