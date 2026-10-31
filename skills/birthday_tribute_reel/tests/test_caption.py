"""A moment's words read at one size on a phone in every look: on the reel the caption's capitals stand at least
CAPTION_CAP px tall (times the shrink the card's whole block takes to fit, read off its name against HEAD), so a look
whose text face has short capitals (the analog look's typewriter) sets its words larger than the floor, and a look whose
capitals are tall keeps its CAPTION size.

    python3 -I -m unittest discover -s S/tests -p test_caption.py
"""
import sys
import unittest
from pathlib import Path

S = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S / "scripts"))
import compose  # noqa: E402
import wall  # noqa: E402

BEAT = {"form": "moment", "name": "ramen night at dani's", "words": "she made enough for twelve", "voice": "mine",
        "talk": []}
WISH = {"name": "dani", "number": "30", "kind": "birthday"}
LOOKS = ("scrapbook", "analog-home-movie", "editorial-quiet", "kinetic-type", "swiss-grid", "cinematic-letterbox")


def card(style, fmt="reel"):
    """(shrink, words): one moment card laid out in `style` on `fmt` over a level edge low in the frame; the shrink its
    block took to fit (its name's size against HEAD) and its words lines."""
    wall.use(style)
    f = compose.Frame(fmt)
    head, lines = wall.card_lines(f, wall.Edge(f.W, f.H * 0.6, 0), BEAT, WISH, fmt, side="over")
    return head[0]["size"] / wall.HEAD[fmt], [ln for ln in lines if ln["name"].startswith("words")]


class Caption(unittest.TestCase):
    def test_every_looks_words_stand_at_least_the_caption_cap_on_the_reel(self):
        for style in LOOKS:
            k, got = card(style)
            self.assertTrue(got, style)
            for ln in got:
                self.assertGreaterEqual(wall.cap(ln["face"]) * ln["size"], 34 * k - 0.5,
                                        f"{style}: '{ln['text']}' capitals {wall.cap(ln['face']) * ln['size']:.1f} px")

    def test_a_look_whose_capitals_are_tall_keeps_its_caption_size(self):
        for style in ("scrapbook", "kinetic-type"):
            k, got = card(style)
            self.assertEqual({ln["size"] for ln in got}, {round(wall.CAPTION["reel"] * k)}, style)


if __name__ == "__main__":
    unittest.main()
