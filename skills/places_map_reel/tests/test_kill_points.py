"""A command killed at any point leaves nothing the next command reads wrongly: an index that names other files goes
before the first of them changes and comes back only once the set is whole, or the new set takes names of its own and
the old one goes only after the new index names it; a file a later command reads is written under a name of its own
and moved onto its name whole; a command reads a set through its index; the cut's critic round stays with its reel; and
the tools resolve before the run's lock is taken.

    python3 -I -m unittest discover -s S/tests -p test_kill_points.py
"""
import json
import os
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
import chunks  # noqa: E402
import clips  # noqa: E402
import grade  # noqa: E402
import music  # noqa: E402
import picks  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())


class InARun(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)

    @staticmethod
    def put(path, text):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text)


class Half:
    """An image whose save is killed partway: the file it was saving holds half of itself."""

    def thumbnail(self, *a):
        pass

    def save(self, path, *a, **kw):
        Path(path).write_text("half")
        raise KeyboardInterrupt


class Indexes(InARun):
    def test_a_draft_cut_short_at_its_first_board_leaves_no_film_json(self):
        for name, text in (("taste.json", "{\"a\": 1}"), ("taste.md", "taste"), ("cast.json", "{\"visits\": []}"),
                           ("film.json", "{\"style\": \"swiss-grid\"}"), ("render/film-report.json", "{}")):
            self.put(name, text)
        with mock.patch.object(grade, "grade_cast", return_value=[]), mock.patch.object(grade, "own_prints", return_value={}), \
                mock.patch.object(storyboard, "build_source", return_value={"photos": []}), \
                mock.patch.object(storyboard.board_drive, "fit_lines", side_effect=lambda src: src), \
                mock.patch.object(storyboard, "write_board", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            storyboard.cmd_draft(None)
        self.assertFalse(Path("film.json").exists())
        self.assertFalse(Path("render/film-report.json").exists())

    def test_a_look_cut_short_between_two_boards_leaves_no_plan_json(self):
        d = storyboard.BOARDS / "swiss-grid"
        self.put(d / "plan.json", "{}")
        self.put(d / "board-reel.json", "{}")
        real = _env.write_json

        def cut(path, obj):
            if Path(path).name == "board-landscape.json":
                raise KeyboardInterrupt
            real(path, obj)
        with mock.patch.object(storyboard, "plan", return_value={"board": {"bpm": 120}}), \
                mock.patch.object(_env, "write_json", cut), self.assertRaises(KeyboardInterrupt):
            storyboard.write_board({}, "swiss-grid")
        self.assertFalse((d / "plan.json").exists())
        with self.assertRaises(SystemExit) as e:
            storyboard.load_plans("swiss-grid")
        self.assertIn("plan.json is missing", str(e.exception.code))

    def test_a_look_written_again_takes_film_json_away_before_its_first_board(self):
        self.put("film.json", "{\"style\": \"swiss-grid\"}")
        with mock.patch.object(storyboard, "plan", return_value={"board": {"bpm": 120}}), \
                mock.patch.object(_env, "write_json", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            storyboard.write_board({}, "swiss-grid")
        self.assertFalse(Path("film.json").exists())

    def test_a_look_written_again_takes_its_sheet_away_and_the_ballot_reads_plan_json(self):
        d = storyboard.BOARDS / "swiss-grid"
        self.put(d / "sheet.png", "the sheet of the last boards")
        with self.assertRaises(SystemExit) as e:
            vote.cmd_ballot(None)
        self.assertIn("0 of 3 storyboards with plan.json and a sheet", str(e.exception.code))
        self.put(d / "plan.json", "{}")
        with mock.patch.object(storyboard, "plan", return_value={"board": {"bpm": 120}}), \
                mock.patch.object(_env, "write_json", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            storyboard.write_board({}, "swiss-grid")
        self.assertFalse((d / "sheet.png").exists())
        with self.assertRaises(SystemExit):
            vote.cmd_ballot(None)
        self.assertFalse(Path("vote/ballot.md").exists())

    def test_storyboard_md_is_written_whole_before_plan_json(self):
        d = storyboard.BOARDS / "swiss-grid"
        self.put(d / "storyboard.md", "the text of the last boards")
        real = _env.write_json

        def cut(path, obj):
            if Path(path).name == "plan.json":
                raise KeyboardInterrupt
            real(path, obj)
        with mock.patch.object(_env, "write_json", cut), self.assertRaises(KeyboardInterrupt):
            storyboard.write_board(SOURCE, "swiss-grid")
        self.assertFalse((d / "plan.json").exists())
        self.assertTrue((d / "storyboard.md").read_text().startswith("# swiss-grid:"))
        storyboard.write_board(SOURCE, "swiss-grid")
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["board-landscape.json", "board-reel.json", "board-square.json",
                                                               "plan.json", "storyboard.md"])

    def test_a_grade_cut_short_in_a_photograph_leaves_no_photos_json_and_the_photograph_as_it_was(self):
        self.put("cast.json", json.dumps({"visits": [{"place": "lisbon", "n": 1, "shots": ["a.jpg"]}]}))
        self.put("public/photos.json", "{\"photos\": []}")
        self.put("public/photos/lisbon-1-1.jpg", "the last grade")
        with mock.patch.object(grade, "toned", return_value=(None, False)), mock.patch.object(grade, "target_of", return_value=0.3), \
                mock.patch.object(grade, "finish", return_value=Half()), self.assertRaises(KeyboardInterrupt):
            grade.grade_cast()
        self.assertFalse(Path("public/photos.json").exists())
        self.assertEqual(Path("public/photos/lisbon-1-1.jpg").read_text(), "the last grade")

    def test_a_normalize_cut_short_leaves_clips_json_naming_frames_that_are_there(self):
        board = {"beats": [{"id": "hook", "frames": 3}],
                 "clips": [{"id": "01", "beat": "hook", "role": "r", "image": "photos/a.jpg", "prompt": "p", "stand_in": "s"}]}
        self.put("board.json", json.dumps(board))
        self.put("film.json", json.dumps({"boards": {"reel": "board.json"}}))
        self.put("clips/01.mp4", "x" * 2000)
        self.put("public/clips/old/01/0001.jpg", "the last frames")
        index = json.dumps({"clips": {"01": {"status": "generated", "dir": "clips/old/01", "frames": 1}}})
        self.put("clips.json", index)
        with mock.patch.object(clips, "conform", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            clips.cmd_normalize(types.SimpleNamespace(why=None))
        self.assertEqual(Path("clips.json").read_text(), index)
        self.assertEqual(Path("public/clips/old/01/0001.jpg").read_text(), "the last frames")

        def conform(src, image, frames, dst):
            self.put(dst / "0001.jpg", "new frames")
            return 1, ""
        with mock.patch.object(clips, "conform", conform):
            self.assertEqual(clips.cmd_normalize(types.SimpleNamespace(why=None)), 0)
        got = json.loads(Path("clips.json").read_text())["clips"]["01"]["dir"]
        self.assertEqual((Path("public") / got / "0001.jpg").read_text(), "new frames")
        self.assertFalse(Path("public/clips/old").exists())


class WrittenWhole(InARun):
    def test_a_photograph_copy_cut_short_is_made_again(self):
        self.put("a.jpg", "a photograph")
        dest = None
        with mock.patch.object(picks, "open_image", return_value=Half()), self.assertRaises(KeyboardInterrupt):
            picks.prepare("a.jpg")
        self.assertEqual(sorted(p.name for p in picks.PHOTOS.iterdir() if not p.name.startswith(".")), [])

        class Whole(Half):
            def save(self, path, *a, **kw):
                Path(path).write_text("whole")
        with mock.patch.object(picks, "open_image", return_value=Whole()):
            dest = picks.prepare("a.jpg")
        self.assertEqual(Path(dest).read_text(), "whole")

    def test_a_bed_cut_short_in_its_compose_leaves_the_source_as_it_was(self):
        self.put("music/source.wav", "the last bed")
        self.put("music.json", json.dumps({"file": "music/source.wav"}))

        def cut(*a, out, **kw):
            Path(out).mkdir(parents=True)
            (Path(out) / "bed.wav").write_text("half")
            raise KeyboardInterrupt
        with mock.patch.object(music.music_engine, "compose", cut), self.assertRaises(KeyboardInterrupt):
            music.cmd_make(types.SimpleNamespace(bpm=None, seconds=1))
        self.assertEqual(Path("music/source.wav").read_text(), "the last bed")
        self.assertEqual(json.loads(Path("music.json").read_text()), {"file": "music/source.wav"})

    def test_a_bed_cut_short_before_its_music_json_leaves_the_source_the_old_one_names(self):
        for old in ("music/source.mp3", "music/source.wav"):
            self.put(old, "the last track")
            self.put("music.json", json.dumps({"file": old}))
            self.make_cut_at_music_json()
            self.assertEqual(Path(old).read_text(), "the last track")
            self.assertEqual(json.loads(Path("music.json").read_text()), {"file": old})

    def make_cut_at_music_json(self):
        write = _env.write_json

        def cut(path, obj):
            if Path(path).name == "music.json":
                raise KeyboardInterrupt
            write(path, obj)
        with mock.patch.object(music.music_engine, "compose", composed), mock.patch.object(_env, "write_json", cut), \
                self.assertRaises(KeyboardInterrupt):
            music.cmd_make(types.SimpleNamespace(bpm=None, seconds=1))


def tone(path, seconds=1):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=d={seconds}", str(path)], check=True)


def composed(style=None, styles=(), avoid=(), seconds=1, edges=(), hue=None, seed="", bpm=None, out=None):
    """A stand-in for music_engine.compose: a second of tone at out/bed.wav, and what music.json carries of it."""
    tone(Path(out) / "bed.wav", seconds)
    return {"recipe": style or "pulse", "key": "A minor", "bpm": bpm, "seconds": seconds, "chords": ["Am"], "removed": []}


class FindsTheMusic(InARun):
    def setUp(self):
        super().setUp()
        for patch in (mock.patch.object(_env, "HOME", Path.cwd()), mock.patch.object(music.music_engine, "compose", composed)):
            patch.start()
            self.addCleanup(patch.stop)

    def find(self, origin=None):
        music.cmd_find(types.SimpleNamespace(origin=origin, bpm=None, seconds=1))
        return json.loads(Path("music.json").read_text())["file"]

    def test_find_after_a_make_cut_short_before_its_cleanup_keeps_the_bed_music_json_names(self):
        self.put("music.json", json.dumps({"file": "music/source.mp3"}))
        tone("music/source.mp3")
        music.cmd_make(types.SimpleNamespace(bpm=None, seconds=1))
        bed = json.loads(Path("music.json").read_text())["file"]
        # the track the old music.json named, still there as a make killed before its cleanup leaves it
        tone("music/source.mp3")
        os.utime("music/source.mp3", ns=(1, 1))
        self.assertEqual(self.find(), bed)

    def test_find_after_make_takes_a_new_source_and_never_a_generated_one(self):
        music.cmd_make(types.SimpleNamespace(bpm=None, seconds=1))
        bed = json.loads(Path("music.json").read_text())["file"]
        # the bed and its effects are the music folder's one folder, the track before it gone
        self.assertEqual([p.name for p in Path("music").iterdir()], [Path(bed).parent.name])
        tone("music/source.mp3")
        tone("music/source.tag.wav")
        self.assertEqual(self.find(), "music/source.mp3")
        self.assertEqual(self.find(), "music/source.mp3")

    def test_a_master_made_again_leaves_the_master_music_json_names_whole_until_the_new_music_json(self):
        tone("music/bed.wav", 2)
        self.put("film.json", json.dumps({"seconds": 1.5, "bpm": 120, "sound": []}))
        self.put("music.json", json.dumps({"file": "music/bed.wav", "master": "music/master-old.wav"}))
        self.put("music/master-old.wav", "the last master")
        write = _env.write_json

        def cut(path, obj):
            if Path(path).name == "music.json":
                raise KeyboardInterrupt
            write(path, obj)
        with mock.patch.object(_env, "write_json", cut), self.assertRaises(KeyboardInterrupt):
            music.cmd_master(types.SimpleNamespace(seconds=None))
        self.assertEqual(Path("music/master-old.wav").read_text(), "the last master")
        self.assertEqual(json.loads(Path("music.json").read_text())["master"], "music/master-old.wav")
        music.cmd_master(types.SimpleNamespace(seconds=None))
        new = json.loads(Path("music.json").read_text())["master"]
        self.assertTrue(Path(new).exists())
        self.assertFalse(Path("music/master-old.wav").exists())


class CriticRound(InARun):
    def test_a_round_opens_only_on_a_render_its_report_vouches_for(self):
        self.put("out/film.mp4", "reel a")
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(None)
        self.assertIn("render/film-report.json", str(e.exception.code))
        self.assertEqual(vote.rounds(), [])

    def test_the_same_reel_keeps_its_round_and_a_new_reel_opens_the_next(self):
        self.put("render/film-report.json", "{}")
        mock.patch.object(vote, "cut_frames", return_value=[]).start()
        self.addCleanup(mock.patch.stopall)
        self.put("out/film.mp4", "reel a")
        self.assertEqual(vote.cmd_cut(None), 0)
        self.assertEqual(vote.cmd_cut(None), 0)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])
        self.put("out/film.mp4", "reel b")
        self.assertEqual(vote.cmd_cut(None), 0)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])


class ToolsFirst(InARun):
    def test_the_tools_resolve_before_the_lock_is_taken(self):
        order, real = [], chunks.lock

        def lock(*a):
            order.append("lock")
            return real(*a)
        with mock.patch.object(_env, "tools", side_effect=lambda: order.append("tools") or {}), \
                mock.patch.object(chunks, "lock", lock):
            with studio.lock("film"):
                pass
        self.assertEqual(order, ["tools", "lock"])


if __name__ == "__main__":
    unittest.main()
