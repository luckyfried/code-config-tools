"""gather.py finds what the person put in the workspace on its own: a folder of a few photos, and a posts file with
dates, captions, the accounts tagged and the comments under each post (a post with no date left out, saying so); a folder the person names with --photos still wins over both.

    python3 -I -m unittest discover -s S/tests -p test_gather.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
GATHER = KIT / "scripts" / "gather.py"
CLOSED = ["--door", "instagram_account=closed: no Instagram tool", "--door", "browser=closed: no browser tool"]
POSTS = {"owner": "danik", "posts": [
    {"date": "2026-03-14", "media": "photos/garden.jpg", "caption": "Mama's garden", "tagged": ["rosa.kaplan"]},
    {"date": "2026-07-02", "media": "photos/tomatoes.jpg", "caption": "Tomato season at mama's"}]}


def gather(root, *args):
    """Runs gather.py from the workspace root the way the agent does; returns (exit code, library.json, its output)."""
    p = subprocess.run([sys.executable, str(GATHER), *CLOSED, *args], cwd=root, capture_output=True, text=True,
                       env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
    latest = root / "build" / "latest"
    lib = root / "build" / latest.read_text().strip() / "library.json" if latest.exists() else None
    return p.returncode, (json.loads(lib.read_text()) if lib and lib.exists() else None), p.stdout + p.stderr


class Gather(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "photos").mkdir()
        for name in ("garden", "tomatoes", "picnic", "birthday-cake"):
            (self.root / "photos" / f"{name}.jpg").write_bytes(b"jpg")

    def test_a_folder_of_four_photos_is_found(self):
        code, lib, log = gather(self.root)
        self.assertEqual(code, 0, log)
        self.assertEqual(lib["source"], "photos")
        self.assertEqual(len(lib["posts"]), 4)
        self.assertEqual(lib["doors"]["photo_folder"], "open: 4 photos in photos")

    def test_a_posts_file_is_read_with_its_dates_captions_and_tags(self):
        (self.root / "export").mkdir()
        (self.root / "export" / "posts.json").write_text(json.dumps(POSTS))
        code, lib, log = gather(self.root)
        self.assertEqual(code, 0, log)
        self.assertEqual(lib["handle"], "danik")
        self.assertEqual(lib["doors"]["posts_file"], "open: 2 posts in export/posts.json")
        first, second = lib["posts"]
        self.assertEqual((first["caption"], first["tagged"], first["ts"]), ("Mama's garden", ["rosa.kaplan"], 1773446400))
        self.assertEqual(Path(first["media"][0]).resolve(), (self.root / "photos" / "garden.jpg").resolve())
        self.assertEqual(second["tagged"], [])
        self.assertFalse(any("posts" in a for a in lib["assumptions"] if a.startswith("Not in the data")))

    def test_a_posts_file_keeps_its_comments_and_leaves_out_only_the_undated_post(self):
        posts = {"owner": "danik", "posts": [
            {"date": "2026-03-14", "media": "photos/garden.jpg", "caption": "Mama's garden", "tagged": ["rosa.kaplan"],
             "comments": [{"user": "rosa.kaplan", "text": "you pulled them too early"}, {"user": "danik", "text": "they were ready"}]},
            {"media": "photos/picnic.jpg", "caption": "no date on this one"},
            {"date": "2026-07-02", "media": "photos/tomatoes.jpg", "caption": "Tomato season at mama's", "comments": []}]}
        (self.root / "export").mkdir()
        (self.root / "export" / "posts.json").write_text(json.dumps(posts))
        code, lib, log = gather(self.root)
        self.assertEqual(code, 0, log)
        self.assertEqual(lib["source"], "export")
        self.assertEqual(lib["doors"]["posts_file"], "open: 2 posts in export/posts.json")
        self.assertEqual([p["caption"] for p in lib["posts"]], ["Mama's garden", "Tomato season at mama's"])
        self.assertEqual([(c["account"], c["text"]) for c in lib["posts"][0]["thread"]],
                         [("rosa.kaplan", "you pulled them too early"), ("danik", "they were ready")])
        self.assertEqual(lib["posts"][1]["thread"], [])
        left = [a for a in lib["assumptions"] if "no date" in a]
        self.assertEqual(left, ["Left out 1 post in export/posts.json with no date."])
        self.assertIn(left[0], log)
        self.assertFalse(any("comments" in a for a in lib["assumptions"] if a.startswith("Not in the data")))

    def test_photos_named_with_the_flag_win_over_the_posts_file_and_the_largest_folder(self):
        (self.root / "export").mkdir()
        (self.root / "export" / "posts.json").write_text(json.dumps(POSTS))
        (self.root / "theirs").mkdir()
        (self.root / "theirs" / "one.jpg").write_bytes(b"jpg")
        code, lib, log = gather(self.root, "--photos", "theirs")
        self.assertEqual(code, 0, log)
        self.assertEqual(lib["source"], "photos")
        self.assertEqual(lib["doors"]["photo_folder"], "open: 1 photos in theirs")
        self.assertEqual([r["caption"] for r in lib["posts"]], [""])


if __name__ == "__main__":
    unittest.main()
