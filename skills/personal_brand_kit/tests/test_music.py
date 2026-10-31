"""music.py's music is the picked look's or theirs: a track the person placed as music/source.<ext> wins; else make
composes a bed on the engine from the picked look's recipe, unless their music words name another, and refuses before
a pick; master lays the board's sound cues a full FX_UNDER_BED_LU under the bed."""
import argparse
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import music  # noqa: E402
import music_engine  # noqa: E402

try:
    music_engine.player()
    PLAYER = True
except music_engine.Refusal:
    PLAYER = False

CUES = [{"kind": "hit", "at": a, "weight": 0.5, "beat": "p", "what": "the line comes on"} for a in (2.5, 7.5, 12.5, 17.5)] + \
       [{"kind": "impact", "at": 30.0, "beat": "closer", "what": "the sign-off"}, {"kind": "stop", "at": 33.0, "beat": "closer"}]


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
        _env.write_json("storyboards/a/board-reel.json", {"style": style, "bpm": 120, "beats": [{"id": "hook"}], "sound": CUES})

    def made(self, seconds=4.0):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_make(argparse.Namespace(bpm=None, seconds=seconds)), 0)
        return _env.read_json("music.json")


class Make(InRun):
    def test_make_refuses_before_a_look_is_picked(self):
        with self.assertRaises(SystemExit) as e:
            music.cmd_make(argparse.Namespace(bpm=None, seconds=4.0))
        self.assertIn("vote.py pick", str(e.exception))

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
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.5)


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
