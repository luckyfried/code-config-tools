"""The proof: every round before deliver renders the reel at half size beside the film in out/ (out/proof.mp4), never
over out/film.mp4, with the cards, the stories and the strip as the full render makes them; qa.py check and vote.py cut
read the newest render and say so; a check that measures pixels measures in board units, so a proof and a full render
of one cut read the same; the critics' round on a proof moves to the full-size film with its type read again there;
deliver.py refuses a run whose newest render is the proof.

    python3 -I -m unittest discover -s S/tests -p test_proof.py
"""
import argparse
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
import chunks  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
PLAIN = types.SimpleNamespace(spawn=subprocess.run)
OUT = Path("../out")

# render.py as studio.render calls it: every job is drawn at the reel's size times its scale. A film is paper with a
# dark square that crosses it, and the paper turns at the film's first second, so the cut and the move are drawn in
# board units and land at the same place of the frame at any scale; a still is the paper at the job's size.
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[2]))
ff = os.environ["FAKE_FFMPEG"]
for job in spec["jobs"]:
    s = job.get("scale") or 1
    w, h = round(1080 * s), round(1920 * s)
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if job["type"] == "video":
        a, b = job["frameRange"]
        t = f"(t+{a}/30)"
        side = round(300 * s)
        graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},1)'[paper];"
                 f"[paper][1]overlay=x='{s}*(100+300*{t})':y={round(700 * s)},format=yuv420p")
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30",
                        "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                        "-frames:v", str(b - a + 1), "-c:v", "libx264", "-preset", "ultrafast", job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}", "-frames:v", "1",
                        job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""

FRAMES = 60


def silent_mux(run, silent, out, seconds, board=None):
    """film.mux with no music: the film is the silent picture."""
    shutil.copyfile(silent, out)
    return False


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        src = self.dir / "src"
        src.mkdir()
        (src / "film.tsx").write_text("export const Film = 1;\n")
        build = self.dir / "build"
        build.mkdir()
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(build)
        tools = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(_env, "enter_build"),
                      mock.patch.object(studio, "SOURCES", (src,)), mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(chunks, "GPU", False), mock.patch.object(storyboard, "LENGTH", (1, 90)),
                      mock.patch.object(film, "mux", silent_mux),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG)):
            patch.start()
            self.addCleanup(patch.stop)
        months = [{"id": f"m{n:02d}", "month": n, "peak": n == 7, "at": {"pull": [2]}} for n in range(1, 13)]
        _env.write_json("storyboards/a/board-reel.json", {"bpm": 120, "beats": [], "sound": [], "year": {"months": months}})
        _env.write_json("film.json", {"hash": "h", "frames": FRAMES, "seconds": FRAMES / 30, "cuts": [1.0], "hook_frame": 4,
                                      "boards": {"reel": "storyboards/a/board-reel.json"},
                                      "rests": {"reel": {"hook": 1, "month": 20, "closer": 50}}, "findings": []})
        _env.write_json("qa/timed.json", {"hash": "h", "pass": True})

    def render(self, *args):
        with mock.patch.object(sys, "argv", ["film.py", "render", *args]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(film.main(), 0)
        return out.getvalue()

    def size(self, mp4):
        p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                       "-of", "json", str(mp4)], capture_output=True, text=True).stdout)["streams"][0]
        return p["width"], p["height"]

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with mock.patch.object(sys, "argv", ["qa.py", "check"]):
                rc = qa.main()
        return rc, out.getvalue(), _env.read_json("qa/check.json"), _env.read_json("qa/film.check.json")

    def test_the_proof_lands_at_half_size_beside_the_film_and_the_film_is_untouched(self):
        OUT.mkdir()
        (OUT / "film.mp4").write_bytes(b"the last full-size film")
        said = self.render("--proof")
        self.assertEqual((OUT / "film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(self.size(OUT / "proof.mp4"), (540, 960))
        self.assertEqual(chunks._frames(PLAIN, FFPROBE, OUT / "proof.mp4"), FRAMES)
        self.assertIn("out/proof.mp4", said)
        self.assertIn("half-size proof", said)
        self.assertEqual(len(list((OUT / "carousel").glob("*.png"))), 10, "the cards render as the full render makes them")
        self.assertEqual({qa.png_size(p) for p in (OUT / "carousel").glob("*.png")}, {(1080, 1350)})
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], proof.SCALE)
        self.assertEqual(proof.scale(OUT / "film.mp4"), proof.SCALE)
        self.render()
        self.assertEqual(self.size(OUT / "film.mp4"), (1080, 1920))
        self.assertEqual(proof.films(OUT), [], "a full render takes the proof out of out/")
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], 1)
        self.assertEqual(proof.scale(OUT / "film.mp4"), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.render("--proof")
        rc, said, proof_check, proof_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said.splitlines()[0])
        self.render()
        rc, said, full_check, full_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        sizes = lambda c: [re.search(r": (\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "format"]
        self.assertEqual(sizes(proof_check), ["1080x1920"])
        self.assertEqual(sizes(proof_check), sizes(full_check))
        for k in ("seconds", "frames", "cuts", "planned_cuts", "extra_scene_cuts", "seconds_under_half", "strip", "strip2"):
            self.assertEqual(proof_measured[k], full_measured[k], k)
        for a, b in zip(proof_measured["luma"], full_measured["luma"]):
            self.assertAlmostEqual(a, b, delta=0.25)

    def test_a_proof_the_size_of_the_film_fails_the_format_check(self):
        self.render()
        shutil.copyfile(OUT / "film.mp4", OUT / "proof.mp4")
        rc, said, check, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "format"], [False],
                         "a proof is held to half the reel's size: a full-size picture in its place is the wrong size")

    def test_the_gate_reads_the_full_size_film_and_never_the_proof(self):
        self.render("--proof")
        res, _, _ = qa.film_checks()
        self.assertEqual([r[1] for r in res if r[0] == "format"], [False], "with no full-size film the gate is red")
        self.assertIn("film.mp4 is missing", [r[2] for r in res if r[0] == "format"][0])


class Rounds(unittest.TestCase):
    """A round on the proof reads the proof; once the full-size film of that cut is rendered, the round moves to it and
    the critics read its type again at full size."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        (self.dir / "build").mkdir()
        os.chdir(self.dir / "build")
        OUT.mkdir()
        _env.write_json("film.json", {"hash": "h"})
        _env.write_json("render/film-report.json", {"failed": 0, "hash": "h"})

    def cut(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(vote.cmd_cut(argparse.Namespace()), 0)
        return out.getvalue()

    def fill(self, path, score=5):
        data = _env.read_json(path)
        for c in vote.CUT_PANEL:
            e = data["critics"][c]["boards"]["film"]
            e["scores"] = {k: score for k in vote.CRITERIA}
            e["paragraph"] = " ".join(["seen"] * 30)
        _env.write_json(path, data)

    def verdict(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = vote.cmd_verdict(argparse.Namespace())
        return rc, out.getvalue()

    def test_a_round_on_the_proof_moves_to_the_full_size_film_and_the_type_is_read_again(self):
        (OUT / "proof.mp4").write_bytes(b"the proof")
        said = self.cut()
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said)
        first = _env.read_json("critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]), (qa.sha(OUT / "proof.mp4"), proof.SCALE, "h"))
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertIn("film.py render", said, "a SHIP on the proof names the full-size render next")
        (OUT / "proof.mp4").unlink()
        (OUT / "film.mp4").write_bytes(b"the full-size film")
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("type", said)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json("critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"]), (qa.sha(OUT / "film.mp4"), 1))
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["type"], "the type is read again on the full-size film")
            self.assertEqual({k: v for k, v in scores.items() if k != "type"}, {k: 5 for k in vote.CRITERIA if k != "type"})
        self.assertEqual(self.verdict()[0], 1, "the round waits for the type read at full size")
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("SHIP"), said)
        self.assertNotIn("film.py render", said)
        self.assertEqual(self.cut().count("round 1"), 1)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])

    def test_a_full_size_film_of_another_cut_opens_the_next_round(self):
        (OUT / "proof.mp4").write_bytes(b"the proof")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        (OUT / "proof.mp4").unlink()
        (OUT / "film.mp4").write_bytes(b"a film of another cut")
        _env.write_json("film.json", {"hash": "another"})
        _env.write_json("render/film-report.json", {"failed": 0, "hash": "another"})
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_render(self):
        (OUT / "proof.mp4").write_bytes(b"the proof")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("film.py render --proof", said)


class Deliver(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        (self.dir / "build").mkdir()
        os.chdir(self.dir / "build")

    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof_and_says_what_to_run(self):
        OUT.mkdir()
        (OUT / "proof.mp4").write_bytes(b"the proof")
        before = sorted(str(p) for p in self.dir.rglob("*"))
        with mock.patch.object(sys, "argv", ["deliver.py"]), mock.patch.object(_env, "enter_build"), \
                mock.patch.object(_env, "tools", return_value={}), self.assertRaises(SystemExit) as e:
            deliver.main()
        said = str(e.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof out/proof.mp4"), said)
        self.assertIn("film.py render", said)
        self.assertEqual(sorted(str(p) for p in self.dir.rglob("*") if p.name not in ("render.lock", "render")), before)


if __name__ == "__main__":
    unittest.main()
