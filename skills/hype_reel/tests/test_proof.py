"""The proof: every critic round before the last reads the cut at half size (film.py cut --proof, proof.silent.mp4),
never over film.silent.mp4 or out/film.mp4; the checks of a proof measure in board units, so a proof and a full cut of
one film.json read the same; the critics' round on a proof moves to the full-size cut with its type read again there;
film.py render and deliver.py refuse a run whose newest cut is the proof.

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
import chunks  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
PROOF = proof.of(film.SILENT)
WHY = "the read of this cut written in at least eight words"

# render.py as _env.render calls it: a film is drawn at 1080x1920 times its job's scale. It is paper with a dark square
# crossing it, a dark band lands at frame 6 (the hook) and the paper turns at the film's second second (the cut), all
# placed in board units, so they land at the same place of the frame and on the same frame at any scale.
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
        graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},1)',"
                 f"drawbox=x=0:y={round(1300 * s)}:w={w}:h={round(400 * s)}:color=0x1a1410:t=fill:enable='gte({t},0.2)'[paper];"
                 f"[paper][1]overlay=x='{s}*(100+300*{t})':y={round(700 * s)},format=yuv420p")
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30",
                        "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                        "-frames:v", str(b - a + 1), "-c:v", "libx264", "-profile:v", "high", "-preset", "veryfast", job["out"]],
                       check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}", "-frames:v", "1",
                        job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""

TIMELINE = [{"id": "hook", "start": 0, "frames": 30, "start_s": 0.0, "seconds": 1.0},
            {"id": "closer", "start": 30, "frames": 30, "start_s": 1.0, "seconds": 1.0}]


class Run(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.run_dir = self.dir / "build" / "r1"
        self.run_dir.mkdir(parents=True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        tools = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(_env, "RENDERER", fake),
                      mock.patch.object(_env, "ROOT", self.dir), mock.patch.object(chunks, "GPU", False),
                      mock.patch.object(storyboard, "refuse_flagged", lambda boards: None),
                      mock.patch.object(qa, "board_checks", lambda board, check: check("board", True, "0 findings")),
                      mock.patch.object(qa, "LENGTH", (1, 25)),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG, LH_ROOT=str(self.dir), LH_RUN=str(self.run_dir))):
            patch.start()
            self.addCleanup(patch.stop)
        _env.write_json("film.json", {"timeline": TIMELINE, "seconds": 2.0, "bpm": 120, "beats": [], "system": {"finish": {}}})

    def cmd(self, mod, *argv):
        with mock.patch.object(sys, "argv", [f"{mod.__name__}.py", *argv]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            try:
                rc = mod.main()
            except SystemExit as e:
                rc = e.code
        return rc, out.getvalue()

    def size(self, mp4):
        p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                       "-of", "json", str(mp4)], capture_output=True, text=True).stdout)["streams"][0]
        return p["width"], p["height"]

    def fill(self, round_file, score=5):
        """The round filled in: every score not yet given at `score`, a paragraph each, and every read passing."""
        data = _env.read_json(round_file)
        for c in vote.CUT_PANEL:
            e = data["critics"][c]["boards"]["film"]
            e["scores"] = {k: score if v is None else v for k, v in e["scores"].items()}
            e["paragraph"] = " ".join(["word"] * 30)
        data["reads"] = {k: {"pass": True, "why": WHY} for k in vote.READS}
        if not data["sound"]["cited"]:
            data["sound"]["cited"] = ("The bed reads at its level, the drop lands on its cut, and the hits stand over the "
                                      "bed as the sound read's table says.")
        _env.write_json(round_file, data)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Cut(Run):
    def test_the_proof_lands_at_half_size_in_its_place_and_the_films_are_untouched(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last full-size film")
        film.SILENT.write_bytes(b"the last full-size cut")
        rc, said = self.cmd(film, "cut", "--proof")
        self.assertEqual(rc, 0, said)
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(film.SILENT.read_bytes(), b"the last full-size cut", "a proof never writes over the cut")
        self.assertEqual(self.size(PROOF), (540, 960))
        self.assertEqual(chunks._frames(types.SimpleNamespace(spawn=subprocess.run), FFPROBE, PROOF), 60)
        self.assertIn(str(PROOF), said)
        self.assertIn("half-size proof", said)
        self.assertEqual(_env.read_json("cut.json")["scale"], proof.SCALE)
        self.assertEqual(_env.read_json("render/cut-report.json")["scale"], proof.SCALE)
        self.assertTrue(Path("frames/film-strip.png").exists())
        self.assertEqual(proof.scale(film.SILENT), proof.SCALE)
        rc, said = self.cmd(film, "cut")
        self.assertEqual(rc, 0, said)
        self.assertEqual(self.size(film.SILENT), (1080, 1920))
        self.assertFalse(PROOF.exists(), "a full-size cut takes the proof's place")
        self.assertEqual(_env.read_json("cut.json")["scale"], 1)
        self.assertEqual(_env.read_json("render/cut-report.json")["scale"], 1)
        self.assertEqual(proof.scale(film.SILENT), 1)

    def test_the_checks_of_the_proof_and_the_full_cut_of_one_film_json_read_the_same_in_board_units(self):
        rc, said = self.cmd(film, "cut", "--proof")
        self.assertEqual(rc, 0, said)
        on_proof = _env.read_json("qa/cut.json")
        rc, said = self.cmd(qa, "check", "--film", str(film.SILENT))
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith(f"reading the half-size proof {PROOF}"), said.splitlines()[0])
        rc, said = self.cmd(film, "cut")
        self.assertEqual(rc, 0, said)
        on_full = _env.read_json("qa/cut.json")
        rc, said = self.cmd(qa, "check", "--film", str(film.SILENT))
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertTrue(on_proof["pass"], on_proof)
        self.assertEqual(rows(on_proof), rows(on_full))
        size = lambda c: [re.match(r"(\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "film"]
        self.assertEqual(size(on_proof), ["1080x1920"])
        self.assertEqual(size(on_proof), size(on_full))
        self.assertEqual(on_proof["hook_frame"], on_full["hook_frame"])
        for k in ("cuts", "planned_cuts", "scene_cuts"):
            self.assertEqual(on_proof["cuts"][k], on_full["cuts"][k], k)
        self.assertEqual(on_proof["still"]["seconds_under_half"], on_full["still"]["seconds_under_half"])
        for a, b in zip(on_proof["still"]["per_second"], on_full["still"]["per_second"]):
            self.assertAlmostEqual(a, b, delta=0.5)

    def test_a_proof_the_size_of_the_cut_fails_the_film_check(self):
        rc, said = self.cmd(film, "cut")
        self.assertEqual(rc, 0, said)
        shutil.copyfile(film.SILENT, PROOF)
        rc, said = self.cmd(qa, "check", "--film", str(film.SILENT))
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in _env.read_json("qa/cut.json")["checks"] if x["check"] == "film"], [False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")


class Rounds(Run):
    def cut(self, scale):
        """A cut of the current film.json at `scale`, as film.py cut leaves it."""
        PROOF.unlink(missing_ok=True)
        (PROOF if scale != 1 else film.SILENT).write_bytes(b"cut")
        _env.write_json("cut.json", {"film": film.film_hash(), "scale": scale})

    def test_the_round_on_the_proof_moves_to_the_full_cut_with_its_type_read_again(self):
        self.cut(proof.SCALE)
        rc, said = self.cmd(vote, "cut")
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith(f"reading the half-size proof {PROOF}"), said)
        self.assertIn("half-size proof", film.ready() or "", "film.py render waits for the full-size cut")
        f = Path("critic/cut-1.json")
        self.assertEqual(_env.read_json(f)["scale"], proof.SCALE)
        self.fill(f)
        rc, said = self.cmd(vote, "verdict")
        self.assertEqual(rc, 0, said)
        self.assertIn("SHIP", said)
        self.assertIn("film.py cut", said.split("SHIP", 1)[1], "a ship on the proof names the full-size cut")
        self.cut(1)
        rc, said = self.cmd(vote, "cut")
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertEqual(vote.rounds(), [f], "the full-size cut keeps the proof's round")
        data = _env.read_json(f)
        self.assertEqual(data["scale"], 1)
        for c in vote.CUT_PANEL:
            scores = data["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["type"], "the critics read the type again at full size")
            self.assertEqual({k: v for k, v in scores.items() if k != "type"}, {k: 5 for k in vote.CRITERIA if k != "type"})
        self.assertTrue(all(r["pass"] for r in data["reads"].values()), "the reads stand")
        self.assertIn("not filled in", film.ready())
        self.fill(f)
        self.assertIsNone(film.ready())
        rc, said = self.cmd(vote, "verdict")
        self.assertEqual(rc, 0, said)
        self.assertNotIn("film.py cut", said)

    def test_a_fix_on_the_proof_cuts_the_proof_again(self):
        self.cut(proof.SCALE)
        self.cmd(vote, "cut")
        self.fill(Path("critic/cut-1.json"), score=3)
        rc, said = self.cmd(vote, "verdict")
        self.assertEqual(rc, 2, said)
        self.assertIn("film.py cut --proof", said)

    def test_deliver_refuses_a_run_whose_newest_cut_is_the_proof(self):
        self.cut(proof.SCALE)
        Path("out").mkdir()
        Path("out/review.html").write_text("the last page")
        with mock.patch.object(sys, "argv", ["deliver.py"]), self.assertRaises(SystemExit) as e:
            deliver.main()
        self.assertTrue(str(e.exception.code).startswith(f"not delivered: the newest render is the half-size proof {PROOF}"),
                        e.exception.code)
        self.assertIn("film.py cut", str(e.exception.code))
        self.assertEqual(Path("out/review.html").read_text(), "the last page", "a refused deliver changes nothing")


class Names(unittest.TestCase):
    def test_the_proof_of_the_cut_sits_beside_it(self):
        self.assertEqual(PROOF, Path("proof.silent.mp4"))

    def test_a_run_made_from_a_filmed_one_never_carries_its_proof(self):
        self.assertIn(str(PROOF), storyboard.FILMED)


if __name__ == "__main__":
    unittest.main()
