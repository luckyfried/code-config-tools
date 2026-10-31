"""A moment from a reel plays its recorded clip on its photo beat: one shot the length of its beat, from the clip's
strongest second, without sound, under the move and the arrival the photograph would have had; a beat without a clip
is the beat it always was."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import fixture  # noqa: E402
import material  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402

TRAM = Path(__file__).resolve().parent / "fixtures" / "clip-tram.mp4"
# the moment whose photograph is a reel's clip: the best liked, the peak every look plays
REEL = fixture.MOMENTS[3][0]


def boards(clip):
    """{letter: {fmt: board}} for the fixture's run, with the moment REEL on the tram clip when `clip`, and the clip
    frames each board names, counted while the run is still there."""
    here = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
        fixture.make(d)
        os.chdir(d)
        try:
            if clip:
                st = _env.read_json("studio.json")
                best, seconds = material.strongest(TRAM)
                st["photos"][REEL]["clip"] = {"source": str(TRAM), "best": best, "seconds": seconds, "grade": "eq=saturation=1.0"}
                _env.write_json("studio.json", st)
            run = storyboard.Run()
            looks = {l: {fmt: storyboard.board_for(run, l, s, fmt)["board"] for fmt in compose.FORMATS}
                     for l, s in zip(compose.LETTERS, run.trio)}
            cut = {x["clip"]["dir"]: sorted(p.name for p in (material.PUB / x["clip"]["dir"]).glob("*.jpg"))
                   for b in (b for fmts in looks.values() for b in fmts.values()) for x in b["beats"] if x.get("clip")}
        finally:
            os.chdir(here)
    return looks, cut


@unittest.skipUnless(fixture.HAVE_PIL and TRAM.is_file(), "Pillow is not installed")
class Clips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plain, _ = boards(False)
        cls.clipped, cls.cut = boards(True)

    def test_the_strongest_second_leaves_the_clip_moving_to_the_beats_end(self):
        best, seconds = material.strongest(TRAM)
        self.assertAlmostEqual(seconds, 4.0, delta=0.1)
        self.assertLessEqual(best, seconds - min(material.LEAVE, seconds - 1))

    def test_a_clip_request_is_one_shot_the_length_of_its_beat(self):
        for fmts in self.clipped.values():
            for b in fmts.values():
                shots = [x for x in b["beats"] if x.get("clip")]
                self.assertEqual([x["id"] for x in shots if x["form"] == "photo"], [x["id"] for x in shots])
                self.assertEqual(len(shots), 1, [x["id"] for x in b["beats"]])
                x = shots[0]
                self.assertEqual(x["clip"]["hold"] + x["clip"]["frames"], x["frames"])
                self.assertEqual(x["clip"]["from"], material.strongest(TRAM)[0])
                names = self.cut[x["clip"]["dir"]]
                self.assertEqual(names, [f"{k:04d}.jpg" for k in range(1, x["clip"]["frames"] + 1)])
                clips = studio.props(b)["clips"]
                self.assertEqual([(c["beat"], c["from"], c["frames"], c["step"]) for c in clips],
                                 [(x["id"], round(x["start"] * x["pulse"]) + x["clip"]["hold"], x["clip"]["frames"], 1)])
                self.assertEqual(clips[0]["image"], x["picture"]["file"])

    def test_the_clip_takes_the_move_and_the_arrival_the_photograph_would_have_had(self):
        for l, fmts in self.clipped.items():
            for fmt, b in fmts.items():
                shot = next(x for x in b["beats"] if x.get("clip"))
                was = next(x for x in self.plain[l][fmt]["beats"] if x["id"] == shot["id"])
                self.assertEqual({k: v for k, v in shot.items() if k != "clip"}, was)

    def test_a_beat_without_a_clip_is_unchanged(self):
        for l, fmts in self.clipped.items():
            for fmt, b in fmts.items():
                rest = [x for x in b["beats"] if not x.get("clip")]
                self.assertEqual(rest, [x for x in self.plain[l][fmt]["beats"] if x["id"] in {y["id"] for y in rest}])
                self.assertNotIn("clips", studio.props(self.plain[l][fmt]))
                self.assertEqual(json.dumps(self.plain[l][fmt]["sound"]), json.dumps(b["sound"]))


if __name__ == "__main__":
    unittest.main()
