"""A move the card marks `once` plays at most once a film and wins the story's peak, the last person: before it the
move is held for it, on it the move is the beat's whatever the look's lead or only moves prefer, after it it is gone.
The bed lifts into that same beat: music.py hands music_engine its landing and end in seconds at the bed's tempo.

    python3 -I -m unittest discover -s S/tests -p test_once.py
"""
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "tests"))
import boards  # noqa: E402
import music  # noqa: E402
import style  # noqa: E402
from test_landing import laid  # noqa: E402

MOVES = [{"id": "doodle-draw-on", "fits": ["photo", "words", "place"]}, {"id": "sticker-pop", "fits": ["photo", "people"]},
         {"id": "exploded-layers", "fits": ["photo", "peak"], "once": True}]


class Once(unittest.TestCase):
    def test_pick_holds_a_once_move_for_the_peak_and_plays_it_there_once(self):
        used = {}
        before = [style.pick(MOVES, {"photo", "peak"} - {"peak"} | {"people"}, "photo", used, None, {"exploded-layers"})
                  for _ in range(3)]
        self.assertNotIn("exploded-layers", before, "a once move held for the peak plays before it")
        self.assertEqual(style.pick(MOVES, {"photo", "people", "words", "peak"}, "photo", used, None), "exploded-layers")
        after = [style.pick(MOVES, {"photo", "peak"}, "photo", used, None) for _ in range(3)]
        self.assertNotIn("exploded-layers", after, "a once move plays a second time")

    def test_each_look_puts_its_once_move_on_the_last_person_and_nowhere_else(self):
        for look in ("scrapbook", "kinetic-type", "analog-home-movie"):
            with self.subTest(look=look):
                once = {m["id"] for m in style.card(look)["moves"] if m.get("once")}
                self.assertTrue(once, f"{look}'s card marks no move once")
                board = laid(look, 5, False)[0]
                persons = [b for b in board["beats"] if b["comp"] == "person"]
                self.assertIn(persons[-1]["move"], once, f"{look}'s peak plays {persons[-1]['move']}")
                self.assertEqual([b["id"] for b in board["beats"] if b["move"] in once], [persons[-1]["id"]])

    def test_the_bed_lifts_into_the_last_persons_beat(self):
        board = laid("scrapbook", 5, False)[0]
        start = 0
        for b in board["beats"]:
            if b["id"] == [x for x in board["beats"] if x["comp"] == "person"][-1]["id"]:
                break
            start += b["frames"]
        land, end = music.peak(board, board["bpm"])
        self.assertAlmostEqual(land, start / boards.FPS, places=6)
        self.assertAlmostEqual(end, (start + b["frames"]) / boards.FPS, places=6)
        half, _ = music.peak(board, board["bpm"] / 2)
        self.assertAlmostEqual(half, land, places=6, msg="a bed at half the board's tempo counts its beats in pairs")
        self.assertIsNone(music.peak({"bpm": 120, "beats": [{"comp": "hook", "frames": 60}]}, 120))


if __name__ == "__main__":
    unittest.main()
