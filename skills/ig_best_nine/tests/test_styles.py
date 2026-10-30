"""The kit draws its looks from the style cards: three boards in three different styles, the named style with the two
trio styles most unlike it, and nothing of a look written into the kit's own code. The agent shows the sheet where it
may ask and picks by taste where it may not, the film ships at the bar or its best cut is delivered with its scores in
the run's brief, and the review page offers the other looks without a score in sight. The board lays nine distinct
layouts, a template fails the timed check whatever the monotony read says, and the moves' windows, covers and holds are
read from the move files themselves.

    python3 -I -m unittest discover -s S/tests -p test_styles.py
"""
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "tests"))
import compose  # noqa: E402
import deliver  # noqa: E402
import palette  # noqa: E402
import qa  # noqa: E402
import story  # noqa: E402
import storyboard  # noqa: E402
import test_story  # noqa: E402
import vote  # noqa: E402

# the kit's own code, without the files the shared system keeps in step across the kits
SYNCED = {"render.py", "setup.py", "music_engine.py"}
OWN = [p for p in sorted((KIT / "scripts").glob("*.py")) if p.name not in SYNCED] + [KIT / "motion/studio/Film.tsx"]
# the code that lays out and draws the film
LOOK = [KIT / "scripts" / n for n in ("story.py", "compose.py", "storyboard.py", "bounds.py")] + [KIT / "motion/studio/Film.tsx"]


def boards(fmt="reel"):
    return {s: test_story.board(fmt, style=s) for s in compose.TRIO}


def photo_beats(b):
    return [x for x in b["beats"] if x["form"] == "photo"]


class Skill(unittest.TestCase):
    text = (KIT / "SKILL.md").read_text()

    def test_the_description_fits_the_listing(self):
        desc = re.search(r"^description: (.*)$", self.text, re.M).group(1).strip().strip('"')
        self.assertLess(len(desc), 1024, len(desc))

    def test_the_agent_shows_the_sheet_where_it_may_ask_and_picks_by_taste_where_it_may_not(self):
        flat = " ".join(self.text.split())
        self.assertIn("show them `out/boards.png`", flat)
        self.assertIn("(`ask` is `false`): pick by `taste.md` and say why in one line", flat)
        self.assertIn('--why "<one line>"', flat)

    def test_the_kit_folder_is_where_skill_md_was_read_and_every_command_runs_in_a_fresh_shell(self):
        flat = " ".join(self.text.split())
        self.assertIn("the folder this SKILL.md was read from", flat)
        self.assertIn("fresh shell", flat)

    def test_no_install_step_is_named(self):
        self.assertFalse(re.search(r"\b(node|npm|npx|venv|pip|download\w*)\b", self.text, re.I))


class Looks(unittest.TestCase):
    def test_no_style_named_draws_the_trio(self):
        self.assertEqual(compose.three(), list(compose.TRIO))

    def test_a_named_style_comes_with_the_two_trio_styles_most_unlike_it(self):
        for named in compose.styles():
            with self.subTest(named=named):
                got = compose.three(named)
                self.assertEqual(got[0], named)
                self.assertEqual(len(set(got)), 3)
                rest = [s for s in compose.TRIO if s != named]
                fewest = min(len(compose.shared_axes(named, a)) + len(compose.shared_axes(named, b))
                             for i, a in enumerate(rest) for b in rest[i + 1:])
                self.assertEqual(len(compose.shared_axes(named, got[1])) + len(compose.shared_axes(named, got[2])), fewest)

    def test_the_three_boards_are_three_styles_each_in_its_cards_faces_and_photograph(self):
        bs = boards()
        self.assertEqual({b["style"] for b in bs.values()}, set(compose.TRIO))
        for s, b in bs.items():
            c = compose.card(s)
            self.assertEqual(b["system"]["display"]["family"], c["faces"]["display"]["family"])
            self.assertEqual(b["system"]["photo"], c["photo"], "the card's photograph treatment passes through whole")
        self.assertEqual([x for x in storyboard.style_findings(bs, list(palette.NEUTRAL)) if " share " in x], [])

    def test_no_look_is_picked_by_rotating_an_index_and_none_is_written_into_the_kit(self):
        faces = {compose.card(s)["faces"][k]["family"] for s in compose.styles() for k in ("display", "text")}
        for f in OWN:
            src = f.read_text()
            self.assertFalse(re.search(r"%\s*len\(", src), f"{f.name} picks by rotating an index")
            self.assertNotIn("TONES", src, f.name)
        for f in LOOK:
            src = f.read_text()
            self.assertFalse(re.findall(r"#[0-9a-fA-F]{6}\b", src), f"{f.name} writes a color of its own")
            for face in faces:
                self.assertNotIn(face, src, f"{f.name} names the face {face}")

    def test_what_the_cards_carry_is_gone_from_the_kit(self):
        for gone in ("design/type.json", "design/easing.json", "design/standards.md", "scripts/tones"):
            self.assertFalse((KIT / gone).exists(), gone)
        self.assertEqual(sorted(p.name for p in (KIT / "fonts").iterdir()), ["LICENSES.md", "styles"])


class Bar(unittest.TestCase):
    @staticmethod
    def round_of(scores):
        it = iter(scores)
        return {"critics": {c: {"boards": {"film": {"scores": {k: next(it) for k in vote.CRITERIA}}}} for c in vote.CUT_PANEL}}

    def test_the_film_ships_at_a_mean_of_four_and_a_half_with_nothing_under_four(self):
        n = len(vote.CUT_PANEL) * len(vote.CRITERIA)
        at = [5] * (n // 2) + [4] * (n - n // 2)
        self.assertTrue(vote.at_bar(self.round_of(at))[2])
        self.assertFalse(vote.at_bar(self.round_of([4] * n))[2], "a mean of 4 is under the bar")
        low = [5] * (n - 1) + [3]
        self.assertGreaterEqual(vote.at_bar(self.round_of(low))[0], vote.BAR)
        self.assertFalse(vote.at_bar(self.round_of(low))[2], "one criterion under 4 holds the film under the bar")


class ReviewPage(unittest.TestCase):
    def test_the_page_offers_the_other_looks_and_names_no_score_rule_or_critic(self):
        with mock.patch.object(deliver._env, "read_json", return_value={}):
            looks = deliver.others_html({"board": compose.TRIO[0], "looks": list(compose.TRIO)})
        for s in compose.TRIO[1:]:
            self.assertIn(compose.card(s)["name"], looks)
        self.assertNotIn(compose.card(compose.TRIO[0])["name"], looks)
        self.assertIn("Prefer another look? Say ", looks)
        self.assertIn("make the second one", looks)
        page = re.sub(r"<style>.*?</style>", "", deliver.PAGE, flags=re.S) + looks
        words = re.sub(r"<[^>]+>|\{\w+\}", " ", page).lower()
        for banned in ("score", "critic", "rule", "the bar", "mean", "verdict", "round"):
            self.assertNotIn(banned, words)


class Board(unittest.TestCase):
    def test_the_nine_take_nine_layouts_in_every_style_and_format(self):
        for fmt in compose.FORMATS:
            for s, b in boards(fmt).items():
                layouts = [x["layout"] for x in photo_beats(b)]
                self.assertEqual(len(layouts), 9, (s, fmt))
                self.assertEqual(len(set(layouts)), 9, (s, fmt, layouts))

    def test_the_film_runs_in_pick_order(self):
        ps = test_story.posts()
        for i, p in enumerate(ps):
            p["pick"] = 9 - i
        self.assertEqual([p["rank"] for p in story.film_order(ps)], [p["rank"] for p in ps])

    def test_a_template_fails_the_timed_check_whatever_the_monotony_read_says(self):
        b = test_story.board()
        for x in photo_beats(b):
            x["layout"] = "bleed"
        f = {"findings": [], "seconds": 30, "hook_frame": 4, "hash": "h", "style": b["style"], "boards": {"reel": "reel.json"}}
        read = {"hash": "h", "monotony": {"pass": True, "read": " ".join(["the cut never repeats itself"] * 6)}}
        files = {"reel.json": b, "critic/timed.json": read, "preview/preview.json": {}}
        with mock.patch.object(qa, "cut", return_value=f), mock.patch.object(qa, "asked", return_value=30), \
                mock.patch.object(qa._env, "read_json", side_effect=lambda p: files.get(str(p))), \
                mock.patch.object(storyboard, "Run", lambda: type("R", (), {"swatches": list(palette.NEUTRAL)})()):
            res, _ = qa.timed_checks()
        rows = {r[0]: r for r in res}
        self.assertTrue(rows["monotony"][1])
        self.assertFalse(rows["template"][1])
        self.assertIn("takes a layout of its own", rows["template"][2])


class Moves(unittest.TestCase):
    MOVES = sorted(p.stem for p in story.MOVES_DIR.glob("*.tsx"))

    def test_a_move_has_a_window_exactly_when_its_file_draws_one(self):
        fr = compose.Frame("reel")
        for m in self.MOVES:
            win, _ = story.window(m, fr.W, fr.H)
            self.assertEqual(tuple(win) != (0, 0, fr.W, fr.H), story.frames_picture(m), m)

    def test_a_beat_the_board_lays_takes_a_move_that_acts_where_the_card_has_one_and_hands_it_no_words(self):
        for fmt in compose.FORMATS:
            for s, b in boards(fmt).items():
                acts = [m for m in compose.ids(compose.card(s), "moves") if not story.frames_picture(m) and not story.only_says(m)]
                for x in photo_beats(b):
                    if x["layout"] != x["move"]:
                        if acts:
                            self.assertFalse(story.only_says(x["move"]), (s, fmt, x["id"], x["move"]))
                        self.assertEqual((x["words"], x["label"]), ("", ""), (s, fmt, x["id"]))

    def test_a_move_that_mats_the_photographs_box_plays_on_a_laid_beat_and_never_on_the_hook_or_the_grid(self):
        self.assertFalse(story.frames_picture("crop-shift"))
        self.assertTrue(story.covers("crop-shift"))
        for fmt in compose.FORMATS:
            for s, b in boards(fmt).items():
                for x in b["beats"]:
                    if x["form"] in ("title", "wall"):
                        self.assertFalse(story.covers(x["move"]) and not story.frames_picture(x["move"]), (s, fmt, x["id"], x["move"]))

    def test_a_landscape_photograph_in_the_cards_layout_takes_its_landscape_box_and_its_line_stays_in_its_line_box(self):
        ps = test_story.posts()
        first = story.film_order(ps)[0]
        first["aspect"] = 0.66
        fr = compose.Frame("reel")
        for s in compose.TRIO:
            b = test_story.board(ps=[dict(p) for p in ps], style=s)
            x = next(x for x in b["beats"] if x["id"] == f"piece-{first['rank']}")
            land = compose.card(s)["photo"]["landscape"]
            self.assertEqual(x["layout"], "card", s)
            photo = next(L for L in x["layers"] if L["kind"] == "Photo")
            if land["box"][1] > 0:
                # the print's rim stands inside the box
                rim = compose.card(s)["photo"]["picture"]["rim"] * fr.W
                self.assertAlmostEqual(photo["box"][1], land["box"][1] * fr.H + rim, delta=1.0, msg=s)
            x0, y0, x1, y1 = fr.safe
            lx, ly, lw, lh = land["line"]
            zone = (x0 + lx * (x1 - x0), y0 + ly * (y1 - y0), x0 + (lx + lw) * (x1 - x0), y0 + (ly + lh) * (y1 - y0))
            for ln in [ln for L in x["layers"] if L["kind"] == "Words" for ln in L["lines"]]:
                bx0, by0, bx1, by1 = compose.text_box(b["system"], ln, ink=True)
                self.assertTrue(zone[0] - 2 <= bx0 and bx1 <= zone[2] + 2 and zone[1] - 2 <= by0 and by1 <= zone[3] + 2, (s, ln["text"], zone))

    def test_the_cut_into_a_move_that_opens_on_a_cover_is_the_hard_cut(self):
        for s, b in boards().items():
            c = compose.card(s)
            for m in story.OPENS_ON_GROUND & set(compose.ids(c, "moves")):
                self.assertEqual(story.cut_into(c, m, "a wipe"), "hard-cut", (s, m))
            for x in b["beats"][1:]:
                if x["move"] in story.OPENS_ON_GROUND:
                    self.assertIn(x["transition"], ("hard-cut", None), (s, x["id"]))

    def test_the_picture_behind_a_window_stands_its_focus_at_the_windows_middle(self):
        fr = compose.Frame("reel")
        win = [0.3 * fr.W, 0.3 * fr.H, 0.4 * fr.W, 0.3 * fr.H]
        for focus in ((0.4, 0.55), (0.6, 0.45), (0.5, 0.5)):
            p = {"aspect": 1.25, "focus": list(focus)}
            x, y, w, h = story.through(p, win, fr)
            self.assertAlmostEqual(x + focus[0] * w, win[0] + win[2] / 2, delta=1.0)
            self.assertAlmostEqual(y + focus[1] * h, win[1] + win[3] / 2, delta=1.0)

    def test_a_shade_under_words_on_a_window_spans_the_frames_width(self):
        fr = compose.Frame("reel")
        S = test_story.board()["system"]
        line = {"text": "a caption", "face": "display", "size": 60, "x": 100, "y": 0.7 * fr.H}
        sh = story.shade_of([line], S, fr, "ink", 0.6, [0, 0.2 * fr.H, fr.W, 0.6 * fr.H])
        self.assertEqual((sh["box"][0], sh["box"][2]), (0, fr.W))

    def test_a_held_composition_is_not_a_stalled_render(self):
        still = next(m for m in self.MOVES if story.still(m))
        moving = next(m for m in self.MOVES if not story.still(m))
        board = {"format": {"fps": 30}, "beats": [{"form": "photo", "move": still, "frames": 60},
                                                  {"form": "photo", "move": moving, "frames": 60},
                                                  {"form": "closer", "move": "", "frames": 90}]}
        self.assertTrue(qa.composed(board, 0.5, 1.9), "inside a beat whose move holds the picture")
        self.assertFalse(qa.composed(board, 2.2, 3.9), "inside a beat whose move pushes the picture")
        self.assertFalse(qa.composed(board, 1.5, 2.5), "across a cut")
        self.assertTrue(qa.composed(board, 4.1, 6.9), "the closer's title stands still once it is set")


class Length(unittest.TestCase):
    def test_twenty_seconds_fits_at_every_tempo_the_music_can_have(self):
        # the snap cuts at the music's tempo, its half or its double, whichever the nine fit at
        for bpm in range(50, 201, 2):
            self.assertTrue(any(story.fits(test_story.posts(), 20, bpm * k) for k in (0.5, 1, 2)), bpm)
        self.assertTrue(story.fits(test_story.posts(), 20, 100), "the short grid holds the nine where the full one would not")


if __name__ == "__main__":
    unittest.main()
