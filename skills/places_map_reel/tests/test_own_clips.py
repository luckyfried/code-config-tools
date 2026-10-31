"""A clip they recorded plays on its stop (tests/fixtures/clip-tram.mp4): the stop's clip is their own, one shot of its
beat's length from the clip's strongest second, with nothing asked of a video model; every other beat is the board it
was without the clip; and normalize conforms the recording to its beat's frames, silent, on the stop's card.

    python3 -I -m unittest discover -s S/tests
"""
import copy
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
import board_drive  # noqa: E402
import clips  # noqa: E402
import look  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
TRAM = KIT / "tests" / "fixtures" / "clip-tram.mp4"


def with_clip(file):
    """The trip with the photograph `file` made from the tram clip, as grade.py records one."""
    src = copy.deepcopy(SOURCE)
    for ph in src["photos"]:
        if ph["file"] == file:
            ph.update(clips.recorded(TRAM))
    return src


class TheirOwnClip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.style = look.TRIO[0]
        cls.plain = board_drive.build(copy.deepcopy(SOURCE), "reel", None, cls.style)
        cls.card = cls.plain["route"]["cards"][2]
        cls.board = board_drive.build(with_clip(cls.card["file"]), "reel", None, cls.style)

    def test_the_clip_is_read_for_its_length_and_its_strongest_second(self):
        rec = clips.recorded(TRAM)
        self.assertEqual(rec["clip"], str(TRAM.resolve()))
        self.assertAlmostEqual(rec["clip_seconds"], 4.0, delta=0.1)
        self.assertTrue(0 <= rec["clip_from"] < rec["clip_seconds"])
        self.assertEqual(clips.recorded(KIT / "tests" / "data" / "trip.json"), {})

    def test_a_clip_request_is_one_shot_the_length_of_its_beat(self):
        beat = next(b for b in self.board["beats"] if b["id"] == self.card["id"])
        own = [c for c in self.board["clips"] if c.get("source")]
        self.assertEqual(len(own), 1)
        c = own[0]
        secs = beat["bars"] * 4 * 60 / self.board["bpm"]
        rec = clips.recorded(TRAM)
        self.assertEqual((c["beat"], c["role"], c["image"], c["source"]), (self.card["id"], "their own clip", self.card["file"], str(TRAM.resolve())))
        self.assertEqual(c["seconds"], round(secs, 1))
        self.assertAlmostEqual(c["from"], max(0.0, min(rec["clip_from"], rec["clip_seconds"] - secs)), places=3)
        self.assertIsNone(c["prompt"])
        self.assertNotIn(str(TRAM.resolve()), json.dumps(self.board["beats"]))

    def test_a_beat_without_a_clip_is_unchanged(self):
        self.assertEqual(self.board["beats"], self.plain["beats"])
        self.assertEqual(self.board["route"], self.plain["route"])
        self.assertEqual([c for c in self.board["clips"] if c["beat"] != self.card["id"]],
                         [c for c in self.plain["clips"] if c["beat"] != self.card["id"]])

    def test_normalize_plays_the_recording_for_its_beats_frames_without_its_sound(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "photos").mkdir(parents=True)
            subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x996633:s=720x1280", "-frames:v", "1",
                            str(run / "public/photos/a.jpg")], check=True)
            c = {"id": "01", "beat": "stop-1", "role": "their own clip", "seconds": 1.5, "image": "photos/a.jpg",
                 "source": str(TRAM.resolve()), "from": 2.0, "prompt": None, "stand_in": None}
            (run / "board.json").write_text(json.dumps({"beats": [{"id": "hook", "frames": 60}, {"id": "stop-1", "frames": 45}], "clips": [c]}))
            (run / "film.json").write_text(json.dumps({"boards": {"reel": "board.json"}}))
            env = dict(os.environ, PM_HOME=d, PM_RUN="run")
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "list"], cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads((run / "clips" / "requests.json").read_text())["clips"], [])
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "normalize"], cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())["clips"]["01"]
            self.assertEqual((got["status"], got["from_frame"], got["frames"]), ("recorded", 60, 45))
            self.assertEqual(len(list((run / "public" / got["dir"]).glob("*.jpg"))), 45)
            here = os.getcwd()
            os.chdir(run)
            try:
                self.assertEqual([p["id"] for p in clips.placed()], ["01"])
            finally:
                os.chdir(here)


if __name__ == "__main__":
    unittest.main()
