"""The film's sound is the shared effects (sfx.py) over the music, and lands where the picture lands: the gate's audio
row is red when the effects sit less than qa.FX_UNDER LU under the master and names both numbers and the effect and
beat counts; the board's effects are a shutter and an impact on the hook, a whoosh on each cut into a person and a
shutter as their photograph lands (on the landing of a move that takes the frame), the riser cut off by the wall's
impact, the tag's pop and the closer's impact on the stop, every one on the music's grid, and the board's own `sound`
is the stop alone, so nothing plays twice; and the bed is composed by the music engine in the picked look's own recipe,
so two looks give two beds at two tempos, each inside its recipe's range, a slow recipe plays fast enough in its range
for five people to run within thirty seconds, and the brief's words can name another recipe.

    python3 -I -m unittest discover -s S/tests -p test_sound.py
"""
import contextlib
import copy
import io
import os
import re
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
        """The check's audio row over a cut at -14 LUFS whose master measured -14.0 LUFS and whose effects film.py cut
        measured at `fx_lufs`, its board seven beats and ten effects."""
        import boards
        import qa
        import storyboard
        Path("render").mkdir()
        Path("render/cut.mp4").write_bytes(b"the cut")
        _env.write_json("render/cut.json", {"hook_frame": 1, "frames": 660, "sound": {"effects": 10, "fx_lufs": fx_lufs, "music": True}})
        beats = [{"id": "hook"}] + [{"id": f"person-{i}", "person": h} for i, h in enumerate(HANDLES, 1)] + [{"id": "closer"}]
        _env.write_json("film.json", {"style": "scrapbook", "bpm": 120, "storyboard": {"beats": beats, "people": HANDLES}})
        _env.write_json("render/board-reel.json", {"bpm": 120, "beats": beats, "sound": [{"kind": "stop", "at": 40.0}]})
        _env.write_json("music.json", {"file": "music/bed.wav", "master_lufs": -14.0})
        video = {"width": 1080, "height": 1920, "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}
        audio = {"codec_name": "aac", "bit_rate": "192000"}
        with mock.patch.object(qa, "video_of", lambda p: (video, audio, 22.0)), mock.patch.object(qa, "loudness", lambda p: -14.0), \
                mock.patch.object(qa, "ffmpeg_lines", lambda *a: []), mock.patch.object(boards, "Ctx", lambda: None), \
                mock.patch.object(storyboard, "problems", lambda *a: []):
            res, _ = qa.cut_checks()
        return next(r for r in res if r[0] == "audio")

    def test_effects_as_loud_as_the_music_turn_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-16.3)
        self.assertFalse(ok, detail)
        self.assertIn("music -14.0 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("10 effects over 7 beats", detail)

    def test_effects_well_under_the_music_turn_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-24.0)
        self.assertTrue(ok, detail)
        self.assertIn("10.0 LU under", detail)


class Effects(unittest.TestCase):
    @staticmethod
    def board(moves):
        """Five people's cards between the hook and the wall, the board laid out the way board() lays it, each person
        moving by `moves[i]` (a move that takes the frame carries its flight on the Cut layer, as board() sets it)."""
        hook = {"id": "hook", "move": "polaroid-drop", "transition": None, "layers": []}
        cards = []
        for i, (h, m) in enumerate(zip(HANDLES, moves), 1):
            f = board_drive.fly(m, 106)
            cards.append({"id": f"person-{i}", "person": h, "move": m, "transition": "page-turn" if i % 2 else "paper-slide",
                          "layers": [{"kind": "Cut", "at": 0, **({"fly": f} if f else {})},
                                     {"kind": "Words", "at": 1.0 + f, "lines": [dict(STAMP, name=f"stamp-{i}")]}]})
        beats = [hook] + cards + [{"id": "closer", "move": "page-drift", "transition": "page-turn", "layers": []}]
        starts, t = {}, 0.0
        for b, n in zip(beats, [4, 6, 6, 6, 6, 9, 9.9]):
            starts[b["id"]] = t
            t += n
        return beats, starts

    def setUp(self):
        board_drive.use("scrapbook", swatches=["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"])

    def test_every_effect_lands_where_the_picture_lands_and_the_boards_sound_is_the_stop_alone(self):
        import sfx
        beats, starts = self.board(["doodle-draw-on", "sticker-pop", "doodle-draw-on", "sticker-pop", "tilted-wall"])
        self.assertEqual([c["kind"] for c in board_drive.sound(beats, starts)], ["stop"])
        fx = board_drive.effects(beats, starts, 106, "people-scrapbook-reel")
        events, _ = sfx.events(fx)
        kinds = [k for _, k in events]
        sec = 60 / 106
        at = lambda k: [round(t / sec, 2) for t, kk in events if kk == k]
        q = lambda x: round(x * 4) / 4   # the grid's quarter beat a moment lands on
        # a whoosh on each cut into a person, the first the one bright one, and none into the wall
        self.assertEqual(kinds.count("bright"), 1)
        whooshes = sorted(at("bright") + at("air") + at("sweep"))
        self.assertEqual(whooshes, [starts[b["id"]] for b in beats if b["id"].startswith("person-")])
        # the hook's photograph lands on frame 0, and 'my people.' lands with an impact
        self.assertIn(0.0, at("shutter"))
        self.assertIn(q(board_drive.TITLE_AT + 0.5), at("impact"))
        # a mark's beat pops as the blade cuts; the tilted wall's beat shutters as the move hands the frame back
        self.assertIn(q(starts["person-1"] + board_drive.CUT), at("pop"))
        f = board_drive.fly("tilted-wall", 106)
        self.assertIn(q(starts["person-5"] + f), at("shutter"))
        # the riser ends on the wall's impact; the tag pops on the last face; the closer's impact lands on the stop
        C = starts["closer"]
        self.assertIn(q(C + board_drive.ROUTE_AT), at("impact"))
        self.assertIn(q(C + board_drive.ROUTE_AT), at("riser"))
        self.assertIn(q(C + board_drive.ROUTE_AT + board_drive.ROUTE), at("pop"))
        stop = board_drive.sound(beats, starts)[0]["at"]
        self.assertIn(q(stop), at("impact"))
        # every effect sits on the grid's quarter beats
        for t, _ in events:
            self.assertAlmostEqual(t / sec * 4, round(t / sec * 4), places=4)

    def test_a_count_hits_on_its_stop(self):
        import sfx
        board_drive.use("kinetic-type", swatches=["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"])
        beats, starts = self.board(["counter", "marquee", "exploded-layers", "stack-and-split", "slam-words"])
        events, _ = sfx.events(board_drive.effects(beats, starts, 106, "people-kinetic-reel"))
        sec = 60 / 106
        stop = starts["person-1"] + board_drive.COUNT_S / sec
        self.assertIn(round(stop * 4) / 4, [round(t / sec, 2) for t, k in events if k == "impact"])

    def test_a_move_that_takes_the_frame_holds_until_the_card_can_be_read_after_it(self):
        self.assertEqual(board_drive.fly("doodle-draw-on", 120), 0)
        for m, secs in board_drive.TAKES.items():
            f = board_drive.fly(m, 132)
            self.assertGreaterEqual(f * 60 / 132, secs + board_drive.HAND_BACK)
            self.assertEqual(f * 4, round(f * 4))


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



def ff(*args):
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def measured(path):
    """`path`'s integrated loudness, LUFS, and its sample peak, dBFS, read in float (astats; volumedetect clips)."""
    said = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af",
                           "astats=measure_perchannel=none,ebur128=framelog=quiet", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", said)[-1]), float(re.findall(r"Peak level dB: (-?[\d.]+)", said)[-1])


class Mastering(Run):
    def test_a_peaky_bed_reaches_the_target_by_one_gain_and_keeps_its_peaks_whole(self):
        """Sharp clicks over a quiet bed need peaks past full scale to reach -14 LUFS: the master is written in float and
        keeps them, so the film's one limiter (sfx.py) is the only thing that touches them."""
        import music
        music.MUSIC.mkdir()
        ff("-f", "lavfi", "-i", "anoisesrc=d=6:c=pink:a=0.01", "-f", "lavfi", "-i", "aevalsrc='if(lt(mod(t,0.25),0.004),0.9,0)':d=6:s=48000",
           "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", "music/source.wav")
        _env.write_json("music.json", {"file": "music/source.wav", "bpm": 120, "downbeats": [0, 2, 4]})
        _env.write_json("film.json", {"seconds": 6.0, "music_start": 0.0})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_master(types.SimpleNamespace(seconds=None)), 0)
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        _, peak = measured(info["master"])
        self.assertGreater(peak, 0.0, "the clicks stand past full scale in the float master, unclipped")

    def test_the_cut_masters_the_music_and_the_effects_together_onto_minus_14_lufs(self):
        """film.py's mux hands the mix to sfx.mux, which brings music and effects onto -14 LUFS in one encode: a master
        laid well under the target comes out at it, with its true peak under the limiter's ceiling."""
        import film
        import sfx
        board_drive.use("scrapbook", swatches=["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"])
        beats, starts = Effects.board(["doodle-draw-on", "sticker-pop", "doodle-draw-on", "sticker-pop", "tilted-wall"])
        board = {"effects": board_drive.effects(beats, starts, 106, "people-scrapbook-reel")}
        ff("-f", "lavfi", "-i", "color=c=gray:s=64x64:r=30:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", "silent.mp4")
        Path("music").mkdir()
        ff("-f", "lavfi", "-i", "aevalsrc=0.08*sin(2*PI*110*t)*abs(sin(2*PI*2*t))+0.027*sin(2*PI*1760*t):d=6:s=48000",
           "-af", "afade=t=out:st=4.8:d=0.4", "-ac", "2", "-c:a", "pcm_f32le", "music/master.wav")
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav", "bpm": 106})
        out = Path("render/cut.mp4")
        sound = film.mux(types.SimpleNamespace(spawn=subprocess.run), Path("silent.mp4"), out, 6.0, board)
        self.assertTrue(sound["music"])
        self.assertLess(sound["fx_lufs"], 0)
        self.assertEqual(sorted(p.name for p in out.parent.iterdir()), ["cut.mp4"], "nothing is left beside the cut")
        lufs, _ = measured(out)
        self.assertAlmostEqual(lufs, sfx.TARGET_LUFS, delta=1.0)
        said = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(out), "-af", "ebur128=peak=true:framelog=quiet",
                               "-f", "null", "-"], capture_output=True, text=True).stderr
        self.assertLessEqual(float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", said)[-1]), -1.5)

    def test_the_cut_lays_its_effects_once_and_measures_the_file_it_mixes(self):
        """One cut lays the board's effects once: the file measured for qa.py's audio row is the file under the music."""
        import film
        import sfx
        board_drive.use("scrapbook", swatches=["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"])
        beats, starts = Effects.board(["doodle-draw-on", "sticker-pop", "doodle-draw-on", "sticker-pop", "tilted-wall"])
        board = {"effects": board_drive.effects(beats, starts, 106, "people-scrapbook-reel")}
        ff("-f", "lavfi", "-i", "color=c=gray:s=64x64:r=30:d=6", "-c:v", "libx264", "-pix_fmt", "yuv420p", "silent.mp4")
        Path("music").mkdir()
        ff("-f", "lavfi", "-i", "aevalsrc=0.08*sin(2*PI*110*t):d=6:s=48000", "-ac", "2", "-c:a", "pcm_f32le", "music/master.wav")
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav", "bpm": 106})
        with mock.patch.object(sfx, "lay", wraps=sfx.lay) as lay:
            sound = film.mux(types.SimpleNamespace(spawn=subprocess.run), Path("silent.mp4"), Path("render/cut.mp4"), 6.0, board)
        self.assertEqual(lay.call_count, 1, "the effects are laid once per cut")
        self.assertLess(sound["fx_lufs"], 0)
        self.assertTrue(Path("render/cut.mp4").is_file())


if __name__ == "__main__":
    unittest.main()
