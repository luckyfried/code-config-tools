"""grid glow-up's call site of scripts/chunks.py and the steps around it.

studio.render hands chunks.render an invoke that runs render.py, here a stand-in that writes each chunk's frames as a
test pattern with the findings file render.py writes; film.py and storyboard.py take the run's lock before their first
write; a film reaches out/ only once every format is finished; film.py renders only the board that was picked, and a
new draft goes to a new vote; deliver.py's page says "not ready" until the gate passes. Then the kill at any point of
any command: an index (board.json, the boards' sheets, preview/preview.json, render/film.json, clips.json, the review
page) goes before the files it speaks for change, so a render stopped between two moves into out/ leaves a set qa.py
refuses; a file a later command trusts gets its name only when whole, and an old file the index still names goes only
after the new index; deliver holds the lock and runs its gate in its own process, every probe through the lock; and a
cut round is opened once per film. The module itself is tested in test_chunks.py.

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
import studio  # noqa: E402
import vote  # noqa: E402

# the probes a test reads a file with run outside any run's lock
PLAIN = types.SimpleNamespace(spawn=subprocess.run)

# render.py as studio.render calls it (`python3 render.py --jobs JOBS.json`): every chunk is its frameRange's frames of a test pattern
# at its `.part.mp4` with an empty `.part.findings.json` beside it, and every still is a test pattern PNG; each job logs
# its name, with " (lock not held)" when none of its open files (/dev/fd) is the run's render.lock.
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[2]))
ff = os.environ["FAKE_FFMPEG"]
lock = os.stat(os.path.join(os.path.dirname(spec["report"]), "render.lock"))
def same(fd):
    try:
        return os.path.samestat(os.fstat(int(fd)), lock)
    except OSError:
        return False
held = any(same(fd) for fd in os.listdir("/dev/fd"))
for job in spec["jobs"]:
    with open(os.environ["FAKE_LOG"], "a") as log:
        log.write(os.path.basename(job["out"]) + ("" if held else " (lock not held)") + "\n")
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if job["type"] == "video":
        a, b = job["frameRange"]
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", str(b - a + 1),
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64", "-frames:v", "1", job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""
BOARD = {"boards": {"reel": {}, "landscape": {}}, "rests": {"hook": 3}, "hash": "h", "letter": "A", "style": "editorial-quiet",
         "name": "Editorial quiet", "tempo": 120, "seconds": 1, "nine": [], "check": {"pass": True, "faults": []},
         "cuts_at": [], "hook_frame": 0}
# the pick of BOARD, as storyboard.py pick writes it
WIN = {"board": "A", "style": "editorial-quiet", "name": "Editorial quiet", "by": "taste", "reason": "their quiet captions",
       "others": ["B", "C"], "hash": "h"}


def checkable(*formats):
    """Boards qa.py check reads to the end: one beat that is not a post, so no card frame is read."""
    hook = {"id": "hook", "layers": [{}, {"words": {}}, {"keys": []}]}
    return {f: {"beats": [hook], "format": {"width": 1080, "height": 1920}, "system": {"safe": {f: {"left": 0, "right": 0}}}}
            for f in formats}


class Run(unittest.TestCase):
    """A run folder to work in, with the fake renderer, the built composition and no graphics card."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.run_dir = self.dir / "run"
        self.run_dir.mkdir()
        src = self.dir / "src"
        src.mkdir()
        (src / "film.tsx").write_text("one")
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        self.log = self.dir / "rendered.log"
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        tools = dict(_env.tools(), chromium="chrome", dist=str(src))
        for patch in (mock.patch.object(_env, "_TOOLS", tools), mock.patch.object(studio, "SOURCES", (src,)),
                      mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(chunks, "GPU", False), mock.patch.object(_env, "enter_run", lambda new=False: None),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=_env.ffmpeg(), FAKE_LOG=str(self.log))):
            patch.start()
            self.addCleanup(patch.stop)

    def job(self, n=23, out="film.mp4"):
        return {"type": "video", "composition": "Film", "props": {"board": 1}, "frames": n, "scale": 1,
                "out": str((self.run_dir / out).resolve())}

    def rendered(self):
        names = self.log.read_text().splitlines() if self.log.exists() else []
        self.log.unlink(missing_ok=True)
        return names

    def write(self, rel, data):
        Path(rel).parent.mkdir(parents=True, exist_ok=True)
        Path(rel).write_text(json.dumps(data))

    def main(self, module, *argv):
        with mock.patch.object(sys, "argv", [f"{module.__name__}.py", *argv]), contextlib.redirect_stdout(io.StringIO()):
            return module.main()


class CallSite(Run):
    def test_a_143_frame_film_renders_three_chunks_joined_whole_and_a_rerun_keeps_them(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rep = studio.render([self.job(143)], "film")
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(self.rendered(), ["0-59.part.mp4", "60-119.part.mp4", "120-142.part.mp4"])
        self.assertEqual(chunks._frames(PLAIN, _env.ffprobe(), self.run_dir / "film.mp4"), 143)
        with contextlib.redirect_stdout(io.StringIO()):
            rep = studio.render([self.job(143)], "film")
        self.assertEqual((self.rendered(), rep["chunks"]), ([], {"kept": 3, "rendered": 0, "to_go": 0}))
        self.assertEqual(rep["jobs"], 1)

    def test_the_renderers_report_is_staging_until_the_command_publishes_it(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rep = studio.render([self.job(3)], "film")
        self.assertEqual(sorted(p.name for p in Path("render").iterdir() if "report" in p.name), [])
        studio.publish("film", rep)
        self.assertEqual(_env.read_json("render/film-report.json")["failed"], 0)

    @unittest.skipIf(os.name == "nt", "the Windows half is proved on a Windows machine")
    def test_the_renderer_holds_the_render_lock(self):
        with contextlib.redirect_stdout(io.StringIO()):
            studio.render([self.job()], "film")
        self.assertNotIn("(lock not held)", self.log.read_text())

    @unittest.skipIf(os.name == "nt", "the Windows half is proved on a Windows machine")
    def test_a_refused_second_command_leaves_the_first_ones_files_alone(self):
        import fcntl
        import film
        import storyboard
        self.write("board.json", BOARD)
        for L in "ABC":
            self.write(f"storyboards/{L}/board.json", dict(BOARD, letter=L))
        self.write("winner.json", WIN)
        Path("frames").mkdir()
        Path("frames/reel-hook.png").write_bytes(b"the first render's")
        Path("render").mkdir()
        before = sorted(str(p) for p in self.run_dir.rglob("*") if p.name != "render.lock")
        with open("render/render.lock", "w", encoding="utf-8") as held:
            held.write(f"film\t{Path('render/film.log').resolve()}\n")
            held.flush()
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for module, cmd in ((film, "render"), (film, "preview"), (storyboard, "sheets")):
                with mock.patch.object(film.critic, "run_swap", lambda b: {"pass": True}), \
                        mock.patch.object(studio, "render") as bridge, self.assertRaises(SystemExit) as e:
                    self.main(module, cmd)
                self.assertIn("a render named film is already running in this run", str(e.exception.code), cmd)
                self.assertFalse(bridge.called, cmd)
        self.assertEqual(sorted(str(p) for p in self.run_dir.rglob("*") if p.name != "render.lock"), before)
        self.assertEqual(Path("frames/reel-hook.png").read_bytes(), b"the first render's")

    def test_a_film_reaches_out_only_when_every_format_is_finished(self):
        import film
        self.write("board.json", BOARD)
        self.write("winner.json", WIN)
        Path("render/silent").mkdir(parents=True)
        Path("render/silent/film.mp4").write_bytes(b"reel")
        done = {"jobs": 4, "failed": 0, "findings": [], "seconds": 1.0}
        quiet = {"posts": lambda b, into: into.mkdir(parents=True), "grid_after": lambda b, drawn, out: out.write_bytes(b"grid"),
                 "story": lambda src, out: out.write_bytes(b"story")}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(film.critic, "run_swap", lambda b: {"pass": True}))
            stack.enter_context(mock.patch.object(studio, "video", lambda b, out, **k: {"type": "video", "out": str(out)}))
            stack.enter_context(mock.patch.object(studio, "still", lambda b, f, out, **k: {"type": "still", "out": str(out)}))
            stack.enter_context(mock.patch.object(studio, "render", lambda jobs, name, run=None: done))
            for name, value in quiet.items():
                stack.enter_context(mock.patch.object(film, name, value))
            with self.assertRaises(FileNotFoundError):
                self.main(film, "render")
            self.assertFalse(Path("out/film.mp4").exists())
            Path("render/silent/film-landscape.mp4").write_bytes(b"landscape")
            self.assertEqual(self.main(film, "render"), 0)
        self.assertEqual((Path("out/film.mp4").read_bytes(), Path("out/film-landscape.mp4").read_bytes()), (b"reel", b"landscape"))


class Vote(Run):
    def test_a_board_that_was_not_picked_is_neither_previewed_nor_rendered(self):
        import film
        self.write("board.json", BOARD)
        for winner in (None, dict(WIN, board="B"), dict(WIN, hash="an earlier draft's")):
            if winner:
                self.write("winner.json", winner)
            for cmd in ("preview", "render"):
                with mock.patch.object(studio, "render") as bridge, self.assertRaises(SystemExit) as e:
                    self.main(film, cmd)
                self.assertIn("storyboard.py pick", str(e.exception.code), cmd)
                self.assertFalse(bridge.called, cmd)
        self.assertFalse(Path("render").exists())

    def test_a_new_draft_goes_to_a_new_vote_and_a_new_pick(self):
        import storyboard
        self.write("grid.json", {"cells": [{"pos": 0}]})
        self.write("plan.json", {"slots": [{"n": 1}]})
        self.write("board.json", BOARD)
        self.write("winner.json", WIN)
        self.write("vote/scores.json", {})
        Path("vote.md").write_text("the last vote")
        with mock.patch.object(studio, "public", lambda: None), mock.patch.object(storyboard, "before_posts", stopped), \
                self.assertRaises(KeyboardInterrupt):
            self.main(storyboard, "draft")
        self.assertEqual([Path(f).exists() for f in ("board.json", "winner.json", "vote/scores.json", "vote.md")], [False] * 4)

    def test_a_pick_clears_what_the_earlier_pick_made_and_keeps_the_looks(self):
        import storyboard
        for L in "ABC":
            self.write(f"storyboards/{L}/board.json", dict(BOARD, letter=L, hash=L))
            Path(f"storyboards/{L}/storyboard.md").write_text(L)
        self.write("winner.json", WIN)
        self.write("render/film.json", {"hash": "h"})
        self.write("critic/cut-1.json", {})
        self.write("vote/scores.json", {"kept": True})
        Path("out/posts").mkdir(parents=True)
        for f in ("film.mp4", "boards.png", "grid-before.png", "review.html"):
            Path("out", f).write_bytes(b"x")
        Path("music").mkdir()
        Path("music/master.0123.wav").write_bytes(b"the last look's master")
        self.main(storyboard, "pick", "B", "--by", "person", "--reason", "they asked for the second one")
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["boards.png", "grid-before.png"])
        self.assertEqual([Path(f).exists() for f in ("render/film.json", "critic", "music/master.0123.wav")], [False] * 3)
        self.assertEqual((_env.read_json("board.json")["letter"], _env.read_json("winner.json")["by"]), ("B", "person"))
        self.assertTrue(_env.read_json("vote/scores.json")["kept"])


class Deliver(Run):
    def test_a_deliver_stopped_during_its_gate_leaves_a_page_that_says_not_ready(self):
        import deliver
        self.write("library.json", {"handle": "h"})
        self.write("taste.json", {"x": 1})
        self.write("winner.json", WIN)

        def stopped(*a, **k):
            raise KeyboardInterrupt

        with mock.patch.object(deliver.qa, "gate_checks", stopped), mock.patch.object(sys, "argv", ["deliver.py"]), \
                self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertIn("Not ready to post", Path("out/review.html").read_text())
        with mock.patch.object(deliver.qa, "gate_checks", green), mock.patch.object(sys, "argv", ["deliver.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertNotIn("Not ready to post", Path("out/review.html").read_text())
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["review.html"])
        self.assertTrue(Path("brief.md").exists())

    def deliverable(self):
        self.write("library.json", {"handle": "h"})
        self.write("taste.json", {"x": 1})
        self.write("winner.json", WIN)
        Path("out").mkdir()
        Path("out/review.html").write_text("delivered")

    def test_deliver_removes_the_page_before_its_first_write_into_out(self):
        import deliver
        self.deliverable()

        def stopped(*a, **k):
            raise KeyboardInterrupt

        with mock.patch.object(deliver, "brief", stopped), mock.patch.object(sys, "argv", ["deliver.py"]), \
                self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertEqual(list(Path("out").iterdir()), [])

    @unittest.skipIf(os.name == "nt", "the Windows half is proved on a Windows machine")
    def test_deliver_holds_the_run_lock_and_runs_its_gate_through_it(self):
        import fcntl
        import deliver
        self.deliverable()
        Path("render").mkdir()
        with open("render/render.lock", "w", encoding="utf-8") as held:
            held.write(f"film\t{Path('render/film.log').resolve()}\n")
            held.flush()
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(sys, "argv", ["deliver.py"]), self.assertRaises(SystemExit) as e:
                deliver.main()
        self.assertIn("a render named film is already running in this run", str(e.exception.code))
        self.assertEqual([(p.name, p.read_text()) for p in Path("out").iterdir()], [("review.html", "delivered")])
        held = []

        def gate(run):
            held.append(run.name)
            return green(run)

        with mock.patch.object(deliver.qa, "gate_checks", gate), mock.patch.object(sys, "argv", ["deliver.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(held, ["deliver"])

    def test_every_process_the_gate_starts_under_deliver_holds_the_lock(self):
        import deliver
        self.deliverable()
        self.write("board.json", dict(BOARD, boards=checkable("reel")))
        self.write("render/film.json", {"hash": "h", "formats": ["reel"]})
        Path("out/film.mp4").write_bytes(b"reel")
        started, inside, spawn = [], [], chunks.Run.spawn

        def through(run, argv, **k):
            inside.append(run.name)
            try:
                return spawn(run, argv, **k)
            finally:
                inside.pop()

        def tool(argv, **k):
            started.append((Path(argv[0]).name, inside[-1] if inside else None))
            return types.SimpleNamespace(returncode=0, stdout='{"format": {"duration": "1.0"}}' if "json" in argv else "1.0", stderr="")

        with mock.patch.object(chunks.Run, "spawn", through), mock.patch.object(subprocess, "run", tool), \
                mock.patch.object(sys, "argv", ["deliver.py"]), contextlib.redirect_stdout(io.StringIO()):
            deliver.main()
        self.assertIn(("ffprobe", "deliver"), started)
        self.assertEqual([s for s in started if s[1] != "deliver"], [])


def stopped(*a, **k):
    raise KeyboardInterrupt


def green(run):
    """A gate with every check passing."""
    import qa
    return qa.Checks(), {"hash": "h"}


class Killed(Run):
    """A command killed part way leaves no index naming files it was changing, and no file under its name half made."""

    def test_a_render_takes_the_page_and_film_json_first_and_moves_the_reel_into_out_last(self):
        import film
        self.write("board.json", dict(BOARD, boards={"reel": {"beats": []}, "landscape": {"beats": []}}))
        self.write("winner.json", WIN)
        self.write("render/film.json", {"hash": "h"})
        Path("out/posts").mkdir(parents=True)
        for name, data in (("review.html", b"delivered"), ("posts/01.png", b"old 1"), ("posts/09.png", b"old 9")):
            Path("out", name).write_bytes(data)
        self.write("music.json", {"file": None, "origin": None})
        Path("music").mkdir()
        Path("music/master.wav").write_bytes(b"a master music.json does not name")
        with mock.patch.object(film.critic, "run_swap", lambda b: {"pass": True}), \
                mock.patch.object(studio, "render", stopped), self.assertRaises(KeyboardInterrupt):
            self.main(film, "render")
        self.assertFalse(Path("out/review.html").exists())
        self.assertFalse(Path("render/film.json").exists())
        moved, real = [], os.replace

        def replace(a, b):
            if Path(b).parts[0] == "out":
                moved.append(str(b))
            real(a, b)

        with self.made() as stack:
            stack.enter_context(mock.patch.object(os, "replace", replace))
            self.assertEqual(self.main(film, "render"), 0)
        self.assertEqual(moved[-1], "out/film.mp4")
        self.assertEqual(sorted(p.name for p in Path("out/posts").iterdir()), ["01.png"])
        self.assertEqual(Path("out/posts/01.png").read_bytes(), b"new 1")
        self.assertTrue(Path("render/film.json").exists())

    def made(self):
        """film.py render's makers as stand-ins: the films already under render/silent, one post, the grid after, the
        Story card."""
        import film
        Path("render/silent").mkdir(parents=True, exist_ok=True)
        Path("render/silent/film.mp4").write_bytes(b"reel")
        Path("render/silent/film-landscape.mp4").write_bytes(b"landscape")

        def drawn(b, into):
            shutil.rmtree(into, ignore_errors=True)
            into.mkdir(parents=True)
            (into / "01.png").write_bytes(b"new 1")

        done = {"jobs": 4, "failed": 0, "findings": [], "seconds": 1.0}
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(film.critic, "run_swap", lambda b: {"pass": True}))
        stack.enter_context(mock.patch.object(studio, "video", lambda b, out, **k: {"type": "video", "out": str(out)}))
        stack.enter_context(mock.patch.object(studio, "still", lambda b, f, out, **k: {"type": "still", "out": str(out)}))
        stack.enter_context(mock.patch.object(studio, "render", lambda jobs, name, run=None: done))
        stack.enter_context(mock.patch.object(film, "posts", drawn))
        stack.enter_context(mock.patch.object(film, "grid_after", lambda b, drawn, out: out.write_bytes(b"grid")))
        stack.enter_context(mock.patch.object(film, "story", lambda src, out: out.write_bytes(b"story")))
        return stack

    def test_a_render_killed_in_its_moves_into_out_then_before_them_leaves_a_set_qa_refuses(self):
        import film
        import qa
        self.write("board.json", dict(BOARD, boards=checkable("reel", "landscape")))
        self.write("winner.json", WIN)
        self.write("render/film.json", {"hash": "h", "formats": ["reel", "landscape"], "music": False})
        self.write("render/film-report.json", {"jobs": 4, "failed": 0, "findings": []})
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last render's reel")
        real = os.replace

        def killed_at(k):
            moved = []

            def replace(a, b):
                if Path(b).parts[0] == "out":
                    moved.append(str(b))
                    if len(moved) == k:
                        raise KeyboardInterrupt
                real(a, b)
            return replace

        # killed between two moves into out/, then the retry killed before its first
        for k in (2, 1):
            with self.made() as stack, self.assertRaises(KeyboardInterrupt):
                stack.enter_context(mock.patch.object(os, "replace", killed_at(k)))
                self.main(film, "render")
            self.assertEqual([Path(f).exists() for f in ("render/film.json", "render/film-report.json")], [False, False])
            first = qa.film_checks()[0][0]
            self.assertEqual(first[:2], ("format", False))
            self.assertIn("render/film.json is not for this board", first[2])

    def test_every_command_that_changes_what_the_review_page_shows_takes_the_page_first(self):
        import plan
        import research
        Path("out").mkdir()
        cad = {"gap_days": 1, "weekday": "Monday", "hour_utc": 9}
        writes = (lambda: plan.write_md({"cadence": cad, "slots": []}),
                  lambda: research.render_audit({"grid_size": 30, "findings": [], "patterns": [], "want": "w"}, "h"))
        for write in writes:
            Path("out/review.html").write_text("delivered")
            write()
            self.assertFalse(Path("out/review.html").exists())

    def test_a_preview_killed_while_rendering_leaves_no_preview_json(self):
        import film
        self.write("board.json", dict(BOARD, boards={"reel": {"beats": []}}))
        self.write("winner.json", WIN)
        self.write("preview/preview.json", {"hash": "h"})
        with mock.patch.object(studio, "render", stopped), self.assertRaises(KeyboardInterrupt):
            self.main(film, "preview")
        self.assertFalse(Path("preview/preview.json").exists())

    def test_a_draft_killed_among_its_photographs_leaves_no_board_and_no_vote(self):
        import storyboard
        self.write("grid.json", {"cells": [{"pos": 0}]})
        self.write("plan.json", {"slots": [{"n": 1}]})
        self.write("board.json", BOARD)
        self.write("winner.json", WIN)
        self.write("storyboards/A/board.json", BOARD)
        Path("storyboards/A/sheet.png").write_bytes(b"the old board's sheet")
        with mock.patch.object(studio, "public", lambda: None), mock.patch.object(storyboard, "before_posts", stopped), \
                self.assertRaises(KeyboardInterrupt):
            self.main(storyboard, "draft")
        self.assertEqual([Path(f).exists() for f in ("board.json", "winner.json", "storyboards")], [False] * 3)

    def test_sheets_killed_between_two_stills_leave_no_board_sheet(self):
        import storyboard
        for L in "ABC":
            self.write(f"storyboards/{L}/board.json", dict(BOARD, letter=L, rests={"hook": 1, "dense": 2, "closer": 3}))
            Path(f"storyboards/{L}/sheet.png").write_bytes(b"the old board's sheet")
        Path("out").mkdir()
        Path("out/boards.png").write_bytes(b"the old looks")
        with mock.patch.object(studio, "render", stopped), self.assertRaises(KeyboardInterrupt):
            self.main(storyboard, "sheets")
        self.assertEqual([Path(f"storyboards/{L}/sheet.png").exists() for L in "ABC"] + [Path("out/boards.png").exists()], [False] * 4)
        with self.assertRaises(SystemExit) as e:
            self.main(vote, "ballot")
        self.assertIn("storyboard.py sheets", str(e.exception.code))

    def clips_board(self):
        beats = [{"id": "b1", "frames": 3}, {"id": "b2", "frames": 3}]
        clips = [{"id": c, "beat": b, "role": "r", "image": "x.jpg", "prompt": "p", "stand_in": "s"} for c, b in (("c1", "b1"), ("c2", "b2"))]
        self.write("board.json", {"boards": {"reel": {"beats": beats, "clips": clips}}})
        Path("clips").mkdir()
        for c in ("c1", "c2"):
            Path(f"clips/{c}.mp4").write_bytes(c.encode() * 1000)

    def test_a_normalize_killed_on_its_second_clip_leaves_the_clips_the_index_names(self):
        import clips
        self.clips_board()
        Path("public/clips/c1-old").mkdir(parents=True)
        Path("public/clips/c1-old/0001.jpg").write_bytes(b"frame")
        old = {"clips": {"c1": {"status": "generated", "image": "x.jpg", "from_frame": 0, "frames": 1, "dir": "clips/c1-old"}}}
        self.write("clips.json", old)
        calls = []

        def ffmpeg(argv, **k):
            calls.append(argv)
            if len(calls) == 2:
                raise KeyboardInterrupt
            Path(argv[-1].replace("%04d", "0001")).write_bytes(b"frame")
            return types.SimpleNamespace(returncode=0, stderr="")

        with mock.patch.object(clips, "size_of", lambda image: (64, 64)), mock.patch.object(clips.subprocess, "run", ffmpeg):
            with self.assertRaises(KeyboardInterrupt):
                self.main(clips, "normalize")
            self.assertEqual(json.loads(Path("clips.json").read_text()), old)
            self.assertEqual(Path("public/clips/c1-old/0001.jpg").read_bytes(), b"frame")
            calls.append("the second clip goes through")
            self.main(clips, "normalize")
            dirs = sorted(r["dir"] for r in clips.placed())
            self.assertEqual(sorted(f"clips/{d.name}" for d in Path("public/clips").iterdir()), dirs)
            self.assertEqual([d.split("/")[1][:3] for d in dirs], ["c1-", "c2-"])
            ran = len(calls)
            self.main(clips, "normalize")
            self.assertEqual((len(calls), sorted(r["dir"] for r in clips.placed())), (ran, dirs))

    def test_a_photo_or_a_graded_copy_killed_half_made_is_not_taken_as_done(self):
        import grade
        import picks
        from PIL import Image
        src = self.dir / "photo.png"
        Image.new("RGB", (40, 30), "red").save(src)
        save = Image.Image.save

        def half(im, fp, *a, **k):
            Path(fp).write_bytes(b"half")
            raise KeyboardInterrupt

        with mock.patch.object(Image.Image, "save", half), self.assertRaises(KeyboardInterrupt):
            picks.prepare(src)
        with mock.patch.object(Image.Image, "save", save):
            Image.open(picks.prepare(src)).verify()
        Path("graded").mkdir()

        def ffmpeg(argv, **k):
            Path(argv[-1]).write_bytes(b"half")
            return types.SimpleNamespace(returncode=1, stderr="killed")

        with mock.patch.object(grade.subprocess, "run", ffmpeg):
            self.assertFalse(grade.grade_file(src, Path("graded/photo.jpg"), "null")[0])
        self.assertEqual(list(Path("graded").iterdir()), [])

    def test_a_make_killed_before_its_music_json_keeps_the_set_the_old_one_names(self):
        import music
        Path("music").mkdir()
        Path("music/source.wav").write_bytes(b"the last bed")
        Path("music/master.wav").write_bytes(b"its master")
        old = {"file": "music/source.wav", "origin": "made", "master": "music/master.wav"}
        self.write("music.json", old)
        write = _env.write_json

        def killed(path, obj):
            if str(path) == "music.json":
                raise KeyboardInterrupt
            write(path, obj)

        self.write("board.json", dict(BOARD, boards={"reel": {"beats": [{}]}}))
        with mock.patch.object(_env, "write_json", killed), self.assertRaises(KeyboardInterrupt):
            self.main(music, "make", "--seconds", "1")
        self.assertEqual(json.loads(Path("music.json").read_text()), old)
        self.assertEqual([Path(f).read_bytes() for f in ("music/source.wav", "music/master.wav")], [b"the last bed", b"its master"])
        self.main(music, "make", "--seconds", "1")
        made = _env.read_json("music.json")
        self.assertTrue(made["made"] and Path(made["file"]).is_file())
        self.assertIn("editorial-quiet recipe", made["origin"])

    def test_find_takes_the_track_a_person_placed_over_a_source_make_wrote(self):
        import music
        Path("music").mkdir()
        made = "music/source.0123456789ab.wav"
        Path(made).write_bytes(b"a bed make wrote")
        self.write("music.json", {"file": made, "origin": "made"})
        Path("music/source.mp3").write_bytes(b"the person's track")
        with mock.patch.object(music, "has_audio", lambda p: True), mock.patch.object(music, "duration", lambda p: 40.0):
            self.main(music, "find")
        self.assertEqual(_env.read_json("music.json")["file"], "music/source.mp3")

    def test_a_cut_round_is_opened_once_for_each_film_that_film_json_names(self):
        self.write("board.json", BOARD)
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"a reel no finished render names")
        with self.assertRaises(SystemExit) as e:
            self.main(vote, "cut")
        self.assertIn("render/film.json", str(e.exception.code))
        self.write("render/film.json", {"hash": "h", "reel": "first"})
        with self.assertRaises(SystemExit) as e:
            self.main(vote, "cut")
        self.assertIn("run qa.py check", str(e.exception.code))
        self.write("qa/check.json", {"film": "first"})
        for _ in range(2):
            self.main(vote, "cut")
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
        # a film rendered again before its round was filled in takes that round
        self.write("render/film.json", {"hash": "h", "reel": "again"})
        self.write("qa/check.json", {"film": "again"})
        self.main(vote, "cut")
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
        self.assertEqual(_env.read_json("critic/cut-1.json")["film"], "again")
        data = _env.read_json("critic/cut-1.json")
        for c in data["critics"].values():
            c["boards"]["film"].update(scores={k: 4 for k in vote.CRITERIA}, paragraph="a word " * 13)
        self.write("critic/cut-1.json", data)
        self.write("render/film.json", {"hash": "h", "reel": "fixed"})
        self.write("qa/check.json", {"film": "fixed"})
        self.main(vote, "cut")
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["round"], 2)

    def test_a_tally_killed_while_writing_vote_md_leaves_no_vote_md(self):
        data = vote.blank(vote.PANEL, list(vote.LETTERS), vote.BOARD)
        for c in data["critics"].values():
            for L, e in c["boards"].items():
                e.update(scores={k: 5 if L == "B" else 4 for k in vote.BOARD}, paragraph="a word " * 13)
        self.write("vote/scores.json", data)
        for L, style in zip("ABC", ("editorial-quiet", "swiss-grid", "kinetic-type")):
            self.write(f"storyboards/{L}/board.json", dict(BOARD, letter=L, style=style))
            Path(f"storyboards/{L}/sheet.png").write_bytes(b"sheet")
        Path("vote.md").write_text("the last vote")
        with mock.patch.object(_env, "write_text", stopped), self.assertRaises(KeyboardInterrupt):
            self.main(vote, "tally")
        self.assertEqual(Path("vote.md").read_text(), "the last vote")
        self.assertEqual(self.main(vote, "tally"), 0)
        self.assertIn("| B | swiss-grid |", Path("vote.md").read_text().split("\n")[4])

    def test_a_plan_check_stopped_before_plan_md_keeps_the_agents_plan_json_and_the_gate_refuses(self):
        import plan
        import qa
        slot = {"n": 1, "weekday": "Monday", "date": "2026-10-26", "time_utc": "09:00", "file": "posts/01.png",
                "grid_spot": "top left", "caption": "the agent's own words for this post"}
        authored = {"drafted": False, "cadence": {"gap_days": 1, "weekday": "Monday", "hour_utc": 9},
                    "slots": [slot, dict(slot, n=2)]}
        self.write("plan.json", authored)
        written = Path("plan.json").read_bytes()
        Path("plan.md").write_text("| 1 |\n| 2 |\n")
        with mock.patch.object(plan, "crop_sheet", stopped), self.assertRaises(KeyboardInterrupt):
            plan.publish(authored, sheet=True)
        self.assertEqual(Path("plan.json").read_bytes(), written)
        self.assertFalse(Path("plan.md").exists())
        board = {"boards": {}, "nine": [], "letter": "A", "hash": "h"}
        with mock.patch.object(qa, "board_checks", lambda: (qa.Checks(), board)), \
                mock.patch.object(qa, "film_checks", lambda run=None: (qa.Checks(), board, None)):
            res, _ = qa.gate_checks()
        row = next(r for r in res if r[0] == "plan")
        self.assertFalse(row[1])
        self.assertIn("plan.md lists []", row[2])

    def test_a_file_is_made_under_a_name_of_its_own_command(self):
        tmp = _env.part(Path("render/film.json"))
        self.assertEqual((tmp.parent, tmp.name), (Path("render"), f".film.{os.getpid()}.part.json"))
        _env.write_json("render/film.json", {"a": 1})
        self.assertEqual([p.name for p in Path("render").iterdir()], ["film.json"])


if __name__ == "__main__":
    unittest.main()


class Critic(Run):
    """The gate's critic row takes a cut round only when vote.py verdict would: whole scores and full paragraphs from
    every critic on the cut's panel, for the film in out/."""

    def gate_row(self, paragraph, score=5):
        import qa
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the cut")
        board = dict(BOARD, nine=[])
        critics = {c: {"boards": {"film": {"scores": {k: score for k in vote.CRITERIA}, "paragraph": paragraph}}}
                   for c in vote.CUT_PANEL}
        self.write("critic/cut-1.json", {"film": qa.sha(Path("out/film.mp4")), "critics": critics})
        with mock.patch.object(qa, "board_checks", lambda: ([], board)), \
                mock.patch.object(qa, "film_checks", lambda run=None: ([], board, None)):
            res, _ = qa.gate_checks()
        return next(r for r in res if r[0] == "critic")

    def test_every_score_five_with_a_ten_word_paragraph_is_red_naming_the_paragraph(self):
        _, ok, detail = self.gate_row("the croissants land well and the band reads at arm's length")
        self.assertFalse(ok)
        self.assertIn("paragraph", detail)

    def test_every_score_at_the_bar_with_full_paragraphs_is_green(self):
        _, ok, detail = self.gate_row(" ".join(["the frame carries each post in under its own note and lands it"] * 3))
        self.assertTrue(ok, detail)

    def test_every_score_four_is_under_the_bar_and_the_first_round_is_red_until_its_fix(self):
        _, ok, detail = self.gate_row(" ".join(["the frame carries each post in under its own note and lands it"] * 3), 4)
        self.assertFalse(ok)
        self.assertIn("FIX ONCE", detail)
