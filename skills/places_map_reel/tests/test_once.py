"""A move the style card marks `once` plays at most once a film and wins the story's peak: the pick never takes a played
`once` move again and, on the peak, picks from the unplayed `once` moves that fit it.

    python3 -I -m unittest discover -s S/tests -p test_once.py
"""
import json
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import look  # noqa: E402
import storyboard  # noqa: E402

DATA = KIT / "tests" / "data"


class Once(unittest.TestCase):
    def test_the_pick_plays_a_once_move_once_and_gives_it_the_peak(self):
        opts = [{"id": "slam", "fits": ["photo", "peak", "words"]}, {"id": "drift", "fits": ["photo"]},
                {"id": "burst", "fits": ["photo", "peak"], "once": True}]
        used, peak = {}, {"photo", "peak", "words"}
        self.assertEqual(look.pick(opts, peak, "photo", used, None), "burst")
        self.assertEqual(look.pick(opts, peak, "photo", used, None), "slam")
        self.assertEqual(look.pick(opts, {"photo"}, "photo", used, "slam"), "drift")

    def test_a_once_move_plays_at_most_once_in_every_look(self):
        for name in ("trip.json", "video-of-my-year.json", "travel-nurse.json"):
            src = json.loads((DATA / name).read_text())
            for st in look.TRIO:
                card = json.loads((KIT / "styles" / f"{st}.json").read_text())
                once = {o["id"] for o in card["moves"] if o.get("once")}
                moves = [b.get("move") for b in storyboard.plan(src, "reel", None, st)["board"]["beats"]]
                for m in once:
                    self.assertLessEqual(moves.count(m), 1, (name, st, m))


if __name__ == "__main__":
    unittest.main()
