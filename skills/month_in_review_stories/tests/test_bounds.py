"""The framing check on the story cards (compose.stories.bounds) and the cards rendered at their rest frames.

    python3 -m unittest discover -s S/tests -p 'test_bounds.py'      # one studio render, under a minute

Every month shape composes cards whose type the camera never cuts where it holds, that stand inside the safe area on a
whole-frame hold, and that never overlap another line on screen with them. Each case breaks one card the way a defect
looks and expects the check's line for it. The render draws every shot of the fixture's cards at a beat in, the middle
and the last frame, and expects no failed frame and no FONT_ERROR or IMAGE_ERROR.
"""
import copy
import tempfile
import unittest
from pathlib import Path

import fixture
import compose
import studio
from compose import stories
from test_compose import months_later, picked, with_posts


def card(b, cid):
    return next(c for c in b["beats"] if c["id"] == cid)


def off_the_label(c):
    v = c["shots"][-1]["view"]
    c["shots"][-1]["view"] = dict(v, h=v["h"] * 0.6)


def past_the_margin(c):
    next(ln for ln in c["lines"] if "out" not in ln)["x"] = 30


def onto_the_line_above(c):
    c["lines"][-1]["y"] = c["lines"][-2]["y"]


# name: (card, break, the start of the line the check writes)
CASES = {
    "close-label-cut": ("story-1", off_the_label, "story-1 shot 3: the camera cuts"),
    "last-past-margin": ("story-4", past_the_margin, "stands outside the safe area"),
    "lines-overlap": ("story-2", onto_the_line_above, "overlap"),
}


class Bounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()
        cls.board = compose.board("editorial-quiet", picked(cls.month))

    def test_every_month_shape_frames_clean(self):
        m = self.month
        shapes = {"picked": picked(m), "spread": m, "three": picked(m, [{"day": 13, "peak": True}, {"day": 17}, {"day": 28}]),
                  "three-posts": with_posts(m, 3), "twelve-posts": with_posts(m, 12), "twenty-posts": with_posts(m, 20),
                  "next-month": months_later(picked(m), 1), "six-weeks": months_later(picked(m), 8)}
        for name, mm in shapes.items():
            with self.subTest(month=name):
                b = compose.board("editorial-quiet", mm)
                self.assertEqual([x for c in b["beats"] for x in stories.bounds(c)], [])

    def test_each_break_is_found(self):
        for name, (cid, brk, want) in CASES.items():
            with self.subTest(case=name):
                c = copy.deepcopy(card(self.board, cid))
                brk(c)
                got = stories.bounds(c)
                self.assertTrue(any(want in g for g in got), f"{name}: wanted {want!r}, got {got}")

    def test_cards_render_at_rest(self):
        work = Path(tempfile.mkdtemp(prefix="mir-bounds-"))
        jobs = studio.rest_jobs(self.board, work / "rest")
        report = studio.render(jobs, work, "bounds", board=self.board)
        self.assertEqual(report.get("failed"), 0, report.get("findings", [])[:3])
        self.assertEqual(studio.lines(studio.findings(report)), [])
        self.assertEqual(len(list((work / "rest").glob("*.png"))), len(jobs))


if __name__ == "__main__":
    unittest.main()
