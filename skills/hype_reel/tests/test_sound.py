"""The film's sound: music.py master writes the music alone, cut on the board's stop and brought to -14 LUFS by one
gain, its peaks kept whole in float; the shared effects (sfx.py) are laid at the mux; and the gate's audio row reads
the whole track's loudness and true peak.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import _env  # noqa: E402
import music  # noqa: E402
import qa  # noqa: E402


class Here(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(d.cleanup)
        cwd = os.getcwd()
        os.chdir(d.name)
        self.addCleanup(os.chdir, cwd)
        self.dir = Path(d.name)


class AudioRow(Here):
    def audio_row(self, lufs, peak):
        """The gate's audio row over a film whose whole track (the music with the shared effects over it) measures `lufs`
        integrated and `peak` dBTP."""
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"")
        _env.write_json("film.json", {"system": {"colors": {"bg": "#412F20"}}, "beats": [{"id": "hook"}, {"id": "making-1"}, {"id": "closer"}],
                                      "sound": [{"kind": "impact", "at": 3.6}, {"kind": "hit", "at": 6.25}]})
        _env.write_json("music.json", {"file": "music/source-a1.wav", "bed_lufs": -21.4, "master_lufs": -14.0})
        probed = {"streams": [{"codec_type": "video"}, {"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}],
                  "format": {"duration": "27.6"}}
        with contextlib.ExitStack() as s:
            for name, fn in (("probe", lambda film, spawn: probed), ("loudness", lambda film, spawn: (lufs, peak)), ("detect", lambda *a: []),
                             ("frame0_check", lambda *a: (True, "")), ("hook_check", lambda *a: (True, "")),
                             ("cuts_figure", lambda *a: ""), ("still_figure", lambda *a: ""), ("board_checks", lambda *a: None)):
                s.enter_context(mock.patch.object(qa, name, fn))
            res = qa.film_checks(Path("out/film.mp4"), audio=True)
        return next(r for r in res if r[0] == "audio")

    def test_the_whole_track_at_minus_14_lufs_under_minus_1_5_dbtp_turns_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-14.0, -2.1)
        self.assertTrue(ok, detail)
        self.assertIn("aac 192 kbps, -14.0 LUFS integrated, true peak -2.1 dBTP; ", detail)
        self.assertIn("the music and the shared effects (sfx.py) mastered together over 3 beats", detail)
        self.assertNotIn("bed", detail)

    def test_a_true_peak_over_minus_1_5_dbtp_turns_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-14.0, -1.0)
        self.assertFalse(ok, detail)
        self.assertIn("true peak -1.0 dBTP", detail)

    def test_a_track_off_minus_14_lufs_by_more_than_1_lu_turns_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-15.2, -3.0)
        self.assertFalse(ok, detail)


class Peak(Here):
    def test_the_bed_lifts_into_the_boards_peak_beat(self):
        b = {"bpm": 120, "beats": [{"id": "hook", "start": 0, "len": 6, "peak": False},
                                   {"id": "made", "start": 26, "len": 7, "peak": True},
                                   {"id": "closer", "start": 33, "len": 8, "peak": False}]}
        _env.write_json("winner.json", {"storyboard": b})
        seen = {}

        def compose(*args, **kw):
            seen.update(kw)
            raise SystemExit(0)
        with mock.patch.object(music.music_engine, "compose", compose), \
                mock.patch.object(music.music_engine, "resolve", lambda *a: ("swiss-grid", None, None)), \
                mock.patch.object(music, "brief", lambda: {}), self.assertRaises(SystemExit):
            music.cmd_make(argparse.Namespace(seconds=None))
        self.assertEqual(seen["peak"], (13.0, 16.5))


class Master(Here):
    def test_master_is_the_music_alone_cut_on_the_stop_with_no_effects_in_it(self):
        """The board's sound cues place nothing in the master: the film's effects are sfx.py's, laid at the mux. The
        impact on beat 2 leaves the music's level where it is, and the stop (beat 10, 5 s) cuts the music to silence."""
        music.MUSIC.mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=8:c=pink:a=0.05", "-ar", "48000",
                        "music/source.wav"], check=True)
        _env.write_json("music.json", {"file": "music/source.wav", "bpm": 120, "fx_lufs": -30.0, "sound_cues": 3})
        _env.write_json("film.json", {"seconds": 7.0, "bpm": 120, "music_offset": 0, "beats": [{"id": "hook"}, {"id": "closer"}],
                                      "sound": [{"kind": "impact", "at": 2.0}, {"kind": "hit", "at": 6.0, "weight": 1.0},
                                                {"kind": "riser", "at": 6.0, "beats": 2}, {"kind": "stop", "at": 10.0}]})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_master(argparse.Namespace(seconds=None)), 0)
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.5)
        for k in ("fx_lufs", "sound_cues", "fx"):
            self.assertNotIn(k, info)
        self.assertFalse((music.MUSIC / "fx.wav").exists(), "no effects stem: the film's effects are laid at render")
        for name in ("FX_UNDER_BED_LU", "RISER_GAIN", "effects", "cue_legs", "fx_stem"):
            self.assertFalse(hasattr(music, name), name)

        def span(f, a, b):
            """The RMS level (dBFS) of `f` between `a` and `b` seconds."""
            r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", f, "-af", f"atrim={a}:{b},astats=measure_perchannel=none",
                                "-f", "null", "-"], capture_output=True, text=True)
            level = re.findall(r"RMS level dB:\s+(-?[\d.]+|-inf)", r.stderr)[-1]
            return -200.0 if level == "-inf" else float(level)
        # the master is the music times one gain: the same gain around the impact (beat 2, 1 s) as before it
        gain = lambda a, b: span(info["master"], a, b) - span("music/source.wav", a, b)  # noqa: E731
        self.assertAlmostEqual(gain(0.2, 0.8), gain(0.9, 1.5), delta=0.1)
        self.assertLess(span(info["master"], 5.2, 7.0), -60)

    def test_a_peaky_track_reaches_the_target_by_one_gain_and_keeps_its_peaks_whole(self):
        """Sharp clicks over a quiet bed need peaks past full scale to reach -14 LUFS. master reads the loudness once and
        sets one gain, with no limiter, and writes the master in 32-bit float, so the clicks stand past full scale
        unclipped and the film's mux (sfx.py) is the only thing that limits them."""
        music.MUSIC.mkdir()
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=7:c=pink:a=0.01", "-f", "lavfi", "-i",
                        "aevalsrc='if(lt(mod(t,0.25),0.004),0.9,0)':d=7:s=48000", "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0", "-ar", "48000", "music/source.wav"], check=True)
        _env.write_json("music.json", {"file": "music/source.wav", "bpm": 120})
        _env.write_json("film.json", {"seconds": 6.0, "bpm": 120, "music_offset": 0})
        calls, real = [], subprocess.run

        def run(argv, **kw):
            calls.append([str(x) for x in argv])
            return real(argv, **kw)
        with mock.patch.object(music.subprocess, "run", run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(music.cmd_master(argparse.Namespace(seconds=None)), 0)
        info = _env.read_json("music.json")
        self.assertAlmostEqual(info["master_lufs"], music.TARGET_LUFS, delta=0.2)
        self.assertFalse([c for c in calls if any("alimiter" in x for x in c)], "no limiter in the master")
        written = next(i for i, c in enumerate(calls) if "master" in Path(c[-1]).name)
        self.assertEqual(sum("ebur128" in " ".join(c) for c in calls[:written]), 1, "one loudness read, then one gain")
        self.assertEqual(calls[written][-3:-1], ["-c:a", "pcm_f32le"])
        said = real([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", info["master"], "-af", "astats=measure_perchannel=none", "-f", "null",
                     "-"], capture_output=True, text=True).stderr
        self.assertGreater(float(re.findall(r"Peak level dB: (-?[\d.]+)", said)[-1]), 0.0,
                           "the clicks stand past full scale in the float master, unclipped")

if __name__ == "__main__":
    unittest.main()
