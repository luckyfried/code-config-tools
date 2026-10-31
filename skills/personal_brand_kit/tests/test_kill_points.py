"""A command stopped at any point leaves nothing the next command reads wrongly. Each test stops a command where a kill
would (an exception at the write it names) or holds what the command waits on, then reads the run as the next command
would: out/ changes with the reel last, deliver holds the render lock, an index goes before the files it names change,
an input moves in whole, the critic's round belongs to its cut, tools resolve before the lock, and a temp name comes
from its destination."""
import contextlib
import hashlib
import io
import json
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
import chunks  # noqa: E402
import film  # noqa: E402
import grade  # noqa: E402
import material  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

sys.path.insert(0, str(KIT / "tests"))
import fixture  # noqa: E402

PIL = unittest.skipUnless(fixture.HAVE_PIL, "Pillow is not installed")


class Killed(Exception):
    pass


def safe(film_, fmt, report):
    """QA's safe row for one film read against its render report, every measurement of the picture itself clean."""
    stream = {"codec_type": "video", "width": 1080, "height": 1080, "codec_name": "h264", "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}
    lo = qa.storyboard.LENGTH[0]
    with mock.patch.object(qa, "probe", return_value={"streams": [stream], "format": {"duration": str(lo)}}), \
            mock.patch.object(qa, "detect", return_value=[]), mock.patch.object(qa, "yavg", return_value=[0.4]), \
            mock.patch.object(qa, "held_from", return_value=lo):
        res = qa.Checks()
        qa.picture(res, film_, fmt, {}, str(report))
    return next(r for r in res if r[0] == "safe")[1]


class InRun(unittest.TestCase):
    """Each test in a scratch run of its own, as the working folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.ws = Path(self.tmp.name)
        self.here = os.getcwd()
        os.chdir(self.ws)

    def tearDown(self):
        os.chdir(self.here)
        self.tmp.cleanup()

    def drafted(self, letter="a"):
        """The fixture's person in this run, with look `letter` drafted from it."""
        fixture.make(self.ws)
        run = storyboard.Run()
        storyboard.write_board(run, letter, run.trio[0])
        return run

    def look(self, letter="a"):
        """A drafted look's files as the vote reads them, without drawing it."""
        d = storyboard.BOARDS / letter
        d.mkdir(parents=True, exist_ok=True)
        (d / "sheet.png").write_bytes(b"png")
        _env.write_json(d / "plan.json", {"reel": {"seconds": 20, "cuts": []}})
        _env.write_json(d / "board-reel.json", {"name": "Kinetic type", "style": "kinetic-type"})


class A_OutChangesWithTheReelLast(InRun):
    OLD, NEW = {"jobs": 4, "failed": 0, "set": "old"}, {"jobs": 4, "failed": 0, "set": "new"}
    REPORT, STAGED = Path("render/film-report.json"), Path("render/.film-report.part.json")

    def made(self, *rels):
        """A render's set in out.part/ and its report beside the name QA reads, over a published old set and report."""
        part = Path("out.part")
        for rel in rels:
            (part / rel).parent.mkdir(parents=True, exist_ok=True)
            (part / rel).write_text("new " + rel)
            (Path("out") / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path("out") / rel).write_text("old " + rel)
        _env.write_json(self.REPORT, self.OLD)
        _env.write_json(self.STAGED, self.NEW)
        return part

    def safe(self, film_):
        return safe(film_, "square", self.REPORT)

    def test_the_reel_moves_into_out_after_every_other_file_and_the_report_after_the_reel(self):
        part = self.made("film.mp4", "film-square.mp4", "film-wide.mp4", "story.png", "stills.json", "stills/01-hook.png")
        Path("out/review.html").write_text("delivered")
        Path("out/stills/09-old.png").write_text("old")
        moved, real = [], os.replace
        with mock.patch("os.replace", side_effect=lambda a, b: (moved.append(Path(b)), real(a, b))):
            film.publish(part)
        into_out = [m for m in moved if m.parts[0] == "out"]
        self.assertEqual(into_out[-1], Path("out/film.mp4"))
        self.assertEqual(len(into_out), 6)
        self.assertEqual(moved[-1], self.REPORT)
        self.assertFalse(Path("out/review.html").exists())
        self.assertFalse(Path("out/stills/09-old.png").exists())
        self.assertEqual(_env.read_json(self.REPORT), self.NEW)

    def test_a_promotion_stopped_part_way_then_a_retry_stopped_before_its_promotion_leaves_a_set_qa_refuses(self):
        part = self.made("film.mp4", "film-square.mp4", "film-wide.mp4")
        real, n = os.replace, []

        def one_then_killed(a, b):
            n.append(b)
            if len(n) > 1:
                raise Killed
            real(a, b)
        with mock.patch("os.replace", side_effect=one_then_killed), self.assertRaises(Killed):
            film.publish(part)
        self.assertEqual(sorted(p.read_text()[:3] for p in Path("out").glob("*.mp4")), ["new", "old", "old"])
        self.assertFalse(self.REPORT.exists())
        self.assertFalse(self.safe(Path("out/film-square.mp4")))
        # the retry: every chunk is whole, so the render only joins and reports; the kill lands before its promotion
        rep = {"jobs": 4, "failed": 0, "findings": [], "seconds": 1.0, "chunks": []}
        with mock.patch.object(chunks, "render", return_value=rep):
            studio.render([], "film", run=mock.Mock())
        self.assertFalse(self.REPORT.exists())
        self.assertFalse(self.safe(Path("out/film-square.mp4")))


class B_DeliverHoldsTheLock(InRun):
    def test_deliver_refuses_while_a_render_holds_the_run_and_writes_nothing(self):
        run = self.ws / "build" / "20261022T000000Z"
        run.mkdir(parents=True)
        for name, data in (("library.json", {"handle": "h"}), ("taste.json", {"x": 1}), ("brand.json", {"handle": "h"}),
                           ("winner.json", {"board": "a"})):
            (run / name).write_text(json.dumps(data))
        env = dict(os.environ, BRAND_RUN=str(run), CSC_DISABLE_KEYCHAIN="1")
        with chunks.lock(run / "render", "film"):
            r = subprocess.run([sys.executable, str(KIT / "scripts" / "deliver.py")], cwd=run, env=env, capture_output=True,
                               text=True, timeout=600)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("a render named film is already running", r.stderr)
        self.assertEqual(list((run / "out").rglob("*")), [], r.stdout + r.stderr)

    def test_every_process_the_gate_starts_under_deliver_goes_through_its_lock(self):
        _env.tools()
        started = []

        class Held:
            def spawn(self, argv, **kw):
                started.append(Path(argv[0]).name)
                return subprocess.CompletedProcess(argv, 0, "{}", "")
        Path("b.json").write_text(json.dumps({"beats": [{"id": "hook", "frames": 30}], "bpm": 120}))
        _env.write_json("film.json", {"boards": {f: "b.json" for f in ("reel", "square", "wide")}, "findings": [], "hash": "h"})
        _env.write_json("music.json", {"file": "music/source.wav"})
        _env.write_json(studio.report_of("film"), {"jobs": 2, "failed": 0, "findings": [], "made": {"formats": list(qa.FILMS), "stories": False}})
        for f in qa.FILMS.values():
            f.parent.mkdir(exist_ok=True)
            f.write_bytes(b"film")
        spawn = qa.spawn
        with mock.patch("subprocess.run", side_effect=AssertionError("a process started outside the lock")), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                qa.gate(Held())
            finally:
                qa.spawn = spawn
        self.assertGreaterEqual(len(started), 3 * 4)
        self.assertEqual(set(started), {Path(_env.ffprobe()).name, Path(_env.ffmpeg()).name})


class C_AnIndexGoesFirst(InRun):
    @PIL
    def test_a_draft_stopped_after_one_board_leaves_the_look_without_a_plan(self):
        run = self.drafted()
        self.assertTrue(Path("storyboards/a/plan.json").exists())
        real, n = _env.write_json, []

        def one_board_then_killed(path, obj):
            n.append(path)
            if len(n) > 1:
                raise Killed
            real(path, obj)
        with mock.patch.object(_env, "write_json", one_board_then_killed), self.assertRaises(Killed):
            storyboard.write_board(run, "a", run.trio[0])
        self.assertFalse(Path("storyboards/a/plan.json").exists())
        with self.assertRaises(SystemExit):
            storyboard.load_plans("a")

    def test_a_new_draft_removes_film_json_before_its_first_board(self):
        Path("film.json").write_text("{}")
        with mock.patch.object(material, "build", side_effect=Killed), self.assertRaises(Killed):
            storyboard.cmd_draft(None, None)
        self.assertFalse(Path("film.json").exists())

    def test_a_draft_stopped_after_the_new_studio_data_and_before_its_boards_leaves_nothing_to_vote_on(self):
        self.look()
        Path("out").mkdir()
        Path("out/boards.png").write_bytes(b"png")
        for name in ("cut", "film"):
            _env.write_json(studio.report_of(name), {"jobs": 4, "failed": 0, "findings": []})
        with mock.patch.object(material, "build", return_value={}), \
                mock.patch.object(storyboard, "Run", return_value=mock.Mock(trio=["kinetic-type"])), \
                mock.patch.object(storyboard, "write_board", side_effect=Killed), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(Killed):
            storyboard.cmd_draft(None, None)
        with self.assertRaises(SystemExit):
            vote.looks()
        self.assertFalse(Path("out/boards.png").exists())
        self.assertFalse(studio.report_of("cut").exists() or studio.report_of("film").exists())

    @PIL
    def test_material_removes_studio_json_before_it_clears_the_folders(self):
        for name in ("brand.json", "library.json", "photo_index.json", "research.json"):
            Path(name).write_text('{"x": 1}')
        Path("studio.json").write_text("{}")
        with mock.patch.object(grade, "ensure_recipe", return_value={"filter": "null"}), \
                mock.patch("shutil.rmtree", side_effect=Killed), self.assertRaises(Killed):
            material.build()
        self.assertFalse(Path("studio.json").exists())

    def test_a_cut_removes_cut_json_before_it_renders(self):
        Path("cut.json").write_text('{"sha": "old"}')
        with mock.patch.object(film, "film", return_value=({}, {"reel": {"beats": []}})), \
                mock.patch.object(film, "timed", side_effect=Killed), self.assertRaises(Killed):
            film.cmd_cut(None, None)
        self.assertFalse(Path("cut.json").exists())


class C_TheInvalidationGoesFirst(InRun):
    @PIL
    def test_sheets_removes_each_sheet_and_the_persons_page_before_its_frames_render(self):
        import compose
        for letter in compose.LETTERS:
            self.look(letter)
        Path("out").mkdir()
        Path("out/boards.png").write_bytes(b"the old looks")
        plan = {"reel": {"rests": {"hook": 5, "closer": 40}, "board": {}}}
        with mock.patch.object(storyboard, "load_plans", return_value=plan), mock.patch.object(studio, "still", return_value={}), \
                mock.patch.object(studio, "render", side_effect=Killed), self.assertRaises(Killed):
            storyboard.cmd_sheets(None, None)
        self.assertEqual([l for l in compose.LETTERS if (storyboard.BOARDS / l / "sheet.png").exists()], [])
        self.assertFalse(Path("out/boards.png").exists())

    def test_snap_removes_film_json_before_it_writes_the_boards_again(self):
        self.look()
        Path("winner.json").write_text('{"board": "a"}')
        Path("film.json").write_text("{}")
        plan = {"reel": {"board": {"style": "kinetic-type", "bpm": 120}}}
        with mock.patch.object(storyboard, "load_plans", return_value=plan), \
                mock.patch.object(storyboard, "write_board", side_effect=Killed), self.assertRaises(Killed):
            storyboard.cmd_snap(None, mock.Mock())
        self.assertFalse(Path("film.json").exists())


@PIL
class V_AReportVouchesForOneCut(InRun):
    """A cut rendered and passed, then the cut changes: the old outputs stay, and QA refuses them as the new cut's."""
    CLEAN = {"jobs": 4, "failed": 0, "findings": []}

    def setUp(self):
        super().setUp()
        Path("out").mkdir()
        for f in ("out/film.mp4", "out/film-square.mp4", "out/film-wide.mp4", "cut.mp4"):
            Path(f).write_bytes(b"the old cut's film")
        for name in ("cut", "film"):
            _env.write_json(studio.report_of(name), self.CLEAN)
        run = self.drafted()
        Path("winner.json").write_text('{"board": "a"}')
        Path("film.json").write_text("{}")
        Path("cut.json").write_text(json.dumps({"sha": qa.sha(Path("cut.mp4"))}))
        sha = film.sha(film.CUT)
        _env.write_json("qa/check.json", {"film": sha, "pass": True, "figures": {}})
        _env.write_json("critic/verdict.json", {"film": sha, "verdict": "ship"})
        self.assertIsNone(film.ready())
        self.assertTrue(safe(Path("cut.mp4"), "reel", studio.report_of("cut")))
        self.assertTrue(safe(Path("out/film-square.mp4"), "square", studio.report_of("film")))
        with contextlib.redirect_stdout(io.StringIO()):
            storyboard.cmd_snap(None, run)

    def refused(self):
        self.assertFalse(Path("cut.mp4").exists() and safe(Path("cut.mp4"), "reel", studio.report_of("cut")))
        for fmt, film_ in qa.FILMS.items():
            self.assertFalse(safe(film_, fmt, studio.report_of("cut" if fmt == "reel" else "film")))

    def test_a_snap_that_changes_the_cut_leaves_nothing_qa_passes(self):
        self.refused()

    def test_a_snap_that_changes_the_cut_leaves_no_cut_for_the_critic_or_the_film(self):
        self.assertIsNotNone(film.ready())
        with self.assertRaises(SystemExit):
            vote.cmd_cut(None)

    def test_the_cut_set_is_the_reports_studio_names(self):
        self.assertEqual(storyboard.CUT_SET[:2], (studio.report_of("cut"), studio.report_of("film")))

    def test_a_snap_then_a_render_stopped_before_its_promotion_leaves_nothing_qa_passes(self):
        rep = {"jobs": 4, "failed": 0, "findings": [], "seconds": 1.0, "chunks": []}
        with mock.patch.object(chunks, "render", return_value=rep):
            studio.render([], "film", run=mock.Mock())
            studio.render([], "cut", run=mock.Mock())
        self.refused()


class W_AVerdictIsTheBallotAsItReadsNow(InRun):
    def test_a_ship_then_a_paragraph_cut_short_leaves_the_gate_red(self):
        Path("cut.mp4").write_bytes(b"the cut")
        film_ = {"scores": dict.fromkeys(vote.CRITERIA, 5), "paragraph": " ".join(["the film holds"] * 10)}
        data = {"round": 1, "film": qa.sha(Path("cut.mp4")),
                "critics": {c: {"boards": {"film": dict(film_)}} for c in vote.CUT_PANEL}}
        _env.write_json("critic/cut-1.json", data)
        Path("film.json").write_text(json.dumps({"boards": dict.fromkeys(qa.FILMS, "none.json"), "findings": []}))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vote.cmd_verdict(None), 0)
            data["critics"]["person"]["boards"]["film"]["paragraph"] = "too short now"
            _env.write_json("critic/cut-1.json", data)
            self.assertEqual(vote.cmd_verdict(None), 1)
            with mock.patch.object(qa, "picture"), mock.patch.object(qa, "spawn", subprocess.run, create=True):
                res, _ = qa.gate_checks()
        self.assertFalse(next(r for r in res if r[0] == "critic")[1])


class C_OldFilesGoAfterTheNewIndex(InRun):
    def test_music_make_stopped_before_music_json_keeps_the_source_it_names(self):
        import music
        Path("music").mkdir()
        Path("music/source.mp3").write_text("their track")
        _env.write_json("music.json", {"file": "music/source.mp3"})
        real = _env.write_json

        def killed_at_music_json(path, obj):
            if str(path) == "music.json":
                raise Killed
            real(path, obj)
        made = {"key": "C major", "bpm": 120, "removed": [], "chords": ["C"]}
        with mock.patch.object(music, "picked", return_value={"bpm": 120, "style": "kinetic-type", "sound": []}), \
                mock.patch.object(music.music_engine, "compose", return_value=made), \
                mock.patch.object(_env, "write_json", killed_at_music_json), self.assertRaises(Killed):
            music.cmd_make(mock.Mock(bpm=None, seconds=2.0))
        self.assertTrue(Path(_env.read_json("music.json")["file"]).exists())


    def test_a_master_stopped_before_music_json_leaves_the_master_it_names_as_it_was(self):
        import music
        ff = _env.ffmpeg()
        Path("music").mkdir()
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=3", "-ar", "48000", "music/source.wav"], check=True)
        subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=2", "-ar", "48000", "music/master.wav"], check=True)
        before = Path("music/master.wav").read_bytes()
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav", "master_seconds": 2.0})
        real = _env.write_json

        def killed_at_music_json(path, obj):
            if str(path) == "music.json":
                raise Killed
            real(path, obj)
        with mock.patch.object(_env, "write_json", killed_at_music_json), self.assertRaises(Killed):
            music.cmd_master(mock.Mock(seconds=2.5))
        named = _env.read_json("music.json")
        self.assertEqual(Path(named["master"]).read_bytes(), before)
        self.assertEqual(named["master_seconds"], 2.0)


class C_ACommandReadsTheIndexOfTheSet(InRun):
    def test_an_incomplete_tally_names_no_look_and_leaves_the_pick_to_the_person(self):
        self.look()
        _env.write_json("vote/scores.json", vote.blank(vote.PANEL, ["a"], vote.BOARD_CRITERIA))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vote.cmd_tally(None), 1)
        self.assertFalse(Path("winner.json").exists())
        self.assertFalse(Path("vote.md").exists())

    def test_the_critic_round_refuses_a_cut_without_cut_json(self):
        Path("cut.mp4").write_bytes(b"a cut stopped before its strips")
        _env.write_json("qa/check.json", {"film": hashlib.sha256(b"a cut stopped before its strips").hexdigest()[:16], "figures": {}})
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("cut.json", str(e.exception))
        self.assertFalse(Path("critic/cut-1.json").exists())


class H_APatternFindsOnlyThePersonsName(InRun):
    def test_music_find_takes_the_persons_source_over_a_generated_name_beside_it(self):
        import music
        ff = _env.ffmpeg()
        Path("music").mkdir()
        for name in ("source.made.wav", "made-1.wav", "master-1.wav", "source.mp3"):
            subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=2", "-ar", "48000", f"music/{name}"], check=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_find(mock.Mock(origin=None)), 0)
        self.assertEqual(_env.read_json("music.json")["file"], "music/source.mp3")


    def test_grade_takes_the_photos_and_never_a_temp_name_a_stopped_pick_left(self):
        Path("photos").mkdir()
        Path("photos/01.jpg").write_bytes(b"jpg")
        Path(_env.part(Path("photos/02.jpg"))).write_bytes(b"half a jpg")
        Path("grade.json").write_text("{}")
        graded = []
        with mock.patch.object(grade, "ensure_recipe", return_value={"filter": "null"}), \
                mock.patch.object(_env, "need"), \
                mock.patch.object(grade, "grade_file", side_effect=lambda f, d, flt: (graded.append(f.name), True, "")[1:]):
            grade.grade_photos()
        self.assertEqual(graded, ["01.jpg"])


@PIL
class D_AnInputMovesInWhole(InRun):
    def test_a_photograph_stopped_before_its_move_is_not_kept_as_made(self):
        from PIL import Image
        Image.new("RGB", (40, 30), "red").save("src.jpg")
        import picks
        with mock.patch("os.replace", side_effect=Killed), self.assertRaises(Killed):
            picks.prepare("src.jpg")
        self.assertEqual(list(Path("photos").glob("[!.]*.jpg")), [])
        self.assertTrue(Path(picks.prepare("src.jpg")).exists())

    def test_a_graded_copy_stopped_before_its_move_is_not_kept_as_made(self):
        from PIL import Image
        Image.new("RGB", (40, 30), "red").save("src.jpg")
        Path("public/graded").mkdir(parents=True)
        with mock.patch("os.replace", side_effect=Killed), self.assertRaises(Killed):
            grade.grade_file(Path("src.jpg"), Path("public/graded/src.jpg"), "null")
        self.assertFalse(Path("public/graded/src.jpg").exists())


class E_ARoundBelongsToItsCut(InRun):
    def setUp(self):
        super().setUp()
        Path("cut.mp4").write_bytes(b"cut one")
        Path("cut.json").write_text("{}")
        self.check()
        vote.cmd_cut(None)
        f = Path("critic/cut-1.json")
        data = json.loads(f.read_text())
        for c in data["critics"].values():
            for b in c["boards"].values():
                b["scores"] = {k: 4 for k in b["scores"]}
        f.write_text(json.dumps(data))

    def check(self):
        _env.write_json("qa/check.json", {"film": hashlib.sha256(Path("cut.mp4").read_bytes()).hexdigest()[:16], "figures": {}})

    def test_the_same_cut_keeps_its_round_and_its_scores(self):
        vote.cmd_cut(None)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
        self.assertTrue(all(v == 4 for c in _env.read_json("critic/cut-1.json")["critics"].values()
                            for b in c["boards"].values() for v in b["scores"].values()))

    def test_a_new_cut_opens_a_new_round(self):
        Path("cut.mp4").write_bytes(b"cut two")
        self.check()
        vote.cmd_cut(None)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])


class F_ToolsResolveBeforeTheLock(InRun):
    def test_the_lock_is_taken_after_setup(self):
        seen = []

        @contextlib.contextmanager
        def lock(render_dir, name):
            seen.append(_env._TOOLS is not None)
            yield None
        saved = _env._TOOLS
        _env._TOOLS = None
        try:
            with mock.patch.object(chunks, "lock", lock), studio.lock("film"):
                pass
        finally:
            _env._TOOLS = saved
        self.assertEqual(seen, [True])


class G_ATempNameComesFromItsDestination(unittest.TestCase):
    def test_each_destination_has_its_own_temp_name_beside_it_with_its_suffix(self):
        self.assertEqual(_env.part("music/master.wav"), Path("music/.master.part.wav"))
        self.assertNotEqual(_env.part("music/master.wav"), _env.part("music/source.wav"))
        self.assertEqual(_env.part("storyboards/a/sheet.png").parent, Path("storyboards/a"))


if __name__ == "__main__":
    unittest.main()
