"""The critic scores the six scored rules against the bar and never stops the render: a scored round under the bar is
still a scored cut, and its scores are stated. Round 1 under the bar names the rule furthest under it to fix once;
after that the cut renders as the best one. The cut writes one tile per sound cue, the frames around the cue over the
waveform of the film's sound, so the cue's placement is read from the run's own files.

    python3 -I -m unittest discover -s S/tests -p test_verdict.py
"""
import contextlib
import io
import os
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
import proof  # noqa: E402
import vote  # noqa: E402

RULES = ("R1", "R2", "R3", "R4", "R5", "R6")
WORDS = " ".join(["the cut reads this way from its strip, its rests, its cue tiles and its requests"] * 3)
CITED = "R5 rests on every cut row on the beat, the end row and each effect row heard over the bed"


class Verdict(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        Path("render").mkdir()
        Path("render/cut.mp4").write_bytes(b"the cut")
        _env.write_json("render/cut.json", {"cut": "board-and-music"})
        self.sha = proof.digest("render/cut.mp4")

    def round(self, n, scores, film=None):
        data = {"round": n, "film": film or self.sha, "cut": proof.picture("board-and-music", "render/cut.mp4"),
                "sound": {"table": "critic/sound.md", "findings": [], "cited": CITED},
                "critics": {c: {"boards": {"film": {"scores": dict(scores), "paragraph": WORDS}}}
                            for c in ("motion_designer", "person")}}
        _env.write_json(f"critic/cut-{n}.json", data)

    def verdict(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = vote.cmd_verdict(None)
        return rc, out.getvalue()

    def test_the_critic_scores_the_six_scored_rules(self):
        self.assertEqual(tuple(vote.CRITERIA), RULES)
        self.assertEqual((vote.BAR_MEAN, vote.BAR_LEAST), (4.5, 4))

    def test_a_cut_under_the_bar_is_scored_and_its_scores_are_stated(self):
        self.round(1, {r: 3 for r in RULES})
        ok, why = vote.scored(self.sha)
        self.assertTrue(ok, why)
        self.assertIn("under the bar", why)
        self.assertIn("mean 3.0", why)

    def test_a_round_for_another_cut_or_half_filled_is_not_scored(self):
        self.round(1, {r: 5 for r in RULES}, film="old")
        self.assertFalse(vote.scored(self.sha)[0])
        self.round(2, dict({r: 5 for r in RULES}, R4=None))
        self.assertFalse(vote.scored(self.sha)[0])

    def test_round_one_under_the_bar_names_the_rule_furthest_under_it_and_a_spent_budget_renders(self):
        self.round(1, dict({r: 5 for r in RULES}, R3=2, R5=3))
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("FIX ONCE", said)
        self.assertIn("R3", said)
        self.assertIn("render this cut", said)

    def test_under_the_bar_after_the_fix_renders_as_the_best_cut(self):
        self.round(1, {r: 3 for r in RULES}, film="first")
        self.round(2, {r: 3 for r in RULES})
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertIn("UNDER THE BAR", said)

    def test_a_mean_of_four_and_a_half_with_none_under_four_is_at_the_bar(self):
        self.round(1, dict({r: 5 for r in RULES}, R1=4, R2=4))
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertIn("AT THE BAR", said)
        self.round(1, dict({r: 5 for r in RULES}, R1=4, R2=4, R3=4, R4=4))
        self.assertIn("under the bar", vote.scored(self.sha)[1])

    def test_a_critic_entry_that_is_not_scores_and_a_paragraph_is_named_never_a_crash(self):
        self.round(1, {r: 5 for r in RULES})
        data = _env.read_json("critic/cut-1.json")
        data["critics"]["person"]["boards"]["film"] = [{"scores": {r: 5 for r in RULES}, "paragraph": WORDS}]
        _env.write_json("critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("person / board film: needs an object with scores and a paragraph", said)

    def test_the_lower_critic_sets_each_rule(self):
        self.round(1, {r: 5 for r in RULES})
        data = _env.read_json("critic/cut-1.json")
        data["critics"]["person"]["boards"]["film"]["scores"]["R2"] = 3
        s, mean, least = vote.standing(data)
        self.assertEqual((s["R2"], least), (3, 3))

    def test_a_round_is_complete_only_once_its_r5_score_cites_the_sound_read(self):
        self.round(1, {r: 5 for r in RULES})
        data = _env.read_json("critic/cut-1.json")
        data["sound"]["cited"] = "fine"
        _env.write_json("critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("sound / cited", said)
        del data["sound"]
        _env.write_json("critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("no sound read", said)

    def test_a_verdict_on_a_round_of_another_cut_than_the_newest_is_refused(self):
        self.round(1, {r: 5 for r in RULES})
        Path("render/cut.mp4").write_bytes(b"the cut drawn again")
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("not a read of the newest cut", said)


class SoundRead(unittest.TestCase):
    def test_the_sound_read_hears_the_cut_through_the_board_and_music_its_mux_laid(self):
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, True)
        cwd = os.getcwd()
        os.chdir(d)
        self.addCleanup(os.chdir, cwd)
        fx = {"id": "reel", "bpm": 120, "beats": [{"id": "hook"}]}
        _env.write_json("render/board-reel.json", {"beats": [], "effects": fx})
        _env.write_json("music.json", {"master": "music/master.wav", "bpm": 120})
        seen = {}

        def read(*a, **k):
            seen["read"] = (a, k)
            return {"table": "critic/sound.md", "findings": [], "cited": ""}
        import sfx
        with mock.patch.object(sfx, "critic_read", read):
            vote.sound_read(Path("render/cut.mp4"), {"seconds": 15.0})
        (board, record, film, seconds, _, path), k = seen["read"]
        self.assertEqual((board, record, film, seconds, path), (fx, {"master": "music/master.wav", "bpm": 120},
                                                                 "render/cut.mp4", 15.0, vote.SOUND))
        self.assertEqual(k, {"ducked": False}, "the mux lowers the music for its impacts and lays no ducks")
        _env.write_json("render/board-reel.json", {"beats": []})
        with self.assertRaises(SystemExit):
            vote.sound_read(Path("render/cut.mp4"), {"seconds": 15.0})


class CueTiles(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, True)
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        _env.tools()

    def test_each_effect_gets_the_frames_around_it_over_the_waveform(self):
        import film
        Path("render").mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=108x192:r=30:d=4", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=4", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", str(film.CUT)],
                       check=True)
        _env.write_json("music.json", {"onsets": [1.0, 2.5, 3.9], "bpm": 120})
        _env.write_json("film.json", {"music_start": 0.5})
        fx = {"id": "t", "bpm": 120, "beats": [
            {"id": "a", "form": "photo", "start": 0, "layers": [{"kind": "Photo", "at": 0}]},
            {"id": "b", "form": "wall", "start": 4, "layers": [{"kind": "Closer", "at": 4}]}]}
        board = {"bpm": 120, "beats": [{"id": "a", "frames": 60}, {"id": "b", "frames": 60}], "effects": fx}
        film.cue_tiles(types.SimpleNamespace(spawn=subprocess.run), board)
        cues = _env.read_json("frames/cues.json")["cues"]
        self.assertEqual([c["kind"] for c in cues], ["shutter", "impact", "riser"])
        self.assertEqual([c["beat"] for c in cues], ["a", "b", "b"])
        hook, wall, _ = cues
        self.assertEqual(wall["at"], 2.0)
        self.assertEqual(wall["frames"][0], 1.4)
        self.assertEqual(len(wall["frames"]), 8)
        self.assertEqual(hook["frames"][0], 0.0)
        self.assertEqual(wall["music_onsets"], [2.0])
        for c in cues:
            self.assertTrue(Path(c["tile"]).exists(), c["tile"])
        size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", wall["tile"]],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(size, f"{8 * film.TILE_W},{320 + 160}")


if __name__ == "__main__":
    unittest.main()
