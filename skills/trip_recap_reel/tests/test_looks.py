"""The three looks: draft lays the trip out as three boards, one per look (cinematic letterbox, analog home movie,
scrapbook), each drawn only from its own card: its faces, its moves and cuts, its palette rule's colors, its photo
layout and its closer; a look that closes on their closing line says a short one once, as the last thing on screen,
and plays a long one whole on its stop and holds its last phrase. A beat's move is picked by what the stop holds, never
by its place in the order. The check
refuses a face not in the card, a move or a cut outside the card's allowlist, a color the palette rule did not make,
one move on two beats running, every shot within SPREAD of one length, the words at one place on more than
MOST_IN_ONE of the beats that carry words, and two looks that share more than MOST_SHARED of the six axes.

    python3 -I -m unittest discover -s S/tests -p test_looks.py
"""
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import board_trip  # noqa: E402
import storyboard  # noqa: E402
import style  # noqa: E402

SWATCHES = ["#7b7561", "#3c2b1a", "#c7cbc7", "#6f4a1e", "#d5e9f2"]
CLOSERS = {"cinematic-letterbox": "title-card", "analog-home-movie": "closing-flicker", "scrapbook": "book-cover"}


def stop(i, name, caption, aspect=0.6667, clip=False, city="lisbon"):
    return {"name": name, "place": f"{name.title()}, Lisbon", "city": city, "photo": f"matched/{i}.jpg", "aspect": aspect,
            "long": 1350, "date": f"mon {14 + i} sep", "time": "09:00", "caption": caption, "day": i + 1,
            "lat": 38.71 + 0.01 * i, "lon": -9.13, "clip": clip, "sees": "",
            "points": {"near": [0.3 + 0.05 * i, 0.88], "far": [0.7 - 0.08 * i, 0.4 + 0.03 * i]}}


def source():
    return {"handle": "mara.makes", "trip": {"name": "lisbon", "label": "lisbon week", "range": "14 to 18 sep", "year": 2026},
            "stops": [stop(0, "alfama", "alfama at seven, the lane to ourselves @ines.draws"),
                      stop(1, "graça", "tram up to graça, standing room only", aspect=1.7778, clip=True),
                      stop(2, "belém", "walked the river all the way out to belém", aspect=0.75),
                      stop(3, "sintra", "train to sintra, lost in the yellow palace @ines.draws", city="sintra"),
                      stop(4, "bairro alto", "last night, the fountain lit up, we stayed @ines.draws")]}


class Looks(unittest.TestCase):
    def setUp(self):
        home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(__import__("shutil").rmtree, home, True)
        patch = mock.patch.object(_env, "read_json", return_value=None)
        patch.start()
        self.addCleanup(patch.stop)
        self.boards = [storyboard.make_board(str(n), look, source(), {"swatches": SWATCHES})
                       for n, look in enumerate(style.TRIO, 1)]

    def findings(self, b):
        return storyboard.look_findings(b, b["beats"])

    def test_the_three_boards_are_the_three_looks_each_clean_and_far_enough_apart(self):
        self.assertEqual([b["style"] for b in self.boards], list(style.TRIO))
        for b in self.boards:
            self.assertEqual(self.findings(b), [], b["style"])
        self.assertEqual(storyboard.across(self.boards), [])

    def test_each_board_carries_its_cards_photo_layout_and_closes_on_its_own_closer(self):
        for b in self.boards:
            c = style.card(b["style"])
            self.assertEqual(b["system"]["photo"], c["photo"], b["style"])
            self.assertEqual(b["system"]["closer"], CLOSERS[b["style"]])
            closer = [x for x in b["beats"] if x["form"] == "closer"]
            self.assertEqual(len(closer), 1)
            said = (closer[0].get("shows") or "").lower()
            self.assertNotIn("dot", said)
            self.assertNotIn("wall", said)

    def test_a_long_closing_line_plays_whole_and_the_closer_holds_its_last_phrase(self):
        analog = self.boards[style.TRIO.index("analog-home-movie")]
        last = analog["beats"][-2]
        self.assertEqual(analog["route"]["signoff"], "we stayed")
        self.assertEqual(last["words"], "last night, the fountain lit up, we stayed", "the long line plays whole on its stop")

    def test_a_short_closing_line_is_said_once_as_the_last_thing_on_screen(self):
        src = source()
        src["stops"][-1]["caption"] = "we stayed up"
        b = board_trip.board(src, style.card("analog-home-movie"))
        last = b["beats"][-2]
        self.assertEqual(b["route"]["signoff"], "we stayed up")
        self.assertEqual((last["words"], last["anchor"], b["route"]["stops"][-1]["caption"]), ("", None, ""),
                         "the stop the line came from plays wordless")
        cinematic = self.boards[style.TRIO.index("cinematic-letterbox")]
        self.assertEqual(cinematic["beats"][-2]["words"], "last night, the fountain lit up, we stayed", "a look closing on its name keeps every line")

    def test_a_recorded_clip_takes_the_move_and_cut_its_photograph_would_have_and_changes_no_other_beat(self):
        """A clip plays on a photo beat: the board with the stop as a recording and the board with it as a photograph
        are the same beat for beat, lengths, moves, cuts and words, except that the clip's beat is the form `clip` and
        holds and shows a clip where the other holds and shows a photograph."""
        src = source()
        still = copy.deepcopy(src)
        still["stops"][1]["clip"] = False
        for look in style.TRIO:
            c = style.card(look)
            a, z = board_trip.board(src, c), board_trip.board(still, c)
            self.assertEqual((a["beats"][1]["form"], z["beats"][1]["form"]), ("clip", "photo"), look)
            self.assertEqual(set(a["beats"][1]["tags"]) ^ set(z["beats"][1]["tags"]), {"clip", "photo"}, look)
            what = lambda x: {k: v for k, v in x.items() if k not in ("form", "tags", "shows")}  # noqa: E731
            self.assertEqual([what(x) for x in a["beats"]], [what(y) for y in z["beats"]], look)
        self.assertEqual(len({b["beats"][2]["move"] for b in self.boards}), 3, "each look moves the same stop its own way")

    def test_a_move_that_flies_the_photograph_in_holds_its_beat_until_the_words_have_read_after_it_lands(self):
        """The trailer moves go where the look wants them: the calm looks take one at most, once, and every beat that
        flies its photograph in runs its flight, the settle and the time its line takes to read."""
        flown = {}
        for b in self.boards:
            for x in b["beats"]:
                if x.get("move") in board_trip.ARRIVES:
                    flown.setdefault(b["style"], []).append(x["move"])
                    self.assertEqual(x["fly"], board_trip.ARRIVES[x["move"]])
                    need = (x["fly"] + board_trip.SETTLE) * b["bpm"] / 60 + board_trip.read_beats(x["words"], b["bpm"])
                    self.assertGreaterEqual(4 * x["bars"], need, (b["style"], x["id"]))
                else:
                    self.assertEqual(x.get("fly", 0.0), 0.0 if x["form"] != "closer" else x.get("fly", 0.0))
        self.assertTrue(flown.get("cinematic-letterbox"), flown)
        for calm in ("analog-home-movie", "scrapbook"):
            self.assertLessEqual(len(flown.get(calm, [])), 1, flown)
        taken = {m["id"] for look in style.styles() for m in style.card(look)["moves"]}
        self.assertFalse(taken & style.LEFT_OUT, "no trip look takes a count")

    def test_every_stop_holds_its_line_between_the_halves_of_the_cuts_either_side_of_it(self):
        """A cut plays half its length over each beat it joins, so a stop's line reads only between those halves: every
        stop with words holds the two halves, a flown-in photograph's landing, the label's lead, the line's reading time
        and its fade."""
        for b in self.boards:
            cuts = [x["transition"] for x in b["beats"][1:]]
            for x, out in zip(b["beats"][1:-1], cuts[1:]):
                if not x["words"]:
                    continue
                landed = (x["fly"] + board_trip.SETTLE) * b["bpm"] / 60 if x["fly"] else 0.0
                need = (max(0.25, board_trip.cut_beats(x["transition"]) / 2, landed) + 0.5
                        + board_trip.read_beats(x["words"], b["bpm"]) + max(0.5, board_trip.cut_beats(out) / 2) + 0.6)
                self.assertGreaterEqual(4 * x["bars"], need, (b["style"], x["id"]))
        self.assertEqual(board_trip.cut_beats("long-dissolve"), 3.0)
        self.assertEqual(board_trip.cut_beats("hard-cut"), 0.0)
        self.assertEqual(board_trip.cut_beats(None), 0.0)

    def test_a_card_that_pastes_its_prints_never_takes_a_move_that_lays_a_print_of_its_own(self):
        b = self.boards[2]
        self.assertFalse(board_trip.full_frame(style.card(b["style"])))
        self.assertFalse({x["move"] for x in b["beats"][1:] if x["form"] != "closer"} & board_trip.WINDOWED)

    def test_a_face_not_in_the_card_is_refused(self):
        b = copy.deepcopy(self.boards[0])
        b["system"]["display"]["family"] = "Archivo"
        self.assertTrue(any("the display face Archivo" in f for f in self.findings(b)))

    def test_a_move_or_a_cut_outside_the_cards_allowlist_is_refused(self):
        b = copy.deepcopy(self.boards[1])
        b["beats"][2]["move"], b["beats"][3]["transition"] = "polaroid-drop", "page-turn"
        said = self.findings(b)
        self.assertTrue(any("'polaroid-drop', which is not a move of analog-home-movie" in f for f in said), said)
        self.assertTrue(any("'page-turn', which is not a transition of analog-home-movie" in f for f in said), said)

    def test_a_color_the_palette_rule_did_not_make_is_refused(self):
        b = copy.deepcopy(self.boards[2])
        b["system"]["colors"]["accent"] = "#ff00aa"
        self.assertTrue(any("#ff00aa, a color the photos-plus-accent palette rule" in f for f in self.findings(b)))

    def test_one_move_on_two_beats_running_is_refused(self):
        b = copy.deepcopy(self.boards[0])
        b["beats"][3]["move"] = b["beats"][2]["move"]
        self.assertTrue(any("two beats running move differently" in f for f in self.findings(b)))

    def test_every_shot_within_a_tenth_of_one_length_is_refused(self):
        b = copy.deepcopy(self.boards[0])
        for x in b["beats"]:
            x["bars"] = 2
        b["beats"][1]["bars"] = 2.1
        self.assertTrue(any("the cut has no rhythm" in f for f in self.findings(b)))
        self.assertGreater(storyboard.SPREAD, 0.09)

    def test_words_at_one_place_on_most_beats_are_refused(self):
        b = copy.deepcopy(self.boards[0])
        for x in b["beats"]:
            if x["form"] != "closer":
                x["anchor"] = "bottom"
        self.assertTrue(any("the words sit at the bottom of the frame" in f for f in self.findings(b)))
        self.assertEqual(board_trip.MOST_IN_ONE, 0.7)

    def test_two_looks_that_share_more_than_two_axes_are_refused(self):
        self.assertEqual(style.MOST_SHARED, 2)
        self.assertEqual(style.too_close(list(style.TRIO)), [])
        self.assertTrue(style.too_close(["scrapbook", "scrapbook"]))


if __name__ == "__main__":
    unittest.main()
