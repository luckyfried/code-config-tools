"""The clip requests the storyboard writes, one per stop: each camera move is the one its own photograph's line and focus
call for, and no two stops in a row ask for the same one; a texture between chapters asks for the place's material,
never the photograph's subject; every request names its light; each stand-in states, from its own card, the layered
move the film makes in the clip's place; and grade.py carries the cast's `texture` to the photograph.

    python3 -I -m unittest discover -s S/tests -p test_requests.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive  # noqa: E402

W = 1080
BOX = [0.0, 600.0, 1080.0, 720.0]


def card(k, tilt=0.0, focus=(0.5, 0.5), move="rise", west=False, place="faro", said=None):
    """Stop `k`'s card: its photograph at BOX, its line falling `tilt` px per px to the east (its slope), its focus at
    `focus` (fractions of the photograph), and the stop's travel out."""
    return {"id": "hook" if k == 0 else f"stop-{k}", "kind": "new", "name": place.capitalize(), "said": said,
            "file": f"photos/{place}-{k}.jpg", "travel": move, "west": west, "photo": BOX, "slope": tilt,
            "focus": [BOX[0] + focus[0] * BOX[2], BOX[1] + focus[1] * BOX[3]]}


def requests(cards, photos=None):
    """The clip requests for `cards`, each on a beat whose own move has no camera words, so the photograph calls it."""
    return board_drive.clips({"route": {"W": W, "cards": cards}, "beats": [{"bars": 1} for _ in cards]}, photos or {})


def look(top):
    return {"light": [[top] * 6] + [[0.5] * 6] * 5, "busy": [[0.2] * 6] * 6}


class Requests(unittest.TestCase):
    def test_each_move_comes_from_its_photographs_line_and_focus_and_differs_from_the_stop_befores(self):
        cards = [card(0, tilt=0.12, focus=(0.5, 0.45)), card(1, focus=(0.5, 0.1)), card(2, tilt=-0.2, focus=(0.5, 0.45)),
                 card(3, focus=(0.52, 0.48)), card(4, focus=(0.05, 0.5)), card(5, focus=(0.05, 0.5))]
        moves = [r["move"] for r in requests(cards)]
        # a line falling 7 degrees to the east trucks right, one rising to the east trucks left, a high focus cranes up
        # toward it, a middle one pushes in, one at an edge pulls back, and the same edge again takes the next best
        for m, words in zip(moves, ("truck to the right", "crane up", "truck to the left", "push in", "pull back", "push in")):
            self.assertIn(words, m, moves)
        kind = lambda m: next(k for k in ("truck", "crane", "push", "pull") if k in m)
        for a, b in zip(moves, moves[1:]):
            self.assertNotEqual(kind(a), kind(b), moves)

    def test_a_texture_between_chapters_asks_for_the_places_material_never_the_photographs_subject(self):
        cards = [card(0), card(1, move="leap", place="faro"), card(2, move="lift", place="oaxaca"), card(3, place="madrid")]
        photos = {"photos/faro-1.jpg": {"about": "a whitewashed lane through a stone arch in bright sun", "camera": "a 28 mm lens",
                                        "texture": "limewash flaking off a sunlit wall"},
                  "photos/oaxaca-2.jpg": {"about": "a market stall heaped with mangoes, the stallholder beside the fruit",
                                          "camera": "a 35 mm lens at eye height", "look": look(0.8)}}
        r = requests(cards, photos)
        self.assertEqual([x["role"] for x in r[1:3]], ["texture between chapters"] * 2)
        self.assertEqual(r[1]["subject"], "limewash flaking off a sunlit wall")
        self.assertTrue(r[1]["read"])
        # with no texture written, the request asks for the place's surface in the photograph's light, with nobody in it
        self.assertNotIn("market", r[2]["subject"])
        for words in ("Oaxaca", "water", "stone", "ground", "in bright light", "no person and no landmark"):
            self.assertIn(words, r[2]["subject"])
        self.assertFalse(r[2]["read"])

    def test_every_request_with_no_about_names_its_photographs_light(self):
        cards = [card(0, said="rode the 28 in the rain", place="lisbon"), card(1, place="porto"), card(2, place="evora"),
                 card(3, place="madrid")]
        photos = {"photos/lisbon-0.jpg": {"look": look(0.2)}, "photos/porto-1.jpg": {"look": look(0.8)},
                  "photos/evora-2.jpg": {"look": look(0.5), "gray": True},
                  "photos/madrid-3.jpg": {"about": "terracotta rooftops in warm afternoon sun", "look": look(0.2)}}
        subjects = [x["subject"] for x in requests(cards, photos)]
        self.assertEqual(subjects[0], "rode the 28 in the rain, in Lisbon, in low light")
        self.assertIn("in bright light", subjects[1])
        self.assertIn("in soft black and white light", subjects[2])
        self.assertEqual(subjects[3], "terracotta rooftops in warm afternoon sun")

    def test_each_stand_in_states_the_layered_move_the_film_makes_in_its_place(self):
        cards = [card(0, tilt=0.2, move="rise"), card(1, focus=(0.2, 0.5), move="lift", west=True),
                 card(2, tilt=-0.05, move="leap"), card(3, tilt=0.0175, focus=(0.8, 0.5), move="closer")]
        stand = [x["stand_in"] for x in requests(cards)]
        self.assertEqual(len(set(stand)), len(stand), stand)
        for s, words in zip(stand, (("falls 11 degrees to the east", "middle of the frame", "drifts east",
                                     "climbs over the map to show every near place"),
                                    ("level line", "left of the frame", "drifts west",
                                     "comes down onto the leg as the photograph folds off the map, riding the dot"),
                                    ("rises 3 degrees to the east", "crosses the water"),
                                    ("falls 1 degree to the east", "right of the frame", "rises to the whole map"))):
            for w in words:
                self.assertIn(w, s)
            self.assertIn("ground below the photograph's", s)
            self.assertNotIn(". ", s)


    def test_no_two_prompts_share_a_sentence_but_their_length_and_loop(self):
        import clips
        cards = [card(0, place="lisbon"), card(1, tilt=0.12, place="porto"), card(2, focus=(0.5, 0.1), place="coimbra"),
                 card(3, tilt=-0.2, place="evora")]
        photos = {f"photos/{p}-{k}.jpg": {"about": a, "camera": c} for k, (p, a, c) in enumerate((
            ("lisbon", "the 28 tram on a wet street at night", "a 35 mm lens at standing height"),
            ("porto", "a riverside quay under cafe umbrellas in warm sun", "a 28 mm lens at eye height"),
            ("coimbra", "a domed fountain pavilion in soft daylight", "a 24 mm lens from a first-floor window"),
            ("evora", "the main square at blue hour", "a 24 mm lens among the tables")))}
        prompts = [clips.prompt_of(r, 2.4) for r in requests(cards, photos)]
        seen = {}
        for p in prompts:
            for sentence in p.split(". ")[:-1]:
                self.assertNotIn(sentence, seen, prompts)
                seen[sentence] = p


class Grade(unittest.TestCase):
    def test_the_casts_texture_reaches_the_photograph(self):
        import grade
        from PIL import Image
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        Image.new("RGB", (120, 90), (180, 150, 110)).save("faro.jpg")
        shot = {"file": str(Path("faro.jpg").resolve()), "about": "a stone arch in bright sun", "camera": "a 28 mm lens",
                "texture": "limewash flaking off a sunlit wall"}
        Path("cast.json").write_text(json.dumps({"visits": [{"place": "faro", "n": 1, "shots": [shot]}]}))
        Path("places.json").write_text(json.dumps({"home": "faro"}))
        rows = grade.grade_cast(own={})
        self.assertEqual(rows[0].get("texture"), "limewash flaking off a sunlit wall")


if __name__ == "__main__":
    unittest.main()
