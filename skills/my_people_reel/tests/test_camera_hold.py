"""The camera's hold on a person's card keeps both of its bounds from the arrival to the leave, in every format: the
picture stays on the card's photograph, and the card's type, laid where board_drive lays it (inside the safe area as
the lens sees type standing in front of the photograph), stays inside the format's safe area as the lens sees it. The
cards are the hard ones: a photograph that just fills the frame, the type filling the whole of that area, one side of it
or a small part of its middle, and the tag in the far corner pulling the camera away from the type.

    python3 -I -m unittest discover -s S/tests
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
import board_drive  # noqa: E402
import layout as L  # noqa: E402

# the photographs' colors the scrapbook card's palette rule makes the board's colors from
SWATCHES = ["#c2763a", "#2f5d7c", "#e9dcc4", "#3a2a20"]


MOTION = KIT / "motion"
ESBUILD = MOTION / "node_modules" / ".bin" / "esbuild"
# for each case, the most the picture runs past the photograph and the most the type runs past the safe area, in
# picture px, over the hold
SCRIPT = """
import {readFileSync} from 'fs';
import {heldOf} from %s;
import {liftOf, typeZ} from %s;
const out = [];
for (const {plan, card} of JSON.parse(readFileSync(process.argv[2], 'utf8'))) {
  const {W, H} = plan, [L, T, R, B] = plan.safe, [px, py, pw, ph] = card.place, [x0, y0, x1, y1] = card.keep;
  let photo = 0, safe = 0;
  for (let i = 0; i <= 20; i++) {
    const f = heldOf(plan, card, i / 20);
    const hw = (f.h * W) / H / 2, hh = f.h / 2;
    photo = Math.max(photo, (Math.max(px - (f.c[0] - hw), f.c[0] + hw - (px + pw), py - (f.c[1] - hh), f.c[1] + hh - (py + ph)) * H) / f.h);
    const k = H / (f.h - 2 * (typeZ(card) - liftOf(card)) * Math.tan((f.fov * Math.PI) / 360));
    const sx = (x) => W / 2 + k * (x - f.c[0]), sy = (y) => H / 2 + k * (y - f.c[1]);
    safe = Math.max(safe, L - sx(x0), sx(x1) - R, T - sy(y0), sy(y1) - B);
  }
  out.push([photo, safe]);
}
console.log(JSON.stringify(out));
"""


def cases(kind):
    """The hard cards in format `kind`: the type over the whole safe area board_drive lays it in, over its left, right,
    top or bottom left part, or small in its middle, each with the tag's tip in a corner away from it."""
    F = L.Frame(kind)
    G = board_drive.lensed(F)
    l, t, r, b = G.left, G.top, G.right, G.bottom
    mx, my = (l + r) / 2, (t + b) / 2
    plan = {"W": F.W, "H": F.H, "safe": list(board_drive.safe_box(F))}
    out = []
    for keep, tip in (([l, t, r, b], [r, b]), ([l, t, mx, b], [r, b]), ([mx, t, r, b], [l, b]), ([l, t, r, my], [l, b]),
                      ([l, my, mx, b], [r, t]), ([mx - 100, my - 100, mx + 100, my + 100], [r, b])):
        out.append({"plan": plan, "card": {"T": {"s": 1, "o": [0, 0]}, "place": [0, 0, F.W, F.H], "field": "photo",
                                           "keep": keep, "tags": [{"tip": tip}], "hook": False}})
    return out


@unittest.skipUnless(ESBUILD.exists(), "the studio's node modules are not installed")
class CameraHold(unittest.TestCase):
    def setUp(self):
        board_drive.use("scrapbook", swatches=SWATCHES)

    def test_the_hold_keeps_the_picture_on_the_photograph_and_the_type_in_the_safe_area(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            entry, bundle, data = Path(d) / "hold.ts", Path(d) / "hold.mjs", Path(d) / "cases.json"
            drive = MOTION / "studio" / "drive"
            entry.write_text(SCRIPT % (json.dumps(str(drive / "camera.ts")), json.dumps(str(drive / "card.tsx"))))
            subprocess.run([str(ESBUILD), str(entry), "--bundle", "--platform=node", "--format=esm", f"--outfile={bundle}",
                            "--log-level=error", "--resolve-extensions=.ts,.tsx,.js"], check=True, cwd=MOTION)
            kinds = ("reel", "square", "wide")
            data.write_text(json.dumps([c for k in kinds for c in cases(k)]))
            r = subprocess.run(["node", str(bundle), str(data)], capture_output=True, text=True, check=True)
        found = json.loads(r.stdout)
        n = len(found) // len(kinds)
        for i, (photo, safe) in enumerate(found):
            with self.subTest(format=kinds[i // n], card=i % n):
                self.assertLessEqual(photo, 0.5)
                self.assertLessEqual(safe, 0.5)


if __name__ == "__main__":
    unittest.main()
