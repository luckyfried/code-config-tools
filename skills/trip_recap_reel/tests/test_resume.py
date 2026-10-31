"""The trip kit's call site of scripts/chunks.py: studio.render hands chunks.render an invoke that runs render.py, here a
stand-in for it that writes each chunk's frames as a test pattern with the findings file render.py writes, and
film.py takes the run's lock before its first write. The module itself is tested in test_chunks.py.

    python3 -I -m unittest discover -s S/tests -p test_resume.py
"""
import argparse
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
# the probes a test reads a file with run outside any run's lock
PLAIN = types.SimpleNamespace(spawn=subprocess.run)

# render.py as studio.render calls it (`python3 render.py --jobs JOBS.json`): every chunk is its frameRange's frames of a test pattern
# at its `.part.mp4` with an empty `.part.findings.json` beside it, and every still is a test pattern PNG; each job logs
# its name, with " (lock not held)" when none of its open files (/dev/fd) is the run's render.lock.
FAKE = r"""#!/usr/bin/env python3
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


class Stop(Exception):
    pass


def frames(mp4):
    return chunks._frames(PLAIN, _env.ffprobe(), mp4)


# the stand-in renderer reads /dev/fd: every test here is POSIX-only
@unittest.skipIf(os.name == "nt", "the Windows half is proved on a Windows machine")
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
        tools = dict(_env.tools(), chromium="/usr/bin/chromium", dist=str(self.src))
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "SOURCES", (self.src,), create=True),
                      mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(chunks, "GPU", False),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=_env.ffmpeg(), FAKE_LOG=str(self.log))):
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
        self.assertEqual(rep["chunks"], {"kept": 0, "rendered": 3, "to_go": 0})
        # the bridge's report is the render's working file; the name the gate reads is the command's to publish
        self.assertFalse((studio.RENDER / "film-report.json").exists())
        self.assertEqual(frames(self.build / "film.mp4"), 143)

    def test_the_renderer_holds_the_render_lock(self):
        studio.render([self.job()], "film")
        self.assertNotIn("(lock not held)", self.log.read_text())

    def test_the_report_counts_the_callers_jobs(self):
        still = {"type": "still", "composition": "Film", "props": {}, "frame": 0, "scale": 1, "out": str((self.build / "a.png").resolve())}
        rep = studio.render([self.job(), still], "film")
        self.assertEqual((rep["jobs"], rep["failed"]), (2, 0))
        self.assertEqual(json.loads((studio.RENDER / "film-bridge.json").read_text())["jobs"], 2)

    def test_a_render_stopped_in_its_moves_then_again_before_them_leaves_a_set_the_next_command_refuses(self):
        import film
        import vote
        reel = {"beats": [{"frames": 23}], "seconds": 23 / 30, "stories": ["a", "b"], "rests": {"a": 2, "b": 12, "closer": 20},
                "timeline": [{"id": "hook", "start": 0, "frames": 23}]}
        out = self.build / "out"
        for d in (out, self.build / "render" / "stories", self.build / "frames"):
            d.mkdir(parents=True)
        for name in ("film.mp4", "film-16x9.mp4", "story-1.png", "story-2.png"):
            (out / name).write_text("earlier")
        _env.write_json(studio.RENDER / "film-report.json", {"jobs": 4, "failed": 0, "findings": []})
        real = os.replace

        def mux(silent, dst, seconds, run):
            real(silent, dst)
            return False

        def first_move(src, dst):
            real(src, dst)
            if Path(dst).resolve().parent == out.resolve():
                raise Stop

        def render(**patches):
            with mock.patch.object(film, "films", return_value={"reel": reel, "landscape": reel, "square": None}), \
                    mock.patch.object(studio, "props", return_value={"board": 1}), contextlib.redirect_stdout(io.StringIO()), \
                    mock.patch.multiple(film, mux=patches.pop("mux", mux)), mock.patch.object(os, "replace", patches.pop("replace", real)), \
                    self.assertRaises(Stop):
                film.cmd_render(argparse.Namespace(also=list(film.ALSO)), None)
        # the first render is stopped after its first move into out/: a new story card beside the earlier films
        render(replace=first_move)
        self.assertEqual((out / "story-1.png").read_bytes()[:4], b"\x89PNG")
        self.assertEqual((out / "film.mp4").read_text(), "earlier")
        self.assertFalse((studio.RENDER / "film-report.json").exists())
        # the retry renders every job whole and is stopped before its first move
        render(mux=mock.Mock(side_effect=Stop))
        self.assertFalse((studio.RENDER / "film-report.json").exists())
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as e:
            vote.cmd_cut(argparse.Namespace())
        self.assertIn("not a finished render", str(e.exception.code))

    def test_a_refused_second_command_leaves_the_first_ones_outputs_untouched(self):
        import fcntl
        import film
        out = self.dir / "out" / "story-1.png"
        out.parent.mkdir(parents=True)
        out.write_text("the first command's card")
        studio.RENDER.mkdir(exist_ok=True)
        before = sorted(str(p.relative_to(self.dir)) for p in self.dir.rglob("*") if "render.lock" not in p.name)
        with open(studio.RENDER / "render.lock", "w", encoding="utf-8") as held:
            held.write(f"film\t{(studio.RENDER / 'film.log').resolve()}")
            held.flush()
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for cmd in ("render", "preview"):
                with mock.patch.object(sys, "argv", ["film.py", cmd]), mock.patch.object(_env, "enter_run"), \
                        self.assertRaises(SystemExit) as e:
                    film.main()
                self.assertIn("is already running in this run", str(e.exception.code))
        self.assertEqual(sorted(str(p.relative_to(self.dir)) for p in self.dir.rglob("*") if "render.lock" not in p.name), before)
        self.assertEqual(out.read_text(), "the first command's card")


class UnderTheLock(unittest.TestCase):
    """Every process film.py starts while it holds the run's lock goes through run.spawn: the mux, its peak read and the
    measure."""

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
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav"})
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
        self.assertTrue(self.film.mux(Path("silent.mp4"), Path("film.mp4"), 1, self.run_))
        m = studio.measure(Path("film.mp4"), [], run=self.run_)
        self.assertEqual(m["frames"], 30)
        # the mux and its peak read, then the duration, the scene cuts, the luma line and the two strips
        self.assertEqual(len(self.started), 7)

    def test_the_mux_lays_only_the_master_music_json_names(self):
        _env.write_json("music.json", {"file": "music/source.wav"})
        self.assertFalse(self.film.mux(Path("silent.mp4"), Path("film.mp4"), 1, self.run_))


if __name__ == "__main__":
    unittest.main()
