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
            (run / "public" / "photos").mkdir(parents=True)
            (run / "clips").mkdir()
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(run / "public/photos/a.jpg"))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/01.mp4"))
            shot = {"subject": "a quay in low sun", "camera": "a 28 mm lens at eye height", "move": "a slow push in toward the subject",
                    "asks": "the still comes to life where it stands", "read": True}
            clips = [dict(shot, id="00", beat="hook", role="the hook's world", seconds=2.0, image="photos/a.jpg",
                          stand_in="the hook's push"),
                     dict(shot, id="01", beat="stop-1", role="a still brought to life", seconds=1.5, image="photos/a.jpg",
                          stand_in="the photograph opens out of its pin")]
            board = {"beats": [{"id": "hook", "frames": 60}, {"id": "stop-1", "frames": 45}], "clips": clips}
            (run / "board.json").write_text(json.dumps(board))
            (run / "film.json").write_text(json.dumps({"boards": {"reel": "board.json"}}))
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"], cwd=d,
                               capture_output=True, text=True, env=dict(os.environ, PM_HOME=d, PM_RUN="run"))
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["00"]["status"], "stand-in")
            self.assertEqual(got["00"]["stand_in"], "the hook's push")
            self.assertEqual(got["01"]["status"], "generated")
            self.assertEqual((got["01"]["from_frame"], got["01"]["frames"]), (60, 45))
            frames = sorted((run / "public" / got["01"]["dir"]).glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   str(frames[0])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")


if __name__ == "__main__":
    unittest.main()
