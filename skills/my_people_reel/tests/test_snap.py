"""snap cuts only the board that won the vote: with no winner.json it exits naming the ballot and the tally, it takes
no --board in place of the vote, and it writes no film.json either way.

    python3 -I -m unittest discover -s S/tests -p test_snap.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


class Snap(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.run_dir = self.root / "build" / "20260101T000000Z"
        (self.run_dir / "storyboards" / "drive").mkdir(parents=True)
        (self.run_dir / "storyboards" / "drive" / "storyboard.json").write_text('{"bpm": 120, "beats": []}')
        (self.root / "build" / "current").write_text(self.run_dir.name + "\n")

    def snap(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "MPR_RUN"}
        env.update(MPR_WORKSPACE=str(self.root), CSC_DISABLE_KEYCHAIN="1")
        return subprocess.run([sys.executable, str(KIT / "scripts" / "storyboard.py"), "snap", *args], cwd=self.root,
                              env=env, capture_output=True, text=True, timeout=120)

    def test_snap_cuts_only_a_board_that_won_the_vote(self):
        r = self.snap()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vote.py ballot", r.stderr)
        self.assertNotEqual(self.snap("--board", "drive").returncode, 0)
        self.assertFalse((self.run_dir / "film.json").exists())


if __name__ == "__main__":
    unittest.main()
