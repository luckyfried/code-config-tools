"""The deliverables: film.py render makes the three films (the reel, landscape and square) with the rests at the films'
own size, the Story card and the caption file; qa.py's check refuses anything in out/ that is not a deliverable;
the review page opens on the reel with no banner once the gate passes, shows the other looks with how to ask for one,
and carries no score, rule or critic; and deliver.py's last line is the reel's path from the project's root, the path
the reply names first.

    python3 -I -m unittest discover -s tests -p test_deliverables.py
"""
import contextlib
import io
import os
import shutil
import struct
import sys
import unittest
import zlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_resume import BOARD, WIN, Run, checkable, green  # noqa: E402
import studio  # noqa: E402

FILMS = ["film-landscape.mp4", "film-square.mp4", "film.mp4"]
PLAN = {"film": {"hook": "the grid, glowed up", "ask": "come see the new nine"},
        "slots": [{"n": 1, "date": "2026-10-28", "caption": "slow morning, one cup"},
                  {"n": 2, "date": "2026-10-30", "caption": "the loaf, split down the middle"}]}


def png(w, h):
    """A PNG's bytes at w x h (one gray row repeated), enough for a size read."""
    raw = b"".join(b"\x00" + b"\x80" * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class Render(Run):
    def render(self):
        """film.py render, the makers faked: the out/ listing after it, the jobs it rendered and each still's scale."""
        import film
        self.write("board.json", dict(BOARD, boards={"reel": {}, "landscape": {}, "square": {}},
                                      rests={"hook": 3, "closer": 9}))
        self.write("winner.json", WIN)
        self.write("plan.json", PLAN)
        jobs, scales = [], []

        def bridge(js, name, run=None):
            for j in js:
                jobs.append(Path(j["out"]).name)
                Path(j["out"]).write_bytes(b"film" if j["type"] == "video" else png(1080, 1920))
            return {"jobs": len(js), "failed": 0, "findings": [], "seconds": 1.0}

        def still(b, f, out, **k):
            scales.append(k.get("scale"))
            return {"type": "still", "out": str(out)}

        def drawn(b, into):
            shutil.rmtree(into, ignore_errors=True)
            into.mkdir(parents=True)
            (into / "01.png").write_bytes(b"post")
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(film.critic, "run_swap", lambda b: {"pass": True}))
            stack.enter_context(mock.patch.object(studio, "video", lambda b, out, **k: {"type": "video", "out": str(out)}))
            stack.enter_context(mock.patch.object(studio, "still", still))
            stack.enter_context(mock.patch.object(studio, "render", bridge))
            stack.enter_context(mock.patch.object(film, "posts", drawn))
            stack.enter_context(mock.patch.object(film, "grid_after", lambda b, drawn, out: out.write_bytes(b"grid")))
            self.assertEqual(self.main(film, "render"), 0)
        return sorted(p.name for p in Path("out").iterdir()), jobs, scales

    def test_a_render_makes_the_three_films_the_story_card_and_the_caption_file(self):
        out, jobs, scales = self.render()
        self.assertEqual(out, sorted(FILMS + ["caption.txt", "grid-after.png", "posts", "story.png"]))
        self.assertEqual(sorted(j for j in jobs if j.endswith(".mp4")), FILMS)
        self.assertEqual(sorted(json_of("render/film.json")["formats"]), ["landscape", "reel", "square"])
        self.assertEqual(set(scales), {1})
        self.assertEqual(Path("out/story.png").read_bytes(), Path("frames/reel-closer.png").read_bytes())
        words = Path("out/caption.txt").read_text()
        for line in ("the grid, glowed up.", "come see the new nine.", "slow morning, one cup", "the loaf, split down the middle"):
            self.assertIn(line, words)


class Out(Run):
    """qa.py's check on out/: the deliverables of the render and nothing else."""

    def row(self):
        import qa
        self.write("board.json", dict(BOARD, boards=checkable("reel", "landscape", "square"),
                                      nine=[{"n": 1, "caption": "slow morning, one cup"}]))
        self.write("render/film.json", {"hash": "h", "formats": ["reel", "landscape", "square"], "music": False})
        self.write("render/film-report.json", {"jobs": 3, "failed": 0, "findings": []})
        self.write("plan.json", dict(PLAN, slots=PLAN["slots"][:1]))
        quiet = {"probe": lambda film, run=None: {"streams": [], "format": {}}, "detect": lambda *a, **k: [],
                 "cards_check": lambda *a, **k: ([], 0, {}), "words_lost": lambda *a: [], "figures": lambda *a: None}
        with contextlib.ExitStack() as stack:
            for name, value in quiet.items():
                stack.enter_context(mock.patch.object(qa, name, value))
            stack.enter_context(mock.patch.object(studio, "measure", lambda *a, **k: {}))
            res = qa.film_checks()[0]
        return next((r[1], r[2]) for r in res if r[0] == "out")

    def deliverables(self):
        Path("out/posts").mkdir(parents=True)
        for name in FILMS:
            Path("out", name).write_bytes(b"film")
        Path("out/posts/01.png").write_bytes(png(1080, 1350))
        Path("out/grid-after.png").write_bytes(b"grid")
        Path("out/story.png").write_bytes(png(1080, 1920))
        Path("out/caption.txt").write_text("Post 1, 2026-10-28\n\nslow morning, one cup\n")

    def test_the_deliverables_alone_pass(self):
        self.deliverables()
        ok, detail = self.row()
        self.assertTrue(ok, detail)

    def test_a_working_file_in_out_is_red_and_named(self):
        self.deliverables()
        Path("out/plan.md").write_text("| 1 |\n")
        ok, detail = self.row()
        self.assertFalse(ok)
        self.assertIn("not a deliverable: ['plan.md']", detail)

    def test_a_missing_story_card_or_caption_is_red(self):
        self.deliverables()
        Path("out/story.png").unlink()
        Path("out/caption.txt").write_text("the reel\n")
        ok, detail = self.row()
        self.assertFalse(ok)
        self.assertIn("out/story.png", detail)
        self.assertIn("caption.txt lacks the caption of posts [1]", detail)


class BlackCards(unittest.TestCase):
    """qa.py's card check on a film whose held card frames came out black: every frame is named, and nothing raises."""

    def test_card_frames_with_no_caption_ink_are_named_not_a_crash(self):
        import qa
        fb = {"system": {"safe": {"reel": {"left": 72, "right": 150}}}, "format": {"width": 1080}}
        seen = [("post-1", 137, {"caption": (96, 857)}), ("post-5", 282, {"caption": None})]
        with mock.patch.object(qa, "card_frames", lambda *a, **k: seen):
            bad, n, widest = qa.cards_check(fb, "reel", "out/film.mp4")
        self.assertEqual(n, 2)
        self.assertEqual(widest, {"caption": (96, 857)})
        self.assertEqual(bad, ["post-5 at frame 282: no caption ink found on the page"])


class Page(Run):
    """deliver.py: the review page is the film's cover, and its last line is the reel's path."""

    def deliver(self, gate, before=None):
        import deliver
        home = self.dir.resolve() / "home"
        run = home / "build" / "20261026-014049"
        run.mkdir(parents=True)
        os.chdir(run)
        self.write("library.json", {"handle": "h", "grid": True})
        self.write("taste.json", {"x": 1})
        self.write("winner.json", WIN)
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"film")
        Path("audit.md").write_text("## What your grid is doing\n\n1. a finding\n")
        if before:
            before()
        out = io.StringIO()
        with mock.patch.object(deliver._env, "HOME", home), mock.patch.object(deliver.qa, "gate_checks", gate), \
                mock.patch.object(sys, "argv", ["deliver.py"]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = deliver.main()
        return code, out.getvalue().splitlines()

    def test_on_a_green_gate_the_page_opens_on_the_reel_with_no_banner(self):
        code, _ = self.deliver(green)
        page = Path("out/review.html").read_text()
        self.assertEqual(code, 0)
        self.assertNotIn("Not ready", page)
        body = page.split("<main>", 1)[1]
        self.assertLess(body.index("<video class='reel' src='film.mp4'"), min(body.index("<img"), body.index("<h2")))
        self.assertTrue(Path("brief.md").exists())
        self.assertEqual(sorted(p.name for p in Path("out").iterdir()), ["film.mp4", "review.html"])

    def test_every_link_on_the_page_stays_inside_out(self):
        import re
        self.deliver(green)
        page = Path("out/review.html").read_text()
        links = re.findall(r"(?:href|src)=['\"]([^'\"]+)['\"]", page)
        self.assertTrue(links)
        self.assertEqual([x for x in links if x.startswith(("../", "/"))], [])

    def test_the_last_line_is_the_reels_path_from_the_projects_root(self):
        code, lines = self.deliver(green)
        self.assertEqual((code, lines[-1]), (0, "build/20261026-014049/out/film.mp4"))

    def test_the_page_shows_the_other_looks_and_no_score_rule_or_critic(self):
        import vote
        para = " ".join(["the frame carries each post in and lands it on the grid"] * 3)
        scores = {k: 3 for k in vote.CRITERIA}
        self.write_round = lambda: self.write("critic/cut-1.json", {"critics": {c: {"boards": {"film": {"scores": scores, "paragraph": para}}}
                                                                               for c in vote.CUT_PANEL}})
        self.deliver(green, before=self.write_round)
        page = Path("out/review.html").read_text()
        self.assertIn("Prefer another look?", page)
        self.assertIn("make the second one", page)
        self.assertIn("src=\"boards.png\"", page)
        self.assertIn("How it was made", page)
        low = page.lower()
        for word in ["critic", "score", "verdict", "the bar", "mean", "fix once"] + [r.split()[0].lower() for r in vote.CRITERIA.values()]:
            self.assertNotIn(word, low)
        brief = Path("brief.md").read_text()
        self.assertIn("4.5", brief)

    def test_a_red_gate_ends_on_the_failing_checks_name_and_no_path(self):
        import qa

        def red(run):
            res = qa.Checks()
            res("format", True, "out/film.mp4: 1080x1920")
            res("posts", False, "0 of 9 posts in out/posts/")
            return res, {"hash": "h"}
        code, lines = self.deliver(red)
        self.assertEqual((code, lines[-1]), (1, "not ready: the gate failed on posts"))


def json_of(p):
    import json
    return json.loads(Path(p).read_text())


if __name__ == "__main__":
    unittest.main()
