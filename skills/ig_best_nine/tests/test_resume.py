"""best nine's call site of scripts/chunks.py, which test_chunks.py tests on its own: studio.render hands chunks.render
an invoke that runs render.py, here a stand-in for it that writes each chunk's frames as a test pattern with the
findings file render.py writes beside it. film.py takes the run's lock before its first write, so a refused command
changes nothing; a failed render leaves out/ as it was, and a preview or a deliver stopped partway never leaves a
measurement or a page that reads finished, and a new cut leaves no render report until it is rendered. Every
process film.py starts under the lock goes through run.spawn. snap cuts only the board that won the vote, and a new
draft starts a new vote. deliver holds the lock through its gate, a
stopped draft leaves no index naming its boards, every input a later command reads moves in whole, and the critics'
round belongs to one reel.

    python3 -I -m unittest discover -s S/tests -p test_resume.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import chunks  # noqa: E402
import deliver  # noqa: E402
import clips  # noqa: E402
import film  # noqa: E402
import music  # noqa: E402
import picks  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

# the probes a test reads a file with run outside any run's lock
PLAIN = types.SimpleNamespace(spawn=subprocess.run)
STYLE = storyboard.compose.TRIO[0]


def fmt_of(name, w=64, h=64):
    return {"width": w, "height": h, "fps": 30, "name": name}


def fake_run(plan=None, styles=(STYLE,)):
    """storyboard.Run as the commands read it, over one plan for every format."""
    return types.SimpleNamespace(plan=lambda style, fmt, bpm: plan, posts=[], words=lambda: {}, seconds=30, styles=styles,
                                 levers={}, swatches=[], taste={})

# render.py as studio.render calls it (`python3 render.py --jobs JOBS.json`): every chunk is its frameRange's frames of a test pattern
# at its `.part.mp4` with an empty `.part.findings.json` beside it, and every still is a test pattern PNG; a job whose
# name (its file name up to the first dot) is in FAKE_FAIL is left unwritten with a RENDER_ERROR finding, as render.py
# reports a job that failed. Each job logs its
# name, with " (lock not held)" when none of the renderer's open files (/dev/fd) is the run's render.lock.
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[2]))
ff = os.environ["FAKE_FFMPEG"]
lock = os.stat(os.path.join(os.path.dirname(os.path.dirname(spec["report"])), "render.lock"))
def same(fd):
    try:
        return os.path.samestat(os.fstat(int(fd)), lock)
    except OSError:
        return False
held = any(same(fd) for fd in os.listdir("/dev/fd"))
fail, findings = os.environ.get("FAKE_FAIL", "").split(), []
for job in spec["jobs"]:
    name = os.path.basename(job["out"])
    with open(os.environ["FAKE_LOG"], "a") as log:
        log.write(name + ("" if held else " (lock not held)") + "\n")
    if name.split(".")[0] in fail:
        findings.append({"job": job["out"], "text": "RENDER_ERROR the test failed it"})
        continue
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if job["type"] == "video":
        a, b = job["frameRange"]
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", str(b - a + 1),
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64", "-frames:v", "1", job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": len(findings), "findings": findings, "seconds": 1}, open(spec["report"], "w"))
sys.exit(1 if findings else 0)
"""


class CallSite(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        self.log = self.dir / "rendered.log"
        src = self.dir / "src"
        src.mkdir()
        (src / "Film.tsx").write_text("export const Film = 1;\n")
        self.run_dir = self.dir / "it's a run"
        self.run_dir.mkdir()
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        tools = dict(_env.tools(), chromium="chrome", dist=True)
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "SOURCE", (src,)),
                      mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(chunks, "GPU", False),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=_env.ffmpeg(), FAKE_LOG=str(self.log), FAKE_FAIL="")):
            patch.start()
            self.addCleanup(patch.stop)

    def job(self, n=23, out="preview/film.mp4"):
        return {"type": "video", "composition": "Film", "props": {"board": {"id": "one"}, "clips": []}, "frames": n,
                "scale": 0.5, "out": str(Path(out).resolve())}

    def rendered(self):
        names = self.log.read_text().splitlines() if self.log.exists() else []
        self.log.unlink(missing_ok=True)
        return names

    def quiet(self, fn, *args, **env):
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()):
            return fn(*args)

    def cut(self):
        """A cut film.json with its three boards, past qa.py timed."""
        for fmt in film.NAMES:
            _env.write_json(f"boards/{fmt}.json", {"id": fmt, "beats": [], "format": fmt_of(fmt)})
        _env.write_json("film.json", {"hash": "h", "style": STYLE, "frames": 23, "seconds": 23 / 30, "cuts": [0.3],
                                      "hook_frame": 4, "boards": {fmt: f"boards/{fmt}.json" for fmt in film.NAMES},
                                      "rests": {fmt: {"closer": 5} for fmt in film.NAMES}})
        _env.write_json("qa/timed.json", {"hash": "h", "pass": True})

    def command(self, *args, **env):
        with mock.patch.object(sys, "argv", ["film.py", *args, "--run", str(self.run_dir)]):
            return self.quiet(film.main, **env)

    def files(self, root="."):
        return {str(p): p.read_bytes() for p in sorted(Path(root).rglob("*")) if p.is_file() and p.name != "render.lock"}

    def test_a_143_frame_film_renders_as_three_chunks_and_joins_whole(self):
        rep = self.quiet(studio.render, [self.job(143)], "preview")
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(self.rendered(), ["0-59.part.mp4", "60-119.part.mp4", "120-142.part.mp4"])
        self.assertEqual(rep["chunks"], {"kept": 0, "rendered": 3, "to_go": 0})
        self.assertEqual(chunks._frames(PLAIN, _env.ffprobe(), Path("preview/film.mp4")), 143)
        self.assertEqual(self.quiet(studio.render, [self.job(143)], "preview")["chunks"], {"kept": 3, "rendered": 0, "to_go": 0})

    @unittest.skipIf(os.name == "nt", "the renderer's open files are listed from /dev/fd")
    def test_the_renderer_holds_the_run_lock(self):
        self.quiet(studio.render, [self.job()], "preview")
        self.assertNotIn("(lock not held)", " ".join(self.rendered()))

    def test_the_report_counts_the_callers_jobs(self):
        jobs = [self.job(), self.job(out="preview/other.mp4"), studio.still({"id": "one"}, 5, "preview/still.png")]
        rep = self.quiet(studio.render, jobs, "preview")
        self.assertEqual((rep["jobs"], rep["failed"]), (3, 0))
        self.assertEqual(json.loads(Path("render/staging/preview-report.json").read_text())["jobs"], 3)

    @unittest.skipIf(os.name == "nt", "an flock; Windows holds the lock by an exclusive open")
    def test_a_refused_command_changes_nothing_in_the_run(self):
        import fcntl
        self.cut()
        Path("render").mkdir()
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the first render's film")
        with open("render/render.lock", "w", encoding="utf-8") as held:
            held.write(f"film\t{Path('render/film.log').resolve()}\n")
            held.flush()
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            before = self.files()
            for cmd in ("preview", "render"):
                with self.assertRaises(SystemExit) as e:
                    self.command(cmd)
                self.assertIn("a render named film is already running in this run", str(e.exception.code))
            self.assertEqual(self.files(), before, "a refused command writes nothing into the run")
        self.assertEqual(self.rendered(), [])

    def test_a_failed_render_leaves_out_as_it_was_and_a_whole_one_moves_in(self):
        self.cut()
        Path("out").mkdir()
        for name in ("film.mp4", "best-nine.png", "review.html"):
            Path("out", name).write_text("the last delivery")
        before = self.files("out")
        with self.assertRaises(SystemExit):
            self.command("render", FAKE_FAIL="best-nine")
        self.assertEqual(self.files("out"), before, "out/ holds the last delivery, whole")
        self.assertEqual(self.command("render"), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["best-nine.png", "film.mp4"],
                         "every deliverable is the new render's, and the last delivery's review page is gone")

    def test_the_review_page_goes_first_and_every_file_replaces_the_last_in_one_move(self):
        self.cut()
        Path("out").mkdir()
        for name in (*film.NAMES.values(), "review.html"):
            Path("out", name).write_text("the last delivery")
        seen, real = [], os.replace

        def replace(src, dst):
            if Path(dst).parent.resolve() == Path("out").resolve():
                seen.append((Path(dst).name, Path(dst).exists(), Path("out/review.html").exists()))
            return real(src, dst)

        with mock.patch.object(os, "replace", side_effect=replace):
            self.assertEqual(self.command("render"), 0)
        self.assertEqual(seen[-1][0], film.NAMES["reel"], "the reel moves in last")
        self.assertTrue(all(there for name, there, _ in seen if name in film.NAMES.values()),
                        "no film is removed before its replace")
        self.assertFalse(any(page for *_, page in seen), "the review page is gone before the first file moves in")

    def test_a_render_stopped_between_two_replacements_leaves_no_report(self):
        self.cut()
        real = os.replace

        def replace(src, dst):
            if Path(dst).name == film.NAMES["reel"] and Path(dst).parent.name == "out":
                raise KeyboardInterrupt
            return real(src, dst)

        with mock.patch.object(os, "replace", side_effect=replace), self.assertRaises(KeyboardInterrupt):
            self.command("render")
        self.assertTrue(Path("out", "best-nine.png").exists())
        self.assertFalse(Path("render/film-report.json").exists(), "the gate refuses a half-moved out/")
        # the retry renders and is stopped again before anything moves into out/
        with mock.patch.object(film, "mux", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.command("render")
        self.assertFalse(Path("render/film-report.json").exists(), "a render's own report stands under no name a reader takes")
        with mock.patch.object(qa, "posts_n", return_value=9), contextlib.redirect_stdout(io.StringIO()):
            res, *_ = qa.film_checks()
        self.assertEqual([ok for name, ok, *_ in res if name == "safe"], [False], "the gate refuses the half-moved out/")
        self.assertEqual(self.command("render"), 0)
        self.assertEqual(_env.read_json("render/film-report.json")["failed"], 0)

    def test_the_reel_renders_alone_unless_more_is_asked(self):
        self.cut()
        self.assertEqual(self.command("render"), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["best-nine.png", "film.mp4"],
                         "the reel and the best-nine image, no other shape and no story card")
        self.assertEqual(self.command("render", "--also", "square"), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["best-nine.png", "film-square.mp4", "film.mp4"])
        self.assertEqual(self.command("render", "--also", "landscape", "stories"), 0)
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["best-nine.png", "film-wide.mp4", "film.mp4", "story.png"],
                         "exactly the asked ones: the square from the last render is gone")
        self.assertEqual(_env.read_json("render/film-report.json")["made"], {"formats": ["reel", "wide"], "stories": True})

    def test_the_check_fails_a_shape_or_a_story_card_nobody_asked_for(self):
        self.cut()
        self.assertEqual(self.command("render"), 0)
        shutil.copyfile("out/film.mp4", "out/film-square.mp4")
        shutil.copyfile("out/best-nine.png", "out/story.png")
        with mock.patch.object(qa, "posts_n", return_value=9), mock.patch.object(qa, "shown_at", return_value=9), \
                contextlib.redirect_stdout(io.StringIO()):
            res, *_ = qa.film_checks()
        failed = [detail for name, ok, detail, *_ in res if ok is False]
        self.assertIn("out/film-square.mp4 is in out/, and the render did not make it (nobody asked for it)", failed)
        self.assertIn("out/story.png is in out/, and the render did not make it (nobody asked for it)", failed)

    def snap(self):
        """snap of a new cut of the winning board, past qa.py timed."""
        _env.write_json("winner.json", {"board": STYLE})
        plan = {"board": {"id": "the new cut", "bpm": 120, "beats": [], "sound": [], "clips": [], "format": fmt_of("reel")}, "scenes": [], "seconds": 23 / 30, "frames": 23,
                "cuts": [0.4], "hook_frame": 3, "rests": {"hook": 1, "dense": 2, "closer": 5}, "rest_beats": {"hook": 1, "dense": 2, "closer": 3}}
        with mock.patch.object(storyboard, "findings", return_value=[]), mock.patch.object(storyboard, "style_findings", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()):
            storyboard.cmd_snap(None, fake_run(plan))
        _env.write_json("qa/timed.json", {"hash": _env.read_json("film.json")["hash"], "pass": True})

    def safe(self):
        with mock.patch.object(qa, "posts_n", return_value=9), contextlib.redirect_stdout(io.StringIO()):
            res, *_ = qa.film_checks()
        return [ok for name, ok, *_ in res if name == "safe"]

    def test_a_new_cut_leaves_the_last_cut_s_films_unvouched_for(self):
        self.cut()
        self.assertEqual(self.command("render"), 0)
        self.assertEqual(self.safe(), [True])
        self.snap()
        self.assertEqual(self.safe(), [False], "the gate refuses the last cut's films as the new cut's")
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("film.py render", str(e.exception.code))

    def test_a_render_of_a_new_cut_stopped_before_it_moves_in_leaves_no_report(self):
        self.cut()
        self.assertEqual(self.command("render"), 0)
        self.snap()
        with mock.patch.object(film, "mux", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.command("render")
        self.assertEqual(self.safe(), [False], "the gate refuses the last cut's films after a stopped render of the new one")
        self.assertEqual(self.command("render"), 0)
        self.assertEqual(self.safe(), [True])

    def test_a_preview_that_does_not_finish_leaves_no_measurement(self):
        self.cut()
        _env.write_json("preview/preview.json", {"hash": "h", "seconds": 1, "strip2": "an earlier film's strip"})
        with self.assertRaises(SystemExit):
            self.command("preview", FAKE_FAIL="0-22")
        self.assertFalse(Path("preview/preview.json").exists(), "vote.py timed and qa.py timed find no figures to read")


class UnderTheLock(unittest.TestCase):
    """Every process film.py starts while it holds the run's lock goes through run.spawn: the mux and the measure."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        Path("music").mkdir()
        ff = _env.ffmpeg()
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30", "-frames:v", "30", "-pix_fmt", "yuv420p",
                        "silent.mp4"], check=True)
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=d=1", "music/master.wav"], check=True)
        _env.write_json("music.json", {"file": "music/master.wav", "master": "music/master.wav"})
        self.started, real = [], subprocess.run

        class Run:
            def spawn(_, argv, **kw):
                self.started.append(Path(argv[0]).name)
                return real(argv, **kw)

        self.run_ = Run()
        refuse = mock.patch.object(subprocess, "run", side_effect=AssertionError("a process started outside run.spawn"))
        refuse.start()
        self.addCleanup(refuse.stop)

    def test_the_mux_and_the_measure_start_through_run_spawn(self):
        self.assertTrue(film.mux(self.run_, Path("silent.mp4"), Path("film.mp4"), 1))
        m = studio.measure(Path("film.mp4"), [], run=self.run_)
        self.assertEqual(m["frames"], 30)
        self.assertEqual(len(self.started), 6)

    def test_every_process_the_gates_film_checks_start_goes_through_run_spawn(self):
        self.assertTrue(film.mux(self.run_, Path("silent.mp4"), Path("film.mp4"), 1))
        Path("out").mkdir()
        for path, _ in qa.FILMS.values():
            shutil.copyfile("film.mp4", path)
        for fmt in qa.FILMS:
            _env.write_json(f"boards/{fmt}.json", {"beats": [], "format": fmt_of(fmt)})
        _env.write_json("film.json", {"cuts": [0.5], "hook_frame": 4, "boards": {fmt: f"boards/{fmt}.json" for fmt in qa.FILMS},
                                      "rests": {fmt: {"closer": 5} for fmt in qa.FILMS}})
        _env.write_json("render/film-report.json", {"failed": 0, "made": {"formats": list(qa.FILMS), "stories": True}})
        self.started.clear()
        with mock.patch.object(qa, "posts_n", return_value=9):
            res, _, measured = qa.film_checks(self.run_)
        self.assertEqual(measured["frames"], 30)
        self.assertIn("ffprobe", self.started)
        self.assertGreater(len(self.started), len(qa.FILMS) * 4, "the probe, the loudness, both detectors and the measure")


class Vote(unittest.TestCase):
    """snap cuts only the board that won the vote, and a new draft starts a new vote."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def test_snap_cuts_only_a_board_that_won_the_vote(self):
        with self.assertRaises(SystemExit) as e:
            storyboard.cmd_snap(None, fake_run())
        self.assertIn("vote.py pick --board", str(e.exception.code))
        self.assertIn("out/boards.png", str(e.exception.code), "the person is shown the looks before one is cut")
        self.assertFalse(Path("film.json").exists())
        with mock.patch.object(sys, "argv", ["storyboard.py", "snap", "--board", STYLE, "--run", str(self.dir)]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            storyboard.main()
        self.assertEqual(e.exception.code, 2, "--board is not an option")

    def test_a_new_draft_starts_a_new_vote(self):
        _env.write_json("winner.json", {"board": STYLE, "swap_passed": True})
        _env.write_json("vote/scores.json", {})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(storyboard.cmd_draft(None, fake_run(styles=())), 0)
        self.assertFalse(Path("winner.json").exists())
        self.assertFalse(Path("vote/scores.json").exists())

    def test_the_fix_round_keeps_the_scored_rounds_of_the_look_picked_again(self):
        _env.write_json("critic/cut-1.json", {"round": 1, "style": STYLE})
        _env.write_json("critic/timed.json", {})
        pick = lambda board: vote.cmd_pick(types.SimpleNamespace(board=board, why=None))
        with contextlib.redirect_stdout(io.StringIO()):
            pick(STYLE)
        self.assertTrue(Path("critic/cut-1.json").exists(), "the fix round's cut is round 2")
        self.assertFalse(Path("critic/timed.json").exists(), "the timed read is of the boards drawn before")
        Path("winner.json").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            pick(storyboard.compose.TRIO[1])
        self.assertFalse(Path("critic").exists(), "another look starts its own rounds")


class Deliver(unittest.TestCase):
    """The review page reads not ready until the gate passes."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        for name, obj in (("library.json", {"handle": "you", "year": 2026}), ("taste.json", {"register": {"lowercase": True}}),
                          ("winner.json", {"board": STYLE, "totals": {}}), ("film.json", {"style": STYLE})):
            _env.write_json(name, obj)
        _env.write_json(f"storyboards/{STYLE}/board-reel.json", {"system": {"colors": {"bg": "#f4f1ea", "ink": "#111111", "accent": "#c98e45"}}})
        posts = [{"rank": r, "date": f"2026-0{r}-01", "caption": c} for r, c in ((1, "Heart croissants #bakery"), (2, ""), (3, "the street fair"))]
        for patch in (mock.patch.object(_env, "tools", return_value={}),
                      mock.patch.object(storyboard, "Run", lambda: types.SimpleNamespace(posts=posts)),
                      mock.patch.object(deliver, "caption", return_value="the nine #bestnine"),
                      mock.patch.object(deliver, "brief", return_value="the brief"),
                      mock.patch.object(sys, "argv", ["deliver.py", "--run", str(self.dir)])):
            patch.start()
            self.addCleanup(patch.stop)

    def page(self):
        return Path("out/review.html").read_text()

    def gate(self, *checks):
        return mock.patch.object(qa, "gate_checks", return_value=(qa.Checks(checks), {"hash": "h"}))

    def test_a_deliver_stopped_during_the_gate_leaves_a_page_that_reads_not_ready(self):
        with mock.patch.object(qa, "gate_checks", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertIn("Not ready to post.", self.page())
        self.assertEqual(Path("brief.md").read_text(), "the brief")
        self.assertFalse(Path("out/brief.md").exists(), "the brief, with its scores, stays beside out/")
        self.assertEqual([p.name for p in Path("out").glob(".*")], [], "every file moved in whole")

    def test_a_green_gate_takes_the_banner_off_and_a_red_one_names_what_failed(self):
        with self.gate(("everything", True, "passed")), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertNotIn("Not ready to post.", self.page())
        with self.gate(("critic", False, "no cut round")), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        self.assertIn("Not ready to post.", self.page())
        self.assertIn("critic no cut round", self.page())

    @unittest.skipIf(os.name == "nt", "an flock; Windows holds the lock by an exclusive open")
    def test_the_gate_runs_while_deliver_holds_the_run_lock(self):
        import fcntl
        held = []

        def gate(run):
            with open("render/render.lock", "rb") as f:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held.append(False)
                except BlockingIOError:
                    held.append(True)
            held.append(isinstance(run, chunks.Run))
            return qa.Checks([("everything", True, "passed")]), {"hash": "h"}

        with mock.patch.object(qa, "gate_checks", side_effect=gate), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(held, [True, True], "the gate runs in deliver's process with the run's lock and its run")


    def test_the_last_line_is_the_reels_path_from_the_workspace_root(self):
        run = Path("build", "20261026T014049Z")
        run.mkdir(parents=True)
        for name in ("library.json", "taste.json", "winner.json", "film.json"):
            shutil.copyfile(name, run / name)
        shutil.copytree("storyboards", run / "storyboards")
        said = io.StringIO()
        with mock.patch.object(_env, "WORKSPACE", self.dir), mock.patch.object(sys, "argv", ["deliver.py", "--run", str(run)]), \
                self.gate(("everything", True, "passed")), contextlib.redirect_stdout(said):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(said.getvalue().splitlines()[-1], "build/20261026T014049Z/out/film.mp4")

    def test_a_green_gate_says_the_ranking_and_the_order_before_the_path(self):
        top = [{"rank": r, "date": f"2026-0{r}-01", "date_label": f"1 {m}", "caption": c}
               for r, m, c in ((1, "jan", "Heart croissants #bakery"), (2, "feb", ""), (3, "mar", "the street fair"))]
        _env.write_json("stats.json", {"top_ranked_by": "likes, then comments, then saves", "top_nine": top})
        said = io.StringIO()
        with self.gate(("everything", True, "passed")), contextlib.redirect_stdout(said):
            self.assertEqual(deliver.main(), 0)
        lines = said.getvalue().splitlines()
        self.assertIn("the nine, first to ninth, ranked by likes, then comments, then saves:", lines)
        self.assertIn("1. 1 jan, Heart croissants #bakery", lines)
        self.assertIn("2. 1 feb, a photograph without a caption", lines)
        self.assertIn("the reel shows them one by one and ends on 2026-01-01, Heart croissants #bakery, the one the film builds to; "
                      "the closing grid holds all nine", lines)
        self.assertTrue(lines[-1].endswith("out/film.mp4"))

    def test_a_ranking_with_no_numbers_says_the_nine_are_the_most_recent_and_why(self):
        _env.write_json("stats.json", {"top_ranked_by": "recent", "top_nine": [{"rank": 1, "date_label": "30 dec", "caption": "snow"}]})
        said = io.StringIO()
        with self.gate(("everything", True, "passed")), contextlib.redirect_stdout(said):
            self.assertEqual(deliver.main(), 0)
        self.assertIn("the nine are the most recent posts, newest first, because the file carries no likes, comments or saves:",
                      said.getvalue().splitlines())

    def test_a_number_the_file_does_not_carry_is_a_dash_in_the_brief(self):
        _env.write_json("stats.json", {"top_ranked_by": "likes, then comments", "top_nine": [
            {"rank": 1, "date_label": "June 13", "kind": "post", "likes": 820, "comments": 57, "saves": None}]})
        rows = deliver.nine_rows()
        self.assertIn("| 1 | June 13 (post) | 820 | 57 | - |  |", rows)
        self.assertFalse(qa.PLACEHOLDER.search("\n".join(rows)), "the gate's text check passes the table")

    def test_a_failed_gate_ends_on_what_failed_and_names_no_film(self):
        said = io.StringIO()
        with self.gate(("everything", True, "passed"), ("critic", False, "no cut round"), ("deliver", False, "no caption")), \
                contextlib.redirect_stdout(said), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        self.assertEqual(said.getvalue().splitlines()[-1], "not delivered: the gate failed on critic, deliver")
        self.assertNotIn("film.mp4", said.getvalue())


class Indexes(unittest.TestCase):
    """A stopped command leaves no index naming files it was changing, and every input a later command reads moves in
    whole."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        # the tests patch subprocess.run, so setup.py must never run under them
        tools = mock.patch.object(_env, "tools", return_value={"ffmpeg": "ffmpeg"})
        tools.start()
        self.addCleanup(tools.stop)

    def test_draft_and_sheets_remove_a_sheet_before_what_it_is_drawn_from_changes(self):
        sheet = storyboard.BOARDS / STYLE / "sheet.png"
        _env.write_json(storyboard.BOARDS / STYLE / "plan.json", {fmt: {"rests": {k: i for i, k in enumerate(storyboard.SHEET)}}
                                                                   for fmt in storyboard.compose.FORMATS})
        for fmt in storyboard.compose.FORMATS:
            _env.write_json(storyboard.BOARDS / STYLE / f"board-{fmt}.json", {"id": fmt})
        seen = []

        def changes(*a, **kw):
            seen.append(sheet.exists())
            raise KeyboardInterrupt

        for cmd, at in ((storyboard.cmd_draft, "write_style"), (storyboard.cmd_sheets, None)):
            sheet.write_bytes(b"the last sheet")
            target = (storyboard, at) if at else (studio, "render")
            with mock.patch.object(*target, side_effect=changes), mock.patch.object(_env, "tools", return_value={}), \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
                cmd(None, fake_run())
        self.assertEqual(seen, [False, False], "the sheet is gone before the first board or frame it shows is written")

    def test_plan_json_is_written_after_storyboard_md(self):
        order, real = [], _env.write_text

        def write(path, text):
            order.append(Path(path).name)
            return real(path, text)

        plan = {"board": {"bpm": 120, "beats": [], "sound": [], "clips": []}, "scenes": [], "seconds": 20, "cuts": [1.0], "hook_frame": 3,
                "rests": {}, "rest_beats": {}}
        with mock.patch.object(_env, "write_text", side_effect=write):
            storyboard.write_style(fake_run(plan), STYLE)
        self.assertEqual(order[-2:], ["storyboard.md", "plan.json"])

    def test_a_draft_stopped_between_two_boards_leaves_no_plan_and_no_film(self):
        d = storyboard.BOARDS / STYLE
        for name in ("board-reel.json", "board-square.json", "board-wide.json", "plan.json"):
            _env.write_json(d / name, {"the last draft": True})
        _env.write_json("film.json", {"style": STYLE})
        real, boards = _env.write_json, []

        def write(path, obj):
            if Path(path).name.startswith("board-"):
                boards.append(path)
                if len(boards) == 2:
                    raise KeyboardInterrupt
            return real(path, obj)

        run = fake_run()
        run.plan = lambda style, fmt, bpm: {"board": {"id": fmt}, "scenes": [], "seconds": 1}
        with mock.patch.object(_env, "write_json", side_effect=write), self.assertRaises(KeyboardInterrupt):
            storyboard.write_style(run, STYLE)
        self.assertFalse(Path("film.json").exists(), "only snap writes film.json")
        self.assertFalse((d / "plan.json").exists())
        with self.assertRaises(SystemExit) as e:
            storyboard.load_plans(STYLE)
        self.assertIn("storyboard.py draft", str(e.exception.code), "check and sheets refuse a half-drafted look")

    def stopped(self, path):
        """A writer that leaves half a file at `path` and stops there."""
        def stop(*args, **kw):
            Path(path).write_bytes(b"half")
            raise KeyboardInterrupt
        return stop

    def test_a_photograph_moves_in_whole(self):
        from PIL import Image
        Image.new("RGB", (64, 48), "gray").save("src.jpg")
        dest = picks.PHOTOS / "r1-src.jpg"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"the last pick")

        def save(im, fp, *a, **kw):
            self.stopped(fp)()

        with mock.patch.object(Image.Image, "save", save), self.assertRaises(KeyboardInterrupt):
            picks.place(1, "src.jpg")
        self.assertEqual(dest.read_bytes(), b"the last pick")
        self.assertEqual(picks.place(1, "src.jpg"), dest)
        with Image.open(dest) as im:
            self.assertEqual(im.size, (64, 48))

    def test_a_stopped_music_make_leaves_the_last_bed_and_music_json_as_they_were(self):
        _env.write_json("winner.json", {"board": STYLE})
        music.MUSIC.mkdir()
        old = music.MUSIC / "source.last.wav"
        old.write_bytes(b"the last bed")
        _env.write_json("music.json", {"file": str(old), "bpm": 100})
        with mock.patch.object(music.music_engine, "compose", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=1))
        self.assertEqual(old.read_bytes(), b"the last bed")
        self.assertEqual(_env.read_json("music.json"), {"file": str(old), "bpm": 100})

    def test_music_make_removes_the_last_bed_only_once_music_json_names_the_new_one(self):
        _env.write_json("winner.json", {"board": STYLE})
        music.MUSIC.mkdir()
        old = music.MUSIC / "source.last.wav"
        old.write_bytes(b"the last bed")
        _env.write_json("music.json", {"file": str(old)})

        def stop(path, obj):
            raise KeyboardInterrupt

        with mock.patch.object(music.music_engine, "compose", side_effect=engine), \
                mock.patch.object(_env, "write_json", side_effect=stop), self.assertRaises(KeyboardInterrupt):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=1))
        self.assertTrue(Path(_env.read_json("music.json")["file"]).exists(), "analyze and master read what music.json names")
        with mock.patch.object(music.music_engine, "compose", side_effect=engine), contextlib.redirect_stdout(io.StringIO()):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=1))
        self.assertFalse(old.exists(), "the last bed goes once music.json names the new one")
        self.assertEqual(_env.read_json("music.json")["file"], str(music.MUSIC / "bed.wav"))

    def test_find_takes_the_track_a_person_placed_after_a_make(self):
        _env.write_json("winner.json", {"board": STYLE})
        with mock.patch.object(music.music_engine, "compose", side_effect=engine), contextlib.redirect_stdout(io.StringIO()):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=1))
        (music.MUSIC / "source.mp3").write_bytes(b"their track")
        with mock.patch.object(music, "has_audio", return_value=True), mock.patch.object(music, "duration", return_value=40.0), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_find(types.SimpleNamespace(origin="their phone")), 0)
        info = _env.read_json("music.json")
        self.assertEqual((Path(info["file"]).name, info["origin"]), ("source.mp3", "their phone"))

    def test_clips_json_never_names_a_missing_folder(self):
        _env.write_json("board.json", {"beats": [{"id": "b1", "frames": 4}],
                                       "clips": [{"id": "c1", "beat": "b1", "role": "r", "image": "photos/a.jpg",
                                                  "prompt": "p", "stand_in": "s"}]})
        _env.write_json("film.json", {"boards": {"reel": "board.json"}})
        Path("public/clips/c1").mkdir(parents=True)
        Path("public/clips/c1/0001.jpg").write_bytes(b"the last clip")
        _env.write_json("clips.json", {"clips": {"c1": {"status": "generated", "dir": "clips/c1", "frames": 1}}})
        a = types.SimpleNamespace(why=None)

        def named():
            return [r["dir"] for r in _env.read_json("clips.json")["clips"].values() if r.get("dir")]

        with mock.patch.object(clips, "arrived", return_value=Path("clips/c1.mp4")), \
                mock.patch.object(clips, "conform", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            clips.cmd_normalize(a)
        self.assertTrue(all((Path("public") / d / "0001.jpg").exists() for d in named()))

        def conform(src, image, frames, dst):
            dst.mkdir(parents=True)
            (dst / "0001.jpg").write_bytes(b"the new clip")
            return 1, ""

        with mock.patch.object(clips, "arrived", return_value=Path("clips/c1.mp4")), \
                mock.patch.object(clips, "conform", side_effect=conform), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(clips.cmd_normalize(a), 0)
        self.assertEqual([(Path("public") / d / "0001.jpg").read_bytes() for d in named()], [b"the new clip"])
        self.assertEqual([p.name for p in Path("public/clips").iterdir()], [Path(d).name for d in named()],
                         "the folder clips.json stopped naming is gone")


class CutRound(unittest.TestCase):
    """The critics' round belongs to one reel: the same reel keeps its round, a new one opens the next."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def test_the_same_reel_keeps_its_round_and_a_new_one_opens_the_next(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the first reel")
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("film.py render", str(e.exception.code), "a round opens only over a render's whole out/")
        _env.write_json("render/film-report.json", {"failed": 0})
        with contextlib.redirect_stdout(io.StringIO()):
            vote.cmd_cut(None)
            first = _env.read_json("critic/cut-1.json")
            first["critics"]["person"]["boards"]["film"]["paragraph"] = "seen"
            _env.write_json("critic/cut-1.json", first)
            vote.cmd_cut(None)
            self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
            self.assertEqual(_env.read_json("critic/cut-1.json"), first, "what the critics filled in stays")
            Path("out/film.mp4").write_bytes(b"the second reel")
            vote.cmd_cut(None)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])

    def test_the_gate_takes_only_a_round_the_vote_takes_and_ships_at_the_bar(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the reel")
        _env.write_json("render/film-report.json", {"failed": 0})
        with contextlib.redirect_stdout(io.StringIO()):
            vote.cmd_cut(None)
        full = ("the cut lands every line on its edge and each one stands long enough to read before the camera leaves; "
                "the grid at the end holds the nine first to ninth from its top left and the first holds longest")

        def critic(score, paragraph, n=1):
            data = _env.read_json(f"critic/cut-{n}.json")
            for c in data["critics"].values():
                e = c["boards"]["film"]
                e["scores"] = {k: score for k in vote.CRITERIA}
                e["paragraph"] = paragraph
            _env.write_json(f"critic/cut-{n}.json", data)
            with mock.patch.object(qa, "timed_checks", return_value=([], {})), \
                    mock.patch.object(qa, "film_checks", return_value=([], {"boards": {}}, None)):
                res, _ = qa.gate_checks()
            return next(r for r in res if r[0] == "critic")

        short = critic(5, "the cut lands every line and the wall holds well")
        self.assertFalse(short[1])
        self.assertIn("paragraph", short[2])
        self.assertTrue(critic(5, full)[1], "mean 5 is at the bar")
        under = critic(4, full)
        self.assertFalse(under[1], "a first round under the bar is fixed once before it is delivered")
        Path("out/film.mp4").write_bytes(b"the fixed reel")
        with contextlib.redirect_stdout(io.StringIO()):
            vote.cmd_cut(None)
        spent = critic(4, full, 2)
        self.assertTrue(spent[1], spent[2])
        self.assertIn("under the bar: the scores go in brief.md", spent[2])


class AudioRow(unittest.TestCase):
    """The gate's audio row reads where master placed the effects: their integrated loudness under the bed's."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def audio_row(self, fx_lufs):
        """The audio row over a reel at -14 LUFS whose master measured the bed at -21.4 LUFS and the effects at
        `fx_lufs`."""
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the reel")
        _env.write_json("board.json", {"bpm": 120, "beats": [{"id": "hook"}, {"id": "piece-1"}, {"id": "closer"}],
                                       "sound": [{"kind": "hit", "at": 0.55, "beat": "hook", "what": "the year lands"},
                                                 {"kind": "hit", "at": 5.3, "beat": "piece-1", "what": "the blade cuts"}]})
        _env.write_json("music.json", {"file": "music/source.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs, "sound_cues": 2})
        f = {"boards": {fmt: "board.json" for fmt in qa.FILMS}, "rests": {fmt: {"closer": 0} for fmt in qa.FILMS}, "cuts": [], "hook_frame": 0}
        probed = {"streams": [{"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}], "format": {"duration": "28"}}
        with mock.patch.object(qa, "cut", return_value=f), mock.patch.object(qa, "posts_n", return_value=9), \
                mock.patch.object(qa, "probe", return_value=probed), mock.patch.object(qa, "loudness", return_value=-14.0), \
                mock.patch.object(qa, "detect", return_value=[]), mock.patch.object(qa, "held_from", return_value=28.0), \
                mock.patch.object(qa.studio, "measure", return_value={}), mock.patch.object(qa, "figures"), \
                mock.patch.object(qa, "shown_at", return_value=9):
            res = qa.film_checks()[0]
        return next(r for r in res if r[0] == "audio")

    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_turns_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-16.3)
        self.assertFalse(ok)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("2 sound cues over 3 beats", detail)

    def test_effects_eight_lu_under_the_bed_turn_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-29.4)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)


def engine(style=None, styles=(), avoid=(), seconds=60.0, edges=(), hue=None, seed="", bpm=None, target_bpm=None, out=Path("music")):
    """music_engine.compose writing its bed and answering what it answers, without the instruments: the recipe the brief
    resolves to, at the tempo asked."""
    rid, recipe, removed = music.music_engine.resolve(music.music_engine.recipes(), style, styles, avoid)
    out.mkdir(parents=True, exist_ok=True)
    (out / "bed.wav").write_bytes(f"{rid} at {bpm}".encode())
    return {"recipe": rid, "key": f"A {recipe['mode']}", "bpm": bpm, "seconds": seconds, "beats": [], "downbeats": [], "sections": [],
            "chords": ["Am"], "programs": [], "removed": removed, "fx": {}, "fx_recipe": rid}


class Music(unittest.TestCase):
    """The music is this person's: the track they placed, else a bed made from their music brief, in its mood at its tempo."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        # the tools resolve to names, so the stand-in ffmpeg below only ever writes inside the scratch folder
        tools = mock.patch.object(_env, "tools", lambda: {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"})
        tools.start()
        self.addCleanup(tools.stop)

    def make(self, brief=None, style=STYLE):
        _env.write_json("winner.json", {"board": style})
        _env.write_json("taste.json", {"handle": "cornerloaf", **({"music": brief} if brief else {})})
        with mock.patch.object(music.music_engine, "compose", side_effect=engine), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_make(types.SimpleNamespace(bpm=None, seconds=10)), 0)
        return _env.read_json("music.json")

    def test_the_bed_is_the_looks_own_recipe_unless_their_brief_names_another(self):
        made = {s: self.make(style=s) for s in storyboard.compose.TRIO}
        for style, info in made.items():
            rid = storyboard.compose.card(style)["music"]
            self.assertEqual(info["recipe"], rid)
            self.assertIn(f"from the {rid} recipe", info["origin"])
            self.assertIn("chosen by the look", info["origin"])
        self.assertEqual(len({i["recipe"] for i in made.values()}), 3, "each look has its own music")
        theirs = self.make({"tempo": 72, "styles": ["warm felt piano"]})
        self.assertNotEqual(theirs["recipe"], made[STYLE]["recipe"])
        self.assertIn("chosen by their brief", theirs["origin"])
        self.assertIn("at 72 bpm", theirs["origin"])

    def test_find_with_no_track_placed_makes_the_bed_and_says_where_it_came_from(self):
        _env.write_json("winner.json", {"board": STYLE})
        _env.write_json("taste.json", {"handle": "cornerloaf", "music": {"tempo": 72, "styles": ["warm felt piano"], "avoid": []}})
        with mock.patch.object(music.music_engine, "compose", side_effect=engine), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_find(types.SimpleNamespace(origin=None, bpm=None, seconds=None)), 0)
        origin = _env.read_json("music.json")["origin"]
        self.assertRegex(origin, r"^made by music\.py from the [a-z-]+ recipe \(.+, chosen by their brief\) in A [a-z]+ at 72 bpm$")

    def test_no_look_chosen_makes_no_music(self):
        with self.assertRaises(SystemExit) as e:
            music.cmd_make(types.SimpleNamespace(bpm=None, seconds=10))
        self.assertIn("vote.py pick", str(e.exception.code))
        self.assertFalse(Path("music.json").exists())


if __name__ == "__main__":
    unittest.main()
