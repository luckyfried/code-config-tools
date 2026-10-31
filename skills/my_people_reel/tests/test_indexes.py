"""Each completion index speaks for a whole set at every moment a command can stop: deliver writes the not-ready page,
then sets out/film.mp4 aside while the caption moves in; sheets tiles sheet.png after a board's other sheets; match takes aspects.json away before the
first photograph changes; make and master write new names, then music.json, then remove the old; find reads only
music/source.<ext>; and build/current is replaced whole.

    python3 -I -m unittest discover -s S/tests -p test_indexes.py
"""
import contextlib
import io
import json
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


def tone(out, seconds, hz=440):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ff("-f", "lavfi", "-i", f"sine=frequency={hz}:duration={seconds}", str(out))


class Indexes(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        _env.tools()

    def stopped_replacing(self, module, name):
        """os.replace as `module` calls it, stopped before it moves a file in under `name`."""
        real = os.replace

        def replace(src, dst):
            if Path(dst).name == name:
                raise Stopped
            real(src, dst)

        return mock.patch.object(module.os, "replace", replace)

    def test_a_deliver_stopped_while_the_caption_moves_in_leaves_no_reel_and_the_next_deliver_refuses(self):
        import deliver
        self.delivered_run()
        run = types.SimpleNamespace(spawn=subprocess.run)
        with self.stopped_replacing(deliver, "caption.md"), self.assertRaises(Stopped):
            deliver.deliver(run)
        self.assertTrue(Path("brief.md").exists())
        self.assertFalse(Path("out/film.mp4").exists())
        with self.assertRaises(SystemExit) as refused:
            deliver.deliver(run)
        self.assertIn("film.py render", str(refused.exception))

    def delivered_run(self):
        _env.write_json("library.json", {"handle": "me", "year": 2026})
        _env.write_json("taste.json", {"year": 2026, "people": [{"handle": "ana"}]})
        _env.write_json("winner.json", {"board": "drive", "totals": {"drive": 40}})
        _env.write_json("cards.json", {"cards": [{"handle": "ana", "file": "out/people/01-ana.png"}]})
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the reel render made")
        Path("out/review.html").write_text("the page of the delivered set")

    def test_a_deliver_stopped_once_the_reel_stands_aside_leaves_the_not_ready_page(self):
        import deliver
        self.delivered_run()
        real = os.replace

        def replace(src, dst):
            real(src, dst)
            if Path(src) == Path("out/film.mp4"):
                raise Stopped

        with mock.patch.object(deliver.os, "replace", replace), self.assertRaises(Stopped):
            deliver.deliver(types.SimpleNamespace(spawn=subprocess.run))
        self.assertFalse(Path("out/film.mp4").exists())
        self.assertIn("Not ready to post", Path("out/review.html").read_text())

    def sheets(self, tile):
        """storyboard.sheets over one board with one frame per format, the renderer making each frame and `tile`
        standing in for the tiler; returns what sheets returns."""
        import storyboard
        Path("storyboards/drive").mkdir(parents=True, exist_ok=True)

        def render(jobs, name, run):
            for j in jobs:
                Path(j["out"]).write_bytes(b"a frame")
            return {}

        studio = types.SimpleNamespace(still=lambda board, frame, out, scale: {"out": out}, render=render)
        with mock.patch.object(storyboard, "load", lambda t: {}), mock.patch.object(storyboard.boards, "Ctx", lambda: None), \
                mock.patch.object(storyboard.boards, "layout", lambda sb, ctx, kind: {}), \
                mock.patch.object(storyboard.boards, "roles", lambda board: {"hook": 0}), \
                mock.patch.object(storyboard.boards, "rest_frame", lambda board, i: 0), \
                mock.patch.object(storyboard, "tile", tile), mock.patch.object(storyboard, "looks", lambda: ("drive",)), \
                mock.patch.object(storyboard, "boards_png", lambda styles: Path("out/boards.png")), \
                contextlib.redirect_stdout(io.StringIO()):
            return storyboard.sheets(None, studio, None)

    def test_a_sheets_run_to_its_end_tiles_every_sheet_and_exits_0(self):
        self.assertEqual(self.sheets(lambda run, row, out: out.write_bytes(b"a sheet")), 0)
        self.assertEqual(sorted(p.name for p in Path("storyboards/drive").glob("sheet*.png")),
                         ["sheet-square.png", "sheet-wide.png", "sheet.png"])

    def test_a_sheets_stopped_before_its_last_tile_leaves_no_sheet_png(self):
        def tile(run, row, out):
            if out.name == "sheet-wide.png":
                raise Stopped
            out.write_bytes(b"a sheet")

        with self.assertRaises(Stopped):
            self.sheets(tile)
        self.assertFalse(Path("storyboards/drive/sheet.png").exists())

    def test_a_match_stopped_at_its_second_photograph_leaves_no_aspects_json(self):
        import cast
        for n, c in (("a", "0x996633"), ("b", "0x336699")):
            ff("-f", "lavfi", "-i", f"color=c={c}:s=96x128", "-frames:v", "1", f"{n}.jpg")
        _env.write_json("cast.json", {"people": {"ana": [{"file": "a.jpg"}, {"file": "b.jpg"}]}})
        Path("public/matched").mkdir(parents=True)
        _env.write_json("public/matched/aspects.json", {"ana-0": 1.0, "ana-1": 1.0})
        with self.stopped_replacing(cast, "ana-1.jpg"), self.assertRaises(Stopped), \
                contextlib.redirect_stdout(io.StringIO()):
            cast.cmd_match(types.SimpleNamespace(cast=None))
        self.assertTrue(Path("public/matched/ana-0.jpg").exists())
        self.assertFalse(Path("public/matched/aspects.json").exists())
        import layout
        with self.assertRaises(SystemExit):
            layout.Photos({}, "public")

    def stopped_at_music_json(self):
        write_json = _env.write_json

        def stopped(path, obj):
            if Path(path).name == "music.json":
                raise Stopped
            write_json(path, obj)

        return mock.patch.object(_env, "write_json", stopped)

    def test_a_second_make_stopped_before_music_json_leaves_the_bed_music_json_names(self):
        import music
        out = io.StringIO()
        with mock.patch.object(music.music_engine, "compose", bed()), contextlib.redirect_stdout(out):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=4))
        named = json.loads(Path("music.json").read_text())["file"]
        before = Path(named).read_bytes()
        with mock.patch.object(music.music_engine, "compose", bed(0.5)), self.stopped_at_music_json(), \
                self.assertRaises(Stopped), contextlib.redirect_stdout(out):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=4))
        self.assertEqual(json.loads(Path("music.json").read_text())["file"], named)
        self.assertEqual(Path(named).read_bytes(), before)

    def test_a_second_master_stopped_before_music_json_leaves_the_master_music_json_names(self):
        import music
        tone("music/source.wav", 6)
        _env.write_json("music.json", {"file": "music/source.wav"})
        _env.write_json("film.json", {"seconds": 4})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            music.cmd_master(types.SimpleNamespace(seconds=None))
        named = json.loads(Path("music.json").read_text())["master"]
        before = Path(named).read_bytes()
        with self.stopped_at_music_json(), self.assertRaises(Stopped), contextlib.redirect_stdout(out):
            music.cmd_master(types.SimpleNamespace(seconds=3))
        self.assertEqual(json.loads(Path("music.json").read_text())["master"], named)
        self.assertEqual(Path(named).read_bytes(), before)

    def test_find_takes_a_track_placed_after_make_and_never_a_file_named_past_source(self):
        import music
        with mock.patch.object(music.music_engine, "compose", bed()), contextlib.redirect_stdout(io.StringIO()):
            music.cmd_make(types.SimpleNamespace(bpm=120, seconds=4))
        tone("music/source.0123456789ab.wav", 40)
        tone("music/source.mp3", 40, 330)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_find(types.SimpleNamespace(origin="a track the person placed")), 0)
        self.assertEqual(json.loads(Path("music.json").read_text())["file"], "music/source.mp3")

    def test_a_new_run_stopped_while_it_names_itself_leaves_build_current_naming_the_run_before(self):
        build = self.d / "build"
        (build / "20260101T000000Z").mkdir(parents=True)
        (build / "current").write_text("20260101T000000Z\n")
        real = pathlib.Path.write_text

        def stopped_half_way(path, text, *args, **kwargs):
            if "current" in path.name:
                real(path, text[:3], *args, **kwargs)
                raise Stopped
            return real(path, text, *args, **kwargs)

        with mock.patch.object(pathlib.Path, "write_text", stopped_half_way), self.assertRaises(Stopped):
            _env._new_run(build)
        self.assertEqual((build / "current").read_text(), "20260101T000000Z\n")


if __name__ == "__main__":
    unittest.main()
