"""The film's sound: the shared layer's effects where the picture lands (a whoosh on every cut and on the dive, a shutter
as every photograph lands, an impact as the title lands and as the closer arrives, the riser into it), on the board's
grid, and nothing else playing; the board's marks where the bed turns and stops; the master music.py makes with its
energy a frame; and the bed music.py makes through the music engine from the picked look's recipe, or the one their
music brief's words name.

    python3 -I -m unittest discover -s S/tests -p test_audio.py
"""
import json
import os
import re
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
import board_drive  # noqa: E402
import look  # noqa: E402
import music  # noqa: E402
import music_engine  # noqa: E402
import sfx  # noqa: E402
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


class Marks(unittest.TestCase):
    def test_the_bed_lifts_into_the_peak_beat_at_its_own_tempo(self):
        board = {"bpm": 90, "beats": [{"bars": 1}, {"bars": 2, "peak": True}, {"bars": 1}]}
        for bed in (90, 180, 45):
            land, end = music.peak(board, bed)
            self.assertAlmostEqual(land, 4 * 60 / 90, places=6)
            self.assertAlmostEqual(end, 12 * 60 / 90, places=6)
        self.assertIsNone(music.peak({"bpm": 90, "beats": [{"bars": 1}, {"bars": 2}]}, 90))
        self.assertIsNone(music.peak(None, 90))

    def test_the_board_marks_where_the_bed_turns_and_where_it_stops_and_plays_nothing(self):
        b = storyboard.plan(SOURCE, "reel", None)["board"]
        kinds = [c["kind"] for c in b["sound"]]
        self.assertEqual(sorted(kinds), ["stop", "turn", "turn"])
        stop = next(c["at"] for c in b["sound"] if c["kind"] == "stop")
        self.assertTrue(all(c["at"] <= stop for c in b["sound"]))
        self.assertEqual(music.edges(b, b["bpm"]), [c["at"] * 60 / b["bpm"] for c in b["sound"] if c["kind"] == "turn"])


class Effects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = storyboard.plan(SOURCE, "reel", None)["board"]
        cls.fx = board_drive.fx_board(cls.b)
        cls.ev, _ = sfx.events(cls.fx)

    def test_a_whoosh_on_every_cut_a_shutter_as_every_photograph_lands_and_the_title_and_closer_hit(self):
        kinds = [k for _, k in self.ev]
        stops = len(self.b["route"]["cards"])
        marks = sum(1 for x in self.b["beats"] if x.get("move") in sfx.MARKS)
        # a whoosh on the dive onto the first place and on every cut into a stop; the closer's way in is its riser
        self.assertEqual(sum(kinds.count(k) for k in ("air", "sweep", "bright")), stops)
        self.assertEqual(kinds.count("bright"), 1)
        self.assertEqual(kinds.count("shutter") + kinds.count("pop"), stops)
        self.assertEqual(kinds.count("pop"), marks)
        self.assertEqual((kinds.count("impact"), kinds.count("riser")), (2, 1))

    def test_every_effect_is_on_the_quarter_beat_grid_before_the_stop(self):
        step = 60 / self.b["bpm"] / sfx.GRID
        stop = next(c["at"] for c in self.b["sound"] if c["kind"] == "stop") * 60 / self.b["bpm"]
        for t, k in self.ev:
            self.assertAlmostEqual(t / step, round(t / step), places=4, msg=(t, k))
            self.assertLess(t, stop, (t, k))

    def test_the_title_hits_as_it_lands_and_the_closer_on_its_cut(self):
        sec = 60 / self.b["bpm"]
        hits = [t for t, k in self.ev if k == "impact"]
        st, _ = board_drive.starts(self.b)
        self.assertAlmostEqual(hits[0], round(board_drive.TITLE_IN * 4) / 4 * sec, places=4)
        self.assertAlmostEqual(hits[1], round(st["closer"] * 4) / 4 * sec, places=4)
        closer = self.fx["beats"][-1]
        self.assertAlmostEqual(closer["layers"][0]["at"]["arrive"], st["closer"] + board_drive.CLOSER_LAND, places=4)

    def test_the_read_reads_every_cut_at_its_hit_on_the_beat(self):
        # the hook's dive, a spectacle's early switch and the closer's landing are lead-ins and arrivals: the read reads
        # each cut where the picture cuts, on the film's beat
        rows = sfx.read_cuts(self.fx)
        self.assertTrue(rows)
        self.assertEqual([r for r in rows if r["verdict"] != "on the beat"], [])
        sec = 60 / self.b["bpm"]
        hook = next(r for r in rows if r["into"] == self.b["route"]["cards"][0]["id"])
        dive = self.b["route"]["hook"]
        self.assertAlmostEqual(hook["at"], (dive["dive"] + dive["settle"]) / 2 * sec, places=3)

    def test_a_spectacles_photograph_lands_when_its_flight_does(self):
        b = json.loads(json.dumps(self.b))
        beat = next(x for x in b["beats"][1:-1])
        beat["move"] = "picture-tunnel"
        got = next(x for x in board_drive.fx_board(b)["beats"] if x["id"] == beat["id"])
        self.assertAlmostEqual(got["layers"][0]["at"]["arrive"] - (got["start"] - got["lead"]),
                               board_drive.FLIGHT["picture-tunnel"] / (60 / b["bpm"]), places=3)


class Master(InARun):
    def test_master_carries_the_music_alone_and_writes_its_energy_a_frame(self):
        os.makedirs("music")
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=4", "-af", "volume=-24dB",
                        "music/quiet.wav"], check=True)
        cues = [{"kind": "turn", "at": 2.0, "beat": "s01", "what": "b"}, {"kind": "stop", "at": 5.0, "beat": "closer", "what": "d"}]
        self.put("film.json", {"seconds": 3.5, "bpm": 120, "sound": cues})
        self.put("music.json", {"file": "music/quiet.wav", "fx": {"hit": "music/fx/hit.wav"}, "bed_lufs": -20, "fx_lufs": -28})
        self.assertEqual(music.cmd_master(types.SimpleNamespace(seconds=None)), 0)
        info = json.loads(Path("music.json").read_text())
        self.assertAlmostEqual(info["master_lufs"], -14, delta=1)
        self.assertFalse({"fx", "bed_lufs", "fx_lufs"} & set(info))
        self.assertFalse(Path("music/fx.wav").exists() or Path("music/mix.wav").exists())
        energy = json.loads(Path("music/energy.json").read_text())
        self.assertEqual(energy["fps"], board_drive.FPS)
        self.assertAlmostEqual(len(energy["rms"]), 3.5 * board_drive.FPS, delta=2)
        self.assertTrue(0 < max(energy["rms"]) <= 1)

    def test_a_peaky_bed_reaches_the_target_by_one_gain_and_keeps_its_peaks_whole(self):
        """Sharp clicks over a quiet bed need peaks past full scale to reach -14 LUFS: the master is written in float and
        keeps them, so the film's one limiter (sfx.py) is the only thing that touches them."""
        ff = _env.ffmpeg()
        os.makedirs("music")
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "anoisesrc=d=6:c=pink:a=0.01", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(mod(t,0.25),0.004),0.9,0)':d=6:s=48000", "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", "music/source.wav"], check=True)
        self.put("music.json", {"file": "music/source.wav", "bpm": 120, "downbeats": [0, 2, 4]})
        self.put("film.json", {"seconds": 6.0, "bpm": 120, "music_start": 0.0, "sound": []})
        self.assertEqual(music.cmd_master(types.SimpleNamespace(seconds=None)), 0)
        info = json.loads(Path("music.json").read_text())
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        said = subprocess.run([ff, "-hide_banner", "-nostats", "-i", info["master"], "-af", "astats=measure_perchannel=none",
                               "-f", "null", "-"], capture_output=True, text=True).stderr
        peak = float(re.findall(r"Peak level dB: (-?[\d.]+)", said)[-1])
        self.assertGreater(peak, 0.0, "the clicks stand past full scale in the float master, unclipped")


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

    def test_the_picked_looks_recipe_makes_the_bed_through_the_engine(self):
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
        # the film's effects are the shared layer's, so music.json names the bed alone
        self.assertNotIn("fx", info)

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
