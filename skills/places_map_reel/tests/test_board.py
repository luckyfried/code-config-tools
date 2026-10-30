"""The drive storyboard solved from a year's source (tests/data/trip.json, eleven places from Lisbon to Oaxaca and
back, with their line from most visits): every format passes the storyboard's checks, and each check refuses the board it
is there to refuse; the film is their moments, drafted from their captions, each beat on its own photograph and their line,
its label never under the type floor, and the hook's title and handle inside the type-safe area in each of the three looks.

    python3 -I -m unittest discover -s S/tests
"""
import copy
import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive  # noqa: E402
import bounds  # noqa: E402
import look  # noqa: E402
import picks  # noqa: E402
import storyboard  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
PHOTOS = {ph["file"]: ph for ph in SOURCE["photos"]}


def plans(bpm=None, style=None):
    return {fmt: storyboard.plan(SOURCE, fmt, bpm, style or look.TRIO[0]) for fmt in storyboard.FORMATS}


def firsts(board):
    first = {}
    for c in board["route"]["cards"]:
        first.setdefault(c["place"], c)
    return first


class DriveBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans = plans()

    def test_the_source_solves_clean_in_every_format_in_each_of_the_three_looks(self):
        for style in look.TRIO:
            by = self.plans if style == look.TRIO[0] else plans(style=style)
            self.assertEqual(storyboard.findings(by, SOURCE["photos"]), [], style)

    def test_every_format_is_cut_on_the_reels_grid(self):
        shape = lambda p: [(b["id"], b["bars"], b["frames"]) for b in p["board"]["beats"]]
        self.assertEqual(shape(self.plans["landscape"]), shape(self.plans["reel"]))
        self.assertEqual(shape(self.plans["square"]), shape(self.plans["reel"]))

    def test_every_beat_says_what_it_reveals_and_what_it_carries(self):
        for b in self.plans["reel"]["board"]["beats"]:
            self.assertTrue(b.get("reveals") and b.get("carries"), b["id"])

    def test_the_film_stops_once_and_holds_still_after_it(self):
        reel = self.plans["reel"]
        b = reel["board"]
        stop = [c["at"] for c in b["sound"] if c["kind"] == "stop"]
        self.assertEqual(len(stop), 1)
        self.assertEqual([c for c in b["sound"] if c["at"] > stop[0]], [])
        # the still runs a second at least: read in frames, as the plan's seconds are rounded to a hundredth
        self.assertGreaterEqual(reel["frames"] - stop[0] * 60 / b["bpm"] * board_drive.FPS, board_drive.STILL * board_drive.FPS - 1e-6)

    def test_a_board_without_its_stop_or_with_a_cue_after_it_is_refused(self):
        b = copy.deepcopy(self.plans["reel"]["board"])
        seconds = self.plans["reel"]["seconds"]
        late = copy.deepcopy(b)
        stop = next(c for c in late["sound"] if c["kind"] == "stop")
        late["sound"].append({**stop, "kind": "hit", "at": stop["at"] + 0.5})
        self.assertTrue(any("after the stop" in x for x in storyboard.sound_findings(late, seconds)))
        b["sound"] = [c for c in b["sound"] if c["kind"] != "stop"]
        self.assertTrue(any("stop cues" in x for x in storyboard.sound_findings(b, seconds)))

    def test_every_place_has_its_name_on_its_card(self):
        # the name leads the label over their line ("Seville · May", or its first row where the label breaks), or, on a
        # stop with no line, it is the line itself
        b = self.plans["reel"]["board"]
        for c in b["route"]["cards"]:
            labels = [ln["text"].lower() for ln in c["lines"] if ln["name"] == "label"]
            name = " ".join(ln["text"] for ln in c["lines"] if ln["name"] == "name").lower()
            self.assertIn(c["name"].lower(), (labels[0].split(" · ")[0] if labels else "", name), c["id"])

    def test_a_label_too_long_for_its_box_at_the_floor_breaks_where_its_parts_meet_never_under_the_floor(self):
        # the name over the month, each row at the card's label size or the type floor, whichever is larger;
        # Aveiro goes by its full name, which no line box holds beside its month at the floor
        long = copy.deepcopy(SOURCE)
        next(q for q in long["places"]["places"] if q["id"] == "aveiro")["name"] = "Aveiro, the Venice of Portugal by the lagoon"
        broke = 0
        for style in look.TRIO:
            for fmt in storyboard.FORMATS:
                p = storyboard.plan(long, fmt, None, style)
                W, H = p["board"]["format"]["width"], p["board"]["format"]["height"]
                for c in p["board"]["route"]["cards"]:
                    labels = [ln for ln in c["lines"] if ln["name"] == "label"]
                    for ln in labels:
                        self.assertGreaterEqual(ln["size"], round(board_drive.LABEL * min(W, H), 1) - 0.05, (style, fmt, ln["text"]))
                    if len(labels) == 2 and labels[0]["text"].lower() == c["name"].lower():
                        broke += 1
                        self.assertEqual(labels[0]["size"], labels[1]["size"], (style, fmt, c["id"]))
                        self.assertGreater(labels[1]["y"], labels[0]["y"], (style, fmt, c["id"]))
        self.assertGreater(broke, 0)

    def test_the_hooks_title_and_handle_stand_inside_the_type_safe_area_in_every_look(self):
        # the scrapbook's turned title rises and falls by its turn, the letterbox's lower third keeps its handle above
        # the safe area's foot
        for style in look.TRIO:
            for fmt, p in plans(style=style).items():
                kicker = p["board"]["route"]["hook"]["kicker"]
                self.assertEqual([ln["name"] for ln in kicker], ["title", "handle"])
                found = [x for x in bounds.check(p["board"]) if x.startswith("safe") and any('"' + ln["text"] + '"' in x for ln in kicker)]
                self.assertEqual(found, [], (style, fmt))

    def test_the_words_stand_in_the_style_cards_faces_colors_and_line_box(self):
        # the label in the card's label face and color, the line in its line face and color, from the top of the card's
        # line box down, and each of the three looks in faces of its own; a look the route sets in heavier instances of
        # its card's families (PHONE) keeps its line at the card's size and rises out of the box's top by what it needs
        files = set()
        for style in look.TRIO:
            card = look.card(style)
            for fmt, p in plans(style=style).items():
                b = p["board"]
                W, H = b["format"]["width"], b["format"]["height"]
                fr = {"width": W, "height": H, **board_drive.SAFE[fmt]}
                for c in b["route"]["cards"]:
                    lay = board_drive.layout_of(card["photo"], PHOTOS[c["file"]], W, H)
                    x0, y0, x1, y1 = board_drive.line_box(fr, lay)
                    phone = board_drive.PHONE.get(style)
                    for ln in c["lines"]:
                        part = lay["label"] if ln["name"] == "label" else lay["line"]
                        face = phone[part["face"]][0] if phone else card["faces"][part["face"]]["file"]
                        self.assertEqual(ln["file"], face, (style, fmt, c["id"]))
                        self.assertEqual(ln["color"], part["color"], (style, fmt, c["id"]))
                        self.assertTrue((phone or y0 - 0.5 <= ln["y"]) and ln["y"] <= y1 + 0.5, (style, fmt, c["id"], ln["text"]))
                        if phone and ln["name"] != "label":
                            self.assertEqual(ln["size"], round(part["size"] * min(W, H) / 1080), (style, fmt, c["id"]))
                    files |= {ln["file"] for ln in c["lines"]}
        self.assertGreaterEqual(len(files), 4)

    def test_a_landscape_photograph_on_the_reel_takes_the_cards_landscape_box_and_its_line_stays_in_its_line_box(self):
        # on the tall frame a photograph wider than it is tall stands in the card's landscape box, and its label and
        # line stand inside the landscape line box, the line fitted down to half the card's size to keep to it
        seen = 0
        for style in look.TRIO:
            card = look.card(style)
            b = plans(style=style)["reel"]["board"]
            W, H = b["format"]["width"], b["format"]["height"]
            fr = {"width": W, "height": H, **board_drive.SAFE["reel"]}
            land = {**card["photo"], "picture": {**card["photo"]["picture"], "box": card["photo"]["landscape"]["box"]},
                    "line": {**card["photo"]["line"], "box": card["photo"]["landscape"]["line"]}}
            pbox = board_drive.picture_box(fr, land["picture"])
            x0, y0, x1, y1 = board_drive.line_box(fr, land)
            for c in b["route"]["cards"]:
                ph = PHOTOS[c["file"]]
                if ph["w"] <= ph["h"]:
                    continue
                seen += 1
                self.assertTrue(pbox[0] <= c["box"][0] and c["box"][2] <= pbox[2] and pbox[1] <= c["box"][1] and c["box"][3] <= pbox[3], (style, c["id"]))
                phone = board_drive.PHONE.get(style)
                for ln in c["lines"]:
                    role = card["photo"]["label" if ln["name"] == "label" else "line"]["face"]
                    face = dict(card["faces"][role], file=phone[role][0]) if phone else card["faces"][role]
                    w = board_drive.width(ln["text"], ln["size"], face)
                    self.assertTrue((phone or y0 - 0.5 <= ln["y"]) and ln["y"] <= y1 + 0.5, (style, c["id"], ln["text"]))
                    if not ln.get("rotate"):
                        self.assertTrue(x0 - 0.5 <= ln["x"] and ln["x"] + w <= x1 + 0.5, (style, c["id"], ln["text"]))
                    if ln["name"] != "label":
                        self.assertGreaterEqual(ln["size"], round(card["photo"]["line"]["size"] * min(W, H) / 1080) / 2 - 0.05, (style, c["id"]))
        self.assertGreater(seen, 0)

    def test_the_closers_map_holds_every_place_of_the_trip_the_far_ones_too(self):
        # Oaxaca is far from Lisbon: its pin, like every other, stands inside the frame the closer settles on
        self.assertIn("oaxaca", {c["place"] for c in self.plans["reel"]["board"]["route"]["cards"] if c["far"]})
        for fmt, plan in self.plans.items():
            rt = plan["board"]["route"]
            for c in rt["cards"]:
                self.assertTrue(0 <= c["pin"][0] <= rt["W"] and 0 <= c["pin"][1] <= rt["H"], (fmt, c["place"], c["pin"]))

    def test_a_photograph_shown_at_another_place_is_refused(self):
        rows = copy.deepcopy(SOURCE["photos"])
        card = self.plans["reel"]["board"]["route"]["cards"][1]
        next(r for r in rows if r["file"] == card["file"])["place"] = "nowhere"
        self.assertTrue(storyboard.binding(self.plans["reel"]["board"], rows))

    def test_beats_start_on_the_frame_nearest_their_musical_beat_at_any_tempo(self):
        for bpm in (96, 118, 125, 137):
            p = storyboard.plan(SOURCE, "reel", bpm)
            pulse = board_drive.FPS * 60 / bpm
            t, start = 0.0, 0
            for b in p["board"]["beats"]:
                self.assertEqual(start, round(t * pulse), (bpm, b["id"]))
                start += b["frames"]
                t += 4 * b["bars"]
            self.assertEqual(start, p["frames"])


class HerMoments(unittest.TestCase):
    """Each visit is a moment: drafted from what they wrote there, held on its own photograph, their line on its card, and
    the film ends on the places they stood in."""

    @classmethod
    def setUpClass(cls):
        cls.board = storyboard.plan(SOURCE, "reel", None)["board"]
        cls.said = {(m["place"], m["n"]): m["line"] for m in SOURCE["moments"] if m["line"]}

    def test_a_visits_moment_is_its_first_post_in_time_order(self):
        day = 86400 * (365 * 56 + 14)  # 2026-01-01
        posts = [(4, "port tasting down by the river with @theo.makes 🌅 #porto", "b.jpg"),
                 (5, "the longest caption of the visit, all about the cellars and the bridge and the river at night", "c.jpg"),
                 (21, "we eloped 💍", "e.jpg"), (40, "posted from porto after they went home", "d.jpg")]
        lib = {"posts": [{"ts": day + 86400 * d, "caption": c, "media": [f]} for d, c, f in posts],
               "reels": [{"ts": day + 86400 * 2, "caption": "the whole night in one reel", "media": ["r.mp4"]}]}
        pl = {"rows": {"posts:0": "porto", "posts:1": "porto", "posts:2": "porto", "posts:3": "porto", "reels:0": "lisbon"},
              "route_visits": [{"place": "lisbon", "from": "2026-01-03", "to": "2026-01-03"},
                               {"place": "porto", "from": "2026-01-05", "to": "2026-01-06"},
                               {"place": "porto", "from": "2026-01-22", "to": "2026-01-22"}]}
        reel, first, again = picks.visit_moments(lib, pl)
        # their first post from the visit, its caption and its photograph together; the longer one waits as a candidate
        self.assertEqual((first["line"], first["with"], first["post"]),
                         ("port tasting down by the river with @theo.makes", ["theo.makes"], "posts:0"))
        self.assertEqual([c["post"] for c in first["captions"]], ["posts:0", "posts:1"])
        self.assertEqual((again["n"], again["line"], again["post"]), (2, "we eloped", "posts:2"))  # two words are a line
        self.assertEqual((reel["line"], reel["post"]), (None, "reels:0"))  # a reel has no photograph: wordless

    def test_her_words_only_ever_stand_on_their_own_posts_photograph(self):
        lib = {"posts": [{"caption": "port tasting", "media": ["b.jpg"]}], "reels": [{"caption": "a reel", "media": ["r.mp4"]}]}
        with mock.patch.object(picks, "prepare", side_effect=lambda f: f"/run/photos/{f}"), \
                mock.patch.object(picks, "shown", side_effect=lambda f: f):
            self.assertEqual(picks.own_print(lib, {"post": "posts:0"}), "/run/photos/b.jpg")
            self.assertIsNone(picks.own_print(lib, {"post": "reels:0"}))
            # a photograph of the set stands for the moment only where the curation pairs them
            self.assertEqual(picks.own_print(lib, {"post": "reels:0", "photo": "set/porto/03-river.jpg"}), "set/porto/03-river.jpg")
        taste = {"moments": [{"place": "porto", "n": 1, "line": "port tasting"}, {"place": "porto", "n": 2, "line": "a reel", "peak": True}]}
        rows = storyboard.moments_of(taste, {("porto", 1): "/run/photos/b.jpg", ("porto", 2): None})
        self.assertEqual(rows, [{"place": "porto", "n": 1, "line": "port tasting", "peak": False},
                                {"place": "porto", "n": 2, "line": None, "peak": True}])

    def test_the_moments_own_print_leads_its_visit_over_a_set_photograph(self):
        import grade
        shots = ["set/oaxaca/06-market-mango-banana-stall.jpg", {"file": "set/oaxaca/01-street.jpg", "line": [0, 0.5, 1, 0.5]}]
        self.assertEqual(grade.own_first(shots, "build/r/photos/mole.jpg"),
                         [{"file": "build/r/photos/mole.jpg"}, {"file": "set/oaxaca/06-market-mango-banana-stall.jpg"},
                          {"file": "set/oaxaca/01-street.jpg", "line": [0, 0.5, 1, 0.5]}])
        # already among the shots, it moves to the front with the line read on it
        self.assertEqual(grade.own_first(shots, "set/oaxaca/01-street.jpg")[0], {"file": "set/oaxaca/01-street.jpg", "line": [0, 0.5, 1, 0.5]})
        self.assertEqual(grade.own_first(shots, None)[0], {"file": "set/oaxaca/06-market-mango-banana-stall.jpg"})

    def test_a_beats_photograph_is_the_one_from_its_moment(self):
        pl = {"route_visits": [{"place": "porto", "from": "2026-01-03"}, {"place": "porto", "from": "2026-01-20"}]}
        options = {"porto": [("/set/porto/01-bridge.jpg", ""), ("/set/porto/02-cellar.jpg", ""), ("/set/porto/03-river.jpg", "")]}
        moments = [{"place": "porto", "n": 2, "photo": "/set/porto/03-river.jpg"}]
        wrote = {}
        with mock.patch.object(picks._env, "read_json", return_value=None), \
                mock.patch.object(picks._env, "write_json", side_effect=lambda name, v: wrote.update({name: v})), \
                mock.patch.object(picks, "contact"), mock.patch.object(picks, "shown", side_effect=lambda f: str(f)):
            picks.write_cast(pl, options, None, moments)
        first, again = wrote["cast.json"]["visits"]
        self.assertEqual(first["shots"][0], "/set/porto/01-bridge.jpg")
        self.assertEqual(again["shots"][0], "/set/porto/03-river.jpg")

    def test_a_stop_holds_by_its_line_and_the_peak_holds_longest(self):
        def held(peak):
            src = copy.deepcopy(SOURCE)
            for m in src["moments"]:
                m["peak"] = (m["place"], m["n"]) == peak
            board = storyboard.plan(src, "reel", None)["board"]
            return board, {(c["place"], c["n"]): b["bars"] * 4 for c, b in zip(board["route"]["cards"], board["beats"])}

        def own(board, beats):
            # a stop's own hold: a stop the camera leaves across a leap carries the camera's travel on top of it
            return {k: v - (board_drive.LEAP if c["go"] == board_drive.LEAP_GO else 0)
                    for (k, v), c in zip(beats.items(), board["route"]["cards"]) if c["kind"] != "hook"}

        board, beats = held(("seville", 2))
        holds = own(board, beats)
        # their line holds a stop longer than no line; the peak the curation marks holds longest, and the sheet shows it
        self.assertLess(holds[("coimbra", 1)], holds[("porto", 1)])
        self.assertEqual(holds[("seville", 2)], max(holds.values()))
        self.assertEqual(board["route"]["cards"][storyboard.stop_index(board)]["place"], "seville")
        board, beats = held(("coimbra", 1))
        holds = own(board, beats)
        self.assertEqual(holds[("coimbra", 1)], max(holds.values()))
        self.assertEqual(board["route"]["cards"][storyboard.stop_index(board)]["place"], "coimbra")

    def test_every_stop_stands_its_words_as_long_as_they_take_to_read(self):
        # every word on the card counts, the label's too; the dot between a name and its month is no word
        reel = self.board
        sec = 60 / reel["bpm"]
        for c, b in zip(reel["route"]["cards"][1:], reel["beats"][1:]):
            words = sum(len([w for w in ln["text"].split() if w != "·"]) for ln in c["lines"])
            shown = (4 * b["bars"] - c["cut"] - c["go"]) * sec
            self.assertGreaterEqual(shown, board_drive.reading(words) - 1e-6, (c["place"], c["n"]))

    def test_her_line_is_on_its_places_card_and_nothing_counts(self):
        for c in self.board["route"]["cards"]:
            rows = " ".join(ln["text"] for ln in c["lines"] if ln["name"] == "said")
            line = self.said.get((c["place"], c["n"]))
            self.assertEqual(rows, line or "", (c["place"], c["n"]))  # their words as they wrote them
            self.assertNotIn("km", c)
        rt = self.board["route"]
        self.assertNotIn("hud", rt)
        self.assertEqual([ln["name"] for ln in rt["hook"]["kicker"]], ["title", "handle"])
        self.assertFalse(any(ch.isdigit() for c in rt["cards"] for ln in c["lines"] if ln["name"] != "said" for ch in ln["text"]))

    def test_the_film_ends_on_the_places_she_stood_in(self):
        # the closer's title is the year (they gave no title of their own) and its sign-off names every place, in the
        # order they first reached it
        cl = self.board["route"]["closer"]
        self.assertEqual(cl["title"], "2026")
        order = list(dict.fromkeys(c["name"] for c in self.board["route"]["cards"]))
        self.assertEqual(cl["signoff"], " · ".join(order))
        self.assertEqual(len(order), len(SOURCE["places"]["places"]))

class SnapCutsTheWinner(unittest.TestCase):
    """storyboard.py snap cuts only the board that won the vote (winner.json) and takes no board in its place."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        shutil.copyfile(KIT / "tests" / "data" / "trip.json", "source.json")
        patch = mock.patch.object(storyboard._env, "enter_run")
        patch.start()
        self.addCleanup(patch.stop)

    def snap(self, *args):
        with mock.patch.object(sys, "argv", ["storyboard.py", "snap", *args]):
            return storyboard.main()

    def test_with_no_look_chosen_snap_refuses_and_cuts_nothing(self):
        for winner in (None, {"board": "drive"}):
            if winner:
                Path("winner.json").write_text(json.dumps(winner))
            with self.assertRaises(SystemExit) as e:
                self.snap()
            self.assertIn("no look is chosen", str(e.exception.code))
            self.assertIn("vote.py pick", str(e.exception.code))
            self.assertFalse(Path("film.json").exists())

    def test_snap_takes_no_board_in_place_of_the_vote(self):
        Path("winner.json").write_text(json.dumps({"board": "drive"}))
        with self.assertRaises(SystemExit) as e:
            self.snap("--board", "drive")
        self.assertEqual(e.exception.code, 2)
        self.assertFalse(Path("film.json").exists())

    def test_with_the_winner_snap_cuts_it(self):
        Path("winner.json").write_text(json.dumps({"board": "scrapbook", "name": "scrapbook", "by": "person"}))
        self.snap()
        film = json.loads(Path("film.json").read_text())
        self.assertEqual(film["style"], "scrapbook")
        self.assertEqual(film["boards"]["reel"], str(storyboard.BOARDS / "scrapbook" / "board-reel.json"))
        self.assertTrue(Path(film["boards"]["reel"]).exists())



if __name__ == "__main__":
    unittest.main()


class WhatTheFilmSays(unittest.TestCase):
    """"home" stands on a place only when they named their home themselves; a photograph is never enlarged past ENLARGE of its own
    pixels; a photograph's own line tilts its truck within TILT of level; and the grade keeps a black-and-white source gray and
    brings the color photographs toward one saturation."""

    def labels(self, places):
        src = dict(SOURCE, places=places)
        return [" ".join(ln["text"] for ln in c["lines"] if ln["name"] == "label")
                for c in storyboard.plan(src, "reel", None)["board"]["route"]["cards"]]

    def test_home_is_said_only_when_she_named_it(self):
        self.assertFalse(any("home" in t.lower() for t in self.labels(dict(SOURCE["places"], home_said=False))))
        said = self.labels(dict(SOURCE["places"], home_said=True))
        self.assertIn("home", said[0].lower())
        # a first place that is not their home is never called home, said or not
        other = dict(SOURCE["places"], home="porto", home_said=True)
        self.assertNotIn("home", self.labels(other)[0].lower())

    def test_a_photograph_is_enlarged_at_most_ENLARGE_and_covers_its_box_when_it_has_the_pixels(self):
        box = [100.0, 400.0, 980.0, 1600.0]
        # too few pixels to cover the box at ENLARGE: it stands at ENLARGE in the box's middle
        ph, scale, seen = board_drive.placed({"w": 400, "h": 300, "focus": [0.5, 0.5]}, box)
        self.assertEqual(scale, board_drive.ENLARGE)
        self.assertEqual(ph, [220.0, 760.0, 640.0, 480.0])
        self.assertEqual(seen, [220.0, 760.0, 860.0, 1240.0])
        # with the pixels it covers the whole box, under its own size
        ph, scale, seen = board_drive.placed({"w": 2880, "h": 1920, "focus": [0.5, 0.5]}, box)
        self.assertLess(scale, 1.0)
        self.assertEqual(seen, box)
        self.assertTrue(ph[0] <= box[0] and ph[0] + ph[2] >= box[2] and ph[1] <= box[1] and ph[1] + ph[3] >= box[3], ph)
        b = copy.deepcopy(storyboard.plan(SOURCE, "reel", None)["board"])
        b["route"]["cards"][1]["scale"] = board_drive.ENLARGE + 0.1
        self.assertTrue(any("enlarged" in x for x in bounds.check(b)))

    def test_a_photographs_own_line_tilts_its_truck_within_TILT_of_level(self):
        most = math.tan(math.radians(board_drive.TILT))
        self.assertEqual(board_drive.slope_of({"w": 1080, "h": 1920, "line": None}), 0.0)
        gentle = board_drive.slope_of({"w": 1080, "h": 1920, "line": [0.1, 0.2, 0.9, 0.25]})
        self.assertAlmostEqual(gentle, 0.05 * 1920 / (0.8 * 1080), places=3)
        self.assertLess(gentle, most)
        self.assertEqual(board_drive.slope_of({"w": 1080, "h": 1920, "line": [0.1, 0.8, 0.9, 0.2]}), round(-most, 4))

    def test_the_closers_dot_hops_about_two_seconds_at_any_tempo_and_the_map_stands_still_a_second_at_least(self):
        for bpm in (45, 60, 90, 96, 120, 180):
            route, beats = board_drive.closer_beats(bpm)
            sec = 60 / bpm
            self.assertTrue(abs(route * sec - board_drive.ROUTE) <= sec / 2 or route == 2, (bpm, route))
            self.assertGreaterEqual((beats - route) * sec, board_drive.STILL - 1e-6, bpm)
            self.assertLess((beats - route) * sec, board_drive.STILL + sec, bpm)

    def test_the_grade_keeps_black_and_white_gray_and_brings_color_toward_one_saturation(self):
        import grade
        from PIL import Image
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        gray = Image.linear_gradient("L").resize((300, 200)).convert("RGB")
        loud = Image.merge("RGB", [Image.linear_gradient("L").resize((300, 200)), Image.new("L", (300, 200), 30),
                                   Image.linear_gradient("L").rotate(90).resize((300, 200))])
        quiet = Image.blend(loud, loud.convert("L").convert("RGB"), 0.7)
        for name, im in (("gray", gray), ("loud", loud), ("quiet", quiet)):
            im.save(tmp / f"{name}.jpg", quality=95)
        toned = {n: grade.toned(tmp / f"{n}.jpg") for n in ("gray", "loud", "quiet")}
        self.assertTrue(toned["gray"][1])
        target = grade.target_of(list(toned.values()))
        done = {n: grade.finish(img, g, target) for n, (img, g) in toned.items()}
        self.assertTrue(all(len(set(p)) == 1 for p in grade.pixels(done["gray"].resize((32, 32)))))
        sats = [grade.saturation(done[n]) for n in ("loud", "quiet")]
        before = [grade.saturation(toned[n][0]) for n in ("loud", "quiet")]
        # the gap narrows, and the loud one keeps at least 0.7 of its saturation
        self.assertLess(abs(sats[0] - sats[1]), abs(before[0] - before[1]), (before, sats))
        self.assertGreaterEqual(sats[0], 0.7 * before[0] - 0.01, (before, sats))
        # the levels set white at WHITE, so nothing the source holds is pushed into clipping
        self.assertLessEqual(max(grade.pixels(toned["gray"][0].convert("L"))), grade.WHITE)


class ALongLineKeepsTheTypeFloor(unittest.TestCase):
    """A long line of theirs on a steep photograph breaks into rows in the card's line box, never under the type floor
    and never out of the type-safe area, in every format and each of the three looks."""

    def test_a_long_line_on_a_steep_photograph_solves_clean_in_every_format(self):
        src = copy.deepcopy(SOURCE)
        for ph in src["photos"]:
            if (ph["place"], ph["n"], ph["k"]) == ("oaxaca", 1, 1):
                ph.update(w=1944, h=2592, aspect=round(1944 / 2592, 4), line=[0.40, 0.47, 1.0, 0.55], focus=[0.6, 0.5])
        for m in src["moments"]:
            if (m["place"], m["n"]) == ("oaxaca", 1):
                m["line"] = "cooked mole from scratch in oaxaca with @kofi.cooks"
        for style in look.TRIO:
            planned = {fmt: storyboard.plan(src, fmt, None, style) for fmt in storyboard.FORMATS}
            self.assertEqual(storyboard.findings(planned, src["photos"]), [], style)
            card = next(c for c in planned["reel"]["board"]["route"]["cards"] if c["place"] == "oaxaca")
            self.assertEqual(" ".join(ln["text"] for ln in card["lines"] if ln["name"] == "said"),
                             look.cased("cooked mole from scratch in oaxaca with @kofi.cooks", look.card(style)["faces"][look.card(style)["photo"]["line"]["face"]]))
