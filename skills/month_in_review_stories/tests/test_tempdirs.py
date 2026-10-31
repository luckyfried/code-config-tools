"""The suite leaves nothing under TMPDIR: every folder a test makes goes when its test process ends.

    python3 -m unittest discover -s S/tests -p 'test_tempdirs.py'
"""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class TempDirs(unittest.TestCase):
    def test_a_workspace_and_a_test_folder_are_gone_when_the_process_ends(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import fixture; "
                "print(fixture.workspace()); print(fixture.tempdir('mir-posts-'))")
        r = subprocess.run([sys.executable, "-B", "-c", code, str(HERE)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        made = [Path(line) for line in r.stdout.split()]
        self.assertEqual(len(made), 2)
        self.assertEqual([p for p in made if p.exists()], [])


if __name__ == "__main__":
    unittest.main()
