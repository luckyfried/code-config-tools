"""The clips: a generated clip that arrived is conformed to its photograph's size and its post's beat and placed on
that post's card from the beat's first frame; a clip that did not arrive stands in, named in clips.json; a moment the
person recorded plays their own clip as one shot the length of its beat.

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

# a recording of the person's own: 4 s of a tram, 720x1280
TRAM = Path(__file__).resolve().parent / "fixtures" / "clip-tram.mp4"


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


class OwnClips(unittest.TestCase):
    """A moment the person recorded plays their own clip on its photograph's card: one shot as long as its beat, nothing
    asked of a video model, trimmed from the recording's strongest second with no sound; every other beat is as it was."""

    @classmethod
    def setUpClass(cls):
        import fixture
        import compose
        from test_compose import picked
        cls.compose = compose
        cls.plain = picked(fixture.month())
        cls.recorded = json.loads(json.dumps(cls.plain))
        next(p for p in cls.recorded["posts"] if p["day"] == 17)["clip"] = str(TRAM)
        cls.before = compose.board("editorial-quiet", cls.plain)["reel"]
        cls.after = compose.board("editorial-quiet", cls.recorded)["reel"]
        cls.key = next(c["key"] for c in cls.after["cards"] if c["day"] == 17)

    def test_a_recorded_moment_is_one_clip_beat_as_long_as_its_beat_with_the_recording_as_its_source(self):
        r = self.after
        own = [c for c in r["clips"] if c["beat"] == self.key]
        self.assertEqual(len(own), 1, own)
        c = own[0]
        self.assertEqual((c["use"], c["source"], c["prompt"]), (clips.OWN, str(TRAM), None))
        beat = next(b for b in r["timeline"]["beats"] if b["id"] == self.key)
        self.assertEqual(beat["form"], "clip")
        # from the cut into its card to the cut out of it
        self.assertEqual(c["at"], [round(beat["at"], 3), round(beat["end"], 3)])
        f = lambda x: round(x * r["fps"] * 60 / r["bpm"])
        self.assertAlmostEqual(c["seconds"], (f(beat["end"]) - f(beat["at"])) / r["fps"], places=1)
        # the card keeps its photograph: no photograph on the reel or the wall is the recording
        self.assertNotIn(str(TRAM), [x.get("source") for x in r["cards"] + r["closer"]["tiles"]])

    def test_a_beat_without_a_clip_is_unchanged(self):
        key = lambda c: (c["beat"], c["use"], c["at"], c["prompt"])
        self.assertEqual([key(c) for c in self.after["clips"] if c["beat"] != self.key],
                         [key(c) for c in self.before["clips"] if c["beat"] != self.key])
        span = lambda r: [(c["key"], c["arrive"], c["leave"], c["move"]) for c in r["cards"] if c["key"] != self.key]
        self.assertEqual(span(self.after), span(self.before))

    def test_normalize_trims_the_recording_from_its_strongest_second_with_no_sound(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "storyboards" / "editorial-quiet").mkdir(parents=True)
            (run / "clips").mkdir()
            (Path(d) / "build" / "latest").write_text("run\n")
            # two still seconds, then two that move: the shot starts where it moves
            rec = Path(d) / "rec.mp4"
            ff("-f", "lavfi", "-i", "color=c=0x808080:s=360x640:r=30:d=2", "-f", "lavfi", "-i", "testsrc=s=360x640:r=30:d=2",
               "-f", "lavfi", "-i", "sine=d=4", "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-map", "2:a",
               "-pix_fmt", "yuv420p", "-shortest", str(rec))
            self.assertGreaterEqual(clips.strongest(rec, 1.0), 1.9)
            card = {"size": [720, 1280], "source": str(Path(d) / "poster.jpg"), "file": "photos/a.jpg"}
            reel = {"fps": 30, "bpm": 60, "cards": [dict(card, key="moment-1", arrive=0, leave=1.5)],
                    "clips": [{"id": "01", "beat": "moment-1", "use": clips.OWN, "source": str(rec), "seconds": 1.5,
                               "at": [0, 1.5], "image": "photos/a.jpg", "prompt": None, "stand_in": "the camera pushes in"}]}
            (run / "storyboards" / "editorial-quiet" / "storyboard.json").write_text(json.dumps({"reel": reel}))
            (run / "winner.json").write_text(json.dumps({"board": "editorial-quiet"}))
            env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
            r = subprocess.run([sys.executable, str(KIT / "scripts/clips.py"), "list"], cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads((run / "clips" / "requests.json").read_text())["clips"], [])
            r = subprocess.run([sys.executable, str(KIT / "scripts/clips.py"), "normalize"], cwd=d, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())
            c = got["clips"]["01"]
            self.assertEqual((c["status"], c["source"], c["frames"]), (clips.OWN, str(rec), 45))
            self.assertTrue(2.0 - 0.2 <= c["from_second"] <= 2.5, c["from_second"])
            frames = sorted((run / got["frames"] / "01").glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            self.assertEqual(clips.placed(run), [{"id": "01", "image": "photos/a.jpg", "from": 0, "frames": 45, "dir": "clips/01"}])


if __name__ == "__main__":
    unittest.main()
