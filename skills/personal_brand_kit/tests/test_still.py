"""The luma line reads the picture, not its grain: a locked frame under moving film grain reads quiet, and a slow
drift under the same grain does not.

    python3 -I -m unittest discover -s S/tests
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import studio  # noqa: E402


def clip(path, drift):
    """Three seconds of the reel's frame, kept lossless: bars and a pale square on the bars, under temporal grain as
    strong as a style card's film grain (it reads about 2 on the full-size frame and about 0.12 at LUMA_WIDTH, as a locked
    closer does); with `drift` the square moves 20 px a second, slower than any move in the film."""
    x = "200+20*t" if drift else "200"
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "smptehdbars=s=1080x1920:r=30:d=3",
                    "-f", "lavfi", "-i", "color=c=0xf0e8d8:s=400x400:r=30:d=3",
                    "-filter_complex", f"[0][1]overlay=x='{x}':y=760,noise=alls=4:allf=t,format=yuv420p",
                    "-c:v", "ffv1", str(path)], check=True)


class StillUnderGrain(unittest.TestCase):
    def test_a_locked_frame_under_grain_is_still_and_a_slow_drift_is_not(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            locked, drift = Path(d) / "locked.mkv", Path(d) / "drift.mkv"
            clip(locked, False)
            clip(drift, True)
            still = studio.luma_line(locked)
            moving = studio.luma_line(drift)
        self.assertEqual(len(still), 2)
        self.assertTrue(all(y < 0.5 for y in still), still)
        self.assertTrue(all(y > 0.5 for y in moving), moving)
        self.assertEqual(studio.under_half(still)["seconds_under_half"], [1, 2])
        self.assertEqual(studio.under_half(moving)["seconds_under_half"], [])


if __name__ == "__main__":
    unittest.main()
