"""The film a studio would deliver, as the kit makes it from a year's source (tests/data/trip.json):
  - every clip request is its own shot for one of three uses, the hook's world, the texture between chapters and a
    still brought to life, written with its subject, its move, its lens, its seconds and a seamless loop
  - the moves between near places take turns between a rise over the map and a lift onto the leg, and no rise stands
    beside a leap or the closer
  - lines too long for the longest film, or for the peak to hold longest in it, are set to their first clause, and
    every place stays; a line set to its first clause and then left out is named once, with their whole line
  - the sheet and the stills rest on their words whole, before they sink as the camera leaves
  - one grade from the look's card lies over every format, and the look is the lever on the closer's layout
  - every format's closer names its places on their own pins, within one room of the pin (the disc, or the print on
    it) and nearer it than any other pin, and a name the cluster leaves no room beside stands in a column with a leader
    to its own pin; two places a pixel apart are one dot, and both names stand beside it
  - the gate reports: a round under the bar with no lever left is delivered under the bar with its scores, read from
    frames of the film
  - out/ holds the three films, the image to post, the story card, the caption, the three looks and the review page,
    which is the film's cover, offers the other two looks, and states no score

    python3 -I -m unittest discover -s S/tests -p test_craft.py
"""
import copy
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import board_drive  # noqa: E402
import bounds  # noqa: E402
import clips  # noqa: E402
import look  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
USES = {"the hook's world", "texture between chapters", "a still brought to life"}


def reel(src=SOURCE):
    return storyboard.plan(src, "reel", None)["board"]


class InADir(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)


class Shots(unittest.TestCase):
    def test_every_clip_request_is_its_own_shot_for_one_of_the_three_uses(self):
        board = reel()
        shots = board["clips"]
        self.assertEqual(len(shots), len(board["route"]["cards"]))
        self.assertEqual({c["role"] for c in shots}, USES)
        self.assertEqual(shots[0]["role"], "the hook's world")
        leaps = [k for k, c in enumerate(board["route"]["cards"]) if c["travel"] == "leap"]
        self.assertTrue(leaps and all(shots[k]["role"] == "texture between chapters" for k in leaps))
        prompts = [clips.prompt_of(c, c["seconds"]) for c in shots]
        self.assertEqual(len(set(prompts)), len(prompts))
        for a, b in zip(shots, shots[1:]):
            self.assertNotEqual(a["move"], b["move"])
        for c, p in zip(shots, prompts):
            self.assertIn(c["move"][1:], p)
            self.assertIn(f"{c['seconds']:g} second", p)
            self.assertIn("seamless loop", p)
            self.assertNotIn("moves gently", p)

    def test_a_shot_takes_its_subject_and_lens_from_what_the_cast_says_of_the_photograph(self):
        src = copy.deepcopy(SOURCE)
        first = reel(src)["route"]["cards"][0]["file"]
        ph = next(p for p in src["photos"] if p["file"] == first)
        ph.update(about="a yellow tram climbing a wet street at night", camera="a 35 mm lens at eye height")
        shot = reel(src)["clips"][0]
        self.assertTrue(shot["read"])
        p = clips.prompt_of(shot, shot["seconds"])
        self.assertTrue(p.startswith("A yellow tram climbing a wet street at night."))
        self.assertIn("a 35 mm lens at eye height", p)


class Moves(unittest.TestCase):
    def test_near_moves_take_turns_between_a_rise_and_a_lift_and_no_rise_stands_beside_a_leap_or_the_closer(self):
        moves = [c["travel"] for c in reel()["route"]["cards"]]
        self.assertLessEqual(set(moves), {"rise", "lift", "leap", "closer"}, moves)
        self.assertIn("rise", moves)
        self.assertIn("lift", moves)
        for a, b in zip(moves, moves[1:]):
            if {a, b} <= {"rise", "lift"}:
                self.assertNotEqual(a, b, moves)
            if "rise" in (a, b):
                self.assertFalse({a, b} & {"leap", "closer"}, moves)


class Fit(unittest.TestCase):
    def test_lines_too_long_for_the_longest_film_are_set_to_their_first_clause_and_every_place_stays(self):
        src = copy.deepcopy(SOURCE)
        for m in src["moments"]:
            m["peak"] = (m["place"], m["n"]) == ("oaxaca", 1)
            if m.get("line"):
                m["line"] += ", and then we walked the whole old town down to the water and back up the hill at dusk"
        with self.assertRaises(board_drive.TooLong):
            board_drive.build(src, "reel")
        fit = board_drive.fit_lines(src)
        self.assertTrue(fit["trimmed"])
        # a line is set to its first clause; one the film still cannot hold is then left out, the place keeping its name
        for t in fit["trimmed"]:
            self.assertIn(t["now"], (board_drive.first_clause(t["line"]), None))
        self.assertGreater(sum(1 for t in fit["trimmed"] if t["now"]), len(fit["trimmed"]) // 2)
        board = reel(fit)
        self.assertFalse(board_drive.peak_short(board))
        self.assertLessEqual(sum(b["bars"] * 4 for b in board["beats"]) * 60 / board["bpm"], board_drive.LENGTH[1] + 1e-6)
        said = {c["place"] for c in board["route"]["cards"]}
        self.assertEqual(said, {m["place"] for m in src["moments"]})

    def test_a_line_set_to_its_first_clause_and_then_left_out_is_named_once_with_her_whole_line(self):
        src = copy.deepcopy(SOURCE)
        for m in src["moments"]:
            m["peak"] = (m["place"], m["n"]) == ("oaxaca", 1)
            if m.get("line"):
                m["line"] = "walked the whole old town down to the water and back up the hill at dusk, then again at dawn with nobody about"
        whole = {(m["place"], m["n"]): m["line"] for m in src["moments"]}
        fit = board_drive.fit_lines(src)
        visits = [(t["place"], t["n"]) for t in fit["trimmed"]]
        self.assertEqual(len(visits), len(set(visits)))
        self.assertTrue(any(not t["now"] for t in fit["trimmed"]))
        for t in fit["trimmed"]:
            self.assertEqual(t["line"], whole[(t["place"], t["n"])])
            said = next(m["line"] for m in fit["moments"] if (m["place"], m["n"]) == (t["place"], t["n"]))
            self.assertEqual(t["now"], said)


class Rests(unittest.TestCase):
    def test_the_sheet_and_the_stills_rest_on_her_words_whole_before_they_sink(self):
        # words.tsx sinks their words LEAVE beats before the camera leaves a place; the hook and the stop rest before that
        words = (KIT / "motion" / "studio" / "route" / "words.tsx").read_text()
        leave = float(re.search(r"const LEAVE = ([\d.]+);", words).group(1))
        p = storyboard.plan(SOURCE, "reel", None)
        b = p["board"]
        beat_at, _ = board_drive.starts(b)
        ids = [x["id"] for x in b["beats"]]
        pulse = board_drive.FPS * 60 / b["bpm"]
        for k, i in (("hook", 0), ("stop", storyboard.stop_index(b))):
            sink = beat_at[ids[i + 1]] - b["route"]["cards"][i]["go"] - leave
            self.assertLessEqual(p["rests"][k], sink * pulse, k)
        self.assertEqual(storyboard.WORDS_SINK, leave)



class FirstFrame(unittest.TestCase):
    def test_the_shutter_never_samples_before_the_first_frame(self):
        # camera.ts blurs each frame by the move between it and half a frame before; before the film's start the
        # camera stands on the closer, so a sample there would smear the hook's first frame
        cam = (KIT / "motion" / "studio" / "route" / "camera.ts").read_text()
        shot = cam[cam.index("export const shotAt"):]
        was = re.search(r"const was = framingAt\(plan, (.+?)\);", shot).group(1)
        self.assertRegex(was, r"^Math\.max\(0, t - half\)$")

class DotTrail(unittest.TestCase):
    def test_the_trail_ends_at_the_first_mark_that_stands_apart_from_the_one_before_it(self):
        # the trail samples the dot every 0.025 beats; on a fast move those samples land far apart and read as separate
        # red dots on the picture, so a mark is drawn only while every mark before it touches its neighbor
        dot = (KIT / "motion" / "studio" / "route" / "dot.tsx").read_text()
        trail = dot[dot.index("parts.trail.forEach"):]
        trail = trail[:trail.index("});")]
        self.assertRegex(trail, r"broken = broken \|\| k\.p\.distanceTo\(prev\) > r \* \(0\.85 \* fall \+ 0\.15\);")
        self.assertRegex(trail, r"m\.visible = tt < still && !broken &&")

class Grade(unittest.TestCase):
    def test_one_grade_from_the_looks_card_lies_over_every_format(self):
        grades = {}
        for style in look.TRIO:
            got = [storyboard.plan(SOURCE, fmt, None, style)["board"]["system"]["finish"]["grade"] for fmt in storyboard.FORMATS]
            self.assertTrue(all(g == got[0] for g in got), style)
            self.assertEqual(got[0], look.card(style)["finish"]["grade"], style)
            grades[style] = got[0]
        self.assertEqual(len({json.dumps(g, sort_keys=True) for g in grades.values()}), len(look.TRIO))

    def test_the_look_is_the_lever_on_the_closers_layout(self):
        # each look's closer leaves its own window open on the map, and every pin stands inside it
        windows = {}
        for style in look.TRIO:
            closer = storyboard.plan(SOURCE, "reel", None, style)["board"]["route"]["closer"]
            windows[style] = tuple(closer["window"])
            self.assertEqual(list(windows[style]), board_drive.closer_window(style, 1080, 1920))
        self.assertEqual(len(set(windows.values())), len(look.TRIO), windows)

    def test_a_vertical_closer_fills_the_frame_down_to_the_band(self):
        # the still last frame of a reel leaves no empty lower third: its window reaches past 68% of the height, while a
        # 16:9 frame's window keeps its share
        for style in look.TRIO:
            x, y, w, h = board_drive.closer_window(style, 1080, 1920)
            self.assertGreater((y + h) / 1920, 0.68, style)
            x, y, w, h = board_drive.closer_window(style, 1920, 1080)
            self.assertLess((y + h) / 1080, 0.66, style)


class TheGateReports(InADir):
    def round(self, scores, lever):
        Path("out").mkdir()
        Path("out/film.mp4").write_text("the cut")
        Path("critic").mkdir()
        data = vote.blank(vote.CUT_PANEL, ["film"])
        frames = [f"f{i + 1:02d}.jpg" for i in range(vote.CUT_FRAMES)]
        for c in vote.CUT_PANEL:
            e = data["critics"][c]["boards"]["film"]
            e.update(scores=dict(scores), unread={}, paragraph=" ".join(["the route holds and the type settles on the beat"] * 4))
        data.update(round=1, film=qa.sha(Path("out/film.mp4")), frames=frames, seen=frames, lever=lever, fixed=None)
        Path("critic/cut-1.json").write_text(json.dumps(data))

    def test_a_round_under_the_bar_with_no_lever_left_is_delivered_under_the_bar_with_every_score(self):
        self.round(dict(dict.fromkeys(vote.CRITERIA, 5), R6=3), {"name": "none", "change": ""})
        with mock.patch("sys.stdout") as out:
            self.assertEqual(vote.cmd_verdict(None), 0)
        said = "".join(str(c.args[0]) for c in out.write.call_args_list)
        self.assertIn("UNDER THE BAR", said)
        self.assertNotIn("SHIP", said)
        self.assertEqual(json.loads(Path("verdict.json").read_text())["verdict"], "under")
        for k in vote.CRITERIA:
            self.assertIn(k, said)

    def test_a_round_reads_the_first_frame_each_beat_leaving_and_each_shapes_closer_from_the_film_it_scores(self):
        Path("out").mkdir()
        for name in ("film.mp4", "out/film.mp4", "out/film-square.mp4"):
            subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=2", "-pix_fmt", "yuv420p",
                            name], check=True)
        Path("film.json").write_text(json.dumps({"frames": 60, "seconds": 2.0, "cuts": [1.0, 1.6],
                                                 "rests": {"reel": {"closer": 58}, "square": {"closer": 58}}}))
        got = vote.cut_frames(Path("film.mp4"), Path("cut"))
        self.assertEqual(sorted(p.name for p in Path("cut").iterdir()), sorted(got))
        self.assertEqual(len([g for g in got if g[0] == "f" and g[1:3].isdigit()]), vote.CUT_FRAMES)
        for name in ("first-t00.000.jpg", "leave01-t00.500.jpg", "leave02-t01.100.jpg", "closer-reel-t01.933.jpg",
                     "closer-square-t01.933.jpg"):
            self.assertIn(name, got)


class TheDeliverable(InADir):
    def test_out_holds_the_three_films_the_post_the_story_card_the_caption_the_cover_and_the_three_looks(self):
        self.assertEqual(qa.DELIVERED, {"film.mp4", "film-16x9.mp4", "film-square.mp4", "post.png", "story.png", "caption.md",
                                        "review.html", "boards.png"})

    def test_the_review_page_is_the_films_cover_offers_the_other_looks_and_states_no_score(self):
        import deliver
        from PIL import Image
        Path("out").mkdir()
        Image.new("RGB", (30, 90), "#ffffff").save("out/boards.png")
        pl = {"places": [{"id": "lisbon", "name": "Lisbon"}, {"id": "porto", "name": "Porto"}]}
        made = deliver.made_html(pl, [{"file": "a.jpg"}, {"file": "b.jpg"}], {}, {}, look.TRIO[0], {})
        page = deliver.PAGE.format(title="t", banner="", caption="c", bg="#000", ink="#fff", accent="#f00", cards="", films="",
                                   looks=deliver.looks_html(look.TRIO[0]), made=made)
        self.assertIn('poster="story.png"', page.replace("'", '"'))
        words = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())
        self.assertIn("Prefer another look? Say 'make the second one' or 'make the third one'", words)
        self.assertIn(look.sentence(look.TRIO[1]), words)
        self.assertNotIn(look.sentence(look.TRIO[0]) + "</figcaption>", page)
        # no score, no rule of the bar, and never the word critic: the page is for the person posting the film
        self.assertNotIn("critic", page.lower())
        self.assertNotIn("score", page.lower())
        for k in vote.CRITERIA:
            self.assertIsNone(re.search(rf"\b{k}\b", words), k)
        self.assertNotIn("The vote", page)
        self.assertNotIn("storyboards/", page)



if __name__ == "__main__":
    unittest.main()
