"""The half-size proof: every critic round before deliver renders the films at half size beside the film in RUN/cut/
(film.py render --proof), qa.py check and vote.py cut read it while it is the newest render and measure it in board
units, the round moves to the full-size film of the same cut for the type read at full size, and deliver.py refuses a
run whose newest render is the proof. A fake renderer draws each job at its board's size times its scale: a paper
ground that turns blue at 1 s, under a dark square that moves across it the whole time.

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
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
STYLE = "cinematic-letterbox"
import _env  # noqa: E402
import chunks  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402

FRAMES = 60
SIZES = {"reel": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080)}

# render.py as the bridge sees it: each video job's clip at its `.part.mp4` with its findings file beside it, drawn at
# its board's size times the job's scale, and a still at its `out`; every job it was handed is logged to FAKE_JOBS
FAKE = r"""
import json, os, subprocess, sys
spec = json.load(open(sys.argv[-1]))
sizes = json.loads(os.environ["FAKE_SIZES"])
with open(os.environ["FAKE_JOBS"], "a") as log:
    for job in spec["jobs"]:
        log.write(json.dumps({"type": job["type"], "board": job["props"]["board"], "scale": job.get("scale")}) + "\n")
for job in spec["jobs"]:
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    if job["type"] != "video":
        open(job["out"], "wb").write(b"png")
        continue
    s = job.get("scale") or 1
    W, H = sizes[job["props"]["board"]]
    w, h = round(W * s / 2) * 2, round(H * s / 2) * 2
    a, b = job["frameRange"]
    t = f"(t+{a}/30)"
    side = round(300 * s)
    graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},1)'[paper];"
             f"[paper][1]overlay=x='{s}*(100+300*{t})':y={round(600 * s)},format=yuv420p")
    subprocess.run([os.environ["FAKE_FFMPEG"], "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30",
                    "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                    "-frames:v", str(b - a + 1), "-c:v", "libx264", "-preset", "veryfast", "-f", "mp4", job["out"]], check=True)
    json.dump([], open(job["out"].removesuffix(".mp4") + ".findings.json", "w"))
json.dump({"findings": []}, open(spec["report"], "w"))
"""


def size(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", str(video)],
                       capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    return s["width"], s["height"]


# the round's sound block as vote.sound_read returns it, and a sentence that cites its rows
HEARD = {"table": "critic/sound.md", "findings": [], "cited": ""}
CITED = "sound rests on every cut row on the beat, the end row and each effect row heard over the bed"


def scored(data, score=5):
    for c in data["critics"].values():
        e = c["boards"]["film"]
        e["scores"] = {k: score for k in e["scores"]}
        e["paragraph"] = " ".join(["the cut holds its one idea from day one to the latest and every move lands"] * 3)
    data["sound"]["cited"] = CITED
    return data


class Proof(unittest.TestCase):
    """film.py render through main over the fake renderer, with the board, the clips, the then/now image, the rules,
    the cards and the order stubbed; the reel runs 60 frames with one planned cut at 1 s."""

    def setUp(self):
        import clips
        import storyboard
        import vote
        self.d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))).resolve()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        here = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, here)
        run = Path("build") / "run"
        (run / "public").mkdir(parents=True)
        (self.d / "render.py").write_text(f"#!{sys.executable}\n{FAKE}")
        self.jobs = self.d / "jobs.log"
        self.env = {"FAKE_FFMPEG": shutil.which("ffmpeg"), "FAKE_SIZES": json.dumps(SIZES), "FAKE_JOBS": str(self.jobs)}
        tools = {"chromium": str(self.d / "chromium"), "dist": str(self.d / "dist"), "ffmpeg": shutil.which("ffmpeg"),
                 "ffprobe": shutil.which("ffprobe")}
        names = [(film, "chosen"), (film, "props"), (film, "timeline"), (film, "board_sha"), (film, "then_now"), (film, "RENDERER"),
                 (clips, "write_requests"), (clips, "normalize"), (qa, "cards_check"), (qa, "order_check"), (_env, "B"), (_env, "tools"),
                 (chunks, "GPU"), (storyboard, "lay_out"), (storyboard, "starts"), (storyboard, "measured"), (storyboard, "check_board"),
                 (vote, "sound_read")]
        saved = {(m, k): getattr(m, k) for m, k in names}
        self.addCleanup(lambda: [setattr(m, k, v) for (m, k), v in saved.items()])
        _env.B, _env.tools, chunks.GPU, film.RENDERER = run, (lambda: tools), False, self.d / "render.py"
        film.chosen = lambda: {"board": STYLE}
        film.props = lambda b: {"board": b["id"]}
        film.board_sha = lambda b: "sha"
        film.timeline = lambda b: {"fps": 30, "frames": FRAMES, "seconds": FRAMES / 30, "style": STYLE, "format": "reel", "width": 1080,
                                   "height": 1920, "beats": [], "cuts": [30], "hook_frame": 0, "stop_frame": FRAMES, "stills": {}}
        film.then_now = lambda board, rows, dst: (dst.parent.mkdir(parents=True, exist_ok=True), dst.write_bytes(b"png"))
        storyboard.lay_out = lambda style, f="reel": {"id": f, "bpm": 120.0, "stills": {"hook": 1, "dense": 2, "closer": 3},
                                                      "sound": [{"kind": "impact", "at": 1.0}, {"kind": "stop", "at": 4.0}],
                                                      "beats": [{"id": "one"}, {"id": "two"}], "facts": {},
                                                      "film": {"cards": [], "closer": {"span": "x"}, "timeline": {"beats": []}}}
        storyboard.starts = lambda b: ([0, 30], FRAMES)
        storyboard.measured = lambda: []
        storyboard.check_board = lambda b, rows, fx: []
        clips.write_requests = lambda b: []
        clips.normalize = lambda b, why=None: 0
        qa.cards_check = lambda: (True, "the cards")
        qa.order_check = lambda b, rows: (True, "the order")
        self.heard, self.saved_sound = [], vote.sound_read
        vote.sound_read = lambda reel: self.heard.append(Path(reel).name) or dict(HEARD)
        _env.write_json(run / "film.json", {"board": STYLE})
        _env.write_json(run / "critic" / "timing.json", {"pass": True, "board_sha": "sha"})
        self.run_dir = run

    def main(self, module, *args):
        old, argv = dict(os.environ), sys.argv
        os.environ.update(self.env)
        sys.argv = [f"{module.__name__}.py", *args]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = module.main()
        finally:
            os.environ.clear()
            os.environ.update(old)
            sys.argv = argv
        return rc, out.getvalue()

    def logged(self):
        jobs = [json.loads(x) for x in self.jobs.read_text().splitlines()] if self.jobs.exists() else []
        self.jobs.unlink(missing_ok=True)
        return jobs

    def test_the_proof_renders_every_film_at_half_size_beside_the_film_and_never_over_it(self):
        rc, said = self.main(film, "render", "--also", "square")
        self.assertEqual(rc, 0, said)
        self.logged()
        full = _env.cut("film.mp4").read_bytes()
        rc, said = self.main(film, "render", "--proof", "--also", "square")
        self.assertEqual(rc, 0, said)
        self.assertEqual(_env.cut("film.mp4").read_bytes(), full, "a proof never writes over the film")
        self.assertEqual(size(_env.cut("proof.mp4")), (540, 960))
        self.assertEqual(size(_env.cut("proof-square.mp4")), (540, 540))
        jobs = self.logged()
        self.assertEqual({j["scale"] for j in jobs if j["type"] == "video"}, {proof.SCALE})
        self.assertEqual({j["scale"] for j in jobs if j["type"] == "still"}, {None}, "the stills render as the full render makes them")
        self.assertIn("proof.mp4", said)
        self.assertEqual(_env.read_json(_env.b("render", "report.json"))["scale"], proof.SCALE)
        self.assertEqual(proof.scale(_env.cut("film.mp4")), proof.SCALE)
        rc, said = self.main(film, "render")
        self.assertEqual(rc, 0, said)
        self.assertEqual(size(_env.cut("film.mp4")), (1080, 1920))
        self.assertEqual(proof.films(_env.cut()), [], "a full render takes the proof's films out of cut/")
        self.assertEqual(_env.read_json(_env.b("render", "report.json"))["scale"], 1)
        self.assertEqual(proof.scale(_env.cut("film.mp4")), 1)

    def test_the_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.assertEqual(self.main(film, "render", "--proof")[0], 0)
        rc, said = self.main(qa, "check")
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith(f"reading the half-size proof {_env.cut('proof.mp4')}"), said.splitlines()[0])
        on_proof = _env.read_json(_env.b("qa", "check.json"))
        self.assertEqual(on_proof["film"], qa.sha(_env.cut("proof.mp4")), "the check names the proof it measured")
        self.assertEqual(self.main(film, "render")[0], 0)
        rc, said = self.main(qa, "check")
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        on_film = _env.read_json(_env.b("qa", "check.json"))
        self.assertEqual(on_film["film"], qa.sha(_env.cut("film.mp4")))
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]  # noqa: E731
        self.assertEqual(rows(on_proof), rows(on_film))
        detail = lambda c: next(x["detail"] for x in c["checks"] if x["check"] == "film")  # noqa: E731
        self.assertIn("reel 1080x1920 in board units, rendered at 540x960", detail(on_proof))
        self.assertIn("reel 1080x1920", detail(on_film))
        a, b = on_proof["numbers"], on_film["numbers"]
        for k in ("duration", "cuts", "planned_cuts", "extra_scene_cuts", "still_seconds", "hook_frame"):
            self.assertEqual(a[k], b[k], k)
        for x, y in zip(a["rest_line"], b["rest_line"]):
            self.assertAlmostEqual(x, y, delta=1.0)
        self.assertAlmostEqual(a["hook_difference"], b["hook_difference"], delta=1.0)

    def test_films_the_size_of_the_full_render_in_the_proofs_place_fail_the_film_row(self):
        self.assertEqual(self.main(film, "render")[0], 0)
        shutil.copyfile(_env.cut("film.mp4"), _env.cut("proof.mp4"))
        res = qa.Checks()
        with contextlib.redirect_stdout(io.StringIO()):
            qa.film_checks(res, scale=proof.SCALE)
        name, ok, detail = next(r for r in res if r[0] == "film")
        self.assertFalse(ok, "a proof is held to half the board's size")
        self.assertIn("cut/proof.mp4 is 2160x3840 in board units", detail)

    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof(self):
        import deliver
        self.assertEqual(self.main(film, "render", "--proof")[0], 0)
        with self.assertRaises(SystemExit) as e:
            self.main(deliver)
        said = str(e.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof"), said)
        self.assertIn("film.py render", said)
        self.assertFalse(_env.out().exists())
        self.assertFalse(_env.cut("review.html").exists())
        self.assertFalse(_env.b("brief.md").exists())

    def test_the_round_scores_the_proof_and_moves_to_the_full_film_of_the_same_cut_for_the_type(self):
        import vote
        self.assertEqual(self.main(film, "render", "--proof")[0], 0)
        rc, said = self.main(vote, "cut")
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof"), said)
        [first] = vote.rounds()
        data = _env.read_json(first)
        self.assertEqual((data["film"], data["scale"]), (vote.digest(_env.cut("proof.mp4")), proof.SCALE))
        self.assertEqual(data["cut"], proof.picture(_env.read_json(_env.b("render", "report.json"))["cut"], _env.cut("proof.mp4")))
        self.assertEqual((data["sound"], self.heard), (HEARD, ["proof.mp4"]), "the round carries the proof's sound read")
        data = scored(data)
        data["critics"]["motion_designer"]["boards"]["film"]["scores"]["concept"] = 3
        _env.write_json(first, data)
        rc, said = self.main(vote, "verdict")
        self.assertEqual(rc, 2, said)
        self.assertIn("film.py render --proof", said, "the one fix renders the proof again")
        _env.write_json(first, scored(data))
        rc, said = self.main(vote, "verdict")
        self.assertEqual(rc, 0, said)
        self.assertIn("SHIP", said)
        self.assertIn("Render the full-size film (film.py render)", said)
        self.assertEqual(self.main(film, "render")[0], 0)
        rc, said = self.main(vote, "cut")
        self.assertEqual(rc, 0, said)
        self.assertEqual(vote.rounds(), [first], "the full-size film of the same cut keeps the round")
        moved = _env.read_json(first)
        self.assertEqual((moved["film"], moved["scale"], moved["proof_film"]),
                         (vote.digest(_env.cut("film.mp4")), 1, data["film"]))
        self.assertEqual((self.heard[-1], moved["sound"]["cited"]), ("film.mp4", CITED),
                         "the sound is read again on the full-size film, and the citation stands for the same cut")
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["type"], "the type is read again at full size")
            self.assertEqual(scores["concept"], 5, "the other scores stand")
        rc, said = self.main(vote, "verdict")
        self.assertEqual(rc, 1, said)
        _env.write_json(first, scored(moved))
        rc, said = self.main(vote, "verdict")
        self.assertEqual(rc, 0, said)
        self.assertIn("SHIP", said)
        self.assertNotIn("Render the full-size film", said)
        self.assertIn("Next: deliver.py", said)

    def ready(self, *args):
        import vote
        self.assertEqual(self.main(film, "render", *args)[0], 0)
        reel = proof.newest(_env.cut("film.mp4"))
        _env.write_json(_env.b("qa", "check.json"), {"film": vote.digest(reel)})
        return reel

    def test_a_cut_round_scores_sound_from_the_sound_read_and_cites_its_rows(self):
        import vote
        self.ready("--proof")
        self.assertEqual(self.main(vote, "cut")[0], 0)
        [first] = vote.rounds()
        data = scored(_env.read_json(first))
        e = data["critics"]["person"]["boards"]["film"]
        e["scores"]["sound"], e["not_read"] = None, ["sound"]
        _env.write_json(first, data)
        rc, said = self.main(vote, "verdict")
        self.assertEqual(rc, 1, said)
        self.assertIn("the sound read is there to read", said)
        e["scores"]["sound"], e["not_read"] = 5, []
        data["sound"]["cited"] = "fine"
        _env.write_json(first, data)
        rc, said = self.main(vote, "verdict")
        self.assertEqual(rc, 1, said)
        self.assertIn("sound / cited", said)
        del data["sound"]
        _env.write_json(first, data)
        self.assertIn("no sound read", self.main(vote, "verdict")[1])
        self.main(vote, "cut")
        self.assertEqual(_env.read_json(first)["sound"], HEARD, "cut reads the sound into the render's round")

    def test_a_render_drawn_by_another_motion_bundle_opens_its_own_round_and_the_old_round_is_refused(self):
        import vote
        dist = self.d / "drawn"
        dist.mkdir()
        (dist / "bundle.js").write_text("one")
        saved = proof.DIST
        self.addCleanup(setattr, proof, "DIST", saved)
        proof.DIST = dist
        reel = self.ready("--proof")
        self.main(vote, "cut")
        [first] = vote.rounds()
        _env.write_json(first, scored(_env.read_json(first)))
        then = os.path.getmtime(reel) - 10
        os.utime(reel, (then, then))
        (dist / "bundle.js").write_text("two")
        with self.assertRaises(SystemExit) as e:
            self.main(vote, "verdict")
        self.assertIn("rendered before the motion bundle changed", str(e.exception.code))
        self.ready("--proof")
        with self.assertRaises(SystemExit) as e:
            self.main(vote, "verdict")
        self.assertIn("is not for the current cut", str(e.exception.code))
        self.assertEqual(self.main(vote, "cut")[0], 0)
        self.assertEqual([p.name for p in vote.rounds()], [first.name, first.name.replace("-1.json", "-2.json")])

    def test_the_sound_read_hears_the_render_through_what_the_mux_laid(self):
        import vote
        vote.sound_read = self.saved_sound
        reel = self.ready("--proof")
        block = vote.sound_read(reel)
        self.assertEqual(block["cited"], "")
        table = Path(block["table"])
        self.assertEqual(table, _env.b("critic", "sound.md").resolve())
        self.assertIn("|", table.read_text())
        self.assertTrue(table.with_suffix(".json").exists())


if __name__ == "__main__":
    unittest.main()
