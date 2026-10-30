"""scripts/chunks.py, the resume module every kit carries byte-identical: a fake renderer stands in for the kit's, writing
each chunk's frames as a test pattern with the findings file that says its checks passed, so the plan, the key, the
resume, the publish, the lock and its hand-off to every child, the findings and the join are checked with no browser.

    python3 -I -m unittest discover -s S/tests -p test_chunks.py
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import chunks  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
# the probes a test reads a file with run outside any run's lock
PLAIN = types.SimpleNamespace(spawn=subprocess.run)

# The kit's renderer as invoke runs it (`python3 fake.py SPEC.json`). A chunk is its frameRange's frames of a test
# pattern at its `.part.mp4` with its `.part.findings.json` beside it; a still is a test pattern PNG. Each job logs its
# name to FAKE_LOG, with " held" when one of its open files (/dev/fd) is the run's lock and " old" when a published file
# already stands where the chunk will go. FAKE_DIE_AFTER=k stops after k jobs with no report; FAKE_NO_REPORT stops after
# the last one with none; a chunk whose name contains FAKE_FINDING gets a FONT_ERROR finding, one containing FAKE_SHORT a
# frame too few, one containing FAKE_REFUSE all its frames but a RENDER_ERROR and no findings file (its checks failed);
# chunks are written on a 90 kHz clock, as Remotion's are; FAKE_SLEEP_IN=renderer writes the renderer's pid to FAKE_PID and
# sleeps before it starts, and FAKE_SLEEP_AFTER=k does the same after k jobs.
FAKE = r"""
import json, os, subprocess, sys, time
spec = json.load(open(sys.argv[1], encoding="utf-8"))
env = os.environ.get
lock = os.stat(env("FAKE_LOCK"))
def same(fd):
    try:
        return os.path.samestat(os.fstat(int(fd)), lock)
    except OSError:
        return False
held = any(same(fd) for fd in os.listdir("/dev/fd"))
if env("FAKE_SLEEP_IN") == "renderer":
    open(env("FAKE_PID"), "w").write(str(os.getpid()))
    time.sleep(60)
found = []
for i, job in enumerate(spec["jobs"]):
    if env("FAKE_DIE_AFTER") and i == int(env("FAKE_DIE_AFTER")):
        sys.exit(137)
    if env("FAKE_SLEEP_AFTER") and i == int(env("FAKE_SLEEP_AFTER")):
        open(env("FAKE_PID"), "w").write(str(os.getpid()))
        time.sleep(60)
    out = job["out"]
    name = os.path.basename(out).split(".")[0]
    old = os.path.exists(os.path.join(os.path.dirname(out), name + ".mp4"))
    with open(env("FAKE_LOG"), "a", encoding="utf-8") as log:
        log.write(name + (" held" if held else "") + (" old" if old and job["type"] == "video" else "") + "\n")
    if job["type"] != "video":
        subprocess.run([env("FAKE_FFMPEG"), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=32x32", "-frames:v", "1", out], check=True)
        continue
    a, b = job["frameRange"]
    n = b - a + 1 - (1 if env("FAKE_SHORT") and env("FAKE_SHORT") in name else 0)
    subprocess.run([env("FAKE_FFMPEG"), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=32x32:r=30", "-frames:v", str(n),
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-video_track_timescale", "90000", out], check=True)
    if env("FAKE_REFUSE") and env("FAKE_REFUSE") in name:
        found.append({"job": out, "text": "RENDER_ERROR Error creating WebGL context"})
        continue
    own = [{"job": out, "text": "FONT_ERROR " + name}] if env("FAKE_FINDING") and env("FAKE_FINDING") in name else []
    found += own
    json.dump(own, open(out[:-len(".mp4")] + ".findings.json", "w", encoding="utf-8"))
if env("FAKE_NO_REPORT"):
    sys.exit(137)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": found}, open(spec["report"], "w", encoding="utf-8"))
"""

# One render of a run in its own process (`python3 drive.py SCRIPTS RENDER_DIR JOBS.json FAKE FFMPEG SOURCE`), on the
# processor's plan, for the tests that kill it while a child it started still runs. With FAKE_SLEEP_IN=after it then
# starts a child through run.spawn, the way a kit muxes the film, which writes its pid to FAKE_PID and sleeps.
DRIVE = r"""
import json, os, subprocess, sys
sys.path.insert(0, sys.argv[1])
import chunks
chunks.GPU = False
render_dir, jobs, fake, ffmpeg = sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8")), sys.argv[4], sys.argv[5]
def invoke(pending, spawn):
    spec, report = os.path.join(render_dir, "spec.json"), os.path.join(render_dir, "report.json")
    if os.path.exists(report):
        os.unlink(report)
    json.dump({"jobs": pending, "report": report}, open(spec, "w", encoding="utf-8"))
    code = spawn([sys.executable, fake, spec]).returncode
    return json.load(open(report, encoding="utf-8")) if os.path.exists(report) else chunks.unreported(pending, code, os.devnull)
with chunks.lock(render_dir, "film") as run:
    chunks.render(run, jobs, os.path.join(render_dir, "..", "public"), sys.argv[6:], ffmpeg, os.environ["FAKE_FFPROBE"], invoke)
    if os.environ.get("FAKE_SLEEP_IN") == "after":
        run.spawn([sys.executable, "-c", "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(60)",
                   os.environ["FAKE_PID"]])
"""

# ffmpeg as the join runs it: with FAKE_SLEEP_IN=join it writes its pid to FAKE_PID and sleeps before it joins, and
# with FAKE_JOIN_FAILS it exits 1 without joining.
SLOW_FFMPEG = r"""
import os, sys, time
if "concat" in sys.argv and os.environ.get("FAKE_SLEEP_IN") == "join":
    open(os.environ["FAKE_PID"], "w").write(str(os.getpid()))
    time.sleep(60)
if "concat" in sys.argv and os.environ.get("FAKE_JOIN_FAILS"):
    sys.exit("concat: the listing cannot be read")
os.execv(os.environ["FAKE_FFMPEG"], [os.environ["FAKE_FFMPEG"], *sys.argv[1:]])
"""


def frames(mp4):
    return chunks._frames(PLAIN, FFPROBE, mp4)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
@unittest.skipIf(os.name == "nt", "the fake renderer reads /dev/fd; the Windows half is proved on a Windows machine")
class Chunks(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.use(self.dir / "run")
        self.src = self.dir / "src"
        self.src.mkdir()
        (self.src / "Film.tsx").write_text("one")
        self.fake = self.dir / "fake.py"
        self.fake.write_text(FAKE)
        self.log = self.dir / "rendered.log"
        self.cwd = None
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        for patch in (mock.patch.object(chunks, "GPU", False),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG, FAKE_FFPROBE=FFPROBE, FAKE_LOG=str(self.log))):
            patch.start()
            self.addCleanup(patch.stop)

    def use(self, run):
        self.run_dir = run
        self.render_dir = run / "render"
        self.public = run / "public"
        self.public.mkdir(parents=True, exist_ok=True)

    def job(self, n=143, out="film.mp4", **extra):
        return {"type": "video", "composition": "Film", "props": {"board": 1}, "frames": n,
                "out": str(self.run_dir / out), **extra}

    def render(self, jobs, ffmpeg=FFMPEG, **env):
        def invoke(pending, spawn):
            spec, report = self.render_dir / "spec.json", self.render_dir / "report.json"
            report.unlink(missing_ok=True)
            spec.write_text(json.dumps({"jobs": pending, "report": str(report.resolve())}), encoding="utf-8")
            code = spawn([sys.executable, str(self.fake.resolve()), str(spec.resolve())], cwd=self.cwd).returncode
            return json.loads(report.read_text(encoding="utf-8")) if report.exists() else chunks.unreported(pending, code, os.devnull)
        with chunks.lock(self.render_dir, "film") as run, \
                mock.patch.dict(os.environ, FAKE_LOCK=str((self.render_dir / "render.lock").resolve()), **env):
            return chunks.render(run, jobs, self.public, [self.src], ffmpeg, FFPROBE, invoke)

    def rendered(self):
        names = self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []
        self.log.unlink(missing_ok=True)
        return names

    def chunk_dir(self):
        (d,) = (self.render_dir / "chunks" / "film").iterdir()
        return d

    def test_a_film_renders_in_chunks_the_renderer_holding_the_lock_and_joins_whole(self):
        rep = self.render([self.job()])
        self.assertEqual((rep["jobs"], rep["failed"], rep["chunks"]), (1, 0, {"kept": 0, "rendered": 3, "to_go": 0}))
        self.assertEqual(self.rendered(), ["0-59 held", "60-119 held", "120-142 held"])
        self.assertEqual(frames(self.run_dir / "film.mp4"), 143)
        self.assertEqual(sorted(p.name for p in self.chunk_dir().iterdir() if ".part." in p.name), [])

    def test_every_joined_frame_sits_on_its_own_tick(self):
        self.assertEqual(self.render([self.job(241)])["failed"], 0)
        r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=time_base:packet=pts",
                            "-of", "json", str(self.run_dir / "film.mp4")], capture_output=True, text=True, check=True)
        probe = json.loads(r.stdout)
        tb = Fraction(probe["streams"][0]["time_base"])
        self.assertEqual(sorted(Fraction(p["pts"]) * tb for p in probe["packets"]), [Fraction(n, 30) for n in range(241)])

    def test_a_chunk_the_renderer_refused_is_never_published(self):
        rep = self.render([self.job()], FAKE_REFUSE="60-119")
        self.assertEqual(rep["failed"], 1)
        self.assertIn("RENDER_ERROR Error creating WebGL context", [f["text"] for f in rep["findings"]])
        self.assertEqual(sorted(p.name for p in self.chunk_dir().glob("60-119*")), ["60-119.part.mp4"])
        self.rendered()
        rep = self.render([self.job()])
        self.assertEqual((rep["failed"], self.rendered()), (0, ["60-119 held"]))

    def test_with_a_graphics_card_a_job_is_one_chunk_over_its_range(self):
        with mock.patch.object(chunks, "GPU", True):
            rep = self.render([self.job(), self.job(40, out="part.mp4", frameRange=[5, 27])])
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(self.rendered(), ["0-142 held", "5-27 held"])
        self.assertEqual((frames(self.run_dir / "film.mp4"), frames(self.run_dir / "part.mp4")), (143, 23))

    def test_a_killed_render_resumes_from_the_chunks_it_published(self):
        rep = self.render([self.job(183)], FAKE_DIE_AFTER="2", FAKE_FINDING="0-59")
        self.assertEqual((rep["failed"], rep["chunks"]), (1, {"kept": 0, "rendered": 2, "to_go": 2}))
        self.assertFalse((self.run_dir / "film.mp4").exists())
        self.rendered()
        rep = self.render([self.job(183)])
        self.assertEqual((rep["failed"], rep["chunks"]), (0, {"kept": 2, "rendered": 2, "to_go": 0}))
        self.assertEqual(self.rendered(), ["120-179 held", "180-182 held"])
        self.assertEqual(frames(self.run_dir / "film.mp4"), 183)
        self.assertEqual([f["text"] for f in rep["findings"]], ["FONT_ERROR 0-59"])

    def test_a_fresh_chunks_findings_reach_the_report_when_the_renderer_dies_before_its_report(self):
        rep = self.render([self.job()], FAKE_FINDING="-", FAKE_NO_REPORT="1")
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(sorted(f["text"] for f in rep["findings"]), ["FONT_ERROR 0-59", "FONT_ERROR 120-142", "FONT_ERROR 60-119"])

    def test_a_truncated_published_chunk_is_replaced_by_rename_never_unlinked_first(self):
        self.render([self.job()])
        self.rendered()
        d = self.chunk_dir()
        (d / "60-119.findings.json").write_text(json.dumps([{"job": "x", "text": "FONT_ERROR stale"}]), encoding="utf-8")
        whole = (d / "60-119.mp4").read_bytes()
        (d / "60-119.mp4").write_bytes(whole[: len(whole) // 2])
        rep = self.render([self.job()])
        self.assertEqual(self.rendered(), ["60-119 held old"])
        self.assertEqual((rep["failed"], rep["findings"], frames(d / "60-119.mp4")), (0, [], 60))
        self.assertEqual(frames(self.run_dir / "film.mp4"), 143)

    def test_a_chunk_short_of_its_frames_is_refused_and_renders_again(self):
        rep = self.render([self.job()], FAKE_SHORT="60-119")
        self.assertEqual(rep["failed"], 1)
        self.assertIn("RENDER_ERROR chunk 60-119 holds 59 frames of 60", [f["text"] for f in rep["findings"]])
        self.assertFalse((self.chunk_dir() / "60-119.mp4").exists())
        self.assertFalse((self.run_dir / "film.mp4").exists())
        self.rendered()
        rep = self.render([self.job()])
        self.assertEqual((rep["failed"], self.rendered()), (0, ["60-119 held"]))
        self.assertEqual(frames(self.run_dir / "film.mp4"), 143)

    def test_a_one_frame_chunk_is_kept_and_joined(self):
        self.assertEqual(self.render([self.job(121)])["failed"], 0)
        self.assertEqual(self.rendered(), ["0-59 held", "60-119 held", "120-120 held"])
        rep = self.render([self.job(121)])
        self.assertEqual((rep["chunks"], self.rendered()), ({"kept": 3, "rendered": 0, "to_go": 0}, []))
        self.assertEqual(frames(self.run_dir / "film.mp4"), 121)

    def test_a_relative_run_folder_with_an_apostrophe_and_a_non_ascii_name_resumes_and_names_the_holder(self):
        # the renderer may run in another folder than the run, so every path it is handed is absolute
        os.chdir(self.dir)
        self.use(Path("José's run"))
        self.src, self.fake, self.cwd = Path("src"), Path("fake.py"), self.dir / "elsewhere"
        self.cwd.mkdir()
        still = {"type": "still", "composition": "Film", "props": {}, "frame": 0, "out": str(self.run_dir / "a.png")}
        rep = self.render([self.job(out="the film's cut.mp4"), still])
        self.assertEqual((rep["failed"], frames(self.dir / "José's run" / "the film's cut.mp4")), (0, 143))
        self.assertTrue((self.dir / "José's run" / "a.png").exists())
        self.assertEqual(list(self.cwd.iterdir()), [])
        self.assertEqual(self.render([self.job(out="the film's cut.mp4")])["chunks"], {"kept": 3, "rendered": 0, "to_go": 0})
        with chunks.lock(self.render_dir, "film"), self.assertRaises(SystemExit) as e, chunks.lock(self.render_dir, "preview"):
            pass
        self.assertIn(f"its log is {self.render_dir.resolve() / 'film.log'}", str(e.exception.code))

    def test_a_refused_second_lock_changes_nothing(self):
        self.render([self.job()])
        def files():
            return {p: p.read_bytes() for p in sorted(self.run_dir.rglob("*")) if p.is_file()}
        with chunks.lock(self.render_dir, "film"):
            before = files()
            with self.assertRaises(SystemExit) as e, chunks.lock(self.render_dir, "preview"):
                pass
            self.assertEqual(files(), before)
        self.assertEqual(str(e.exception.code), "a render named film is already running in this run; its log is "
                                                f"{self.render_dir.resolve() / 'film.log'}")

    def test_the_key_follows_the_job_the_public_files_and_the_source_never_the_out(self):
        seen = []
        def run(job):
            self.render([job])
            seen.append(len(list((self.render_dir / "chunks" / "film").iterdir())))
        run(self.job())
        run(self.job(out="elsewhere.mp4"))
        run(self.job(props={"board": 2}))
        (self.public / "m01.jpg").write_text("a photograph")
        run(self.job())
        (self.src / "Film.tsx").write_text("two")
        run(self.job())
        self.assertEqual(seen, [1, 1, 2, 3, 4])

    def test_the_report_counts_the_callers_jobs(self):
        still = {"type": "still", "composition": "Film", "props": {}, "frame": 0, "out": str(self.run_dir / "a.png")}
        rep = self.render([self.job(), still])
        self.assertEqual((rep["jobs"], rep["failed"]), (2, 0))
        self.assertTrue((self.run_dir / "a.png").exists())
        rep = self.render([self.job(), still], FAKE_NO_REPORT="1")
        self.assertEqual((rep["jobs"], rep["failed"]), (2, 1))

    def test_a_renderer_that_leaves_no_report_is_named_with_its_exit_and_its_last_error_lines(self):
        log = self.dir / "render.log"
        log.write_text("THREE.WebGLRenderer: Context Lost.\nTHREE.Clock: a tick\n"
                       "THREE.WebGLRenderer: Error creating WebGL context.\nnode exited\n", encoding="utf-8")
        self.assertEqual(chunks.unreported([{"out": "a.png"}], 1, log), {"gl": None, "findings": [{"job": "a.png", "text":
            "RENDER_ERROR the renderer exited 1 with no report; its last lines: THREE.WebGLRenderer: Context Lost. | "
            "THREE.WebGLRenderer: Error creating WebGL context. | node exited"}]})

    def slow_ffmpeg(self):
        slow = self.dir / "ffmpeg"
        slow.write_text(f"#!{sys.executable}\n{SLOW_FFMPEG}")
        slow.chmod(0o755)
        return str(slow)

    def test_a_restart_that_kills_the_whole_command_keeps_every_chunk_that_passed(self):
        jobs = self.dir / "jobs.json"
        jobs.write_text(json.dumps([self.job(183)]), encoding="utf-8")
        drive = self.dir / "drive.py"
        drive.write_text(DRIVE)
        pid = self.dir / "child.pid"
        self.render_dir.mkdir(parents=True, exist_ok=True)
        (self.render_dir / "render.lock").touch()
        # the bridge and its renderer in one process group, as a machine restart finds them
        group = subprocess.Popen([sys.executable, str(drive), str(Path(chunks.__file__).parent), str(self.render_dir),
                                  str(jobs), str(self.fake), FFMPEG, str(self.src)], start_new_session=True,
                                 env=dict(os.environ, FAKE_LOCK=str(self.render_dir / "render.lock"), FAKE_PID=str(pid),
                                          FAKE_SLEEP_AFTER="2"))
        deadline = time.monotonic() + 60
        while not pid.exists() and time.monotonic() < deadline and group.poll() is None:
            time.sleep(0.1)
        self.assertTrue(pid.exists(), "the renderer never passed two chunks")
        os.killpg(group.pid, signal.SIGKILL)
        group.wait()
        # the renderer in the group holds the lock it inherited until the kernel has reaped it too
        self.lock_comes_free()
        self.rendered()
        rep = self.render([self.job(183)])
        self.assertEqual((rep["failed"], rep["chunks"]), (0, {"kept": 2, "rendered": 2, "to_go": 0}))
        self.assertEqual(self.rendered(), ["120-179 held", "180-182 held"])
        self.assertEqual(frames(self.run_dir / "film.mp4"), 183)

    def test_a_failed_join_never_replaces_the_film_even_with_a_whole_join_a_killed_command_left(self):
        self.render([self.job()])
        film = (self.run_dir / "film.mp4").read_bytes()
        subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=32x32:r=30", "-frames:v", "143",
                        "-pix_fmt", "yuv420p", str(self.run_dir / "film.join.mp4")], check=True)
        rep = self.render([self.job()], ffmpeg=self.slow_ffmpeg(), FAKE_JOIN_FAILS="1")
        self.assertEqual(rep["failed"], 1)
        self.assertIn("ffmpeg exited 1", " ".join(f["text"] for f in rep["findings"]))
        self.assertIn("the listing cannot be read", " ".join(f["text"] for f in rep["findings"]))
        self.assertEqual((self.run_dir / "film.mp4").read_bytes(), film)
        self.assertFalse((self.run_dir / "film.join.mp4").exists())

    def survives(self, sleep_in, ffmpeg=FFMPEG):
        """Starts a render in its own process, kills that process while the child it is waiting on still runs, and
        checks that the lock refuses a second render until the child is gone."""
        jobs = self.dir / "jobs.json"
        jobs.write_text(json.dumps([self.job()]), encoding="utf-8")
        drive = self.dir / "drive.py"
        drive.write_text(DRIVE)
        pid = self.dir / "child.pid"
        self.render_dir.mkdir(parents=True, exist_ok=True)
        (self.render_dir / "render.lock").touch()
        parent = subprocess.Popen([sys.executable, str(drive), str(Path(chunks.__file__).parent), str(self.render_dir),
                                   str(jobs), str(self.fake), ffmpeg, str(self.src)],
                                  env=dict(os.environ, FAKE_LOCK=str(self.render_dir / "render.lock"), FAKE_PID=str(pid),
                                           FAKE_SLEEP_IN=sleep_in))
        deadline = time.monotonic() + 60
        # the child creates its pid file before it writes the pid
        while not (pid.exists() and pid.read_text()) and time.monotonic() < deadline and parent.poll() is None:
            time.sleep(0.1)
        self.assertTrue(pid.exists() and pid.read_text(), "the child never started")
        child = int(pid.read_text())
        parent.send_signal(signal.SIGKILL)
        parent.wait()
        try:
            with self.assertRaises(SystemExit) as e, chunks.lock(self.render_dir, "second"):
                pass
            self.assertIn("a render named film is already running", str(e.exception.code))
        finally:
            os.kill(child, signal.SIGKILL)
        self.lock_comes_free()

    def lock_comes_free(self):
        """Waits up to 10 s for a second render to take the lock, as it can once every process holding it is gone."""
        deadline = time.monotonic() + 10
        while True:
            try:
                with chunks.lock(self.render_dir, "second"):
                    return
            except SystemExit:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.1)

    def test_the_lock_outlives_a_killed_command_while_its_renderer_lives(self):
        self.survives("renderer")

    def test_the_lock_outlives_a_killed_command_while_its_join_lives(self):
        self.survives("join", self.slow_ffmpeg())

    def test_the_lock_outlives_a_killed_command_while_a_child_it_started_after_the_render_lives(self):
        self.survives("after")


if __name__ == "__main__":
    unittest.main()
