"""Their own recorded clips on photo beats: a stop the person filled with a clip they shot plays it as one shot the
length of its beat, cut from the clip's strongest second, without its sound, on the card its photograph would have
had; a beat without a clip is the beat it always was.

    python3 -I -m unittest discover -s S/tests -p test_clips.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import board_trip  # noqa: E402
import clips  # noqa: E402
import style  # noqa: E402
from test_looks import source  # noqa: E402

TRAM = KIT / "tests" / "fixtures" / "clip-tram.mp4"


def frames_of(folder):
    return sorted(Path(folder).glob("*.jpg"))


class TheirClip(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(__import__("shutil").rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        patch = mock.patch.object(_env, "read_json", return_value=None)
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_clip_request_is_one_shot_the_length_of_its_beat_from_the_clips_strongest_second(self):
        src = source()
        src["stops"][1]["clip"] = str(TRAM)
        for look in style.TRIO:
            b = board_trip.board(src, style.card(look))
            st, beat = b["route"]["stops"][1], b["beats"][1]
            c = next(c for c in b["clips"] if c["beat"] == beat["id"])
            self.assertEqual((c["role"], c["source"], c["prompt"]), ("their own clip", str(TRAM), None), look)
            self.assertEqual(c["window"], [st["at"], st["end"]], f"{look}: the clip plays over its beat, whole")
            self.assertEqual(beat["form"], "clip", look)
        at, n = clips.window({"bpm": b["bpm"]}, c)
        self.assertLessEqual(n, 4 * clips.FPS, "the fixture is long enough for one shot with no loop")
        Path("public/matched").mkdir(parents=True)
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-ss", "1", "-i", str(TRAM), "-frames:v", "1", "-vf", "scale=360:640",
                        "public/matched/1.jpg"], check=True)
        start = clips.strongest(TRAM, n)
        self.assertLessEqual(start + n / clips.FPS, 4.0 + 1e-6, "the shot ends inside the clip")
        dst, got, err = clips.conform(c["id"], TRAM, "matched/1.jpg", n, "null", start)
        self.assertEqual((got, err), (n, ""), "one frame of the clip for every frame of its beat")
        self.assertEqual(len(frames_of(dst)), n)

    def test_the_strongest_second_is_where_the_clip_moves_the_most_and_the_shot_fits_inside_it(self):
        # two still seconds, one that moves, one still: the shot starts on the moving second when it fits after it
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=64x64:r=30:d=2",
                        "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=1", "-f", "lavfi", "-i", "color=c=gray:s=64x64:r=30:d=1",
                        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", "moves.mp4"], check=True)
        self.assertEqual(clips.strongest("moves.mp4", 15), 2.0)
        self.assertEqual(clips.strongest("moves.mp4", 60), 2.0)
        self.assertAlmostEqual(clips.strongest("moves.mp4", 100), 20 / 30, places=3, msg="moved earlier so the shot ends inside the clip")
        self.assertEqual(clips.strongest("moves.mp4", 150), 0.0, "a clip shorter than its shot plays from its start")

    def test_a_beat_without_a_clip_is_unchanged_and_asks_for_a_generated_clip(self):
        src = source()
        src["stops"][1]["clip"] = str(TRAM)
        still = source()
        still["stops"][1]["clip"] = False
        for look in style.TRIO:
            c = style.card(look)
            a, z = board_trip.board(src, c), board_trip.board(still, c)
            self.assertEqual([x for i, x in enumerate(a["beats"]) if i != 1], [y for i, y in enumerate(z["beats"]) if i != 1], look)
            ca, cz = ({c["beat"]: c for c in b["clips"]} for b in (a, z))
            for beat in set(ca) - {"stop-2"}:
                self.assertEqual(ca[beat]["window"], cz[beat]["window"], (look, beat))
            self.assertEqual(cz["stop-2"]["role"], "the photograph brought to life", look)
            self.assertNotIn("source", cz["stop-2"], look)


if __name__ == "__main__":
    unittest.main()
