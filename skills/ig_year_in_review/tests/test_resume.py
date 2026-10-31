"""yir's call site of scripts/chunks.py: studio.render hands chunks.render an invoke that runs render.py, here a
stand-in for it that writes each chunk's frames as a test pattern with the findings file render.py writes, and
film.py takes the run's lock before its first write. The module itself is tested in test_chunks.py.

    python3 -I -m unittest discover -s S/tests -p test_resume.py
"""
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
    if job["type"] == "video":
        a, b = job["frameRange"]
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", str(b - a + 1),
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64", "-frames:v", "1", job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""


def frames(mp4):
    return chunks._frames(PLAIN, _env.ffprobe(), mp4)


class ChunkedResume(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.build = self.dir / "build"
        self.build.mkdir()
        self.src = self.dir / "src"
        self.src.mkdir()
        (self.src / "film.tsx").write_text("one")
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        self.log = self.dir / "rendered.log"
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.build)
        ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
        tools = {"python": sys.executable, "ffmpeg": ff, "ffprobe": fp, "chromium": "chrome", "dist": True}
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "SOURCES", (self.src,)),
                      mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(chunks, "GPU", False),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=ff, FAKE_LOG=str(self.log))):
            patch.start()
            self.addCleanup(patch.stop)

    def job(self, n=23, out="film.mp4", **extra):
        return {"type": "video", "composition": "Film", "props": {"board": 1}, "frames": n, "scale": 1,
                "out": str((self.build / out).resolve()), **extra}

    def rendered(self):
        names = self.log.read_text().split() if self.log.exists() else []
        self.log.unlink(missing_ok=True)
        return names

    def test_a_143_frame_job_plans_three_chunks_and_joins_whole(self):
        rep = studio.render([self.job(143)], "film")
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(self.rendered(), ["0-59.part.mp4", "60-119.part.mp4", "120-142.part.mp4"])
        self.assertEqual(json.loads((studio.RENDER / "film-report.part.json").read_text())["chunks"], {"kept": 0, "rendered": 3, "to_go": 0})
        self.assertEqual(frames(self.build / "film.mp4"), 143)

    @unittest.skipIf(os.name == "nt", "the Windows half is proved on a Windows machine")
    def test_the_renderer_holds_the_render_lock(self):
        studio.render([self.job()], "film")
        self.assertNotIn("(lock not held)", self.log.read_text())

    def test_the_report_counts_the_callers_jobs(self):
        still = {"type": "still", "composition": "Film", "props": {}, "frame": 0, "scale": 1, "out": str((self.build / "a.png").resolve())}
        rep = studio.render([self.job(), still], "film")
        self.assertEqual((rep["jobs"], rep["failed"]), (2, 0))
        self.assertEqual(json.loads((studio.RENDER / "film-report.part.json").read_text())["jobs"], 2)

    @unittest.skipIf(os.name == "nt", "the Windows half is proved on a Windows machine")
    def test_a_refused_second_command_leaves_the_first_ones_outputs_untouched(self):
        import fcntl
        import film
        out = self.dir / "out" / "carousel" / "01-hook.png"
        out.parent.mkdir(parents=True)
        out.write_text("the first command's card")
        studio.RENDER.mkdir(exist_ok=True)
        before = sorted(str(p.relative_to(self.dir)) for p in self.dir.rglob("*") if "render.lock" not in p.name)
        with open(studio.RENDER / "render.lock", "w", encoding="utf-8") as held:
            held.write(f"film\t{(studio.RENDER / 'film.log').resolve()}")
            held.flush()
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for cmd in ("render", "preview"):
                with mock.patch.object(sys, "argv", ["film.py", cmd]), mock.patch.object(_env, "enter_build"), \
                        self.assertRaises(SystemExit) as e:
                    film.main()
                self.assertIn("is already running in this run", str(e.exception.code))
        self.assertEqual(sorted(str(p.relative_to(self.dir)) for p in self.dir.rglob("*") if "render.lock" not in p.name), before)
        self.assertEqual(out.read_text(), "the first command's card")


class Deliverables(unittest.TestCase):
    """film.py render makes the film, the stories, the carousel and the strip beside out/ and moves them in once all are
    made."""

    def setUp(self):
        import film
        self.film = film
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        build = self.dir / "build"
        (build / "qa").mkdir(parents=True)
        (build / "qa" / "timed.json").write_text(json.dumps({"hash": "h", "pass": True}))
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(build)
        self.out = self.dir / "out"
        (self.out / "carousel").mkdir(parents=True)
        (self.out / "stories").mkdir()
        (self.out / "strip").mkdir()
        for rel in ("film.mp4", "carousel/01-hook.png", "carousel/05-gone.png", "stories/02-gone.png", "strip/04-gone.jpg"):
            (self.out / rel).write_text("the last set")
        months = [{"id": f"m{n:02d}", "month": n, "peak": n == 12, "at": {"pull": [4]}} for n in range(1, 13)]
        board = {"bpm": 120, "year": {"months": months}}
        f = {"hash": "h", "frames": 30, "seconds": 1, "rests": {"reel": {"hook": 0, "closer": 29}}}

        def render(jobs, name, run=None):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("made")
            return {"failed": 0}

        for patch in (mock.patch.object(film, "film", return_value=(f, board)),
                      mock.patch.object(studio, "video", lambda b, out, n, **k: {"out": str(out)}),
                      mock.patch.object(studio, "still", lambda b, fr, out, **k: {"out": str(out)}),
                      mock.patch.object(studio, "render", render),
                      mock.patch.object(film, "mux", lambda run, silent, out, s: shutil.copyfile(silent, out)),
                      mock.patch.object(film, "card", lambda src, dst: shutil.copyfile(src, dst)),
                      mock.patch.object(film, "strip_frame", lambda src, dst: shutil.copyfile(src, dst))):
            patch.start()
            self.addCleanup(patch.stop)

    def files(self):
        return {str(p.relative_to(self.out)): p.read_text() for p in self.out.rglob("*") if p.is_file()}

    def test_a_render_that_fails_on_a_card_leaves_the_last_set_whole(self):
        made = []

        def card(src, dst):
            if len(made) == 4:
                raise OSError("the fifth card")
            made.append(dst)
            shutil.copyfile(src, dst)

        before = self.files()
        with mock.patch.object(self.film, "card", card), self.assertRaises(OSError):
            self.film.cmd_render(None, None)
        self.assertEqual(self.files(), before)

    def test_a_whole_set_moves_in_and_the_cards_it_no_longer_makes_leave(self):
        self.film.cmd_render(None, None)
        got = self.files()
        self.assertEqual(len([k for k in got if k.startswith("carousel/")]), 10)
        self.assertEqual(len([k for k in got if k.startswith("stories/")]), 3)
        self.assertEqual(len([k for k in got if k.startswith("strip/")]), 8)
        self.assertEqual(set(got.values()), {"made"})
        self.assertNotIn("carousel/05-gone.png", got)
        self.assertNotIn("stories/02-gone.png", got)
        self.assertNotIn("strip/04-gone.jpg", got)
        self.assertFalse((self.dir / "out.part").exists())


class UnderTheLock(unittest.TestCase):
    """Every process film.py starts while it holds the run's lock goes through run.spawn: the mux and the measure."""

    def setUp(self):
        import film
        self.film = film
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        (self.dir / "music").mkdir()
        ff = _env.ffmpeg()
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30", "-frames:v", "30", "-pix_fmt", "yuv420p",
                        "silent.mp4"], check=True)
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=d=1", "music/master.wav"], check=True)
        _env.write_json("music.json", {"master": "music/master.wav"})
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
        self.assertTrue(self.film.mux(self.run_, Path("silent.mp4"), Path("film.mp4"), 1))
        m = studio.measure(Path("film.mp4"), [], run=self.run_)
        self.assertEqual(m["frames"], 30)
        self.assertEqual(len(self.started), 6)


if __name__ == "__main__":
    unittest.main()
