"""The storyboard of a synthetic person: its bounds and type floor, the wall that fills every frame, the hook's line
and rest, the words on every page (their own captions under the day they go up, their handle and bio, never a count), the beat
frames every format shares, and the sound cues, one where each beat lands. With no post of theirs on the wall the film
opens on the new posts. The three boards are three styles, each move chosen from its beat's content, and the vote
ships only at the bar. No files, no render.

Run from anywhere: python3 -m unittest discover -s S/tests
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import compose  # noqa: E402
import drive  # noqa: E402
import film  # noqa: E402
import storyboard as B  # noqa: E402
import vote  # noqa: E402

CAPTIONS = ["back home and still cooking like it's sicily", "dinner with @sam_and_june", "cold hands, warm coffee",
            "this light though", "took the long way through", "trying a new preset on", "new filter, who dis",
            "city lights, but make it neon", "testing colors, tell me which", "first light on the harbour wall"]
NEXT = ["slow morning, one cup", "pastéis de nata, straight from the oven", "baguettes cooling on the rack",
        "the sesame buns came out right", "every croissant in the window", "flour everywhere, the dough resting",
        "a cinnamon bun and one coffee", "the loaf, split down the middle",
        "a whole tray of them still warm on the bench before the doors open"]


BIO = "eating my way around on film \U0001F35E lisbon / wherever the bread is"


def people(m=9, handle="maren.okafor", audit=None, captions=CAPTIONS, bio=BIO, nxt=NEXT, bare=()):
    """A person with thirty posts, five of them loud on the first screen, every one with its cover but the positions in
    `bare`, and m new posts: (before, nine, plan, breaks)."""
    before = []
    for i in range(30):
        flags = ["clash"] if i in (5, 6, 7, 8) else ["text"] if i == 9 else []
        cap = captions[i % len(captions)]
        covered = i + 1 not in bare
        before.append({"pos": i + 1, "caption": cap, "saves": 2 if flags else 20 + (i * 7) % 15, "likes": 40 + i,
                       "file": f"before/{i + 1:02d}.jpg" if covered else None, "size": [1080, 1350] if covered else None,
                       "plate": ["#d8c4a8", "#3a2a1c"], "accent": "#c8643f" if flags else None, "flags": flags})
    first = dt.date(2026, 10, 27)
    slots = [{"n": n, "date": (first + dt.timedelta(days=n - 1)).isoformat()} for n in range(1, m + 1)]
    nine = [{"n": n, "file": f"graded/{n:02d}.jpg", "size": [1200, 1600], "crop45": [0.0, 0.0, 1.0], "crop34": [0.0, 0.0, 1.0],
             "caption": nxt[n - 1], "moment": nxt[n - 1], "follows": n, "place": "calm" if n % 2 else "busy",
             "focal": [0.7 if n == 5 else 0.3, 0.5]}
            for n, s in zip(range(1, m + 1), slots)]
    plan = {"handle": handle, "slots": slots, "cadence": {"gap_days": 1}}
    return before, nine, plan, B.breaks_of(before)


def person(m=9, handle="maren.okafor", audit=None, fmt="reel", captions=CAPTIONS, bio=BIO, nxt=NEXT, bare=()):
    """The board of that person in one format, and its faults."""
    before, nine, plan, breaks = people(m, handle, audit, captions, bio, nxt, bare)
    board = drive.build(fmt, before, nine, plan, audit, breaks, None, None, handle, bio)
    return board, B.faults(fmt, board)


def rest_slot(board, fmt="reel"):
    """The hook slot the frame comes to rest on and reads the hook over: the one it lands on first."""
    G = drive.geometry(fmt)
    land = next(k["box"] for k in board["beats"][0]["layers"][1]["keys"] if k["ease"] == "land")
    return next(s for s in board["hook"]["slots"] if [round(v, 1) for v in drive.cell(G, s)] == land)


def words_of(board, name):
    """The words the hook, the closer or a held post's page carries, as one line of text."""
    if name == "hook":
        return board["look"]["title"]
    if name == "closer":
        return " ".join(ln["text"] for ln in board["header"]["lines"])
    return drive.page_words(page_of(board, name))


def page_of(board, name):
    return next(b["layers"][0]["page"] for b in board["beats"] if b["id"] == name)


def held(board):
    return [b for b in board["beats"] if b["id"].startswith("post-") and b["layers"][0]["full"]]


class Board(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board, cls.faults = person()

    def test_nine_posts_hold_their_bounds_and_the_type_floor(self):
        self.assertEqual(self.faults, [])
        posts = [b for b in self.board["beats"] if b["id"].startswith("post-")]
        self.assertEqual(len(posts), 9)
        lo, hi = B.LENGTH
        self.assertTrue(lo <= self.board["seconds"] <= hi)
        self.assertLessEqual(B.hook_frame(self.board), B.HOOK_FRAMES)

    def test_fewer_than_nine_land_only_the_posts_there_are(self):
        board, faults = person(5)
        self.assertEqual(faults, [])
        self.assertEqual(len([b for b in board["beats"] if b["id"].startswith("post-")]), 5)

    def test_a_handle_too_long_for_the_closer_is_a_fault(self):
        _, faults = person(handle="ovenlight.bakery.and.the.long.harbour.wall.kitchen")
        self.assertTrue(any("closer" in f for f in faults), faults)

    def test_the_picture_holds_a_second_after_the_stop(self):
        self.assertAlmostEqual(self.board["seconds"] - self.board["stop_seconds"], 1.0)

    def test_a_held_post_holds_its_caption_whole_then_drops(self):
        posts = held(self.board)
        self.assertEqual(len(posts), 3)
        for b in posts:
            pg = b["layers"][0]["page"]
            standing = pg["sink"] - drive.page_landed(pg)
            read = drive.PEAK_READ if b["layers"][0].get("peak") else drive.READ
            with self.subTest(beat=b["id"]):
                # the words stand whole for three quarters of a second or more until they sink, and the post moves
                # on within a beat of its read
                self.assertGreaterEqual(standing * 60 / drive.BPM, 0.75)
                self.assertLessEqual(standing, read + 1.5)
                self.assertLess(pg["sink"], b["layers"][0]["times"]["drop"][0])
                # the paper opens out once the words have gone, and the post leaves through it
                self.assertLessEqual(pg["sink"], pg["open"][0])
                self.assertLessEqual(pg["open"][0], b["layers"][0]["times"]["drop"][0])

    def test_the_peak_is_the_middle_held_post_and_the_longest_still_in_the_film(self):
        posts = [b["layers"][0] for b in held(self.board)]
        stand = {p["n"]: p["page"]["sink"] - drive.page_landed(p["page"]) for p in posts}
        peak = [p["n"] for p in posts if p.get("peak")]
        self.assertEqual(peak, [posts[1]["n"]])
        self.assertEqual(max(stand, key=stand.get), peak[0])
        # its caption stands longer than the closer's still after the stop
        self.assertGreater(stand[peak[0]] * 60 / drive.BPM, self.board["seconds"] - self.board["stop_seconds"])

    def test_a_held_caption_starts_within_a_second_of_its_photograph_coming_in(self):
        for b in held(self.board):
            p = b["layers"][0]
            with self.subTest(beat=b["id"]):
                self.assertLessEqual((p["page"]["lines"][0]["at"] - p["times"]["fly"][0]) * 60 / drive.BPM, 1.0)

    def test_a_held_posts_page_carries_its_own_caption_and_its_day_and_nothing_else(self):
        for b in held(self.board):
            n = int(b["id"].split("-")[1])
            with self.subTest(beat=b["id"]):
                self.assertEqual(words_of(self.board, b["id"]), NEXT[n - 1])
                self.assertRegex(b["layers"][0]["page"]["label"]["text"], r"^[A-Z][a-z]+day \d{1,2} [A-Z][a-z]+$")

    def test_the_hook_page_carries_the_words_of_the_post_it_rests_on(self):
        hook = self.board["hook"]
        self.assertEqual(set(hook), {"slots", "rest", "title"})
        self.assertEqual(words_of(self.board, "hook"), CAPTIONS[rest_slot(self.board) % len(CAPTIONS)])
        self.assertEqual(drive.page_words(self.board["page"]), words_of(self.board, "hook"))

    def test_a_finding_without_saves_moves_the_hook_and_its_words_say_no_count(self):
        audit = {"findings": [{"title": "Close-ups cut into the trip", "positions": [2, 5, 7, 9, 13], "numbers": {"posts": 5}}]}
        board, faults = person(audit=audit)
        self.assertEqual(faults, [])
        self.assertEqual(board["hook"]["slots"], [5, 7, 9])
        self.assertIn(words_of(board, "hook"), CAPTIONS)

    def test_a_hook_on_posts_with_no_words_is_wordless(self):
        board, faults = person(captions=[""])
        self.assertEqual(faults, [])
        self.assertIsNone(board["page"])

    def test_the_closer_header_is_their_handle_and_their_bio(self):
        lines = self.board["header"]["lines"]
        self.assertEqual(lines[0]["text"], "@maren.okafor")
        self.assertEqual(" ".join(ln["text"] for ln in lines if ln["name"].startswith("bio-")), BIO)
        for fmt in ("square", "landscape"):
            board, faults = person(fmt=fmt)
            self.assertEqual(faults, [])
            lines = board["header"]["lines"]
            self.assertEqual(" ".join(ln["text"] for ln in lines if ln["name"].startswith("bio-")), BIO, fmt)
        board, faults = person(bio=None)
        self.assertEqual(faults, [])
        self.assertEqual(words_of(board, "closer"), "@maren.okafor")

    def test_no_word_cue_or_story_line_counts_saves_or_rolls_a_date(self):
        board = self.board
        said = [c["what"] for c in board["sound"]] + [s["reveals"] for s in board["story"]] + [s["carries"] for s in board["story"]]
        for w in said:
            with self.subTest(line=w):
                self.assertNotRegex(w, r"\bsaves?\b|\broll|\bdate\b")
        for b in held(board):
            label = b["layers"][0]["page"]["label"]["text"]
            with self.subTest(page=b["id"]):
                # a page's label names the day the post goes up, in words, and counts nothing
                self.assertNotRegex(label, r"\bsaves?\b|\d{4}")

    def test_a_sound_lands_where_a_beat_lands_and_nowhere_else(self):
        board = self.board
        cues = board["sound"]
        self.assertLessEqual(len(cues), len(board["beats"]) + 4)
        self.assertEqual({c["kind"] for c in cues}, {"hit", "riser", "impact", "stop"})
        self.assertEqual([(c["kind"], c["beat"]) for c in cues if c["kind"] != "hit"],
                         [("riser", "closer"), ("impact", "closer"), ("stop", "closer")])
        posts = [b["id"] for b in board["beats"] if b["id"].startswith("post-")]
        self.assertEqual([c["beat"] for c in cues if c["kind"] == "hit"], ["hook"] + posts + ["closer"])

    def test_with_no_loud_posts_the_hook_finds_the_off_color_posts_never_the_least_saved(self):
        before = [{"pos": i, "saves": i, "flags": [], "file": f"before/{i:02d}.jpg", "size": [1080, 1350],
                   "plate": ["#f0f0f0", "#101010"] if i not in (4, 6, 8) else ["#e03020", "#402010"]} for i in range(1, 31)]
        self.assertEqual(set(B.breaks_of(before)), {4, 6, 8})

    def test_a_first_screen_with_no_cover_breaks_nothing(self):
        before = [dict(b, file=None, size=None) for b in people()[0]]
        self.assertEqual(B.breaks_of(before), [])

    def test_words_too_long_for_the_page_are_a_fault_never_a_wordless_beat(self):
        nxt = ["thewholeharbourwallkitchenovenlightbakerymorningrunbeforethedoorsopenedwithsamandjune"] + NEXT[1:]
        board, faults = person(nxt=nxt)
        self.assertTrue(any("post-1" in f for f in faults), faults)

    def test_every_format_runs_on_the_reels_beat_frames_and_declares_them(self):
        before, nine, plan, breaks = people()
        boards = B.boards_of(None, None, before, nine, plan, None, breaks, None, None, "maren.okafor", BIO)
        reel = [b["frames"] for b in boards["reel"]["beats"]]
        for fmt, board in boards.items():
            with self.subTest(fmt=fmt):
                self.assertEqual([b["frames"] for b in board["beats"]], reel)
                self.assertEqual(sum(reel), round(board["seconds"] * drive.FPS))

    def test_the_hook_never_lands_on_a_post_without_a_cover(self):
        for audit in (None, {"findings": [{"positions": [5, 6, 7]}]}):
            board, _ = person(bare=(7,), audit=audit)
            with self.subTest(audit=audit):
                self.assertTrue(board["hook"]["slots"])
                self.assertNotIn(6, board["hook"]["slots"])

    def test_with_no_post_of_theirs_on_the_wall_the_film_opens_on_the_new_posts(self):
        # a folder of photos and no feed gives no grid; a grid whose posts have no cover gives nothing to show
        for name, bare in (("no grid", None), ("no cover", range(1, 31))):
            before, nine, plan, _ = people(bare=bare or ())
            before = before if bare else []
            boards = B.boards_of(None, None, before, nine, plan, None, B.breaks_of(before), None, None, "maren.okafor", BIO)
            for fmt, board in boards.items():
                with self.subTest(name=name, fmt=fmt):
                    self.assertEqual(B.faults(fmt, board), [])
                    hook = board["beats"][0]
                    self.assertEqual((board["hook"]["slots"], hook["frames"]), ([], 0))
                    self.assertEqual([c["key"] for c in hook["layers"][0]["cells"]], [f"post-{n}" for n in range(1, 10)])
                    post1 = board["beats"][1]["layers"][0]
                    # the frame opens round the part of post 1's photograph the camera sees
                    x, y, w, h = hook["layers"][1]["keys"][0]["box"]
                    wx, wy, ww, wh = post1["whole"]
                    self.assertTrue(wx - 0.5 <= x and wy - 0.5 <= y and x + w <= wx + ww + 0.5 and y + h <= wy + wh + 0.5,
                                    (x, y, w, h))
                    self.assertEqual([c["beat"] for c in board["sound"] if c["kind"] == "hit"], [f"post-{n}" for n in range(1, 10)] + ["closer"])
                    self.assertLess(drive.rests(board)["hook"], round(post1["times"]["seat"] * drive.PULSE))
            with self.subTest(name=name, length="reel"):
                self.assertTrue(B.length_band(9)[0] <= boards["reel"]["seconds"] <= B.LENGTH[1])
                self.assertLessEqual(B.hook_frame(boards["reel"]), B.HOOK_FRAMES)

    def test_seven_hook_visits_never_run_the_frame_backward(self):
        board, _ = person(audit={"findings": [{"positions": [3, 4, 5, 6, 7, 8, 9]}]})
        self.assertEqual(len(board["hook"]["slots"]), 7)
        keys = [k["t"] for k in board["beats"][0]["layers"][1]["keys"]]
        self.assertEqual(keys, sorted(keys))

    def test_the_hook_story_line_counts_nothing(self):
        line = next(s["reveals"] for s in self.board["story"] if s["beat"] == "hook")
        self.assertNotRegex(line, r"\b(two|three|four|five|six|seven|eight|nine|\d+)\b")

    def test_the_hook_event_is_its_line_on_the_first_frame_then_the_frame_landing(self):
        self.assertEqual(B.hook_frame(self.board), 0)
        keys = self.board["beats"][0]["layers"][1]["keys"]
        land = next(k for k in keys if k["ease"] == "land")
        self.assertAlmostEqual(land["t"], self.board["hook"]["title"] + 0.15, places=3)
        board, _ = person(captions=[""])
        land = next(k for k in board["beats"][0]["layers"][1]["keys"] if k["ease"] == "land")
        self.assertEqual(B.hook_frame(board), round(land["t"] * drive.PULSE))
        self.assertLessEqual(B.hook_frame(board), B.HOOK_FRAMES)

    def test_every_format_and_style_sets_each_page_whole_in_one_size_off_the_photograph(self):
        before, nine, plan, breaks = people()
        for style in compose.TRIO:
            boards = B.boards_of(style, None, before, nine, plan, None, breaks, None, None, "maren.okafor", BIO)
            for fmt, board in boards.items():
                W, H = board["format"]["width"], board["format"]["height"]
                for b in held(board):
                    pg, n = b["layers"][0]["page"], int(b["id"].split("-")[1])
                    pic, box = pg["pic"], pg["box"]
                    with self.subTest(style=style, fmt=fmt, page=b["id"]):
                        self.assertEqual(B.faults(fmt, board), [])
                        self.assertEqual(drive.page_words(pg).lower(), NEXT[n - 1])
                        self.assertEqual(len({ln["size"] for ln in pg["lines"]}), 1)
                        self.assertEqual({ln["x"] for ln in pg["lines"]}, {box[0]})
                        if pg["over"]:
                            # words set on the photograph are in caps over a photograph that fills the frame
                            self.assertEqual(pic, [0, 0, W, H])
                            self.assertEqual(drive.page_words(pg), drive.page_words(pg).upper())
                        elif W > H:
                            # a wide frame stands the photograph in its middle and its words in a column beside it
                            self.assertTrue(box[0] >= pic[2] or box[2] <= pic[0], (pic, box))
                        else:
                            self.assertTrue(box[1] >= pic[3] or box[3] <= pic[1], (pic, box))

    def test_the_wall_runs_edge_to_edge(self):
        G = drive.geometry("reel")["grid"]
        self.assertEqual(G["x0"], 0)
        self.assertAlmostEqual(3 * G["cw"] + 2 * G["g"], drive.geometry("reel")["W"])

    def test_every_camera_key_before_the_closer_sees_only_the_wall(self):
        W, H = self.board["format"]["width"], self.board["format"]["height"]
        top = drive.geometry("reel")["grid"]["y0"]
        lock = self.board["beats"][-1]["layers"][0]["lock"]
        # while a held post's page stands, its paper covers all but the photograph, so the camera sits square on the
        # photograph wherever that puts its view
        paper = [(b["layers"][0]["page"]["close"][0], b["layers"][0]["page"]["open"][1]) for b in held(self.board)]
        keys = [k for k in self.board["beats"][0]["layers"][2]["keys"] if k["t"] < lock - 0.25
                and not any(a <= k["t"] <= z for a, z in paper)]
        self.assertGreater(len(keys), 12)
        for k in keys:
            x0, y0, x1, _ = drive.footprint(k, W, H)
            with self.subTest(t=k["t"]):
                self.assertGreaterEqual(x0, -1)
                self.assertLessEqual(x1, W + 1)
                self.assertGreaterEqual(y0, top - 1)

    def test_the_hook_rests_on_the_middle_column(self):
        self.assertEqual(rest_slot(self.board) % 3, 1)

    def test_every_sound_names_its_event_and_the_stop_is_the_last(self):
        cues = self.board["sound"]
        self.assertTrue(all(c["what"].strip() for c in cues))
        self.assertEqual(cues[-1]["kind"], "stop")
        self.assertEqual(max(c["at"] for c in cues), cues[-1]["at"])
        self.assertAlmostEqual(cues[-1]["at"] * drive.PULSE / drive.FPS, self.board["stop_seconds"], places=3)

    def test_a_wrapped_caption_never_ends_on_a_comma(self):
        lines = drive.wrap("cold hands, warm coffee and the long walk home", 40, 760)
        self.assertTrue(lines)
        self.assertLessEqual(len(lines), 2)
        self.assertFalse(lines[-1].endswith(","))


class Styles(unittest.TestCase):
    """Three boards are three styles, and each beat's move is the one its content fits."""

    def test_a_run_drafts_the_trio_or_a_named_style_and_the_two_most_unlike_it(self):
        self.assertEqual(sorted(compose.trio()), sorted(compose.TRIO))
        self.assertEqual(compose.trio("editorial-quiet")[0], "editorial-quiet")
        for named in compose.styles():
            got = compose.trio(named)
            with self.subTest(style=named):
                self.assertEqual(got[0], named)
                self.assertEqual(len(set(got)), 3)
                if named not in compose.TRIO:
                    rest = sorted(compose.TRIO, key=lambda s: len(compose.shared_axes(named, s)))
                    self.assertEqual(sorted(len(compose.shared_axes(named, s)) for s in got[1:]),
                                     sorted(len(compose.shared_axes(named, s)) for s in rest[:2]))

    def test_each_style_sets_the_film_in_its_own_faces_colors_and_moves(self):
        before, nine, plan, breaks = people()
        seen = {}
        for style in compose.TRIO:
            reel = B.boards_of(style, None, before, nine, plan, None, breaks, None, None, "maren.okafor", BIO)["reel"]
            card = compose.card(style)
            moves = [b["move"] for b in reel["timeline"]["beats"] if b["move"]]
            with self.subTest(style=style):
                self.assertEqual(B.faults("reel", reel), [])
                self.assertEqual(reel["look"]["display"], card["faces"]["display"]["family"])
                self.assertTrue(set(moves) <= set(compose.ids(card, "moves")), moves)
                # no two beats in a row share a move while the card allows another
                if len(compose.ids(card, "moves")) > 1:
                    self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), moves)
            seen[style] = (reel["look"]["display"], reel["look"]["colors"]["bg"], tuple(moves))
        for i, a in enumerate(compose.TRIO):
            for b in compose.TRIO[i + 1:]:
                with self.subTest(pair=(a, b)):
                    self.assertNotEqual(seen[a][:2], seen[b][:2])

    def test_a_move_follows_what_the_beat_shows_never_its_place_in_the_film(self):
        options = [{"id": "push", "fits": ["photo", "portrait"]}, {"id": "slide", "fits": ["photo", "landscape"]},
                   {"id": "slam", "fits": ["words"]}]
        self.assertEqual(compose.pick(options, {"photo", "landscape"}, "photo", {}), "slide")
        self.assertEqual(compose.pick(options, {"photo", "portrait"}, "photo", {}), "push")
        self.assertEqual(compose.pick(options, set(), "words", {}), "slam")
        # the move the beat before used goes last while another fits
        self.assertEqual(compose.pick(options, {"photo", "landscape"}, "photo", {}, avoid="slide"), "push")


class Bar(unittest.TestCase):
    """The film ships at a mean of 4.5 over the seven rules with no rule under 4, never under it."""

    def test_the_bar_is_a_mean_and_a_floor(self):
        rules = list(vote.CRITERIA)
        self.assertEqual((vote.MEAN, vote.FLOOR), (4.5, 4))
        self.assertTrue(vote.at_bar(dict.fromkeys(rules, 5)))
        self.assertTrue(vote.at_bar(dict(dict.fromkeys(rules, 5), concept=4, image=4, type=4)))
        self.assertFalse(vote.at_bar(dict.fromkeys(rules, 4)), "a mean of 4 is under the bar")
        self.assertFalse(vote.at_bar(dict(dict.fromkeys(rules, 5), sound=3)), "one rule under 4 is under the bar")

    def test_the_redraft_a_fix_asks_for_keeps_its_round_and_another_look_starts_at_round_one(self):
        import json
        import os
        import tempfile
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            try:
                Path("critic").mkdir()
                Path("critic/cut-1.json").write_text(json.dumps({"round": 1, "board": "A", "film": "f1"}))
                Path("critic/swap.json").write_text("{}")
                Path("winner.json").write_text(json.dumps({"board": "A"}))
                B.reset_after_pick(keep="A")
                self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the fix's redraft spends the one fix")
                self.assertFalse(Path("critic/swap.json").exists())
                self.assertFalse(Path("winner.json").exists())
                B.reset_after_pick(keep="B")
                self.assertEqual(vote.rounds(), [], "another look is a new film with rounds of its own")
            finally:
                os.chdir(here)


class Posts(unittest.TestCase):
    """The nine posts are one set: a card that sets its line over its picture lays the post that way, and every
    post's line sets at one size, the largest at which each caption sets whole."""

    CAPS = ["sliced thin", "sixty croissants for @sam_and_june's wedding breakfast", "first loaf from the new oven"]

    def test_a_card_that_sets_its_line_over_the_picture_lays_the_post_over_it(self):
        self.assertEqual(film.post_layout(compose.card("kinetic-type")), "over")
        self.assertEqual(film.post_layout(compose.card("editorial-quiet")), "margin")

    def test_every_posts_line_sets_at_one_size_with_each_caption_whole(self):
        board = {"nine": [{"n": n + 1, "caption": c} for n, c in enumerate(self.CAPS)]}
        for style in ("kinetic-type", "editorial-quiet", "swiss-grid"):
            compose.use(style)
            line = compose.card(style)["photo"]["line"]
            size = film.over_size(board, line) if film.post_layout(compose.card(style)) == "over" else \
                film.margin_size(board, line, 30)
            with self.subTest(style=style):
                self.assertLessEqual(size, line["size"])
                for c in self.CAPS:
                    words = film.post_words({"caption": c}, line["face"], size, film.PW - 2 * film.MARGIN_M, 5, 40)
                    self.assertEqual(" ".join(words[2]), film.cased(c, line["face"]))


if __name__ == "__main__":
    unittest.main()
