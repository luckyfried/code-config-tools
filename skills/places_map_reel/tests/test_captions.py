"""Captions a phone reads (scripts/captions.py): over a bright photograph the scrim under light words deepens until they
read, and a label that does not read in its own color stands in the line's; the storyboard check names a caption no
remedy reaches and a closer line set under the least size a phone shows legibly, and the closer the studio draws sets
every word at that size or larger; a board cut to the music's tempo holds every stop's words whole for their reading
with its headline in within a second of its beat, and the check names a stop whose words do not; the words of a
stop before a flight leave a quarter of the way into whichever cut takes the flight, and the sheet rests that stop
before they go.

    python3 -I -m unittest discover -s S/tests -p test_captions.py
"""
import copy
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
import captions  # noqa: E402
import legible  # noqa: E402
import look  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
# the look whose light words stand over the photograph under a scrim, its label in the card's accent
LIGHT = "cinematic-letterbox"
# the look whose words stand on the card's ground beside the photograph
GROUND = "swiss-grid"
# a gray that reads at 4.5:1 over a white photograph under no scrim the remedy may lay
MID = "#7a7a7a"
# a tempo the fixture's film is cut to, as a snap to music at twice 70 bpm cuts it
MUSIC = 140
NODE = shutil.which("node")
MOTION = KIT / "motion"
MODULES = build_motion.modules_of(KIT, KIT.parent / "video_studio") / "node_modules"
ESBUILD = MODULES / ".bin" / "esbuild"


def layout(board, c):
    """The card's layout as the check reads it back from the board."""
    f = board["format"]
    return board_drive.layout_of(board["system"]["photo"], {"w": c["photo"][2], "h": c["photo"][3]}, f["width"], f["height"])


def short(board):
    return min(board["format"]["width"], board["format"]["height"])


def over_photo(card):
    """The groups of a card's words that stand on its photograph."""
    return [g for g in captions.groups(card) if any(captions.on_photo(card, ln) for ln in g)]


class InARun(unittest.TestCase):
    """Each test in a run folder of its own, whose photographs (public/) it paints one gray so every caption over one
    is measured against known pixels."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)

    def photos(self, gray):
        from PIL import Image
        for ph in SOURCE["photos"]:
            p = Path("public") / ph["file"]
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.new("L", (max(1, ph["w"] // 4), max(1, ph["h"] // 4)), gray).save(p, "PNG")

    def plan(self, style, fmt="reel", bpm=None):
        return storyboard.plan(SOURCE, fmt, bpm, style)


class TheRemedy(InARun):
    def test_a_bright_photograph_deepens_the_scrim_under_light_words_until_they_read(self):
        self.photos(0)
        dark = self.plan(LIGHT)["board"]
        self.photos(255)
        bright = self.plan(LIGHT)["board"]
        seen = 0
        for d, b in zip(dark["route"]["cards"], bright["route"]["cards"]):
            if not over_photo(b):
                continue
            seen += 1
            # over a dark photograph the scrim stays at the least the studio lays; over a white one it deepens
            self.assertEqual(d.get("scrim", captions.SCRIM_DEPTH), captions.SCRIM_DEPTH, d["id"])
            self.assertGreater(b.get("scrim", captions.SCRIM_DEPTH), captions.SCRIM_DEPTH, b["id"])
            self.assertLessEqual(b["scrim"], legible.SCRIM_MOST, b["id"])
        self.assertGreater(seen, 0, "the look sets words over its photographs")
        self.assertEqual([x for x in captions.findings(bright) if "over the photograph" in x], [])

    def test_a_label_that_does_not_read_in_its_own_color_stands_in_the_lines(self):
        self.photos(0)
        dark = self.plan(LIGHT)["board"]
        self.photos(255)
        bright = self.plan(LIGHT)["board"]
        colors, switched = bright["route"]["colors"], 0
        for d, b in zip(dark["route"]["cards"], bright["route"]["cards"]):
            lay = layout(bright, b)
            own, line = lay["label"]["color"], lay["line"]["color"]
            for dg, bg in zip(captions.groups(d), captions.groups(b)):
                if bg[0].get("name") != "label" or not over_photo({**b, "lines": bg}):
                    continue
                self.assertEqual({ln["color"] for ln in dg}, {own}, d["id"])
                self.assertEqual({ln["color"] for ln in bg}, {line}, b["id"])
                # in its own color the label measures under what its size needs over the white photograph
                r, want, _ = captions.measure(b, bg, captions.hexof(colors, own), b["scrim"], captions.veil_of(b["lines"], colors),
                                              captions.hexof(colors, lay["ground"]), short(bright))
                self.assertLess(r, want, b["id"])
                switched += 1
        self.assertGreater(switched, 0, "the look's accent label does not read over white")


class TheCheck(InARun):
    def findings(self, plans):
        return storyboard.findings(plans, SOURCE["photos"])

    def test_a_caption_no_remedy_reaches_is_named(self):
        self.photos(255)
        # over the photograph: mid-gray words the deepest scrim does not bring to what they need
        p = self.plan(LIGHT)
        b = p["board"]
        c = next(c for c in b["route"]["cards"] if over_photo(c))
        for ln in c["lines"]:
            ln["color"] = MID
        c.pop("scrim", None)
        captions.lay(c, layout(b, c), b["route"]["colors"], short(b))
        self.assertEqual(c["scrim"], legible.SCRIM_MOST)
        named = [x for x in self.findings({"reel": p}) if x.startswith(f"reel: {c['id']}: ") and "over the photograph" in x]
        self.assertTrue(named, c["id"])
        self.assertIn("give the beat a photograph that is darker under its words", named[0])
        # on the ground: words in a color the palette sets next to the ground's
        p = self.plan(GROUND)
        b = p["board"]
        c = b["route"]["cards"][1]
        lay = layout(b, c)
        self.assertFalse(over_photo(c))
        for ln in c["lines"]:
            ln["color"] = lay["ground"]
        named = [x for x in self.findings({"reel": p}) if x.startswith(f"reel: {c['id']}: ") and "on the card's ground" in x]
        self.assertEqual(len(named), len(captions.groups(c)), c["id"])

    def test_a_closer_line_set_under_32_px_is_named(self):
        for style in look.TRIO:
            plans = {fmt: self.plan(style, fmt) for fmt in storyboard.FORMATS}
            self.assertEqual([x for x in self.findings(plans) if ": closer: " in x], [], style)
            for fmt, p in plans.items():
                b = p["board"]
                floor = legible.LEAST * short(b) / 1080
                # the board laid out without the floor: every closer line the shape then sets under it is named
                b["route"]["closer"].pop("least", None)
                under = [(what, size) for what, _, size in captions.closer_lines(b) if size < floor - 0.05]
                got = [x for x in self.findings({**plans, fmt: p}) if x.startswith(f"{fmt}: closer: ")]
                self.assertEqual(len(got), len(under), (style, fmt))
                for (what, size), x in zip(under, got):
                    self.assertIn(f"the {what} ", x)
                    self.assertIn(f"is set at {size:g} px, under the {legible.LEAST} px a phone shows legibly", x)
            # the letterbox's title card sets the handle at 30 px on the reel without the floor
            if style == LIGHT:
                handle = plans["reel"]["board"]["handle"]
                self.assertIn(f'reel: closer: the handle "{handle}" is set at 30 px, under the 32 px a phone shows legibly',
                              self.findings(plans))


class TheTiming(InARun):
    def test_a_board_cut_to_the_music_holds_every_stops_words_whole_with_the_headline_in_a_second_after_its_beat(self):
        flown = 0
        for style in look.TRIO:
            b = self.plan(style, bpm=MUSIC)["board"]
            self.assertTrue(b.get("to_music"), style)
            self.assertEqual(captions.timing(b), [], style)
            times = board_drive.word_times(b)
            self.assertEqual(len(times), sum(1 for c in b["route"]["cards"] if c["lines"]))
            for t in times:
                self.assertGreaterEqual(t["whole"], t["need"] - 1 / board_drive.FPS, (style, t["id"]))
                self.assertLessEqual(t["settled"] or 0, board_drive.SETTLED + 1 / board_drive.FPS, (style, t["id"]))
            flown += sum(1 for x in b["beats"] if x.get("early"))
        self.assertGreater(flown, 0, "a stop the camera flies to keeps its words in time")

    def test_words_that_come_up_late_or_stand_too_briefly_are_named_by_the_check(self):
        p = self.plan(LIGHT, bpm=MUSIC)
        b, sec = p["board"], 60 / MUSIC
        times = {t["id"]: t for t in board_drive.word_times(b)}
        cards = {c["id"]: c for c in b["route"]["cards"]}
        # a stop whose words come up two beats later than the board cut them
        late = copy.deepcopy(p)
        c = next(c for c in late["board"]["route"]["cards"] if c["i"] and c["lines"])
        c["cut"] += 2
        self.assertTrue([x for x in self.findings(late) if x.startswith(f"reel: {c['id']}: the headline ") and "settles" in x])
        # a stop the camera leaves sooner than its words take to read
        brief = copy.deepcopy(p)
        sid = min((t for t in times.values() if t["id"] != "hook"), key=lambda t: t["whole"] - t["need"])["id"]
        slack = times[sid]["whole"] - times[sid]["need"]
        k = next(i for i, c in enumerate(brief["board"]["route"]["cards"]) if c["id"] == sid)
        brief["board"]["route"]["cards"][k]["go"] = cards[sid]["go"] + slack / sec + 0.5
        named = [x for x in self.findings(brief) if x.startswith(f"reel: {sid}: \"") and "stands whole for" in x]
        self.assertTrue(named, sid)
        self.assertIn(f"under the {times[sid]['need']:.2f} s its {times[sid]['n']} words take to read", named[0])

    def findings(self, p):
        return storyboard.findings({"reel": p}, SOURCE["photos"])

    def test_the_kits_own_tempo_lays_a_draft_whose_timing_the_check_leaves_to_the_snap(self):
        for style in look.TRIO:
            b = self.plan(style)["board"]
            self.assertFalse(b.get("to_music", True), style)
            self.assertEqual([x for x in captions.findings(b) if "stands whole" in x or "settles" in x], [], style)

    def test_the_words_before_a_flight_leave_a_quarter_into_whichever_cut_takes_it_and_the_sheet_rests_before_them(self):
        self.assertEqual([board_drive.cut_beats(c) for c in ("bars-close", "grid-wipe", "paper-slide", "hard-cut", None)],
                         [2.0, 1.4, 1.2, 0.0, 0.0])
        cleared = 0
        for style in look.TRIO:
            p = self.plan(style)
            b = p["board"]
            sec = 60 / b["bpm"]
            at, end = board_drive.starts(b)
            ids = [x["id"] for x in b["beats"]]
            # with no window on the cuts into the flights, the words of the stops before them would stand longer
            unclipped = copy.deepcopy(b)
            for x in unclipped["beats"]:
                if x.get("early"):
                    x["transition"] = "hard-cut"
            whole = {t["id"]: t["whole"] for t in board_drive.word_times(b)}
            longer = {t["id"]: t["whole"] for t in board_drive.word_times(unclipped)}
            for i, x in enumerate(b["beats"][1:], 1):
                if x.get("early") and board_drive.cut_beats(x["transition"]) and ids[i - 1] in whole:
                    self.assertLessEqual(whole[ids[i - 1]], longer[ids[i - 1]], (style, ids[i - 1]))
                    cleared += int(x["transition"] != board_drive.FLIGHT_CUT and whole[ids[i - 1]] < longer[ids[i - 1]])
            # the sheet's stop rests before its words fade for the cut into the flight after it
            st = ids.index(p["rest_beats"]["stop"])
            nxt = b["beats"][st + 1]
            if nxt.get("early") and board_drive.cut_beats(nxt["transition"]):
                leave = at[ids[st + 1]]
                after = at[ids[st + 2]] if st + 2 < len(ids) else end
                w = min(board_drive.cut_beats(nxt["transition"]), (leave - at[ids[st]]) / 2, (after - leave) / 2)
                fade = leave - nxt["early"] / sec - w / 4 - storyboard.WORDS_FADE
                self.assertLess(p["rests"]["stop"], fade * board_drive.FPS * sec, style)
        self.assertGreater(cleared, 0, "a cut into a flight other than the bars clears the words before it too")


# the closer at rest, as the film hands it its frame (route/RouteFilm.tsx), as static markup
RUN = """
import fs from 'node:fs';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {planOf, lookOf} from 'ROUTE/plan.ts';
import {CloserFrame, KIT, registerClosers} from 'ROUTE/closers.tsx';
import {closerOf} from 'MOVES/index.ts';
registerClosers();
const out = process.argv.slice(2).map((file) => {
  const board = JSON.parse(fs.readFileSync(file, 'utf8'));
  const plan = planOf(board);
  const look = lookOf(plan);
  const sys = board.system;
  const safe = sys.safe[board.format.name ?? 'reel'] ?? {top: 0, bottom: 0};
  const frame = {window: plan.closer.window, least: plan.closer.least, top: Math.max(safe.top, sys.finish.bars * plan.H),
    bottom: plan.H - Math.max(safe.bottom, sys.finish.bars * plan.H)};
  return renderToStaticMarkup(React.createElement(CloserFrame.Provider, {value: frame},
    React.createElement(closerOf(KIT + sys.closer), {look, local: 99, u: 1})));
});
process.stdout.write(JSON.stringify(out));
"""

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


@unittest.skipUnless(NODE and ESBUILD.exists(), "node or the studio's node modules are absent")
class TheStudioSetsTheCloserLegibly(unittest.TestCase):
    """Each look's closer in each format, drawn by the kit's own closers at rest, in node."""

    def test_every_word_of_the_closer_is_set_at_the_least_size_a_phone_shows_legibly_or_larger(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / "stub.mjs").write_text(STUB)
        (d / "run.mjs").write_text(RUN.replace("ROUTE/", str(MOTION / "studio" / "route") + "/")
                                   .replace("MOVES/", str(MOTION / "system" / "moves") + "/"))
        subprocess.run([str(ESBUILD), str(d / "run.mjs"), "--bundle", "--platform=node", "--format=cjs",
                        f"--outfile={d / 'run.cjs'}", f"--alias:remotion={d / 'stub.mjs'}", "--log-level=error"],
                       check=True, cwd=MOTION, env=dict(os.environ, NODE_PATH=str(MODULES)))
        boards = {}
        for style in look.TRIO:
            for fmt in storyboard.FORMATS:
                b = board_drive.frames(storyboard.plan(SOURCE, fmt, None, style)["board"])
                boards[style, fmt] = b
                (d / f"{style}-{fmt}.json").write_text(json.dumps(b))
        r = subprocess.run([NODE, str(d / "run.cjs"), *(str(d / f"{s}-{f}.json") for s, f in boards)], capture_output=True,
                           text=True, check=True, timeout=120)
        for (style, fmt), html in zip(boards, json.loads(r.stdout)):
            b = boards[style, fmt]
            floor = legible.LEAST * short(b) / 1080
            sizes = [float(v) for v in re.findall(r"font-size:([\d.]+)px", html)]
            self.assertTrue(sizes, (style, fmt))
            self.assertGreaterEqual(min(sizes), floor - 0.05, (style, fmt))
            # the handle stands in the markup at the size the check measured it at
            if b.get("handle"):
                self.assertIn(b["handle"], html)
            want = dict((what, size) for what, _, size in captions.closer_lines(b))
            self.assertTrue(any(abs(s - want["handle"]) < 0.06 for s in sizes), (style, fmt, want, sorted(set(sizes))))


if __name__ == "__main__":
    unittest.main()
