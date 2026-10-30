"""film.py's draft and render over scripts/chunks.py: a fake renderer renders each chunk job as a small real clip the way
the shared render.py does (the clip at its `.part.mp4`, the findings file beside it once its checks pass), so what
the render stages into cut/, when, and which of their processes hold the run's lock are the kit's own. The module
itself is tests/test_chunks.py.

    python3 -I -m unittest discover -s S/tests -p test_resume.py
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
# the look every board in these tests takes: the first of the trio
STYLE = "cinematic-letterbox"
import _env  # noqa: E402
import chunks  # noqa: E402
import film  # noqa: E402

# render.py as the bridge sees it: each video job's clip lands at its `.part.mp4` with its findings file beside it,
# and a still at its `out`. The ranges in FAKE_FAIL fail with a RENDER_ERROR and no findings file.
FAKE_RENDERER = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[-1]))
fail = set(filter(None, os.environ.get("FAKE_FAIL", "").split(",")))
findings = []
for job in spec["jobs"]:
    tag = "-".join(map(str, job["frameRange"])) if job["type"] == "video" else "still"
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if tag in fail:
        findings.append({"job": job["out"], "text": "RENDER_ERROR fake"})
        continue
    if job["type"] == "video":
        n = job["frameRange"][1] - job["frameRange"][0] + 1
        subprocess.run([os.environ["FAKE_FFMPEG"], "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", str(n),
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-f", "mp4", job["out"]], check=True)
        json.dump([], open(job["out"].removesuffix(".mp4") + ".findings.json", "w"))
    else:
        open(job["out"], "wb").write(b"png")
json.dump({"findings": findings}, open(spec["report"], "w"))
"""

# ffmpeg and ffprobe as the commands start them: each run appends to FAKE_LOG whether one of its open files is the run's
# render lock, then runs the real tool.
TOOL = r"""
import os, sys
lock = os.environ["FAKE_LOCK"]
def same(fd):
    try:
        return os.path.exists(lock) and os.path.samestat(os.fstat(int(fd)), os.stat(lock))
    except OSError:
        return False
held = any(same(fd) for fd in os.listdir("/dev/fd"))
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(f"{os.path.basename(sys.argv[0])} {'held' if held else 'not held'}\n")
os.execv(os.environ["FAKE_REAL"] + os.path.basename(sys.argv[0])[len("fake-"):], [sys.argv[0], *sys.argv[1:]])
"""


def frames(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return int(r.stdout.strip() or -1)


class Run(unittest.TestCase):
    """A run folder, a kit motion folder, the fake renderer and the logging ffmpeg and ffprobe, with the bridge pointed at
    them and chunks of 60 frames (the processor's plan)."""
    def setUp(self):
        # the run sits under a folder with an apostrophe and is named relative to the working folder, as _env names it
        self.d = Path(tempfile.mkdtemp(prefix="it's-", dir=os.environ.get("TMPDIR"))).resolve()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        here = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, here)
        run = Path("build") / "run"
        (run / "public").mkdir(parents=True)
        (run / "public" / "photo.jpg").write_bytes(b"one")
        self.motion = self.d / "motion"
        for f in ("studio/Film.tsx", "system/system.tsx"):
            (self.motion / f).parent.mkdir(parents=True, exist_ok=True)
            (self.motion / f).write_text(f)
        for name, body in (("render.py", FAKE_RENDERER), ("fake-ffmpeg", TOOL), ("fake-ffprobe", TOOL)):
            (self.d / name).write_text(f"#!{sys.executable}\n{body}")
            (self.d / name).chmod((self.d / name).stat().st_mode | stat.S_IEXEC)
        self.log = self.d / "tools.log"
        real = str(Path(shutil.which("ffmpeg")).parent) + os.sep
        self.env = {"FAKE_LOG": str(self.log), "FAKE_LOCK": str((run / "render" / "render.lock").resolve()), "FAKE_REAL": real,
                    "FAKE_FFMPEG": shutil.which("ffmpeg"), "FAKE_FAIL": ""}
        tools = {"chromium": str(self.d / "chromium"), "dist": str(self.motion / "dist"), "motion": str(self.motion),
                 "ffmpeg": str(self.d / "fake-ffmpeg"), "ffprobe": str(self.d / "fake-ffprobe")}
        saved = (_env.B, _env.tools, chunks.GPU, film.RENDERER)
        self.addCleanup(lambda: (setattr(_env, "B", saved[0]), setattr(_env, "tools", saved[1]), setattr(chunks, "GPU", saved[2]),
                                 setattr(film, "RENDERER", saved[3])))
        _env.B, _env.tools, chunks.GPU, film.RENDERER = run, (lambda: tools), False, self.d / "render.py"
        self.run_dir = run


class Commands(Run):
    """film.py render and draft through main, over the fake renderer, with the board, the clips, the then/now image, the
    check after the render and the timing round stubbed: the reel runs 23 frames and the square 26, so a range of 0-25
    fails the square alone."""
    def setUp(self):
        super().setUp()
        import clips
        import qa
        import storyboard
        saved = {(m, k): getattr(m, k) for m, k in ((film, "chosen"), (film, "props"), (film, "timeline"), (film, "board_sha"), (film, "mux"),
                                                       (film, "then_now"), (clips, "write_requests"), (clips, "normalize"), (qa, "film_checks"),
                                                       (storyboard, "lay_out"), (storyboard, "starts"), (storyboard, "measured"))}
        self.addCleanup(lambda: [setattr(m, k, v) for (m, k), v in saved.items()])
        film.chosen = lambda: {"board": STYLE}
        film.props = lambda b: {"board": b["id"]}
        film.timeline = lambda b: {"seconds": 23 / 30, "frames": 23}
        film.board_sha = lambda b: "sha"
        storyboard.lay_out = lambda style, f="reel": {"id": f, "stills": {"hook": 1, "dense": 2, "closer": 3}}
        storyboard.starts = lambda b: ([0], 26 if b["id"] == "square" else 23)
        storyboard.measured = lambda: []
        film.then_now = lambda board, rows, dst: (dst.parent.mkdir(parents=True, exist_ok=True), dst.write_bytes(b"png"))
        clips.write_requests = lambda b: []
        clips.normalize = lambda b, why=None: 0
        self.film_checks, self.checked = saved[(qa, "film_checks")], []
        qa.film_checks = lambda res, run=None: self.checked.append(sorted(p.name for p in _env.cut().iterdir()))
        _env.write_json(self.run_dir / "critic" / "timing.json", {"pass": True, "board_sha": "sha"})
        self.out = self.run_dir / "cut"

    def main(self, *args, **env):
        old, argv = dict(os.environ), sys.argv
        os.environ.update(self.env, **env)
        sys.argv = ["film.py", *args]
        try:
            return film.main()
        finally:
            os.environ.clear()
            os.environ.update(old)
            sys.argv = argv

    def delivered(self):
        return sorted(str(f.relative_to(self.out)) for f in self.out.rglob("*") if f.is_file()) if self.out.exists() else []

    def test_a_render_with_a_failed_format_delivers_nothing_and_the_rerun_finishes_the_same_run(self):
        self.assertEqual(self.main("render", "--also", "landscape", "square", FAKE_FAIL="0-25"), 1)
        self.assertEqual(self.delivered(), [])
        self.assertEqual(self.main("render", "--also", "landscape", "square"), 0)
        self.assertEqual(_env.B, self.run_dir)
        self.assertEqual(self.delivered(), ["cover.png", "film-16x9.mp4", "film-square.mp4", "film.mp4", "stories/01-hook.png",
                                            "stories/02-dense.png", "stories/03-closer.png", "then-now.png"])
        self.assertEqual(frames(self.out / "film-square.mp4"), 26)

    def test_a_render_killed_during_the_mux_delivers_nothing(self):
        mux = film.mux

        def killed(run, silent, out, seconds):
            if "square" in out.name:
                Path(out).write_bytes(b"half a film")
                raise KeyboardInterrupt
            return mux(run, silent, out, seconds)
        film.mux = killed
        with self.assertRaises(KeyboardInterrupt):
            self.main("render", "--also", "square")
        self.assertEqual(self.delivered(), [])

    @unittest.skipIf(os.name == "nt", "flock is POSIX; the Windows lock is proved on a Windows machine")
    def test_a_refused_second_command_changes_nothing_in_the_run(self):
        draft = self.run_dir / "draft" / "film.mp4"
        draft.parent.mkdir(parents=True)
        draft.write_bytes(b"the first draft")
        lock = self.run_dir / "render" / "render.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        holder = subprocess.Popen([sys.executable, "-c", "import fcntl, sys, time\nf = open(sys.argv[1], 'a+')\nfcntl.flock(f, fcntl.LOCK_EX)\n"
                                   "f.truncate(0); f.write('report\\n'); f.flush()\nprint('held', flush=True)\ntime.sleep(60)", str(lock)],
                                  stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.kill)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        with self.assertRaises(SystemExit) as e:
            self.main("draft")
        self.assertIn("a render named report is already running in this run", e.exception.code)
        self.assertEqual(draft.read_bytes(), b"the first draft")
        self.assertFalse((self.run_dir / "timeline.json").exists())

    def test_every_process_a_render_starts_holds_the_runs_lock(self):
        self.assertEqual(self.main("render"), 0)
        ran = self.log.read_text().splitlines()
        self.assertIn("fake-ffmpeg held", ran)
        self.assertIn("fake-ffprobe held", ran)
        self.assertEqual([x for x in ran if x.endswith(" not held")], [])

    def test_a_render_removes_the_review_page_before_it_changes_the_cut(self):
        page = self.out / "review.html"
        page.parent.mkdir(parents=True)
        page.write_text("the last deliver's ready page")
        move = os.replace

        def killed(src, dst):
            if Path(dst).resolve().is_relative_to(self.out.resolve()):
                raise KeyboardInterrupt
            return move(src, dst)
        film.os.replace = killed
        self.addCleanup(setattr, film.os, "replace", move)
        with self.assertRaises(KeyboardInterrupt):
            self.main("render")
        self.assertFalse(page.exists())

    def test_a_render_killed_between_two_files_in_the_cut_leaves_no_report_and_a_finished_one_writes_it(self):
        report = self.run_dir / "render" / "report.json"
        move = os.replace
        moved = []

        def killed(src, dst):
            if Path(dst).resolve().is_relative_to(self.out.resolve()):
                if moved:
                    raise KeyboardInterrupt
                moved.append(dst)
            return move(src, dst)
        film.os.replace = killed
        self.addCleanup(setattr, film.os, "replace", move)
        with self.assertRaises(KeyboardInterrupt):
            self.main("render")
        self.assertFalse(report.exists())
        film.os.replace = move
        self.assertEqual(self.main("render"), 0)
        self.assertEqual(_env.B, self.run_dir)
        self.assertEqual(_env.read_json(report)["failed"], 0)

    def test_a_render_stopped_before_its_report_is_finished_in_the_same_run_and_nothing_reads_it_before(self):
        import vote
        report = self.run_dir / "render" / "report.json"
        move = os.replace

        def before_the_report(src, dst):
            if Path(dst).name == "report.json":
                raise KeyboardInterrupt
            return move(src, dst)
        film.os.replace = before_the_report
        self.addCleanup(setattr, film.os, "replace", move)
        with self.assertRaises(KeyboardInterrupt):
            self.main("render")
        film.os.replace = move
        self.assertIn("film.mp4", self.delivered())
        self.assertFalse(report.exists())
        mux = film.mux

        def killed(run, silent, out, seconds):
            raise KeyboardInterrupt
        film.mux = killed
        with self.assertRaises(KeyboardInterrupt):
            self.main("render", "--also", "square")
        self.assertEqual(_env.B, self.run_dir)
        self.assertFalse(report.exists())
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("film.py render", str(e.exception.code))
        film.mux = mux
        self.assertEqual(self.main("render"), 0)
        self.assertEqual(_env.B, self.run_dir)
        self.assertEqual(_env.read_json(report)["failed"], 0)

    def test_the_cut_refuses_a_finished_render_whose_reel_is_gone(self):
        import vote
        self.assertEqual(self.main("render"), 0)
        (self.out / "film.mp4").unlink()
        _env.write_json(self.run_dir / "film.json", {"board": STYLE})
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("cut/film.mp4 is missing", str(e.exception.code))
        self.assertEqual(vote.rounds(), [])

    def test_the_reel_renders_with_its_cover_and_story_cards_and_other_shapes_only_when_asked(self):
        self.assertEqual(self.main("render"), 0)
        cards = ["cover.png", "stories/01-hook.png", "stories/02-dense.png", "stories/03-closer.png", "then-now.png"]
        self.assertEqual(self.delivered(), sorted(cards + ["film.mp4"]), "the reel with its cover, story cards and then/now card, no other shape")
        self.assertEqual(self.checked, [["cover.png", "film.mp4", "stories", "then-now.png"]])
        self.assertFalse(_env.out().exists(), "a render publishes nothing: deliver does")
        self.assertEqual(_env.read_json(_env.b("render", "report.json"))["made"], {"formats": ["reel"]})
        self.assertEqual(self.main("render", "--also", "square"), 0)
        out = _env.cut()
        self.assertEqual(sorted(str(f.relative_to(out)) for f in out.rglob("*") if f.is_file()), sorted(cards + ["film-square.mp4", "film.mp4"]))
        self.assertEqual(_env.read_json(_env.b("render", "report.json"))["made"], {"formats": ["reel", "square"]})

    def test_the_check_fails_a_shape_nobody_asked_for_and_a_missing_cover_or_story_card(self):
        import qa
        _env.write_json(self.run_dir / "timeline.json", {"seconds": 23 / 30, "frames": 23})
        _env.write_json(self.run_dir / "film.json", {"board": STYLE})
        _env.write_json(self.run_dir / "render" / "report.json", {"failed": 0, "made": {"formats": ["reel"]}})
        self.out.mkdir(parents=True)
        shutil.copyfile(shutil.which("ffprobe"), self.out / "film-square.mp4")
        res = qa.Checks()
        self.film_checks(res)
        self.assertIn("cut/film-square.mp4 is in cut/, and the render did not make it (nobody asked for it)",
                      next(d for n, ok, d in res if n == "film"))
        _env.need("PIL")
        from PIL import Image
        then = Image.new("L", (1080, 1080))
        then.paste(255, (540, 0, 1080, 1080))
        then.save(self.out / "then-now.png")
        ok, detail = qa.cards_check()
        self.assertFalse(ok)
        self.assertIn("missing: 01-hook.png, 02-dense.png, 03-closer.png, cover.png", detail)
        (self.out / "stories").mkdir()
        tall = Image.new("RGB", (1080, 1920))
        for name in ("01-hook.png", "02-dense.png", "03-closer.png"):
            tall.save(self.out / "stories" / name)
        tall.save(self.out / "cover.png")
        self.assertTrue(qa.cards_check()[0])

    def test_a_draft_removes_its_check_before_its_media(self):
        check = self.run_dir / "draft" / "check.json"
        _env.write_json(check, {"board": STYLE, "board_sha": "sha"})
        rmtree = shutil.rmtree

        def killed(*a, **k):
            raise KeyboardInterrupt
        shutil.rmtree = killed
        self.addCleanup(setattr, shutil, "rmtree", rmtree)
        with self.assertRaises(KeyboardInterrupt):
            self.main("draft")
        self.assertFalse(check.exists())

    @unittest.skipIf(os.name == "nt", "flock is POSIX; the Windows lock is proved on a Windows machine")
    def test_the_tools_resolve_before_the_lock_is_taken(self):
        import fcntl
        tools, seen = _env.tools(), []

        def resolve():
            if not seen:
                lock = self.run_dir / "render" / "render.lock"
                lock.parent.mkdir(parents=True, exist_ok=True)
                with open(lock, "a+") as f:
                    try:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        seen.append("free")
                    except OSError:
                        seen.append("held")
            return tools
        _env.tools = resolve
        self.assertEqual(self.main("render"), 0)
        self.assertEqual(seen, ["free"])

    def test_a_render_killed_while_it_fills_the_cut_never_leaves_the_reel_without_the_rest(self):
        move = os.replace
        moved = []

        def killed(src, dst):
            if Path(dst).resolve().is_relative_to(self.out.resolve()):
                if moved:
                    raise KeyboardInterrupt
                moved.append(dst)
            return move(src, dst)
        film.os.replace = killed
        self.addCleanup(setattr, film.os, "replace", move)
        with self.assertRaises(KeyboardInterrupt):
            self.main("render")
        film.os.replace = move
        self.assertNotIn("film.mp4", self.delivered())
        self.assertEqual(len(self.delivered()), 1)


if __name__ == "__main__":
    unittest.main()
