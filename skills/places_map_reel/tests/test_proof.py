"""The proof: every round before deliver renders the three films at half size beside them in out/ (out/proof.mp4,
out/proof-16x9.mp4, out/proof-square.mp4), never over out/film.mp4, with the posted image, the story card and frames/
as the full render makes them; qa.py check and vote.py cut read the newest render and say so, a check that measures
pixels measures in board units, so a proof and a full render of one cut read the same, and a round's frames come from
the render it reads; the critics' round on a proof moves to the full-size film with its frames cut again from it and
R3, the type, read again there; deliver.py refuses a run whose newest render is the proof.

    python3 -I -m unittest discover -s S/tests -p test_proof.py
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import board_drive  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
FRAMES = 60
SIZES = {"reel": (1080, 1920), "landscape": (1920, 1080), "square": (1080, 1080)}


def drawn(jobs, name, run=None):
    """studio.render as the composition draws: every job at its board's size times its scale. A film is paper with a
    dark square that crosses it, and the paper turns at the film's second second, so the cut and the move are drawn in
    board units and land at the same place of the frame at any scale; a still is a test picture at the job's size."""
    for job in jobs:
        w, h = SIZES[job["props"]["board"]["format"]]
        s = job.get("scale") or 1
        w, h = round(w * s), round(h * s)
        Path(job["out"]).parent.mkdir(parents=True, exist_ok=True)
        if job["type"] == "video":
            side = round(300 * s)
            graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte(t,1)'[paper];"
                     f"[paper][1]overlay=x='{s}*(100+300*t)':y={round(500 * s)},format=yuv420p")
            subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30",
                            "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                            "-frames:v", str(job["frames"]), "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high",
                            job["out"]], check=True)
        else:
            subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={w}x{h}", "-frames:v", "1",
                            job["out"]], check=True)
    return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}


def size(media):
    p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                   "-of", "json", str(media)], capture_output=True, text=True).stdout)["streams"][0]
    return p["width"], p["height"]


class InARun(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        self.run_dir = Path(tmp.name)
        enter = mock.patch.object(_env, "enter_run", lambda *a: Path.cwd())
        enter.start()
        self.addCleanup(enter.stop)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(InARun):
    def setUp(self):
        super().setUp()
        for patch in (mock.patch.object(studio, "render", drawn),
                      mock.patch.object(board_drive, "fx_board", lambda b: {"id": "board", "bpm": 120, "beats": []})):
            patch.start()
            self.addCleanup(patch.stop)
        for fmt in SIZES:
            _env.write_json(f"board-{fmt}.json", {"id": fmt, "format": fmt})
        _env.write_json("film.json", {"hash": "h", "style": "swiss-grid", "frames": FRAMES, "seconds": FRAMES / 30,
                                      "cuts": [1.0], "hook_frame": 4, "length": [0, 60],
                                      "boards": {fmt: f"board-{fmt}.json" for fmt in SIZES},
                                      "rests": {fmt: {"hook": 4, "stop": 30, "closer": 50} for fmt in SIZES}})
        _env.write_json("qa/timed.json", {"hash": "h", "pass": True})

    def render(self, *args):
        with mock.patch.object(sys, "argv", ["film.py", "render", *args]), contextlib.redirect_stdout(io.StringIO()) as out:
            rc = film.main()
        self.assertEqual(rc, 0, out.getvalue())
        return out.getvalue()

    def check(self):
        with mock.patch.object(sys, "argv", ["qa.py", "check"]), contextlib.redirect_stdout(io.StringIO()) as out:
            rc = qa.main()
        return rc, out.getvalue(), _env.read_json("qa/check.json"), _env.read_json("qa/film.check.json")

    def test_the_proof_lands_at_half_size_beside_the_films_and_the_films_are_untouched(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last full-size film")
        said = self.render("--proof")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(size("out/proof.mp4"), (540, 960))
        self.assertEqual(size("out/proof-16x9.mp4"), (960, 540))
        self.assertEqual(size("out/proof-square.mp4"), (540, 540))
        self.assertFalse(Path("out/film-16x9.mp4").exists())
        self.assertEqual(size("out/post.png"), (1080, 1080), "the posted image renders as the full render makes it")
        self.assertEqual(size("out/story.png"), (1080, 1920))
        self.assertEqual(size("frames/reel-closer.png"), (540, 960))
        self.assertIn("out/proof.mp4", said)
        self.assertIn("reading the half-size proof out/proof.mp4", said, "the render's own check reads the proof")
        self.assertIn("CHECKS GREEN", said)
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], proof.SCALE)
        self.assertEqual(proof.scale(), proof.SCALE)
        self.render()
        self.assertEqual(size("out/film.mp4"), (1080, 1920))
        self.assertEqual(proof.films("out"), [], "a full render takes the proof's films out of out/")
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], 1)
        self.assertEqual(proof.scale(), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.render("--proof")
        rc, said, proof_check, proof_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said.splitlines()[0])
        self.assertTrue(Path("qa/film-strip2.png").exists(), "the strips keep the film's names for the proof")
        self.render()
        rc, said, full_check, full_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        sizes = lambda c: [re.search(r": (\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "format"]
        self.assertEqual(sizes(proof_check), ["1080x1920", "1920x1080", "1080x1080"])
        self.assertEqual(sizes(proof_check), sizes(full_check))
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
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "format"], [False, False, False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_the_gate_reads_the_full_size_films_and_never_the_proof(self):
        self.render("--proof")
        res, _, _ = qa.film_checks()
        self.assertEqual([r[1] for r in res if r[0] == "format"], [False, False, False], "with no full-size film the gate is red")
        self.assertIn("out/film.mp4 is missing", [r[2] for r in res if r[0] == "format"][0])

    def test_a_round_on_the_proof_reads_its_frames_from_the_proof(self):
        self.render("--proof")
        got = vote.cut_frames(proof.newest(), Path("cut"))
        closer = next(g for g in got if g.startswith("closer-square"))
        self.assertEqual(size(Path("cut") / closer), (540, 540), "the square's closer comes from the square proof")
        self.assertEqual(size(Path("cut") / got[0]), (540, 960))


def fill(path, score=4):
    data = _env.read_json(path)
    for c in vote.CUT_PANEL:
        e = data["critics"][c]["boards"]["film"]
        e["scores"] = {k: score for k in vote.CRITERIA}
        e["paragraph"] = " ".join(["seen"] * 30)
    data["seen"] = list(data["frames"])
    if score < vote.BAR:
        data["lever"] = {"name": "closer.map", "change": "the closer holds the whole route a beat longer"}
    _env.write_json(path, data)


class Rounds(InARun):
    """A round on the proof reads the proof; once the full-size film of that cut is rendered, the round moves to it,
    its frames are cut again from the full-size film, and the critics read R3, the type, again there."""

    def setUp(self):
        super().setUp()
        Path("out").mkdir()
        _env.write_json("film.json", {"hash": "h"})
        _env.write_json("render/film-report.json", {"failed": 0})
        self.read = []
        cut = mock.patch.object(vote, "cut_frames", lambda film, into: self.read.append(str(film)) or ["first.jpg", "f01.jpg"])
        cut.start()
        self.addCleanup(cut.stop)

    def cut(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(vote.cmd_cut(None), 0)
        return out.getvalue()

    def verdict(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = vote.cmd_verdict(None)
        return rc, out.getvalue()

    def test_a_round_on_the_proof_moves_to_the_full_size_film_and_the_type_is_read_again(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        said = self.cut()
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said)
        self.assertEqual(self.read, ["out/proof.mp4"])
        first = _env.read_json("critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]), (qa.sha("out/proof.mp4"), proof.SCALE, "h"))
        fill("critic/cut-1.json", 5)
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("SHIP"), said)
        self.assertIn("film.py render", said, "a SHIP on the proof names the full-size render next")
        Path("out/proof.mp4").unlink()
        Path("out/film.mp4").write_bytes(b"the full-size film")
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("R3", said)
        self.assertEqual(self.read, ["out/proof.mp4", "out/film.mp4"], "the round's frames are cut again from the full-size film")
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json("critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"], moved["seen"]), (qa.sha("out/film.mp4"), 1, []))
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["R3"], "the type is read again on the full-size film")
            self.assertEqual({k: v for k, v in scores.items() if k != "R3"}, {k: 5 for k in vote.CRITERIA if k != "R3"})
        self.assertEqual(self.verdict()[0], 1, "the round waits for the type read at full size")
        fill("critic/cut-1.json", 5)
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("SHIP"), said)
        self.assertNotIn("film.py render", said)
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])

    def test_a_full_size_film_of_another_cut_opens_the_next_round(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.cut()
        fill("critic/cut-1.json", 3)
        Path("out/proof.mp4").unlink()
        Path("out/film.mp4").write_bytes(b"a film of another cut")
        _env.write_json("film.json", {"hash": "another"})
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_render(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.cut()
        fill("critic/cut-1.json", 3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("film.py render --proof", said)


class Deliver(InARun):
    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof_and_says_what_to_run(self):
        Path("out").mkdir()
        Path("out/proof.mp4").write_bytes(b"the proof")
        before = sorted(str(p) for p in Path(".").rglob("*"))
        with mock.patch.object(sys, "argv", ["deliver.py"]), mock.patch.object(_env, "tools", return_value={}), \
                self.assertRaises(SystemExit) as e:
            deliver.main()
        said = str(e.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof out/proof.mp4"), said)
        self.assertIn("film.py render", said)
        self.assertEqual(sorted(str(p) for p in Path(".").rglob("*") if not str(p).startswith("render")), before)


if __name__ == "__main__":
    unittest.main()
