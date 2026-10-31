"""The generated clips: a clip that arrived is conformed to its photograph's size and its beat's length and placed on
that photograph's print from the beat's first frame; a clip that did not arrive stands in, named in clips.json.

python3 -m unittest discover -s tests   (from the kit's folder)
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
    def test_an_arrived_clip_is_placed_on_its_print_and_a_missing_one_stands_in(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "photos").mkdir(parents=True)
            (run / "clips").mkdir()
            (Path(d) / "build" / "current").symlink_to("run")
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(run / "public/photos/a.jpg"))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/made.mp4"))
            clips = [{"id": "hook", "beat": "hook", "role": "their photograph breathing", "seconds": 2.0, "image": "photos/a.jpg",
                      "prompt": "p", "stand_in": "the camera's drift"},
                     {"id": "made", "beat": "made", "role": "the plate answering", "seconds": 1.5, "image": "photos/a.jpg",
                      "prompt": "p", "stand_in": "the turned plate"}]
            film = {"beats": [{"id": "hook", "frames": 60}, {"id": "made", "frames": 45}], "clips": clips}
            (run / "film.json").write_text(json.dumps(film))
            env = {k: v for k, v in os.environ.items() if k not in ("LH_ROOT", "LH_RUN")}
            r = subprocess.run([sys.executable, str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"],
                               cwd=d, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["hook"]["status"], "stand-in")
            self.assertEqual(got["hook"]["stand_in"], "the camera's drift")
            self.assertEqual(got["made"]["status"], "generated")
            self.assertEqual((got["made"]["from_frame"], got["made"]["frames"]), (60, 45))
            frames = sorted((run / "public" / got["made"]["dir"]).glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   str(frames[0])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")


if __name__ == "__main__":
    unittest.main()
