"""deliver.py ends, on a passing gate, with the reel's path from the project's root on a line of its own: the path the
reply names first, copied rather than typed. With no username in the data, the review page and the brief are titled
with the year and its places alone.

    python3 -I -m unittest discover -s tests -p test_reply_path.py
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import deliver  # noqa: E402
import qa  # noqa: E402

BRIEF = deliver.brief


class LastLine(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve()
        run = self.home / "build" / "20261026-014049"
        (run / "out").mkdir(parents=True)
        here = Path.cwd()
        os.chdir(run)
        self.addCleanup(os.chdir, here)
        for name, obj in (("library.json", {"handle": "maren", "year": 2025}), ("taste.json", {"year": 2025}),
                          ("winner.json", {"board": "swiss-grid"}), ("places.json", {"places": [{"name": "Lisbon"}]})):
            Path(name).write_text(json.dumps(obj))
        for patch in (mock.patch.object(deliver, "brief", lambda *a: "brief"), mock.patch.object(deliver, "caption", lambda *a: "caption"),
                      mock.patch.object(deliver._env, "enter_run"), mock.patch.object(deliver._env, "HOME", self.home),
                      mock.patch.object(sys, "argv", ["deliver.py"])):
            patch.start()
            self.addCleanup(patch.stop)

    def deliver(self, ok):
        res = qa.Checks()
        res("format", ok, "out/film.mp4: 1080x1920")
        out = io.StringIO()
        with mock.patch.object(qa, "gate_checks", return_value=(res, {"hash": "h"})), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            code = deliver.main()
        return code, out.getvalue().splitlines()

    def test_the_last_line_is_the_reels_path_from_the_projects_root(self):
        code, lines = self.deliver(True)
        self.assertEqual((code, lines[-1]), (0, "build/20261026-014049/out/film.mp4"))

    def test_with_no_handle_the_page_and_the_brief_are_titled_with_the_year_alone(self):
        Path("library.json").write_text(json.dumps({"handle": None, "year": 2025}))
        code, _ = self.deliver(True)
        page = Path("out/review.html").read_text()
        titles = re.findall(r"<title>(.*?)</title>|<h1>(.*?)</h1>", page)
        brief = BRIEF({"handle": None, "year": 2025}, {}, {"places": [{"name": "Lisbon"}]}, {"board": "swiss-grid"}, {}, {}, [], []).splitlines()[0]
        self.assertEqual(code, 0)
        self.assertEqual(sorted(t or h for t, h in titles), ["2025 in 1 places", "2025 in 1 places"])
        self.assertEqual(brief, "# 2025 in 1 places: how this was made")

    def test_a_failed_gate_ends_on_the_failing_checks_name_and_no_path(self):
        code, lines = self.deliver(False)
        self.assertEqual((code, lines[-1]), (1, "not ready: the gate failed on format"))


class Brief(unittest.TestCase):
    def test_an_unread_score_is_stated_as_unread_and_never_reads_as_a_placeholder(self):
        cut = {"round": 1, "critics": {"person": {"boards": {"film": {"scores": {"R4": 4, "R5": None}}}}}}
        text = BRIEF({"handle": "maren", "year": 2025}, {}, {"places": [{"name": "Lisbon"}]}, {"board": "swiss-grid"}, {}, {}, [cut], [])
        line = next(ln for ln in text.splitlines() if ln.startswith("- Round 1,"))
        self.assertIn("R5 unread", line)
        self.assertEqual([m.group(0) for m in qa.PLACEHOLDER.finditer(line)], [])


if __name__ == "__main__":
    unittest.main()
