"""film.py render takes the run lock before it writes anything into the run, and out/ takes the three films, the posted
image and the story card only once every one of them is finished, so a refused or failed render leaves out/ as the last finished render left it
and the run's chunks stay where the next command looks for them; a render takes out/review.html away before it changes
anything in out/ and render/film-report.json away until its last rename, the render bridge writes its report under a
working name, so a render that follows one cut short and is itself cut short before its renames leaves no report for
the gate, a preview cut short leaves no preview.json to be read as this cut's, and every process film.py starts under
the lock goes through run.spawn. A finished render ends with qa.py check on what it made. deliver.py holds the lock from
its first write to its last.

    python3 -I -m unittest discover -s S/tests -p test_film_outputs.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import chunks  # noqa: E402
import film  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

# a render takes no options: it always makes the whole set
ASKED = types.SimpleNamespace()


def frames(mp4):
    return chunks._frames(types.SimpleNamespace(spawn=subprocess.run), _env.ffprobe(), mp4)


class Outputs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        run = Path(tmp.name)
        here = Path.cwd()
        os.chdir(run)
        self.addCleanup(os.chdir, here)
        Path("board.json").write_text(json.dumps({"id": "board"}))
        Path("film.json").write_text(json.dumps({
            "hash": "h", "frames": 3, "seconds": 0.1, "boards": {fmt: "board.json" for fmt in film.NAMES},
            "rests": {fmt: {"closer": 2} for fmt in film.NAMES}}))
        Path("qa").mkdir()
        Path("qa/timed.json").write_text(json.dumps({"hash": "h", "pass": True}))
        Path("out").mkdir()
        Path("render").mkdir()
        Path("render/film-report.json").write_text(json.dumps({"jobs": 0, "failed": 0, "findings": [], "last": True}))
        for name in self.LAST:
            (Path("out") / name).write_text("the last finished render")

    LAST = [*film.NAMES.values(), *film.CARDS, "review.html"]

    def untouched(self):
        return {p.name: p.read_text() for p in Path("out").iterdir()} == {name: "the last finished render" for name in self.LAST}

    def test_a_refused_render_writes_nothing_into_the_run(self):
        with studio.lock("preview"):
            with self.assertRaises(SystemExit) as e:
                film.cmd_render(ASKED)
        self.assertIn("a render named preview is already running", str(e.exception.code))
        self.assertTrue(self.untouched())
        self.assertFalse(Path("render/silent").exists())

    def test_a_failed_render_leaves_out_as_it_was(self):
        def failed(jobs, name, run=None):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("half")
            return {"jobs": len(jobs), "failed": 1, "findings": [], "seconds": 0}
        with mock.patch.object(studio, "render", failed), self.assertRaises(SystemExit):
            film.cmd_render(ASKED)
        self.assertTrue(self.untouched())

    def test_a_finished_render_replaces_every_deliverable_and_checks_what_it_made(self):
        checked = []

        def check(run=None):
            checked.append(sorted(p.name for p in Path("out").iterdir()))
            return qa.Checks(), {"hash": "h"}, None
        with mock.patch.object(studio, "render", self.finished), mock.patch.object(qa, "film_checks", check):
            self.assertEqual(film.cmd_render(ASKED), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), sorted([*film.NAMES.values(), *film.CARDS]))
        self.assertEqual(checked, [sorted([*film.NAMES.values(), *film.CARDS])])
        self.assertEqual(json.loads(Path("qa/check.json").read_text())["hash"], "h")
        self.assertEqual(Path("out/post.png").read_text(), "still")
        self.assertTrue(all(frames(Path("out") / n) == 3 for n in film.NAMES.values()))
        self.assertEqual(sorted(p.name for p in Path("render/silent").iterdir()), [])
        self.assertEqual(json.loads(Path("render/film-report.json").read_text())["jobs"], 2 * len(film.NAMES) + len(film.CARDS))

    def test_a_render_cut_short_among_the_renames_leaves_no_review_page(self):
        real = os.replace

        def cut(src, dst):
            if Path(dst).suffix == ".mp4":
                raise KeyboardInterrupt
            real(src, dst)
        with mock.patch.object(studio, "render", self.finished), mock.patch.object(film.os, "replace", cut), \
                self.assertRaises(KeyboardInterrupt):
            film.cmd_render(ASKED)
        self.assertFalse(Path("out/review.html").exists())
        self.assertFalse(Path("render/film-report.json").exists())
        self.assertEqual(Path("out/post.png").read_text(), "still")

    def test_a_render_after_one_cut_short_among_its_renames_and_cut_short_before_its_own_leaves_no_report(self):
        real, moved = os.replace, []

        def cut(src, dst):
            if Path(dst).suffix == ".mp4":
                moved.append(dst)
                if len(moved) == 2:
                    raise KeyboardInterrupt
            real(src, dst)
        with mock.patch.object(studio, "render", self.finished), mock.patch.object(film.os, "replace", cut), \
                self.assertRaises(KeyboardInterrupt):
            film.cmd_render(ASKED)
        self.assertEqual(frames("out/film-16x9.mp4"), 3)
        self.assertEqual(Path("out/film.mp4").read_text(), "the last finished render")

        def chunked(run, jobs, *a):
            return self.finished(jobs, "film")
        tools = dict(_env.tools(), engine="remotion", node="node", motion=".")
        with mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "public", return_value=Path(".")), \
                mock.patch.object(chunks, "render", chunked), mock.patch.object(film, "mux", side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            film.cmd_render(ASKED)
        self.assertFalse(Path("render/film-report.json").exists())
        with mock.patch.object(qa, "FILMS", {}), mock.patch.object(qa, "cards_check", return_value=(True, "")):
            res, _, _ = qa.film_checks()
        self.assertEqual([(r[0], r[1]) for r in res if r[0] == "safe"], [("safe", False)])

    def test_a_preview_cut_short_leaves_no_preview_json(self):
        Path("preview").mkdir()
        Path("preview/preview.json").write_text(json.dumps({"hash": "h"}))

        def cut(jobs, name, run=None):
            raise KeyboardInterrupt
        with mock.patch.object(studio, "render", cut), self.assertRaises(KeyboardInterrupt):
            film.cmd_preview(None)
        self.assertFalse(Path("preview/preview.json").exists())

    @staticmethod
    def finished(jobs, name, run=None):
        for j in jobs:
            Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
            if j["type"] == "video":
                subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30",
                                "-frames:v", "3", "-pix_fmt", "yuv420p", j["out"]], check=True)
            else:
                Path(j["out"]).write_text("still")
        return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 0}


class UnderTheLock(unittest.TestCase):
    """Every process film.py starts while it holds the run's lock goes through run.spawn: the mux, its peak read and the
    measure."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        Path("music").mkdir()
        ff = _env.ffmpeg()
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30", "-frames:v", "30", "-pix_fmt", "yuv420p",
                        "silent.mp4"], check=True)
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=d=1", "music/master-1.wav"], check=True)
        Path("music.json").write_text(json.dumps({"master": "music/master-1.wav"}))
        self.started, real = [], subprocess.run

        class Run:
            def spawn(_, argv, **kw):
                self.started.append(Path(argv[0]).name)
                return real(argv, **kw)

        self.run_ = Run()
        refuse = mock.patch.object(subprocess, "run", side_effect=AssertionError("a process started outside run.spawn"))
        refuse.start()
        self.addCleanup(refuse.stop)

    def test_the_mux_and_the_measure_start_through_run_spawn(self):
        self.assertTrue(film.mux(self.run_, Path("silent.mp4"), Path("film.mp4"), 1))
        m = studio.measure(Path("film.mp4"), [], run=self.run_)
        self.assertEqual(m["frames"], 30)
        self.assertGreaterEqual(len(self.started), 8)


class CutChanged(unittest.TestCase):
    """render/film-report.json vouches for out/ as the render of one cut: a snap that cuts again takes it away first, so
    the old films never pass the gate as the new cut's, with no render after the snap or with one killed before its
    renames."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        shutil.copyfile(KIT / "tests" / "data" / "trip.json", "source.json")
        Path("winner.json").write_text(json.dumps({"board": "swiss-grid"}))
        Path("film.json").write_text(json.dumps({"style": "swiss-grid", "hash": "the old cut"}))
        Path("render").mkdir()
        Path("render/film-report.json").write_text(json.dumps({"jobs": 1, "failed": 0, "findings": []}))
        Path("out").mkdir()
        for name in film.NAMES.values():
            (Path("out") / name).write_text("the film of the old cut")

    def safe(self):
        with mock.patch.object(qa, "FILMS", {}), mock.patch.object(qa, "cards_check", return_value=(True, "")):
            res, _, _ = qa.film_checks()
        return [r[1] for r in res if r[0] == "safe"]

    def test_a_snap_that_cuts_again_leaves_no_report_for_the_old_films(self):
        storyboard.cmd_snap(None)
        self.assertNotEqual(json.loads(Path("film.json").read_text())["hash"], "the old cut")
        self.assertFalse(Path("render/film-report.json").exists())
        self.assertEqual(self.safe(), [False])

    def test_a_snap_then_a_render_killed_before_its_renames_leaves_no_report(self):
        storyboard.cmd_snap(None)
        Path("qa").mkdir()
        Path("qa/timed.json").write_text(json.dumps({"hash": json.loads(Path("film.json").read_text())["hash"], "pass": True}))

        def chunked(run, jobs, *a):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
            return Outputs.finished(jobs, "film")
        tools = dict(_env.tools(), engine="remotion", node="node", motion=".")
        with mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "public", return_value=Path(".")), \
                mock.patch.object(chunks, "render", chunked), mock.patch.object(film, "mux", side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            film.cmd_render(ASKED)
        self.assertEqual(Path("out/film.mp4").read_text(), "the film of the old cut")
        self.assertFalse(Path("render/film-report.json").exists())
        self.assertEqual(self.safe(), [False])


class Delivered(unittest.TestCase):
    """deliver.py: out/review.html says the gate has not passed until it passes, so a deliver cut short at the gate
    leaves a page that says not ready, and only a passing gate leaves the page without the banner."""

    def setUp(self):
        import deliver
        self.deliver = deliver
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        for name, obj in (("library.json", {"handle": "maren", "year": 2025}), ("taste.json", {"year": 2025}),
                          ("winner.json", {"board": "scrapbook"}), ("places.json", {"places": [{"name": "Lisbon"}]})):
            Path(name).write_text(json.dumps(obj))
        Path("out").mkdir()
        Path("out/review.html").write_text("<p>the last delivered page</p>")
        for patch in (mock.patch.object(deliver, "brief", lambda *a: "brief"), mock.patch.object(deliver, "caption", lambda *a: "caption"),
                      mock.patch.object(deliver._env, "enter_run"), mock.patch.object(sys, "argv", ["deliver.py"])):
            patch.start()
            self.addCleanup(patch.stop)

    def gate(self, ok):
        res = qa.Checks()
        res("format", ok, "out/film.mp4: 1080x1920")
        return mock.patch.object(qa, "gate_checks", return_value=(res, {"hash": "h"}))

    def test_a_deliver_cut_short_at_the_gate_leaves_a_page_that_says_not_ready(self):
        with mock.patch.object(qa, "gate_checks", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.deliver.main()
        self.assertIn("Not ready to post", Path("out/review.html").read_text())

    def test_only_a_passing_gate_leaves_the_page_without_the_banner(self):
        with self.gate(False):
            self.assertEqual(self.deliver.main(), 1)
        self.assertIn("<li>format out/film.mp4: 1080x1920</li>", Path("out/review.html").read_text())
        with self.gate(True):
            self.assertEqual(self.deliver.main(), 0)
        page = Path("out/review.html").read_text()
        self.assertNotIn("Not ready to post", page)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["caption.md", "review.html"])
        self.assertEqual(Path("brief.md").read_text(), "brief")

    def test_deliver_holds_the_lock_through_its_gate_and_runs_the_gate_under_it(self):
        seen = []

        def gate(run):
            with self.assertRaises(SystemExit) as e, studio.lock("film"):
                pass
            seen.append((type(run), str(e.exception.code)))
            return qa.Checks(), {"hash": "h"}
        with mock.patch.object(qa, "gate_checks", gate):
            self.assertEqual(self.deliver.main(), 0)
        self.assertEqual([x[0] for x in seen], [chunks.Run])
        self.assertIn("a render named deliver is already running", seen[0][1])
        with studio.lock("film"):
            pass

    def test_every_process_the_gate_starts_under_deliver_goes_through_run_spawn(self):
        ff, real = _env.ffmpeg(), subprocess.run
        for name, size in (("film.mp4", "1080x1920"), ("film-16x9.mp4", "1920x1080"), ("film-square.mp4", "1080x1080")):
            real([ff, "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s={size}:r=30:d=1", "-f", "lavfi", "-i", "sine=d=1",
                  "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", f"out/{name}"], check=True)
        Path("film.json").write_text(json.dumps({"hash": "h", "tone": "drive", "cuts": [], "hook_frame": 0, "sound": [], "bpm": 120,
                                                 "boards": {"reel": "board.json"}, "length": [20, 40]}))
        Path("board.json").write_text(json.dumps({"route": {"cards": []}}))
        Path("music.json").write_text(json.dumps({"file": "music/source.wav", "origin": "their own track"}))
        Path("render").mkdir()
        Path("render/film-report.json").write_text(json.dumps({"jobs": 1, "failed": 0, "findings": []}))
        Path("engine.json").write_text(json.dumps({"engine": "remotion"}))
        started = []

        def spawn(run, argv, **kw):
            started.append(argv[0])
            return real(argv, **kw)
        with mock.patch.object(qa, "timed_checks", return_value=(qa.Checks(), json.loads(Path("film.json").read_text()))), \
                mock.patch.object(chunks.Run, "spawn", spawn), \
                mock.patch.object(subprocess, "run", side_effect=AssertionError("a process started outside run.spawn")):
            self.deliver.main()
        self.assertEqual(set(started), {_env.ffprobe(), _env.ffmpeg()})
        self.assertGreaterEqual(started.count(_env.ffprobe()), 3)
        self.assertGreaterEqual(started.count(_env.ffmpeg()), 9)


class CriticRow(unittest.TestCase):
    """The gate's critic row passes only a cut round the vote would take: every score and every paragraph."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the cut")
        Path("critic").mkdir()
        for name, ret in (("timed_checks", (qa.Checks(), {})), ("film_checks", (qa.Checks(), {"boards": {"reel": "board.json"}}, None)),
                          ("words_in", []), ("places_check", (True, "places"))):
            patch = mock.patch.object(qa, name, return_value=ret)
            patch.start()
            self.addCleanup(patch.stop)

    def row(self, words):
        board = {"scores": dict.fromkeys(vote.CRITERIA, 4),
                 "paragraph": " ".join(["word"] * 30)}
        short = dict(board, paragraph=" ".join(["word"] * words))
        Path("critic/cut-1.json").write_text(json.dumps({"round": 1, "film": qa.sha(Path("out/film.mp4")), "critics": {
            "motion_designer": {"boards": {"film": board}}, "person": {"boards": {"film": short}}}}))
        res, _ = qa.gate_checks()
        return next(r for r in res if r[0] == "critic")

    def test_a_round_of_fours_with_a_ten_word_paragraph_is_red_and_names_it(self):
        _, ok, detail = self.row(10)
        self.assertFalse(ok)
        self.assertIn("person / board film: the paragraph needs at least 25 words", detail)

    def test_a_round_of_fours_with_full_paragraphs_is_green(self):
        _, ok, detail = self.row(25)
        self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
