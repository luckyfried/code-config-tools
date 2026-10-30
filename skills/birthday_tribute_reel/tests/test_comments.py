"""The words beside a card's photograph are the comments the two left under that post: a comment alone is shown, a
comment and its answer show as the pair, and a comment by anyone else stays off the screen.

    python3 -I -m unittest discover -s S/tests -p test_comments.py

The year is a posts file of four drawn photographs, run through gather.py and research.py in a temporary workspace.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "scripts"))
import compose  # noqa: E402

POSTS = {"owner": "tomas.ferr", "posts": [
    {"date": "2025-01-10", "media": "photos/beach.jpg", "caption": "cold sand, warm Ana", "tagged": ["ana.vale"],
     "comments": [{"user": "ana.vale", "text": "my socks are still wet"}]},
    {"date": "2025-04-12", "media": "photos/cabin.jpg", "caption": "cabin, snow, no signal, perfect", "tagged": ["ana.vale"],
     "comments": [{"user": "ana.vale", "text": "best no-signal week"}, {"user": "tomas.ferr", "text": "the fire did all the work"}]},
    {"date": "2025-07-20", "media": "photos/road.jpg", "caption": "Ana drives, i choose the music", "tagged": ["ana.vale"],
     "comments": [{"user": "rui.p", "text": "take me with you next time"}]},
    {"date": "2025-10-02", "media": "photos/ramen.jpg", "caption": "ramen again", "tagged": ["ana.vale"], "comments": []}]}
COLORS = {"beach": ((214, 196, 160), (40, 96, 150)), "cabin": ((236, 240, 244), (70, 52, 40)),
          "road": ((180, 150, 110), (52, 60, 66)), "ramen": ((92, 60, 40), (220, 170, 90))}
WS = B = None


def setUpModule():
    global WS, B
    from PIL import Image, ImageDraw
    WS = Path(tempfile.mkdtemp(prefix="bt-comments-", dir=os.environ.get("TMPDIR")))
    (WS / "photos").mkdir()
    for name, (ground, subject) in COLORS.items():
        im = Image.new("RGB", (1080, 1350), ground)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1080, 520), fill=tuple(min(255, c + 30) for c in ground))
        d.ellipse((380, 640, 700, 1200), fill=subject)
        im.save(WS / "photos" / f"{name}.jpg", quality=90)
    (WS / "export").mkdir()
    (WS / "export" / "posts.json").write_text(json.dumps(POSTS))
    env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
    run = lambda *a: subprocess.run([sys.executable, *map(str, a)], cwd=WS, env=env, check=True, capture_output=True, text=True)
    run(S / "scripts" / "gather.py", "--door", "instagram_account=closed: none in the test", "--door", "browser=closed: none in the test")
    run(S / "scripts" / "research.py", "--who", "@ana.vale", "--occasion", "our anniversary")
    B = WS / "build" / (WS / "build" / "latest").read_text().strip()
    os.chdir(WS)


def tearDownModule():
    os.chdir(S)
    shutil.rmtree(WS, ignore_errors=True)


def post_of(caption):
    shared = json.loads((B / "shared.json").read_text())
    return next(x["id"] for x in shared["items"] if x["caption"] == caption)


def curated(name, moments):
    """A copy of the run folder whose taste.json names `moments` as the year's, as the agent curates them; returns its Ctx."""
    d = WS / "build" / name
    shutil.copytree(B, d, symlinks=True)
    taste = json.loads((B / "taste.json").read_text())
    taste["moments"] = moments
    taste["written_by"] = "the test"
    (d / "taste.json").write_text(json.dumps(taste))
    return compose.Ctx(d)


class Comments(unittest.TestCase):
    def setUp(self):
        self.beach, self.cabin, self.road = (post_of(c) for c in ("cold sand, warm Ana", "cabin, snow, no signal, perfect",
                                                                    "Ana drives, i choose the music"))

    def talk(self, board):
        return {b["post"]: [(t["by"], t["text"]) for t in b["talk"]] for b in board["beats"] if b["form"] == "moment"}

    def test_research_drafts_each_moment_with_the_comments_under_its_post(self):
        talk = {m["post"]: [(t["by"], t["text"]) for t in m["talk"]] for m in json.loads((B / "taste.json").read_text())["moments"]}
        self.assertEqual(talk[self.beach], [("ana.vale", "my socks are still wet")], "a comment alone is drafted")
        self.assertEqual(talk[self.cabin], [("ana.vale", "best no-signal week"), ("tomas.ferr", "the fire did all the work")])
        self.assertEqual(talk[self.road], [], "a comment by anyone else is never drafted")

    def test_a_comment_alone_is_on_its_card_a_pair_shows_as_a_pair_and_no_one_else_is(self):
        ctx = compose.Ctx(B)
        board = compose.finish(ctx, compose.plan(ctx, "scrapbook"), "1")
        talk = self.talk(board)
        self.assertEqual(talk[self.beach], [("ana.vale", "my socks are still wet")])
        self.assertEqual(talk[self.cabin], [("ana.vale", "best no-signal week"), ("tomas.ferr", "the fire did all the work")])
        self.assertEqual(talk[self.road], [])
        self.assertNotIn("take me with you", json.dumps(board))
        for r in board["photos"].values():
            r["subject"] = [0.33, 0.46, 0.67, 0.9]
        cards = {c["post"]: c for c in compose.lay(board, "reel")["film"]["cards"]}
        said = lambda post: " ".join(l["text"] for l in cards[post]["lines"] if str(l.get("name") or "").startswith("talk"))
        self.assertEqual(said(self.beach), "my socks are still wet")
        self.assertEqual(said(self.cabin), "best no-signal week the fire did all the work")
        self.assertEqual(said(self.road), "")

    def test_a_curated_moment_keeps_only_the_comments_left_under_its_own_post(self):
        ms = {m["post"]: dict(m) for m in json.loads((B / "taste.json").read_text())["moments"]}
        ms[self.road]["talk"] = [{"by": "rui.p", "text": "take me with you next time"},
                                 {"by": "ana.vale", "text": "my socks are still wet"}]
        board = compose.plan(curated("curated", list(ms.values())), "scrapbook")
        talk = self.talk(board)
        self.assertEqual(talk[self.beach], [("ana.vale", "my socks are still wet")])
        self.assertEqual(talk[self.road], [], "a line from another post or by anyone else stays off the card")


if __name__ == "__main__":
    unittest.main()
