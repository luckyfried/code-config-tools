"""The person's look, the length asked, their counts, the handle, the wall and the set's grade.

    python3 -m unittest discover -s S/tests -p 'test_look.py'
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture
import compose
import deliver
import qa
import storyboard
from compose import month, photos, reel
from PIL import Image

# a look as a person hands it over: last month's template.json
SEED = {"month": "2026-07", "palette": ["#1f3d2b", "#f2e8cf", "#e07a5f"], "font": "Fraunces", "cards": 4, "numbering": "1/4",
        "caption_voice": "short, lowercase, no exclamation marks"}
# the files of the editorial-quiet card's two faces, the only type its boards set
CARD = {f["file"] for f in json.loads((fixture.SCRIPTS.parent / "styles" / "editorial-quiet.json").read_text())["faces"].values()}


def picked(m):
    m = copy.deepcopy(m)
    by_day = {p["day"]: p for p in m["posts"]}
    m["moments"] = [{"day": d, "photo": by_day[d]["photo"], "line": by_day[d]["caption"], "peak": d == 13} for d in (5, 13, 17, 28)]
    return m


def with_look(m, d=SEED):
    from compose import look
    m = copy.deepcopy(m)
    m["look"] = look.read(d, "template.json")
    return m


def asked(m, **ask):
    m = copy.deepcopy(m)
    m["ask"] = ask
    return m


def lines_of(b):
    return storyboard.all_lines(b)


def run(ws, *args):
    env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
    return subprocess.run([sys.executable, str(fixture.SCRIPTS / args[0]), *args[1:]], cwd=ws, env=env, capture_output=True, text=True)


class Look(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()
        cls.board = compose.board("editorial-quiet", with_look(picked(cls.month)))

    def test_every_card_and_the_reel_take_the_palette(self):
        c = self.board["system"]["colors"]
        self.assertEqual((c["bg"], c["ink"], c["line"]), ("#1f3d2b", "#f2e8cf", "#e07a5f"))
        self.assertEqual(self.board["reel"]["colors"], c)

    def test_every_card_is_numbered_as_the_look_numbers_them(self):
        titles = [b["lines"][0]["text"] for b in self.board["beats"]]
        self.assertEqual([t.split(" ")[0] for t in titles], ["1/4", "2/4", "3/4", "4/4"])

    def test_every_line_is_set_in_the_cards_faces_and_a_font_it_does_not_set_is_named(self):
        self.assertEqual({x["file"] for x in lines_of(self.board)} - CARD, set())
        self.assertEqual(self.board["look"]["font_used"], "Instrument Serif")
        self.assertIn("Fraunces is not a font this style sets", self.board["look"]["font_note"])

    def test_a_font_the_card_sets_needs_no_note_and_any_other_is_named(self):
        from compose import look, style
        card = style.card("editorial-quiet")
        faces, note = look.faces_of(card, "Hanken Grotesk")
        self.assertEqual((faces["family"], note), ("Instrument Serif", None))
        faces, note = look.faces_of(card, "Helvetica Neue")
        self.assertEqual(faces["family"], "Instrument Serif")
        self.assertIn("Helvetica Neue", note)
        self.assertIn("Hanken Grotesk", note)
        self.assertEqual(look.faces_of(card), (faces, None))

    def test_the_look_check_passes_on_the_look_and_fails_when_it_is_not_worn(self):
        self.assertEqual(storyboard.look_check(self.board)["bad"], [])
        b = copy.deepcopy(self.board)
        b["system"]["colors"]["bg"] = b["reel"]["colors"]["bg"] = "#141212"
        self.assertTrue(storyboard.look_check(b)["bad"])
        b = copy.deepcopy(self.board)
        b["beats"][2]["lines"][0]["text"] = "03 · my september"
        self.assertTrue(storyboard.look_check(b)["bad"])
        bad = [r for r in storyboard.check_board(b, with_look(self.month)) if not r["ok"]]
        self.assertIn("look", [r["check"] for r in bad])
        # a line in a face the card does not set is the style check's
        b = copy.deepcopy(self.board)
        b["beats"][0]["lines"][1]["file"] = "fonts/styles/swiss-grid/GeistMono[wght].ttf"
        bad = [r for r in storyboard.check_board(b, with_look(self.month)) if not r["ok"]]
        self.assertEqual([r["check"] for r in bad], ["style"])
        self.assertIn("not one of the card's faces", bad[0]["detail"])

    def test_the_frame_check_reads_the_palette_off_the_rendered_still(self):
        run_ = Path(tempfile.mkdtemp(prefix="mir-look-"))
        (run_ / "out" / "cards").mkdir(parents=True)
        cards = [{"png": "out/cards/01-story.png"}]
        im = Image.new("RGB", (1080, 1920), "#1f3d2b")
        im.paste(Image.new("RGB", (600, 120), "#f2e8cf"), (100, 300))
        im.save(run_ / cards[0]["png"])
        ok, detail = qa.frame_look(run_, self.board, cards)
        self.assertTrue(ok, detail)
        Image.new("RGB", (1080, 1920), "#141212").save(run_ / cards[0]["png"])
        ok, detail = qa.frame_look(run_, self.board, cards)
        self.assertFalse(ok, detail)

    def test_draft_reads_template_json_in_the_workspace_and_next_months_template_keeps_the_look(self):
        from compose import look
        ws = fixture.workspace()
        fixture.researched(ws)
        shutil.copyfile(fixture.build(ws) / "taste.draft.md", fixture.build(ws) / "taste.md")
        (ws / "template.json").write_text(json.dumps(SEED))
        r = run(ws, "storyboard.py", "draft")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("type in Instrument Serif", r.stdout)
        self.assertIn("Fraunces is not a font this style sets", r.stdout)
        b = json.loads((fixture.build(ws) / "storyboards" / "editorial-quiet" / "storyboard.json").read_text())
        self.assertEqual(b["system"]["colors"]["bg"], "#1f3d2b")
        t = deliver.template(b)
        self.assertEqual(t["palette"], SEED["palette"])
        self.assertEqual((t["style"], t["font"], t["numbering"], t["month"]), ("editorial-quiet", "Instrument Serif", "1/4", "2026-09"))
        again = look.read(t, "build/template.json")
        self.assertEqual(look.roles_of(again)["bg"], "#1f3d2b")
        (ws / "template.json").unlink()
        (ws / "build" / "template.json").write_text(json.dumps(t))
        here = os.getcwd()
        os.chdir(ws)
        try:
            self.assertEqual(look.roles_of(look.find())["bg"], "#1f3d2b")
        finally:
            os.chdir(here)

    def test_a_month_with_no_photographs_says_its_colors_are_the_kits(self):
        from compose import look
        m = copy.deepcopy(self.month)
        for p in m["posts"]:
            p["photo"] = None
        th = compose.board("editorial-quiet", m)["look"]["theme"]
        self.assertEqual(th["from"], "kit")
        self.assertIn("no photographs", look.source({"theme": th}))
        self.assertEqual(look.source({"theme": {"from": "photographs"}}), "their photographs")

    def test_with_no_look_the_colors_come_from_the_photographs(self):
        b = compose.board("editorial-quiet", picked(self.month))
        self.assertEqual(b["look"]["theme"]["from"], "photographs")
        self.assertEqual(storyboard.look_check(b)["bad"], [])
        self.assertNotEqual(b["system"]["colors"]["bg"], "#1f3d2b")


class Choreography(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = compose.board("editorial-quiet", picked(fixture.month()))

    def test_every_card_lands_in_its_own_color(self):
        for c in self.board["reel"]["cards"]:
            self.assertNotIn("grey", c)
        self.assertNotIn("gray", " ".join(str(c.get("text", "")) for c in self.board["beats"]))

    def test_no_card_holds_half_of_itself(self):
        for c in self.board["beats"]:
            beats = [s["beats"] for s in c["shots"]]
            self.assertLess(max(beats), sum(beats) / 2, c["id"])
        self.assertGreater(len({tuple(s["beats"] for s in c["shots"]) for c in self.board["beats"]}), 1)

    def test_every_plate_is_sized_to_its_words(self):
        for c in self.board["reel"]["cards"]:
            x0, _, x1, _ = c["strip"]
            words = [ln for ln in c["lines"] if ln["y"] > c["strip"][1]]
            widest = max(ln["x"] + reel.width(ln["text"], ln["size"], ln["file"]) for ln in words)
            self.assertLessEqual(x1, widest + reel.PAD + 1)
            self.assertLess(x1 - x0, reel.W * 0.95)


class Length(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = picked(fixture.month())

    def test_an_asked_length_is_met_to_the_frame(self):
        for s in (12, 15, 22.5, 30):
            b = compose.board("editorial-quiet", asked(self.month, seconds=s))
            self.assertEqual(b["reel"]["frames"], round(s * 30), s)
            self.assertEqual(b["reel"]["beats"][-1]["to"] if "to" in b["reel"]["beats"][-1] else b["reel"]["end"], b["reel"]["end"])

    def test_a_length_outside_the_range_is_refused_by_name(self):
        for s in (5, 60):
            with self.assertRaises(month.OutOfRange) as e:
                compose.board("editorial-quiet", asked(self.month, seconds=s))
            self.assertEqual(str(e.exception), f"not delivered: this kit makes a reel of 12 to 30 s, and the ask is for {s} s. "
                                               "Ask for a length in that range.")

    def test_with_no_ask_the_reel_runs_15_s(self):
        b = compose.board("editorial-quiet", self.month)
        self.assertEqual(b["reel"]["frames"], 450)

    def test_the_holds_follow_what_each_photograph_carries(self):
        b = compose.board("editorial-quiet", asked(self.month, seconds=30))
        spans = [c["leave"] - c["arrive"] for c in b["reel"]["cards"]]
        self.assertGreater(max(spans) - min(spans), 1.0, spans)

    def test_draft_refuses_an_ask_outside_the_range_and_makes_nothing(self):
        ws = fixture.workspace()
        fixture.researched(ws)
        bd = fixture.build(ws)
        shutil.copyfile(bd / "taste.draft.md", bd / "taste.md")
        t = json.loads((bd / "taste.json").read_text())
        t["ask"] = {"seconds": 60}
        (bd / "taste.json").write_text(json.dumps(t))
        before = sorted(str(p.relative_to(ws)) for p in ws.rglob("*"))
        r = run(ws, "storyboard.py", "draft")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "not delivered: this kit makes a reel of 12 to 30 s, and the ask is for 60 s. "
                                           "Ask for a length in that range.")
        self.assertEqual(sorted(str(p.relative_to(ws)) for p in ws.rglob("*")), before)


class Counts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.month = fixture.month()

    def test_asked_counts_count_up_over_their_hold(self):
        b = compose.board("editorial-quiet", asked(self.month, counts=True))
        rows = [x for x in lines_of(b) if x.get("name") == "count"]
        self.assertTrue(rows)
        for x in rows:
            self.assertGreaterEqual(x["tally"]["beats"], 1.0, x["text"])
        self.assertEqual(storyboard.count_check(b), [])

    def test_unasked_there_are_no_counts_and_a_shown_count_is_a_failure(self):
        b = compose.board("editorial-quiet", picked(self.month))
        self.assertEqual([x for x in lines_of(b) if x.get("name") == "count"], [])
        c = compose.board("editorial-quiet", asked(self.month, counts=True))
        for x in lines_of(c):
            x.pop("tally", None)
        self.assertTrue(storyboard.count_check(c))


class Handle(unittest.TestCase):
    def test_no_handle_means_no_handle_line_and_no_name_on_any_card(self):
        m = picked(fixture.month())
        m["handle"], m["name"] = None, "lucky fried"
        b = compose.board("editorial-quiet", m)
        text = json.dumps(b)
        self.assertNotIn("lucky fried", text)
        m["handle"] = "ines.photo"
        signed = compose.board("editorial-quiet", m)
        self.assertIn("@ines.photo", json.dumps([x["text"].lower() for x in lines_of(signed)]))
        self.assertNotIn("ines.photo", json.dumps([x["text"].lower() for x in lines_of(b)]))
        # the closing page signs off with the handle, and with none it carries none
        self.assertEqual((signed["reel"]["look"]["handle"], b["reel"]["look"]["handle"]), ("@ines.photo", ""))
        self.assertEqual(len(b["beats"][0]["lines"]), len(signed["beats"][0]["lines"]) - 1)
        self.assertIsNone(b["handle"])
        self.assertEqual(b["reel"]["look"]["signoff"].lower(), "see you in october.")

    def test_gather_never_takes_an_email_or_a_name_as_the_handle(self):
        for given in ("pat@example.com", "pat baker", "example.com"):
            ws = fixture.workspace()
            (ws / "pulled" / "items.json").write_text(json.dumps({"source": "instagram account", "handle": given}))
            r = run(ws, "gather.py", "--pulled", "pulled", "--month", "september")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("handle: none", r.stdout)
            lib = json.loads((fixture.build(ws) / "library.json").read_text())
            self.assertIsNone(lib["handle"])
            self.assertTrue(any("not used" in a for a in lib["assumptions"]), lib["assumptions"])

    def test_a_username_is_kept(self):
        ws = fixture.workspace()
        r = run(ws, "gather.py", "--pulled", "pulled", "--month", "september")
        self.assertIn("handle: @ines.photo", r.stdout)


class Wall(unittest.TestCase):
    def test_every_post_with_a_photograph_has_a_cell_and_one_without_counts(self):
        ws = Path(tempfile.mkdtemp(prefix="mir-wall-"))
        rows = ["date,type,caption,likes,comments,photo"]
        src = sorted((fixture.FIXTURE / "photos").iterdir())
        (ws / "photos").mkdir()
        for i, day in enumerate((2, 6, 10, 15, 20, 27)):
            name = "" if day == 6 else f"photos/{day:02d}.jpg"
            if name:
                shutil.copy(src[i], ws / name)
            rows.append(f"2026-08-{day:02d},{'reel' if day in (6, 20) else 'photo'},post on the {day}th,{900 if day == 6 else 100 + day},{day},{name}")
        (ws / "posts.csv").write_text("\n".join(rows) + "\n")
        self.assertEqual(run(ws, "gather.py", "--month", "august", "--today", "2026-09-03").returncode, 0)
        self.assertEqual(run(ws, "research.py").returncode, 0)
        m = json.loads((fixture.build(ws) / "month.json").read_text())
        self.assertEqual(len(m["posts"]), 6)
        b = compose.board("editorial-quiet", m)
        self.assertEqual(sorted(t["day"] for t in b["reel"]["closer"]["tiles"]), [2, 10, 15, 20, 27])
        c = compose.board("editorial-quiet", asked(m, counts=True))
        said = " ".join(x["text"] for x in lines_of(c))
        self.assertIn("900 likes", said)
        self.assertEqual(sorted(t["day"] for t in c["reel"]["closer"]["tiles"]), [2, 10, 15, 20, 27])


class Grade(unittest.TestCase):
    def test_every_photograph_moves_toward_the_sets_median_before_it_is_staged(self):
        m = fixture.month()
        paths = [p["photo"] for p in m["posts"] if p["photo"]]
        target = photos.median_lightness(paths)
        b = compose.board("editorial-quiet", picked(m))
        self.assertAlmostEqual(b["reel"]["grade"]["target"], round(target, 4))
        out = Path(tempfile.mkdtemp(prefix="mir-grade-"))
        for i, p in enumerate(paths):
            before = photos.lightness(photos.open_image(p))
            after = photos.lightness(Image.open(photos.stage(p, out / f"{i}.jpg", target)))
            if abs(before - target) > 0.03:
                self.assertLess(abs(after - target), abs(before - target), p)
        # the set's one color: a photograph cooler than the set's median cast is warmed toward it, within CAST
        cast = photos.median_cast(paths)
        self.assertEqual(b["reel"]["grade"]["cast"], cast)
        self.assertGreater(cast[0], cast[2])
        cool = Image.new("RGB", (64, 64), (70, 90, 140))
        own = photos.cast_of(cool)
        got = photos.cast_of(photos.graded(cool, photos.lightness(cool), photos.lightness(cool), cast))
        self.assertGreater(got[0] / got[2], own[0] / own[2])
        self.assertLess(abs(got[0] - cast[0]), abs(own[0] - cast[0]))
        self.assertLessEqual(got[2] / own[2], 1.0)
        self.assertGreaterEqual(got[2] / own[2], photos.CAST[0] - 0.02)
        flat = Image.new("RGB", (64, 64), (40, 40, 40))
        self.assertGreater(photos.lightness(photos.graded(flat, photos.lightness(flat), 0.6)), photos.lightness(flat))
        self.assertEqual(photos.graded(flat, photos.lightness(flat), None).getpixel((0, 0)), (40, 40, 40))


if __name__ == "__main__":
    unittest.main()
