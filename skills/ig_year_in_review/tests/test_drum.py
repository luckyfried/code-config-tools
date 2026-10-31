"""A count's drums, from motion/system/three/Type3D.tsx bundled with the kit's own esbuild: at the end of a roll every
column of the end number is drawn and stands on its digit, including a column the start number lacks (380 to 3010,
38 to 3010) and a column whose end digit equals the blank it arrives from.

    python3 -I -m unittest discover -s S/tests
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MOTION = Path(__file__).resolve().parents[1] / "motion"
CASES = [(380, 3010), (38, 3010), (9, 131), (0, 9), (99, 100), (122, 131), (5, 1005)]

ENTRY = """import {drum, digitsOf} from %s;
const cases = %s;
const out = cases.map(([from, to]) => {
  const n = digitsOf(to);
  return {from, to, cols: Array.from({length: n}, (_, i) => {
    const d = drum({from, to, p: [1]}, i, n, 1);
    const lead = (v) => i > 0 && i >= digitsOf(v);
    const whole = Math.floor(d.pos + 1e-9);
    return {digit: (d.a + whole) %% 10, drawn: !(whole === 0 && lead(from)) && !(whole === d.span && lead(to))};
  })};
});
console.log(JSON.stringify(out));
"""


class Drum(unittest.TestCase):
    def test_every_column_of_the_end_number_lands_drawn_on_its_digit(self):
        esbuild = MOTION / "node_modules/.bin/esbuild"
        if not esbuild.exists():
            self.skipTest("motion/node_modules is not installed")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            entry, bundle = Path(tmp) / "entry.mjs", Path(tmp) / "bundle.mjs"
            entry.write_text(ENTRY % (json.dumps(str(MOTION / "system/three/Type3D.tsx")), json.dumps(CASES)))
            r = subprocess.run([str(esbuild), str(entry), "--bundle", "--platform=node", "--format=esm", "--log-level=error",
                                f"--outfile={bundle}"], cwd=MOTION, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            r = subprocess.run(["node", str(bundle)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
        for case in json.loads(r.stdout):
            shown = "".join(str(c["digit"]) if c["drawn"] else " " for c in reversed(case["cols"]))
            self.assertEqual(shown, str(case["to"]), f"{case['from']} to {case['to']}")


if __name__ == "__main__":
    unittest.main()
