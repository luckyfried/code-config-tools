"""The hook tags every head in the photograph of them together, in every format: a tag stands under its head or over
it, whichever side leaves it in the frame and clear of the tags beside it, and hangs under its neighbor's tag where the
heads crowd; a placement that would leave a head without its tag is never the one laid. Where no group photograph
opens the film, the title and the edge it stands on stay off the face of the photograph that does.

    python3 -I -m unittest discover -s S/tests -p test_hook_tags.py
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


TALL = 16 / 9


class Photos:
    """A matched group framed whole across a 9:16 picture (its heads inside the band it spans), and one portrait."""

    def __init__(self, face=(0.4, 0.3, 0.6, 0.5), framed=True):
        self.aspect = {"group": TALL, "p0.x-0": TALL if framed else 1.25}
        self.face, self.whole = list(face), framed
        # a 16:9 photograph laid whole across a 9:16 picture spans the middle 9/16 / 16/9 of its height
        span = (9 / 16) / TALL
        self.band = {r: [round((1 - span) / 2, 4), round((1 + span) / 2, 4)] for r in self.aspect} if framed else {}

    def framed(self, role):
        return self.whole

    def role(self, h):
        return "p0.x-0"

    def info(self, role):
        return {"point": [0.5, (self.face[1] + self.face[3]) / 2], "face": self.face}


def band(heads, top, span):
    return {f"p{i}.x": [u, round(top + v * span, 4)] for i, (u, v) in enumerate(heads)}


def hook(heads, kind, photos=None):
    photos = photos or Photos()
    ctx = types.SimpleNamespace(photos=photos, cast={"group": {"heads": heads}} if heads else {}, heads=lambda: list(heads),
                                handle="me", year=2026, people=[types.SimpleNamespace(handle="p0.x")])
    F = bd.lensed(L.Frame(kind))
    return F, bd.hook(F, ctx)


ROWS = {
    "five in a row": [(0.08, 0.35), (0.3, 0.36), (0.5, 0.34), (0.7, 0.35), (0.92, 0.36)],
    "five near the top": [(0.1, 0.12), (0.3, 0.14), (0.5, 0.12), (0.7, 0.13), (0.9, 0.12)],
    "six across": [(0.05, 0.3), (0.22, 0.32), (0.4, 0.3), (0.58, 0.31), (0.76, 0.3), (0.95, 0.33)],
    "four low": [(0.2, 0.55), (0.4, 0.56), (0.6, 0.55), (0.8, 0.56)],
}
# a landscape group and a 4:5 one, each framed whole across the 9:16 picture
BANDS = {"landscape": (0.3125, 0.375), "4:5": (0.1484, 0.7031)}


class HookTags(unittest.TestCase):
    """The hook laid under an edge, the frame of a look the kit names no other frame for."""

    def setUp(self):
        frames = dict(bd.FRAMES)
        self.addCleanup(bd.FRAMES.update, frames)
        bd.FRAMES.pop("scrapbook")
        bd.use("scrapbook", swatches=SWATCHES)

    def test_every_head_in_the_group_gets_its_tag_in_every_format(self):
        for kind in ("reel", "square", "wide"):
            for shape, (top, span) in BANDS.items():
                for name, row in ROWS.items():
                    with self.subTest(kind=kind, shape=shape, row=name):
                        heads = band(row, top, span)
                        F, (edge, role, layers) = hook(heads, kind)
                        self.assertEqual(role, "group")
                        tags = [t for la in layers if la["kind"] == "Tags" for t in la["tags"]]
                        self.assertEqual(sorted(t["text"] for t in tags), sorted(f"@{h}" for h in heads))
                        for i, t in enumerate(tags):
                            self.assertTrue(bd.in_frame(F, t), t)
                            for o in tags[:i]:
                                self.assertFalse(t["box"][0] < o["box"][2] and o["box"][0] < t["box"][2]
                                                 and t["box"][1] < o["box"][3] and o["box"][1] < t["box"][3], (t, o))

    def test_the_title_stays_off_the_face_of_the_photograph_that_opens_the_film(self):
        face = [0.4, 0.38, 0.6, 0.5]
        for kind in ("reel", "square"):
            with self.subTest(kind=kind):
                F, (edge, role, layers) = hook({}, kind, Photos(face))
                cut = layers[0]
                x, y, w, h = cut["place"]
                fy0, fy1 = y + face[1] * h, y + face[3] * h
                words = [ln for la in layers if la["kind"] == "Words" for ln in la["lines"]]
                self.assertTrue(bd.face_clear(F, face, cut["place"], [bd.hull(bd.turned(bd.box(ln), ln)) for ln in words]))
                self.assertFalse(fy0 < edge.yc < fy1, (edge.yc, fy0, fy1))


class WholeHooks(unittest.TestCase):
    def test_every_person_the_film_names_is_on_the_hook_in_each_looks_own_shape(self):
        """The marquee band carries every name in the film's order across the frame; the home movie stamps each in rows
        from the top corner; the scrapbook sticks each round the print. Each stays in the safe area, clear of the
        title, and no two stamps or stickers overlap."""
        people = [types.SimpleNamespace(handle=f"p{i}.x") for i in range(7)]
        for look, shape in (("kinetic-type", "band"), ("analog-home-movie", "stamp"), ("scrapbook", "sticker")):
            bd.use(look, swatches=SWATCHES)
            for kind in ("reel", "square", "wide"):
                with self.subTest(look=look, kind=kind):
                    ctx = types.SimpleNamespace(photos=Photos(), cast={}, heads=lambda: [], handle="me", year=2026,
                                                people=people)
                    F = bd.lensed(L.Frame(kind))
                    edge, role, layers = bd.hook(F, ctx)
                    tags = [t for la in layers if la["kind"] == "Tags" for t in la["tags"]]
                    self.assertEqual({t["shape"] for t in tags}, {shape})
                    names = " ".join(t["text"] for t in tags).split()
                    # in the case the look sets its tags in
                    self.assertEqual([n.lower() for n in names if n.startswith("@")], [f"@{p.handle}" for p in people])
                    board = {"format": {"kind": kind}, "beats": [{"id": "hook", "layers": layers}]}
                    self.assertEqual(bd.problems(board), [])
                    for i, t in enumerate(tags):
                        for o in tags[:i]:
                            self.assertFalse(t["box"][0] < o["box"][2] and o["box"][0] < t["box"][2]
                                             and t["box"][1] < o["box"][3] and o["box"][1] < t["box"][3], (t, o))


if __name__ == "__main__":
    unittest.main()
