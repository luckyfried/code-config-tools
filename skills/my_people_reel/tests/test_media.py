"""An export's media: a post's photograph resolves to its own exact path, else to the one file under media/ with its
name; a name two files share resolves to nothing, so no post takes another post's photograph.

    python3 -I -m unittest discover -s S/tests
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gather  # noqa: E402


class Media(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.root)
        for rel in ("media/posts/202601/a.jpg", "media/posts/202602/a.jpg", "media/posts/202603/b.jpg"):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(rel)

    def test_a_shared_name_resolves_only_by_its_exact_path(self):
        m = gather.Media(self.root)
        self.assertEqual(m.resolve("media/posts/202602/a.jpg"), str((self.root / "media/posts/202602/a.jpg").resolve()))
        self.assertIsNone(m.resolve("media/other/a.jpg"))
        self.assertEqual(m.resolve("media/other/b.jpg"), str((self.root / "media/posts/202603/b.jpg").resolve()))


if __name__ == "__main__":
    unittest.main()
