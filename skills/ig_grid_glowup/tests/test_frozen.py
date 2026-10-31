"""The gate's frozen row reads the whole film, its ending too: a picture that stands still for a second or more
anywhere, past the board's stop included, turns it red, and a film that moves to its last frame keeps it green.

    python3 -I -m unittest discover -s tests -p test_frozen.py
"""
import contextlib
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_resume import BOARD, Run, checkable  # noqa: E402
import _env  # noqa: E402
import studio  # noqa: E402


class FrozenRow(Run):
    def frozen_row(self, hold):
        """The check's frozen row over a reel of two moving seconds and then `hold` seconds of one repeated frame, the
        board's stop on the first held frame (2.0 s)."""
        import qa
        Path("out").mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=2", "-vf",
                        f"tpad=stop_mode=clone:stop_duration={hold}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "out/film.mp4"], check=True)
        boards = checkable("reel")
        boards["reel"].update(stop_seconds=2.0, seconds=2.0 + hold)
        self.write("board.json", dict(BOARD, boards=boards))
        self.write("render/film.json", {"hash": "h", "formats": ["reel"], "music": False})
        self.write("render/film-report.json", {"jobs": 1, "failed": 0, "findings": []})
        quiet = {"probe": lambda film, run=None: {"streams": [], "format": {}}, "cards_check": lambda *a, **k: ([], 0, {}),
                 "words_lost": lambda *a: [], "figures": lambda *a: None}
        with contextlib.ExitStack() as stack:
            for name, value in quiet.items():
                stack.enter_context(mock.patch.object(qa, name, value))
            stack.enter_context(mock.patch.object(studio, "measure", lambda *a, **k: {}))
            res = qa.film_checks()[0]
        return next((r[1], r[2]) for r in res if r[0] == "frozen")

    def test_an_ending_that_stands_still_past_the_stop_turns_the_frozen_row_red(self):
        ok, detail = self.frozen_row(1.5)
        self.assertFalse(ok, "the closer keeps a living element to the last frame, past the stop too")
        self.assertIn("1 frozen stretches", detail)

    def test_a_film_that_moves_to_its_last_frame_keeps_the_frozen_row_green(self):
        ok, detail = self.frozen_row(0)
        self.assertTrue(ok, detail)
        self.assertIn("0 frozen stretches", detail)

    def test_an_ending_held_under_a_second_keeps_the_frozen_row_green(self):
        ok, detail = self.frozen_row(0.5)
        self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
