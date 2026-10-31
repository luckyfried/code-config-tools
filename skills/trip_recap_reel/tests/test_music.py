"""The film's music is the person's: a placed track wins, else a bed composed for the winning look; and the effects sit
under it. music.py find never makes over a placed track; with nothing placed it composes the look's recipe at the
board's tempo, for the film's length, through music_engine.compose (the kit synthesizes nothing of its own); the brief's
words choose another recipe; analyze keeps a composed bed's own grid; master scales the effects stem by loudness to FX_UNDER_BED_LU under the bed, writes both numbers to
music.json and the storyboard's `Mixed:` line, writes the cut's storyboard.md again at the music's tempo and the film's
length, and lays no key.

    python3 -I -m unittest discover -s S/tests -p test_music.py
"""
import argparse
import contextlib
import io
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
import music  # noqa: E402

TOOLS = {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
FIND = argparse.Namespace(origin=None, bpm=None, seconds=None)


def made_by_ffmpeg(argv, **kw):
    """ffmpeg writing the file it is asked for."""
    Path(argv[-1]).write_bytes(b"wav")
    return subprocess.CompletedProcess(argv, 0, "", "")


class Music(unittest.TestCase):
    def setUp(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.run_dir = home / "build" / "r1"
        self.run_dir.mkdir(parents=True)
        (home / "build" / "RUN").write_text("r1\n")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.run_dir)
        for patch in (mock.patch.object(_env, "HOME", home), mock.patch.object(_env, "_TOOLS", dict(TOOLS))):
            patch.start()
            self.addCleanup(patch.stop)

    def board(self, bars=6):
        """The board that won the vote, `bars` long."""
        _env.write_json("winner.json", {"board": "1"})
        _env.write_json("storyboards/1/storyboard.json", {"id": "1", "style": "analog-home-movie", "bpm": 83, "beats": [{"id": "hook", "bars": 1}, {"id": "closer", "bars": bars - 1}]})

    def film(self):
        """The cut: a three-second film of three beats at 120 bpm with four cues, over a quiet four-second bed, and the
        winning board's storyboard.md as draft left it, at the board's tempo."""
        self.board(bars=3)
        music.MUSIC.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=4", "-af", "volume=-18dB", "-ar", "48000", "music/source.wav"], check=True)
        _env.write_json("music.json", {"file": "music/source.wav"})
        stops = [{"name": "Bolzano", "city": "Bolzano", "date": "tue 2 jun", "photo": "a.jpg", "leg": 0, "compass": None, "caption": "window seat"},
                 {"name": "Braies", "city": "Braies", "date": "wed 3 jun", "photo": "b.jpg", "leg": 41.2, "compass": "east", "caption": "rowing out"}]
        _env.write_json("film.json", {"id": "1", "name": "Bolzano to Braies · Analog home movie", "look": "Analog home movie",
                                      "style": "analog-home-movie", "sentence": "Home movie.", "idea": "The trip, stop by stop.",
                                      "seconds": 3.0, "bpm": 120, "music_offset": 0, "route": {"stops": stops}, "clips": [],
                                      "system": {"closer": "closing-flicker"},
                                      "beats": [{"id": "hook", "bars": 1, "move": "slow-push", "anchor": "middle", "shows": "Bolzano"},
                                                {"id": "stop-2", "bars": 1, "move": "drift", "transition": "flash-frame", "anchor": "bottom", "shows": "Braies"},
                                                {"id": "closer", "bars": 1, "transition": "fade", "anchor": "middle", "shows": "the closing line"}],
                                      "sound": [{"kind": "hit", "at": 0.0, "beat": "hook", "what": "the first photograph opens", "weight": 0.8},
                                                {"kind": "hit", "at": 2.0, "beat": "stop-2", "what": "the cut lands", "weight": 0.65, "bright": 0.5},
                                                {"kind": "impact", "at": 3.5, "beat": "closer", "what": "the closing line settles"},
                                                {"kind": "stop", "at": 5.0, "beat": "closer", "what": "the picture and the music stop together"}]})
        _env.write_text("storyboards/1/storyboard.md", "# the board\n\nMusic: none yet (music.py make).\nMixed: not yet; music.py master writes the "
                        "bed's and the effects' loudness here.\n\n3 beats on 3 bars at 83 bpm; 2 stops, Bolzano to Braies.\n")

    def quiet(self):
        return contextlib.redirect_stdout(io.StringIO())

    def composed(self):
        """music_engine.compose, recorded: the arguments of each call, and the music.json fields a bed carries."""
        calls = []

        def compose(style, styles, avoid, seconds, edges, hue, seed, bpm=None, target_bpm=None, out=None):
            calls.append({"style": style, "styles": styles, "avoid": avoid, "seconds": seconds, "bpm": bpm})
            return {"recipe": style or "default", "key": "A minor", "bpm": bpm, "seconds": seconds, "beats": [0.0],
                    "downbeats": [0.0], "sections": [], "chords": ["Am"], "programs": [], "removed": [], "fx": {}, "fx_recipe": style}
        return calls, compose

    def test_find_with_nothing_placed_composes_the_winning_looks_recipe_for_the_films_length(self):
        self.board(bars=6)
        _env.write_json("taste.json", {"handle": "mara", "music": {"mood": "film", "tempo": None, "styles": [], "avoid": ["vocals"]}})
        calls, compose = self.composed()
        with mock.patch.object(music.music_engine, "compose", compose), self.quiet():
            self.assertEqual(music.cmd_find(FIND), 0)
        recipe = _env.read_json(KIT / "styles" / "analog-home-movie.json")["music"]
        self.assertEqual([(c["style"], c["avoid"]) for c in calls], [(recipe, ["vocals"])])
        bpm = calls[0]["bpm"]
        # six bars of the board at the bed's tempo, and four seconds past them
        self.assertAlmostEqual(calls[0]["seconds"], 6 * 240 / bpm + 4, places=3)
        info = _env.read_json("music.json")
        self.assertEqual((info["file"], info["recipe"]), ("music/bed.wav", recipe))
        self.assertTrue(info["origin"].startswith(f"made by music.py from the {recipe} recipe"), info["origin"])
        self.assertIn("chosen by the look", info["origin"])

    def test_the_brief_words_choose_another_recipe(self):
        self.board(bars=6)
        book = music.music_engine.recipes()
        look = _env.read_json(KIT / "styles" / "analog-home-movie.json")["music"]
        other = next(r for r in book["recipes"] if r != look)
        words = [book["recipes"][other]["name"]]
        _env.write_json("taste.json", {"handle": "mara", "music": {"styles": words, "avoid": []}})
        rid, _, _ = music.music_engine.resolve(book, look, words, [])
        calls, compose = self.composed()
        with mock.patch.object(music.music_engine, "compose", compose), self.quiet():
            music.cmd_make(argparse.Namespace(bpm=None, seconds=4))
        self.assertEqual(rid, other, "the recipe's own name in the brief chooses it")
        self.assertIn("chosen by their brief", _env.read_json("music.json")["origin"])

    def test_analyze_keeps_a_composed_beds_own_grid(self):
        music.MUSIC.mkdir()
        made = {"file": "music/bed.wav", "recipe": "r", "bpm": 83, "beats": [0.0, 0.723], "downbeats": [0.0]}
        _env.write_json("music.json", made)
        with mock.patch.object(music.subprocess, "run", side_effect=AssertionError("a composed bed analyzed")), self.quiet():
            self.assertEqual(music.cmd_analyze(FIND), 0)
        self.assertEqual(_env.read_json("music.json"), made)

    def test_the_kit_synthesizes_no_music_of_its_own(self):
        for name in ("MOODS", "synth", "Stereo", "hit", "riser", "impact", "score"):
            self.assertFalse(hasattr(music, name), f"music.py still has {name}")

    def test_find_keeps_a_placed_track_and_never_makes_over_it(self):
        music.MUSIC.mkdir()
        (music.MUSIC / "source.mp3").write_bytes(b"the track they chose")
        with mock.patch.object(music.music_engine, "compose", side_effect=AssertionError("a bed made over a placed track")), \
                mock.patch.object(music, "has_audio", lambda f: True), mock.patch.object(music, "duration", lambda f: 60.0), self.quiet():
            self.assertEqual(music.cmd_find(argparse.Namespace(origin="their own library", bpm=None, seconds=None)), 0)
        self.assertEqual(_env.read_json("music.json"), {"file": "music/source.mp3", "origin": "their own library", "seconds": 60.0})

    def test_the_effects_sit_eight_lu_under_the_bed_and_the_master_says_so(self):
        """Real ffmpeg: a quiet four-second bed, four cues over three beats at 120 bpm; the effects stem lands
        FX_UNDER_BED_LU under the bed's loudness, both numbers reach music.json and the storyboard, no key is laid."""
        self.film()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            music.cmd_master(argparse.Namespace(seconds=None))
        info = _env.read_json("music.json")
        under = info["bed_lufs"] - info["fx_lufs"]
        self.assertAlmostEqual(under, music.FX_UNDER_BED_LU, delta=0.6, msg=f"bed {info['bed_lufs']}, effects {info['fx_lufs']}")
        self.assertAlmostEqual(music.integrated_file("music/fx.wav"), info["fx_lufs"], delta=0.1)
        self.assertAlmostEqual(music.integrated_file("music/bed-cut.wav"), info["bed_lufs"], delta=0.1)
        self.assertAlmostEqual(info["master_lufs"], -14.0, delta=1.0)
        self.assertEqual(sorted(p.name for p in music.MUSIC.iterdir()), ["bed-cut.wav", "fx", "fx.wav", "master.wav", "mix.wav", "source.wav"])
        said = f"bed {info['bed_lufs']} LUFS, effects {info['fx_lufs']} LUFS, {under:.1f} LU under; 4 sound cues over 3 beats"
        self.assertIn(said, out.getvalue())
        md = Path("storyboards/1/storyboard.md").read_text()
        self.assertIn(f"Mixed: {said}.", md)
        self.assertIn("Music: none yet (music.py make).", md, "the origin line is find's and stays as it left it")

    def test_master_states_the_films_length_at_the_musics_tempo_in_the_storyboard(self):
        """Real ffmpeg: the winning board was drafted at its look's 83 bpm; the cut runs at the music's 120 bpm for 3.0 s,
        and after master its storyboard.md says so on the spans line, with the Music and Mixed lines in the same pass."""
        self.film()
        with self.quiet():
            music.cmd_master(argparse.Namespace(seconds=None))
        md = Path("storyboards/1/storyboard.md").read_text()
        self.assertIn("3 beats on 3 bars at 120 bpm, 3.0 s; 2 stops, Bolzano to Braies.", md)
        self.assertNotIn("83 bpm", md)
        self.assertIn("| 5 | stop | the picture and the music stop together |", md, "the cut's cues, not the draft's")


if __name__ == "__main__":
    unittest.main()
