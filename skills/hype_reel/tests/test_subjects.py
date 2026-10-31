"""A reel about anything: the ideas offered when the request names no subject, each kind of subject read from its
folder, the pieces only a launch makes, the share caption, the moves only a beat with a number takes, the move the kit
adds to a card, and the sound each beat lays.

python3 -m unittest discover -s tests   (from the kit's folder)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
FIX = KIT / "evals" / "fixtures"
sys.path.insert(0, str(KIT / "scripts"))
import compose  # noqa: E402
import deliver  # noqa: E402
import drive  # noqa: E402
import film  # noqa: E402
import gather  # noqa: E402
import ideas  # noqa: E402
import qa  # noqa: E402
import sfx  # noqa: E402
import storyboard  # noqa: E402

TRIO = ("kinetic-type", "cinematic-letterbox", "swiss-grid")


def scratch(test):
    d = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
    test.addCleanup(d.cleanup)
    return Path(d.name)


def script(name, *args, cwd):
    return subprocess.run([sys.executable, "-I", str(KIT / "scripts" / name), *args], cwd=cwd, capture_output=True,
                          text=True, timeout=300)


class Ideas(unittest.TestCase):
    def setUp(self):
        self.ideas = ideas.draft([str(FIX / "ideas" / "pulled")], FIX / "ideas")

    def test_three_to_five_ideas_each_one_line_naming_a_subject_and_an_angle(self):
        self.assertTrue(3 <= len(self.ideas) <= 5, len(self.ideas))
        for x in self.ideas:
            self.assertTrue(x["subject"].strip(), x)
            self.assertTrue(x["angle"].strip(), x)
            self.assertIn(x["tone"], drive.TONES)
            self.assertNotIn("\n", x["line"])
            self.assertIn(x["subject"], x["line"])
            self.assertIn(x["angle"], x["line"])

    def test_the_ideas_come_from_a_friend_an_account_they_follow_and_their_project(self):
        subjects = [x["subject"] for x in self.ideas]
        self.assertIn("@ines.bakes.lisbon", subjects)
        self.assertIn("@harbourlight.film", subjects)
        self.assertIn("Tidepool Weather", subjects)
        self.assertEqual(len(set(map(str.lower, subjects))), len(subjects))

    def test_an_idea_from_a_private_account_is_marked_private(self):
        x = ideas.idea("@ana.mar", "quiet", "", "follows", True)
        self.assertTrue(x["private"])
        self.assertFalse(any(i["private"] for i in self.ideas if i["subject"] != "@ana.mar"))

    def test_with_nothing_pulled_there_are_still_three_ideas(self):
        empty = scratch(self)
        got = ideas.draft([], empty)
        self.assertEqual(len(got), 3)

    def test_the_list_ends_on_something_else(self):
        root = scratch(self)
        shutil.copytree(FIX / "ideas", root, dirs_exist_ok=True)
        r = script("ideas.py", "--root", str(root), cwd=root)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertTrue(lines[-1].endswith("Something else"), lines)
        self.assertTrue(4 <= len(lines) <= 6, lines)
        self.assertFalse(json.loads((root / "build" / "ideas.json").read_text())["skipped"])

    def test_a_named_subject_skips_the_step(self):
        root = scratch(self)
        shutil.copytree(FIX / "ideas", root, dirs_exist_ok=True)
        r = script("ideas.py", "--root", str(root), "--subject", "Sunday Soup Swap", cwd=root)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads((root / "build" / "ideas.json").read_text())
        self.assertTrue(got["skipped"])
        self.assertEqual(got["ideas"], [])
        self.assertNotIn("Something else", r.stdout)


class Subjects(unittest.TestCase):
    def test_each_fixture_reads_as_its_kind(self):
        want = {"friend": ("Ines Duarte", "friend", "@ines.bakes.lisbon"), "idea": ("Sunday Soup Swap", "idea", ""),
                "account": ("Harbourlight", "account", "@harbourlight.film")}
        for folder, (name, kind, handle) in want.items():
            s = gather.read_about(FIX / folder / "subject.md")
            self.assertEqual((s["name"], s["kind"], s["handle"]), (name, kind, handle), folder)
            self.assertTrue(s["facts"], folder)
        self.assertTrue(gather.read_about(FIX / "account" / "subject.md")["page"])

    def test_a_friend_is_not_a_launch_and_its_pictures_are_the_subjects(self):
        root = scratch(self)
        shutil.copytree(FIX / "friend", root / "friend")
        r = script("gather.py", "--root", str(root), "--about", "friend/subject.md", "--assets", "friend", cwd=root)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        lib = json.loads((root / "build" / "current" / "library.json").read_text())
        s = lib["subject"]
        self.assertEqual((s["name"], s["kind"], s["launch"]), ("Ines Duarte", "friend", False))
        self.assertEqual(len(s["stills"]), 4)


class Making(unittest.TestCase):
    def test_making_words_count_only_for_a_subject_they_made(self):
        import cast
        plates = {"words": "confession: i've been making plates in secret for a year"}
        self.assertTrue(cast.making(plates, "Tide Table", cast.theirs_of({"kind": "product"})))
        self.assertFalse(cast.making(plates, "Ines Duarte", cast.theirs_of({"kind": "friend"}), "@ines.bakes.lisbon"))
        tagged = {"words": "bread run with @ines.bakes.lisbon"}
        self.assertTrue(cast.making(tagged, "Ines Duarte", False, "@ines.bakes.lisbon"))


class Launch(unittest.TestCase):
    def test_only_a_launch_has_stories_and_a_countdown(self):
        self.assertEqual(deliver.sections_for({"launch": False}), ("film", "feed post", "share"))
        self.assertIn("countdown", deliver.sections_for({"launch": True}))
        self.assertEqual([c[0] for c in storyboard.CARDS], ["cover"])
        self.assertEqual({c[0] for c in storyboard.LAUNCH_CARDS}, {"story-1", "story-2", "story-3", "countdown"})

    def test_the_captions_of_anything_carry_no_date_and_a_share_caption(self):
        taste = {"plan": {"punchline": "Bread before sunrise.", "share": "Ines bakes before the city wakes up."},
                 "register": {"hashtags": []}}
        got = deliver.drafts(taste, {"name": "Ines Duarte", "launch": False, "facts": ["bakes at five"]})
        self.assertEqual(set(got), set(deliver.sections_for({"launch": False})))
        self.assertNotIn("#launchday", " ".join(got.values()))
        self.assertTrue(1 <= len(qa.share_sentences(got["share"])) <= 3, got["share"])


class Closer(unittest.TestCase):
    def test_a_one_line_closer_never_runs_the_name_into_the_punchline(self):
        ctx = {"name": "Ines Duarte", "date_label": "forty loaves before sunrise", "launch": False}
        self.assertEqual(storyboard.signoff_of(ctx, "letter-build"), "forty loaves before sunrise")
        self.assertEqual(storyboard.signoff_of({**ctx, "date_label": ""}, "letter-build"), "Ines Duarte")
        self.assertEqual(storyboard.signoff_of({**ctx, "date_label": "14 November", "name": "Tide Table", "launch": True},
                                               "letter-build"), "Tide Table 14 November")
        self.assertEqual(storyboard.signoff_of(ctx, "poster"), "forty loaves before sunrise")


class Share(unittest.TestCase):
    def test_the_share_caption_counts_sentences_with_hashtags_aside(self):
        self.assertEqual(len(qa.share_sentences("Ines bakes at five. Go early! #bread #lisbon")), 2)
        self.assertEqual(len(qa.share_sentences("one. two. three. four.")), 4)


class ReadTime(unittest.TestCase):
    def test_a_beat_holds_what_its_words_take_to_read(self):
        per = 0.5
        for n in (1, 4, 9):
            b = {"form": "photo", "words": " ".join(["word"] * n), "label": "", "move": None}
            self.assertGreaterEqual(drive.least(b, per) * per, drive.READ["start"] + drive.READ["word"] * n - 1e-9, n)

    def test_words_under_a_flight_read_after_it_lands(self):
        per = 0.75
        for move, fly in drive.ARRIVES.items():
            b = {"form": "photo", "words": "every saturday", "label": "", "move": move}
            self.assertGreaterEqual(drive.least(b, per) * per, fly + drive.READ["start"] + 2 * drive.READ["word"], move)


def beat(part, form, words="", label="", peak=False):
    return {"id": part, "part": part, "form": form, "words": words, "label": label, "own": True, "peak": peak, "len": 4}


class NewMoves(unittest.TestCase):
    def test_a_move_that_counts_takes_only_a_beat_whose_words_hold_a_number(self):
        card = compose.card("kinetic-type")
        self.assertIn("counter", {m["id"] for m in card["moves"]})
        beats = [beat("hook", "title", "the best bread in town", "Ines")] + \
            [beat(f"build-{i}", "title", words) for i, words in enumerate(
                ["up before the city", "every loaf by hand", "a queue round the block", "the crust sings"], 1)] + \
            [beat("made", "photo", "Ines Duarte", peak=True), beat("closer", "closer")]
        drive.choose(card, beats)
        self.assertEqual([b["id"] for b in beats if b["move"] == "counter"], [])

    def test_a_move_that_sets_two_words_takes_no_longer_line(self):
        card = compose.card("kinetic-type")
        beats = [beat("hook", "title", "meet my friend ines")] + \
            [beat(f"build-{i}", "photo", words) for i, words in enumerate(
                ["rides a bike everywhere", "swam the whole tagus crossing", "every saturday before sunrise",
                 "a cake box on the back"], 1)] + [beat("made", "photo", "Ines Duarte", peak=True), beat("closer", "closer")]
        beats[1]["words"], beats[1]["label"] = "every saturday", "Ines Duarte"
        drive.choose(card, beats)
        self.assertEqual([b["id"] for b in beats if b["move"] in drive.SHORT], [])

    def test_swiss_grid_carries_exploded_layers(self):
        ids = {m["id"] for m in compose.card("swiss-grid")["moves"]}
        self.assertIn("exploded-layers", ids)
        self.assertIn("tilted-wall", ids)
        self.assertIn("picture-tunnel", {m["id"] for m in compose.card("cinematic-letterbox")["moves"]})
        self.assertIn("slam-words", {m["id"] for m in compose.card("kinetic-type")["moves"]})

    def test_every_move_a_card_names_has_its_file(self):
        moves = KIT / "motion" / "system" / "moves"
        for style in TRIO:
            for m in compose.card(style)["moves"]:
                self.assertTrue(list(moves.rglob(f"{m['id']}.tsx")), (style, m["id"]))


class Sound(unittest.TestCase):
    def test_every_cut_photograph_and_closer_lays_a_sound(self):
        board = {"id": "t", "bpm": 120, "signoff": "@ines.bakes.lisbon", "beats": [
            {"id": "hook", "form": "title", "words": "up at five", "start": 0, "len": 4, "move": "slam-words",
             "transition": None},
            {"id": "build-1", "form": "photo", "words": "", "label": "the loaf", "start": 4, "len": 4, "move": None,
             "transition": "hard-cut"},
            {"id": "closer", "form": "closer", "words": "", "start": 8, "len": 6, "move": None,
             "transition": "hard-cut"}]}
        fx = film.fx_board(board)
        self.assertEqual([b["layers"][0]["kind"] for b in fx["beats"]], ["Title", "Photo", "Closer"])
        kinds = [k for _, k in sfx.events(fx)[0]]
        for k in ("impact", "shutter", "riser"):
            self.assertIn(k, kinds)
        self.assertTrue({"bright", "sweep", "air"} & set(kinds), kinds)


if __name__ == "__main__":
    unittest.main()
