"""The proof: every critic round before deliver reads the cut at half size. `film.py cut --proof` renders it beside the
cut (render/proof-cut.mp4), never over render/cut.mp4 or out/film.mp4, and the beats at rest the critics read come out
at the size the full cut gives them; qa.py check and vote.py cut read the newest cut and say so; a check that measures
pixels measures in board units, so a proof and a full cut of one board read the same; the critics' round on a proof
moves to the full-size cut with R3, the type, read again there; film.py render and deliver.py refuse a run whose
newest cut is the proof.

    python3 -I -m unittest discover -s S/tests -p test_proof.py
"""
import contextlib
import io
import json
import os
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
import boards  # noqa: E402
import chunks  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")

# render.py as studio.render calls it: every job is drawn at its board's size times its scale. A film is paper with a
# dark square that crosses it, and the paper turns at each beat's first frame, so the cuts and the move are drawn in
# board units and land at the same place of the frame at any scale; a still is the paper at the job's size.
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[2]))
ff = os.environ["FAKE_FFMPEG"]
for job in spec["jobs"]:
    fmt = job["props"]["board"]["format"]
    s = job.get("scale") or 1
    w, h = round(fmt["width"] * s), round(fmt["height"] * s)
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if job["type"] == "video":
        a, b = job["frameRange"]
        t = f"(t+{a}/30)"
        side = round(300 * s)
        graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},1)',"
                 f"drawbox=x=0:y=0:w={w}:h={h}:color=0x3a6a40:t=fill:enable='gte({t},2)'[paper];"
                 f"[paper][1]overlay=x='{s}*(100+250*{t})':y={round(700 * s)},format=yuv420p")
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30",
                        "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                        "-frames:v", str(b - a + 1), "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high",
                        job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}", "-frames:v", "1",
                        job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""

FRAMES = 90
BEATS = [{"id": "a", "frames": 30, "layers": [{"kind": "Photo", "at": 0.0}]},
         {"id": "b", "frames": 30, "layers": [{"kind": "Photo", "at": 0.0}]},
         {"id": "c", "frames": 30, "layers": [{"kind": "Photo", "at": 0.0}]}]
BOARD = {"bpm": 120, "format": {"width": 1080, "height": 1920}, "beats": BEATS, "effects": {}}
FILM = {"style": "drive", "bpm": 120, "storyboard": {"people": ["ana"], "beats": [{"person": "ana"}], "cards": {}}}


def score(path, value=5):
    data = _env.read_json(path)
    for critic in data["critics"].values():
        critic["boards"]["film"] = {"scores": {k: value for k in vote.CRITERIA},
                                    "paragraph": " ".join(["each beat lands on the cut and the type reads at a glance"] * 3)}
    _env.write_json(path, data)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.root, True)
        fake = self.root / "render.py"
        fake.write_text(FAKE)
        drawn = self.root / "dist"
        drawn.mkdir()
        (drawn / "bundle.js").write_text("export const Film = 1;\n")
        self.run_dir = self.root / "build" / "20260101T000000Z"
        self.run_dir.mkdir(parents=True)
        (self.root / "build" / "current").write_text(self.run_dir.name + "\n")
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        tools = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(_env, "WORKSPACE", self.root),
                      mock.patch.object(studio, "SOURCES", (drawn,)), mock.patch.object(studio, "DIST", drawn),
                      mock.patch.object(studio, "RENDERER", fake), mock.patch.object(chunks, "GPU", False),
                      mock.patch.object(studio, "props", lambda b: {"board": b, "clips": []}),
                      mock.patch.object(film, "board_for", lambda f, ctx, kind: _env.write_json(f"render/board-{kind}.json", BOARD) or BOARD),
                      mock.patch.object(boards, "Ctx", lambda: types.SimpleNamespace(people=[])),
                      mock.patch.object(film, "mux", self.mux), mock.patch.object(film, "cue_tiles", lambda *a, **k: None),
                      mock.patch.object(storyboard, "problems", lambda *a, **k: []),
                      mock.patch.object(qa, "LENGTH", (1, 30)),
                      mock.patch.dict(os.environ, {"FAKE_FFMPEG": FFMPEG, "MPR_WORKSPACE": str(self.root)})):
            patch.start()
            self.addCleanup(patch.stop)
        os.environ.pop("MPR_RUN", None)
        _env.write_json("film.json", FILM)

    @staticmethod
    def mux(run, silent, out, seconds, board):
        """The cut's picture as the cut: no music and no effects in this run."""
        shutil.copyfile(silent, out)
        return {"effects": 0, "fx_lufs": -40.0, "music": False}

    def main(self, module, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", [f"{module.__name__}.py", *args]), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            try:
                rc = module.main()
            except SystemExit as e:
                rc = e.code
        os.chdir(self.run_dir)
        os.environ.pop("MPR_RUN", None)
        return rc, out.getvalue()

    def cut(self, *args):
        rc, said = self.main(film, "cut", *args)
        self.assertEqual(rc, 0, said)
        return said

    def check(self):
        rc, said = self.main(qa, "check")
        return rc, said, _env.read_json("qa/check.json")

    def size(self, path):
        p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                       "-of", "json", str(path)], capture_output=True, text=True).stdout)["streams"][0]
        return p["width"], p["height"]

    def test_the_proof_lands_at_half_size_beside_the_cut_and_the_cut_and_the_film_are_untouched(self):
        Path("render").mkdir(exist_ok=True)
        Path("out").mkdir()
        Path("render/cut.mp4").write_bytes(b"the last full-size cut")
        Path("out/film.mp4").write_bytes(b"the delivered reel")
        said = self.cut("--proof")
        self.assertEqual(Path("render/cut.mp4").read_bytes(), b"the last full-size cut", "a proof never writes over the cut")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the delivered reel", "a proof never writes over the film")
        self.assertEqual(self.size("render/proof-cut.mp4"), (540, 960))
        self.assertEqual(chunks._frames(types.SimpleNamespace(spawn=subprocess.run), FFPROBE, Path("render/proof-cut.mp4")), FRAMES)
        self.assertIn("render/proof-cut.mp4", said)
        self.assertEqual(_env.read_json("render/cut.json")["scale"], proof.SCALE)
        self.assertEqual(proof.scale(film.CUT), proof.SCALE)
        proof_rest = self.size("frames/01-a.png")
        self.cut()
        self.assertEqual(self.size("render/cut.mp4"), (1080, 1920))
        self.assertEqual(self.size("frames/01-a.png"), proof_rest, "the beats at rest come out at one size from either cut")
        self.assertFalse(Path("render/proof-cut.mp4").exists(), "a full cut takes the proof away")
        self.assertFalse(Path("render/proof-cut-silent.mp4").exists())
        self.assertEqual(_env.read_json("render/cut.json")["scale"], 1)
        self.assertEqual(proof.scale(film.CUT), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_cut(self):
        self.cut("--proof")
        proof_measured = _env.read_json("render/cut.json")["measure"]
        rc, said, proof_check = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof render/proof-cut.mp4"), said.splitlines()[0])
        self.cut()
        full_measured = _env.read_json("render/cut.json")["measure"]
        rc, said, full_check = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        size = lambda c: next(x["detail"].split()[0] for x in c["checks"] if x["check"] == "film")
        self.assertEqual(size(proof_check), "1080x1920")
        self.assertEqual(size(proof_check), size(full_check))
        for k in ("seconds", "frames", "cuts", "planned_cuts", "extra_scene_cuts", "seconds_under_half"):
            self.assertEqual(proof_measured[k], full_measured[k], k)
        for a, b in zip(proof_measured["luma"], full_measured["luma"]):
            self.assertAlmostEqual(a, b, delta=0.25)
        self.assertEqual(proof_measured["strip"], full_measured["strip"], "the strips carry one name for either cut")

    def test_a_proof_the_size_of_the_cut_fails_the_film_check(self):
        self.cut()
        shutil.copyfile("render/cut.mp4", "render/proof-cut.mp4")
        info = _env.read_json("render/cut.json")
        _env.write_json("render/cut.json", dict(info, scale=proof.SCALE, film=film.file_sha("render/proof-cut.mp4")))
        rc, said, check = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "film"], [False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_the_round_on_the_proof_moves_to_the_full_cut_and_the_type_is_read_again(self):
        self.cut("--proof")
        rc, said = self.main(vote, "cut")
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof"), said)
        r1 = _env.read_json("critic/cut-1.json")
        self.assertEqual(r1["scale"], proof.SCALE)
        self.assertEqual(r1["film"], film.file_sha("render/proof-cut.mp4"))
        score("critic/cut-1.json")
        rc, said = self.main(vote, "verdict")
        self.assertIn("film.py cut", said)
        self.assertIn("full size", said)
        rc, said = self.main(film, "render")
        self.assertNotEqual(rc, 0)
        self.assertIn("half-size proof", str(rc) + said)
        self.cut()
        rc, said = self.main(vote, "cut")
        self.assertEqual(rc, 0, said)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the full cut of the proof's board keeps its round")
        r1 = _env.read_json("critic/cut-1.json")
        self.assertEqual(r1["film"], film.file_sha("render/cut.mp4"))
        self.assertEqual(r1["scale"], 1)
        for c in vote.CUT_PANEL:
            scores = r1["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["R3"], "the type is read again on the full-size cut")
            self.assertEqual({k for k, v in scores.items() if v == 5}, set(vote.CRITERIA) - {"R3"})
        self.assertFalse(vote.scored(r1["film"])[0])
        score("critic/cut-1.json")
        self.assertTrue(vote.scored(r1["film"])[0])
        rc, said = self.main(vote, "verdict")
        self.assertIn("AT THE BAR", said)
        self.assertNotIn("film.py cut", said)

    def test_deliver_refuses_a_run_whose_newest_cut_is_the_proof(self):
        self.cut("--proof")
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the reel of an earlier full cut")
        _env.write_json("cards.json", {"cards": []})
        rc, said = self.main(deliver)
        self.assertIsInstance(rc, str)
        self.assertTrue(rc.startswith("not delivered: the newest render is the half-size proof render/proof-cut.mp4"), rc)
        self.assertIn("film.py cut", rc)
        self.assertFalse(Path("out/review.html").exists(), "a refused deliver writes nothing into out/")


if __name__ == "__main__":
    unittest.main()
