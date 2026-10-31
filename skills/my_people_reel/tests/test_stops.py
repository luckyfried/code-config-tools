"""A command stopped at any point leaves nothing the next command reads wrongly: deliver holds the run's lock and every
process its gate starts goes through it; a draft takes the snap away with the vote and the board before away whole; a
sheets takes the sheets away before it draws; a clip normalize stopped half way leaves clips.json naming whole folders;
a maker stopped mid-file leaves no file at the name a later command reads; a made bed stopped before music.json leaves
the source music.json names; and the critics' round of a cut is opened once.

    python3 -I -m unittest discover -s S/tests -p test_stops.py
"""
import contextlib
import hashlib
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


def bed(level=0.0, stopped=None):
    """A stand-in for music_engine.compose: it writes music/bed.wav (one second of `level`) and answers what compose
    answers; with `stopped`, it writes half the file and raises it."""
    import wave

    def compose(recipe, styles, avoid, seconds, edges, hue, seed, bpm=120, out=None):
        f = Path(out) / "bed.wav"
        if stopped:
            f.write_bytes(b"half a file")
            raise stopped
        with wave.open(str(f), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(int(level * 32767).to_bytes(2, "little", signed=True) * 22050)
        return {"key": "C major", "bpm": bpm, "removed": [], "chords": ["C"], "recipe": recipe}

    return compose


class Stopped(Exception):
    """The command stopped where a kill would stop it."""


def ff(*args):
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


class Stops(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.run_dir = self.root / "build" / "20260101T000000Z"
        self.run_dir.mkdir(parents=True)
        (self.root / "build" / "current").write_text(self.run_dir.name + "\n")
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        env = mock.patch.dict(os.environ, {"MPR_WORKSPACE": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("MPR_RUN", None)

    def test_deliver_holds_the_run_lock_and_every_process_its_gate_starts_goes_through_it(self):
        _env.write_json(self.run_dir / "library.json", {"handle": "me", "year": 2026})
        _env.write_json(self.run_dir / "taste.json", {"year": 2026, "people": [{"handle": "ana"}]})
        _env.write_json(self.run_dir / "winner.json", {"board": "drive", "totals": {"drive": 40}, "order": ["drive"]})
        _env.write_json(self.run_dir / "cards.json", {"cards": [{"handle": "ana", "file": "out/people/01-ana.png"}]})
        _env.write_json(self.run_dir / "engine.json", {"made": {"formats": ["reel", "square", "wide"], "stories": True}})
        (self.run_dir / "out").mkdir()
        for f, size in (("film", "1080x1920"), ("film-square", "1080x1080"), ("film-wide", "1920x1080")):
            ff("-f", "lavfi", "-i", f"testsrc=s={size}:r=30:d=1", "-pix_fmt", "yuv420p", str(self.run_dir / f"out/{f}.mp4"))
        import deliver
        import studio
        real, held = subprocess.run, {"spawned": []}

        def spawn(argv, **kwargs):
            held["spawned"].append(argv[0])
            return real(argv, **kwargs)

        @contextlib.contextmanager
        def lock(name):
            held["lock"] = name
            yield types.SimpleNamespace(spawn=spawn)

        _env.tools()
        outside = mock.Mock(side_effect=AssertionError("a process started outside the run's lock"))
        with mock.patch.object(_env, "WORKSPACE", str(self.root)), mock.patch.object(studio, "lock", lock), \
                mock.patch.object(subprocess, "run", outside), mock.patch.object(sys, "argv", ["deliver.py"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        self.assertEqual(held.get("lock"), "deliver")
        self.assertGreaterEqual(len(held["spawned"]), 7, held["spawned"])
        self.assertEqual(set(held["spawned"]), {_env.ffmpeg(), _env.ffprobe()})
        self.assertIn("Not ready to post", (self.run_dir / "out" / "review.html").read_text())

    def deliver(self, failing):
        """deliver.py on a run with a reel in out/ and the gate's failing checks given; its exit code and stdout."""
        _env.write_json(self.run_dir / "library.json", {"handle": "me", "year": 2026})
        _env.write_json(self.run_dir / "taste.json", {"year": 2026, "people": [{"handle": "ana"}]})
        _env.write_json(self.run_dir / "winner.json", {"board": "drive", "totals": {"drive": 40}, "order": ["drive"]})
        _env.write_json(self.run_dir / "cards.json", {"cards": []})
        (self.run_dir / "out").mkdir()
        (self.run_dir / "out" / "film.mp4").write_bytes(b"the reel")
        import deliver
        import studio

        @contextlib.contextmanager
        def lock(name):
            yield types.SimpleNamespace(spawn=subprocess.run)

        printed = io.StringIO()
        with mock.patch.object(_env, "WORKSPACE", str(self.root)), mock.patch.object(studio, "lock", lock), \
                mock.patch.object(deliver.qa, "gate", lambda run: failing), mock.patch.object(sys, "argv", ["deliver.py"]), \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(io.StringIO()):
            code = deliver.main()
        return code, printed.getvalue().splitlines()[-1]

    def test_a_green_delivers_last_line_is_the_delivered_reels_path_from_the_workspace_root(self):
        code, last = self.deliver([])
        self.assertEqual(code, 0)
        self.assertEqual(last, "build/20260101T000000Z/out/film.mp4")
        self.assertEqual((self.root / last).read_bytes(), b"the reel")

    def test_a_red_delivers_last_line_names_the_failing_check_and_no_film(self):
        code, last = self.deliver([("deliver", "caption has no hashtags")])
        self.assertEqual(code, 1)
        self.assertTrue(last.startswith("not delivered: the gate failed on deliver;"), last)
        self.assertNotIn("film.mp4", last)

    def test_a_draft_takes_the_snap_away_with_the_vote(self):
        (self.run_dir / "taste.md").write_text("you are")
        for f in ("winner.json", "film.json"):
            (self.run_dir / f).write_text("{}")
        env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
        subprocess.run([sys.executable, str(KIT / "scripts" / "storyboard.py"), "draft"], cwd=self.root, env=env,
                       capture_output=True, text=True, timeout=120)
        self.assertFalse((self.run_dir / "winner.json").exists())
        self.assertFalse((self.run_dir / "film.json").exists())

    def test_a_draft_stopped_while_it_deletes_the_board_before_leaves_no_board_to_read(self):
        os.chdir(self.run_dir)
        Path("taste.md").write_text("you are")
        Path("storyboards/drive/frames").mkdir(parents=True)
        for f in ("storyboard.json", "storyboard.md", "sheet.png", "frames/hook-reel.png"):
            Path("storyboards/drive", f).write_text("the board before")
        import storyboard

        def stopped_deleting(path, *args, **kwargs):
            if Path(path).exists():
                raise Stopped

        with mock.patch.object(storyboard.boards, "Ctx", lambda: None), mock.patch.object(storyboard.S, "trio_for", lambda named: ("drive",)), \
                mock.patch.object(storyboard.boards, "draft", lambda t, ctx: {"name": "the board after"}), \
                mock.patch.object(storyboard, "markdown", lambda sb, ctx: ""), \
                mock.patch.object(storyboard, "summary", lambda sb, ctx: {"beats": 0, "seconds": 0, "cuts_per_minute": 0}), \
                mock.patch.object(shutil, "rmtree", stopped_deleting), self.assertRaises(Stopped), \
                contextlib.redirect_stdout(io.StringIO()):
            storyboard.cmd_draft(types.SimpleNamespace(style=None))
        self.assertFalse(Path("storyboards/drive").exists())

    def test_a_sheets_stopped_while_it_renders_leaves_no_sheet_to_vote_on(self):
        os.chdir(self.run_dir)
        Path("storyboards/drive").mkdir(parents=True)
        for f in ("sheet.png", "sheet-square.png", "sheet-wide.png"):
            Path("storyboards/drive", f).write_text("tiled from the frames before")
        import storyboard

        def stopped(jobs, name, run):
            raise Stopped

        studio = types.SimpleNamespace(still=lambda *a, **k: {}, render=stopped)
        with mock.patch.object(storyboard, "load", lambda t: {}), mock.patch.object(storyboard.boards, "Ctx", lambda: None), \
                mock.patch.object(storyboard.boards, "layout", lambda sb, ctx, kind: {}), \
                mock.patch.object(storyboard.boards, "roles", lambda board: {"hook": 0}), \
                mock.patch.object(storyboard.boards, "rest_frame", lambda board, i: 0), \
                mock.patch.object(storyboard, "looks", lambda: ("drive",)), self.assertRaises(Stopped):
            storyboard.sheets(None, studio, None)
        self.assertEqual(sorted(Path("storyboards/drive").glob("sheet*.png")), [])

    def test_a_normalize_stopped_half_way_leaves_clips_json_naming_whole_folders(self):
        run = self.run_dir
        (run / "public" / "matched").mkdir(parents=True)
        (run / "clips").mkdir()
        ff("-f", "lavfi", "-i", "color=c=0x996633:s=320x480", "-frames:v", "1", str(run / "public/matched/a.jpg"))
        clips = [{"id": i, "beat": b, "role": "r", "seconds": 1.0, "image": "matched/a.jpg", "prompt": "p", "stand_in": "s"}
                 for i, b in (("00", "hook"), ("01", "person-5"))]
        _env.write_json(run / "render" / "board-reel.json",
                        {"beats": [{"id": "hook", "frames": 20}, {"id": "person-5", "frames": 20}], "clips": clips})

        def arrive(color):
            for i in ("00", "01"):
                ff("-f", "lavfi", "-i", f"color=c={color}:s=320x480:r=30:d=1", "-pix_fmt", "yuv420p", str(run / f"clips/{i}.mp4"))

        arrive("red")
        r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "normalize"], cwd=self.root,
                           capture_output=True, text=True, env=os.environ)
        self.assertEqual(r.returncode, 0, r.stderr)
        arrive("blue")
        import clips as clips_py
        real, calls = subprocess.run, []

        def stopped_on_the_second_clip(argv, **kwargs):
            if "-stream_loop" in argv:
                calls.append(argv)
                if len(calls) == 2:
                    raise Stopped
            return real(argv, **kwargs)

        os.chdir(run)
        with mock.patch.object(clips_py.subprocess, "run", stopped_on_the_second_clip), self.assertRaises(Stopped), \
                contextlib.redirect_stdout(io.StringIO()):
            clips_py.cmd_normalize(types.SimpleNamespace(why=None))
        named = json.loads((run / "clips.json").read_text())["clips"]
        self.assertEqual({r["status"] for r in named.values()}, {"generated"})
        for r in named.values():
            self.assertEqual(len(list((run / "public" / r["dir"]).glob("*.jpg"))), r["frames"], r["dir"])

    def test_a_maker_stopped_mid_file_leaves_no_file_where_a_later_command_reads_one(self):
        os.chdir(self.run_dir)
        import music
        import picks
        tools = (_env.ffmpeg(), _env.ffprobe())

        def stopped_mid_file(argv, **kwargs):
            self.assertIn(argv[0], tools)
            if argv[0] == tools[1]:
                return subprocess.CompletedProcess(argv, 0, stdout="10\n", stderr="")
            Path(argv[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(argv[-1]).write_bytes(b"half a file")
            raise Stopped

        with mock.patch.object(music.music_engine, "compose", bed(stopped=Stopped)), self.assertRaises(Stopped):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=8))
        self.assertEqual(sorted(Path("music").glob("bed-*.wav")), [])
        self.assertFalse(Path("music.json").exists())
        video = self.root / "reel.mp4"
        with mock.patch.object(picks.subprocess, "run", stopped_mid_file), self.assertRaises(Stopped):
            picks.poster(video)
        self.assertEqual([p.name for p in Path("photos").glob("[!.]*.jpg")], [])

    def test_a_made_bed_stopped_before_music_json_leaves_the_source_music_json_names(self):
        os.chdir(self.run_dir)
        import music
        Path("music").mkdir()
        Path("music/source.mp3").write_bytes(b"the source the index names")
        _env.write_json("music.json", {"file": "music/source.mp3"})
        write_json = _env.write_json

        def stopped_at_the_index(path, obj):
            if Path(path).name == "music.json":
                raise Stopped
            write_json(path, obj)

        with mock.patch.object(_env, "write_json", stopped_at_the_index), \
                mock.patch.object(music.music_engine, "compose", bed()), self.assertRaises(Stopped):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=8))
        self.assertEqual(json.loads(Path("music.json").read_text())["file"], "music/source.mp3")
        self.assertEqual(Path("music/source.mp3").read_bytes(), b"the source the index names")

    def test_the_same_cut_keeps_its_round_and_a_changed_cut_opens_the_next(self):
        os.chdir(self.run_dir)
        import vote

        def cut(data):
            Path("render").mkdir(exist_ok=True)
            Path("render/cut.mp4").write_bytes(data)
            _env.write_json("render/cut.json", {"film": hashlib.sha256(data).hexdigest()[:16]})

        def score(path):
            data = _env.read_json(path)
            for critic in data["critics"].values():
                critic["boards"]["film"] = {"scores": {f"R{i}": 4 for i in range(1, 7)}, "paragraph": " ".join(["each beat lands on the cut and the type reads at a glance"] * 3)}
            _env.write_json(path, data)

        cut(b"the first cut")
        with contextlib.redirect_stdout(io.StringIO()):
            vote.cmd_cut(None)
            vote.cmd_cut(None)
            self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
            # a cut that replaces one nobody scored takes its round over
            cut(b"the cut before anyone scored")
            vote.cmd_cut(None)
            self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
            self.assertEqual(_env.read_json("critic/cut-1.json")["film"], hashlib.sha256(b"the cut before anyone scored").hexdigest()[:16])
            score("critic/cut-1.json")
            cut(b"the cut after the fix")
            vote.cmd_cut(None)
            self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
            Path("render/cut.json").unlink()
            with self.assertRaises(SystemExit):
                vote.cmd_cut(None)


if __name__ == "__main__":
    unittest.main()
