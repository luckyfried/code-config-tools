"""film.py render makes the films and stills in the run, and out/ takes them by rename only when every format
succeeded: a failed render leaves out/ as it was, and one that succeeds replaces every film and still. The reel renders
alone unless the person asked for more: --also landscape, square and stories add the wide film, the square film and the
stills, exactly the ones named, and qa.py check fails on a shape in out/ that the render did not make.

    python3 -I -m unittest discover -s S/tests -p test_film.py
"""
import io
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import film  # noqa: E402
import qa  # noqa: E402

# the processes a test's command starts run outside any run's lock
PLAIN = types.SimpleNamespace(spawn=subprocess.run)


class FilmOutputs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name)
        board = {"beats": []}
        self.f = {"hash": "h", "frames": 23, "bpm": 120, "seconds": 1}
        for patch in (mock.patch.object(_env, "_RUN", self.d / "B"), mock.patch.object(film.compose, "lay", lambda *a: board),
                      mock.patch.object(film.compose, "rest_frames", lambda *a: [("hook", 0)])):
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.d)
        (self.d / "out" / "stills").mkdir(parents=True)
        Path("out/film.mp4").write_bytes(b"the last film")
        Path("out/stills/reel-hook.png").write_bytes(b"the last still")

    def render(self, failed, also=("landscape", "square", "stories")):
        def fake(jobs, name, run):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_bytes(b"new " + j["type"].encode())
            return {"failed": failed}
        with mock.patch.object(film.studio, "render", fake), redirect_stdout(io.StringIO()):
            return film._render(self.f, PLAIN, also)

    def test_a_failed_render_leaves_out_as_it_was(self):
        with self.assertRaises(SystemExit):
            self.render(1)
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last film")
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["film.mp4", "stills"])
        self.assertEqual(Path("out/stills/reel-hook.png").read_bytes(), b"the last still")

    def test_a_render_that_succeeds_replaces_every_film_and_still(self):
        self.assertEqual(self.render(0), 0)
        self.assertEqual({p.name: p.read_bytes() for p in Path("out").glob("*.mp4")},
                         {"film.mp4": b"new video", "film-square.mp4": b"new video", "film-wide.mp4": b"new video"})
        self.assertEqual(sorted(p.name for p in Path("out/stills").iterdir()), ["feed-hook.png", "reel-hook.png", "wide-hook.png"])

    def test_the_ready_page_goes_before_the_first_file_moves_in_and_the_reel_moves_last(self):
        Path("out/review.html").write_text("ready to post")
        moved, real = [], os.replace

        def replace(src, dst):
            moved.append((Path(dst).name, Path("out/review.html").exists()))
            real(src, dst)
        with mock.patch.object(film.os, "replace", replace):
            self.assertEqual(self.render(0), 0)
        self.assertEqual([page for _, page in moved], [False] * len(moved))
        self.assertEqual([name for name, _ in moved if name != "film-report.json"][-1], "film.mp4")
        self.assertFalse(Path("out/review.html").exists())

    def test_the_render_report_is_gone_while_out_changes_and_comes_back_after_the_reel(self):
        report = film.studio.render_dir() / "film-report.json"
        report.parent.mkdir(parents=True)
        report.write_text('{"failed": 0, "jobs": 9}')  # the last render's, passing
        moved, real = [], os.replace

        def replace(src, dst):
            moved.append(report.exists())
            real(src, dst)
        with mock.patch.object(film.os, "replace", replace):
            self.assertEqual(self.render(0), 0)
        self.assertEqual(moved, [False] * len(moved))
        self.assertEqual(_env.read_json(report)["failed"], 0)


    def test_a_render_nobody_asked_extras_of_makes_the_reel_alone_and_takes_the_last_extras_away(self):
        Path("out/film-square.mp4").write_bytes(b"the last square film")
        Path("out/film-wide.mp4").write_bytes(b"the last wide film")
        self.assertEqual(self.render(0, ()), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["film.mp4", "post.png", "story.png"])
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"new video")
        self.assertEqual(Path("out/post.png").read_bytes(), b"new still", "the feed post is the square closer at rest")
        self.assertEqual(Path("out/story.png").read_bytes(), b"new still", "the story is the reel's hook at rest")
        self.assertEqual(_env.read_json(film.studio.render_dir() / "film-report.json")["made"], {"formats": ["reel"], "stories": False, "posts": True})
        self.assertEqual(qa.made(), ({"reel"}, False))

    def test_also_makes_exactly_the_shapes_the_person_asked_for(self):
        self.assertEqual(self.render(0, ("square",)), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["film-square.mp4", "film.mp4", "post.png", "story.png"])
        self.assertEqual(self.render(0, ("landscape", "stories")), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["film-wide.mp4", "film.mp4", "post.png", "stills", "story.png"])
        self.assertEqual(sorted(p.name for p in Path("out/stills").iterdir()), ["reel-hook.png", "wide-hook.png"])
        self.assertEqual(qa.made(), ({"reel", "wide"}, True))

    def test_the_render_command_takes_the_shapes_after_also(self):
        got = {}
        with mock.patch.object(sys, "argv", ["film.py", "render", "--also", "landscape", "square", "stories"]), \
                mock.patch.object(film, "cmd_render", lambda a: got.setdefault("also", a.also) and 0):
            film.main()
        self.assertEqual(got["also"], ["landscape", "square", "stories"])

    def test_the_quiet_after_the_stop_is_measured_from_the_stop_on(self):
        import math
        import wave
        path = self.d / "stop.wav"
        rate = 48000
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            tone = (int(9000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate))
            w.writeframes(b"".join(v.to_bytes(2, "little", signed=True) for v in tone) + bytes(2 * rate))
        self.assertGreater(qa.after(path, 0.0, PLAIN), qa.QUIET)
        self.assertLessEqual(qa.after(path, 1.05, PLAIN), qa.QUIET)

    def test_the_check_fails_on_a_shape_in_out_that_nobody_asked_for(self):
        (self.d / "B").mkdir()
        _env.write_json(self.d / "B" / "film.json", {"hash": "h", "bpm": 120, "rest": ["hook"], "cuts": [], "hook_frame": 0})
        _env.write_json(film.studio.render_dir() / "film-report.json", {"failed": 0, "jobs": 1, "findings": [],
                                                                         "made": {"formats": ["reel"], "stories": False}})
        Path("out/film-wide.mp4").write_bytes(b"a wide film nobody asked for")
        with mock.patch.object(qa, "probe", return_value={}), mock.patch.object(qa, "detect", return_value=[]), \
                mock.patch.object(qa.studio, "measure", return_value={}), mock.patch.object(qa, "figures"):
            res, _, _ = qa.film_checks(PLAIN)
        bad = {(r[0], r[2]) for r in res if r[1] is False}
        self.assertIn(("format", "out/film-wide.mp4 is in out/, and the render did not make it (nobody asked for it)"), bad)
        self.assertTrue(any(name == "stills" and "reel-hook.png" in detail for name, detail in bad), bad)
        self.assertFalse(any("film-square.mp4" in detail for _, detail in bad), bad)


if __name__ == "__main__":
    unittest.main()
