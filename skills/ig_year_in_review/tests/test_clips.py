"""The generated clips: a clip that arrived is conformed to its photograph's size and its month's length and placed on
that month from the beat's first frame; a clip that did not arrive stands in, named in clips.json.

    python3 -I -m unittest discover -s S/tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402


def ff(*args):
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


class Clips(unittest.TestCase):
    def test_an_arrived_clip_is_placed_on_its_month_and_a_missing_one_stands_in(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            build = Path(d) / "build"
            (build / "public" / "photos").mkdir(parents=True)
            (build / "clips").mkdir()
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(build / "public/photos/a.jpg"))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(build / "clips/m02.mp4"))
            clips = [{"id": "m01", "beat": "m01", "role": "january's photograph moving", "seconds": 2.0, "image": "photos/a.jpg",
                      "prompt": "p", "stand_in": "the camera and the unfolding on the still photograph"},
                     {"id": "m02", "beat": "m02", "role": "february's photograph moving", "seconds": 1.5,
                      "image": "photos/a.jpg", "prompt": "p", "stand_in": "the camera and the unfolding on the still photograph"}]
            board = {"beats": [{"id": "hook", "frames": 90}, {"id": "m01", "frames": 60}, {"id": "m02", "frames": 45}], "clips": clips}
            (build / "board.json").write_text(json.dumps(board))
            (build / "film.json").write_text(json.dumps({"boards": {"reel": "board.json"}}))
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"],
                               cwd=d, capture_output=True, text=True, env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((build / "clips.json").read_text())["clips"]
            self.assertEqual(got["m01"]["status"], "stand-in")
            self.assertEqual(got["m01"]["why"], "no video model")
            self.assertEqual(got["m02"]["status"], "generated")
            self.assertEqual((got["m02"]["from_frame"], got["m02"]["frames"]), (150, 45))
            frames = sorted((build / "public" / got["m02"]["dir"]).glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   str(frames[0])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")


if __name__ == "__main__":
    unittest.main()
