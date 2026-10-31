"""The sound under the person's music: the shared effects (sfx.py) only where a beat lands, keyed and on the music's
grid, laid and mastered with the music by the shared mux under -1.5 dBTP, the music mastered alone by one gain,
the bed composed by the music engine in the winning look's recipe at the board's tempo, and the person's own track
winning when they placed one.

    python3 -m unittest discover -s S/tests -p test_audio.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fixture

import _env  # noqa: E402
import compose  # noqa: E402
import film  # noqa: E402
import music  # noqa: E402
import qa  # noqa: E402
import sfx  # noqa: E402
import studio  # noqa: E402
from compose import sound  # noqa: E402
from test_compose import picked  # noqa: E402

KINDS = set(sound.SAID) | {"stop"}
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
        self.assertLessEqual(set(kinds), KINDS)
        # the title's line lands on an impact, every cut after the first card on a whoosh, every photograph on its
        # landing, and the closer takes the one riser with an impact on it
        self.assertEqual(kinds.count("riser"), 1)
        self.assertGreaterEqual(kinds.count("impact"), 2)
        self.assertEqual(sum(kinds.count(k) for k in ("bright", "sweep", "air")), len(r["cards"]))
        self.assertEqual(sum(kinds.count(k) for k in ("shutter", "pop")), len(r["cards"]) - 1)
        self.assertLessEqual(kinds.count("bright"), 1)
        self.assertEqual(kinds[-1], "stop")
        # the storyboard's lines are exactly the effects the shared layer lays, nothing played twice
        self.assertEqual(len(r["sound"]) - 1, len(sfx.events(r["fx"], r["bpm"])[0]))

    def test_every_effect_sits_on_the_musics_quarter_beat_from_frame_0(self):
        r = self.board["reel"]
        step = 60 / r["bpm"] / sfx.GRID
        for t, kind in sfx.events(r["fx"], r["bpm"])[0]:
            self.assertAlmostEqual(t / step, round(t / step), places=4, msg=(kind, t))

    def test_a_card_sounds_only_where_its_line_lands(self):
        for c in self.board["beats"]:
            kinds = [x["kind"] for x in c["sound"]]
            self.assertLessEqual(set(kinds), KINDS, c["id"])
            self.assertLessEqual(len(kinds), 4, f"{c['id']}: {kinds}")
            self.assertIn("impact", kinds, c["id"])


def ff(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *map(str, args)], capture_output=True, text=True)


def ebur(path, chain=""):
    """(integrated loudness, true peak) of a file's sound, read by ebur128 here, apart from qa.py."""
    said = ff("-i", path, "-af", f"{chain + ',' if chain else ''}ebur128=peak=true:framelog=quiet", "-vn", "-f", "null", "-").stderr
    tp = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", said)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", said)[-1]), float(tp[-1])


def peaky_bed(path, seconds, noise=0.01, click=0.9):
    """Pink noise of amplitude `noise` with sharp clicks of amplitude `click` four times a second: with the defaults,
    music whose peaks stand far over its loudness."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=pink:a={noise}:seed=3", "-f", "lavfi",
                    "-i", f"aevalsrc='if(lt(mod(t,0.25),0.004),{click},0)':d={seconds}:s=48000", "-filter_complex",
                    "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", "-ac", "2", str(path)], check=True)


def silent_film(path, seconds):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s=64x64:r=30:d={seconds}", "-pix_fmt", "yuv420p",
                    str(path)], check=True)


class Mix(unittest.TestCase):
    """Every video's sound: the music alone mastered by one gain, the effects laid over it and the two mastered together
    by the shared mux, once."""

    @classmethod
    def setUpClass(cls):
        cls.board = compose.board("editorial-quiet", picked(fixture.month()))

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_master_is_the_music_alone_at_minus_14_by_one_gain_kept_whole_in_float(self):
        bed, out = self.d / "bed.wav", self.d / "out.wav"
        peaky_bed(bed, 8)
        got = music.master(bed, 6.0, out, stop=5.5)
        self.assertAlmostEqual(got["lufs"], music.TARGET_LUFS, delta=0.3)
        codec = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(codec, "pcm_f32le")
        peak = float(re.findall(r"Peak level dB: (-?[\d.]+)", ff("-i", out, "-af", "astats=measure_perchannel=none", "-f", "null", "-").stderr)[-1])
        self.assertGreater(peak, 0.0, "the clicks stand past full scale in the float master, unclipped: the mux limits them")
        after = ff("-i", out, "-af", "atrim=5.6,astats=measure_perchannel=none", "-f", "null", "-").stderr
        self.assertIn("Peak level dB: -inf", after, "the music has cut at the stop")
        self.assertAlmostEqual(seconds_of(out), 6.0, delta=0.05)

    def test_the_reels_sound_is_laid_and_mastered_by_the_mux_in_one_encode_under_minus_1_5_dbtp(self):
        r = self.board["reel"]
        secs, stop = r["frames"] / r["fps"], film.stop_of(r)
        bed, silent, out = self.d / "bed.wav", self.d / "silent.mp4", self.d / "film.mp4"
        # noise, the band the AAC encoder's noise substitution would swap and overshoot the limiter on
        peaky_bed(bed, secs + 2, noise=0.2, click=0)
        silent_film(silent, secs)
        spawned = []

        def spawn(argv, **kw):
            spawned.append([str(x) for x in argv])
            return subprocess.run(argv, **kw)

        film.sound(silent, bed, secs, out, r["fx"], {"bpm": self.board["bpm"]}, stop=stop, spawn=spawn)
        encodes = [a for a in spawned if "aac" in a]
        self.assertEqual(len(encodes), 1, encodes)
        self.assertEqual(encodes[0][encodes[0].index("-aac_pns") + 1], "0")
        self.assertIn(sfx.LIMIT, " ".join(encodes[0]))
        lufs, tp = ebur(out)
        self.assertAlmostEqual(lufs, -14.0, delta=1.0)
        self.assertLessEqual(tp, -1.5)
        self.assertEqual(qa.levels(out), (lufs, tp))
        self.assertTrue(qa.stopped(qa.silences(out), stop, secs)[0], qa.silences(out))

    def test_a_card_lays_the_series_effects_at_the_series_frames(self):
        whole = sfx.events(film.series_fx(self.board), self.board["bpm"])[0]
        at = 0
        for c in self.board["beats"]:
            f = studio.card_frames(self.board, c)
            s0, s1 = at / studio.FPS, (at + f) / studio.FPS
            want = [(round(t - s0, 4), k) for t, k in whole if s0 <= t < s1]
            got = [(round(t, 4), k) for t, k in sfx.events(film.series_fx(self.board, at), self.board["bpm"])[0] if 0 <= t < s1 - s0]
            self.assertEqual(got, want, c["id"])
            self.assertTrue(want, c["id"])
            at += f

    def test_after_the_stop_the_room_plays_alone_and_music_past_it_is_red(self):
        r = self.board["reel"]
        secs, stop = r["frames"] / r["fps"], film.stop_of(r)
        bed, silent = self.d / "bed.wav", self.d / "silent.mp4"
        # a full bed, its loudness near its peaks as music's is, mastered as a film's music is: cut at the stop, or
        # running on past the film's end
        peaky_bed(bed, secs + 2, noise=0.2, click=0)
        silent_film(silent, secs)
        for length, cut, want in ((secs, stop, True), (secs + 2, None, False)):
            m, out = self.d / f"music-{want}.wav", self.d / f"film-{want}.mp4"
            music.master(bed, length, m, stop=cut)
            sfx.mux(subprocess.run, silent, out, secs, r["fx"], {"master": str(m), "bpm": self.board["bpm"]}, "ffmpeg")
            ok, said = qa.stopped(qa.silences(out), stop, secs)
            self.assertEqual(ok, want, said)


class AudioRow(unittest.TestCase):
    def audio_row(self, tp):
        """qa.py's audio row over a reel at -14 LUFS whose true peak measures `tp` dBTP."""
        run_ = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, run_, ignore_errors=True)
        board = compose.board("editorial-quiet", picked(fixture.month()))
        r = board["reel"]
        (run_ / "out").mkdir()
        (run_ / "out" / "film.mp4").write_bytes(b"the film")
        _env.write_json(run_ / "film.json", board)
        v = {"codec_type": "video", "codec_name": "h264", "profile": "High", "width": 1080, "height": 1920, "pix_fmt": "yuv420p",
             "r_frame_rate": "30/1"}
        a = {"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}
        measured = {"cuts": 0, "cuts_per_minute": 0, "planned_cuts": [], "extra_scene_cuts": [], "luma": [], "strip": "s", "strip2": "s",
                    "seconds_under_half": 0, "longest_run_under_half": 0, "hook_frame": 0, "hook_ok": True}
        c = qa.Checks()
        with mock.patch.object(qa, "probe", lambda p, spawn=None: (v, a, r["frames"] / r["fps"])), \
                mock.patch.object(qa, "levels", lambda p, spawn=None: (-14.0, tp)), \
                mock.patch.object(qa, "blacks", lambda p, spawn=None: []), mock.patch.object(qa, "frozen", lambda *x, **k: []), \
                mock.patch.object(qa, "silences", lambda p, spawn=None: []), mock.patch.object(qa, "frame_look", lambda *x: (True, "")), \
                mock.patch.object(qa.studio, "measure", lambda *x, **k: dict(measured)):
            qa.render_checks(run_, c)
        return next(row for row in c.rows if row["check"] == "audio")

    def test_a_reel_under_minus_1_5_dbtp_at_minus_14_lufs_is_green(self):
        row = self.audio_row(-2.4)
        self.assertTrue(row["pass"], row["detail"])
        self.assertIn("true peak at most -2.4 dBTP (the ceiling -1.5)", row["detail"])
        self.assertIn("sound effects over", row["detail"])

    def test_a_true_peak_over_minus_1_5_dbtp_is_red(self):
        row = self.audio_row(-1.2)
        self.assertFalse(row["pass"], row["detail"])
        self.assertIn("true peak over -1.5 dBTP in ['film']", row["detail"])


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

    def test_the_bed_lifts_into_the_peak_beat_from_its_landing_to_its_end(self):
        self.brief(BRIEF)
        info, _, _ = self.made()
        board = json.loads((self.build / "storyboards" / "editorial-quiet" / "storyboard.json").read_text())
        r = board["reel"]
        beat = next(b for b in r["timeline"]["beats"] if b.get("peak"))
        land, end = info["peak"]
        self.assertEqual([land, end], list(music.peak(board)))
        self.assertAlmostEqual(end, beat["end"] * 60 / r["bpm"], delta=0.002)
        self.assertTrue(beat["at"] * 60 / r["bpm"] - 0.002 <= land < end, (land, end))

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

    def test_every_frozen_stretch_counts_the_ending_too(self):
        # the closer keeps its slow push to the last frame, so a picture that stands still past the stop is frozen
        # like a stall in the middle
        self.assertEqual(qa.frozen("film.mp4", self.found(13.433333)), [13.433333])
        self.assertEqual(qa.frozen("film.mp4", self.found(6.2, 14.9)), [6.2, 14.9])
        self.assertEqual(qa.frozen("film.mp4", self.found()), [])
