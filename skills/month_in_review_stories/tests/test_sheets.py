"""storyboard.py sheets renders only a board whose check is green: with no check.json or a failed one it says so in one
line and exits nonzero before it takes the lock or touches a still; with a green one it goes on to the render.

    python3 -m unittest discover -s S/tests -p test_sheets.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import fixture

import _env  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402


@contextlib.contextmanager
def held(work, name):
    Path(work).mkdir(parents=True, exist_ok=True)
    yield None


def made(jobs, work, name, board=None, run=None, hold=None):
    from PIL import Image
    for j in jobs:
        Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 4)).save(j["out"])
    return {"failed": 0, "exit": 0, "findings": []}


class Sheets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = fixture.workspace()
        fixture.researched(cls.ws)
        cls.build = fixture.build(cls.ws)
        (cls.build / "taste.md").write_text("their month, in prose\n")
        fixture.run(cls.ws, "storyboard.py", "draft")
        cls.boards = cls.build / "storyboards"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)

    def setUp(self):
        (self.boards / "check.json").unlink(missing_ok=True)
        shutil.rmtree(self.boards / "render", ignore_errors=True)

    def sheets(self):
        return subprocess.run([sys.executable, str(fixture.SCRIPTS / "storyboard.py"), "sheets"], cwd=self.ws,
                              env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"), capture_output=True, text=True)

    def test_a_board_with_no_check_or_a_failed_one_is_refused_before_the_lock(self):
        for check in (None, {"ok": False, "boards": {}}):
            if check is not None:
                (self.boards / "check.json").write_text(json.dumps(check))
            r = self.sheets()
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")
            self.assertEqual(r.stderr.strip().splitlines(),
                             ["the board has not passed its check: run storyboard.py check first and fix what it fails"])
            self.assertFalse((self.boards / "render").exists())
            self.assertFalse((self.boards / "editorial-quiet" / "rest").exists())

    def test_a_green_check_goes_on_to_the_render(self):
        (self.boards / "check.json").write_text(json.dumps({"ok": True, "boards": {}}))
        render = mock.Mock(side_effect=made)
        with mock.patch.object(_env, "run", lambda: self.build), mock.patch.object(studio, "lock", held), \
                mock.patch.object(studio, "render", render), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(storyboard.sheets(None), 0)
        render.assert_called_once()
        self.assertTrue(render.call_args.args[0])
        self.assertTrue(json.loads((self.boards / "sheets.json").read_text())["ok"])
        self.assertTrue((self.boards / "editorial-quiet" / "sheet.png").exists())


if __name__ == "__main__":
    unittest.main()
