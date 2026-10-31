"""gather.py's media lookup: an export's uri finds its own photograph, never another post's."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import gather  # noqa: E402


class MediaLookup(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.root = Path(self.d.name)
        for rel in ("media/posts/202601/a.jpg", "media/posts/202602/a.jpg", "media/other/b.jpg"):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(b"x")

    def tearDown(self):
        self.d.cleanup()

    def test_a_name_in_two_folders_finds_nothing_and_the_exact_path_still_wins(self):
        md = gather.Media(self.root)
        self.assertIsNone(md.resolve("media/posts/202603/a.jpg"))
        self.assertEqual(md.resolve("media/posts/202602/a.jpg"), str((self.root / "media/posts/202602/a.jpg").resolve()))
        self.assertEqual(md.resolve("media/moved/b.jpg"), str((self.root / "media/other/b.jpg").resolve()))


if __name__ == "__main__":
    unittest.main()
