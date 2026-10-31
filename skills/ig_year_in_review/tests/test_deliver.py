"""deliver.py never leaves out/ looking delivered before the gate passes: the page says it is not ready until the gate
has passed, so a deliver stopped partway leaves that page, and a green gate takes the banner off. The gate runs in
deliver's own process under its lock, so nothing it starts escapes the lock. The page reads: its text is a color of the
look's that contrasts with its ground. It shows the film: the player's poster is the hook's frame (its story card) and
the strip beside it is the reel's frames at rest, 9:16, in the film's order. out/ holds only what is posted and that
page: the working brief stays in build/. The page is the person's: the other two looks with the line that picks one,
how the film was made in plain words, and no score, no rule name and no critic; the scores of the cut, against the bar,
are in build/brief.md, which says so when the delivered cut is under it.

    python3 -I -m unittest discover -s S/tests -p test_deliver.py
"""
import json
import os
import re
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
import palette  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import style  # noqa: E402
import vote  # noqa: E402


BRIEF = deliver.brief


class Deliver(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        build = self.dir / "build"
        build.mkdir()
        for name, obj in (("library.json", {"handle": "a", "year": 2026}), ("taste.json", {"register": {}}),
                          ("winner.json", {"board": "kinetic-type", "by": "person", "why": ""}),
                          ("film.json", {"boards": {"reel": "board.json"}}), ("board.json", {})):
            (build / name).write_text(json.dumps(obj))
        self.out = self.dir / "out"
        self.out.mkdir()
        (self.out / "review.html").write_text("the last delivery, green")
        for patch in (mock.patch.object(_env, "WORKSPACE", self.dir), mock.patch.object(_env, "_TOOLS", {}),
                      mock.patch.object(deliver, "caption", return_value="a caption"),
                      mock.patch.object(deliver, "brief", return_value="a brief")):
            patch.start()
            self.addCleanup(patch.stop)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)

    def gate(self, outcome):
        def checks(run):
            self.during = (self.out / "review.html").read_text()
            self.run = run
            if isinstance(outcome, BaseException):
                raise outcome
            return qa.Checks([("vote", outcome == 0, "winner drive" if outcome == 0 else "no winner")]), {"hash": "h"}
        return mock.patch.object(qa, "gate_checks", checks)

    def test_a_deliver_stopped_during_the_gate_leaves_a_page_that_is_not_ready(self):
        with self.gate(KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt):
            deliver.main()
        page = (self.out / "review.html").read_text()
        self.assertIn("Not ready to post.", page)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["caption.md", "review.html"])

    def test_a_green_gate_takes_the_banner_off_and_a_red_one_names_what_failed(self):
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        self.assertIn("Not ready to post.", self.during)
        self.assertNotIn("class='banner'", (self.out / "review.html").read_text())
        with self.gate(1):
            self.assertEqual(deliver.main(), 1)
        self.assertIn("vote: no winner", (self.out / "review.html").read_text())

    def test_the_gate_runs_in_delivers_process_under_its_lock(self):
        with self.gate(0), mock.patch("subprocess.run", side_effect=AssertionError("a process outside the lock")):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(self.run.name, "deliver")
        self.assertIn("deliver", (self.dir / "build" / "render" / "render.lock").read_text())
        self.assertTrue((self.dir / "build" / "qa" / "gate.json").exists())


    def test_the_last_line_is_the_reels_path_from_the_workspace_root(self):
        import contextlib
        import io
        said = io.StringIO()
        with self.gate(0), contextlib.redirect_stdout(said):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(said.getvalue().splitlines()[-1], "out/film.mp4")

    def render(self):
        """film.py render of a twelve-month year, the studio standing in: every still a 1080x1920 frame."""
        from PIL import Image
        months = [{"id": f"m{n:02d}", "month": n, "peak": n == 7, "at": {"pull": [4 + 6 * n]}} for n in range(1, 13)]
        f = {"hash": "h", "frames": 30, "seconds": 1, "rests": {"reel": {"hook": 0, "closer": 29}}}
        (self.dir / "build" / "qa").mkdir()
        (self.dir / "build" / "qa" / "timed.json").write_text(json.dumps({"hash": "h", "pass": True}))

        def render(jobs, name, run=None):
            for j in jobs:
                out = Path(j["out"])
                out.parent.mkdir(parents=True, exist_ok=True)
                if out.suffix == ".png":
                    Image.new("RGB", (1080, 1920), (40, 60, 90)).save(out)
                else:
                    out.write_bytes(b"the silent film")
            return {"failed": 0}
        os.chdir(self.dir / "build")
        with mock.patch.object(film, "film", return_value=(f, {"bpm": 120, "year": {"months": months}})), \
                mock.patch.object(studio, "video", lambda b, out, n, **k: {"out": str(out)}), \
                mock.patch.object(studio, "still", lambda b, fr, out, **k: {"out": str(out)}), \
                mock.patch.object(studio, "render", render), \
                mock.patch.object(film, "mux", lambda run, silent, out, s: shutil.copyfile(silent, out)):
            film.cmd_render(None, None)

    def test_every_styles_page_text_contrasts_with_its_ground(self):
        for name in style.styles():
            with self.subTest(style=name):
                colors = style.colors_of(style.card(name), palette.swatches_of({}))
                bg, text = deliver.page_colors(colors)
                self.assertEqual(bg, colors["bg"])
                self.assertGreaterEqual(palette.contrast(palette.hex_rgb(text), palette.hex_rgb(bg)), 4.5, (name, text, bg))

    def test_the_delivered_pages_text_is_never_its_ground(self):
        colors = style.colors_of(style.card("kinetic-type"), palette.swatches_of({}))
        (self.dir / "build" / "board.json").write_text(json.dumps({"year": {"colors": colors}}))
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        bg, text = re.search(r"body\{[^}]*background:(#[0-9a-fA-F]{6});color:(#[0-9a-fA-F]{6})", (self.out / "review.html").read_text()).groups()
        self.assertEqual(bg.lower(), colors["bg"])
        self.assertNotEqual(text.lower(), bg.lower())
        self.assertGreaterEqual(palette.contrast(palette.hex_rgb(text), palette.hex_rgb(bg)), 4.5)

    def test_the_player_has_the_hooks_frame_as_its_poster_and_the_reels_frames_beside_it(self):
        from PIL import Image
        self.render()
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        page = (self.out / "review.html").read_text()
        poster = re.search(r'<video src="film.mp4" poster="([^"]+)"', page).group(1)
        strip = re.findall(r"<img src='([^']+)'", page.split("<div class='strip'>", 1)[1].split("</div>", 1)[0])
        # the poster is the hook's frame whole: its story card, the reel's frame at rest, 1080x1920
        self.assertEqual(poster, "stories/01-hook.png")
        with Image.open(self.out / poster) as im:
            self.assertEqual(im.size, (1080, 1920))
        self.assertEqual(strip, ["strip/01-hook.jpg", "strip/02-m01.jpg", "strip/03-m03.jpg", "strip/04-m05.jpg",
                                 "strip/05-m07.jpg", "strip/06-m10.jpg", "strip/07-m12.jpg", "strip/08-closer.jpg"])
        self.assertLess(page.index("<video"), page.index("<div class='strip'>"))
        self.assertEqual(qa.PLACEHOLDER.findall(page), [])
        for rel in strip:
            with Image.open(self.out / rel) as im:
                self.assertEqual(im.width * 16, im.height * 9, (rel, im.size))

    def test_a_failed_gate_ends_on_what_failed_and_names_no_film(self):
        import contextlib
        import io
        said = io.StringIO()
        with self.gate(1), contextlib.redirect_stdout(said), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        self.assertEqual(said.getvalue().splitlines()[-1], "the gate failed: vote")
        self.assertNotIn("film.mp4", said.getvalue())

    def test_out_holds_only_what_is_posted_and_the_page_opens_on_the_hook_card(self):
        sheet = self.dir / "build/storyboards/kinetic-type/sheet.png"
        sheet.parent.mkdir(parents=True)
        sheet.write_bytes(b"the working sheet")
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        self.assertFalse((self.out / "storyboards").exists())
        page = (self.out / "review.html").read_text()
        self.assertIn('poster="stories/01-hook.png"', page)
        self.assertNotIn("storyboards/", page)

    def test_the_brief_stays_in_build_and_out_holds_only_what_is_posted(self):
        (self.out / "brief.md").write_text("a brief from an older delivery")
        (self.dir / "build" / "vote.md").write_text("| board | professional |\n|---|---|\n| kinetic-type | 5 |\n| total | 5 |\n")
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["caption.md", "review.html"])
        self.assertEqual((self.dir / "build" / "brief.md").read_text(), "a brief")
        page = (self.out / "review.html").read_text()
        self.assertNotIn("brief.md", page)
        self.assertNotIn("The vote", page)
        self.assertNotIn("<td>total</td>", page)

    def scored(self, person):
        """One round of the cut: the motion designer all 5s, the person `person` (a whole score each, or a dict)."""
        scores = {"motion_designer": dict.fromkeys(vote.CRITERIA, 5), "person": dict.fromkeys(vote.CRITERIA, 4)}
        scores["person"].update(person)
        crit = self.dir / "build" / "critic"
        crit.mkdir(exist_ok=True)
        rounds = sorted(crit.glob("cut-*.json"))
        n = len(rounds) + 1
        (crit / f"cut-{n}.json").write_text(json.dumps({"round": n, "film": "x", "critics": {
            who: {"boards": {"film": {"scores": s}}} for who, s in scores.items()}}))

    def looks(self):
        order = list(style.TRIO)
        board = self.dir / "build" / "storyboards"
        for s in order:
            (board / s).mkdir(parents=True, exist_ok=True)
            (board / s / "sheet.png").write_bytes(s.encode())
        (board / "boards.json").write_text(json.dumps({"order": order}))
        return order

    def test_the_page_shows_the_other_two_looks_and_the_line_that_picks_one(self):
        order = self.looks()
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        page = (self.out / "review.html").read_text()
        block = page.split("<h2>The other two looks</h2>", 1)[1]
        shown = re.findall(r"<img src='(looks/[^']+)'", block)
        # the film is the second look; the page shows the first and the third, numbered as out/boards.png numbers them
        self.assertEqual(shown, [f"looks/1-{order[0]}.png", f"looks/3-{order[2]}.png"])
        for rel, s in zip(shown, (order[0], order[2])):
            self.assertEqual((self.out / rel).read_bytes(), s.encode())
            self.assertIn(style.sentence(s), block)
        self.assertIn("Prefer another look? Say 'make the first one'.", block)
        self.assertEqual(sorted(p.name for p in (self.out / "looks").iterdir()), [Path(r).name for r in shown])
        self.assertIn("<h2>How it was made</h2>", page)
        self.assertIn("You picked it.", page)

    def test_the_line_that_picks_another_look_names_the_second_one_when_the_film_is_the_first(self):
        order = self.looks()
        (self.dir / "build" / "winner.json").write_text(json.dumps({"board": order[0], "by": "panel", "why": ""}))
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        self.assertIn("Prefer another look? Say 'make the second one'.", (self.out / "review.html").read_text())

    def test_the_page_carries_no_score_no_rule_name_and_no_critic(self):
        self.looks()
        self.scored({"pacing": 3})
        with self.gate(0):
            self.assertEqual(deliver.main(), 0)
        page = (self.out / "review.html").read_text().lower()
        for word in ("critic", "score", "the bar", "swap test", "verdict", "round", "professional", "pacing", "transitions"):
            self.assertNotIn(word, re.sub(r"<style>.*?</style>", "", page, flags=re.S), word)

    def test_the_brief_carries_the_scores_against_the_bar_and_says_when_the_cut_is_under_it(self):
        build = self.dir / "build"
        os.chdir(build)
        self.scored({"pacing": 3})
        cuts = [_env.read_json(p) for p in vote.rounds()]
        lib, taste, win = {"year": 2026, "doors": {}}, {}, {"board": "kinetic-type", "by": "person"}
        text = BRIEF(lib, taste, win, {}, {}, {}, cuts)
        scores = text.split("## the scores", 1)[1]
        self.assertIn("The bar: a mean of 4.5 with no score under 4.", scores)
        self.assertIn("pacing 3", scores)
        self.assertIn("Under the bar", scores)
        self.assertIn("under 4 on pacing", scores)
        self.scored({})
        text = BRIEF(lib, taste, win, {}, {}, {}, [_env.read_json(p) for p in vote.rounds()])
        self.assertIn("At the bar.", text.split("## the scores", 1)[1])

    def test_the_gate_refuses_an_out_folder_that_holds_what_is_not_posted(self):
        build = self.dir / "build"
        os.chdir(build)
        (build / "brief.md").write_text("a brief")
        (self.out / "caption.md").write_text("a caption #a")
        (self.out / "storyboards").mkdir()
        with mock.patch.object(qa, "timed_checks", return_value=([], {})), \
                mock.patch.object(qa, "film_checks", return_value=([], {"boards": {"reel": "board.json"}}, None)), \
                mock.patch.object(qa, "OUT", self.out):
            res, _ = qa.gate_checks(None)
        row = next(r for r in res if r[0] == "deliver")
        self.assertFalse(row[1])
        self.assertIn("out/ holds what is not posted: ['storyboards']", row[2])


class StillBefore(unittest.TestCase):
    """The frozen check counts only the part of a still stretch before the board's stop: a closer that settles half a
    second before the stop and holds into the ending's still passes, a stall in the middle of the film fails."""

    def lines(self, *pairs):
        out = []
        for kind, v in pairs:
            out.append(f"[freezedetect @ 0x1] lavfi.freezedetect.freeze_{kind}: {v}")
        return out

    def test_a_closer_settling_just_before_the_stop_stands_still_only_until_the_stop(self):
        got = qa.still_before(self.lines(("start", 39.7)), 40.33)
        self.assertEqual(len(got), 1)
        self.assertLess(got[0][1] - got[0][0], 1.0)

    def test_a_stall_in_the_middle_and_one_long_before_the_stop_are_both_kept_whole(self):
        got = qa.still_before(self.lines(("start", 10.0), ("duration", 1.5), ("end", 11.5), ("start", 38.0)), 40.33)
        self.assertEqual([(a, round(b, 2)) for a, b in got], [(10.0, 11.5), (38.0, 40.33)])
        self.assertTrue(all(b - a >= 1.0 for a, b in got))

    def test_the_still_from_the_stop_on_is_the_ending(self):
        self.assertEqual(qa.still_before(self.lines(("start", 40.33)), 40.33), [])


if __name__ == "__main__":
    unittest.main()
