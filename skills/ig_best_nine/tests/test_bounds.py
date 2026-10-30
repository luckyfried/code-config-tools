"""The bounds check on the bakery's boards: clean boards pass in every style and format at every length the kit
makes, and every overlap or crop found by eye in the reviewed films is a case the check fails on.

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
import story  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402

BOOK = json.loads((KIT / "tests" / "cornerloaf.json").read_text())


def posts():
    return [dict(p) for p in BOOK["posts"]]


def board(style=compose.TRIO[0], fmt="reel", seconds=None):
    return storyboard.board_for(style, posts(), fmt, storyboard.words_default(BOOK["year"]), BOOK["handle"], BOOK["year"], None,
                                seconds)["board"]


def beat(b, bid):
    return next(x for x in b["beats"] if x["id"] == bid)


def first(b, kind, *forms):
    """The first beat holding a layer of `kind` (of one of `forms` when named) and that layer."""
    for x in b["beats"]:
        for L in x["layers"]:
            if L["kind"] == kind and (not forms or x["form"] in forms):
                return x, L
    raise LookupError(kind)


class Clean(unittest.TestCase):
    def test_every_style_format_and_length_is_clean(self):
        for style in compose.TRIO:
            for fmt in compose.FORMATS:
                for seconds in (*storyboard.LENGTH, storyboard.SECONDS):
                    with self.subTest(style=style, fmt=fmt, seconds=seconds):
                        self.assertEqual(bounds.check(board(style, fmt, seconds)), [])


class EyeCases(unittest.TestCase):
    """Each case is a clean board with one defect put back, the way it was seen in a reviewed frame."""

    def fails(self, b, *words):
        found = bounds.check(b)
        self.assertTrue(any(all(w in f for w in words) for f in found), f"no finding with {words}: {found[:6]}")

    def words_on_ground(self, b):
        for x in b["beats"]:
            for L in x["layers"]:
                if L["kind"] == "Words" and not L.get("over") and x["form"] == "photo" and len(L["lines"]) > 1:
                    return x, L
        raise LookupError("no ground words")

    def test_a_line_past_the_edge_leaves_the_safe_area(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                b = board(style)
                x, L = self.words_on_ground(b)
                L["lines"][-1]["x"] = b["format"]["width"] - 20
                self.fails(b, x["id"], "leaves the safe area")

    def test_two_lines_set_on_one_place_overlap(self):
        b = board()
        x, L = self.words_on_ground(b)
        L["lines"][1]["y"] = L["lines"][0]["y"]
        self.fails(b, x["id"], "overlap")

    def test_ground_words_moved_onto_their_photograph_run_onto_it(self):
        b = board()
        x, L = self.words_on_ground(b)
        photo = next(P for P in x["layers"] if P["kind"] == "Photo")
        win = photo.get("window") or photo["box"]
        dy = win[1] + win[3] / 2 - L["lines"][0]["y"]
        dx = max(win[0], 0) + 40 - L["lines"][0]["x"]
        for ln in L["lines"]:
            ln["y"] += dy
            ln["x"] += dx
        self.fails(b, x["id"], "runs onto the photograph")

    def test_words_over_a_photograph_with_the_shade_taken_away_have_none_under_them(self):
        b = board()
        x, _ = first(b, "Shade", "photo")
        x["layers"] = [L for L in x["layers"] if L["kind"] != "Shade"]
        self.fails(b, x["id"], "no shade under it")

    def test_a_display_line_under_the_floor(self):
        b = board()
        x, L = self.words_on_ground(b)
        ln = next(ln for ln in L["lines"] if ln["face"] == "display")
        ln["size"] = story.FLOOR["reel"] - 10
        self.fails(b, x["id"], "under the", "floor")

    def test_a_subject_cropped_out_of_its_box(self):
        b = board()
        x, P = first(b, "Photo", "photo")
        P["focus"] = [P["uv"][2] + 0.05, P["uv"][3] + 0.05]
        self.fails(b, x["id"], "cropped out of its box")

    def test_a_grid_tile_off_the_frame_and_two_that_meet(self):
        b = board()
        tiles = [L for L in beat(b, "grid")["layers"] if L["kind"] == "Slice"]
        tiles[0]["box"][0] = -50
        tiles[2]["box"] = list(tiles[1]["box"])
        self.fails(b, "grid", "leaves the frame")
        self.fails(b, "grid", "two grid tiles meet")


class Timing(unittest.TestCase):
    def test_every_layer_starts_inside_its_shot(self):
        for style in compose.TRIO:
            b = board(style)
            for x in b["beats"][1:]:
                beats = x["frames"] / compose.pulse_of(b["bpm"])
                for L in x["layers"]:
                    with self.subTest(style=style, beat=x["id"], kind=L["kind"]):
                        self.assertTrue(0 <= L.get("at", 0) < beats, f"{x['id']} {L['kind']} starts at beat {L.get('at')} of {beats:.2f}")

    def test_the_grid_and_the_closer_start_on_a_beat(self):
        for seconds in (*storyboard.LENGTH, 33):
            b = board(seconds=seconds)
            f = 0
            for x in b["beats"]:
                if x["id"] in ("grid", "closer"):
                    with self.subTest(seconds=seconds, beat=x["id"]):
                        at = f / compose.pulse_of(b["bpm"])
                        self.assertAlmostEqual(at, round(at), delta=0.5 / compose.pulse_of(b["bpm"]) + 1e-9)
                f += x["frames"]

    def test_every_asked_length_fits_at_a_multiple_of_every_heard_tempo(self):
        for seconds in storyboard.LENGTH:
            self.assertTrue(story.fits(posts(), seconds, story.BPM), f"{seconds} s at {story.BPM} bpm")
            # music.py hears a tempo between 70 and 140 bpm; snap takes its half, whole or double
            for bpm in range(70, 141):
                with self.subTest(seconds=seconds, bpm=bpm):
                    self.assertTrue(any(story.fits(posts(), seconds, bpm * k) for k in (0.5, 1, 2)), f"no multiple of {bpm} bpm fits {seconds} s")


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
