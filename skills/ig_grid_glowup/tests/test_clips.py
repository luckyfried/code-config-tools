"""A clip they recorded on its post: normalize conforms the recording as one shot the length of its beat, from the
second the board names, sound off, opening on its first frame for the frames a trailer move takes to land its
photograph and keeping its last frame when the recording ends first; list asks no video model for it; a generated clip
beside it is handled as before. picks reads the recording's strongest second and makes its poster that second's frame.

    python3 -I -m unittest discover -s S/tests -p test_clips.py
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import clips  # noqa: E402
import picks  # noqa: E402

CLIP = KIT / "tests" / "fixtures" / "clip-tram.mp4"


class OwnClip(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        from PIL import Image
        (self.dir / "public" / "graded").mkdir(parents=True)
        for n in ("04", "05"):
            Image.new("RGB", (360, 640), (180, 120, 90)).save(self.dir / "public" / "graded" / f"{n}.jpg")

    def board(self, frames, hold):
        beats = [{"id": "hook", "frames": 30}, {"id": "post-4", "frames": 20}, {"id": "post-5", "frames": frames}]
        cl = [{"id": "04", "beat": "post-4", "role": "texture", "seconds": 0.7, "image": "graded/04.jpg",
               "prompt": "the bench; a slow truck left; 0.7 s, a seamless loop", "stand_in": "the card sliding in"},
              {"id": "05", "beat": "post-5", "role": "their own clip", "seconds": frames / 30, "image": "graded/05.jpg",
               "source": str(CLIP), "from": 1.0, "hold": hold, "prompt": None, "stand_in": None}]
        _env.write_json("board.json", {"boards": {"reel": {"beats": beats, "clips": cl}}})

    def run_cmd(self, cmd, *args):
        out = io.StringIO()
        with mock.patch.object(_env, "enter_run", lambda new=False: None), \
                mock.patch.object(sys, "argv", ["clips.py", cmd, *args]), contextlib.redirect_stdout(out):
            code = clips.main()
        return code, out.getvalue()

    def frames_of(self, rel):
        return sorted((Path("public") / rel).glob("*.jpg"))

    def test_a_recording_plays_as_one_shot_the_length_of_its_beat_from_its_second(self):
        self.board(150, 12)
        code, out = self.run_cmd("list")
        self.assertEqual(code, 0, out)
        reqs = json.loads(Path("clips/requests.json").read_text())["clips"]
        self.assertEqual([r["id"] for r in reqs], ["04"])
        self.assertIn("their own clip", out)
        code, out = self.run_cmd("normalize", "--why", "no video model in this session")
        self.assertEqual(code, 0, out)
        rec = json.loads(Path("clips.json").read_text())["clips"]
        self.assertEqual(rec["04"]["status"], "stand-in")
        own = rec["05"]
        self.assertEqual((own["status"], own["frames"], own["from_frame"], own["source"]), ("recorded", 150, 50, str(CLIP)))
        shot = self.frames_of(own["dir"])
        self.assertEqual(len(shot), 150)
        digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
        # it opens on one frame held through the trailer move, then moves; the 4 s recording read from 1 s ends at
        # frame 102 and its last frame holds to the end of the beat
        self.assertEqual(len({digest(f) for f in shot[:12]}), 1)
        self.assertNotEqual(digest(shot[11]), digest(shot[13]))
        self.assertEqual(len({digest(f) for f in shot[110:]}), 1)
        self.assertEqual(clips.placed(), [{"id": "05", "image": "graded/05.jpg", "from": 50, "frames": 150, "dir": own["dir"]}])

    def test_the_shot_carries_no_sound_and_the_photographs_size(self):
        self.board(30, 0)
        _, _, rel = clips.conform(CLIP, "graded/05.jpg", 30, "05", 1.0, 0)
        from PIL import Image
        with Image.open(self.frames_of(rel)[0]) as im:
            self.assertEqual(im.size, (360, 640))
        self.assertTrue(all(f.suffix == ".jpg" for f in (Path("public") / rel).iterdir()))

    def test_the_strongest_second_is_inside_the_recording_and_its_poster_is_that_frame(self):
        at = picks.strongest(CLIP)
        self.assertTrue(0 <= at <= picks.seconds_of(CLIP) - 1.0)
        with mock.patch.object(picks, "PHOTOS", self.dir / "photos"):
            p = picks.poster(CLIP, at)
            again = picks.poster(CLIP, at)
            cover = picks.poster(CLIP)
        self.assertEqual(p, again)
        self.assertNotEqual(p, cover)
        r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width", "-of", "csv=p=0", p],
                           capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "720")

    def test_a_clip_in_their_photo_folder_joins_the_pool_with_its_second(self):
        from PIL import Image
        folder = self.dir / "named"
        folder.mkdir()
        named = []
        for i, rgb in enumerate(((180, 120, 90), (90, 140, 170), (200, 170, 60))):
            f = folder / f"next-{i}.jpg"
            Image.new("RGB", (400, 500), rgb).save(f)
            named.append({"ts": 1792698717 + i, "caption": "", "media": [str(f)]})
        named.append({"ts": 1792698720, "caption": "", "media": [str(CLIP)]})
        _env.write_json("library.json", {"source": "photos", "grid": [], "posts": [], "stories": [], "facebook": [],
                                         "photos": named})
        with mock.patch.object(_env, "enter_run", lambda new=False: None), \
                mock.patch.object(sys, "argv", ["picks.py"]), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(picks.main(), 0)
        pool = json.loads(Path("picks.json").read_text())["pool"]
        row = next(r for r in pool if r["src"] == str(CLIP))
        self.assertEqual(row["from"], picks.strongest(CLIP))
        self.assertTrue(row["photo"].endswith(".jpg"))
        self.assertFalse(any("from" in r for r in pool if r["src"] != str(CLIP)))


if __name__ == "__main__":
    unittest.main()
