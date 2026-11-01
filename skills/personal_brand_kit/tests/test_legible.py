"""Every caption a board lays over a photograph reads on a phone (legible.py, R3 in motion/system/standards.md): the
layout deepens a beat's scrim under light words the photograph under them outshines, a label that does not read in its
own color takes the line's, and `storyboard.py check` names what no scrim reaches and a line set under the size a phone
shows."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import compose  # noqa: E402
import fixture  # noqa: E402
import legible  # noqa: E402
import storyboard  # noqa: E402

COLORS = {"paper": "#f4efe6", "ink": "#111111", "muted": "#777777"}
LAB = {"face": "text", "size": 56, "color": "ink"}


@unittest.skipUnless(fixture.HAVE_PIL, "Pillow is not installed")
class Captions(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.here = os.getcwd()
        self.d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        os.chdir(self.d.name)
        for name, gray in (("bright", 245), ("dark", 30)):
            Path("public").mkdir(exist_ok=True)
            Image.new("RGB", (96, 120), (gray,) * 3).save(f"public/{name}.png")
        compose.use("kinetic-type")
        self.fr = compose.Frame("reel")

    def tearDown(self):
        os.chdir(self.here)
        self.d.cleanup()

    def pic(self, name):
        return {"file": f"{name}.png", "aspect": 1.25, "subject": [0.5, 0.45], "zoom": storyboard.ZOOM,
                "box": [-0.06 * self.fr.W, -0.06 * self.fr.H, 1.06 * self.fr.W, 1.06 * self.fr.H]}

    def text(self, size=85, label="market"):
        a = self.fr.area
        return storyboard.set_text(self.fr, "at the market: peaches, figs", [a[0], a[1] + 0.6 * (a[3] - a[1]), a[2], a[3]],
                                   "display", size, "start", label, LAB if label else None)

    def beat(self, name, line, dark, size=85, label="market", label_color="ink"):
        t = self.text(size, label)
        if t["label"]:
            t["label"]["color"] = label_color
        top = min(bx[1] for bx in storyboard.text_boxes(t))
        return {"id": "p01", "form": "photo", "picture": self.pic(name), "text": dict(t, color=line),
                "scrim": {"from": top - self.fr.H / 6, "to": self.fr.H, "dark": dark} if dark else None}

    def test_light_words_over_a_bright_photograph_deepen_the_scrim_until_they_read(self):
        t = self.text(label=None)
        dark, _ = storyboard.shade_words(self.fr, self.pic("bright"), t, 0.3, "paper", "paper", COLORS)
        self.assertGreater(dark, 0.3)
        self.assertLessEqual(dark, legible.SCRIM_MOST)
        q = storyboard.quarters_under(self.fr, self.pic("bright"), storyboard.text_boxes(t))
        want = legible.need(t["size"], self.fr.W)
        self.assertTrue(all(legible.contrast(COLORS["paper"], x, dark, linear=False) >= want for x in q))
        self.assertLess(legible.contrast(COLORS["paper"], q[0], 0.3, linear=False), want)

    def test_a_photograph_dark_enough_keeps_the_cards_scrim(self):
        dark, label = storyboard.shade_words(self.fr, self.pic("dark"), self.text(label=None), 0.3, "paper", "paper", COLORS)
        self.assertEqual((dark, label), (0.3, "paper"))

    def test_a_label_that_does_not_read_in_its_own_color_takes_the_lines(self):
        _, label = storyboard.shade_words(self.fr, self.pic("dark"), self.text(), 0.6, "paper", "ink", COLORS)
        self.assertEqual(label, "paper")

    def test_the_layout_leaves_the_check_nothing_to_name(self):
        t = self.text()
        dark, label = storyboard.shade_words(self.fr, self.pic("bright"), t, 0.6, "paper", "ink", COLORS)
        x = self.beat("bright", "paper", dark, label_color=label)
        self.assertEqual(storyboard.legibility(self.fr, x, COLORS), [])

    def test_the_check_names_light_words_the_photograph_outshines(self):
        bad = storyboard.legibility(self.fr, self.beat("bright", "paper", 0.3, label=None), COLORS)
        self.assertEqual(len(bad), 1, bad)
        self.assertRegex(bad[0], r'^p01: "at the market.*" reads \d+\.\d:1 over the photograph under it \(scrim 0\.3\), '
                                 r'under the 3:1 a 85 px line needs on a phone')

    def test_the_check_names_a_label_no_scrim_makes_read(self):
        # a gray label too dull to read at its size even under the deepest scrim over a bright photograph
        dark, _ = storyboard.shade_words(self.fr, self.pic("bright"), self.text(), 0.6, "muted", "muted", COLORS)
        self.assertEqual(dark, legible.SCRIM_MOST)
        bad = storyboard.legibility(self.fr, self.beat("bright", "muted", dark, label_color="muted"), COLORS)
        self.assertTrue(any(b.lower().startswith('p01: "market" reads') and "the deepest scrim" in b for b in bad), bad)

    def test_the_check_names_dark_words_a_scrim_cannot_help(self):
        bad = storyboard.legibility(self.fr, self.beat("dark", "ink", 0.6, label=None), COLORS)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn("a black scrim never helps dark words", bad[0])

    def test_the_check_names_a_line_set_under_the_size_a_phone_shows(self):
        x = self.beat("dark", "paper", 0.6, label=None)
        x["text"]["size"] = 24
        bad = storyboard.legibility(self.fr, x, COLORS)
        self.assertTrue(any(b == f'p01: "{x["text"]["lines"][0]["text"]}" is set at 24 px, under the 32 px a phone shows legibly'
                            for b in bad), bad)

    def test_a_line_comes_down_no_further_than_the_size_a_phone_shows(self):
        a = self.fr.area
        t = storyboard.set_text(self.fr, "first coffee: rain outside, a cornetto, a cortado, the paper, the walk home",
                                [a[0], a[1], a[2], a[1] + 50], "text", 40, "start")
        self.assertGreaterEqual(t["size"], legible.LEAST)


if __name__ == "__main__":
    unittest.main()
