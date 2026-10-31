"""The board builder on an invented year: each look's board in every format lays out inside the rules of the frame, its
cards are the year's moments in the two people's own words, each holding as long as its photograph asks, the film runs
the length the person asked for at any tempo, the photographs that show the one it is for lead and close it, and thin
years still make the film; and every card's beat hands its move the middle of the photograph's subject.

USAGE (from anywhere; needs Pillow and ffmpeg, the same as the pipeline):
    python3 -m unittest discover -s S/tests -p 'test_boards.py'

The year is evals/fixtures/make_person.py with drawn photographs, run through gather.py and research.py in a
temporary workspace. The thin years are that year with the named one's comments cut to three, with their own posts
removed, with no comment of theirs at all, and an agent's curation of four and of nine moments.
"""
import argparse
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "scripts"))
import compose  # noqa: E402
import wall  # noqa: E402

STYLE = "scrapbook"  # the board most tests lay out; the per-look tests name their own


def look(style):
    """The kit's story with `style`'s card faces in use: its timing, its faces and its measures."""
    wall.use(style)
    return wall


def faces():
    """The font file each voice is set in, in the look in use."""
    return {v: wall.face_of(v)["file"] for v in wall.VOICES}

WS = None
B = None
storyboard = None  # imported once the workspace has a run, as it reads the run folder on import
SUBJECTS = {}  # photo file name: the subject box the fixture carries for it, as the storyboard agent records it


def setUpModule():
    global WS, B, storyboard
    WS = Path(tempfile.mkdtemp(prefix="bt-boards-", dir=os.environ.get("TMPDIR")))
    env = dict(os.environ)
    env["TRIBUTE_PHOTOS"] = ""  # the drawn year
    run = lambda *a: subprocess.run([sys.executable, *map(str, a)], cwd=WS, env=env, check=True, capture_output=True, text=True)
    run(S / "evals" / "fixtures" / "make_person.py", WS)
    run(S / "scripts" / "gather.py", "--door", "instagram_account=closed: none in the test", "--door", "browser=closed: none in the test")
    run(S / "scripts" / "research.py", "--who", "@dani.reyes", "--occasion", "dani's 30th birthday")
    B = WS / "build" / (WS / "build" / "latest").read_text().strip()
    spec = importlib.util.spec_from_file_location("make_person", S / "evals" / "fixtures" / "make_person.py")
    mp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mp)
    SUBJECTS.update(mp.subjects_by_file(WS, B))
    os.chdir(WS)
    import storyboard as sb
    storyboard = sb


def tearDownModule():
    os.chdir(S)
    shutil.rmtree(WS, ignore_errors=True)


def year(name, cut):
    """A copy of the run folder whose shared.json and picks.json `cut` has thinned; returns its Ctx."""
    d = WS / "build" / name
    if not d.exists():
        shutil.copytree(B, d, symlinks=True)
        shared = json.loads((B / "shared.json").read_text())
        picks = json.loads((B / "picks.json").read_text())
        cut(shared, picks)
        (d / "shared.json").write_text(json.dumps(shared))
        (d / "picks.json").write_text(json.dumps(picks))
    return compose.Ctx(d)


def curated(name, moments):
    """A copy of the run folder whose taste.json names `moments` as the year's, as the agent curates them; returns its Ctx."""
    d = WS / "build" / name
    if not d.exists():
        shutil.copytree(B, d, symlinks=True)
        taste = json.loads((B / "taste.json").read_text())
        taste["moments"] = moments
        taste["written_by"] = "the test"
        (d / "taste.json").write_text(json.dumps(taste))
    return compose.Ctx(d)


def three_comments(shared, picks):
    friend = shared["who"]["handle"]
    keep = [e for e in sorted(shared["exchanges"], key=lambda e: e["ts"]) if e["by"] == friend][:3]
    texts = {e["text"] for e in keep}
    shared["exchanges"] = [e for e in shared["exchanges"] if e["by"] != friend or e["text"] in texts]
    shared["pairs"] = [p for p in shared["pairs"] if p["answer"]["text"] in texts]


def no_posts_of_theirs(shared, picks):
    shared["items"] = [x for x in shared["items"] if x["from"] != "theirs"]
    shared["pairs"] = [p for p in shared["pairs"] if not p["post"].startswith("feed")]
    shared["exchanges"] = [e for e in shared["exchanges"] if not str(e.get("post") or "").startswith("feed")]
    picks["items"] = [r for r in picks["items"] if r["from"] != "theirs"]


def no_comments(shared, picks):
    friend = shared["who"]["handle"]
    shared["exchanges"] = [e for e in shared["exchanges"] if e["by"] != friend]
    shared["pairs"] = []


def boxed(board):
    """The board with each photograph's subject box recorded, the step the storyboard agent does by eye."""
    for r in board["photos"].values():
        r["subject"] = SUBJECTS[Path(r["file"]).name]
    return board


def drafted():
    return json.loads((B / "taste.json").read_text())["moments"]


class Moments(unittest.TestCase):
    """research.py drafts the year's moments from the captions, the people, the places and the dates, never from counts."""

    def test_research_drafts_the_moments_from_their_captions(self):
        ms = drafted()
        self.assertGreaterEqual(len(ms), 12)
        shared = json.loads((B / "shared.json").read_text())
        captions = [storyboard.fold_words(x.get("caption")) for x in shared["items"]]
        for m in ms:
            self.assertTrue({"post", "date", "name", "line", "place", "people", "talk", "peak"} <= set(m), m)
            self.assertFalse({"likes", "comments", "saves", "count", "score"} & set(m), m)
            self.assertIn(m["name"].lower(), m["line"].lower())
            self.assertTrue(any(c.startswith(storyboard.fold_words(m["line"])) for c in captions), m["line"])
            self.assertFalse(m["peak"])
        self.assertEqual([m["date"] for m in ms], sorted(m["date"] for m in ms))
        first = ms[0]
        self.assertEqual((first["post"], first["name"], first["people"]), ("post:0", "first coffee of the year", ["dani.reyes"]))
        porto = next(m for m in ms if m["post"] == "post:21")
        self.assertEqual((porto["place"], porto["name"]), ("porto", "porto"))
        tulips = next(m for m in ms if m["post"] == "feed:1")
        self.assertEqual([t["by"] for t in tulips["talk"]], ["maren.okafor", "dani.reyes"])
        self.assertFalse([m for m in ms if m["post"].startswith("post:136")], "the occasion post is the hook, not a moment")
        self.assertIn("first coffee of the year", (B / "taste.draft.md").read_text())

    def test_a_tagged_photograph_with_no_caption_is_a_wordless_moment(self):
        shared = json.loads((B / "shared.json").read_text())
        x = next(x for x in shared["items"] if x["id"] == drafted()[3]["post"])
        x["caption"] = ""
        m = next((m for m in compose.draft_moments(shared) if m["post"] == x["id"]), None)
        self.assertIsNotNone(m, "a shared photograph with no caption is still a moment of the year")
        self.assertEqual((m["name"], m["line"]), ("", ""))

    def test_a_number_keeps_its_point_and_its_colon(self):
        self.assertEqual(compose.moment_name("6:30am on the ridge with @dani.reyes, cold"), "6:30am on the ridge")
        self.assertEqual(compose.moment_name("50.5 km on foot. never again"), "50.5 km on foot")
        self.assertEqual(compose.moment_name("done: the end"), "done")

    def test_a_long_name_gives_its_with_to_the_line(self):
        line = "front row in marrakech with my favorite travel partner"
        self.assertEqual(compose.moment_name(line), "front row in marrakech")
        self.assertEqual(compose.moment_words(line, "front row in marrakech"), "with my favorite travel partner")
        self.assertEqual(compose.moment_name("dinner with the oaxaca crew"), "dinner with the oaxaca crew")
        line = "dani turns 30 on october 24 and i'm already planning the table @dani.reyes"
        self.assertEqual(compose.moment_name(line), "dani turns 30 on october 24")
        self.assertEqual(compose.moment_words(compose.plain(line), "dani turns 30 on october 24"),
                         "and i'm already planning the table")
        self.assertEqual(compose.moment_name("bread and butter for dinner"), "bread and butter for dinner")

    def test_a_line_of_tags_after_the_name_leaves_no_words(self):
        self.assertEqual(compose.moment_words("dinner with @sam_and_june and @dani.reyes #earthtones", "dinner"), "")
        self.assertEqual(compose.moment_words("dinner with @a, @b & @c", "dinner"), "")
        self.assertEqual(compose.moment_words("oaxaca with @dani.reyes, she picked the tomatoes", "oaxaca"),
                         "she picked the tomatoes")

    def test_the_words_check_reads_emoji_as_the_screen_sets_them(self):
        kit = look("scrapbook")
        for c in ("love \u2764\ufe0f it", "\U0001F469\u200d\U0001F4BB coding all night", "\U0001F170 day one"):
            self.assertIn(storyboard.fold_words(compose.plain(c)), storyboard.fold_words(c), repr(c))
            self.assertIn(kit.fold(compose.plain(c)), kit.fold(c), repr(c))

    def test_a_basename_two_files_share_resolves_to_nothing(self):
        import gather
        root = WS / "media-twins"
        for d, name in (("a", "IMG_1.jpg"), ("b", "IMG_1.jpg"), ("a", "IMG_2.jpg")):
            (root / "media" / d).mkdir(parents=True, exist_ok=True)
            (root / "media" / d / name).write_bytes(b"x")
        m = gather.Media(root)
        self.assertIsNone(m.resolve("posts/IMG_1.jpg"), "two files share the name, so the name alone picks neither")
        self.assertEqual(m.resolve("media/b/IMG_1.jpg"), str((root / "media" / "b" / "IMG_1.jpg").resolve()))
        self.assertEqual(m.resolve("posts/IMG_2.jpg"), str((root / "media" / "a" / "IMG_2.jpg").resolve()))


class Boards(unittest.TestCase):
    def film(self, ctx, label):
        pool = storyboard.their_words(ctx)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        for fmt in compose.FORMATS:
            s = compose.lay(board, fmt)
            with self.subTest(year=label, fmt=fmt):
                self.assertEqual(compose.bounds(s, board), [])
                if fmt == "reel":
                    self.assertEqual(storyboard.cut_issues(board, s), [])
                    self.assertEqual(storyboard.unwritten(s, board, ctx, pool), [])
        return board

    def test_full_year(self):
        board = self.film(compose.Ctx(B), "full")
        cards = [b for b in board["beats"] if b["form"] == "moment"]
        self.assertGreaterEqual(len(cards), 8)
        self.assertEqual([b["date"] for b in cards], sorted(b["date"] for b in cards))
        self.assertTrue(all(b["name"] for b in cards))
        self.assertFalse([b for b in board["beats"] if "value" in b])
        self.assertEqual(board["beats"][-1]["form"], "closer")

    def test_three_comments(self):
        self.film(year("three", three_comments), "three comments")

    def test_no_posts_of_theirs(self):
        board = self.film(year("mine-only", no_posts_of_theirs), "no posts of theirs")
        self.assertFalse([p for p in board["photos"] if p.startswith("feed")])

    def test_no_comments(self):
        self.film(year("silent", no_comments), "no comments")

    def test_a_photograph_with_no_caption_is_a_wordless_card(self):
        pid = drafted()[3]["post"]

        def blank(shared, picks):
            for x in [*shared["items"], *picks["items"]]:
                if x["id"] == pid:
                    x["caption"] = ""
        board = self.film(year("wordless", blank), "a wordless moment")
        card = next((b for b in board["beats"] if b.get("post") == pid), None)
        self.assertIsNotNone(card, "the photograph is shown as a card of its own")
        self.assertEqual((card["name"], card["words"]), ("", ""))
        s = compose.lay(board, "reel")
        self.assertEqual(next(c for c in s["film"]["cards"] if c["post"] == pid)["head"], [])

    def test_the_hook_is_a_still_photograph_and_carries_no_caption(self):
        def no_photo(shared, picks):
            picks["items"] = [r for r in picks["items"] if r["id"] != "post:136"]

        def a_video(shared, picks):
            for r in picks["items"]:
                if r["id"] == "post:136":
                    r["video"] = r["src"]
        for label, cut in (("occasion-no-photo", no_photo), ("occasion-video", a_video)):
            ctx = year(label, cut)
            board = compose.plan(ctx, STYLE)
            hook = board["beats"][0]
            base = hook["post"].partition("#")[0]
            with self.subTest(label):
                self.assertNotEqual(base, "post:136")
                self.assertFalse(ctx.rows[base].get("video"))
                self.assertEqual(hook["words"], "", "the hook is the lockup alone: the tag, the figure, the day")
                self.assertNotIn(base, [b.get("post") for b in board["beats"][1:]])

    def test_a_thin_year_keeps_every_moment_the_agent_curated(self):
        for n in (4, 9):
            ms = [dict(m) for m in drafted()[:n]]
            board = compose.plan(curated(f"thin-{n}", ms), STYLE)
            cards = [b for b in board["beats"] if b["form"] == "moment"]
            self.assertEqual([b["post"] for b in cards], [m["post"] for m in ms], n)

    def chosen(self):
        """Eight of the drafted moments, as an agent curates them: one renamed in the caption's own words, one renamed in
        words nobody wrote, one marked as the peak of the year."""
        ms = [dict(m) for m in drafted()[:16:2]]
        ms[0]["name"] = "first coffee"
        ms[1]["name"] = "a name nobody wrote"
        ms[5]["peak"] = True
        return ms

    def test_the_cards_are_the_moments_the_taste_names(self):
        ms = self.chosen()
        board = self.film(curated("curated", ms), "curated")
        cards = [b for b in board["beats"] if b["form"] == "moment"]
        self.assertEqual([b["post"] for b in cards], [m["post"] for m in ms])
        self.assertEqual(cards[0]["name"], "first coffee")
        self.assertEqual(cards[1]["name"], drafted()[2]["name"], "a name not in the caption's own words falls back to the draft's")

    def test_a_card_holds_as_long_as_its_photograph_asks_and_the_peak_longest(self):
        ms = self.chosen()
        board = compose.plan(curated("curated", ms), STYLE)
        kit = look("scrapbook")
        cards = [b for b in board["beats"] if b["form"] == "moment"]
        self.assertGreater(len({b["hold"] for b in cards}), 2, "the holds follow the photographs, not a grid")
        slow = [b for b in cards if not b["run"]]
        for a, b in zip(slow, slow[1:]):
            self.assertEqual(a["hold"] < b["hold"], a["pulses"] < b["pulses"], (a["id"], b["id"]))
        peak = cards[5]
        self.assertTrue(peak["peak"])
        self.assertEqual(peak["pulses"], max(b["pulses"] for b in cards))
        self.assertGreaterEqual(peak["hold"], kit.PEAK * max(b["hold"] for b in cards if b is not peak) - 0.01)
        self.assertIn(peak["id"], board["rest"])
        m = dict(drafted()[0], talk=[], people=[])
        self.assertGreater(kit.hold_of(dict(m, talk=[{"by": "dani.reyes", "text": "the best one yet, every single time"}]), 2),
                           kit.hold_of(m, 2), "words to read hold the photograph longer")
        self.assertGreater(kit.hold_of(dict(m, people=["a", "b", "c"]), 2), kit.hold_of(m, 2), "a crowd holds longer")
        self.assertGreater(kit.hold_of(m, 2), kit.hold_of(m, 1), "a photograph that tags them holds longer")

    def test_the_words_are_the_moment_and_their_own_lines(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "3"))
        s = compose.lay(board, "reel")
        kit = look("scrapbook")
        pool = [storyboard.fold_words(p) for p in storyboard.their_words(ctx)]
        beats = {b["id"]: b for b in board["beats"]}
        hook, cards = s["film"]["cards"][0], s["film"]["cards"][1:]
        self.assertEqual(hook["head"][0]["text"], board["wish"]["number"])
        for c in cards:
            b = beats[c["key"]]
            self.assertEqual(" ".join(l["text"] for l in c["head"]), b["name"])
            self.assertTrue(all(l["file"] == faces()["display"] for l in c["head"]))
            self.assertFalse([l for l in c["lines"] if l.get("name") in ("date", "tag") or l["text"].isdigit()], c["key"])
            talk = [l for l in c["lines"] if str(l.get("name") or "").startswith("talk")]
            self.assertEqual(len(talk) > 0, bool(b["talk"]), c["key"])
            for l in talk:
                self.assertTrue(any(storyboard.fold_words(l["text"]) in p for p in pool), l["text"])
                by = next(t for t in b["talk"] if storyboard.fold_words(l["text"]) in storyboard.fold_words(t["text"]))["by"]
                self.assertEqual(l["file"], faces()["theirs" if by == ctx.who else "mine"], l["text"])

    def test_the_closer_carries_the_age_and_no_count(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "4"))
        s = compose.lay(board, "reel")
        self.assertNotIn("ticks", {c["kind"] for c in s["sound"]})
        number = board["wish"]["number"]
        self.assertEqual(s["film"]["closer"]["big"]["text"], number)
        self.assertEqual(s["film"]["closer"]["last"]["text"], number[-1])
        story = compose.story(board)
        self.assertIn(number, story["closer"])
        self.assertNotIn("counter", " ".join(story.values()))

    def test_the_wish_reads_on_its_bands_over_any_wall(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "4"))
        kit = look("scrapbook")
        for fmt in compose.FORMATS:
            cl = compose.lay(board, fmt)["film"]["closer"]
            with self.subTest(fmt=fmt):
                self.assertEqual({l["color"] for l in cl["lines"]}, {"paper"})
                self.assertEqual(len(cl["bands"]), 2)
                for band, group in zip(cl["bands"], (cl["lines"][:1], cl["lines"][1:])):
                    ys = [q[1] for l in group for q in kit.hull(l)]
                    self.assertLessEqual(band[0], min(ys) - kit.BAND + 0.1, group)
                    self.assertGreaterEqual(band[1], max(ys) + kit.BAND - 0.1, group)
                big = kit.hull(cl["big"])
                self.assertLess(cl["bands"][0][1], min(q[1] for q in big), "the title's band stops over the age")
                self.assertGreater(cl["bands"][1][0], cl["big"]["y"], "the date's band starts under the age's baseline")

    def test_a_card_takes_the_light_out_under_its_type_alone(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "4"))
        kit = look("scrapbook")
        for fmt in compose.FORMATS:
            s = compose.lay(board, fmt)
            for c in s["film"]["cards"]:
                xs = [q[0] for l in [*c["head"], *c["lines"]] for q in kit.hull(l)]
                with self.subTest(fmt=fmt, card=c["key"]):
                    if not xs:
                        self.assertIsNone(c["type_x"])
                        continue
                    self.assertAlmostEqual(c["type_x"][0], min(xs), delta=0.06)
                    self.assertAlmostEqual(c["type_x"][1], max(xs), delta=0.06)
                    self.assertLess(c["type_x"][1] - c["type_x"][0], s["format"]["width"], "the shade spans the type, not the frame")

    def test_the_wall_has_a_cell_for_every_photograph_and_no_more(self):
        kit = look("scrapbook")
        for n, rows in ((3, [2, 2]), (4, [2, 3]), (5, [3, 3]), (8, [3, 3, 3])):
            ms = [dict(m) for m in drafted()[:n]]
            ctx = curated(f"wall-{n}", ms)
            board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
            for fmt in compose.FORMATS:
                s = compose.lay(board, fmt)
                W, H = s["format"]["width"], s["format"]["height"]
                slots = [c["slot"] for c in s["film"]["cards"]]
                with self.subTest(photos=n + 1, fmt=fmt):
                    self.assertEqual(len(slots), n + 1)
                    tops = sorted({sl[0][1] for sl in slots})
                    self.assertEqual([sum(sl[0][1] == y for sl in slots) for y in tops], rows)
                    for y in tops:
                        row = sorted((sl for sl in slots if sl[0][1] == y), key=lambda sl: sl[0][0])
                        self.assertAlmostEqual(row[0][0][0], kit.MARGIN, delta=0.2)
                        self.assertAlmostEqual(row[-1][1][0], W - kit.MARGIN, delta=0.2)
                    self.assertAlmostEqual(min(sl[0][1] for sl in slots), kit.MARGIN, delta=0.2)
                    self.assertAlmostEqual(max(sl[2][1] for sl in slots), H - kit.MARGIN, delta=0.2)
                    self.assertGreater(kit.MARGIN, kit.GUTTER, "the margin round the wall keeps its outer cells whole")
                    for c in s["film"]["cards"]:
                        (x0, y0), _, (x1, y1), _ = c["slot"]
                        kr = [(x0 - c["T"]["o"][0]) / c["T"]["s"], (y0 - c["T"]["o"][1]) / c["T"]["s"]]
                        px, py, pw, ph = c["place"]
                        self.assertGreaterEqual(kr[0], px - 0.5, "the cell shows the photograph, never past it")
                        self.assertGreaterEqual(kr[1], py - 0.5)
                        self.assertLessEqual(kr[0] + (x1 - x0) / c["T"]["s"], px + pw + 0.5)
                        self.assertLessEqual(kr[1] + (y1 - y0) / c["T"]["s"], py + ph + 0.5)

    def test_a_sound_lands_where_a_beat_lands_and_nowhere_else(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "5"))
        cues = compose.lay(board, "reel")["sound"]
        self.assertLessEqual(len(cues), len(board["beats"]) + 4)
        self.assertEqual({c["kind"] for c in cues}, {"hit", "riser", "impact", "stop"})
        # one hit where each card lands (the hook's age, each moment's name) and the closer's last figure punched home
        self.assertEqual(sum(c["kind"] == "hit" for c in cues), len(board["beats"]))
        self.assertEqual([c["kind"] for c in cues][-3:], ["impact", "hit", "stop"])

    def test_the_shared_effects_land_on_the_boards_cues_on_the_musics_grid(self):
        import sfx
        import wall
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "5"))
        film = {**compose.fit(board, 112), "sound": compose.lay(board, "reel", 112)["sound"]}
        tm = wall.times(film)
        cards = [b for b in film["beats"] if b["form"] == "moment"]
        for b in cards:
            self.assertEqual(tm[b["id"]]["at"] * wall.GRID % 1, 0, f"{b['id']} starts on a quarter beat")
        ev, _ = sfx.events(wall.effects_board(film), 112)
        q = 60 / 112 / wall.GRID
        for t, kind in ev:
            self.assertAlmostEqual(t / q, round(t / q), places=4, msg=f"{kind} at {t} s is on the music's grid")
        kinds = [k for _, k in ev]
        cues = {c["kind"]: c["at"] * 60 / 112 for c in film["sound"] if c["kind"] in ("riser", "impact", "stop")}
        self.assertEqual(ev[0], (round(round(tm["hook"]["cut"] * 60 / 112 / q) * q, 6), "impact"), "the age slams as the hook lands")
        self.assertEqual(sum(k in ("air", "sweep", "bright") for k in kinds), sum(1 for b in cards if b.get("transition")))
        self.assertEqual(kinds.count("bright"), 1, "the bright sweep once a film")
        self.assertEqual(sum(k in ("shutter", "pop") for k in kinds), len(cards), "each photograph lands on a shutter or its mark's pop")
        self.assertEqual(kinds.count("riser"), 1)
        slam = next(t for t, k in ev if k == "riser")
        self.assertAlmostEqual(slam, cues["impact"], delta=q / 2, msg="the riser runs into the sheet's slam")
        self.assertEqual(kinds[-3:], ["impact", "riser", "impact"], "the slam, then the last figure punched home")
        self.assertLess(ev[-1][0], cues["stop"], "nothing sounds from the stop on")

    def test_master_writes_the_films_length_at_the_musics_tempo_into_the_storyboard(self):
        import argparse
        import _env
        import music
        d = WS / "build" / "mastered"
        shutil.copytree(B, d, symlinks=True)
        ctx = compose.Ctx(d)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "6"))
        md = d / "storyboards" / "6" / "storyboard.md"
        secs = round(compose.seconds_of(compose.fit(board, 112)["beats"], 112), 3)
        with mock.patch.object(_env, "_RUN", d), mock.patch.object(music, "MUSIC", d / "music"):
            storyboard.write_md(board, md)  # drafted at the board's own tempo
            (d / "music").mkdir()
            src = d / "music" / "source.wav"
            subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=f=220:d=70", "-ar", "48000", str(src)], check=True)
            _env.write_json(d / "music.json", {"file": str(src), "origin": "made by the test", "bpm": 112})
            _env.write_json(d / "film.json", {**compose.fit(board, 112), "seconds": secs, "sound": compose.lay(board, "reel", 112)["sound"]})
            music.cmd_master(argparse.Namespace(seconds=None))
        line = next(x for x in md.read_text().splitlines() if x.startswith("- length: "))
        self.assertTrue(line.startswith(f"- length: {secs:.1f} s ({board['length_from']}) at 112 bpm, "), line)
        self.assertLessEqual(abs(secs - board["length"]), 1)
        # the shared effects beside the master, under the music by FX_UNDER_BED_LU, silent from the stop, and the
        # music's energy a frame
        m = _env.read_json(d / "music.json")
        self.assertGreaterEqual(m["master_lufs"] - m["fx_lufs"], music.FX_UNDER_BED_LU - 0.2)
        self.assertEqual(m["sound_cues"], len(m["effects"]))
        energy = _env.read_json(d / "music" / "energy.json")
        self.assertEqual((energy["fps"], len(energy["rms"])), (compose.FPS, int(secs * compose.FPS)))
        stop = next(c["at"] for c in _env.read_json(d / "film.json")["sound"] if c["kind"] == "stop") * 60 / 112
        tail = subprocess.run([_env.ffmpeg(), "-v", "info", "-ss", f"{stop + music.STOP_FADE + 0.01:.3f}", "-i", m["effects_wav"],
                               "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
        self.assertIn("max_volume: -91", tail, "the effects are silent from the stop on")

    def reel(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "2"))
        return ctx, board, copy.deepcopy(compose.lay(board, "reel"))

    def test_invented_line_is_refused(self):
        ctx, board, s = self.reel()
        words = next(l for c in s["film"]["cards"] for l in c["lines"] if str(l.get("name") or "").startswith("words"))
        words["text"] = "words nobody wrote"
        self.assertEqual(len(storyboard.unwritten(s, board, ctx)), 1)

    def test_bounds_sees_an_edge_that_cuts_its_subject(self):
        ctx, board, s = self.reel()
        c = s["film"]["cards"][1]
        self.assertFalse([i for i in compose.bounds(s, board) if "cuts the subject" in i])
        x0, y0, x1, y1 = c["subject"]
        across = y0 + 0.8 * (y1 - y0) if c["side"] == "over" else y0 + 0.2 * (y1 - y0)
        c["line"], c["tilt"] = [across, across], 0
        self.assertTrue([i for i in compose.bounds(s, board) if f"{c['key']}: the edge cuts the subject" in i])

    def test_bounds_sees_a_line_outside_the_safe_area(self):
        ctx, board, s = self.reel()
        c = s["film"]["cards"][2]
        c["head"][0]["y"] = s["format"]["height"] - 40
        self.assertTrue([i for i in compose.bounds(s, board) if f"{c['key']}: '{c['head'][0]['text'][:30]}' leaves the safe area" in i])


class Label(unittest.TestCase):
    """A moment's date is handed to its move only where the move's print lands clear of the people."""

    def test_a_subject_in_the_label_band_takes_no_label_and_one_above_it_takes_the_date(self):
        f = compose.Frame("reel")
        moment = {"form": "moment", "date": "2026-03-09"}
        low = [100.0, 0.55 * f.H, 900.0, 0.95 * f.H]
        high = [100.0, 0.1 * f.H, 900.0, 0.5 * f.H]
        self.assertEqual(wall.label_of(f, moment, low), "")
        self.assertEqual(wall.label_of(f, moment, high), compose.when("2026-03-09", False))
        self.assertEqual(wall.label_of(f, {"form": "hook", "date": "2026-03-09"}, high), "")

    def test_no_laid_card_prints_its_label_over_its_subject(self):
        ctx = compose.Ctx(B)
        st = compose.lay(boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1")), "reel")
        cards = {c["key"]: c for c in st["film"]["cards"]}
        top, foot = (k * st["format"]["height"] for k in wall.LABEL_BAND)
        for b in st["beats"]:
            if b["label"]:
                sub = cards[b["id"]]["subject"]
                self.assertFalse(sub[3] > top and sub[1] < foot, b["id"])


def occasion(name, words):
    """A copy of the run folder whose occasion is the one the person names in `words`, read with the same captions
    research read, in shared.json and taste.json alike, as research.py writes them; returns its Ctx."""
    import datetime as dt
    import shared as shared_py
    d = WS / "build" / name
    if not d.exists():
        shutil.copytree(B, d, symlinks=True)
        sh = json.loads((B / "shared.json").read_text())
        taste = json.loads((B / "taste.json").read_text())
        caps = [x["caption"] for x in sh["items"] if x["from"] == "mine" and x.get("caption")]
        occ = shared_py.occasion_of({"occasion": words}, caps, sh["who"]["first"], dt.date.today())
        sh["occasion"] = occ
        taste["occasion"] = {k: occ.get(k) for k in ("kind", "age", "years", "date", "label", "title")}
        (d / "shared.json").write_text(json.dumps(sh))
        (d / "taste.json").write_text(json.dumps(taste))
    return compose.Ctx(d)


def texts(s):
    """Every line a laid-out studio board sets: the cards' names, words and small lines, the closer's figure and wish."""
    cl = s["film"]["closer"]
    return [l["text"] for c in s["film"]["cards"] for l in [*c["head"], *c["lines"]]] + [cl["big"]["text"], cl["last"]["text"]] + \
        [l["text"] for l in cl["lines"]]


class Occasion(unittest.TestCase):
    """The hook's small line and the closer's figure come from the occasion the person names, and a thin year's first
    draft reaches the length band on its own."""

    def test_a_four_photograph_year_reaches_the_band_at_its_own_length(self):
        ms = [dict(m) for m in drafted()[:3]]
        for m in ms:
            m.pop("peak", None)
            m["talk"] = []
        ctx = curated("four-photos", ms)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        self.assertEqual(len([b for b in board["beats"] if b.get("post")]), 4, "the hook and three cards")
        lo, hi = compose.tempo_range(STYLE)
        for bpm in (lo, compose.tempo_of(STYLE), hi):
            with self.subTest(bpm=bpm):
                s = compose.lay(board, "reel", bpm)
                self.assertEqual(storyboard.cut_issues(board, s), [])
                secs = sum(x["frames"] for x in s["beats"]) / compose.FPS
                self.assertGreaterEqual(secs, compose.LENGTH[0])
                self.assertLessEqual(abs(secs - board["length"]), 1)
        self.assertEqual(board["length"], compose.LENGTH[0], "with no length asked a thin year runs the band's floor")

    def test_a_farewell_has_no_turns_and_no_age(self):
        ctx = occasion("farewell", "a farewell video for my coworker, their last day")
        self.assertEqual((ctx.occ["kind"], ctx.occ.get("age"), ctx.occ.get("date")), ("farewell", None, None),
                         "the birthday caption (dani turns 30 on october 24) adds nothing to a farewell")
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        self.assertEqual(board["wish"]["number"], "dani")
        for fmt in compose.FORMATS:
            s = compose.lay(board, fmt)
            with self.subTest(fmt=fmt):
                self.assertEqual(compose.bounds(s, board), [])
                said = texts(s)
                self.assertFalse([t for t in said if "turns" in t or "30" in t], said)
                hook = s["film"]["cards"][0]
                self.assertEqual(next(l["text"] for l in hook["lines"] if l.get("name") == "tag"), "dani · farewell")
                self.assertEqual(s["film"]["closer"]["big"]["text"], "dani")
                self.assertEqual(next(l["text"] for l in s["film"]["closer"]["lines"] if l.get("name") == "title"), "farewell, dani")
        self.assertNotIn("the age", " ".join(compose.story(board).values()))

    def test_an_anniversary_counts_its_years(self):
        ctx = occasion("anniversary", "our anniversary, five years")
        board = compose.plan(ctx, STYLE)
        s = compose.lay(boxed(compose.finish(ctx, board, "1")), "reel")
        self.assertEqual(s["film"]["closer"]["big"]["text"], "5")
        self.assertEqual(next(l["text"] for l in s["film"]["cards"][0]["lines"] if l.get("name") == "tag"), "dani · anniversary")
        self.assertFalse([t for t in texts(s) if "turns" in t])

    def test_no_day_given_states_no_day(self):
        import re
        d = WS / "build" / "no-day"
        if not d.exists():
            shutil.copytree(B, d, symlinks=True)
            for name, key in (("shared.json", "occasion"), ("taste.json", "occasion")):
                data = json.loads((B / name).read_text())
                data[key]["date"] = None
                (d / name).write_text(json.dumps(data))
        ctx = compose.Ctx(d)
        self.assertEqual((ctx.occ["kind"], ctx.occ.get("date")), ("birthday", None))
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        self.assertIsNone(board["wish"]["date"])
        self.assertIsNone(board["day"])
        day = re.compile(r"\b(mon|tue|wed|thu|fri|sat|sun) \d{1,2} [a-z]{3}\b|\b\d{4}-\d{2}-\d{2}\b")
        for fmt in compose.FORMATS:
            s = compose.lay(board, fmt)
            with self.subTest(fmt=fmt):
                self.assertEqual(compose.bounds(s, board), [])
                self.assertFalse([t for t in texts(s) if day.search(t)], texts(s))
                hook = s["film"]["cards"][0]
                self.assertEqual([l["name"] for l in hook["lines"] if l.get("name") in ("date", "tag")], ["tag"])
                self.assertEqual([l["text"] for l in s["film"]["closer"]["lines"]][1:], [f"from {board['wish']['from']}"])
        given = compose.lay(boxed(compose.finish(compose.Ctx(B), compose.plan(compose.Ctx(B), STYLE), "1")), "reel")
        self.assertTrue([t for t in texts(given) if day.search(t)], "a day the captions gave is still shown")

    def test_a_birthday_is_unchanged(self):
        ctx = compose.Ctx(B)
        self.assertEqual((ctx.occ["kind"], ctx.occ["age"]), ("birthday", 30))
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        s = compose.lay(board, "reel")
        hook = s["film"]["cards"][0]
        self.assertEqual(hook["head"][0]["text"], "30")
        self.assertEqual(next(l["text"] for l in hook["lines"] if l.get("name") == "tag"), "dani turns")
        self.assertEqual(s["film"]["closer"]["big"]["text"], "30")
        self.assertIn("30, the age,", compose.story(board)["hook"])


def asked(name, seconds, age=True):
    """A copy of the run folder whose ask names `seconds`, and, with `age` false, gives no age; returns its Ctx."""
    d = WS / "build" / name
    if not d.exists():
        shutil.copytree(B, d, symlinks=True)
        ask = json.loads((B / "ask.json").read_text())
        (d / "ask.json").write_text(json.dumps({**ask, "seconds": seconds}))
        if not age:
            for f in ("shared.json", "taste.json"):
                data = json.loads((B / f).read_text())
                data["occasion"] = {**data["occasion"], "age": None, "label": "Dani's birthday", "title": "happy birthday, dani"}
                (d / f).write_text(json.dumps(data))
    return compose.Ctx(d)


class Ask(unittest.TestCase):
    """The film runs the length the person asked for, the photographs that show the one it is for lead and close it,
    and with no age asked none is shown."""

    def test_the_film_runs_the_asked_length_at_every_tempo(self):
        for seconds in (20, 45, 60):
            ctx = asked(f"asked-{seconds}", seconds)
            board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
            self.assertEqual(board["length"], seconds)
            for bpm in (*compose.tempo_range(STYLE), compose.tempo_of(STYLE)):
                s = compose.lay(board, "reel", bpm)
                secs = sum(x["frames"] for x in s["beats"]) / compose.FPS
                with self.subTest(seconds=seconds, bpm=bpm):
                    self.assertLessEqual(abs(secs - seconds), 1, secs)
                    self.assertEqual(storyboard.cut_issues(board, s), [])

    def test_a_board_off_its_length_is_a_cut_issue(self):
        ctx = asked("asked-20", 20)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        s = compose.lay(board, "reel")
        self.assertEqual(storyboard.cut_issues(board, s), [])
        self.assertTrue([i for i in storyboard.cut_issues(dict(board, length=45), s) if "is not the board's 45 s" in i])

    def test_the_photographs_that_show_them_lead_and_close(self):
        ctx = asked("asked-20", 20)
        by = {x["id"]: x for x in ctx.items}
        cards = [b for b in compose.plan(ctx, STYLE)["beats"] if b["form"] in ("hook", "moment")]
        shows = [compose.shown(by[b["post"].split("#")[0]]) for b in cards]
        self.assertEqual(shows[0], 2, "the hook is a photograph that tags them")
        self.assertGreater(shows[-1], 0, "the last card before the closer shows them")
        # four moments the agent chose, the last one's photograph showing no one the person named
        ms = [dict(m, peak=False) for m in drafted()[:4]]
        ctx = curated("close-on-them", ms)
        last = ms[-1]["post"]
        sh = json.loads((ctx.B / "shared.json").read_text())
        for x in sh["items"]:
            if x["id"] == last:
                x["why"], x["from"] = ["in your posts"], "mine"
        (ctx.B / "shared.json").write_text(json.dumps(sh))
        ctx = compose.Ctx(ctx.B)
        by = {x["id"]: x for x in ctx.items}
        moved = [b for b in compose.plan(ctx, STYLE)["beats"] if b["form"] == "moment"]
        self.assertEqual(sorted(b["post"] for b in moved), sorted(m["post"] for m in ms), "every chosen moment stays in the film")
        self.assertNotEqual(moved[-1]["post"], last)
        self.assertGreater(compose.shown(by[moved[-1]["post"]]), 0, "a photograph that shows them closes it")

    def test_with_no_age_asked_the_hook_and_closer_carry_the_name_and_no_turns(self):
        ctx = asked("asked-no-age", 45, age=False)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1"))
        self.assertEqual(board["wish"]["number"], "dani")
        s = compose.lay(board, "reel")
        hook = s["film"]["cards"][0]
        self.assertEqual(hook["head"][0]["text"], "dani")
        kit = look("scrapbook")
        tag = next(l for l in hook["lines"] if l.get("name") == "tag")
        self.assertEqual(tag["text"], "dani · birthday")
        self.assertGreater(min(q[0] for q in kit.hull(tag)), max(q[0] for q in kit.hull(hook["head"][0])),
                           "the tag stands beside the name at its right in one lockup, never over it")
        self.assertFalse([t for t in texts(s) if "turns" in t or t == "30"], texts(s))
        self.assertEqual(next(l["text"] for l in s["film"]["closer"]["lines"] if l.get("name") == "title"), "happy birthday, dani")


class Vote(unittest.TestCase):
    """snap cuts only the board that won the vote, and a new draft starts a new vote: storyboard.py runs as the command
    in a copy of the year's run, named in build/latest for the test."""

    def setUp(self):
        latest = WS / "build" / "latest"
        self.addCleanup(latest.write_text, latest.read_text())
        self.run_dir = WS / "build" / f"vote-{self.id().rsplit('.', 1)[-1]}"
        shutil.copytree(B, self.run_dir, symlinks=True)
        latest.write_text(self.run_dir.name + "\n")
        (self.run_dir / "taste.md").write_text("# taste\n")

    def storyboard(self, *args):
        return subprocess.run([sys.executable, str(S / "scripts" / "storyboard.py"), *args], cwd=WS, capture_output=True,
                              text=True)

    def test_snap_cuts_only_a_board_that_won_the_vote(self):
        r = self.storyboard("snap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vote.py ballot", r.stderr)
        self.assertNotEqual(self.storyboard("snap", "--board", "1").returncode, 0)
        self.assertFalse((self.run_dir / "film.json").exists())

    def test_a_new_draft_starts_a_new_vote(self):
        (self.run_dir / "vote").mkdir(exist_ok=True)
        (self.run_dir / "winner.json").write_text('{"board": "1"}')
        (self.run_dir / "vote" / "scores.json").write_text("{}")
        r = self.storyboard("draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertFalse((self.run_dir / "winner.json").exists())
        self.assertFalse((self.run_dir / "vote" / "scores.json").exists())

    def test_a_new_draft_removes_the_render_report_the_cut_and_the_type_reads_of_the_boards_it_replaces(self):
        (self.run_dir / "film.json").write_text('{"id": "1"}')
        (self.run_dir / "render").mkdir(exist_ok=True)
        (self.run_dir / "render" / "film-report.json").write_text('{"failed": 0}')
        (self.run_dir / "storyboards" / "1").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "storyboards" / "1" / "type.json").write_text('{"findings": []}')
        r = self.storyboard("draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertFalse((self.run_dir / "render" / "film-report.json").exists())
        self.assertFalse((self.run_dir / "film.json").exists())
        self.assertFalse((self.run_dir / "storyboards" / "1" / "type.json").exists())


if __name__ == "__main__":
    unittest.main()


def hooked(name, hook):
    """A copy of the run folder whose taste.json names `hook` as the hook's photograph; returns its Ctx."""
    d = WS / "build" / name
    if not d.exists():
        shutil.copytree(B, d, symlinks=True)
        taste = json.loads((B / "taste.json").read_text())
        taste["hook"] = hook
        (d / "taste.json").write_text(json.dumps(taste))
    return compose.Ctx(d)


class Look(unittest.TestCase):
    """The hook the agent names, a fast run before the peak, the type in two faces with no word alone on a last row, and
    a clip request written from the shot the agent saw in its photograph."""

    def test_the_hook_is_the_photograph_taste_json_names(self):
        ctx = compose.Ctx(B)
        default = compose.plan(ctx, STYLE)
        other = next(b["post"] for b in default["beats"][2:] if b["form"] == "moment")
        board = compose.plan(hooked("hook-named", other), STYLE)
        self.assertEqual(board["beats"][0]["post"].partition("#")[0], other)
        self.assertNotIn(other, [b.get("post") for b in board["beats"][1:]], "the hook's post is not a card too")
        self.assertEqual(compose.plan(hooked("hook-named-1", f"{other}#1"), STYLE)["beats"][0]["post"], f"{other}#1")
        for bad in ("post:99999", f"{other}#9"):
            with self.subTest(bad), self.assertRaises(SystemExit) as e:
                compose.plan(hooked(f"hook-bad-{bad.replace(':', '').replace('#', '-')}", bad), STYLE)
            self.assertIn("taste.json hook", str(e.exception))

    def test_the_three_cards_before_the_peak_run_fast_with_their_names_alone(self):
        ms = [dict(m) for m in drafted()[:16:2]]
        ms[5]["peak"] = True
        board = compose.plan(curated("look-run", ms), STYLE)
        kit = look("scrapbook")
        cards = [b for b in board["beats"] if b["form"] == "moment"]
        self.assertEqual([b["run"] for b in cards], [False, False, True, True, True, False, False, False])
        for b in cards[2:5]:
            self.assertAlmostEqual(b["pulses"] * 60 / board["bpm"], kit.FAST, delta=60 / board["bpm"] / kit.GRID + 1e-9)
            self.assertEqual((b["words"], b["talk"]), ("", []), b["id"])
            self.assertTrue(b["name"], b["id"])
        self.assertGreater(cards[5]["pulses"], max(b["pulses"] for b in cards if b is not cards[5]))

    def test_a_calm_look_flies_one_photograph_in_once_on_the_peak(self):
        ms = [dict(m) for m in drafted()[:16:2]]
        ms[5]["peak"] = True
        ctx = curated("look-run", ms)
        for style, move in (("scrapbook", "exploded-layers"), ("analog-home-movie", "tilted-wall"), ("editorial-quiet", "exploded-layers")):
            with self.subTest(style):
                self.assertIn({"id": move, "once": True}, [{k: o.get(k) for k in ("id", "once")} for o in compose.card(style)["moves"]],
                              "the card marks the move it flies once")
                board = compose.plan(ctx, style)
                used = [(b["id"], b["move"]) for b in board["beats"] if b.get("move") in wall.SPECTACLE]
                peak = next(b for b in board["beats"] if b.get("peak"))
                self.assertEqual(used, [(peak["id"], move)])
                self.assertEqual(peak["transition"], "hard-cut", "the picture cuts straight into the flight")

    def test_a_type_led_look_takes_its_cards_trailer_moves_wherever_they_win_and_never_on_a_run(self):
        # a run of three cards the trailer moves would win (each tagged peak), then a photograph they do win:
        # swiss-grid's exploded-layers (fits photo and peak) on a wordless landscape peak, kinetic-type's picture-tunnel
        # on a peak with a line, the move the card marks `once`, which wins the peak over slam-words (fits words and peak)
        def beats(peak):
            out = [{"id": "hook", "form": "hook", "post": "p0"}]
            out += [{"id": f"run-{i}", "form": "moment", "post": f"p{i}", "run": True, "peak": True} for i in (1, 2, 3)]
            out += [{"id": "card", "form": "moment", "post": "p4", "peak": True, **peak}, {"id": "closer", "form": "closer"}]
            return out
        photos = {f"p{i}": {"aspect": 0.75} for i in range(5)}
        moments = {f"p{i}": {"people": ["me"], "place": None} for i in range(5)}
        for style, peak, move in (("swiss-grid", {}, "exploded-layers"), ("kinetic-type", {"words": "the ridge at six"}, "picture-tunnel")):
            with self.subTest(style):
                card = compose.card(style)
                self.assertIn(move, compose.ids(card, "moves"), "the move is the style card's")
                # a type-led card's moves are its grammar, and the move it marks `once` still plays on the peak alone
                self.assertIn(card["id"], wall.GRAMMAR)
                bs = beats(peak)
                wall.choose(card, bs, photos, moments, "me")
                self.assertEqual(bs[4]["move"], move)
                for b in bs[1:4]:
                    self.assertNotIn(b["move"], wall.TAKES, "a run card never takes a frame-taking move")

    def test_a_flight_lands_on_the_grid_and_its_card_holds_its_words_after_it(self):
        ms = [dict(m) for m in drafted()[:16:2]]
        ms[5]["peak"] = True
        ctx = curated("look-run", ms)
        for style in ("scrapbook", "analog-home-movie", "editorial-quiet"):
            with self.subTest(style):
                board = boxed(compose.finish(ctx, compose.plan(ctx, style), f"flight-{style}"))
                st = compose.lay(board, "reel")
                bpm = st["bpm"]
                film = compose.fit(board, bpm)
                tm = wall.times(film)
                peak = next(b for b in film["beats"] if b.get("peak"))
                take = wall.TAKES[peak["move"]] * bpm / 60
                t = tm[peak["id"]]
                self.assertEqual(t["cut"] * wall.GRID % 1, 0, "the photograph lands on a quarter beat")
                self.assertLessEqual(t["cut"] - t["at"], take)
                self.assertGreater(t["cut"] - t["at"], take - 1 / wall.GRID)
                self.assertAlmostEqual(t["flies"], t["cut"] - take, places=6)
                self.assertGreaterEqual((t["end"] - t["cut"]) * 60 / bpm, wall.LEAST, "its words read after the landing")
                self.assertIn({"kind": "hit", "at": round(t["cut"], 3)}, [{k: c[k] for k in ("kind", "at")} for c in st["sound"]],
                              "its hit falls as it lands")
                beat = next(b for b in st["beats"] if b["id"] == peak["id"])
                self.assertEqual((beat["flies"], beat["lands"]), (round(t["flies"], 4), round(t["cut"], 4)))
                self.assertEqual([b["id"] for b in st["beats"] if "flies" in b], [peak["id"]])

    def test_every_look_sets_its_type_in_its_own_card_faces(self):
        ctx = compose.Ctx(B)
        for style in ("scrapbook", "analog-home-movie", "editorial-quiet"):
            with self.subTest(style):
                look(style)
                card = compose.card(style)["faces"]
                own = {v[k] for v in card.values() if isinstance(v, dict) for k in ("file", "italic") if v.get(k)}
                self.assertTrue(set(faces().values()) <= own, faces())
                s = compose.lay(boxed(compose.finish(ctx, compose.plan(ctx, style), f"look-faces-{style}")), "reel")
                cl = s["film"]["closer"]
                files = {l["file"] for c in s["film"]["cards"] for l in [*c["head"], *c["lines"]]} | {l["file"] for l in cl["lines"]}
                self.assertTrue(files <= own, files)
                self.assertEqual({Path(f).parent.name for f in files}, {style}, files)

    def test_a_last_row_of_one_word_takes_the_word_before_it_down(self):
        kit = look("scrapbook")
        text = "we walked the long way home along the river"
        measure = kit.width("we walked the long way home along the", 60, "mine") + 1
        rows = kit.wrap(text, 60, "mine", measure)
        self.assertGreater(len(rows), 1)
        self.assertGreater(len(rows[-1].split()), 1, rows)
        self.assertEqual(" ".join(rows), text)
        self.assertTrue(all(kit.width(r, 60, "mine") <= measure for r in rows), rows)

    def test_a_last_row_of_one_word_takes_the_word_before_it_from_a_row_of_two(self):
        kit = look("scrapbook")
        text = "marrakech dance floor"
        measure = kit.width("marrakech dance", 60, "display") + 1
        rows = kit.wrap(text, 60, "display", measure)
        self.assertEqual(rows, ["marrakech", "dance floor"])

    def test_on_every_card_the_name_stands_over_its_words_in_the_films_lowercase(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "look-order"))
        sides = set()
        for fmt in compose.FORMATS:
            for c in compose.lay(board, fmt)["film"]["cards"][1:]:
                words = [ln for ln in c["lines"] if ln["name"].startswith(("words", "talk"))]
                with self.subTest(fmt=fmt, card=c["key"], side=c["side"]):
                    for ln in words:
                        self.assertEqual(ln["text"], ln["text"].lower())
                    if c["head"] and words:
                        sides.add(c["side"])
                        self.assertLess(max(ln["y"] for ln in c["head"]), min(ln["y"] for ln in words))
        self.assertEqual(sides, {"over", "under"}, "the year has cards with the type on either side of the line")

    def test_a_clip_request_shows_its_cards_frame_loops_its_motion_and_the_hook_asks_for_the_full_frame(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "look-frame"))
        beats = {b["id"]: b for b in board["beats"]}
        for r in compose.lay(board, "reel")["clips"]:
            beats[r["beat"]]["shot"] = {"subject": f"what beat {r['beat']} shows", "moves": "the grass in the wind"}
        reqs = compose.lay(board, "reel")["clips"]
        hook = [r for r in reqs if r["use"] == "the hook's world"]
        cards = [r for r in reqs if r["use"] != "the hook's world"]
        self.assertTrue(hook and cards)
        self.assertEqual(hook[0]["frame"], "the whole photograph, full frame")
        for r in reqs:
            with self.subTest(r["beat"]):
                if r not in hook:
                    self.assertIn("a portrait 9:16 card showing", r["frame"])
                self.assertIn(f"Frame: {r['frame']}", r["prompt"])
                self.assertIn("returns to where it began", r["prompt"])
                self.assertNotIn("stand_in", r, "a request is never a clip and never names a stand-in")

    def test_a_clips_light_and_height_are_read_about_its_subject_and_its_sky(self):
        from PIL import Image, ImageDraw
        kit = look("scrapbook")
        sky = Image.new("RGB", (160, 200), (235, 200, 150))
        ImageDraw.Draw(sky).rectangle((48, 80, 112, 180), fill=(18, 16, 20))
        ground = Image.new("RGB", (160, 200))
        ground.putdata([((x * 37 + y * 91) % 200 + 20,) * 3 for y in range(200) for x in range(160)])
        both = sky.copy()
        both.paste(ground.crop((0, 50, 160, 200)), (0, 50))
        shots = {"backlit": sky, "ground": ground, "both": both}
        with mock.patch.object(kit, "pixels", lambda B, f: shots[f]):
            self.assertIn("backlit", kit.light_of({"file": "backlit", "subject": [0.3, 0.4, 0.7, 0.9]}))
            self.assertNotIn("backlit", kit.light_of({"file": "ground", "subject": [0.3, 0.4, 0.7, 0.9]}))
            level = [[0, 0.25, 2.0]]
            self.assertEqual(kit.height_of({"file": "ground", "lines": level}), "the camera at the photograph's own height and angle")
            self.assertIn("high and looking down", kit.height_of({"file": "both", "lines": level}))

    def test_each_clip_request_is_written_from_its_beats_shot(self):
        ctx = compose.Ctx(B)
        board = boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "look-clips"))
        reqs = compose.lay(board, "reel")["clips"]
        self.assertEqual(reqs[0]["use"], "the hook's world")
        self.assertTrue(all(r["prompt"] is None for r in reqs), "a beat with no shot has no prompt")
        allowed = {r["file"] for r in board["photos"].values()}
        asked = [i for i in storyboard.board_issues(board, ctx, allowed) if 'write in this beat "shot"' in i]
        self.assertEqual(len(asked), len(reqs), asked)
        beats = {b["id"]: b for b in board["beats"]}
        for i, r in enumerate(reqs):
            beats[r["beat"]]["shot"] = {"subject": f"the two of them on beat {i}, as the agent saw them",
                                        "moves": f"the light on the water of beat {i}"}
        reqs = compose.lay(board, "reel")["clips"]
        self.assertEqual(len({r["prompt"] for r in reqs}), len(reqs), "one prompt a shot, never one template")
        for i, r in enumerate(reqs):
            with self.subTest(r["beat"]):
                for k in ("subject", "move", "lens", "light"):
                    self.assertTrue(r[k], k)
                    self.assertIn(r[k].rstrip("."), r["prompt"], k)
                self.assertIn(f"{r['duration']} s", r["prompt"])
                self.assertIn("seamless loop", r["prompt"])
        self.assertFalse([i for i in storyboard.board_issues(board, ctx, allowed) if 'write in this beat "shot"' in i])


CLIP = S / "tests" / "fixtures" / "clip-tram.mp4"


def with_clip(name, still, post):
    """A copy of the run folder `still` whose post `post` the person filled with the fixture's recorded clip, read the
    way picks.py reads a clip; returns its Ctx."""
    import picks
    d = WS / "build" / name
    if not d.exists():
        shutil.copytree(still, d, symlinks=True)
        p = json.loads((d / "picks.json").read_text())
        row = next(r for r in p["items"] if r["id"] == post)
        p["items"] = [r for r in p["items"] if r["id"] != post]
        p["videos"] = [r for r in p.get("videos") or [] if r["id"] != post] + [{**row, "video": str(CLIP), "shot": picks.strongest(CLIP),
                                                                                "seconds": picks.duration(CLIP)}]
        (d / "picks.json").write_text(json.dumps(p))
        # the photograph its card shows, graded as storyboard.py grades it before the clips are cut
        (d / "public" / "graded").mkdir(parents=True, exist_ok=True)
        shutil.copy(row["photo"], d / "public" / "graded" / Path(row["photo"]).name)
    return compose.Ctx(d)


class Recorded(unittest.TestCase):
    """A clip the person recorded plays on its moment's card as one shot the length of its beat, from the second its
    shot starts on, its sound left out; nothing is asked of a video model for it."""

    @classmethod
    def setUpClass(cls):
        videos = {r["id"] for r in json.loads((B / "picks.json").read_text()).get("videos") or []}
        ms = [dict(m) for m in drafted() if m["post"] not in videos][:16:2]
        ms[5]["peak"] = True
        cls.still = curated("rec-still", ms)
        # a card of the year that holds its words, neither the peak nor one of the run before it, on every look
        on = lambda style: {b["post"] for b in compose.finish(cls.still, compose.plan(cls.still, style), f"rec-on-{style}")["beats"]
                            if b["form"] == "moment" and not b.get("run") and not b.get("peak")}
        cls.post = next(m["post"] for m in ms if all(m["post"] in on(s) for s in ("scrapbook", "analog-home-movie", "editorial-quiet")))
        cls.clip = with_clip("rec-clip", WS / "build" / "rec-still", cls.post)

    def boards(self, style):
        out = []
        for ctx, name in ((self.still, "still"), (self.clip, "clip")):
            board = boxed(compose.finish(ctx, compose.plan(ctx, style), f"rec-{name}-{style}"))
            out.append((board, compose.lay(board, "reel")))
        return out

    def test_a_clip_request_is_one_shot_the_length_of_its_beat(self):
        import clips
        import picks
        import _env
        start = picks.strongest(CLIP)
        self.assertLessEqual(start, 1.0, "a 4 s clip starts where a beat's length of it is still to come")
        for style in ("scrapbook", "analog-home-movie", "editorial-quiet"):
            with self.subTest(style):
                (_, _), (board, st) = self.boards(style)
                beat = next(b for b in board["beats"] if b.get("post") == self.post)
                own = [c for c in st["clips"] if c.get("source")]
                self.assertEqual(len(own), 1)
                c = own[0]
                secs = clips.windows(st)[beat["id"]][1] / clips.FPS
                self.assertEqual((c["beat"], c["use"], c["source"], c["prompt"]), (beat["id"], wall.OWN, str(CLIP), None))
                self.assertEqual(c["image"], board["photos"][self.post]["file"], "it plays where its photograph would")
                self.assertEqual(c["from"], round(min(start, max(0.0, picks.duration(CLIP) - c["duration"])), 3),
                                 "from its strongest second, or as much earlier as its beat needs of it")
                self.assertAlmostEqual(c["to"] - c["from"], secs, delta=1.5 / clips.FPS)
                self.assertAlmostEqual(c["duration"], secs, delta=1.5 / clips.FPS)
                self.assertNotIn(beat["id"], [r["beat"] for r in st["clips"] if not r.get("source")], "no model is asked for it")
        run = WS / "build" / "rec-clip"
        was_run, was_board = _env._RUN, clips.board
        _env._RUN, clips.board = run, lambda: st
        try:
            self.assertEqual(clips.cmd_normalize(argparse.Namespace(why="no video model")), 0)
            placed = clips.placed()
        finally:
            _env._RUN, clips.board = was_run, was_board
        at, n = clips.windows(st)[beat["id"]]
        got = next(r for r in json.loads((run / "clips.json").read_text())["clips"].values() if r["status"] == "recorded")
        self.assertEqual((got["beat"], got["from_frame"], got["frames"]), (beat["id"], at, n), "one shot, its beat's first frame to its last")
        self.assertEqual(len(list((run / "public" / got["dir"]).glob("*.jpg"))), n)
        self.assertEqual([p.get("own") for p in placed if p["dir"] == got["dir"]], [True])

    def test_a_beat_without_a_clip_is_unchanged(self):
        for style in ("scrapbook", "analog-home-movie", "editorial-quiet"):
            with self.subTest(style):
                (b0, s0), (b1, s1) = self.boards(style)
                rec = next(b["id"] for b in b1["beats"] if b.get("recorded"))
                self.assertEqual([b for b in b0["beats"] if b["id"] != rec], [b for b in b1["beats"] if b["id"] != rec])
                self.assertEqual({k: v for k, v in next(b for b in b1["beats"] if b["id"] == rec).items() if k != "recorded"},
                                 next(b for b in b0["beats"] if b["id"] == rec))
                bare = lambda s: [{k: v for k, v in c.items() if k != "id"} for c in s["clips"] if c["beat"] != rec]
                self.assertEqual(bare(s0), bare(s1))
                self.assertEqual([b for b in s0["beats"] if b["id"] != rec], [b for b in s1["beats"] if b["id"] != rec])


FOCUS = """
const [bundle, path] = process.argv.slice(1);
const {readFileSync} = await import('fs');
const {planOf, timelineOf, photoBoxOf} = await import(bundle);
const plan = planOf(JSON.parse(readFileSync(path, 'utf8')));
const tl = timelineOf(plan);
console.log(JSON.stringify(plan.cards.map((c) => {
  const b = tl.beats.find((x) => x.id === c.key);
  const flown = b.place !== undefined;
  const on = flown ? [c.place[0], c.place[1], c.place[0] + c.place[2], c.place[1] + c.place[3]] : photoBoxOf(plan, c);
  return {key: c.key, move: b.move, focus: b.focus ?? null, subject: c.subject, on};
})));
"""

NODE = shutil.which("node")
ESBUILD = S / "motion" / "node_modules" / ".bin" / "esbuild"


@unittest.skipUnless(NODE and ESBUILD.exists(), "an authoring check of the motion source: needs node and motion/node_modules")
class DoodleFocus(unittest.TestCase):
    """A card's beat hands its move the middle of the photograph's subject, so a doodle rings the people the photograph
    is of, never the middle of the print."""

    def test_every_card_beat_carries_the_subjects_middle_on_the_photograph_the_move_finds(self):
        ctx = compose.Ctx(B)
        s = compose.lay(boxed(compose.finish(ctx, compose.plan(ctx, STYLE), "1")), "reel")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            entry, bundle, path = Path(d) / "entry.ts", Path(d) / "camera.mjs", Path(d) / "board.json"
            path.write_text(json.dumps(s))
            entry.write_text(f"export {{planOf}} from '{S}/motion/studio/drive/plan';\n"
                             f"export {{timelineOf}} from '{S}/motion/studio/drive/camera';\n"
                             f"export {{photoBoxOf}} from '{S}/motion/studio/drive/card';\n")
            subprocess.run([str(ESBUILD), str(entry), "--bundle", "--format=esm", "--platform=node", "--log-level=error",
                            f"--outfile={bundle}"], check=True, cwd=S / "motion")
            rows = json.loads(subprocess.run([NODE, "--input-type=module", "-e", FOCUS, str(bundle), str(path)], check=True,
                                             capture_output=True, text=True).stdout)
        self.assertTrue(rows)
        self.assertIn("doodle-draw-on", {r["move"] for r in rows})
        for r in rows:
            with self.subTest(card=r["key"]):
                self.assertIsNotNone(r["focus"])
                (x0, y0, x1, y1), (a, b, c, e) = r["subject"], r["on"]
                want = [((x0 + x1) / 2 - a) / (c - a), ((y0 + y1) / 2 - b) / (e - b)]
                for got, w in zip(r["focus"], want):
                    self.assertAlmostEqual(got, w, places=6)
                    self.assertTrue(-0.01 <= got <= 1.01, r)
