"""The check's frozen row reads the whole film, its ending too: a picture that stands still for a second or more
anywhere, past the board's stop and inside the closer included, turns it red, and a film that moves to its last frame
keeps it green.

python3 -m unittest discover -s tests -p test_frozen.py   (from the kit's folder)
"""
import contextlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402


class FrozenRow(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(d.cleanup)
        cwd = os.getcwd()
        os.chdir(d.name)
        self.addCleanup(os.chdir, cwd)

    def frozen_row(self, hold):
        """The check's frozen row over a film of two moving seconds and then `hold` seconds of one repeated frame, the
        closer opening and the board's stop (beat 4 at 120 bpm, 2.0 s) on the first held frame."""
        Path("out").mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=2", "-vf",
                        f"tpad=stop_mode=clone:stop_duration={hold}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "out/film.mp4"], check=True)
        _env.write_json("film.json", {"seconds": 2.0 + hold, "bpm": 120, "cuts": [], "beats": [{"id": "hook", "at": 0}, {"id": "closer", "at": 4.0}],
                                      "sound": [{"kind": "impact", "at": 4.0, "beat": "closer"},
                                                {"kind": "stop", "at": 4.0, "beat": "closer", "what": "the picture and the music stop together"}]})
        with contextlib.ExitStack() as s:
            for name, fn in (("probe", lambda p, run=None: {"streams": [], "format": {}}), ("frame_luma", lambda run=None, film=None: [0.5]),
                             ("board_check", lambda film: (True, "")), ("figures", lambda *a: None)):
                s.enter_context(mock.patch.object(qa, name, fn))
            s.enter_context(mock.patch.object(studio, "measure", lambda *a, **k: {}))
            res = qa.film_checks()
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
