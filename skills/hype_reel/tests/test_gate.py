"""The critics gate the film: a board any critic fails on the swap test cannot win, and the film does not render
until a round on the current cut reads it as not monotonous. The still check reads a picture that has locked, through
grain.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import film  # noqa: E402
import qa  # noqa: E402
import vote  # noqa: E402

WHY = "the read of this board written in at least eight words"


def scores(swap, ids=("1", "2")):
    return {"critics": {c: {"boards": {i: {"scores": {k: 5 if i == "1" else 4 for k in vote.CRITERIA},
                                           "paragraph": " ".join(["word"] * 30), "swap": {"pass": swap[i], "why": WHY}}
                                       for i in ids}} for c in vote.PANEL}}


class Folder(unittest.TestCase):
    def setUp(self):
        self.here = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        for i in ("1", "2"):
            vote._env.write_json(f"storyboards/{i}/storyboard.json", {"id": i, "name": f"board {i}", "beats": []})

    def tearDown(self):
        os.chdir(self.here)
        self.dir.cleanup()

    def tally(self, swap):
        vote._env.write_json("vote/scores.json", scores(swap))
        with contextlib.redirect_stdout(io.StringIO()):
            return vote.cmd_tally(None)


class Swap(Folder):
    def test_the_highest_board_that_fails_the_swap_test_loses(self):
        self.assertEqual(self.tally({"1": False, "2": True}), 0)
        self.assertEqual(vote._env.read_json("winner.json")["board"], "2")

    def test_every_board_failing_the_swap_test_names_no_winner(self):
        self.assertEqual(self.tally({"1": False, "2": False}), 1)
        self.assertFalse(Path("winner.json").exists())

    def test_a_swap_read_without_a_why_is_not_filled_in(self):
        data = scores({"1": True, "2": True})
        data["critics"]["editor"]["boards"]["1"]["swap"]["why"] = "fine"
        self.assertTrue(any("swap" in x for x in vote.problems(data, vote.PANEL, ["1", "2"])))


class Reads(Folder):
    def cut(self, failed=None, film_hash=None, unread=False, score=5):
        Path("film.json").write_text(json.dumps({"timeline": [], "seconds": 20}))
        film.SILENT.write_bytes(b"cut")
        h = film.film_hash()
        vote._env.write_json("cut.json", {"film": h})
        data = vote.blank(vote.CUT_PANEL, ["film"], swap=False)
        for c in vote.CUT_PANEL:
            e = data["critics"][c]["boards"]["film"]
            e["scores"] = {k: score for k in vote.CRITERIA}
            e["paragraph"] = " ".join(["word"] * 30)
        reads = {k: {"pass": None if unread else True, "why": "" if unread else WHY} for k in vote.READS}
        if failed:
            reads[failed] = {"pass": False, "why": "every beat rises from the bottom the same way"}
        data.update({"round": 1, "film": film_hash or h, "reads": reads})
        vote._env.write_json("critic/cut-1.json", data)

    def test_a_monotonous_cut_does_not_render(self):
        self.cut("monotony")
        self.assertIn("fails monotony", film.ready())

    def test_a_field_behind_the_type_does_not_render(self):
        self.cut("frame")
        self.assertIn("fails frame", film.ready())

    def test_a_round_on_another_film_does_not_render(self):
        self.cut(film_hash="0" * 16)
        self.assertIn("not watched this cut", film.ready())

    def test_a_round_left_unread_does_not_render(self):
        self.cut(unread=True)
        self.assertIn("not filled in", film.ready())

    def test_a_cut_that_passes_every_read_renders(self):
        self.cut()
        self.assertIsNone(film.ready())

    def test_a_cut_under_the_bar_with_its_fix_unspent_does_not_render(self):
        self.cut(score=4)
        self.assertIn("under the bar", film.ready())


class Still(unittest.TestCase):
    """Four seconds of a picture: grain over a held frame reads as still in the figure, a slow drift does not."""
    def clip(self, src):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        out = Path(d.name) / "clip.mp4"
        r = __import__("subprocess").run([qa._env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", src, "-t", "4", "-r", "30",
                                          "-pix_fmt", "yuv420p", str(out)])
        self.assertEqual(r.returncode, 0)
        return str(out)

    def test_grain_over_a_held_frame_reads_still(self):
        # grain at this strength moves every frame by about 4 levels of luma; the held picture under it has not moved
        qa.still_figure(self.clip("color=c=0x8899AA:s=1080x1920:d=4,noise=alls=2:allf=t"), subprocess.run)
        per = qa.MEASURES["still"]["per_second"]
        self.assertTrue(per and all(x < qa.STILL for x in per), per)

    def test_a_slow_drift_does_not_read_still(self):
        qa.still_figure(self.clip("testsrc2=s=1080x1920:d=4,scroll=h=0.002"), subprocess.run)
        self.assertEqual(qa.MEASURES["still"]["seconds_under_half"], [])


class FrameZero(unittest.TestCase):
    """Frame 0 is the film's cover in the feed: a black frame fails, a picture between the letterbox bars passes."""

    def photo(self, size):
        from PIL import Image
        return Image.effect_noise(size, 40)

    def test_a_black_frame_fails(self):
        from PIL import Image
        self.assertLess(qa.spread(Image.new("L", (270, 480), 0), 0), qa.FLAT)

    def test_a_picture_between_black_bars_passes(self):
        from PIL import Image
        im = Image.new("L", (270, 480), 0)
        im.paste(self.photo((270, 336)), (0, 72))
        self.assertGreaterEqual(qa.spread(im, 0.15), qa.FLAT)


class Placeholder(unittest.TestCase):
    def test_the_word_none_in_a_caption_is_not_a_placeholder(self):
        self.assertIsNone(qa.PLACEHOLDER.search("which one is your morning cup? none of them."))

    def test_a_python_none_is(self):
        self.assertIsNotNone(qa.PLACEHOLDER.search("made by None"))


class Register(unittest.TestCase):
    """The captions keep the person's hashtag habit: a person who never tags gets none, one who tags gets one to ten."""
    def sec(self, tag):
        return {"film": f"would you eat out of this? Miradouro, dec 5{tag}", "feed post": f"two plates. Miradouro{tag}"}

    def test_a_person_without_hashtags_passes_with_none(self):
        self.assertTrue(qa.in_register(self.sec(""), "Miradouro", {"lowercase": True, "hashtags": []})[0])

    def test_a_person_without_hashtags_fails_with_some(self):
        self.assertFalse(qa.in_register(self.sec(" #miradouro"), "Miradouro", {"lowercase": True, "hashtags": []})[0])

    def test_a_person_with_hashtags_fails_with_none(self):
        self.assertFalse(qa.in_register(self.sec(""), "Miradouro", {"lowercase": True, "hashtags": ["#ceramics"]})[0])


if __name__ == "__main__":
    unittest.main()
