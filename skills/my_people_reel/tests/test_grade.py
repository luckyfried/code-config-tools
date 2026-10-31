"""One grade before anything is placed: cast.py match moves every photograph most of the way to the set's black and
white points and its color cast most of the way to the palette's warmth, so a washed-out photograph with a cyan cast
reads in the same light as a crisp neutral one.

    python3 -I -m unittest discover -s S/tests -p test_grade.py
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageCms, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cast  # noqa: E402


def ends(im):
    """The 2nd and 98th percentiles of a photograph's Lab lightness, in bytes."""
    tr = ImageCms.buildTransformFromOpenProfiles(ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB"), "RGB", "LAB")
    lab = ImageCms.applyTransform(im.convert("RGB"), tr)
    h, acc, out = lab.getchannel(0).histogram(), 0, []
    for v, c in enumerate(h):
        acc += c
        while len(out) < 2 and acc >= sum(h) * (0.02, 0.98)[len(out)]:
            out.append(v)
    return out, [ImageStat.Stat(lab.getchannel(k)).mean[0] for k in (1, 2)]


class Grade(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d)
        here = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, here)

    def test_every_photograph_reads_in_one_grade(self):
        ramp = Image.linear_gradient("L").resize((400, 600))
        crisp = Image.merge("RGB", [ramp.point(lambda v: 8 + v * 240 // 255)] * 3)
        dull = ramp.point(lambda v: 75 + v * 110 // 255)
        cyan = Image.merge("RGB", (dull.point(lambda v: max(0, v - 40)), dull, dull.point(lambda v: min(255, v + 10))))
        crisp.save("crisp.jpg")
        cyan.save("cyan.jpg")
        Path("cast.json").write_text(json.dumps({"people": {
            "ana.costa": [{"file": "crisp.jpg", "point": [0.5, 0.4]}], "ben.okafor": [{"file": "cyan.jpg", "point": [0.5, 0.4]}]}}))
        with contextlib.redirect_stdout(io.StringIO()):
            cast.cmd_match(argparse.Namespace(cast=None))
        (a0, a1), a_ab = ends(Image.open("public/matched/ana.costa-0.jpg"))
        (b0, b1), b_ab = ends(Image.open("public/matched/ben.okafor-0.jpg"))
        self.assertLess(abs(a0 - b0), 10, (a0, b0))
        self.assertLess(abs(a1 - b1), 10, (a1, b1))
        self.assertLess(max(abs(x - y) for x, y in zip(a_ab, b_ab)), 2, (a_ab, b_ab))

    def test_a_trimmed_photograph_leaves_the_marked_edge_out_and_its_points_stay_on_the_person(self):
        """`trim` keeps the part of a photograph inside its box (a photographer's mark at its edge left out): the
        matched picture is that part alone, and a point given on the whole photograph lands on the same place in it."""
        import layout
        Image.linear_gradient("L").resize((400, 300)).convert("RGB").save("wide.jpg")
        Path("cast.json").write_text(json.dumps({"people": {"ana.costa": [
            {"file": "wide.jpg", "point": [0.5, 0.425], "face": [0.4, 0.2, 0.6, 0.6], "trim": [0.0, 0.0, 1.0, 0.85]}]}}))
        with contextlib.redirect_stdout(io.StringIO()):
            cast.cmd_match(argparse.Namespace(cast=None))
        aspects = json.loads(Path("public/matched/aspects.json").read_text())
        v0, v1 = aspects["ana.costa-0"]["band"]
        W, H = Image.open("public/matched/ana.costa-0.jpg").size
        self.assertAlmostEqual((v1 - v0) * H / W, 255 / 400, delta=0.01)
        row = layout.Photos(json.loads(Path("cast.json").read_text()), "public").cast["people"]["ana.costa"][0]
        self.assertAlmostEqual(row["point"][1], v0 + 0.5 * (v1 - v0), delta=0.002)
        self.assertAlmostEqual(row["face"][3], v0 + 0.6 / 0.85 * (v1 - v0), delta=0.002)


if __name__ == "__main__":
    unittest.main()
