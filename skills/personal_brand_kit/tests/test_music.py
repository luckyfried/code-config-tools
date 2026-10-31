"""music.py's music is the picked look's or theirs: a track the person placed as music/source.<ext> wins; else make
composes a bed on the engine from the picked look's recipe, unless their music words name another, and refuses before
a pick; master cuts the bed on the board's stop, brings it to -14 LUFS by one gain in 32-bit float, measures the shared
effects a full FX_UNDER_BED_LU under it, and writes the music's energy one number a frame; every film film.py makes is
mixed and mastered by the shared mux (sfx.mux)."""
import argparse
import inspect
import io
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import film  # noqa: E402
import music  # noqa: E402
import music_engine  # noqa: E402

try:
    music_engine.player()
    PLAYER = True
except music_engine.Refusal:
    PLAYER = False

# a picked look's board: the title, two photographs and the sign-off, with the music stopping on the held sign-off
BEATS = [{"id": "hook", "form": "title", "start": 0, "beats": 6, "move": "white-space-crop", "transition": None,
          "say": "slow mornings", "text": {"at": 0.5, "enter": "rise"}},
         {"id": "m1", "form": "photo", "start": 6, "beats": 10, "move": "slow-push", "transition": "dissolve", "say": "the harbour"},
         {"id": "m2", "form": "photo", "start": 16, "beats": 14, "move": "exploded-layers", "transition": "dissolve", "say": "at dawn"},
         {"id": "closer", "form": "closer", "start": 30, "beats": 6, "move": "breath-hold", "transition": "dissolve", "say": "see you"}]
CUES = [{"kind": "stop", "at": 33.0, "beat": "closer", "what": "the music stops on the sign-off"}]


class InRun(unittest.TestCase):
    """Each test in a scratch run of its own, as the working folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.here = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.here)
        self.tmp.cleanup()

    def picked(self, style, words=(), avoid=()):
        _env.write_json("taste.json", {"handle": "maren.okafor", "music": {"words": list(words), "avoid": list(avoid)}})
        _env.write_json("winner.json", {"board": "a"})
        _env.write_json("storyboards/a/board-reel.json", {"id": "a-reel", "style": style, "bpm": 120, "fps": 30, "beats": BEATS,
                                                         "closer": {"at": 30, "still": 33}, "sound": CUES})

    def made(self, seconds=4.0):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_make(argparse.Namespace(bpm=None, seconds=seconds)), 0)
        return _env.read_json("music.json")


class Make(InRun):
    def test_make_refuses_before_a_look_is_picked(self):
        with self.assertRaises(SystemExit) as e:
            music.cmd_make(argparse.Namespace(bpm=None, seconds=4.0))
        self.assertIn("vote.py pick", str(e.exception))

    def test_the_bed_lifts_into_the_peak_beat(self):
        board = {"bpm": 120, "beats": [dict(b, peak=b["id"] == "m2") for b in BEATS]}
        self.assertEqual(music.peak(board, 120), (8.0, 15.0))
        self.assertEqual(music.peak(board, 60), (8.0, 15.0), "a bed at half the board's tempo lifts on the same seconds of the picture")
        self.assertIsNone(music.peak({"bpm": 120, "beats": BEATS}, 120))
        self.picked("swiss-grid")
        asked = {}
        def compose(*a, **kw):
            asked.update(kw)
            raise SystemExit("asked")
        with mock.patch.object(music.music_engine, "compose", compose), mock.patch.object(music, "peak", lambda b, bpm: (8.0, 15.0)), \
                self.assertRaises(SystemExit):
            music.cmd_make(argparse.Namespace(bpm=None, seconds=4.0))
        self.assertEqual(asked["peak"], (8.0, 15.0))

    @unittest.skipUnless(PLAYER, "no instrument player for this python")
    def test_the_bed_is_the_picked_looks_recipe(self):
        self.picked("swiss-grid")
        info = self.made()
        self.assertEqual(info["recipe"], "swiss-grid")
        self.assertIn("(chosen by the look)", info["origin"])
        self.assertEqual(info["file"], "music/bed.wav")

    @unittest.skipUnless(PLAYER, "no instrument player for this python")
    def test_their_music_words_name_another_recipe_and_their_avoid_takes_an_instrument_out(self):
        self.picked("kinetic-type", words=["soft piano"], avoid=["pads"])
        info = self.made()
        self.assertEqual(info["recipe"], "editorial-quiet")
        self.assertIn("(chosen by their words)", info["origin"])
        self.assertIn("without", info["origin"])


@unittest.skipUnless(PLAYER, "no instrument player for this python")
class Master(InRun):
    def test_the_effects_sit_a_full_eight_lu_under_the_bed_as_the_gate_reads_them(self):
        self.picked("editorial-quiet")
        _env.write_json("film.json", {"seconds": 34.0, "music_start": 0, "boards": {"reel": "storyboards/a/board-reel.json"}})
        self.made(seconds=38.0)
        with redirect_stdout(io.StringIO()):
            music.cmd_master(argparse.Namespace(seconds=None))
        info = _env.read_json("music.json")
        self.assertGreaterEqual(round(info["bed_lufs"] - info["fx_lufs"], 1), music.FX_UNDER_BED_LU, info)
        # the master alone comes to the target; the film's mux masters it and the effects together
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        self.assertNotIn("film_lufs", info)
        self.assertGreater(info["sound_cues"], 4)
        energy = _env.read_json("music/energy.json")
        self.assertEqual((energy["fps"], len(energy["rms"])), (30, 34 * 30))

    def test_the_sections_turn_where_the_film_lands_on_its_sign_off(self):
        self.assertEqual(music.edges({"bpm": 120, "closer": {"at": 30}}, 120), [15.0])
        self.assertEqual(music.edges({"bpm": 120, "closer": {"at": 30}}, 60), [15.0])
        self.assertEqual(music.edges({"bpm": 120}, 120), [])


class OneGain(InRun):
    def test_a_peaky_bed_reaches_the_target_by_one_gain_and_keeps_its_peaks_whole(self):
        """Sharp clicks over a quiet bed need peaks past full scale to reach -14 LUFS: the master is written in float and
        keeps them, so the film's one limiter (sfx.py) is the only thing that touches them."""
        ff = _env.ffmpeg()
        music.MUSIC.mkdir()
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "anoisesrc=d=6:c=pink:a=0.01", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(mod(t,0.25),0.004),0.9,0)':d=6:s=48000", "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", "music/source.wav"], check=True)
        _env.write_json("music.json", {"file": "music/source.wav", "bpm": 120, "downbeats": [0, 2, 4]})
        _env.write_json("film.json", {"seconds": 6.0, "music_start": 0.0})
        with redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_master(argparse.Namespace(seconds=None)), 0)
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        # astats reads the float samples as they are; volumedetect converts to 16-bit and clips
        said = subprocess.run([ff, "-hide_banner", "-nostats", "-i", info["master"], "-af", "astats=measure_perchannel=none", "-f", "null",
                               "-"], capture_output=True, text=True).stderr
        peak = float(re.findall(r"Peak level dB: (-?[\d.]+)", said)[-1])
        self.assertGreater(peak, 0.0, "the clicks stand past full scale in the float master, unclipped")


class FilmMux(InRun):
    def test_every_film_is_mixed_and_mastered_by_the_shared_mux(self):
        """film.py has no encode of its own: every film takes its board's effects and the master through sfx.mux, which
        masters the whole mix once and encodes it."""
        self.assertIs(inspect.signature(film.mux).parameters["board"].default, inspect.Parameter.empty,
                      "a film without a board would be encoded outside sfx.mux")
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav"})
        calls = []
        run = types.SimpleNamespace(spawn=lambda *a, **k: None)
        with mock.patch.object(film.sfx, "mux", lambda *a: calls.append(a) or True), \
                mock.patch.object(film.storyboard, "effects_board", lambda b: {"effects of": b["id"]}):
            self.assertTrue(film.mux(run, "render/silent/cut.mp4", "cut.mp4", 12.0, {"id": "a-reel"}))
        self.assertEqual(calls, [(run.spawn, "render/silent/cut.mp4", "cut.mp4", 12.0, {"effects of": "a-reel"},
                                  {"file": "music/source.wav", "master": "music/master.wav"}, _env.ffmpeg())])


class Find(InRun):
    def test_a_track_the_person_placed_wins(self):
        self.picked("kinetic-type")
        music.MUSIC.mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=2", "music/source.wav"], check=True)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_find(argparse.Namespace(origin=None, bpm=None, seconds=4.0)), 0)
        info = _env.read_json("music.json")
        self.assertEqual((info["file"], info["origin"]), ("music/source.wav", "placed by the agent in music/"))
        self.assertAlmostEqual(info["seconds"], 2.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
