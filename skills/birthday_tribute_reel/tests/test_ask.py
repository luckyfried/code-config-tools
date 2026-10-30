"""research reads the person's ask as they said it: the length they asked for (refused, with nothing made, outside the
range the kit makes), the age only when they gave it, the name they call the named one, their own line for the wish,
and the photos that show the named one; when nothing in the posts names them, every photo is used and the run says so.

    python3 -I -m unittest discover -s S/tests -p test_ask.py
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import compose  # noqa: E402
import shared  # noqa: E402

CLOSED = ["--door", "instagram_account=closed: no Instagram tool", "--door", "browser=closed: no browser tool"]
GRANDPA = {"owner": "lena.wojcik", "posts": [
    {"date": "2026-01-02", "media": "photos/snow.jpg", "caption": "grandpa's cabin, first snow of the year",
     "comments": [{"user": "marek.w", "text": "he shoveled before breakfast again"}]},
    {"date": "2026-04-20", "media": "photos/garden.jpg", "caption": "planting with grandpa, he still won't wear gloves"},
    {"date": "2026-07-14", "media": "photos/man-portrait.jpg", "caption": "grandpa at the market, haggling for fun"},
    {"date": "2026-08-30", "media": "photos/tomatoes.jpg", "caption": "grandpa's tomatoes beat mine again"},
    {"date": "2026-09-05", "media": "photos/selfie.jpg", "caption": "new phone who dis", "comments": [{"user": "ola.k", "text": "finally"}]}]}


def workspace(test, posts):
    """A workspace holding `posts` as export/posts.json and its photos, gathered; returns its root."""
    tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name)
    (root / "photos").mkdir()
    for p in posts["posts"]:
        (root / p["media"]).write_bytes(b"jpg")
    (root / "export").mkdir()
    (root / "export" / "posts.json").write_text(json.dumps(posts))
    p = run(root, "gather.py", *CLOSED)
    test.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    return root


def run(root, script, *args):
    return subprocess.run([sys.executable, str(KIT / "scripts" / script), *args], cwd=root, capture_output=True, text=True,
                          env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))


def run_dir(root):
    return root / "build" / (root / "build" / "latest").read_text().strip()


class Length(unittest.TestCase):
    def test_the_range_is_the_kits_and_a_length_outside_it_is_refused(self):
        lo, hi = compose.LENGTH
        self.assertEqual((lo, hi), (20, 60))
        for n in (lo, 45, hi):
            self.assertIsNone(compose.refusal(n), n)
        for n in (10, 19, 61, 90):
            said = compose.refusal(n)
            self.assertTrue(said.startswith(f"not delivered: {n} s is outside the 20–60 s"), said)

    def test_research_makes_nothing_for_a_length_outside_the_range(self):
        root = workspace(self, GRANDPA)
        for script in ("research.py", "shared.py"):
            p = run(root, script, "--who", "grandpa", "--seconds", "90")
            with self.subTest(script):
                self.assertNotEqual(p.returncode, 0)
                self.assertIn("not delivered: 90 s is outside the 20–60 s", p.stdout + p.stderr)
                self.assertFalse((run_dir(root) / "shared.json").exists(), "nothing shorter is made in its place")
                self.assertFalse((run_dir(root) / "ask.json").exists())

    def test_the_asked_length_is_kept_with_the_ask(self):
        root = workspace(self, GRANDPA)
        p = run(root, "shared.py", "--who", "grandpa", "--seconds", "45")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads((run_dir(root) / "ask.json").read_text())["seconds"], 45)


class Words(unittest.TestCase):
    CAPS = ["dani turns 30 on october 24 and i'm already planning the table @dani.reyes", "five years of us"]
    NOW = dt.date(2026, 10, 1)

    def test_the_age_comes_from_the_ask_alone(self):
        occ = shared.occasion_of({"who": "@dani.reyes"}, self.CAPS[:1], "Dani", self.NOW)
        self.assertEqual((occ["kind"], occ["age"], occ["date"]), ("birthday", None, "2026-10-24"),
                         "a caption gives the occasion and its day, never the age")
        self.assertEqual(occ["title"], "happy birthday, dani")
        self.assertNotIn("turns", occ["label"])
        asked = shared.occasion_of({"occasion": "she turns 30 on october 24"}, self.CAPS[:1], "Dani", self.NOW)
        self.assertEqual((asked["age"], asked["title"]), (30, "happy 30th, dani"))
        years = shared.occasion_of({"occasion": "our anniversary"}, self.CAPS[1:], "Ana", self.NOW)
        self.assertEqual((years["kind"], years["years"]), ("anniversary", None))

    def test_their_own_line_is_the_wish(self):
        occ = shared.occasion_of({"occasion": "her 30th", "line": "to the girl who knows every wall"}, [], "Marta", self.NOW)
        self.assertEqual(occ["title"], "to the girl who knows every wall")
        self.assertEqual(occ["age"], 30)

    def test_the_name_they_give_leads(self):
        for words, name in (("my sister leila (@leila.bakes)", "leila"), ("marta (@marta.sol)", "marta"), ("@dani.reyes", None),
                            ("my mom", "mom"), ("grandpa", "grandpa"), ("us", None), ("", None), (None, None)):
            self.assertEqual(shared.asked_name(words), name, words)


class Photos(unittest.TestCase):
    def test_captions_that_name_them_are_their_photos_when_nothing_tags_them(self):
        root = workspace(self, GRANDPA)
        p = run(root, "shared.py", "--who", "grandpa", "--occasion", "his 90th")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        sh = json.loads((run_dir(root) / "shared.json").read_text())
        self.assertEqual(sh["who"]["first"].lower(), "grandpa")
        self.assertIsNone(sh["who"]["handle"])
        self.assertEqual([x["caption"][:20] for x in sh["items"]],
                         [p["caption"][:20] for p in GRANDPA["posts"][:4]], "the selfie names no one and is left out")
        self.assertTrue(all(x["why"] == ["named"] for x in sh["items"]))
        self.assertEqual((sh["occasion"]["age"], sh["occasion"]["title"]), (90, "happy 90th, grandpa"))

    def test_with_nothing_naming_them_every_photo_is_used_and_the_run_says_which_and_why(self):
        posts = {"owner": "lena.wojcik", "posts": [dict(p, caption=c) for p, c in zip(GRANDPA["posts"][:3], ("first snow", "the garden", "market day"))]}
        root = workspace(self, posts)
        p = run(root, "shared.py", "--who", "grandpa")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        sh = json.loads((run_dir(root) / "shared.json").read_text())
        self.assertEqual(len(sh["items"]), 3)
        said = [a for a in sh["assumptions"] if "every photo" in a]
        self.assertEqual(len(said), 1, sh["assumptions"])
        self.assertIn("nothing in your posts tags or names grandpa", said[0].lower())
        for c in ("first snow", "the garden", "market day"):
            self.assertIn(c, said[0])
        self.assertIn(said[0], p.stdout)

    def test_a_post_that_tags_them_or_is_their_own_shows_them_more_than_one_that_names_them(self):
        self.assertEqual(compose.shown({"why": ["tagged"], "from": "mine"}), 2)
        self.assertEqual(compose.shown({"why": ["their post tagging you"], "from": "theirs"}), 2)
        self.assertEqual(compose.shown({"why": ["mentioned"], "from": "mine"}), 1)
        self.assertEqual(compose.shown({"why": ["named"], "from": "mine"}), 1)
        self.assertEqual(compose.shown({"why": ["in your posts"], "from": "mine"}), 0)


if __name__ == "__main__":
    unittest.main()
