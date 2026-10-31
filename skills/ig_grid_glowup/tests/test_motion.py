"""The motion system's pure modules, tested by node's own runner."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

DRIVE = Path(__file__).resolve().parents[1] / "motion" / "studio" / "drive"

# plan.ts takes one value from the renderer, staticFile, which names a file in public/ as the bundle serves it (a path
# from the root). The shipped kit carries no motion/node_modules, so the test resolves `remotion` to that one function,
# the renderer's own rule outside a browser, and plan.ts runs as it is with nothing installed.
STUB = "export const staticFile = (p) => '/' + p.replace(/^\\/+/, '');\n"
HOOKS = """import {registerHooks} from 'node:module';
const stub = new URL('./remotion.mjs', import.meta.url).href;
registerHooks({resolve: (spec, ctx, next) => (spec === 'remotion' ? {url: stub, shortCircuit: true} : next(spec, ctx))});
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestMotion(unittest.TestCase):
    def test_drive_plan(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "remotion.mjs").write_text(STUB)
            (Path(d) / "hooks.mjs").write_text(HOOKS)
            r = subprocess.run(["node", "--no-warnings", "--import", (Path(d) / "hooks.mjs").as_uri(), "--test", "--test-reporter=tap",
                                str(DRIVE / "plan.test.ts")],
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("\n# fail 0\n", r.stdout)
        self.assertRegex(r.stdout, r"\n# pass [1-9]\d*\n")


if __name__ == "__main__":
    unittest.main()
