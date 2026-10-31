"""The film's craft as the board lays it and the plan and the verdict hold it: the hook's title states the glow-up from
the film's first frame; a held post's page closes round its photograph before its words and opens once they go; the closer's header carries their handle and their
bio, and the ask signs it off; a post's move comes from its photograph (the held posts close, a wide photograph slides
in, a tall one drops); every post carries the focus point its layered move pushes toward; the film carries its style
card's finish, easing and photo layout; the clip requests are the hook's world, a
still brought to life on each held post and a texture on each passed one, each its own shot; plan.py check refuses a
plan whose shots or film words are missing; and the gate's critic row stays red on FIX ONCE until the run has made its
fix, then delivers the best cut.

    python3 -I -m unittest discover -s tests -p test_craft.py
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_storyboard import BIO, held, people  # noqa: E402
from test_resume import BOARD, Run  # noqa: E402
import drive  # noqa: E402
import compose  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

FILM = {"hook": "the grid, glowed up", "ask": "come see the new nine",
        "world": "a bakery street at first light, 35 mm at eye level, low sun on the shutters"}
BEAT_SECONDS = 0.5


def shot(n, held):
    return (f"loaf {n} cooling on the bench, 50 mm at eye level, soft window light" if held
            else f"close on the crust of loaf {n}, {(100, 60, 35)[n % 3]} mm from above, raking window light")


def built(fmt="reel", style=None):
    before, nine, plan, breaks = people()
    plan["film"] = FILM
    held = drive.held_posts(len(nine))
    for i, p in enumerate(nine):
        p["shot"] = shot(p["n"], i in held)
        p["focal"] = [0.3, 0.4]
        # every third photograph is wide, so the passed posts carry both of the moves a photograph can ask for
        p["size"] = [1600, 1200] if i % 3 == 1 else [1200, 1600]
    return drive.build(fmt, before, nine, plan, None, breaks, None, None, "maren.okafor", BIO, style=style)


class Board(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = built()

    def words(self, name):
        return self.board["beats"][0]["layers"][1]["words"][name]

    def test_the_hook_states_the_glow_up_from_the_first_frame(self):
        first = self.board["timeline"]["beats"][0]
        self.assertEqual((self.board["look"]["title"], first["words"], first["at"]), (FILM["hook"], FILM["hook"], 0.0))
        # the film opens on their grid, and the title is a page of the card that closes round it, its words entering in
        # the card's display face once the paper is in
        self.assertIsNone(first["move"])
        pg = self.board["page"]
        self.assertEqual(drive.page_words(pg).lower(), FILM["hook"])
        self.assertEqual(pg["close"], [drive.OPENING, drive.OPENING + drive.OPEN_OUT])
        self.assertLess(pg["close"][1], pg["lines"][0]["at"])
        self.assertLess(pg["lines"][0]["at"], 1.0)
        self.assertEqual(storyboard.hook_frame(self.board), 0)

    def test_the_closer_header_carries_the_handle_and_the_bio_and_the_ask_signs_it_off(self):
        lines = self.board["header"]["lines"]
        self.assertEqual((lines[0]["name"], lines[0]["text"]), ("handle", "@maren.okafor"))
        self.assertEqual(" ".join(ln["text"] for ln in lines if ln["name"].startswith("bio-")), BIO)
        self.assertEqual(self.board["look"]["signoff"], FILM["ask"])

    def test_a_page_closes_round_its_photograph_before_its_words_and_opens_once_they_have_gone(self):
        for b in held(self.board):
            pg = b["layers"][0]["page"]
            with self.subTest(page=b["id"]):
                self.assertLessEqual(pg["close"][1], pg["lines"][0]["at"])
                self.assertLess(drive.page_landed(pg), pg["sink"])
                self.assertLessEqual(pg["sink"], pg["open"][0])

    def posts(self):
        return [ly for b in self.board["beats"] for ly in b["layers"] if ly["kind"] == "Post"]

    def test_the_gate_reads_each_held_card_while_its_words_stand(self):
        import qa
        posts = held(self.board)
        for b in posts:
            pg, times = b["layers"][0]["page"], b["layers"][0]["times"]
            reads = qa.hold_reads(times, pg)
            self.assertEqual(len(reads), 3, b["id"])
            self.assertGreaterEqual(reads[0], drive.page_landed(pg) - 1e-6, b["id"])
            self.assertLess(reads[-1], pg["sink"], b["id"])
        self.assertTrue(posts)

    def test_each_posts_move_comes_from_its_photograph_and_the_held_posts_close(self):
        moves = [p["move"] for p in self.posts()]
        held = drive.held_posts(len(moves))
        want = ["close" if i in held else "slide" if i % 3 == 1 else "drop" for i in range(len(moves))]
        self.assertEqual(moves, want)
        self.assertEqual(len(set(moves)), 3)

    def test_a_post_that_slides_or_falls_meets_the_frame_waiting_on_the_first_cell(self):
        G = drive.geometry("reel")
        slot0 = drive.cell(G, 0)
        keys = self.board["beats"][0]["layers"][1]["keys"]
        for p in self.posts():
            if p["move"] == "close":
                continue
            during = [k for k in keys if p["times"]["fly"][0] - 0.01 <= k["t"] <= p["times"]["seat"]]
            with self.subTest(post=p["n"], move=p["move"]):
                self.assertTrue(during)
                for k in during:
                    # never an empty frame sweeping the wall: it stays on the first cell, opening a little toward the card
                    self.assertLess(abs(k["box"][0] + k["box"][2] / 2 - slot0[0] - slot0[2] / 2), 1)
                    self.assertLess(k["box"][2], slot0[2] * 1.1)
                self.assertEqual(p["times"]["reflow"][0] if p["move"] == "slide" else p["times"]["fly"][0],
                                 p["times"]["fly"][0])

    def test_a_falling_post_sets_off_above_the_cameras_view(self):
        cam = self.board["beats"][0]["layers"][2]["keys"]
        W, H = self.board["format"]["width"], self.board["format"]["height"]
        for p in self.posts():
            if p["move"] != "drop":
                continue
            k = max((c for c in cam if c["t"] <= p["times"]["seat"]), key=lambda c: c["t"])
            _, sy, _ = drive.project(k, W, H, p["from"][0], p["from"][1] + p["slot"][3] / 2, 3)
            with self.subTest(post=p["n"]):
                self.assertLess(sy, 0)

    def test_the_closer_card_runs_to_the_pictures_bottom_edge_and_fills_most_of_its_width(self):
        for fmt in ("reel", "square", "landscape"):
            board = built(fmt)
            W, H = board["format"]["width"], board["format"]["height"]
            G = drive.geometry(fmt)
            x, y, w, h = drive.first_screen(G)
            stop = board["beats"][-1]["layers"][0]["still"]
            k = max((c for c in board["beats"][0]["layers"][2]["keys"] if c["t"] <= stop), key=lambda c: c["t"])
            ft = drive.FT * w / drive.BAND_W
            x0, bottom, _ = drive.project(k, W, H, x - ft, y + h + ft, drive.WALL_Z + 8)
            x1, _, _ = drive.project(k, W, H, x + w + ft, y + h + ft, drive.WALL_Z + 8)
            with self.subTest(fmt=fmt):
                # no wall shows under the card
                self.assertGreaterEqual(bottom, H - 1)
                if fmt == "reel":
                    self.assertGreater((x1 - x0) / W, 0.7)

    def test_the_bio_is_as_they_wrote_it_emoji_and_line_breaks_kept(self):
        bio = "eating my way around on 35mm \U0001F35E\U0001F39E\ufe0f lisbon / wherever the bread is"
        for size, width in ((40, 900), (58, 900)):
            lines = drive.bio_lines(bio, size, width, 3)
            with self.subTest(size=size, width=width):
                self.assertEqual(" ".join(lines), bio)
                self.assertTrue(all(ln.split()[0] != "/" for ln in lines), lines)
        self.assertEqual(drive.bio_lines("bread on film\nlisbon \U0001F35E", 58, 900, 3), ["bread on film", "lisbon \U0001F35E"])
        # a bio that cannot fit is never cut into: its first line too long for the space gives no bio at all
        self.assertIsNone(drive.bio_lines("x" * 400, 58, 560, 3))

    def test_their_posts_stand_muted_beside_the_new_ones(self):
        cells = self.board["beats"][0]["layers"][0]["cells"]
        self.assertTrue({c["mute"] for c in cells if c["key"].startswith("before-")} == {drive.MUTE} and drive.MUTE > 0)
        self.assertFalse([c for c in cells if c["key"].startswith("post-") and c.get("mute")])

    def test_every_post_carries_its_focus_point_for_the_layered_move(self):
        self.assertEqual({tuple(p["uvFocal"]) for p in self.posts()}, {(0.3, 0.6)})

    def test_the_film_carries_its_style_cards_finish_easing_and_photo_layout(self):
        for style in compose.TRIO:
            board = built(style=style)
            card = compose.card(style)
            with self.subTest(style=style):
                self.assertEqual(board["system"]["style"], style)
                self.assertEqual([board["system"][k] for k in ("finish", "ease", "photo")], [card[k] for k in ("finish", "ease", "photo")])

    def test_the_clip_requests_are_the_world_stills_and_textures_each_its_own_shot(self):
        clips = self.board["clips"]
        held = drive.held_posts(9)
        self.assertEqual([c["role"] for c in clips], ["world"] + ["still" if i in held else "texture" for i in range(9)])
        self.assertEqual(clips[0]["beat"], "hook")
        self.assertTrue(clips[0]["prompt"].startswith(FILM["world"]))
        for i, c in enumerate(clips[1:]):
            self.assertTrue(c["prompt"].startswith(shot(i + 1, i in held)), c["prompt"])
        for c in clips:
            self.assertRegex(c["prompt"], r"; a slow (dolly forward|push in|truck (left|right)|tilt down); ")
            self.assertIn(f"{c['seconds']} s, a seamless loop", c["prompt"])
        self.assertEqual(len({c["prompt"] for c in clips}), len(clips))


class PlanShots(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def problems(self, film=None, shots=None):
        import plan
        Path("a.jpg").write_bytes(b"a photograph")
        shots = shots or [""] * 3
        caps = ["slow morning, one cup", "the loaf split down the middle", "flour everywhere, the dough resting",
                "the last tray out of the oven", "crumbs on the counter, door open"][:len(shots)]
        slots = [{"n": n, "date": f"2026-11-0{n}", "weekday": "Wednesday", "photo": "a.jpg", "caption": c,
                  "shot": shots[n - 1]} for n, c in enumerate(caps, 1)]
        return [x for x in plan.problems({"slots": slots, "film": film or {}}) if "shot" in x or x.startswith("film")]

    def test_a_plan_without_its_shots_and_film_words_is_refused(self):
        bad = self.problems()
        for what in ("post 1's shot", "post 2's shot", "post 3's shot", "film: the hook", "film: the ask", "film: the world"):
            self.assertTrue(any(x.startswith(what) for x in bad), (what, bad))

    def test_a_shot_that_pastes_the_caption_is_refused(self):
        bad = self.problems(FILM, ["slow morning, one cup, 50 mm at eye level, window light",
                                   "the bread on the bench, 50 mm at eye level, window light", shot(3, True)])
        self.assertTrue(any(x.startswith("post 1's shot pastes in the caption") for x in bad), bad)
        self.assertFalse(any(x.startswith("post 2's shot") for x in bad), bad)

    def test_two_passed_posts_in_a_row_on_one_lens_are_refused_and_on_their_own_lenses_hold(self):
        same = "close on the {} grain, 100 mm from above, raking window light"
        bad = self.problems(FILM, [shot(1, True), same.format("crust's"), same.format("flour's"), shot(4, True)])
        self.assertTrue(any(x.startswith("post 3's shot: the film passes this post right after post 2") for x in bad), bad)
        self.assertFalse(any(x.startswith("post 2's shot") for x in bad), bad)
        self.assertEqual(self.problems(FILM, [shot(1, True), shot(2, False), shot(3, False), shot(4, True)]), [])

    def test_a_shot_lit_by_daylight_or_sunlight_names_its_light(self):
        bad = self.problems(FILM, ["the cup and saucer on the table, 50 mm at eye level, soft daylight",
                                   "macro of the crumb, 100 mm from above, low sunlight", shot(3, True)])
        self.assertEqual([x for x in bad if "names no light" in x], [])

    def test_a_plan_with_every_shot_and_its_film_words_holds(self):
        self.assertEqual(self.problems(FILM, [shot(1, True), shot(2, False), shot(3, True)]), [])


class Verdict(Run):
    """The gate's critic row on a film under the bar: red while the one fix is still the run's to make, green on the
    round after it, when the render is delivered as the best cut."""

    def round(self, n, low):
        import qa
        Path("out").mkdir(exist_ok=True)
        Path("out/film.mp4").write_bytes(f"cut {n}".encode())
        para = " ".join(["the frame carries each post in under its own note and lands it"] * 3)
        scores = {k: 4 for k in vote.CRITERIA} | low
        critics = {c: {"boards": {"film": {"scores": scores, "paragraph": para}}} for c in vote.CUT_PANEL}
        self.write(f"critic/cut-{n}.json", {"round": n, "film": qa.sha(Path("out/film.mp4")), "critics": critics,
                                            "fixed": "the hook line now states the glow-up" if n > 1 else None})

    def row(self):
        import qa
        board = dict(BOARD, nine=[])
        with mock.patch.object(qa, "board_checks", lambda: ([], board)), \
                mock.patch.object(qa, "film_checks", lambda run=None: ([], board, None)):
            res, _ = qa.gate_checks()
        return next(r for r in res if r[0] == "critic")

    def test_fix_once_keeps_the_gate_red_and_the_round_after_it_delivers(self):
        rule = next(k for k in vote.CRITERIA if k in vote.LEVERS)
        self.round(1, {rule: 3})
        _, ok, detail = self.row()
        self.assertFalse(ok)
        self.assertIn("FIX ONCE", detail)
        self.round(2, {rule: 3})
        _, ok, detail = self.row()
        self.assertTrue(ok, detail)
        self.assertIn("DELIVER", detail)


if __name__ == "__main__":
    unittest.main()
