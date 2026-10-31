"""A move hands the frame back onto the card's own print: every photo beat the moves are given carries the print as its
card draws it (a print taped in its border turns the card's tilt, each other card the other way, in its border and
under its tape; a photograph that is not a taped print hangs level and bare), and a move that takes the frame lands on
the print where the camera sees it as the move hands the frame back. The camera holding a card pushes in toward the
person and keeps the picture on the photograph, so that is not the print's place on the card, and the shared moves,
which draw the print at the beat's box and place, are given the place the camera sees. A cut into the closer turns
onto the wall the scene draws.

    python3 -I -m unittest discover -s S/tests -p test_landing.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "tests"))
import board_drive  # noqa: E402
import boards  # noqa: E402
from test_many_people import ESBUILD, NODE_ENV, PEOPLE, SWATCHES, run_folder  # noqa: E402

MOTION = KIT / "motion"
# per photo beat of each board: the tilt, box, place, rim and tape the moves get, its card's index, band and mount, the
# card's print tilt, rim and tape, its flight, and where the camera sees its print as a move that takes the frame hands back
SCRIPT = """
import {readFileSync} from 'fs';
import {planOf} from %s;
import {landed, printAt} from %s;
import {opensOnto} from %s;
const out = [];
for (const board of JSON.parse(readFileSync(process.argv[2], 'utf8'))) {
  const plan = planOf(board), seen = landed(board, plan), pic = plan.photo.picture;
  for (const b of seen.over.beats) {
    const i = plan.cards.findIndex((c) => c.key === b.id);
    if (i < 0 || !b.box) continue;
    const c = plan.cards[i];
    const fly = board.beats.find((x) => x.id === b.id).layers.find((l) => l.kind === 'Cut').fly ?? 0;
    out.push({id: b.id, i, tilt: b.tilt, box: b.box, place: b.place, band: c.band, mount: c.mount, card: c.place,
      picTilt: pic.tilt, picRim: pic.rim, picTape: pic.tape, rim: b.rim, tape: b.tape, fly, at: fly ? printAt(plan, i, c.arrive + fly - 0.19 / plan.beat) : null});
  }
}
const closers = JSON.parse(readFileSync(process.argv[2], 'utf8')).map((board) => {
  const plan = planOf(board);
  const over = plan.over.beats.find((b) => b.id === 'closer');
  return {line: plan.line.beats.find((b) => b.id === 'closer').form, over: over.form, opens: opensOnto(plan.look, over)};
});
const safes = JSON.parse(readFileSync(process.argv[2], 'utf8')).map((board) => {
  const plan = planOf(board);
  return {W: plan.W, H: plan.H, box: plan.safe, look: plan.look.safe};
});
console.log(JSON.stringify({beats: out, closers, safes}));
"""


def laid(look, n, framed):
    """`look`'s board for n people in 9:16, 1:1 and 16:9; with `framed`, each person's photograph a landscape print the
    look frames on its card."""
    here = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
        os.chdir(d)
        try:
            run_folder(d, n)
            if framed:
                aspects = {f"{h}-0": {"aspect": 1.7778, "band": [0.285, 0.715]} for h, *_ in PEOPLE[:n]}
                aspects["group"] = 0.75
                Path(d, "public", "matched", "aspects.json").write_text(json.dumps(aspects))
            board_drive.use(look, swatches=SWATCHES)
            ctx = boards.Ctx()
            sb = boards.draft(look, ctx)
            return [boards.layout(sb, ctx, k) for k in ("reel", "square", "wide")]
        finally:
            os.chdir(here)


@unittest.skipUnless(ESBUILD.exists(), "the studio's node modules are not installed")
class Landing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases = laid("scrapbook", 5, True) + laid("scrapbook", 5, False) + laid("editorial-quiet", 5, False)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            entry, bundle, data = Path(d) / "landing.ts", Path(d) / "landing.mjs", Path(d) / "boards.json"
            drive = MOTION / "studio" / "drive"
            entry.write_text(SCRIPT % (json.dumps(str(drive / "plan.ts")), json.dumps(str(drive / "camera.ts")),
                                       json.dumps(str(MOTION / "system" / "moves" / "arrival.tsx"))))
            subprocess.run([str(ESBUILD), str(entry), "--bundle", "--platform=node", "--format=esm", f"--outfile={bundle}",
                            "--log-level=error", "--resolve-extensions=.ts,.tsx,.js"], check=True, cwd=MOTION, env=NODE_ENV)
            data.write_text(json.dumps(cases))
            r = subprocess.run(["node", str(bundle), str(data)], capture_output=True, text=True, check=True)
        got = json.loads(r.stdout)
        cls.beats, cls.closers, cls.safes = got["beats"], got["closers"], got["safes"]

    def test_every_photo_beat_carries_its_print_as_the_card_draws_it(self):
        """A print taped in its border hangs at the card's tilt (each other card the other way), in a border the card's
        share of its width, under the card's strips of tape; a photograph that is not one lands bare and level, so
        the move never ends on a rim or tape the card does not draw."""
        taped = 0
        for b in self.beats:
            with self.subTest(beat=b["id"]):
                for k in ("tilt", "rim", "tape"):
                    self.assertIsInstance(b[k], (int, float), f"a beat with no {k} lands at the look's print {k}")
                if b["band"] and b["mount"] not in ("projected", "flat") and b["picRim"] > 0:
                    taped += b["picTilt"] != 0
                    self.assertEqual(b["tilt"], (-1 if b["i"] % 2 else 1) * b["picTilt"])
                    (bx, _, bw, _), (px, _, pw, _) = b["box"], b["place"]
                    self.assertAlmostEqual(b["rim"], b["picRim"] * (min(bx + bw, px + pw) - max(bx, px)), places=3)
                    self.assertEqual(b["tape"], min(2, b["picTape"]))
                else:
                    self.assertEqual((b["tilt"], b["rim"]), (0, 0))
                    if not b["band"]:
                        self.assertEqual(b["tape"], 0)
        self.assertGreater(taped, 0, "no taped print turned on its card was laid")
        self.assertTrue(any(b["rim"] == 0 for b in self.beats), "no bare photograph was laid")

    def test_a_cut_into_the_wall_turns_onto_the_scenes_own_wall(self):
        """The cuts drawn over the scene meet the closer as the wall it is, and the shared arrival draws no frame for
        it, so a cut into the wall shows the wall the scene draws and never a stand-in drawn over it."""
        self.assertTrue(self.closers)
        for c in self.closers:
            self.assertEqual(c, {"line": "wall", "over": "wall", "opens": False})

    def test_the_moves_are_handed_the_formats_safe_area(self):
        """The look the shared moves read carries the format's safe area as px in from each edge, so a move lays its
        words inside it and never at the grid's margin."""
        self.assertTrue(self.safes)
        for c in self.safes:
            x0, y0, x1, y1 = c["box"]
            self.assertEqual(c["look"], {"left": x0, "top": y0, "right": c["W"] - x1, "bottom": c["H"] - y1})
            self.assertGreater(c["look"]["top"], 0, "the reel's safe area starts under the frame's top")

    def test_a_move_that_takes_the_frame_lands_where_the_camera_sees_the_print(self):
        flown = [b for b in self.beats if b["fly"]]
        self.assertTrue(flown, "no move that takes the frame was laid")
        for b in flown:
            with self.subTest(beat=b["id"]):
                for got, want in zip(b["box"] + b["place"], b["at"]["box"] + b["at"]["place"]):
                    self.assertAlmostEqual(got, want, places=3)
        # the camera that holds the card is not at the card's own frame when the move hands back
        moved = [b for b in flown if max(abs(p - q) for p, q in zip(b["place"], b["card"])) > 1]
        self.assertTrue(moved, "every landing stood at its place on the card")


if __name__ == "__main__":
    unittest.main()
