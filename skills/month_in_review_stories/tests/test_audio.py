"""The sound under the person's music: a cue only where a beat lands, the effects stem placed by loudness under the bed,
the bed composed by the music engine in the winning look's recipe at the board's tempo, and the person's own track
winning when they placed one.

    python3 -m unittest discover -s S/tests -p test_audio.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture

import compose  # noqa: E402
import music  # noqa: E402
import qa  # noqa: E402
from test_compose import picked  # noqa: E402

KINDS = {"hit", "riser", "impact", "stop"}
BRIEF = {"styles": [], "avoid": ["vocals", "spoken word"]}


def seconds_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def make(ws, *args):
    return subprocess.run([sys.executable, str(fixture.SCRIPTS / "music.py"), "make", *args], cwd=ws, capture_output=True, text=True,
                          env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))


class Cues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = compose.board("editorial-quiet", picked(fixture.month()))

    def test_the_reel_sounds_where_each_beat_lands_and_nowhere_else(self):
        r = self.board["reel"]
        kinds = [c["kind"] for c in r["sound"]]
        self.assertLessEqual(len(r["sound"]), len(r["beats"]) + 4, kinds)
        self.assertLessEqual(set(kinds), KINDS)
        self.assertEqual(kinds.count("riser"), 1)
        self.assertEqual(kinds.count("impact"), 1)
        self.assertEqual(kinds[-1], "stop")

    def test_a_card_sounds_only_where_its_line_lands(self):
        for c in self.board["beats"]:
            kinds = [x["kind"] for x in c["sound"]]
            self.assertLessEqual(set(kinds), KINDS, c["id"])
            self.assertLessEqual(len(kinds), 3, f"{c['id']}: {kinds}")


class Mix(unittest.TestCase):
    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_is_red(self):
        ok, detail = qa.mixed({"bed_lufs": -21.4, "fx_lufs": -16.3, "sound_cues": 10}, 6)
        self.assertFalse(ok)
        for said in ("-21.4", "-16.3", "10 sound cues over 6 beats"):
            self.assertIn(said, detail)
        self.assertTrue(qa.mixed({"bed_lufs": -21.4, "fx_lufs": -29.4, "sound_cues": 10}, 6)[0])
        self.assertTrue(qa.mixed({"sound_cues": 0}, 6)[0])
        self.assertFalse(qa.mixed({"sound_cues": 10}, 6)[0])

    def test_master_places_the_effects_by_loudness_under_the_bed(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        bed = d / "bed.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=6:sample_rate=48000",
                        "-af", "volume=-30dB", "-ac", "2", str(bed)], check=True)
        cues = [{"kind": "hit", "at": 2, "weight": 0.9, "bright": 0.5}, {"kind": "riser", "at": 4, "beats": 2},
                {"kind": "impact", "at": 6}, {"kind": "hit", "at": 8, "weight": 0.6}, {"kind": "stop", "at": 10}]
        fx = {}
        for i, c in enumerate(music.music_engine.CUES):
            fx[c] = str(d / f"{c}.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={440 + 110 * i}:duration=0.5:sample_rate=48000",
                            "-ac", "2", fx[c]], check=True)
        got = music.master(bed, 6.0, d / "out.wav", cues=cues, bpm=128, fx=fx)
        self.assertAlmostEqual(got["bed_lufs"] - got["fx_lufs"], music.FX_UNDER_BED_LU, delta=0.5)
        self.assertAlmostEqual(got["lufs"], -14.0, delta=1.0)
        self.assertTrue(qa.mixed(dict(got, sound_cues=len(cues)), 3)[0])


class Make(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = fixture.workspace()
        fixture.researched(cls.ws)
        cls.build = fixture.build(cls.ws)
        (cls.build / "taste.md").write_text("their month, in prose\n")
        cls.drafted = json.loads((cls.build / "taste.json").read_text())["music"]
        fixture.run(cls.ws, "storyboard.py", "draft")
        (cls.build / "winner.json").write_text('{"board": "editorial-quiet"}')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)

    def brief(self, m):
        taste = json.loads((self.build / "taste.json").read_text())
        taste["music"] = m
        (self.build / "taste.json").write_text(json.dumps(taste))

    def made(self):
        r = make(self.ws, "--seconds", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        info = json.loads((self.build / "music.json").read_text())
        bed = self.build / "music" / "bed.wav"
        return info, seconds_of(bed), bed.read_bytes()

    def test_research_drafts_a_music_brief_and_the_storyboard_carries_it(self):
        m = self.drafted
        self.assertEqual(set(m), {"styles", "avoid"})
        self.assertTrue(m["avoid"])
        md = (self.build / "storyboards" / "editorial-quiet" / "storyboard.md").read_text()
        self.assertIn("The music brief (taste.json `music`): " + json.dumps(m), md)
        self.assertIn("\nMixed: ", md)

    def test_the_bed_is_the_winning_looks_recipe_at_the_boards_tempo(self):
        self.brief(BRIEF)
        info, seconds, _ = self.made()
        board = json.loads((self.build / "storyboards" / "editorial-quiet" / "storyboard.json").read_text())
        self.assertEqual(info["recipe"], board["music"]["recipe"])
        self.assertAlmostEqual(info["bpm"], board["music"]["bpm"], delta=0.01)
        self.assertIn("(chosen by the look)", info["origin"])
        self.assertGreater(seconds, 1.5)
        md = (self.build / "storyboards" / "editorial-quiet" / "storyboard.md").read_text()
        self.assertIn(f"\nMusic: {info['origin']}.\n", md)

    def test_a_track_the_person_placed_wins(self):
        self.brief(BRIEF)
        placed = self.build / "music" / "source.wav"
        placed.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=2", str(placed)], check=True)
        self.addCleanup(placed.unlink, missing_ok=True)
        r = make(self.ws, "--seconds", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        info = json.loads((self.build / "music.json").read_text())
        self.assertEqual((info["file"], info["origin"]), (str(placed.resolve()), "their own track, music/source.wav"))
        self.assertTrue(placed.exists())
        md = (self.build / "storyboards" / "editorial-quiet" / "storyboard.md").read_text()
        self.assertIn("\nMusic: their own track, music/source.wav.\n", md)


class Frozen(unittest.TestCase):
    @staticmethod
    def found(*starts):
        err = "".join(f"[freezedetect @ 0x0] lavfi.freezedetect.freeze_start: {t}\n" for t in starts)
        return lambda *a, **k: subprocess.CompletedProcess(a, 0, "", err)

    def test_a_page_settling_into_the_stop_is_the_ending_and_a_stall_before_it_is_frozen(self):
        # the last frames of a closing page's eased build read as still to freezedetect: a stretch from there is the
        # ending; one that starts earlier is a stalled picture
        self.assertEqual(qa.frozen("film.mp4", 13.5, self.found(13.433333)), [])
        self.assertEqual(qa.frozen("film.mp4", 13.5, self.found(6.2, 13.2)), [6.2, 13.2])
        self.assertEqual(qa.frozen("film.mp4", spawn=self.found(14.9)), [14.9])
