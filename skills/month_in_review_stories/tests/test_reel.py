"""The reel's craft as its plan states it: the hook, the holds, the shots, the closer's stillness and the safe area.

    python3 -m unittest discover -s S/tests -p 'test_reel.py'
"""
import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fixture
import compose
from compose import reel
from compose.common import H, SAFE, W

KIT = Path(__file__).resolve().parents[1]

# the four moments the agent picks, the wedding the peak, each with the shot it wrote from its photograph
PICKED = [(5, False), (13, True), (17, False), (28, False)]
SHOT = {"subject": "the moment in the photograph", "move": "a slow dolly in", "lens": "50 mm", "height": "eye height",
        "light": "soft window light"}


def picked(m):
    m = copy.deepcopy(m)
    by_day = {p["day"]: p for p in m["posts"]}
    m["moments"] = [{"day": d, "photo": by_day[d]["photo"], "line": by_day[d]["caption"], "peak": peak,
                     "shot": dict(SHOT, subject=f"the day {d} photograph")} for d, peak in PICKED]
    return m


def seconds(r, beat):
    return beat * 60 / r["bpm"]


def settled(r, ln):
    """The beat a line's last word has landed on."""
    step = ln.get("step", r["enter"]["step"])
    return ln["at"] + (len(ln["text"].split()) - 1) * step + r["enter"]["beats"]


def ink(ln):
    """The line's ink [x0, y0, x1, y1] in card px, from its own font's outlines, its letters spaced by its tracking."""
    font = reel._font(ln["file"], 200)
    x0, y0, x1, y1 = font.getbbox(ln["text"], anchor="ls")
    k = ln["size"] / 200
    spaced = ln.get("tracking", 0.0) * ln["size"] * max(0, len(ln["text"]) - 1)
    x = ln["x"] - {"middle": 0.5, "end": 1.0}.get(ln.get("anchor"), 0.0) * reel.width(ln["text"], ln["size"], ln["file"], ln.get("tracking", 0.0))
    return x + x0 * k, ln["y"] + y0 * k, x + x1 * k + spaced, ln["y"] + y1 * k


# how far in a turned print's window side stands at the type, px: half the card's tilt over the half height of the print
TURN = 16


def on_screen(box, hold, zoom):
    """The box as the hold's camera frames it at its widest reach, [x0, y0, x1, y1] in frame px: a push or a pull scales
    the card about its middle by up to `zoom`; a crane holds that zoom and moves anywhere between the card's foot and its
    head."""
    x0, y0, x1, y1 = box
    sx = lambda x: (x - W / 2) * zoom + W / 2
    mx, my = W * (1 - 1 / zoom) / 2, H * (1 - 1 / zoom) / 2
    if hold == "crane":
        return sx(x0), (y0 - 2 * my) * zoom, sx(x1), y1 * zoom
    sy = lambda y: (y - H / 2) * zoom + H / 2
    return sx(x0), sy(y0), sx(x1), sy(y1)


class Reel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = picked(fixture.month())
        cls.board = compose.board("editorial-quiet", cls.month)
        cls.r = cls.board["reel"]

    def test_the_hook_states_the_month_and_has_landed_inside_the_first_second(self):
        first = self.r["cards"][0]
        hook = [x for x in first["lines"] if x.get("name") == "hook"]
        self.assertEqual([x["text"] for x in hook], ["my september, in four stories"])
        self.assertLess(seconds(self.r, settled(self.r, hook[0])), 1.0)
        self.assertNotIn("hook", [x.get("name") for c in self.r["cards"][1:] for x in c["lines"]])

    def test_no_two_beats_in_a_row_hold_the_same_way_and_the_first_pushes_in(self):
        holds = [c["hold"] for c in self.r["cards"]]
        self.assertEqual(holds[0], "push")
        self.assertTrue(all(a != b for a, b in zip(holds, holds[1:])), holds)
        self.assertLessEqual(self.r["zoom"], 1.05)

    def test_the_wall_moves_in_view_in_every_look_and_no_two_beats_in_a_row_move_alike(self):
        for name in compose.TRIO:
            beats = compose.board(name, self.month)["reel"]["timeline"]["beats"]
            moves = [b["move"] for b in beats]
            self.assertNotIn(moves[-1], reel.COVERS, (name, moves))
            self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), (name, moves))

    def test_the_months_line_and_its_descenders_stand_clear_above_the_first_print_in_every_look(self):
        for name in compose.TRIO:
            c = compose.board(name, self.month)["reel"]["cards"][0]
            hook = next(x for x in c["lines"] if x.get("name") == "hook")
            self.assertGreaterEqual(c["band"][0] - (hook["y"] + 0.25 * hook["size"]), 24, (name, hook["y"], hook["size"], c["band"]))

    def test_the_first_cards_words_stand_inside_the_window_of_the_print_its_title_move_drops(self):
        # polaroid-drop on the title stands its print inside the safe area, as wide as the frame allows and no taller
        # than the safe area, its rim covering everything outside the picture's window: the month's line, the day and
        # their words stand inside that window through the whole hold, in every style whose first move it is
        sy0, sy1 = SAFE["top"], H - SAFE["bottom"]
        w = min(W * 0.96, (sy1 - sy0) / 1.31)
        rest = sy0 + max(0.0, (sy1 - sy0 - 1.31 * w) / 2)
        top, foot = rest + 0.035 * w, rest + 1.05 * w - 0.035 * w
        # the print turns a little on the title, so its window's sides stand up to TURN px further in at the type
        left, right = (W - w) / 2 + 0.035 * w + TURN, (W + w) / 2 - 0.035 * w - TURN
        seen = 0
        for name in compose.style.styles():
            r = compose.board(name, self.month)["reel"]
            if r["timeline"]["beats"][0]["move"] != "polaroid-drop":
                continue
            seen += 1
            c = r["cards"][0]
            for ln in c["lines"]:
                x0, y0, x1, y1 = on_screen(ink(ln), c["hold"], r["zoom"])
                where = (name, ln["text"], round(x0), round(y0), round(x1), round(y1), round(left), round(top), round(right), round(foot))
                self.assertGreaterEqual(y0, top, where)
                self.assertLessEqual(y1, foot, where)
                self.assertGreaterEqual(x0, left, where)
                self.assertLessEqual(x1, right, where)
        self.assertGreater(seen, 0)

    def test_the_walls_month_line_stands_whole_above_the_paper_foot_a_wall_move_lays(self):
        # a wall move lays its paper from four fifths of the frame down (page-drift's torn foot): the month line under
        # the wall, its descenders included, stands above it in every look
        for name in compose.TRIO:
            r = compose.board(name, self.month)["reel"]
            ln = r["closer"]["lines"][0]
            self.assertLessEqual(ln["y"] + 0.25 * ln["size"], 0.8 * r["H"] - 12, (name, ln["y"], ln["size"]))

    def test_a_moments_words_stand_where_the_cards_line_sets_them_in_every_look(self):
        # the look's own page: centred under a scrapbook print, in the swiss grid's column, from the left margin
        # in the editorial page, the first card's a further INSET in (inside its title move's print); every word
        # inside the safe area through its hold
        for name in compose.TRIO:
            r = compose.board(name, self.month)["reel"]
            box = compose.style.card(name)["photo"]["line"]
            for k, c in enumerate(r["cards"]):
                inset = reel.INSET if k == 0 else 0
                said = [x for x in c["lines"] if x.get("name") != "hook"]
                for ln in said:
                    x0, y0, x1, y1 = on_screen(ink(ln), c["hold"], r["zoom"])
                    where = (name, c["key"], ln["text"], round(x0), round(x1))
                    self.assertGreaterEqual(x0, SAFE["left"], where)
                    self.assertLessEqual(x1, W - SAFE["right"], where)
                    if box["align"] == "center":
                        self.assertEqual((ln.get("anchor"), ln["x"]), ("middle", W / 2), where)
                    else:
                        self.assertEqual(ln.get("anchor"), "start", where)
                if box["align"] != "center":
                    self.assertEqual(len({x["x"] for x in said}), 1, (name, c["key"]))
                    # in its column, or from the left margin when the column would cut their words
                    starts = {max(reel.TX, round(box["box"][0] * W, 1)) + inset, reel.TX + inset}
                    self.assertIn(said[0]["x"], starts, (name, c["key"]))
                self.assertNotIn("…", " ".join(x["text"] for x in said[1:]) if name != "editorial-quiet" else "", (name, c["key"]))
        short = copy.deepcopy(self.month)
        for x in short["moments"]:
            x["line"] = " ".join(x["line"].split()[:3])
        swiss = compose.board("swiss-grid", short)["reel"]["cards"]
        column = max(reel.TX, round(compose.style.card("swiss-grid")["photo"]["line"]["box"][0] * W, 1))
        at = [c["lines"][-1]["x"] for c in swiss]
        self.assertEqual(at, [column + reel.INSET] + [column] * (len(swiss) - 1), at)

    def test_picture_and_music_stop_as_the_closing_page_finishes_its_build_in_every_look(self):
        # every closing page draws its build on its progress from its start to the stop, so the stop is where it ends
        moves = Path(compose.__file__).resolve().parents[2] / "motion" / "system" / "moves" / "closer"
        for name in reel.BUILD:
            self.assertNotIn("span(local", (moves / f"{name}.tsx").read_text(), name)
        for name in compose.TRIO:
            page = compose.board(name, self.month)["reel"]["closer"]["page"]
            self.assertAlmostEqual(page["still"] - page["at"], reel.BUILD[page["name"]], places=2, msg=name)

    def test_every_clip_is_the_shot_written_for_its_photograph_and_each_seam_asks_for_texture(self):
        clips, cards = self.r["clips"], self.r["cards"]
        self.assertEqual([c["use"] for c in clips], ["hook"] + ["texture", "still"] * (len(cards) - 1))
        at = lambda beat: round(beat * self.r["fps"] * 60 / self.r["bpm"])
        for c in clips:
            # as long as its window of the film as the film draws it, to the frame, the 9:16 frame, written out and back
            self.assertEqual(c["seconds"], round((at(c["at"][1]) - at(c["at"][0])) / self.r["fps"], 1))
            for said in (f"{c['seconds']:g} s", "9:16", "1080x1920", c["subject"], c["move"], c["lens"], c["light"]):
                self.assertIn(said, c["prompt"])
            self.assertIn("its last frame is its first", c["loop"])
            self.assertIn(c["stand_in"], reel.STAND_IN.values())
        for c, card in zip([c for c in clips if c["use"] != "texture"], cards):
            self.assertEqual(c["subject"], f"the day {card['day']} photograph")
            for k in ("move", "lens", "height", "light"):
                self.assertEqual(c[k], SHOT[k])
            self.assertEqual(c["at"], [0.0 if c["use"] == "hook" else round(card["arrive"], 3), card["move"][0]])
            self.assertEqual(c["stand_in"], reel.STAND_IN[card["hold"]])
        for c, card in zip([c for c in clips if c["use"] == "texture"], cards):
            self.assertEqual(c["at"], card["move"])
            self.assertIn("and back", c["move"])

    def test_a_hold_plays_the_way_out_its_shot_names_first(self):
        for move, hold in [("a slow push in toward the crust and back", "push"), ("a crane up the wall and back down", "crane"),
                           ("the camera pulls back and returns", "pull")]:
            self.assertEqual(reel.hold_of({"move": move}, None, 1), hold, move)
        self.assertNotEqual(reel.hold_of({"move": "a crane up the wall and back down"}, "crane", 1), "crane")

    def test_no_two_beats_in_a_row_draw_the_line_the_same_way(self):
        acts = [c["act"] for c in self.r["cards"]]
        self.assertTrue(all(a != b for a, b in zip(acts, acts[1:])), acts)

    def test_the_line_acts_on_what_its_card_shows(self):
        # it falls onto the peak, rides in along a wide photograph, else climbs, never as the card before it did
        self.assertEqual([reel.act_of(True, "portrait", None), reel.act_of(False, "landscape", None), reel.act_of(False, "portrait", None)],
                         ["fall", "ride", "climb"])
        self.assertEqual(reel.act_of(False, "portrait", "climb"), "fall")
        self.assertEqual([c["act"] for c in self.r["cards"] if c["peak"]], ["fall"])
        self.assertGreater(len({c["act"] for c in self.r["cards"]}), 1)

    def test_the_line_reaches_where_its_act_starts_as_the_camera_lands_from_the_move_that_brings_it(self):
        track = self.r["line"]
        at = lambda t: [y for b, y, _ in track if abs(b - t) < 0.006]
        cards = self.r["cards"]
        for before, c in zip(cards, cards[1:]):
            start = at(c["rise"][0])
            self.assertEqual(len(start), 1, c["key"])
            self.assertEqual(at(before["move"][1]), start, c["key"])
            self.assertEqual([y for b, y, _ in track if before["move"][0] < b < before["move"][1]], [], c["key"])

    def test_a_falling_line_starts_inside_the_frame_above_its_photograph(self):
        track = self.r["line"]
        falls = [c for c in self.r["cards"] if c["act"] == "fall"]
        self.assertTrue(falls)
        for c in falls:
            start = [y for b, y, _ in track if abs(b - c["rise"][0]) < 0.006]
            card_y = (start[0] - c["T"]["o"][1]) / c["T"]["s"]
            self.assertGreater(card_y, 0, c["key"])
            self.assertLess(card_y, c["band"][0], c["key"])

    def test_the_last_line_draws_back_into_its_cell_before_it_runs_out_under_the_wall(self):
        track, last, cl = self.r["line"], self.r["cards"][-1], self.r["closer"]
        a, land = last["move"][0], cl["land"]
        after = [(round((b - a) / (land - a), 2), y) for b, y, _ in track if a < b < land - 1e-3]
        self.assertEqual(after, [(0.8, last["cell"][1]), (0.88, self.r["floor"] + 8)])

    def test_the_closers_posts_rise_once_the_pull_back_has_the_top_of_the_wall_in_the_picture(self):
        cl = self.r["closer"]
        rises = [t["at"] for t in cl["tiles"]]
        self.assertGreaterEqual(min(rises), cl["at"] + 0.4)
        self.assertLessEqual(max(rises), cl["at"] + 0.45 + 1.4 + 0.01)
        self.assertEqual(rises, sorted(rises))

    def test_the_type_steps_from_the_months_line_to_their_words_to_the_day(self):
        display = self.board["system"]["display"]["file"]
        first = self.r["cards"][0]["lines"]
        hook = next(x for x in first if x.get("name") == "hook")
        day = next(x for x in first if x.get("name") == "small")
        words = [x for x in first if x.get("name") not in ("hook", "small", "count", "big")]
        text = self.board["system"]["text"]["file"]
        # the day is the caption's small kicker in the text face, their words the card's photo line, in its face
        self.assertEqual((hook["file"], day["file"]), (display, text))
        self.assertTrue(words and all(x["file"] == display for x in words))
        self.assertGreater(hook["size"], max(x["size"] for x in words))
        self.assertGreater(min(x["size"] for x in words), day["size"])

    def test_a_line_that_fits_one_row_sets_larger_than_one_that_runs_to_two(self):
        m = copy.deepcopy(self.month)
        m["moments"][0]["line"] = "the day it all came together"
        m["moments"][1]["line"] = "the long way round the lake and back again before the rain came in over the hills that evening"
        cards = compose.board("editorial-quiet", m)["reel"]["cards"]
        said = lambda c: [x for x in c["lines"] if x.get("name") not in ("hook", "small", "count", "big")]
        by_day = {c["day"]: said(c) for c in cards}
        short, long_ = by_day[m["moments"][0]["day"]], by_day[m["moments"][1]["day"]]
        self.assertEqual((len(short), len(long_)), (1, 2))
        self.assertGreater(short[0]["size"], long_[0]["size"])
        day = next(x for c in cards for x in c["lines"] if x.get("name") == "small")
        self.assertLess(day["size"], long_[0]["size"])
        for ln in short + long_:
            self.assertLessEqual(ln["x"] + reel.width(ln["text"], ln["size"], ln["file"]), reel.R0 - reel.INSET + 0.5, ln["text"])

    def test_the_wall_shares_its_columns_and_every_rim_stands_apart(self):
        tiles = self.r["closer"]["tiles"]
        cw = min(t["cell"][2] - t["cell"][0] for t in tiles)
        lefts = {round(t["cell"][0]) for t in tiles}
        for t in tiles:
            x0, _, x1, _ = t["cell"]
            self.assertTrue(any(abs(x1 - (l + cw)) < 1 for l in lefts), (t["day"], t["cell"]))
            self.assertGreaterEqual(t["label"]["size"], 28)
        self.assertLessEqual(2 * reel.RIM, reel.GAP)

    def test_the_drafted_light_names_the_side_it_falls_from(self):
        from PIL import Image, ImageDraw
        import research
        im = Image.new("RGB", (300, 400), (60, 60, 60))
        ImageDraw.Draw(im).rectangle((0, 0, 99, 399), fill=(230, 220, 200))
        self.assertEqual(research.light_from(im), "from the left")
        self.assertEqual(research.light_from(Image.new("RGB", (300, 400), (90, 90, 90))), "from in front of the subject")

    def test_the_requests_carry_every_shot_field(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "storyboards" / "editorial-quiet").mkdir(parents=True)
            (Path(d) / "build" / "latest").write_text("run\n")
            (run / "storyboards" / "editorial-quiet" / "storyboard.json").write_text(json.dumps({"reel": self.r}))
            (run / "winner.json").write_text(json.dumps({"board": "editorial-quiet"}))
            got = subprocess.run([sys.executable, str(fixture.SCRIPTS / "clips.py"), "list"], cwd=d, capture_output=True, text=True,
                                 env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
            self.assertEqual(got.returncode, 0, got.stderr)
            reqs = json.loads((run / "clips" / "requests.json").read_text())["clips"]
        self.assertEqual(len(reqs), len(self.r["clips"]))
        for q in reqs:
            for k in ("use", "subject", "move", "lens", "height", "light", "seconds", "loop", "image", "prompt", "stand_in"):
                self.assertTrue(q.get(k), (q["id"], k))
            self.assertIn(f"{q['seconds']:g} s", q["prompt"])

    def test_the_closer_stops_with_the_ask_landed_and_holds_still_and_silent_over_a_second(self):
        cl = self.r["closer"]
        stop = cl["still"]
        self.assertGreaterEqual(seconds(self.r, self.r["end"] - stop), 1.0)
        stops = [c for c in self.r["sound"] if c["kind"] == "stop"]
        self.assertEqual([c["at"] for c in stops], [stop])
        self.assertEqual(max(c["at"] for c in self.r["sound"]), stop)
        for ln in cl["lines"]:
            self.assertLessEqual(settled(self.r, ln), stop + 1e-6, ln["text"])

    def test_every_word_on_a_card_stays_inside_the_safe_area_through_its_hold(self):
        for c in self.r["cards"]:
            for ln in c["lines"]:
                x0, y0, x1, y1 = on_screen(ink(ln), c["hold"], self.r["zoom"])
                where = f"{c['key']} ({c['hold']}) {ln['text']!r}: {x0:.0f}..{x1:.0f} x {y0:.0f}..{y1:.0f}"
                self.assertGreaterEqual(x0, SAFE["left"], where)
                self.assertLessEqual(x1, W - SAFE["right"], where)
                self.assertGreaterEqual(y0, SAFE["top"], where)
                self.assertLessEqual(y1, H - SAFE["bottom"], where)

    def test_the_reel_carries_the_safe_area_the_camera_frames_the_closer_in(self):
        self.assertEqual(self.r["safe"], SAFE)


if __name__ == "__main__":
    unittest.main()


class Cuts(unittest.TestCase):
    """The cuts that jump and the moves that fly a photograph in, on the scrapbook card, whose photo beats cut hard."""

    def test_no_frame_is_drawn_inside_a_jump_and_its_cut_falls_between_two_frames(self):
        r = compose.board("scrapbook", picked(fixture.month()))["reel"]
        tick = r["bpm"] / (60 * r["fps"])
        jumps = [c["move"] for c in r["cards"] if c["move"][1] - c["move"][0] < 1.5 * tick]
        self.assertTrue(jumps)
        for a, b in jumps:
            # the last frame before the jump ends is drawn before it starts
            self.assertLessEqual((math.ceil(b / tick - 1e-6) - 1) * tick, a + 1e-6, (a, b))
            mid = (a + b) / 2 / tick
            self.assertAlmostEqual(mid - math.floor(mid), 0.5, delta=0.01)
            self.assertIn(round(a + (b - a) / 2, 3), [round(x, 3) for x in r["timeline"]["cuts"]])

    def test_a_stack_that_flies_in_keeps_its_cards_hold_and_its_words_and_shutter_wait_for_its_landing(self):
        pick = reel.style.pick

        def prefer(options, tags, form, used, avoid):
            if form == "photo" and "exploded-layers" in [o["id"] for o in options] and not used.get("exploded-layers"):
                used["exploded-layers"] = 1
                return "exploded-layers"
            return pick(options, tags, form, used, avoid)

        # a 28 s reel, which has the beats past its four moments' natural holds that a move taking the frame adds
        month = dict(picked(fixture.month()), ask={"seconds": 28})
        with mock.patch.object(reel.style, "pick", prefer):
            r = compose.board("scrapbook", month)["reel"]
        beat = next(b for b in r["timeline"]["beats"] if b["move"] == "exploded-layers")
        card = next(c for c in r["cards"] if c["key"] == beat["id"])
        # the stack lands the photograph and hands back with a cut on the landing (exploded-layers.tsx), so the beat
        # holds as long as its card does
        self.assertEqual(beat["held"], reel.held_of(card)["held"])
        # the landing exploded-layers reads from its beat (motion/system/moves/arrival.tsx): 0.55 of the room from the
        # cut to the hold's end, at most 1.15 s
        land = min(1.15, 0.55 * seconds(r, beat["held"][1] - beat["at"]))
        first = min(ln["at"] for ln in card["lines"] if ln["text"].strip())
        self.assertGreaterEqual(seconds(r, first - beat["at"]), land - 1e-3)
        # the shutter under the photograph sounds as the stack lands
        cue = next(b for b in r["fx"]["beats"] if b["id"] == beat["id"])
        self.assertAlmostEqual(seconds(r, cue["layers"][0]["at"]["arrive"] - beat["at"]), land, delta=0.02)


    def test_each_photographs_beat_hands_its_move_the_part_that_matters_as_fractions_of_the_photograph(self):
        # a move that marks the photograph (doodle-draw-on) rings this point, so it is where the card's crop centres
        r = compose.board("scrapbook", picked(fixture.month()))["reel"]
        cards = {c["key"]: c for c in r["cards"] if c["file"]}
        beats = [b for b in r["timeline"]["beats"] if b["id"] in cards]
        self.assertTrue(beats)
        for b in beats:
            (x, y, w, h), (fx, fy) = cards[b["id"]]["place"], cards[b["id"]]["focus"]
            u, v = b["focus"]
            self.assertAlmostEqual(x + u * w, fx, delta=0.5, msg=b["id"])
            self.assertAlmostEqual(y + v * h, fy, delta=0.5, msg=b["id"])
            self.assertTrue(0 <= u <= 1 and 0 <= v <= 1, b)

    def test_a_move_that_takes_the_frame_plays_only_on_beats_past_every_moments_natural_hold(self):
        # a move that takes the frame adds its beats to its own beat; it plays only when the reel has those beats past
        # every moment's natural hold, so no other moment's words are cut short for it, even when the look prefers one
        pick, carried = reel.style.pick, reel.carried
        natural = []

        def prefer(options, tags, form, used, avoid):
            for name in reel.TAKES:
                if form == "photo" and name in [o["id"] for o in options]:
                    used[name] = used.get(name, 0) + 1
                    return name
            return pick(options, tags, form, used, avoid)

        def kept(m, caps):
            natural[:] = carried(m, caps)
            return list(natural)

        played = 0
        for secs in (15, 20, 24, 28, 30):
            month = dict(picked(fixture.month()), ask={"seconds": secs})
            with mock.patch.object(reel.style, "pick", prefer), mock.patch.object(reel, "carried", kept):
                r = compose.board("scrapbook", month)["reel"]
            last = reel.closing(r["bpm"], compose.style.card("scrapbook")["closer"])[3]
            spare = r["end"] - reel.OPEN - last - sum(natural)
            moves = [b["move"] for b in r["timeline"]["beats"] if b.get("move") in reel.TAKES]
            played += len(moves)
            self.assertLessEqual(sum(reel.TAKES[x] * r["bpm"] / 60 for x in moves), max(0.0, spare) + 1e-6, (secs, moves))
        self.assertGreater(played, 0)

    def test_a_move_that_lays_a_window_plays_only_on_the_first_card_whose_band_stands_inside_it(self):
        # tape-slap paints the card's ground outside a window from 16 to 78 percent of the frame down; a later card's
        # words stand from ABOVE over its band or under it to past that foot, and the wall runs from WALL_TOP, so a
        # window move plays on the first card alone, even when the look prefers one on every beat
        pick = reel.style.pick

        def prefer(options, tags, form, used, avoid):
            for name in sorted(reel.WINDOWS):
                if name in [o["id"] for o in options]:
                    used[name] = used.get(name, 0) + 1
                    return name
            return pick(options, tags, form, used, avoid)

        for name in compose.TRIO:
            with mock.patch.object(reel.style, "pick", prefer):
                r = compose.board(name, picked(fixture.month()))["reel"]
            moves = [b.get("move") for b in r["timeline"]["beats"]]
            self.assertFalse([x for x in moves[1:] if x in reel.WINDOWS], (name, moves))
        self.assertIn("tape-slap", reel.WINDOWS)

    def test_a_calmer_photograph_shortens_its_look_never_the_time_its_words_take_to_read(self):
        m = compose.Month(picked(fixture.month()))
        compose.board("scrapbook", m)
        caps = [[p.said] for p in m.walk]
        with mock.patch.object(reel, "busy_ratio", lambda m, p: 1.0):
            even = reel.carried(m, caps)
        with mock.patch.object(reel, "busy_ratio", lambda m, p: 0.5):
            calm = reel.carried(m, caps)
        for p, a, b in zip(m.walk, even, calm):
            if p is not m.peak:
                self.assertGreaterEqual(b, min(a, 9.0) - 2.5 * (1 - 0.5 ** 0.5) - 1e-9, p.said)


class Field(unittest.TestCase):
    """The card's field around its print: the photograph mirrored past its edges is a haze, never a second picture."""

    def test_the_mirrored_field_blurs_to_a_haze_past_the_photograph_and_falls_off_soon(self):
        src = (KIT / "motion" / "studio" / "climb" / "card.tsx").read_text()
        field = src[src.index("const fieldMaterial"):src.index("customProgramCacheKey = () => 'field'")]
        self.assertIn("float far = smoothstep(0.0, 120.0, past);", field)
        self.assertIn("softAt(mirror, vec2(110.0 / uPlace.z, 110.0 / uPlace.w)), far)", field)
        self.assertIn("exp(-max(past, 0.0) / 260.0)", field)

    def test_the_look_hands_the_moves_the_safe_area(self):
        src = (KIT / "motion" / "studio" / "climb" / "plan.ts").read_text()
        look = src[src.index("export const lookOf"):]
        self.assertIn("safe: r.safe,", look[:look.index("\n};")])
