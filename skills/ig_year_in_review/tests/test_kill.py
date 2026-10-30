"""A command stopped at any point, on a first run or a retry, leaves nothing the next command reads wrongly: an index
goes before the files it names change, or the new files take new names and the index moves to them, and an index is
published only when its set is whole; a reader reads the index, never one member; an input lands whole under its name;
the critic's round is reused for the same reel; the tools resolve before the run's lock; and the gate's processes hold
deliver's lock.

    python3 -I -m unittest discover -s S/tests -p test_kill.py
"""
import argparse
import io
import json
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
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

PLAIN = types.SimpleNamespace(spawn=subprocess.run)


def spawn_probe(spawned):
    """A run whose spawn answers ffprobe and ffmpeg as a whole 40 s reel would."""
    def spawn(argv, **kw):
        spawned.append(Path(argv[0]).name)
        if "json" in argv:
            out = json.dumps({"streams": [{"codec_type": "video"}, {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "40"}})
        else:
            out = "40"
        return subprocess.CompletedProcess(argv, 0, out, "")
    return types.SimpleNamespace(spawn=spawn)


def made_by_ffmpeg(argv, **kw):
    """ffmpeg writing the file it is asked for, from the input's bytes when the input is a file."""
    src = Path(argv[argv.index("-i") + 1]) if "-i" in argv else None
    Path(argv[-1]).write_bytes(src.read_bytes() if src and src.is_file() else b"wav")
    return subprocess.CompletedProcess(argv, 0, "", "")


class Base(unittest.TestCase):
    """A workspace with its build/ folder, entered the way every command enters it."""

    def cut(self):
        """A snapped cut, its board and its music, and a whole render of it in out/."""
        import qa
        _env.write_json("film.json", {"hash": "h", "boards": {"reel": "board.json"}, "cuts": [1.0], "hook_frame": 3})
        _env.write_json("board.json", {"bpm": 120, "sound": []})
        _env.write_json("music.json", {"file": "music/source.wav"})
        Path("../out").mkdir()
        for path, _ in qa.FILMS.values():
            path.write_bytes(b"the last render's film")
        _env.write_json("render/film-report.json", {"jobs": 19, "failed": 0, "findings": [], "hash": "h"})

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name)
        self.B = self.d / "build"
        self.B.mkdir()
        patch = mock.patch.object(_env, "WORKSPACE", self.d)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.B)


class Indexes(Base):
    def test_preview_json_goes_before_the_preview_renders(self):
        Path("film.json").write_text(json.dumps({"boards": {"reel": "board.json"}, "frames": 30}))
        Path("board.json").write_text("{}")
        pv = Path("preview/preview.json")
        pv.parent.mkdir()
        pv.write_text('{"hash": "the last cut"}')
        seen = []

        def render(jobs, name, run):
            seen.append(pv.exists())
            raise KeyboardInterrupt
        with mock.patch.object(film.studio, "render", render), mock.patch.object(film.studio, "props", lambda b: {}), \
                self.assertRaises(KeyboardInterrupt):
            film.cmd_preview(argparse.Namespace(), PLAIN)
        self.assertEqual(seen, [False])

    def test_a_draft_stopped_between_its_board_and_its_plan_leaves_nothing_the_next_command_reads(self):
        d = Path("storyboards/analog-home-movie")
        d.mkdir(parents=True)
        _env.write_json("storyboards/boards.json", {"order": list(storyboard.style.TRIO)})
        for f in (Path("film.json"), Path("winner.json"), d / "plan.json", d / "board-reel.json"):
            f.write_text('{"the last": "draft"}')
        (d / "sheet.png").write_bytes(b"the last draft's sheet")
        write = _env.write_json

        def write_json(path, obj):
            write(path, obj)
            if Path(path).name == "board-reel.json":
                raise KeyboardInterrupt
        with mock.patch.object(storyboard, "board_for", lambda s, run, bpm=None: {"board": {"new": True}}), \
                mock.patch.object(_env, "write_json", write_json), redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            storyboard.cmd_draft(argparse.Namespace(), types.SimpleNamespace(taste={}))
        self.assertEqual([f for f in ("film.json", "winner.json", d / "plan.json", d / "sheet.png") if Path(f).exists()], [])
        for refuses in (lambda: storyboard.load_plan("analog-home-movie"), vote.boards):
            with self.assertRaises(SystemExit):
                refuses()

    def test_the_clips_index_names_whole_frames_and_the_old_frames_go_after_it(self):
        old = Path("public/clips/20261021T000000-1/m01")
        old.mkdir(parents=True)
        (old / "0001.jpg").write_bytes(b"the last normalize's frame")
        _env.write_json("clips.json", {"clips": {"m01": {"status": "generated", "dir": "clips/20261021T000000-1/m01"}}})
        import clips
        seen, write = [], _env.write_json

        def conform(src, image, frames, dst):
            dst.mkdir(parents=True)
            (dst / "0001.jpg").write_bytes(b"a frame")
            return 1, ""

        def write_json(path, obj):
            if Path(path).name == "clips.json":
                named = Path("public") / obj["clips"]["m01"]["dir"]
                seen.append((old.exists(), named != old.relative_to("public").parent and (named / "0001.jpg").exists()))
            write(path, obj)
        board = {"beats": [{"id": "m01", "frames": 30}], "clips": [{"id": "m01", "beat": "m01", "role": "r", "image": "a.jpg", "prompt": "p"}]}
        with mock.patch.object(clips, "board", lambda: board), mock.patch.object(clips, "arrived", lambda cid: Path("m01.mp4")), \
                mock.patch.object(clips, "conform", conform), mock.patch.object(_env, "write_json", write_json), redirect_stdout(io.StringIO()):
            clips.cmd_normalize(argparse.Namespace(why=None))
        self.assertEqual(seen, [(True, True)])
        self.assertFalse(old.parent.exists())
        self.assertEqual([p["dir"] for p in clips.placed()], [_env.read_json("clips.json")["clips"]["m01"]["dir"]])

    def test_a_render_moves_the_reel_in_last_with_the_review_page_and_the_report_gone_while_files_move(self):
        part = Path("../out.part")
        for f in ("film.mp4", "carousel/01-hook.png", "stories/01-hook.png"):
            (part / f).parent.mkdir(parents=True, exist_ok=True)
            (part / f).write_bytes(b"new")
        out = Path("../out")
        out.mkdir()
        (out / "review.html").write_text("green, for the last set")
        report = Path("render/film-report.json")
        report.parent.mkdir()
        report.write_text('{"jobs": 19, "failed": 0}')
        moved, real = [], os.replace

        def replace(src, dst):
            if "out" in Path(dst).parts:
                moved.append((Path(dst).name, (out / "review.html").exists(), report.exists()))
            real(src, dst)
        with mock.patch.object(film.os, "replace", replace):
            film.publish(part, {"jobs": 19, "failed": 0, "new": True})
        self.assertEqual([m[0] for m in moved][-1], "film.mp4")
        self.assertEqual([m for m in moved if m[1] or m[2]], [])
        self.assertTrue(_env.read_json(report)["new"])


class Render(Base):
    def test_a_render_stopped_while_files_move_then_a_retry_stopped_before_the_first_move_leaves_a_set_nothing_reads_as_whole(self):
        import qa
        import studio as studio_
        self.cut()
        part = Path("../out.part")
        for f in ("film.mp4", "carousel/01-hook.png", "stories/01-hook.png"):
            (part / f).parent.mkdir(parents=True, exist_ok=True)
            (part / f).write_bytes(b"the new render's")
        moved, real = [], os.replace

        def replace(src, dst):
            if "out" in Path(dst).parts:
                if moved:
                    raise KeyboardInterrupt
                moved.append(dst)
            real(src, dst)
        with mock.patch.object(film.os, "replace", replace), self.assertRaises(KeyboardInterrupt):
            film.publish(part, {"jobs": 19, "failed": 0, "findings": [], "hash": "h"})
        # the retry renders whole, and is stopped before its first file moves into out/
        whole = {"jobs": 19, "failed": 0, "findings": [], "seconds": 1.0}
        with mock.patch.object(studio_.chunks, "render", lambda *a: dict(whole)), mock.patch.object(studio_, "public", lambda: Path("public")), \
                mock.patch.object(_env, "_TOOLS", {"chromium": "chromium", "dist": "dist", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                redirect_stdout(io.StringIO()):
            studio_.render([], "film", PLAIN)
            res, _, _ = qa.film_checks(spawn_probe([]))
        self.assertEqual([ok for name, ok, *_ in res if name == "safe"], [False])
        with self.assertRaises(SystemExit):
            vote.cmd_cut(argparse.Namespace())


class CutChanged(Base):
    """An approved film in out/ with its report, then the cut snapped again: the report that vouched for out/ goes before
    the cut changes, so QA refuses the old film as the new cut's, whether or not a render follows and is stopped."""

    def snap_again(self):
        self.cut()
        _env.write_json("storyboards/boards.json", {"order": list(storyboard.style.TRIO)})
        _env.write_json("winner.json", {"board": "analog-home-movie"})
        board = {"bpm": 120, "beats": [], "sound": [], "clips": [], "year": {"months": [], "total": 1, "closer": {"still": 10}, "signoff": "a new sign-off"}}
        plan = {"board": board, "seconds": 40, "cuts": [], "hook_frame": 7, "frames": 1200, "rests": {}, "rest_beats": {}, "story": []}
        with mock.patch.object(storyboard, "board_for", lambda s, run, bpm=None: plan), mock.patch.object(storyboard, "findings", lambda p: []), \
                mock.patch.object(storyboard, "write_md", lambda run, s, p: None), redirect_stdout(io.StringIO()):
            storyboard.cmd_snap(argparse.Namespace(), types.SimpleNamespace(words={}, months=[], taste={}))
        self.assertNotEqual(_env.read_json("film.json")["hash"], "h")

    def safe(self):
        import qa
        with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}):
            res, _, _ = qa.film_checks(spawn_probe([]))
        return [ok for name, ok, *_ in res if name == "safe"]

    def test_a_cut_snapped_again_leaves_the_old_film_refused(self):
        self.snap_again()
        self.assertEqual(self.safe(), [False])

    def test_a_cut_snapped_again_then_a_render_stopped_before_its_first_move_leaves_the_old_film_refused(self):
        import studio as studio_
        self.snap_again()
        whole = {"jobs": 19, "failed": 0, "findings": [], "seconds": 1.0}
        with mock.patch.object(studio_.chunks, "render", lambda *a: dict(whole)), mock.patch.object(studio_, "public", lambda: Path("public")), \
                mock.patch.object(_env, "_TOOLS", {"chromium": "chromium", "dist": "dist", "ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                redirect_stdout(io.StringIO()):
            studio_.render([], "film", PLAIN)
        self.assertEqual(self.safe(), [False])


class Inputs(Base):
    def test_a_photograph_stopped_while_saving_never_lands_under_its_name(self):
        import picks

        class Stopped:
            def thumbnail(self, *a):
                pass

            def save(self, path, *a, **kw):
                Path(path).write_bytes(b"half a jpeg")
                raise KeyboardInterrupt
        photos = Path("public/photos")
        with mock.patch.object(picks, "PHOTOS", photos), mock.patch.object(picks, "open_image", lambda *a, **k: Stopped()), \
                mock.patch.object(picks, "matched", lambda im: im), self.assertRaises(KeyboardInterrupt):
            picks.place(1, self.d / "a.jpg", photos)
        self.assertEqual([p.name for p in photos.glob("*.jpg")], [])

    def test_picks_json_names_the_photographs_it_read_and_the_cut_board_keeps_its_own(self):
        import picks
        from PIL import Image
        os.chdir(self.d)
        src = self.d / "a.png"
        Image.new("RGB", (40, 30), (120, 90, 60)).save(src)
        old = Path("build/public/photos/m01-a.jpg")
        old.parent.mkdir(parents=True)
        old.write_bytes(b"the earlier run's photograph")
        # the cut snapped from the earlier run names its photograph
        _env.write_json("build/storyboards/analog-home-movie/board-reel.json", {"year": {"months": [{"id": "m01", "file": "photos/m01-a.jpg"}]}})
        _env.write_json("build/film.json", {"boards": {"reel": "storyboards/analog-home-movie/board-reel.json"}})
        _env.write_json("build/picks.json", {"months": [{"month": 1, "file": "photos/m01-a.jpg", "src": str(src)}]})
        _env.write_json("build/library.json", {"year": 2023, "posts": [{"media": [str(src)], "ts": 1700000000, "caption": "c"}], "stories": []})
        seen, write = [], _env.write_json

        def write_json(path, obj):
            if Path(path).name == "picks.json":
                named = Path("build/public") / obj["months"][0]["file"]
                seen.append((old.read_bytes(), named != old and named.stat().st_size > 0))
            write(path, obj)
        with mock.patch.object(sys, "argv", ["picks.py"]), mock.patch.object(picks, "analyse", lambda m: {}), \
                mock.patch.object(picks, "line_of", lambda *a: [0, 0.8, 1, 0.8]), \
                mock.patch.object(picks, "sheet", lambda *a: None), mock.patch.object(_env, "write_json", write_json), redirect_stdout(io.StringIO()):
            picks.main()
        self.assertEqual(seen, [(b"the earlier run's photograph", True)])
        board = _env.read_json("build/storyboards/analog-home-movie/board-reel.json")
        self.assertEqual([(Path("build/public") / m["file"]).read_bytes() for m in board["year"]["months"]], [b"the earlier run's photograph"])

    def test_a_focus_read_from_the_photograph_is_kept_when_picks_runs_again(self):
        import picks
        from PIL import Image
        os.chdir(self.d)
        a, b = self.d / "a.png", self.d / "b.png"
        Image.new("RGB", (40, 30), (120, 90, 60)).save(a)
        Image.new("RGB", (40, 30), (60, 90, 120)).save(b)
        _env.write_json("build/library.json", {"year": 2023, "stories": [],
                                               "posts": [{"media": [str(a)], "ts": 1673000000, "caption": "c"},
                                                         {"media": [str(b)], "ts": 1676000000, "caption": "d"}]})
        _env.write_json("build/picks.json", {"months": [{"month": 1, "src": str(a), "focus": [0.5, 0.3], "focus_from": "read"},
                                                        {"month": 2, "src": str(b), "focus": [0.3, 0.3], "focus_from": "found"}]})
        with mock.patch.object(sys, "argv", ["picks.py"]), mock.patch.object(picks, "analyse", lambda m: {}), \
                mock.patch.object(picks, "focus_of", lambda im: [0.45, 0.5]), mock.patch.object(picks, "line_of", lambda *a, **k: [0, 0.5, 1, 0.5]), \
                mock.patch.object(picks, "sheet", lambda *a: None), redirect_stdout(io.StringIO()):
            picks.main()
        months = _env.read_json("build/picks.json")["months"]
        self.assertEqual([(m["focus"], m["focus_from"]) for m in months], [([0.5, 0.3], "read"), ([0.45, 0.5], "found")])

    def composed(self, calls=None):
        """music_engine.compose standing in: the bed written whole under music/bed.wav, the call recorded."""
        import music

        def compose(style, styles, avoid, seconds, edges, hue, seed, bpm=None, out=None):
            if calls is not None:
                calls.append({"style": style, "styles": styles, "avoid": avoid, "seed": seed, "bpm": bpm})
            (out / "bed.wav").write_bytes(b"the new bed")
            return {"recipe": style, "key": "A minor", "bpm": bpm, "seconds": seconds, "beats": [0.0], "downbeats": [0.0],
                    "sections": [], "chords": ["Am"], "programs": [], "removed": []}
        return mock.patch.object(music.music_engine, "compose", compose)

    def test_made_music_keeps_the_source_music_json_names_until_it_names_the_new_one(self):
        import music
        m = Path("music")
        m.mkdir()
        (m / "source.wav").write_bytes(b"the earlier bed")
        _env.write_json("music.json", {"file": str(m / "source.wav"), "bpm": 100, "beats": [0.6]})
        _env.write_json("winner.json", {"board": "analog-home-movie"})
        named, write = [], _env.write_json

        def write_json(path, obj):
            if Path(path).name == "music.json":
                named.append(((m / "source.wav").read_bytes(), Path(obj["file"]).read_bytes()))
            write(path, obj)
        with self.composed(), mock.patch.object(_env, "write_json", write_json), redirect_stdout(io.StringIO()):
            music.cmd_make(argparse.Namespace(bpm=88, seconds=10))
        self.assertEqual(named, [(b"the earlier bed", b"the new bed")])
        self.assertEqual(_env.read_json("music.json")["file"], str(m / "bed.wav"))

    def test_find_takes_only_the_person_facing_source_never_a_made_bed(self):
        import music
        m = Path("music")
        m.mkdir()
        (m / "source.mp3").write_bytes(b"the track the agent saved")
        os.utime(m / "source.mp3", (1, 1))
        (m / "source.20261022T120000-1.wav").write_bytes(b"a made bed, newer")
        _env.write_json("winner.json", {"board": "analog-home-movie"})
        a = argparse.Namespace(origin=None, bpm=None, seconds=None)
        with mock.patch.object(music, "has_audio", lambda f: True), mock.patch.object(music, "duration", lambda f: 60.0), \
                self.composed(), redirect_stdout(io.StringIO()):
            music.cmd_find(a)
            self.assertEqual(_env.read_json("music.json")["file"], str(m / "source.mp3"))
            (m / "source.mp3").unlink()
            music.cmd_find(a)
        self.assertEqual(_env.read_json("music.json")["file"], str(m / "bed.wav"))

    def test_the_bed_is_the_picked_looks_own_recipe_and_a_brief_names_another(self):
        import music
        calls = []
        for won, brief in (("analog-home-movie", None), ("swiss-grid", None), ("swiss-grid", {"styles": ["lo-fi"], "avoid": ["drums"]})):
            _env.write_json("winner.json", {"board": won})
            _env.write_json("taste.json", {"music": brief} if brief else {})
            with self.composed(calls), redirect_stdout(io.StringIO()):
                music.cmd_make(argparse.Namespace(bpm=None, seconds=10))
            self.assertIn(f"chosen by {'their brief' if brief else 'the card'}", _env.read_json("music.json")["origin"])
        self.assertEqual([(c["style"], c["seed"]) for c in calls], [("analog-home-movie", "analog-home-movie"), ("swiss-grid", "swiss-grid"),
                                                                    ("swiss-grid", "swiss-grid")])
        self.assertEqual((calls[2]["styles"], calls[2]["avoid"]), (["lo-fi"], ["drums"]))
        # each bed is at a tempo inside the range of the recipe it was made from: the look's own, or the one a brief named
        book = music.music_engine.recipes()
        for c in calls:
            rid, recipe, _ = music.music_engine.resolve(book, c["style"], c["styles"], c["avoid"])
            lo, hi = recipe["tempo"]
            self.assertTrue(lo <= c["bpm"] <= hi, c)
        self.assertEqual([music.music_engine.resolve(book, c["style"], c["styles"], c["avoid"])[0] == c["style"] for c in calls],
                         [True, True, False])

    def test_make_refuses_before_a_look_is_picked(self):
        import music
        with self.composed(), self.assertRaises(SystemExit):
            music.cmd_make(argparse.Namespace(bpm=None, seconds=10))

    def test_a_master_is_published_once_whole_and_the_old_master_goes_after(self):
        import music
        m = Path("music")
        m.mkdir()
        (m / "master.wav").write_bytes(b"the earlier master")
        _env.write_json("music.json", {"file": "music/source.wav", "master": "music/master.wav", "master_lufs": -14.1})
        named, write = [], _env.write_json

        def write_json(path, obj):
            if Path(path).name == "music.json":
                named.append(((m / "master.wav").read_bytes(), Path(obj["master"]).read_bytes(), obj.get("master_lufs")))
            write(path, obj)

        def ffmpeg(argv, **kw):
            if "-af" in argv and "ebur128" in argv[argv.index("-af") + 1]:
                return subprocess.CompletedProcess(argv, 0, "", "I: -14.0 LUFS")
            Path(argv[-1]).write_bytes(b"the new master")
            return subprocess.CompletedProcess(argv, 0, "", "")
        with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg"}), mock.patch.object(music.subprocess, "run", ffmpeg), \
                mock.patch.object(_env, "write_json", write_json), redirect_stdout(io.StringIO()):
            music.cmd_master(argparse.Namespace(seconds=10))
        self.assertEqual(named, [(b"the earlier master", b"the new master", -14.0)])
        self.assertEqual(sorted(m.glob("master*.wav")), [Path(_env.read_json("music.json")["master"])])


class Gate(Base):
    def test_every_process_the_gates_film_checks_start_goes_through_the_runs_spawn(self):
        import qa
        self.cut()
        spawned = []
        with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                mock.patch("subprocess.run", side_effect=AssertionError("a process outside the lock")):
            qa.film_checks(spawn_probe(spawned))
        self.assertIn("ffprobe", spawned)
        self.assertIn("ffmpeg", spawned)


class AudioRow(Base):
    def audio_row(self, fx_lufs):
        """The gate's audio row over a film at -14 LUFS whose master measured the bed at -21.4 LUFS and the effects at
        `fx_lufs`."""
        import qa
        self.cut()
        _env.write_json("board.json", {"bpm": 120, "beats": [{"id": "hook"}, {"id": "m01"}, {"id": "closer"}],
                                       "sound": [{"kind": "impact", "at": 1.0, "beat": "hook", "what": "the year lands"},
                                                 {"kind": "hit", "at": 4.0, "beat": "m01", "what": "january lands"}]})
        _env.write_json("music.json", {"file": "music/source.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs, "sound_cues": 2})
        probed = {"streams": [{"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}], "format": {"duration": "40"}}
        with mock.patch.object(_env, "_TOOLS", {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), mock.patch.object(qa, "probe", lambda film, run=None: probed), \
                mock.patch.object(qa, "loudness", lambda film, run=None: -14.0):
            res = qa.film_checks(spawn_probe([]))[0]
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


class CriticRow(Base):
    def critic_row(self, paragraph, designer=5, person=4):
        """The gate's critic row over a cut round: the motion designer's every score `designer`, the person's every
        score `person` and the person's paragraph `paragraph`."""
        import qa
        self.cut()
        full = ("The slit opens along each photograph's own edge, the name rises on it, their words follow one by one and "
                "hold whole before the camera pulls back, and the dot carries every cut to the closer.")
        board = lambda p, v: {"boards": {"film": {"scores": {k: v for k in vote.CRITERIA}, "paragraph": p}}}
        _env.write_json("critic/cut-1.json", {"round": 1, "film": qa.sha(qa.FILMS["reel"][0]), "fixed": None,
                                              "critics": {"motion_designer": board(full, designer), "person": board(paragraph, person)}})
        f = {"hash": "h", "boards": {"reel": "board.json"}}
        with mock.patch.object(qa, "timed_checks", lambda: (qa.Checks(), f)), \
                mock.patch.object(qa, "film_checks", lambda run=None: (qa.Checks(), f, {})):
            res, _ = qa.gate_checks()
        return next(r for r in res if r[0] == "critic")

    def test_a_ten_word_paragraph_turns_the_critic_row_red_and_names_the_paragraph(self):
        _, ok, detail = self.critic_row("That is my year and I would post it today.")
        self.assertFalse(ok)
        self.assertIn("person / board film: the paragraph needs at least 25 words", detail)

    WHOLE = ("That is my year: snowed in with rita, my first day, the tulips with marta, our first tomatoes, provence with "
             "mum, and my first bowl, which gets the longest beat. I would post it.")

    def test_a_round_at_the_bar_with_whole_paragraphs_turns_the_critic_row_green(self):
        _, ok, detail = self.critic_row(self.WHOLE, designer=5, person=4)
        self.assertTrue(ok, detail)
        self.assertIn("mean 4.50", detail)

    def test_every_score_four_is_under_the_bar_and_turns_the_critic_row_red(self):
        _, ok, detail = self.critic_row(self.WHOLE, designer=4, person=4)
        self.assertFalse(ok, detail)
        self.assertIn("mean 4.00", detail)


class CutRound(Base):
    def test_the_cut_refuses_a_reel_the_render_report_does_not_name_for_the_current_cut(self):
        self.cut()
        Path("render/film-report.json").unlink()
        with self.assertRaises(SystemExit):
            vote.cmd_cut(argparse.Namespace())
        _env.write_json("render/film-report.json", {"jobs": 19, "failed": 0, "hash": "an earlier cut"})
        with self.assertRaises(SystemExit):
            vote.cmd_cut(argparse.Namespace())
        self.assertEqual(vote.rounds(), [])

    def test_the_cut_reuses_the_round_of_the_same_reel_and_opens_one_for_a_new_reel(self):
        self.cut()
        Path("../out/film.mp4").write_bytes(b"the reel")
        with redirect_stdout(io.StringIO()):
            vote.cmd_cut(argparse.Namespace())
            vote.cmd_cut(argparse.Namespace())
            self.assertEqual(len(vote.rounds()), 1)
            Path("../out/film.mp4").write_bytes(b"the reel, fixed")
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


if __name__ == "__main__":
    unittest.main()
