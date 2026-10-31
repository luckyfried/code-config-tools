"""deliver.py never leaves out/ looking delivered before the gate passes: the page says it is not ready until the gate
has passed, so a deliver stopped partway leaves that page, and a green gate takes the banner off. deliver holds the
run's lock while it writes and runs its gate in its own process with that lock, so a render cannot start while it
runs and every process the gate starts goes through run.spawn.

    python3 -I -m unittest discover -s S/tests -p test_deliver.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import chunks  # noqa: E402
import deliver  # noqa: E402
import qa  # noqa: E402


class Deliver(unittest.TestCase):
    def setUp(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, home, True)
        self.run_dir = run = home / "build" / "r1"
        run.mkdir(parents=True)
        (home / "build" / "RUN").write_text("r1\n")
        for name, obj in (("library.json", {"handle": "a"}), ("taste.json", {"trip": {"name": "lisbon week"}}),
                          ("winner.json", {"board": "1", "totals": {"1": 30}}),
                          ("storyboards/1/storyboard.json", {"id": "1", "look": "Cinematic letterbox",
                                                             "system": {"colors": {"bg": "#1d1b19", "ink": "#1d1b19", "paper": "#f2eadb", "accent": "#c4572f"}}})):
            (run / name).parent.mkdir(parents=True, exist_ok=True)
            (run / name).write_text(json.dumps(obj))
        self.out = run / "out"
        self.out.mkdir()
        (self.out / "review.html").write_text("the last delivery, green")
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        for patch in (mock.patch.object(_env, "HOME", home), mock.patch.dict(os.environ, {"TR_RUN": ""}),
                      mock.patch.object(sys, "argv", ["deliver.py"]),
                      mock.patch.object(_env, "tools", return_value={"ffmpeg": "/t/ffmpeg-test", "ffprobe": "/t/ffprobe-test"}),
                      mock.patch.object(deliver, "caption", return_value="a caption"),
                      mock.patch.object(deliver, "brief", return_value="a brief")):
            patch.start()
            self.addCleanup(patch.stop)

    def gate(self, outcome):
        def gate_checks(run):
            self.during = (self.out / "review.html").read_text()
            self.held_by = run.name
            try:
                with chunks.lock(self.run_dir / "render", "film"):
                    self.render_started = True
            except SystemExit:
                self.render_started = False
            if isinstance(outcome, BaseException):
                raise outcome
            res = qa.Checks()
            res("white", outcome == 0, "2 frames")
            return res
        return mock.patch.object(qa, "gate_checks", gate_checks)

    def test_the_gate_starts_through_the_lock_and_a_render_cannot_start_while_deliver_runs(self):
        with self.gate(0), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(self.held_by, "deliver")
        self.assertFalse(self.render_started)

    def test_every_process_the_gate_starts_goes_through_the_lock(self):
        (self.run_dir / "film.json").write_text(json.dumps({"seconds": 10.0, "cuts": [1.0], "bpm": 120}))
        for name in ("film.mp4", "film-16x9.mp4", "film-square.mp4"):
            (self.out / name).write_bytes(b"a film")
        spawned, outside = [], []

        def spawn(held, argv, **kw):
            spawned.append((held.name, Path(argv[0]).name))
            return subprocess.CompletedProcess(argv, 0, "10.0" if "csv=p=0" in argv else "{}", "")

        def run(argv, **kw):
            outside.append(argv)
            raise AssertionError(f"started outside the lock: {argv}")
        with mock.patch.object(chunks.Run, "spawn", spawn), mock.patch.object(subprocess, "run", run), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        self.assertEqual(outside, [])
        self.assertEqual(sorted(set(spawned)), [("deliver", "ffmpeg-test"), ("deliver", "ffprobe-test")])

    def test_a_deliver_stopped_while_it_writes_the_brief_leaves_the_earlier_brief_whole(self):
        (self.run_dir / "brief.md").write_text("the earlier brief")
        real = Path.write_text

        def write_text(p, text, *a, **kw):
            if "brief" in p.name:
                real(p, text[: len(text) // 2], *a, **kw)
                raise KeyboardInterrupt
            return real(p, text, *a, **kw)
        with self.gate(0), mock.patch.object(Path, "write_text", write_text), self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertEqual((self.run_dir / "brief.md").read_text(), "the earlier brief")
        self.assertIn("Not ready to post.", (self.out / "review.html").read_text())

    def test_a_deliver_stopped_during_the_gate_leaves_a_page_that_is_not_ready(self):
        with self.gate(KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertIn("Not ready to post.", (self.out / "review.html").read_text())
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["caption.md", "review.html"])

    def test_a_green_gate_takes_the_banner_off_and_a_red_one_names_what_failed(self):
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        self.assertIn("Not ready to post.", self.during)
        self.assertNotIn("class='banner'", (self.out / "review.html").read_text())
        with self.gate(1):
            self.assertEqual(deliver.main(), 1)
        self.assertIn("white  2 frames", (self.out / "review.html").read_text())



class Cover(unittest.TestCase):
    """out/ holds only the deliverables, and the review page is the film's page: the board's paper with its ink on it,
    the cover as the film's poster and as the picture to post with, the two other looks with the words that ask for
    one, no score and no link outside out/; qa.py's deliver row refuses anything else in out/."""

    def setUp(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, home, True)
        self.run_dir = run = home / "build" / "r1"
        (run / "storyboards" / "1").mkdir(parents=True)
        (home / "build" / "RUN").write_text("r1\n")
        for name, obj in (("library.json", {"handle": "a"}), ("taste.json", {"trip": {"name": "lisbon week"}}),
                          ("winner.json", {"board": "1", "totals": {"1": 30}}),
                          ("storyboards/1/storyboard.json", {"id": "1", "look": "Cinematic letterbox",
                                                             "system": {"colors": {"bg": "#1d1b19", "ink": "#1d1b19", "paper": "#f2eadb", "accent": "#c4572f"}}})):
            (run / name).write_text(json.dumps(obj))
        self.out = run / "out"
        (self.out / "storyboards").mkdir(parents=True)
        (self.out / "storyboards" / "1.png").write_bytes(b"a sheet")
        for name in ("brief.md", "film.mp4", "cover.png"):
            (self.out / name).write_text("an earlier delivery")
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        for patch in (mock.patch.object(_env, "HOME", home), mock.patch.dict(os.environ, {"TR_RUN": ""}),
                      mock.patch.object(sys, "argv", ["deliver.py"]),
                      mock.patch.object(_env, "tools", return_value={"ffmpeg": "/t/ffmpeg-test", "ffprobe": "/t/ffprobe-test"}),
                      mock.patch.object(deliver, "caption", return_value="a caption"),
                      mock.patch.object(deliver, "brief", return_value="a brief")):
            patch.start()
            self.addCleanup(patch.stop)

    def deliver(self):
        with mock.patch.object(qa, "gate_checks", lambda run: qa.Checks()), contextlib.redirect_stdout(io.StringIO()):
            return deliver.main()

    def test_out_holds_only_the_deliverables_and_the_brief_sits_beside_it(self):
        self.assertEqual(self.deliver(), 0)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["caption.md", "cover.png", "film.mp4", "review.html"])
        self.assertEqual((self.run_dir / "brief.md").read_text(), "a brief")

    def test_the_page_is_paper_with_ink_on_it_and_the_cover_is_its_poster(self):
        self.deliver()
        page = (self.out / "review.html").read_text()
        self.assertIn("background:#f2eadb;color:#1d1b19", page)
        self.assertIn('poster="cover.png"', page)
        self.assertIn("<img src='cover.png'", page)
        self.assertNotIn("storyboards/", page)
        self.assertNotIn("<table>", page)

    def test_the_page_shows_the_other_looks_asks_for_one_and_carries_no_score(self):
        from PIL import Image
        for n, look in (("2", "Analog home movie"), ("3", "Scrapbook")):
            (self.run_dir / "storyboards" / n).mkdir()
            (self.run_dir / "storyboards" / n / "storyboard.json").write_text(json.dumps({"id": n, "look": look}))
        Image.new("RGB", (300, 3 * 120 + 24), "white").save(self.out / "boards.png")
        (self.run_dir / "critic").mkdir()
        (self.run_dir / "critic" / "cut-1.json").write_text(json.dumps({"round": 1, "critics": {
            "motion_designer": {"boards": {"film": {"scores": {"professional": 3, "moves": 5}}}}}}))
        self.assertEqual(self.deliver(), 0)
        self.assertIn("boards.png", sorted(p.name for p in self.out.iterdir()))
        page = (self.out / "review.html").read_text()
        self.assertIn("Prefer another look? Say \u201cmake the second one\u201d", page)
        self.assertIn("Analog home movie: say \u201cmake the second one\u201d", page)
        self.assertIn("Scrapbook: say \u201cmake the third one\u201d", page)
        self.assertNotIn("Cinematic letterbox: say", page, "the film's own look is not offered again")
        for word in ("critic", "professional", "mean", "under the bar", "<table"):
            self.assertNotIn(word, page)
        self.assertNotIn("../", page, "every link on the page stays inside out/")

    def test_the_deliver_row_refuses_a_file_in_out_that_is_not_a_deliverable(self):
        os.chdir(self.run_dir)
        res = qa.Checks()
        with mock.patch.object(qa, "film_checks", return_value=res), mock.patch.object(qa, "board_check", return_value=(True, "")):
            rows = {r[0]: (r[1], r[2]) for r in qa.gate_checks()}
        self.assertFalse(rows["deliver"][0])
        self.assertIn("out/ holds brief.md, storyboards, which is not a deliverable", rows["deliver"][1])
        self.assertIn("brief.md missing", rows["deliver"][1])


if __name__ == "__main__":
    unittest.main()
