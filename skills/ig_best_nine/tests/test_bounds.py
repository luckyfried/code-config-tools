"""The bounds check on the bakery's boards: clean boards pass in every tone, format and count of posts, and every
overlap or crop found by eye in the reviewed films is a case the check fails on.

    python3 -I -m unittest discover -s S/tests
"""
import json
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import bounds  # noqa: E402
import compose  # noqa: E402
import picks  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
from tones import drive  # noqa: E402

BOOK = json.loads((KIT / "tests" / "cornerloaf.json").read_text())


def board(tone, fmt="reel", n=9):
    posts = [dict(p) for p in BOOK["posts"][:n]]
    b = storyboard.board_for(tone, posts, fmt, storyboard.words_default(BOOK["year"])[tone], BOOK["handle"], BOOK["year"])["board"]
    b.setdefault("tone", tone)
    return b


def beat(b, bid):
    return next(i for i, x in enumerate(b["beats"]) if x["id"] == bid)


def layers(b, i, kind):
    return [L for L in b["beats"][i]["layers"] if L["kind"] == kind]


def items(b, i, kind):
    return [e for e in bounds.Shot(b, i).items if e["kind"] == kind]


class Clean(unittest.TestCase):
    def test_every_tone_format_and_count_is_clean(self):
        for tone in storyboard.TONES:
            for fmt in compose.FORMATS:
                for n in range(1, 10):
                    with self.subTest(tone=tone, fmt=fmt, n=n):
                        self.assertEqual(bounds.check(board(tone, fmt, n)), [])


class EyeCases(unittest.TestCase):
    """Each case is a clean board with one defect put back, the way it was seen in a reviewed frame."""

    def fails(self, b, *words):
        found = bounds.check(b)
        self.assertTrue(any(all(w in f for w in words) for f in found), f"no finding with {words}: {found[:6]}")

    def test_drive_count_over_the_edge_onto_its_photograph(self):
        b = board("drive")
        num = layers(b, beat(b, "piece-4"), "Words")[0]["lines"][0]
        num["y"] += 120
        num["pivot"][1] += 120
        self.fails(b, "piece-4", "crosses the cut onto its photograph")

    def test_drive_turned_caption_past_the_safe_area(self):
        b = board("drive")
        cap = layers(b, beat(b, "piece-4"), "Words")[1]["lines"][-1]
        x = b["format"]["width"] - 110 - compose.text_width(b["system"], cap)
        cap.update(x=x, rotate=-8, pivot=[x, cap["y"]])
        self.fails(b, "piece-4", "leaves the safe area")

    def test_drive_count_into_a_bar(self):
        b = board("drive")
        i = beat(b, "nine")
        bar = layers(b, i, "Bars")[0]["bars"][1]
        bar[2] += 200
        self.fails(b, "nine", "runs into a bar")

    def test_drive_closer_slice_under_the_floor(self):
        b = board("drive")
        poly = layers(b, beat(b, "closer"), "Slice")[0]["poly"]
        poly[2][1] = poly[3][1] = 180
        self.fails(b, "closer", "on its short side, under 240")

    def test_drive_closer_count_onto_a_slice(self):
        b = board("drive")
        i = beat(b, "closer")
        num = layers(b, i, "Words")[0]["lines"][0]
        poly = layers(b, i, "Slice")[0]["poly"]
        dy = (poly[0][1] + poly[3][1]) / 2 + 60 - num["y"]
        num["y"] += dy
        if num.get("pivot"):
            num["pivot"][1] += dy
        self.fails(b, "closer", "runs onto photograph")


class DriveTiming(unittest.TestCase):
    def test_every_move_after_the_hook_starts_inside_its_shot(self):
        b = board("drive")
        for beat in b["beats"][1:]:
            beats = beat["frames"] / compose.pulse_of(b["bpm"])
            for L in beat["layers"]:
                with self.subTest(beat=beat["id"], kind=L["kind"]):
                    self.assertTrue(0 <= L["at"] < beats, f"{beat['id']} {L['kind']} starts at beat {L['at']} of {beats:.2f}")

    def test_the_run_fills_whole_bars(self):
        for n in range(1, 10):
            with self.subTest(n=n):
                self.assertEqual(sum(drive.run_beats(n)) % 4, 0)

    def test_the_counts_run_down_from_the_lowest_rank_to_the_top_post(self):
        for n in (3, 9):
            with self.subTest(n=n):
                b = board("drive", n=n)
                ids = [x["id"] for x in b["beats"] if x["id"].startswith("piece-")]
                self.assertEqual(ids, [f"piece-{r}" for r in range(n, 0, -1)])

    def test_nine_posts_fit_the_band_at_a_multiple_of_every_heard_tempo(self):
        beats = drive.HOOK_BEATS + sum(drive.run_beats(9)) + drive.NINE_BEATS + drive.CLOSER_BEATS
        lo, hi = storyboard.length_band(9)
        self.assertTrue(lo <= beats * 60 / drive.BPM <= hi, f"{beats} beats at {drive.BPM} bpm")
        # music.py hears a tempo between 70 and 140 bpm; snap takes its half, whole or double
        for bpm in range(70, 141):
            with self.subTest(bpm=bpm):
                self.assertTrue(any(lo <= beats * 60 / (bpm * k) <= hi for k in (0.5, 1, 2)), f"{beats} beats at {bpm} bpm")


class DriveField(unittest.TestCase):
    def field(self, rgb):
        import os
        import tempfile
        from PIL import Image
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                Path("public").mkdir()
                Image.new("RGB", (300, 300), rgb).save("public/p.png")
                compose.pixels.cache_clear()
                frame = compose.Frame("reel")
                edge = drive.Edge(frame, drive.EDGE["reel"]["count"], 0)
                return drive.field_for(drive.sys_(), frame, {"file": "p.png", "aspect": 1.0, "focus": [0.5, 0.5]}, edge)
            finally:
                os.chdir(here)
                compose.pixels.cache_clear()

    def test_a_picture_the_paper_colour_takes_the_accent_field(self):
        self.assertEqual(self.field((236, 230, 220)), "accent")

    def test_a_picture_apart_from_the_paper_keeps_the_paper(self):
        self.assertEqual(self.field((70, 50, 30)), "paper")


class QuietSeconds(unittest.TestCase):
    def test_the_quiet_seconds_are_figures(self):
        r = studio.under_half([3, 0.4, 0.3, 4, 0.2, 5])
        self.assertEqual(r, {"seconds_under_half": [2, 3, 5], "longest_run_under_half": 2})


class Crop(unittest.TestCase):
    def test_square_crop_stays_inside_and_centres_on_the_focus(self):
        self.assertEqual(picks.square_crop(0.75, [0.5, 0.5]), [0.125, 0.0, 0.75])
        self.assertEqual(picks.square_crop(0.75, [0.95, 0.5]), [0.25, 0.0, 0.75])
        self.assertEqual(picks.square_crop(1.3333, [0.5, 0.1]), [0.0, 0.0, 1.0])
        self.assertEqual(picks.square_crop(1.0, [0.3, 0.7]), [0.0, 0.0, 1.0])

    def test_focus_finds_the_subject(self):
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (400, 300), (200, 196, 190))
        d = ImageDraw.Draw(im)
        for k in range(12):
            d.ellipse((60 + k * 4, 50 + k * 3, 140 - k * 2, 120 - k * 2), outline=(150 + k * 8, 40, 20), width=2)
        u, v = picks.focus_of(im)
        self.assertLess(u, 0.45)
        self.assertLess(v, 0.45)


if __name__ == "__main__":
    unittest.main()
