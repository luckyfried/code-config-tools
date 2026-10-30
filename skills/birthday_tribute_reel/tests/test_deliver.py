"""deliver.py never leaves out/ looking delivered before the gate passes: the page says it is not ready until the gate
has passed, so a deliver stopped partway leaves that page, and a green gate takes the banner off. deliver holds the
run's lock while it works and runs its gate in its own process under it. A delivered run is
continued in a copy, and build/latest names the copy only once the copy is whole, so a copy stopped partway is never
the run the next script picks. The gate's critic row counts a cut round only when the vote would count it. A green
deliver's last line is the delivered reel's path from the workspace root, the one the reply names.
On a red gate the last line names the failing checks and no film.

    python3 -I -m unittest discover -s S/tests -p test_deliver.py
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import deliver  # noqa: E402


class Deliver(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        B = self.dir / "build" / "run"
        B.mkdir(parents=True)
        for name, obj in (("library.json", {"handle": "a"}), ("taste.json", {"register": {}}),
                          ("winner.json", {"board": "1", "totals": {"1": 60}}), ("shared.json", {"who": {"handle": "b"}})):
            (B / name).write_text(json.dumps(obj))
        self.out = self.dir / "out"
        self.out.mkdir()
        (self.out / "review.html").write_text("the last delivery, green")
        self.B = B
        for patch in (mock.patch.object(_env, "_RUN", B), mock.patch.object(_env, "_TOOLS", {}),
                      mock.patch.object(deliver, "caption", return_value="a caption"),
                      mock.patch.object(deliver, "brief", return_value="a brief")):
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.dir)

    def gate(self, outcome, during=None):
        def gate_checks(run):
            self.during = (self.out / "review.html").read_text()
            self.run = run
            if during:
                during()
            if isinstance(outcome, BaseException):
                raise outcome
            return ([("vote", True, "a winner")] if outcome == 0 else [("vote", False, "no winner")]), {}
        return mock.patch.object(deliver.qa, "gate_checks", gate_checks)

    def test_a_deliver_stopped_during_the_gate_leaves_a_page_that_is_not_ready(self):
        with self.gate(KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt), redirect_stdout(io.StringIO()):
            deliver.main()
        self.assertIn("Not ready to post.", (self.out / "review.html").read_text())
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["caption.md", "review.html"])
        self.assertEqual((self.B / "brief.md").read_text(), "a brief", "the run's record stays in the run, never in out/")

    def test_a_green_gate_takes_the_banner_off_and_a_red_one_names_what_failed_in_the_record_only(self):
        with self.gate(1), redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        page = (self.out / "review.html").read_text()
        self.assertIn("Not ready to post.", page)
        self.assertNotIn("vote: no winner", page)
        self.assertIn("vote: no winner", (self.B / "brief.md").read_text())
        with self.gate(0), redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertIn("Not ready to post.", self.during)
        self.assertNotIn("class='banner'", (self.out / "review.html").read_text())

    def test_a_green_delivers_last_line_is_the_delivered_reels_path_from_the_workspace_root(self):
        (self.out / "film.mp4").write_bytes(b"the reel")
        printed = io.StringIO()
        with self.gate(0), redirect_stdout(printed):
            self.assertEqual(deliver.main(), 0)
        last = printed.getvalue().splitlines()[-1]
        self.assertEqual(last, "build/run/out/film.mp4")
        self.assertEqual((self.dir / last).read_bytes(), b"the reel")

    def test_a_red_delivers_last_line_names_the_failing_check_and_no_film(self):
        (self.out / "film.mp4").write_bytes(b"the reel")
        printed = io.StringIO()
        with self.gate(1), redirect_stdout(printed):
            self.assertEqual(deliver.main(), 1)
        last = printed.getvalue().splitlines()[-1]
        self.assertEqual(last, "not delivered: the gate failed on vote")
        self.assertNotIn("film.mp4", last)

    @unittest.skipIf(os.name == "nt", "the lock is a flock on POSIX")
    def test_deliver_runs_its_gate_in_its_own_process_under_the_runs_lock(self):
        import fcntl

        def probe():
            with open(self.B / "render" / "render.lock") as f:
                self.held = f.read()
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.held = None
                except OSError:
                    pass
        with self.gate(1, probe), mock.patch("subprocess.run", side_effect=AssertionError("a gate in another process")), \
                redirect_stdout(io.StringIO()):
            deliver.main()
        self.assertTrue(self.run.spawn)
        self.assertTrue((self.held or "").startswith("deliver\t"))


class GateCritic(unittest.TestCase):
    """The gate's critic row takes the cut round for the current reel only as vote.py takes a ballot: every score a
    whole number, every paragraph whole and naming the round's frames, the worst thing named; and it passes only at the
    bar, a mean of 4.5 with none under 4."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.B = self.dir / "build" / "run"
        (self.B / "critic").mkdir(parents=True)
        (self.B / "film.json").write_text(json.dumps({"id": "1"}))
        (self.dir / "out").mkdir()
        (self.dir / "out" / "film.mp4").write_bytes(b"the reel")
        qa = deliver.qa
        for patch in (mock.patch.object(_env, "_RUN", self.B), mock.patch.object(_env, "_TOOLS", {}),
                      mock.patch.object(qa, "timed_checks", return_value=(qa.Checks(), None)),
                      mock.patch.object(qa, "film_checks", return_value=(qa.Checks(), None, None)),
                      mock.patch.object(qa, "shared_check", return_value=(True, "shared"))):
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.dir)

    def critic(self, paragraph, scores=None, worst="the closer's wall sits a little dark under the wish"):
        import vote
        qa = deliver.qa
        frames = self.B / "critic" / "cut-1"
        frames.mkdir(exist_ok=True)
        (frames / "r1-f07-16.25s.png").write_bytes(b"png")
        entry = {"scores": dict(zip(vote.CRITERIA, scores or [4] * len(vote.CRITERIA))), "paragraph": paragraph, "worst": worst}
        cut = {"round": 1, "board": "1", "film": qa.sha(qa.FILM), "frames": str(frames),
               "critics": {c: {"boards": {"film": dict(entry)}} for c in vote.CUT_PANEL}}
        (self.B / "critic" / "cut-1.json").write_text(json.dumps(cut))
        res, _ = qa.gate_checks()
        return next(r for r in res if r[0] == "critic")

    def test_a_round_the_vote_refuses_keeps_the_gate_red(self):
        _, ok, detail = self.critic("the reel is good and the cards read well enough")
        self.assertFalse(ok)
        self.assertIn("paragraph", detail)

    def test_a_whole_round_at_the_bar_that_names_its_frames_passes(self):
        _, ok, detail = self.critic(" ".join(["the cards carry their year and each landing hits its sound in r1-f07"] * 3),
                                    scores=[5, 5, 4, 5, 4, 5, 5])
        self.assertIs(ok, True, detail)

    def test_a_round_of_fours_is_below_the_bar_and_fails_before_the_fix(self):
        _, ok, detail = self.critic(" ".join(["the cards carry their year and each landing hits its sound in r1-f07"] * 3))
        self.assertIs(ok, False, detail)
        self.assertIn("below the bar", detail)

    def test_a_round_that_names_none_of_its_frames_keeps_the_gate_red(self):
        _, ok, detail = self.critic(" ".join(["the cards carry their year and each landing hits its sound"] * 3),
                                    scores=[5] * 7)
        self.assertIs(ok, False, detail)
        self.assertIn("r1-f07", detail)


class DeliveredRun(unittest.TestCase):
    def test_a_copy_of_a_delivered_run_stopped_partway_is_never_named_latest(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        build = Path(tmp.name) / "build"
        (build / "done").mkdir(parents=True)
        (build / "done" / "delivered.json").write_text("{}")
        (build / "latest").write_text("done\n")

        def stopped(src, dst, **kw):
            Path(dst).mkdir()
            raise KeyboardInterrupt

        with mock.patch.object(_env, "BUILD", build), mock.patch.object(_env, "_RUN", None), \
                mock.patch.object(sys, "argv", [str(_env.SKILL / "scripts" / "storyboard.py")]), \
                mock.patch("shutil.copytree", stopped), self.assertRaises(KeyboardInterrupt):
            _env.run_dir()
        self.assertEqual((build / "latest").read_text().strip(), "done")

    def test_reading_a_delivered_run_from_outside_a_kit_command_copies_nothing(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        build = Path(tmp.name) / "build"
        (build / "done").mkdir(parents=True)
        (build / "done" / "delivered.json").write_text("{}")
        (build / "latest").write_text("done\n")
        with mock.patch.object(_env, "BUILD", build), mock.patch.object(_env, "_RUN", None), \
                mock.patch.object(sys, "argv", ["-c"]):
            self.assertEqual(_env.run_dir(), build / "done")
        self.assertEqual(sorted(p.name for p in build.iterdir()), ["done", "latest"])


if __name__ == "__main__":
    unittest.main()
