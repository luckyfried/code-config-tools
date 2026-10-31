"""music.py and the gate's audio row: a bed composed from the picked look's own recipe at its board's tempo unless the
person's brief names a sound or the person placed a track, mastered and cut on the board's stop with its energy a frame
beside it, the board's sound effects measured under it, and the row that is red when the effects sit too close to the
music.

    python3 -I -m unittest discover -s S/tests -p test_music.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _env  # noqa: E402
import music  # noqa: E402
import qa  # noqa: E402
from test_resume import Run  # noqa: E402

BRIEF = {"styles": [], "avoid": ["vocals", "big drops"]}


# the effects' board drive.py writes, cut down: the hook line slamming home, a photograph coming in and seating, the
# closer's lock
FX = {"id": "t", "bpm": 120, "beats": [
    {"id": "hook-title", "form": "words", "start": 0.0, "layers": [{"kind": "Title", "at": {"arrive": 0.0, "end": 2.0},
                                                                     "title": {"text": "same feed"}, "slam": [1.0, 0.0]}]},
    {"id": "post-1", "form": "photo", "transition": "dissolve", "start": 3.0,
     "layers": [{"kind": "Photo", "at": {"arrive": 5.0, "end": 5.2}, "label": "", "text": ""}]},
    {"id": "closer", "form": "closer", "start": 9.0, "layers": [{"kind": "Closer", "at": {"arrive": 9.0, "end": 11.0}}]}]}


def picked(style, tempo, beats=3, fx=None, stop=None):
    """board.json as storyboard.py pick writes it, cut down to what music.py reads."""
    return {"style": style, "tempo": tempo, "seconds": 6.5,
            "boards": {"reel": {"bpm": 120, "tempo": tempo, "format": {"fps": 30}, "beats": [{"frames": 60}] * beats,
                                "fx": fx or {"id": "t", "bpm": tempo, "beats": []}, "stop_seconds": stop}}}


class Music(Run):
    def test_two_looks_make_two_different_beds_each_from_its_own_recipe_at_its_tempo(self):
        made = []
        self.write("taste.json", {"handle": "ines.at.home", "music": BRIEF})
        for style, tempo in (("editorial-quiet", 72), ("kinetic-type", 124)):
            self.write("board.json", picked(style, tempo))
            self.main(music, "make", "--seconds", "2")
            info = _env.read_json("music.json")
            made.append((info["recipe"], info["bpm"], info["origin"], Path(info["file"]).read_bytes()))
        (quiet, quiet_bpm, quiet_origin, quiet_bed), (loud, loud_bpm, loud_origin, loud_bed) = made
        self.assertEqual((quiet, quiet_bpm, loud, loud_bpm), ("editorial-quiet", 72, "kinetic-type", 124))
        self.assertIn("from the editorial-quiet recipe", quiet_origin)
        self.assertIn("chosen by the board's style", quiet_origin)
        self.assertIn("at 124 bpm", loud_origin)
        self.assertNotEqual(quiet_bed, loud_bed)

    def test_the_bed_lifts_into_the_peak_post_from_its_landing_to_its_beats_end(self):
        board = picked("swiss-grid", 120)
        board["boards"]["reel"]["timeline"] = {"beats": [
            {"id": "post-1", "form": "photo", "at": 2.0, "end": 6.0, "peak": False},
            {"id": "post-5", "form": "clip", "at": 8.0, "end": 14.0, "peak": True, "hand": 1.29}]}
        self.assertEqual(music.peak(board), (8.0 * 0.5 + 1.29, 14.0 * 0.5))
        board["boards"]["reel"]["timeline"]["beats"][1].pop("hand")
        self.assertEqual(music.peak(board), (4.0, 7.0))
        self.write("board.json", board)
        self.write("taste.json", {"handle": "ines.at.home", "music": BRIEF})
        self.main(music, "make", "--seconds", "8")
        self.assertEqual(_env.read_json("music.json")["peak"], [4.0, 7.0])
        board["boards"]["reel"]["timeline"]["beats"][1]["peak"] = False
        self.assertIsNone(music.peak(board))

    def test_find_makes_the_bed_for_the_look_and_a_placed_track_wins(self):
        self.write("board.json", dict(picked("swiss-grid", 100), seconds=1))
        self.write("taste.json", {"handle": "ines.at.home", "music": BRIEF})
        self.assertEqual(self.main(music, "find"), 0)
        made = _env.read_json("music.json")
        self.assertTrue(made["origin"].startswith("made by music.py from the swiss-grid recipe"), made["origin"])
        placed = music.MUSIC / "source.wav"
        placed.write_bytes(Path(made["file"]).read_bytes())
        self.assertEqual(self.main(music, "find", "--origin", "chosen by Ines"), 0)
        self.assertEqual({k: _env.read_json("music.json")[k] for k in ("file", "origin")},
                         {"file": str(placed), "origin": "chosen by Ines"})

    def test_master_cuts_on_the_stop_writes_the_energy_and_measures_the_effects_under_the_music(self):
        self.write("taste.json", {"handle": "ines.at.home", "music": BRIEF})
        self.write("board.json", dict(picked("editorial-quiet", 120, fx=FX, stop=5.5), seconds=7.0))
        self.main(music, "make", "--seconds", "8")
        _env.write_text("storyboard.md", "# The storyboard\n\nMusic: not yet.\nMixed: not yet.\n")
        self.main(music, "master")
        info = _env.read_json("music.json")
        # the master mixes no effects: film.py render lays them over it, and the effects alone sit well under it
        self.assertNotIn("sound_cues", info)
        self.assertGreaterEqual(info["bed_lufs"] - info["fx_lufs"], music.FX_UNDER_BED_LU - 1)
        self.assertAlmostEqual(music.integrated_file(music.MUSIC / "fx.wav"), info["fx_lufs"], delta=0.2)
        self.assertEqual(info["effects"], 5)
        # one number a frame, and the music silent from the stop
        energy = _env.read_json(music.MUSIC / "energy.json")
        self.assertEqual(energy["fps"], 30)
        self.assertEqual(len(energy["rms"]), 7 * 30)
        self.assertGreater(max(energy["rms"][:150]), 0.01)
        self.assertLess(max(energy["rms"][int(5.6 * 30):]), 1e-3)
        md = Path("storyboard.md").read_text()
        self.assertIn(f"Music: {info['origin']}.", md)
        self.assertRegex(md, r"Mixed: music -1[34]\.\d+ LUFS, effects -[\d.]+ LUFS, \d+\.\d LU under; 5 effects over 3 beats\.")


    def test_a_peaky_track_reaches_the_target_by_one_gain_and_keeps_its_peaks_whole(self):
        """Sharp clicks over a quiet bed need peaks past full scale to reach -14 LUFS. master reads the loudness once and
        sets one gain, with no limiter, and writes the master in 32-bit float, so the clicks stand past full scale
        unclipped and the film's mux (sfx.py) is the only thing that limits them."""
        music.MUSIC.mkdir(exist_ok=True)
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=7:c=pink:a=0.01", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(mod(t,0.25),0.004),0.9,0)':d=7:s=48000", "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", str(music.MUSIC / "source.wav")], check=True)
        self.write("music.json", {"file": str(music.MUSIC / "source.wav"), "origin": "chosen by Ines"})
        self.write("board.json", dict(picked("editorial-quiet", 120), seconds=6.0))
        calls, real = [], subprocess.run

        def run(argv, **kw):
            calls.append([str(x) for x in argv])
            return real(argv, **kw)
        with mock.patch.object(music.subprocess, "run", run):
            self.main(music, "master")
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        self.assertFalse([c for c in calls if any("alimiter" in x for x in c)], "no limiter in the master")
        written = next(i for i, c in enumerate(calls) if "master" in Path(c[-1]).name)
        self.assertEqual(sum("ebur128" in " ".join(c) for c in calls[:written]), 1, "one loudness read, then one gain")
        self.assertEqual(calls[written][-3:-1], ["-c:a", "pcm_f32le"])
        said = real([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", info["master"], "-af", "astats=measure_perchannel=none", "-f", "null",
                     "-"], capture_output=True, text=True).stderr
        self.assertGreater(float(re.findall(r"Peak level dB: (-?[\d.]+)", said)[-1]), 0.0,
                           "the clicks stand past full scale in the float master, unclipped")

REEL = {"bpm": 120, "tempo": 120, "seconds": 22.0, "beats": [{}, {}, {}], "stop_seconds": 20.0, "fx": {
    "id": "r", "bpm": 120, "beats": [
        {"id": "hook-title", "form": "words", "start": 0.0, "layers": [{"kind": "Title", "at": {"arrive": 0.0, "end": 2.0},
                                                                         "title": {"text": "a b"}, "slam": [2.0, 0.0]}]},
        {"id": "closer", "form": "closer", "start": 38.0, "layers": [{"kind": "Closer", "at": {"arrive": 38.0, "end": 40.0}}]}]}}


class AudioRow(unittest.TestCase):
    def test_the_row_names_the_second_of_every_effect_and_that_the_music_stops_as_the_ask_lands(self):
        ok, detail = qa.mix({"bed_lufs": -14.0, "fx_lufs": -24.0}, REEL)
        self.assertTrue(ok, detail)
        self.assertIn("3 effects over 3 beats at impact 1.00 s, impact 19.00 s, riser 19.00 s", detail)
        self.assertIn("the music stops at 20.00 s as the ask lands and the profile holds in silence to 22.00 s", detail)

    def test_effects_close_under_the_music_are_red(self):
        ok, detail = qa.mix({"bed_lufs": -14.0, "fx_lufs": -16.3}, REEL)
        self.assertFalse(ok)
        self.assertIn("music -14.0 LUFS, effects -16.3 LUFS", detail)

    def test_effects_eight_lu_under_the_music_are_green(self):
        ok, detail = qa.mix({"bed_lufs": -14.0, "fx_lufs": -22.0}, REEL)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)

    def test_a_board_with_effects_and_none_measured_is_red(self):
        ok, detail = qa.mix({"bed_lufs": -14.0}, REEL)
        self.assertFalse(ok)
        self.assertIn("no effects measured", detail)


if __name__ == "__main__":
    unittest.main()
