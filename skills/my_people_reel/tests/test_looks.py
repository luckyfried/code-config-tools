"""A run draws three looks and the person picks one. With no style named the three are the scrapbook, the analog home
movie and kinetic type; a named style comes first with the two of those that share the fewest axes with it. The pick
takes a letter, an ordinal, a look's name or its style id; when taste.json says the person is not asked, a pick names
why in one line, and a pick that changes the look takes away the music, the cut and the critics' rounds made for the
look before. out/boards.png holds the three reel sheets one over another under each look's letter and name. Each look
lays out five and twelve people in every format with no problem, and nothing the kit writes or says calls the person
"her" or "she".

    python3 -I -m unittest discover -s S/tests -p test_looks.py
"""
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "tests"))
import _env  # noqa: E402
import board_drive  # noqa: E402
import boards  # noqa: E402
import storyboard  # noqa: E402
import style as S  # noqa: E402
import vote  # noqa: E402
from test_many_people import SWATCHES, run_folder  # noqa: E402

TRIO = ("scrapbook", "analog-home-movie", "kinetic-type")


class InRun(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)


class Trio(unittest.TestCase):
    def test_no_named_style_draws_the_scrapbook_the_home_movie_and_kinetic_type(self):
        self.assertEqual(S.trio_for(None), TRIO)

    def test_a_named_style_comes_first_with_the_two_that_differ_most_from_it(self):
        for named in S.styles():
            with self.subTest(style=named):
                trio = S.trio_for(named)
                self.assertEqual(trio[0], named)
                self.assertEqual(len(set(trio)), 3)
                rest = [t for t in TRIO if t != named]
                least = sorted(len(S.shared_axes(named, t)) for t in rest)[:2]
                self.assertEqual(sorted(len(S.shared_axes(named, t)) for t in trio[1:]), least)

    def test_the_three_looks_of_the_trio_share_no_face_and_no_closer(self):
        faces = [{S.card(t)["faces"][k]["file"] for k in ("display", "text")} for t in TRIO]
        self.assertEqual([a & b for i, a in enumerate(faces) for b in faces[i + 1:]], [set(), set(), set()])
        self.assertEqual(len({S.card(t)["closer"] for t in TRIO}), 3)


class Pick(InRun):
    def setUp(self):
        super().setUp()
        for t in TRIO:
            _env.write_json(storyboard.sb_path(t), {"style": t, "name": f"the {t} board"})
        _env.write_json(storyboard.LOOKS, {"looks": list(TRIO)})

    def pick(self, look, why=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return vote.cmd_pick(types.SimpleNamespace(look=look, why=why))

    def test_a_letter_an_ordinal_a_name_or_a_style_id_picks_the_look(self):
        for said, t in (("A", TRIO[0]), ("second", TRIO[1]), ("Kinetic type", TRIO[2]), ("analog-home-movie", TRIO[1]),
                        ("c", TRIO[2])):
            with self.subTest(said=said):
                self.assertEqual(self.pick(said), 0)
                win = _env.read_json("winner.json")
                self.assertEqual(win["board"], t)
                self.assertEqual(win["look"], S.card(t)["name"])
                self.assertEqual(win["by"], "the person")

    def test_words_that_name_no_look_are_refused_naming_the_three(self):
        with self.assertRaises(SystemExit) as refused:
            self.pick("the fourth one")
        for t in TRIO:
            self.assertIn(t, str(refused.exception))
        self.assertFalse(Path("winner.json").exists())

    def test_a_person_not_asked_gets_a_pick_that_says_why(self):
        _env.write_json("taste.json", {"ask": False})
        with self.assertRaises(SystemExit) as refused:
            self.pick("B")
        self.assertIn("--why", str(refused.exception))
        self.assertEqual(self.pick("B", "their feed is warm film grain and family rooms"), 0)
        win = _env.read_json("winner.json")
        self.assertEqual((win["board"], win["by"]), (TRIO[1], "taste"))
        self.assertEqual(win["why"], "their feed is warm film grain and family rooms")

    def test_a_pick_that_changes_the_look_takes_the_music_the_cut_and_its_rounds_away(self):
        self.pick("A")
        for f in ("music.json", "film.json", "critic/cut-1.json"):
            _env.write_json(f, {"made for": "A"})
        self.pick("first")
        self.assertTrue(all(Path(f).exists() for f in ("music.json", "film.json", "critic/cut-1.json")))
        self.pick("third")
        self.assertEqual([f for f in ("music.json", "film.json", "critic/cut-1.json") if Path(f).exists()], [])


class BoardsPng(InRun):
    def test_the_three_reel_sheets_stand_one_over_another_under_their_letters(self):
        sizes = [(600, 300), (640, 320), (600, 280)]
        for t, (w, h), c in zip(TRIO, sizes, ("#aa5533", "#335577", "#ddcc22")):
            storyboard.sb_path(t).parent.mkdir(parents=True)
            Image.new("RGB", (w, h), c).save(storyboard.sb_path(t).parent / "sheet.png")
        out = storyboard.boards_png(TRIO)
        self.assertEqual(out, Path("out/boards.png"))
        im = Image.open(out).convert("RGB")
        self.assertEqual(im.size, (640, sum(h for _, h in sizes) + 3 * 120))
        # each sheet sits under its own heading, in order
        y = 0
        for (w, h), c in zip(sizes, ((0xaa, 0x55, 0x33), (0x33, 0x55, 0x77), (0xdd, 0xcc, 0x22))):
            y += 120
            self.assertEqual(im.getpixel((w // 2, y + h // 2)), c)
            y += h


class EveryLookLaysOut(unittest.TestCase):
    def test_each_look_lays_out_five_and_twelve_people_in_every_format_with_no_problem(self):
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        for n in (5, 12):
            with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
                os.chdir(d)
                run_folder(d, n)
                ctx = boards.Ctx()
                for t in TRIO:
                    board_drive.use(t, swatches=SWATCHES)
                    sb = boards.draft(t, ctx)
                    self.assertEqual(len(sb["people"]), n)
                    for kind in ("reel", "square", "wide"):
                        with self.subTest(people=n, look=t, format=kind):
                            self.assertEqual(board_drive.problems(boards.layout(sb, ctx, kind)), [])
                os.chdir(here)

    def test_the_picture_and_the_music_stop_together_as_each_looks_closer_settles(self):
        """The stop lands on the beat each look's closer stands still: letter-build once its last letter has landed,
        the cover once its handle is in, never a beat of stillness before the music stops; the home movie's flicker
        never stands still and plays its whole two beats."""
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            run_folder(d, 5)
            ctx = boards.Ctx()
            want = {"scrapbook": 1.6, "analog-home-movie": board_drive.SHAPE, "kinetic-type": 8 / 9 + 1 / 3}
            for t in TRIO:
                board_drive.use(t, swatches=SWATCHES)
                board = boards.layout(boards.draft(t, ctx), ctx, "reel")
                closer = board["beats"][-1]
                shape = next(x for x in closer["layers"] if x["kind"] == "Shape")
                start = sum(b["frames"] for b in board["beats"][:-1]) / boards.FPS * board["bpm"] / 60
                stop = next(c["at"] for c in board["sound"] if c["kind"] == "stop")
                with self.subTest(look=t, closer=shape["name"]):
                    self.assertAlmostEqual(stop - start - shape["at"], want[t], delta=0.05)
            os.chdir(here)


class Words(unittest.TestCase):
    def test_nothing_the_kit_writes_or_says_calls_the_person_her_or_she(self):
        files = [*KIT.glob("scripts/*.py"), KIT / "SKILL.md", *KIT.glob("pipeline/*.md"), *KIT.glob("critic/*.md"),
                 *KIT.glob("evals/*.md")]
        found = [f"{f.relative_to(KIT)}:{i}" for f in files for i, line in enumerate(f.read_text().splitlines(), 1)
                 if re.search(r"\b(her|hers|herself|she)\b", line, re.I)]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
