"""A command cut off at any point leaves nothing the next command reads wrongly: a record that names other files goes
before the first of them changes and comes back once they are whole, every file a later step reads arrives by rename,
film.py render moves the reel into out/ last and publishes its report only after, the critics' round opens only on a
render film.json vouches for and is reused while the files it scored stand, deliver keeps the workspace's out/ whole
at every point and holds the run's render lock and runs its gate in its own process, every process the gate starts going through the
lock's spawn, and a green deliver's last line is the delivered reel's path from the workspace root, the one the reply names; a red
deliver's last line names the failing checks and no film.

    python3 -m unittest discover -s S/tests -p test_cutoff.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import fixture

import _env  # noqa: E402
import chunks  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402
from compose import photos  # noqa: E402

ENV = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")


class Hold:
    spawn = staticmethod(subprocess.run)


@contextlib.contextmanager
def held(work, name):
    Path(work).mkdir(parents=True, exist_ok=True)
    yield Hold()


def made(jobs, work, name, board=None, run=None, hold=None):
    for j in jobs:
        Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
        Path(j["out"]).write_bytes(b"new")
    return {"failed": 0, "exit": 0, "findings": []}


def wrote(silent, wav, seconds, out, fx, **kw):
    Path(out).write_bytes(b"new")
    return {"lufs": -14.0}


# what studio.measure returns, every key qa.py check reads after a render
MEASURED = {"seconds": 1, "cuts": 1, "cuts_per_minute": 1, "hook_frame": 0, "hook_ok": True, "planned_cuts": [], "extra_scene_cuts": [],
            "luma": [], "strip": "s", "strip2": "s", "seconds_under_half": 0, "longest_run_under_half": 0}


class Cutoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = fixture.workspace()
        fixture.researched(cls.ws)
        cls.build = cls.ws / "build" / (cls.ws / "build" / "latest").read_text().strip()
        (cls.build / "taste.md").write_text("their month, in prose\n")
        fixture.run(cls.ws, "storyboard.py", "draft")
        cls.board = json.loads((cls.build / "storyboards" / "editorial-quiet" / "storyboard.json").read_text())
        (cls.build / "winner.json").write_text(json.dumps({"board": "editorial-quiet"}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)

    def patched(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(film._env, "writable_run", lambda: self.build))
        stack.enter_context(mock.patch.object(studio, "lock", held))
        return stack

    def test_preview_json_goes_before_the_preview_renders(self):
        pv = self.build / "preview" / "preview.json"
        pv.parent.mkdir(exist_ok=True)
        pv.write_text(json.dumps({"hash": studio.board_hash(self.board)}))
        with self.patched(), mock.patch.object(studio, "render", side_effect=RuntimeError("cut off")):
            with self.assertRaises(RuntimeError):
                film.cmd_preview(None)
        self.assertFalse(pv.exists())

    def test_render_moves_the_reel_in_last_after_the_records_that_name_out_go(self):
        out = self.build / "out"
        (out / "cards").mkdir(parents=True, exist_ok=True)
        for f in ("review.html", "film.mp4", "series.mp4"):
            (out / f).write_text("old")
        for f in ("cards.json", "film.json", "render-report.json"):
            (self.build / f).write_text("{}")
        bed = self.build / "music" / "source.wav"
        bed.parent.mkdir(exist_ok=True)
        bed.write_bytes(b"bed")
        (self.build / "music.json").write_text(json.dumps({"file": str(bed)}))
        (self.build / "critic").mkdir(exist_ok=True)
        (self.build / "critic" / "timed.json").write_text(json.dumps({"hash": studio.board_hash(self.board), "pass": True}))
        real, moved, seen = os.replace, [], {}

        def replace(src, dst):
            if Path(dst).parent in (out, out / "cards"):
                moved.append(Path(dst).name)
                if Path(dst).name == "film.mp4" and not seen:
                    seen.update({f: (out / f).exists() for f in ("review.html",)},
                                **{f: (self.build / f).exists() for f in ("cards.json", "film.json", "render-report.json")})
                    raise OSError("cut off before the reel")
            return real(src, dst)

        with self.patched(), mock.patch.object(studio, "render", made), mock.patch.object(film, "sound", wrote), \
                mock.patch.object(film, "cut", lambda series, start, seconds, o, spawn=None: Path(o).write_bytes(b"new")), \
                mock.patch.object(studio, "measure", lambda *a, **k: dict(MEASURED)), \
                mock.patch.object(film.os, "replace", replace):
            with self.assertRaises(OSError):
                film.cmd_render(None)
        self.assertEqual(seen, {"review.html": False, "cards.json": False, "film.json": False, "render-report.json": False})
        # unasked, the series is no deliverable: a series.mp4 an earlier render left in out/ goes with the records
        self.assertEqual(moved[-1], "film.mp4")
        self.assertNotIn("series.mp4", moved)
        self.assertFalse((out / "series.mp4").exists())
        self.assertEqual((out / "film.mp4").read_text(), "old")

        def failed(jobs, work, name, board=None, run=None, hold=None):
            return {"failed": 1, "exit": 1, "findings": [{"text": "RENDER_ERROR the renderer stopped"}]}

        with self.patched(), mock.patch.object(studio, "render", failed):
            with self.assertRaises(SystemExit):
                film.cmd_render(None)
        self.assertFalse((self.build / "render-report.json").exists())
        with self.patched(), mock.patch.object(studio, "render", made), \
                mock.patch.object(film, "sound", side_effect=RuntimeError("cut off before the files move")):
            with self.assertRaises(RuntimeError):
                film.cmd_render(None)
        rounds = list((self.build / "critic").glob("cut-*.json"))
        here = os.getcwd()
        os.chdir(self.ws)
        try:
            with self.assertRaises(SystemExit):
                vote.cmd_cut(None)
        finally:
            os.chdir(here)
        self.assertEqual(list((self.build / "critic").glob("cut-*.json")), rounds)
        c = qa.checks(self.build, False, spawn=None)
        self.assertEqual([r["check"] for r in c.rows if r["pass"] is False], ["film"])
        with self.patched(), mock.patch.object(studio, "render", made), mock.patch.object(film, "sound", wrote), \
                mock.patch.object(film, "cut", lambda series, start, seconds, o, spawn=None: Path(o).write_bytes(b"new")), \
                mock.patch.object(studio, "measure", lambda *a, **k: dict(MEASURED)):
            self.assertEqual(film.cmd_render(None), 0)
        self.assertEqual((out / "film.mp4").read_text(), "new")
        self.assertEqual(json.loads((self.build / "film.json").read_text()), self.board)
        self.assertEqual(json.loads((self.build / "render-report.json").read_text())["failed"], 0)

    def test_render_moves_the_series_in_when_asked(self):
        sb = self.build / "storyboards" / "editorial-quiet" / "storyboard.json"
        self.addCleanup(_env.write_json, sb, self.board)
        self.addCleanup((self.build / "out" / "series.mp4").unlink, missing_ok=True)
        self.addCleanup(lambda: (self.build / "film.json").exists() and _env.write_json(self.build / "film.json", self.board))
        board = dict(self.board, ask={"counts": False, "seconds": None, "series": True})
        _env.write_json(sb, board)
        bed = self.build / "music" / "source.wav"
        bed.parent.mkdir(exist_ok=True)
        bed.write_bytes(b"bed")
        (self.build / "music.json").write_text(json.dumps({"file": str(bed)}))
        (self.build / "critic").mkdir(exist_ok=True)
        (self.build / "critic" / "timed.json").write_text(json.dumps({"hash": studio.board_hash(board), "pass": True}))
        self.addCleanup(lambda: (self.build / "critic" / "timed.json").write_text(json.dumps({"hash": studio.board_hash(self.board), "pass": True})))
        out, real, moved = self.build / "out", os.replace, []

        def replace(src, dst):
            if Path(dst).parent in (out, out / "cards"):
                moved.append(Path(dst).name)
            return real(src, dst)

        with self.patched(), mock.patch.object(studio, "render", made), mock.patch.object(film, "sound", wrote), \
                mock.patch.object(film, "cut", lambda series, start, seconds, o, spawn=None: Path(o).write_bytes(b"new")), \
                mock.patch.object(studio, "measure", lambda *a, **k: dict(MEASURED)), \
                mock.patch.object(film.os, "replace", replace):
            film.cmd_render(None)
        self.assertEqual(moved[-2:], ["series.mp4", "film.mp4"])
        self.assertEqual(_env.read_json(self.build / "cards.json")["series"], "out/series.mp4")

    def test_a_cut_round_opens_only_on_a_render_film_json_vouches_for(self):
        out = self.build / "out"
        (out / "cards").mkdir(parents=True, exist_ok=True)
        shutil.rmtree(self.build / "critic", ignore_errors=True)
        (self.build / "film.json").unlink(missing_ok=True)
        (out / "film.mp4").write_text("a reel moved in before the cards finished")
        r = subprocess.run([sys.executable, str(fixture.SCRIPTS / "vote.py"), "cut"], cwd=self.ws, capture_output=True, text=True, env=ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("film.json is missing", r.stderr)
        self.assertEqual(list((self.build / "critic").glob("cut-*.json")), [])

    def test_a_run_continued_from_a_delivered_one_opens_no_round_until_it_renders(self):
        ws, run = self.gate_run("continued")
        (run / "delivered.json").write_text("{}")
        here = os.getcwd()
        os.chdir(ws)
        try:
            new = _env.writable_run()
        finally:
            os.chdir(here)
        self.assertNotEqual(new.name, run.name)
        self.assertFalse((ws / new / "film.json").exists())
        r = subprocess.run([sys.executable, str(fixture.SCRIPTS / "vote.py"), "cut"], cwd=ws, capture_output=True, text=True, env=ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("film.json is missing", r.stderr)

    def test_the_critics_round_is_reused_while_its_files_stand(self):
        out = self.build / "out"
        (out / "cards").mkdir(parents=True, exist_ok=True)
        (self.build / "film.json").write_text(json.dumps(self.board))
        shutil.rmtree(self.build / "critic", ignore_errors=True)
        (out / "film.mp4").write_text("cut one")
        for _ in range(2):
            fixture.run(self.ws, "vote.py", "cut")
        self.assertEqual(sorted(p.name for p in (self.build / "critic").glob("cut-*.json")), ["cut-1.json"])
        (out / "film.mp4").write_text("cut two")
        fixture.run(self.ws, "vote.py", "cut")
        self.assertEqual(sorted(p.name for p in (self.build / "critic").glob("cut-*.json")), ["cut-1.json", "cut-2.json"])

    def test_a_render_stages_only_the_clip_frames_clips_json_names(self):
        run = self.build / "clipsrun"
        named, stray = run / "clips" / "frames-1" / "01", run / "clips" / "frames" / "09"
        for d in (named, stray):
            d.mkdir(parents=True)
            (d / "0001.jpg").write_bytes(b"jpg")
        (run / "clips.json").write_text(json.dumps({"frames": "clips/frames-1", "clips": {}}))
        pub = studio.public(run / "work", None, run)
        self.assertTrue((pub / "clips" / "01" / "0001.jpg").exists())
        self.assertFalse((pub / "clips" / "09").exists())

    def test_a_photograph_cut_off_while_it_is_staged_is_never_left_half_written(self):
        src = next((self.ws / "photos").rglob("*.jpg"))
        dest = self.build / "stagetest" / "photos" / "a.jpg"

        def half(im, fp, *a, **k):
            Path(fp).write_bytes(b"\xff\xd8half")
            raise OSError("cut off")

        with mock.patch.object(photos.Image.Image, "save", half):
            with self.assertRaises(OSError):
                photos.stage(src, dest)
        self.assertFalse(dest.exists())
        photos.stage(src, dest)
        self.assertGreater(dest.stat().st_size, 1000)

    def test_deliver_waits_for_a_render_holding_the_run(self):
        with chunks.lock(self.build / "render", "render"):
            r = subprocess.run([sys.executable, str(fixture.SCRIPTS / "deliver.py")], cwd=self.ws, capture_output=True,
                               text=True, env=ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("a render named render is already running", r.stderr)


    def gate_run(self, name):
        """A copy of the workspace whose run deliver reaches the gate in, with stand-in files that fail it."""
        ws = Path(shutil.copytree(self.ws, self.ws.parent / f"{self.ws.name}-{name}"))
        run = ws / "build" / (ws / "build" / "latest").read_text().strip()
        board = json.loads((run / "storyboards" / "editorial-quiet" / "storyboard.json").read_text())
        (run / "film.json").write_text(json.dumps(board))
        (run / "winner.json").write_text(json.dumps({"board": "editorial-quiet"}))
        rows = [{"n": 1, "id": board["beats"][0]["id"], "png": "out/cards/01.png", "mp4": "out/cards/01.mp4"}]
        (run / "cards.json").write_text(json.dumps({"cards": rows}))
        (run / "out" / "cards").mkdir(parents=True, exist_ok=True)
        for f in ("film.mp4", "series.mp4", "cards/01.mp4", "cards/01.png"):
            (run / "out" / f).write_bytes(bytes(32))
        return ws, run

    def deliver_in(self, ws, spawn):
        @contextlib.contextmanager
        def lock(work, name):
            yield types.SimpleNamespace(spawn=spawn)

        def outside(*a, **kw):
            raise AssertionError(f"a process started outside the lock's spawn: {a[0] if a else kw.get('args')}")

        here = os.getcwd()
        os.chdir(ws)
        try:
            with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe", "node": "node", "python": sys.executable}), \
                    mock.patch.object(studio, "lock", lock), mock.patch.object(subprocess, "Popen", outside):
                return deliver.main()
        finally:
            os.chdir(here)

    def test_every_process_the_gate_starts_under_deliver_goes_through_the_locks_spawn(self):
        ws, run = self.gate_run("gate")
        seen = []

        def spawn(argv, **kw):
            seen.append(Path(argv[0]).name)
            return subprocess.CompletedProcess(argv, 0, "{}" if Path(argv[0]).name == "ffprobe" else "", "")

        code = self.deliver_in(ws, spawn)
        self.assertEqual(code, 1)
        self.assertIn("ffprobe", seen)
        self.assertIn("ffmpeg", seen)
        self.assertEqual(set(seen), {"ffmpeg", "ffprobe"})

    def test_a_deliver_on_a_delivered_run_drops_delivered_json_before_out_changes(self):
        ws, run = self.gate_run("again")
        (run / "delivered.json").write_text(json.dumps({"run": run.name, "out": str(ws / "out")}))

        put = _env.write_text

        def first_write(path, text):
            self.assertFalse((run / "delivered.json").exists(), f"delivered.json still stands as {Path(path).name} changes")
            put(path, text)

        def spawn(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, "{}" if argv[0] == "ffprobe" else "", "")

        with mock.patch.object(_env, "write_text", first_write):
            self.assertEqual(self.deliver_in(ws, spawn), 1)
        self.assertFalse((run / "delivered.json").exists())


    def test_the_workspaces_out_stands_whole_wherever_deliver_is_cut_off(self):
        ws, run = self.gate_run("swap")
        (run / "engine.json").write_text("{}")
        old = {"caption.md": "last month's caption", "review.html": "the last month, ready", "film.mp4": "old",
               "cards/09-gone.png": "a card this run does not carry"}

        def last_delivery():
            shutil.rmtree(ws / "out", ignore_errors=True)
            for k, v in old.items():
                (ws / "out" / k).parent.mkdir(parents=True, exist_ok=True)
                (ws / "out" / k).write_text(v)

        class Cut(Exception):
            pass

        real, n = os.replace, 0
        while True:
            n += 1
            last_delivery()
            calls = [0]

            def replace(src, dst, n=n):
                calls[0] += 1
                if calls[0] == n:
                    raise Cut()
                return real(src, dst)

            with mock.patch.object(qa, "checks", lambda run, gate, spawn: qa.Checks()), mock.patch.object(os, "replace", replace):
                try:
                    code = self.deliver_in(ws, subprocess.run)
                except Cut:
                    code = None
            got = {f.relative_to(ws / "out").as_posix(): f.read_bytes() for f in (ws / "out").rglob("*") if f.is_file()}
            self.assertIn("caption.md", got, f"cut off at rename {n}, out/caption.md is gone")
            if "review.html" in got:
                want = {f.relative_to(run / "out").as_posix(): f.read_bytes() for f in (run / "out").rglob("*") if f.is_file()}
                self.assertIn(got, (want, {k: v.encode() for k, v in old.items()}),
                              f"cut off at rename {n}, out/review.html stands over a mix of two deliveries")
            if code is not None:
                break
            self.assertFalse((run / "delivered.json").exists())
        self.assertEqual(code, 0)
        self.assertNotIn("cards/09-gone.png", got)
        self.assertGreater(n, 5)

    def test_a_green_delivers_last_line_is_the_delivered_reels_path_from_the_workspace_root(self):
        ws, run = self.gate_run("path")
        (run / "engine.json").write_text("{}")
        printed = io.StringIO()
        with mock.patch.object(qa, "checks", lambda run, gate, spawn: qa.Checks()), contextlib.redirect_stdout(printed):
            self.assertEqual(self.deliver_in(ws, subprocess.run), 0)
        last = printed.getvalue().splitlines()[-1]
        self.assertEqual(last, f"build/{run.name}/out/film.mp4")
        self.assertTrue((ws / last).is_file())

    def test_a_green_deliver_keeps_the_brief_in_the_run_and_next_months_look_in_build(self):
        ws, run = self.gate_run("kept")
        (run / "engine.json").write_text("{}")
        with mock.patch.object(qa, "checks", lambda run, gate, spawn: qa.Checks()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.deliver_in(ws, subprocess.run), 0)
        self.assertTrue((run / "brief.md").is_file())
        self.assertEqual(json.loads((ws / "build" / "template.json").read_text())["style"], "editorial-quiet")
        for out in (run / "out", ws / "out"):
            self.assertFalse((out / "brief.md").exists(), out)
            self.assertFalse((out / "template.json").exists(), out)
        self.assertNotIn("template.json", (run / "out" / "review.html").read_text())


    def test_a_red_delivers_last_line_names_the_failing_check_and_no_film(self):
        ws, run = self.gate_run("red")

        def checks(run, gate, spawn):
            c = qa.Checks()
            c.add("register", False, "caption 0 hashtags")
            return c

        printed = io.StringIO()
        with mock.patch.object(qa, "checks", checks), contextlib.redirect_stdout(printed), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.deliver_in(ws, subprocess.run), 1)
        last = printed.getvalue().splitlines()[-1]
        self.assertEqual(last, "not delivered: the gate failed on register")
        self.assertNotIn("film.mp4", last)

if __name__ == "__main__":
    unittest.main()
