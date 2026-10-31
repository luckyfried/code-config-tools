"""The kit's commands around the shared chunk module: snap cuts only a board that won the vote and a new draft starts a
new vote; film.py render takes the run's lock before it writes and fills out/ only once every still rendered; deliver.py
leaves a page that says the run is not ready until its gate passes. A render removes the delivered page before out/
changes, keeps the last set there when a still fails, reports the cut and only its latest attempt, and removes its proof
(render-report.json and engine.json) while it moves files into out/ and publishes it only after the last move; the
film carries the master music.json names; cut.json certifies a cut only once its strips and its checks pass.

    python3 -I -m unittest discover -s S/tests -p test_render.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402

# render.py as the kit's invoke starts it (`python3 render.py --jobs JOBS.json`): a still becomes a one-frame picture,
# unless its file name is in FAKE_FAIL, which it reports as a RENDER_ERROR.
FAKE = r"""
import json, os, subprocess, sys
from pathlib import Path
spec = json.loads(Path(sys.argv[-1]).read_text())
fail = set(filter(None, os.environ.get("FAKE_FAIL", "").split(",")))
findings = []
for job in spec["jobs"]:
    out = Path(job["out"])
    with open(os.environ["FAKE_LOG"], "a") as log:
        log.write(out.name + "\n")
    if out.name in fail:
        findings.append({"job": job["out"], "text": "RENDER_ERROR told to fail"})
        continue
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([os.environ["FAKE_FFMPEG"], "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64", "-frames:v", "1",
                    str(out)], check=True)
Path(spec["report"]).write_text(json.dumps({"jobs": len(spec["jobs"]), "failed": len(findings), "findings": findings}))
sys.exit(1 if findings else 0)
"""


def workspace(tmp):
    """A workspace whose build/current is one empty run."""
    run = Path(tmp) / "build" / "run"
    run.mkdir(parents=True)
    (run.parent / "current").symlink_to("run", target_is_directory=True)
    return run


def script(root, name, *args):
    env = {k: v for k, v in os.environ.items() if k != "LH_RUN"}
    return subprocess.run([sys.executable, str(KIT / "scripts" / name), *args], cwd=root, capture_output=True, text=True,
                          env={**env, "LH_ROOT": str(root)})


class Vote(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.root = Path(self.tmp.name)
        self.run = workspace(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_snap_cuts_only_a_board_that_won_the_vote(self):
        r = script(self.root, "storyboard.py", "snap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vote.py ballot", r.stderr)
        self.assertNotIn("--board", r.stderr)
        r = script(self.root, "storyboard.py", "snap", "--board", "1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unrecognized arguments: --board", r.stderr)
        self.assertFalse((self.run / "winner.json").exists())
        self.assertFalse((self.run / "film.json").exists())

    def test_a_new_draft_starts_a_new_vote(self):
        (self.run / "vote").mkdir()
        (self.run / "winner.json").write_text('{"board": "1"}')
        (self.run / "vote" / "scores.json").write_text("{}")
        script(self.root, "storyboard.py", "draft")
        self.assertFalse((self.run / "winner.json").exists())
        self.assertFalse((self.run / "vote" / "scores.json").exists())


@unittest.skipUnless(os.name == "posix", "the fake renderer is an executable script")
class Render(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        d = Path(self.tmp.name)
        fake = d / "render.py"
        fake.write_text(FAKE)
        self.log = d / "rendered.log"
        self.run_dir = workspace(d)
        (self.run_dir / "public").mkdir()
        self.saved = (_env._TOOLS, Path.cwd(), dict(os.environ), _env.RENDERER)
        tools = _env.tools()
        _env._TOOLS = {**tools, "chromium": "chromium", "dist": str(_env.DIST)}
        _env.RENDERER = fake
        os.environ.update(FAKE_LOG=str(self.log), FAKE_FFMPEG=tools["ffmpeg"], FAKE_FAIL="")
        os.chdir(self.run_dir)

    def tearDown(self):
        _env._TOOLS, cwd, env, _env.RENDERER = self.saved
        os.chdir(cwd)
        os.environ.clear()
        os.environ.update(env)
        self.tmp.cleanup()

    def render_command(self, card):
        """film.py render on one card, with the film, the cut and the critics' round taken as ready."""
        import film
        saved = film.load_film, film.ready, film.card_jobs
        self.addCleanup(lambda: (setattr(film, "load_film", saved[0]), setattr(film, "ready", saved[1]),
                                 setattr(film, "card_jobs", saved[2])))
        board = {"id": "t", "seconds": 1.0, "bpm": 120, "title": "Harbourlight",
                 "beats": [{"id": "hook", "form": "photo", "start": 0, "len": 1, "words": "", "label": "", "move": None,
                            "transition": None},
                           {"id": "closer", "form": "closer", "start": 1, "len": 1, "words": "", "label": "",
                            "move": None, "transition": "hard-cut"}]}
        film.load_film, film.ready = (lambda: board), (lambda: None)
        film.card_jobs = lambda f: ([{"type": "still", "composition": "Film", "props": {}, "out": str(card)}],
                                    [{"file": str(card)}])
        return film

    def test_the_film_and_the_stills_reach_out_only_once_every_still_rendered(self):
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", "30",
                        "-pix_fmt", "yuv420p", "film.silent.mp4"], check=True)
        card = self.run_dir / "out" / "story.png"
        film = self.render_command(card)
        os.environ.update(FAKE_FAIL="story.png")
        self.assertEqual(film.cmd_render(None), 1)
        self.assertEqual(sorted(p.name for p in (self.run_dir / "out").iterdir()), [])
        os.environ.update(FAKE_FAIL="")
        self.assertEqual(film.cmd_render(None), 0)
        self.assertEqual(sorted(p.name for p in (self.run_dir / "out").iterdir()), ["film.mp4", "story.png"])

    def silent_cut(self):
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", "30",
                        "-pix_fmt", "yuv420p", "film.silent.mp4"], check=True)

    def test_a_render_removes_the_delivered_page_before_out_changes_and_keeps_the_last_set(self):
        self.silent_cut()
        card = self.run_dir / "out" / "story.png"
        card.parent.mkdir()
        card.write_bytes(b"the last render's card")
        (self.run_dir / "out" / "review.html").write_text("the delivered page")
        film = self.render_command(card)
        os.environ.update(FAKE_FAIL="story.png")
        self.assertEqual(film.cmd_render(None), 1)
        self.assertEqual(sorted(p.name for p in (self.run_dir / "out").iterdir()), ["story.png"])
        self.assertEqual(card.read_bytes(), b"the last render's card")

    def test_a_failed_still_before_a_good_one_leaves_the_report_of_the_good_one_and_the_cut(self):
        self.silent_cut()
        cut = {"jobs": 1, "failed": 0, "findings": [{"job": "cut", "text": "a finding of the cut"}]}
        _env.write_json("render/cut-report.json", cut)
        _env.write_json("render-report.json", cut)
        film = self.render_command(self.run_dir / "out" / "story.png")
        os.environ.update(FAKE_FAIL="story.png")
        self.assertEqual(film.cmd_render(None), 1)
        os.environ.update(FAKE_FAIL="")
        self.assertEqual(film.cmd_render(None), 0)
        rep = _env.read_json("render-report.json")
        self.assertEqual((rep["jobs"], rep["failed"]), (2, 0))
        self.assertEqual([f["text"] for f in rep["findings"]], ["a finding of the cut"])

    def test_a_render_stopped_between_two_moves_into_out_leaves_no_proof_of_a_render(self):
        self.silent_cut()
        film = self.render_command(self.run_dir / "out" / "story.png")
        self.assertEqual(film.cmd_render(None), 0)
        self.assertTrue(Path("engine.json").exists() and Path("render-report.json").exists())
        real, moves = os.replace, []

        def replace(src, dst, *a, **k):
            if Path(dst).resolve().parent == (self.run_dir / "out").resolve():
                moves.append(dst)
                if len(moves) == 2:
                    raise KeyboardInterrupt
            return real(src, dst, *a, **k)
        with mock.patch.object(os, "replace", replace), self.assertRaises(KeyboardInterrupt):
            film.cmd_render(None)
        self.assertEqual(len(moves), 2)
        self.assertFalse(Path("engine.json").exists())
        self.assertFalse(Path("render-report.json").exists())

    def test_a_render_stopped_and_retried_without_promotion_leaves_no_proof_of_a_render(self):
        self.silent_cut()
        film = self.render_command(self.run_dir / "out" / "story.png")
        self.assertEqual(film.cmd_render(None), 0)
        real, moves = os.replace, []

        def replace(src, dst, *a, **k):
            if Path(dst).resolve().parent == (self.run_dir / "out").resolve():
                moves.append(dst)
                if len(moves) == 2:
                    raise KeyboardInterrupt
            return real(src, dst, *a, **k)

        def killed(*a, **k):
            raise KeyboardInterrupt
        with mock.patch.object(os, "replace", replace), self.assertRaises(KeyboardInterrupt):
            film.cmd_render(None)
        with mock.patch.object(film, "mux", killed), self.assertRaises(KeyboardInterrupt):
            film.cmd_render(None)
        os.environ.update(FAKE_FAIL="story.png")
        self.assertEqual(film.cmd_render(None), 1)
        self.assertFalse(Path("engine.json").exists())
        self.assertFalse(Path("render-report.json").exists())

    def test_the_film_carries_the_master_music_json_names(self):
        self.silent_cut()
        Path("music").mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=d=1", "music/master-a1.wav"], check=True)
        _env.write_json("music.json", {"file": "music/source-a1.wav", "master": "music/master-a1.wav"})
        film = self.render_command(self.run_dir / "out" / "story.png")
        self.assertEqual(film.cmd_render(None), 0)
        streams = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                  "out/film.mp4"], capture_output=True, text=True).stdout.split()
        self.assertIn("audio", streams)

    def test_with_no_music_the_film_carries_its_sound_effects(self):
        self.silent_cut()
        film = self.render_command(self.run_dir / "out" / "story.png")
        self.assertEqual(film.cmd_render(None), 0)
        level = subprocess.run([_env.ffmpeg(), "-v", "info", "-i", "out/film.mp4", "-af", "volumedetect", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
        peak = float(re.search(r"max_volume: (-?[\d.]+) dB", level).group(1))
        self.assertGreater(peak, -30, "the closer's impact is in the film")

    def cut_command(self):
        """film.py cut on a one-second film.json the board's check passes, its render a picture made here."""
        import film
        _env.write_json("film.json", {"timeline": [{"start": 0, "frames": 30}], "seconds": 1.0})

        def render(run, jobs, report):
            self.silent_cut()
            return {"jobs": 1, "failed": 0, "findings": []}
        for p in (mock.patch.object(film._env, "render", render), mock.patch.object(film.storyboard, "board_issues", lambda *a: [])):
            p.start()
            self.addCleanup(p.stop)
        return film

    def test_a_cut_stopped_before_its_strips_and_checks_leaves_no_cut_for_the_critics(self):
        import vote
        film = self.cut_command()
        _env.write_json("cut.json", {"film": film.film_hash()})
        _env.write_json("qa/cut.json", {"pass": True})

        def killed(*a, **k):
            raise KeyboardInterrupt
        with mock.patch.object(film, "strips", killed), self.assertRaises(KeyboardInterrupt):
            film.cmd_cut(None)
        self.assertFalse(Path("cut.json").exists())
        self.assertFalse(Path("qa/cut.json").exists())
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertEqual(str(e.exception.code), "there is no cut of the current film.json: run film.py cut first")

    def test_a_cut_is_certified_only_once_its_checks_pass(self):
        film = self.cut_command()
        with mock.patch.object(film, "strips", lambda *a: 0), \
                mock.patch.object(film.qa, "film_checks", lambda *a, **k: [("still", False, "a still picture")]):
            self.assertEqual(film.cmd_cut(None), 1)
        self.assertFalse(Path("cut.json").exists())
        with mock.patch.object(film, "strips", lambda *a: 0), mock.patch.object(film.qa, "film_checks", lambda *a, **k: []):
            self.assertEqual(film.cmd_cut(None), 0)
        self.assertEqual(_env.read_json("cut.json")["film"], film.film_hash())

    def test_checking_the_silent_cut_again_reads_the_cuts_own_report(self):
        import qa
        film = self.cut_command()
        _env.write_json("film.json", {"timeline": [{"start": 0, "frames": 30}], "seconds": 1.0,
                                      "system": {"colors": {"bg": "#000000"}}})
        for name, stand_in in (("board_checks", lambda board, check: None), ("frame0_check", lambda *a: (True, "a frame"))):
            p = mock.patch.object(qa, name, stand_in)
            p.start()
            self.addCleanup(p.stop)

        def render(run, jobs, report):
            self.silent_cut()
            rep = {"jobs": 1, "failed": 0, "findings": []}
            _env.write_json(report, rep)
            return rep
        with mock.patch.object(film, "strips", lambda *a: 0), mock.patch.object(film._env, "render", render):
            film.cmd_cut(None)
        safe = [c for c in _env.read_json("qa/cut.json")["checks"] if c["check"] == "safe"]
        self.assertEqual([c["pass"] for c in safe], [True])
        with mock.patch.object(sys, "argv", ["qa.py", "check", "--film", "film.silent.mp4"]), \
                mock.patch.object(qa._env, "enter_run", lambda: None):
            qa.main()
        self.assertEqual([c for c in _env.read_json("qa/cut.json")["checks"] if c["check"] == "safe"], safe)

    def test_a_refused_render_command_leaves_the_running_ones_outputs_untouched(self):
        import fcntl
        card = self.run_dir / "out" / "story.png"
        card.parent.mkdir()
        card.write_bytes(b"the running render's card")
        film = self.render_command(card)
        (self.run_dir / "render").mkdir()
        held = open(self.run_dir / "render" / "render.lock", "a+")
        self.addCleanup(held.close)
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held.write("film-report\tthe log\n")
        held.flush()
        with self.assertRaises(SystemExit) as e:
            film.cmd_render(None)
        self.assertEqual(str(e.exception.code), "a render named film-report is already running in this run; its log is the log")
        self.assertEqual(card.read_bytes(), b"the running render's card")
        self.assertFalse(self.log.exists())


class Deliver(unittest.TestCase):
    def test_a_deliver_killed_before_its_gate_ends_leaves_a_page_that_says_not_ready(self):
        import deliver
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            run = workspace(tmp)
            for f, v in (("library.json", {"subject": {"name": "the cup"}}), ("taste.json", {"register": {}}),
                         ("winner.json", {"board": "1", "totals": {"1": 20}})):
                (run / f).write_text(json.dumps(v))
            saved = Path.cwd(), dict(os.environ), _env.ROOT
            self.addCleanup(lambda: (os.chdir(saved[0]), os.environ.clear(), os.environ.update(saved[1]),
                                     setattr(_env, "ROOT", saved[2])))
            os.environ["LH_ROOT"] = tmp
            os.environ.pop("LH_RUN", None)
            _env.ROOT = None

            def killed(*a, **k):
                raise KeyboardInterrupt

            with mock.patch.object(deliver.qa, "gate_checks", killed), mock.patch.object(sys, "argv", ["deliver.py"]):
                with self.assertRaises(KeyboardInterrupt):
                    deliver.main()
            self.assertIn("Not ready to post", (run / "out" / "review.html").read_text())


    def deliver_in_a_run(self, checks):
        """deliver.py in build/20261026-014049 under a workspace, the gate answering `checks`: (exit, what it printed)."""
        import contextlib
        import io
        import deliver
        tmp = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
        self.addCleanup(shutil.rmtree, tmp, True)
        run = Path(tmp) / "build" / "20261026-014049"
        run.mkdir(parents=True)
        (run.parent / "current").symlink_to(run.name, target_is_directory=True)
        for f, v in (("library.json", {"subject": {"name": "the cup"}}), ("taste.json", {"register": {}}),
                     ("winner.json", {"board": "1", "totals": {"1": 20}})):
            (run / f).write_text(json.dumps(v))
        saved = Path.cwd(), dict(os.environ), _env.ROOT
        self.addCleanup(lambda: (os.chdir(saved[0]), os.environ.clear(), os.environ.update(saved[1]),
                                 setattr(_env, "ROOT", saved[2])))
        os.environ["LH_ROOT"] = tmp
        os.environ.pop("LH_RUN", None)
        _env.ROOT = None
        said = io.StringIO()
        with mock.patch.object(deliver.qa, "gate_checks", lambda *a, **k: list(checks)), \
                mock.patch.object(sys, "argv", ["deliver.py"]), contextlib.redirect_stdout(said), \
                contextlib.redirect_stderr(io.StringIO()):
            code = deliver.main()
        return code, said.getvalue()

    def test_the_last_line_is_the_reels_path_from_the_workspace_root(self):
        code, said = self.deliver_in_a_run([("film", True, "ok")])
        self.assertEqual(code, 0)
        self.assertEqual(said.splitlines()[-1], "build/20261026-014049/out/film.mp4")

    def test_a_failed_gate_ends_on_what_failed_and_names_no_film(self):
        code, said = self.deliver_in_a_run([("film", True, "ok"), ("made", False, "out/film.mp4 is not the current cut")])
        self.assertEqual(code, 1)
        self.assertEqual(said.splitlines()[-1], "the gate failed: made")
        self.assertNotIn("build/20261026-014049/out/film.mp4", said)

if __name__ == "__main__":
    unittest.main()
