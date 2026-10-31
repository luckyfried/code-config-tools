"""The closer is never a still frame: from the stop on the film holds its picture at the stop's instant, and the shared
MoveLayer keeps the closer's slow push to the last frame when the film hands it its own time (`now`), the board's
time in the music's beats, the units of `t`, never held at the stop.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import re
import unittest
from pathlib import Path

FILM = Path(__file__).resolve().parents[1] / "motion/studio/drive/DriveFilm.tsx"


class CloserPush(unittest.TestCase):
    def test_the_film_hands_the_move_layer_its_time_past_the_stop(self):
        calls = re.findall(r"<MoveLayer\b[^>]*?/>", FILM.read_text(), re.S)
        self.assertEqual(len(calls), 1, calls)
        self.assertIn("now={musicAt(plan, t)}", calls[0])
