"""The film's music is the person's: a placed track wins, else a bed composed for the winning look; and the effects sit
under it. music.py find never makes over a placed track; with nothing placed it composes the look's recipe at the
board's tempo, for the film's length, through music_engine.compose (the kit synthesizes nothing of its own); the brief's
words choose another recipe; analyze keeps a composed bed's own grid; master brings the music alone to -14 LUFS by one gain, in float, writes its
loudness to music.json and the storyboard's `Mixed:` line, writes the cut's storyboard.md again at the music's tempo and the film's
length, and lays no key.

    python3 -I -m unittest discover -s S/tests -p test_music.py
"""
import argparse
import contextlib
import io
import os
import re
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
        """The cut: a three-second film of three beats at 120 bpm with three effects, over a quiet four-second bed, and the
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
                                      "sound": [{"kind": "impact", "at": 1.0, "beat": "hook", "what": "the trip's name lands"},
                                                {"kind": "bright", "at": 4.0, "beat": "stop-2", "what": "the cut whooshes"},
                                                {"kind": "impact", "at": 3.5, "beat": "closer", "what": "the closer opens"},
                                                {"kind": "stop", "at": 5.0, "beat": "closer", "what": "the picture and the music stop together"}]})
        _env.write_text("storyboards/1/storyboard.md", "# the board\n\nMusic: none yet (music.py make).\nMixed: not yet; music.py master writes the "
                        "bed's and the effects' loudness here.\n\n3 beats on 3 bars at 83 bpm; 2 stops, Bolzano to Braies.\n")

    def quiet(self):
        return contextlib.redirect_stdout(io.StringIO())

    def composed(self):
        """music_engine.compose, recorded: the arguments of each call, and the music.json fields a bed carries."""
        calls = []

        def compose(style, styles, avoid, seconds, edges, hue, seed, bpm=None, target_bpm=None, out=None, peak=None):
            calls.append({"style": style, "styles": styles, "avoid": avoid, "seconds": seconds, "bpm": bpm, "peak": peak})
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

    def test_the_bed_lifts_into_the_peak_stop_from_where_its_photograph_lands(self):
        _env.write_json("winner.json", {"board": "1"})
        _env.write_json("storyboards/1/storyboard.json", {"id": "1", "style": "analog-home-movie", "bpm": 80, "beats": [
            {"id": "hook", "bars": 2}, {"id": "stop-2", "bars": 2}, {"id": "stop-3", "bars": 2.25, "peak": True, "fly": 1.1},
            {"id": "closer", "bars": 1.5}]})
        calls, compose = self.composed()
        with mock.patch.object(music.music_engine, "compose", compose), \
                mock.patch.object(music.music_engine, "tempo", lambda *a: 80.0), self.quiet():
            music.cmd_make(argparse.Namespace(bpm=None, seconds=30))
        land, end = calls[0]["peak"]
        self.assertAlmostEqual(land, 16 * 60 / 80 + 1.1)
        self.assertAlmostEqual(end, 25 * 60 / 80)

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

    def test_the_master_is_the_music_alone_with_its_energy_a_frame_and_says_so(self):
        """Real ffmpeg: a quiet four-second bed under a three-beat cut at 120 bpm; master brings the music alone to
        -14 LUFS (the effects are laid at render, sfx.py), writes its energy a frame beside it, and states both in
        music.json and the storyboard's Mixed line."""
        self.film()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            music.cmd_master(argparse.Namespace(seconds=None))
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], -14.0, delta=1.0)
        self.assertNotIn("fx_lufs", info)
        self.assertEqual(sorted(p.name for p in music.MUSIC.iterdir()), ["bed-cut.wav", "energy.json", "master.wav", "source.wav"])
        energy = _env.read_json("music/energy.json")
        self.assertEqual(energy["fps"], 30)
        self.assertAlmostEqual(len(energy["rms"]), 3.0 * 30, delta=2)
        self.assertTrue(all(0 <= r <= 1 for r in energy["rms"]))
        self.assertIn("the effects are laid under it as the film renders (sfx.py)", out.getvalue())
        md = Path("storyboards/1/storyboard.md").read_text()
        self.assertIn(f"Mixed: the music mastered to {info['master_lufs']} LUFS; 3 effects over 3 beats", md)
        self.assertIn("Music: none yet (music.py make).", md, "the origin line is find's and stays as it left it")

    def test_a_peaky_track_reaches_the_target_by_one_gain_and_keeps_its_peaks_whole(self):
        """Real ffmpeg: sharp clicks over a quiet bed need peaks past full scale to reach -14 LUFS. master reads the
        loudness once and sets one gain, with no limiter, and writes the master in 32-bit float, so the clicks stand past
        full scale unclipped and the film's mux (sfx.py) is the only thing that limits them."""
        self.film()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=4:c=pink:a=0.01", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(mod(t,0.25),0.004),0.9,0)':d=4:s=48000", "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", "music/source.wav"], check=True)
        calls, real = [], subprocess.run

        def run(argv, **kw):
            calls.append([str(x) for x in argv])
            return real(argv, **kw)
        with mock.patch.object(music.subprocess, "run", run), self.quiet():
            music.cmd_master(argparse.Namespace(seconds=None))
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        self.assertFalse([c for c in calls if any("alimiter" in x for x in c)], "no limiter in the master")
        written = next(i for i, c in enumerate(calls) if "master" in Path(c[-1]).name)
        self.assertEqual(sum("ebur128" in " ".join(c) for c in calls[:written]), 1, "one loudness read, then one gain")
        self.assertEqual(calls[written][-3:-1], ["-c:a", "pcm_f32le"])
        said = real(["ffmpeg", "-hide_banner", "-nostats", "-i", info["master"], "-af", "astats=measure_perchannel=none", "-f", "null",
                     "-"], capture_output=True, text=True).stderr
        self.assertGreater(float(re.findall(r"Peak level dB: (-?[\d.]+)", said)[-1]), 0.0,
                           "the clicks stand past full scale in the float master, unclipped")

    def test_master_states_the_films_length_at_the_musics_tempo_in_the_storyboard(self):
        """Real ffmpeg: the winning board was drafted at its look's 83 bpm; the cut runs at the music's 120 bpm for 3.0 s,
        and after master its storyboard.md says so on the spans line, with the Music and Mixed lines in the same pass."""
        self.film()
        with self.quiet():
            music.cmd_master(argparse.Namespace(seconds=None))
        md = Path("storyboards/1/storyboard.md").read_text()
        self.assertIn("3 beats on 3 bars at 120 bpm, 3.0 s; 2 stops, Bolzano to Braies.", md)
        self.assertNotIn("83 bpm", md)
        self.assertIn("| 5 | stop | the picture and the music stop together |", md, "the cut's sounds, not the draft's")


if __name__ == "__main__":
    unittest.main()
