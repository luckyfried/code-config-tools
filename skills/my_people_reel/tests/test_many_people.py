"""A request that names more people than a row of the closing wall holds makes the film of every one of them: six
named people give six cards and a wall that holds all six, eight and twelve keep every one in every format on a wall
taller than the 9:16 frame. The camera runs down a grown wall with the tag, so each wall tag stands between the safe
area's top and foot as the camera sees it when the tag lands on it, and comes to rest on the wall's foot; no two moves
between cards in a row are the same. No stamp on
the wall covers a face, and a photograph of them together whose heads the cast does not name opens on every person's
tag. The cut may run 4 s longer for each person after the fifth. The description the catalog shows stays inside its
1024 characters with every phrasing that triggers the kit.

    python3 -I -m unittest discover -s S/tests
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_drive  # noqa: E402
import boards  # noqa: E402
import layout as L  # noqa: E402
import qa  # noqa: E402

# the photographs' colors the scrapbook card's palette rule makes the board's colors from
SWATCHES = ["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"]


MOTION = KIT / "motion"
ESBUILD = MOTION / "node_modules" / ".bin" / "esbuild"
PEOPLE = [("dani.reyes", "july", "sicily", "remember when we missed the last ferry"),
          ("theo.makes", "april", "porto", "measured twice, still crooked"),
          ("ines.walks", "may", "oaxaca", "the whole valley going gold"),
          ("kofi.cooks", "september", "marrakech", "save me a seat and a spoon"),
          ("liv.outside", "january", "lisbon", "the first good day of the year"),
          ("sam_and_june", "february", "home", "we still talk about that soup"),
          ("maya.l", "june", "ericeira", "same time next summer"),
          ("rui.santos", "august", "the coast", "you drove, i sang"),
          ("kai_w", "march", "the river", "first swim of the year, never again"),
          ("ola.n", "october", "berlin", "the train was late and so were we"),
          ("noor.h", "november", "amsterdam", "two bikes, one map, no plan"),
          ("gabi.lima", "december", "rio", "the year ended on a rooftop")]
TRIGGERS = ["who I spent the year with", "my people", "my people 2026", "friendship recap", "the friends who made my year",
            "my top friends as a video", "best friends recap", "who I hung out with most",
            "a reel of my friends from this year", "shout out my people", "tag my friends in a year recap", "my crew this year"]
# where each wall tag sits on screen as it lands, and where the camera rests at the stop
SCRIPT = """
import {readFileSync} from 'fs';
import {planOf} from %s;
import {framingAt} from %s;
const out = [];
for (const board of JSON.parse(readFileSync(process.argv[2], 'utf8'))) {
  const plan = planOf(board), {W, H} = plan, R = plan.closer.route;
  const tags = board.beats.find((b) => b.id === 'closer').layers.filter((l) => l.kind === 'Slice').sort((a, b) => a.owner - b.owner).map((l) => l.tag);
  const seen = tags.map((g, j) => {
    const f = framingAt(plan, R.at + (R.len * (j + 1)) / tags.length).framing, k = H / f.h;
    const sx = (x) => W / 2 + k * (x - f.c[0]), sy = (y) => H / 2 + k * (y - f.c[1]);
    return [sy(g.box[1]), sy(Math.max(g.box[3], g.tip[1]))];
  });
  const rest = framingAt(plan, plan.closer.still).framing;
  out.push({kind: board.format.kind, height: plan.closer.height, safe: plan.safe, seen, rest: [rest.c[1], rest.h]});
}
console.log(JSON.stringify(out));
"""


def run_folder(d, n, wide=False):
    """A run folder at `d` holding n people as research.py, taste.json and cast.py match leave them: each with a
    photograph of the two of them (4:5, or 4:3 with the face high in it when `wide`), a month, a place and a line of
    their own, and a photograph of four of them together."""
    matched = Path(d, "public", "matched")
    matched.mkdir(parents=True)
    people, told, cast, aspects = [], [], {}, {"group": 0.75}
    for i, (h, when, where, said) in enumerate(PEOPLE[:n]):
        Image.new("RGB", (500, 375) if wide else (400, 500), (60 + 20 * i, 110, 200 - 15 * i)).save(matched / f"{h}-0.jpg")
        people.append({"rank": i + 1, "handle": h, "signals": {"their_comments": 12 - i}, "stretch": {"months": [i + 1], "label": when},
                       "line": {"text": said, "from": "their comment"}})
        told.append({"rank": i + 1, "handle": h, "when": when, "where": where, "line": said})
        cast[h] = [{"file": f"matched/{h}-0.jpg", "point": [0.5, 0.35], "face": [0.4, 0.2, 0.6, 0.42]} if wide else
                   {"file": f"matched/{h}-0.jpg", "point": [0.5, 0.45]}]
        aspects[f"{h}-0"] = 0.75 if wide else 1.25
    Image.new("RGB", (500, 375), (180, 140, 90)).save(matched / "group.jpg")
    heads = {h: [0.2 + 0.2 * i, 0.35] for i, (h, *_) in enumerate(PEOPLE[:4])}
    Path(d, "people.json").write_text(json.dumps({"handle": "maren.okafor", "year": 2026, "people": people}))
    Path(d, "taste.json").write_text(json.dumps({"handle": "maren.okafor", "year": 2026, "register": {"lowercase": True}, "people": told}))
    Path(d, "cast.json").write_text(json.dumps({"group": {"file": "matched/group.jpg", "point": [0.5, 0.4], "heads": heads}, "people": cast}))
    (matched / "aspects.json").write_text(json.dumps(aspects))


class ManyPeople(unittest.TestCase):
    def setUp(self):
        board_drive.use("scrapbook", swatches=SWATCHES)

    boards = {}

    @classmethod
    def made(cls, n, wide=False):
        """The scrapbook storyboard drafted for n people and laid out in every format: (storyboard, {kind: board})."""
        if (n, wide) not in cls.boards:
            here = os.getcwd()
            with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
                os.chdir(d)
                try:
                    run_folder(d, n, wide)
                    ctx = boards.Ctx()
                    sb = boards.draft("scrapbook", ctx)
                    cls.boards[n, wide] = (sb, {k: boards.layout(sb, ctx, k) for k in ("reel", "square", "wide")})
                finally:
                    os.chdir(here)
        return cls.boards[n, wide]

    @staticmethod
    def wall(board):
        """The closer's wall in a laid-out board: (its height, its slices)."""
        closer = board["beats"][-1]
        route = next(x for x in closer["layers"] if x["kind"] == "Route")
        return route.get("height", board["format"]["height"]), [x for x in closer["layers"] if x["kind"] == "Slice"]

    def test_a_large_face_at_the_foot_keeps_the_wide_wall_in_the_frame(self):
        """Five people whose landscape photographs cast.py match laid whole across 9:16 pictures, the last with a face
        as tall as a third of their photograph: in 16:9 the wall stands the frame's height, every slice inside it, and
        the last print stands smaller than the frame's width rather than pushing the rows over it out of the frame."""
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                run_folder(d, 5)
                aspects = {h: {"aspect": 1.7778, "band": [0.285, 0.715]} for h in (f"{p[0]}-0" for p in PEOPLE[:5])}
                aspects["group"] = 0.75
                Path(d, "public", "matched", "aspects.json").write_text(json.dumps(aspects))
                cast = json.loads(Path(d, "cast.json").read_text())
                for h, *_ in PEOPLE[:5]:
                    cast["people"][h] = [{"file": f"matched/{h}-0.jpg", "point": [0.5, 0.45]}]
                cast["people"][PEOPLE[4][0]] = [{"file": f"matched/{PEOPLE[4][0]}-0.jpg", "point": [0.6, 0.42],
                                                 "face": [0.44, 0.25, 0.75, 0.62]}]
                Path(d, "cast.json").write_text(json.dumps(cast))
                ctx = boards.Ctx()
                board = boards.layout(boards.draft("scrapbook", ctx), ctx, "wide")
            finally:
                os.chdir(here)
        height, slices = self.wall(board)
        self.assertEqual(height, 1080)
        self.assertEqual(len(slices), 5)
        self.assertTrue(all(max(y for _, y in s["poly"]) > 0 and min(y for _, y in s["poly"]) < 1080 for s in slices))
        self.assertEqual(board_drive.problems(board), [])

    def test_six_named_people_make_six_cards_and_a_wall_of_all_six(self):
        sb, laid = self.made(6)
        handles = [h for h, *_ in PEOPLE[:6]]
        self.assertEqual(sb["people"], handles)
        self.assertEqual([b["person"] for b in sb["beats"] if b["comp"] == "person"], handles)
        height, slices = self.wall(laid["reel"])
        self.assertEqual(sorted(s["owner"] for s in slices), list(range(1, 7)))
        self.assertTrue(all(s.get("tag") for s in slices))
        self.assertGreaterEqual(height, 1920)
        self.assertEqual(board_drive.problems(laid["reel"]), [])

    def test_eight_and_twelve_people_keep_every_one_in_every_format(self):
        for n in (8, 12):
            sb, laid = self.made(n)
            self.assertEqual(len(sb["people"]), n)
            self.assertEqual(sum(b["comp"] == "person" for b in sb["beats"]), n)
            for kind, board in laid.items():
                with self.subTest(people=n, format=kind):
                    height, slices = self.wall(board)
                    self.assertEqual(sorted(s["owner"] for s in slices), list(range(1, n + 1)))
                    self.assertEqual(board_drive.problems(board), [])
            self.assertGreater(self.wall(laid["reel"])[0], 1920)

    @unittest.skipUnless(ESBUILD.exists(), "the studio's node modules are not installed")
    def test_the_camera_runs_down_the_wall_with_the_tag_and_rests_on_its_foot(self):
        cases = [(6, False), (8, False), (12, False), (7, True), (12, True)]
        laid = [self.made(n, wide)[1][k] for n, wide in cases for k in ("reel", "square", "wide")]
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            entry, bundle, data = Path(d) / "wall.ts", Path(d) / "wall.mjs", Path(d) / "boards.json"
            drive = MOTION / "studio" / "drive"
            entry.write_text(SCRIPT % (json.dumps(str(drive / "plan.ts")), json.dumps(str(drive / "camera.ts"))))
            subprocess.run([str(ESBUILD), str(entry), "--bundle", "--platform=node", "--format=esm", f"--outfile={bundle}",
                            "--log-level=error", "--resolve-extensions=.ts,.tsx,.js"], check=True, cwd=MOTION)
            data.write_text(json.dumps(laid))
            r = subprocess.run(["node", str(bundle), str(data)], capture_output=True, text=True, check=True)
        grown = 0
        for i, w in enumerate(json.loads(r.stdout)):
            F = L.Frame(w["kind"])
            grown += w["height"] > F.H
            with self.subTest(format=w["kind"], people=cases[i // 3]):
                self.assertAlmostEqual(w["height"], self.wall(laid[i])[0], places=3)
                _, top, _, bottom = w["safe"]
                for y0, y1 in w["seen"]:
                    self.assertTrue(top - 0.5 <= y0 and y1 <= bottom + 0.5,
                                    f"a wall tag lands from y {y0:.0f} to {y1:.0f} on screen, past the safe area's {top} to {bottom}")
                self.assertAlmostEqual(w["rest"][0], w["height"] - F.H / 2, places=3)
                self.assertAlmostEqual(w["rest"][1], F.H, places=3)
        self.assertGreaterEqual(grown, 2)

    def test_no_two_moves_in_a_row_are_the_same(self):
        """Every beat, the hook and the closer too, makes a move from its card's allowlist, never the move the beat before
        it made."""
        allowed = {m["id"] for m in board_drive.look().card["moves"]}
        for n in (6, 12):
            beats = self.made(n)[1]["reel"]["beats"]
            kinds = [b["move"] for b in beats]
            with self.subTest(people=n):
                self.assertEqual(len(kinds), n + 2)
                self.assertTrue(set(kinds) <= allowed, kinds)
                self.assertEqual([a for a, b in zip(kinds, kinds[1:]) if a == b], [])

    def test_no_stamp_on_the_wall_covers_a_face(self):
        """Seven people, each in a 4:3 photograph whose face stands high in it: every stamp hangs on the wall clear of
        every face its cast names, in every format."""
        for kind, board in self.made(7, True)[1].items():
            closer = board["beats"][-1]["layers"]
            faces = [[x + f0 * w, y + f1 * h, x + f2 * w, y + f3 * h] for s in closer if s["kind"] == "Slice"
                     for (x, y, w, h), (f0, f1, f2, f3) in [(s["place"], s["photo"]["face"])]]
            stamps = [board_drive.hull(board_drive.turned(board_drive.box(ln, ink=True), ln)) for w in closer
                      if w["kind"] == "Words" for ln in w["lines"] if ln.get("name", "").startswith("stamp-")]
            with self.subTest(format=kind):
                self.assertEqual(len(stamps), 7)
                self.assertEqual([(s, f) for s in stamps for f in faces
                                  if s[0] < f[2] and f[0] < s[2] and s[1] < f[3] and f[1] < s[3]], [])

    def test_a_group_photograph_with_no_head_named_opens_on_every_persons_tag(self):
        """Where the cast names no head in the photograph of them together, the hook still opens on it, with every
        person's tag in the film's order standing whole in the frame: no tag points at a stranger."""
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                run_folder(d, 5)
                cast = json.loads(Path(d, "cast.json").read_text())
                del cast["group"]["heads"]
                Path(d, "cast.json").write_text(json.dumps(cast))
                ctx = boards.Ctx()
                for kind in ("reel", "square", "wide"):
                    F = board_drive.lensed(L.Frame(kind))
                    _, role, layers = board_drive.hook(F, ctx)
                    tags = [t for x in layers if x["kind"] == "Tags" for t in x["tags"]]
                    with self.subTest(format=kind):
                        self.assertEqual(role, "group")
                        self.assertEqual([t["text"] for t in tags], [f"@{h}" for h, *_ in PEOPLE[:5]])
                        self.assertTrue(all(board_drive.in_frame(F, t) for t in tags))
            finally:
                os.chdir(here)


class Length(unittest.TestCase):
    def test_the_cut_may_run_four_seconds_longer_for_each_person_after_the_fifth(self):
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                for n, most in ((1, 30), (5, 30), (6, 34), (8, 42)):
                    Path(d, "film.json").write_text(json.dumps({"storyboard": {"people": [h for h, *_ in PEOPLE[:n]]}}))
                    self.assertEqual(qa.longest(), most)
            finally:
                os.chdir(here)


class Description(unittest.TestCase):
    def test_the_description_fits_the_catalog_and_keeps_every_trigger(self):
        head = (KIT / "SKILL.md").read_text().split("---")[1]
        desc = json.loads(re.search(r"^description: (\".*\")$", head, re.M).group(1))
        self.assertLessEqual(len(desc), 1024)
        for t in TRIGGERS:
            self.assertIn(f"'{t}'", desc)
        self.assertIn("never answer with a plan or a list of ideas", desc)
        self.assertIn("which of three looks", desc)


if __name__ == "__main__":
    unittest.main()
