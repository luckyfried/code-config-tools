"""The gate's frozen row reads the whole film, its ending too: a picture that stands still for a second or more
anywhere, past the board's stop included, turns it red, and a film that moves to its last frame keeps it green.

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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import _env  # noqa: E402
import qa  # noqa: E402


class FrozenRow(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(d.cleanup)
        cwd = os.getcwd()
        os.chdir(d.name)
        self.addCleanup(os.chdir, cwd)

    def frozen_row(self, hold):
        """The gate's frozen row over a film of two moving seconds and then `hold` seconds of one repeated frame, its
        board's stop cue (beat 4 at 120 bpm, 2.0 s) on the first held frame."""
        Path("out").mkdir()
        film = Path("out/film.mp4")
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=2", "-vf",
                        f"tpad=stop_mode=clone:stop_duration={hold}", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(film)], check=True)
        _env.write_json("film.json", {"bpm": 120, "beats": [{"id": "hook"}, {"id": "closer"}], "system": {"finish": {}},
                                      "sound": [{"kind": "stop", "at": 4.0, "what": "the music stops"}]})
        probed = {"streams": [{"codec_type": "video"}], "format": {"duration": str(2 + hold)}}
        with contextlib.ExitStack() as s:
            for name, fn in (("probe", lambda film, spawn: probed), ("frame0_check", lambda *a: (True, "")), ("hook_check", lambda *a: (True, "")),
                             ("cuts_figure", lambda *a: ""), ("still_figure", lambda *a: ""), ("board_checks", lambda *a: None)):
                s.enter_context(mock.patch.object(qa, name, fn))
            res = qa.film_checks(film, audio=False)
        return next(r for r in res if r[0] == "frozen")

    def test_an_ending_that_stands_still_past_the_stop_turns_the_frozen_row_red(self):
        _, ok, detail = self.frozen_row(1.5)
        self.assertFalse(ok, "the closer keeps a living element to the last frame, past the stop too")
        self.assertIn("1 frozen stretches", detail)

    def test_a_film_that_moves_to_its_last_frame_keeps_the_frozen_row_green(self):
        _, ok, detail = self.frozen_row(0)
        self.assertTrue(ok, detail)
        self.assertIn("0 frozen stretches", detail)

    def test_an_ending_held_under_a_second_keeps_the_frozen_row_green(self):
        _, ok, detail = self.frozen_row(0.5)
        self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
