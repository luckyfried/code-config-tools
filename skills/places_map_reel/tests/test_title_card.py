"""The cinematic-letterbox closer's words stand inside the profile's safe width to the end of their push: the plan hands
the moves the board's safe area for its format, and the title card lays its title, its places and its handle in the
measure between the safe sides, narrowed by its push and pushed about the measure's middle, so nothing it says sits
under the app's own buttons.

    python3 -I -m unittest discover -s S/tests -p test_title_card.py
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
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "scripts" / "dev"))
import board_drive  # noqa: E402
import build_motion  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
NODE = shutil.which("node")
MOTION = KIT / "motion"
MODULES = build_motion.modules_of(KIT, KIT.parent / "video_studio") / "node_modules"
ESBUILD = MODULES / ".bin" / "esbuild"

STUB = """
import React from 'react';
export const Img = (props) => React.createElement('img', props);
export const continueRender = () => {};
export const delayRender = () => 0;
export const staticFile = (f) => f;
export const random = () => 0.5;
export const useCurrentFrame = () => 0;
export const useVideoConfig = () => ({width: 1080, height: 1920, fps: 30, durationInFrames: 1});
"""

# the closer at its last frame, inside the frame the film hands it, as static markup
RUN = """
import fs from 'node:fs';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {planOf, lookOf} from 'ROUTE/plan.ts';
import {CloserFrame, KIT, registerClosers} from 'ROUTE/closers.tsx';
import {closerOf} from 'MOVES/index.ts';
const board = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const plan = planOf(board);
const look = lookOf(plan);
registerClosers();
const safe = board.system.safe[board.format.name ?? 'reel'];
const frame = {window: plan.closer.window, top: safe.top, bottom: plan.H - safe.bottom};
const html = renderToStaticMarkup(React.createElement(CloserFrame.Provider, {value: frame},
  React.createElement(closerOf(KIT + 'title-card'), {look, local: 99, u: 1})));
process.stdout.write(JSON.stringify({safe: look.safe ?? null, W: plan.W, html}));
"""

num = lambda style, key: float(re.search(rf"(?:^|;){key}:(-?[\d.]+)(?:px)?(?:;|$)", style).group(1))


@unittest.skipUnless(NODE and ESBUILD.exists(), "node or the studio's node modules are absent")
class TheTitleCardStandsInsideTheSafeWidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        board = board_drive.frames(storyboard.plan(SOURCE, "reel", None, "cinematic-letterbox")["board"])
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        cls.addClassCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / "stub.mjs").write_text(STUB)
        (d / "run.mjs").write_text(RUN.replace("ROUTE/", str(MOTION / "studio" / "route") + "/")
                                   .replace("MOVES/", str(MOTION / "system" / "moves") + "/"))
        (d / "b.json").write_text(json.dumps(board))
        subprocess.run([str(ESBUILD), str(d / "run.mjs"), "--bundle", "--platform=node", "--format=cjs",
                        f"--outfile={d / 'run.cjs'}", f"--alias:remotion={d / 'stub.mjs'}", "--log-level=error"],
                       check=True, cwd=MOTION, env=dict(os.environ, NODE_PATH=str(MODULES)))
        r = subprocess.run([NODE, str(d / "run.cjs"), str(d / "b.json")], capture_output=True, text=True, check=True, timeout=120)
        cls.got, cls.board = json.loads(r.stdout), board

    def test_the_look_carries_the_formats_safe_area(self):
        self.assertEqual(self.got["safe"], self.board["system"]["safe"]["reel"])

    def test_every_word_stays_inside_the_safe_sides_to_the_end_of_the_push(self):
        W, safe, html = self.got["W"], self.board["system"]["safe"]["reel"], self.got["html"]
        styles = re.findall(r'style="([^"]*)"', html)
        pushed = next(s for s in styles if "transform:scale(" in s)
        k = float(re.search(r"transform:scale\(([\d.]+)\)", pushed).group(1))
        o = re.search(r"transform-origin:([\d.]+)(px|%)", pushed)
        ox = float(o.group(1)) * (W / 100 if o.group(2) == "%" else 1)
        words = [s for s in styles[styles.index(pushed) + 1:] if "font-size" in s and "left:" in s and "right:" in s]
        self.assertTrue(words)
        for s in words:
            size = num(s, "font-size")
            # a tracked line carries its last letter's spacing on the right, inside its box
            trail = size * float(re.search(r"letter-spacing:([\d.]+)em", s).group(1)) if "letter-spacing" in s else 0.0
            left, right = num(s, "left"), W - num(s, "right") - trail
            ends = ox + (left - ox) * k, ox + (right - ox) * k
            self.assertGreaterEqual(ends[0], safe["left"] - 0.5, s)
            self.assertLessEqual(ends[1], W - safe["right"] + 0.5, s)


if __name__ == "__main__":
    unittest.main()
