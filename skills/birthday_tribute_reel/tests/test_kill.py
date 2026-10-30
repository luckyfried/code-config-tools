"""A command stopped at any point leaves nothing the next command reads wrongly: an index goes before the files it names
change and comes back only when they are whole, an input lands whole under its name, the critic's round is reused for
the same reel, the tools resolve before the run's lock, the gate's processes hold deliver's lock, and a temp name is never
shared between two commands.

    python3 -I -m unittest discover -s S/tests -p test_kill.py
"""
import argparse
import io
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import film  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

PLAIN = types.SimpleNamespace(spawn=subprocess.run)


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name)
        self.B = self.d / "build" / "run"
        self.B.mkdir(parents=True)
        patch = mock.patch.object(_env, "_RUN", self.B)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.d)


class Indexes(Base):
    def test_preview_json_goes_before_the_preview_renders(self):
        pv = self.B / "preview" / "preview.json"
        pv.parent.mkdir()
        pv.write_text('{"hash": "the last cut"}')
        seen = []

        def render(jobs, name, run):
            seen.append(pv.exists())
            raise KeyboardInterrupt
        with mock.patch.object(film.compose, "lay", lambda *a: {}), mock.patch.object(film.studio, "render", render), \
                self.assertRaises(KeyboardInterrupt):
            film._preview({"bpm": 120, "frames": 30}, PLAIN)
        self.assertEqual(seen, [False])
        self.assertFalse(pv.exists())

    def test_sheets_removes_each_type_read_before_its_frames_change(self):
        import storyboard  # grade, which it imports, reads the run's folder on import
        tj = self.B / "storyboards" / "1" / "type.json"
        tj.parent.mkdir(parents=True)
        tj.write_text('{"findings": []}')
        seen, rmtree = [], storyboard.shutil.rmtree

        def render(jobs, name, run):
            seen.append(tj.exists())
            return {"findings": [], "failed": 0}

        def removed(path, **kw):
            seen.append(tj.exists())
            rmtree(path, **kw)
        with mock.patch.object(storyboard, "load_boards", lambda: [{"id": "1"}]), \
                mock.patch.object(storyboard.shutil, "rmtree", removed), \
                mock.patch.object(storyboard, "stage_assets", lambda: None), \
                mock.patch.object(storyboard, "write_md", lambda b, path: path.write_text("moves")), \
                mock.patch.object(storyboard.compose, "lay", lambda *a: {}), \
                mock.patch.object(storyboard.compose, "rest_frames", lambda *a: [("hook", 0)]), \
                mock.patch.object(storyboard.studio, "render", render), redirect_stdout(io.StringIO()):
            storyboard._sheets(PLAIN)
        self.assertEqual(seen, [False] * len(seen))
        self.assertEqual(len(seen), len(storyboard.FORMATS) + 2, "each format's frames, the look's frames, then the render")
        self.assertTrue(tj.exists())
        self.assertTrue((tj.parent / "storyboard.md").exists())

    def test_the_ballot_refuses_a_board_whose_sheets_are_not_this_drafts(self):
        sb = self.B / "storyboards" / "1"
        sb.mkdir(parents=True)
        (sb / "storyboard.json").write_text('{"id": "1", "name": "n"}')
        with self.assertRaises(SystemExit) as e:
            vote.cmd_ballot(argparse.Namespace())
        self.assertIn("storyboard.py sheets", str(e.exception))
        self.assertFalse((self.B / "vote" / "ballot.md").exists())


class Inputs(Base):
    def test_a_photograph_stopped_while_saving_never_lands_under_its_name(self):
        import picks
        photos = self.B / "photos"

        class Stopped:
            def thumbnail(self, *a):
                pass

            def save(self, path, *a, **kw):
                Path(path).write_bytes(b"half a jpeg")
                raise KeyboardInterrupt
        src = self.d / "a.jpg"
        src.write_bytes(b"x")
        with mock.patch.object(picks, "PHOTOS", photos), mock.patch.object(picks, "open_image", lambda *a, **k: Stopped()), \
                self.assertRaises(KeyboardInterrupt):
            picks.prepare(src)
        self.assertEqual([p.name for p in photos.glob("*.jpg")], [])

    def test_a_graded_photograph_stopped_in_ffmpeg_never_lands_under_its_name(self):
        import grade  # it reads the run's folder on import
        dest = self.B / "public" / "graded" / "a.jpg"
        dest.parent.mkdir(parents=True)

        def ffmpeg(argv, **kw):
            Path(argv[-1]).write_bytes(b"half a jpeg")
            raise KeyboardInterrupt
        with mock.patch.object(grade, "match_light", lambda src, tmp, tone=None: Path(tmp).write_bytes(b"png")), \
                mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg"}), mock.patch.object(grade.subprocess, "run", ffmpeg), \
                self.assertRaises(KeyboardInterrupt):
            grade.grade_file(self.d / "a.jpg", dest, "null")
        self.assertFalse(dest.exists())

    def test_made_music_removes_an_older_makes_source_only_after_music_json_names_the_new_bed(self):
        import music
        m = self.B / "music"
        m.mkdir()
        old = m / "source.20261030T120000Z-1.wav"
        old.write_bytes(b"a bed an older make wrote")
        _env.write_json(self.B / "music.json", {"file": str(old)})
        named, write = [], _env.write_json

        def write_json(path, obj):
            if Path(path).name == "music.json":
                named.append((Path(obj["file"]).exists(), old.exists()))
            write(path, obj)
        with mock.patch.object(music, "MUSIC", m), mock.patch.object(music.music_engine, "compose", engine), \
                mock.patch.object(_env, "write_json", write_json), redirect_stdout(io.StringIO()):
            music.cmd_make(argparse.Namespace(board=None, bpm=None, seconds=10))
        self.assertEqual(named, [(True, True)], "music.json names the new bed while the old source is still there")
        self.assertFalse(old.exists())
        self.assertEqual(Path(_env.read_json(self.B / "music.json")["file"]), m / "bed.wav")

    def test_find_takes_a_track_placed_after_a_made_bed(self):
        import music
        m = self.B / "music"

        def tools(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, "60\n", "")
        with mock.patch.object(music, "MUSIC", m), mock.patch.object(music.music_engine, "compose", engine), \
                mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                mock.patch.object(music.subprocess, "run", tools), redirect_stdout(io.StringIO()):
            music.cmd_make(argparse.Namespace(board=None, bpm=None, seconds=10))
            (m / "source.mp3").write_bytes(b"the track the person placed")
            music.cmd_find(argparse.Namespace(origin=None))
        self.assertEqual(Path(_env.read_json(self.B / "music.json")["file"]).name, "source.mp3")

    def test_a_master_stopped_after_it_lands_leaves_music_json_naming_the_old_master_whole(self):
        import music
        m = self.B / "music"
        m.mkdir()
        (m / "source.wav").write_bytes(b"the track")
        (m / "master.wav").write_bytes(b"the old master")
        _env.write_json(self.B / "music.json", {"file": str(m / "source.wav"), "master": str(m / "master.wav")})
        _env.write_json(self.B / "film.json", {"seconds": 10, "bpm": 120, "sound": []})
        real = os.replace

        def replace(src, dst):
            real(src, dst)
            if Path(dst).parent == m:
                raise KeyboardInterrupt

        def ffmpeg(argv, **kw):
            if argv[-1].endswith(".wav"):
                Path(argv[-1]).write_bytes(b"the new master")
            return subprocess.CompletedProcess(argv, 0, "", "I: -14.0 LUFS")
        with mock.patch.object(music, "MUSIC", m), mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg"}), \
                mock.patch.object(music.subprocess, "run", ffmpeg), mock.patch.object(music.os, "replace", replace), \
                self.assertRaises(KeyboardInterrupt):
            music.cmd_master(argparse.Namespace(seconds=None))
        self.assertEqual(Path(_env.read_json(self.B / "music.json")["master"]).read_bytes(), b"the old master")

    def test_the_film_lays_the_master_music_json_names(self):
        _env.write_json(self.B / "music.json", {"master": str(self.d / "named.wav")})
        (self.B / "music").mkdir()
        (self.B / "music" / "master.wav").write_bytes(b"a master no index names")
        spawned = []
        film.mux(self.d / "silent.mp4", self.d / "out.mp4", 10, types.SimpleNamespace(spawn=lambda argv, **kw: spawned.append(argv)))
        self.assertIn(str(self.d / "named.wav"), spawned[0])


def made_by_ffmpeg(argv, **kw):
    """ffmpeg writing the file it is asked for, from the input's bytes when the input is a file."""
    src = Path(argv[argv.index("-i") + 1]) if "-i" in argv else None
    Path(argv[-1]).write_bytes(src.read_bytes() if src and src.is_file() else b"wav")
    return subprocess.CompletedProcess(argv, 0, "", "")


def engine(style=None, styles=(), avoid=(), seconds=60.0, edges=(), hue=None, seed="", bpm=None, target_bpm=None, out=Path("music"),
           calls=None):
    """The music engine's compose, standing in: it writes out/bed.wav and returns what music.json carries, and notes
    what it was asked for in `calls`."""
    if calls is not None:
        calls.append({"style": style, "styles": list(styles), "avoid": list(avoid), "seconds": seconds, "bpm": bpm})
    out.mkdir(parents=True, exist_ok=True)
    (out / "bed.wav").write_bytes(b"bed")
    return {"key": "D major", "bpm": bpm or 100.0, "chords": ["D", "G"], "removed": [], "beats": [], "downbeats": []}


class Brief(Base):
    """make asks the music engine for the chosen look's recipe, turned by the person's music brief, as long as the board
    and four seconds; find makes it when nothing is placed."""

    def make(self, style, music_brief=None, length=36.0, cmd="make"):
        import music
        _env.write_json(self.B / "winner.json", {"board": "1"})
        _env.write_json(self.B / "storyboards" / "1" / "storyboard.json", {"style": style, "length": length, "bpm": 120, "beats": []})
        _env.write_json(self.B / "taste.json", {"handle": "maren.okafor", **({"music": music_brief} if music_brief else {})})
        calls = []
        ask = lambda *a, **kw: engine(*a, calls=calls, **kw)
        with mock.patch.object(music.music_engine, "compose", ask), mock.patch.object(music, "edges", lambda b, bpm: []), \
                redirect_stdout(io.StringIO()):
            args = argparse.Namespace(board=None, bpm=None, seconds=None, origin=None)
            self.assertEqual((music.cmd_find if cmd == "find" else music.cmd_make)(args), 0)
        return calls[0], _env.read_json(self.B / "music.json")

    def test_each_look_plays_its_own_recipe_in_its_own_tempo_range(self):
        import compose
        for style in ("scrapbook", "analog-home-movie", "editorial-quiet"):
            with self.subTest(style):
                asked, info = self.make(style)
                lo, hi = compose.tempo_range(style)
                self.assertEqual(asked["style"], compose.card(style)["music"])
                self.assertTrue(lo <= asked["bpm"] <= hi, asked)
                self.assertIn(f"the {compose.card(style)['music']} recipe", info["origin"])
                self.assertIn("chosen by the style", info["origin"])

    def test_the_brief_turns_the_recipe_its_words_and_its_tempo_reach_the_engine(self):
        import compose
        asked, _ = self.make("scrapbook", {"styles": ["warm strings"], "avoid": ["vocals", "big drums"]})
        self.assertEqual((asked["styles"], asked["avoid"]), (["warm strings"], ["vocals", "big drums"]))
        asked, _ = self.make("scrapbook", {"tempo": 104})
        self.assertEqual(asked["bpm"], 104.0)
        lo, hi = compose.tempo_range("scrapbook")
        asked, _ = self.make("scrapbook", {"tempo": 400})
        self.assertTrue(lo <= asked["bpm"] <= hi, "a tempo past the look's range is folded into it")

    def test_find_with_nothing_placed_makes_a_bed_as_long_as_the_board_and_four_seconds(self):
        import music
        asked, info = self.make("editorial-quiet", cmd="find")
        self.assertEqual(asked["seconds"], 40.0)
        self.assertEqual(Path(info["file"]), music.MUSIC / "bed.wav")


class AudioRow(Base):
    def audio_row(self, fx_lufs):
        """The gate's audio row over a film at -14 LUFS whose master measured the bed at -21.4 LUFS and the effects at
        `fx_lufs`."""
        import qa
        _env.write_json(self.B / "film.json", {"hash": "h", "bpm": 120, "cuts": [], "hook_frame": 0, "rest": [],
                                               "beats": [{"id": "hook"}, {"id": "card-1"}, {"id": "closer"}],
                                               "sound": [{"kind": "hit", "at": 0.3}, {"kind": "hit", "at": 4.0}]})
        _env.write_json(self.B / "music.json", {"file": "source.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs, "sound_cues": 2})
        Path("out").mkdir()
        for film, _ in qa.FILMS.values():
            film.write_bytes(b"a film")
        probed = {"streams": [{"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}], "format": {"duration": "40"}}
        with mock.patch.object(qa, "probe", lambda film, run=None: probed), mock.patch.object(qa, "loudness", lambda film, run=None: -14.0), \
                mock.patch.object(qa, "detect", lambda *a: []), mock.patch.object(qa.studio, "measure", lambda *a, **kw: {}), \
                mock.patch.object(qa, "figures", lambda *a: None):
            res = qa.film_checks()[0]
        return next(r for r in res if r[0] == "audio")

    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_turns_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-16.3)
        self.assertFalse(ok)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("2 sound cues over 3 beats", detail)

    def test_effects_eight_lu_under_the_bed_turn_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-29.4)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)


class Gate(Base):
    def test_every_process_the_gates_film_checks_start_goes_through_the_runs_spawn(self):
        import qa
        _env.write_json(self.B / "film.json", {"hash": "h", "bpm": 120, "sound": [], "cuts": [1.0], "hook_frame": 3, "rest": []})
        Path("out").mkdir()
        for film, _ in qa.FILMS.values():
            film.write_bytes(b"a film")
        spawned = []

        def spawn(argv, **kw):
            spawned.append(Path(argv[0]).name)
            out = '{"streams": [], "format": {"duration": "10"}}' if "json" in argv else "10"
            return subprocess.CompletedProcess(argv, 0, out, "")
        with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                mock.patch("subprocess.run", side_effect=AssertionError("a process outside the lock")):
            qa.film_checks(types.SimpleNamespace(spawn=spawn))
        self.assertIn("ffprobe", spawned)
        self.assertIn("ffmpeg", spawned)


class RenderRetry(Base):
    def test_a_render_stopped_in_out_then_a_retry_stopped_before_out_leaves_a_set_qa_refuses(self):
        import qa
        f = {"hash": "h", "id": "1", "frames": 23, "bpm": 120, "seconds": 1, "sound": [], "cuts": [], "hook_frame": 0, "rest": ["hook"]}
        _env.write_json(self.B / "film.json", f)
        Path("out/stills").mkdir(parents=True)
        for name in film.OUT.values():
            Path(name).write_bytes(b"the last film")
        _env.write_json(self.B / "render" / "film-report.json", {"jobs": 9, "failed": 0, "findings": [], "reel": "last"})

        def chunks_render(run, jobs, *a):  # the shared bridge: every job made, none failed
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_bytes(b"new " + j["type"].encode())
            return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}
        real = os.replace

        def stop_after_the_square(src, dst):
            real(src, dst)
            if str(dst) == film.OUT["feed"]:
                raise KeyboardInterrupt
        tools = {"chromium": "chromium", "dist": "dist", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
        with mock.patch.object(_env, "_TOOLS", tools), mock.patch.object(film.compose, "lay", lambda *a: {"beats": []}), \
                mock.patch.object(film.compose, "rest_frames", lambda *a: [("hook", 0)]), \
                mock.patch.object(studio.chunks, "render", chunks_render), redirect_stdout(io.StringIO()):
            with mock.patch.object(film.os, "replace", stop_after_the_square), self.assertRaises(KeyboardInterrupt):
                film._render(f, PLAIN, film.ALSO)  # out/ holds the new square beside the last wide and reel
            with mock.patch.object(film, "mux", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                film._render(f, PLAIN, film.ALSO)  # the retry renders again and stops before out/ changes
        self.assertEqual(Path(film.OUT["feed"]).read_bytes(), b"new video")
        self.assertEqual(Path(film.OUT["reel"]).read_bytes(), b"the last film")

        def spawn(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, '{"streams": [], "format": {"duration": "10"}}' if "json" in argv else "10", "")
        with mock.patch.object(_env, "_TOOLS", tools):
            res, _, _ = qa.film_checks(types.SimpleNamespace(spawn=spawn))
        self.assertEqual([ok for name, ok, *_ in res if name == "safe"], [False])
        with self.assertRaises(SystemExit):
            vote.cmd_cut(argparse.Namespace())
        with self.assertRaises(SystemExit):
            film.cmd_frames(argparse.Namespace(out=None))

    def snap(self):
        """storyboard.py snap of a board that passed the vote, to a new cut."""
        import storyboard
        sb = self.B / "storyboards" / "1"
        sb.mkdir(parents=True, exist_ok=True)
        _env.write_json(sb / "storyboard.json", {"id": "1", "style": "scrapbook", "music": {}, "beats": [], "name": "n"})
        _env.write_json(sb / "type.json", {"findings": []})
        _env.write_json(self.B / "winner.json", {"board": "1"})
        lay = {"beats": [], "sound": [], "clips": []}
        with mock.patch.object(storyboard, "board_issues", lambda *a: []), mock.patch.object(storyboard, "allowed_photos", set), \
                mock.patch.object(storyboard.compose, "Ctx", lambda: None), mock.patch.object(storyboard.compose, "lay", lambda *a: lay), \
                mock.patch.object(storyboard.compose, "fit", lambda b, bpm: b), \
                mock.patch.object(storyboard.compose, "hook_frame", lambda *a: 0), mock.patch.object(storyboard.compose, "hook_event", lambda *a: None), \
                mock.patch.object(storyboard.compose, "story", lambda *a: None), redirect_stdout(io.StringIO()):
            self.assertEqual(storyboard.cmd_snap(argparse.Namespace()), 0)

    def safe(self):
        import qa

        def spawn(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, '{"streams": [], "format": {"duration": "10"}}' if "json" in argv else "10", "")
        with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}):
            res, _, _ = qa.film_checks(types.SimpleNamespace(spawn=spawn))
        return [ok for name, ok, *_ in res if name == "safe"]

    def old_film(self):
        """out/ and its clean report, for the cut before this one."""
        Path("out/stills").mkdir(parents=True)
        for name in film.OUT.values():
            Path(name).write_bytes(b"the last film")
        _env.write_json(self.B / "render" / "film-report.json", {"jobs": 9, "failed": 0, "findings": [], "reel": "last"})

    def test_a_new_cut_with_no_render_leaves_a_set_qa_refuses(self):
        self.old_film()
        self.snap()
        self.assertEqual(self.safe(), [False])
        with self.assertRaises(SystemExit):
            vote.cmd_cut(argparse.Namespace())

    def test_a_new_cut_whose_render_is_stopped_before_out_leaves_a_set_qa_refuses(self):
        self.old_film()
        self.snap()

        def chunks_render(run, jobs, *a):
            for j in jobs:
                Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
                Path(j["out"]).write_bytes(b"new " + j["type"].encode())
            return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}
        f = _env.read_json(self.B / "film.json")
        with mock.patch.object(_env, "_TOOLS", {"chromium": "chromium", "dist": "dist", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                mock.patch.object(film.compose, "lay", lambda *a: {"beats": []}), \
                mock.patch.object(film.compose, "rest_frames", lambda *a: [("hook", 0)]), \
                mock.patch.object(studio.chunks, "render", chunks_render), mock.patch.object(film, "mux", side_effect=KeyboardInterrupt), \
                redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            film._render(f, PLAIN)
        self.assertEqual(Path(film.OUT["reel"]).read_bytes(), b"the last film")
        self.assertEqual(self.safe(), [False])


class CutRound(Base):
    """A cut round belongs to one reel: the same reel reuses it, a reel rendered again before its round was scored takes
    its place, and a new reel after a scored round opens the next round."""

    def test_the_cut_reuses_the_round_of_the_same_reel_and_opens_one_for_a_new_reel(self):
        (self.B / "film.json").write_text('{"id": "1"}')
        report = self.B / "render" / "film-report.json"
        report.parent.mkdir()
        with redirect_stdout(io.StringIO()), mock.patch.object(vote, "cut_frames", lambda src, folder, tag, seconds: []):
            with self.assertRaises(SystemExit):
                vote.cmd_cut(argparse.Namespace())  # no report: out/ is not a whole render
            _env.write_json(report, {"failed": 0, "reel": "the reel"})
            vote.cmd_cut(argparse.Namespace())
            vote.cmd_cut(argparse.Namespace())
            self.assertEqual(len(vote.rounds()), 1)
            _env.write_json(report, {"failed": 0, "reel": "the reel, rendered again"})
            vote.cmd_cut(argparse.Namespace())
            self.assertEqual([(_env.read_json(p)["round"], _env.read_json(p)["film"]) for p in vote.rounds()],
                             [(1, "the reel, rendered again")], "an unscored round is not spent")
            cut = _env.read_json(vote.rounds()[-1])
            for e in cut["critics"].values():
                e["boards"]["film"]["scores"] = {k: 4 for k in vote.CRITERIA}
            _env.write_json(vote.rounds()[-1], cut)
            _env.write_json(report, {"failed": 0, "reel": "the reel, fixed"})
            vote.cmd_cut(argparse.Namespace())
        self.assertEqual([_env.read_json(p)["round"] for p in vote.rounds()], [1, 2])


class Lock(Base):
    @unittest.skipIf(os.name == "nt", "the lock is a flock on POSIX")
    def test_the_tools_resolve_before_the_runs_lock(self):
        import fcntl
        held = []

        def setup(argv, **kw):
            with open(self.B / "render" / "render.lock", "a+") as f:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held.append(False)
                except OSError:
                    held.append(True)
            return subprocess.CompletedProcess(argv, 0, '{"ffmpeg": "/bin/true"}', "")
        (self.B / "render").mkdir()
        with mock.patch.object(_env, "_TOOLS", None), mock.patch("subprocess.run", setup):
            with studio.lock("film"):
                _env.ffmpeg()
        self.assertEqual(held, [False])

    def test_two_commands_naming_runs_never_share_a_temp_name(self):
        temps, real = [], os.replace

        def replace(src, dst):
            temps.append(Path(src).name)
            real(src, dst)
        with mock.patch.object(_env, "BUILD", self.d / "build"), mock.patch.object(_env.os, "replace", replace):
            _env._name_latest(self.d / "build" / "20261022T120000Z")
            _env._name_latest(self.d / "build" / "20261022T120000Z-2")
        self.assertEqual(len(set(temps)), 2)
        self.assertEqual((self.d / "build" / "latest").read_text().strip(), "20261022T120000Z-2")


if __name__ == "__main__":
    unittest.main()
