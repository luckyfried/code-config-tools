"""A move the card marks `once` plays at most once a film and wins the story's peak, on a grammar card (one whose
spectacle moves are its everyday moves) as on any other."""
import sys
import unittest
from pathlib import Path

S = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S / "scripts"))
import compose  # noqa: E402
import wall  # noqa: E402


def year(n, peak):
    """`n` photograph cards between the hook and the closer, every photograph upright, card `peak` the year's peak and
    each card's line about it."""
    beats = [{"id": "hook", "form": "hook", "post": "p0"}]
    beats += [{"id": f"card-{i}", "form": "moment", "post": f"p{i}", "words": "a line", "peak": i == peak, "hold": 2}
              for i in range(1, n + 1)]
    beats.append({"id": "closer", "form": "closer"})
    photos = {f"p{i}": {"aspect": 1.25} for i in range(n + 1)}
    return beats, photos, {f"p{i}": {"people": ["them"]} for i in range(n + 1)}


class Once(unittest.TestCase):
    def test_on_every_card_the_once_move_plays_on_the_peak_alone(self):
        for style in sorted(wall.GRAMMAR | {"scrapbook"}):
            c = compose.card(style)
            marked = [o["id"] for o in c["moves"] if o.get("once") and "photo" in o["fits"]]
            if not marked:
                continue
            for peak in (2, 6):
                beats, photos, moments = year(8, peak)
                wall.choose(c, beats, photos, moments, "me")
                moves = [b["move"] for b in beats]
                with self.subTest(style=style, peak=peak):
                    self.assertEqual(beats[peak]["move"], marked[0], moves)
                    self.assertEqual(moves.count(marked[0]), 1, moves)


if __name__ == "__main__":
    unittest.main()
