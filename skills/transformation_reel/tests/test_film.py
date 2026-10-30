"""The numbers the gate reads (scripts/qa.py) and the review page deliver.py writes.

    python3 -m unittest discover -s S/tests        (S = this skill's folder)
"""
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
# the look every board in these tests takes: the first of the trio
STYLE = "cinematic-letterbox"

import _env  # noqa: E402
import deliver  # noqa: E402
import qa  # noqa: E402


class Hook(unittest.TestCase):
    def test_an_entrance_on_frame_zero_is_a_hook(self):
        self.assertTrue(qa.hook_ok({"hook_frame": 0, "hook_difference": 5.2}))

    def test_a_late_entrance_or_frames_that_do_not_change_are_no_hook(self):
        self.assertFalse(qa.hook_ok({"hook_frame": 31, "hook_difference": 5.2}))
        self.assertFalse(qa.hook_ok({"hook_frame": 0, "hook_difference": 0.4}))
        self.assertFalse(qa.hook_ok({"hook_frame": None, "hook_difference": 5.2}))

    def test_an_opening_that_sets_their_words_is_the_first_event_and_day_one_landing_is_without_one(self):
        import storyboard
        film = {"pulse": 30, "cards": [{"arrive": 2.4}]}
        self.assertEqual(storyboard.hook_frame({"film": dict(film, opening=3.0)}), 0)
        self.assertEqual(storyboard.hook_frame({"film": dict(film, opening=0.0)}), 72)


class Figures(unittest.TestCase):
    def test_the_rest_line_reads_a_held_second_as_locked_and_a_moving_one_as_not(self):
        # Two seconds of a still field, then two of a bar crossing it; the trailing third of a second holds again.
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        v = d / "rest.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=160x320:r=30:d=4.34", "-f", "lavfi", "-i",
                        "color=c=white:s=24x320:r=30:d=4.34", "-filter_complex", "[0][1]overlay=x='if(lt(t,2),0,min(t-2,2)*60)':y=0",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(v)], check=True)
        line = qa.rest_line(v, 30, 130, 20, 40)
        self.assertEqual(len(line), 5)
        self.assertTrue(line[0] < 0.5 and line[1] < 0.5 and line[4] < 0.5, line)
        self.assertTrue(line[2] > 0.5 and line[3] > 0.5, line)


class Span(unittest.TestCase):
    def test_the_caption_states_the_span_in_their_own_words(self):
        said = {"label": "14 months", "said": "fourteen months in"}
        self.assertTrue(qa.span_check("14 months of pottery, august 2025 to october 2026", said)[0])
        self.assertTrue(qa.span_check("fourteen months of pottery", said)[0])

    def test_another_span_or_none_fails(self):
        said = {"label": "14 months", "said": "fourteen months in"}
        self.assertFalse(qa.span_check("a year of pottery", said)[0])
        self.assertFalse(qa.span_check("pottery, august 2025 to october 2026", said)[0])
        self.assertFalse(qa.span_check("14 months of pottery, 2 years in", said)[0])

    def test_a_span_they_never_say_stays_out_of_the_caption(self):
        unsaid = {"label": "9 months", "said": ""}
        self.assertFalse(qa.span_check("nine months of walking lisbon", unsaid)[0])
        self.assertTrue(qa.span_check("walking lisbon, nov 22 2025 to sep 5 2026", unsaid)[0])


class Strips(unittest.TestCase):
    """The timing round's strips come out of one read of the draft: every strip from a single ffmpeg pass."""

    def test_every_strip_comes_from_one_pass_over_the_draft(self):
        import film
        from PIL import Image
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        video = d / "draft.mp4"
        subprocess.run([_env.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc=size=180x320:rate=30:duration=3", "-pix_fmt", "yuv420p", str(video)], check=True)
        calls = []

        class Run:
            def spawn(self, argv, **kw):
                calls.append(argv)
                return subprocess.run(argv, **kw)
        sheets = [([0, 5, 10, 15], d / "strip-hook.png", 4, "18:32"), ([30, 40, 50, 60, 70, 80], d / "strip-p02.png", 6, "18:32"),
                  (list(range(0, 90, 30)), d / "film-strip.png", 10, "14:26")]
        film.grab(Run(), video, sheets)
        self.assertEqual(len(calls), 1)
        for frames, dst, cols, size in sheets:
            w, h = (int(v) for v in size.split(":"))
            rows = -(-len(frames) // cols)
            with Image.open(dst) as im:
                self.assertEqual(im.size, (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), dst.name)


class RunBoundary(unittest.TestCase):
    def test_the_one_fix_renders_again_in_its_run_and_only_a_published_film_starts_the_next(self):
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        saved = _env.B
        self.addCleanup(setattr, _env, "B", saved)
        os.chdir(d)
        run = Path("build") / "20261026-014049"
        _env.B = run
        for p in (run / "cut" / "film.mp4", run / "render" / "report.json", run / "subject.json"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        # a cut under the bar is rendered again for round 2 in the run the critics scored
        self.assertEqual(_env.open_run(), run)
        (run / "out").mkdir()
        (run / "out" / "film.mp4").write_text("the film the gate passed")
        with contextlib.redirect_stderr(io.StringIO()):
            nxt = _env.open_run()
        self.assertNotEqual(nxt, run)
        self.assertTrue((nxt / "subject.json").exists())


class Deliver(unittest.TestCase):
    """deliver.py stages its pages beside the cut in RUN/cut/ and publishes the set to RUN/out/ only on a passing gate,
    so out/ holds the deliverables alone and never a set the gate refused."""

    def setUp(self):
        import storyboard
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        saved = {(m, k): getattr(m, k) for m, k in ((_env, "B"), (deliver, "brief"), (subprocess, "run"), (storyboard, "lay_out"),
                                                    (qa, "gate_checks"))}
        self.addCleanup(lambda: [setattr(m, k, v) for (m, k), v in saved.items()])
        _env.B = d
        for name, body in (("library.json", {"handle": "@maren"}), ("taste.json", {"register": {}}), ("subject.json", {"subject": "pottery"}),
                           ("winner.json", {"board": STYLE, "totals": {STYLE: 30}}), ("film.json", {"board": STYLE})):
            _env.write_json(d / name, body)
        # their darkest and their paper are the film's own colors; the system's colors are one dark under the other
        self.colors = {"ground": "#594831", "ink": "#1b1513", "paper": "#efe8dc", "words": "#e6bc71"}
        storyboard.lay_out = lambda style, f="reel": {"facts": {"label": "14 months"}, "system": {"colors": {"bg": "#17100b", "ink": "#17100b"}},
                                                     "film": {"colors": self.colors, "cards": []}, "bpm": 120}
        # the three looks draft made, each with the frames boards.png shows
        from PIL import Image
        self.trio = storyboard.styles_of({})
        for s in self.trio:
            _env.write_json(d / "storyboards" / s / "storyboard.json", {"style": s, "title": f"Look {s}", "look_said": f"The {s} sentence.", "idea": "one idea"})
            (d / "storyboards" / s / "frames").mkdir()
            for k in storyboard.SHOWN:
                Image.new("RGB", (90, 160), (40, 30, 20)).save(d / "storyboards" / s / "frames" / f"{k}.png")
        self.real_brief = deliver.brief
        deliver.brief = lambda *a: "the brief\n"
        (d / "cut").mkdir()
        (d / "cut" / "film.mp4").write_bytes(b"the reel")
        self.page = d / "out" / "review.html"

    def gate(self, code):
        def checks(res, run):
            self.seen = _env.cut("review.html").read_text()
            self.out_during_gate = self.page.parent.exists()
            if code is None:
                raise KeyboardInterrupt
            res.add("film", True, "ok") if code == 0 else res.add("render", False, "1 failed")
        qa.gate_checks = checks

    def test_a_deliver_killed_while_its_gate_runs_leaves_no_out(self):
        self.page.parent.mkdir(parents=True)
        (self.page.parent / "film.mp4").write_bytes(b"the last deliver's reel")
        self.gate(None)
        with self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertFalse(self.page.parent.exists())
        self.assertFalse(self.out_during_gate)

    def test_only_a_passing_gate_publishes_and_out_holds_the_deliverables_alone(self):
        self.page.parent.mkdir(parents=True)
        (self.page.parent / "film.mp4").write_bytes(b"the last deliver's reel")
        self.gate(1)
        self.assertEqual(deliver.main(), 1)
        self.assertFalse(self.page.parent.exists())
        self.gate(0)
        self.assertEqual(deliver.main(), 0)
        self.assertEqual(sorted(p.name for p in self.page.parent.iterdir()), ["caption.md", "film.mp4", "looks", "review.html"])
        self.assertEqual(_env.b("brief.md").read_text(), "the brief\n")
        self.assertEqual((self.page.parent / "film.mp4").read_bytes(), b"the reel")
        for page in (self.seen, self.page.read_text()):
            self.assertNotIn("Not ready", page)

    def scored(self, scores):
        import vote
        round_ = {"round": 1, "film": vote.digest(_env.cut("film.mp4")),
                  "critics": {c: {"boards": {"film": {"scores": dict(scores), "not_read": [], "paragraph": "read"}}} for c in vote.CUT_PANEL}}
        _env.write_json(_env.b("critic", f"cut-{STYLE}-1.json"), round_)

    def test_the_way_to_ask_for_another_look_names_a_look_the_page_shows_never_the_one_made(self):
        _env.cut().mkdir(parents=True, exist_ok=True)
        shown = deliver.looks(_env.cut(), self.trio[1])
        self.assertIn('Prefer another look? Say "make the first one"', shown)
        self.assertNotIn("make the second one", shown)

    def test_the_review_page_shows_the_film_and_the_other_two_looks_and_never_a_score(self):
        import vote
        self.scored({"concept": 5, "image": 4, "type": 3, "motion": 5, "sound": 4, "shots": 4, "deliverable": 5})
        self.gate(0)
        self.assertEqual(deliver.main(), 0)
        page = self.page.read_text()
        said = re.sub(r"<[^>]+>", " ", page)
        others = [s for s in self.trio if s != STYLE]
        self.assertEqual(re.findall(r"src='(looks/[^']+)'", page), [f"looks/{self.trio.index(s) + 1}-{s}.png" for s in others])
        for s in others:
            self.assertTrue((self.page.parent / "looks" / f"{self.trio.index(s) + 1}-{s}.png").exists())
            self.assertIn(f"Look {s}", said)
        self.assertIn('Prefer another look? Say "make the second one"', page)
        self.assertIn("How it was made", page)
        for word in ("critic", "bar", "score", "scores", "round", "mean", "4.29"):
            self.assertNotRegex(said.lower(), rf"\b{re.escape(word)}\b")
        for rule in vote.CRITERIA.values():
            self.assertNotIn(rule.split()[0], said)

    def page_colors(self):
        css = re.search(r"body\{margin:0;background:(#[0-9a-f]{6});color:(#[0-9a-f]{6})", self.page.read_text())
        return css.group(1), css.group(2)

    def test_the_review_page_is_set_in_the_films_colors_and_its_text_reads(self):
        self.gate(0)
        self.assertEqual(deliver.main(), 0)
        self.assertEqual(self.page_colors(), ("#594831", "#efe8dc"))
        self.assertGreaterEqual(deliver.contrast(*self.page_colors()), 7)
        self.assertIn('poster="cover.png"', self.page.read_text())

    def test_a_palette_whose_words_would_not_read_on_the_page_gives_way_to_the_kits(self):
        self.colors.update(ink="#6a5a4a", paper="#8a7a6a")
        self.gate(0)
        self.assertEqual(deliver.main(), 0)
        self.assertGreaterEqual(deliver.contrast(*self.page_colors()), 7)

    def test_a_cut_under_the_bar_is_delivered_and_its_scores_are_stated_in_the_brief_alone(self):
        self.scored({"concept": 4, "image": 3, "type": 4, "motion": 3, "sound": 4, "shots": 2, "deliverable": 2})
        deliver.brief = self.real_brief
        self.gate(0)
        self.assertEqual(deliver.main(), 0)
        brief = _env.b("brief.md").read_text()
        under = re.search(r"Mean 3.14 against the bar of 4.5; under the bar on ([a-z, ]+)\.", brief)
        self.assertEqual(set(under.group(1).split(", ")), {"image", "motion", "shots", "deliverable"})
        self.assertNotIn("every rule read at", brief)
        self.assertNotIn("3.14", self.page.read_text())

    def test_the_last_line_is_the_reels_path_from_the_workspace_root(self):
        import contextlib
        import io
        ws = _env.B / "workspace"
        run = Path("build", "20261026-014049")
        (ws / run).mkdir(parents=True)
        shutil.copytree(_env.B, ws / run, dirs_exist_ok=True, ignore=lambda d, names: ["workspace"])
        here = os.getcwd()
        os.chdir(ws)
        self.addCleanup(os.chdir, here)
        _env.B = run
        self.page = ws / run / "out" / "review.html"
        self.gate(0)
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            self.assertEqual(deliver.main(), 0)
        self.assertEqual(said.getvalue().splitlines()[-1], "build/20261026-014049/out/film.mp4")

    def test_a_failed_gate_ends_on_what_failed_and_names_no_film(self):
        import contextlib
        import io
        self.gate(1)
        said = io.StringIO()
        with contextlib.redirect_stdout(said), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(deliver.main(), 1)
        self.assertEqual(said.getvalue().splitlines()[-1], "not delivered: the gate failed on render")
        self.assertNotIn("film.mp4", said.getvalue())
        self.assertFalse(self.page.parent.exists())

    def test_a_deliver_killed_before_its_page_leaves_no_page_from_the_last_deliver(self):
        self.page.parent.mkdir(parents=True)
        self.page.write_text("the last deliver's ready page")
        put = deliver.put

        def killed(path, text):
            raise KeyboardInterrupt
        deliver.put = killed
        self.addCleanup(setattr, deliver, "put", put)
        with self.assertRaises(KeyboardInterrupt):
            deliver.main()
        self.assertFalse(self.page.exists())

    @unittest.skipIf(os.name == "nt", "flock is POSIX; the Windows lock is proved on a Windows machine")
    def test_every_process_the_gate_starts_under_deliver_holds_the_runs_lock(self):
        import fcntl
        import storyboard
        d = _env.B
        _env.write_json(d / "timeline.json", {"fps": 30, "cuts": [30], "width": 1080, "height": 1920, "seconds": 10, "style": STYLE,
                                              "hook_frame": 0})
        _env.write_json(d / "music.json", {"file": "music/master.wav"})
        for name in qa.FILES.values():
            (d / "cut" / name).write_bytes(b"")
        _env.write_json(d / "render" / "report.json", {"failed": 0, "made": {"formats": list(qa.FILES)}})
        board = {"facts": {"label": "14 months"}, "system": {}, "bpm": 120, "beats": [{"id": "hook", "layers": []}],
                 "sound": [{"kind": "hit", "at": 0}, {"kind": "stop", "at": 8}],
                 "film": {"cards": [{"id": "p01", "date": "2025-08-01", "kind": "hook", "file": "public/stations/p01.jpg"}], "colors": self.colors}}
        saved = {k: getattr(storyboard, k) for k in ("measured", "check_board", "words_of")}
        self.addCleanup(lambda: [setattr(storyboard, k, v) for k, v in saved.items()])
        self.addCleanup(setattr, _env, "_TOOLS", _env._TOOLS)
        storyboard.lay_out = lambda style, f="reel": board
        storyboard.measured = lambda: [{"id": "p01", "date": "2025-08-01"}]
        storyboard.check_board = lambda *a: []
        storyboard.words_of = lambda b: []
        _env._TOOLS = {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
        lock = d / "render" / "render.lock"
        calls = []

        def run(argv, **kw):
            lock.parent.mkdir(parents=True, exist_ok=True)
            with open(lock, "a+") as f:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held = False
                except OSError:
                    held = True
            calls.append((Path(argv[0]).name, held, bool(kw.get("pass_fds"))))
            out = '{"streams": [{"codec_type": "audio"}], "format": {"duration": "10"}}' if kw.get("text") else b""
            return subprocess.CompletedProcess(argv, 0, out, "")
        subprocess.run = run
        deliver.main()
        self.assertEqual({c[0] for c in calls}, {"ffmpeg", "ffprobe"}, calls)
        self.assertGreater(len(calls), 10)
        self.assertTrue(all(c[1] and c[2] for c in calls), calls)

    def test_a_deliver_while_another_command_holds_the_lock_refuses_and_writes_nothing(self):
        import chunks
        self.gate(0)
        with chunks.lock(_env.b("render"), "report"):
            with self.assertRaises(SystemExit) as e:
                deliver.main()
        self.assertIn("report", str(e.exception.code))
        self.assertFalse(self.page.parent.exists())


class Gate(unittest.TestCase):
    """The gate reads each index, never the files an index completes: a board is whole when its storyboard.json and
    its sheet are there, and the strip is the strip of this reel or none."""

    def setUp(self):
        import storyboard
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        names = ("film_checks", "probe", "measure", "summary", "loudness", "ff", "cards_check", "order_check")
        saved = {(m, k): getattr(m, k) for m, k in [(_env, "B"), (storyboard, "lay_out"), (storyboard, "measured"), (storyboard, "check_board")]
                 + [(qa, n) for n in names]}
        self.addCleanup(lambda: [setattr(m, k, v) for (m, k), v in saved.items()])
        _env.B = d

    def boards(self):
        res = qa.Checks()
        qa.film_checks = lambda res, run=None: None
        qa.gate_checks(res)
        return next(r for r in res if r[0] == "boards")

    def test_a_board_whose_styleframes_are_all_there_with_no_sheet_is_not_whole(self):
        import storyboard
        trio = storyboard.styles_of({})
        for s in trio:
            sb = _env.b("storyboards", s)
            (sb / "frames").mkdir(parents=True, exist_ok=True)
            for f in storyboard.FRAMES:
                (sb / "frames" / f"{f}.png").write_bytes(b"a styleframe")
            (sb / "storyboard.md").write_text("the board")
            _env.write_json(sb / "storyboard.json", {"style": s})
            if s != STYLE:
                (sb / "sheet.png").write_bytes(b"the sheet")
        _env.write_json(_env.b("storyboards", "check.json"), {s: {"reel": []} for s in trio})
        _env.out("boards.png").parent.mkdir(parents=True, exist_ok=True)
        _env.out("boards.png").write_bytes(b"the three looks")
        self.assertFalse(self.boards()[1], self.boards())
        (_env.b("storyboards", STYLE) / "sheet.png").write_bytes(b"the sheet")
        self.assertTrue(self.boards()[1], self.boards())
        _env.out("boards.png").unlink()
        self.assertFalse(self.boards()[1], self.boards())

    def test_picking_another_look_clears_everything_made_for_the_first_and_keeps_the_three_looks(self):
        import argparse
        import storyboard
        import vote
        trio = storyboard.styles_of({})
        for s in trio:
            _env.write_json(_env.b("storyboards", s, "storyboard.json"), {"style": s, "title": s})
        _env.write_json(_env.b("film.json"), {"board": trio[0]})
        _env.write_json(_env.b("winner.json"), {"board": trio[0], "recommended": trio[0]})
        made = [_env.out("boards.png"), _env.out("film.mp4"), _env.out("looks", "a.png"), _env.cut("film.mp4"),
                _env.b("music", "bed.1", "bed.wav"), _env.b("critic", "timing.json"), _env.b("draft", "film.mp4"),
                _env.b("public", "clips", "1", "0001.jpg"), _env.b("caption.md"), _env.b("brief.md"), _env.b("music.json")]
        for p in made:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"made for the first look")
        _env.write_json(_env.b("film.json"), {"board": trio[0]})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vote.cmd_pick(argparse.Namespace(style=trio[1], why=None)), 0)
        self.assertEqual([p.name for p in made if p.exists()], ["boards.png"])
        self.assertEqual(sorted(p.name for p in _env.out().iterdir()), ["boards.png"])
        self.assertEqual(_env.read_json(_env.b("winner.json"))["board"], trio[1])
        self.assertTrue(all(_env.b("storyboards", s, "storyboard.json").exists() for s in trio))

    def test_picking_another_look_after_a_red_gate_keeps_the_three_looks_the_person_chose_from(self):
        import argparse
        import storyboard
        import vote
        trio = storyboard.styles_of({})
        for s in trio:
            _env.write_json(_env.b("storyboards", s, "storyboard.json"), {"style": s, "title": s})
        _env.write_json(_env.b("film.json"), {"board": trio[0]})
        _env.write_json(_env.b("winner.json"), {"board": trio[0], "recommended": trio[0]})
        # a deliver whose gate went red carried boards.png into cut/ and left no out/
        for p in (_env.cut("boards.png"), _env.cut("film.mp4")):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"made for the first look")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vote.cmd_pick(argparse.Namespace(style=trio[1], why=None)), 0)
        self.assertEqual(sorted(p.name for p in _env.out().iterdir()), ["boards.png"])
        self.assertFalse(_env.cut().exists())

    def test_a_strip_that_ffmpeg_does_not_finish_leaves_no_strip(self):
        import storyboard
        _env.write_json(_env.b("timeline.json"), {"seconds": 2.0})
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        for name in qa.FILES.values():
            _env.cut().mkdir(parents=True, exist_ok=True)
            _env.cut(name).write_bytes(b"a film")
        _env.b("qa").mkdir()
        strip = _env.b("qa", "strip.png")
        strip.write_bytes(b"the strip of the last reel")
        qa.probe = lambda p, run=None: {}
        qa.measure = lambda *a: {"hook_frame": 0, "hook_difference": 0, "sound": {"stop": 2.0}, "duration": 2.0}
        qa.summary = lambda m: ""
        qa.cards_check = lambda: (True, "")
        qa.order_check = lambda b, rows: (True, "")
        storyboard.lay_out = lambda style, f="reel": {"facts": {}}
        storyboard.measured = lambda: []
        storyboard.check_board = lambda b, rows, fx: []

        def ff(*args, run=None):
            if "-frames:v" in args:
                Path(args[-1]).write_bytes(b"half a strip")
                return subprocess.CompletedProcess(args, 1, "", "killed")
            return subprocess.CompletedProcess(args, 0, "", "")
        qa.ff = ff
        qa.film_checks(qa.Checks())
        self.assertEqual(sorted(p.name for p in _env.b("qa").iterdir()), ["numbers.json"])

    def frozen_row(self, start, end):
        """The check's frozen row over a 60 s reel whose music stops at 57.1 s, with one frozen stretch from `start`
        to `end`."""
        import storyboard
        _env.write_json(_env.b("timeline.json"), {"seconds": 60.0})
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        for name in qa.FILES.values():
            _env.cut().mkdir(parents=True, exist_ok=True)
            _env.cut(name).write_bytes(b"a film")
        qa.probe = lambda p, run=None: {}
        qa.measure = lambda *a: {"hook_frame": 0, "hook_difference": 5, "sound": {"stop": 57.1}, "duration": 60.0}
        qa.summary = lambda m: ""
        qa.cards_check = lambda: (True, "")
        qa.order_check = lambda b, rows: (True, "")
        storyboard.lay_out = lambda style, f="reel": {"facts": {}}
        storyboard.measured = lambda: []
        storyboard.check_board = lambda b, rows, fx: []
        said = (f"[freezedetect @ 0x1] lavfi.freezedetect.freeze_start: {start}\n"
                f"[freezedetect @ 0x1] lavfi.freezedetect.freeze_duration: {end - start}\n"
                f"[freezedetect @ 0x1] lavfi.freezedetect.freeze_end: {end}\n")
        qa.ff = lambda *args, run=None: subprocess.CompletedProcess(args, 0, "", said if any("freezedetect" in str(a) for a in args) else "")
        res = qa.Checks()
        with contextlib.redirect_stdout(io.StringIO()):
            qa.film_checks(res)
        return next(r for r in res if r[0] == "frozen")

    def test_a_closer_that_settles_under_a_second_before_the_stop_is_not_frozen_and_a_stall_is(self):
        self.assertTrue(self.frozen_row(56.17, 60.0)[1])
        self.assertFalse(self.frozen_row(56.0, 60.0)[1])
        self.assertFalse(self.frozen_row(20.0, 21.2)[1])

    def test_the_check_measures_the_films_type_in_the_picked_looks_faces(self):
        import compose
        import storyboard
        _env.write_json(_env.b("timeline.json"), {"seconds": 2.0})
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        for name in qa.FILES.values():
            _env.cut().mkdir(parents=True, exist_ok=True)
            _env.cut(name).write_bytes(b"a film")
        qa.probe = lambda p, run=None: {}
        qa.measure = lambda *a: {"hook_frame": 0, "hook_difference": 0, "sound": {"stop": 2.0}, "duration": 2.0}
        qa.summary = lambda m: ""
        qa.cards_check = lambda: (True, "")
        qa.order_check = lambda b, rows: (True, "")
        qa.ff = lambda *args, run=None: subprocess.CompletedProcess(args, 0, "", "")
        storyboard.lay_out = lambda style, f="reel": {"facts": {}}
        storyboard.measured = lambda: []
        seen = []
        storyboard.check_board = lambda b, rows, fx: seen.append(compose.in_use()["id"]) or []
        # another look was in use in this process before the check, as it is when the check runs after a sheet
        compose.use(next(s for s in storyboard.styles_of({}) if s != STYLE))
        qa.film_checks(qa.Checks())
        self.assertEqual(set(seen), {STYLE})


    def audio_row(self, fx_lufs):
        """The gate's audio row over three films at -14 LUFS whose master measured the bed at -21.4 LUFS and the
        effects at `fx_lufs`, with two sound cues over three beats."""
        import storyboard
        _env.write_json(_env.b("timeline.json"), {"seconds": 40.0})
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        _env.write_json(_env.b("music.json"), {"file": "music/source.wav", "bed_lufs": -21.4, "fx_lufs": fx_lufs})
        _env.cut().mkdir(parents=True, exist_ok=True)
        for name in qa.FILES.values():
            _env.cut(name).write_bytes(b"a film")

        def probe(p, run=None):
            w, h = qa.SIZES[next(f for f, n in qa.FILES.items() if n == Path(p).name)]
            return {"streams": [{"codec_type": "video", "width": w, "height": h, "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p",
                                 "r_frame_rate": "30/1"}, {"codec_type": "audio", "codec_name": "aac", "bit_rate": "192000"}],
                    "format": {"duration": "40"}}
        qa.probe = probe
        qa.loudness = lambda film, run=None: -14.0
        qa.measure = lambda *a: {"hook_frame": 0, "hook_difference": 0, "sound": {"stop": 40.0}, "duration": 40.0}
        qa.summary = lambda m: ""
        qa.cards_check = lambda: (True, "")
        qa.order_check = lambda b, rows: (True, "")
        qa.ff = lambda *args, run=None: subprocess.CompletedProcess(args, 0, "", "")
        # the count of cues is the board's, the one source the gate and the figures both read: two landings and the stop
        storyboard.lay_out = lambda style, f="reel": {"facts": {}, "beats": [{"id": "hook"}, {"id": "p02"}, {"id": "closer"}], "bpm": 112.5,
                                                     "sound": [{"kind": "land", "at": 1}, {"kind": "land", "at": 9}, {"kind": "stop", "at": 20}]}
        storyboard.measured = lambda: []
        storyboard.check_board = lambda b, rows, fx: []
        res = qa.Checks()
        qa.film_checks(res)
        return next(r for r in res if r[0] == "audio")

    def test_effects_peak_normalized_over_a_quiet_bed_turn_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-16.3)
        self.assertFalse(ok, detail)
        self.assertIn("bed -21.4 LUFS, effects -16.3 LUFS", detail)
        self.assertIn("2 sound cues over 3 beats", detail)

    def test_effects_eight_lu_under_the_bed_turn_the_audio_row_green(self):
        _, ok, detail = self.audio_row(-29.4)
        self.assertTrue(ok, detail)
        self.assertIn("8.0 LU under", detail)
        self.assertIn("2 sound cues over 3 beats", detail)

    def test_effects_less_than_eight_lu_under_the_bed_turn_the_audio_row_red(self):
        _, ok, detail = self.audio_row(-28.9)
        self.assertFalse(ok, detail)
        self.assertIn("7.5 LU under (at least 8)", detail)


    def test_the_critic_row_refuses_the_ballot_the_vote_refuses(self):
        import storyboard
        import vote
        storyboard.lay_out = lambda style, f="reel": None
        qa.film_checks = lambda res, run=None: None
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        reel = _env.cut("film.mp4")
        reel.parent.mkdir(parents=True, exist_ok=True)
        reel.write_bytes(b"the reel")
        full = ("Watched it through with sound: their line lands on every photograph, the chapters hold longer with their "
                "next line under them, and the closer grows their own words out of the latest station.")
        cut = {"film": qa.sha(reel), "critics": {c: {"boards": {"film": {"scores": {k: 4 for k in vote.CRITERIA}, "paragraph": full}}}
                                                 for c in vote.CUT_PANEL}}

        def critic():
            res = qa.Checks()
            qa.gate_checks(res)
            return next(r for r in res if r[0] == "critic")
        cut["critics"]["person"]["boards"]["film"]["paragraph"] = "that is my year of clay in my own words, yes"
        _env.write_json(_env.b("critic", f"cut-{STYLE}-1.json"), cut)
        row = critic()
        self.assertFalse(row[1], row)
        self.assertIn("person / board film: the paragraph needs at least 25 words", row[2])
        cut["critics"]["person"]["boards"]["film"]["paragraph"] = full
        _env.write_json(_env.b("critic", f"cut-{STYLE}-1.json"), cut)
        # a whole first round under the bar with a lever in reach is the one fix still to take
        row = critic()
        self.assertFalse(row[1], row)
        self.assertIn("FIX ONCE: concept has a lever, take the one fix", row[2])
        # with the fix taken, a second round under the bar is delivered with its scores: the gate never refuses a score
        reel.write_bytes(b"the reel after the one fix")
        _env.write_json(_env.b("critic", f"cut-{STYLE}-2.json"), cut | {"film": qa.sha(reel), "round": 2, "fixed": "the subject's milestones"})
        row = critic()
        self.assertTrue(row[1], row)
        self.assertIn("DELIVER WITH SCORES", row[2])

    def test_a_session_that_made_no_clip_before_the_render_has_no_lever_for_the_shots(self):
        import vote
        reel = _env.cut("film.mp4")
        reel.parent.mkdir(parents=True, exist_ok=True)
        reel.write_bytes(b"the reel")
        _env.write_json(_env.b("film.json"), {"board": STYLE})
        scores = {k: 5 for k in vote.CRITERIA} | {"shots": 2}
        _env.write_json(_env.b("critic", f"cut-{STYLE}-1.json"), {"film": qa.sha(reel), "round": 1, "critics": {
            c: {"boards": {"film": {"scores": scores, "paragraph": ""}}} for c in vote.CUT_PANEL}})
        rs = vote.rounds()
        _env.write_json(_env.b("clips.json"), {"clips": {"clip-p01": {"status": "generated"}, "clip-p04": {"status": "photograph"}}})
        self.assertEqual(vote.outcome(rs)[:2], ("FIX ONCE", "shots"))
        _env.write_json(_env.b("clips.json"), {"clips": {"clip-p01": {"status": "photograph"}, "clip-p04": {"status": "photograph"}}})
        what, rule, why = vote.outcome(rs)
        self.assertEqual((what, rule), ("DELIVER WITH SCORES", None))
        self.assertIn("shots", why)


if __name__ == "__main__":
    unittest.main()
