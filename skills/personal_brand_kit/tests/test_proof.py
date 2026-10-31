"""The proof: every critic round before deliver watches the timed cut at half size, film.py cut --proof, which lands
beside the cut as proof-cut.mp4 and never over cut.mp4 or out/film.mp4; qa.py check and vote.py cut read the newest
cut and say so when it is the proof; a check that measures pixels measures in board units, so a proof and a full-size
cut of one film read the same; the critics' round on a proof moves to the full-size cut with its type read again
there; film.py render and deliver.py refuse while the newest cut is the proof.

    python3 -I -m unittest discover -s tests -p test_proof.py
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
PROOF = Path("proof-cut.mp4")

# render.py as studio.render calls it: every job is drawn at its board's size times its scale. A film is paper with a
# dark square that crosses it, and the paper turns at the film's first second, so the cut and the move are drawn in
# board units and land at the same place of the frame at any scale; a still is the paper at the job's size.
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[2]))
ff = os.environ["FAKE_FFMPEG"]
for job in spec["jobs"]:
    fmt = job["props"]["board"].get("format") or {}
    s = job.get("scale") or 1
    w, h = round(fmt.get("width", 1080) * s), round(fmt.get("height", 1920) * s)
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if job["type"] == "video":
        a, b = job["frameRange"]
        t = f"(t+{a}/30)"
        side = round(300 * s)
        graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},1)'[paper];"
                 f"[paper][1]overlay=x='{s}*(100+300*{t})':y={round(700 * s)},format=yuv420p")
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xc8b89a:s={w}x{h}:r=30",
                        "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                        "-frames:v", str(b - a + 1), "-c:v", "libx264", "-preset", "ultrafast", job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xc8b89a:s={w}x{h}", "-frames:v", "1",
                        job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""

FRAMES = 60
BEATS = [{"id": "hook", "frames": 30, "rest": 5}, {"id": "closer", "frames": 30, "rest": 20}]


def silent_mux(run, silent, out, seconds, board):
    """The film without its sound: the checks below read the picture, and with no music.json the audio row is not held."""
    shutil.copyfile(silent, out)
    return False


class InRun(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.run_dir = self.dir / "run"
        (self.run_dir / "out").mkdir(parents=True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        for patch in (mock.patch.dict(os.environ, BRAND_RUN=str(self.run_dir)),
                      mock.patch.object(_env, "tools", return_value={"python": sys.executable, "ffmpeg": FFMPEG,
                                                                     "ffprobe": FFPROBE, "chromium": "chrome", "dist": True})):
            patch.start()
            self.addCleanup(patch.stop)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(InRun):
    def setUp(self):
        super().setUp()
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        src = self.dir / "dist"
        src.mkdir()
        (src / "bundle.js").write_text("export const Film = 1;\n")
        pub = self.dir / "public"
        pub.mkdir()
        for patch in (mock.patch.object(studio, "SOURCES", (src,)), mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(studio, "public", return_value=pub), mock.patch.object(chunks, "GPU", False),
                      mock.patch.object(film, "mux", silent_mux), mock.patch.object(storyboard, "LENGTH", (1, 30)),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG)):
            patch.start()
            self.addCleanup(patch.stop)
        sizes = {"reel": (1080, 1920), "square": (1080, 1080), "wide": (1920, 1080)}
        for name, (w, h) in sizes.items():
            _env.write_json(f"boards/{name}.json", {"id": name, "beats": BEATS, "bpm": 120,
                                                    "format": {"name": name, "width": w, "height": h}})
        _env.write_json("film.json", {"hash": "h", "name": "Kinetic type", "board": "a", "style": "kinetic-type", "bpm": 120,
                                      "seconds": FRAMES / 30, "cuts": [1.0], "hook_frame": 4, "findings": [],
                                      "boards": {k: f"boards/{k}.json" for k in sizes},
                                      "rests": {k: {"hook": 5, "peak": 40, "closer": 50} for k in sizes}})

    def cut(self, *args):
        with mock.patch.object(sys, "argv", ["film.py", "cut", *args]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(film.main(), 0)
        return out.getvalue()

    def size(self, mp4):
        p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                       "-of", "json", str(mp4)], capture_output=True, text=True).stdout)["streams"][0]
        return p["width"], p["height"]

    def check(self):
        with mock.patch.object(sys, "argv", ["qa.py", "check"]), contextlib.redirect_stdout(io.StringIO()) as out:
            rc = qa.main()
        return rc, out.getvalue(), _env.read_json("qa/check.json"), _env.read_json("cut.json")["measured"]

    def test_the_proof_lands_at_half_size_beside_the_cut_and_the_films_are_untouched(self):
        Path("cut.mp4").write_bytes(b"the last full-size cut")
        Path("out/film.mp4").write_bytes(b"the last full-size film")
        said = self.cut("--proof")
        self.assertEqual(Path("cut.mp4").read_bytes(), b"the last full-size cut", "a proof never writes over the cut")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(self.size(PROOF), (540, 960))
        self.assertEqual(chunks._frames(PLAIN, FFPROBE, PROOF), FRAMES)
        self.assertIn(str(PROOF), said)
        self.assertEqual(sorted(p.name for p in Path(".").glob("cut-strip*")), ["cut-strip.png", "cut-strip12.jpg"])
        c = _env.read_json("cut.json")
        self.assertEqual((c["file"], c["sha"], c["scale"]), (str(PROOF), qa.sha(PROOF), proof.SCALE))
        self.assertEqual(_env.read_json(studio.report_of("proof"))["scale"], proof.SCALE)
        self.assertEqual(proof.scale("cut.mp4"), proof.SCALE)
        self.cut()
        self.assertEqual(self.size("cut.mp4"), (1080, 1920))
        self.assertFalse(PROOF.exists(), "a full-size cut takes the proof away")
        self.assertEqual(_env.read_json("cut.json")["scale"], 1)
        self.assertEqual(_env.read_json(studio.report_of("cut"))["scale"], 1)
        self.assertEqual(proof.scale("cut.mp4"), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_size_cut(self):
        self.cut("--proof")
        rc, said, proof_check, proof_measured = self.check()
        self.assertTrue(said.startswith(f"reading the half-size proof {PROOF}"), said.splitlines()[0])
        self.assertEqual(proof_check["film"], qa.sha(PROOF))
        self.cut()
        full_rc, said, full_check, full_measured = self.check()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertEqual(full_check["film"], qa.sha("cut.mp4"))
        self.assertEqual(rc, full_rc)
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        for name in ("film", "black", "frozen", "white", "safe", "hook"):
            self.assertIn((name, True), rows(proof_check), name)
        sizes = lambda c: [re.search(r": (\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "film"]
        self.assertEqual(sizes(proof_check), ["1080x1920"])
        self.assertEqual(sizes(proof_check), sizes(full_check))
        for k in ("seconds", "frames", "cuts", "planned_cuts", "extra_scene_cuts", "seconds_under_half"):
            self.assertEqual(proof_measured[k], full_measured[k], k)
        for a, b in zip(proof_measured["luma"], full_measured["luma"]):
            self.assertAlmostEqual(a, b, delta=0.25)

    def test_a_proof_the_size_of_the_cut_fails_the_film_check(self):
        self.cut()
        shutil.copyfile("cut.mp4", PROOF)
        rc, said, check, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "film"], [False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_render_refuses_while_the_newest_cut_is_the_proof(self):
        self.cut()
        self.cut("--proof")
        why = film.ready()
        self.assertTrue(why.startswith(f"the newest cut is the half-size proof {PROOF}"), why)
        self.assertIn("film.py cut", why)


class Rounds(InRun):
    """A round on the proof reads the proof; once the full-size cut of that film is made, the round moves to it and
    the critics read its type again at full size."""

    def setUp(self):
        super().setUp()
        _env.write_json("film.json", {"hash": "h"})
        Path("cut.json").write_text("{}")

    def made(self, path, data):
        """A cut at `path` with qa.py check run on it."""
        Path(path).write_bytes(data)
        _env.write_json("qa/check.json", {"film": qa.sha(path), "checks": []})

    def cut(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(vote.cmd_cut(None), 0)
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
            rc = vote.cmd_verdict(None)
        return rc, out.getvalue()

    def test_a_round_on_the_proof_moves_to_the_full_size_cut_and_the_type_is_read_again(self):
        self.made(PROOF, b"the proof")
        said = self.cut()
        self.assertTrue(said.startswith(f"reading the half-size proof {PROOF}"), said)
        self.assertIn(str(PROOF), said.splitlines()[-1])
        first = _env.read_json("critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]), (qa.sha(PROOF), proof.SCALE, "h"))
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("SHIP"), said)
        self.assertIn("film.py cut, qa.py check", said, "a SHIP on the proof names the full-size cut next")
        PROOF.unlink()
        self.made("cut.mp4", b"the full-size cut")
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("type", said)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json("critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"], moved["proof_film"]), (qa.sha("cut.mp4"), 1, first["film"]))
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["type"], "the type is read again on the full-size cut")
            self.assertEqual({k: v for k, v in scores.items() if k != "type"}, {k: 5 for k in vote.CRITERIA if k != "type"})
        self.assertEqual(self.verdict()[0], 1, "the round waits for the type read at full size")
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertEqual(said.strip(), "SHIP: round 1, mean 5.00, lowest 5: at the bar")
        self.assertEqual(_env.read_json("critic/verdict.json")["film"], qa.sha("cut.mp4"), "the verdict film.py render reads")
        self.assertIn("round 1 is this cut's", self.cut())
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])

    def test_a_full_size_cut_of_another_film_opens_the_next_round(self):
        self.made(PROOF, b"the proof")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        PROOF.unlink()
        self.made("cut.mp4", b"a cut of another film")
        _env.write_json("film.json", {"hash": "another"})
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_cut(self):
        self.made(PROOF, b"the proof")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("film.py cut --proof", said)


class Deliver(InRun):
    def test_deliver_refuses_a_run_whose_newest_cut_is_the_proof_and_says_what_to_run(self):
        Path("cut.mp4").write_bytes(b"an older full-size cut")
        PROOF.write_bytes(b"the proof")
        before = sorted(str(p) for p in Path(".").rglob("*"))
        with mock.patch.object(sys, "argv", ["deliver.py"]), self.assertRaises(SystemExit) as e:
            deliver.main()
        said = str(e.exception.code)
        self.assertTrue(said.startswith(f"not delivered: the newest render is the half-size proof {PROOF}"), said)
        self.assertIn("film.py cut for the full-size cut", said)
        self.assertEqual(sorted(str(p) for p in Path(".").rglob("*") if p.name not in ("render.lock", "render")), before)


class CutSet(unittest.TestCase):
    def test_a_new_cut_takes_the_proof_and_its_report_with_the_rest_of_the_cut(self):
        self.assertIn(PROOF, storyboard.CUT_SET)
        self.assertIn(studio.report_of("proof"), storyboard.CUT_SET)


if __name__ == "__main__":
    unittest.main()
