"""A command stopped partway leaves the run in a state the next command reads correctly or refuses: deliver takes the
run's lock and removes the delivered page before out/ changes; draft removes film.json and lands each board whole;
every input a later command reads is made under a staged name and moved in; an index goes only after the files it
names are replaced, and a sheet goes before the frames it shows; the cut's critics' round is reused for the same cut; snap cuts the board as the vote stored it;
and every process QA starts goes through the spawn it is given.

    python3 -I -m unittest discover -s S/tests -p test_stops.py
"""
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402

REAL_RUN = subprocess.run


def setUpModule():
    # setup.py runs once here, so a test that replaces subprocess.run never reaches it
    _env.tools()


def half_then_killed(cmd, *a, **k):
    """A process killed after it wrote part of its output (the last argument)."""
    Path(cmd[-1]).write_bytes(b"half")
    raise KeyboardInterrupt


def made(folder):
    """The files in `folder` a later command would read (not the staged ones)."""
    return sorted(p.name for p in Path(folder).iterdir() if not p.name.startswith(".")) if Path(folder).is_dir() else []


def ff(*args):
    REAL_RUN([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


# the chosen board a music make reads: its style names the card's music recipe
WINNER = {"board": "1", "storyboard": {"id": "1", "style": "kinetic-type", "bpm": 120, "beats": [{"len": 4}]}}


class Run(unittest.TestCase):
    """A workspace whose build/current is one run, with the process inside it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.root = Path(self.tmp.name)
        self.run = self.root / "build" / "run"
        self.run.mkdir(parents=True)
        (self.run.parent / "current").symlink_to("run", target_is_directory=True)
        saved = Path.cwd(), dict(os.environ), _env.ROOT
        self.addCleanup(lambda: (os.chdir(saved[0]), os.environ.clear(), os.environ.update(saved[1]),
                                 setattr(_env, "ROOT", saved[2])))
        self.addCleanup(self.tmp.cleanup)
        os.environ["LH_ROOT"] = str(self.root)
        os.environ.pop("LH_RUN", None)
        _env.ROOT = None
        os.chdir(self.run)

    def put(self, name, value):
        p = self.run / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value if isinstance(value, str) else json.dumps(value))
        return p


class Deliver(Run):
    def setUp(self):
        super().setUp()
        self.put("library.json", {"subject": {"name": "the cup"}})
        self.put("taste.json", {"register": {}})
        self.put("winner.json", {"board": "1", "totals": {"1": 20}})
        self.page = self.put("out/review.html", "<p>the delivered page</p>")

    def test_a_deliver_stopped_before_its_captions_leaves_no_delivered_page(self):
        import deliver

        def killed(*a, **k):
            raise KeyboardInterrupt
        with mock.patch.object(deliver, "captions", killed), mock.patch.object(sys, "argv", ["deliver.py"]):
            with self.assertRaises(KeyboardInterrupt):
                deliver.main()
        self.assertFalse(self.page.exists())

    @unittest.skipUnless(os.name == "posix", "the held lock is a flock")
    def test_a_deliver_refused_by_a_running_render_changes_nothing(self):
        import fcntl
        import deliver
        (self.run / "render").mkdir()
        held = open(self.run / "render" / "render.lock", "a+")
        self.addCleanup(held.close)
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held.write("cards-report\tthe log\n")
        held.flush()
        with mock.patch.object(sys, "argv", ["deliver.py"]), self.assertRaises(SystemExit) as e:
            deliver.main()
        self.assertEqual(str(e.exception.code), "a render named cards-report is already running in this run; its log is the log")
        self.assertEqual(made(self.run / "out"), ["review.html"])
        self.assertEqual(self.page.read_text(), "<p>the delivered page</p>")


class Draft(Run):
    def test_a_draft_stopped_while_it_writes_a_board_leaves_no_board_and_no_film(self):
        import storyboard
        self.put("library.json", {"subject": {"name": "the cup"}})
        self.put("taste.md", "you are")
        self.put("film.json", {"board": "1", "name": "the film of the old board"})
        self.put("storyboards/1/storyboard.json", {"id": "1", "name": "the old board"})

        def killed(*a, **k):
            raise KeyboardInterrupt
        c = storyboard.cast
        with mock.patch.object(c, "measure_subject", lambda lib: {"pieces": [1]}), \
                mock.patch.object(c, "cast", lambda *a: {}), mock.patch.object(c, "stage_subject", lambda p: None), \
                mock.patch.object(storyboard, "stage_assets", lambda: None), \
                mock.patch.object(storyboard, "context", lambda *a: ({}, [])), \
                mock.patch.object(storyboard, "board", lambda *a: {"id": "1", "name": "the new board"}), \
                mock.patch.object(storyboard, "write_md", killed), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                storyboard.cmd_draft(None)
        self.assertFalse((self.run / "film.json").exists())
        self.assertFalse((self.run / "storyboards" / "1").exists())


class Sheets(Run):
    def test_sheets_stopped_while_it_renders_leaves_no_sheet_of_the_old_frames(self):
        import storyboard
        sheet = self.put("storyboards/1/sheet.png", "the sheet of the old frames")
        self.put("storyboards/1/frames/01-hook.png", "an old frame")

        def killed(*a, **k):
            raise KeyboardInterrupt
        board = {"id": "1", "name": "n", "tone": "drive", "bpm": 120, "beats": [{"frames": 30, "pulse": 7.5}]}
        with mock.patch.object(storyboard._env, "engine", lambda: {}), mock.patch.object(storyboard._env, "render", killed), \
                mock.patch.object(storyboard, "load_boards", lambda: {"1": board}), \
                mock.patch.object(storyboard, "issues", lambda b: []), mock.patch.object(storyboard, "timed", lambda b: board), \
                mock.patch.object(storyboard, "timeline", lambda t: [{"id": "hook"}]), \
                mock.patch.object(storyboard, "rest", lambda *a: 0), self.assertRaises(KeyboardInterrupt):
            storyboard.cmd_sheets(None)
        self.assertFalse(sheet.exists())


class Staged(Run):
    def test_a_stopped_photograph_leaves_no_photograph(self):
        import picks

        class Picture:
            def thumbnail(self, *a):
                pass

            def save(self, path, *a, **k):
                half_then_killed([path])
        with mock.patch.object(picks, "open_image", lambda *a, **k: Picture()), self.assertRaises(KeyboardInterrupt):
            picks.prepare(self.put("theirs.jpg", "photo"))
        self.assertEqual(made(self.run / picks.PHOTOS), [])

    def test_a_stopped_poster_leaves_no_poster(self):
        import picks

        def run(cmd, *a, **k):
            if cmd[0] == _env.ffprobe():
                return subprocess.CompletedProcess(cmd, 0, "2.0", "")
            half_then_killed(cmd)
        with mock.patch.object(picks.subprocess, "run", run), self.assertRaises(KeyboardInterrupt):
            picks.poster(self.put("reel.mp4", "reel"))
        self.assertEqual(made(self.run / picks.PHOTOS), [])

    def stopped_at_music_json(self, command):
        """`command` stopped as it publishes music.json."""
        import music
        write = music._env.write_json

        def killed(path, obj):
            if str(path) == "music.json":
                raise KeyboardInterrupt
            write(path, obj)
        with mock.patch.object(music._env, "write_json", killed), self.assertRaises(KeyboardInterrupt), \
                contextlib.redirect_stdout(io.StringIO()):
            command(music)
        return json.loads((self.run / "music.json").read_text())

    def test_a_stopped_make_leaves_music_json_naming_the_audio_its_grid_was_read_from(self):
        self.put("music/source.wav", "the bed the grid was read from")
        self.put("music.json", {"file": "music/source.wav", "bpm": 76, "downbeats": [0.5, 3.66]})
        self.put("winner.json", WINNER)
        info = self.stopped_at_music_json(lambda m: m.cmd_make(argparse.Namespace(mood="calm", bpm=None, seconds=2.0)))
        self.assertEqual((self.run / info["file"]).read_bytes(), b"the bed the grid was read from")

    def test_a_stopped_master_leaves_music_json_naming_its_own_master(self):
        ff("-f", "lavfi", "-i", "sine=f=220:d=3", "-ac", "2", str(self.put("music/source.wav", "")))
        self.put("music/master.wav", "the master music.json names")
        self.put("music.json", {"file": "music/source.wav", "bpm": 120, "master": "music/master.wav"})
        self.put("film.json", {"seconds": 2.0, "bpm": 120})
        info = self.stopped_at_music_json(lambda m: m.cmd_master(argparse.Namespace(seconds=None)))
        self.assertEqual((self.run / info["master"]).read_bytes(), b"the master music.json names")


class Index(Run):
    def test_music_make_removes_the_old_source_only_after_music_json_names_the_new_one(self):
        import music
        self.put("music/source.mp3", "the track found")
        self.put("music.json", {"file": "music/source.mp3", "bpm": 120})
        self.put("winner.json", WINNER)
        write = music._env.write_json

        def killed(path, obj):
            if str(path) == "music.json":
                raise KeyboardInterrupt
            write(path, obj)
        with mock.patch.object(music._env, "write_json", killed), self.assertRaises(KeyboardInterrupt), \
                contextlib.redirect_stdout(io.StringIO()):
            music.cmd_make(argparse.Namespace(mood="calm", bpm=None, seconds=2.0))
        self.assertTrue((self.run / json.loads((self.run / "music.json").read_text())["file"]).exists())

    def test_a_stopped_normalize_leaves_clips_json_naming_whole_clips(self):
        import clips
        self.put("film.json", {"beats": [{"id": "made", "frames": 45}],
                               "clips": [{"id": "made", "beat": "made", "role": "r", "image": "photos/a.jpg", "prompt": "p",
                                          "stand_in": "s"}]})
        self.put("clips/made.mp4", "x" * 2000)
        self.put("public/clips/made/0001.jpg", "the frame")
        self.put("clips.json", {"clips": {"made": {"status": "generated", "dir": "clips/made", "frames": 1}}})

        def killed(*a, **k):
            raise KeyboardInterrupt
        with mock.patch.object(clips, "conform", killed), self.assertRaises(KeyboardInterrupt):
            clips.cmd_normalize(argparse.Namespace(why=None))
        for r in json.loads((self.run / "clips.json").read_text())["clips"].values():
            self.assertEqual(made(self.run / "public" / r["dir"]), ["0001.jpg"])


class Vote(Run):
    def test_asking_for_the_critics_again_on_the_same_cut_reopens_its_round(self):
        import film
        import vote
        self.put("film.json", {"board": "1"})
        self.put("film.silent.mp4", "cut")
        self.put("cut.json", {"film": film.film_hash()})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vote.cmd_cut(None), 0)
            self.assertEqual(vote.cmd_cut(None), 0)
        self.assertEqual(made(self.run / "critic"), ["cut-1.json"])

    def test_snap_cuts_the_board_the_vote_judged_never_an_edit_since(self):
        import storyboard
        import vote
        board = self.run / "storyboards" / "1" / "storyboard.json"
        self.put("storyboards/1/storyboard.json", {"id": "1", "name": "as voted", "style": "kinetic-type", "bpm": 120, "beats": []})
        why = "the read of this board written in at least eight words"
        self.put("vote/scores.json", {"critics": {c: {"boards": {"1": {
            "scores": {k: 5 for k in vote.CRITERIA}, "paragraph": " ".join(["word"] * 30),
            "swap": {"pass": True, "why": why}}}} for c in vote.PANEL}})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vote.cmd_tally(None), 0)
        board.write_text(json.dumps({"id": "1", "name": "edited after the vote", "style": "kinetic-type", "bpm": 120, "beats": []}))
        with mock.patch.object(storyboard, "timed", lambda b, m=None: {**b, "seconds": 1.0}), \
                mock.patch.object(storyboard, "timeline", lambda f: []), \
                mock.patch.object(storyboard, "stills_of", lambda f: ([], {})), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(storyboard.cmd_snap(None), 0)
        self.assertEqual(json.loads((self.run / "film.json").read_text())["name"], "as voted")


class Gate(Run):
    def test_every_process_the_gate_starts_goes_through_the_spawn_it_is_given(self):
        import qa
        ff("-f", "lavfi", "-i", "testsrc=s=108x192:r=30:d=1", "-f", "lavfi", "-i", "sine=d=1", "-shortest",
           "-pix_fmt", "yuv420p", "-c:a", "aac", str(self.run / "film.mp4"))
        (self.run / "out").mkdir()
        os.replace(self.run / "film.mp4", self.run / "out" / "film.mp4")
        self.put("film.json", {"system": {"colors": {"bg": "#000000"}},
                               "beats": [{"id": "hook", "frames": 30, "layers": []}]})
        self.put("music.json", {"file": "music/source.wav"})
        started = []

        def spawn(cmd, *a, **k):
            started.append(Path(cmd[0]).name)
            return REAL_RUN(cmd, *a, **k)

        def outside(*a, **k):
            raise AssertionError(f"started outside the spawn: {a[0]}")
        with mock.patch.object(qa.subprocess, "run", outside), mock.patch.object(qa, "board_checks", lambda b, c: None), \
                contextlib.redirect_stdout(io.StringIO()):
            qa.gate_checks(spawn)
        self.assertGreaterEqual(len(started), 8)
        self.assertEqual(set(started), {Path(_env.ffmpeg()).name, Path(_env.ffprobe()).name})


if __name__ == "__main__":
    unittest.main()
