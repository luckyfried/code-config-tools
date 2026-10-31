"""The clips: a generated clip that arrived is conformed to its photograph's size and its beat's length and placed on
that photograph's card from the beat's first frame; one that did not arrive stands in, named in clips.json. A clip the
person recorded plays on its piece as one shot the length of its beat, from its strongest second, sound off, and the
board is otherwise the board a photograph would have had.

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
sys.path.insert(0, str(KIT / "tests"))
import _env  # noqa: E402
import clips as clips_  # noqa: E402
import picks  # noqa: E402

TRAM = KIT / "tests/fixtures/clip-tram.mp4"


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
            clips = [{"id": "00", "beat": "hook", "role": "the wall's world", "seconds": 2.0, "image": "photos/a.jpg",
                      "prompt": "p", "stand_in": "the hook's push"},
                     {"id": "01", "beat": "piece-1", "role": "the photograph brought to life", "seconds": 1.5,
                      "image": "photos/a.jpg", "prompt": "p", "stand_in": "the card lifts"}]
            board = {"beats": [{"id": "hook", "frames": 60}, {"id": "piece-1", "frames": 45}], "clips": clips}
            (run / "board.json").write_text(json.dumps(board))
            (run / "film.json").write_text(json.dumps({"boards": {"reel": "board.json"}}))
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "normalize", "--run", "build/run",
                                "--why", "no video model"], cwd=d, capture_output=True, text=True)
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



def probe(path, entries):
    return subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", entries, "-of", "csv=p=0", str(path)],
                          capture_output=True, text=True).stdout.strip()


def grey(path):
    """The frame as a 32x32 grey copy, for comparing two frames."""
    return subprocess.run([_env.ffmpeg(), "-v", "error", "-i", str(path), "-vf", "scale=32:32,format=gray", "-f", "rawvideo", "-"],
                          capture_output=True).stdout


def apart(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


class Recorded(unittest.TestCase):
    """A clip the person recorded is their own shot: nothing is generated for it, and it plays on its piece's beat."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.run_ = self.d / "build" / "run"
        (self.run_ / "public" / "photos").mkdir(parents=True)

    def normalize(self, frames, start):
        poster = self.run_ / "public/photos/r3-tram.jpg"
        self.assertTrue(picks.poster(TRAM, poster, start))
        cl = [{"id": "00", "beat": "piece-3", "role": "their own clip", "source": str(TRAM), "from": start, "seconds": frames / 30,
               "image": "photos/r3-tram.jpg", "prompt": None, "stand_in": None},
              {"id": "01", "beat": "grid", "role": "the texture of the grid", "seconds": 1.5, "image": "photos/r3-tram.jpg",
               "prompt": "p", "stand_in": "the grid landing tile by tile"}]
        board = {"beats": [{"id": "hook", "frames": 60}, {"id": "piece-3", "frames": frames}, {"id": "grid", "frames": 90}], "clips": cl}
        (self.run_ / "board.json").write_text(json.dumps(board))
        (self.run_ / "film.json").write_text(json.dumps({"boards": {"reel": "board.json"}}))
        for args in (["list"], ["normalize", "--why", "no video model"]):
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), *args, "--run", "build/run"], cwd=self.d,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads((self.run_ / "clips.json").read_text())["clips"], poster

    def test_a_recorded_clip_is_one_shot_the_length_of_its_beat_from_its_strongest_second(self):
        got, poster = self.normalize(55, 1.5)
        own = got["00"]
        self.assertEqual(own["status"], "recorded")
        self.assertEqual((own["from_frame"], own["frames"], own["start"]), (60, 55, 1.5))
        frames = sorted((self.run_ / "public" / own["dir"]).glob("*.jpg"))
        self.assertEqual(len(frames), 55, "one shot exactly its beat long")
        self.assertEqual(probe(frames[0], "stream=width,height"), probe(poster, "stream=width,height"))
        self.assertLess(apart(grey(frames[0]), grey(poster)), 6, "the shot starts on its poster, the frame a move flies in")
        self.assertGreater(apart(grey(frames[0]), grey(frames[-1])), 1, "and it moves")
        self.assertEqual(got["01"]["status"], "stand-in", "the generated clips are asked for as before")
        requests = json.loads((self.run_ / "clips/requests.json").read_text())["clips"]
        self.assertEqual([q["id"] for q in requests], ["01"], "nothing is asked of a video model for their own clip")
        with _env_in(self.run_):
            shown = clips_.placed()
        self.assertEqual([(c["id"], c["beat"], c["from"], c["frames"]) for c in shown], [("00", "piece-3", 60, 55)])

    def test_a_beat_longer_than_the_rest_of_the_clip_holds_its_last_frame(self):
        got, _ = self.normalize(60, 3.5)
        frames = sorted((self.run_ / "public" / got["00"]["dir"]).glob("*.jpg"))
        self.assertEqual(len(frames), 60, "never looped back to its start, never short")
        self.assertLess(apart(grey(frames[-1]), grey(frames[-10])), 1)

    def test_the_strongest_second_leaves_the_clip_room_to_play(self):
        at = picks.strongest(TRAM)
        self.assertGreaterEqual(at, 0.0)
        self.assertLessEqual(at, float(probe(TRAM, "format=duration")) - picks.SHOT + 1e-6)
        self.assertEqual(probe(TRAM, "stream=codec_type").splitlines().count("audio"), 0)


class _env_in:
    """Inside the run folder for the length of a with block."""

    def __init__(self, run):
        self.run, self.here = run, None

    def __enter__(self):
        self.here = os.getcwd()
        os.chdir(self.run)

    def __exit__(self, *exc):
        os.chdir(self.here)


class OnTheBoard(unittest.TestCase):
    """A piece they gave as a recorded clip keeps the board a photograph would have had: the same beats, arrivals and
    moves; only the clips say that piece plays their recording."""

    def test_a_clip_request_is_one_shot_the_length_of_its_beat_and_every_other_beat_is_unchanged(self):
        import compose
        import test_story as T
        for style in compose.TRIO:
            plain = T.plan(style=style)["board"]
            ps = T.posts()
            ps[2].update(video="photos/2026-03-08.mp4", clip_at=1.2)
            filmed = T.plan(ps=ps, style=style)["board"]
            with self.subTest(style=style):
                self.assertEqual(filmed["beats"], plain["beats"])
                own = [c for c in filmed["clips"] if c["role"] == "their own clip"]
                self.assertEqual(len(own), 1)
                beat = next(x for x in filmed["beats"] if x["id"] == own[0]["beat"])
                self.assertEqual(own[0]["beat"], "piece-3")
                self.assertEqual((own[0]["source"], own[0]["from"], own[0]["prompt"]), ("photos/2026-03-08.mp4", 1.2, None))
                self.assertAlmostEqual(own[0]["seconds"], beat["beats"] * 60 / filmed["bpm"], places=2)
                self.assertEqual(own[0]["image"], next(L for L in beat["layers"] if L["kind"] == "Photo")["photo"]["file"])
                rest = lambda b: [(c["beat"], c["role"], c["image"]) for c in b["clips"] if c["beat"] != "piece-3"]
                self.assertEqual(rest(filmed), rest(plain), "the other clips are asked for as before")


if __name__ == "__main__":
    unittest.main()
