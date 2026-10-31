"""The film hands the shared moves the shot as it draws it, run in node on real boards: a beat's print tilt (none on a
photograph with no print), so a landing move ends on the print where and how the shot hangs it; on the grid a move
lands on, every other tile as the shot draws it, so the move lands them in their cells; the scrapbook keepsake stands
below the shared cover's own column; the closer keeps the shared slow push from the stop to the last frame, the
keepsake with it, both growing about the safe area's middle; a photograph's beat hands the moves the part of the
photograph that matters; and the film's words are drawn at the optical size the board measures them at.

    python3 -I -m unittest discover -s S/tests
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_story import board

KIT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
ESBUILD = KIT / "motion" / "node_modules" / ".bin" / "esbuild"
MOTION = KIT / "motion"

# The renderer and its 3D canvas stand in as plain elements, so the film's parts run outside a composition.
STUB = """
import React from 'react';
export const Img = (props) => React.createElement('img', props);
export const AbsoluteFill = (props) => React.createElement('div', props);
export const continueRender = () => {};
export const delayRender = () => 0;
export const staticFile = (f) => f;
export const random = () => 0.5;
export const useCurrentFrame = () => globalThis.FRAME ?? 0;
export const useVideoConfig = () => ({width: 1080, height: 1920, fps: 30, durationInFrames: 1});
export const ThreeCanvas = () => null;
export const Bloom = () => null;
export const EffectComposer = () => null;
"""

RUN = """
import React from 'react';
import fs from 'node:fs';
import {renderToStaticMarkup} from 'react-dom/server';
import {Frame, Keepsake, lineOf, Words} from 'MOTION/studio/Film.tsx';
import {printOf} from 'MOTION/system/moves/arrival.tsx';
import {coverOf} from 'MOTION/system/moves/closer/book-cover.tsx';
import {SystemProvider} from 'MOTION/system/system.tsx';

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const [name, c] of Object.entries(spec)) {
  if (c.do === 'line') {
    const beats = lineOf(c.board, c.board.beats.map((_, i) => i * 8), c.board.beats.length * 8).beats;
    out[name] = beats.map((b) => ({...b, print: b.photo ? printOf(c.look, b) : null}));
  } else if (c.do === 'keepsake') {
    out[name] = {html: renderToStaticMarkup(React.createElement(Keepsake, {look: c.look, u: 1})), foot: coverOf(c.look).foot};
  } else if (c.do === 'frame') {
    // the stage draws its grain on a canvas once; a blank one stands in, and text measures by its length
    const pad = {createImageData: (w, h) => ({data: new Uint8ClampedArray(w * h * 4)}), putImageData: () => {},
      measureText: (s) => ({width: s.length * 10})};
    globalThis.document ??= {createElement: () => ({getContext: () => pad, toDataURL: () => 'data:,'})};
    globalThis.FRAME = c.frame;
    out[name] = renderToStaticMarkup(React.createElement(SystemProvider, {value: {system: c.board.system}},
      React.createElement(Frame, {board: c.board, clips: []})));
  } else if (c.do === 'words') {
    out[name] = renderToStaticMarkup(React.createElement(Words, {board: c.board, beat: c.beat, local: 3, length: 8, only: 'Words'}));
  }
}
process.stdout.write(JSON.stringify(out));
"""


def look(b, tilt=7.0, rim=33.0, tape=2):
    """The film's look as the moves read it, with a card tilt, rim and tape no shot of these boards draws a print with."""
    W, H = b["format"]["width"], b["format"]["height"]
    return {"W": W, "H": H, "fps": 30, "pulse": 15, "colors": {"accent": "#c03a2b", "accent2": "#2b6cc0", "ink": "#111111",
            "paper": "#ffffff"}, "display": "Gloock", "text": "Caveat Brush", "italic": False,
            "title": "my best nine", "handle": "@cornerloaf", "signoff": "see you in 2027",
            "tone": {"ground": "#f4f1ea", "dip": None, "matte": "#000000", "light": "#ffffff", "pen": "#111111",
                     "rim": "#fbfaf6", "tape": "#e8d9a8"},
            "grid": {"m": 60, "cols": [60, 380, 700, 1020], "rows": [60, 1860], "rules": "none"},
            "print": {"box": [0, 0, W, H], "rim": rim, "tilt": tilt, "tape": tape}, "finished": True}


def near(a, b, tol=0.5):
    return all(abs(x - y) <= tol for x, y in zip(a, b)) and len(a) == len(b)


@unittest.skipUnless(NODE and ESBUILD.exists(), "node or the engine (motion/node_modules) is absent")
class FilmMoves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        stub = cls.tmp / "stub.mjs"
        stub.write_text(STUB)
        entry = cls.tmp / "run.mjs"
        entry.write_text(RUN.replace("MOTION", str(MOTION)))
        cls.js = cls.tmp / "run.cjs"
        aliases = [f"--alias:{m}={stub}" for m in ("remotion", "@remotion/three", "@react-three/postprocessing")]
        subprocess.run([str(ESBUILD), str(entry), "--bundle", "--platform=node", "--format=cjs", "--jsx=automatic", f"--outfile={cls.js}", *aliases,
                        "--log-level=error"], check=True, cwd=MOTION,
                       env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1", NODE_PATH=str(MOTION / "node_modules")))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_spec(self, spec):
        f = self.tmp / "spec.json"
        f.write_text(json.dumps(spec))
        out = subprocess.run([NODE, str(self.js), str(f)], capture_output=True, text=True, timeout=120,
                             env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def test_a_landing_move_lands_on_the_print_at_the_shots_own_tilt_and_none_on_a_bare_photograph(self):
        b = board(style="scrapbook")
        beats = self.run_spec({"line": {"do": "line", "board": b, "look": look(b)}})["line"]
        seen = set()
        for on, x in zip(beats, b["beats"]):
            if x["form"] != "photo":
                continue
            layer = next(L for L in x["layers"] if L["kind"] == "Photo")
            pr = layer.get("print") or {}
            want = pr.get("tilt", 0)
            seen.add(want)
            with self.subTest(beat=x["id"]):
                self.assertEqual(on.get("tilt"), want, "the print hangs at the shot's tilt, never the card's")
                self.assertEqual(on["print"]["tilt"], want)
                self.assertEqual((on.get("rim"), on.get("tape")), (pr.get("rim", 0), pr.get("tape", 0)),
                                 "the print's rim and tape are the shot's, none on a photograph the board prints none on")
                self.assertEqual(on["print"]["rim"], pr.get("rim", 0))
                bx, by, bw, bh = layer["box"]
                self.assertTrue(near(on["print"]["rect"], [max(0, bx), max(0, by), min(b["format"]["width"], bx + bw) - max(0, bx),
                                                           min(b["format"]["height"], by + bh) - max(0, by)]),
                                "the print's picture is the shot's box")
        self.assertEqual(seen, {0, -3}, "the board has prints hung at the card's tilt and photographs with no print")

    def test_a_move_onto_the_grid_lands_every_other_tile_in_its_own_cell(self):
        for style in ("swiss-grid", "scrapbook"):
            b = board(style=style)
            grid = next(x for x in b["beats"] if x["id"] == "grid")
            self.assertIn("landing", grid, f"{style}: the wall's move flies a photograph onto the grid")
            on = self.run_spec({"line": {"do": "line", "board": b, "look": look(b)}})["line"][b["beats"].index(grid)]
            tiles = [L for L in grid["layers"] if L["kind"] == "Slice"]
            landed = tiles[grid["landing"]]
            with self.subTest(style=style):
                self.assertEqual(on["photo"], landed["photo"]["file"])
                self.assertEqual((on["tilt"], on["rim"], on["tape"]), (0, 0, 0), "a tile is a bare print: no tilt, rim or tape")
                self.assertEqual((on["print"]["tilt"], on["print"]["rim"]), (0, 0))
                others = [L for L in tiles if L is not landed]
                self.assertEqual([c["box"] for c in on.get("cells") or []], [L["box"] for L in others])
                self.assertEqual([c["photo"] for c in on["cells"]], [L["photo"]["file"] for L in others])
                for c in on["cells"]:
                    x, y, w, h = c["box"]
                    px, py, pw, ph = c["place"]
                    self.assertTrue(px <= x + 0.5 and py <= y + 0.5 and px + pw >= x + w - 0.5 and py + ph >= y + h - 0.5,
                                    "each tile's photograph covers its cell, as the shot draws it")
                self.assertEqual({(L["at"], L["beats"]) for L in tiles}, {(0, 0)}, "the whole wall stands under the move")

    def test_a_grid_no_move_lands_on_carries_no_cells(self):
        b = board(style="cinematic-letterbox")
        grid = next(x for x in b["beats"] if x["id"] == "grid")
        self.assertNotIn("landing", grid)
        on = self.run_spec({"line": {"do": "line", "board": b, "look": look(b)}})["line"][b["beats"].index(grid)]
        self.assertNotIn("cells", on)

    def test_the_keepsake_stands_below_the_shared_covers_column(self):
        b = board(style="scrapbook")
        got = self.run_spec({"k": {"do": "keepsake", "look": dict(look(b), photo="top.jpg")}})["k"]
        top = float(re.search(r"top:([\d.]+)px", got["html"]).group(1))
        self.assertAlmostEqual(top, got["foot"] + 56 * b["format"]["width"] / 1080, delta=0.01)

    def test_the_closer_keeps_its_slow_push_from_the_stop_to_the_last_frame_with_the_keepsake_on_it(self):
        b = board(style="scrapbook")
        end = sum(x["frames"] for x in b["beats"])
        got = self.run_spec({f"f{n}": {"do": "frame", "board": b, "frame": n} for n in (end - 31, end - 1)})
        scales = {}
        for n, html in got.items():
            found = [float(v) for v in re.findall(r"transform:scale\(([\d.]+)\)", html)]
            self.assertEqual(len(found), 2, f"{n}: the cover and the keepsake each take the push")
            self.assertEqual(found[0], found[1], "the keepsake moves with the cover it is pasted on")
            scales[n] = found[0]
        self.assertGreater(scales["f%d" % (end - 1)], scales["f%d" % (end - 31)], "the last frame is never the frame before it")
        self.assertGreater(scales["f%d" % (end - 31)], 1.0)

    def test_the_closer_grows_about_the_safe_areas_middle_so_its_words_end_inside_the_safe_area(self):
        b = board(style="scrapbook")
        end = sum(x["frames"] for x in b["beats"])
        sf = b["system"]["safe"][b["format"]["name"]]
        W, H = b["format"]["width"], b["format"]["height"]
        mid = ((sf["left"] + W - sf["right"]) / 2, (sf["top"] + H - sf["bottom"]) / 2)
        html = self.run_spec({"f": {"do": "frame", "board": b, "frame": end - 1}})["f"]
        origins = [(float(x), float(y)) for x, y in re.findall(r"transform-origin:([\d.]+)px ([\d.]+)px", html)]
        self.assertEqual(len(origins), 2, "the cover and the keepsake each grow about one point")
        for o in origins:
            self.assertTrue(near(o, mid, 0.01), (o, mid))

    def test_a_photographs_beat_hands_the_doodle_the_part_of_the_photograph_that_matters(self):
        b = board(style="scrapbook")
        beats = self.run_spec({"line": {"do": "line", "board": b, "look": look(b)}})["line"]
        seen = 0
        for on, x in zip(beats, b["beats"]):
            layer = next((L for L in x["layers"] if L["kind"] == "Photo"), None)
            if x["form"] != "photo" or not layer or "focus" not in layer:
                continue
            seen += 1
            self.assertEqual(on["focus"], layer["focus"], x["id"])
        self.assertTrue(seen)

    def test_the_films_words_are_drawn_with_optical_sizing_off(self):
        b = board(style="kinetic-type")
        i = next(i for i, x in enumerate(b["beats"]) if any(L["kind"] == "Words" for L in x["layers"]))
        html = self.run_spec({"w": {"do": "words", "board": b, "beat": i}})["w"]
        texts = re.findall(r"<text[^>]*>", html)
        self.assertTrue(texts)
        self.assertFalse([t for t in texts if "font-optical-sizing:none" not in t])


if __name__ == "__main__":
    unittest.main()


class SafeArea(unittest.TestCase):
    def test_the_look_hands_the_moves_the_formats_safe_area(self):
        """The shared moves lay their words out from the look's safe area (polaroid-drop's foot, among them); the film's
        look carries the board's own safe area for its format."""
        src = (MOTION / "studio" / "Film.tsx").read_text()
        look = src[src.index("const lookOf"):src.index("/** The frame of a generated clip")]
        self.assertIn("safe: board.format.name ? s.safe[board.format.name] : undefined", look)
