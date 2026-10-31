"""The film commands around the renderer: a command takes the run's lock before it writes anything into the run, a
final render that does not finish or draws a white film leaves out/ as it was, and a finished one takes the review
page and then the reel away before the new set moves in, writes cards.json, and moves the reel in last, so a render
stopped anywhere, and stopped again on its retry, leaves no reel for the gate. A cut takes cut.json away before it
lays the board out. The reel renders alone unless the person asked for more: --also landscape, square and stories add
the wide film, the square film and the story cards, exactly the ones named, and the gate fails on a shape in out/ that
the render did not make.
The renderer is a stand-in that records what each call was handed.

    python3 -I -m unittest discover -s S/tests -p test_commands.py
"""
import contextlib
import io
import os
import pathlib
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
import film  # noqa: E402


def tree(root):
    return {str(p.relative_to(root)): (p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(Path(root).rglob("*"))}


def clip(out, n=30):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30", "-frames:v", str(n),
                    "-pix_fmt", "yuv420p", str(out)], check=True)


class Commands(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.run_dir = self.root / "build" / "20260101T000000Z"
        (self.run_dir / "render").mkdir(parents=True)
        (self.root / "build" / "current").write_text(self.run_dir.name + "\n")

    @unittest.skipIf(os.name == "nt", "the lock held here is a POSIX flock")
    def test_a_refused_command_writes_nothing_into_the_run(self):
        import fcntl
        (self.run_dir / "film.json").write_text("{}")
        (self.run_dir / "render" / "cut.mp4").write_bytes(b"the first command's cut")
        env = {k: v for k, v in os.environ.items() if k != "MPR_RUN"}
        env.update(MPR_WORKSPACE=str(self.root), CSC_DISABLE_KEYCHAIN="1")
        with open(self.run_dir / "render" / "render.lock", "a+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held.write("cut\n")
            held.flush()
            before = tree(self.run_dir)
            for cmd in ("cut", "render"):
                p = subprocess.run([sys.executable, str(KIT / "scripts" / "film.py"), cmd], cwd=self.root, env=env,
                                   capture_output=True, text=True, timeout=120)
                self.assertNotEqual(p.returncode, 0, cmd)
                self.assertIn("is already running in this run", p.stderr, cmd)
                self.assertEqual(tree(self.run_dir), before, cmd)


class Final(unittest.TestCase):
    """cmd_render over a run whose cut has passed its checks and its vote, with two people's stills."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        clip("render/cut.mp4")
        film_sha = film.file_sha(Path("render/cut.mp4"))
        _env.write_json("render/cut.json", {"film": film_sha, "frames": 30})
        _env.write_json("qa/check.json", {"pass": True, "cut": film_sha})
        beats = [{"id": "a", "frames": 15}, {"id": "b", "frames": 15}]
        _env.write_json("render/board-reel.json", {"beats": beats})
        people = [types.SimpleNamespace(handle=h, rank=2 - i) for i, h in enumerate(("ana", "bo"))]
        self.calls = []
        self.white = set()
        self.fails = set()
        for patch in (
            mock.patch.object(film, "the_film", lambda: {"storyboard": {"cards": {"ana": "a", "bo": "b"}}}),
            mock.patch.object(film.boards, "Ctx", lambda: types.SimpleNamespace(people=people)),
            mock.patch.object(film, "board_for", lambda f, ctx, kind: {"beats": beats, "kind": kind}),
            mock.patch.object(film, "frames_of", lambda b: ([0, 15], 30)),
            mock.patch.object(film.studio, "props", lambda b: {"board": b}),
            mock.patch.object(film.studio, "render", self.render),
            mock.patch.object(film, "white_seconds", lambda run, m: [0.0] if Path(m).name in self.white else []),
            mock.patch.dict(sys.modules, vote=types.SimpleNamespace(scored=lambda sha: (True, ""))),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def render(self, jobs, name, run=None):
        """The renderer: makes each job's file, but a still named in `self.fails`."""
        self.calls.append([Path(j["out"]).name for j in jobs])
        failed = 0
        for j in jobs:
            if Path(j["out"]).name in self.fails:
                failed += 1
                continue
            clip(j["out"], 30 if j["type"] == "video" else 1)
        return {"jobs": len(jobs), "failed": failed, "findings": [], "seconds": 1, "cpu_seconds": 1}

    def final(self, also=("landscape", "square", "stories")):
        with contextlib.redirect_stdout(io.StringIO()):
            return film.cmd_render(argparse_ns(also), types.SimpleNamespace(spawn=subprocess.run))

    def test_a_render_that_does_not_finish_leaves_out_unchanged(self):
        self.fails = {"02-bo.png"}
        self.assertEqual(self.final(), 1)
        self.assertFalse(Path("out").exists())

    def test_a_finished_render_puts_every_deliverable_in_out(self):
        Path("out").mkdir()
        Path("out/review.html").write_text("the page of the set before")
        self.assertEqual(self.final(), 0)
        for f in ("film.mp4", "film-square.mp4", "film-wide.mp4", "cover.png", "story.png", "people/01-ana.png", "people/02-bo.png"):
            self.assertTrue((Path("out") / f).exists(), f)
        self.assertFalse(Path("out/review.html").exists())

    def set_before(self):
        Path("out/people").mkdir(parents=True)
        Path("out/film.mp4").write_bytes(b"the reel of the set before")
        Path("out/people/01-ana.png").write_bytes(b"a still of the set before")
        Path("out/review.html").write_text("the page of the set before")
        _env.write_json("cards.json", {"cards": [{"file": "out/people/01-ana.png"}]})

    def stopped_publishing(self, when):
        publish = film.publish

        def stopped(src, out):
            if when(Path(out)):
                raise Stopped
            publish(src, out)

        return mock.patch.object(film, "publish", stopped)

    def test_a_render_stopped_between_two_renames_then_stopped_again_before_it_moves_anything_is_refused(self):
        self.set_before()
        with self.stopped_publishing(lambda out: out.parts[:2] == ("out", "people")), self.assertRaises(Stopped):
            self.final()
        self.assertTrue(Path("out/film-wide.mp4").exists())
        self.assertFalse(Path("out/film.mp4").exists())
        self.assertFalse(Path("out/review.html").exists())

        def stopped(jobs, name, run=None):
            raise Stopped

        with mock.patch.object(film.studio, "render", stopped), self.assertRaises(Stopped):
            self.final()
        self.assertFalse(Path("out/film.mp4").exists())
        import qa
        ok, detail = qa.formats_check(1.0)
        self.assertFalse(ok)
        self.assertIn("out/film.mp4 is missing", detail)

    def test_a_render_stopped_while_it_takes_the_set_away_takes_the_page_first(self):
        self.set_before()
        unlink = pathlib.Path.unlink

        def stopped_at_the_reel(path, *args, **kwargs):
            if path == Path("out/film.mp4"):
                raise Stopped
            return unlink(path, *args, **kwargs)

        with mock.patch.object(pathlib.Path, "unlink", stopped_at_the_reel), self.assertRaises(Stopped):
            self.final()
        self.assertFalse(Path("out/review.html").exists())

    def test_a_render_stopped_before_the_reel_has_written_cards_json_for_the_new_set(self):
        self.set_before()
        with self.stopped_publishing(lambda out: out == film.OUTS["reel"]), self.assertRaises(Stopped):
            self.final()
        self.assertFalse(Path("out/film.mp4").exists())
        self.assertTrue(Path("cards.json").exists())
        files = [c["file"] for c in _env.read_json("cards.json")["cards"]]
        self.assertEqual(files, ["out/people/01-ana.png", "out/people/02-bo.png"])

    def test_a_cut_stopped_while_it_lays_the_board_out_leaves_no_cut_json(self):
        _env.write_json("render/cut.json", {"board": "the board before", "film": "the cut before"})

        def stopped(f, ctx, kind):
            Path("render/board-reel.json").write_text("half a board")
            raise Stopped

        with mock.patch.object(film, "the_film", lambda: {"tone": "drive", "bpm": 120, "storyboard": {}}), \
                mock.patch.object(film, "board_for", stopped), self.assertRaises(Stopped):
            film.cmd_cut(types.SimpleNamespace(cmd="cut", again=False), types.SimpleNamespace(spawn=subprocess.run))
        self.assertFalse(Path("render/cut.json").exists())

    def test_a_cut_stopped_while_it_renders_leaves_no_cut_json(self):
        _env.write_json("render/cut.json", {"board": "the board before", "film": "the cut before"})

        def stopped(jobs, name, run=None):
            raise Stopped

        with mock.patch.object(film, "the_film", lambda: {"tone": "drive", "bpm": 120, "storyboard": {}}), \
                mock.patch.object(film.studio, "props", lambda b: {"board": b, "clips": []}), \
                mock.patch.object(film.studio, "render", stopped), self.assertRaises(Stopped):
            film.cmd_cut(types.SimpleNamespace(cmd="cut", again=False), types.SimpleNamespace(spawn=subprocess.run))
        self.assertFalse(Path("render/cut.json").exists())

    def test_a_render_nobody_asked_extras_of_makes_the_reel_its_cover_and_story_card_and_takes_the_last_extras_away(self):
        self.set_before()
        Path("out/film-square.mp4").write_bytes(b"the square of the set before")
        Path("out/film-wide.mp4").write_bytes(b"the wide of the set before")
        self.assertEqual(self.final(()), 0)
        self.assertEqual(sorted(str(p.relative_to("out")) for p in Path("out").rglob("*")), ["cover.png", "film.mp4", "story.png"])
        self.assertEqual(_env.read_json("cards.json")["cards"], [])
        self.assertEqual(_env.read_json("engine.json")["made"], {"formats": ["reel"], "stories": False})
        import qa
        self.assertEqual(qa.made(), ({"reel"}, False))

    def test_also_makes_exactly_the_shapes_the_person_asked_for(self):
        self.assertEqual(self.final(("square",)), 0)
        self.assertEqual(sorted(str(p.relative_to("out")) for p in Path("out").rglob("*")), ["cover.png", "film-square.mp4", "film.mp4", "story.png"])
        self.assertEqual(self.final(("landscape", "stories")), 0)
        self.assertEqual(sorted(str(p.relative_to("out")) for p in Path("out").rglob("*")),
                         ["cover.png", "film-wide.mp4", "film.mp4", "people", "people/01-ana.png", "people/02-bo.png", "story.png"])
        import qa
        self.assertEqual(qa.made(), ({"reel", "wide"}, True))

    def test_the_render_command_takes_the_shapes_after_also(self):
        got = {}

        @contextlib.contextmanager
        def lock(name):
            yield None
        with mock.patch.object(sys, "argv", ["film.py", "render", "--also", "landscape", "square", "stories"]), \
                mock.patch.object(film._env, "enter_run", lambda: None), mock.patch.object(film.studio, "lock", lock), \
                mock.patch.object(film, "cmd_render", lambda a, run: got.setdefault("also", a.also) and 0):
            film.main()
        self.assertEqual(got["also"], ["landscape", "square", "stories"])

    def test_the_gate_fails_on_a_shape_in_out_that_nobody_asked_for(self):
        self.assertEqual(self.final(()), 0)
        Path("out/film-wide.mp4").write_bytes(b"a wide film nobody asked for")
        Path("out/people").mkdir()
        Path("out/people/01-ana.png").write_bytes(b"a story card nobody asked for")
        import qa
        ok, detail = qa.formats_check(1.0)
        self.assertFalse(ok)
        self.assertIn("out/film-wide.mp4 is in out/, and the render did not make it (nobody asked for it)", detail)
        self.assertNotIn("film-square.mp4", detail)
        ok, detail = qa.cards_check()
        self.assertFalse(ok)
        self.assertIn("01-ana.png", detail)

    def test_a_white_film_fails_the_render_and_leaves_out_unchanged(self):
        self.white = {"wide-silent.mp4"}
        self.assertEqual(self.final(), 1)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(Path("out").exists())


class Stopped(Exception):
    """The command stopped where a kill would stop it."""


def argparse_ns(also=()):
    return types.SimpleNamespace(cmd="render", again=False, also=list(also))


def flashed(out, white):
    """Two seconds of test picture with `white` frames of plain white between them, at 30 fps."""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30:d=1", "-f", "lavfi", "-i",
                    f"color=c=white:s=64x64:r=30:d={white / 30}", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30:d=1",
                    "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p", str(out)], check=True)


def burned(out):
    """Four seconds of test picture whited out for two frames in every seventeen, so the burns fall at every phase of
    a sampler that looks twice a second."""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:r=30:d=4", "-vf",
                    "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(n,17),2)'", "-pix_fmt", "yuv420p", str(out)],
                   check=True)


class Blank(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_ = types.SimpleNamespace(spawn=subprocess.run)

    def test_a_burn_that_whites_out_two_frames_at_a_cut_is_not_a_blank_film(self):
        burned(self.tmp / "burn.mp4")
        self.assertEqual(film.white_seconds(self.run_, self.tmp / "burn.mp4"), [])

    def test_a_second_of_white_where_a_context_was_lost_is_blank_from_where_it_starts(self):
        flashed(self.tmp / "lost.mp4", 30)
        seconds = film.white_seconds(self.run_, self.tmp / "lost.mp4")
        self.assertEqual(len(seconds), 1)
        self.assertAlmostEqual(seconds[0], 1.0, delta=0.07)


if __name__ == "__main__":
    unittest.main()
