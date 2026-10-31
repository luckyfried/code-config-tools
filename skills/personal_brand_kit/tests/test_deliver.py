"""deliver.py: the drafted caption when the agent wrote none, the review page as the film's cover (the reel with the
hook as its poster, the other two looks and how to ask for one, how it was made, the brand) with no score on it, and
brief.md as the run's notes beside out/, carrying every score of the cut against the bar and what the critic left when
the one fix was spent."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _env  # noqa: E402
import deliver  # noqa: E402
import qa  # noqa: E402
import vote  # noqa: E402
from unittest import mock  # noqa: E402


class DraftedCaption(unittest.TestCase):
    def test_the_drafted_caption_is_their_statement_never_a_measurement(self):
        brand = {"statement": "Sand and night: the streets, the table, the sea."}
        taste = {"register": {"hashtags": ["#lisbonwalks", "#eatlisbon"]}}
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                text = deliver.caption(brand, taste)
            finally:
                os.chdir(here)
        self.assertIn("one sentence, found in my photographs", text.lower())
        self.assertIn(brand["statement"], text)
        self.assertNotIn("measured", text.lower())


def scores(low=None):
    s = dict.fromkeys(vote.CRITERIA, 5)
    if low:
        s["picture"] = low
    return {"scores": s, "paragraph": "x"}


class Cover(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        run = self.d / "build" / "20261027T000000Z"
        (run / "out").mkdir(parents=True)
        (run / "critic").mkdir()
        for letter, name in zip("abc", ("Kinetic type", "Editorial quiet", "Swiss grid")):
            (run / "storyboards" / letter).mkdir(parents=True)
            (run / "storyboards" / letter / "plan.json").write_text("{}")
            (run / "storyboards" / letter / "board-reel.json").write_text(json.dumps({"name": name}))
        brand = {"handle": "h", "statement": "the table, the market, the walk home.",
                 "palette": [{"name": "terracotta", "hex": "#BA5F43", "share": 0.4, "role": "lead"}],
                 "voice": {"case": "lowercase", "avg_words": 9, "devices": [{"name": "opening label"}]},
                 "aspire": {"palette": [{"name": "sea blue", "hex": "#3A6EA5"}], "subjects": ["the coast"]},
                 "stop": [{"line": "neon edits", "why": "they landed under your usual likes"}]}
        both = lambda low=None: {c: {"boards": {"film": scores(low)}} for c in vote.CUT_PANEL}
        for name, obj in (("library.json", {"handle": "h"}), ("taste.json", {"avoid": ["neon"]}), ("brand.json", brand),
                          ("winner.json", {"board": "a", "name": "Kinetic type", "by": "taste", "why": "loud and short, like the captions"}),
                          ("critic/verdict.json", {"round": 2, "verdict": "spent", "what": "picture: the person gave 3"}),
                          ("critic/cut-1.json", {"round": 1, "critics": both(2)}),
                          ("critic/cut-2.json", {"round": 2, "critics": both(3), "fixed": "the mask word"})):
            (run / name).write_text(json.dumps(obj))
        os.chdir(run)
        with mock.patch.object(_env, "ROOT", self.d.resolve()), mock.patch.object(_env, "enter", lambda new=False: run), \
                mock.patch.object(sys, "argv", ["deliver.py"]), mock.patch.object(deliver, "caption", lambda *a: "a caption"), \
                mock.patch.object(qa, "gate", lambda run=None: 0), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.page = Path("out/review.html").read_text()

    def test_the_page_opens_on_the_reel_with_the_hook_as_its_poster(self):
        self.assertLess(self.page.index('<video src="film.mp4" poster="story.png"'), self.page.index("<h1>"))
        for name in ("film-square.mp4", "film-wide.mp4", "post.png", "story.png"):
            self.assertIn(f'src="{name}"', self.page)
        self.assertIn('<video src="film-square.mp4" poster="post.png"', self.page)

    def test_the_page_offers_the_other_two_looks_by_name(self):
        self.assertIn("Prefer another look? Say 'make the second one'", self.page)
        self.assertIn("Editorial quiet", self.page)
        self.assertIn("Swiss grid", self.page)

    def test_the_page_carries_how_it_was_made_and_the_brand_and_no_score(self):
        for part in ("How it was made", "Your palette", "background:#BA5F43", "Your voice", "What you like elsewhere",
                     "What to stop"):
            self.assertIn(part, self.page)
        for word in ("score", "critic", "verdict", "R1", "the bar", "vote"):
            self.assertNotIn(word, self.page.lower() if word.islower() else self.page)

    def test_the_runs_notes_stay_beside_out_and_carry_every_score_and_what_was_left(self):
        self.assertFalse(Path("out/brief.md").exists())
        notes = Path("brief.md").read_text()
        self.assertIn("Round 2: mean 4.67, lowest 3, under the bar.", notes)
        self.assertIn("What holds it under: picture: the person gave 3", notes)
        self.assertIn("Picked by their taste: loud and short, like the captions.", notes)


if __name__ == "__main__":
    unittest.main()
