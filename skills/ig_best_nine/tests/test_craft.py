"""The film at studio grade, as the parts a test can read: the finish and the faces are the style card's own, clip
requests a cinematographer would write with the beat's length and a loop and no two moments in a row moving the
same way, an accent the year's colors carry rather than a speck, out/ holding only what is posted with the
review page as its cover and the brief beside it in the run, and the critic scoring against the standards with the
posted three by three grid as the swap test's standard.

    python3 -I -m unittest discover -s S/tests -p test_craft.py
"""
import colorsys
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "tests"))
import _env  # noqa: E402
import compose  # noqa: E402
import deliver  # noqa: E402
import qa  # noqa: E402
import test_story  # noqa: E402

WARM = [{"hex": "#887561", "name": "taupe", "share": 0.42}, {"hex": "#2F2218", "name": "charcoal", "share": 0.26},
        {"hex": "#D9D7CF", "name": "snow white", "share": 0.19}, {"hex": "#C98E45", "name": "caramel", "share": 0.11},
        {"hex": "#AF1407", "name": "tomato red", "share": 0.02}]


class InRun(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.dir)


class Finish(unittest.TestCase):
    def test_the_finish_and_the_faces_are_the_style_cards_own(self):
        for style in compose.TRIO:
            with self.subTest(style=style):
                c, S = compose.card(style), test_story.board(style=style)["system"]
                self.assertEqual(S["finish"], c["finish"])
                self.assertEqual(S["ease"], c["ease"])
                for role in ("display", "text"):
                    self.assertEqual(S[role]["family"], c["faces"][role]["family"])


class Shots(unittest.TestCase):
    def test_each_clip_names_its_subject_move_lens_and_light_and_moments_vary_the_move(self):
        for style in compose.TRIO:
            cl = test_story.board(style=style)["clips"]
            for c in cl:
                self.assertRegex(c["prompt"], r"\d+ mm", (style, c["id"]))
                self.assertIn("light", c["prompt"])
                self.assertNotIn("camera still", c["prompt"])
            moves = [c["prompt"].split(": ", 1)[1].split(",")[0] for c in cl if c["role"] == "the photograph brought to life"]
            self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), (style, moves))

    def test_the_list_adds_the_beats_length_and_a_seamless_loop(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "photos").mkdir(parents=True)
            subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600",
                            "-frames:v", "1", str(run / "public/photos/a.jpg")], check=True)
            clip = {"id": "00", "beat": "hook", "role": "the wall's world", "seconds": 2.0, "image": "photos/a.jpg",
                    "prompt": "bread, as in this photograph: a slow push in, 35 mm lens, its own light", "stand_in": "s"}
            (run / "board.json").write_text(json.dumps({"beats": [{"id": "hook", "frames": 75}], "clips": [clip]}))
            (run / "film.json").write_text(json.dumps({"boards": {"reel": "board.json"}}))
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/clips.py"), "list", "--run", "build/run"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads((run / "clips/requests.json").read_text())["clips"][0]["prompt"]
            self.assertTrue(got.startswith(clip["prompt"]))
            self.assertIn("2.5 seconds", got)
            self.assertIn("seamless loop", got)


class Accent(unittest.TestCase):
    def test_a_speck_of_one_photograph_never_sets_the_accent(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            run.mkdir(parents=True)
            idx = [{"src": f"p{i}.jpg", "colors": [{"rgb": [int(c["hex"][k:k + 2], 16) for k in (1, 3, 5)], "share": c["share"]} for c in WARM]}
                   for i in range(9)]
            (run / "photo_index.json").write_text(json.dumps(idx))
            r = subprocess.run([sys.executable, "-I", str(KIT / "scripts/palette.py"), "--run", "build/run"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            accent = json.loads((run / "palette.json").read_text())["roles"]["accent"]
            hue = colorsys.rgb_to_hls(*(int(accent[k:k + 2], 16) / 255 for k in (1, 3, 5)))[0] * 360
            self.assertTrue(20 < hue < 50, f"{accent} is the caramel the year carries, not the 2 % tomato red")


class Cover(InRun):
    WIN = compose.TRIO[1]

    def setUp(self):
        super().setUp()
        for name, obj in (("library.json", {"handle": "you", "year": 2026}),
                          ("winner.json", {"board": self.WIN, "looks": list(compose.TRIO), "totals": {self.WIN: 90}}),
                          ("taste.json", {"register": {"lowercase": True}, "nine": [{"rank": 1, "why": "their own reason"}]}),
                          ("research.json", {"nine": [{"rank": 1, "why": "a drafted color word"}]}),
                          ("stats.json", {"top_ranked_by": "likes", "top_nine": [{"rank": 1, "date_label": "14 feb", "kind": "post", "likes": 5}]}),
                          ("film.json", {"style": self.WIN, "seconds": 30})):
            _env.write_json(name, obj)
        for t in compose.TRIO:
            Path(f"storyboards/{t}").mkdir(parents=True)
            Path(f"storyboards/{t}/sheet.png").write_bytes(b"png")
        _env.write_json(f"storyboards/{self.WIN}/board-reel.json", test_story.board(style=self.WIN))
        Path("out/storyboards").mkdir(parents=True)
        Path("out/storyboards/old.png").write_bytes(b"stale")
        Path("out/brief.md").write_text("stale")
        for patch in (mock.patch.object(_env, "tools", return_value={}), mock.patch.object(deliver, "ranking", return_value=[]),
                      mock.patch.object(qa, "gate_checks", return_value=(qa.Checks([("everything", True, "passed")]), {"hash": "h"})),
                      mock.patch.object(sys, "argv", ["deliver.py", "--run", str(self.dir)])):
            patch.start()
            self.addCleanup(patch.stop)

    def test_out_holds_what_is_posted_the_review_page_is_its_cover_and_the_brief_stays_in_the_run(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.main(), 0)
        self.assertFalse(Path("out/storyboards").exists(), "the storyboards stay in the run")
        self.assertFalse(Path("out/brief.md").exists(), "the brief, with its scores, is never in out/")
        page = Path("out/review.html").read_text()
        self.assertIn("film.mp4", page)
        self.assertNotIn("<table", page)
        brief = Path("brief.md").read_text().splitlines()
        self.assertIn("review.html", "\n".join(brief[:4]), "the brief opens with the cover's link")
        row = next(ln for ln in brief if ln.startswith("| 1 |"))
        self.assertIn("their own reason", row)


class Critic(unittest.TestCase):
    def test_the_critic_scores_against_the_standards_and_the_posted_grid_is_the_standard(self):
        critic = " ".join((KIT / "critic/critic.md").read_text().split())
        standards = (KIT / "motion/system/standards.md").read_text()
        for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"):
            self.assertIn(f"| {r} ", standards)
        self.assertIn("scored against", critic)
        self.assertIn("motion/system/standards.md", critic)
        self.assertNotIn("fixed slots", critic)
        self.assertIn("three by three grid of the posted image is the standard", critic)


if __name__ == "__main__":
    unittest.main()
