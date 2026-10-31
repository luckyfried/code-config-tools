"""A command stopped partway never leaves part of a file where a later command reads one: graded and matched
photographs, the photographs picks prepares and their posters, the mastered music and the style sheet are made
under a temporary name and moved in whole, and clips.py normalize makes the new clip folders first, then clips.json,
and only then removes the folders it no longer names; music.json names the earlier track until music.py make has
composed the new bed. Each test stops the command inside its write.

    python3 -I -m unittest discover -s S/tests -p test_inputs_whole.py
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
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import clips  # noqa: E402
import grade  # noqa: E402
import music  # noqa: E402
import picks  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
from PIL import Image  # noqa: E402


class Stop(Exception):
    pass


def done(argv):
    return subprocess.CompletedProcess(argv, 0, "", "")


def stopped(argv, **kw):
    """A process killed while it writes: half its output stands at the name it was given."""
    Path(argv[-1]).write_bytes(b"half a file")
    raise Stop


class InputsWhole(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        for patch in (mock.patch.object(_env, "ffmpeg", return_value="ffmpeg"),
                      mock.patch.object(_env, "ffprobe", return_value="ffprobe")):
            patch.start()
            self.addCleanup(patch.stop)
        self.quiet = contextlib.ExitStack()
        self.quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.addCleanup(self.quiet.close)

    def names(self, folder):
        return sorted(p.name for p in Path(folder).glob("[!.]*")) if Path(folder).exists() else []

    def test_a_grade_stopped_partway_leaves_no_graded_photograph(self):
        grade.GRADED.mkdir(parents=True)
        with mock.patch.object(grade.subprocess, "run", stopped), self.assertRaises(Stop):
            grade.grade_file(Path("photos/a.jpg"), grade.GRADED / "a.jpg", "null")
        self.assertEqual(self.names(grade.GRADED), [])

    def test_a_prepared_photograph_and_a_poster_stopped_partway_leave_nothing_at_their_names(self):
        Path("in").mkdir()
        Image.new("RGB", (40, 30), "red").save("in/a.jpg")
        real = Image.Image.save

        def save(im, fp, *a, **kw):
            Path(fp).write_bytes(b"half a jpeg")
            raise Stop
        with mock.patch.object(Image.Image, "save", save), self.assertRaises(Stop):
            picks.prepare("in/a.jpg")
        self.assertEqual(self.names(picks.PHOTOS), [])
        with mock.patch.object(Image.Image, "save", real):
            got = picks.prepare("in/a.jpg")
        self.assertEqual(Image.open(got).size, (40, 30))

        def run(argv, **kw):
            if argv[0] == "ffprobe":
                return subprocess.CompletedProcess(argv, 0, "10\n", "")
            stopped(argv)
        with mock.patch.object(picks.subprocess, "run", run), self.assertRaises(Stop):
            picks.poster("in/clip.mp4")
        self.assertEqual(self.names(picks.PHOTOS), [Path(got).name])

    def test_a_master_stopped_partway_leaves_no_master(self):
        music.MUSIC.mkdir()
        _env.write_json("music.json", {"file": "music/source.wav"})
        _env.write_json("film.json", {"seconds": 2.0})

        def run(argv, **kw):
            if argv[-1] == "-":
                return subprocess.CompletedProcess(argv, 0, "", "I: -14.0 LUFS")
            if "master" in Path(argv[-1]).name:
                stopped(argv)
            Path(argv[-1]).write_bytes(b"mix")
            return done(argv)
        with mock.patch.object(music.subprocess, "run", run), self.assertRaises(Stop):
            music.cmd_master(argparse.Namespace(seconds=None))
        self.assertNotIn("master.wav", self.names(music.MUSIC))

    def test_a_master_stopped_at_its_move_leaves_music_json_naming_no_master(self):
        music.MUSIC.mkdir()
        (music.MUSIC / "master.wav").write_bytes(b"the earlier master")
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav", "master_lufs": -14.0})
        _env.write_json("film.json", {"seconds": 2.0})

        def run(argv, **kw):
            if argv[-1] == "-":
                return subprocess.CompletedProcess(argv, 0, "", "I: -14.0 LUFS")
            Path(argv[-1]).write_bytes(b"mix")
            return done(argv)

        real = os.replace

        def replace(src, dst):
            if Path(dst).name == "master.wav":
                raise Stop
            real(src, dst)
        with mock.patch.object(music.subprocess, "run", run), mock.patch.object(music.os, "replace", replace), \
                self.assertRaises(Stop):
            music.cmd_master(argparse.Namespace(seconds=None))
        self.assertEqual((music.MUSIC / "master.wav").read_bytes(), b"the earlier master")
        self.assertEqual(_env.read_json("music.json"), {"file": "music/source.wav"})

    def test_a_bed_stopped_while_it_is_composed_leaves_music_json_naming_the_earlier_track(self):
        music.MUSIC.mkdir()
        (music.MUSIC / "source.mp3").write_bytes(b"their track")
        _env.write_json("music.json", {"file": "music/source.mp3"})
        with mock.patch.object(music.music_engine, "compose", side_effect=Stop), self.assertRaises(Stop):
            music.cmd_make(argparse.Namespace(bpm=None, seconds=2.0))
        self.assertEqual(_env.read_json("music.json"), {"file": "music/source.mp3"})
        self.assertTrue((music.MUSIC / "source.mp3").exists())

    def test_a_style_sheet_stopped_partway_leaves_no_sheet(self):
        real = Image.Image.save

        def render(jobs, name, run=None):
            for j in jobs:
                real(Image.new("RGB", (20, 30), "blue"), j["out"])
            return {"jobs": len(jobs), "failed": 0, "findings": []}

        def save(im, fp, *a, **kw):
            if "sheet" in Path(fp).name:
                stopped([fp])
            real(im, fp, *a, **kw)
        with mock.patch.object(storyboard, "load_boards", return_value=[{"id": "1", "name": "lisbon week · Scrapbook", "style": "scrapbook"}]), \
                mock.patch.object(storyboard, "sheet_frames", return_value=({}, (("hook", 1), ("middle", 2), ("closer", 3)))), \
                mock.patch.object(studio, "still", lambda tb, fr, out, scale: {"out": str(out)}), \
                mock.patch.object(studio, "render", render), mock.patch.object(Image.Image, "save", save), \
                self.assertRaises(Stop):
            storyboard.cmd_sheets(argparse.Namespace(board=None), None)
        self.assertEqual(self.names(storyboard.BOARDS / "1"), ["frames"])

    def test_a_normalize_stopped_partway_leaves_clips_json_naming_whole_folders(self):
        _env.write_json("film.json", {"clips": [{"id": c, "beat": "b", "role": "r", "image": f"graded/{c}.jpg", "prompt": "p",
                                                 "stand_in": "s"} for c in ("01", "02")]})
        clips.CLIPS.mkdir()
        for c in ("01", "02"):
            (clips.CLIPS / f"{c}.mp4").write_bytes(c.encode() * 600)

        def frames(argv, **kw):
            for n in (1, 2, 3):
                Path(argv[-1] % n).write_bytes(b"jpeg")
            return done(argv)

        def second_stops(argv, **kw):
            if Path(argv[-1]).parent.name.lstrip(".").startswith("02"):
                Path(argv[-1] % 1).write_bytes(b"jpeg")
                raise Stop
            return frames(argv)
        normalize = lambda: clips.cmd_normalize(argparse.Namespace(why=None))
        with mock.patch.object(clips, "window", return_value=(0, 3)), mock.patch.object(clips, "size_of", return_value=(64, 64)), \
                mock.patch.object(grade, "ensure_recipe", return_value={"filter": "null"}):
            with mock.patch.object(clips.subprocess, "run", frames):
                normalize()
            first = Path("clips.json").read_text()
            (clips.CLIPS / "02.mp4").write_bytes(b"a new clip" * 200)
            with mock.patch.object(clips.subprocess, "run", second_stops), self.assertRaises(Stop):
                normalize()
            self.assertEqual(Path("clips.json").read_text(), first)
            named = [r["dir"] for r in json.loads(first)["clips"].values()]
            self.assertEqual([self.names(clips.PUBLIC / d) for d in named], [["0001.jpg", "0002.jpg", "0003.jpg"]] * 2)
            with mock.patch.object(clips.subprocess, "run", frames):
                normalize()
        now = [r["dir"] for r in _env.read_json("clips.json")["clips"].values()]
        self.assertEqual(now[0], named[0])
        self.assertNotEqual(now[1], named[1])
        self.assertEqual(sorted(p.name for p in (clips.PUBLIC / "clips").iterdir()), sorted(Path(d).name for d in now))


if __name__ == "__main__":
    unittest.main()
