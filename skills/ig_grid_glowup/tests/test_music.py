"""music.py and the gate's audio row: a bed composed from the picked look's own recipe at its board's tempo unless the
person's brief names a sound or the person placed a track, the effects stem placed by loudness under the bed, and the
row that is red when the effects sit closer to the bed than that.

    python3 -I -m unittest discover -s S/tests -p test_music.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _env  # noqa: E402
import music  # noqa: E402
import qa  # noqa: E402
from test_resume import Run  # noqa: E402

BRIEF = {"styles": [], "avoid": ["vocals", "big drops"]}


def picked(style, tempo, beats=3, sound=()):
    """board.json as storyboard.py pick writes it, cut down to what music.py reads."""
    return {"style": style, "tempo": tempo, "seconds": 6.5,
            "boards": {"reel": {"bpm": tempo, "format": {"fps": 30}, "beats": [{"frames": 60}] * beats, "sound": list(sound)}}}


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

    def test_master_places_the_effects_by_loudness_under_the_bed_and_says_so_in_the_storyboard(self):
        self.write("taste.json", {"handle": "ines.at.home", "music": BRIEF})
        sound = [{"kind": "hit", "at": 1.0, "beat": "hook", "what": "the frame lands", "weight": 0.95, "bright": 0.45},
                 {"kind": "riser", "at": 6.0, "beat": "closer", "what": "the build", "beats": 2.0},
                 {"kind": "impact", "at": 8.0, "beat": "closer", "what": "the frame locks"},
                 {"kind": "stop", "at": 11.0, "beat": "closer", "what": "the stop"}]
        self.write("board.json", picked("editorial-quiet", 120, sound=sound))
        self.main(music, "make", "--seconds", "8")
        _env.write_text("storyboard.md", "# The storyboard\n\nMusic: not yet.\nMixed: not yet.\n")
        self.main(music, "master")
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["bed_lufs"] - info["fx_lufs"], music.FX_UNDER_BED_LU, delta=0.5)
        self.assertAlmostEqual(music.integrated_file(music.MUSIC / "bed-cut.wav"), info["bed_lufs"], delta=0.2)
        self.assertAlmostEqual(music.integrated_file(music.MUSIC / "fx.wav"), info["fx_lufs"], delta=0.2)
        md = Path("storyboard.md").read_text()
        self.assertIn(f"Music: {info['origin']}.", md)
        self.assertRegex(md, r"Mixed: bed -[\d.]+ LUFS, effects -[\d.]+ LUFS, [78]\.\d LU under; 4 sound cues over 3 beats\.")


REEL = {"bpm": 120, "seconds": 22.0, "beats": [{}, {}, {}],
        "sound": [{"kind": "hit", "at": 2.0}, {"kind": "impact", "at": 38.0}, {"kind": "stop", "at": 40.0}]}


class AudioRow(unittest.TestCase):
    def test_the_row_names_the_second_of_every_cue_and_that_the_music_stops_as_the_ask_lands(self):
        ok, detail = qa.mix({"bed_lufs": -21.4, "fx_lufs": -29.4, "sound_cues": 3}, REEL)
        self.assertTrue(ok, detail)
        self.assertIn("at hit 1.00 s, impact 19.00 s, stop 20.00 s", detail)
        self.assertIn("the music stops at 20.00 s as the ask lands and the profile holds in silence to 22.00 s", detail)

    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_is_red(self):
        ok, detail = qa.mix({"bed_lufs": -21.4, "fx_lufs": -16.3, "sound_cues": 2}, REEL)
        self.assertFalse(ok)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("2 sound cues over 3 beats", detail)

    def test_effects_eight_lu_under_the_bed_are_green(self):
        ok, detail = qa.mix({"bed_lufs": -21.4, "fx_lufs": -29.4, "sound_cues": 2}, REEL)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)

    def test_a_master_with_cues_and_no_effects_measured_is_red(self):
        ok, detail = qa.mix({"bed_lufs": -21.4, "sound_cues": 2}, REEL)
        self.assertFalse(ok)
        self.assertIn("no effects stem measured", detail)


if __name__ == "__main__":
    unittest.main()
