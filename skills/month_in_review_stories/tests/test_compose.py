"""The board builder and the board checks, on the fixture month and on months shaped differently.

    python3 -m unittest discover -s S/tests -p 'test_compose.py'
"""
import copy
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture
import compose
import deliver
import research
import storyboard
import studio
from compose import month, reel, style

# the four moments the agent picks: the fixture's four top posts by likes and comments, the wedding the peak
PICKED = [{"day": 5}, {"day": 13, "peak": True}, {"day": 17}, {"day": 28}]


def picked(m, moments=PICKED):
    """Their month with the moments the agent picks, each named by the photograph of its day's post (or by its day when
    the post has none) and saying its caption unless it gives its own line."""
    m = copy.deepcopy(m)
    by_day = {p["day"]: p for p in m["posts"]}
    m["moments"] = [{"day": x["day"], "photo": by_day[x["day"]]["photo"] if x["day"] in by_day else f"no-post-on-{x['day']}.jpg",
                     "line": x.get("line", by_day.get(x["day"], {}).get("caption", "")), "peak": bool(x.get("peak"))}
                    for x in moments]
    return m


def months_later(m, k):
    """The same month moved k months on."""
    m = copy.deepcopy(m)
    n = m["month"]["year"] * 12 + m["month"]["month"] - 1 + k
    m["month"]["year"], m["month"]["month"] = n // 12, n % 12 + 1
    return m


def with_posts(m, n):
    """Their month with n posts on spread days, their captions and photographs in turn, each post's photograph a file of
    its own as gather writes them."""
    m = copy.deepcopy(m)
    base = m["posts"]
    days = sorted({1 + (i * 27) // n for i in range(n)})
    into = Path(tempfile.mkdtemp(prefix="mir-posts-"))
    m["posts"] = [dict(base[i % len(base)], day=d) for i, d in enumerate(days)]
    for p in m["posts"]:
        if p.get("photo"):
            own = into / f"{p['day']:02d}-{Path(p['photo']).name}"
            own.symlink_to(p["photo"])
            p["photo"] = str(own)
    m.pop("moments", None)
    return m


def on_screen(b):
    """Every word a board draws, lowercased, since the card's faces set their own case."""
    return [w.lower() for w in storyboard.reel_words(b) + [w for c in b["beats"] for w in storyboard.card_words(c)]]


def their_rows():
    with open(fixture.FIXTURE / "posts.csv", newline="") as f:
        return list(csv.DictReader(f))


def their_numbers():
    """The fixture's likes and comments figures that could not be a day of the month."""
    return {r[k] for r in their_rows() for k in ("likes", "comments") if int(r[k]) > 31}


def their_counts():
    """Each day's likes and comments as the fixture's table carries them."""
    return {int(r["date"][8:10]): (int(r["likes"]), int(r["comments"])) for r in their_rows()}


def asked(m, **ask):
    m = copy.deepcopy(m)
    m["ask"] = ask
    return m


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()
        cls.picked = picked(cls.month)
        cls.board = compose.board("editorial-quiet", cls.picked)
        cls.spread = compose.board("editorial-quiet", cls.month)

    def test_month_is_their_posts_with_their_counts(self):
        m = self.month
        self.assertEqual(len(m["posts"]), 8)
        self.assertNotIn("year", m)
        self.assertEqual({p["day"]: (p["likes"], p["comments"]) for p in m["posts"]}, their_counts())
        self.assertIn("my sister marta got married", m["posts"][3]["caption"])

    def test_a_table_with_no_likes_is_enough(self):
        ws = fixture.workspace()
        with open(ws / "posts.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        with open(ws / "posts.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "type", "caption", "photo"])
            w.writeheader()
            w.writerows({k: r[k] for k in ("date", "type", "caption", "photo")} for r in rows)
        self.assertEqual(len(fixture.researched(ws)["posts"]), 8)

    def test_the_moments_draft_is_their_days_words_and_people(self):
        ws = fixture.workspace()
        fixture.researched(ws)
        b = fixture.build(ws)
        taste, research = (json.loads((b / f).read_text()) for f in ("taste.json", "research.json"))
        posts = {p["photo"]: p for p in research["posts"]}
        # the draft is the month as its captions tell it: its first post, its last, and the caption that says the most
        self.assertEqual([posts[x["photo"]]["day"] for x in taste["moments"]], [2, 13, 28])
        self.assertEqual([posts[x["photo"]]["day"] for x in taste["moments"] if x["peak"]], [13])
        self.assertTrue(all(x["what"] == x["line"] == posts[x["photo"]]["caption"] for x in taste["moments"]))
        people = {p["day"]: p["people"] for p in research["posts"]}
        self.assertEqual((people[17], people[24], people[13]), (["joana.m"], ["rita.c", "sofia.m"], []))
        self.assertEqual(taste["ask"], {"counts": False, "seconds": None, "series": False})
        text = (b / "taste.json").read_text()
        self.assertNotRegex(text, r"\blikes\b|\bcomments\b")
        self.assertFalse([n for n in their_numbers() if re.search(rf"\b{n}\b", text)])
        # the draft shows each post's figures, for an ask that wants them, and never ranks the posts by them
        draft = (b / "taste.draft.md").read_text()
        likes, comments = their_counts()[13]
        self.assertIn(f"{likes} likes, {comments} comments", draft)
        self.assertNotIn("most likes", draft)

    def test_the_picked_moments_are_the_beats(self):
        r = self.board["reel"]
        # the reel opens on the peak, then the other moments in date order; the story cards run in date order
        self.assertEqual([c["day"] for c in r["cards"]], [13, 5, 17, 28])
        self.assertTrue(r["cards"][0]["peak"])
        self.assertEqual([c["id"] for c in self.board["beats"]], ["story-1", "story-2", "story-3", "story-4"])
        for c, card in zip(self.board["beats"], sorted(r["cards"], key=lambda c: c["day"])):
            self.assertTrue(all(x["file"] == card["file"] for x in c["bands"]), c["id"])
        self.assertEqual(len({c["file"] for c in r["cards"]}), 4)
        # unpicked, the moments are the month's story as its captions tell it, the caption that says the most the peak
        self.assertEqual([c["day"] for c in self.spread["reel"]["cards"]], [13, 2, 28])
        # with no counts in the data any pick stands, and its peak opens the reel
        bare = copy.deepcopy(self.month)
        for p in bare["posts"]:
            p["likes"] = p["comments"] = None
        later = compose.board("editorial-quiet", picked(bare, [{"day": 2}, {"day": 9}, {"day": 28, "peak": True}]))
        self.assertEqual([c["day"] for c in later["reel"]["cards"]], [28, 2, 9])

    def test_a_line_wraps_evenly_and_never_leaves_one_word_alone(self):
        w = lambda t: 10 * len(t)
        text = "my sister got married under the trees at aveleda"
        self.assertEqual(month.fill(text, w, 400)[-1], "aveleda")
        lines = month.wrap(text, w, 400)
        self.assertEqual(len(lines), 2)
        self.assertGreater(len(lines[-1].split()), 1)
        self.assertLess(max(map(w, lines)), 300)
        self.assertEqual(month.fit(text, w, 400), "my sister got married under the trees…")

    def test_words_too_long_for_two_rows_end_on_their_last_whole_sentence(self):
        m = month.Month(self.picked)
        compose.look.dress(m, style.card("editorial-quiet"), m.look, m.given_swatches)
        post = m.peak
        post.said = "my sister marta got married under the trees at quinta da aveleda. arms up from the whole family as the rain held off"
        limit = reel.R0 - reel.L0
        lines = reel.words_of(m, post, 50, limit)
        self.assertEqual(" ".join(lines), "my sister marta got married under the trees at quinta da aveleda.")
        self.assertLessEqual(len(lines), 2)
        post.said = "one sentence so long that it never sets on two rows of the frame however evenly it wraps, " * 2
        self.assertTrue(reel.words_of(m, post, 50, limit)[-1].endswith("…"))

    def test_a_label_fits_its_width_and_a_word_too_long_for_it_breaks(self):
        w = lambda t: 10 * len(t)
        self.assertTrue(all(w(x) <= 100 for x in month.wrap("a supercalifragilistic day", w, 100)))
        self.assertLessEqual(w(month.fit("supercalifragilistic", w, 100)), 100)
        self.assertLessEqual(w(month.fit("a supercalifragilistic day", w, 100)), 100)
        self.assertEqual(month.fit("a short day", w, 120), "a short day")
        m = picked(self.month)
        long = "the long quinta past the river where the road ends and the trees begin"
        for p in m["posts"]:
            p["place"] = long
        b = compose.board("editorial-quiet", m)
        labels = [c["lines"][0] for c in b["reel"]["cards"]] + [x for c in b["beats"] for x in c["lines"] if x["text"].startswith("sep ")]
        self.assertTrue(labels)
        for x in labels:
            self.assertLessEqual(reel.width(x["text"], x["size"], x["file"]), reel.R0 - reel.L0 + 0.5, x["text"])

    def test_a_video_is_never_the_photograph(self):
        ts = lambda d: int(datetime.datetime(2026, 9, d, 12, tzinfo=datetime.timezone.utc).timestamp())
        lib = {"month": {"key": "2026-09", "year": 2026, "month": 9, "name": "september"}, "handle": "a",
               "posts": [], "reels": [{"ts": ts(5), "caption": "a", "media": ["a.mp4", "a.jpg"]},
                                      {"ts": ts(6), "caption": "b", "media": ["b.MP4"]}]}
        self.assertEqual([p["photo"] for p in research.month_json(lib, Path(tempfile.mkdtemp()))["posts"]], ["a.jpg", None])
        # a month with two photographs among its posts is told, the rest as type; fewer than three posts is not a month
        ws = fixture.workspace()
        fixture.researched(ws)
        b = fixture.build(ws)
        lib = json.loads((b / "library.json").read_text())
        posts = [x for k in ("posts", "reels") for x in lib[k] if x.get("ts") and f"{research.when(x['ts']):%Y-%m}" == lib["month"]["key"]]
        self.assertGreater(len(posts), 3)
        for x in posts[2:]:
            x["media"] = [str(Path(x["media"][0]).with_suffix(".mp4"))] if x.get("media") else []
        (b / "library.json").write_text(json.dumps(lib))
        go = lambda: subprocess.run([sys.executable, str(fixture.SCRIPTS / "research.py")], cwd=ws, capture_output=True, text=True,
                                    env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"))
        r = go()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sum(1 for p in json.loads((b / "month.json").read_text())["posts"] if p["photo"]), 2)
        for k in ("posts", "reels"):
            lib[k] = [x for x in lib[k] if x not in posts[2:]]
        (b / "library.json").write_text(json.dumps(lib))
        r = go()
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("three posts", r.stdout)

    def test_a_moment_with_no_post_or_too_many_is_refused(self):
        for bad in ([{"day": 3}, {"day": 13}, {"day": 17}], [{"day": d} for d in (2, 5, 9, 13, 17)]):
            with self.assertRaises(ValueError):
                compose.board("editorial-quiet", picked(self.month, bad))

    def test_the_peak_holds_longest_and_words_take_their_time(self):
        cs = self.board["reel"]["cards"]
        span = {c["day"]: c["leave"] - c["arrive"] for c in cs}
        self.assertEqual(max(span, key=span.get), 13)
        self.assertTrue(all(span[13] > v for d, v in span.items() if d != 13), span)
        quiet = picked(self.month, [{"day": 5}, {"day": 13, "peak": True, "line": ""}, {"day": 17}, {"day": 28}])
        quiet["moments"][2]["line"] = "front of the crowd at the show, four songs in and still filming, my arms up the whole night long"
        span = {c["day"]: c["leave"] - c["arrive"] for c in compose.board("editorial-quiet", quiet)["reel"]["cards"]}
        self.assertTrue(all(span[13] > v for d, v in span.items() if d != 13), span)
        m = picked(self.month, [{"day": 5}, {"day": 13}, {"day": 17}, {"day": 28}])
        short = {c["day"]: c["leave"] - c["arrive"] for c in compose.board("editorial-quiet", m)["reel"]["cards"]}
        m["moments"][3]["line"] = "the cup"
        shorter = {c["day"]: c["leave"] - c["arrive"] for c in compose.board("editorial-quiet", m)["reel"]["cards"]}
        self.assertLess(shorter[28], short[28])

    def test_the_words_on_screen_are_theirs(self):
        caps = {p["day"]: p["caption"].lower() for p in self.month["posts"]}
        for c in self.board["reel"]["cards"]:
            small, *cap = [x["text"].lower() for x in c["lines"] if x.get("name") != "hook"]
            self.assertEqual(small, f"sep {c['day']}")
            said = " ".join(cap).rstrip("…")
            self.assertTrue(caps[c["day"]].startswith(said), (said, caps[c["day"]]))
        words = " ".join(on_screen(self.board))
        self.assertNotRegex(words, r"\blikes\b|\bcomments?\b|\bposts?\b|\bhigh\b|\bbest\b")
        self.assertFalse([n for n in their_numbers() if re.search(rf"\b{n}\b", words)])

    def test_the_words_are_the_moments_lines_and_an_empty_line_is_wordless(self):
        m = picked(self.month, [{"day": 5}, {"day": 13, "peak": True, "line": "marta got married"}, {"day": 17, "line": ""},
                                {"day": 28}])
        b = compose.board("editorial-quiet", m)
        said = {c["day"]: [x["text"] for x in c["lines"] if x.get("name") not in ("hook", "small")] for c in b["reel"]["cards"]}
        self.assertEqual(said[13], ["marta got married"])
        self.assertEqual(said[17], [])
        self.assertEqual([x["line"] for x in b["moments"]][1:3], ["marta got married", ""])
        self.assertNotIn("still filming", " ".join(storyboard.card_words(b["beats"][2])))
        # two posts on one day: the moment is the one whose photograph it names
        two = copy.deepcopy(self.month)
        twin = dict(two["posts"][4], photo=two["posts"][4]["photo"] + ".other.jpg", caption="the queue outside before the doors")
        two["posts"].append(twin)
        b = compose.board("editorial-quiet", picked(two, PICKED) | {"moments": [
            {"photo": twin["photo"], "line": twin["caption"], "peak": True}] + [dict(x, peak=False) for x in picked(self.month, PICKED)["moments"][1:]]})
        self.assertEqual(" ".join(x["text"] for x in b["reel"]["cards"][0]["lines"] if x.get("name") not in ("hook", "small")),
                         "the queue outside before the doors")

    def test_two_photographs_of_one_day_each_keep_their_own_file_and_cell(self):
        # a post and a reel of one day whose photographs share a file name in different folders
        two = copy.deepcopy(self.month)
        post = next(p for p in two["posts"] if p["day"] == 17)
        into = Path(tempfile.mkdtemp(prefix="mir-twin-"))
        twin = dict(post, type="reel", photo=str(into / Path(post["photo"]).name), caption="the queue outside before the doors")
        Path(twin["photo"]).symlink_to(two["posts"][0]["photo"])
        two["posts"].append(twin)
        m = picked(two, [{"day": 13}, {"day": 28}])
        m["moments"][:0] = [{"photo": twin["photo"], "line": twin["caption"], "peak": True},
                            {"photo": post["photo"], "line": post["caption"], "peak": False}]
        b = compose.board("editorial-quiet", m)
        r = b["reel"]
        same = [c for c in r["cards"] if c["day"] == 17]
        self.assertEqual(len(same), 2)
        self.assertNotEqual(same[0]["file"], same[1]["file"])
        self.assertEqual(sorted(c["source"] for c in same), sorted(str(Path(x).resolve()) for x in (post["photo"], twin["photo"])))
        lead = next(c for c in same if c["source"] == str(Path(twin["photo"]).resolve()))
        self.assertEqual(r["cards"][0]["file"], lead["file"])
        self.assertEqual(sorted(x["file"] for c in b["beats"] for x in c["bands"]), sorted(c["file"] for c in r["cards"]))
        # each photograph of the day has a cell of its own on the closer's wall, the day beneath each
        tiles = [t for t in r["closer"]["tiles"] if t["day"] == 17]
        self.assertEqual(len(tiles), 2)
        self.assertEqual(sorted(c["cell"] for c in same), sorted(t["cell"] for t in tiles))
        # the day is named once, under its first photograph
        self.assertEqual([t["label"]["text"].lower() for t in tiles], ["sep 17", ""])
        # the storyboard names each beat's photograph and the words it sets
        with tempfile.TemporaryDirectory() as d:
            storyboard.write_md(b, Path(d) / "storyboard.md")
            md = (Path(d) / "storyboard.md").read_text()
        for c in same:
            self.assertIn(f"- photograph: {c['source']}", md)
        self.assertIn("- on screen: my september, in four stories / sep 17 / the queue outside before the doors", md.lower())

    def wall_holds_the_posts(self, b, m):
        """The closer of board b is the month m's posts with a photograph and nothing else: one cell each in date order,
        the day beneath it, the rows filling the wall's width with no cell left over, and every moment's photograph
        set into its own post's cell."""
        r = b["reel"]
        tiles = r["closer"]["tiles"]
        shown = sorted((p for p in m["posts"] if p.get("photo")), key=lambda p: p["day"])
        self.assertEqual([t["day"] for t in tiles], [p["day"] for p in shown])
        self.assertNotIn("days", r["closer"])
        self.assertNotIn("letters", r["closer"])
        rows, named = {}, set()
        for t in tiles:
            x0, y0, x1, y1 = t["cell"]
            self.assertLess(x0, x1)
            self.assertLess(y0, y1)
            rows.setdefault(y0, []).append(t)
            lab = t["label"]
            # a day is named once, under its first photograph
            self.assertEqual(lab["text"].lower(), "" if t["day"] in named else f"sep {t['day']}")
            named.add(t["day"])
            self.assertTrue(y1 < lab["y"] - 0.7 * lab["size"] and lab["y"] <= reel.FLOOR, (t["cell"], lab))
            self.assertLessEqual(reel.width(lab["text"], lab["size"], lab["file"]), x1 - x0 + 0.5)
            if not t["moment"]:
                self.assertTrue(t["file"] and t["source"] and len(t["crop"]) == 4, t)
        for row in rows.values():
            row.sort(key=lambda t: t["cell"][0])
            self.assertAlmostEqual(row[0]["cell"][0], reel.L0, delta=0.5)
            self.assertAlmostEqual(row[-1]["cell"][2], reel.R0, delta=0.5)
            self.assertTrue(all(a["cell"][2] < z["cell"][0] for a, z in zip(row, row[1:])))
        cells = [t["cell"] for t in tiles]
        for c in r["cards"]:
            if c["file"]:
                self.assertTrue(c["stays"])
                self.assertEqual(sum(1 for t in tiles if t["moment"] and t["cell"] == c["cell"]), 1)
            else:
                self.assertFalse(c["stays"])
                self.assertNotIn(c["cell"], cells)
        self.assertEqual(sum(1 for t in tiles if t["moment"]), sum(1 for c in r["cards"] if c["file"]))

    def test_the_ending_is_the_months_posts_and_never_an_empty_calendar(self):
        r = self.board["reel"]
        cl = r["closer"]
        self.wall_holds_the_posts(self.board, self.picked)
        self.assertEqual(len(cl["tiles"]), 8)
        self.assertEqual([t["day"] for t in cl["tiles"] if t["moment"]], [5, 13, 17, 28])
        # the month's line lands under the wall, and the style's closing page comes over it with the handle and the ask
        self.assertEqual([x["text"].lower() for x in cl["lines"]], ["my september, in four stories"])
        self.assertEqual(cl["page"]["name"], style.card("editorial-quiet")["closer"])
        self.assertEqual((r["look"]["handle"], r["look"]["signoff"].lower()), ("@ines.photo", "see you in october."))
        self.assertNotIn("count", cl)
        self.assertNotIn("slot", cl)
        last = self.board["beats"][-1]
        self.assertIn("see you in october.  ·  @ines.photo", [w.lower() for w in storyboard.card_words(last)])
        stop = [c for c in r["sound"] if c["kind"] == "stop"]
        self.assertEqual(len(stop), 1)
        self.assertLess(stop[0]["at"], r["end"])
        # three posts close on a wall of three, twenty on a wall of twenty
        for n in (3, 20):
            m = with_posts(self.month, n)
            b = compose.board("editorial-quiet", m)
            self.assertEqual(len(b["reel"]["closer"]["tiles"]), n)
            self.wall_holds_the_posts(b, m)
        # a post with no photograph has no cell, and its moment's type card leaves the wall as the camera does
        m = picked(self.month, [{"day": 13, "peak": True}, {"day": 17}, {"day": 28}])
        bare = next(p for p in m["posts"] if p["day"] == 28)
        bare["photo"] = None
        m["moments"][2]["photo"] = None
        b = compose.board("editorial-quiet", m)
        self.assertEqual([c["beat"] for c in b["reel"]["clips"] if c["use"] != "texture"], [c["key"] for c in b["reel"]["cards"] if c["file"]])
        self.assertEqual(len(b["reel"]["closer"]["tiles"]), 7)
        self.wall_holds_the_posts(b, m)

    def test_the_brief_names_each_moment_as_it_was_picked(self):
        taste = {"moments": [dict(x, what=f"what happened on day {d}") for x, d in zip(self.picked["moments"], (5, 13, 17, 28))]}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "month.json").write_text(json.dumps(self.month))
            rows = deliver.moment_rows(Path(d), self.board, taste)
        caps = {p["day"]: p["caption"] for p in self.month["posts"]}
        self.assertEqual(len(rows), 2 + len(PICKED))
        for x, row in zip(PICKED, rows[2:]):
            cells = [c.strip() for c in row.strip("|").split("|")]
            self.assertEqual(cells[0], f"{x['day']}" + (" (the peak)" if x.get("peak") else ""))
            self.assertEqual(cells[1], f"what happened on day {x['day']}")
            self.assertEqual(cells[2], Path(self.picked["moments"][PICKED.index(x)]["photo"]).name)
            self.assertEqual(cells[4], caps[x["day"]])

    def test_every_board_check_passes(self):
        for m, b in ((self.picked, self.board), (self.month, self.spread)):
            for r in storyboard.check_board(b, m):
                self.assertTrue(r["ok"], f"{r['check']}: {r['detail']}")

    def test_every_card_carries_the_same_header_with_its_number(self):
        heads = [c["lines"][0]["text"].lower() for c in self.board["beats"]]
        self.assertEqual(heads, [f"{i:02d} · my september, in four stories" for i in range(1, 5)])

    def test_cards_are_15_s(self):
        self.assertEqual({studio.card_frames(self.board, c) for c in self.board["beats"]}, {450})

    def test_the_reel_runs_its_moments_then_the_closer_and_ends_on_its_stop(self):
        r = self.board["reel"]
        keys = [b["key"] for b in r["beats"]]
        self.assertEqual(keys, ["moment-1", "moment-2", "moment-3", "moment-4", "closer"])
        self.assertEqual(r["cuts"], [round(b["from"] * 30 * 60 / r["bpm"]) for b in r["beats"][1:]])
        self.assertEqual(storyboard.reel_structure(self.board), [])

    def test_the_reel_fails_a_beat_that_carries_nothing(self):
        b = copy.deepcopy(self.board)
        b["reel"]["beats"][2]["carries"] = ""
        self.assertTrue(any("carries" in x for x in storyboard.reel_structure(b)))
        b = copy.deepcopy(self.board)
        b["reel"]["sound"] = [c for c in b["reel"]["sound"] if c["kind"] != "stop"]
        self.assertIn("the last sound cue is not the stop", storyboard.reel_structure(b))

    def test_every_moments_move_belongs_to_its_photograph(self):
        got = storyboard.photo_swap(self.board, self.picked)
        self.assertEqual(len(got), 4)
        self.assertTrue(all(changed for _, changed in got), got)

    def test_swap_fails_a_card_that_ignores_their_moments(self):
        self.assertTrue(all(changed for _, changed in storyboard.swap_test(self.board, self.picked)))
        same = storyboard.swap_test(self.board, self.picked, build=lambda m: compose.board("editorial-quiet", self.picked))
        self.assertTrue(same and not any(changed for _, changed in same))

    def test_monotony_fails_equal_shots(self):
        b = copy.deepcopy(self.board)
        for c in b["beats"]:
            for s in c["shots"]:
                s["beats"] = 4
        self.assertFalse(storyboard.monotony(b)["ok"])

    def test_every_card_holds_somewhere_at_every_pulse_the_styles_take(self):
        from compose import stories
        m = month.Month(self.picked)
        for bpm in range(96, 141):
            m.bpm = bpm
            for p in m.moments:
                s = stories.shots_of(m, p)
                mid = sorted(s)[1:3]
                self.assertEqual(sum(s), stories.beats_of(m), (bpm, s))
                self.assertGreaterEqual(max(s), storyboard.MONOTONY["held"] * sum(mid) / 2, (bpm, p.name, s))

    def test_a_beats_words_are_placed_by_its_words_not_the_hook_above_them(self):
        card = {"lines": [{"name": "hook", "y": 500}, {"name": "said", "y": 1300, "anchor": "start"}]}
        self.assertEqual(storyboard.place_of(card), "in the bottom third, start")

    def test_words_fail_on_capitals_or_exclamations(self):
        b = copy.deepcopy(self.board)
        b["beats"][0]["lines"].append(dict(b["beats"][0]["lines"][0], text="Wow!"))
        self.assertFalse([r for r in storyboard.check_board(b, self.picked) if r["check"] == "words"][0]["ok"])

    def test_every_card_signs_off_with_the_handle(self):
        for c in self.board["beats"]:
            signs = [x for x in c["lines"] if self.board["handle"] in x["text"].lower()]
            self.assertEqual(len(signs), 1, c["id"])
            self.assertGreaterEqual(signs[0]["at"], sum(sh["beats"] for sh in c["shots"][:3]), c["id"])

    def test_the_close_look_holds_the_subjects_gesture_and_the_words_under_it(self):
        from compose import stories
        for c in self.board["beats"]:
            if not c.get("bands"):
                continue
            close = c["shots"][1]
            self.assertIn("to", close, c["id"])
            safe = stories.safe_of(stories.held(close))
            day = next(x for x in c["lines"] if x["text"].lower().startswith("sep "))
            self.assertTrue(stories.inside(stories.box_of(day), safe, -2), (c["id"], day["text"]))
            r = stories.rect_of(close["to"])
            self.assertGreaterEqual(r[3] - r[1], 2 * stories.REACH[1] - 1, c["id"])

    def test_handle_and_month_come_from_the_month(self):
        m = copy.deepcopy(self.picked)
        m["handle"], m["name"] = "someone.else", "someone"
        b = compose.board("editorial-quiet", months_later(m, 1))
        self.assertEqual(b["handle"], "@someone.else")
        words = " ".join(on_screen(b))
        self.assertNotIn(self.month["handle"], words)
        self.assertIn("oct 13", words)
        self.assertIn("see you in november", words)


class Asked(unittest.TestCase):
    """What the person asked for (taste.json `ask`): their top posts with their counts, the reel's length, and the series."""

    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()

    def checked(self, m):
        b = compose.board("editorial-quiet", m)
        bad = [f"{r['check']}: {r['detail']}" for r in storyboard.check_board(b, m) if not r["ok"]]
        self.assertFalse(bad)
        return b

    def test_asked_for_their_numbers_each_card_shows_its_count_and_the_moments_stay_the_story(self):
        counts = their_counts()
        b = self.checked(asked(self.month, counts=True))
        top = [2, 13, 28]
        self.assertEqual(sorted(c["day"] for c in b["reel"]["cards"]), top)
        said = lambda d: f"{counts[d][0]:,} likes  ·  {counts[d][1]:,} comments"
        for c in b["reel"]["cards"]:
            self.assertEqual([x["text"].lower() for x in c["lines"] if x.get("name") == "count"], [said(c["day"])])
        for c, day in zip(b["beats"], top):
            self.assertEqual([x["text"].lower() for x in c["lines"] if x.get("name") == "count"], [said(day)])
        # likes and comments never choose a moment: a pick that leaves out the posts with the most stands
        mine = compose.board("editorial-quiet", asked(picked(self.month, [{"day": 2}, {"day": 9}, {"day": 21}, {"day": 24}]), counts=True))
        self.assertEqual(sorted(c["day"] for c in mine["reel"]["cards"]), [2, 9, 21, 24])
        # unasked, no figure reaches the screen
        words = " ".join(on_screen(compose.board("editorial-quiet", self.month)))
        self.assertFalse([n for n in their_numbers() if re.search(rf"\b{n}\b", words)])

    def test_a_count_reads_on_its_ground_and_lands_with_its_beats_rise_in_every_look(self):
        from compose import look
        m = asked(self.month, counts=True)
        for name in compose.TRIO:
            b = compose.board(name, m)
            colors = b["reel"]["colors"]
            for c in b["reel"]["cards"]:
                for x in (x for x in c["lines"] if x.get("name") == "count"):
                    self.assertGreaterEqual(look.contrast(colors[x["color"]], colors["bg"]), 4.5, (name, x["color"], colors))
                    self.assertLessEqual(x["tally"]["at"] + x["tally"]["beats"], sum(c["rise"]) + 1e-6, (name, c["rise"], x["tally"]))
            for c in b["beats"]:
                for x in (x for x in c["lines"] if x.get("name") == "count"):
                    self.assertGreaterEqual(look.contrast(colors[x["color"]], colors["bg"]), 4.5, (name, c["id"], x["color"]))

    def test_a_reel_asked_for_15_s_runs_15_s(self):
        for m in (asked(picked(self.month), seconds=15), asked(self.month, seconds=15, counts=True),
                  asked(picked(self.month, [{"day": 13, "peak": True}, {"day": 17}, {"day": 28}]), seconds=15)):
            r = self.checked(m)["reel"]
            self.assertEqual(r["frames"], 450)
            self.assertAlmostEqual(r["end"], 15 * r["bpm"] / 60, places=2)
            span = {c["day"]: c["leave"] - c["arrive"] for c in r["cards"]}
            if any(c["peak"] for c in r["cards"]):
                peak = next(c["day"] for c in r["cards"] if c["peak"])
                self.assertTrue(all(span[peak] > v for d, v in span.items() if d != peak), span)

    def test_a_moment_with_no_photograph_is_big_type_on_the_ground(self):
        m = copy.deepcopy(self.month)
        for p in m["posts"]:
            if p["day"] in (13, 17):
                p["photo"] = None
        top = [{"day": 5}, {"day": 13, "peak": True}, {"day": 17}, {"day": 28}]
        for ask, moments, big in (({}, PICKED, None), ({"counts": True}, top, ["1,180", "likes  ·  96 comments"])):
            b = self.checked(asked(picked(m, moments), **ask))
            cards = {c["day"]: c for c in b["reel"]["cards"]}
            self.assertEqual([d for d, c in cards.items() if c["file"] is None], [13, 17])
            for d in (13, 17):
                rows = [x for x in cards[d]["lines"] if x.get("name") == "big"]
                self.assertTrue(rows and all(x["face"] == "display" for x in rows), d)
                story = b["beats"][[x["day"] for x in moments].index(d)]
                self.assertEqual([x["file"] for x in story["bands"]], [None])
                # the type is up within the card's first frames, so the card never opens on bare ground
                self.assertLessEqual(min(x["at"] for x in story["lines"] if x.get("name") == "big"), 0.2)
                self.assertEqual(" ".join(x["text"] for x in story["lines"] if x.get("name") == "big"), " ".join(x["text"] for x in rows))
            rows = [x["text"] for x in cards[13]["lines"] if x.get("name") == "big"]
            if big:
                self.assertEqual(rows, big)
            else:
                self.assertEqual(" ".join(rows), next(p["caption"] for p in m["posts"] if p["day"] == 13))
        # the reel opens on the peak's type when the peak has no photograph
        first = compose.board("editorial-quiet", picked(m))["reel"]["cards"][0]
        self.assertEqual((first["day"], first["file"]), (13, None))
        self.assertTrue([x for x in first["lines"] if x.get("name") == "big"])

    def test_the_series_is_made_only_when_asked(self):
        self.assertFalse(compose.board("editorial-quiet", self.month)["ask"]["series"])
        self.assertTrue(compose.board("editorial-quiet", asked(self.month, series=True))["ask"]["series"])


class Frames(unittest.TestCase):
    def test_shot_frames_round_as_the_browser_does(self):
        # a shot boundary on a half frame is the later frame in the composition, so the still named for it is the frame
        # whose bounds check runs
        self.assertEqual([studio.jround(x) for x in (37.5, 112.5, 262.5, 18.75)], [38, 113, 263, 19])
        board = {"bpm": 96, "fps": 30, "beats": [{"id": "hook", "frames": 450, "shots": [{"beats": 6}, {"beats": 2}, {"beats": 16}]}]}
        self.assertEqual([(s["a"], s["e"]) for s in studio.shots(board)], [(0, 113), (113, 150), (150, 450)])


class Variants(unittest.TestCase):
    """Months the board builder composes, each passing the board checks."""

    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()

    def compose_ok(self, m, want):
        b = compose.board("editorial-quiet", m)
        self.assertEqual(len(b["beats"]), want)
        self.assertEqual(len(b["reel"]["cards"]), want)
        bad = [f"{r['check']}: {r['detail']}" for r in storyboard.check_board(b, m) if not r["ok"]]
        self.assertFalse(bad)

    def test_three_moments(self):
        self.compose_ok(picked(self.month, [{"day": 13, "peak": True}, {"day": 17}, {"day": 28}]), 3)

    def test_the_next_months(self):
        for k in (1, 3, 4, 8):
            self.compose_ok(months_later(picked(self.month), k), 4)

    def test_few_and_many_posts(self):
        for n in (3, 4, 7, 12, 20):
            self.compose_ok(with_posts(self.month, n), 3)

    def test_no_handle(self):
        m = picked(self.month)
        m["handle"] = ""
        self.compose_ok(m, 4)

    def test_no_captions(self):
        m = picked(self.month)
        for p in m["posts"]:
            p["caption"] = ""
        self.compose_ok(m, 4)

    def test_no_photographs(self):
        # a month told in words alone is a full reel of type cards and a closer of its words, with no wall and no
        # photograph named anywhere on its board
        m = picked(self.month, [{"day": 13, "peak": True}, {"day": 17}, {"day": 28}])
        for p in m["posts"]:
            p["photo"] = None
        for x in m["moments"]:
            x["photo"] = None
        self.compose_ok(m, 3)
        r = compose.board("editorial-quiet", m)["reel"]
        self.assertEqual(r["closer"]["tiles"], [])
        self.assertEqual([c["file"] for c in r["cards"]], [None, None, None])
        self.assertEqual(r["frames"], round(r["end"] * r["fps"] * 60 / r["bpm"]))
        said = " ".join(b["reveals"] + " " + b["carries"] for b in r["beats"])
        self.assertNotIn("photograph", said)
        # a clip is a photograph brought to life, so a type card asks for none
        self.assertEqual(r["clips"], [])


class NoFixtureValues(unittest.TestCase):
    """The handle, the month and their moments come from the account and the request, never from the kit's code."""

    def test_code_carries_none_of_the_fixtures_values(self):
        pat = re.compile(r"\bines\b|ines\.photo|september|[\"']sep[\"']|sourdough|wedding|marta|aveleda|coliseu|matosinhos|joana|\b1180\b", re.I)
        files = [p for p in list(fixture.SCRIPTS.rglob("*.py")) + list((fixture.KIT / "motion" / "studio").rglob("*"))
                 if p.is_file() and "__pycache__" not in p.parts]
        hits = [f"{p.relative_to(fixture.KIT)}:{i + 1}" for p in files for i, ln in enumerate(p.read_text().splitlines())
                if pat.search(ln) and "january" not in ln]  # the table of month names is not a fixture value
        self.assertGreater(len(files), 10)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
