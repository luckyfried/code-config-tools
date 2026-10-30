"""The generated clips (scripts/clips.py): a clip that arrived is conformed to its photograph's size and its beat's
length and placed on that photograph's card from the beat's first frame; a clip that did not arrive stands in, named in
clips.json.

    python3 -m unittest discover -s S/tests        (S = this skill's folder)
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
# the look every board in these tests takes: the first of the trio
STYLE = "cinematic-letterbox"
import _env  # noqa: E402


def ff(*args):
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def picked(run, style=STYLE, bpm=112.5, frames=(150, 150)):
    """A run whose vote picked `style`: its storyboard (tempo, beats, no cues) and winner.json."""
    _env.write_json(run / "storyboards" / style / "storyboard.json",
                    {"style": style, "bpm": bpm, "beats": [{"id": f"b{i}", "frames": f} for i, f in enumerate(frames)], "sound": [], "facts": {}})
    _env.write_json(run / "winner.json", {"board": style})


class Clips(unittest.TestCase):
    def test_an_arrived_clip_is_placed_on_its_card_and_a_missing_one_stands_in(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "photos").mkdir(parents=True)
            (run / "clips").mkdir()
            (run / "storyboards" / STYLE).mkdir(parents=True)
            (Path(d) / "build" / "RUN").write_text("run\n")
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(run / "public/photos/p01.jpg"))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/clip-p04.mp4"))
            clips = [{"id": "clip-p01", "beat": "hook", "role": "hook", "seconds": 2.0, "image": "photos/p01.jpg", "prompt": "p",
                      "stand_in": "the card's own push in"},
                     {"id": "clip-p04", "beat": "p04", "role": "milestone", "seconds": 1.5, "image": "photos/p01.jpg", "prompt": "p",
                      "stand_in": "the camera's lift over the wall"}]
            board = {"style": STYLE, "beats": [{"id": "hook", "frames": 60}, {"id": "p04", "frames": 45}], "clips": clips}
            (run / "storyboards" / STYLE / "storyboard.json").write_text(json.dumps(board))
            (run / "film.json").write_text(json.dumps({"board": STYLE}))
            r = subprocess.run([sys.executable, str(KIT / "scripts/clips.py"), "normalize", "--why", "no video model"], cwd=d,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["clip-p01"]["status"], "photograph")
            self.assertEqual(got["clip-p01"]["stand_in"], "the card's own push in")
            self.assertEqual(got["clip-p04"]["status"], "generated")
            self.assertEqual((got["clip-p04"]["from_frame"], got["clip-p04"]["frames"]), (60, 45))
            frames = sorted((run / "public" / got["clip-p04"]["dir"]).glob("*.jpg"))
            self.assertEqual(len(frames), 45)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(frames[0])],
                                  capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")



class Killed(unittest.TestCase):
    """A command killed while it writes an input a later command reads leaves the old input whole, or none."""

    def setUp(self):
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))).resolve()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.addCleanup(setattr, _env, "B", _env.B)
        _env.B = self.run = d / "run"

    def test_a_normalize_killed_midway_keeps_the_clips_its_index_names(self):
        import clips
        run = self.run
        (run / "public" / "photos").mkdir(parents=True)
        (run / "clips").mkdir()
        ff("-f", "lavfi", "-i", "color=c=0x996633:s=120x160", "-frames:v", "1", str(run / "public/photos/p01.jpg"))
        ff("-f", "lavfi", "-i", "testsrc=s=64x48:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/clip-p04.mp4"))
        board = {"style": STYLE, "beats": [{"id": "p04", "frames": 15}],
                 "clips": [{"id": "clip-p04", "beat": "p04", "role": "milestone", "image": "photos/p01.jpg", "prompt": "p", "stand_in": "s"}]}
        _env.write_json(run / "storyboards" / STYLE / "storyboard.json", board)
        _env.write_json(run / "film.json", {"board": STYLE})
        why = argparse.Namespace(why=None)
        self.assertEqual(clips.cmd_normalize(why), 0)
        first = _env.read_json(run / "clips.json")["clips"]["clip-p04"]["dir"]
        conform = clips.conform

        def killed(src, image, frames, dst):
            raise KeyboardInterrupt
        clips.conform = killed
        self.addCleanup(setattr, clips, "conform", conform)
        with self.assertRaises(KeyboardInterrupt):
            clips.cmd_normalize(why)
        self.assertEqual(_env.read_json(run / "clips.json")["clips"]["clip-p04"]["dir"], first)
        self.assertEqual(len(list((run / "public" / first).glob("*.jpg"))), 15)
        clips.conform = conform
        self.assertEqual(clips.cmd_normalize(why), 0)
        now = _env.read_json(run / "clips.json")["clips"]["clip-p04"]["dir"]
        self.assertEqual(len(list((run / "public" / now).glob("*.jpg"))), 15)
        self.assertEqual([p.name for p in (run / "public" / "clips").iterdir()], [Path(now).parent.name])

    def music_here(self):
        import music
        self.addCleanup(setattr, music, "MUSIC", music.MUSIC)
        music.MUSIC = self.run / "music"
        music.MUSIC.mkdir(parents=True, exist_ok=True)
        picked(self.run)
        return music

    def kill_the_index(self):
        write = _env.write_json
        self.addCleanup(setattr, _env, "write_json", write)

        def killed(path, obj):
            if Path(path).name == "music.json":
                raise KeyboardInterrupt
            return write(path, obj)
        _env.write_json = killed

    def test_a_music_make_killed_while_the_engine_writes_keeps_the_old_track(self):
        music = self.music_here()
        src = music.MUSIC / "source.wav"
        src.write_bytes(b"the old track")
        _env.write_json(self.run / "music.json", {"file": str(src)})
        real = music.music_engine.compose
        self.addCleanup(setattr, music.music_engine, "compose", real)

        def half(*args, out, **kw):
            out.mkdir(parents=True)
            (out / "bed.wav").write_bytes(b"half a bed")
            raise KeyboardInterrupt
        music.music_engine.compose = half
        with self.assertRaises(KeyboardInterrupt):
            music.cmd_make(argparse.Namespace(bpm=None, seconds=2.0))
        self.assertEqual(src.read_bytes(), b"the old track")
        self.assertEqual(_env.read_json(self.run / "music.json")["file"], str(src))
        self.assertEqual(_env.read_json(self.run / "music.json")["file"], str(src))
        self.assertEqual(sorted(p.name for p in src.parent.iterdir() if not p.name.startswith("bed.")), ["source.wav"])

    def test_a_second_make_killed_before_its_index_keeps_the_track_the_index_names(self):
        music = self.music_here()
        self.assertEqual(music.cmd_make(argparse.Namespace(bpm=None, seconds=2.0)), 0)
        named = _env.read_json(self.run / "music.json")["file"]
        first = Path(named).read_bytes()
        self.kill_the_index()
        with self.assertRaises(KeyboardInterrupt):
            music.cmd_make(argparse.Namespace(bpm=None, seconds=3.0))
        self.assertEqual(_env.read_json(self.run / "music.json")["file"], named)
        self.assertEqual(Path(named).read_bytes(), first)

    def test_find_takes_a_track_placed_after_a_make(self):
        music = self.music_here()
        self.assertEqual(music.cmd_make(argparse.Namespace(bpm=None, seconds=2.0)), 0)
        placed = music.MUSIC / "source.mp3"
        ff("-f", "lavfi", "-i", "sine=frequency=330:duration=2", str(placed))
        self.assertEqual(music.cmd_find(argparse.Namespace(origin="their own track")), 0)
        self.assertEqual(_env.read_json(self.run / "music.json")["file"], str(placed))

    def test_a_master_killed_before_its_index_leaves_the_mux_the_master_the_index_names(self):
        import film
        music = self.music_here()
        src = music.MUSIC / "source.wav"
        ff("-f", "lavfi", "-i", "sine=frequency=220:duration=3", str(src))
        _env.write_json(self.run / "music.json", {"file": str(src)})
        _env.write_json(self.run / "film.json", {"seconds": 2.0})
        self.assertEqual(music.cmd_master(argparse.Namespace(seconds=None)), 0)
        first = sorted(music.MUSIC.glob("master*"))[0].read_bytes()
        self.kill_the_index()
        with self.assertRaises(KeyboardInterrupt):
            music.cmd_master(argparse.Namespace(seconds=1.0))
        seen = []

        class Run:
            def spawn(self, cmd, **kw):
                seen.append(cmd)
        film.mux(Run(), self.run / "silent.mp4", self.run / "film.mp4", 2.0)
        inputs = [seen[0][i + 1] for i, x in enumerate(seen[0]) if x == "-i"]
        self.assertEqual(len(inputs), 2, seen[0])
        self.assertEqual(Path(inputs[1]).read_bytes(), first)

    def test_a_music_make_killed_before_its_index_keeps_the_track_the_index_names(self):
        import music
        src = self.run / "music" / "source.mp3"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"their own track")
        _env.write_json(self.run / "music.json", {"file": str(src)})
        self.addCleanup(setattr, music, "MUSIC", music.MUSIC)
        self.addCleanup(setattr, _env, "write_json", _env.write_json)
        music.MUSIC = src.parent
        picked(self.run)

        def killed(path, obj):
            raise KeyboardInterrupt
        _env.write_json = killed
        with self.assertRaises(KeyboardInterrupt):
            music.cmd_make(argparse.Namespace(bpm=None, seconds=2.0))
        self.assertEqual(src.read_bytes(), b"their own track")



class Music(unittest.TestCase):
    """The film's music: a track the person placed wins, else a bed composed from the picked look's recipe at its board's
    tempo."""

    def setUp(self):
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))).resolve()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.addCleanup(setattr, _env, "B", _env.B)
        _env.B = self.run = d / "run"
        import music
        self.addCleanup(setattr, music, "MUSIC", music.MUSIC)
        music.MUSIC = self.run / "music"
        music.MUSIC.mkdir(parents=True)
        picked(self.run)
        self.music = music

    def brief(self, music=None):
        _env.write_json(self.run / "taste.json", {"handle": "maren.okafor", **({"music": music} if music else {})})

    def test_two_looks_compose_two_different_beds_each_at_its_boards_tempo(self):
        made = []
        for style, bpm in ((STYLE, 72.0), ("kinetic-type", 120.0)):
            picked(self.run, style, bpm)
            self.brief()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(self.music.cmd_make(argparse.Namespace(bpm=None, seconds=2.0)), 0)
            info = _env.read_json(self.run / "music.json")
            made.append((info["bpm"], info["board"], info["origin"], Path(info["file"]).read_bytes()))
        (a_bpm, a_board, a_origin, a_bed), (b_bpm, b_board, b_origin, b_bed) = made
        self.assertEqual((a_bpm, b_bpm), (72.0, 120.0))
        self.assertEqual((a_board, b_board), (STYLE, "kinetic-type"))
        self.assertIn(f"chosen by the {STYLE} look", a_origin)
        self.assertIn("chosen by the kinetic-type look", b_origin)
        self.assertNotEqual(a_bed, b_bed)

    def test_find_with_no_placed_track_composes_a_bed_as_long_as_the_board_needs(self):
        self.brief({"styles": ["felt piano arpeggios"], "avoid": []})
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.music.cmd_find(argparse.Namespace(origin=None, bpm=None, seconds=None)), 0)
        info = _env.read_json(self.run / "music.json")
        self.assertTrue(info["origin"].startswith("composed by music.py from the "), info["origin"])
        # the board's 10 s and four seconds to fade
        self.assertEqual(info["seconds"], 14.0)
        self.assertRegex(info["file"], r"/bed\.[0-9-]+/bed\.wav$")

    def test_master_states_the_cut_s_length_at_the_tempo_the_music_plays_in_the_film(self):
        board = {"style": STYLE, "bpm": 112.5, "beats": [{"id": "hook", "frames": 150}, {"id": "closer", "frames": 150}],
                 "sound": [{"kind": "hit", "at": 0.3, "beat": "hook", "what": "day one lands"},
                           {"kind": "stop", "at": 20.0, "beat": "closer", "what": "picture and music stop together"}]}
        _env.write_json(self.run / "storyboards" / STYLE / "storyboard.json", board)
        md = self.run / "storyboards" / STYLE / "storyboard.md"
        src = self.music.MUSIC / "source.wav"
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=14", str(src)], check=True)
        # the film's beats are the board's, whatever tempo the track came at, and the cut's length is the film's
        for track, tempo, head in ((100, 1.125, "2 beats at 112.5 bpm, 12.0 s; picture and music stop together at beat 20.00 and"),
                                   (160, 1.0, "2 beats at 112.5 bpm, 12.0 s; picture and music stop together at beat 20.00 and")):
            md.write_text("# drive\n\n2 beats at 112.5 bpm, 10.0 s; picture and music stop together at beat 20.00 and the wall "
                          "holds silent to the end.\n\nMusic: not yet.\nMixed: not yet.\n")
            _env.write_json(self.run / "music.json", {"file": str(src), "origin": "made by the test", "bpm": track})
            _env.write_json(self.run / "film.json", {"board": STYLE, "seconds": 12.0, "bpm": 112.5, "music_start": 0.0, "tempo": tempo})
            with redirect_stdout(io.StringIO()):
                self.assertEqual(self.music.cmd_master(argparse.Namespace(seconds=None)), 0)
            lines = md.read_text().splitlines()
            self.assertTrue(lines[2].startswith(head), lines[2])
            self.assertEqual(lines[4], "Music: made by the test.")
            self.assertTrue(lines[5].startswith("Mixed: bed "), lines[5])

    def test_a_track_the_person_placed_wins_over_the_brief(self):
        self.brief({"mood": "calm", "tempo": 96})
        placed = self.music.MUSIC / "source.wav"
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(placed)], check=True)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.music.cmd_find(argparse.Namespace(origin="their own track", bpm=None, seconds=None)), 0)
        info = _env.read_json(self.run / "music.json")
        self.assertEqual((info["file"], info["origin"]), (str(placed), "their own track"))
        self.assertEqual(sorted(self.music.MUSIC.glob("source.*")), [placed])


if __name__ == "__main__":
    unittest.main()
