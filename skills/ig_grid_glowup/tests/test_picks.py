"""The photo picks when the grid cannot be measured: a named photo folder beside a grid whose posts point at photos
that are not there still ranks every named photograph into picks.json, and every grid cell carries its flags. The exit
code says whether there is anything to post: a grid of fewer than nine posts with photos to post is a pass, and a
folder with no photo that can be posted is a refusal in one plain sentence. A folder of photos with no feed export
beside it, named or found, is the pool and the grid is empty.

    python3 -I -m unittest discover -s S/tests -p test_picks.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import gather  # noqa: E402
import picks  # noqa: E402

TS = 1792698717


class Picks(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.dir, True)
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.dir)

    def test_a_grid_with_no_photo_to_measure_still_ranks_the_named_photos(self):
        from PIL import Image
        folder = self.dir / "named"
        folder.mkdir()
        named = []
        for i, rgb in enumerate(((180, 120, 90), (90, 140, 170), (200, 170, 60))):
            p = folder / f"next-{i}.jpg"
            Image.new("RGB", (400, 500), rgb).save(p)
            named.append({"ts": TS + i, "caption": "", "media": [str(p)]})
        # an export's posts whose media files are not there: gather keeps them on the grid with no photo
        grid = [{"pos": i, "kind": "post", "ts": TS - i, "caption": "", "media": [], "likes": 10, "comments": 1}
                for i in range(9)]
        _env.write_json("library.json", {"source": "export", "grid": grid, "posts": grid, "stories": [], "facebook": [],
                                         "photos": named})
        with mock.patch.object(_env, "enter_run", lambda new=False: None), \
                mock.patch.object(sys, "argv", ["picks.py"]), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            code = picks.main()
        self.assertEqual(code, 0)
        out = json.loads(Path("picks.json").read_text())
        self.assertEqual(sorted(e["src"] for e in out["pool"]), sorted(r["media"][0] for r in named))
        fits = [e["fit"] for e in out["pool"]]
        self.assertEqual(fits, sorted(fits, reverse=True))
        cells = json.loads(Path("grid.json").read_text())["cells"]
        self.assertEqual([c["flags"] for c in cells], [[]] * 9)

    def photos(self, name, colors):
        from PIL import Image
        folder = self.dir / name
        folder.mkdir()
        out = []
        for i, rgb in enumerate(colors):
            p = folder / f"{name}-{i}.jpg"
            Image.new("RGB", (80, 100), rgb).save(p)
            out.append(str(p))
        return out

    def picks(self, grid_media, named):
        """picks.main on an export of one post per grid file beside a folder of named photos: (code, stdout, stderr)."""
        grid = [{"pos": i, "kind": "post", "ts": TS - i, "caption": "", "media": [m], "likes": 10, "comments": 1}
                for i, m in enumerate(grid_media)]
        photos = [{"ts": TS + i, "caption": "", "media": [m]} for i, m in enumerate(named)]
        _env.write_json("library.json", {"source": "export", "grid": grid, "posts": grid, "stories": [], "facebook": [],
                                         "photos": photos})
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(_env, "enter_run", lambda new=False: None), \
                mock.patch.object(sys, "argv", ["picks.py"]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = picks.main()
        return code, out.getvalue(), err.getvalue()

    def test_a_grid_of_five_posts_with_photos_to_post_passes(self):
        grid = self.photos("grid", ((150, 110, 80), (120, 130, 100), (170, 140, 110), (100, 90, 70), (140, 120, 90)))
        named = self.photos("named", ((180, 120, 90), (90, 140, 170), (200, 170, 60)))
        code, out, err = self.picks(grid, named)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(json.loads(Path("grid.json").read_text())["cells"]), 5)
        self.assertEqual(sorted(e["src"] for e in json.loads(Path("picks.json").read_text())["pool"]), sorted(named))

    def test_a_folder_with_no_photo_that_can_be_posted_is_refused_in_one_sentence(self):
        grid = self.photos("grid", [(60 + 15 * i, 110, 160 - 10 * i) for i in range(9)])
        named = self.photos("named", ((250, 250, 250), (5, 5, 5)))
        code, out, err = self.picks(grid, named)
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(Path("picks.json").read_text())["pool"], [])
        self.assertIn("no photo in the folder can be posted", (out + err).lower())

    def test_a_folder_with_no_feed_export_is_the_pool_and_the_grid_is_empty(self):
        import colorsys
        from PIL import Image
        colors = [tuple(int(v * 255) for v in colorsys.hsv_to_rgb(i / 12, 0.6, 0.8)) for i in range(12)]
        for name, args in (("named", ["--photos", "trip"]), ("found", [])):
            with self.subTest(name):
                ws = self.dir / name
                (ws / "trip").mkdir(parents=True)
                os.chdir(ws)
                folder = [ws / "trip" / f"{i:02d}.jpg" for i in range(len(colors))]
                for f, rgb in zip(folder, colors):
                    Image.new("RGB", (80, 100), rgb).save(f)
                out = io.StringIO()
                with mock.patch.object(_env, "HOME", ws), mock.patch.object(_env, "enter_run", lambda new=False: None), \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                    with mock.patch.object(sys, "argv", ["gather.py"] + args):
                        self.assertEqual(gather.main(), 0, out.getvalue())
                    with mock.patch.object(sys, "argv", ["picks.py"]):
                        code = picks.main()
                lib = json.loads(Path("library.json").read_text())
                self.assertEqual(lib["grid"], [])
                self.assertEqual(sorted(Path(r["media"][0]).resolve() for r in lib["photos"]), [f.resolve() for f in folder])
                self.assertEqual(code, 0, out.getvalue())
                self.assertEqual(json.loads(Path("grid.json").read_text())["cells"], [])
                self.assertEqual(len(json.loads(Path("picks.json").read_text())["pool"]), 12)


if __name__ == "__main__":
    unittest.main()
