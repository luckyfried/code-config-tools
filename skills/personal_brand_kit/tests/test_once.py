"""A move the card marks `once` plays at most once a film and wins the story's peak, whatever other move that takes
the frame the card lists before it or the peak photograph's tags favor."""
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import storyboard  # noqa: E402


def run_of(n):
    """A run of `n` moments, the last the peak, every photograph upright with people in it."""
    photos = {f"m{i}": {"file": f"m{i}.jpg", "aspect": 1.25} for i in range(n)}
    story = [{"photo": f"m{i}", "line": f"moment {i} with them", "pillar": "work", "people": ["them"], "likes": i}
             for i in range(n)]
    return types.SimpleNamespace(d={"photos": photos}, story=story, hook="hello there", handle="@them",
                                 question="what would you build", signoff="them")


def card(camera):
    """A card whose one `once` move is listed after another move that takes the frame and fits the peak's people."""
    return {"axes": {"camera": camera},
            "moves": [{"id": "polaroid-drop", "fits": ["title"]},
                      {"id": "exploded-layers", "fits": ["photo", "people", "peak"]},
                      {"id": "picture-tunnel", "fits": ["photo", "peak"], "once": True},
                      {"id": "sticker-pop", "fits": ["photo", "words"]},
                      {"id": "rule-draw", "fits": ["words"]},
                      {"id": "page-drift", "fits": ["closer", "photo"]}],
            "transitions": [{"id": "cut", "fits": ["photo", "title", "words", "closer"]}]}


class Once(unittest.TestCase):
    def test_the_once_move_wins_the_peak_and_plays_once(self):
        for camera in ("slam", "slow"):
            beats = storyboard.story(run_of(6), card(camera), 120)
            peak = next(b for b in beats if b["peak"])
            moves = [b["move"] for b in beats]
            self.assertEqual(peak["move"], "picture-tunnel", (camera, moves))
            self.assertEqual(moves.count("picture-tunnel"), 1, (camera, moves))


if __name__ == "__main__":
    unittest.main()
