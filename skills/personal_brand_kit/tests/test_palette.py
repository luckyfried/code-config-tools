"""palette.py turns a style card's palette rule and the person's own feed colors into a board's colors: every rule a
card may name gives the six roles, and mono-plus-one is an off-white paper, a near-black ink in the feed's own hues,
and one accent that reads on the paper."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import fixture  # noqa: E402
import palette  # noqa: E402

FEED = [c["hex"].lower() for c in fixture.FEED]


class MonoPlusOne(unittest.TestCase):
    def setUp(self):
        self.roles = palette.palette_of({"rule": "mono-plus-one"}, FEED)["roles"]

    def test_the_paper_is_off_white_in_the_feeds_lightest_hue(self):
        h, l, s = palette.hls(palette.hex_rgb(self.roles["paper"]))
        self.assertAlmostEqual(l, 0.94, delta=0.01)
        self.assertLessEqual(s, 0.15)  # 0.12, as near as a hex can hold it at this lightness
        self.assertNotEqual(self.roles["paper"], "#ffffff")
        self.assertEqual(self.roles["bg"], self.roles["paper"])

    def test_the_ink_is_near_black(self):
        self.assertLess(palette.lum(palette.hex_rgb(self.roles["ink"])), 0.01)
        self.assertNotEqual(self.roles["ink"], "#000000")

    def test_the_one_accent_reads_on_the_paper(self):
        self.assertGreaterEqual(palette.contrast(palette.hex_rgb(self.roles["accent"]), palette.hex_rgb(self.roles["paper"])), 3.0)
        self.assertEqual(self.roles["accent"], self.roles["accent2"])


class EveryRule(unittest.TestCase):
    def test_every_rule_gives_the_six_roles_as_hexes(self):
        rules = [{"rule": "photos"}, {"rule": "photos-plus-accent"}, {"rule": "two-inks", "contrast": 4.5}, {"rule": "mono-plus-one"},
                 {"rule": "fixed", "warm": dict.fromkeys(palette.ROLES, "#f0e6d8"), "cool": dict.fromkeys(palette.ROLES, "#dfe6ee")}]
        for rule in rules:
            roles = palette.palette_of(rule, FEED)["roles"]
            self.assertEqual(set(roles), set(palette.ROLES), rule)
            self.assertTrue(all(len(v) == 7 and v.startswith("#") for v in roles.values()), (rule, roles))

    def test_an_unknown_rule_refuses(self):
        with self.assertRaises(SystemExit):
            palette.palette_of({"rule": "rainbow"}, FEED)

    def test_without_feed_colors_the_neutral_four_stand_in(self):
        self.assertEqual(palette.swatches_of({}, None), list(palette.NEUTRAL))
        self.assertEqual(palette.swatches_of({}, {"feed": fixture.FEED}), FEED)


if __name__ == "__main__":
    unittest.main()
