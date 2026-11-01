"""The proof: every round before deliver renders the videos at half size beside the full-size ones in out/
(out/proof.mp4, out/proof-series.mp4, out/cards/proof-NN-story.mp4), never over them, with the stills as the full render
makes them; qa.py check and vote.py cut read the newest render and say so; a check that measures a video's pixels
measures in board units, so a proof and a full render of one board read the same; the critics' round on a proof moves
to the full-size film with its type (R3) read again there; deliver.py refuses a run whose newest render is the proof.

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
import types
import unittest
from pathlib import Path
from unittest import mock

import fixture

import _env  # noqa: E402
import chunks  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import sfx  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")

# render.py as studio.render calls it: every job is drawn at the board's size times its scale. A video is paper that
# turns blue at its 0.3rd second, with a dark square swinging across it, so the cut, the hook and the motion are drawn
# in board units and land at the same place of the frame at any scale; a still is the paper at the job's size.
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
        graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte({t},0.3)'[paper];"
                 f"[paper][1]overlay=x='{s}*(390+300*sin(2*{t}))':y={round(700 * s)},format=yuv420p")
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


def sounded(silent, wav, seconds, out, fx, record, start=0.0, stop=None, energy=None, fps=30, spawn=subprocess.run):
    """film.sound with a tone for the music: the silent video and an AAC track, at `out`."""
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(silent), "-f", "lavfi", "-i",
                    f"sine=frequency=440:sample_rate=48000:duration={seconds}", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)


def size(path):
    p = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                   "-of", "json", str(path)], capture_output=True, text=True).stdout)["streams"][0]
    return p["width"], p["height"]


def rows(check):
    return {r["check"]: r for r in check["checks"] if r["pass"] is not None}


def figures(check):
    return [r["figures"] for r in check["checks"] if r["pass"] is None]


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(unittest.TestCase):
    """One board rendered as the proof, then at full size."""

    @classmethod
    def setUpClass(cls):
        cls.ws = fixture.workspace()
        fixture.researched(cls.ws)
        cls.run_dir = fixture.build(cls.ws)
        (cls.run_dir / "taste.md").write_text("their month, in prose\n")
        fixture.run(cls.ws, "storyboard.py", "draft")
        sb = cls.run_dir / "storyboards" / "editorial-quiet" / "storyboard.json"
        board = dict(json.loads(sb.read_text()), ask={"counts": False, "seconds": None, "series": True})
        _env.write_json(sb, board)
        _env.write_json(cls.run_dir / "winner.json", {"board": "editorial-quiet"})
        _env.write_json(cls.run_dir / "critic" / "timed.json", {"hash": studio.board_hash(board), "pass": True, "reads": {}})
        bed = cls.run_dir / "music" / "bed.wav"
        bed.parent.mkdir(parents=True, exist_ok=True)
        bed.write_bytes(b"bed")
        _env.write_json(cls.run_dir / "music.json", {"file": str(bed)})
        fake = cls.ws / "render.py"
        fake.write_text(FAKE)
        src = cls.ws / "src"
        src.mkdir()
        (src / "Film.tsx").write_text("export const Film = 1;\n")
        out = cls.run_dir / "out"
        (out / "cards").mkdir(parents=True)
        (out / "film.mp4").write_bytes(b"the last full-size film")
        (out / "cards" / "01-story.mp4").write_bytes(b"the last full-size story")
        tools = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
        with contextlib.ExitStack() as stack:
            for p in (mock.patch.object(_env, "tools", return_value=tools), mock.patch.object(_env, "writable_run", lambda: cls.run_dir),
                      mock.patch.object(studio, "SOURCES", (src,)), mock.patch.object(studio, "RENDERER", fake),
                      mock.patch.object(chunks, "GPU", False), mock.patch.object(film, "sound", sounded),
                      mock.patch.object(film, "ENCODE", ["-c:v", "libx264", "-preset", "veryfast"]),
                      mock.patch.dict(os.environ, FAKE_FFMPEG=FFMPEG)):
                stack.enter_context(p)
            cls.proof_said = cls.render("--proof")
            cls.after_proof = {"film": (out / "film.mp4").read_bytes(), "story": (out / "cards" / "01-story.mp4").read_bytes(),
                               "sizes": {p.relative_to(out).as_posix(): size(p) for p in [*proof.films(out), *proof.films(out / "cards"),
                                                                                     out / "cover.png", *sorted((out / "cards").glob("*.png"))]},
                               "report": _env.read_json(cls.run_dir / "render-report.json"),
                               "cards": _env.read_json(cls.run_dir / "cards.json"), "scale": proof.scale(out / "film.mp4"),
                               "check": _env.read_json(cls.run_dir / "qa" / "check.json")}
            cls.proof_qa = cls.qa()
            cls.gate = qa.checks(cls.run_dir, True)
            cls.render()
            cls.full_qa = cls.qa()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)

    @classmethod
    def render(cls, *args):
        with mock.patch.object(sys, "argv", ["film.py", "render", *args]), contextlib.redirect_stdout(io.StringIO()) as said:
            try:
                rc = film.main()
            except SystemExit as e:
                raise AssertionError(f"film.py render {' '.join(args)} exited: {e.code}") from None
        assert rc == 0, said.getvalue()
        return said.getvalue()

    @classmethod
    def qa(cls):
        here = os.getcwd()
        os.chdir(cls.ws)
        try:
            with mock.patch.object(sys, "argv", ["qa.py", "check"]), contextlib.redirect_stdout(io.StringIO()) as said:
                qa.main()
        finally:
            os.chdir(here)
        return said.getvalue(), _env.read_json(cls.run_dir / "qa" / "check.json")

    def test_the_proof_lands_at_half_size_beside_the_full_size_files_and_never_over_them(self):
        got = self.after_proof
        self.assertEqual(got["film"], b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(got["story"], b"the last full-size story", "nor over a card's story")
        half, full = (540, 960), (1080, 1920)
        self.assertEqual(got["sizes"], {"proof.mp4": half, "proof-series.mp4": half, "cards/proof-01-story.mp4": half,
                                        "cards/proof-02-story.mp4": half, "cards/proof-03-story.mp4": half, "cover.png": full,
                                        "cards/01-story.png": full, "cards/02-story.png": full, "cards/03-story.png": full})
        self.assertEqual(got["scale"], proof.SCALE)
        self.assertEqual(got["report"]["scale"], proof.SCALE)
        self.assertEqual(got["cards"]["film"], "out/proof.mp4")
        self.assertEqual(got["cards"]["series"], "out/proof-series.mp4")
        self.assertEqual([c["mp4"] for c in got["cards"]["cards"]], [f"out/cards/proof-0{n}-story.mp4" for n in (1, 2, 3)])
        self.assertIn("half-size proof", self.proof_said)

    def test_the_full_render_takes_the_proofs_videos_out_of_out(self):
        out = self.run_dir / "out"
        self.assertEqual(size(out / "film.mp4"), (1080, 1920))
        self.assertEqual(size(out / "cards" / "01-story.mp4"), (1080, 1920))
        self.assertEqual(proof.films(out) + proof.films(out / "cards"), [])
        self.assertEqual(proof.scale(out / "film.mp4"), 1)
        self.assertEqual(_env.read_json(self.run_dir / "render-report.json")["scale"], 1)
        self.assertEqual(_env.read_json(self.run_dir / "cards.json")["film"], "out/film.mp4")

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        said, check = self.proof_qa
        self.assertTrue(said.startswith("reading the half-size proof"), said.splitlines()[0])
        self.assertEqual(rows(self.after_proof["check"]), rows(check), "the render's own check reads the proof the same way")
        full_said, full = self.full_qa
        self.assertNotIn("proof", full_said.splitlines()[0])
        self.assertEqual({k: r["pass"] for k, r in rows(check).items()}, {k: r["pass"] for k, r in rows(full).items()})
        for k in ("film", "series", "cards", "hook", "black", "frozen"):
            self.assertTrue(rows(check)[k]["pass"], rows(check)[k]["detail"])
        board_size = lambda c, k: re.match(r"(\d+x\d+)", rows(c)[k]["detail"]).group(1)
        for k in ("film", "series"):
            self.assertEqual(board_size(check, k), "1080x1920")
            self.assertEqual(board_size(check, k), board_size(full, k))
            self.assertIn("in board units, rendered at 540x960", rows(check)[k]["detail"])
        for a, b in zip(figures(check), figures(full)):
            for k in ("cuts", "planned_cuts", "extra_scene_cuts", "seconds_under_half"):
                if k in a:
                    self.assertEqual(a[k], b[k], k)
            for x, y in zip(a.get("luma", []), b.get("luma", [])):
                self.assertAlmostEqual(x, y, delta=0.25)
            if "strip" in a:
                self.assertEqual((Path(a["strip"]).name, Path(a["strip2"]).name), (Path(b["strip"]).name, Path(b["strip2"]).name),
                                 "the strips keep their names, so the critics open the same files")

    def test_the_gate_reads_the_full_size_film_and_never_the_proof(self):
        film_row = next(r for r in self.gate.rows if r["check"] == "film")
        self.assertFalse(film_row["pass"], "the gate holds the full-size film, here an older file that is no video")
        self.assertNotIn("board units", film_row["detail"])
        deliverable = next(r for r in self.gate.rows if r["check"] == "deliver")
        self.assertIn("proof.mp4", deliverable["detail"], "a proof in out/ is not a deliverable")


# the round's sound block as vote.sound_read returns it, and a sentence that cites its rows
HEARD = {"table": "critic/sound.md", "findings": [], "cited": ""}
CITED = "R5 rests on every cut row on the beat, the end row and each effect row heard over the bed"


class Rounds(unittest.TestCase):
    """A round on the proof reads the proof; once the full-size render of that board is in, the round moves to it and
    the critics read its type (R3) again at full size. Each round carries the sound read of the reel it scores."""

    def setUp(self):
        self.run_dir = fixture.tempdir("mir-rounds-")
        self.out = self.run_dir / "out"
        (self.out / "cards").mkdir(parents=True)
        _env.write_json(self.run_dir / "film.json", {"id": "board"})
        (self.out / "cover.png").write_bytes(b"the cover")
        (self.out / "cards" / "01-story.png").write_bytes(b"a still")
        p = mock.patch.object(_env, "run", lambda: self.run_dir)
        p.start()
        self.addCleanup(p.stop)
        self.heard = []
        sound = mock.patch.object(vote, "sound_read", lambda run, reel: self.heard.append(Path(reel).name) or dict(HEARD))
        sound.start()
        self.addCleanup(sound.stop)

    def proofed(self):
        (self.out / "proof.mp4").write_bytes(b"the proof")
        (self.out / "cards" / "proof-01-story.mp4").write_bytes(b"the proof's story")

    def rendered(self):
        for p in proof.films(self.out) + proof.films(self.out / "cards"):
            p.unlink()
        (self.out / "film.mp4").write_bytes(b"the full-size film")
        (self.out / "cards" / "01-story.mp4").write_bytes(b"the full-size story")

    def cut(self):
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(vote.cmd_cut(None), 0)
        return said.getvalue()

    def fill(self, n=1, score=5):
        path = self.run_dir / "critic" / f"cut-{n}.json"
        data = _env.read_json(path)
        for c in vote.CUT_PANEL:
            e = data["critics"][c]["boards"]["film"]
            e["scores"] = {k: score for k in vote.CRITERIA}
            e["paragraph"] = " ".join([f"seen{n}"] * 30)
        if n > 1:
            data["fixed"] = "the line on every card is shorter now"
        data["sound"]["cited"] = CITED
        _env.write_json(path, data)

    def verdict(self):
        with contextlib.redirect_stdout(io.StringIO()) as said:
            rc = vote.cmd_verdict(None)
        return rc, said.getvalue()

    def test_a_round_on_the_proof_moves_to_the_full_size_render_and_the_type_is_read_again(self):
        self.proofed()
        said = self.cut()
        self.assertTrue(said.startswith("reading the half-size proof"), said)
        first = _env.read_json(self.run_dir / "critic" / "cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]),
                         (vote.fingerprint(self.run_dir), proof.SCALE,
                          proof.picture(studio.board_hash({"id": "board"}), self.out / "proof.mp4")))
        self.assertEqual((first["sound"], self.heard), (HEARD, ["proof.mp4"]), "the round carries the proof's sound read")
        self.fill()
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("AT THE BAR"), said)
        self.assertIn("film.py render", said, "at the bar on the proof names the full-size render next")
        self.rendered()
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("R3", said)
        self.assertEqual([p.name for p in vote.rounds(self.run_dir)], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json(self.run_dir / "critic" / "cut-1.json")
        self.assertEqual((moved["film"], moved["scale"], moved["proof_film"]), (vote.fingerprint(self.run_dir, 1), 1, first["film"]))
        self.assertEqual(self.heard[-1], "film.mp4", "the sound is read again on the full-size reel")
        self.assertEqual(moved["sound"]["cited"], CITED, "the citation stands for the same board")
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["R3"], "the type is read again on the full-size render")
            self.assertEqual({k: v for k, v in scores.items() if k != "R3"}, {k: 5 for k in vote.CRITERIA if k != "R3"})
        self.assertEqual(self.verdict()[0], 1, "the round waits for the type read at full size")
        self.fill()
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("AT THE BAR"), said)
        self.assertNotIn("film.py render", said)
        self.assertIn("round 1", self.cut())
        self.assertEqual([p.name for p in vote.rounds(self.run_dir)], ["cut-1.json"])

    def test_a_full_size_render_of_another_board_opens_the_next_round(self):
        self.proofed()
        self.cut()
        self.fill(score=3)
        self.rendered()
        _env.write_json(self.run_dir / "film.json", {"id": "another board"})
        self.cut()
        self.assertEqual([p.name for p in vote.rounds(self.run_dir)], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json(self.run_dir / "critic" / "cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_render(self):
        self.proofed()
        self.cut()
        self.fill(score=3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertTrue(said.startswith("FIX ONCE"), said)
        self.assertIn("film.py render --proof", said)

    def test_a_round_is_complete_only_once_its_r5_score_cites_the_sound_read(self):
        self.proofed()
        self.assertIn("sound.cited", self.cut())
        self.fill()
        path = self.run_dir / "critic" / "cut-1.json"
        data = _env.read_json(path)
        data["sound"]["cited"] = "fine"
        _env.write_json(path, data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("sound / cited", said)
        del data["sound"]
        _env.write_json(path, data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("no sound read", said)
        self.cut()
        self.assertEqual(_env.read_json(path)["sound"], HEARD, "cut reads the sound into the render's round")

    def test_a_new_render_of_a_scored_board_opens_its_own_round_and_the_old_round_is_refused(self):
        self.proofed()
        self.cut()
        self.fill()
        (self.out / "proof.mp4").write_bytes(b"the proof drawn again")
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("not a read of the newest render", said)
        self.cut()
        self.assertEqual([p.name for p in vote.rounds(self.run_dir)], ["cut-1.json", "cut-2.json"])

    def test_a_render_drawn_by_another_motion_bundle_opens_its_own_round(self):
        dist = self.run_dir / "dist"
        dist.mkdir()
        (dist / "bundle.js").write_text("one")
        self.proofed()
        with mock.patch.object(proof, "DIST", dist):
            self.cut()
            self.assertEqual(_env.read_json(self.run_dir / "critic" / "cut-1.json")["cut"],
                             proof.picture(studio.board_hash({"id": "board"}), self.out / "proof.mp4", dist))
            self.fill()
            (dist / "bundle.js").write_text("two")
            with self.assertRaises(SystemExit) as e:
                self.cut()
            self.assertIn("rendered before the motion bundle changed", str(e.exception.code))
            self.rendered()
            self.cut()
        self.assertEqual([p.name for p in vote.rounds(self.run_dir)], ["cut-1.json", "cut-2.json"],
                         "the full-size render of another bundle is not the proof's round")


class SoundRead(unittest.TestCase):
    def test_the_sound_read_hears_the_reel_through_what_film_py_sound_lays(self):
        run = fixture.tempdir("mir-sound-")
        fx = {"id": "board-reel", "bpm": 120, "beats": [{"id": "hook"}]}
        _env.write_json(run / "film.json", {"id": "board", "reel": {"fx": fx, "frames": 450, "fps": 30}})
        _env.write_json(run / "music.json", {"file": "music/bed.wav", "bpm": 120})
        seen = {}

        def read(*a):
            seen["read"] = a
            return dict(HEARD)
        with mock.patch.object(sfx, "critic_read", read):
            self.assertEqual(vote.sound_read(run, run / "out" / "proof.mp4"), HEARD)
        board, record, movie, seconds, _, path = seen["read"]
        self.assertEqual((board, movie, seconds, path), (fx, str(run / "out" / "proof.mp4"), 15.0, run / "critic" / "sound.md"))
        self.assertEqual(record, {"file": "music/bed.wav", "bpm": 120, "master": str(run / "render" / "out" / "proof.wav")},
                         "the reel's own master, the music film.py sound cut for it")


class Deliver(unittest.TestCase):
    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof_and_says_what_to_run(self):
        run = fixture.tempdir("mir-deliver-")
        (run / "out").mkdir()
        (run / "out" / "proof.mp4").write_bytes(b"the proof")
        (run / "out" / "film.mp4").write_bytes(b"an older full-size film")
        (run / "delivered.json").write_text("{}")

        @contextlib.contextmanager
        def held(work, name):
            Path(work).mkdir(parents=True, exist_ok=True)
            yield types.SimpleNamespace(spawn=subprocess.run)

        with mock.patch.object(_env, "run", lambda: run), mock.patch.object(studio, "lock", held), \
                mock.patch.object(sys, "argv", ["deliver.py"]):
            with self.assertRaises(SystemExit) as refused:
                deliver.main()
        said = str(refused.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof"), said)
        self.assertIn("film.py render", said)
        self.assertTrue((run / "delivered.json").exists(), "a refused deliver changes nothing")
        self.assertEqual(sorted(p.name for p in (run / "out").iterdir()), ["film.mp4", "proof.mp4"])


if __name__ == "__main__":
    unittest.main()
