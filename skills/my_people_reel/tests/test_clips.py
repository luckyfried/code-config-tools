"""The generated clips: a clip that arrived is conformed to its photograph's size and its beat's length and placed on
that photograph's card from the beat's first frame; a clip that did not arrive stands in, named in clips.json.

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
    def test_an_arrived_clip_is_placed_on_its_card_and_a_missing_one_stands_in(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "matched").mkdir(parents=True)
            (run / "clips").mkdir()
            (run / "render").mkdir()
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(run / "public/matched/a.jpg"))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/01.mp4"))
            clips = [{"id": "00", "beat": "hook", "role": "them together", "seconds": 2.0, "image": "matched/a.jpg",
                      "prompt": "p", "stand_in": "the hook's push"},
                     {"id": "01", "beat": "person-5", "role": "the person brought to life", "seconds": 1.5,
                      "image": "matched/a.jpg", "prompt": "p", "stand_in": "the card lifts"}]
            board = {"beats": [{"id": "hook", "frames": 60}, {"id": "person-5", "frames": 75}], "clips": clips}
            (run / "render" / "board-reel.json").write_text(json.dumps(board))
            (Path(d) / "build" / "current").write_text("run\n")
            env = {k: v for k, v in os.environ.items() if k not in ("MPR_RUN", "MPR_WORKSPACE")}
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"],
                               cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["00"]["status"], "stand-in")
            self.assertEqual(got["00"]["stand_in"], "the hook's push")
            self.assertEqual(got["01"]["status"], "generated")
            self.assertEqual((got["01"]["from_frame"], got["01"]["frames"]), (60, 75))
            frames = sorted((run / "public" / got["01"]["dir"]).glob("*.jpg"))
            self.assertEqual(len(frames), 75)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   str(frames[0])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")


if __name__ == "__main__":
    unittest.main()
