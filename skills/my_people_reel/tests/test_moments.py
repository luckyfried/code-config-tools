"""The research draft's moments are what the two of them did: per person the photograph of the two of them, its month
and its place (the one its caption names, none when it names none), the person's caption of it and the line the other wrote under their year, never a count of posts; and
the read of why each person is in the film is prose without a number in it.

    python3 -I -m unittest discover -s S/tests
"""
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import research  # noqa: E402

PEOPLE = {"people": [{"rank": 1, "handle": "dani.reyes", "score": 110,
                      "signals": {"own_tags": 26, "tags_of_owner": 7, "their_comments": 30, "owner_comments": 41, "story_tags": 6},
                      "stretch": {"months": [7, 8], "label": "july and august"},
                      "line": {"text": "remember when we missed the last ferry", "from": "their comment"}, "lines": [],
                      "voice": {"describe": "loud, in capitals"}, "exchanges": [], "photos_together": 38}]}
# the photograph of the two of them picks.py chose, posted 2026-07-22
PICKS = {"people": [{"rank": 1, "handle": "dani.reyes", "src": "library/posts/2026-07-22-001-0.jpg", "ts": 1784721600,
                     "caption": "@dani.reyes owned this whole summer", "colors": []}]}


class Moments(unittest.TestCase):
    def test_a_moment_is_the_photograph_its_place_and_month_and_their_words(self):
        self.assertEqual(research.moments(PEOPLE, PICKS),
                         [{"who": "dani.reyes", "when": "july", "where": None, "what": "@dani.reyes owned this whole summer",
                           "they_said": "remember when we missed the last ferry"}])

    def test_a_moments_place_is_the_one_its_caption_names(self):
        picks = {"people": [dict(PICKS["people"][0], caption="@dani.reyes on the last ferry out of palermo")]}
        (m,) = research.moments(PEOPLE, picks)
        self.assertEqual((m["where"], m["when"]), ("palermo", "july"))

    def test_a_moment_whose_caption_names_no_place_stamps_its_month_alone(self):
        """A caption that names home, or no place, stamps the month alone."""
        for caption in ("back home with @dani.reyes", "@dani.reyes owned this whole summer"):
            picks = {"people": [dict(PICKS["people"][0], caption=caption)]}
            (m,) = research.moments(PEOPLE, picks)
            self.assertEqual((m["where"], m["when"]), (None, "july"))

    def test_why_a_person_is_in_the_film_is_prose_without_a_number(self):
        (x,) = research.people_read(PEOPLE, PICKS, research.moments(PEOPLE, PICKS))
        self.assertEqual(x["why"], "in your photographs, you in theirs, their comments under yours, yours under theirs, in your stories")
        self.assertEqual((x["when"], x["where"], x["what"]), ("july", None, "@dani.reyes owned this whole summer"))
        self.assertNotIn("score", x)


if __name__ == "__main__":
    unittest.main()
