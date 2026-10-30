"""The places map's call site of scripts/chunks.py: studio.render hands chunks.render an invoke that runs render.py,
here a stand-in for it that writes each chunk's frames as a test pattern with the findings file render.py writes, and
the renderer holds the run's lock. The module itself is tested in test_chunks.py.

    python3 -I -m unittest discover -s S/tests -p test_resume.py
"""
import json
import os
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


class Chunked(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        self.run_dir = d / "maren's run"
        self.run_dir.mkdir()
        src = d / "src"
        src.mkdir()
        (src / "film.tsx").write_text("one")
        fake = d / "render.py"
        fake.write_text(FAKE)
        self.log = d / "rendered.log"
        tools = dict(_env.tools(), chromium="chrome", dist=True)
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "SOURCES", (src,)),
                      mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(studio.clips, "placed", lambda: []), mock.patch.object(chunks, "GPU", False),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=_env.ffmpeg(), FAKE_LOG=str(self.log))):
            patch.start()
            self.addCleanup(patch.stop)
        here = Path.cwd()
        os.chdir(self.run_dir)
        self.addCleanup(os.chdir, here)

    def job(self, n=23, out="film.mp4"):
        return studio.video({"id": "board"}, out, n)

    def rendered(self):
        names = self.log.read_text().split("\n") if self.log.exists() else []
        self.log.unlink(missing_ok=True)
        return [x for x in names if x]

    def test_a_143_frame_film_renders_in_three_chunks_and_joins_whole(self):
        rep = studio.render([self.job(143)], "film")
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(self.rendered(), ["0-59.part.mp4", "60-119.part.mp4", "120-142.part.mp4"])
        self.assertEqual(json.loads((studio.RENDER / "film-report.part.json").read_text())["chunks"], {"kept": 0, "rendered": 3, "to_go": 0})
        self.assertEqual(frames("film.mp4"), 143)
        rep = studio.render([self.job(143)], "film")
        self.assertEqual((rep["failed"], rep["chunks"], self.rendered()), (0, {"kept": 3, "rendered": 0, "to_go": 0}, []))

    @unittest.skipIf(os.name == "nt", "the Windows lock is a handle; the lead proves it on the Windows machine")
    def test_the_renderer_holds_the_run_lock(self):
        studio.render([self.job()], "preview")
        self.assertNotIn("(lock not held)", self.log.read_text())

    def test_the_report_counts_the_callers_jobs(self):
        rep = studio.render([self.job(), studio.still({"id": "board"}, 0, "s.png")], "film")
        self.assertEqual((rep["jobs"], rep["failed"]), (2, 0))
        self.assertEqual(json.loads((studio.RENDER / "film-report.part.json").read_text())["jobs"], 2)

    def test_a_render_while_one_runs_exits_nonzero_and_renders_nothing(self):
        with studio.lock("film"):
            with self.assertRaises(SystemExit) as e:
                studio.render([self.job()], "preview")
        self.assertNotEqual(e.exception.code, 0)
        self.assertIn("film", str(e.exception.code))
        self.assertEqual(self.rendered(), [])


if __name__ == "__main__":
    unittest.main()
