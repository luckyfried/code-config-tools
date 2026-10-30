"""The rest frames the sheets, the frames and the story card are drawn at: every card is at rest there, before the
camera's move off it starts, so its photograph is sharp and its words are whole.

USAGE (from anywhere):
    python3 -m unittest discover -s S/tests -p 'test_rest.py'
"""
import re
import sys
import unittest
from pathlib import Path

S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "scripts"))
import compose  # noqa: E402


def camera_go():
    """The camera's GO, read from the camera itself: beats before a card's end its move starts."""
    text = (S / "motion" / "studio" / "drive" / "camera.ts").read_text()
    return float(re.search(r"^const GO = ([0-9.]+);", text, re.M).group(1))


class Rest(unittest.TestCase):
    def test_a_cards_rest_frame_falls_before_the_cameras_move_off_it(self):
        beats = [{"id": "hook", "form": "hook", "pulses": 3}, {"id": "card-1", "form": "moment", "pulses": 4},
                 {"id": "card-2", "form": "moment", "pulses": 4},
                 {"id": "closer", "form": "closer", "pulses": 9, "stop": 5.0}]
        board = {"beats": beats, "rest": ["hook", "card-1", "card-2", "closer"]}
        st = {"style": "scrapbook", "bpm": 120}
        pulse = compose.FPS * 60 / st["bpm"]
        go = camera_go()
        ends = {"hook": 3, "card-1": 7, "card-2": 11}
        rest = dict(compose.rest_frames(st, board))
        for bid, end in ends.items():
            with self.subTest(bid):
                start = end - (2 * go if bid == "card-2" else go)
                self.assertLessEqual(rest[bid], start * pulse, "the rest frame falls inside the camera's move")
                self.assertGreaterEqual(rest[bid], (start - 0.5) * pulse, "the rest frame is long before the move")
        self.assertGreater(rest["closer"], 11 * pulse)


if __name__ == "__main__":
    unittest.main()
