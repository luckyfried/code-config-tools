"""The proof: every round before deliver renders the films at half size beside the films in out/ (out/proof.mp4,
out/proof-square.mp4, out/proof-wide.mp4), never over them, with the best-nine image and the frames as the full render
makes them; qa.py check and vote.py cut read the newest render and say so; a check that measures a film's pixels
measures in board units, so a proof and a full render of one cut read the same; the critics' round on a proof moves to
the full-size reel with its type read again there; deliver.py refuses a run whose newest render is the proof.

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
import studio  # noqa: E402
import sfx  # noqa: E402
import story  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
PLAIN = types.SimpleNamespace(spawn=subprocess.run)
STYLE = storyboard.compose.TRIO[0]

# render.py as studio.render calls it: every job is drawn at its board's size times its scale. A film is paper with a
# dark square that crosses it, and the paper turns at the film's second second, so the cut and the move are drawn in
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
                 f"[paper][1]overlay=x='{s}*(100+300*{t})':y={round(400 * s)},format=yuv420p")
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
SIZES = {"reel": (1080, 1920), "square": (1080, 1080), "wide": (1920, 1080)}


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        fake = self.dir / "render.py"
        fake.write_text(FAKE)
        src = self.dir / "src"
        src.mkdir()
        (src / "Film.tsx").write_text("export const Film = 1;\n")
        self.run_dir = self.dir / "run"
        self.run_dir.mkdir()
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.run_dir)
        tools = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
        # a fixture cut of two seconds, with no posts to count: the length asked is the cut's and the stills show all of none
        for patch in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(studio, "SOURCE", (src,)),
                      mock.patch.object(studio, "RENDERER", fake), mock.patch.object(chunks, "GPU", False),
                      mock.patch.object(qa, "asked", return_value=FRAMES / 30), mock.patch.object(qa, "posts_n", return_value=0),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG)):
            patch.start()
            self.addCleanup(patch.stop)
        for fmt, (w, h) in SIZES.items():
            _env.write_json(f"boards/{fmt}.json", {"id": fmt, "beats": [], "bpm": 120,
                                                   "format": {"name": fmt, "width": w, "height": h, "fps": 30}})
        _env.write_json("film.json", {"hash": "h", "style": STYLE, "frames": FRAMES, "seconds": FRAMES / 30, "cuts": [1.0],
                                      "hook_frame": 4, "boards": {fmt: f"boards/{fmt}.json" for fmt in SIZES},
                                      "rests": {fmt: {"hook": 1, "dense": 30, "closer": 50} for fmt in SIZES}})
        _env.write_json("qa/timed.json", {"hash": "h", "pass": True})

    def render(self, *args):
        with mock.patch.object(sys, "argv", ["film.py", "render", *args, "--run", str(self.run_dir)]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(film.main(), 0)
        return out.getvalue()

    def size(self, mp4):
        p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                       "-of", "json", str(mp4)], capture_output=True, text=True).stdout)["streams"][0]
        return p["width"], p["height"]

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with mock.patch.object(sys, "argv", ["qa.py", "check", "--run", str(self.run_dir)]):
                rc = qa.main()
        return rc, out.getvalue(), _env.read_json("qa/check.json"), _env.read_json("qa/film.check.json")

    def test_the_proof_lands_at_half_size_beside_the_films_and_the_films_are_untouched(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last full-size reel")
        Path("out/film-wide.mp4").write_bytes(b"the last full-size wide film")
        said = self.render("--proof", "--also", "landscape")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size reel", "a proof never writes over the film")
        self.assertEqual(Path("out/film-wide.mp4").read_bytes(), b"the last full-size wide film")
        self.assertEqual(self.size("out/proof.mp4"), (540, 960))
        self.assertEqual(self.size("out/proof-wide.mp4"), (960, 540))
        self.assertEqual(chunks._frames(PLAIN, FFPROBE, Path("out/proof.mp4")), FRAMES)
        self.assertEqual(qa.png_size("out/best-nine.png"), (1080, 1080), "the best-nine image renders as the full render makes it")
        self.assertEqual(qa.png_size("frames/reel-closer.png"), (540, 960))
        self.assertIn("out/proof.mp4", said)
        self.assertIn("half-size proof", said)
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], proof.SCALE)
        self.assertEqual(proof.scale(), proof.SCALE)
        self.render("--also", "landscape")
        self.assertEqual(self.size("out/film.mp4"), (1080, 1920))
        self.assertEqual(self.size("out/film-wide.mp4"), (1920, 1080))
        self.assertEqual(proof.films("out"), [], "a full render takes the proof's films out of out/")
        self.assertEqual(_env.read_json("render/film-report.json")["scale"], 1)
        self.assertEqual(proof.scale(), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.render("--proof", "--also", "landscape")
        rc, said, proof_check, proof_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said.splitlines()[0])
        self.assertTrue(Path("qa/film-strip2.png").exists(), "the strip the critics open is named for the film")
        self.render("--also", "landscape")
        rc, said, full_check, full_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        sizes = lambda c: [re.search(r": (\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "format"]
        self.assertEqual(sizes(proof_check), ["1080x1920", "1920x1080"])
        self.assertEqual(sizes(proof_check), sizes(full_check))
        for k in ("seconds", "frames", "cuts", "planned_cuts", "extra_scene_cuts", "seconds_under_half"):
            self.assertEqual(proof_measured[k], full_measured[k], k)
        for a, b in zip(proof_measured["luma"], full_measured["luma"]):
            self.assertAlmostEqual(a, b, delta=0.25)

    def test_a_proof_the_size_of_the_film_fails_the_format_check(self):
        self.render()
        shutil.copyfile("out/film.mp4", "out/proof.mp4")
        rc, said, check, _ = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "format"], [False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_the_gate_reads_the_full_size_film_and_never_the_proof(self):
        self.render("--proof")
        with contextlib.redirect_stdout(io.StringIO()):
            res, _, _ = qa.film_checks()
        self.assertEqual([r[1] for r in res if r[0] == "format"], [False], "with no full-size film the gate is red")
        self.assertIn("out/film.mp4 is missing", [r[2] for r in res if r[0] == "format"][0])


# the round's sound block as vote.sound_read returns it, and a sentence that cites its rows
HEARD = {"table": "critic/sound.md", "findings": [], "cited": ""}
CITED = "R5 rests on every cut row on the beat, the end row and each effect row heard over the bed"


class Rounds(unittest.TestCase):
    """A round on the proof reads the proof; once the full-size reel of that cut is rendered, the round moves to it and
    the critics read its type again at full size. Each round carries the sound read of the reel it scores."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)
        Path("out").mkdir()
        _env.write_json("film.json", {"hash": "h", "style": STYLE})
        _env.write_json("render/film-report.json", {"failed": 0})
        self.heard = []
        sound = mock.patch.object(vote, "sound_read", lambda film: self.heard.append(str(film)) or dict(HEARD))
        sound.start()
        self.addCleanup(sound.stop)

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
        data["sound"]["cited"] = CITED
        _env.write_json(path, data)

    def verdict(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = vote.cmd_verdict(None)
        return rc, out.getvalue()

    def test_a_round_on_the_proof_moves_to_the_full_size_reel_and_the_type_is_read_again(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        said = self.cut()
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said)
        first = _env.read_json("critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]),
                         (qa.sha("out/proof.mp4"), proof.SCALE, proof.picture("h", "out/proof.mp4")))
        self.assertEqual((first["sound"], self.heard), (HEARD, ["out/proof.mp4"]), "the round carries the proof's sound read")
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertIn("film.py render", said, "a SHIP on the proof names the full-size render next")
        Path("out/proof.mp4").unlink()
        Path("out/film.mp4").write_bytes(b"the full-size reel")
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("type", said)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json("critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"]), (qa.sha("out/film.mp4"), 1))
        self.assertEqual(self.heard[-1], "out/film.mp4", "the sound is read again on the full-size reel")
        self.assertEqual(moved["sound"]["cited"], CITED, "the citation stands for the same cut")
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["type"], "the type is read again on the full-size reel")
            self.assertEqual({k: v for k, v in scores.items() if k != "type"}, {k: 5 for k in vote.CRITERIA if k != "type"})
        self.assertEqual(self.verdict()[0], 1, "the round waits for the type read at full size")
        self.fill("critic/cut-1.json")
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("SHIP"), said)
        self.assertNotIn("film.py render", said)
        self.assertEqual(self.cut().count("round 1"), 1)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])

    def test_a_full_size_reel_of_another_cut_opens_the_next_round(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        Path("out/proof.mp4").unlink()
        Path("out/film.mp4").write_bytes(b"a reel of another cut")
        _env.write_json("film.json", {"hash": "another", "style": STYLE})
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_render(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.cut()
        self.fill("critic/cut-1.json", 3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("film.py render --proof", said)

    def test_a_round_is_complete_only_once_its_music_score_cites_the_sound_read(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.assertIn("sound.cited", self.cut())
        self.fill("critic/cut-1.json")
        data = _env.read_json("critic/cut-1.json")
        data["sound"]["cited"] = "fine"
        _env.write_json("critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("sound / cited", said)
        del data["sound"]
        _env.write_json("critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("no sound read", said)
        self.cut()
        self.assertEqual(_env.read_json("critic/cut-1.json")["sound"], HEARD, "cut reads the sound into the reel's round")

    def test_a_new_render_of_a_scored_cut_opens_its_own_round_and_the_old_round_is_refused(self):
        Path("out/proof.mp4").write_bytes(b"the proof")
        self.cut()
        self.fill("critic/cut-1.json")
        Path("out/proof.mp4").write_bytes(b"the proof drawn again")
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("not a read of the newest render", said)
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("critic/cut-2.json")["film"], qa.sha("out/proof.mp4"))

    def test_a_reel_drawn_by_another_motion_bundle_opens_its_own_round(self):
        dist = Path("dist")
        dist.mkdir()
        (dist / "bundle.js").write_text("one")
        Path("out/proof.mp4").write_bytes(b"the proof")
        with mock.patch.object(proof, "DIST", dist):
            self.cut()
            self.assertEqual(_env.read_json("critic/cut-1.json")["cut"], proof.picture("h", "out/proof.mp4", dist))
            self.fill("critic/cut-1.json")
            (dist / "bundle.js").write_text("two")
            with self.assertRaises(SystemExit) as e:
                self.cut()
            self.assertIn("rendered before the motion bundle changed", str(e.exception.code))
            Path("out/proof.mp4").unlink()
            Path("out/film.mp4").write_bytes(b"the full-size reel of the new bundle")
            self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"],
                         "the full-size reel of another bundle is not the proof's round")


class SoundRead(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def test_the_sound_read_hears_the_reel_through_the_effects_board_the_mux_lays(self):
        board = {"id": "reel", "bpm": 110, "beats": []}
        _env.write_json("boards/reel.json", board)
        _env.write_json("film.json", {"boards": {"reel": "boards/reel.json"}, "seconds": 16.0})
        _env.write_json("music.json", {"master": "music/master.wav", "bpm": 110})
        seen = {}

        def read(*a):
            seen["read"] = a
            return dict(HEARD)
        with mock.patch.object(story, "fx_board", lambda b: seen.setdefault("board", b) and {"fx": "the reel's"}), \
                mock.patch.object(sfx, "critic_read", read):
            self.assertEqual(vote.sound_read(Path("out/proof.mp4")), HEARD)
        self.assertEqual(seen["board"], board, "film.py mux lays story.fx_board of the reel's board")
        fx, record, movie, seconds, _, path = seen["read"]
        self.assertEqual((fx, record, movie, seconds, path),
                         ({"fx": "the reel's"}, {"master": "music/master.wav", "bpm": 110}, "out/proof.mp4", 16.0, vote.SOUND))


class Deliver(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof_and_says_what_to_run(self):
        Path("out").mkdir()
        Path("out/proof.mp4").write_bytes(b"the proof")
        before = sorted(str(p) for p in Path(".").rglob("*"))
        with mock.patch.object(sys, "argv", ["deliver.py", "--run", str(self.dir)]), \
                mock.patch.object(_env, "tools", return_value={}), self.assertRaises(SystemExit) as e:
            deliver.main()
        said = str(e.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof out/proof.mp4"), said)
        self.assertIn("film.py render", said)
        self.assertEqual(sorted(str(p) for p in Path(".").rglob("*") if p.name not in ("render.lock", "render")), before)


if __name__ == "__main__":
    unittest.main()
