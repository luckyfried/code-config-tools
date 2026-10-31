"""A card's type takes its color from the field it sits on: on the paper it is ink, whatever the photograph hidden
behind the paper reads in. On a card laid under an edge every line stands level at rest, whatever the edge's tilt; on
the scrapbook's print card the caption is hand-lettered under the print, turned with the hand and inside the safe area,
and on a reel a keepsake print and the month fill the page's lower third under it; the prints arrive differently from one
person to the next. A home movie's typed lines stand a third larger than its card's size when they clear the eyes.
A handle of the person's own at the start or end of their words is printed once, on their tag; every other name in
the words stays.

    python3 -I -m unittest discover -s S/tests -p test_card_type.py
"""
import sys
import types
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive as bd  # noqa: E402
import layout as L  # noqa: E402

# the photographs' colors the scrapbook card's palette rule makes the board's colors from
SWATCHES = ["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"]


ZE = types.SimpleNamespace(rank=3, handle="ze.do.largo", stamp="lisbon, september", voice="slow")


class Photos:
    def __init__(self, face, aspect=1.25):
        self.aspect = {"ze.do.largo-0": aspect}
        self.face = face

    def framed(self, role):
        return False

    def info(self, role):
        return {"point": [0.5, self.face[3] + 0.1], "face": self.face}


def card(face):
    F = bd.lensed(L.Frame("reel"))
    edge, role, layers, ok = bd.card(F, Photos(face), ZE, "the best summer of my life", 2)
    return edge, layers, [ln for la in layers if la["kind"] == "Words" for ln in la["lines"]]


class CardType(unittest.TestCase):
    """The card laid under an edge, the frame of a look the kit names no other frame for."""

    def setUp(self):
        frames = dict(bd.FRAMES)
        self.addCleanup(bd.FRAMES.update, frames)
        bd.FRAMES.pop("scrapbook")
        bd.use("scrapbook", swatches=SWATCHES)

    def test_type_on_the_ground_is_the_role_that_reads_on_it(self):
        # a face at the photograph's very top leaves no edge over it: the photograph fills the frame from the edge down
        # and the type stands on the card's ground over it, in the role that reads there
        edge, layers, lines = card([0.4, 0.02, 0.6, 0.2])
        self.assertEqual(layers[0]["field"], "bg")
        self.assertEqual({ln["color"] for ln in lines}, {bd.look().on_ground})
        self.assertFalse(any("strip" in ln for ln in lines))

    def test_every_line_stands_level_over_a_tilted_edge(self):
        edge, layers, lines = card([0.35, 0.3, 0.6, 0.5])
        self.assertNotEqual(edge.tilt, 0)
        self.assertEqual([ln.get("rotate") or 0 for ln in lines], [0] * len(lines))
        F = bd.lensed(L.Frame("reel"))
        self.assertTrue(bd.fits(F, lines, edge))

    def test_their_own_handle_is_printed_once_on_their_tag(self):
        self.assertEqual(bd.printed(ZE, "the best summer of my life @ze.do.largo"), "the best summer of my life")
        self.assertEqual(bd.printed(ZE, "@ze.do.largo, the best summer"), "the best summer")
        self.assertEqual(bd.printed(ZE, "@ana.costa swore the river was warm"), "@ana.costa swore the river was warm")
        self.assertEqual(bd.printed(ZE, "@ze.do.largo"), "@ze.do.largo")
        self.assertEqual(bd.printed(ZE, None), None)


class PrintCard(unittest.TestCase):
    def setUp(self):
        bd.use("scrapbook", swatches=SWATCHES)

    def test_the_caption_is_hand_lettered_under_the_print_turned_with_the_hand_and_inside_the_safe_area(self):
        F = bd.lensed(L.Frame("reel"))
        edge, role, layers, ok = bd.card(F, Photos([0.35, 0.3, 0.6, 0.5]), ZE, "the best summer of my life", 2)
        self.assertTrue(ok)
        cut = layers[0]
        self.assertEqual(cut["field"], "bg")
        spec = bd.look().card["photo"]["line"]
        lines = [ln for la in layers if la["kind"] == "Words" for ln in la["lines"]]
        said = [ln for ln in lines if ln["name"].startswith("said-")]
        self.assertEqual({ln["color"] for ln in said}, {bd.look().on_ground})
        self.assertEqual({ln.get("rotate") or 0 for ln in said}, {spec.get("rotate") or 0})
        # the print stands over its caption: the words start under the print's foot
        x, y, w, h = cut["place"]
        self.assertGreater(bd.top_of(said), y + h)
        self.assertEqual(bd.problems({"format": {"kind": "reel"}, "beats": [{"id": "person-3", "layers": layers}]}), [])

    def test_a_reel_page_fills_its_lower_third_with_a_keepsake_print_and_the_month_stamped_low(self):
        F = bd.lensed(L.Frame("reel"))
        photos = Photos([0.35, 0.3, 0.6, 0.5])
        photos.aspect["ze.do.largo-1"] = 0.8
        edge, role, layers, ok = bd.card(F, photos, ZE, "the best summer of my life", 2)
        cut = layers[0]
        keep = cut["keepsake"]
        self.assertEqual(keep["file"], "matched/ze.do.largo-1.jpg")
        lines = [ln for la in layers if la["kind"] == "Words" for ln in la["lines"]]
        said = [ln for ln in lines if ln["name"].startswith("said-")]
        month = next(ln for ln in lines if ln["name"].startswith("stamp-"))
        # the keepsake and the month stand under the caption, on either side of the page's middle, inside the frame
        x0, y0, x1, y1 = keep["box"]
        self.assertGreater(y0, bd.foot_of(said))
        self.assertLess(y1, F.H)
        self.assertTrue(month["low"])
        self.assertGreater(bd.top_of([month]), bd.foot_of(said))
        self.assertTrue(y0 < month["y"] < y1)
        self.assertTrue((x0 + x1) / 2 > F.W / 2 > month["x"] or (x0 + x1) / 2 < F.W / 2 < month["x"])
        self.assertEqual(bd.problems({"format": {"kind": "reel"}, "beats": [{"id": "person-3", "layers": layers}]}), [])

    def test_a_square_page_has_no_lower_third_and_keeps_the_month_under_the_caption(self):
        F = bd.lensed(L.Frame("square"))
        edge, role, layers, ok = bd.card(F, Photos([0.35, 0.3, 0.6, 0.5]), ZE, "the best summer of my life", 2)
        self.assertNotIn("keepsake", layers[0])
        lines = [ln for la in layers if la["kind"] == "Words" for ln in la["lines"]]
        said = [ln for ln in lines if ln["name"].startswith("said-")]
        month = next(ln for ln in lines if ln["name"].startswith("stamp-"))
        self.assertFalse(month.get("low"))
        self.assertGreater(bd.top_of([month]), bd.foot_of(said))

    def test_the_prints_arrive_differently_from_one_person_to_the_next(self):
        F = bd.lensed(L.Frame("reel"))
        entries = [bd.card(F, Photos([0.35, 0.3, 0.6, 0.5]), ZE, "the best summer", i)[2][0]["entry"] for i in range(3)]
        self.assertEqual(len(set(entries)), 3)


class TypedLines(unittest.TestCase):
    def setUp(self):
        bd.use("analog-home-movie", swatches=SWATCHES)

    def test_a_home_movies_typed_lines_stand_a_third_larger_than_its_cards_size_when_they_clear_the_eyes(self):
        F = bd.lensed(L.Frame("reel"))
        edge, role, layers, ok = bd.card(F, Photos([0.4, 0.1, 0.6, 0.25], aspect=1.78), ZE, "the best summer of my life", 2)
        self.assertTrue(ok)
        spec = bd.look().card["photo"]["line"]
        said = [ln for la in layers if la["kind"] == "Words" for ln in la["lines"] if ln["name"].startswith("said-")]
        self.assertGreaterEqual(min(ln["size"] for ln in said), spec["size"] * 4 / 3)
        self.assertEqual(bd.problems({"format": {"kind": "reel"}, "beats": [{"id": "person-3", "layers": layers}]}), [])


if __name__ == "__main__":
    unittest.main()
