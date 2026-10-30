"""gather.py links a post's media by the exact path the export names, never by a file of the same name elsewhere; with no
username in the posts nothing stands in for one, and the film's hook and closer show the year alone.

    python3 -I -m unittest discover -s S/tests
"""
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import gather  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
DAY = 86400 * (365 * 56 + 14)  # 2026-01-01


class ExactMedia(unittest.TestCase):
    def test_a_post_links_only_the_file_at_its_own_path(self):
        with tempfile.TemporaryDirectory(dir=KIT / "tests") as d:
            root = Path(d)
            (root / "media" / "posts" / "202601").mkdir(parents=True)
            (root / "media" / "stories" / "202603").mkdir(parents=True)
            (root / "media" / "posts" / "202601" / "a.jpg").write_bytes(b"a")
            (root / "media" / "stories" / "202603" / "b.jpg").write_bytes(b"b")
            md = gather.Media(root)
            self.assertEqual(md.resolve("media/posts/202601/a.jpg"), str((root / "media/posts/202601/a.jpg").resolve()))
            self.assertIsNone(md.resolve("media/posts/202601/b.jpg"))


class NoHandle(unittest.TestCase):
    def test_posts_with_no_handle_draft_a_hook_and_a_closer_with_the_year_alone(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, home, True)
        here = Path.cwd()
        self.addCleanup(os.chdir, here)
        (home / "pulled").mkdir()
        (home / "pulled" / "1.jpg").write_bytes(b"x")
        post = {"ts": DAY + 86400 * 40, "caption": "the bridge at dusk", "media": ["1.jpg"], "lat": 41.15, "lon": -8.61}
        (home / "pulled" / "items.json").write_text(json.dumps({"source": "photos", "posts": [post]}))
        out = io.StringIO()
        with mock.patch.dict(os.environ), mock.patch.object(gather._env, "HOME", home), \
                mock.patch.object(sys, "argv", ["gather.py", "--pulled", "pulled", "--year", "2026"]), \
                mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(gather.main(), 0)
        lib = json.loads((home / "build" / (home / "build" / "RUN").read_text().strip() / "library.json").read_text())
        placeholder = re.compile(r"@|\byou\b|\bNone\b")
        self.assertIsNone(lib["handle"])
        self.assertIsNone(placeholder.search(out.getvalue().split("\n")[0]), out.getvalue())
        self.assertEqual([a for a in lib["assumptions"] if placeholder.search(a)], [])
        # the film from that library: the hook's title and the closer's title are the year, with no handle under them
        src = copy.deepcopy(SOURCE)
        src["handle"] = lib["handle"]
        year = str(src["places"]["year"])
        for fmt in storyboard.FORMATS:
            route = storyboard.plan(src, fmt)["board"]["route"]
            hook = [(ln["name"], ln["text"]) for ln in route["hook"]["kicker"]]
            self.assertEqual(hook, [("title", year)], fmt)
            self.assertEqual(route["closer"]["title"], year, fmt)
            self.assertIsNone(placeholder.search(route["closer"]["signoff"]), fmt)


if __name__ == "__main__":
    unittest.main()
