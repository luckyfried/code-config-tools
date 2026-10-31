"""The film's finish: type that fades casts no shadow once it is half gone; the closer keeps the shared slow push from
the stop to the last frame, and the frozen row reads the whole film, its ending included; and a move that draws an
accent on a corner of the print's top finds that corner bare of tape.

    python3 -I -m unittest discover -s S/tests -p test_finish.py
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

KIT = Path(__file__).resolve().parents[1]
MOTION = KIT / "motion"
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import qa  # noqa: E402


class FadingType(unittest.TestCase):
    def test_fading_type_casts_no_shadow_once_it_is_half_gone(self):
        src = (MOTION / "system/three/Type3D.tsx").read_text()
        self.assertIn("castShadow={castShadow && opacity > SHADOW_FROM}", src)
        self.assertIn("const SHADOW_FROM = 0.5;", src)
        self.assertNotIn("castShadow={castShadow}", src)


class CloserPush(unittest.TestCase):
    def test_the_film_hands_the_move_layer_its_time_past_the_stop(self):
        src = (MOTION / "studio/drive/DriveFilm.tsx").read_text()
        calls = re.findall(r"<MoveLayer\b[^>]*?>", src, re.S)
        self.assertEqual(len(calls), 1, calls)
        self.assertIn("now={stepped / plan.pulse}", calls[0])
        self.assertIn("const stepped = Math.floor(now / step) * step;", src)
        self.assertIn("const frame = Math.min(stepped, still);", src)

    def test_a_frozen_ending_is_a_frozen_stretch(self):
        """Two seconds of a slow push, then a second and a half held on one frame: the held ending is read."""
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            held, pushed = Path(d) / "held.mp4", Path(d) / "pushed.mp4"
            for out, x in ((held, "200+20*min(t\\,2)"), (pushed, "200+20*t")):
                subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                                "-f", "lavfi", "-i", "color=c=0x303030:s=540x960:r=30:d=3.5",
                                "-f", "lavfi", "-i", "color=c=0xf0e8d8:s=200x200:r=30:d=3.5",
                                "-filter_complex", f"[0][1]overlay=x='{x}':y=380,format=yuv420p",
                                "-c:v", "libx264", "-qp", "0", str(out)], check=True)
            self.assertEqual(len(qa.frozen_in(held)), 1)
            self.assertEqual(qa.frozen_in(pushed), [])

    def test_the_frozen_row_spares_no_stretch_after_the_stop(self):
        src = (KIT / "scripts/qa.py").read_text()
        self.assertIn("frozen = frozen_in(film, run)", src)
        self.assertNotIn("< held - 0.04", src)


TAPE = """
const [bundle] = process.argv.slice(1);
const {bareCorner, hash} = await import(bundle);
const out = [];
for (const move of ['doodle-draw-on', 'sticker-pop', 'page-drift']) {
  for (let i = 0; i < 40; i++) {
    const steps = Array.from({length: 40}, (_, j) => ({id: 'b' + j, move: j === i ? move : 'page-drift'}));
    out.push({move, seed: i + 1, hash: hash(i + 1), bare: bareCorner({steps}, {key: 'b' + i}) ?? null});
  }
}
console.log(JSON.stringify(out));
"""

NODE = shutil.which("node")
ESBUILD = MOTION / "node_modules" / ".bin" / "esbuild"


@unittest.skipUnless(NODE and ESBUILD.exists(), "an authoring check of the motion source: needs node and motion/node_modules")
class AccentCorner(unittest.TestCase):
    def test_the_accent_marks_the_corner_the_card_leaves_bare(self):
        moves = MOTION / "system/moves/move"
        # the corner the sticker draws on, as the shared move picks it; the doodle rings the photograph's focus and
        # marks no corner, so every strip of tape stays on under it
        self.assertIn("const right = hash(seed) > 0.5;", (moves / "sticker-pop.tsx").read_text())
        self.assertNotIn("hash(seed)", (moves / "doodle-draw-on.tsx").read_text())
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            entry, bundle = Path(d) / "entry.ts", Path(d) / "card.mjs"
            entry.write_text(f"export {{bareCorner}} from '{MOTION}/studio/drive/card';\n"
                             f"export {{hash}} from '{MOTION}/system/three/motion';\n")
            subprocess.run([str(ESBUILD), str(entry), "--bundle", "--format=esm", "--platform=node", "--log-level=error",
                            f"--outfile={bundle}"], check=True, cwd=MOTION)
            rows = json.loads(subprocess.run([NODE, "--input-type=module", "-e", TAPE, str(bundle)], check=True,
                                             capture_output=True, text=True).stdout)
        for r in rows:
            want = {"sticker-pop": 1 if r["hash"] > 0.5 else 0}.get(r["move"])
            self.assertEqual(r["bare"], want, r)
        self.assertEqual({r["bare"] for r in rows if r["move"] == "sticker-pop"}, {0, 1})


if __name__ == "__main__":
    unittest.main()
