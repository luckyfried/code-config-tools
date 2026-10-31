"""The three looks, drafted from one person's run (tests/fixture.py): three style cards, each board in every format
inside the rules `storyboard.py check` holds it to, every word on screen one of theirs, each beat's move chosen from
what the beat shows, the question held as long as it takes to read, labels large enough to read, and the story's peak
and the hook's rest named for the cover and the image to post."""
import math
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(HERE))
import compose  # noqa: E402
import fixture  # noqa: E402
import storyboard  # noqa: E402


def drafted(moments=fixture.MOMENTS, **taste):
    """{letter: {fmt: plan}} for the run the fixture makes with `moments` and `taste`."""
    here = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
        fixture.make(d, moments, **taste)
        os.chdir(d)
        try:
            run = storyboard.Run()
            looks = {l: {fmt: storyboard.board_for(run, l, s, fmt) for fmt in compose.FORMATS} for l, s in zip(compose.LETTERS, run.trio)}
            bad = {l: storyboard.findings(run, p) for l, p in looks.items()}
        finally:
            os.chdir(here)
    return run, looks, bad


def on_screen(board):
    """Every word the board sets: its lines, labels, the mask's word and the words set beat by beat."""
    out = []
    for x in board["beats"]:
        t = x.get("text") or {}
        out += [ln["text"] for ln in t.get("lines") or []] + ([t["label"]["text"]] if t.get("label") else [])
        out += [x["words"], x["label"]]
    out += [board["signoff"], board["handle"]]
    return [w for s in out for w in re.findall(r"[a-z0-9']+", (s or "").lower())]


@unittest.skipUnless(fixture.HAVE_PIL, "Pillow is not installed")
class Looks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r, cls.looks, cls.bad = drafted()

    def test_the_three_looks_are_the_three_default_cards(self):
        self.assertEqual([p["reel"]["board"]["style"] for p in self.looks.values()], ["kinetic-type", "editorial-quiet", "swiss-grid"])

    def test_every_board_in_every_format_passes_the_check(self):
        self.assertEqual(self.bad, {"a": [], "b": [], "c": []})
        self.assertEqual(storyboard.style_findings(self.r.trio), [])
        for plans in self.looks.values():
            for p in plans.values():
                self.assertTrue(12 <= p["seconds"] <= 30, p["seconds"])
                self.assertLessEqual(p["hook_frame"], storyboard.HOOK_FRAMES)

    def test_every_word_on_screen_is_theirs(self):
        st = fixture.studio()
        theirs = " ".join([st["bio"], st["name"], st["handle"], *fixture.CAPTIONS, *(m["line"] for m in st["story"]),
                           *(m["pillar"] for m in st["story"])]).lower()
        mine = set(re.findall(r"[a-z0-9']+", theirs))
        for plans in self.looks.values():
            for p in plans.values():
                self.assertEqual(set(on_screen(p["board"])) - mine, set(), p["board"]["id"])

    def test_the_story_runs_hook_moments_ask_closer_with_the_peak_last(self):
        for plans in self.looks.values():
            b = plans["reel"]["board"]
            ids = [x["id"] for x in b["beats"]]
            # a slow look fits fewer moments in the length: the story keeps its order and its peak
            self.assertEqual((ids[0], ids[-3:]), ("hook", ["p04", "ask", "closer"]), b["style"])
            self.assertEqual(ids[1:-2], sorted(ids[1:-2]))
            self.assertGreaterEqual(len(ids), 5)
            self.assertEqual([x["peak"] for x in b["beats"] if x["form"] == "photo"][-1], True)
            self.assertEqual(b["beats"][-2]["say"], "what's in season where you are?")
            self.assertEqual(b["signoff"], "Maren Okafor")

    def test_no_beat_repeats_the_move_before_it(self):
        for plans in self.looks.values():
            moves = [x["move"] for x in plans["reel"]["board"]["beats"]]
            self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), moves)

    def test_the_question_holds_as_long_as_it_takes_to_read(self):
        for plans in self.looks.values():
            b = plans["reel"]["board"]
            ask = next(x for x in b["beats"] if x["id"] == "ask")
            seconds = ask["beats"] * 60 / b["bpm"]
            self.assertTrue(2.2 <= seconds <= 4.0, (b["style"], seconds))

    def test_every_label_reads_at_arm_length(self):
        for plans in self.looks.values():
            for fmt, p in plans.items():
                k = min(compose.PROFILES[fmt]["width"], compose.PROFILES[fmt]["height"]) / 1080
                for x in p["board"]["beats"]:
                    lab = (x.get("text") or {}).get("label")
                    if lab:
                        self.assertGreaterEqual(lab["size"], round(storyboard.LABEL_LEAST * k), (p["board"]["id"], x["id"]))

    def test_a_landscape_photograph_takes_the_cards_landscape_layout_and_its_line_stays_in_its_line_box(self):
        for plans in self.looks.values():
            for fmt, p in plans.items():
                b = p["board"]
                card = compose.card(b["style"])
                compose.use(b["style"])
                fr = compose.Frame(fmt)
                wide = [x for x in b["beats"] if x["form"] == "photo" and x["picture"] and x["picture"]["aspect"] < 1]
                self.assertTrue(wide, b["id"])
                for x in wide:
                    land = card["photo"]["landscape"]
                    self.assertEqual(x["picture"]["box"], storyboard.picture_box(fr, dict(card["photo"]["picture"], box=land["box"])), b["id"])
                    lb = storyboard.line_box(fr, land["line"])
                    tb = x["text"]["box"]
                    self.assertTrue(lb[0] <= tb[0] and lb[1] <= tb[1] and tb[2] <= lb[2] and tb[3] <= lb[3], (b["id"], tb, lb))
                    for bx in storyboard.text_boxes(x["text"]):
                        self.assertTrue(lb[0] - 2 <= bx[0] and bx[2] <= lb[2] + 2 and bx[3] <= lb[3] + 2, (b["id"], bx, lb))

    def test_on_a_frame_as_wide_as_tall_an_upright_photograph_takes_the_box_nearer_its_shape_and_its_line_clears_it(self):
        def shape(box):
            return (box[3] - box[1]) / (box[2] - box[0])
        for plans in self.looks.values():
            for fmt, p in plans.items():
                b = p["board"]
                fr = compose.Frame(fmt)
                if fr.W < fr.H:
                    continue
                card = compose.card(b["style"])
                compose.use(b["style"])
                boxes = [storyboard.picture_box(fr, card["photo"]["picture"]),
                         storyboard.picture_box(fr, dict(card["photo"]["picture"], box=card["photo"]["landscape"]["box"]))]
                for x in b["beats"]:
                    if x["form"] != "photo" or not x["picture"] or x["picture"]["aspect"] < 1:
                        continue
                    a = x["picture"]["aspect"]
                    nearest = min(abs(math.log(shape(bx) / a)) for bx in boxes)
                    self.assertAlmostEqual(abs(math.log(shape(x["picture"]["box"]) / a)), nearest, 6, (b["id"], x["id"]))
                    pb = x["picture"]["box"]
                    if pb[0] > 0 and pb[2] < fr.W:
                        for tb in storyboard.text_boxes(x["text"]):
                            self.assertTrue(tb[3] <= pb[1] + 2 or tb[1] >= pb[3] - 2, (b["id"], x["id"], tb, pb))

    def test_a_flat_or_clean_card_shows_each_photograph_as_posted_and_any_other_under_the_films_grade(self):
        for plans in self.looks.values():
            for p in plans.values():
                b = p["board"]
                posted = compose.card(b["style"])["axes"]["finish"] in storyboard.AS_POSTED
                for x in b["beats"]:
                    if x["picture"]:
                        self.assertEqual(x["picture"]["file"].startswith("studio/posted/"), posted, (b["id"], x["id"]))

    def test_a_line_over_a_rule_drawn_at_the_pictures_head_ends_the_rules_gap_above_it_in_every_format(self):
        seen = 0
        for plans in self.looks.values():
            for fmt, p in plans.items():
                fr = compose.Frame(fmt)
                for x in p["board"]["beats"]:
                    if x["form"] != "photo" or x["move"] not in storyboard.HEADS or not x["picture"] or not x["text"]:
                        continue
                    heavy, gap = storyboard.HEADS[x["move"]]
                    top = x["picture"]["box"][1] - (heavy + gap) * fr.W / 1080
                    for bx in storyboard.text_boxes(x["text"]):
                        self.assertLessEqual(bx[3], top - gap * fr.W / 1080 + 2, (p["board"]["id"], x["id"], bx))
                    seen += 1
        self.assertTrue(seen)

    def test_a_line_under_running_bands_stands_between_them_in_every_format(self):
        seen = 0
        for plans in self.looks.values():
            for fmt, p in plans.items():
                fr = compose.Frame(fmt)
                for x in p["board"]["beats"]:
                    if x["move"] in storyboard.BANDS and x.get("text"):
                        seen += 1
                        (above, below), h = storyboard.BANDS[x["move"]]
                        for bx in storyboard.text_boxes(x["text"]):
                            self.assertGreaterEqual(bx[1], above * fr.H + h * fr.W / 1080, (fmt, x["id"], bx))
                            self.assertLessEqual(bx[3], below * fr.H, (fmt, x["id"], bx))
        self.assertTrue(seen)

    def test_an_opening_line_in_a_window_of_the_ground_stands_inside_the_window_in_every_format(self):
        seen = 0
        for plans in self.looks.values():
            for fmt, p in plans.items():
                fr = compose.Frame(fmt)
                for x in p["board"]["beats"]:
                    if x["move"] in storyboard.WINDOWS and x.get("text"):
                        seen += 1
                        top, foot = storyboard.WINDOWS[x["move"]]
                        for bx in storyboard.text_boxes(x["text"]):
                            self.assertGreaterEqual(bx[1], top * fr.H, (fmt, x["id"], bx))
                            self.assertLessEqual(bx[3], (1 - foot) * fr.H, (fmt, x["id"], bx))
        self.assertTrue(seen)

    def test_every_beat_plays_a_move_made_for_its_form_where_the_card_has_one(self):
        # the swiss grid's one words move is rule-draw, which its photo moments use too
        for plans in self.looks.values():
            b = plans["reel"]["board"]
            moves = {o["id"]: o["fits"] for o in compose.card(b["style"])["moves"]}
            for x in b["beats"]:
                if any(x["form"] in fits for fits in moves.values()):
                    self.assertIn(x["form"], moves[x["move"]], (b["style"], x["id"], x["move"]))
                if x["form"] == "words":
                    # the question is on screen from its first frame: the kit sets it, or the move is handed it
                    self.assertTrue(x["text"] or x["words"], (b["style"], x["move"]))

    def test_no_line_of_a_beat_crosses_another_or_its_label_in_any_format(self):
        for plans in self.looks.values():
            for fmt, p in plans.items():
                for x in p["board"]["beats"]:
                    bs = storyboard.text_boxes(x.get("text"))
                    for i, u in enumerate(bs):
                        for v in bs[i + 1:]:
                            cross = min(u[2], v[2]) > max(u[0], v[0]) and min(u[3], v[3]) > max(u[1], v[1])
                            self.assertFalse(cross, (p["board"]["style"], fmt, x["id"], u, v))

    def test_a_question_the_move_would_size_by_width_alone_is_set_by_the_kit_on_a_wide_frame(self):
        b = self.looks["c"]["wide"]["board"]
        ask = next(x for x in b["beats"] if x["form"] == "words")
        self.assertIn(ask["move"], storyboard.WIDTH_SIZED)
        self.assertEqual(ask["words"], "")
        self.assertEqual(ask["text"]["at"], 0)
        a = compose.Frame("wide").area
        self.assertTrue(all(bx[3] <= a[3] for bx in storyboard.text_boxes(ask["text"])))
        self.assertTrue(next(x for x in self.looks["c"]["reel"]["board"]["beats"] if x["form"] == "words")["words"])

    def test_a_label_over_a_scrimmed_photograph_takes_the_lines_color_where_its_own_would_not_read(self):
        # kinetic type's label is its ink, near black; the fixture's photographs are dark under the scrim
        b = self.looks["a"]["reel"]["board"]
        labels = [(x["text"]["label"]["color"], x["text"]["color"]) for x in b["beats"]
                  if x["form"] == "photo" and x.get("scrim") and x["text"].get("label")]
        self.assertTrue(labels)
        self.assertTrue(all(lab == line for lab, line in labels), labels)

    def test_the_rests_name_the_hook_and_the_peak_inside_their_beats(self):
        for plans in self.looks.values():
            p = plans["square"]
            b, pulse = p["board"], p["board"]["beats"][0]["pulse"]
            peak = next(x for x in b["beats"] if x["peak"])
            start = round(peak["start"] * pulse)
            self.assertTrue(start <= p["rests"]["peak"] < start + peak["frames"])
            self.assertLess(p["rests"]["hook"], b["beats"][0]["frames"])

    def test_every_sound_cue_is_inside_the_film_and_only_a_cut_look_stops(self):
        for plans in self.looks.values():
            p = plans["reel"]
            b = p["board"]
            self.assertTrue(all(0 <= q["frame"] < p["frames"] for q in b["sound"]))
            stops = [q for q in b["sound"] if q["kind"] == "stop"]
            self.assertEqual(bool(stops), compose.card(b["style"])["axes"]["transition"] == "cut")
            self.assertLessEqual(b["closer"]["still"] * b["beats"][0]["pulse"], p["frames"])


@unittest.skipUnless(fixture.HAVE_PIL, "Pillow is not installed")
class Story(unittest.TestCase):
    def test_a_named_style_leads_beside_the_two_defaults_that_differ_most(self):
        run, looks, bad = drafted(style="scrapbook")
        self.assertEqual(run.trio[0], "scrapbook")
        self.assertEqual(len(set(run.trio)), 3)
        self.assertEqual(storyboard.style_findings(run.trio), [])

    def test_their_own_words_win_over_the_drafted_ones(self):
        run, looks, _ = drafted(hook="a month at my table", question="what are you cooking", signoff="see you tuesday")
        b = looks["b"]["reel"]["board"]
        self.assertEqual(b["beats"][0]["say"], "a month at my table")
        self.assertEqual(b["beats"][-2]["say"], "what are you cooking")
        self.assertEqual(b["signoff"], "see you tuesday")

    def test_a_long_story_drops_the_least_liked_moments_and_keeps_the_peak(self):
        extra = [(f"2026-0{i}-0{i}-00{i}-0", f"walk number {i}: the long way round.", "walk", 10 + i, (114, 114, 58), (0.5, 0.5), True)
                 for i in range(1, 8)]
        moments = extra + fixture.MOMENTS
        run, looks, bad = drafted(moments)
        for letter, plans in looks.items():
            b = plans["reel"]["board"]
            self.assertLessEqual(plans["reel"]["seconds"], 30)
            said = [x["say"] for x in b["beats"] if x["form"] == "photo"]
            self.assertEqual(said[-1], "at the market: peaches, figs, green almonds.")
            self.assertNotIn("walk number 1: the long way round.", said)
            self.assertEqual(bad[letter], [])

    def test_an_opening_line_too_tall_for_the_grids_panel_sets_smaller_inside_the_type_area(self):
        run, looks, bad = drafted(hook="tea and chapter nine")
        self.assertEqual(bad["c"], [])
        a = compose.Frame("reel").area
        t = looks["c"]["reel"]["board"]["beats"][0]["text"]
        self.assertGreaterEqual(t["panel"]["box"][1] + 1, a[1] - round(0.045 * compose.Frame("reel").W))
        self.assertTrue(all(a[1] - 1 <= bx[1] for bx in storyboard.text_boxes(t)))

    def test_a_thin_feed_still_makes_a_film_in_range(self):
        run, looks, bad = drafted(fixture.MOMENTS[:2])
        for letter, plans in looks.items():
            self.assertTrue(12 <= plans["reel"]["seconds"] <= 30, plans["reel"]["seconds"])
            self.assertEqual(bad[letter], [])


class Choices(unittest.TestCase):
    def test_a_move_is_chosen_for_what_the_beat_shows_never_by_turn(self):
        options = [{"id": "first", "fits": ["photo"]}, {"id": "people", "fits": ["photo", "people", "portrait"]}]
        tags = storyboard.tags_of({"form": "photo", "photo": {"aspect": 1.25}, "say": "", "people": ["@sam"]})
        self.assertEqual(storyboard.pick(options, tags, "photo", {}, None), "people")
        self.assertEqual(storyboard.pick(options, tags, "photo", {}, {"people"}), "first")

    def test_a_dropped_moment_leaves_no_two_beats_alike_either_side_of_it(self):
        # the moves are chosen for the beats that stay: a moment the length cannot fit goes before any move is given
        from types import SimpleNamespace
        card = {"axes": {"camera": "slow"}, "moves": [{"id": "push", "fits": ["photo"]}, {"id": "drift", "fits": ["photo"]},
                {"id": "title", "fits": ["title"]}, {"id": "ask", "fits": ["words"]}, {"id": "end", "fits": ["closer"]}],
                "transitions": [{"id": "cut", "fits": ["photo", "words", "closer"]}]}
        photo = {"aspect": 1.25}
        story = [{"photo": f"m{i}", "line": f"moment {i}", "pillar": "table", "likes": likes}
                 for i, likes in enumerate([50, 10, 40, 30, 90])]
        run = SimpleNamespace(d={"photos": {f"m{i}": dict(photo) for i in range(5)}}, story=story, hook="home",
                              question="who's coming over?", signoff="", handle="me")
        beats = storyboard.story(run, card, 60)
        self.assertLess(len([b for b in beats if b["form"] == "photo"]), 5)
        moves = [b["move"] for b in beats]
        self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), moves)

    def test_the_mask_cuts_the_longest_word_of_the_line(self):
        self.assertEqual(storyboard.mask_word("what's in season where you are?"), "season")
        self.assertEqual(storyboard.mask_word("who's coming over"), "coming")


if __name__ == "__main__":
    unittest.main()
