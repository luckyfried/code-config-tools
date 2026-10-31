"""The pick cannot be skipped: storyboard.py snap cuts only the look winner.json names and refuses before anything is
cut without it, and a new draft removes the old pick and the old scores, so a look drafted again is picked again."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fixture  # noqa: E402

KIT = HERE.parent


def run(ws, *args):
    env = dict(os.environ, BRAND_RUN=str(ws), CSC_DISABLE_KEYCHAIN="1")
    return subprocess.run([sys.executable, "-I", str(KIT / "scripts" / "storyboard.py"), *args], cwd=ws, env=env,
                          capture_output=True, text=True)


class Snap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.ws = fixture.make(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_snap_cuts_only_a_look_that_was_picked(self):
        r = run(self.ws, "snap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vote.py pick", r.stderr)
        self.assertFalse((self.ws / "film.json").exists())

    def test_a_new_draft_starts_a_new_pick(self):
        (self.ws / "vote").mkdir()
        (self.ws / "winner.json").write_text('{"board": "a"}')
        (self.ws / "vote" / "scores.json").write_text("{}")
        run(self.ws, "draft")
        self.assertFalse((self.ws / "winner.json").exists())
        self.assertFalse((self.ws / "vote" / "scores.json").exists())


if __name__ == "__main__":
    unittest.main()
