"""The step after the vote takes only the board that won it, and a new draft starts a new vote: music.py make reads
winner.json alone and refuses with no winner, and storyboard.py draft removes winner.json and vote/scores.json. The
gate's critic row passes only a cut round the vote itself would accept.

    python3 -m unittest discover -s S/tests -p test_vote.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture

import qa  # noqa: E402
import vote  # noqa: E402


def run(ws, script, *args):
    return subprocess.run([sys.executable, str(fixture.SCRIPTS / script), *args], cwd=ws, capture_output=True, text=True,
                          env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))


class Vote(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = fixture.workspace()
        fixture.researched(cls.ws)
        cls.build = cls.ws / "build" / (cls.ws / "build" / "latest").read_text().strip()
        (cls.build / "taste.md").write_text("their month, in prose\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)

    def test_music_is_made_only_for_a_board_that_won_the_vote(self):
        (self.build / "winner.json").unlink(missing_ok=True)
        r = run(self.ws, "music.py", "make")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("vote.py ballot", r.stderr)
        self.assertNotEqual(run(self.ws, "music.py", "make").returncode, 0)
        self.assertFalse((self.build / "music.json").exists())

    def test_a_new_draft_starts_a_new_vote(self):
        (self.build / "vote").mkdir(exist_ok=True)
        (self.build / "winner.json").write_text('{"board": "editorial-quiet"}')
        (self.build / "vote" / "scores.json").write_text("{}")
        r = run(self.ws, "storyboard.py", "draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertFalse((self.build / "winner.json").exists())
        self.assertFalse((self.build / "vote" / "scores.json").exists())

    def test_a_new_draft_drops_what_stood_on_the_old_board(self):
        """music.json, film.json and the board's checks and sheets go with the vote, so preview and render cannot run
        on music made for a board nobody voted for, and the ballot cannot admit a board its checks never saw."""
        run(self.ws, "storyboard.py", "draft")
        sb = self.build / "storyboards"
        for f in (self.build / "music.json", self.build / "film.json", sb / "check.json", sb / "sheets.json"):
            f.write_text('{"ok": true, "boards": {"editorial-quiet": {"ok": true, "findings": []}}}')
        r = run(self.ws, "storyboard.py", "draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        for f in (self.build / "music.json", self.build / "film.json", sb / "check.json", sb / "sheets.json"):
            self.assertFalse(f.exists(), f)
        self.assertTrue((sb / "editorial-quiet" / "storyboard.json").exists())
        self.assertIn("vote.py ballot", run(self.ws, "music.py", "make").stderr)

    def test_a_draft_cut_off_after_the_boards_words_leaves_no_board(self):
        run(self.ws, "storyboard.py", "draft")
        code = ("import os, sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['storyboard.py', 'draft']; import storyboard; "
                "w = storyboard.write_md; storyboard.write_md = lambda *a: (w(*a), os._exit(9)); storyboard.main()")
        r = subprocess.run([sys.executable, "-c", code, str(fixture.SCRIPTS)], cwd=self.ws, capture_output=True, text=True,
                           env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
        self.assertEqual(r.returncode, 9, r.stderr[-800:])
        self.assertFalse((self.build / "storyboards" / "editorial-quiet" / "storyboard.json").exists())
        for script, args in (("storyboard.py", ["check"]), ("film.py", ["preview"]), ("vote.py", ["ballot"])):
            self.assertNotEqual(run(self.ws, script, *args).returncode, 0, script)
        self.assertEqual(run(self.ws, "storyboard.py", "draft").returncode, 0)

    def test_the_bed_music_json_names_stands_until_a_new_one_is_named(self):
        run(self.ws, "storyboard.py", "draft")
        (self.build / "winner.json").write_text('{"board": "editorial-quiet"}')
        bed = self.build / "music" / "source-1.wav"
        bed.parent.mkdir(exist_ok=True)
        bed.write_bytes(b"the bed music.json named")
        named = json.dumps({"file": str(bed.resolve())})
        (self.build / "music.json").write_text(named)
        self.assertNotEqual(run(self.ws, "music.py", "make", "--seconds", "-1").returncode, 0)
        self.assertEqual((self.build / "music.json").read_text(), named)
        self.assertEqual(bed.read_bytes(), b"the bed music.json named")
        self.assertEqual(run(self.ws, "music.py", "make", "--seconds", "2").returncode, 0)
        new = Path(json.loads((self.build / "music.json").read_text())["file"])
        self.assertNotEqual(new, bed.resolve())
        self.assertGreater(new.stat().st_size, 1000)
        self.assertEqual(new.name, "bed.wav")

    def test_the_gate_takes_only_a_cut_round_the_vote_accepts(self):
        run = Path(tempfile.mkdtemp(dir=self.ws.parent))
        (run / "critic").mkdir()
        full = " ".join(["the cut holds its moments long enough to read and the red line carries every turn"] * 2)

        def row(paragraph):
            data = vote.blank(vote.CUT_PANEL, ["film"])
            data["film"] = vote.fingerprint(run)
            for i, e in enumerate(data["critics"].values()):
                e["boards"]["film"] = {"scores": {k: 4 for k in vote.CRITERIA}, "paragraph": paragraph if i == 0 else full}
            (run / "critic" / "cut-1.json").write_text(json.dumps(data))
            c = qa.Checks()
            qa.gate_checks(run, c)
            return next(r for r in c.rows if r["check"] == "critic")

        short = row("the cut is fine and the music works for me")
        self.assertFalse(short["pass"])
        self.assertIn("paragraph", short["detail"])
        self.assertTrue(row(full)["pass"])
        # a score under the bar never fails the gate: the row states every rule against the bar
        data = json.loads((run / "critic" / "cut-1.json").read_text())
        data["critics"]["person"]["boards"]["film"]["scores"]["R6"] = 2
        (run / "critic" / "cut-1.json").write_text(json.dumps(data))
        c = qa.Checks()
        qa.gate_checks(run, c)
        got = next(r for r in c.rows if r["check"] == "critic")
        self.assertTrue(got["pass"], got["detail"])
        self.assertIn("R6 2", got["detail"])
        self.assertIn("a mean of 4.5 with none under 4", got["detail"])

    def test_the_cut_is_scored_on_the_seven_rules_and_a_rule_not_read_never_meets_the_bar(self):
        self.assertEqual(list(vote.CRITERIA), [f"R{i}" for i in range(1, 8)])
        self.assertEqual(set(vote.LEVERS), {"R1", "R3", "R4", "R5", "R6"})
        every = {k: 5 for k in vote.CRITERIA}
        self.assertTrue(vote.against_bar(every)[0])
        self.assertFalse(vote.against_bar(dict(every, R2=vote.NOT_READ))[0])
        self.assertFalse(vote.against_bar(dict(every, R5=3))[0])
        self.assertFalse(vote.against_bar({k: 4 for k in vote.CRITERIA})[0])
        self.assertIn("R2 not read", vote.against_bar(dict(every, R2=vote.NOT_READ))[2])

    def test_a_cut_under_the_bar_is_fixed_once_then_delivered_as_the_best_cut(self):
        d = self.build / "critic"
        d.mkdir(exist_ok=True)
        words = lambda n: " ".join(f"round {n} frame read of the line climbing the wall over the photographs as the camera holds" for _ in range(2))

        def cut(n, scores):
            data = vote.blank(vote.CUT_PANEL, ["film"])
            data.update(round=n, film="f", fixed="the shots rewritten from each photograph" if n > 1 else None)
            for c, e in data["critics"].items():
                e["boards"]["film"] = {"scores": dict(scores), "paragraph": f"{c} {words(n)}"}
            (d / f"cut-{n}.json").write_text(json.dumps(data))

        try:
            cut(1, dict({k: 5 for k in vote.CRITERIA}, R6=3, R2=3))
            r = run(self.ws, "vote.py", "verdict")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("FIX ONCE", r.stdout)
            self.assertIn("R6 at 3", r.stdout)
            cut(2, dict({k: 5 for k in vote.CRITERIA}, R2=3))
            r = run(self.ws, "vote.py", "verdict")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("SPENT", r.stdout)
            self.assertIn("R2 3", r.stdout)
            cut(2, {k: 5 for k in vote.CRITERIA})
            r = run(self.ws, "vote.py", "verdict")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("AT THE BAR", r.stdout)
            # round 2 reads the new cut: a paragraph repeated from round 1 is refused
            data = json.loads((d / "cut-2.json").read_text())
            data["critics"]["person"]["boards"]["film"]["paragraph"] = f"person {words(1)}"
            (d / "cut-2.json").write_text(json.dumps(data))
            r = run(self.ws, "vote.py", "verdict")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("the last round's", r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_rule_with_no_lever_is_a_spent_budget_never_a_blocked_render(self):
        d = self.build / "critic"
        d.mkdir(exist_ok=True)
        try:
            data = vote.blank(vote.CUT_PANEL, ["film"])
            data.update(round=1, film="f", fixed=None)
            para = " ".join(["the wall and the line read well but the photographs sit flat under a plain push"] * 2)
            for e in data["critics"].values():
                e["boards"]["film"] = {"scores": dict({k: 5 for k in vote.CRITERIA}, R2=3, R7=vote.NOT_READ), "paragraph": para}
            (d / "cut-1.json").write_text(json.dumps(data))
            r = run(self.ws, "vote.py", "verdict")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("SPENT", r.stdout)
            self.assertIn("R7 not read", r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_timed_read_nobody_can_make_says_so_and_a_failed_one_is_stated(self):
        board = {"style": "editorial-quiet", "reel": {}}
        r = Path(tempfile.mkdtemp(dir=self.ws.parent))
        (r / "critic").mkdir()
        (r / "film.json").write_text(json.dumps(board))
        import studio
        reads = {k: {"pass": True, "read": "x"} for k in vote.READS}
        reads["sound"] = {"pass": vote.NOT_READ, "read": "x"}
        reads["held"] = {"pass": False, "read": "x"}
        (r / "critic" / "timed.json").write_text(json.dumps({"hash": studio.board_hash(board), "pass": False, "reads": reads}))
        c = qa.Checks()
        qa.gate_checks(r, c)
        got = next(x for x in c.rows if x["check"] == "timed")
        self.assertTrue(got["pass"], got["detail"])
        self.assertIn("sound not read", got["detail"])
        self.assertIn("held fail", got["detail"])

    def test_render_refuses_a_board_drafted_from_another_taste(self):
        self.assertEqual(run(self.ws, "storyboard.py", "draft").returncode, 0)
        (self.build / "winner.json").write_text('{"board": "editorial-quiet"}')
        taste = self.build / "taste.json"
        before = taste.read_text()
        try:
            r = run(self.ws, "film.py", "render")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("timed read is not made", r.stderr)
            t = json.loads(before)
            t["moments"][0]["line"] = "a new line for the first moment"
            taste.write_text(json.dumps(t))
            r = run(self.ws, "film.py", "render")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("taste.json changed since the board was drafted", r.stderr)
        finally:
            taste.write_text(before)

    def test_draft_refuses_a_moment_whose_shot_is_unwritten(self):
        taste = self.build / "taste.json"
        before = taste.read_text()
        try:
            t = json.loads(before)
            day = t["moments"][1]["day"]
            t["moments"][1]["shot"]["move"] = ""
            taste.write_text(json.dumps(t))
            r = run(self.ws, "storyboard.py", "draft")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(f"day {day} has no shot subject or move", r.stderr)
        finally:
            taste.write_text(before)


class Gate(unittest.TestCase):
    def test_check_and_gate_each_keep_the_others_record(self):
        run_ = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        (run_ / "qa").mkdir()
        (run_ / "qa" / "gate.json").write_text('{"pass": true}')
        qa.report(qa.checks(run_, False), run_ / "qa" / "check.json", False)
        self.assertEqual((run_ / "qa" / "gate.json").read_text(), '{"pass": true}')
        self.assertTrue((run_ / "qa" / "check.json").exists())
        shutil.rmtree(run_, ignore_errors=True)

    def test_out_holds_the_deliverables_and_nothing_else(self):
        run_ = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        out = run_ / "out"
        (out / "cards").mkdir(parents=True)
        for f in ("film.mp4", "cover.png", "caption.md", "review.html", "cards/01-story.png", "cards/01-story.mp4"):
            (out / f).write_text("{}")
        deliver = lambda: next(r for r in (lambda c: (qa.gate_checks(run_, c), c.rows)[1])(qa.Checks()) if r["check"] == "deliver")
        self.assertTrue(deliver()["pass"], deliver()["detail"])
        for f in ("brief.md", "template.json"):
            (out / f).write_text("{}")
            got = deliver()
            self.assertFalse(got["pass"], f)
            self.assertIn(f, got["detail"])
            (out / f).unlink()
        (out / "storyboard-drive.png").write_text("x")
        got = deliver()
        self.assertFalse(got["pass"])
        self.assertIn("storyboard-drive.png", got["detail"])
        shutil.rmtree(run_, ignore_errors=True)

    def test_the_effects_sit_eight_lu_under_the_music(self):
        import music
        self.assertEqual(music.FX_UNDER_BED_LU, 8)
        self.assertFalse(qa.mixed({"sound_cues": 7, "bed_lufs": -23.0, "fx_lufs": -30.9}, 5)[0])
        self.assertTrue(qa.mixed({"sound_cues": 7, "bed_lufs": -23.0, "fx_lufs": -31.0}, 5)[0])
        self.assertTrue(qa.mixed({"sound_cues": 7, "bed_lufs": -23.0, "fx_lufs": -30.97}, 5)[0])

    def test_the_music_stops_where_the_ask_lands(self):
        self.assertTrue(qa.stopped([(1.0, 1.5), (13.1, None)], 13.0, 15.0)[0])
        self.assertFalse(qa.stopped([(1.0, 1.5), (14.2, None)], 13.0, 15.0)[0])
        self.assertFalse(qa.stopped([(13.1, 14.0)], 13.0, 15.0)[0])


if __name__ == "__main__":
    unittest.main()


class Caption(unittest.TestCase):
    def test_the_drafted_caption_says_the_count_as_the_hook_does(self):
        import deliver
        taste = {"month": {"name": "September"}, "register": {"lowercase": True, "hashtags": []}}
        with tempfile.TemporaryDirectory() as d:
            cap = deliver.caption(Path(d), taste, 3)
        self.assertTrue(cap.startswith("my september, in three stories\n"), cap)
