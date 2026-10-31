"""The bar and the pick. The bar: the mean of every score 4.5 or more and no score under 4. Round 1 under it names the
one fix; round 2 under it is the spent budget, so film.py render makes the cut as it stands. The pick: the person picks
the look; with taste.json `ask` false the agent picks and must say why in one line; picking another look after a cut
starts the film again from the pick (its music, its cut and its rounds)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import vote  # noqa: E402


def round_(n, low=4, rest=5):
    s = dict.fromkeys(vote.CRITERIA, rest)
    s["picture"] = low
    film = {"scores": s, "paragraph": " ".join(["the film holds"] * 10)}
    return {"round": n, "film": f"cut{n}", "critics": {c: {"boards": {"film": film}} for c in vote.CUT_PANEL}}


class Here(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.here = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.here)
        self.tmp.cleanup()


class TheVerdict(Here):
    def verdict(self, *rounds):
        for r in rounds:
            _env.write_json(f"critic/cut-{r['round']}.json", r)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = vote.cmd_verdict(None)
        return rc, (_env.read_json("critic/verdict.json") or {}).get("verdict"), out.getvalue()

    def test_a_mean_at_the_bar_with_every_score_four_or_more_ships(self):
        # five 5s and a 4 for each critic: mean 4.83, lowest 4
        rc, v, _ = self.verdict(round_(1, low=4))
        self.assertEqual((rc, v), (0, "ship"))

    def test_every_score_four_is_under_the_bar(self):
        rc, v, said = self.verdict(round_(1, low=4, rest=4))
        self.assertEqual((rc, v), (2, "fix"))
        self.assertIn("mean 4.00", said)

    def test_one_score_under_four_is_under_the_bar_whatever_the_mean(self):
        rc, v, said = self.verdict(round_(1, low=3))
        self.assertEqual((rc, v), (2, "fix"))
        self.assertIn("picture", said)

    def test_round_two_under_the_bar_renders_as_spent(self):
        rc, v, said = self.verdict(round_(1, low=3), round_(2, low=3))
        self.assertEqual((rc, v), (0, "spent"))
        self.assertIn("film.py render", said)
        self.assertEqual(_env.read_json("critic/verdict.json")["lowest"], 3)


class ThePick(Here):
    def setUp(self):
        super().setUp()
        for letter, style in zip("abc", ("kinetic-type", "editorial-quiet", "swiss-grid")):
            d = Path("storyboards", letter)
            d.mkdir(parents=True)
            (d / "sheet.png").write_bytes(b"")
            (d / "plan.json").write_text(json.dumps({"reel": {"seconds": 20, "cuts": [1], "rests": {}}}))
            (d / "board-reel.json").write_text(json.dumps({"name": style, "style": style, "beats": []}))

    def pick(self, letter, why=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            return vote.cmd_pick(Namespace(letter=letter, why=why)), out.getvalue()

    def test_the_person_picks_without_a_reason(self):
        Path("taste.json").write_text(json.dumps({"ask": True}))
        self.pick("b")
        self.assertEqual(_env.read_json("winner.json")["board"], "b")
        self.assertEqual(_env.read_json("winner.json")["by"], "person")

    def test_the_agent_picks_by_taste_only_with_a_reason(self):
        Path("taste.json").write_text(json.dumps({"ask": False}))
        with self.assertRaises(SystemExit):
            self.pick("c")
        self.assertFalse(Path("winner.json").exists())
        self.pick("c", why="their captions are short and plain")
        self.assertEqual(_env.read_json("winner.json")["why"], "their captions are short and plain")

    def test_another_look_starts_the_film_again_from_the_pick(self):
        Path("taste.json").write_text(json.dumps({"ask": True}))
        self.pick("a")
        _env.write_json("music.json", {"recipe": "kinetic", "file": "music/bed.wav"})
        Path("music").mkdir()
        for f in ("cut.mp4", "cut.json", "film.json"):
            Path(f).write_text("{}")
        _env.write_json("critic/cut-1.json", round_(1))
        self.pick("b")
        for gone in ("music.json", "music", "cut.mp4", "cut.json", "film.json", "critic"):
            self.assertFalse(Path(gone).exists(), gone)
        self.assertEqual(_env.read_json("winner.json")["board"], "b")


if __name__ == "__main__":
    unittest.main()
