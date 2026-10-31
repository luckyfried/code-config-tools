"""film.py render as a command: out/ gains its films, story cards and cover only once every job of the command succeeded, and
a failed one leaves out/ as it was. A render that changes out/ makes every film first, removes the review page,
timeline.json and the render report the gate reads before out/ changes, moves the reel in last and writes the report
after it; a preview removes preview.json before it renders. The bridge is faked, so these read what the command does around it; the refusal
by a running render is in test_resume.py, against the real lock.

    python3 -I -m unittest discover -s S/tests -p test_render_cmd.py
"""
import argparse
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import film  # noqa: E402
import studio  # noqa: E402


def board(seconds=2.0):
    return {"beats": [{"frames": 60}], "seconds": seconds, "stories": ["a", "b"], "rests": {"a": 5, "b": 40, "closer": 55},
            "timeline": [{"id": "hook", "start": 0, "frames": 60}]}


class RenderCommand(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        self.boards = boards = {"reel": board(), "landscape": None, "square": None}
        for name, value in (("films", lambda: boards), ("mux", self.mux)):
            self.addCleanup(setattr, film, name, getattr(film, name))
            setattr(film, name, value)
        self.addCleanup(setattr, studio, "props", studio.props)
        studio.props = lambda b: {"board": "fixture"}
        (self.d / "out").mkdir()
        for name in ("film.mp4", "story-1.png", "story-2.png", "story-3.png"):
            (self.d / "out" / name).write_text("earlier")

    def mux(self, silent, out, seconds, run):
        os.replace(silent, out)
        return False

    def run_render(self, bridge):
        self.addCleanup(setattr, studio, "render", studio.render)
        studio.render = bridge
        with contextlib.redirect_stdout(io.StringIO()):
            return film.cmd_render(argparse.Namespace(also=list(film.ALSO)), None)

    def earlier(self):
        return {f.name: f.read_text() for f in (self.d / "out").iterdir()}

    def test_a_failed_job_leaves_out_as_it_was(self):
        def bridge(jobs, name, run=None):
            for j in jobs:
                if "story-1" not in j["out"]:
                    Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                    Path(j["out"]).write_text("new")
            return {"jobs": len(jobs), "failed": 1, "findings": [], "seconds": 1}
        before = self.earlier()
        self.assertEqual(self.run_render(bridge), 1)
        self.assertEqual(self.earlier(), before)

    def test_a_whole_render_replaces_the_films_and_the_cards(self):
        def bridge(jobs, name, run=None):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("new")
            return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}
        self.assertEqual(self.run_render(bridge), 0)
        self.assertEqual(self.earlier(), {"film.mp4": "new", "story-1.png": "new", "story-2.png": "new", "cover.png": "new"})

    def test_out_changes_after_every_mux_review_page_first_and_reel_last(self):
        self.boards["landscape"] = board()
        (self.d / "out" / "review.html").write_text("the last delivery, green")
        Path("timeline.json").write_text("{}")
        before, seen, moved = self.earlier(), [], []

        def mux(silent, out, seconds, run):
            seen.append(self.earlier())
            os.replace(silent, out)
            return False
        film.mux = mux
        real = os.replace

        report = Path("render/film-report.json")

        def replace(src, dst):
            if Path(dst).resolve().parent == (self.d / "out").resolve():
                moved.append((Path(dst).name, (self.d / "out" / "review.html").exists(), Path("timeline.json").exists(),
                              report.exists()))
            real(src, dst)

        def bridge(jobs, name, run=None):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("new")
            rep = {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}
            _env.write_json(report, rep)
            return rep
        with mock.patch.object(film.os, "replace", replace):
            self.assertEqual(self.run_render(bridge), 0)
        self.assertEqual(seen, [before, before])
        self.assertEqual(moved[-1][0], "film.mp4")
        self.assertEqual([m[1:] for m in moved], [(False, False, False)] * len(moved))
        self.assertTrue(Path("timeline.json").exists())
        self.assertEqual(_env.read_json(report)["failed"], 0)

    def test_a_preview_removes_its_index_before_it_renders(self):
        (self.d / "preview").mkdir()
        (self.d / "preview" / "preview.json").write_text("{}")

        def bridge(jobs, name, run=None):
            self.index_during = (self.d / "preview" / "preview.json").exists()
            raise KeyboardInterrupt
        self.addCleanup(setattr, studio, "render", studio.render)
        studio.render = bridge
        with self.assertRaises(KeyboardInterrupt):
            film.cmd_preview(argparse.Namespace(), None)
        self.assertFalse(self.index_during)
        self.assertFalse((self.d / "preview" / "preview.json").exists())


if __name__ == "__main__":
    unittest.main()
