"""The check's frozen row reads the whole film, its ending too: a cut whose last 1.5 s repeat one frame is red even
when the board's stop falls on the first repeated frame, and a cut that holds one frame for half a second is green.
The closer keeps its slow push to the last frame, so a film that stands still at its end is a stalled render.

    python3 -I -m unittest discover -s S/tests -p test_frozen.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402

HANDLES = ["liv.outside", "theo.makes"]


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is absent")
class FrozenRow(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        _env.tools()

    def frozen_row(self, hold):
        """The check's frozen row over a cut of two moving seconds and then `hold` seconds of one repeated frame, its
        board's stop on the first held frame."""
        import boards
        import qa
        import storyboard
        Path("render").mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=2", "-vf",
                        f"tpad=stop_mode=clone:stop_duration={hold}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "render/cut.mp4"], check=True)
        _env.write_json("render/cut.json", {"hook_frame": 1, "frames": int(30 * (2 + hold)), "sound": {}})
        beats = [{"id": "hook"}] + [{"id": f"person-{i}", "person": h} for i, h in enumerate(HANDLES, 1)] + [{"id": "closer"}]
        _env.write_json("film.json", {"style": "scrapbook", "bpm": 120, "storyboard": {"beats": beats, "people": HANDLES}})
        _env.write_json("render/board-reel.json", {"bpm": 120, "beats": beats, "sound": [{"kind": "stop", "at": 4.0}]})
        video = {"width": 1080, "height": 1920, "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}
        with mock.patch.object(qa, "video_of", lambda p: (video, {}, 2 + hold)), mock.patch.object(boards, "Ctx", lambda: None), \
                mock.patch.object(storyboard, "problems", lambda *a: []):
            res, _ = qa.cut_checks()
        return next(r for r in res if r[0] == "frozen")

    def test_an_ending_that_stands_still_past_the_stop_turns_the_frozen_row_red(self):
        _, ok, detail = self.frozen_row(1.5)
        self.assertFalse(ok, "the closer keeps its slow push to the last frame, past the stop too")
        self.assertIn("1 frozen stretches", detail)

    def test_an_ending_held_under_a_second_keeps_the_frozen_row_green(self):
        _, ok, detail = self.frozen_row(0.5)
        self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
