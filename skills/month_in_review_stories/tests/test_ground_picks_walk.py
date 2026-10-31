"""No word stands on a photograph, the moments are the month's top posts whenever it carries counts, a reel with no
asked length runs 15 s, and the reel shows each moment once, the peak first.

    python3 -m unittest discover -s S/tests -p 'test_ground_picks_walk.py'
"""
import copy
import json
import unittest

import fixture
import compose
import storyboard
from compose import stories
from compose.common import W


def picked(m, days, peak=None):
    """Their month with the moments the agent picks on `days`, each saying its caption, the one on `peak` the peak."""
    m = copy.deepcopy(m)
    by_day = {p["day"]: p for p in m["posts"]}
    m["moments"] = [{"day": d, "photo": by_day[d]["photo"], "line": by_day[d]["caption"], "peak": d == peak} for d in days]
    return m


def uncounted(m):
    """Their month with no likes or comments in its data."""
    m = copy.deepcopy(m)
    for p in m["posts"]:
        p["likes"] = p["comments"] = None
    return m


def asked(m, **ask):
    m = copy.deepcopy(m)
    m["ask"] = ask
    return m


class Ground(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m = fixture.month()
        cls.boards = [compose.board("editorial-quiet", m), compose.board("editorial-quiet", picked(m, [5, 13, 17, 28], 13)),
                      compose.board("editorial-quiet", asked(m, counts=True))]

    def test_no_story_word_or_plate_stands_on_a_photograph(self):
        seen = 0
        for b in self.boards:
            for card in b["beats"]:
                for rect in (x["rect"] for x in card["bands"] if x["file"]):
                    seen += 1
                    for ln in card["lines"]:
                        self.assertTrue(stories.apart(stories.box_of(ln), rect), (card["id"], ln["text"], rect))
                    for st in card["strips"]:
                        self.assertTrue(stories.apart(st["rect"], rect), (card["id"], st["rect"], rect))
        self.assertGreater(seen, 0)

    def test_the_story_line_ends_its_climb_clear_of_the_plates_above_the_band(self):
        for b in self.boards:
            for card in b["beats"]:
                above = max(st["rect"][3] for st in card["strips"] if st["rect"][3] <= 600)
                for rule in card["rules"]:
                    # the line is drawn 9 px thick about its height
                    self.assertGreaterEqual(min(v for _, v, _ in rule["y"]) - 4.5, above, card["id"])

    def test_no_reel_word_or_plate_stands_on_a_photograph(self):
        seen = set()
        for b in self.boards:
            for c in b["reel"]["cards"]:
                lo, hi = c["band"]
                if c["file"]:
                    x, y, w, h = c["place"]
                    # the photograph covers its band and its post's cell lies inside the band
                    self.assertTrue(x <= 0.1 and x + w >= W - 0.1 and y <= lo + 0.1 and y + h >= hi - 0.1, c["key"])
                    s, (_, oy) = c["T"]["s"], c["T"]["o"]
                    self.assertGreaterEqual((c["cell"][1] - oy) / s, lo - 0.5, c["key"])
                    self.assertLessEqual((c["cell"][3] - oy) / s, hi + 0.5, c["key"])
                for ln in c["lines"]:
                    # the month's line stands on the ground above the first band, every other word on the ground on
                    # its card's side of its band
                    if ln.get("name") == "hook" or (c["side"] == "over" and ln.get("name") != "big"):
                        self.assertLessEqual(ln["y"] + 0.24 * ln["size"], lo, (c["key"], ln["text"]))
                    elif ln.get("name") != "big":
                        self.assertGreaterEqual(ln["y"] - 0.74 * ln["size"], hi, (c["key"], ln["text"]))
                if c["side"] == "over":
                    self.assertLessEqual(c["strip"][3], lo, c["key"])
                else:
                    self.assertGreaterEqual(c["strip"][1], hi, c["key"])
                seen.add(c["side"])
        # the words stand over their band on some card and under it on another
        self.assertEqual(seen, {"over", "under"})


class Picks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()

    def test_unasked_the_moments_are_the_months_story_and_the_fullest_caption_the_peak(self):
        r = compose.board("editorial-quiet", self.month)["reel"]
        self.assertEqual(sorted(c["day"] for c in r["cards"]), [2, 13, 28])
        self.assertEqual([c["day"] for c in r["cards"] if c["peak"]], [13])
        self.assertFalse([x for c in r["cards"] for x in c["lines"] if x.get("name") == "count"])

    def test_a_pick_stands_whatever_its_posts_likes(self):
        r = compose.board("editorial-quiet", picked(self.month, [2, 9, 21], 9))["reel"]
        self.assertEqual([c["day"] for c in r["cards"]], [9, 2, 21])

    def test_a_month_with_no_counts_tells_the_same_story_and_takes_any_pick(self):
        m = uncounted(self.month)
        self.assertEqual([c["day"] for c in compose.board("editorial-quiet", m)["reel"]["cards"]], [13, 2, 28])
        r = compose.board("editorial-quiet", picked(m, [2, 9, 21], 9))["reel"]
        self.assertEqual([c["day"] for c in r["cards"]], [9, 2, 21])

    def test_the_research_draft_is_the_months_story(self):
        ws = fixture.workspace()
        fixture.researched(ws)
        b = fixture.build(ws)
        taste, research = (json.loads((b / f).read_text()) for f in ("taste.json", "research.json"))
        posts = {p["photo"]: p for p in research["posts"]}
        self.assertEqual([posts[x["photo"]]["day"] for x in taste["moments"]], [2, 13, 28])
        self.assertEqual([posts[x["photo"]]["day"] for x in taste["moments"] if x["peak"]], [13])

    def test_with_no_asked_length_the_reel_runs_15_s(self):
        for m in (self.month, picked(self.month, [5, 13, 17, 28], 13), uncounted(self.month)):
            r = compose.board("editorial-quiet", m)["reel"]
            self.assertEqual(r["frames"], 450)
            self.assertAlmostEqual(r["end"], 15 * r["bpm"] / 60, places=2)


class Walk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = compose.board("editorial-quiet", picked(fixture.month(), [5, 13, 17, 28], 13))

    def test_the_peak_opens_and_the_others_follow_in_date_order_each_once(self):
        r = self.board["reel"]
        self.assertNotIn("hook", r)
        self.assertEqual([c["day"] for c in r["cards"]], [13, 5, 17, 28])
        self.assertEqual(len({c["file"] for c in r["cards"]}), 4)
        self.assertEqual([b["key"] for b in r["beats"]], ["moment-1", "moment-2", "moment-3", "moment-4", "closer"])
        self.assertEqual(r["beats"][0]["from"], 0)
        self.assertLessEqual(r["cards"][0]["arrive"], 0.5)
        self.assertEqual(storyboard.reel_structure(self.board), [])

    def test_the_closer_holds_still_over_a_second_after_its_stop(self):
        r = self.board["reel"]
        self.assertGreaterEqual((r["end"] - r["closer"]["still"]) * 60 / r["bpm"], 1.0)


if __name__ == "__main__":
    unittest.main()
