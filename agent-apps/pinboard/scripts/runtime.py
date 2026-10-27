"""The shared runtime of an interactive agent app.

An app whose page takes the person's choices, or that keeps what the agent
found between runs, imports this module from its scripts/run.py:

    from runtime import Runtime, Conflict, Rejected

It gives the app one private data folder, <project>/data/<app>/, outside the
app folder; records with a revision each; an inbox of the person's choices,
one event per key, in the states pending, working, completed, failed, and
cancelled; a health check; migrations that copy the data folder first; and a
server on this machine for the page and the inbox. No host wakes the agent
when a choice lands: the agent checks the inbox when the person asks.

Python 3 standard library only. Every write is a temp file and a rename, and
every change to a record or an event holds the data folder's lock, so the
server and the agent's own run never write over each other.

python3 runtime.py --self-test runs this module's tests and exits 0 when
every one passes.
"""

import contextlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATES = ("pending", "working", "completed", "failed", "cancelled")
ACTION_REACH = ("local", "external")
POLLING = "The agent checks the inbox when you ask."
NAME = re.compile(r"[A-Za-z0-9_-]{1,128}")
MAX_BODY = 64 * 1024

try:
    import fcntl

    def _hold(handle):
        fcntl.flock(handle, fcntl.LOCK_EX)

    def _let_go(handle):
        fcntl.flock(handle, fcntl.LOCK_UN)

except ImportError:
    import msvcrt

    def _hold(handle):
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)

    def _let_go(handle):
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


class Conflict(Exception):
    """A record changed since the revision the caller expected."""


class Rejected(Exception):
    """A call the runtime refuses: an undeclared action, a bad name, or a
    move an event's state does not allow."""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _name(value, what):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise Rejected(f"{what} {value!r} must be 1 to 128 letters, digits, hyphens, or underscores.")
    return value


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temp, path)


def _write_json(path, value):
    _write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _files(folder):
    """The .json files in `folder`; none when it does not exist yet. A
    folder that can't be read raises."""
    if not folder.exists():
        return []
    return [path for path in folder.iterdir() if path.suffix == ".json"]


def _alive(pid):
    if os.name == "nt":
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return code.value == 259
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Runtime:
    """One app's data folder, records, inbox, health, migrations, and server.

    `actions` names every action the page can send and its reach: `local`
    changes only this machine, `external` reaches outside it and is never
    taken on a choice alone.
    """

    def __init__(self, app, project, actions):
        self.app = _name(app, "The app name")
        self.project = Path(project)
        for action, reach in actions.items():
            _name(action, "The action")
            if reach not in ACTION_REACH:
                raise Rejected(f"The action {action!r} must be local or external, not {reach!r}.")
        self.actions = dict(actions)
        self._data = self.project / "data" / self.app
        self._server = None

    @property
    def data(self):
        """The app's private data folder, made with schema version 0 on first use."""
        if not (self._data / "schema.json").exists():
            with self._locked():
                pass
        return self._data

    @contextlib.contextmanager
    def _locked(self):
        """Holds the data folder's lock, making the folder and its schema.json
        first when they are not there."""
        self._data.mkdir(parents=True, exist_ok=True)
        with open(self._data / ".lock", "a+b") as handle:
            _hold(handle)
            try:
                if not (self._data / "schema.json").exists():
                    _write_json(self._data / "schema.json", {"version": 0})
                yield
            finally:
                _let_go(handle)

    def _record_path(self, kind, id):
        return self.data / "records" / _name(kind, "The kind") / f"{_name(id, 'The record id')}.json"

    def _event_path(self, event_id):
        return self.data / "inbox" / f"{_name(event_id, 'The event id')}.json"

    def put(self, kind, id, body, expect=None):
        """Writes the record `kind`/`id` (a new id when `id` is None) at the
        next revision. With `expect`, the record's current revision (0 when
        there is none) must equal it, or Conflict."""
        id = uuid.uuid4().hex if id is None else id
        path = self._record_path(kind, id)
        with self._locked():
            current = _read_json(path)["revision"] if path.exists() else 0
            if expect is not None and expect != current:
                raise Conflict(f"{kind}/{id} is at revision {current}, not {expect}.")
            record = {"id": id, "kind": kind, "revision": current + 1, "at": _now(), "body": body}
            _write_json(path, record)
        return record

    def get(self, kind, id):
        """The record `kind`/`id`, or None."""
        path = self._record_path(kind, id)
        return _read_json(path) if path.exists() else None

    def list(self, kind):
        """Every record of `kind`, oldest write first."""
        records = [_read_json(path) for path in _files(self.data / "records" / _name(kind, "The kind"))]
        return sorted(records, key=lambda record: (record["at"], record["id"]))

    def _events(self):
        """Every event in the inbox, oldest first."""
        events = [_read_json(path) for path in _files(self.data / "inbox")]
        return sorted(events, key=lambda event: (event["at"], event["id"]))

    def _enqueue(self, action, target, payload, key):
        if _name(action, "The action") not in self.actions:
            raise Rejected(f"The action {action!r} is not one this app declares.")
        if not isinstance(key, str) or not key:
            raise Rejected("A choice needs a key, so the same choice twice is one event.")
        payload = {} if payload is None else payload
        if not isinstance(payload, dict):
            raise Rejected("A choice's payload must be an object.")
        if target is not None and not isinstance(target, str):
            raise Rejected('A choice\'s target must be "<kind>/<id>" or null.')
        with self._locked():
            for event in self._events():
                if event["key"] == key:
                    return event, False
            record = None
            if target is not None:
                kind, _, id = target.partition("/")
                record = self.get(kind, id)
            event = {
                "id": uuid.uuid4().hex,
                "app": self.app,
                "action": action,
                "target": target,
                "target_revision": record["revision"] if record else None,
                "key": key,
                "at": _now(),
                "payload": payload,
                "status": "pending",
                "worker": None,
                "lease_until": None,
                "attempts": 0,
                "result": None,
                "error": None,
            }
            _write_json(self._event_path(event["id"]), event)
        return event, True

    def enqueue(self, action, target, payload, key):
        """Adds the person's choice `action` on the record `target`
        ("<kind>/<id>", or None) as a pending event. An event with the same
        key already there is returned instead."""
        return self._enqueue(action, target, payload, key)[0]

    def claim(self, worker, lease_seconds=300):
        """The oldest pending event, or working event whose lease has run
        out, now working for `worker` until the lease ends; or None."""
        with self._locked():
            now = _now()
            for event in self._events():
                expired = event["status"] == "working" and event["lease_until"] <= now
                if event["status"] == "pending" or expired:
                    lease = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
                    event.update(
                        status="working",
                        worker=worker,
                        lease_until=lease.isoformat(timespec="microseconds"),
                        attempts=event["attempts"] + 1,
                    )
                    _write_json(self._event_path(event["id"]), event)
                    return event
        return None

    def _move(self, event_id, start, end, attempt=None, **fields):
        path = self._event_path(event_id)
        with self._locked():
            if not path.exists():
                raise Rejected(f"There is no event {event_id}.")
            event = _read_json(path)
            if event["status"] != start:
                raise Rejected(f"Event {event_id} is {event['status']}, so it can't become {end}.")
            if attempt is not None and event["attempts"] != attempt:
                raise Rejected(f"Event {event_id} was claimed again after this claim's lease expired.")
            event.update(status=end, lease_until=None, **fields)
            _write_json(path, event)
        return event

    def complete(self, event_id, result, attempt):
        """A working event, now completed with `result`. `attempt` is the
        `attempts` of the event `claim` returned, so a claim whose lease ran
        out and was claimed again can no longer finish it."""
        return self._move(event_id, "working", "completed", attempt, result=result)

    def fail(self, event_id, error, attempt):
        """A working event, now failed with `error`. `attempt` is as for
        `complete`."""
        return self._move(event_id, "working", "failed", attempt, error=error)

    def cancel(self, event_id):
        """A pending event, now cancelled."""
        return self._move(event_id, "pending", "cancelled")

    def inbox(self):
        """How many events are in each state."""
        counts = dict.fromkeys(STATES, 0)
        for event in self._events():
            counts[event["status"]] += 1
        return counts

    def _server_pid(self):
        path = self._data / "server.pid"
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None
        return pid if _alive(pid) else None

    def health(self):
        """The data folder writable, the schema version readable, and the
        inbox readable make `ok`; whether the server runs and the polling
        mode are reported beside them."""
        report = {"data": str(self._data), "mode": "polling", "says": POLLING}
        try:
            probe = self.data / f".probe.{uuid.uuid4().hex}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            report["writable"] = True
        except OSError:
            report["writable"] = False
        try:
            report["schema_version"] = int(_read_json(self._data / "schema.json")["version"])
        except (OSError, ValueError, KeyError, TypeError):
            report["schema_version"] = None
        try:
            report["inbox"] = self.inbox()
            report["inbox_readable"] = True
        except (OSError, ValueError, KeyError):
            report["inbox"] = None
            report["inbox_readable"] = False
        report["server_running"] = self._server_pid() is not None
        report["ok"] = report["writable"] and report["schema_version"] is not None and report["inbox_readable"]
        return report

    def migrate(self, version, steps):
        """Brings the data from schema.json's version up to `version`, step
        `n` taking it from n - 1 to n, after a copy of the data folder to
        backups/<utc stamp>/. A step that raises leaves schema.json at the
        last version that completed. Returns the version reached. Refuses
        while server.pid names a live process.

        The steps run holding the data folder's lock, so a step works on the
        files under the folder it is given and calls no Runtime method."""
        root = self.data
        if self._server_pid() is not None:
            raise Rejected("Stop the app's server before migrating.")
        with self._locked():
            current = int(_read_json(root / "schema.json")["version"])
            if version <= current:
                return current
            for n in range(current + 1, version + 1):
                if n not in steps:
                    raise Rejected(f"There is no migration step to version {n}.")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            skip = {"backups", "server.pid", ".lock"}
            shutil.copytree(
                root,
                root / "backups" / stamp,
                ignore=lambda folder, names: (
                    [n for n in names if n in skip or n.startswith(".probe.")] if Path(folder) == root else []
                ),
            )
            for n in range(current + 1, version + 1):
                steps[n](root)
                _write_json(root / "schema.json", {"version": n})
        return version

    def serve(self, site, port=8765):
        """Serves the folder `site` and the inbox on 127.0.0.1:`port` until
        stopped. Refuses to start while server.pid names a live process."""
        pid_path = self.data / "server.pid"
        with self._locked():
            running = self._server_pid()
            if running is not None:
                raise Rejected(
                    f"The page is already being served by process {running}. Stop it first, or remove "
                    f"{pid_path} when no server is running."
                )
            _write(pid_path, str(os.getpid()))
        runtime = self

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(site), **kwargs)

            def log_message(self, *args):
                pass

            def _answer(self, status, value):
                body = json.dumps(value).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                route = self.path.split("?", 1)[0]
                try:
                    if route == "/api/health":
                        return self._answer(200, runtime.health())
                    if route == "/api/inbox":
                        return self._answer(200, runtime._events())
                    if route.startswith("/api/records/"):
                        return self._answer(200, runtime.list(route[len("/api/records/") :]))
                except Rejected as refused:
                    return self._answer(400, {"error": str(refused)})
                if route.startswith("/api/"):
                    return self._answer(404, {"error": f"There is no {route}."})
                return super().do_GET()

            def do_POST(self):
                route = self.path.split("?", 1)[0]
                parts = route.strip("/").split("/")
                try:
                    if route == "/api/inbox":
                        length = int(self.headers.get("Content-Length") or 0)
                        if length > MAX_BODY:
                            return self._answer(413, {"error": "A choice must be under 64 KiB."})
                        try:
                            choice = json.loads(self.rfile.read(length) or b"{}")
                        except ValueError:
                            return self._answer(400, {"error": "A choice must be a JSON object."})
                        if not isinstance(choice, dict):
                            return self._answer(400, {"error": "A choice must be a JSON object."})
                        event, made = runtime._enqueue(
                            choice.get("action"), choice.get("target"), choice.get("payload"), choice.get("key")
                        )
                        return self._answer(201 if made else 200, event)
                    if len(parts) == 4 and parts[:2] == ["api", "inbox"] and parts[3] == "cancel":
                        return self._answer(200, runtime.cancel(parts[2]))
                except Rejected as refused:
                    return self._answer(409 if route.endswith("/cancel") else 400, {"error": str(refused)})
                return self._answer(404, {"error": f"There is no {route}."})

        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            self._server.serve_forever()
        finally:
            if self._server is not None:
                self._server.server_close()
                self._server = None
            with contextlib.suppress(OSError):
                if pid_path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                    pid_path.unlink()


if __name__ == "__main__":
    import tempfile
    import threading
    import time
    import unittest
    import urllib.error
    import urllib.request

    class RuntimeTests(unittest.TestCase):
        def setUp(self):
            scratch = Path.cwd() / ".tmp"
            self.made_scratch = not scratch.exists()
            scratch.mkdir(exist_ok=True)
            self.project = Path(tempfile.mkdtemp(dir=scratch))
            self.rt = Runtime("job-board", self.project, {"shortlist": "local", "apply": "external"})

        def tearDown(self):
            shutil.rmtree(self.project)
            if self.made_scratch:
                with contextlib.suppress(OSError):
                    (Path.cwd() / ".tmp").rmdir()

        def test_put_revisions_and_a_stale_expect_conflicts(self):
            self.assertEqual(self.rt.data, self.project / "data" / "job-board")
            first = self.rt.put("job", "j1", {"title": "Baker"})
            self.assertEqual(first["revision"], 1)
            second = self.rt.put("job", "j1", {"title": "Baker"}, expect=1)
            self.assertEqual(second["revision"], 2)
            with self.assertRaises(Conflict):
                self.rt.put("job", "j1", {"title": "Chef"}, expect=1)
            self.assertEqual(self.rt.get("job", "j1")["body"], {"title": "Baker"})
            self.assertIsNone(self.rt.get("job", "j2"))
            minted = self.rt.put("job", None, {"title": "Cook"})
            self.assertEqual(len(minted["id"]), 32)
            self.assertEqual([r["id"] for r in self.rt.list("job")], ["j1", minted["id"]])
            with self.assertRaises(Rejected):
                self.rt.get("../job", "j1")

        def test_the_same_key_twice_is_one_event(self):
            self.rt.put("job", "j1", {"title": "Baker"})
            one = self.rt.enqueue("shortlist", "job/j1", {"note": "yes"}, "j1-yes")
            two = self.rt.enqueue("shortlist", "job/j1", {"note": "yes"}, "j1-yes")
            self.assertEqual(one["id"], two["id"])
            self.assertEqual(one["target_revision"], 1)
            self.assertEqual(self.rt.inbox()["pending"], 1)
            with self.assertRaises(Rejected):
                self.rt.enqueue("delete", "job/j1", {}, "j1-delete")

        def test_claim_complete_fail_cancel_and_an_expired_lease(self):
            a = self.rt.enqueue("shortlist", None, {}, "a")
            b = self.rt.enqueue("shortlist", None, {}, "b")
            c = self.rt.enqueue("shortlist", None, {}, "c")
            d = self.rt.enqueue("shortlist", None, {}, "d")
            first = self.rt.claim("w1")
            self.assertEqual(first["id"], a["id"])
            self.assertEqual(self.rt.complete(a["id"], {"done": True}, first["attempts"])["result"], {"done": True})
            second = self.rt.claim("w1")
            self.assertEqual(second["id"], b["id"])
            self.assertEqual(self.rt.fail(b["id"], "No page", second["attempts"])["error"], "No page")
            self.assertEqual(self.rt.cancel(c["id"])["status"], "cancelled")
            with self.assertRaises(Rejected):
                self.rt.cancel(a["id"])
            with self.assertRaises(Rejected):
                self.rt.complete(d["id"], None, 0)
            stale = self.rt.claim("w1", lease_seconds=0)
            self.assertEqual(stale["id"], d["id"])
            again = self.rt.claim("w2")
            self.assertEqual((again["id"], again["worker"], again["attempts"]), (d["id"], "w2", 2))
            self.assertIsNone(self.rt.claim("w3"))
            with self.assertRaises(Rejected):
                self.rt.complete(d["id"], {"by": "w1"}, stale["attempts"])
            self.assertEqual(self.rt.complete(d["id"], {"by": "w2"}, again["attempts"])["result"], {"by": "w2"})
            self.assertEqual(
                self.rt.inbox(), {"pending": 0, "working": 0, "completed": 2, "failed": 1, "cancelled": 1}
            )

        def test_health_is_ok_on_a_fresh_folder_and_reports_polling(self):
            health = self.rt.health()
            self.assertTrue(health["ok"], health)
            self.assertEqual((health["mode"], health["says"]), ("polling", POLLING))
            self.assertEqual(health["schema_version"], 0)
            self.assertFalse(health["server_running"])

        def test_an_unreadable_inbox_makes_health_not_ok(self):
            if os.name == "nt" or os.geteuid() == 0:
                self.skipTest("permissions don't stop this user from reading a folder")
            inbox = self.rt.data / "inbox"
            inbox.mkdir()
            inbox.chmod(0)
            try:
                health = self.rt.health()
            finally:
                inbox.chmod(0o700)
            self.assertEqual((health["ok"], health["inbox_readable"]), (False, False))

        def test_migrate_backs_up_and_stops_at_the_last_completed_step(self):
            self.rt.put("job", "j1", {"title": "Baker"})
            (self.rt.data / ".probe.left").write_text("ok", encoding="utf-8")

            def broken(root):
                raise RuntimeError("step 3 breaks")

            with self.assertRaises(RuntimeError):
                self.rt.migrate(3, {1: lambda root: None, 2: lambda root: None, 3: broken})
            self.assertEqual(_read_json(self.rt.data / "schema.json"), {"version": 2})
            backups = list((self.rt.data / "backups").iterdir())
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "records" / "job" / "j1.json").is_file())
            self.assertFalse((backups[0] / ".probe.left").exists())
            self.assertEqual(self.rt.migrate(3, {3: lambda root: None}), 3)
            self.assertEqual(self.rt.health()["schema_version"], 3)

        def test_migrate_refuses_while_the_server_runs(self):
            (self.rt.data / "server.pid").write_text(str(os.getpid()), encoding="utf-8")
            with self.assertRaises(Rejected):
                self.rt.migrate(1, {1: lambda root: None})
            self.assertEqual(_read_json(self.rt.data / "schema.json"), {"version": 0})
            self.assertFalse((self.rt.data / "backups").exists())

        def test_serve_answers_its_routes_and_a_second_serve_refuses(self):
            site = self.project / "site"
            site.mkdir()
            (site / "index.html").write_text("<p>board</p>", encoding="utf-8")
            self.rt.put("job", "j1", {"title": "Baker"})
            thread = threading.Thread(target=self.rt.serve, args=(site, 0), daemon=True)
            thread.start()
            for _ in range(500):
                server = self.rt._server
                if server is not None:
                    break
                time.sleep(0.01)
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def call(path, body=None):
                data = None if body is None else json.dumps(body).encode("utf-8")
                request = urllib.request.Request(base + path, data=data, method="GET" if body is None else "POST")
                try:
                    with urllib.request.urlopen(request, timeout=5) as answer:
                        return answer.status, answer.read()
                except urllib.error.HTTPError as answer:
                    with answer:
                        return answer.code, answer.read()

            try:
                self.assertEqual(call("/index.html"), (200, b"<p>board</p>"))
                status, body = call("/api/health")
                self.assertEqual((status, json.loads(body)["server_running"]), (200, True))
                status, body = call("/api/records/job")
                self.assertEqual((status, [r["id"] for r in json.loads(body)]), (200, ["j1"]))
                choice = {"action": "shortlist", "target": "job/j1", "payload": {}, "key": "j1-yes"}
                status, body = call("/api/inbox", choice)
                self.assertEqual(status, 201)
                event = json.loads(body)
                self.assertEqual(call("/api/inbox", choice)[0], 200)
                status, body = call("/api/inbox")
                self.assertEqual((status, [e["id"] for e in json.loads(body)]), (200, [event["id"]]))
                self.assertEqual(call("/api/inbox", {"action": "delete", "key": "k"})[0], 400)
                status, body = call("/api/inbox", {"action": [], "key": "x"})
                self.assertEqual(status, 400)
                self.assertIn("The action", json.loads(body)["error"])
                status, body = call(f"/api/inbox/{event['id']}/cancel", {})
                self.assertEqual((status, json.loads(body)["status"]), (200, "cancelled"))
                self.assertEqual(call(f"/api/inbox/{event['id']}/cancel", {})[0], 409)
                with self.assertRaises(Rejected):
                    Runtime("job-board", self.project, {}).serve(site, 0)
            finally:
                server.shutdown()
                thread.join(5)
            self.assertFalse((self.rt.data / "server.pid").exists())

    if sys.argv[1:] != ["--self-test"]:
        print("python3 runtime.py --self-test runs this module's tests; an app imports it from scripts/run.py.")
        sys.exit(2)
    sys.exit(0 if unittest.main(argv=[sys.argv[0]], exit=False).result.wasSuccessful() else 1)
