"""The film's sound: one cue where each beat lands and the few the story's shape asks for; the effects stem 8 LU under
the person's music, read back by the gate; and the bed music.py makes through the music engine from the picked look's
recipe, or the one their music brief's words name, with the effects played on its own instruments.

    python3 -I -m unittest discover -s S/tests -p test_audio.py
"""
import json
import os
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
import look  # noqa: E402
import music  # noqa: E402
import music_engine  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())


class InARun(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)

    @staticmethod
    def put(path, obj):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(obj if isinstance(obj, str) else json.dumps(obj))


class Cues(unittest.TestCase):
    def test_a_cue_where_each_beat_lands_and_only_the_shapes_few_besides(self):
        b = storyboard.plan(SOURCE, "reel", None)["board"]
        kinds = [c["kind"] for c in b["sound"]]
        self.assertLessEqual(len(kinds), len(b["beats"]) + 4, kinds)
        self.assertLessEqual(set(kinds), {"hit", "riser", "impact", "stop"})
        self.assertEqual((kinds.count("riser"), kinds.count("stop")), (1, 1))
        for x in b["beats"]:
            self.assertTrue(any(c["beat"] == x["id"] for c in b["sound"]), x["id"])


class Mix(InARun):
    def test_master_sets_the_effects_eight_lu_under_the_bed_and_says_so(self):
        # a quiet bed: the effects peak-normalized over it would sit above it
        os.makedirs("music")
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=4", "-af", "volume=-24dB",
                        "music/quiet.wav"], check=True)
        beats = [{"id": "hook"}, {"id": "s01"}, {"id": "closer"}]
        self.put("storyboards/drive/board-reel.json", {"bpm": 120, "beats": beats})
        self.put("storyboards/drive/storyboard.md", "# drive\n\nMixed: not yet.\n")
        cues = [{"kind": "hit", "at": 0.5, "beat": "hook", "what": "a", "weight": 0.9},
                {"kind": "impact", "at": 2.0, "beat": "s01", "what": "b"},
                {"kind": "hit", "at": 5.0, "beat": "closer", "what": "c", "weight": 0.8},
                {"kind": "stop", "at": 5.0, "beat": "closer", "what": "d"}]
        self.put("film.json", {"seconds": 3.5, "bpm": 120, "sound": cues, "boards": {"reel": "storyboards/drive/board-reel.json"}})
        self.put("music.json", {"file": "music/quiet.wav"})
        self.assertEqual(music.cmd_master(types.SimpleNamespace(seconds=None)), 0)
        info = json.loads(Path("music.json").read_text())
        bed, fx = music.integrated_file("music/bed.wav"), music.integrated_file("music/fx.wav")
        self.assertAlmostEqual(bed - fx, music.FX_UNDER_BED_LU, delta=0.5)
        self.assertAlmostEqual(info["bed_lufs"] - info["fx_lufs"], music.FX_UNDER_BED_LU, delta=0.3)
        self.assertFalse(Path("music/key.wav").exists())
        md = Path("storyboards/drive/storyboard.md").read_text()
        self.assertIn(f"Mixed: bed {info['bed_lufs']} LUFS, effects {info['fx_lufs']} LUFS", md)
        self.assertIn("4 sound cues over 3 beats.", md)

    def test_the_gate_refuses_effects_louder_than_the_bed_and_never_counts_cues(self):
        ok, said = qa.mix({"bed_lufs": -21.4, "fx_lufs": -16.3}, 19, 16)
        self.assertFalse(ok)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", said)
        ok, said = qa.mix({"bed_lufs": -21.4, "fx_lufs": -29.4}, 200, 16)
        self.assertTrue(ok)
        self.assertIn("8.0 LU under", said)
        self.assertIn("200 sound cues over 16 beats", said)
        self.assertFalse(qa.mix({}, 19, 16)[0])


class Brief(unittest.TestCase):
    def test_every_look_of_the_kit_names_a_recipe_the_engine_makes(self):
        book = music_engine.recipes()
        for style in look.TRIO:
            rid, _, removed = music_engine.resolve(book, look.card(style).get("music") or style)
            self.assertIn(rid, book["recipes"], style)
            self.assertEqual(removed, [], style)


class Make(InARun):
    def make(self, brief, style="scrapbook"):
        if brief is not None:
            self.put("taste.json", {"handle": "maren.okafor", "music": brief})
        if style:
            self.put("winner.json", {"board": style})
        self.assertEqual(music.cmd_make(types.SimpleNamespace(bpm=None, seconds=3)), 0)
        return json.loads(Path("music.json").read_text())

    def test_the_picked_looks_recipe_makes_the_bed_through_the_engine_with_its_effects(self):
        calls = []
        real = music_engine.compose

        def compose(*args, **kw):
            calls.append((args, kw))
            return real(*args, **kw)
        with mock.patch.object(music_engine, "compose", compose):
            info = self.make(None)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], look.card("scrapbook").get("music") or "scrapbook")
        self.assertEqual(info["recipe"], "scrapbook")
        self.assertIn("chosen by the look", info["origin"])
        bed = Path(info["file"])
        self.assertTrue(bed.is_file() and bed.parent.name.startswith("bed-"), info["file"])
        self.assertAlmostEqual(music.duration(bed), 3, delta=0.2)
        self.assertEqual(sorted(Path(f).name for f in info["fx"].values()), ["bright.wav", "hit.wav", "impact.wav", "riser.wav"])
        self.assertTrue(all(Path(f).is_file() for f in info["fx"].values()))

    def test_the_briefs_words_choose_another_recipe_and_take_an_instrument_out(self):
        book = music_engine.recipes()
        other = next(r for r in book["recipes"] if r != "scrapbook")
        word = book["styles"][other][0]
        info = self.make({"styles": [word], "avoid": []})
        self.assertEqual(info["recipe"], other)
        self.assertIn("chosen by their brief", info["origin"])

    def test_each_look_makes_a_bed_of_its_own(self):
        made = {}
        for style in look.TRIO:
            made[style] = self.make(None, style)
        self.assertEqual(len({m["recipe"] for m in made.values()}), 3)
        self.assertEqual(len({tuple(m["programs"]) for m in made.values()}), 3)
        self.assertFalse(list(Path("music").glob("source.*")))
        self.assertEqual(len(list(Path("music").glob("bed-*"))), 1)

    def find(self):
        self.assertEqual(music.cmd_find(types.SimpleNamespace(bpm=None, seconds=3, origin=None)), 0)
        return json.loads(Path("music.json").read_text())

    def test_a_pick_of_another_look_makes_its_bed_again_and_a_track_they_brought_stays(self):
        first = self.make(None, "scrapbook")
        self.assertEqual(first["style"], "scrapbook")
        # the same pick keeps the bed it made
        self.assertEqual(self.find()["file"], first["file"])
        # another pick: find makes the bed again for the look picked now
        self.put("winner.json", {"board": "swiss-grid"})
        again = self.find()
        self.assertNotEqual(again["file"], first["file"])
        self.assertEqual(again["style"], "swiss-grid")
        self.assertEqual(again["recipe"], look.card("swiss-grid").get("music") or "swiss-grid")
        # a track they brought carries no recipe and stays whatever look is picked
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=2", "music/theirs.wav"], check=True)
        self.put("music.json", {"file": "music/theirs.wav", "origin": "their own track", "seconds": 2})
        self.put("winner.json", {"board": "cinematic-letterbox"})
        self.assertEqual(self.find()["file"], "music/theirs.wav")

    def test_before_a_pick_the_bed_is_the_kits_default_recipe_at_the_kits_tempo(self):
        info = self.make(None, style=None)
        self.assertEqual(info["recipe"], music_engine.recipes()["default"])
        self.assertIn("chosen by the kit's default", info["origin"])


if __name__ == "__main__":
    unittest.main()
