"""A spectacle's flight on the places map: the stop's beat carries `early`, the seconds of the camera's travel from the
stop before, and the shared move layer starts the flight that long before the stop's cut, which stays at the stop's
arrival; the flight lands on its photograph once the camera holds it, before its words come up, and the shutter the
sound lays lands with it; and every photograph's beat hands the moves the photograph's focus.

    python3 -I -m unittest discover -s S/tests -p test_flights.py
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
import board_drive  # noqa: E402
import look  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
NODE = shutil.which("node")
MOTION = KIT / "motion"
sys.path.insert(0, str(KIT / "scripts" / "dev"))
import build_motion  # noqa: E402

# the node modules the bundle resolves from (the kit's own, else the studio's beside it), as the tests' esbuild runs
MODULES = build_motion.modules_of(KIT, KIT.parent / "video_studio") / "node_modules"
ESBUILD = MODULES / ".bin" / "esbuild"

# the renderer's file helper stands in, so the plan and the moves run outside a composition
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

# for each flown beat: its cut and `early` as the timeline gives them, the beat the film is on and the beat whose early
# move draws at moments around the flight's start, and where the flight lands, in beats from the film's start
RUN = """
import fs from 'node:fs';
import {planOf, lookOf, timelineOf} from 'ROUTE/plan.ts';
import {beatAt, earlyAt} from 'MOVES/layer.tsx';
import {arrivalOf} from 'MOVES/arrival.tsx';
import {moveOf} from 'MOVES/index.ts';
const board = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const plan = planOf(board);
const look = lookOf(plan);
const line = timelineOf(board, plan);
const out = [];
line.beats.forEach((b, i) => {
  if (!b.early) return;
  const lead = (b.early * look.fps) / look.pulse;
  const from = line.cuts[i] - lead;
  const at = (t) => ({on: beatAt(line, look, t)?.beat.id ?? null, early: earlyAt(line, look, t)?.beat.id ?? null});
  const p = earlyAt(line, look, from + 1e-6);
  const a = arrivalOf(p, {'picture-tunnel': 1.1, 'exploded-layers': 1.15, 'tilted-wall': 1.2}[b.move]);
  out.push({id: b.id, move: b.move, frameTaking: Boolean(moveOf(b.move)?.early), cut: line.cuts[i], arrive: plan.cards[i].arrive,
    cutAt: plan.cards[i].cutAt, early: b.early, before: at(from - 0.05), during: at(from + 0.05),
    landed: from + (a.land * look.fps) / look.pulse, s: a.s});
});
const held = line.beats.map((b, i) => ({id: b.id, form: b.form, place: b.place ?? null, focus: b.focus ?? null,
  card: plan.cards[i] ? plan.cards[i].focus : null}));
process.stdout.write(JSON.stringify({pulse: plan.pulse, fps: plan.fps, flights: out, held}));
"""


def boards():
    """The reel's board in each of the kit's three looks, framed at its tempo."""
    return {st: board_drive.frames(storyboard.plan(SOURCE, "reel", None, st)["board"]) for st in look.TRIO}


class EarlyOnTheBeat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boards = boards()

    def test_a_flown_stops_beat_carries_the_travel_from_the_stop_before_in_seconds(self):
        flown = 0
        for st, b in self.boards.items():
            sec = 60 / b["bpm"]
            cards = b["route"]["cards"]
            for i, (c, beat) in enumerate(zip(cards, b["beats"])):
                self.assertNotIn("early", c, f"{st} {c['id']}: the card never moves its beat's start")
                if beat.get("move") in board_drive.FLIGHT:
                    flown += 1
                    self.assertAlmostEqual(beat["early"], cards[i - 1]["go"] * sec, places=3, msg=f"{st} {c['id']}")
                else:
                    self.assertNotIn("early", beat, f"{st} {c['id']}")
        self.assertGreater(flown, 0, "the fixture flies at least one stop")

    def test_the_whoosh_takes_the_frame_where_the_flight_does_and_the_shutter_lands_with_it(self):
        for st, b in self.boards.items():
            sec = 60 / b["bpm"]
            at, _ = board_drive.starts(b)
            fx = {x["id"]: x for x in board_drive.fx_board(b)["beats"]}
            for c, beat in zip(b["route"]["cards"], b["beats"]):
                if beat.get("move") not in board_drive.FLIGHT:
                    continue
                go = b["route"]["cards"][c["i"] - 1]["go"]
                self.assertAlmostEqual(fx[c["id"]]["start"], at[c["id"]] - go, places=2, msg=f"{st} {c['id']}")
                self.assertAlmostEqual(fx[c["id"]]["layers"][0]["at"]["arrive"] - fx[c["id"]]["start"],
                                       board_drive.FLIGHT[beat["move"]] / sec, places=3)


@unittest.skipUnless(NODE and ESBUILD.exists(), "node or the studio's node modules are absent")
class TheSharedLayerFliesIt(unittest.TestCase):
    """The board's beats through the kit's own plan and timeline into the shared moves, run in node."""

    @classmethod
    def setUpClass(cls):
        cls.boards = boards()
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        cls.addClassCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / "stub.mjs").write_text(STUB)
        (d / "run.mjs").write_text(RUN.replace("ROUTE/", str(MOTION / "studio" / "route") + "/")
                                   .replace("MOVES/", str(MOTION / "system" / "moves") + "/"))
        subprocess.run([str(ESBUILD), str(d / "run.mjs"), "--bundle", "--platform=node", "--format=cjs",
                        f"--outfile={d / 'run.cjs'}", f"--alias:remotion={d / 'stub.mjs'}", "--log-level=error"],
                       check=True, cwd=MOTION, env=dict(os.environ, NODE_PATH=str(MODULES)))
        cls.got = {}
        for st, b in cls.boards.items():
            (d / f"{st}.json").write_text(json.dumps(b))
            r = subprocess.run([NODE, str(d / "run.cjs"), str(d / f"{st}.json")], capture_output=True, text=True,
                               check=True, timeout=120)
            cls.got[st] = json.loads(r.stdout)

    def flights(self):
        out = [(st, b, f) for st, b in self.boards.items() for f in self.got[st]["flights"]]
        self.assertTrue(out, "the fixture flies at least one stop")
        return out

    def test_the_cut_stays_at_the_arrival_and_the_beat_carries_its_lead(self):
        for st, b, f in self.flights():
            beat = next(x for x in b["beats"] if x["id"] == f["id"])
            self.assertTrue(f["frameTaking"], f"{st} {f['id']}: {f['move']} takes the frame")
            self.assertAlmostEqual(f["cut"], f["arrive"], places=6, msg=f"{st} {f['id']}: the cut is the stop's arrival")
            self.assertEqual(f["early"], beat["early"])

    def test_the_flight_starts_as_the_camera_leaves_the_stop_before(self):
        for st, b, f in self.flights():
            cards = b["route"]["cards"]
            i = next(k for k, c in enumerate(cards) if c["id"] == f["id"])
            # the shared layer draws the flight from the camera leaving the stop before, over that stop's own beat
            self.assertAlmostEqual(f["cut"] - f["early"] * self.got[st]["fps"] / self.got[st]["pulse"],
                                   f["cut"] - cards[i - 1]["go"], places=2, msg=f"{st} {f['id']}")
            self.assertEqual(f["before"], {"on": cards[i - 1]["id"], "early": None}, f"{st} {f['id']}")
            self.assertEqual(f["during"], {"on": cards[i - 1]["id"], "early": f["id"]}, f"{st} {f['id']}")
            self.assertAlmostEqual(f["s"], 0, places=3)

    def test_the_flight_lands_where_the_camera_holds_it_before_its_words_and_with_its_shutter(self):
        for st, b, f in self.flights():
            sec = 60 / b["bpm"]
            fx = next(x for x in board_drive.fx_board(b)["beats"] if x["id"] == f["id"])
            self.assertGreaterEqual(f["landed"], f["arrive"] + board_drive.LAND, f"{st} {f['id']}: the camera has settled")
            self.assertLessEqual(f["landed"] + board_drive.HAND / sec, f["cutAt"] + 1e-3, f"{st} {f['id']}: before its words")
            self.assertAlmostEqual(f["landed"], fx["layers"][0]["at"]["arrive"], places=2, msg=f"{st} {f['id']}: the shutter")


    def test_each_photographs_beat_hands_the_moves_the_part_that_matters_as_fractions_of_where_it_lies(self):
        # a move that marks the photograph (doodle-draw-on) rings this point, the one the camera pushes toward
        seen = 0
        for st in self.boards:
            for h in self.got[st]["held"]:
                if h["form"] != "photo" or not h["place"]:
                    continue
                seen += 1
                (x, y, w, ht), (u, v) = h["place"], h["focus"]
                with self.subTest(look=st, beat=h["id"]):
                    self.assertAlmostEqual(x + u * w, h["card"][0], places=3)
                    self.assertAlmostEqual(y + v * ht, h["card"][1], places=3)
                    self.assertTrue(0 <= u <= 1 and 0 <= v <= 1, h)
        self.assertTrue(seen)


if __name__ == "__main__":
    unittest.main()
