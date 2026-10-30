"""The film is the nine by their own numbers: a countdown from the ninth to the first, each as its own caption line
and its day, holding as long as its post asks for, the whole reel at the length asked, and the closer the nine in a
three by three grid, the first at its top left; no like count, rank, total or countdown figure is set on any board.

    python3 -I -m unittest discover -s S/tests
"""
import hashlib
import json
import re
import sys
import unittest
from unittest import mock
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import compose  # noqa: E402
import research  # noqa: E402
import stats  # noqa: E402
import story  # noqa: E402
import storyboard  # noqa: E402

BOOK = json.loads((KIT / "tests" / "cornerloaf.json").read_text())
STYLE = compose.TRIO[0]


def posts(n=9):
    return [dict(p) for p in BOOK["posts"][:n]]


def plan(fmt="reel", ps=None, bpm=None, seconds=None, style=STYLE, swatches=None):
    ps = posts() if ps is None else ps
    return storyboard.board_for(style, ps, fmt, storyboard.words_default(BOOK["year"]), BOOK["handle"], BOOK["year"], bpm, seconds,
                                swatches)


def board(fmt="reel", ps=None, bpm=None, seconds=None, style=STYLE, swatches=None):
    return plan(fmt, ps, bpm, seconds, style, swatches)["board"]


def lines_of(beat):
    return [ln for L in beat["layers"] if L["kind"] == "Words" for ln in L["lines"]]


def said(beat):
    """The beat's caption as set on screen: its display lines, top to bottom."""
    return " ".join(ln["text"] for ln in lines_of(beat) if ln.get("face") == "display")


def pieces(b):
    return [x for x in b["beats"] if x["id"].startswith("piece-")]


def frames_of(b):
    return {x["id"]: x["frames"] for x in pieces(b)}


def worded(b):
    """The pieces whose words the board sets itself (a move that sets its own label sets them in the film)."""
    return [x for x in pieces(b) if lines_of(x)]


class Order(unittest.TestCase):
    def test_the_film_counts_down_from_the_ninth_to_the_first(self):
        for style in compose.TRIO:
            for fmt in compose.FORMATS:
                with self.subTest(style=style, fmt=fmt):
                    self.assertEqual([x["id"] for x in pieces(board(fmt, style=style))], [f"piece-{r}" for r in range(9, 0, -1)])

    def test_the_hook_opens_on_the_first(self):
        hook = board()["beats"][0]
        photo = next(L for L in hook["layers"] if L["kind"] == "Photo")
        self.assertEqual(photo["photo"]["file"], posts()[0]["file"])

    def test_the_first_holds_longest(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                f = frames_of(board(style=style))
                self.assertGreater(f["piece-1"], max(v for k, v in f.items() if k != "piece-1"))


class Ranking(unittest.TestCase):
    """stats.rank: the nine by the account's own numbers, the most first."""

    @staticmethod
    def row(ts, **numbers):
        return dict({"ts": ts, "media": [f"{ts}.jpg"], "caption": ""}, **numbers)

    def test_likes_rank_first_then_comments_then_saves(self):
        rows = [self.row(1, likes=5, comments=1, saves=9), self.row(2, likes=9, comments=0, saves=0),
                self.row(3, likes=5, comments=1, saves=10), self.row(4, likes=5, comments=3, saves=0)]
        ranked, by = stats.rank(rows)
        self.assertEqual([r["ts"] for r in ranked], [2, 4, 3, 1])
        self.assertEqual(by, "likes, then comments, then saves")

    def test_a_file_with_saves_alone_ranks_by_saves(self):
        rows = [self.row(1, saves=3), self.row(2, saves=12), self.row(3, saves=7)]
        ranked, by = stats.rank(rows)
        self.assertEqual([r["ts"] for r in ranked], [2, 3, 1])
        self.assertEqual(by, "saves")

    def test_with_no_numbers_the_nine_are_the_most_recent(self):
        rows = [self.row(t) for t in range(1, 15)]
        ranked, by = stats.rank(rows)
        self.assertEqual([r["ts"] for r in ranked[:9]], list(range(14, 5, -1)))
        self.assertEqual(by, "recent")
        self.assertIn("the nine are the most recent", stats.RECENT)

    def test_fewer_than_nine_posts_are_refused(self):
        self.assertEqual(research.short_of_nine({"top_nine": [{"rank": r} for r in range(1, 6)]}), "not delivered: 5 posts, nine needed")
        self.assertIsNone(research.short_of_nine({"top_nine": [{"rank": r} for r in range(1, 10)]}))
        with mock.patch.object(storyboard._env, "read_json", side_effect=lambda f: {"stats.json": {"year": 2026}, "picks.json": {"nine": []}}.get(f)), \
                mock.patch.object(storyboard, "posts_of", return_value=posts(5)), self.assertRaises(SystemExit) as e:
            storyboard.Run()
        self.assertEqual(e.exception.code, "not delivered: 5 posts, nine needed")


class Length(unittest.TestCase):
    def test_the_reel_runs_the_length_asked_at_every_tempo_the_nine_fit(self):
        lo, hi = storyboard.LENGTH
        for seconds in (lo, 25, 30, 40, hi):
            tempos = [bpm for bpm in range(80, 161, 10) if storyboard.story.fits(posts(), seconds, bpm)]
            self.assertTrue(tempos, f"no tempo fits {seconds} s")
            for bpm in tempos[:: max(1, len(tempos) // 3)]:
                for fmt in compose.FORMATS:
                    with self.subTest(seconds=seconds, bpm=bpm, fmt=fmt):
                        self.assertLessEqual(abs(plan(fmt, bpm=bpm, seconds=seconds)["seconds"] - seconds), 0.5)

    def test_the_ask_is_read_from_taste_and_one_outside_the_range_makes_nothing(self):
        lo, hi = storyboard.LENGTH
        self.assertEqual(storyboard.asked({}), storyboard.SECONDS)
        self.assertEqual(storyboard.asked({"seconds": 40}), 40)
        for seconds in (lo - 5, hi + 15):
            with self.subTest(seconds=seconds), self.assertRaises(SystemExit) as e:
                storyboard.asked({"seconds": seconds})
            self.assertEqual(e.exception.code, f"not made: the reel runs {lo} to {hi} s, and {seconds} s was asked; nothing shorter or longer is made in its place")


class Holds(unittest.TestCase):
    def test_a_captioned_post_holds_longer_than_a_wordless_one_and_a_repeat_holds_shortest(self):
        ps = posts()
        for p in ps:
            p["look"] = hashlib.sha256(str(p["rank"]).encode()).hexdigest()[:16]
        ps[5]["caption"] = ""  # rank 6, wordless
        ps[3]["look"] = ps[6]["look"]  # rank 4 repeats the photograph of rank 7, which comes before it
        for seconds in (20, 30, 40):
            with self.subTest(seconds=seconds):
                f = frames_of(board(ps=ps, seconds=seconds))
                captioned = [f[f"piece-{r}"] for r in (2, 3, 5, 7, 8, 9)]
                self.assertGreater(min(captioned), f["piece-6"])
                self.assertGreater(f["piece-6"], f["piece-4"])

    def test_more_words_hold_longer_and_the_holds_are_no_grid(self):
        f = frames_of(board())
        words = {p["rank"]: len(p["caption"].split()) for p in posts()}
        order = [r for r in range(9, 1, -1)]
        for a in order:
            for b in order:
                if words[a] > words[b]:
                    self.assertGreaterEqual(f[f"piece-{a}"], f[f"piece-{b}"], f"{words[a]} words against {words[b]}")
        ids = [x["id"] for x in pieces(board())]
        self.assertGreaterEqual(len({f[i] for i in ids}), 4, "no beat grid")

    def test_every_line_lands_before_the_beat_is_half_over(self):
        for bpm in (100, 120, 140):
            for style in compose.TRIO:
                for beat in worded(board(bpm=bpm, style=style)):
                    with self.subTest(bpm=bpm, style=style, beat=beat["id"]):
                        at = max(L["at"] for L in beat["layers"] if L["kind"] == "Words")
                        self.assertLess(at * compose.pulse_of(bpm), beat["frames"] / 2)


class Words(unittest.TestCase):
    def test_no_count_rank_or_total_reaches_the_screen(self):
        likes = {str(p["likes"]) for p in BOOK["posts"]} | {str(sum(p["likes"] for p in BOOK["posts"]))}
        for style in compose.TRIO:
            for fmt in compose.FORMATS:
                b = board(fmt, style=style)
                shown = [ln["text"] for beat in b["beats"] for ln in lines_of(beat)]
                shown += [x[k] for x in b["beats"] for k in ("words", "label") if x.get(k)]
                for text in shown:
                    with self.subTest(style=style, fmt=fmt, text=text):
                        figures = {f.replace(" ", "").replace(",", "") for f in re.findall(r"\d[\d ,]*", text)}
                        self.assertFalse(figures & likes)
                        self.assertNotRegex(text, r"\bno\. ?\d|#\d|\b[1-9]\s*/\s*9\b")

    def test_each_moment_says_its_own_caption_and_its_day(self):
        for style in compose.TRIO:
            b = board(style=style)
            for beat in pieces(b):
                p = next(p for p in posts() if beat["id"] == f"piece-{p['rank']}")
                texts = [ln["text"].lower() for ln in lines_of(beat)]
                with self.subTest(style=style, beat=beat["id"]):
                    if texts:
                        self.assertEqual(texts[0], p["date"])
                        self.assertEqual(" ".join(texts[1:]), p["caption"])
                    else:
                        # a move that sets the words itself is handed the caption
                        self.assertEqual(beat["words"], p["caption"])

    def test_a_moment_without_a_caption_is_wordless(self):
        ps = posts()
        ps[4]["caption"] = ""
        beat = next(x for x in board(ps=ps)["beats"] if x["id"] == f"piece-{ps[4]['rank']}")
        self.assertEqual([ln["text"] for ln in lines_of(beat)] or [beat["label"]], [ps[4]["date"]])


class Lines(unittest.TestCase):
    T = [1771070400, 1779019200, 1788091200]
    STATS = {"top_nine": [
        {"rank": 1, "ts": T[0], "date": "2026-02-14", "caption": "Heart croissants, gone by 9 #bakery"},
        {"rank": 2, "ts": T[1], "date": "2026-05-17", "caption": "1,000 followers!! thank you"},
        {"rank": 3, "ts": T[2], "date": "2026-08-30", "caption": "Lunch in Palermo with @dani.reyes #sicily"},
    ]}
    PICKS = {"nine": [{"rank": r, "file": f"{r}.jpg", "aspect": 1.0, "focus": [0.5, 0.5], "crop": [0, 0, 1], "look": f"{r:016x}"} for r in (1, 2, 3)]}

    def test_the_board_sets_the_curated_moment_line_of_each_post(self):
        taste = {"register": {"lowercase": True}, "moments": [{"ts": self.T[1], "line": ""}, {"ts": self.T[0], "line": "Heart croissants"}]}
        out = storyboard.posts_of(self.STATS, self.PICKS, taste)
        said = {p["ts"]: p["caption"] for p in out}
        # a curated line as written, a caption whose only words are a count wordless, an uncurated one its lead in their case
        self.assertEqual(said, {self.T[0]: "Heart croissants", self.T[1]: "", self.T[2]: "lunch in palermo with @dani.reyes"})
        self.assertEqual([p["look"] for p in out], [f"{r:016x}" for r in (1, 2, 3)])


class Selection(unittest.TestCase):
    def test_the_board_never_reads_the_likes_that_picked_the_nine(self):
        bare = [{k: v for k, v in p.items() if k != "likes"} for p in posts()]
        self.assertEqual(board(ps=bare), board())


class Pieces(unittest.TestCase):
    def test_no_hold_on_the_reel_leaves_its_lower_third_bare(self):
        frame = compose.Frame("reel")
        for name in story.LAYOUTS:
            if name != "card":
                with self.subTest(layout=name):
                    x, y, w, h = story.geometry(name, frame)["photo"]
                    self.assertGreaterEqual(y + h, frame.H * 2 / 3)

    def test_no_mark_and_no_tape_lands_on_the_words(self):
        for style in compose.TRIO:
            for fmt in compose.FORMATS:
                b = board(fmt, style=style)
                for x in worded(b):
                    photo = next((L for L in x["layers"] if L["kind"] == "Photo"), None)
                    if not photo or not story.marks(x["move"]) and not (photo.get("print") or {}).get("tape"):
                        continue
                    with self.subTest(style=style, fmt=fmt, beat=x["id"]):
                        bx, by, bw, bh = photo["box"]
                        s, rim = min(bw, bh), (photo.get("print") or {}).get("rim", 0)
                        reach = [r for r in (story.writes(x["move"], photo["box"], b["format"]["width"]) if story.marks(x["move"]) else None,
                                             [bx - 0.2 * s, by - 0.4 * rim - 0.16 * s, bx + bw + 0.2 * s, by + 0.16 * s]
                                             if (photo.get("print") or {}).get("tape") else None) if r]
                        for ln in lines_of(x):
                            for r in reach:
                                self.assertFalse(story._meets(story.text_box(b["system"], ln, ink=True), r), ln["text"])


class Ending(unittest.TestCase):
    def test_the_grid_is_the_nine_three_by_three_the_first_at_its_top_left(self):
        for style in compose.TRIO:
            for fmt in compose.FORMATS:
                with self.subTest(style=style, fmt=fmt):
                    b = board(fmt, style=style)
                    W, H = b["format"]["width"], b["format"]["height"]
                    grid = next(x for x in b["beats"] if x["id"] == "grid")
                    tiles = [L for L in grid["layers"] if L["kind"] == "Slice"]
                    self.assertEqual(len(tiles), 9)
                    boxes = {L["owner"]: L["box"] for L in tiles}
                    for x, y, w, h in boxes.values():
                        self.assertTrue(0 <= x and x + w <= W and 0 <= y and y + h <= H)
                    self.assertEqual((len({round(b[0]) for b in boxes.values()}), len({round(b[1]) for b in boxes.values()})), (3, 3))
                    self.assertEqual(len({(round(b[2]), round(b[3])) for b in boxes.values()}), 1, "every tile the same size")
                    reading = sorted(boxes, key=lambda r: (round(boxes[r][1]), round(boxes[r][0])))
                    self.assertEqual(reading, list(range(1, 10)))
                    self.assertEqual(b["beats"][-1]["form"], "closer")

    def test_the_wall_stands_whole_for_three_seconds_before_the_cut_into_the_closer(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                b = board(style=style)
                grid = next(x for x in b["beats"] if x["id"] == "grid")
                landed = max(L["at"] + L["beats"] for L in grid["layers"] if L["kind"] == "Slice")
                self.assertGreaterEqual((grid["beats"] - landed - story.EDGE) * 60 / b["bpm"], 3.0)

    def test_the_closer_comes_up_over_the_whole_wall(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                b = board(style=style)
                grid = next(x for x in b["beats"] if x["id"] == "grid")
                under = b["beats"][-1]["layers"]
                self.assertEqual([L["box"] for L in under], [L["box"] for L in grid["layers"] if L["kind"] == "Slice"])
                self.assertTrue(all(L["at"] == 0 and L["beats"] == 0 for L in under))

    def test_the_reel_and_wide_grid_carry_the_year_the_handle_and_the_ask_and_the_square_is_the_grid_alone(self):
        for fmt in compose.FORMATS:
            with self.subTest(fmt=fmt):
                grid = next(x for x in board(fmt)["beats"] if x["id"] == "grid")
                texts = [ln["text"] for ln in lines_of(grid)]
                if fmt == "square":
                    self.assertEqual(texts, [])
                    continue
                self.assertEqual(texts[0], str(BOOK["year"]))
                self.assertIn(BOOK["handle"], texts[1])
                self.assertIn("share yours", texts[1])

    def test_a_run_with_no_username_sets_no_handle_on_any_beat(self):
        with mock.patch.object(storyboard._env, "read_json", side_effect=lambda f: {"stats.json": {"year": BOOK["year"]}, "picks.json": {"nine": []}}.get(f)), \
                mock.patch.object(storyboard, "posts_of", return_value=posts()):
            run = storyboard.Run()
        for fmt in ("reel", "wide"):
            with self.subTest(fmt=fmt):
                b = storyboard.board_for(STYLE, posts(), fmt, run.words(), run.handle, run.year)["board"]
                texts = [ln["text"] for beat in b["beats"] for ln in lines_of(beat)] + [x["label"] for x in b["beats"]]
                self.assertFalse([t for t in texts if "@you" in t], "no handle is made up")
                grid = next(x for x in b["beats"] if x["id"] == "grid")
                self.assertEqual(lines_of(grid)[-1]["text"], "share yours")

    def test_the_sound_names_no_count(self):
        b = board()
        self.assertFalse([c for c in b["sound"] if re.search(r"\bcount\b|\bno\. ", c["what"])])

    def test_a_sound_lands_where_a_beat_lands_and_nowhere_else(self):
        b = board()
        cues = b["sound"]
        ids = [x["id"] for x in pieces(b)]
        self.assertEqual([(c["kind"], c["beat"]) for c in cues if c["kind"] != "hit"],
                         [("riser", ids[-1]), ("impact", ids[-1]), ("stop", "closer")])
        self.assertEqual([c["beat"] for c in cues if c["kind"] == "hit"], ["hook", *ids[:-1], "grid", "closer"])


class Moments(unittest.TestCase):
    def test_the_moments_draft_is_their_captions_people_places_and_days_in_film_order(self):
        stats_ = {"top_nine": [
            {"rank": 1, "kind": "post", "ts": 1783166400, "date": "2026-07-04", "likes": 400, "comments": 9, "caption": "lunch in palermo with @dani.reyes #sicily"},
            {"rank": 2, "kind": "reel", "ts": 1770724800, "date": "2026-02-10", "likes": 300, "comments": 4, "caption": "first snow on the roof"},
        ]}
        out = research.moments(stats_)
        # the countdown's order: the last ranked first, the first last
        self.assertEqual([m["date"] for m in out], ["2026-02-10", "2026-07-04"])
        self.assertEqual([m["rank"] for m in out], [2, 1])
        self.assertEqual(out[1]["line"], "lunch in palermo with @dani.reyes")
        self.assertEqual(out[1]["people"], ["dani.reyes"])
        self.assertEqual(out[1]["place"], "palermo")
        self.assertEqual(out[0]["people"], [])
        self.assertIsNone(out[0]["place"])
        for m in out:
            self.assertFalse({"likes", "comments", "posts", "times_usual", "total"} & set(m))


class Colors(unittest.TestCase):
    """The film's colors are the style card's palette rule over the run's swatches: no color is the kit's own."""

    A, B = ["#2b4a7a", "#e8d9b0", "#c0392b"], ["#1f6b3a", "#f2f2ea", "#8e44ad"]

    def test_the_accent_follows_the_photographs_in_every_style(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                a = board(style=style, swatches=self.A)["system"]["colors"]
                b = board(style=style, swatches=self.B)["system"]["colors"]
                self.assertNotEqual(a["accent"], b["accent"])

    def test_the_board_shows_no_color_outside_its_palette(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                b = board(style=style, swatches=self.A)
                c = b["system"]["colors"]
                made = {v.lower() for k, v in c.items() if k != "swatches"} | {x["hex"].lower() for x in c["swatches"]}
                beats = {k: v for k, v in b.items() if k != "system"}
                self.assertEqual({h.lower() for h in storyboard.hexes_in(beats)} - made, set())

if __name__ == "__main__":
    unittest.main()
