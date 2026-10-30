"""The grade matches every photograph to one light before the film's grade: a white sun or lamp stays white in a photo
with a strong cast, the set's saturations end closer together than they began, a black-and-white photograph is toned
in the palette's hue while a colored one is left as it is, and the film's grade never adds saturation past the
photographs' own and, with a gray palette, leaves a gray gray and a clipped yellow as yellow as it came.

    python3 -I -m unittest discover -s S/tests -p 'test_grade.py'
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "scripts"))
import _env  # noqa: E402

grade = None
TMP = None


def setUpModule():
    global grade, TMP
    TMP = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
    with mock.patch.object(_env, "_RUN", Path(TMP.name)):  # grade.py names the run's folders on import
        import grade as g
    grade = g


def tearDownModule():
    TMP.cleanup()


def photo(name, ground, disk=None):
    """A drawn photograph: one ground color, with a disk of `disk` at its center when given."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 300), ground)
    if disk:
        ImageDraw.Draw(im).ellipse((160, 110, 240, 190), fill=disk)
    path = Path(TMP.name) / name
    im.save(path)
    return path


def matched(src):
    from PIL import Image
    out = src.with_name(f"matched-{src.name}")
    grade.match_light(src, out)
    return Image.open(out).convert("RGB")


def saturation(im):
    from PIL import ImageStat
    return ImageStat.Stat(im.convert("HSV")).mean[1] / 255


class MatchLight(unittest.TestCase):
    def test_a_white_sun_in_a_warm_photograph_stays_white(self):
        for ground in ((200, 130, 60), (60, 120, 210), (90, 170, 70)):
            with self.subTest(ground):
                r, g, b = matched(photo(f"sun-{ground[0]}.png", ground, (255, 255, 255))).getpixel((200, 150))
                self.assertLessEqual(max(r, g, b) - min(r, g, b), 6, (r, g, b))
                self.assertGreaterEqual(min(r, g, b), 245, (r, g, b))

    def test_a_sunset_keeps_the_gold_it_was_taken_in_and_a_camera_tint_is_taken_out(self):
        from PIL import ImageStat
        warm = lambda im: (lambda m: m[0] / m[2])(ImageStat.Stat(im).mean)
        sunset = photo("sunset.png", (150, 110, 78))
        self.assertGreater(warm(matched(sunset)), 1.45, "the sunset stays gold")
        tint = photo("tint.png", (128, 120, 112))
        self.assertLess(warm(matched(tint)), 128 / 112 - 0.03, "a camera's warm tint is pulled toward gray")

    def test_the_sets_saturations_end_closer_together_than_they_began(self):
        from PIL import Image
        loud, quiet = photo("stock-sky.png", (30, 110, 250)), photo("overcast.png", (140, 128, 118))
        before = [saturation(Image.open(p)) for p in (loud, quiet)]
        after = [saturation(matched(p)) for p in (loud, quiet)]
        self.assertLess(after[0], before[0] * 0.8, "a stock-blue sky calms")
        self.assertLess(after[0] / after[1], before[0] / before[1], (before, after))


    def test_a_black_and_white_photograph_is_toned_in_the_palettes_hue_and_a_colored_one_is_not(self):
        from PIL import Image
        warm = {"palette": {"together": [{"hex": "#403731", "share": 0.5}, {"hex": "#af9c7a", "share": 0.3},
                                         {"hex": "#cd2f3b", "share": 0.2}]}}
        tone = grade.recipe(warm)["tone"]
        ramp = Image.new("RGB", (256, 40))
        ramp.putdata([(x, x, x) for _ in range(40) for x in range(256)])
        gray = Path(TMP.name) / "ramp.png"
        ramp.save(gray)
        out = gray.with_name("toned-ramp.png")
        grade.match_light(gray, out, tone)
        toned = Image.open(out).convert("RGB")
        r, g, b = toned.getpixel((128, 20))
        self.assertGreater(r, b + 15, ("the mids take the palette's warm hue", (r, g, b)))
        for x in (2, 253):
            px = toned.getpixel((x, 20))
            self.assertLessEqual(max(px) - min(px), 4, ("black and white stay neutral", x, px))
        sky = photo("sky.png", (70, 120, 200), (230, 200, 150))
        with_tone, without = sky.with_name("sky-tone.png"), sky.with_name("sky-plain.png")
        grade.match_light(sky, with_tone, tone)
        grade.match_light(sky, without)
        self.assertEqual(list(Image.open(with_tone).getdata()), list(Image.open(without).getdata()))


class Recipe(unittest.TestCase):
    def test_the_films_grade_never_adds_saturation_past_the_photographs_own(self):
        loud = {"palette": {"together": [{"hex": h, "share": 1} for h in ("#ff1010", "#10ff10", "#1010ff")]}}
        gray = {"palette": {"together": [{"hex": h, "share": 1} for h in ("#808080", "#a0a0a0")]}}
        for taste in (loud, gray, {}):
            with self.subTest(taste):
                rr = float(grade.recipe(taste)["filter"].split("colorchannelmixer=rr=")[1].split(":")[0])
                sat = (rr - grade.LUMA[0]) / (1 - grade.LUMA[0])  # rr = 0.299 (1 - s) + s
                self.assertLessEqual(sat, 1.0)
                self.assertGreaterEqual(sat, 0.78 - 1e-3)

    def test_with_a_gray_palette_the_grade_leaves_a_gray_gray_and_a_clipped_yellow_no_greener(self):
        import subprocess
        from PIL import Image
        ff = _env.tools().get("ffmpeg")
        if not ff:
            self.skipTest("no ffmpeg")
        colors = [(128, 128, 128), (200, 200, 200), (252, 252, 121), (255, 255, 172)]  # grays and clipped yellows
        src = Path(TMP.name) / "patches.png"
        im = Image.new("RGB", (8 * len(colors), 8))
        for i, c in enumerate(colors):
            im.paste(c, (8 * i, 0, 8 * i + 8, 8))
        im.save(src)
        gray = {"palette": {"together": [{"hex": h, "share": 1} for h in ("#404040", "#808080", "#e0e0e0")]}}
        out = src.with_name("patches-graded.png")
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(src), "-vf", grade.recipe(gray)["filter"], str(out)],
                       check=True)
        graded = Image.open(out).convert("RGB")
        for i, c in enumerate(colors):
            r, g, b = graded.getpixel((8 * i + 4, 4))
            with self.subTest(color=c, graded=(r, g, b)):
                self.assertLessEqual(abs(g - r), 1, "red and green stay level")
                if c[1] == c[2]:
                    self.assertLessEqual(max(r, g, b) - min(r, g, b), 1, "a gray stays gray")

    def test_the_graded_jpeg_keeps_a_clipped_yellows_red_and_green_where_the_grade_left_them(self):
        from PIL import Image
        if not _env.tools().get("ffmpeg"):
            self.skipTest("no ffmpeg")
        # grays and clipped yellows, and blues that mirror the yellows so the photo's mean is gray
        colors = [(128, 128, 128), (200, 200, 200), (252, 252, 121), (255, 255, 172), (121, 121, 252), (172, 172, 255)]
        src = Path(TMP.name) / "write.jpg"
        im = Image.new("RGB", (16 * len(colors), 16))
        for i, c in enumerate(colors):
            im.paste(c, (16 * i, 0, 16 * i + 16, 16))
        im.save(src, quality=100, subsampling=0)
        matched, out = src.with_name("write-matched.png"), src.with_name("write-graded.jpg")
        grade.match_light(src, matched)
        ok, err = grade.grade_file(src, out, "null")  # the light matched and written, no grade between
        self.assertTrue(ok, err)
        want, got = Image.open(matched).convert("RGB"), Image.open(out).convert("RGB")
        for i, c in enumerate(colors):
            (r0, g0, _), (r, g, _) = want.getpixel((16 * i + 8, 8)), got.getpixel((16 * i + 8, 8))
            with self.subTest(color=c, matched=(r0, g0), written=(r, g)):
                self.assertLessEqual(abs((g - r) - (g0 - r0)), 1, "green gains nothing on red in the write")


if __name__ == "__main__":
    unittest.main()
