"""The vote gates the cut: storyboard.py snap times only the board in winner.json and takes no --board, and a new draft
removes the old vote's winner and scores, so a board drafted again is voted again; it removes the timed films and the
style sheets and the boards too, before its first photograph changes, so nothing reads them against the new board. A
snap stopped between two formats leaves no film.json. vote.py cut refuses an out/ with no render report and a film
whose measurements or frames are another film's, and run again for the same film keeps its round. The gate's critic row refuses a cut round the vote refuses (a score missing or a
paragraph under 25 words) and names the reason.

    python3 -I -m unittest discover -s S/tests -p test_vote_gate.py
"""
import argparse
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import storyboard  # noqa: E402


class Stop(Exception):
    pass


class VoteGate(unittest.TestCase):
    def setUp(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.run_dir = home / "build" / "r1"
        self.run_dir.mkdir(parents=True)
        (home / "build" / "RUN").write_text("r1\n")
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        for patch in (mock.patch.object(_env, "HOME", home), mock.patch.dict(os.environ, {"TR_RUN": ""})):
            patch.start()
            self.addCleanup(patch.stop)

    def storyboard(self, *argv):
        """storyboard.py with argv; returns the exit message, or None when it returned."""
        with mock.patch.object(sys, "argv", ["storyboard.py", *argv]), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            try:
                storyboard.main()
            except SystemExit as e:
                return str(e.code)
        return None

    def test_snap_with_no_winner_refuses_naming_the_vote(self):
        why = self.storyboard("snap")
        self.assertIn("no board picked", why or "")
        self.assertIn("vote.py tally", why)
        self.assertIn("vote.py pick", why)
        self.assertFalse((self.run_dir / "film.json").exists())

    def test_snap_refuses_a_board_named_on_the_command_line(self):
        (self.run_dir / "storyboards" / "1").mkdir(parents=True)
        why = self.storyboard("snap", "--board", "1")
        self.assertIn("--board", why or "")
        self.assertIn("winner.json", why)
        self.assertFalse((self.run_dir / "film.json").exists())

    def test_a_new_draft_removes_the_old_votes_winner_and_scores(self):
        d = self.run_dir
        _env.write_json(d / "taste.json", {"words": {}})
        (d / "taste.md").write_text("taste")
        _env.write_json(d / "points.json", {"a": [0.5, 0.5]})
        _env.write_json(d / "winner.json", {"board": "1"})
        (d / "vote").mkdir()
        _env.write_json(d / "vote" / "scores.json", {"critics": []})
        for name in ("film.json", "film-landscape.json", "film-square.json"):
            _env.write_json(d / name, {"seconds": 1})
        (d / "storyboards" / "1").mkdir(parents=True)
        (d / "storyboards" / "1" / "sheet.png").write_bytes(b"the old board's sheet")
        _env.write_json(d / "storyboards" / "1" / "storyboard.json", {"id": "1"})
        with mock.patch.object(storyboard, "stop_photos", side_effect=Stop), self.assertRaises(Stop):
            self.storyboard("draft")
        self.assertFalse((d / "winner.json").exists())
        self.assertFalse((d / "vote" / "scores.json").exists())
        left = [n for n in ("film.json", "film-landscape.json", "film-square.json", "storyboards/1/sheet.png",
                            "storyboards/1/storyboard.json") if (d / n).exists()]
        self.assertEqual(left, [])

    def test_a_snap_stopped_between_two_formats_leaves_no_film_json(self):
        d = self.run_dir
        _env.write_json(d / "winner.json", {"board": "1"})
        _env.write_json(d / "storyboards" / "1" / "storyboard.json", {"id": "1", "style": "cinematic-letterbox"})
        _env.write_json(d / "film.json", {"board": "the earlier one"})
        real = _env.write_json

        def write_json(path, obj):
            if Path(path).name == "film-square.json":
                raise Stop
            real(path, obj)
        with mock.patch.object(storyboard, "check_board", return_value=([], [])), \
                mock.patch.object(storyboard, "film_of", side_effect=lambda b, m, fmt: {"fmt": fmt}), \
                mock.patch.object(storyboard, "monotony", return_value=[]), mock.patch.object(_env, "write_json", write_json), \
                self.assertRaises(Stop):
            self.storyboard("snap")
        self.assertFalse((d / "film.json").exists())

    def cut(self, seconds):
        """A timed cut of board 1 as snap writes it, `seconds` long."""
        return {"id": "1", "seconds": seconds, "cuts": [1.0], "bpm": 120, "beats": [{"frames": 60, "bars": 4}], "sound": [],
                "route": {"closer": {"still": 0}}, "stories": ["a", "b"], "rests": {"a": 5, "b": 40, "closer": 50},
                "timeline": [{"id": "hook", "start": 0, "frames": 60}]}

    def rendered(self):
        """A run whose out/ and clean render report are the films of the earlier cut, and whose winner snap times again."""
        d = self.run_dir
        _env.write_json(d / "winner.json", {"board": "1"})
        _env.write_json(d / "storyboards" / "1" / "storyboard.json", {"id": "1", "style": "cinematic-letterbox"})
        for name in ("film.json", "film-landscape.json", "film-square.json"):
            _env.write_json(d / name, self.cut(2.0))
        (d / "out").mkdir()
        for name in ("film.mp4", "film-16x9.mp4", "film-square.mp4"):
            (d / "out" / name).write_bytes(b"the earlier cut")
        _env.write_json(d / "render" / "film-report.json", {"jobs": 3, "failed": 0, "findings": []})

    def snap_a_new_cut(self):
        """snap times a new cut of the same length."""
        new = dict(self.cut(2.0), cuts=[0.5, 1.5])
        with mock.patch.object(storyboard, "check_board", return_value=([], [])), mock.patch.object(storyboard, "monotony", return_value=[]), \
                mock.patch.object(storyboard, "film_of", side_effect=lambda b, m, fmt: new), mock.patch.object(storyboard.studio, "public"):
            self.assertIsNone(self.storyboard("snap"))
        self.assertEqual(_env.read_json(self.run_dir / "film.json")["cuts"], [0.5, 1.5])

    def checks(self, which):
        """qa.py's `which` checks (film_checks or gate_checks) on the run as it stands, its tools faked: {row: (pass, detail)}."""
        import qa

        class Run:
            name = "test"

            def spawn(_, argv, **kw):
                return subprocess.CompletedProcess(argv, 0, "10.0" if "csv=p=0" in argv else "{}", "")
        with mock.patch.object(_env, "tools", return_value={"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                mock.patch.object(storyboard, "check_board", return_value=([], [])), mock.patch.object(storyboard, "monotony", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()):
            res = getattr(qa, which)(Run())
        return {r[0]: (r[1], r[2]) for r in res if r[1] is not None}

    def read(self):
        """qa.py check and film.py frames as run on the film now in out/: both name its digest."""
        import qa
        for f in ("qa/check.json", "frames/frames.json"):
            _env.write_json(self.run_dir / f, {"film": qa.sha(self.run_dir / "out" / "film.mp4")})

    def safe(self):
        """qa.py's safe check on the run as it stands."""
        return self.checks("film_checks")["safe"][0]

    def audio_row(self, music):
        """qa's audio row on a rendered run whose music.json is `music`: nine cues over six beats, the film's track probed as
        aac at 192 kbps and measured at -14 LUFS, so the row turns on the stems' numbers alone."""
        import qa
        self.rendered()
        _env.write_json(self.run_dir / "film.json", dict(self.cut(2.0), beats=[{"frames": 60, "bars": 4}] * 6, sound=[{"kind": "hit", "at": 0.0}] * 9))
        _env.write_json(self.run_dir / "music.json", music)
        os.chdir(self.run_dir)
        streams = {"streams": [{"codec_type": "video", "width": 1080, "height": 1920}, {"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}],
                   "format": {"duration": "2.0"}}
        with mock.patch.object(qa, "probe", return_value=streams), mock.patch.object(qa, "loudness", return_value=(-14.0, -2.0)):
            return self.checks("film_checks")["audio"]

    def test_the_audio_row_is_red_when_the_effects_stem_is_peak_normalized_over_the_bed(self):
        ok, detail = self.audio_row({"file": "music/source.wav", "bed_lufs": -21.4, "fx_lufs": -16.3})
        self.assertFalse(ok)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS, -5.1 LU under (at least 7); 9 sound cues over 6 beats", detail)

    def test_the_audio_row_is_green_with_the_effects_eight_lu_under_the_bed_and_prints_the_counts(self):
        ok, detail = self.audio_row({"file": "music/source.wav", "bed_lufs": -21.4, "fx_lufs": -29.4})
        self.assertTrue(ok, detail)
        self.assertIn("aac 192 kbps, -14.0 LUFS integrated, true peak -2.0 dBTP; bed -21.4 LUFS, effects -29.4 LUFS, 8.0 LU under (at least 7); 9 sound cues over 6 beats", detail)

    def test_qa_refuses_the_earlier_cuts_films_once_snap_times_a_new_cut(self):
        self.rendered()
        os.chdir(self.run_dir)
        self.assertTrue(self.safe())
        self.snap_a_new_cut()
        self.assertFalse(self.safe())

    def test_qa_refuses_the_earlier_cuts_films_when_the_new_cuts_render_is_stopped_before_its_moves(self):
        import film
        self.rendered()
        self.snap_a_new_cut()

        def bridge(jobs, name, run=None):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_text("new")
            return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}
        with mock.patch.object(film.studio, "render", bridge), mock.patch.object(film.studio, "props", return_value={}), \
                mock.patch.object(film, "mux", side_effect=Stop), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(Stop):
            film.cmd_render(argparse.Namespace(also=list(film.ALSO)), None)
        self.assertEqual((self.run_dir / "out" / "film.mp4").read_bytes(), b"the earlier cut")
        self.assertFalse(self.safe())

    def test_the_gate_refuses_a_cut_round_the_vote_refuses_and_names_the_reason(self):
        import qa
        import vote
        self.rendered()
        os.chdir(self.run_dir)
        full = ("The photograph fills the frame at every beat and the camera moves through it toward what it looks at, each line their own; "
                "the closer sets the trip's name and dates and holds still.")
        data = vote.blank(vote.CUT_PANEL, ["film"])
        for c in vote.CUT_PANEL:
            data["critics"][c]["boards"]["film"].update(scores={k: 4 for k in vote.CRITERIA}, paragraph=full)
        data["critics"]["person"]["boards"]["film"]["paragraph"] = "my week in my own lines, the way I walked it"
        data.update(round=1, film=qa.sha(qa.FILM), fixed=None)
        self.read()
        _env.write_json(self.run_dir / "critic" / "cut-1.json", data)
        ok, detail = self.checks("gate_checks")["critic"]
        self.assertFalse(ok)
        self.assertIn("person / board film: the paragraph needs at least 25 words", detail)
        data["critics"]["person"]["boards"]["film"]["paragraph"] = full
        _env.write_json(self.run_dir / "critic" / "cut-1.json", data)
        ok, detail = self.checks("gate_checks")["critic"]
        self.assertTrue(ok)
        self.assertIn("lowest 4", detail)

    def test_a_new_draft_removes_the_render_report_with_the_cut(self):
        self.rendered()
        d = self.run_dir
        _env.write_json(d / "taste.json", {"words": {}})
        (d / "taste.md").write_text("taste")
        _env.write_json(d / "points.json", {"a": [0.5, 0.5]})
        with mock.patch.object(storyboard, "stop_photos", side_effect=Stop), self.assertRaises(Stop):
            self.storyboard("draft")
        self.assertFalse((d / "render" / "film-report.json").exists())

    def test_cut_refuses_an_out_folder_with_no_render_report(self):
        import vote
        (self.run_dir / "out").mkdir()
        (self.run_dir / "out" / "film.mp4").write_bytes(b"a reel from a render stopped in its moves")
        os.chdir(self.run_dir)
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("not a finished render", str(e.exception.code))
        self.assertFalse((self.run_dir / "critic" / "cut-1.json").exists())

    def test_cut_run_again_for_the_same_film_keeps_its_round(self):
        import vote
        (self.run_dir / "render").mkdir()
        (self.run_dir / "render" / "film-report.json").write_text("{}")
        (self.run_dir / "out").mkdir()
        film = self.run_dir / "out" / "film.mp4"
        film.write_bytes(b"cut one")
        self.read()

        def cut():
            with mock.patch.object(sys, "argv", ["vote.py", "cut"]), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(vote.main(), 0)
            return sorted(p.name for p in (self.run_dir / "critic").glob("cut-*.json"))
        self.assertEqual(cut(), ["cut-1.json"])
        self.assertEqual(cut(), ["cut-1.json"])
        film.write_bytes(b"cut two")
        self.read()
        self.assertEqual(cut(), ["cut-1.json", "cut-2.json"])

    def test_cut_refuses_a_film_whose_frames_were_not_cut_from_it(self):
        import vote
        (self.run_dir / "render").mkdir()
        (self.run_dir / "render" / "film-report.json").write_text("{}")
        (self.run_dir / "out").mkdir()
        film = self.run_dir / "out" / "film.mp4"
        film.write_bytes(b"cut one")
        self.read()
        os.chdir(self.run_dir)
        with contextlib.redirect_stdout(io.StringIO()):
            vote.cmd_cut(None)
        film.write_bytes(b"cut two, rendered after the fix")
        import qa
        _env.write_json(self.run_dir / "qa" / "check.json", {"film": qa.sha(film)})
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("frames/ are not cut from out/film.mp4", str(e.exception.code))
        self.assertEqual(sorted(p.name for p in (self.run_dir / "critic").glob("cut-*.json")), ["cut-1.json"])


if __name__ == "__main__":
    unittest.main()
