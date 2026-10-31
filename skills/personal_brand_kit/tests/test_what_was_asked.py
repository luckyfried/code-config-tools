"""What every run delivers and what the person asked for: film.py render makes the reel, the square and the wide films,
the story card and the posted image on every run, and the stills only when --also names stories, taking away stills an
earlier render left that this one was not asked for; qa.py's gate holds out/ to the deliverables and refuses anything
else in it; deliver.py's last line is the reel's path from the project's root, the path the reply names first.

    python3 -I -m unittest discover -s tests -p test_what_was_asked.py
"""
import argparse
import contextlib
import io
import json
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
import deliver  # noqa: E402
import film  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402

BEATS = [{"id": "hook", "frames": 30, "rest": 5}, {"id": "piece-1", "frames": 30, "rest": 10}, {"id": "closer", "frames": 30, "rest": 20}]
EVERY_RUN = ["film-square.mp4", "film-wide.mp4", "film.mp4", "post.png", "story.png"]


class InRun(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        here = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, here)


class Asked(InRun):
    def setUp(self):
        super().setUp()
        Path("out/stills").mkdir(parents=True)
        for name in ("film.mp4", "film-square.mp4", "film-wide.mp4", "story.png", "stills.json", "stills/01-hook.png"):
            Path("out", name).write_text("an earlier render's")
        self.jobs = []
        self.frames = {}

    def render(self, *also):
        """film.py render with --also naming `also`, the cut passed and the bridge and mux faked: out/ after it."""
        Path("cut.mp4").write_text("the cut, with its master")
        f = {"name": "Kinetic type", "seconds": 3.0, "rests": {"reel": {"hook": 5, "peak": 40, "closer": 80}, "square": {"hook": 6, "peak": 41, "closer": 80}}}
        boards = {fmt: {"beats": BEATS} for fmt in ("reel", "square", "wide")}

        def bridge(jobs, name, run=None):
            for j in jobs:
                self.jobs.append(Path(j["out"]).name)
                self.frames[Path(j["out"]).name] = j.get("frame")
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("new")
            rep = {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}
            _env.write_json(_env.part(studio.report_of(name)), rep)
            return rep

        def mux(run, silent, out, seconds):
            Path(out).write_text("new")
            return False
        with mock.patch.object(film, "film", return_value=(f, boards)), mock.patch.object(film, "ready", return_value=None), \
                mock.patch.object(film, "mux", mux), mock.patch.object(studio, "props", lambda b: {}), \
                mock.patch.object(studio, "render", bridge), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(film.cmd_render(argparse.Namespace(also=list(also), force=False), None), 0)
        return sorted(p.name for p in Path("out").iterdir())

    def test_every_render_makes_the_three_films_and_both_cards_and_takes_the_last_stills_away(self):
        self.assertEqual(self.render(), EVERY_RUN)
        self.assertEqual({Path("out", n).read_text() for n in EVERY_RUN if n != "film.mp4"}, {"new"})
        # the reel is the cut, the file qa.py check measured and the critic watched; the other shapes render
        self.assertEqual(sorted(self.jobs), ["film-square.mp4", "film-wide.mp4", "post.png", "story.png"])
        self.assertEqual(Path("out/film.mp4").read_text(), "the cut, with its master")
        self.assertEqual(_env.read_json(studio.report_of("film"))["made"], {"formats": ["reel", "square", "wide"], "stories": False})
        self.assertEqual(qa.made(), ({"reel", "square", "wide"}, False))

    def test_the_story_card_is_the_hook_at_rest_and_the_image_to_post_the_squares_peak(self):
        self.render()
        self.assertEqual((self.frames["story.png"], self.frames["post.png"]), (5, 41))

    def test_stories_adds_the_stills(self):
        self.assertEqual(self.render("stories"), sorted(EVERY_RUN + ["stills", "stills.json"]))
        self.assertEqual(sorted(p.name for p in Path("out/stills").iterdir()), ["01-hook.png", "02-piece-1.png", "03-closer.png"])
        self.assertEqual(qa.made(), ({"reel", "square", "wide"}, True))


class Refused(InRun):
    """qa.py's gate: out/ holds the deliverables; a still nobody asked for, a missing card or a file that is not a
    deliverable is a red row naming it."""

    def rows(self, made):
        Path("out").mkdir(exist_ok=True)
        for name in ("film.mp4", "film-square.mp4", "film-wide.mp4"):
            Path("out", name).write_bytes(b"a film")
        Path("board.json").write_text(json.dumps({"bpm": 120, "beats": BEATS}))
        Path("film.json").write_text(json.dumps({"boards": dict.fromkeys(qa.FILMS, "board.json"), "findings": [], "hash": "h"}))
        _env.write_json(studio.report_of("film"), {"jobs": 0, "failed": 0, "findings": [], "made": made})
        cards = {"out/story.png": (1080, 1920), "out/post.png": (1080, 1080)}
        with mock.patch.object(qa, "picture"), mock.patch.object(qa, "subject_check"), mock.patch.object(qa, "project"), \
                mock.patch.object(qa, "probe", return_value={"streams": []}), \
                mock.patch.object(qa, "png_size", lambda p: cards.get(Path(p).as_posix())):
            res, _ = qa.gate_checks()
        return [(r[0], r[1], r[2]) for r in res if r[1] is not None]

    def cards(self):
        for name in ("story.png", "post.png"):
            Path("out", name).write_bytes(b"a card")

    def test_the_films_and_cards_pass_their_rows(self):
        Path("out").mkdir()
        self.cards()
        rows = self.rows({"formats": ["reel", "square", "wide"], "stories": False})
        self.assertEqual([r for r in rows if r[0] in ("film", "cards", "stills", "out") and r[1] is False], [])
        self.assertIn(("stills", True, "no stills asked for, none in out/"), rows)
        self.assertIn(("out", True, "out/ holds the deliverables only"), rows)

    def test_a_missing_card_is_red(self):
        Path("out").mkdir()
        Path("out/story.png").write_bytes(b"a card")
        rows = self.rows({"formats": ["reel", "square", "wide"], "stories": False})
        self.assertIn(("cards", False, "out/story.png at 1080x1920, out/post.png missing"), rows)

    def test_a_still_nobody_asked_for_and_a_note_in_out_are_red_and_named(self):
        Path("out/stills").mkdir(parents=True)
        self.cards()
        Path("out/stills/01-hook.png").write_bytes(b"an earlier render's")
        Path("out/brief.md").write_text("the run's notes")
        rows = self.rows({"formats": ["reel", "square", "wide"], "stories": False})
        self.assertIn(("stills", False, "no stills asked for, and out/ holds stills/01-hook.png"), rows)
        self.assertIn(("out", False, "out/ holds the deliverables only; and brief.md"), rows)

    def test_a_render_that_has_not_finished_is_red(self):
        rows = self.rows({"formats": ["reel", "square", "wide"], "stories": False})
        studio.report_of("film").unlink()
        with mock.patch.object(qa, "picture"), mock.patch.object(qa, "subject_check"), mock.patch.object(qa, "project"), \
                mock.patch.object(qa, "probe", return_value={"streams": []}):
            res, _ = qa.gate_checks()
        self.assertIn(("safe", False), [(r[0], r[1]) for r in res if "render/film-report.json" in r[2]])
        self.assertTrue(rows)


class LastLine(InRun):
    """deliver.py ends, on a green gate, with the reel's path from the project's root on a line of its own."""

    def deliver(self, failed):
        root = self.d.resolve()
        run = root / "build" / "20261026T014049Z"
        (run / "out").mkdir(parents=True)
        for name, obj in (("library.json", {"handle": "h"}), ("taste.json", {"x": 1}), ("brand.json", {"handle": "h"}),
                          ("winner.json", {"board": "a"})):
            (run / name).write_text(json.dumps(obj))
        os.chdir(run)
        out = io.StringIO()

        def gate(run=None):
            print("PASS  film      out/film.mp4: 1080x1920")
            if failed:
                print("FAIL  safe      out/film.mp4: 1 render job failed")
                print("FAIL  safe      a font failed to load")
            return failed
        with mock.patch.object(_env, "ROOT", root), mock.patch.object(_env, "enter", lambda new=False: run), \
                mock.patch.object(sys, "argv", ["deliver.py"]), mock.patch.object(deliver, "brief", lambda *a: "a brief"), \
                mock.patch.object(deliver, "caption", lambda *a: "a caption"), mock.patch.object(qa, "gate", gate), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = deliver.main()
        return code, out.getvalue().splitlines()

    def test_the_last_line_is_the_reels_path_from_the_projects_root(self):
        code, lines = self.deliver(0)
        self.assertEqual((code, lines[-1]), (0, "build/20261026T014049Z/out/film.mp4"))

    def test_a_red_gate_ends_on_the_failing_checks_name_and_no_path(self):
        code, lines = self.deliver(1)
        self.assertEqual((code, lines[-1]), (1, "not ready: the gate failed on safe"))


if __name__ == "__main__":
    unittest.main()
