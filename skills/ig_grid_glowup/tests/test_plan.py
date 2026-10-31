"""The plan's draft on a grid whose posts lack their photos: a post with no measured photo is never the post a new one
follows, and a grid with no measured photo at all gives every new post nothing to follow, while the draft still
writes plan.json and plan.md. With no grid at all (a folder of photos and no feed) it plans nine posts, and
plan.md says there was no feed to compare against.

    python3 -I -m unittest discover -s S/tests -p test_plan.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import plan  # noqa: E402

TS = 1792698717
COLORS = ((180, 120, 90), (90, 140, 170), (200, 170, 60), (110, 160, 90))


class Draft(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def draft(self, measured, grid=9, colors=COLORS):
        """plan.cmd_draft on a photo to post per color beside a grid of `grid` posts where only the positions in
        `measured` carry a measured photo: the slots of plan.json."""
        from PIL import Image
        Path("photos").mkdir()
        pool = []
        for i, rgb in enumerate(colors):
            # one name per photo, never `x-0`, `x-1`: those are one carousel's slides, and the draft takes one of them
            p = self.dir / "photos" / f"{chr(97 + i)}.jpg"
            Image.new("RGB", (400, 500), rgb).save(p)
            pool.append({"photo": str(p), "src": str(p), "kind": "photo", "ts": TS + i, "fit": 0.9 - 0.1 * i,
                         "lab": [40 + 12 * i, 10 - 6 * i, 20 - 8 * i], "bright": 0.5, "detail": 0.05,
                         "focal": [0.5, 0.45], "w": 400, "h": 500})
        cells = [{"pos": i, "kind": "post", "ts": TS - 86400 * i, "caption": "", "saves": None, "flags": [],
                  "a": {"lab": [45 + 3 * i, 5, 15]} if i in measured else None} for i in range(grid)]
        _env.write_json("grid.json", {"cells": cells})
        _env.write_json("picks.json", {"pool": pool})
        _env.write_json("library.json", {"handle": "you", "photos": [{"ts": r["ts"], "caption": "", "media": [r["src"]]}
                                                                    for r in pool]})
        _env.write_json("taste.json", {})
        Path("taste.md").write_text("# taste\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(plan.cmd_draft(None), 0)
        self.assertTrue(Path("plan.md").exists())
        return json.loads(Path("plan.json").read_text())["slots"]

    def test_a_grid_post_with_no_photo_is_never_the_post_a_new_one_follows(self):
        slots = self.draft(measured={0, 1, 2, 3, 5, 6, 7, 8})
        self.assertEqual(len(slots), 4)
        self.assertNotIn(5, [s["follows"] for s in slots])
        self.assertTrue(all(isinstance(s["follows"], int) for s in slots))

    def test_a_grid_with_no_photo_at_all_gives_the_new_posts_nothing_to_follow(self):
        slots = self.draft(measured=set())
        self.assertEqual([s["follows"] for s in slots], [None] * 4)

    def test_with_no_grid_at_all_the_draft_plans_nine_and_says_there_was_no_feed(self):
        colors = [(40 + 17 * i, 200 - 13 * i, 90 + 11 * i) for i in range(12)]
        slots = self.draft(measured=set(), grid=0, colors=colors)
        self.assertEqual([s["n"] for s in slots], list(range(1, 10)))
        self.assertEqual([s["follows"] for s in slots], [None] * 9)
        self.assertIn("There was no feed to compare against", Path("plan.md").read_text())


if __name__ == "__main__":
    unittest.main()
