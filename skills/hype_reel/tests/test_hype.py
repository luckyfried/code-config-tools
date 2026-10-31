"""The hype reel for any subject: the date the person wrote, the line a photograph says, the moves and cuts each beat takes from the card, the
frame each board rests on, the black the gate allows, the looks the review page offers, and the kit's own words.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import collections
import datetime as dt
import json
import os
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "evals" / "fixtures"))
import _env  # noqa: E402
import compose  # noqa: E402
import deliver  # noqa: E402
import drive  # noqa: E402
import gather  # noqa: E402
import make_person  # noqa: E402
import qa  # noqa: E402
import research  # noqa: E402
import storyboard  # noqa: E402


class Here(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(d.cleanup)
        cwd = os.getcwd()
        os.chdir(d.name)
        self.addCleanup(os.chdir, cwd)
        self.dir = Path(d.name)


class Dates(unittest.TestCase):
    def test_a_short_weekday_reads_like_the_whole_one(self):
        today = dt.date(2026, 10, 30)
        self.assertEqual(gather.parse_date("sat 28 nov", today), gather.parse_date("saturday 28 nov", today))
        self.assertEqual(gather.parse_date("fri 22 jan", today)[0], "2027-01-22")
        self.assertEqual(gather.parse_date("fri", today), gather.parse_date("friday", today))


class Moments(unittest.TestCase):
    def test_the_moments_are_what_the_person_did_with_no_count_in_them(self):
        lib = {"subject": {"name": "Moss Runner"}, "feed": [
            {"file": "b.jpg", "date": "2026-06-02", "words": "porto with @dani.reyes and @ines.walks", "caption": "porto",
             "likes": 900, "comments": 40},
            {"file": "a.jpg", "date": "2026-02-01", "words": "first test run on the trail", "caption": "a trail", "likes": 3},
            {"file": "c.jpg", "date": "2026-03-01", "words": "", "caption": "a shoe", "likes": 5000}]}
        mom, _ = research.moments(lib, {2: collections.Counter({"home": 1})})
        self.assertEqual([m["said"] for m in mom], ["first test run on the trail", "porto with @dani.reyes and @ines.walks"])
        self.assertEqual(mom[1]["people"], ["@dani.reyes", "@ines.walks"])
        self.assertEqual(mom[0]["photo"], "a.jpg")

    def test_a_long_caption_says_the_sentence_that_names_the_subject(self):
        said = "confession: i've been sewing these in secret for a year. moss runner is nearly ready."
        mom, _ = research.moments({"subject": {"name": "Moss Runner"},
                                   "feed": [{"file": "a.jpg", "date": "2026-10-11", "words": said, "caption": said}]}, {})
        self.assertEqual(mom[0]["line"], "moss runner is nearly ready")

    def test_a_short_caption_is_said_whole(self):
        self.assertEqual(research.line_of("kiln day, round four", "Tide Table"), "kiln day, round four")

    def test_a_long_caption_naming_no_subject_says_its_first_sentence(self):
        said = "a long night at the bench with the radio on. the last coat went on just after midnight and dried"
        self.assertEqual(research.line_of(said, "Moss Runner"), "a long night at the bench with the radio on")


def beat(part, form, words="", label="", own=False, peak=False, n=4):
    return {"id": part, "part": part, "form": form, "words": words, "label": label, "own": own, "peak": peak,
            "len": n}


class Moves(unittest.TestCase):
    def test_no_subject_beat_after_the_hook_takes_a_move_that_covers_its_picture(self):
        for style in ("kinetic-type", "cinematic-letterbox", "swiss-grid"):
            card = compose.card(style)
            beats = [beat("hook", "title", "nearly ready", "14 nov", own=True)] + \
                [beat(f"build-{i}", "photo", label="Moss Runner", own=True) for i in range(1, 7)] + \
                [beat("made", "photo", "Moss Runner", "14 nov", own=True, peak=True), beat("closer", "closer")]
            drive.choose(card, beats)
            covered = [b["id"] for b in beats[1:-1] if b["move"] in drive.COVERS]
            self.assertEqual(covered, [], style)

    def test_the_reveal_takes_a_move_made_for_its_form(self):
        for style in ("kinetic-type", "cinematic-letterbox", "swiss-grid"):
            card = compose.card(style)
            beats = [beat("hook", "title", "nearly ready", "14 nov", own=True)] + \
                [beat(f"build-{i}", "photo", label="Moss Runner", own=True) for i in range(1, 7)] + \
                [beat("made", "photo", "Moss Runner", "14 nov", own=True, peak=True), beat("closer", "closer")]
            drive.choose(card, beats)
            fits = {m["id"]: m["fits"] for m in card["moves"]}
            self.assertIn("photo", fits[beats[-2]["move"]], style)

    def test_a_beat_with_words_never_takes_a_move_its_words_leave_on(self):
        for style in ("kinetic-type", "cinematic-letterbox", "swiss-grid"):
            card = compose.card(style)
            beats = [beat("hook", "title", "nearly ready", "14 nov", own=True)] + \
                [beat(f"build-{i}", "photo", f"day {i}", label="Moss Runner") for i in range(1, 7)] + \
                [beat("made", "photo", "Moss Runner", "14 nov", own=True, peak=True), beat("closer", "closer")]
            drive.choose(card, beats)
            passing = [b["id"] for b in beats[:-1] if b["move"] in drive.PASSING]
            self.assertEqual(passing, [], style)

    def test_the_reveal_holds_longest(self):
        for style in ("kinetic-type", "cinematic-letterbox", "swiss-grid"):
            card = compose.card(style)
            beats = [beat("hook", "title", "tide table is nearly ready and the glaze is right at last", "14 nov", own=True)] + \
                [dict(beat("build", "photo", f"the {i} glaze test came out of the kiln"), id=f"build-{i}") for i in range(1, 7)] + \
                [beat("made", "photo", "Moss Runner", "14 nov", own=True, peak=True), beat("closer", "closer")]
            drive.choose(card, beats)
            drive.lengths(beats, card, 120)
            self.assertEqual(max(beats[:-1], key=lambda b: b["len"])["id"], "made", style)

    def test_a_wordless_photograph_of_the_build_takes_the_wall_and_holds_its_flight(self):
        card = compose.card("swiss-grid")
        beats = [beat("hook", "title", "nearly ready", "14 nov", own=True), beat("build", "photo", "the first try"),
                 beat("build", "photo", own=True), beat("made", "photo", "Moss Runner", own=True, peak=True),
                 beat("closer", "closer")]
        drive.choose(card, beats)
        self.assertEqual(beats[2]["move"], "tilted-wall")
        self.assertNotEqual(beats[-1]["move"], "tilted-wall")
        per = 60 / 123
        self.assertGreaterEqual(drive.least(beats[2], per) * per, drive.ARRIVES["tilted-wall"] + drive.SETTLE)

    def test_the_film_never_opens_on_black(self):
        card = compose.card("cinematic-letterbox")
        beats = [beat("hook", "title", "nearly ready", "14 nov", own=True), beat("closer", "closer")]
        drive.choose(card, beats)
        self.assertNotIn(beats[0]["move"], drive.NOT_FIRST)


class Layouts(unittest.TestCase):
    def test_a_photograph_with_no_words_covers_the_frame(self):
        card = compose.card("swiss-grid")
        said = beat("build", "photo", "the fourth try", own=False)
        bare = beat("build", "photo", own=True)
        said["move"] = bare["move"] = "grid-snap"
        self.assertEqual(drive.layout_of(said, card), "card")
        self.assertEqual(drive.layout_of(bare, card), "frame")

    def test_a_move_drawn_on_the_photograph_gets_its_box(self):
        card = compose.card("swiss-grid")
        for move in sorted(drive.BOXED):
            b = beat("build", "photo", own=True)
            b.update(move=move, photo={"file": "a.jpg", "aspect": 1.25}, id="build-1")
            drive.lay(b, card)
            self.assertEqual(b["layout"], "card", move)
            self.assertLess(b["picture"]["box"][2], drive.W, move)
            self.assertEqual(b["lines"], [], move)

    def test_only_the_build_takes_a_move_drawn_on_the_photograph(self):
        card = compose.card("swiss-grid")
        beats = [beat("hook", "title", "nearly ready", "14 nov", own=True)] + \
            [beat("build", "photo", f"day {i}") for i in range(1, 7)] + \
            [beat("made", "photo", "Moss Runner", "14 nov", own=True, peak=True), beat("closer", "closer")]
        drive.choose(card, beats)
        self.assertNotIn(beats[0]["move"], drive.BOXED)
        self.assertNotIn(beats[-2]["move"], drive.BOXED)
        self.assertTrue(any(b["move"] in drive.BOXED for b in beats[1:-2]))

    def test_a_landscape_photograph_sets_its_line_in_the_landscape_line_box(self):
        card = compose.card("swiss-grid")
        land = card["photo"]["landscape"]
        b = beat("build", "photo", "the glaze ran into the kiln shelf on the fourth firing")
        b.update(move="grid-snap", photo={"file": "a.jpg", "aspect": 0.66}, id="build-1")
        drive.lay(b, card)
        a = drive.area_of("reel")
        x0, y0 = a[0] + land["line"][0] * (a[2] - a[0]), a[1] + land["line"][1] * (a[3] - a[1])
        x1, y1 = x0 + land["line"][2] * (a[2] - a[0]), y0 + land["line"][3] * (a[3] - a[1])
        self.assertEqual(b["picture"]["box"][1], round(land["box"][1] * drive.H, 1))
        for ln in b["lines"]:
            self.assertGreaterEqual(ln["top"], y0 - 0.5)
            self.assertLessEqual(ln["top"] + ln["size"] * compose.face_of(ln["face"])["lineHeight"], y1 + 0.5)
            self.assertLessEqual(ln["x"] + ln["w"], x1 + 0.5)


    def test_every_slammed_word_fits_the_frame_whole_at_one_size(self):
        card = compose.card("kinetic-type")
        said = "tide table is nearly unbreakable"
        b = beat("hook", "title", said, "14 nov", own=True)
        b.update(move="word-per-beat-slam", photo={"file": "a.jpg", "aspect": 1.25})
        drive.lay(b, card)
        self.assertEqual(b["layout"], "field")
        self.assertEqual(len({ln["size"] for ln in b["lines"]}), 1)
        for ln in b["lines"]:
            half = ln["w"] * drive.SLAM["from"] / 2
            self.assertGreaterEqual(ln["x"] - half, 0, ln["text"])
            self.assertLessEqual(ln["x"] + half, drive.W, ln["text"])
        self.assertEqual([ln.get("until") for ln in b["lines"]], [1, 2, 3, 4, None])
        self.assertEqual([ln.get("ground") for ln in b["lines"]], [None, "accent", None, "accent", None])
        self.assertEqual(storyboard.line_issues("1", b, "reel"), [])

    def test_the_reveal_sets_its_name_off_the_picture(self):
        for style, move, layout in (("swiss-grid", "grid-snap", "card"), ("cinematic-letterbox", "anamorphic-push", "matte")):
            for name in ("tide table", "pottery classes"):
                card = compose.card(style)
                b = beat("made", "photo", name, "november 14", own=True, peak=True)
                b.update(move=move, photo={"file": "a.jpg", "aspect": 1.25})
                drive.lay(b, card)
                self.assertEqual((b["layout"], b["scrim"]), (layout, 0), style)
                x, y, w, h = b["picture"]["box"]
                for ln in b["lines"]:
                    foot = ln["top"] + ln["size"] * compose.face_of(ln["face"])["lineHeight"]
                    self.assertTrue(foot <= y or ln["top"] >= y + h, (style, ln["text"]))
                self.assertEqual(storyboard.line_issues("1", b, "reel"), [], (style, name))

    def test_the_grid_reveal_sets_the_name_at_the_title_size(self):
        card = compose.card("swiss-grid")
        for name in ("Ines Duarte", "tide table"):
            b = beat("made", "photo", name, own=True, peak=True)
            b.update(move="grid-snap", photo={"file": "a.jpg", "aspect": 1.25})
            drive.lay(b, card)
            self.assertEqual({ln["size"] for ln in b["lines"]}, {drive.FAMILY["grid"]["want"]}, name)
            self.assertEqual(storyboard.line_issues("1", b, "reel"), [], name)

    def test_the_letterboxed_reveal_shows_the_subject_whole(self):
        card = compose.card("cinematic-letterbox")
        b = beat("made", "photo", "tide table", "november 14", own=True, peak=True)
        b.update(move="anamorphic-push", photo={"file": "a.jpg", "aspect": 1.25, "subject": [0.12, 0.17, 0.89, 0.81],
                                                "ground": ["#1f4aa8", "#1a3a88"]})
        drive.lay(b, card)
        p = b["picture"]
        x, y, w, h = p["place"]
        self.assertGreaterEqual(y + 0.17 * h, 0)
        self.assertLessEqual(y + 0.81 * h, p["box"][3])
        self.assertAlmostEqual(x + w / 2, p["box"][2] / 2, delta=1)
        self.assertEqual(len(p["fill"]), 2)


class Cuts(unittest.TestCase):
    def test_a_cut_takes_at_most_three_eighths_of_either_beat_it_joins(self):
        card = compose.card("cinematic-letterbox")
        beats = [beat("hook", "title", "x", n=8), *[beat(f"b{i}", "photo", n=n) for i, n in enumerate((4, 8, 2, 12, 2))],
                 beat("closer", "closer", n=8)]
        drive.cuts_of(card, beats, drive.TONES["cinematic"])
        for a, b in zip(beats, beats[1:]):
            self.assertLessEqual(drive.cut_beats(b["transition"]), 0.75 * min(a["len"], b["len"]), (a["id"], b["id"], b["transition"]))
        self.assertIn("long-dissolve", [b["transition"] for b in beats])

    def test_two_beats_of_words_never_crossfade_while_a_jump_cut_fits(self):
        for style in ("kinetic-type", "cinematic-letterbox", "swiss-grid"):
            card = compose.card(style)
            for tone in drive.TONES.values():
                beats = [beat("hook", "title", "x", n=8), *[beat(f"b{i}", "photo", "a line", n=8) for i in range(4)],
                         beat("closer", "closer", n=8)]
                drive.cuts_of(card, beats, tone)
                for b in beats[1:]:
                    self.assertTrue(drive.cut_jumps(b["transition"]), (style, b["id"], b["transition"]))

    def test_every_tone_names_cuts_that_exist(self):
        for name, tone in drive.TONES.items():
            self.assertTrue(tone["cuts"], name)
            for c in tone["cuts"]:
                self.assertTrue((drive.CUTS / f"{c}.tsx").exists(), (name, c))

    def test_a_beat_comes_to_rest_outside_both_its_cuts(self):
        tl = [{"start": 0, "frames": 60, "bars": 1, "transition": None},
              {"start": 60, "frames": 60, "bars": 1, "transition": "long-dissolve"},
              {"start": 120, "frames": 60, "bars": 1, "transition": "bars-close"}]
        pulse = 15
        r = storyboard.rest(tl, 1)
        self.assertGreaterEqual(r, 60 + drive.cut_beats("long-dissolve") / 2 * pulse)
        self.assertLessEqual(r, 120 - drive.cut_beats("bars-close") / 2 * pulse)


class Labels(unittest.TestCase):
    def test_the_name_and_the_date_land_once_each_before_the_reveal(self):
        still = lambda n: {"file": f"subject/{n}.jpg", "aspect": 1.25, "line": ""}
        ctx = {"name": "moss runner", "hero": still("hero"), "hook": None, "hook_line": "moss runner is nearly ready",
               "date_label": "November 14", "build": [{"file": f"photos/{n}.jpg", "aspect": 1.25, "line": f"day {n}"} for n in (1, 2)],
               "stills": [still(n) for n in ("hero", "a", "b", "c", "d")], "footage": None}
        beats = drive.beats_of(ctx)
        subject = [b["label"] for b in beats if b["part"] == "build" and b["own"]]
        self.assertEqual(subject, ["moss runner", "", "", ""])
        self.assertEqual([b["label"] for b in beats if b["part"] in ("hook", "made")], ["November 14", "November 14"])


class Looks(Here):
    def test_the_review_page_offers_the_two_looks_not_made_by_name(self):
        for n, style in (("1", "kinetic-type"), ("2", "cinematic-letterbox"), ("3", "swiss-grid")):
            beats = [{"part": p, "words": "w"} for p in ("hook", "build", "build", "closer")]
            _env.write_json(f"storyboards/{n}/storyboard.json", {"name": style, "style": style, "beats": beats})
            for i, x in enumerate(beats):
                Path(f"storyboards/{n}/frames").mkdir(parents=True, exist_ok=True)
                Path(f"storyboards/{n}/frames/{i + 1:02d}-{x['part']}.png").write_bytes(b"")
        page = deliver.looks_html({"board": "2", "order": ["1", "2", "3"]})
        self.assertIn('Say "make the first one" or "make the third one"', page)
        self.assertIn(storyboard.LOOKS["swiss-grid"], page)
        self.assertNotIn(storyboard.LOOKS["cinematic-letterbox"], page)
        self.assertNotIn("critic", page.lower())


class Stills(unittest.TestCase):
    def test_the_build_story_shows_a_beat_that_says_something(self):
        parts = [("hook", "a line"), ("build", ""), ("build", "kiln day"), ("build", ""), ("build", ""), ("build", ""),
                 ("made", "the name"), ("closer", "")]
        beats = [{"id": f"b{i}", "part": p, "words": w, "frames": 30} for i, (p, w) in enumerate(parts)]
        tl = [{"id": b["id"], "start": 30 * i, "frames": 30, "bars": 1, "transition": ""} for i, b in enumerate(beats)]
        film = {"beats": beats, "timeline": tl}
        with unittest.mock.patch.object(storyboard, "feed_board", lambda f, c: {}):
            cards, _ = storyboard.stills_of(film)
        self.assertEqual([c["beat"] for c in cards if c["out"] == "out/story-2.png"], ["b2"])
        for b in beats:
            b["words"] = ""
        with unittest.mock.patch.object(storyboard, "feed_board", lambda f, c: {}):
            cards, _ = storyboard.stills_of(film)
        self.assertEqual([c["beat"] for c in cards if c["out"] == "out/story-2.png"], ["b3"])

    def test_the_hook_still_shows_the_whole_line_its_move_lands_one_word_at_a_time(self):
        card = compose.card("kinetic-type")
        b = beat("hook", "title", "tide table is nearly ready", own=True)
        b.update(move="word-per-beat-slam", photo={"file": "a.jpg", "aspect": 1.25})
        drive.lay(b, card)
        self.assertEqual(" ".join(ln["text"] for ln in b["still"]), "tide table is nearly ready")
        self.assertEqual({ln["t"] for ln in b["still"]}, {0})
        self.assertEqual(len({ln["top"] for ln in b["still"]}), 5)
        self.assertEqual(storyboard.line_issues("1", b, "reel"), [])
        b.update(frames=30, id="hook")
        film = {"beats": [b, {"id": "closer", "part": "closer", "words": "", "frames": 30}],
                "timeline": [{"id": "hook", "start": 0, "frames": 30, "bars": 1, "transition": None},
                             {"id": "closer", "start": 30, "frames": 30, "bars": 1, "transition": ""}]}
        with unittest.mock.patch.object(storyboard, "feed_board", lambda f, c: {}):
            cards, _ = storyboard.stills_of(film)
        self.assertEqual([c.get("board") for c in cards if c["out"] == "out/story-1.png"], ["still"])


class Fixture(Here):
    def test_the_camera_roll_ends_on_the_export_day(self):
        from PIL import Image
        for _, _, rel, _ in make_person.ROLL:
            p = self.dir / "media" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (40, 30)).save(p)
        for folder in {(self.dir / "media" / r[2]).parent for r in make_person.ROLL}:
            (folder / "manifest.json").write_text('{"items": []}')
        make_person.camera_roll(self.dir / "out", self.dir / "media", 2026, dt.date(2026, 6, 30))
        items = json.loads((self.dir / "out" / "camera-roll" / "manifest.json").read_text())["items"]
        self.assertEqual(len(items), sum(1 for m, d, _, _ in make_person.ROLL if (m, d) <= (6, 30)))


# the kit's own text: what it tells the agent and what its scripts say; the music engine, the renderer and setup are
# shared with every kit and are not read here
OWN = [KIT / "SKILL.md", *sorted((KIT / "pipeline").glob("*.md")), *sorted((KIT / "critic").glob("*.md")),
       *sorted((KIT / "design").glob("*.md")),
       *[p for p in sorted((KIT / "scripts").glob("*.py")) if p.name not in ("music_engine.py", "render.py", "setup.py")]]
CRAFT = re.compile(r"\b(plates?|glaze[sd]?|kilns?|pottery|potters?|ceramics?|stoneware|greenware|turntable)\b", re.I)
PRONOUN = re.compile(r"\b(she|her|hers|herself)\b", re.I)


class Words(unittest.TestCase):
    def test_the_kit_speaks_of_any_subject_never_one_craft(self):
        found = [f"{p.relative_to(KIT)}:{i}: {m.group(0)}" for p in OWN for i, ln in enumerate(p.read_text().splitlines(), 1)
                 if p.name != "research.py" for m in [CRAFT.search(ln)] if m]
        self.assertEqual(found, [])

    def test_the_person_is_never_she(self):
        files = OWN + [KIT / "evals" / "fixtures" / "make_person.py", *sorted((KIT / "tests").glob("*.py"))]
        found = [f"{p.relative_to(KIT)}:{i}" for p in files if p.name != "test_hype.py"
                 for i, ln in enumerate(p.read_text().splitlines(), 1) if PRONOUN.search(ln)]
        self.assertEqual(found, [])

    def test_the_skill_states_the_films_length(self):
        text = (KIT / "SKILL.md").read_text()
        lo, hi = storyboard.LENGTH
        self.assertIn(f"{lo:g} to {hi:g} seconds", text)


if __name__ == "__main__":
    unittest.main()
