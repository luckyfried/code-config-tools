"""The black check sees a single black frame: a photograph the page failed to load leaves one or a few frames black,
and a film with one is never called green.

    python3 -I -m unittest discover -s S/tests
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import qa  # noqa: E402


def clip(path, black):
    """Two seconds of a warm paper color, with frame 30 black when `black`."""
    box = ["-vf", "drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='eq(n,30)',format=yuv420p"] if black else ["-vf", "format=yuv420p"]
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=0xc8b8a0:s=270x480:r=30:d=2", *box,
                    "-c:v", "libx264", "-qp", "0", str(path)], check=True)


class Flash(unittest.TestCase):
    def test_one_black_frame_is_found_and_a_clean_film_has_none(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            flash, clean = Path(d) / "flash.mp4", Path(d) / "clean.mp4"
            clip(flash, True)
            clip(clean, False)
            found = qa.detect(flash, f"blackdetect=d={qa.FLASH}:pix_th=0.10", "black_start")
            none = qa.detect(clean, f"blackdetect=d={qa.FLASH}:pix_th=0.10", "black_start")
        self.assertEqual(len(found), 1, found)
        self.assertEqual(none, [])


if __name__ == "__main__":
    unittest.main()
