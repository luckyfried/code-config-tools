"""qa.py's measures that need no film: the placeholder scan, where a board holds still to its end, where the hook frame
puts its photograph's subject, the render report's findings, and the audio rows of the gate and of the critic's
check."""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _env  # noqa: E402
import qa  # noqa: E402


class Placeholder(unittest.TestCase):
    def test_their_words_pass(self):
        for t in ("5 posts fit none of them", "none of your inks", "what's yours?", "banana bread, sunday"):
            self.assertIsNone(qa.PLACEHOLDER.search(t), t)

    def test_leaked_values_fail(self):
        for t in ("None", "olive NaN%", "TODO", "{{handle}}", "undefined a week", "lorem ipsum", "@handle"):
            self.assertIsNotNone(qa.PLACEHOLDER.search(t), t)


class HeldFrom(unittest.TestCase):
    def test_the_closers_still_is_where_the_picture_may_hold(self):
        self.assertEqual(qa.held_from({"bpm": 120, "closer": {"still": 28}, "sound": [{"kind": "hit", "at": 3}]}), 14.0)

    def test_a_board_whose_closer_never_stills_never_holds(self):
        self.assertEqual(qa.held_from({"bpm": 120, "closer": {}, "sound": [{"kind": "stop", "at": 28}]}), float("inf"))


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
class Subject(unittest.TestCase):
    def subject(self, draw):
        import os
        import random
        import tempfile
        from PIL import Image
        import picks
        rnd = random.Random(7)
        im = Image.new("RGB", (640, 420), (200, 210, 215))
        draw(im, rnd)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            path = Path(d) / "photo.jpg"
            im.save(path, quality=95)
            return picks.subject(path)

    def test_a_couple_on_an_empty_beach_is_the_subject(self):
        def couple(im, rnd):
            for x in range(430, 470):
                for y in range(230, 290):
                    im.putpixel((x, y), (rnd.randrange(256), 30, 40))
        (u, v), plain = self.subject(couple)
        self.assertTrue(plain)
        self.assertAlmostEqual(u, 0.7, delta=0.06)
        self.assertAlmostEqual(v, 0.62, delta=0.08)

    def test_a_picture_busy_all_over_takes_where_its_detail_gathers(self):
        def busy(im, rnd):
            for x in range(0, 640, 2):
                for y in range(0, 420, 2):
                    im.putpixel((x, y), (rnd.randrange(256),) * 3)
        (u, v), plain = self.subject(busy)
        self.assertFalse(plain)
        self.assertTrue(0.3 <= u <= 0.7 and 0.3 <= v <= 0.7, (u, v))


class HookSubject(unittest.TestCase):
    """The hook frame's subject, read where the film lays its photograph: the photograph covers its box `zoom` times
    closer around its subject."""

    def board(self, box, aspect=1.5, zoom=1.0, **subject):
        return {"format": {"width": 1080, "height": 1920, "name": "reel"},
                "beats": [{"id": "hook", "picture": dict({"box": box, "aspect": aspect, "zoom": zoom}, **subject)}]}

    def test_a_full_frame_photograph_puts_its_subject_where_it_stands(self):
        self.assertEqual(qa.hook_subject(self.board([0, 0, 1080, 1920], aspect=1920 / 1080, subject=[0.5, 0.6])), (0.5, 0.6))

    def test_a_plain_photographs_subject_is_read_as_its_room(self):
        x0, y0, x1, y1 = qa.hook_subject(self.board([0, 0, 1080, 1920], aspect=1920 / 1080, subject=[0.5, 0.6], plain=True))
        self.assertAlmostEqual(x0, 0.5 - qa.ROOM[0], places=3)
        self.assertAlmostEqual(y1, 0.6 + qa.ROOM[1], places=3)

    def test_a_close_crop_keeps_the_subject_in_the_frame(self):
        x, y = qa.hook_subject(self.board([0, 0, 1080, 1920], aspect=0.66, zoom=1.3, subject=[0.9, 0.5]))
        self.assertTrue(qa.HELD <= x <= 1 - qa.HELD, x)

    def test_a_hook_without_a_photograph_or_subject_reads_nothing(self):
        self.assertIsNone(qa.hook_subject({"beats": [{"id": "hook"}]}))
        self.assertIsNone(qa.hook_subject(self.board([0, 0, 1080, 1920])))


class Safe(unittest.TestCase):
    """The safe check reads the render report alone: a resumed render keeps the log of the attempt that wrote it, so a
    shader error the renderer retried past stays in that log after the report is clean."""

    def check(self, log_text, findings):
        import json
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            film, report = Path(d) / "film.mp4", Path(d) / "film-report.json"
            film.write_bytes(b"")
            report.write_text(json.dumps({"jobs": 1, "failed": 0, "findings": findings}))
            (Path(d) / "film.log").write_text(log_text)
            lo = qa.storyboard.LENGTH[0]
            stream = {"codec_type": "video", "width": 1080, "height": 1920, "codec_name": "h264", "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}
            with mock.patch.object(qa, "probe", return_value={"streams": [stream], "format": {"duration": str(lo)}}), \
                    mock.patch.object(qa, "detect", return_value=[]), mock.patch.object(qa, "yavg", return_value=[0.4]), \
                    mock.patch.object(qa, "held_from", return_value=lo):
                res = qa.Checks()
                qa.picture(res, film, "reel", {}, str(report))
        return next(r for r in res if r[0] == "safe")

    def test_a_retried_shader_error_in_the_log_with_a_clean_report_passes(self):
        row = self.check("retrying 0-449.part.mp4 (attempt 2 of 3): GL_LOST THREE.WebGLProgram: Shader Error 0\n", [])
        self.assertTrue(row[1], row[2])

    def test_a_font_finding_in_the_report_fails(self):
        row = self.check("", [{"job": "x", "text": "FONT_ERROR Inter did not load"}])
        self.assertFalse(row[1], row[2])



class Frozen(unittest.TestCase):
    """The frozen row reads the whole film: the closer keeps its slow push from the stop to the last frame, so a
    frozen stretch inside the closer, its ending too, is a stall."""

    def row(self, freezes):
        import json
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            film, report = Path(d) / "film.mp4", Path(d) / "film-report.json"
            film.write_bytes(b"")
            report.write_text(json.dumps({"jobs": 1, "failed": 0, "findings": []}))
            lo = qa.storyboard.LENGTH[0]
            stream = {"codec_type": "video", "width": 1080, "height": 1920, "codec_name": "h264", "pix_fmt": "yuv420p", "r_frame_rate": "30/1"}
            found = lambda film, flt, key: [f"[freezedetect] {key}: {at}" for at in freezes] if "freeze" in flt else []
            board = {"bpm": 120, "closer": {"at": 22, "still": 26}}
            with mock.patch.object(qa, "probe", return_value={"streams": [stream], "format": {"duration": str(lo)}}), \
                    mock.patch.object(qa, "detect", found), mock.patch.object(qa, "yavg", return_value=[0.4]):
                res = qa.Checks()
                qa.picture(res, film, "reel", board, str(report))
        return next(r for r in res if r[0] == "frozen")

    def test_a_film_that_never_freezes_passes(self):
        self.assertTrue(self.row([])[1])

    def test_a_frozen_stretch_after_the_stop_fails(self):
        row = self.row([13.5])
        self.assertFalse(row[1], row[2])
        self.assertIn("from 13.50 s", row[2])


class AudioRow(unittest.TestCase):
    """The gate's audio row reads the bed's and the effects' loudness music.py master measured, and names them with the
    cue and beat counts."""

    def row(self, fx_lufs):
        """The audio row over three films at -14 LUFS whose master measured the bed at -21.4 LUFS and the effects at
        `fx_lufs`."""
        import json
        import os
        import tempfile
        from unittest import mock
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                Path("out").mkdir()
                for film in qa.FILMS.values():
                    film.write_bytes(b"")
                Path("board.json").write_text(json.dumps({"bpm": 120, "beats": [{"id": "hook"}, {"id": "piece-1"}, {"id": "closer"}],
                                                          "sound": [{"kind": "impact", "at": 0.8, "beat": "hook"}, {"kind": "hit", "at": 5.8, "beat": "piece-1"}]}))
                Path("film.json").write_text(json.dumps({"boards": dict.fromkeys(qa.FILMS, "board.json"), "findings": []}))
                Path("music.json").write_text(json.dumps({"file": "music/source.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs, "sound_cues": 2}))
                probed = {"streams": [{"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}]}
                with mock.patch.object(qa, "picture"), mock.patch.object(qa, "subject_check"), mock.patch.object(qa, "project"), \
                        mock.patch.object(qa, "probe", return_value=probed), mock.patch.object(qa, "loudness", return_value=-14.0):
                    res, _ = qa.gate_checks()
            finally:
                os.chdir(here)
        return next(r for r in res if r[0] == "audio")

    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_turns_the_audio_row_red(self):
        _, ok, detail = self.row(-16.3)
        self.assertFalse(ok, detail)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("2 sound effects over 3 beats", detail)

    def test_effects_eight_lu_under_the_bed_turn_the_audio_row_green(self):
        _, ok, detail = self.row(-29.4)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)


class CheckAudioRow(unittest.TestCase):
    """The critic's check reads the sound from the cut it watches, which carries the master: check.json's audio row
    names the master's, the bed's and the effects' loudness, the gap under the floor, the cues over the beats, and
    where the sound falls quiet against the stop."""

    def audio_row(self, quiet):
        """The check's audio row over a cut whose sound falls quiet for good at `quiet` seconds (None: never)."""
        import json
        import os
        import tempfile
        from unittest import mock
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                qa.CUT.write_bytes(b"")
                Path("board.json").write_text(json.dumps({"bpm": 120, "beats": [{"id": "hook"}, {"id": "piece-1"}, {"id": "closer"}],
                                                          "sound": [{"kind": "impact", "at": 0.8, "beat": "hook"}, {"kind": "hit", "at": 5.8, "beat": "piece-1"},
                                                                    {"kind": "stop", "at": 42.0, "beat": "closer"}],
                                                          "closer": {"still": 42.0}}))
                Path("film.json").write_text(json.dumps({"boards": dict.fromkeys(qa.FILMS, "board.json"), "findings": [], "hook_frame": 10}))
                Path("music.json").write_text(json.dumps({"file": "music/source.wav", "master_lufs": -14.2, "bed_lufs": -21.4, "fx_lufs": -29.6,
                                                          "sound_cues": 2, "origin": "made from their brief: calm at 108 bpm"}))
                probed = {"streams": [{"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}]}
                with mock.patch.object(qa, "picture"), mock.patch.object(qa, "subject_check"), mock.patch.object(qa, "project"), \
                        mock.patch.object(qa, "probe", return_value=probed), mock.patch.object(qa, "loudness", return_value=-14.0), \
                        mock.patch.object(qa.sfx, "quiet_from", return_value=quiet):
                    res, _ = qa.check_checks()
            finally:
                os.chdir(here)
        return next(r for r in res if r[0] == "audio")

    def test_the_check_names_every_sound_number_from_the_cut(self):
        _, ok, detail = self.audio_row(20.9)
        self.assertTrue(ok, detail)
        for said in ("cut.mp4: aac 192 kbps, -14.0 LUFS integrated", "master -14.2 LUFS, bed -21.4 LUFS, effects -29.6 LUFS",
                     "8.2 LU under (at least 8)", "2 sound effects over 3 beats", "quiet under -30 dB from 20.90 s to the end, the picture still from 21.00 s",
                     "the bed: made from their brief"):
            self.assertIn(said, detail)

    def test_a_bed_that_plays_past_the_held_picture_to_the_last_frame_turns_the_row_red(self):
        _, ok, detail = self.audio_row(None)
        self.assertFalse(ok, detail)
        self.assertIn("never quiet under -30 dB before the end, the picture still from 21.00 s", detail)


class QuietFrom(unittest.TestCase):
    """Where a film's sound falls quiet to its end, read from a real file: ffmpeg closes a silence that runs to the end
    of the stream at the stream's end, and that silence is the film's quiet."""

    def film(self, d, chain):
        out = Path(d, "f.m4a")
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", chain, "-c:a", "aac", str(out)], check=True)
        return out

    def test_a_tone_that_stops_is_quiet_from_where_it_stops_to_the_end(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            got = qa.sfx.quiet_from(_env.ffmpeg(), self.film(d, "sine=f=220:d=4,volume=enable='gte(t,2.5)':volume=0"))
        self.assertIsNotNone(got)
        self.assertAlmostEqual(got, 2.5, delta=0.1)

    def test_the_room_under_the_film_after_its_music_stops_is_quiet(self):
        import os
        import tempfile
        # a tone that stops at 2.5 s over a room as loud as the shared sound layer's to the end: -46 dB, peaks near -34
        room = ("sine=f=220:d=4:r=48000,volume=enable='gte(t,2.5)':volume=0[s];"
                "anoisesrc=d=4:c=pink:a=0.03:r=48000,lowpass=f=2000[n];[s][n]amix=inputs=2:normalize=0[out0]")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            got = qa.sfx.quiet_from(_env.ffmpeg(), self.film(d, room))
        self.assertIsNotNone(got)
        self.assertAlmostEqual(got, 2.5, delta=0.1)

    def test_a_tone_to_the_end_is_never_quiet(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            got = qa.sfx.quiet_from(_env.ffmpeg(), self.film(d, "sine=f=220:d=4,volume=enable='between(t,1,2)':volume=0"))
        self.assertIsNone(got)


if __name__ == "__main__":
    unittest.main()
