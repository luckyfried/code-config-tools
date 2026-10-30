"""The board builder (scripts/storyboard.py, compose.py, tones/drive.py, framing.py): the facts it computes from the
posts, the wall and its stations, and the rules every board keeps in every format.

    python3 -m unittest discover -s S/tests        (S = this skill's folder; needs Pillow)
"""
import argparse
import copy
import os
import random
import re
import shutil
import statistics
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
# the look every board in these tests takes: the one of the trio that tells all 27 pottery posts inside 60 s
STYLE = "kinetic-type"
sys.path.insert(0, str(KIT / "evals" / "fixtures"))

import _env  # noqa: E402
import compose  # noqa: E402
import framing  # noqa: E402
import qa  # noqa: E402
import research  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402
from tones import drive  # noqa: E402
from make_person import SET_CAPTIONS  # noqa: E402
from timeline import matches, milestones, terms_for  # noqa: E402

# The pottery set's dates, as make_person.py dates its photographs; its captions are SET_CAPTIONS["pottery"].
POTTERY_DATES = ["2025-08-09", "2025-08-18", "2025-08-28", "2025-09-18", "2025-09-30", "2025-10-18", "2025-10-30", "2025-11-18", "2025-11-30",
                 "2025-12-18", "2025-12-30", "2026-01-18", "2026-01-30", "2026-02-24", "2026-03-24", "2026-04-18", "2026-04-30", "2026-05-18",
                 "2026-05-30", "2026-06-18", "2026-06-30", "2026-07-24", "2026-08-18", "2026-08-30", "2026-09-18", "2026-09-30", "2026-10-14"]
SIZES = [(1200, 1600), (1600, 1200), (1000, 1000), (900, 1400), (1500, 1000), (1920, 1080)]
# their line on each pottery photograph, as research.py drafts it from their caption
POTTERY_LINES = ["day one", "class one tonight", "centering is the hardest part", "the first pot that survived", "a mug", "a stack of early bowls",
                 "bigger forms this week", "walls getting thinner", "shelves of greenware drying all weekend", "rows of them now", "one big smooth form",
                 "a whole kiln load of mine", "decoration now", "first glaze firing", "matte glaze", "my first matching set", "brushwork on a thrown jar",
                 "raku firing", "a bowl made to be used", "slip inlay", "beyond bowls and mugs", "my first sale table",
                 "a shopfront that stocks my work now", "carving all week", "a vase in someone's home", "tall glazed jugs", "fourteen months in"]


def photograph(path, k):
    """A stand-in photograph: a lit wall over a table, a pot on it, and grain, so a camera move shows."""
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(k)
    w, h = SIZES[k % len(SIZES)]
    im = Image.new("RGB", (w, h), (196, 184, 168))
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(h * 0.62), w, h], fill=(120, 84, 58))
    pw, ph = int(w * rnd.uniform(0.25, 0.5)), int(h * rnd.uniform(0.25, 0.45))
    cx = int(w * rnd.uniform(0.35, 0.65))
    d.ellipse([cx - pw // 2, int(h * 0.66) - ph, cx + pw // 2, int(h * 0.66)], fill=(rnd.randrange(60, 220), rnd.randrange(60, 160), rnd.randrange(40, 120)))
    noise = Image.effect_noise((w, h), 40).convert("RGB")
    im = Image.blend(im, noise, 0.18).filter(ImageFilter.GaussianBlur(0.6))
    im.save(path, quality=90)
    return str(path)


def posts_of(dates, captions, folder):
    out = []
    for i, (d, c) in enumerate(zip(dates, captions), 1):
        out.append({"id": f"p{i:02d}", "date": d, "kind": "post", "caption": c, "photo": photograph(Path(folder) / f"s{i:02d}.jpg", i), "src": None,
                    "video": None, "step": round(0.1 + (i * 37 % 11) / 11, 3)})
    return out


def build(dates, captions, folder, curate=None):
    """The builder's draft, without the files: framed rows and their facts, their words taken from research.py's draft of
    taste.json's moments (each moment passed through `curate` first, as the agent's read would change it)."""
    posts, _ = storyboard.dated(posts_of(dates, captions, folder))
    milestones(posts)
    moments = research.moments(posts)
    for m in moments:
        (curate or (lambda m: None))(m)
    storyboard.told(posts, moments)
    rows = framing.frame(posts, Path(folder) / "public")["posts"]
    fx = storyboard.facts(rows) | {"said": research.said_span(posts, storyboard.facts(rows)["months"] or 0)}
    return rows, fx, Path(folder) / "public"


def assert_readable(test, board):
    """Every card holds still long enough to read its words: a chapter's line from its landing, an ordinary card's from
    when it starts to rise, and a next line from its rising, each READ[0] + READ[1] * words seconds."""
    k = 60 / board["bpm"]
    for c in board["film"]["cards"]:
        title = sum(len(ln["text"].split()) for ln in c["title"])
        rest = sum(len(ln["text"].split()) for ln in c["rest"])
        start = c["title_at"] if c["kind"] == "ordinary" else c["land"]
        with test.subTest(card=c["id"]):
            if title:
                test.assertGreaterEqual((c["leave"] - start) * k + 1e-6, 0.3 + 0.12 * title)
            if rest:
                test.assertGreaterEqual((c["leave"] - c["rest_at"]) * k + 1e-6, 0.3 + 0.12 * rest)


WHO = {"name": "Maren Okafor", "handle": "@maren.okafor"}


class Pottery(unittest.TestCase):
    """The pottery set: 27 posts, 2025-08-09 to 2026-10-14."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.rows, cls.fx, cls.public = build(POTTERY_DATES, SET_CAPTIONS["pottery"], cls.tmp.name)
        cls.boards = {f: compose.board(STYLE, cls.rows, cls.fx, WHO, f) for f in compose.FORMATS}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        # the card in use is global and a test may lay out another look; the boards here are the class's look
        compose.use(STYLE)

    def findings(self, board):
        return storyboard.check_board(board, self.rows, self.fx)

    def test_facts(self):
        self.assertEqual((self.fx["first"], self.fx["latest"]), ("2025-08-09", "2026-10-14"))
        self.assertEqual((self.fx["days"], self.fx["months"], self.fx["count"]), (431, 14, 27))

    def test_milestones_are_the_posts_whose_caption_says_first(self):
        self.assertEqual([p["id"] for p in self.rows if p["milestone"]], ["p04", "p14", "p16", "p22"])

    def test_three_boards_take_the_trio_in_board_order(self):
        self.assertEqual(storyboard.styles_of({}), ["cinematic-letterbox", "editorial-quiet", "kinetic-type"])
        named = storyboard.styles_of({"style": "kinetic-type"})
        self.assertEqual((named[0], len(set(named))), ("kinetic-type", 3))

    def test_a_sound_lands_where_a_beat_lands_and_nowhere_else(self):
        for f, b in self.boards.items():
            with self.subTest(format=f):
                cues = b["sound"]
                self.assertLessEqual(len(cues), len(b["beats"]) + 4)
                self.assertLessEqual({c["kind"] for c in cues}, {"hit", "riser", "impact", "stop"})
                self.assertEqual([(c["kind"], c["beat"]) for c in cues if c["kind"] in ("riser", "impact", "stop")],
                                 [("riser", "closer"), ("impact", "closer"), ("stop", "closer")])
                hits = [c["beat"] for c in cues if c["kind"] == "hit"]
                self.assertEqual(sorted(set(hits), key=hits.index), [bt["id"] for bt in b["beats"][:-1]])
                self.assertLessEqual(hits.count("hook"), 2)
                self.assertTrue(all(hits.count(bt["id"]) == 1 for bt in b["beats"][1:-1]), hits)
                self.assertEqual(set(qa.sound_of(b)), {"cues", "last", "stop"})
                self.assertEqual(qa.sound_of(b)["cues"], sum(1 for c in b["sound"] if c["kind"] != "stop"))

    def test_every_board_keeps_every_rule_in_every_format(self):
        for f, b in self.boards.items():
            with self.subTest(format=f):
                self.assertEqual(self.findings(copy.deepcopy(b)), [])

    def test_the_wall_holds_every_photograph_in_calendar_order_and_leaves_the_course_clear(self):
        for f, b in self.boards.items():
            film = b["film"]
            W, H = b["format"]["width"], b["format"]["height"]
            course = film["course"]
            tiles = [c["tile"] for c in film["cards"]]
            with self.subTest(format=f):
                self.assertEqual([c["id"] for c in film["cards"]], [r["id"] for r in self.rows])
                self.assertEqual([c["date"] for c in film["cards"]], sorted(c["date"] for c in film["cards"]))
                self.assertEqual((course[0], course[2]), (0, W))
                for x0, y0, x1, y1 in tiles:
                    self.assertTrue(0 < x0 < x1 < W and 0 < y0 < y1 < H)
                    self.assertTrue(y1 <= course[1] + 0.01 or y0 >= course[3] - 0.01, (y0, y1, course))
                for i, a in enumerate(tiles):
                    for c in tiles[i + 1:]:
                        self.assertFalse(a[0] < c[2] - 0.01 and c[0] < a[2] - 0.01 and a[1] < c[3] - 0.01 and c[1] < a[3] - 0.01)

    def test_the_course_runs_across_the_walls_top_and_no_station_frames_it(self):
        for f, b in self.boards.items():
            course = b["film"]["course"]
            with self.subTest(format=f):
                self.assertLess(course[1], min(c["tile"][1] for c in b["film"]["cards"]))
                for c in b["film"]["cards"]:
                    st = c["station"]
                    y0, y1 = st["c"][1] - st["h"] / 2, st["c"][1] + st["h"] / 2
                    self.assertLessEqual(max(0, min(y1, course[3]) - max(y0, course[1])) / st["h"], 0.1, c["id"])

    def test_day_one_and_the_latest_hang_double_and_no_two_moves_in_a_row_are_the_same(self):
        for f, b in self.boards.items():
            cards = b["film"]["cards"]
            wide = [c["tile"][2] - c["tile"][0] for c in cards]
            # a print with no move of its own plays the print's lift and the camera alone
            moves = [c["move"] for c in cards[1:]]
            with self.subTest(format=f):
                for k in (0, -1):
                    self.assertGreater(wide[k], 1.8 * statistics.median(wide[1:-1]))
                self.assertFalse([k for k in range(1, len(moves)) if moves[k] and moves[k] == moves[k - 1]], moves)
                self.assertLessEqual({m for m in moves if m}, set(compose.ids(compose.card(STYLE), "moves")))
                self.assertTrue(any(moves), moves)

    def test_the_closer_shape_runs_three_beats_and_at_a_slow_tempo_under_two_seconds_so_it_never_stalls_before_the_stop(self):
        shape = lambda bpm: drive.seconds_of(drive.to_stop(bpm) - drive.CLOSER_MOVE - drive.WALL_READ, bpm)
        self.assertAlmostEqual(drive.to_stop(125) - drive.CLOSER_MOVE - drive.WALL_READ, 3.0)
        for bpm in (60, 73, 79):
            self.assertLessEqual(shape(bpm), drive.CLOSER_MOST + 1e-9)

    def test_a_type_mask_sets_the_peaks_line_full_frame_then_cuts_to_the_print_so_the_line_is_on_screen_once(self):
        for f, b in self.boards.items():
            film = b["film"]
            beats = film["timeline"]["beats"]
            masked = [k for k, bt in enumerate(beats) if bt["move"] == "type-mask-reveal"]
            with self.subTest(format=f):
                self.assertTrue(masked, [bt["move"] for bt in beats])
                for k in masked:
                    mask, then = beats[k], beats[k + 1]
                    card = next(c for c in film["cards"] if c["id"] == mask["id"])
                    self.assertEqual(mask["words"], card["mask"])
                    # the print's label sets its date and their next line, never the line the mask set
                    self.assertNotIn(card["mask"], " ".join(ln["text"] for ln in card["title"] + card["rest"]))
                    self.assertNotIn("box", mask)
                    self.assertEqual((then["form"], then["move"], then["words"], then["box"]), ("photo", None, "", card["box"]))
                    self.assertEqual(then["at"], mask["end"])
                    # the print is seen standing with its line for longer than its line takes to read
                    self.assertLess(card["arrive"], then["at"])
                    self.assertGreater(card["leave"] - then["at"], 2.0)

    def test_every_print_stands_on_the_wall_and_one_that_covers_its_station_edge_to_edge_is_refused(self):
        for f, b in self.boards.items():
            with self.subTest(format=f):
                self.assertFalse([x for x in self.findings(b) if x.startswith(("wall:", "edge:"))])
        b = copy.deepcopy(self.boards["reel"])
        c = b["film"]["cards"][5]
        x0, y0, x1, y1 = c["rect"]
        w, h = x1 - x0, y1 - y0
        c["rect"] = [x0 - w, y0 - h, x1 + w, y1 + h]
        bad = [x for x in self.findings(b) if x.startswith("edge:")]
        self.assertEqual(len(bad), 1)
        self.assertIn(c["id"], bad[0])

    def test_the_only_numbers_on_screen_are_their_dates(self):
        for f, b in self.boards.items():
            shown = {n for w in storyboard.words_of(b) for n in re.findall(r"\d+", w)}
            with self.subTest(format=f):
                self.assertFalse({"432", "431", "27"} & shown, shown)
                self.assertFalse(any(re.search(r"\d+ (months|days)", w) for w in storyboard.words_of(b)))
                self.assertLessEqual(shown, storyboard.allowed_numbers(self.fx, self.rows))
        bad = copy.deepcopy(self.boards["reel"])
        bad["film"]["closer"]["lines"][0]["text"] = "500 days"
        self.assertTrue(any(x.startswith("numbers:") for x in self.findings(bad)))

    def test_every_card_carries_their_own_line_and_no_count(self):
        for f, b in self.boards.items():
            film = b["film"]
            with self.subTest(format=f):
                self.assertFalse({"hook", "word"} & set(film), set(film))
                # an ordinary post the film leaves wordless keeps its date; the latest's line repeated their span, so
                # their next line stands in its place
                lines = ["" if r["id"] in film["unsaid"] else ln for r, ln in zip(self.rows, POTTERY_LINES)]
                lines[-1] = "the piece the whole year was aiming at"
                # the peak a type mask sets carries its line as the mask's words
                self.assertEqual([(c["mask"] or " ".join(ln["text"] for ln in c["title"])).lower() for c in film["cards"]], lines)
                self.assertTrue(film["unsaid"] and len(film["unsaid"]) < len(self.rows) / 2, film["unsaid"])
                self.assertEqual({c["kind"] for c in film["cards"] if c["id"] in film["unsaid"]}, {"ordinary"})
                for c, r in zip(film["cards"], self.rows):
                    self.assertFalse({"figure", "label", "phrase"} & set(c), set(c))
                    # their words are printed in ink on the paper under their photograph
                    self.assertTrue(all(ln["color"] == "ink" for ln in c["title"] + c["rest"]))
                    self.assertEqual(c["dateLine"]["text"], compose.cased(drive.short(r["date"]), "text"))

    def test_the_hook_and_the_milestones_carry_their_next_line_and_their_span_is_said_once(self):
        cards = self.boards["reel"]["film"]["cards"]
        rest = {c["id"]: " ".join(ln["text"] for ln in c["rest"]).lower() for c in cards}
        title = {c["id"]: " ".join(ln["text"] for ln in c["title"]).lower() for c in cards}
        self.assertEqual(rest["p01"], "dry clay crumbs all over the studio floor and no idea what i'm doing")
        self.assertEqual(rest["p04"], "lumpy, and i love it")
        # the latest's line is their span, which the closer sets, so the latest says their next line instead
        self.assertEqual((title["p27"], rest["p27"]), ("the piece the whole year was aiming at", ""))
        for f, b in self.boards.items():
            with self.subTest(format=f):
                # the closer sets their span once; an opening that sets words opens on it, and no card repeats it
                opening = b["film"]["timeline"]["beats"][0]["words"]
                self.assertEqual(sum(w.lower().count("fourteen months in") for w in storyboard.words_of(b)), 1 + (opening == "fourteen months in"))
        for c in cards:
            if c["kind"] == "ordinary":
                self.assertEqual(c["rest"], [], c["id"])
            if c["rest"]:
                self.assertLess(c["title_at"], c["rest_at"])
                self.assertLess(c["rest_at"], c["leave"])

    def test_every_line_enters_as_its_print_starts_toward_the_lens_and_has_landed_when_the_camera_arrives(self):
        for f, b in self.boards.items():
            for c in b["film"]["cards"]:
                with self.subTest(format=f, card=c["id"]):
                    self.assertEqual(c["land"], c["arrive"])
                    approach = c["arrive"] - (drive.dive_of(b["bpm"]) if c["kind"] == "hook" else drive.RISE * c["travel"])
                    self.assertGreaterEqual(c["title_at"] + 1e-9, approach)
                    self.assertLess(c["title_at"], c["arrive"])

    def test_every_card_holds_long_enough_to_read_their_line(self):
        assert_readable(self, self.boards["reel"])

    def test_the_closer_sets_their_own_words_for_the_span_over_their_dates(self):
        self.assertEqual(self.fx["said"], "fourteen months in")
        for f, b in self.boards.items():
            cl = b["film"]["closer"]
            with self.subTest(format=f):
                self.assertFalse({"figure", "label"} & set(cl), set(cl))
                self.assertEqual(cl["span"], "fourteen months in")
                self.assertIn("fourteen months in", b["film"]["look"].values())
                self.assertEqual([ln["text"].lower() for ln in cl["lines"] if ln["name"] in ("first", "latest")], ["aug 9, 2025", "oct 14, 2026"])
                # the dates are set as the camera settles on the wall, and the closer shape after it
                self.assertTrue(all(cl["at"] + cl["move"] - 0.25 - 1e-6 <= ln["at"] < cl["shape"] for ln in cl["lines"]))

    def test_the_closers_words_stand_on_the_plain_course_between_the_tiles(self):
        for f, b in self.boards.items():
            cl, course = b["film"]["closer"], b["film"]["course"]
            with self.subTest(format=f):
                for ln in cl["lines"]:
                    face = ln.get("face", "text")
                    self.assertGreaterEqual(ln["y"] - compose.cap(face) * ln["size"], course[1] + drive.GAP, ln["text"])
                    self.assertLessEqual(ln["y"] + compose.descent(face) * ln["size"], course[3] - drive.GAP, ln["text"])
        b = copy.deepcopy(self.boards["reel"])
        b["film"]["closer"]["lines"][0]["y"] = b["film"]["course"][1]
        self.assertTrue(any(x.startswith("course:") for x in self.findings(b)))

    def test_the_storyboard_lists_each_beats_photograph_and_their_line(self):
        b = self.boards["reel"]
        by = {s["beat"]: s for s in b["scenes"]}
        self.assertEqual(by["p04"]["line"].lower(), "the first pot that survived / lumpy, and i love it")
        self.assertEqual(by["p04"]["photo"], Path(self.rows[3]["photo"]).name)
        self.assertEqual(by["hook"]["line"].lower(), "day one / dry clay crumbs all over the studio floor and no idea what i'm doing")
        self.assertEqual(by["p05"]["line"].lower(), "a mug")
        self.assertEqual(by["closer"]["line"], "fourteen months in")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            md = Path(d) / "storyboard.md"
            storyboard.write_md(storyboard.finished(copy.deepcopy(b), self.fx), self.fx, [], md)
            text = md.read_text()
        self.assertIn("| beat | frames | photograph | their line | move | cut into it | the move reveals | it carries across the cut |", text)
        self.assertNotIn("None", text)
        self.assertIn("| p04 |", text)
        self.assertIn("the first pot that survived", text)
        self.assertNotIn("27 posts", text)
        self.assertNotIn("milestones on days", text)
        for cue in b["sound"]:
            self.assertNotIn("count", cue["what"])

    def test_the_square_dates_under_the_type_floor_are_refused(self):
        b = copy.deepcopy(self.boards["square"])
        first = next(ln for ln in b["film"]["closer"]["lines"] if ln["name"] == "first")
        compose.use(STYLE)
        self.assertEqual(first["size"], max(drive.COURSE["square"]["date"], drive.least_size()))
        first["size"] = (drive.TYPE_FLOOR - 1) / compose.cap("text")
        bad = [x for x in self.findings(b) if x.startswith("type:")]
        self.assertEqual(len(bad), 1)
        self.assertIn("aug 9, 2025", bad[0].lower())

    def test_a_line_past_the_safe_lines_is_refused(self):
        b = copy.deepcopy(self.boards["reel"])
        latest = next(ln for ln in b["film"]["closer"]["lines"] if ln["name"] == "latest")
        latest["x"] = 1080
        self.assertTrue(any(x.startswith("safe:") for x in self.findings(b)))

    def test_the_closer_ends_on_their_handle_and_asks_only_what_they_asked_for(self):
        for f, b in self.boards.items():
            with self.subTest(format=f):
                cl = b["film"]["closer"]
                self.assertEqual([ln["name"] for ln in cl["lines"]], ["first", "latest"])
                # with no ask, the closer shape signs off on their handle
                self.assertIn(WHO["handle"], b["film"]["look"].values())
                self.assertNotIn("share yours", storyboard.words_of(b))
                # the picture and the music stop after the closer shape, and the held picture after it is the longest hold
                self.assertLess(cl["shape"], cl["still"])
                self.assertGreaterEqual((cl["end"] - cl["still"]) * 60 / b["bpm"] + 1e-6, drive.HOLD[0])
        fx = self.fx | {"call_to_action": "follow for part two"}
        for f in compose.FORMATS:
            b = compose.board(STYLE, self.rows, fx, WHO, f)
            with self.subTest(format=f, call="follow for part two"):
                self.assertEqual(b["film"]["closer"]["lines"][-1]["text"].lower(), "follow for part two")
                self.assertIn("follow for part two", b["film"]["look"].values())
                self.assertEqual(storyboard.check_board(b, self.rows, fx), [])

    def test_a_late_first_event_is_refused(self):
        b = copy.deepcopy(self.boards["reel"])
        b["film"]["opening"] = 0.0
        b["film"]["cards"][0]["arrive"] = 3.0
        self.assertTrue(any(x.startswith("beats:") for x in self.findings(b)))

    def test_every_card_holds_still_under_the_camera_and_the_whole_film_runs_at_most_a_minute(self):
        held = [c["leave"] - c["arrive"] for c in self.boards["reel"]["film"]["cards"]]
        self.assertGreaterEqual(min(held), drive.HELD - 1e-6)
        self.assertLessEqual(sum(bt["frames"] for bt in self.boards["reel"]["beats"]) / compose.FPS, drive.LONGEST)

    def test_a_slower_look_leaves_ordinary_posts_out_so_its_film_runs_inside_a_minute(self):
        c = compose.card("cinematic-letterbox")
        compose.use(c["id"])
        bpm = compose.bpm_of(c)
        kept, passed = drive.fitting(self.rows, self.fx["said"], c, bpm)
        self.assertTrue(passed)
        self.assertLessEqual(drive.lengths_for(kept, self.fx["said"], c, bpm)[0], drive.LONGEST)
        keep = [r["id"] for r in self.rows if r["milestone"]] + [self.rows[0]["id"], self.rows[-1]["id"]]
        self.assertFalse(set(keep) & set(passed), passed)
        b = compose.board(c["id"], kept, self.fx, WHO, "reel")
        self.assertLessEqual(sum(bt["frames"] for bt in b["beats"]) / compose.FPS, drive.LONGEST + 0.05)
        self.assertEqual(storyboard.check_board(b, kept, self.fx), [])

    def test_every_beat_has_its_sound_and_the_stop_ends_the_picture(self):
        b = self.boards["reel"]
        s = qa.sound_of(b)
        cl = b["film"]["closer"]
        self.assertEqual(s["stop"], round(cl["still"] * 60 / b["bpm"], 2))
        self.assertLessEqual(s["last"], s["stop"])
        beats = {c["beat"] for c in b["sound"]}
        self.assertLessEqual({bt["id"] for bt in b["beats"]}, beats)
        lands = {c["beat"] for c in b["sound"] if c["kind"] in ("hit", "impact")}
        self.assertEqual(lands, {bt["id"] for bt in b["beats"]})
        self.assertEqual(sum(bt["frames"] for bt in b["beats"]), round(cl["end"] * b["film"]["pulse"]))

    def test_every_beat_says_what_it_reveals_and_carries(self):
        b = self.boards["reel"]
        self.assertEqual([s["beat"] for s in b["scenes"]], [bt["id"] for bt in b["beats"]])
        for s in b["scenes"]:
            self.assertTrue(s["reveals"] and s["carries"], s)

    def test_six_shots_ask_for_the_hooks_world_the_stills_brought_to_life_and_the_texture_between_chapters(self):
        b = self.boards["reel"]
        kinds = {c["id"]: c["kind"] for c in b["film"]["cards"]}
        self.assertEqual([(c["beat"], c["role"]) for c in b["clips"]],
                         [("hook", "the hook's world"), ("p04", "a still brought to life"), ("p08", "texture between chapters"),
                          ("p22", "a still brought to life"), ("p23", "texture between chapters"), ("p27", "a still brought to life")])
        self.assertEqual(b["film"]["cards"][b["film"]["peak"]]["id"], "p22")
        self.assertEqual({kinds[c["beat"]] for c in b["clips"] if c["role"] == "texture between chapters"}, {"ordinary"})
        for c in b["clips"]:
            with self.subTest(clip=c["id"]):
                self.assertTrue(c["lens"] and c["light"] and c["move"] and c["loop"] and c["stand_in"] and c["seconds"] > 0)
                for part in (c["lens"], c["light"], c["move"], f"{c['seconds']} s", "loops seamlessly"):
                    self.assertIn(part, c["prompt"])
        # one shot per prompt: no two shots share a lens, a light, a move or a prompt
        for key in ("lens", "light", "move", "prompt"):
            self.assertEqual(len({c[key] for c in b["clips"]}), len(b["clips"]), key)

    def test_the_stills_are_inside_the_film(self):
        b = self.boards["reel"]
        total = sum(bt["frames"] for bt in b["beats"])
        self.assertEqual(set(b["stills"]), {"hook", "ordinary", "dense", "closer", "end"})
        for k, v in b["stills"].items():
            self.assertTrue(0 <= v < total, k)

    def test_layout_is_solved_per_format_never_scaled(self):
        reel, land = self.boards["reel"], self.boards["landscape"]
        self.assertEqual((land["format"]["width"], land["format"]["height"]), (1920, 1080))
        self.assertEqual([bt["frames"] for bt in reel["beats"]], [bt["frames"] for bt in land["beats"]])
        self.assertNotEqual(reel["film"]["course"], land["film"]["course"])
        self.assertNotEqual([c["tile"] for c in reel["film"]["cards"]], [c["tile"] for c in land["film"]["cards"]])


class Words(unittest.TestCase):
    """Their words on the cards are the curated moments in taste.json, matched by photograph; a card without a curated
    line is wordless, and the type sits on the photograph's quiet side."""

    DATES = ["2025-03-01", "2025-03-20", "2025-04-12", "2025-05-02", "2025-05-30", "2025-06-21", "2025-07-15", "2025-08-09"]
    CAPTIONS = ["first walk along the river. cold and grey", "ran 5.5 km. new record", "met @maren.okafor at the studio, finally",
                "milestone: finally 1000 followers! thank you all", "the hill path", "longest loop so far", "a slow sunday",
                "latest: the whole route, start to finish"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)

    def boards(self, rows, fx):
        return {f: compose.board(STYLE, rows, fx, WHO, f) for f in compose.FORMATS}

    def assert_clean(self, boards, rows, fx):
        for f, b in boards.items():
            with self.subTest(format=f):
                self.assertEqual(storyboard.check_board(copy.deepcopy(b), rows, fx), [])

    def test_a_sentence_ends_only_at_a_stop_before_a_space_or_the_end(self):
        self.assertEqual(research.lines_of("ran 5.5 km. new record", True), ("ran 5.5 km", "new record"))
        self.assertEqual(research.lines_of("met @maren.okafor at the studio, finally", True), ("met @maren.okafor at the studio", "finally"))
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name)
        cards = compose.board(STYLE, rows, fx, WHO, "reel")["film"]["cards"]
        self.assertEqual([" ".join(ln["text"] for ln in c["title"]).lower() for c in cards[:3]],
                         ["first walk along the river", "ran 5.5 km", "met @maren.okafor at the studio"])
        self.assertEqual(" ".join(ln["text"] for ln in cards[0]["rest"]).lower(), "cold and grey")

    def test_a_card_shows_the_moment_curated_for_its_photograph_and_a_figure_alone_is_wordless(self):
        def curate(m):
            if m["date"] == "2025-05-02":
                m["line"], m["next"] = "", ""
            if m["date"] == "2025-05-30":
                m["line"] = "up the hill path at last"
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name, curate)
        boards = self.boards(rows, fx)
        self.assert_clean(boards, rows, fx)
        self.assertNotIn("1000", storyboard.allowed_numbers(fx, rows))
        cards = {c["id"]: c for c in boards["reel"]["film"]["cards"]}
        self.assertEqual(cards["p04"]["kind"], "milestone")
        self.assertEqual((cards["p04"]["title"], cards["p04"]["rest"]), ([], []))
        self.assertEqual(" ".join(ln["text"] for ln in cards["p05"]["title"]).lower(), "up the hill path at last")
        for b in boards.values():
            self.assertFalse(any("1000" in w for w in storyboard.words_of(b)))

    def test_a_moment_finds_its_photograph_by_its_path_in_any_order(self):
        posts, _ = storyboard.dated(posts_of(self.DATES, self.CAPTIONS, self.tmp.name))
        moments = [{"photo": p["photo"], "line": f"moment {p['id']}", "next": ""} for p in reversed(posts)]
        storyboard.told(posts, moments)
        self.assertEqual([p["line"] for p in posts], [f"moment p{i:02d}" for i in range(1, 9)])
        stranger = {"photo": str(Path(self.tmp.name) / "elsewhere" / "s01.jpg"), "line": "not theirs", "next": ""}
        storyboard.told(posts, [stranger])
        self.assertEqual({p["line"] for p in posts}, {""})

    def test_a_wordless_hook_milestone_and_latest_build_clean_and_the_closer_sets_nothing_before_the_wall_settles(self):
        def curate(m):
            if m["chapter"]:
                m["line"], m["next"] = "", ""
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name, curate)
        boards = self.boards(rows, fx)
        self.assert_clean(boards, rows, fx)
        for f, b in boards.items():
            film = b["film"]
            with self.subTest(format=f):
                for c in film["cards"]:
                    if c["kind"] != "ordinary":
                        self.assertEqual((c["title"], c["rest"]), ([], []), c["id"])
                cl = film["closer"]
                self.assertTrue(all(ln["at"] >= cl["at"] + cl["move"] - 0.25 - 1e-6 for ln in cl["lines"]))
                self.assertFalse(any(c["beat"] == "hook" and c["kind"] == "riser" for c in b["sound"]))
                assert_readable(self, b)

    def test_a_long_single_clause_opener_holds_until_it_is_read(self):
        opener = "the first time i laced up and went out the door without knowing how far i would get or whether i would come back walking"
        rows, fx, _ = build(self.DATES, [opener] + self.CAPTIONS[1:], self.tmp.name)
        self.assertEqual(rows[0]["next"], "")
        b = compose.board(STYLE, rows, fx, WHO, "reel")
        hook = b["film"]["cards"][0]
        self.assertEqual(" ".join(ln["text"] for ln in hook["title"]).lower(), opener)
        self.assertGreaterEqual((hook["leave"] - hook["land"]) * 60 / b["bpm"] + 1e-6, 0.3 + 0.12 * len(opener.split()))
        assert_readable(self, b)
        self.assertEqual(storyboard.check_board(b, rows, fx), [])

    def test_a_long_word_shrinks_until_its_line_fits(self):
        word = "handthrownstonewareextravaganza"
        compose.use(STYLE)
        lines, size = drive.fit(word, 132, "display", 600, 3)
        self.assertEqual(lines, [compose.cased(word)])
        self.assertLessEqual(compose.width(word, size, "display"), 600)
        rows, fx, _ = build(self.DATES, [f"{word}. finally"] + self.CAPTIONS[1:], self.tmp.name)
        self.assert_clean(self.boards(rows, fx), rows, fx)

    def test_without_their_own_words_for_the_span_the_closer_carries_their_two_dates(self):
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name)
        self.assertEqual(fx["said"], "")
        boards = self.boards(rows, fx)
        self.assert_clean(boards, rows, fx)
        for f, b in boards.items():
            cl = b["film"]["closer"]
            with self.subTest(format=f):
                self.assertEqual(cl["span"], "mar 1, 2025 – aug 9, 2025")
                self.assertIn("mar 1, 2025 – aug 9, 2025", b["film"]["look"].values())
                self.assertFalse({"first", "latest"} & {ln["name"] for ln in cl["lines"]})
                self.assertFalse(any("month" in w for w in storyboard.words_of(b)))
        md = Path(self.tmp.name) / "storyboard.md"
        storyboard.write_md(storyboard.finished(copy.deepcopy(boards["reel"]), fx), fx, [], md)
        self.assertIn("From 2025-03-01 to 2025-08-09", md.read_text())
        self.assertNotIn("days", md.read_text().split("## Sound cues")[0])
        self.assertNotIn("month", md.read_text().split("## Sound cues")[0].split("\n", 4)[4])

    def test_their_words_sit_on_the_paper_of_their_print_and_never_on_its_photograph(self):
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name)
        boards = self.boards(rows, fx)
        self.assert_clean(boards, rows, fx)
        for f, b in boards.items():
            compose.use(STYLE)
            for c in b["film"]["cards"]:
                with self.subTest(format=f, card=c["id"]):
                    for ln in [c["dateLine"]] + c["title"] + c["rest"]:
                        face = ln.get("face", "display" if ln in c["title"] else "text")
                        top, foot = ln["y"] - compose.cap(face) * ln["size"], ln["y"] + compose.descent(face) * ln["size"]
                        self.assertTrue(top >= c["photo"][3] - 1e-6 or foot <= c["photo"][1] + 1e-6, ln["text"])
                        self.assertTrue(c["rect"][1] <= top and foot <= c["rect"][3], ln["text"])
        b = copy.deepcopy(boards["reel"])
        c = next(c for c in b["film"]["cards"] if c["title"])
        c["title"][0]["y"] = (c["photo"][1] + c["photo"][3]) / 2
        self.assertTrue(any(x.startswith("over:") and c["id"] in x for x in storyboard.check_board(b, rows, fx)))


class Length(unittest.TestCase):
    """The reel runs the length the person asked for when the set can be made well at it, every card holding as long
    as its photograph carries; an ask outside the set's range is made at its nearest end, with one plain line that says
    the length made and why."""

    DATES = Words.DATES
    CAPTIONS = Words.CAPTIONS

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)

    def seconds(self, b):
        return sum(bt["frames"] for bt in b["beats"]) / compose.FPS

    def range(self, rows, said, seed=""):
        """The shortest and longest film these rows make in STYLE at the tempo its music plays for the run `seed`."""
        c = compose.card(STYLE)
        compose.use(STYLE)
        return drive.lengths_for(rows, said, c, compose.bpm_of(c, seed))

    def test_the_reel_runs_the_length_asked_anywhere_in_its_range(self):
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name)
        lo, hi = self.range(rows, fx["said"])
        # at its least, each photograph is on screen four seconds at most, closer included
        self.assertLess(lo, 4 * len(rows))
        self.assertGreater(hi, 30)
        self.assertLessEqual(hi, drive.LONGEST)
        for ask in (lo, 30, 40, hi):
            with self.subTest(ask=ask):
                for f in compose.FORMATS:
                    b = compose.board(STYLE, rows, fx | {"seconds": ask}, WHO, f)
                    self.assertLess(abs(self.seconds(b) - ask), 0.5, f)
                    self.assertEqual(storyboard.check_board(b, rows, fx), [])
                    assert_readable(self, b)

    def test_a_hold_follows_what_its_photograph_carries(self):
        rows, fx, _ = build(self.DATES, self.CAPTIONS, self.tmp.name)
        flat = {"light": [[0.5] * 12 for _ in range(20)], "busy": [[0.03] * 12 for _ in range(20)]}
        detailed = {"light": [[0.2 + 0.6 * ((r + c) % 2) for c in range(12)] for r in range(20)], "busy": [[0.12] * 12 for _ in range(20)]}
        for r in rows:
            r["look"], r["line"], r["next"], r["milestone"] = copy.deepcopy(flat), "", "", False
        rows[5]["look"] = detailed
        rows[2]["line"] = rows[6]["line"] = "the hill path"
        rows[3]["line"] = "the hill path in the rain with the whole club behind me"
        b = compose.board(STYLE, rows, fx | {"seconds": 40}, WHO, "reel")
        held = {c["id"]: c["leave"] - c["arrive"] for c in b["film"]["cards"]}
        # p02 repeats day one; p06 is a new, wide, detailed scene; p07 comes back to the flat one
        self.assertLess(held["p02"], held["p06"])
        self.assertLess(held["p07"], held["p06"])
        self.assertLess(held["p03"], held["p04"])
        self.assertTrue(any(abs(x * 4 - round(x * 4)) > 1e-3 for x in held.values()), held)

    def draft(self, seconds):
        self.addCleanup(setattr, _env, "B", _env.B)
        _env.B = Path(tempfile.mkdtemp(dir=self.tmp.name))
        folder = _env.b("in")
        folder.mkdir(parents=True)
        _env.write_json(_env.b("subject.json"), {"subject": "running", "posts": posts_of(self.DATES, self.CAPTIONS, folder)})
        _env.b("taste.md").write_text("# taste\n")
        moments = research.moments(_env.read_json(_env.b("subject.json"))["posts"])
        _env.write_json(_env.b("taste.json"), {"moments": moments, "seconds": seconds})
        _env.write_json(_env.b("library.json"), {"handle": "maren"})
        import contextlib
        import io
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            code = storyboard.cmd_draft(argparse.Namespace())
        return code, said.getvalue()

    def drafted(self, ask):
        """Draft with `ask` seconds asked: the exit code, what draft printed, the board, the range these photographs
        make and the film's length in seconds."""
        code, said = self.draft(ask)
        b = _env.read_json(_env.b("storyboards", STYLE, "storyboard.json"))
        return code, said, b, self.range(storyboard.measured(), "", _env.b().name), self.seconds(b) if b else None

    def test_an_ask_above_the_range_makes_the_longest_film_and_says_why(self):
        code, said, b, (lo, hi), secs = self.drafted(200)
        self.assertEqual(code, 0, said)
        self.assertEqual(b["facts"]["seconds"], hi)
        self.assertLess(abs(secs - hi), 0.5)
        line = f"You asked for 200 s; these 8 photographs carry at most {secs:.1f} s, so the film is {secs:.1f} s."
        self.assertIn(line, said.splitlines())
        import deliver
        md = deliver.brief({}, {"seconds": 200}, {}, b, {"board": STYLE, "totals": {}}, {"seconds": round(secs, 3)}, {}, {}, {}, [])
        self.assertIn(f"- {line}", md.splitlines())

    def test_an_ask_below_the_range_makes_the_shortest_film_and_says_why(self):
        code, said, b, (lo, hi), secs = self.drafted(4)
        self.assertEqual(code, 0, said)
        self.assertEqual(b["facts"]["seconds"], lo)
        self.assertLess(abs(secs - lo), 0.5)
        self.assertIn(f"You asked for 4 s; these 8 photographs need at least {secs:.1f} s to be seen and their words read, "
                      f"so the film is {secs:.1f} s.", said.splitlines())
        assert_readable(self, b)

    def test_with_no_ask_the_film_runs_at_its_own_pace_and_says_nothing_of_an_ask(self):
        code, said, b, (lo, hi), secs = self.drafted(None)
        self.assertEqual(code, 0, said)
        self.assertIsNone(b["facts"]["seconds"])
        self.assertTrue(lo <= secs <= hi + 0.1, (lo, secs, hi))
        self.assertNotIn("asked", said)
        import deliver
        md = deliver.brief({}, {"seconds": None}, {}, b, {"board": STYLE, "totals": {}}, {"seconds": round(secs, 3)}, {}, {}, {}, [])
        self.assertNotIn("asked", md)

    def test_an_ask_inside_the_range_drafts_a_board_of_that_length(self):
        code, said = self.draft(30)
        self.assertIn("30.0 s", said)
        b = _env.read_json(_env.b("storyboards", STYLE, "storyboard.json"))
        self.assertLess(abs(self.seconds(b) - 30), 0.5)
        self.assertEqual(b["facts"]["seconds"], 30)


class Photographs(unittest.TestCase):
    """framing.py's copies: the station copy covers the reel's frame at a station and is never enlarged; the tile copy
    is TILE px on its long side at most."""

    def test_a_large_photograph_is_cut_down_to_cover_the_station_and_a_small_one_is_never_enlarged(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            big = Path(d) / "big.jpg"
            Image.new("RGB", (4000, 3000), (120, 90, 60)).save(big)
            small = Path(d) / "small.jpg"
            Image.new("RGB", (900, 1400), (120, 90, 60)).save(small)
            posts = [{"id": "p01", "date": "2026-01-01", "photo": str(big)}, {"id": "p02", "date": "2026-02-01", "photo": str(small)}]
            rows = framing.frame(posts, Path(d) / "public")["posts"]
            pub = Path(d) / "public"

            def size(f):
                with Image.open(pub / f) as im:
                    return im.size
            w, h = size(rows[0]["photo"])
            self.assertTrue(w >= framing.STATION[0] and h >= framing.STATION[1] and w < 4000, (w, h))
            self.assertEqual(size(rows[1]["photo"]), (900, 1400))
            self.assertEqual(max(size(rows[0]["tile"])), framing.TILE)
            self.assertEqual(size(rows[1]["tile"]), (514, 800))

    def test_every_photograph_day_one_included_takes_the_one_grade_of_the_set(self):
        from PIL import Image, ImageStat
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            posts = []
            for i, rgb in enumerate([(52, 44, 38), (150, 140, 128), (160, 150, 140), (148, 136, 126)], 1):
                p = Path(d) / f"s{i}.jpg"
                noise = Image.effect_noise((900, 1200), 30).convert("RGB")
                Image.blend(Image.new("RGB", (900, 1200), rgb), noise, 0.1).save(p)
                posts.append({"id": f"p{i:02d}", "date": f"2026-0{i}-01", "photo": str(p)})
            rows = framing.frame(posts, Path(d) / "public")["posts"]
            pub = Path(d) / "public"

            def light(f):
                with Image.open(f) as im:
                    return ImageStat.Stat(im.convert("L")).mean[0]
            before = [light(p["photo"]) for p in posts]
            tiles = [light(pub / r["tile"]) for r in rows]
            photos = [light(pub / r["photo"]) for r in rows]
            # day one comes up toward the set's light, the photographs already near it barely move, and the tile and
            # the station copy of each photograph carry the same grade
            self.assertGreater(tiles[0], before[0] + 20)
            for k in (1, 2, 3):
                self.assertLess(abs(tiles[k] - before[k]), 6)
            self.assertLess(max(tiles) - min(tiles), (max(before) - min(before)) * 0.75)
            for t, p in zip(tiles, photos):
                self.assertLess(abs(t - p), 2)


class Short(unittest.TestCase):
    """Sets at the edge: two posts three weeks apart, a few posts, one post, posts without a date."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_posts_build_clean_and_show_no_months(self):
        rows, fx, _ = build(["2026-03-01", "2026-03-22"], ["first bowl #pottery", "a better bowl #pottery"], self.tmp.name)
        self.assertEqual((fx["days"], fx["months"], fx["count"]), (21, None, 2))
        for f in compose.FORMATS:
            b = compose.board(STYLE, rows, fx, WHO, f)
            with self.subTest(format=f):
                self.assertEqual(storyboard.check_board(b, rows, fx), [])
                self.assertFalse(any("months" in w for w in storyboard.words_of(b)))

    def test_three_and_four_posts_set_the_closers_words_inside_the_safe_lines(self):
        for n in (3, 4):
            dates = [(date(2026, 1, 5) + timedelta(days=50 * i)).isoformat() for i in range(n)]
            rows, fx, _ = build(dates, [f"the garden, week {i * 7} #garden" for i in range(n)], self.tmp.name)
            for f in compose.FORMATS:
                b = compose.board(STYLE, rows, fx, WHO, f)
                with self.subTest(posts=n, format=f):
                    self.assertEqual(storyboard.check_board(b, rows, fx), [])
                    top, bottom = drive.COURSE[f]["words"]
                    for ln in b["film"]["closer"]["lines"]:
                        face = ln.get("face", "text")
                        self.assertGreaterEqual(ln["y"] - compose.cap(face) * ln["size"], top, ln["text"])
                        self.assertLessEqual(ln["y"] + compose.descent(face) * ln["size"], bottom, ln["text"])

    def test_six_posts_without_captions_or_handle_build_clean(self):
        dates = [(date(2025, 1, 5) + timedelta(days=40 * i)).isoformat() for i in range(6)]
        rows, fx, _ = build(dates, [""] * 6, self.tmp.name)
        self.assertEqual(sum(1 for r in rows if r["milestone"]), 3)
        for f in compose.FORMATS:
            b = compose.board(STYLE, rows, fx, {"name": "", "handle": ""}, f)
            with self.subTest(format=f):
                self.assertEqual(storyboard.check_board(b, rows, fx), [])
                self.assertFalse(any(ln["name"] == "handle" for ln in b["film"]["closer"]["lines"]))

    def test_one_post_is_no_before_and_after(self):
        posts, _ = storyboard.dated([{"id": "p01", "date": "2026-01-01", "caption": "", "milestone": False, "day": 1}])
        with self.assertRaises(storyboard.Refusal):
            storyboard.facts(posts)

    def test_posts_without_dates_are_left_out(self):
        have, left = storyboard.dated([{"id": "a", "date": "2026-02-01"}, {"id": "b", "date": None}, {"id": "c", "date": "2026-01-01"}, {"id": "d"}])
        self.assertEqual([p["id"] for p in have], ["c", "a"])
        self.assertEqual([p["id"] for p in left], ["b", "d"])
        with self.assertRaises(storyboard.Refusal):
            storyboard.facts([])

    def test_every_post_on_one_day_is_no_before_and_after(self):
        rows = [{"date": "2026-01-01", "day": 1, "milestone": False}] * 3
        with self.assertRaises(storyboard.Refusal):
            storyboard.facts(rows)


class Vote(unittest.TestCase):
    """The film is cut only from a board that won the vote, and a board drafted again is voted again."""

    def setUp(self):
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.addCleanup(setattr, _env, "B", _env.B)
        _env.B = d

    def test_snap_cuts_only_a_board_that_won_the_vote(self):
        with self.assertRaises(SystemExit) as e:
            storyboard.cmd_snap(argparse.Namespace())
        self.assertIn("vote.py tally", str(e.exception.code))
        argv = sys.argv
        self.addCleanup(setattr, sys, "argv", argv)
        sys.argv = ["storyboard.py", "snap", "--board", STYLE]
        with self.assertRaises(SystemExit) as e:
            storyboard.main()
        self.assertEqual(e.exception.code, 2)
        self.assertFalse(_env.b("film.json").exists())

    def test_a_new_draft_starts_a_new_vote(self):
        _env.write_json(_env.b("winner.json"), {"board": STYLE})
        _env.write_json(_env.b("vote", "scores.json"), {})
        with self.assertRaises(SystemExit):
            storyboard.cmd_draft(argparse.Namespace())
        self.assertFalse(_env.b("winner.json").exists())
        self.assertFalse(_env.b("vote", "scores.json").exists())

    def test_a_new_draft_drops_the_cut_and_the_check_of_the_old_board(self):
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        _env.write_json(_env.b("storyboards", "check.json"), {STYLE: {"reel": []}})
        with self.assertRaises(SystemExit):
            storyboard.cmd_draft(argparse.Namespace())
        self.assertFalse(_env.b("film.json").exists())
        self.assertFalse(_env.b("storyboards", "check.json").exists())

    def test_a_new_draft_drops_the_sheet_and_the_styleframes_of_the_old_board(self):
        for f in ("sheet.png", "frames/hook.png"):
            p = _env.b("storyboards", STYLE, f)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"the old board")
        with self.assertRaises(SystemExit):
            storyboard.cmd_draft(argparse.Namespace())
        self.assertFalse(_env.b("storyboards", STYLE, "sheet.png").exists())
        self.assertFalse(_env.b("storyboards", STYLE, "frames").exists())

    def test_a_sheets_killed_while_it_renders_leaves_no_sheet_and_the_ballot_refuses(self):
        import film
        _env.write_json(_env.b("storyboards", STYLE, "storyboard.json"), {"style": STYLE, "stills": {"hook": 0}})
        _env.b("storyboards", STYLE, "sheet.png").write_bytes(b"the sheet of the last styleframes")
        saved = {k: getattr(film, k) for k in ("props", "render_jobs")}
        self.addCleanup(lambda: [setattr(film, k, v) for k, v in saved.items()])
        film.props = lambda b: {}

        def killed(run, jobs):
            raise KeyboardInterrupt
        film.render_jobs = killed
        with self.assertRaises(KeyboardInterrupt):
            storyboard.cmd_sheets(argparse.Namespace())
        self.assertFalse(_env.b("storyboards", STYLE, "sheet.png").exists())
        with self.assertRaises(SystemExit) as e:
            vote.cmd_ballot(argparse.Namespace())
        self.assertIn("storyboard.py sheets", str(e.exception.code))

    def test_the_cut_round_is_reused_until_the_reel_changes(self):
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        _env.write_json(_env.b("render", "report.json"), {"failed": 0})
        _env.cut().mkdir(parents=True)
        _env.cut("film.mp4").write_bytes(b"the first reel")
        checked = lambda: _env.write_json(_env.b("qa", "check.json"), {"film": vote.digest(_env.cut("film.mp4"))})
        checked()
        self.assertEqual(vote.cmd_cut(argparse.Namespace()), 0)
        filled = _env.read_json(_env.b("critic", f"cut-{STYLE}-1.json")) | {"fixed": "half a score"}
        _env.write_json(_env.b("critic", f"cut-{STYLE}-1.json"), filled)
        self.assertEqual(vote.cmd_cut(argparse.Namespace()), 0)
        self.assertEqual([p.name for p in vote.rounds()], [f"cut-{STYLE}-1.json"])
        self.assertEqual(_env.read_json(_env.b("critic", f"cut-{STYLE}-1.json")), filled)
        _env.cut("film.mp4").write_bytes(b"the reel after the one fix")
        # the critic reads the new cut's checks, so its round waits for them
        with self.assertRaises(SystemExit) as e:
            vote.cmd_cut(argparse.Namespace())
        self.assertIn("run qa.py check", str(e.exception.code))
        checked()
        self.assertEqual(vote.cmd_cut(argparse.Namespace()), 0)
        self.assertEqual([p.name for p in vote.rounds()], [f"cut-{STYLE}-1.json", f"cut-{STYLE}-2.json"])

    def half_written(self, *names):
        """Path.write_text that writes half of its text to a file whose name holds one of `names`, then is killed."""
        real = Path.write_text
        self.addCleanup(setattr, Path, "write_text", real)

        def half(path, text, *a, **k):
            if any(n in path.name for n in names):
                real(path, text[:len(text) // 2])
                raise KeyboardInterrupt
            return real(path, text, *a, **k)
        Path.write_text = half

    def a_set(self, n=2):
        folder = _env.b("in")
        folder.mkdir(parents=True, exist_ok=True)
        dates = [(date(2026, 1, 1) + timedelta(days=30 * i)).isoformat() for i in range(n)]
        _env.write_json(_env.b("subject.json"), {"subject": "pottery", "posts": posts_of(dates, ["first bowl"] + [""] * (n - 1), folder)})
        _env.b("taste.md").write_text("# taste\n")
        _env.write_json(_env.b("taste.json"), {"moments": research.moments(_env.read_json(_env.b("subject.json"))["posts"])})
        _env.write_json(_env.b("library.json"), {"handle": "@maren"})

    def test_photographs_framed_again_take_their_measure_and_their_boards_away_first(self):
        import framing
        self.a_set()
        _env.write_json(_env.b("public", "matched", "measure.json"), {"posts": "the last photographs"})
        _env.write_json(_env.b("storyboards", STYLE, "storyboard.json"), {"style": STYLE})
        saved = {k: getattr(m, k) for m, k in ((framing, "framed_plate"), (_env, "open_run"))}
        self.addCleanup(lambda: [setattr(m, k, saved[k]) for m, k in ((framing, "framed_plate"), (_env, "open_run"))])
        _env.open_run = lambda: _env.B

        def killed(im):
            raise KeyboardInterrupt
        framing.framed_plate = killed
        with self.assertRaises(KeyboardInterrupt):
            framing.main()
        self.assertFalse(_env.b("public", "matched", "measure.json").exists())
        self.assertFalse(_env.b("storyboards", STYLE, "storyboard.json").exists())

    def test_a_draft_killed_while_it_writes_a_boards_text_publishes_no_board(self):
        self.a_set()
        self.half_written("storyboard.md", ".storyboard.part.md")
        with self.assertRaises(KeyboardInterrupt):
            storyboard.cmd_draft(argparse.Namespace())
        self.assertEqual(list(_env.b("storyboards").glob("*/storyboard.json")), [])
        self.assertEqual(list(_env.b("storyboards").glob("*/storyboard.md")), [])

    def test_a_ballot_killed_while_it_is_written_keeps_the_last_ballot_whole(self):
        _env.write_json(_env.b("storyboards", STYLE, "storyboard.json"), {"style": STYLE, "id": STYLE, "title": STYLE})
        _env.b("storyboards", STYLE, "sheet.png").write_bytes(b"the sheet")
        _env.b("vote").mkdir()
        _env.b("vote", "ballot.md").write_text("the last ballot")
        self.half_written("ballot")
        with self.assertRaises(KeyboardInterrupt):
            vote.cmd_ballot(argparse.Namespace())
        self.assertEqual(_env.b("vote", "ballot.md").read_text(), "the last ballot")
        self.assertEqual(sorted(p.name for p in _env.b("vote").iterdir()), ["ballot.md"])

    def test_a_tally_killed_while_it_writes_the_vote_keeps_the_last_vote_whole(self):
        _env.write_json(_env.b("storyboards", STYLE, "storyboard.json"), {"style": STYLE})
        data = vote.blank(vote.PANEL, [STYLE], swap=True)
        for c in data["critics"].values():
            e = c["boards"][STYLE]
            e["scores"] = {k: 4 for k in e["scores"]}
            e["paragraph"] = " ".join(["the board holds its photographs"] * 6)
            if "swap" in e:
                e["swap"] = {f: "holds" for f in e["swap"]}
        _env.write_json(_env.b("vote", "scores.json"), data)
        _env.b("vote.md").write_text("the last vote")
        self.half_written("vote.md", ".vote.part.md")
        with self.assertRaises(KeyboardInterrupt):
            vote.cmd_tally(argparse.Namespace())
        self.assertEqual(_env.b("vote.md").read_text(), "the last vote")
        self.assertEqual([p.name for p in _env.B.glob("*vote*") if p.is_file()], ["vote.md"])

    def test_the_cut_refuses_a_reel_whose_render_has_not_finished(self):
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        _env.out().mkdir(parents=True)
        _env.out("film.mp4").write_bytes(b"a reel stopped partway")
        for report in (None, {"failed": 2}):
            if report:
                _env.write_json(_env.b("render", "report.json"), report)
            with self.subTest(report=report):
                with self.assertRaises(SystemExit) as e:
                    vote.cmd_cut(argparse.Namespace())
                self.assertIn("film.py render", str(e.exception.code))
                self.assertEqual(vote.rounds(), [])

    def test_a_tally_that_reaches_no_winner_leaves_none(self):
        _env.write_json(_env.b("storyboards", STYLE, "storyboard.json"), {"style": STYLE})
        _env.write_json(_env.b("winner.json"), {"board": STYLE})
        data = vote.blank(vote.PANEL, [STYLE], swap=True)
        for c in data["critics"].values():
            e = c["boards"][STYLE]
            e["scores"] = {k: 3 for k in e["scores"]}
            e["paragraph"] = " ".join(["the board holds its photographs"] * 6)
            if "swap" in e:
                e["swap"] = {f: "holds" for f in e["swap"]} | {"dense": "swappable"}
        _env.write_json(_env.b("vote", "scores.json"), data)
        self.assertEqual(vote.cmd_tally(argparse.Namespace()), 1)
        self.assertFalse(_env.b("winner.json").exists())
        _env.write_json(_env.b("winner.json"), {"board": STYLE})
        _env.write_json(_env.b("vote", "scores.json"), vote.blank(vote.PANEL, [STYLE], swap=True))
        self.assertEqual(vote.cmd_tally(argparse.Namespace()), 1)
        self.assertFalse(_env.b("winner.json").exists())


class Research(unittest.TestCase):
    """research.py's draft of taste.md: their moments in their own words and dates, never a count of posts."""

    def test_the_you_are_lines_name_the_moments_and_no_post_count(self):
        import research
        sub = {"subject": "pottery", "chosen_by": "named by the person", "steadiness": 0.8,
               "candidates": [{"subject": "pottery", "run_days": 431}, {"subject": "lisbon", "run_days": 60}],
               "first": {"date": "2025-08-09", "caption": "day one. a bag of clay"},
               "milestones": [{"date": "2025-09-18", "why": "their caption says first", "caption": "the first pot that survived"}],
               "latest": {"date": "2026-10-14", "caption": "fourteen months in"},
               "changed": [{"line": "a year ago i couldn't center a lump of clay"}]}
        span = {"first": "2025-08-09", "latest": "2026-10-14", "label": "14 months", "days": 431}
        text = "\n".join(research.you_are(sub, span))
        self.assertIsNone(re.search(r"\d+ posts", text), text)
        for said in ("day one. a bag of clay", "the first pot that survived", "fourteen months in", "a year ago i couldn't center", "14 months"):
            self.assertIn(said, text)


class Subject(unittest.TestCase):
    """timeline.py's named subject: the posts it takes from the feed."""

    def take(self, named, captions):
        _, terms, every = terms_for(named, [])
        return [c for c in captions if matches({"caption": c}, terms, every)]

    def test_a_named_subject_outside_every_group_takes_the_posts_that_name_each_of_its_words(self):
        walks = list(SET_CAPTIONS["lisbon"])
        feed = walks + ["everything is orange in lisbon #travel", "first coffee of the year in lisbon",
                        "back in marrakech with @ines.walks", "dinner with @ines.walks"]
        self.assertEqual(self.take("my lisbon walks", feed), walks)

    def test_a_named_word_group_takes_every_post_of_the_group(self):
        self.assertEqual(self.take("my balcony garden", ["first seedlings up", "the balcony at dusk", "dinner out"]),
                         ["first seedlings up", "the balcony at dusk"])


if __name__ == "__main__":
    unittest.main()
