"""The clips: a generated clip that arrived is conformed to its photograph's size and its beat's length and placed on
that photograph's card from the beat's first frame; a clip that did not arrive stands in, named in clips.json; and a
clip the person recorded is one shot the length of its beat, cut from its strongest seconds, silent, placed on its
card beside the generated ones, while the beat without a clip stands in as it would alone.

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


    def test_their_own_clip_is_one_shot_the_length_of_its_beat_from_its_strongest_seconds(self):
        import clips
        tram = KIT / "tests" / "fixtures" / "clip-tram.mp4"
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "matched").mkdir(parents=True)
            (run / "render").mkdir()
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=720x1280", "-frames:v", "1", str(run / "public/matched/a.jpg"))
            req = [{"id": "00", "beat": "hook", "role": "them together", "seconds": 2.0, "image": "matched/a.jpg",
                    "prompt": "p", "stand_in": "the hook's push"},
                   {"id": "01", "beat": "person-1", "role": "their own clip", "source": str(tram), "seconds": 2.5,
                    "image": "matched/a.jpg", "prompt": None, "stand_in": None}]
            board = {"beats": [{"id": "hook", "frames": 60}, {"id": "person-1", "frames": 75}], "clips": req}
            (run / "render" / "board-reel.json").write_text(json.dumps(board))
            (Path(d) / "build" / "current").write_text("run\n")
            env = {k: v for k, v in os.environ.items() if k not in ("MPR_RUN", "MPR_WORKSPACE")}
            for cmd in ("list", "normalize"):
                r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), cmd, "--why", "no video model"],
                                   cwd=d, capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stderr)
            asked = {c["id"]: c for c in json.loads((run / "clips" / "requests.json").read_text())["clips"]}
            self.assertNotIn("save_as", asked["01"])
            self.assertAlmostEqual(asked["01"]["to"] - asked["01"]["from"], 2.5, places=2)
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["00"]["status"], "stand-in")
            self.assertEqual(got["00"]["stand_in"], "the hook's push")
            self.assertEqual(got["01"]["status"], "their_clip")
            self.assertEqual((got["01"]["from_frame"], got["01"]["frames"]), (60, 75))
            self.assertEqual((got["01"]["from"], got["01"]["to"]), (asked["01"]["from"], asked["01"]["to"]))
            self.assertEqual(len(sorted((run / "public" / got["01"]["dir"]).glob("*.jpg"))), 75)
            cwd = os.getcwd()
            os.chdir(run)
            try:
                self.assertEqual([c["id"] for c in clips.placed()], ["01"])
            finally:
                os.chdir(cwd)

    def test_the_strongest_seconds_are_where_the_recording_moves(self):
        import clips
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            v = Path(d) / "v.mp4"
            # two still seconds, then two seconds of moving bars, then two still seconds
            ff("-f", "lavfi", "-i", "color=c=0x777777:s=180x320:r=30:d=2", "-f", "lavfi", "-i", "testsrc=s=180x320:r=30:d=2",
               "-f", "lavfi", "-i", "color=c=0x777777:s=180x320:r=30:d=2", "-filter_complex", "[0][1][2]concat=n=3:v=1",
               "-pix_fmt", "yuv420p", str(v))
            t0, t1 = clips.strongest(v, 2.0)
            self.assertLessEqual(abs(t0 - 2.0), 0.5, (t0, t1))
            self.assertAlmostEqual(t1 - t0, 2.0, places=2)
            self.assertEqual(clips.strongest(v, 9.0), (0.0, 6.0))


if __name__ == "__main__":
    unittest.main()
