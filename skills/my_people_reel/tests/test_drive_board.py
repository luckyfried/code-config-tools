"""The drive board's check: a person's card passes as the film lays it out, and each way a line or a tag can leave its
place is refused: type outside the safe area, under the floor or under its edge onto the photograph, and a tag outside
the safe area or running into the type, two tags on the closer's wall over each other, a print on the wall that cuts
the face its cast names, lies under type, or shows less than half of its photograph's shorter side (in every format),
and a format whose closer has no layout is named by the check with its cause. A card is laid on
the person's first photograph (their moment's), always. A card's type is the stamp of where and when the photograph of
the two of them was taken and the other's own words over it, never a count; the film runs in taste.json's order and
holds the last a beat longer; the closer's wall carries each person's stamp and the last person's stamp, the handle and the title. A
line is a person's own when their comments, captions or replies say it, never because taste.json does. A framed
photograph's print stands right under the edge, its top no further below it than the tag's room over the head.

    python3 -I -m unittest discover -s S/tests
"""
import copy
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive  # noqa: E402
import storyboard  # noqa: E402
import boards  # noqa: E402
import layout as L  # noqa: E402

# the photographs' colors the scrapbook card's palette rule makes the board's colors from
SWATCHES = ["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"]


STAMP = {"text": "sicily, july", "x": 88, "y": 854.0, "size": 150, "file": "fonts/styles/scrapbook/CaveatBrush-Regular.ttf",
         "face": "display", "tracking": -0.02, "color": "ink", "rotate": 0.0, "pivot": [88, 854.0], "name": "stamp-5"}
SAID = {"text": "save me a seat and a spoon", "x": 88, "y": 628.0, "size": 62, "file": "fonts/styles/scrapbook/Gloock-Regular.ttf",
        "face": "text", "tracking": -0.02, "color": "ink", "rotate": 0.0, "pivot": [88, 854.0]}
TAG = {"text": "@kofi.cooks", "file": "fonts/styles/scrapbook/CaveatBrush-Regular.ttf", "size": 42, "tip": [540.0, 1233.5], "side": "above",
       "box": [393.0, 1140.2, 687.0, 1215.8]}


def card():
    """A person's card in the reel, as board_drive lays out the fifth person's: the stamp and their words over a level
    edge at y 1000, their tag in the photograph under it."""
    return {"format": {"kind": "reel"}, "beats": [{"id": "person-5", "layers": [
        {"kind": "Cut", "at": 0, "line": [1000.0, 1000.0], "field": "photo"},
        {"kind": "Words", "at": 1.0, "lines": [dict(STAMP)]},
        {"kind": "Words", "at": 1.35, "lines": [dict(SAID)]},
        {"kind": "Tags", "at": 0.25, "tags": [copy.deepcopy(TAG)]}]}]}


def found(board):
    return [msg for _, msg in board_drive.problems(board)]


def person(rank=4, handle="kofi.cooks", stamp="marrakech, september", voice="warm"):
    return types.SimpleNamespace(rank=rank, handle=handle, stamp=stamp, voice=voice)


PERSON = {"handle": "dani.reyes", "rank": 1, "score": 110, "stretch": {"months": [7, 8], "label": "july and august"},
          "line": {"text": "remember when we missed the last ferry", "from": "their comment"}}


class DriveBoard(unittest.TestCase):
    def setUp(self):
        board_drive.use("scrapbook", swatches=SWATCHES)

    def test_the_card_as_laid_out_passes(self):
        self.assertEqual(found(card()), [])

    def test_a_line_past_the_safe_area_is_refused(self):
        b = card()
        b["beats"][0]["layers"][2]["lines"][0]["x"] = 600
        self.assertTrue(any("runs outside the safe area" in m for m in found(b)), found(b))

    def test_a_line_under_the_floor_is_refused(self):
        b = card()
        b["beats"][0]["layers"][2]["lines"][0]["size"] = 30
        self.assertTrue(any("under the 28 px floor" in m for m in found(b)), found(b))

    def test_a_line_under_its_edge_is_refused(self):
        b = card()
        b["beats"][0]["layers"][2]["lines"][0]["y"] = 1040
        self.assertTrue(any("under its edge onto the photograph" in m for m in found(b)), found(b))

    def test_a_line_that_runs_into_another_is_refused(self):
        b = card()
        b["beats"][0]["layers"][2]["lines"][0]["y"] = 800
        self.assertTrue(any("'save me a seat and a spoon' runs into 'sicily, july'" in m for m in found(b)), found(b))

    def test_a_tag_that_points_out_of_the_frame_is_refused(self):
        """A tag's pill stays inside the safe area; its pointer may reach past the safe area's side to a head standing
        there, never out of the frame."""
        b = card()
        b["beats"][0]["layers"][3]["tags"][0]["tip"] = [1000.0, 1233.5]
        self.assertEqual(found(b), [])
        b["beats"][0]["layers"][3]["tags"][0]["tip"] = [1100.0, 1233.5]
        self.assertEqual(found(b), ["the tag @kofi.cooks runs outside the safe area"])
        b["beats"][0]["layers"][3]["tags"][0]["tip"] = [540.0, 1253.5]
        self.assertEqual(found(b), ["the tag @kofi.cooks runs outside the safe area"])

    def test_a_tag_over_the_type_is_refused(self):
        b = card()
        b["beats"][0]["layers"][3]["tags"][0]["box"] = [100.0, 580.0, 394.0, 655.0]
        self.assertEqual(found(b), ["the tag @kofi.cooks runs into the type"])

    def test_two_wall_tags_over_each_other_are_refused(self):
        def slice_(owner, box):
            x = 476.0 * (owner % 4)
            poly = [[x, 0.0], [x + 468.0, 0.0], [x + 468.0, 400.0], [x, 400.0]]
            return {"kind": "Slice", "owner": owner, "poly": poly, "place": [x, -100.0, 468.0, 624.0], "photo": {"role": "kofi.cooks-1"},
                    "tag": dict(TAG, box=box, owner=owner)}
        b = {"format": {"kind": "wide"}, "beats": [{"id": "closer", "layers": [
            slice_(4, [752.0, 213.9, 1041.4, 289.5]), slice_(2, [1100.0, 220.7, 1420.0, 296.3])]}]}
        self.assertEqual(found(b), [])
        b["beats"][0]["layers"][1]["tag"]["box"] = [829.1, 220.7, 1149.2, 296.3]
        self.assertEqual(found(b), ["the tag @kofi.cooks runs into the type or another tag"])

    def test_a_cards_type_is_the_stamp_and_their_own_words(self):
        """A card's lines are the stamp of where and when the photograph was taken, in the person's case, and the
        other's own words over it: no count, no rank, no caption of what a number counts."""
        self.assertEqual(boards.Person(PERSON, {"when": "july", "where": "sicily"}).stamp, "sicily, july")
        self.assertEqual(boards.Person(PERSON, {"when": "july", "where": "sicily"}, lowercase=False).stamp, "Sicily, July")
        self.assertEqual(boards.Person(PERSON).stamp, "july and august")
        F = L.Frame("reel")
        edge = board_drive.Edge(F, 860, 0.0)
        lines = board_drive.stamp_lines(F, person(), "save me a seat and a spoon", edge, 1.0)
        self.assertEqual([ln["name"] for ln in lines], ["stamp-4", "said-4-0"])
        self.assertEqual([ln["text"] for ln in lines], ["marrakech, september", "save me a seat and a spoon"])
        self.assertTrue(board_drive.fits(F, lines, edge))

    def test_the_wall_carries_each_stamp_and_the_handle_and_title_on_paper(self):
        """On the closer's wall each person's stamp hangs under their slice's edge, the last person's too, and the
        handle and the title stand on the paper over the last edge, the title the largest type on the wall: no count,
        no rank."""
        F = L.Frame("reel")
        (chip,) = board_drive.chip(F, person(rank=5, handle="liv.outside", stamp="lisbon, january"), (0, 540), board_drive.Edge(F, 100, 0.0), 96)
        self.assertEqual((chip["name"], chip["text"]), ("stamp-5", "lisbon, january"))
        self.assertLessEqual(board_drive.width(chip), 540 - 16 - chip["x"])
        ctx = types.SimpleNamespace(handle="maren.okafor", year=2026)
        lines = board_drive.hero_lines(F, ctx, board_drive.Edge(F, 1200, 0.0), 1.0)
        self.assertEqual([ln["name"] for ln in lines], ["handle-0", "handle-1"])
        self.assertEqual([ln["text"] for ln in lines], ["@maren.okafor · 2026", "my people."])
        self.assertGreater(lines[1]["size"], chip["size"])
        self.assertLess(lines[1]["y"], 1200)
        self.assertTrue(board_drive.fits(F, lines, board_drive.Edge(F, 1200, 0.0)))

    def test_the_draft_runs_in_tastes_order_and_holds_the_last_longest(self):
        """The cards run in the order taste.json lists the people, whatever their rank, each named by its place in
        that order, with their line for as long as its words need, and the last, the one the film closes on, the
        longest of them all by a beat."""
        def told(rank, handle, line):
            return types.SimpleNamespace(rank=rank, handle=handle, line=line)
        people = [told(3, "dani.reyes", "remember when we missed the last ferry and it turned into the best night of the whole summer"),
                  told(1, "theo.makes", "porto in april has a light i keep trying to mix"), told(2, "liv.outside", None)]
        beats = board_drive.draft(types.SimpleNamespace(people=people))
        self.assertEqual([(b["id"], (b["line"] or "").split()[:1], b["pulses"]) for b in beats if b["comp"] == "person"],
                         [("person-1", ["remember"], 7), ("person-2", ["porto"], 6), ("person-3", [], 8)])

    def test_a_wall_slice_that_cuts_its_face_is_refused(self):
        """The first person's slice across the foot of the wide wall, its photograph's face named in the cast: laid
        with the face inside the slice it passes; laid with the top of the head at the frame's foot it is refused."""
        foot = [[-20.0, 400.0], [1940.0, 400.0], [1940.0, 1120.0], [-20.0, 1120.0]]
        face = [0.5, 0.3, 0.6, 0.45]
        b = {"format": {"kind": "wide"}, "beats": [{"id": "closer", "layers": [
            {"kind": "Slice", "owner": 1, "poly": foot, "photo": {"role": "dani.reyes-0", "face": face}, "place": [-20.0, 300.0, 1960.0, 1307.0]}]}]}
        self.assertEqual(found(b), [])
        b["beats"][0]["layers"][0]["place"] = [-20.0, 700.0, 1960.0, 1307.0]
        self.assertEqual(found(b), ["the wall cuts the face in dani.reyes-0"])

    def test_type_over_a_face_on_the_wall_is_refused(self):
        """A stamp on the closer's wall beside the face its cast names passes; the same stamp across that face is
        refused."""
        foot = [[-20.0, 400.0], [1940.0, 400.0], [1940.0, 1120.0], [-20.0, 1120.0]]
        face = [0.5, 0.3, 0.6, 0.45]

        def wall(x):
            return {"format": {"kind": "wide"}, "beats": [{"id": "closer", "layers": [
                {"kind": "Slice", "owner": 1, "poly": foot, "photo": {"role": "dani.reyes-0", "face": face}, "place": [-20.0, 300.0, 1960.0, 1307.0]},
                {"kind": "Words", "at": 1.0, "lines": [dict(STAMP, x=x, pivot=[x, STAMP["y"]])]}]}]}
        self.assertEqual(found(wall(200)), [])
        self.assertEqual(found(wall(900)), ["the wall's type covers the face in dani.reyes-0"])

    def test_a_format_with_no_wall_is_named_by_the_check_and_the_check_goes_on(self):
        """A format whose closer has no layout is one of the check's problems, named by its format with its cause,
        and every other format is still checked."""
        def layout(sb, ctx, kind, bpm=None):
            raise board_drive.Unfit(f"the drive closer has no layout for 6 people in {kind}", {"ines.walks-0"})
        with mock.patch.object(storyboard.boards, "layout", layout):
            got = storyboard.problems({"tone": "drive", "beats": [], "people": []}, types.SimpleNamespace(by={}, people=[]))
        self.assertEqual(got, [(k, f"the drive closer has no layout for 6 people in {k}") for k in storyboard.FORMATS])

    def test_a_draft_with_no_wall_prints_its_cause_and_exits_one(self):
        """A draft whose closer has no layout prints one FAIL line naming the cause and returns 1, never a traceback."""
        import io
        import os
        import tempfile
        from contextlib import redirect_stdout

        def layout(sb, ctx, kind, bpm=None):
            raise board_drive.Unfit(f"the closer has no layout for 5 people in {kind}", {"ze.do.largo-0"})
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                Path("taste.md").write_text("# taste\n")
                out = io.StringIO()
                with mock.patch.object(storyboard.boards, "Ctx", lambda: types.SimpleNamespace(by={}, people=[])), \
                        mock.patch.object(storyboard.boards, "draft", lambda t, ctx: {"style": t, "bpm": 120, "beats": [], "people": []}), \
                        mock.patch.object(storyboard.boards, "layout", layout), redirect_stdout(out):
                    rc = storyboard.cmd_draft(types.SimpleNamespace(style=None))
            finally:
                os.chdir(here)
        self.assertEqual(rc, 1)
        for t in ("scrapbook", "analog-home-movie", "kinetic-type"):
            self.assertIn(f"FAIL  {t}: the closer has no layout for 5 people in reel", out.getvalue())

    def test_a_wall_print_keeps_half_its_shorter_side_in_every_format(self):
        """A print on the closer's wall shows at least half of its photograph's shorter side, across and down, so the
        eye reads the photograph: in each format a portrait print showing 0.6 of its width passes, and the same print
        cut to a band of 0.4 is refused."""
        sizes = {"reel": (1080, 1920), "square": (1080, 1080), "wide": (1920, 1080)}
        for kind, (W, H) in sizes.items():
            with self.subTest(kind=kind):
                w, h = 0.4 * W, 0.4 * W * 1.25
                place = [0.0, 0.0, w, h]

                def wall(seen):
                    poly = [[0.0, 0.0], [seen * w, 0.0], [seen * w, h], [0.0, h]]
                    return {"format": {"kind": kind}, "beats": [{"id": "closer", "layers": [
                        {"kind": "Slice", "owner": 2, "poly": poly, "place": place, "photo": {"role": "ines.walks-0"}}]}]}
                self.assertEqual(found(wall(0.6)), [])
                self.assertEqual(found(wall(0.4)), ["the wall shows less than half of the shorter side of ines.walks-0"])

    def test_a_wall_print_that_cannot_fill_its_slice_stands_whole_on_paper(self):
        """A tall photograph with a large face across the short foot of the wide wall: filling the slice would show a
        band of it and cut the face, so it stands smaller, its slice trimmed to it, and neither refusal holds."""
        F = L.Frame("wide")
        role, face = "dani.reyes-0", [0.3, 0.2, 0.7, 0.6]
        photos = types.SimpleNamespace(aspect={role: 1.33}, info={role: {"point": [0.5, 0.4], "face": face}}.get, framed=lambda r: False)
        foot = [[-20.0, 700.0], [1940.0, 700.0], [1940.0, 1100.0], [-20.0, 1100.0]]
        pl = board_drive.slice_place(photos, role, foot, (0.5, 0.4), F)
        poly = board_drive.trimmed(foot, pl)
        s = {"poly": poly, "place": pl, "photo": {"role": role, "face": face}}
        self.assertFalse(board_drive.sliver(F, s))
        self.assertFalse(board_drive.face_cut(F, s))
        xs, ys = [x for x, _ in poly], [y for _, y in poly]
        self.assertLess(max(xs) - min(xs), 1960 - 1)
        self.assertTrue(pl[0] - 0.5 <= min(xs) and max(xs) <= pl[0] + pl[2] + 0.5 and pl[1] - 0.5 <= min(ys) and max(ys) <= pl[1] + pl[3] + 0.5)

    def test_a_wall_tag_under_a_stamp_points_up_past_it(self):
        """A top-row person whose chin sits just under the safe area's top, a stamp hanging over the place under it:
        the tag stands under the stamp, inside the slice, its pointer reaching up to the chin."""
        F = L.Frame("reel")
        role = "theo.makes-0"
        photos = types.SimpleNamespace(info={role: {"point": [0.3, 0.2], "face": [0.25, 0.1, 0.35, 0.2]}}.get)
        poly = [[540.0, -20.0], [1100.0, -20.0], [1100.0, 700.0], [540.0, 700.0]]
        pl = [540.0, -20.0, 560.0, 1400.0]
        stamp = [560.0, F.top, 760.0, 400.0]
        t = board_drive.wall_tag(F, photos, role, "theo.makes", pl, poly, [stamp])
        self.assertIsNotNone(t)
        self.assertGreaterEqual(t["box"][1], stamp[3])
        self.assertLessEqual(t["box"][3], 700.0)
        self.assertEqual(t["tip"], [round(540.0 + 0.30 * 560.0, 1), round(-20.0 + 0.21 * 1400.0, 1)])

    def test_a_wall_tag_for_a_chin_over_the_safe_area_stands_under_the_stamp(self):
        """A top-row person whose whole face stands over the safe area's top, a stamp hanging under it: the tag comes
        down into the safe area and, finding the stamp there, stands under it, its pointer reaching up to the chin."""
        F = L.Frame("reel")
        role = "theo.makes-0"
        photos = types.SimpleNamespace(info={role: {"point": [0.3, 0.06], "face": [0.25, 0.03, 0.35, 0.1]}}.get)
        poly = [[540.0, -20.0], [1100.0, -20.0], [1100.0, 600.0], [540.0, 600.0]]
        pl = [540.0, -20.0, 560.0, 1400.0]
        stamp = [560.0, F.top + 9, 760.0, F.top + 115]
        t = board_drive.wall_tag(F, photos, role, "theo.makes", pl, poly, [stamp])
        self.assertIsNotNone(t)
        self.assertGreaterEqual(t["box"][1], stamp[3])
        self.assertLessEqual(t["box"][3], 600.0)

    def test_a_line_breaks_into_an_even_rag_before_it_breaks_before_a_phrase(self):
        """A line's words break as evenly as they allow; a break before a phrase wins only among even rags, so no
        short first line stands over a long one because the long one opens with "our"."""
        text = "the razor man on our corner since before i was born, cap on, pink packets out"
        probe = board_drive.line(text, "text", 44, 0, 0)
        for f in (0.6, 0.7, 0.8, 0.9):
            rows = board_drive.wrap(probe, board_drive.width(probe) * f)
            ws = [board_drive.width(probe, r) for r in rows]
            self.assertGreater(min(ws), 0.6 * max(ws), rows)

    def test_a_card_is_laid_on_their_first_photograph_always(self):
        """The first photograph is the moment's, the one the stamp names and the words are about; a second never takes
        its card, though the first leaves no clear placement and the second does."""
        rows = [{"file": "a.jpg", "point": [0.5, 0.45], "face": [0.0, 0.0, 1.0, 1.0]}, {"file": "b.jpg", "point": [0.5, 0.45]}]
        info = {"kofi.cooks-0": rows[0], "kofi.cooks-1": rows[1]}
        photos = types.SimpleNamespace(cast={"people": {"kofi.cooks": rows}}, info=info.get,
                                       aspect={"kofi.cooks-0": 1.0, "kofi.cooks-1": 0.8}, framed=lambda r: False)
        _, role, _, ok = board_drive.card(board_drive.lensed(L.Frame("reel")), photos, person(), "save me a seat", 0)
        self.assertEqual((role, ok), ("kofi.cooks-0", False))

    def test_a_face_at_the_top_of_its_photograph_stands_under_the_edge_on_paper(self):
        """A wide photograph whose face sits near its top cannot fill the reel with the face under an edge; the card
        lays the photograph from the edge down, the stamp and words on the paper over it, the face whole and clear of
        the type and the tag."""
        info = {"theo.makes-0": {"file": "a.jpg", "point": [0.33, 0.27], "tip": [0.33, 0.32], "face": [0.29, 0.11, 0.38, 0.28]}}
        photos = types.SimpleNamespace(cast={"people": {"theo.makes": [info["theo.makes-0"]]}}, info=info.get,
                                       aspect={"theo.makes-0": 0.7025}, framed=lambda r: False)
        F = board_drive.lensed(L.Frame("reel"))
        edge, role, layers, ok = board_drive.card(F, photos, person(rank=2, handle="theo.makes", stamp="april"),
                                                  "you underexposed by half a stop and it still beats mine", 1)
        cut = layers[0]
        self.assertEqual((role, ok, cut["field"]), ("theo.makes-0", True, "bg"))
        self.assertGreaterEqual(cut["place"][1], min(edge.yl, edge.yr) - 0.5)
        self.assertEqual(found({"format": {"kind": "reel"}, "beats": [{"id": "person-2", "layers": layers}]}), [])

    def test_a_large_face_in_a_framed_photograph_stays_whole_in_the_wide_frame(self):
        """A landscape photograph laid whole across its 9:16 picture fills the 16:9 frame's width, so its face runs a
        half of the frame's height: the card raises the photograph until the chin clears the frame's foot, the face
        whole and clear of the type and the tag."""
        info = {"ze.do.largo-0": {"file": "a.jpg", "point": [0.6, 0.45], "tip": [0.72, 0.6], "face": [0.44, 0.39, 0.75, 0.55]}}
        photos = types.SimpleNamespace(cast={"people": {"ze.do.largo": [info["ze.do.largo-0"]]}}, info=info.get,
                                       aspect={"ze.do.largo-0": 1.7778}, framed=lambda r: True, band={"ze.do.largo-0": (0.285, 0.715)})
        F = board_drive.lensed(L.Frame("wide"))
        edge, role, layers, ok = board_drive.card(F, photos, person(rank=5, handle="ze.do.largo", stamp="september"),
                                                  "the razor man on our corner since before i was born", 5)
        self.assertTrue(ok)
        self.assertEqual(found({"format": {"kind": "wide"}, "beats": [{"id": "person-5", "layers": layers}]}), [])

    def test_a_wall_stamp_hangs_clear_of_a_person_with_no_face_named(self):
        """A silhouette's slice on the wall names no face: its stamp hangs on the side of the slice away from the point
        the cast keeps in view, never across the person."""
        F = L.Frame("wide")
        info = {"tomas.surf-0": {"point": [0.1, 0.2]}}
        photos = types.SimpleNamespace(info=info.get)
        pl = [600.0, 0.0, 500.0, 800.0]
        (num,) = board_drive.hung(F, photos, "tomas.surf-0", person(rank=1, handle="tomas.surf", stamp="august"),
                               (600.0, 1100.0), board_drive.Edge(F, 100, 0), 64, pl)
        self.assertGreater(num["x"], 800)

    def test_type_beside_a_dark_print_stands_in_ink_on_the_paper(self):
        """Type set beside a dark photograph, on the paper around it, is read against the paper and set in ink."""
        from unittest import mock
        from PIL import Image
        ln = board_drive.line("september", "display", 150, 88, 854)
        with mock.patch.object(board_drive, "pixels", lambda file: Image.new("RGB", (64, 64))):
            tone, _ = board_drive.tone_of(L.Frame("reel"), "matched/a.jpg", [700.0, 0.0, 380.0, 1920.0], [ln])
        self.assertEqual(tone, "ink")

    def test_each_wall_slice_is_owned_by_its_card_in_the_films_order(self):
        """A card finds its slice on the wall by its place in the film: the beat person-N and the slice owned by N are
        the same person's, whatever their rank."""
        handles = ["liv.outside", "theo.makes", "ines.walks", "dani.reyes", "kofi.cooks"]
        people = [person(rank=r, handle=h, stamp=m) for r, h, m in zip((5, 2, 3, 1, 4), handles, ("january", "april", "may", "august", "october"))]
        info = {f"{h}-0": {"file": "a.jpg", "point": [0.5, 0.4]} for h in handles}
        photos = types.SimpleNamespace(cast={"people": {h: [info[f"{h}-0"]] for h in handles}}, info=info.get,
                                       aspect={k: 0.75 for k in info}, framed=lambda r: False)
        ctx = types.SimpleNamespace(people=people, photos=photos, handle="maren.okafor", year=2026)
        F = board_drive.lensed(L.Frame("wide"))
        layers = board_drive.closer(F, ctx, {h: f"{h}-0" for h in handles}, board_drive.Edge(F, 700, 0.0))
        owners = {L_["photo"]["role"]: L_["owner"] for L_ in layers if L_["kind"] == "Slice"}
        beats = board_drive.draft(types.SimpleNamespace(people=[types.SimpleNamespace(rank=p.rank, handle=p.handle, line=None) for p in people]))
        self.assertEqual({f"{b['person']}-0": int(b["id"].split("-")[1]) for b in beats if b["comp"] == "person"}, owners)

    def test_a_wall_tag_never_stands_over_the_safe_area(self):
        """A tag on the closer's wall whose person stands at the very top of a top-row slice is not hung over the
        safe area's top: wall_tag finds no place for it, and the wall moves that photograph down instead."""
        F = L.Frame("reel")
        photos = types.SimpleNamespace(info={"kofi.cooks-0": {"point": [0.5, 0.02]}}.get)
        poly = [[0.0, -60.0], [1080.0, -60.0], [1080.0, 600.0], [0.0, 600.0]]
        t = board_drive.wall_tag(F, photos, "kofi.cooks-0", "kofi.cooks", [0.0, -60.0, 1080.0, 1350.0], poly, [])
        self.assertTrue(t is None or t["box"][1] >= F.top, t)

    def test_a_card_says_the_line_taste_settled_for_their_moment(self):
        """The card's words are the line taste.json settled for the person's moment, else people.json's pick; a moment
        taste.json left without a line, or with emoji alone, is wordless, never given the pick."""
        p = {"handle": "theo.makes", "rank": 2, "line": {"text": "porto in april has a light i keep trying to mix", "from": "their comment"},
             "lines": [{"text": "you underexposed by half a stop and it still beats mine"}]}
        settled = boards.Person(p, {"line": "you underexposed by half a stop and it still beats mine"}, 2026)
        self.assertEqual(board_drive.heard_line(settled), "you underexposed by half a stop and it still beats mine")
        self.assertEqual(board_drive.heard_line(boards.Person(p, {}, 2026)), "porto in april has a light i keep trying to mix")
        self.assertIsNone(board_drive.heard_line(boards.Person(p, {"line": ""}, 2026)))
        self.assertIsNone(board_drive.heard_line(boards.Person(p, {"line": "\U0001F382\U0001F382"}, 2026)))

    def test_a_line_with_emoji_is_said_without_them(self):
        """A person's line that carries emoji is said in their words with the emoji off, and the storyboard check knows
        it as theirs; a line of emoji alone, or one with a link, is never said."""
        p = {"handle": "joana.lima", "rank": 2, "line": {"text": "my face when i read your texts, every single time \U0001F602"},
             "lines": [{"text": "who said you could post this without asking me \U0001F62D"}, {"text": "\U0001F382\U0001F382"},
                       {"text": "look http://x.co"}]}
        joana = boards.Person(p, {"line": "who said you could post this without asking me \U0001F62D"}, 2026)
        self.assertEqual(board_drive.heard_line(joana), "who said you could post this without asking me")
        self.assertIn("who said you could post this without asking me", storyboard.own_lines(joana))
        self.assertEqual(board_drive.heard_line(boards.Person(p, {}, 2026)), "my face when i read your texts, every single time")

    def test_a_caption_is_said_without_the_handles_that_trail_it(self):
        """A caption that ends on the person's handle is said without it, since their tag shows it, and the storyboard
        check knows the shorter line as theirs; a handle inside the line stays."""
        p = {"handle": "ze.do.largo", "rank": 5, "lines": [],
             "line": {"text": "the razor man on our corner, cap on, pink packets out @ze.do.largo"}}
        ze = boards.Person(p, {}, 2026)
        self.assertEqual(board_drive.heard_line(ze), "the razor man on our corner, cap on, pink packets out")
        self.assertIn("the razor man on our corner, cap on, pink packets out", storyboard.own_lines(ze))
        self.assertEqual(boards.said("@rita.clay's hands on the wheel @rita.clay @joana.lima"), "@rita.clay's hands on the wheel")

    def test_a_line_taste_wrote_is_not_its_own_source(self):
        """A line taste.json carries that none of the person's comments, captions or replies say is not theirs: the
        storyboard check refuses it."""
        p = {"handle": "theo.makes", "rank": 2, "line": {"text": "porto in april has a light i keep trying to mix"}, "lines": [],
             "exchanges": [{"they": "good lines", "own": "@theo.makes thank you"}]}
        theo = boards.Person(p, {"line": "porto in april, the light"}, 2026)
        self.assertNotIn("porto in april, the light", storyboard.own_lines(theo))
        self.assertTrue({"porto in april has a light i keep trying to mix", "good lines", "thank you"} <= storyboard.own_lines(theo))


class FramedPrint(unittest.TestCase):
    def test_a_landscape_print_on_a_tall_card_starts_at_the_edge_not_a_mounts_width_under_it(self):
        F = L.Frame("reel")
        edge = board_drive.Edge(F, 860, 0.0)
        clear = board_drive.CLEAR + (board_drive.POINTER + board_drive.PILL_H) * board_drive.TAG["reel"] + 8
        band = (0.2942, 0.7058)
        place, _ = board_drive.cover(F, 1920 / 1080, edge, (0.47, 0.3436), 540, clear=clear, most=1.0, foot=0.07, band=band)
        print_top = place[1] + band[0] * place[3]
        head = place[1] + 0.3436 * place[3]
        self.assertLessEqual(print_top - 860, clear)
        self.assertGreaterEqual(head - 860, clear - 0.5)


if __name__ == "__main__":
    unittest.main()
