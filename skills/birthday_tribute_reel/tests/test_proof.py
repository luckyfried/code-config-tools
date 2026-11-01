"""The proof: every round before deliver renders the films at half size beside the films in out/ (out/proof.mp4,
out/proof-square.mp4, out/proof-wide.mp4), never over out/film.mp4, with the posted image, the story card and the stills
as the full render makes them. qa.py check and vote.py cut read the newest render and say so; a size qa.py reads off a
proof is in board units, so a proof and a full render of one cut read the same; the critics' round on a proof moves to
the full-size reel, with its frames cut again from it and the type read again there; deliver.py refuses a run whose
newest render is the proof.

    python3 -I -m unittest discover -s S/tests -p test_proof.py
"""
import contextlib
import io
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
import compose  # noqa: E402
import deliver  # noqa: E402
import film  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import sfx  # noqa: E402
import vote  # noqa: E402
import wall  # noqa: E402

FFMPEG, FFPROBE = shutil.which("ffmpeg"), shutil.which("ffprobe")
TOOLS = {"python": sys.executable, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "chromium": "chrome", "dist": True}
SIZES = {"reel": (1080, 1920), "feed": (1080, 1080), "wide": (1920, 1080)}
FRAMES = 60


def draw(jobs, name, run):
    """studio.render with every job drawn at its format's size times its scale: a film is paper with a dark square that
    crosses it, and the paper turns at the first second, so the cut and the move land at the same place of the frame
    at any scale; a still is the paper at the job's size."""
    for job in jobs:
        s = job.get("scale") or 1
        w, h = (round(v * s) for v in SIZES[job["props"]["board"]["format"]])
        Path(job["out"]).parent.mkdir(parents=True, exist_ok=True)
        if job["type"] == "video":
            side = round(300 * s)
            graph = (f"[0]drawbox=x=0:y=0:w={w}:h={h}:color=0x30507a:t=fill:enable='gte(t,1)'[paper];"
                     f"[paper][1]overlay=x='{s}*(100+300*t)':y={round(500 * s)},format=yuv420p")
            subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}:r=30",
                            "-f", "lavfi", "-i", f"color=c=0x1a1410:s={side}x{side}:r=30", "-filter_complex", graph,
                            "-frames:v", str(job["frames"]), "-c:v", "libx264", "-preset", "ultrafast", "-f", "mp4",
                            job["out"]], check=True)
        else:
            subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xf0e8d8:s={w}x{h}", "-frames:v", "1",
                            "-update", "1", job["out"]], check=True)
    return {"jobs": len(jobs), "failed": 0, "findings": [], "seconds": 1}


def clip(path, w, h):
    """A two-second film of one size at `path`."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=s={w}x{h}:r=30:d=2", "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "ultrafast", str(path)], check=True)
    return Path(path)


def width(png):
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(png)], capture_output=True, text=True).stdout.strip()
    return tuple(int(x) for x in out.split(","))


class Workspace(unittest.TestCase):
    """A workspace folder with its run in B/ and the tools found."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.d)
        (self.d / "B").mkdir()
        for patch in (mock.patch.object(_env, "_RUN", self.d / "B"), mock.patch.object(_env, "tools", return_value=TOOLS)):
            patch.start()
            self.addCleanup(patch.stop)


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Proof(Workspace):
    def setUp(self):
        super().setUp()
        for patch in (mock.patch.object(film.compose, "lay", lambda f, fmt, bpm: {"format": fmt}),
                      mock.patch.object(film.compose, "rest_frames", lambda *a: [("hook", 0)]),
                      mock.patch.object(compose, "LENGTH", (1, 60)), mock.patch.object(film.studio, "render", draw)):
            patch.start()
            self.addCleanup(patch.stop)
        _env.write_json("B/film.json", {"hash": "h", "id": "1", "frames": FRAMES, "bpm": 120, "seconds": FRAMES / 30,
                                        "length": FRAMES / 30, "cuts": [1.0], "hook_frame": 4, "rest": ["hook"], "sound": []})
        _env.write_json("B/qa/timed.json", {"hash": "h", "pass": True})

    def render(self, *args):
        with mock.patch.object(sys, "argv", ["film.py", "render", *args]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(film.main(), 0)
        return out.getvalue()

    def check(self):
        with mock.patch.object(sys, "argv", ["qa.py", "check"]), contextlib.redirect_stdout(io.StringIO()) as out:
            rc = qa.main()
        return rc, out.getvalue(), _env.read_json("B/qa/check.json"), _env.read_json("B/qa/film.check.json")

    def test_the_proof_lands_at_half_size_beside_the_film_and_the_film_is_untouched(self):
        Path("out").mkdir()
        Path("out/film.mp4").write_bytes(b"the last full-size film")
        said = self.render("--proof", "--also", "square")
        self.assertEqual(Path("out/film.mp4").read_bytes(), b"the last full-size film", "a proof never writes over the film")
        self.assertEqual(width("out/proof.mp4"), (540, 960))
        self.assertEqual(width("out/proof-square.mp4"), (540, 540))
        self.assertFalse(Path("out/film-square.mp4").exists())
        self.assertEqual(width("out/post.png"), (1080, 1080), "the posted image renders as the full render makes it")
        self.assertEqual(width("out/story.png"), (1080, 1920))
        self.assertIn("out/proof.mp4", said)
        self.assertIn("half-size proof", said)
        report = _env.read_json("B/render/film-report.json")
        self.assertEqual(report["scale"], proof.SCALE)
        self.assertEqual(report["reel"], qa.sha("out/proof.mp4"), "the report certifies the proof it made")
        self.assertEqual(proof.scale(), proof.SCALE)
        self.render("--also", "square")
        self.assertEqual(width("out/film.mp4"), (1080, 1920))
        self.assertEqual(width("out/film-square.mp4"), (1080, 1080))
        self.assertEqual(proof.films("out"), [], "a full render takes the proof's films out of out/")
        self.assertEqual(_env.read_json("B/render/film-report.json")["scale"], 1)
        self.assertEqual(proof.scale(), 1)

    def test_qa_check_reads_the_proof_and_measures_it_in_board_units_as_the_full_render(self):
        self.render("--proof", "--also", "square")
        rc, said, proof_check, proof_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said.splitlines()[0])
        self.assertTrue(Path("B/qa/film-strip2.png").exists(), "the strip the critics open is named for the film")
        self.render("--also", "square")
        rc, said, full_check, full_measured = self.check()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("proof", said.splitlines()[0])
        rows = lambda c: [(x["check"], x["pass"]) for x in c["checks"]]
        self.assertEqual(rows(proof_check), rows(full_check))
        sizes = lambda c: [re.search(r": (\d+x\d+)", x["detail"]).group(1) for x in c["checks"] if x["check"] == "format"]
        self.assertEqual(sizes(proof_check), ["1080x1920", "1080x1080"])
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
        self.assertEqual([x["pass"] for x in check["checks"] if x["check"] == "format"], [False],
                         "a proof is held to half the board's size: a full-size picture in its place is the wrong size")

    def test_the_gate_reads_the_full_size_film_and_never_the_proof(self):
        self.render("--proof")
        res, _, _ = qa.film_checks()
        self.assertEqual([r[1] for r in res if r[0] == "format"], [False], "with no full-size reel the gate is red")
        self.assertIn("out/film.mp4 is missing", [r[2] for r in res if r[0] == "format"][0])


# the round's sound block as vote.sound_read returns it, and a sentence that cites its rows
HEARD = {"table": "B/critic/sound.md", "findings": [], "cited": ""}
CITED = "R5 rests on every cut row on the beat, the end row and each effect row heard over the bed"


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg and ffprobe are not on PATH")
class Rounds(Workspace):
    """A round on the proof cuts its frames from the proof; once the full-size reel of that cut is rendered, the round
    moves to it, its frames are cut again from the full-size reel, and the critics read the type again there. Each round
    carries the sound read of the reel it scores."""

    def setUp(self):
        super().setUp()
        _env.write_json("B/film.json", {"hash": "h", "id": "1", "seconds": 2})
        self.heard = []
        sound = mock.patch.object(vote, "sound_read", lambda film: self.heard.append(str(film)) or dict(HEARD))
        sound.start()
        self.addCleanup(sound.stop)

    def rendered(self, mp4, w, h):
        clip(mp4, w, h)
        _env.write_json("B/render/film-report.json", {"failed": 0, "reel": qa.sha(mp4)})

    def cut(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(vote.cmd_cut(None), 0)
        return out.getvalue()

    def fill(self, score=5):
        path = vote.rounds()[-1]
        data = _env.read_json(path)
        for c in vote.CUT_PANEL:
            e = data["critics"][c]["boards"]["film"]
            e["scores"] = {k: score for k in vote.CRITERIA}
            e["paragraph"] = "frame r1-f03 " + " ".join(["seen"] * 30)
            e["worst"] = "the closer's last line sits a little low in r1-f20"
        data["sound"]["cited"] = CITED
        _env.write_json(path, data)

    def verdict(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = vote.cmd_verdict(None)
        return rc, out.getvalue()

    def test_a_round_on_the_proof_moves_to_the_full_size_reel_and_the_type_is_read_again(self):
        self.rendered("out/proof.mp4", 270, 480)
        said = self.cut()
        self.assertTrue(said.startswith("reading the half-size proof out/proof.mp4"), said)
        first = _env.read_json("B/critic/cut-1.json")
        self.assertEqual((first["film"], first["scale"], first["cut"]),
                         (qa.sha("out/proof.mp4"), proof.SCALE, proof.picture("h", "out/proof.mp4")))
        self.assertEqual((first["sound"], self.heard), (HEARD, ["out/proof.mp4"]), "the round carries the proof's sound read")
        frames = sorted(Path(first["frames"]).glob("*.png"))
        self.assertEqual(width(frames[0]), (270, 480), "the round's frames are the proof's")
        self.fill()
        rc, said = self.verdict()
        self.assertEqual(rc, 0, said)
        self.assertIn("film.py render", said, "a SHIP on the proof names the full-size render next")
        Path("out/proof.mp4").unlink()
        self.rendered("out/film.mp4", 540, 960)
        said = self.cut()
        self.assertNotIn("proof", said.splitlines()[0])
        self.assertIn("type", said)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"], "the final read is the same round")
        moved = _env.read_json("B/critic/cut-1.json")
        self.assertEqual((moved["film"], moved["scale"]), (qa.sha("out/film.mp4"), 1))
        self.assertEqual(self.heard[-1], "out/film.mp4", "the sound is read again on the full-size reel")
        self.assertEqual(moved["sound"]["cited"], CITED, "the citation stands for the same cut")
        self.assertEqual([p.name for p in sorted(Path(moved["frames"]).glob("*.png"))], [p.name for p in frames])
        self.assertEqual(width(sorted(Path(moved["frames"]).glob("*.png"))[0]), (540, 960),
                         "the frames are cut again from the full-size reel")
        for c in vote.CUT_PANEL:
            scores = moved["critics"][c]["boards"]["film"]["scores"]
            self.assertIsNone(scores["type"], "the type is read again on the full-size reel")
            self.assertEqual({k: v for k, v in scores.items() if k != "type"}, {k: 5 for k in vote.CRITERIA if k != "type"})
        self.assertEqual(self.verdict()[0], 1, "the round waits for the type read at full size")
        self.fill()
        rc, said = self.verdict()
        self.assertEqual(rc, 0)
        self.assertTrue(said.startswith("SHIP"), said)
        self.assertNotIn("film.py render", said)
        self.assertIn("already scores this reel", self.cut())
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])

    def test_a_full_size_reel_of_another_cut_opens_the_next_round(self):
        self.rendered("out/proof.mp4", 270, 480)
        self.cut()
        self.fill(3)
        Path("out/proof.mp4").unlink()
        self.rendered("out/film.mp4", 540, 960)
        _env.write_json("B/film.json", {"hash": "another", "id": "1", "seconds": 2})
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("B/critic/cut-2.json")["scale"], 1)

    def test_a_fix_on_the_proof_names_the_proof_render(self):
        self.rendered("out/proof.mp4", 270, 480)
        self.cut()
        self.fill(3)
        rc, said = self.verdict()
        self.assertEqual(rc, 2)
        self.assertIn("film.py render --proof", said)

    def test_a_round_is_complete_only_once_its_sound_score_cites_the_sound_read(self):
        self.rendered("out/proof.mp4", 270, 480)
        self.assertIn("sound.cited", self.cut())
        self.fill()
        data = _env.read_json("B/critic/cut-1.json")
        data["sound"]["cited"] = "fine"
        _env.write_json("B/critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("sound / cited", said)
        del data["sound"]
        _env.write_json("B/critic/cut-1.json", data)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("no sound read", said)
        self.cut()
        self.assertEqual(_env.read_json("B/critic/cut-1.json")["sound"], HEARD, "cut reads the sound into the reel's round")

    def test_a_new_render_of_a_scored_cut_opens_its_own_round_and_the_old_round_is_refused(self):
        self.rendered("out/proof.mp4", 270, 480)
        self.cut()
        self.fill()
        self.rendered("out/proof.mp4", 260, 480)
        rc, said = self.verdict()
        self.assertEqual(rc, 1)
        self.assertIn("not a read of the newest render", said)
        self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(_env.read_json("B/critic/cut-2.json")["film"], qa.sha("out/proof.mp4"))

    def test_a_reel_drawn_by_another_motion_bundle_opens_its_own_round(self):
        dist = Path("dist")
        dist.mkdir()
        (dist / "bundle.js").write_text("one")
        self.rendered("out/proof.mp4", 270, 480)
        with mock.patch.object(proof, "DIST", dist):
            self.cut()
            self.assertEqual(_env.read_json("B/critic/cut-1.json")["cut"], proof.picture("h", "out/proof.mp4", dist))
            self.fill()
            (dist / "bundle.js").write_text("two")
            with self.assertRaises(SystemExit) as e:
                self.cut()
            self.assertIn("rendered before the motion bundle changed", str(e.exception.code))
            Path("out/proof.mp4").unlink()
            self.rendered("out/film.mp4", 540, 960)
            self.cut()
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"],
                         "the full-size reel of another bundle is not the proof's round")


class SoundRead(Workspace):
    def test_the_sound_read_hears_the_reel_through_the_effects_music_py_laid(self):
        film_ = {"hash": "h", "id": "1", "seconds": 14.0, "bpm": 100}
        _env.write_json("B/film.json", film_)
        Path("B/music").mkdir()
        Path("B/music/fx.wav").write_bytes(b"RIFF")
        track = {"master": "B/music/master.wav", "effects_wav": "B/music/fx.wav", "impacts": [1.2]}
        _env.write_json("B/music.json", track)
        seen = {}

        def read(*a, **k):
            seen["read"], seen["kw"] = a, k
            return dict(HEARD)
        with mock.patch.object(wall, "effects_board", lambda f: seen.setdefault("board", f) and {"fx": "the cut's"}), \
                mock.patch.object(sfx, "critic_read", read):
            self.assertEqual(vote.sound_read(Path("out/proof.mp4")), HEARD)
        self.assertEqual(seen["board"], film_, "music.py master lays wall.effects_board of B/film.json")
        fx, record, movie, seconds, _, path = seen["read"]
        self.assertEqual((fx, record, movie, seconds, path),
                         ({"fx": "the cut's"}, track, "out/proof.mp4", 14.0, vote.sound_md()))
        self.assertEqual(seen["kw"], {"fx": "B/music/fx.wav", "ducked": False},
                         "the effects are the file music.py laid, the bed as film.py mux lays it")


class Deliver(Workspace):
    def test_deliver_refuses_a_run_whose_newest_render_is_the_proof_and_says_what_to_run(self):
        Path("out").mkdir()
        Path("out/proof.mp4").write_bytes(b"the proof")
        before = sorted(str(p) for p in Path("out").rglob("*"))
        with mock.patch.object(sys, "argv", ["deliver.py"]), self.assertRaises(SystemExit) as e:
            deliver.main()
        said = str(e.exception.code)
        self.assertTrue(said.startswith("not delivered: the newest render is the half-size proof out/proof.mp4"), said)
        self.assertIn("film.py render", said)
        self.assertEqual(sorted(str(p) for p in Path("out").rglob("*")), before)
        self.assertFalse(Path("B/brief.md").exists())


if __name__ == "__main__":
    unittest.main()
