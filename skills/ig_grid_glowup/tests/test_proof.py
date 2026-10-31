"""The proof: every critic round before deliver renders the films at half size, and the deliver render is full size.

film.py render --proof renders each film at half size as out/proof.mp4 and out/proof-<format>.mp4, never over
out/film.mp4, with the frames, posts, Story card and grid as the full render makes them, and render/film.json records
its scale; a full render takes the proof's films out of out/. qa.py check reads the proof while it is the newest
render and says so first, and every size and place it measures on the proof (the films' size, the caption's ink on the
held pages) is in board units, the full render's numbers. vote.py cut opens the round on the proof; the full-size
film of the same cut moves the round to it and empties the type scores, which the critics read again at full size.
deliver.py refuses a run whose newest render is the proof.

    python3 -I -m unittest discover -s tests -p test_proof.py
"""
import contextlib
import io
import json
import re
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_deliverables import png  # noqa: E402
from test_resume import PLAIN, Run  # noqa: E402
import _env  # noqa: E402
import chunks  # noqa: E402
import drive  # noqa: E402
import proof  # noqa: E402
import studio  # noqa: E402

# render.py as studio.render calls it: every job drawn at its board's size times its scale, paper with the caption's
# ink over each held page's box, and in a film a square that moves, so no stretch of it is frozen
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[2]))
ff = os.environ["FAKE_FFMPEG"]
for job in spec["jobs"]:
    fb, s = job["props"]["board"], job["scale"]
    w, h = round(fb["format"]["width"] * s), round(fb["format"]["height"] * s)
    ink = "".join(f",drawbox=x={round(x0 * s)}:y={round(y0 * s)}:w={round((x1 - x0) * s)}:h={round((y1 - y0) * s)}:color=0x1a1410:t=fill"
                  for b in fb["beats"] for x0, y0, x1, y1 in [b["layers"][0]["page"]["box"]])
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    paper = ["-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30"]
    if job["type"] == "video":
        a, b = job["frameRange"]
        side = round(200 * s)
        graph = f"[0]null{ink}[paper];[paper][1]overlay=x='{s}*(100+300*(t+{a}/30))':y={round(300 * s)},format=yuv420p"
        subprocess.run([ff, "-v", "error", "-y", *paper, "-f", "lavfi", "-i", f"color=c=0x30507a:s={side}x{side}:r=30",
                        "-filter_complex", graph, "-frames:v", str(b - a + 1), "-c:v", "libx264", "-preset", "ultrafast",
                        "-crf", "12", job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", *paper, "-vf", "null" + ink, "-frames:v", "1", job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""
FRAMES = 60


def page(top):
    """A held post's page: one caption line at y, its ink over the box from 300 to 700 px across."""
    return {"lines": [{"y": top + 70, "size": 80, "words": [{"at": 0.5}]}], "box": [300, top, 700, top + 80],
            "color": "#1a1410", "sink": 3.5}


def fmt_board(fmt, w, h):
    beat = {"id": "post-1", "frames": FRAMES, "layers": [{"page": page(h - 790), "times": {"close": [0.5]}, "full": True}]}
    return {"beats": [beat], "format": {"width": w, "height": h, "fps": 30},
            "system": {"safe": {fmt: {"left": 60, "right": 60}}, "colors": {"paper": "#f0e8d8", "ink": "#1a1410"}}}


BOARD = {"boards": {"reel": fmt_board("reel", 1080, 1920), "square": fmt_board("square", 1080, 1080)},
         "rests": {"hook": 5, "closer": 50}, "hash": "h", "letter": "A", "style": "editorial-quiet",
         "name": "Editorial quiet", "tempo": 120, "seconds": FRAMES / 30, "nine": [{"n": 1, "caption": "slow morning, one cup"}],
         "check": {"pass": True, "faults": []}, "cuts_at": [], "hook_frame": 0, "handle": "them"}
WIN = {"board": "A", "style": "editorial-quiet", "name": "Editorial quiet", "by": "taste", "reason": "their quiet captions",
       "others": ["B", "C"], "hash": "h"}
PLAN = {"film": {"hook": "the grid, glowed up", "ask": "come see the new nine"},
        "slots": [{"n": 1, "date": "2026-10-28", "caption": "slow morning, one cup"}]}


class Proof(Run):
    def setUp(self):
        super().setUp()
        fake = self.dir / "proof-render.py"
        fake.write_text(FAKE)
        for patch in (mock.patch.object(studio, "RENDERER", fake), mock.patch.object(drive, "CAP", {"display": 0.7})):
            patch.start()
            self.addCleanup(patch.stop)
        self.write("board.json", BOARD)
        self.write("winner.json", WIN)
        self.write("plan.json", PLAN)
        self.write("critic/swap.json", {"pass": True, "swap": {"1": "the cup"}, "objections": []})

    def render(self, *argv):
        """film.py render, the swap test, the posts and the grid faked: what it printed."""
        import film

        def drawn(b, into):
            shutil.rmtree(into, ignore_errors=True)
            into.mkdir(parents=True)
            (into / "01.png").write_bytes(png(1080, 1350))
        said = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(film.critic, "run_swap", lambda b: {"pass": True}))
            stack.enter_context(mock.patch.object(film, "posts", drawn))
            stack.enter_context(mock.patch.object(film, "grid_after", lambda b, drawn, out: out.write_bytes(b"grid")))
            stack.enter_context(mock.patch.object(sys, "argv", ["film.py", "render", *argv]))
            stack.enter_context(contextlib.redirect_stdout(said))
            self.assertEqual(film.main(), 0)
        return said.getvalue()

    def check(self):
        """qa.py check: its exit, what it printed, qa/check.json and the reel's measurement."""
        import qa
        said = io.StringIO()
        with mock.patch.object(sys, "argv", ["qa.py", "check"]), contextlib.redirect_stdout(said):
            rc = qa.main()
        return rc, said.getvalue(), _env.read_json("qa/check.json"), _env.read_json("qa/film.check.json")

    def size(self, mp4):
        p = json.loads(PLAIN.spawn([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "json", mp4],
                                   capture_output=True, text=True).stdout)["streams"][0]
        return p["width"], p["height"]

    def test_the_proof_renders_at_half_size_beside_the_film_and_never_over_it(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last full-size film")
        said = self.render("--proof")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(self.size("out/proof.mp4"), (540, 960))
        self.assertEqual(self.size("out/proof-square.mp4"), (540, 540))
        self.assertEqual(chunks._frames(PLAIN, _env.ffprobe(), Path("out/proof.mp4")), FRAMES)
        self.assertFalse(Path("out/film-square.mp4").exists())
        self.assertIn("out/proof.mp4", said)
        self.assertIn("half-size proof", said)
        self.assertEqual(_env.read_json("render/film.json")["scale"], proof.SCALE)
        self.assertEqual(proof.scale(), proof.SCALE)
        from PIL import Image
        self.assertEqual(Image.open("frames/reel-closer.png").size, (1080, 1920), "the critics' frames are full size on a proof")
        self.assertTrue(Path("out/story.png").exists() and Path("out/posts/01.png").exists())
        self.render()
        self.assertEqual(self.size("out/film.mp4"), (1080, 1920))
        self.assertEqual(self.size("out/film-square.mp4"), (1080, 1080))
        self.assertEqual(proof.films("out"), [], "a full render takes the proof's films out of out/")
        self.assertEqual(_env.read_json("render/film.json")["scale"], 1)
        self.assertEqual(proof.scale(), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.render("--proof")
        rc, said, proof_check, proof_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said.splitlines()[0])
        self.assertEqual(proof_check["film"], _env.read_json("render/film.json")["reel"])
        self.assertTrue(Path("qa/film-strip2.png").exists(), "the strip keeps its name on the proof")
        self.render()
        rc, said, full_check, full_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        sizes = lambda c: [re.search(r": (\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "format"]
        self.assertEqual(sizes(proof_check), ["1080x1920", "1080x1080"])
        self.assertEqual(sizes(proof_check), sizes(full_check))
        cards = lambda c: [x["detail"].split(": ", 1)[1] for x in c["checks"] if x["check"] == "cards"]
        self.assertEqual(cards(full_check), ["3 held page frames, caption inside the safe width: caption x 300 to 699"] * 2)
        self.assertEqual(cards(proof_check), cards(full_check), "the caption's ink is measured in board units on the proof")
        for k in ("seconds", "frames", "cuts", "planned_cuts", "extra_scene_cuts", "seconds_under_half"):
            self.assertEqual(proof_measured[k], full_measured[k], k)
        for a, b in zip(proof_measured["luma"], full_measured["luma"]):
            self.assertAlmostEqual(a, b, delta=0.25)

    def test_a_proof_the_size_of_the_film_fails_the_format_check(self):
        self.render()
        for p in Path("out").glob("film*.mp4"):
            shutil.copyfile(p, proof.of(p))
        rc, said, check, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "format"], [False, False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_the_gate_reads_the_full_size_films_only(self):
        import qa
        self.render("--proof")
        res = qa.film_checks()[0]
        self.assertEqual([(r[1], r[2]) for r in res if r[0] == "format"][0], (False, "out/film.mp4 is missing"))
        out = next(r for r in res if r[0] == "out")
        self.assertFalse(out[1])
        self.assertIn("proof.mp4", out[2])


SCORES = {"concept": 5, "image": 5, "type": 5, "motion": 5, "sound": 5, "posts": 5, "deliverable": 5}
WORDS = " ".join(["the reel lands each post on its cell and the type settles in the style's own faces"] * 3)


class Rounds(Run):
    """vote.py cut on the proof, then on the full-size film of the same cut."""

    def rendered(self, digest, scale, board_hash="h"):
        """The record of a render: render/film.json and qa/check.json for its reel, and its films in out/."""
        Path("out").mkdir(exist_ok=True)
        for p in Path("out").glob("*.mp4"):
            p.unlink()
        Path("out/film.mp4" if scale == 1 else "out/proof.mp4").write_bytes(digest.encode())
        self.write("board.json", dict(BOARD, hash=board_hash))
        self.write("render/film.json", {"hash": board_hash, "reel": digest, "scale": scale, "formats": ["reel"]})
        self.write("qa/check.json", {"film": digest})

    def vote(self, cmd):
        import vote
        said = io.StringIO()
        with mock.patch.object(sys, "argv", ["vote.py", cmd]), contextlib.redirect_stdout(said):
            rc = vote.main()
        return rc, said.getvalue()

    def fill(self, n, scores=SCORES):
        f = Path(f"critic/cut-{n}.json")
        data = _env.read_json(f)
        for c in data["critics"].values():
            c["boards"]["film"].update(scores={k: (scores[k] if v is None else v) for k, v in c["boards"]["film"]["scores"].items()},
                                       paragraph=WORDS)
        f.write_text(json.dumps(data))
        return data

    def test_the_round_moves_from_the_proof_to_the_full_size_film_and_the_type_is_read_again(self):
        self.rendered("proofreel", proof.SCALE)
        rc, said = self.vote("cut")
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said)
        first = _env.read_json("critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]), ("proofreel", proof.SCALE, "h"))
        self.fill(1)
        rc, said = self.vote("verdict")
        self.assertEqual(rc, 0)
        self.assertIn("SHIP", said)
        self.assertIn("render the full-size film (film.py render), run qa.py check, then vote.py cut", said)
        self.rendered("fullreel", 1)
        rc, said = self.vote("cut")
        self.assertIn("moves to the full-size", said)
        self.assertEqual(sorted(Path("critic").glob("cut-*.json")), [Path("critic/cut-1.json")])
        moved = _env.read_json("critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"], moved["proof_film"]), ("fullreel", 1, "proofreel"))
        for c in moved["critics"].values():
            got = c["boards"]["film"]["scores"]
            self.assertIsNone(got["type"])
            self.assertEqual({k: v for k, v in got.items() if k != "type"}, {k: 5 for k in SCORES if k != "type"})
        self.assertEqual(self.vote("verdict")[0], 1, "the round waits for the type read at full size")
        self.fill(1, dict(SCORES, type=4))
        rc, said = self.vote("verdict")
        self.assertIn("SHIP", said)
        self.assertNotIn("full-size", said)

    def test_a_fix_once_on_the_proof_names_the_proof_render(self):
        self.rendered("proofreel", proof.SCALE)
        self.vote("cut")
        self.fill(1, dict(SCORES, sound=2))
        rc, said = self.vote("verdict")
        self.assertEqual(rc, 2)
        self.assertIn("film.py render --proof", said)

    def test_a_new_cut_opens_the_next_round_on_its_proof(self):
        self.rendered("proofreel", proof.SCALE)
        self.vote("cut")
        self.fill(1, dict(SCORES, sound=2))
        self.rendered("fullother", 1, board_hash="h2")
        self.vote("cut")
        self.assertTrue(Path("critic/cut-2.json").exists())
        self.assertEqual(_env.read_json("critic/cut-1.json")["film"], "proofreel")


class Deliver(Run):
    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof(self):
        import deliver
        Path("out").mkdir()
        Path("out/proof.mp4").write_bytes(b"proof")
        with mock.patch.object(deliver.qa, "gate_checks", lambda run=None: self.fail("the gate never runs on a proof")), \
                mock.patch.object(sys, "argv", ["deliver.py"]), self.assertRaises(SystemExit) as stop:
            deliver.main()
        self.assertEqual(str(stop.exception), proof.refusal("out/film.mp4"))
        self.assertIn("film.py render for the full-size film", str(stop.exception))
        self.assertFalse(Path("out/review.html").exists())


if __name__ == "__main__":
    unittest.main()
