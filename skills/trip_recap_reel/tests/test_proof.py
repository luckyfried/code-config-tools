"""The proof: every round before deliver renders the films at half size beside the film in out/ (out/proof.mp4), never
over out/film.mp4, and qa.py check, film.py frames and vote.py cut read the newest render and say so; a check that
measures pixels measures in board units, so a proof and a full render of one cut read the same; the critics' round on
a proof moves to the full-size film with its type read again there; deliver.py refuses a run whose newest render is
the proof.

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
import studio  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")

# render.py as studio.render calls it: every job is drawn at its board's size times its scale. A film is a mid paper with
# a dark square that crosses it, and the paper turns at the film's first second, so the cut and the move are drawn in
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
        graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},1)'[paper];"
                 f"[paper][1]overlay=x='{s}*(100+300*{t})':y={round(400 * s)},format=yuv420p")
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x9a8a70:s={w}x{h}:r=30",
                        "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                        "-frames:v", str(b - a + 1), "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high",
                        job["out"]], check=True)
        json.dump([], open(job["out"][:-len(".mp4")] + ".findings.json", "w"))
    else:
        subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x9a8a70:s={w}x{h}", "-frames:v", "1",
                        job["out"]], check=True)
json.dump({"jobs": len(spec["jobs"]), "failed": 0, "findings": [], "seconds": 1}, open(spec["report"], "w"))
"""

FRAMES = 60


def board(width, height):
    return {"format": {"width": width, "height": height, "fps": 30}, "beats": [{"frames": FRAMES, "at": 0}], "bpm": 120,
            "seconds": FRAMES / 30, "cuts": [1.0], "rests": {"a": 10, "closer": 50}, "stories": [], "sound": [],
            "timeline": [{"id": "hook", "start": 0, "frames": 30, "bars": 1, "start_s": 0, "seconds": 1, "transition": None},
                         {"id": "closer", "start": 30, "frames": 30, "bars": 1, "start_s": 1, "seconds": 1, "transition": None}]}


class Run(unittest.TestCase):
    """A run folder, build/r1 under a scratch home, entered as every command enters it."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.run_dir = self.home / "build" / "r1"
        self.run_dir.mkdir(parents=True)
        (self.home / "build" / "RUN").write_text("r1\n")
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        for patch in (mock.patch.object(_env, "HOME", self.home), mock.patch.dict(os.environ, {"TR_RUN": ""})):
            patch.start()
            self.addCleanup(patch.stop)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(Run):
    def setUp(self):
        super().setUp()
        fake = self.home / "render.py"
        fake.write_text(FAKE)
        src = self.home / "src"
        src.mkdir()
        (src / "Film.tsx").write_text("export const Film = 1;\n")
        tools = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "SOURCES", (src,)),
                      mock.patch.object(studio, "RENDERER", fake), mock.patch.object(chunks, "GPU", False),
                      mock.patch.object(studio, "public", return_value=self.home / "public"),
                      mock.patch.object(film, "mux", self.mux),
                      mock.patch.object(qa, "board_check", return_value=(True, "the fixture's board")),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG)):
            patch.start()
            self.addCleanup(patch.stop)
        _env.write_json("film.json", board(1080, 1920))
        _env.write_json("film-square.json", board(1080, 1080))

    def mux(self, silent, out, seconds, f, run):
        os.replace(silent, out)
        return False

    def render(self, *args):
        with mock.patch.object(sys, "argv", ["film.py", "render", "--also", "square", *args]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
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
        return rc, out.getvalue(), _env.read_json("qa/check.json")

    def test_the_proof_lands_at_half_size_beside_the_film_and_the_film_is_untouched(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last full-size film")
        said = self.render("--proof")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(self.size("out/proof.mp4"), (540, 960))
        self.assertEqual(self.size("out/proof-square.mp4"), (540, 540))
        self.assertFalse(Path("out/film-square.mp4").exists())
        self.assertIn("out/proof.mp4", said)
        self.assertEqual(self.size("frames/reel-closer.png"), (540, 960), "the frames render as the full render makes them")
        self.assertEqual(self.size("out/cover.png"), (1080, 1920))
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], proof.SCALE)
        self.assertEqual(proof.scale(), proof.SCALE)
        self.render()
        self.assertEqual(self.size("out/film.mp4"), (1080, 1920))
        self.assertEqual(self.size("out/film-square.mp4"), (1080, 1080))
        self.assertEqual(proof.films("out"), [], "a full render takes the proof's films out of out/")
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], 1)
        self.assertEqual(proof.scale(), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.render("--proof")
        rc, said, proof_check = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said.splitlines()[0])
        self.assertEqual(proof_check["film"], qa.sha("out/proof.mp4"), "the check describes the film it read")
        self.render()
        rc, said, full_check = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        sizes = lambda c: [re.search(r"(\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] in ("film", "square")]
        self.assertEqual(sizes(proof_check), ["1080x1920", "1080x1080"])
        self.assertEqual(sizes(proof_check), sizes(full_check))
        a, b = proof_check["figures"], full_check["figures"]
        for k in ("cuts", "planned_cuts", "extra_scene_cuts"):
            self.assertEqual(a["cuts"][k], b["cuts"][k], k)
        self.assertEqual(a["still"]["seconds_under_half"], b["still"]["seconds_under_half"])
        for x, y in zip(a["still"]["luma"], b["still"]["luma"]):
            self.assertAlmostEqual(x, y, delta=0.25)

    def test_a_proof_the_size_of_the_film_fails_the_film_check(self):
        self.render()
        for p in Path("out").glob("film*.mp4"):
            shutil.copyfile(p, proof.of(p))
        rc, said, check = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] in ("film", "square")], [False, False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_frames_are_cut_from_the_newest_render(self):
        self.render("--proof")
        with mock.patch.object(sys, "argv", ["film.py", "frames"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(film.main(), 0)
        self.assertEqual(_env.read_json("frames/frames.json")["film"], qa.sha("out/proof.mp4"))

    def test_the_gate_reads_the_full_size_film_and_never_the_proof(self):
        self.render("--proof")
        res = qa.film_checks()
        self.assertEqual([(r[1], r[2]) for r in res if r[0] == "film"], [(False, "out/film.mp4 is missing")])


class Rounds(Run):
    """A round on the proof reads the proof; once the full-size film of that cut is rendered, the round moves to it and
    the critics read its type again at full size."""

    def setUp(self):
        super().setUp()
        Path("out").mkdir()
        _env.write_json("film.json", {"seconds": 2})
        _env.write_json("render/film-report.json", {"failed": 0, "made": {"formats": ["reel", "square"], "stories": False}})

    def read(self, mp4):
        """qa.py check and film.py frames on `mp4`, as the round needs before vote.py cut."""
        _env.write_json("qa/check.json", {"film": qa.sha(mp4)})
        _env.write_json("frames/frames.json", {"film": qa.sha(mp4)})

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

    def test_a_round_on_the_proof_moves_to_the_full_size_film_and_the_type_is_read_again(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.read("out/proof.mp4")
        said = self.cut()
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said)
        first = _env.read_json("critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]), (qa.sha("out/proof.mp4"), proof.SCALE, qa.sha("film.json")))
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0, said)
        self.assertIn("film.py render --also square", said, "a SHIP on the proof names the full-size render next")
        Path("out/proof.mp4").unlink()
        Path("out/film.mp4").write_bytes(b"the full-size film")
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            vote.cmd_cut(None)
        self.read("out/film.mp4")
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("type", said)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json("critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"]), (qa.sha("out/film.mp4"), 1))
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
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.read("out/proof.mp4")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        Path("out/proof.mp4").unlink()
        Path("out/film.mp4").write_bytes(b"a film of another cut")
        _env.write_json("film.json", {"seconds": 3})
        self.read("out/film.mp4")
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_render(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.read("out/proof.mp4")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("film.py render --also square --proof", said)


class Deliver(Run):
    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof_and_says_what_to_run(self):
        Path("out").mkdir()
        Path("out/proof.mp4").write_bytes(b"the proof")
        _env.write_json("render/film-report.json", {"failed": 0, "made": {"formats": ["reel", "square"], "stories": True}})
        before = sorted(str(p) for p in Path(".").rglob("*"))
        with mock.patch.object(sys, "argv", ["deliver.py"]), mock.patch.object(_env, "need"), \
                mock.patch.object(_env, "tools", return_value={"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}), \
                self.assertRaises(SystemExit) as e:
            deliver.main()
        said = str(e.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof out/proof.mp4"), said)
        self.assertIn("film.py render --also square stories", said)
        self.assertIn("film.py frames", said)
        self.assertEqual(sorted(str(p) for p in Path(".").rglob("*") if p.name not in ("render.lock",)), before)


class Names(unittest.TestCase):
    def test_every_film_has_its_proof_beside_it(self):
        self.assertEqual(proof.of("out/film.mp4"), Path("out/proof.mp4"))
        self.assertEqual(proof.of("out/film-16x9.mp4"), Path("out/proof-16x9.mp4"))
        self.assertEqual(proof.of("out/film-square.mp4"), Path("out/proof-square.mp4"))
        self.assertEqual(proof.board((540, 960), proof.SCALE), (1080, 1920))


if __name__ == "__main__":
    unittest.main()
