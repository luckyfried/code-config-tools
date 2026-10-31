"""The handle on screen, drafted from an export the way a run drafts it: it is the username the export's profile files
give, or there is none; an export without them shows no handle, whatever its folder is called, and a stand-in handle
(@your_handle, @username and the like), as the handle or anywhere in the words on screen, fails the build. A delivery
from an export without a handle names no stand-in in its board, its caption, its brief or its review page.

    python3 -I -m unittest discover -s S/tests
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
S = KIT / "scripts"
ENV = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")


def run(ws, *args):
    return subprocess.run([sys.executable, *args], cwd=ws, capture_output=True, text=True, env=ENV)


class Handle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        root = Path(cls.tmp.name)
        # three of the fixture's own photographs (evals/fixtures/photos/)
        months = [{"month": m, "photo": photo, "posts": 3, "likes": 40, "caption": f"the lake in month {m}. annecy", "more": []}
                  for m, photo in ((3, "garden.jpg"), (6, "picnic.jpg"), (9, "snow.jpg"))]
        book = root / "book.json"
        book.write_text(json.dumps({"handle": "lake.days", "name": "Lake Days", "year": 2026, "exported": "2026-12-30", "months": months}))
        cls.ws = root / "ws"
        cls.ws.mkdir()
        r = run(cls.ws, str(KIT / "evals/fixtures/make_export.py"), str(book), str(cls.ws))
        assert r.returncode == 0, r.stderr[-800:]
        # the export without its profile files; its folder still carries the username in its name
        export = next(cls.ws.glob("instagram-lake.days-*"))
        shutil.rmtree(export / "personal_information")
        cls.gather = run(cls.ws, str(S / "gather.py"), "--door", "instagram_account=closed: none in the test",
                         "--door", "browser=closed: none in the test")
        assert cls.gather.returncode == 0, cls.gather.stderr[-800:]
        r = run(cls.ws, str(S / "research.py"))
        assert r.returncode == 0, r.stderr[-800:]
        b = cls.ws / "build"
        (b / "taste.md").write_text((b / "taste.draft.md").read_text())
        p = json.loads((b / "picks.json").read_text())
        for m in p["months"]:
            m["scene"] = "a lake under a ridge"
            m["line"] = [0, 0.6, 1, 0.6]
        (b / "picks.json").write_text(json.dumps(p))
        cls.draft = run(cls.ws, str(S / "storyboard.py"), "draft")
        cls.stats = json.loads((b / "stats.json").read_text())
        board = b / "storyboards/analog-home-movie/board-reel.json"
        cls.year = json.loads(board.read_text())["year"] if cls.draft.returncode == 0 else {}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def edited(self, name, change):
        """Runs the test with build/<name> changed by `change`, then puts the file back."""
        f = self.ws / "build" / name
        before = f.read_text()
        self.addCleanup(f.write_text, before)
        data = json.loads(before)
        change(data)
        f.write_text(json.dumps(data))

    def test_an_export_without_profile_files_shows_no_handle(self):
        self.assertEqual(self.draft.returncode, 0, self.draft.stderr[-800:])
        self.assertIsNone(self.stats["handle"])
        self.assertIn("handle: none", self.gather.stdout)
        y = self.year
        self.assertIsNone(y["handle"])
        shown = [y["title"], y["signoff"], *(r["label"] for r in y["rows"])] + [ln for m in y["months"] for ln in [m["name"], *m["said"]]]
        self.assertEqual([ln["text"] for ln in shown if "@" in ln["text"] or "lake.days" in ln["text"]], [])

    def test_a_stand_in_handle_fails_the_build(self):
        for stand_in in ("your_handle", "@username", "you", "<handle>"):
            with self.subTest(stand_in=stand_in):
                self.edited("stats.json", lambda d: d.update(handle=stand_in))
                for cmd in ("draft", "check"):
                    r = run(self.ws, str(S / "storyboard.py"), cmd)
                    self.assertNotEqual(r.returncode, 0, (cmd, r.stdout[-400:]))
                    self.assertIn("stand-in handle", r.stderr)
                self.doCleanups()

    def test_a_stand_in_handle_in_the_words_on_screen_fails_the_build(self):
        def line(d):
            for mo in d["moments"]:
                mo["line"] = "out on the water with @your_handle"
        self.edited("taste.json", line)
        r = run(self.ws, str(S / "storyboard.py"), "draft")
        self.assertNotEqual(r.returncode, 0, r.stdout[-400:])
        self.assertIn("@your_handle", r.stderr)

    def test_a_delivery_without_a_handle_shows_no_stand_in_anywhere(self):
        b = self.ws / "build"
        for path in (b / "winner.json", b / "film.json"):
            self.addCleanup(path.unlink, missing_ok=True)
        self.addCleanup(shutil.rmtree, self.ws / "out", True)
        r = run(self.ws, str(S / "storyboard.py"), "draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        (b / "winner.json").write_text(json.dumps({"board": "analog-home-movie", "by": "person", "why": ""}))
        # a three-month year is shorter than a reel, so snap names that finding; the film.json it writes is all deliver reads
        r = run(self.ws, str(S / "storyboard.py"), "snap")
        self.assertTrue((b / "film.json").exists(), r.stderr[-800:])
        # the gate refuses a delivery with no film; the page, the caption and the brief are written before it runs
        run(self.ws, str(S / "deliver.py"))
        texts = {name: (self.ws / "out" / name).read_text() for name in ("review.html", "caption.md")}
        texts["brief.md"] = (b / "brief.md").read_text()
        texts["board"] = (b / "storyboards/analog-home-movie/board-reel.json").read_text()
        self.assertEqual({k: re.findall(r"@(?:you|me)\b", v) for k, v in texts.items() if re.search(r"@(?:you|me)\b", v)}, {})
        self.assertIsNone(json.loads(texts["board"])["year"]["handle"])
        self.assertIn("<title>2026 in review</title>", texts["review.html"])

    def test_a_real_handle_from_the_profile_is_shown(self):
        self.edited("stats.json", lambda d: d.update(handle="lake.days"))
        r = run(self.ws, str(S / "storyboard.py"), "draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        y = json.loads((self.ws / "build/storyboards/analog-home-movie/board-reel.json").read_text())["year"]
        # the handle as the export gives it, in the case the look sets its text face in
        self.assertEqual(y["handle"]["text"].lower(), "@lake.days")


if __name__ == "__main__":
    unittest.main()
