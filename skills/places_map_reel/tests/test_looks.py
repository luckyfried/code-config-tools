"""The run's three looks: research.py leans to one of the kit's three with its reason, the boards take the look the
person named and the two of the kit's three most unlike it, and the map's colors keep the handle under the hook's
title readable: the accent where it reads on both the land and the sea, else the words' own color.

    python3 -I -m unittest discover -s S/tests -p test_looks.py
"""
import collections
import sys
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive  # noqa: E402
import look  # noqa: E402
import research  # noqa: E402
import storyboard  # noqa: E402


def contrast(a, b):
    return board_drive._contrast(board_drive.hex_rgb(a), board_drive.hex_rgb(b))


class TheLean(unittest.TestCase):
    def lean(self, themes=(), emoji=0.2, shot=4.0):
        return research.lean(collections.Counter(dict(themes)), {"emoji_per_caption": emoji}, {"avg_shot_seconds": shot})

    def test_research_leans_to_one_of_the_kits_looks_and_says_why(self):
        for got, style, words in ((self.lean({"film photography": 3}), "cinematic-letterbox", "film photography"),
                                  (self.lean(emoji=1.5), "swiss-grid", "emoji"),
                                  (self.lean(shot=0.9), "swiss-grid", "fast reels"),
                                  (self.lean({"film photography": 2}), "scrapbook", "quiet captions")):
            self.assertEqual(got["style"], style, got)
            self.assertIn(words, got["why"])
            self.assertIn(got["style"], look.TRIO)
            look.card(got["style"])

    def test_film_photography_outweighs_fast_cuts(self):
        self.assertEqual(self.lean({"film photography": 4}, emoji=2, shot=0.5)["style"], "cinematic-letterbox")

    def test_a_year_with_no_reels_reads_as_slow(self):
        got = research.lean(collections.Counter(), {}, {})
        self.assertEqual(got["style"], "scrapbook")


class TheThreeBoards(unittest.TestCase):
    def test_with_no_look_named_the_boards_are_the_kits_three(self):
        self.assertEqual(look.trio_for(None), look.TRIO)
        with mock.patch.object(storyboard._env, "read_json", return_value=None):
            self.assertEqual(storyboard.styles(), list(look.TRIO))

    def test_a_named_look_takes_the_two_of_the_kits_three_that_share_the_fewest_axes_with_it(self):
        # kinetic-type shares an axis with swiss-grid and none with the other two
        self.assertEqual(len(look.shared_axes("kinetic-type", "swiss-grid")), 1)
        self.assertEqual(look.trio_for("kinetic-type"), ("kinetic-type", "cinematic-letterbox", "scrapbook"))
        # analog-home-movie shares an axis with cinematic-letterbox and none with the other two
        self.assertEqual(len(look.shared_axes("analog-home-movie", "cinematic-letterbox")), 1)
        self.assertEqual(look.trio_for("analog-home-movie"), ("analog-home-movie", "swiss-grid", "scrapbook"))
        with mock.patch.object(storyboard._env, "read_json", return_value={"style": "kinetic-type"}):
            self.assertEqual(storyboard.styles(), ["kinetic-type", "cinematic-letterbox", "scrapbook"])

    def test_a_named_look_of_the_kits_three_takes_the_other_two_in_order(self):
        self.assertEqual(look.trio_for("scrapbook"), ("scrapbook", "swiss-grid", "cinematic-letterbox"))

    def test_every_style_names_itself_and_two_more_of_the_kits_three(self):
        for s in look.styles():
            trio = look.trio_for(s)
            self.assertEqual(trio[0], s)
            self.assertEqual(len(set(trio)), 3, trio)
            self.assertTrue(set(trio[1:]) <= set(look.TRIO), trio)

    def test_a_look_the_kit_does_not_have_is_refused_by_name(self):
        with self.assertRaises(SystemExit) as e:
            look.trio_for("vaporwave")
        self.assertIn("no style named 'vaporwave'", str(e.exception))


class TheHandlesColor(unittest.TestCase):
    LIGHT = {"bg": "#f3eee4", "paper": "#ffffff", "ink": "#111111", "accent2": "#7fb3d5", "muted": "#888888"}

    def test_an_accent_that_reads_on_the_land_and_the_sea_marks_the_handle(self):
        m = board_drive.map_colors({**self.LIGHT, "accent": "#1a237e"})
        self.assertEqual(m["mark"], "#1a237e")
        self.assertGreaterEqual(min(contrast(m["mark"], m["land"]), contrast(m["mark"], m["sea"])), 3)

    def test_an_accent_under_3_on_the_land_or_the_sea_falls_back_to_the_words_color(self):
        # the yellow reads under 3 on both; the red reads 5.4 on the land and 2.4 on the sea
        for accent in ("#ffd84d", "#c0392b"):
            m = board_drive.map_colors({**self.LIGHT, "accent": accent})
            self.assertLess(min(contrast(accent, m["land"]), contrast(accent, m["sea"])), 3)
            self.assertEqual(m["mark"], m["over"], m)
            self.assertEqual(m["over"], "#111111")

    def test_on_a_dark_ground_a_dim_accent_falls_back_to_the_words_color(self):
        m = board_drive.map_colors({"bg": "#14161c", "paper": "#f3eee4", "ink": "#f3eee4", "accent": "#3a3f8f",
                                    "accent2": "#2e7d6b", "muted": "#5a5f6a"})
        self.assertEqual(m["mark"], m["over"])
        self.assertEqual(m["over"], "#f3eee4")


if __name__ == "__main__":
    unittest.main()
