"""The motion system's pure modules, tested by node's own runner."""
import shutil
import subprocess
import unittest
from pathlib import Path

DRIVE = Path(__file__).resolve().parents[1] / "motion" / "studio" / "drive"


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestMotion(unittest.TestCase):
    def test_drive_plan(self):
        r = subprocess.run(["node", "--test", str(DRIVE / "plan.test.ts")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
