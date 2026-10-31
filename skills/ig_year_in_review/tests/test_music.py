"""music.py: a composed bed keeps its own grid, and the bed lifts into the story's peak where the board's peak month
opens its photograph and ends."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import music  # noqa: E402


class Music(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.here = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.here)
        self.tmp.cleanup()

    def test_analyze_leaves_a_composed_beds_own_grid(self):
        info = {"file": "music/bed.wav", "recipe": "swiss-grid", "bpm": 123.0, "beats": [0.0, 0.488, 0.976, 1.463, 1.951],
                "downbeats": [0.0, 1.951]}
        Path("music.json").write_text(json.dumps(info))
        self.assertEqual(music.cmd_analyze(types.SimpleNamespace()), 0)
        self.assertEqual(json.loads(Path("music.json").read_text()), info)

    def test_the_bed_lifts_into_the_peak_months_photograph_and_out_at_its_end(self):
        board = {"bpm": 123.0, "sound": [], "year": {"months": [
            {"id": "m09", "peak": False, "at": {"open": [50.0, 0.8], "end": 56.0}},
            {"id": "m10", "peak": True, "at": {"open": [56.55, 0.8], "end": 66.0}}]}}
        Path("storyboards/swiss-grid").mkdir(parents=True)
        Path("storyboards/swiss-grid/board-reel.json").write_text(json.dumps(board))
        land, end = music.peak("swiss-grid", 123.0)
        self.assertAlmostEqual(land, 56.55 * 60 / 123.0)
        self.assertAlmostEqual(end, 66.0 * 60 / 123.0)
        # at the bed's double tempo the same moments fall at twice the beat count
        self.assertAlmostEqual(music.peak("swiss-grid", 246.0)[0], 56.55 * 60 / 123.0)
        self.assertIsNone(music.peak(None, 123.0))

    def test_make_hands_the_engine_the_peak(self):
        got = {}

        def compose(*args, **kw):
            got.update(kw)
            return {"key": "G aeolian", "bpm": 123.0, "removed": [], "chords": []}
        board = {"bpm": 123.0, "sound": [], "year": {"months": [{"id": "m10", "peak": True, "at": {"open": [8.0, 0.8], "end": 16.0}}]}}
        Path("storyboards/swiss-grid").mkdir(parents=True)
        Path("storyboards/swiss-grid/board-reel.json").write_text(json.dumps(board))
        Path("winner.json").write_text(json.dumps({"board": "swiss-grid"}))
        with mock.patch.object(music.music_engine, "compose", compose), mock.patch.object(music, "MUSIC", Path("music")):
            music.cmd_make(types.SimpleNamespace(seconds=20.0, bpm=123.0))
        self.assertEqual(got.get("peak"), (8.0 * 60 / 123.0, 16.0 * 60 / 123.0))


if __name__ == "__main__":
    unittest.main()
