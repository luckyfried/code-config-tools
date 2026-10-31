"""The film's sound sits under its music: the gate's audio row reads the effects stem against the bed by loudness.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import contextlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import _env  # noqa: E402
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
    def audio_row(self, fx_lufs):
        """The gate's audio row over a film at -14 LUFS whose master measured the bed at -21.4 LUFS and the effects at
        `fx_lufs`."""
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"")
        _env.write_json("film.json", {"system": {"colors": {"bg": "#412F20"}}, "beats": [{"id": "hook"}, {"id": "making-1"}, {"id": "closer"}],
                                      "sound": [{"kind": "impact", "at": 3.6}, {"kind": "hit", "at": 6.25}]})
        _env.write_json("music.json", {"file": "music/source-a1.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs, "sound_cues": 2})
        probed = {"streams": [{"codec_type": "video"}, {"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}],
                  "format": {"duration": "27.6"}}
        with contextlib.ExitStack() as s:
            for name, fn in (("probe", lambda film, spawn: probed), ("loudness", lambda film, spawn: -14.0), ("detect", lambda *a: []),
                             ("frame0_check", lambda *a: (True, "")), ("hook_check", lambda *a: (True, "")),
                             ("cuts_figure", lambda *a: ""), ("still_figure", lambda *a: ""), ("board_checks", lambda *a: None)):
                s.enter_context(mock.patch.object(qa, name, fn))
            res = qa.film_checks(Path("out/film.mp4"), audio=True)
        return next(r for r in res if r[0] == "audio")

    def test_an_effects_stem_peak_normalized_over_a_quiet_bed_turns_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-16.3)
        self.assertFalse(ok, detail)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("2 sound cues over 3 beats", detail)

    def test_effects_eight_lu_under_the_bed_turn_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-29.4)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)


if __name__ == "__main__":
    unittest.main()
