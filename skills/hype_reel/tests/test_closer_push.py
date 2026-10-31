"""The closer is never a still frame: from the stop on the film holds its picture at the stop's instant, and the shared
MoveLayer keeps the closer's slow push to the last frame when the film hands it its own time (`now`), the film's time
in beats, never held at the stop.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import re
import unittest
from pathlib import Path

FILM = Path(__file__).resolve().parents[1] / "motion/studio/film/HypeFilm.tsx"


class CloserPush(unittest.TestCase):
    def test_the_film_hands_the_move_layer_its_time_past_the_stop(self):
        calls = re.findall(r"<MoveLayer\b[^>]*?/>", FILM.read_text(), re.S)
        self.assertEqual(len(calls), 1, calls)
        self.assertIn("now={timeAt(placed, frame)}", calls[0])


class Safe(unittest.TestCase):
    def test_the_look_hands_the_moves_the_formats_safe_area(self):
        """The shared moves lay their words out inside the look's safe area; the film's look carries the board's own
        safe area for its format."""
        look = (FILM.parent / "time.ts").read_text()
        self.assertIn("safe: board.format.name ? board.system.safe?.[board.format.name] : undefined", look)
