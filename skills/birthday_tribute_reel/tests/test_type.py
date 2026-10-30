"""Every letter the film sets fills as the font draws it: a glyph whose contour crosses itself (a B's two counters drawn
as one contour) is triangulated into the same area FreeType fills, so no counter of a B, a P or an 8 comes out solid,
in each face the three looks set their names, words and wishes in.

    python3 -I -m unittest discover -s S/tests -p test_type.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
MOTION = KIT / "motion"
LETTERS = "BPRe8gAWwo"
FACES = ["fonts/styles/scrapbook/CaveatBrush-Regular.ttf", "fonts/styles/scrapbook/Gloock-Regular.ttf",
         "fonts/styles/analog-home-movie/YoungSerif-Regular.ttf", "fonts/styles/analog-home-movie/VT323-Regular.ttf",
         "fonts/styles/editorial-quiet/InstrumentSerif-Regular.ttf", "fonts/styles/editorial-quiet/InstrumentSerif-Italic.ttf"]

AREAS = """
import {createRequire} from 'module';
const [motion, bundle, file, letters] = process.argv.slice(1);
const {glyphGeometry} = await import(bundle);
const font = createRequire(motion + '/')('opentype.js').loadSync(file);
font.file = file;
const out = {};
for (const ch of letters) {
  const geo = glyphGeometry(font, font.charToGlyph(ch), 0), pos = geo.getAttribute('position'), idx = geo.getIndex();
  let a = 0;
  for (let i = 0; i < idx.count; i += 3) {
    const [p, q, r] = [0, 1, 2].map((k) => [pos.getX(idx.getX(i + k)), pos.getY(idx.getX(i + k))]);
    a += Math.abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1])) / 2;
  }
  out[ch] = a;
}
console.log(JSON.stringify(out));
"""


def filled(face, ch, size=400):
    """The area FreeType fills for `ch`, in em squared."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("L", (2 * size, 2 * size), 0)
    ImageDraw.Draw(im).text((size // 2, size * 3 // 2), ch, font=ImageFont.truetype(str(KIT / face), size), fill=255,
                            anchor="ls")
    return sum(im.get_flattened_data()) / 255 / size / size


NODE = shutil.which("node")
ESBUILD = MOTION / "node_modules" / ".bin" / "esbuild"


@unittest.skipUnless(NODE and ESBUILD.exists(), "an authoring check of the motion source: needs node and motion/node_modules")
class Glyphs(unittest.TestCase):
    def test_each_letter_fills_the_area_the_font_draws(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            bundle = Path(d) / "type.mjs"
            subprocess.run([str(ESBUILD), str(MOTION / "system" / "three" / "type.ts"),
                            "--bundle", "--platform=node", "--format=esm", "--log-level=error", f"--outfile={bundle}"],
                           check=True, env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
            for face in FACES:
                p = subprocess.run([NODE, "--input-type=module", "-e", AREAS, str(MOTION), bundle.as_uri(),
                                    str(KIT / face), LETTERS], capture_output=True, text=True,
                                   env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
                self.assertEqual(p.returncode, 0, p.stderr[-800:])
                areas = json.loads(p.stdout)
                for ch in LETTERS:
                    with self.subTest(face=face, letter=ch):
                        self.assertAlmostEqual(areas[ch] / filled(face, ch), 1.0, delta=0.03)


if __name__ == "__main__":
    unittest.main()
