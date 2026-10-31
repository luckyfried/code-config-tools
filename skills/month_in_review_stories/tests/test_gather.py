"""gather.py finding a post's photograph and its counts in an export.

    python3 -m unittest discover -s S/tests -p 'test_gather.py'
"""
import json
import tempfile
import unittest
from pathlib import Path

import fixture  # noqa: F401  (puts the kit's scripts on the path)
import gather


class Media(unittest.TestCase):
    def test_a_photograph_is_its_exact_path_else_a_file_name_found_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel in ("media/posts/a/x.jpg", "media/reels/b/x.jpg", "media/posts/c/y.jpg"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(b"jpg")
            md = gather.Media(root)
            self.assertEqual(md.resolve("media/reels/b/x.jpg"), str((root / "media/reels/b/x.jpg").resolve()))
            self.assertIsNone(md.resolve("media/stories/x.jpg"))
            self.assertEqual(md.resolve("media/stories/y.jpg"), str((root / "media/posts/c/y.jpg").resolve()))


class Counts(unittest.TestCase):
    def test_a_post_entry_that_carries_its_likes_and_comments_keeps_them(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "content").mkdir()
            (root / "media/posts").mkdir(parents=True)
            (root / "media/posts/a.jpg").write_bytes(b"jpg")
            (root / "media/posts/b.jpg").write_bytes(b"jpg")
            (root / "content/posts_1.json").write_text(json.dumps([
                {"caption": "a", "likes": 1210, "comments": 102, "media": [{"uri": "media/posts/a.jpg", "creation_timestamp": 1790424000, "title": "a"}]},
                {"caption": "b", "media": [{"uri": "media/posts/b.jpg", "creation_timestamp": 1790424100, "title": "b"}]}]))
            got = {p["caption"]: (p["likes"], p["comments"]) for p in gather.read_export(root)["posts"]}
            self.assertEqual(got, {"a": (1210, 102), "b": (None, None)})


class Tables(unittest.TestCase):
    def test_a_posts_table_that_names_their_handle_gives_the_cards_their_handle(self):
        rows = [{"date": "2026-09-02", "caption": "a", "handle": "@noor.frames"}, {"date": "2026-09-05", "caption": "b", "handle": "@noor.frames"},
                {"date": "2026-09-09", "caption": "c", "handle": ""}]
        self.assertEqual(gather.table_handle(rows), "@noor.frames")
        self.assertIsNone(gather.table_handle([{"date": "2026-09-02", "caption": "a"}]))
        self.assertEqual(gather.username(gather.table_handle(rows))[0], "noor.frames")


if __name__ == "__main__":
    unittest.main()
