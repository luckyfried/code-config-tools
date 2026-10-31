"""The film's sound sits under the music and lands where a beat lands: the gate's audio row is red when the effects
stem is less than music.FX_UNDER_BED_LU - 1 LU under the bed and names both numbers and the cue and beat counts; the
board's cues are one where each beat lands, the build into the wall, the stop's hit and the stop, at most four more
than the beats; and the bed is composed by the music engine in the picked look's own recipe, so two looks give two
beds at two tempos, each inside its recipe's range, a slow recipe plays fast enough in its range for five people to
run within thirty seconds, and the brief's words can name another recipe.

    python3 -I -m unittest discover -s S/tests -p test_sound.py
"""
import contextlib
import copy
import io
import os
import shutil
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
import layout as L  # noqa: E402

STAMP = {"text": "sicily, july", "x": 88, "y": 854.0, "size": 150, "file": "fonts/styles/scrapbook/CaveatBrush-Regular.ttf",
         "face": "display", "tracking": -0.02, "color": "ink", "rotate": 0.0, "pivot": [88, 854.0]}
SAID = {"text": "save me a seat", "x": 88, "y": 628.0, "size": 62, "file": "fonts/styles/scrapbook/Gloock-Regular.ttf",
        "face": "text", "tracking": -0.02, "color": "ink", "rotate": 0.0, "pivot": [88, 854.0]}
TAG = {"text": "@kofi.cooks", "file": "fonts/styles/scrapbook/CaveatBrush-Regular.ttf", "size": 42, "tip": [540.0, 1233.5], "side": "above",
       "box": [393.0, 1140.2, 687.0, 1215.8]}
HANDLES = ["liv.outside", "theo.makes", "ines.walks", "dani.reyes", "kofi.cooks"]


class Run(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        _env.tools()


class AudioRow(Run):
    def audio_row(self, fx_lufs):
        """The check's audio row over a cut at -14 LUFS whose master measured the bed at -21.4 LUFS and the effects at
        `fx_lufs`, its board seven beats and ten cues."""
        import boards
        import qa
        import storyboard
        Path("render").mkdir()
        Path("render/cut.mp4").write_bytes(b"the cut")
        _env.write_json("render/cut.json", {"hook_frame": 1, "frames": 660})
        beats = [{"id": "hook"}] + [{"id": f"person-{i}", "person": h} for i, h in enumerate(HANDLES, 1)] + [{"id": "closer"}]
        _env.write_json("film.json", {"style": "scrapbook", "bpm": 120, "storyboard": {"beats": beats, "people": HANDLES}})
        _env.write_json("render/board-reel.json", {"bpm": 120, "beats": beats, "sound": [{"kind": "hit", "at": 0.0}] * 9 + [{"kind": "stop", "at": 40.0}]})
        _env.write_json("music.json", {"file": "music/bed.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs, "sound_cues": 10})
        video = {"width": 1080, "height": 1920, "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}
        audio = {"codec_name": "aac", "bit_rate": "192000"}
        with mock.patch.object(qa, "video_of", lambda p: (video, audio, 22.0)), mock.patch.object(qa, "loudness", lambda p: -14.0), \
                mock.patch.object(qa, "ffmpeg_lines", lambda *a: []), mock.patch.object(boards, "Ctx", lambda: None), \
                mock.patch.object(storyboard, "problems", lambda *a: []):
            res, _ = qa.cut_checks()
        return next(r for r in res if r[0] == "audio")

    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_turns_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-16.3)
        self.assertFalse(ok, detail)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("10 sound cues over 7 beats", detail)

    def test_effects_eight_lu_under_the_bed_turn_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-29.4)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)


class Cues(unittest.TestCase):
    def test_a_sound_lands_where_a_beat_lands_and_nowhere_else(self):
        """Five people's cards, each with its tag, its stamp and two lines of their words, between the hook's five
        tags and the wall: a hit as the camera lands on the hook's photograph, one hit of one weight as the blade
        cuts each person's photograph, the build into the wall and its impact, the hit as the tag lands on the last
        face, and the stop. Tags pop, words rise and the camera travels in silence."""
        people = [types.SimpleNamespace(rank=i, handle=h, stamp=f"place {i}, month {i}", voice="warm") for i, h in enumerate(HANDLES, 1)]
        ctx = types.SimpleNamespace(person={p.handle: p for p in people}.__getitem__, handle="maren.okafor", year=2026)
        hook = {"id": "hook", "layers": [{"kind": "Tags", "at": 0.5, "tags": [dict(copy.deepcopy(TAG), text=f"@{h}") for h in HANDLES]}]}
        cards = [{"id": f"person-{p.rank}", "person": p.handle, "layers": [
            {"kind": "Tags", "at": 0.25, "tags": [dict(copy.deepcopy(TAG), text=f"@{p.handle}")]},
            {"kind": "Words", "at": 1.0, "lines": [dict(STAMP, name=f"stamp-{p.rank}", text=p.stamp)]},
            {"kind": "Words", "at": 1.35, "lines": [dict(SAID), dict(SAID, text="and a spoon")], "step": 0.08}]} for p in people]
        beats = [hook] + cards + [{"id": "closer", "layers": []}]
        board_drive.use("scrapbook", swatches=["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"])
        starts, t = {}, 0.0
        for b, n in zip(beats, [4, 6, 6, 6, 6, 7, 9]):
            starts[b["id"]] = t
            t += n
        cues = board_drive.sound(beats, starts, ctx, people, L.Frame("reel"))
        self.assertLessEqual(len(cues), len(beats) + 4)
        self.assertEqual({c["kind"] for c in cues}, {"hit", "riser", "impact", "stop"})
        hits = [c for c in cues if c["kind"] == "hit"]
        self.assertEqual([c["beat"] for c in hits], ["hook"] + [b["id"] for b in cards] + ["closer"])
        self.assertEqual(len({c["weight"] for c in hits if c["beat"].startswith("person-")}), 1)
        self.assertEqual([(c["kind"], c["beat"]) for c in cues if c["kind"] in ("riser", "impact", "stop")],
                         [("riser", "closer"), ("impact", "closer"), ("stop", "closer")])
        riser, impact = (next(c for c in cues if c["kind"] == k) for k in ("riser", "impact"))
        self.assertAlmostEqual(riser["at"] + riser["beats"], impact["at"])


class Beds(Run):
    def make(self, look, brief=None):
        import music
        _env.write_json("winner.json", {"board": look})
        _env.write_json("taste.json", {"handle": "maren.okafor", **({"music": brief} if brief else {})})
        with contextlib.redirect_stdout(io.StringIO()):
            music.cmd_make(types.SimpleNamespace(bpm=None, seconds=4))
        info = _env.read_json("music.json")
        return info, Path(info["file"]).read_bytes()

    def test_two_looks_make_two_beds_in_their_own_recipes_at_two_tempos(self):
        import music_engine
        import style
        book = music_engine.recipes()["recipes"]
        made = {look: self.make(look) for look in ("scrapbook", "kinetic-type")}
        for look, (info, _) in made.items():
            recipe = style.card(look)["music"]
            lo, hi = book[recipe]["tempo"]
            self.assertEqual(info["recipe"], recipe)
            self.assertTrue(lo <= info["bpm"] <= hi, (look, info["bpm"]))
            self.assertIn(f"from the {recipe} recipe", info["origin"])
            self.assertIn("chosen by the look", info["origin"])
        self.assertNotEqual(made["scrapbook"][0]["bpm"], made["kinetic-type"][0]["bpm"])
        self.assertNotEqual(made["scrapbook"][1][:40000], made["kinetic-type"][1][:40000])

    def test_a_slow_recipe_plays_fast_enough_in_its_range_that_five_people_run_within_thirty_seconds(self):
        import music
        import music_engine
        import style
        recipe = style.card("analog-home-movie")["music"]
        lo, hi = music_engine.recipes()["recipes"][recipe]["tempo"]
        sb = {"bpm": 120, "beats": [{"pulses": 4}] + [{"pulses": 6}] * 4 + [{"pulses": 8}, {"pulses": 11}]}
        with mock.patch.object(music, "picked_board", lambda look: (None, sb)):
            info, _ = self.make("analog-home-movie")
        self.assertTrue(lo <= info["bpm"] <= hi, info["bpm"])
        self.assertLessEqual(47 * 60 / info["bpm"], 29.5)

    def test_the_briefs_words_can_name_another_recipe(self):
        import style
        other = style.card("kinetic-type")["music"]
        info, _ = self.make("scrapbook", {"mood": "drive", "styles": [other], "avoid": []})
        self.assertEqual(info["recipe"], other)
        self.assertIn("chosen by their brief", info["origin"])


if __name__ == "__main__":
    unittest.main()
