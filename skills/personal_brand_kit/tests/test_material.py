"""material.py's story: the agent's moments in their order once taste.json is theirs; while it is research.py's draft,
each pillar's best-liked moment that breaks no habit, never a line twice, the peak (best liked) last; the hook's
photograph is a moment the story does not play."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import material  # noqa: E402

LIB = {"posts": [{"likes": n} for n in (10, 90, 40, 70, 20, 60)], "reels": []}
RES = {"pillars": [{"name": "table"}, {"name": "market"}, {"name": "walk"}],
       "outliers": [{"caption": "NEON NIGHT OUT!!"}]}
M = [{"row": 0, "photo": "a.jpg", "line": "sunday table: lemons, butter, bread.", "pillar": "table"},
     {"row": 1, "photo": "b.jpg", "line": "tonight's table: worth the wait.", "pillar": "table"},
     {"row": 2, "photo": "c.jpg", "line": "at the market: figs.", "pillar": "market"},
     {"row": 3, "photo": "d.jpg", "line": "NEON NIGHT OUT!!", "pillar": "walk"},
     {"row": 4, "photo": "e.jpg", "line": "laundry lines, blue doors.", "pillar": "walk"},
     {"row": 5, "photo": "f.jpg", "line": "", "pillar": None}]


class Story(unittest.TestCase):
    def test_their_own_moments_play_in_their_order(self):
        got = material.story([M[4], M[0], M[2]], LIB, RES, drafted=False)
        self.assertEqual([m["photo"] for m in got], ["e.jpg", "a.jpg", "c.jpg"])

    def test_the_draft_plays_each_pillars_best_liked_moment_and_the_peak_last(self):
        got = material.story(M, LIB, RES, drafted=True)
        photos = [m["photo"] for m in got]
        # each pillar's best liked in the pillars' order, then a second round while the story is under four, the
        # peak moved last
        self.assertEqual(photos, ["c.jpg", "e.jpg", "a.jpg", "b.jpg"])
        self.assertNotIn("d.jpg", photos)
        self.assertEqual(len({m["line"] for m in got}), len(got))

    def test_the_hook_opens_on_a_moment_the_story_does_not_play(self):
        told = material.story(M, LIB, RES, drafted=True)
        pool = material.hook_pool(M, LIB, RES, told)
        played = {m["photo"] for m in told}
        self.assertNotIn(pool[0], played)
        self.assertNotIn("d.jpg", pool[: len(pool) - len(told)])


if __name__ == "__main__":
    unittest.main()
