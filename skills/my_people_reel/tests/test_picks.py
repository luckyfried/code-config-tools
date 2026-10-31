"""picks.py on a sparse year: five people with a photograph each and two group photographs between them gives a wall
of the photographs there are, fewer than nine, and passes; only a person with no photograph fails it.

    python3 -I -m unittest discover -s S/tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

KIT = Path(__file__).resolve().parents[1]
PEOPLE = ["ana.b", "bo.c", "cy.d", "di.e", "ed.f"]


class Picks(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.ws)
        run = self.ws / "build" / "r1"
        run.mkdir(parents=True)
        (self.ws / "build" / "current").write_text("r1\n")
        posts, photos = [], {h: [] for h in PEOPLE}

        def post(name, ts, who, shade):
            src = str(self.ws / f"{name}.jpg")
            Image.new("RGB", (400, 500), (shade, 120, 255 - shade)).save(src)
            posts.append({"ts": ts, "media": [src], "tagged": who, "caption": f"with @{who[0]}"})
            for h in who:
                photos[h].append({"src": src, "ts": ts, "caption": f"with @{who[0]}", "with": [x for x in who if x != h],
                                  "kind": "post", "owner": "me"})
        for i, h in enumerate(PEOPLE):
            post(f"p{i}", 1770000000 + i * 86400, [h], 40 * i)
        post("g0", 1780000000, PEOPLE[:3], 30)
        post("g1", 1781000000, PEOPLE[2:], 200)
        (run / "library.json").write_text(json.dumps({"posts": posts, "stories": [], "tagged_in": []}))
        (run / "people.json").write_text(json.dumps({"people": [{"handle": h, "rank": i + 1, "photos": photos[h]}
                                                                 for i, h in enumerate(PEOPLE)]}))
        self.run_dir = run

    def picks(self):
        env = dict(os.environ, MPR_WORKSPACE=str(self.ws))
        env.pop("MPR_RUN", None)
        return subprocess.run([sys.executable, "-I", str(KIT / "scripts" / "picks.py")], cwd=self.ws, env=env,
                              capture_output=True, text=True)

    def test_a_wall_of_fewer_than_nine_passes(self):
        done = self.picks()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        out = json.loads((self.run_dir / "picks.json").read_text())
        self.assertEqual([x["handle"] for x in out["people"]], PEOPLE)
        self.assertLess(len(out["wall"]), 9)


if __name__ == "__main__":
    unittest.main()
