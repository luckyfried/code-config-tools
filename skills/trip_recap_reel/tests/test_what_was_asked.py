"""What the person asked for: film.py render makes the reel and its cover alone unless --also names the 16:9 film, the square film or
the story cards, makes exactly the ones it names, and takes away an extra an earlier render left that this one was not
asked for; qa.py refuses an extra in out/ the render did not make; deliver.py's last line is the reel's path from the
project's root, the path the reply names first.

    python3 -I -m unittest discover -s S/tests -p test_what_was_asked.py
"""
import argparse
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
import deliver  # noqa: E402
import film  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402

EXTRAS = ["film-16x9.mp4", "film-square.mp4"] + [f"story-{n}.png" for n in range(1, 6)]


def board():
    return {"beats": [{"frames": 60}], "seconds": 2.0, "stories": ["a", "b", "c", "d", "e"],
            "rests": {"a": 5, "b": 20, "c": 30, "d": 40, "e": 50, "closer": 55}, "timeline": [{"id": "hook", "start": 0, "frames": 60}]}


class Asked(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        here = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, here)
        Path("out").mkdir()
        for name in ["film.mp4"] + EXTRAS:
            Path("out", name).write_text("an earlier render's")
        self.jobs = []

    def render(self, *also):
        """film.py render with --also naming `also`, its bridge and mux faked: (exit code, out/ after it)."""
        def bridge(jobs, name, run=None):
            for j in jobs:
                self.jobs.append(Path(j["out"]).name)
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("new")
            return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}

        def mux(silent, out, seconds, run):
            os.replace(silent, out)
            return False
        boards = {"reel": board(), "landscape": board(), "square": board()}
        with mock.patch.object(film, "films", lambda: boards), mock.patch.object(film, "mux", mux), \
                mock.patch.object(studio, "props", lambda b: {"board": "fixture"}), mock.patch.object(studio, "render", bridge), \
                contextlib.redirect_stdout(io.StringIO()):
            code = film.cmd_render(argparse.Namespace(also=list(also)), None)
        return code, sorted(p.name for p in Path("out").iterdir())

    def test_a_render_nobody_asked_extras_of_makes_the_reel_alone_and_takes_the_last_extras_away(self):
        self.assertEqual(self.render(), (0, ["cover.png", "film.mp4"]))
        self.assertEqual(Path("out/film.mp4").read_text(), "new")
        self.assertEqual([j for j in self.jobs if not j.startswith("reel-")], ["film.mp4", "cover.png"])
        self.assertEqual(_env.read_json("render/film-report.json")["made"], {"formats": ["reel"], "stories": False})
        self.assertEqual(qa.made(), ({"reel"}, False))

    def test_also_makes_exactly_the_shapes_it_names(self):
        for also, extra in ((["square"], ["film-square.mp4"]),
                            (["landscape", "stories"], ["film-16x9.mp4"] + [f"story-{n}.png" for n in range(1, 6)]),
                            (["landscape", "square", "stories"], EXTRAS)):
            self.jobs = []
            self.assertEqual(self.render(*also), (0, sorted(["cover.png", "film.mp4"] + extra)), also)
            self.assertEqual({Path("out", n).read_text() for n in ["film.mp4"] + extra}, {"new"}, also)
            self.assertEqual(sorted({j.split("-")[0] for j in self.jobs if j.endswith(".png") and not j.startswith(("story-", "cover"))}),
                             sorted(["reel"] + [f for f in ("landscape", "square") if f in also]), also)
        self.assertEqual(qa.made(), ({"reel", "landscape", "square"}, True))

    def test_the_render_refuses_a_shape_it_does_not_know(self):
        with mock.patch.object(sys, "argv", ["film.py", "render", "--also", "portrait"]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            film.main()
        self.assertEqual(e.exception.code, 2)


class Refused(unittest.TestCase):
    """qa.py film checks: a shape in out/ the last render did not make is a red row naming it."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        here = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, here)
        _env.write_json("film.json", dict(board(), bpm=120, sound=[], cuts=[1.0]))
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the reel")

    def rows(self, made):
        _env.write_json("render/film-report.json", {"jobs": 1, "failed": 0, "findings": [], "made": made})
        streams = {"streams": [{"codec_type": "video", "width": 1080, "height": 1920, "codec_name": "h264", "profile": "High",
                                "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}], "format": {"duration": "2.0"}}
        with mock.patch.object(qa, "probe", return_value=streams), mock.patch.object(qa, "detect", return_value=[]), \
                mock.patch.object(qa, "frame_luma", return_value=[0.3]), mock.patch.object(qa, "board_check", return_value=(True, "board")), \
                mock.patch.object(qa, "figures"), mock.patch.object(studio, "measure"):
            return {r[0]: (r[1], r[2]) for r in qa.film_checks() if r[1] is not None}

    def test_the_reel_alone_passes_with_no_extra_rows_red(self):
        rows = self.rows({"formats": ["reel"], "stories": False})
        self.assertEqual([k for k, (ok, _) in rows.items() if ok is False], [])
        self.assertIn("no story cards asked for", rows["stories"][1])

    def test_an_extra_nobody_asked_for_is_red_and_named(self):
        Path("out/film-16x9.mp4").write_bytes(b"an earlier render's")
        Path("out/story-1.png").write_bytes(b"an earlier render's")
        rows = self.rows({"formats": ["reel"], "stories": False})
        self.assertEqual(rows["landscape"][0], False)
        self.assertIn("out/film-16x9.mp4 is in out/, and the render did not make it (nobody asked for it)", rows["landscape"][1])
        self.assertEqual(rows["stories"][0], False)
        self.assertIn("story-1.png", rows["stories"][1])


class LastLine(unittest.TestCase):
    """deliver.py ends, on a green gate, with the reel's path from the project's root on a line of its own."""

    def setUp(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))).resolve()
        self.addCleanup(shutil.rmtree, home, True)
        run = home / "build" / "20261026-014049"
        (run / "out").mkdir(parents=True)
        (home / "build" / "RUN").write_text("20261026-014049\n")
        for name, obj in (("library.json", {"handle": "a"}), ("taste.json", {"trip": {"name": "lisbon week"}}),
                          ("winner.json", {"board": "1", "totals": {"1": 30}}),
                          ("storyboards/1/storyboard.json", {"id": "1", "look": "Cinematic letterbox",
                                                             "system": {"colors": {"bg": "#1d1b19", "ink": "#1d1b19", "paper": "#f2eadb", "accent": "#c4572f"}}})):
            (run / name).parent.mkdir(parents=True, exist_ok=True)
            (run / name).write_text(json.dumps(obj))
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        for patch in (mock.patch.object(_env, "HOME", home), mock.patch.dict(os.environ, {"TR_RUN": ""}),
                      mock.patch.object(sys, "argv", ["deliver.py"]),
                      mock.patch.object(deliver, "caption", return_value="a caption"),
                      mock.patch.object(deliver, "brief", return_value="a brief")):
            patch.start()
            self.addCleanup(patch.stop)

    def deliver(self, ok):
        res = qa.Checks()
        res("film", ok, "1080x1920")
        out = io.StringIO()
        with mock.patch.object(qa, "gate_checks", return_value=res), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            code = deliver.main()
        return code, out.getvalue().splitlines()

    def test_the_last_line_is_the_reels_path_from_the_projects_root(self):
        code, lines = self.deliver(True)
        self.assertEqual((code, lines[-1]), (0, "build/20261026-014049/out/film.mp4"))

    def test_a_red_gate_ends_on_the_failing_checks_name_and_no_path(self):
        code, lines = self.deliver(False)
        self.assertEqual((code, lines[-1]), (1, "not ready: the gate failed on film"))


if __name__ == "__main__":
    unittest.main()
