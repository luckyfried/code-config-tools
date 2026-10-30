"""gather.py finds each post's photograph: where the download says first, then by a file name only one file carries;
the handle is the one the data names, and none when it names none.

    python3 -I -m unittest discover -s S/tests
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import gather  # noqa: E402


class Resolve(unittest.TestCase):
    def test_the_exact_path_wins_and_a_shared_name_finds_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root, photos = Path(d) / "export", Path(d) / "photos"
            for rel in ("media/posts/202602/a.jpg", "media/posts/202605/a.jpg", "media/posts/202605/b.jpg", "media/posts/202602/e.jpg"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(b"x")
            for rel in ("one/c.jpg", "one/d.jpg", "two/d.jpg", "one/e.jpg"):
                (photos / rel).parent.mkdir(parents=True, exist_ok=True)
                (photos / rel).write_bytes(b"x")
            md = gather.Media(root, photos)
            got = {uri: md.resolve(uri) for uri in ("media/posts/202602/e.jpg", "media/posts/202609/a.jpg", "media/posts/202609/b.jpg",
                                                    "media/posts/202609/c.jpg", "media/posts/202609/d.jpg")}
            self.assertEqual(got, {"media/posts/202602/e.jpg": str((root / "media/posts/202602/e.jpg").resolve()),
                                   "media/posts/202609/a.jpg": None,
                                   "media/posts/202609/b.jpg": str((root / "media/posts/202605/b.jpg").resolve()),
                                   "media/posts/202609/c.jpg": str((photos / "one/c.jpg").resolve()),
                                   "media/posts/202609/d.jpg": None})



class Handle(unittest.TestCase):
    def library(self, items):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ws = Path(d)
            (ws / "pulled").mkdir()
            (ws / "pulled" / "a.jpg").write_bytes(b"x")
            posts = [{"ts": 1767268800 + i * 86400 * 20, "caption": f"day {i}", "media": ["a.jpg"], "likes": i} for i in range(14)]
            (ws / "pulled" / "items.json").write_text(json.dumps(dict(items, posts=posts)))
            here = os.getcwd()
            try:
                with mock.patch.object(_env, "WORKSPACE", ws), mock.patch.object(sys, "argv", ["gather.py", "--root", str(ws)]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    gather.main()
                return json.loads(Path("library.json").read_text())
            finally:
                os.chdir(here)

    def test_the_handle_is_the_one_the_data_names_and_none_when_it_names_none(self):
        self.assertEqual(self.library({"handle": "juno.outside"})["handle"], "juno.outside")
        self.assertIsNone(self.library({})["handle"])

class Download(unittest.TestCase):
    def test_a_posts_list_from_the_download_in_a_folder_of_its_own_is_read_with_the_counts_it_carries(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ws = Path(d)
            entries = []
            for i in range(12):
                uri = f"media/posts/2026{i % 9 + 1:02d}/p{i}.jpg"
                (ws / "ig" / uri).parent.mkdir(parents=True, exist_ok=True)
                (ws / "ig" / uri).write_bytes(b"x")
                entries.append({"media": [{"uri": uri, "creation_timestamp": 1767268800 + i * 86400 * 20, "title": f"day {i}"}],
                                "likes": 100 + i, "comments": i})
            (ws / "ig" / "posts_1.json").write_text(json.dumps(entries))
            here = os.getcwd()
            try:
                with mock.patch.object(_env, "WORKSPACE", ws), \
                        mock.patch.object(sys, "argv", ["gather.py", "--root", str(ws), "--year", "2026"]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertIn(gather.main(), (None, 0))
                lib = json.loads(Path("library.json").read_text())
            finally:
                os.chdir(here)
            self.assertEqual(sorted((p["likes"], p["comments"]) for p in lib["posts"]), [(100 + i, i) for i in range(12)])
            self.assertTrue(all(p["media"] for p in lib["posts"]))


if __name__ == "__main__":
    unittest.main()
