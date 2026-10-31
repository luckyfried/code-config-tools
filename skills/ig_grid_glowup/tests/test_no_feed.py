"""A folder of photos and no feed: there is nothing to audit and no grid before, so research.py writes no audit.md
and no grid-before.png, picks.py draws no grid sheet, and qa.py's gate has no audit row and no grid row and passes
on the rest. Nothing the agent or the critics read names a grid that was never made: the ballot sends no one to a grid
before, and the taste draft states no grid, no caption numbers and no posting time. A run with a feed keeps both files,
both rows and the sheet, and its ballot and taste draft read as they always have.

    python3 -I -m unittest discover -s S/tests -p test_no_feed.py
"""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_resume import BOARD, WIN, Run, checkable  # noqa: E402
import picks  # noqa: E402
import research  # noqa: E402
import vote  # noqa: E402

CELL = {"pos": 1, "caption": "", "file": None, "size": None, "plate": ["#e8dcc6", "#3b2418"], "accent": None}
PARAGRAPH = " ".join(["the frame carries each post in from the whole photograph and seats it at the top of the grid"] * 3)
TS = 1792698717  # a Thursday, 19:51 UTC
WEEK = 7 * 86400
# three posts a week apart, each Thursday evening, in their lowercase five-word voice
FEED = [{"pos": i, "kind": "post", "ts": TS - i * WEEK, "caption": "slow morning on the dunes", "media": [],
         "likes": 40 + i, "saves": 3} for i in range(3)]


class Research(Run):
    def research(self, posts):
        """research.py and research.py audit on a folder of photos beside a feed of `posts` (none: no feed), with what
        picks.py and palette.py leave for it: the posts' grid cells and no palette. Returns taste.draft.md."""
        self.write("library.json", {"handle": "you", "year": 2026, "source": "export" if posts else "photos", "grid": posts,
                                    "posts": posts, "reels": [], "stories": [], "likes": [], "saved": [], "comments": [],
                                    "facebook": [], "following": [], "photos": [{"ts": TS, "caption": "", "media": ["photos/a.jpg"]}]})
        self.write("grid.json", {"cells": [dict(p, flags=[], a={"bright": 0.5}) for p in posts]})
        self.write("palette.json", {})
        self.write("photo_index.json", [])
        with mock.patch.object(research, "run", lambda script: f"{script} ok\n"):
            self.assertEqual(self.main(research), 0)
            self.assertEqual(self.main(research, "audit"), 0)
        return Path("taste.draft.md").read_text()

    def test_with_no_feed_research_writes_no_audit_and_no_grid_before(self):
        self.research([])
        self.assertEqual(sorted(p.name for p in Path("out").glob("*")), [])
        self.assertTrue(Path("audit.json").exists())

    def test_with_no_feed_the_taste_draft_states_no_grid_no_caption_numbers_and_no_posting_time(self):
        draft = self.research([])
        self.assertNotIn("None", draft)
        for line in ("the grid now", "the usual grid post", "words a caption", "posts most on"):
            self.assertNotIn(line, draft)

    def test_with_a_feed_the_taste_draft_states_the_grid_the_caption_numbers_and_the_posting_time(self):
        draft = self.research(FEED)
        for line in ("- the grid now: ", "- the usual grid post: 41 likes, 3 saves",
                     "- 5 words a caption, 100% lowercase, 0.0 emoji a caption, endings {'no mark': 3}",
                     "- posts most on Thursday, around 19:00 UTC"):
            self.assertIn(line + "\n", draft)

    def test_with_a_feed_research_writes_the_audit_and_the_grid_before(self):
        cells = [{"pos": i, "kind": "post", "cover": None} for i in range(3)]
        picks.grid_sheet(cells, "grid-sheet.png")
        finding = {"title": "A run of posts that clash", "plain": "Three posts in a row pull away from the rest.", "positions": [0]}
        with contextlib.redirect_stdout(io.StringIO()):
            research.render_audit({"grid_size": 3, "findings": [finding] * 3, "patterns": [], "want": "Warm tones."}, "you")
        self.assertEqual([p for p in ("audit.md", "grid-before.png") if not Path(p).exists()], [])
        self.assertFalse(Path("out").exists())


class Picks(Run):
    def picks(self, grid):
        """picks.py on a folder of three photos beside a feed of `grid` posts, each with its own photo (none: no feed).
        Returns what it prints."""
        from PIL import Image
        Path("in").mkdir()

        def photo(name, rgb):
            path = Path("in", name).resolve()
            Image.new("RGB", (80, 100), rgb).save(path)
            return str(path)
        photos = [{"ts": TS + i, "caption": "", "media": [photo(f"{i}.jpg", rgb)]}
                  for i, rgb in enumerate(((180, 120, 90), (90, 140, 170), (200, 170, 60)))]
        grid = [dict(p, media=[photo(f"grid-{p['pos']}.jpg", (150, 110 + 10 * p["pos"], 80))]) for p in grid]
        self.write("library.json", {"source": "export" if grid else "photos", "grid": grid, "posts": grid, "stories": [],
                                    "facebook": [], "photos": photos})
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["picks.py"]), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(picks.main(), 0)
        return out.getvalue()

    def test_with_no_feed_picks_draws_no_grid_sheet(self):
        out = self.picks([])
        self.assertFalse(Path("grid-sheet.png").exists())
        self.assertNotIn("grid-sheet.png", out)

    def test_with_a_feed_picks_draws_the_grid_sheet(self):
        out = self.picks(FEED)
        self.assertTrue(Path("grid-sheet.png").exists())
        self.assertIn("wrote grid.json, grid-sheet.png, photo_index.json and picks.json\n", out)


class Ballot(Run):
    def ballot(self, before):
        """vote.py ballot on the three drafted storyboards beside a grid before of `before` (none: no feed, so research
        drew no grid-before.png). Returns vote/ballot.md."""
        for L, style in zip("ABC", ("editorial-quiet", "swiss-grid", "kinetic-type")):
            self.write(f"storyboards/{L}/board.json", dict(BOARD, letter=L, style=style, before=before))
            Path(f"storyboards/{L}/sheet.png").write_bytes(b"sheet")
            Path(f"storyboards/{L}/storyboard.md").write_text(L)
        if before:
            Path("grid-before.png").write_bytes(b"their grid")
        self.assertEqual(self.main(vote, "ballot"), 0)
        return Path("vote/ballot.md").read_text()

    def test_with_no_feed_the_ballot_names_no_grid_before(self):
        ballot = self.ballot([])
        self.assertNotIn("grid-before", ballot)
        self.assertIn("Open each board's sheet at full size and its storyboard before scoring.\n", ballot)

    def test_with_a_feed_the_ballot_puts_their_grid_before_beside_the_boards(self):
        self.assertIn("Open each board's sheet at full size and its storyboard before scoring, with their grid as it is "
                      "now (grid-before.png) beside them.\n", self.ballot([CELL]))


class Gate(Run):
    """qa.py's gate on a run whose other records are all in place."""

    def records(self, before):
        import qa
        board = dict(BOARD, before=before, boards=checkable("reel"))
        self.write("board.json", board)
        Path("photos").mkdir()
        Path("photos/a.jpg").write_bytes(b"a photograph")
        self.write("plan.json", {"slots": [{"n": 1, "date": "2026-10-28", "weekday": "Wednesday", "photo": "photos/a.jpg",
                                            "caption": "first light on the dunes",
                                            "shot": "the dune ridge at dawn, 35 mm at knee height, low raking sun"}],
                                 "film": {"hook": "the grid, glowed up", "ask": "come see the new nine",
                                          "world": "a dune path at first light, 50 mm at eye level, soft haze"}})
        self.write("taste.json", {})
        Path("taste.md").write_text("You are here. You like this. Your style is warm. Your voice is quiet. Avoid neon.")
        for L in "ABC":
            Path(f"storyboards/{L}").mkdir(parents=True)
            Path(f"storyboards/{L}/sheet.png").write_bytes(b"sheet")
        Path("storyboard.md").write_text("board")
        Path("vote.md").write_text("| A | editorial-quiet | 84 |\n")
        self.write("winner.json", WIN)
        Path("out").mkdir()
        Path("out/boards.png").write_bytes(b"the three boards")
        Path("out/film.mp4").write_bytes(b"the cut")
        Path("plan.md").write_text("| 1 |\n")
        Path("brief.md").write_text("how this was made")
        Path("out/review.html").write_text("<p>your next posts</p>")
        critics = {c: {"boards": {"film": {"scores": {k: 5 for k in vote.CRITERIA}, "paragraph": PARAGRAPH}}} for c in vote.CUT_PANEL}
        self.write("critic/cut-1.json", {"film": qa.sha(Path("out/film.mp4")), "critics": critics})
        return board

    def gate_rows(self, before):
        """The gate's own rows, the board and film checks green."""
        import qa
        board = self.records(before)
        with mock.patch.object(qa, "board_checks", lambda: (qa.Checks(), board)), \
                mock.patch.object(qa, "film_checks", lambda run=None: (qa.Checks(), board, None)):
            res, _ = qa.gate_checks()
        return {r[0]: r[1] for r in res}

    def film_rows(self, before):
        """The film checks' rows, every probe of the film quiet."""
        import qa
        import studio
        self.write("board.json", dict(BOARD, before=before, boards=checkable("reel")))
        self.write("render/film.json", {"hash": "h", "formats": ["reel"], "music": False})
        self.write("render/film-report.json", {"jobs": 1, "failed": 0, "findings": []})
        Path("out").mkdir(exist_ok=True)
        Path("out/film.mp4").write_bytes(b"the reel")
        quiet = {"probe": lambda film, run=None: {"streams": [], "format": {}}, "detect": lambda *a, **k: [],
                 "cards_check": lambda *a, **k: ([], 0, {}), "words_lost": lambda *a: [], "figures": lambda *a: None}
        with contextlib.ExitStack() as stack:
            for name, value in quiet.items():
                stack.enter_context(mock.patch.object(qa, name, value))
            stack.enter_context(mock.patch.object(studio, "measure", lambda *a, **k: {}))
            return [r[0] for r in qa.film_checks()[0]]

    def test_with_no_feed_the_gate_has_no_audit_or_grid_row_and_passes_on_the_rest(self):
        rows = self.gate_rows(before=[])
        self.assertNotIn("audit", rows)
        self.assertEqual([k for k, ok in rows.items() if not ok], [])
        self.assertNotIn("grid", self.film_rows(before=[]))

    def test_with_a_feed_the_gate_keeps_its_audit_and_grid_rows(self):
        self.assertIs(self.gate_rows(before=[CELL])["audit"], False)
        self.assertIn("grid", self.film_rows(before=[CELL]))


if __name__ == "__main__":
    unittest.main()
