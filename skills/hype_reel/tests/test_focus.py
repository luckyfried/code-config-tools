"""A photograph's beat hands the shared moves the photograph's focus as fractions of where it lies, so a move that marks
the photograph (doodle-draw-on) rings the point the camera centres on, never the middle of the print. The picture is
drive.py's own, run through the film's timeline (motion/studio/film/time.ts) in node.

    python3 -I -m unittest discover -s S/tests -p test_focus.py
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
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "scripts" / "dev"))
import build_motion  # noqa: E402
import drive  # noqa: E402

NODE = shutil.which("node")
MOTION = KIT / "motion"
MODULES = build_motion.modules_of(KIT, KIT.parent / "video_studio") / "node_modules"
ESBUILD = MODULES / ".bin" / "esbuild"

# the renderer's helpers the film's system imports stand in, so the timeline runs outside a composition
STUB = """
export const staticFile = (f) => f;
export const continueRender = () => {};
export const delayRender = () => 0;
"""

RUN = """
import fs from 'node:fs';
import {timelineOf} from 'FILM/time.ts';
const placed = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
process.stdout.write(JSON.stringify(timelineOf(placed).beats.map((b) => ({id: b.id, place: b.place, focus: b.focus}))));
"""


@unittest.skipUnless(NODE and ESBUILD.exists(), "node or the studio's node modules are absent")
class Focus(unittest.TestCase):
    def test_the_beat_carries_the_photographs_focus_as_fractions_of_where_it_lies(self):
        photos = {"wide": {"file": "photos/a.jpg", "aspect": 0.75, "subject": [0.62, 0.2, 0.86, 0.5]},
                  "tall": {"file": "photos/b.jpg", "aspect": 1.5, "focus": [0.3, 0.7]}}
        box = [0, 300, 1080, 980]
        beats = [{"id": k, "form": "photo", "layout": "card", "move": "doodle-draw-on", "picture": drive.picture_of(p, box),
                  "lines": [], "words": "", "label": "", "peak": False} for k, p in photos.items()]
        placed = [{"beat": b, "i": i, "from": 30 * i, "frames": 30, "at": 4 * i, "end": 4 * i + 4, "pulse": 7.5}
                  for i, b in enumerate(beats)]
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            d = Path(d)
            (d / "stub.mjs").write_text(STUB)
            (d / "run.mjs").write_text(RUN.replace("FILM/", str(MOTION / "studio" / "film") + "/"))
            (d / "placed.json").write_text(json.dumps(placed))
            subprocess.run([str(ESBUILD), str(d / "run.mjs"), "--bundle", "--platform=node", "--format=cjs",
                            f"--outfile={d / 'run.cjs'}", f"--alias:remotion={d / 'stub.mjs'}", "--log-level=error"],
                           check=True, cwd=MOTION, env=dict(os.environ, NODE_PATH=str(MODULES)))
            got = json.loads(subprocess.run([NODE, str(d / "run.cjs"), str(d / "placed.json")], capture_output=True,
                                            text=True, check=True, timeout=120).stdout)
        for b, p in zip(got, photos.values()):
            with self.subTest(beat=b["id"]):
                fx, fy = drive.focus_of(p)
                self.assertAlmostEqual(b["focus"][0], fx, delta=0.002)
                self.assertAlmostEqual(b["focus"][1], fy, delta=0.002)


if __name__ == "__main__":
    unittest.main()
