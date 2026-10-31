"""Every flight in a film is its own, and its cut is seen: the film's flights take the card's spectacles in turn, so two
flights are never one move; a look with letterbox bars closes them over the switch where its flight takes the frame and
opens them on the flight, so the cut plays centred on that switch and never on the arrival the flight covers; a stop the person
wrote nothing about takes the card's move made for a wordless beat; and the review page counts the photographs the film
shows and says where its music came from in plain words.

    python3 -I -m unittest discover -s S/tests -p test_flight_cuts.py
"""
import copy
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive  # noqa: E402
import look  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
CINEMA = "cinematic-letterbox"
NODE = shutil.which("node")
MOTION = KIT / "motion"
sys.path.insert(0, str(KIT / "scripts" / "dev"))
import build_motion  # noqa: E402

# the node modules the bundle resolves from (the kit's own, else the studio's beside it), as the tests' esbuild runs
MODULES = build_motion.modules_of(KIT, KIT.parent / "video_studio") / "node_modules"
ESBUILD = MODULES / ".bin" / "esbuild"


def standing(src):
    """The trip with every photograph standing (taller than wide): every stop tags its photograph a portrait."""
    s = copy.deepcopy(src)
    for p in s["photos"]:
        if p["w"] > p["h"]:
            p["w"], p["h"] = p["h"], p["w"]
            p["aspect"] = round(p["h"] / p["w"], 4)
    return s


def board(src=SOURCE, style=CINEMA):
    return board_drive.frames(storyboard.plan(src, "reel", None, style)["board"])


class EveryFlightIsItsOwn(unittest.TestCase):
    def test_two_flights_in_a_row_never_take_one_spectacle_while_the_card_has_another(self):
        flew = 0
        for src in (SOURCE, standing(SOURCE)):
            for st in look.TRIO:
                card = look.card(st)
                kinds = {o["id"] for o in card["moves"]} & set(board_drive.FLIGHT)
                flights = [b["move"] for b in board(src, st)["beats"] if b.get("move") in board_drive.FLIGHT]
                flew += len(flights)
                if len(kinds) < 2:
                    continue
                for a, b in zip(flights, flights[1:]):
                    self.assertNotEqual(a, b, f"{st}: {flights}")
        self.assertGreater(flew, 0, "the fixture flies at least one stop")


class TheFlightsCutIsSeen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boards = {"as shot": board(SOURCE), "standing": board(standing(SOURCE))}

    def test_a_flown_stop_closes_the_bars_over_its_flight_and_only_flights_and_the_closer_do(self):
        for name, b in self.boards.items():
            flown = 0
            for beat in b["beats"]:
                if beat["id"] == "hook":
                    continue
                if beat.get("move") in board_drive.FLIGHT:
                    flown += 1
                    self.assertEqual(beat["transition"], board_drive.FLIGHT_CUT, f"{name} {beat['id']}")
                elif beat["id"] != "closer":
                    self.assertNotEqual(beat["transition"], board_drive.FLIGHT_CUT, f"{name} {beat['id']}")
            self.assertGreater(flown, 0, name)
            self.assertEqual(b["beats"][-1]["transition"], board_drive.FLIGHT_CUT, f"{name}: the closer closes the bars")

    def test_a_look_without_bars_keeps_its_own_cuts_into_its_flights(self):
        for st in look.TRIO:
            if any(o["id"] == board_drive.FLIGHT_CUT for o in look.card(st)["transitions"]):
                continue
            own = {o["id"] for o in look.card(st)["transitions"]}
            for beat in board(SOURCE, st)["beats"][1:]:
                self.assertIn(beat["transition"], own, f"{st} {beat['id']}")


class AWordlessStop(unittest.TestCase):
    def test_takes_the_cards_move_for_a_wordless_beat_unless_the_beat_before_took_it(self):
        took = 0
        for src in (SOURCE, standing(SOURCE)):
            b = board(src)
            quiet = {o["id"] for o in look.card(CINEMA)["moves"] if "wordless" in o["fits"]} - look.COVERS - set(board_drive.FLIGHT)
            self.assertTrue(quiet, "the card has a move made for a wordless beat")
            prev = None
            for c, beat in zip(b["route"]["cards"], b["beats"]):
                if c["i"] and not c.get("said") and beat["move"] not in board_drive.FLIGHT:
                    if prev in quiet:
                        self.assertNotEqual(beat["move"], prev, c["id"])
                    else:
                        self.assertIn(beat["move"], quiet, c["id"])
                        took += 1
                prev = beat["move"]
        self.assertGreater(took, 0, "the fixture has a wordless stop")


class InADir(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)


class TheReviewPage(InADir):
    def test_counts_the_photographs_the_film_shows_never_the_library(self):
        import deliver
        b = board(SOURCE)
        Path(f"storyboards/{CINEMA}").mkdir(parents=True)
        Path(f"storyboards/{CINEMA}/board-reel.json").write_text(json.dumps(b))
        shown = {c["file"] for c in b["route"]["cards"]}
        library = [{"file": f"photos/x-{k}.jpg"} for k in range(len(shown) + 20)]
        pl = {"places": [{"id": "lisbon"}, {"id": "porto"}]}
        words = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", deliver.made_html(pl, library, {}, {}, CINEMA, {}))).split())
        self.assertIn(f"one for each stop ({len(shown)} in all)", words)

    def test_says_where_the_music_came_from_without_a_script_or_a_code_name(self):
        import music
        Path("winner.json").write_text(json.dumps({"board": CINEMA}))
        self.assertEqual(music.cmd_make(types.SimpleNamespace(bpm=None, seconds=3)), 0)
        origin = json.loads(Path("music.json").read_text())["origin"]
        self.assertNotIn(".py", origin)
        for rid in json.loads((KIT / "music" / "recipes.json").read_text())["recipes"]:
            self.assertIsNone(re.search(rf"\b{re.escape(rid)}\b", origin), origin)
        self.assertIn("chosen by the look", origin)


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

# for each flown beat: where its flight takes the frame, the cut the kit draws a little before, at, and after that
# switch and at the arrival, and the cut the shared layer draws at the same moments
RUN = """
import fs from 'node:fs';
import {planOf, lookOf, timelineOf, sharedOf, flightCutAt, wordsGoneBy} from 'ROUTE/plan.ts';
import {carry} from 'ROUTE/closers.tsx';
import {cutAt} from 'MOVES/layer.tsx';
const board = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const plan = planOf(board);
const look = lookOf(plan);
const full = timelineOf(board, plan);
const line = sharedOf(full);
const out = [];
const gone = wordsGoneBy(full, look);
full.beats.forEach((b, i) => {
  if (!b.early) return;
  const go = full.cuts[i] - (b.early * look.fps) / look.pulse;
  const kit = (t) => { const f = flightCutAt(full, look, t); return f ? {id: f.into.id, u: f.u} : null; };
  const shared = (t) => { const c = cutAt(line, t); return c ? c.into.id : null; };
  out.push({id: b.id, transition: b.transition, go, arrive: full.cuts[i], atGo: kit(go), before: kit(go - 0.2), after: kit(go + 0.2),
    atArrive: kit(full.cuts[i] + 0.01), sharedAtGo: shared(go), sharedAtArrive: shared(full.cuts[i] + 0.01), held: line.beats[i].transition,
    gone: gone[i - 1], atGone: kit(gone[i - 1]), leaves: plan.cards[i - 1].goAt});
});
const rows = carry(['Lisbon · Porto · Coimbra · Aveiro · Évora · Seville', '· Córdoba · Granada · Faro', '· Oaxaca · Madrid']);
process.stdout.write(JSON.stringify({flights: out, rows}));
"""


@unittest.skipUnless(NODE and ESBUILD.exists(), "node or the studio's node modules are absent")
class TheKitDrawsTheFlightsCutAtItsSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
        for name, src in (("as shot", SOURCE), ("standing", standing(SOURCE))):
            (d / "b.json").write_text(json.dumps(board(src)))
            r = subprocess.run([NODE, str(d / "run.cjs"), str(d / "b.json")], capture_output=True, text=True, check=True, timeout=120)
            got = json.loads(r.stdout)
            cls.got[name], cls.rows = got["flights"], got["rows"]

    def test_the_cut_plays_centred_on_the_switch_and_never_on_the_arrival(self):
        n = 0
        for name, flights in self.got.items():
            for f in flights:
                n += 1
                self.assertEqual(f["transition"], board_drive.FLIGHT_CUT, f"{name} {f['id']}")
                self.assertEqual(f["atGo"]["id"], f["id"], f"{name} {f['id']}")
                self.assertAlmostEqual(f["atGo"]["u"], 0.5, places=6, msg=f"{name} {f['id']}: centred on the switch")
                self.assertLess(f["before"]["u"], 0.5)
                self.assertGreater(f["after"]["u"], 0.5)
                # by the arrival, which the flight covers, the cut is past its middle or over
                self.assertTrue(f["atArrive"] is None or f["atArrive"]["u"] > 0.5, f"{name} {f['id']}: {f['atArrive']}")

    def test_the_shared_layer_draws_no_second_cut_into_a_flight(self):
        for name, flights in self.got.items():
            for f in flights:
                self.assertIsNone(f["held"], f"{name} {f['id']}")
                self.assertNotEqual(f["sharedAtGo"], f["id"])
                self.assertNotEqual(f["sharedAtArrive"], f["id"])

    def test_a_stops_words_are_gone_before_the_cut_into_the_flight_closes_over_them(self):
        n = 0
        for name, flights in self.got.items():
            for f in flights:
                n += 1
                # gone a quarter of the way into the cut's window, while the bars stand clear of the line's band
                self.assertAlmostEqual(f["atGone"]["u"], 0.25, places=6, msg=f"{name} {f['id']}")
                self.assertLess(f["gone"], f["leaves"], f"{name} {f['id']}")
        self.assertGreater(n, 0)

    def test_the_closers_rows_each_open_on_a_place(self):
        self.assertEqual(self.rows, ["Lisbon · Porto · Coimbra · Aveiro · Évora · Seville ·", "Córdoba · Granada · Faro ·",
                                     "Oaxaca · Madrid"])


if __name__ == "__main__":
    unittest.main()
