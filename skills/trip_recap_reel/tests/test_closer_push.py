"""The closer is never a still frame: from the stop on the film holds its picture at the stop's instant, and the shared
MoveLayer keeps the closer's slow push to the last frame when the film hands it its own time (`now`), the cadence-
stepped frame, never held at the stop.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import re
import unittest
from pathlib import Path

FILM = Path(__file__).resolve().parents[1] / "motion/studio/Film.tsx"


class CloserPush(unittest.TestCase):
    def test_the_film_hands_the_move_layer_its_time_past_the_stop(self):
        calls = re.findall(r"<MoveLayer\b[^>]*?/>", FILM.read_text(), re.S)
        self.assertEqual(len(calls), 1, calls)
        self.assertIn("now={frame / plan.pulse}", calls[0])


PLAN = FILM.parent / "plan.ts"


class CloserBand(unittest.TestCase):
    def test_the_last_stop_glides_to_the_middle_of_the_frame_under_the_closer(self):
        """The closer's words stand in the middle of the frame between its bars; the last stop's picture moves there with
        them, so the closing line never rides the picture's edge."""
        self.assertIn("const shot = closingOf(plan, shotAt(plan, t)!, t);", FILM.read_text())
        plan = PLAN.read_text()
        self.assertIn("const dy = (plan.H / 2 - (shot.box[1] + shot.box[3]) / 2) * u * u * (3 - 2 * u);", plan)
        self.assertIn("const u = clamp01((t - plan.closer.at) / CLOSING);", plan)


class Safe(unittest.TestCase):
    def test_the_look_hands_the_moves_the_formats_safe_area(self):
        self.assertIn("safe: sys.safe[board.format.name || 'reel'] ?? sys.safe.reel,", PLAN.read_text())
