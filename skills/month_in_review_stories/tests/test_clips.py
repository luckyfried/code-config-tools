"""The generated clips: a clip that arrived is conformed to its photograph's size and its post's beat and placed on
that post's card from the beat's first frame; a clip that did not arrive stands in, named in clips.json.

    python3 -m unittest discover -s S/tests -p 'test_clips.py'
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
import clips  # noqa: E402


def ff(*args):
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


class Clips(unittest.TestCase):
    def test_an_arrived_clip_is_placed_on_its_card_and_a_missing_one_stands_in(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "storyboards" / "editorial-quiet").mkdir(parents=True)
            (run / "clips").mkdir()
            (Path(d) / "build" / "latest").write_text("run\n")
            photo = Path(d) / "a.jpg"
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(photo))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/01.mp4"))
            card = {"size": [1200, 1600], "source": str(photo), "file": "photos/a.jpg"}
            reel = {"fps": 30, "bpm": 60,
                    "cards": [dict(card, key="post-1", arrive=2, leave=3.5), dict(card, key="post-2", arrive=3.5, leave=5)],
                    "clips": [{"id": "00", "beat": "post-1", "use": "still", "seconds": 1.5, "at": [2, 3.5],
                               "image": "photos/a.jpg", "prompt": "p", "stand_in": "the camera pushes in on the photograph"},
                              {"id": "01", "beat": "post-2", "use": "still", "seconds": 1.5, "at": [3.5, 5],
                               "image": "photos/a.jpg", "prompt": "p", "stand_in": "the camera pushes in on the photograph"}]}
            (run / "storyboards" / "editorial-quiet" / "storyboard.json").write_text(json.dumps({"reel": reel}))
            (run / "winner.json").write_text(json.dumps({"board": "editorial-quiet"}))
            env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
            r = subprocess.run([sys.executable, str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"],
                               cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["00"]["status"], "stand-in")
            self.assertEqual(got["00"]["stand_in"], "the camera pushes in on the photograph")
            self.assertEqual(got["00"]["why"], "no video model")
            self.assertEqual(got["01"]["status"], "generated")
            self.assertEqual((got["01"]["from_frame"], got["01"]["frames"]), (105, 45))
            first = json.loads((run / "clips.json").read_text())["frames"]
            frames = sorted((run / first / "01").glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            # a second normalize conforms into a folder of its own and removes the one clips.json does not name
            r = subprocess.run([sys.executable, str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"],
                               cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            second = json.loads((run / "clips.json").read_text())["frames"]
            self.assertNotEqual(first, second)
            self.assertEqual(sorted(p.name for p in (run / "clips").glob("frames*")), [Path(second).name])
            frames = sorted((run / second / "01").glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   str(frames[0])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")
            self.assertEqual(clips.placed(run), [{"id": "01", "image": "photos/a.jpg", "from": 105, "frames": 45, "dir": "clips/01"}])


if __name__ == "__main__":
    unittest.main()
