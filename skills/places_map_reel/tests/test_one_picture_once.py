"""A photograph posted on two visits of one place is shown once: the second visit leads with the place's next best.

    python3 -I -m unittest discover -s S/tests -p test_one_picture_once.py
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import grade  # noqa: E402
import picks  # noqa: E402


class OnePictureOnce(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        # the river at dusk posted on both visits under two names, and three other photographs of the place
        self.f = {}
        for name, picture in (("dusk-march", b"river at dusk"), ("dusk-sept", b"river at dusk"),
                              ("bridge", b"bridge"), ("tower", b"tower"), ("lanes", b"lanes")):
            self.f[name] = str(d / f"{name}.jpg")
            Path(self.f[name]).write_bytes(picture)

    def test_the_second_visit_does_not_repeat_the_picture_the_first_showed(self):
        f = self.f
        pl = {"route_visits": [{"place": "porto"}, {"place": "porto"}]}
        options = {"porto": [(f["dusk-march"], ""), (f["bridge"], ""), (f["tower"], ""), (f["lanes"], "")]}
        moments = [{"place": "porto", "n": 1, "photo": f["dusk-march"]}, {"place": "porto", "n": 2, "photo": f["dusk-sept"]}]
        wrote = {}
        with mock.patch.object(picks._env, "read_json", return_value=None), \
                mock.patch.object(picks._env, "write_json", side_effect=lambda name, v: wrote.update({name: v})), \
                mock.patch.object(picks, "contact"):
            picks.write_cast(pl, options, None, moments)
        first, second = ([Path(s).name for s in v["shots"]] for v in wrote["cast.json"]["visits"])
        self.assertEqual(first, ["dusk-march.jpg", "bridge.jpg"])
        self.assertEqual(second, ["tower.jpg", "lanes.jpg"])

    def test_the_grade_does_not_set_the_repeated_print_back_before_the_second_visit(self):
        f = self.f
        cast = {"visits": [{"place": "porto", "n": 1, "shots": [f["dusk-march"], f["bridge"]]},
                           {"place": "porto", "n": 2, "shots": [f["tower"], f["lanes"]]}]}
        own = {("porto", 1): f["dusk-march"], ("porto", 2): f["dusk-sept"]}
        first, second = ([Path(s["file"]).name for s in v] for v in grade.cast_shots(cast, own))
        self.assertEqual(first, ["dusk-march.jpg", "bridge.jpg"])
        self.assertEqual(second, ["tower.jpg", "lanes.jpg"])

    def test_a_new_picture_on_the_second_visit_still_leads_it(self):
        f = self.f
        cast = {"visits": [{"place": "porto", "n": 1, "shots": [f["dusk-march"]]},
                           {"place": "porto", "n": 2, "shots": [f["tower"]]}]}
        own = {("porto", 1): f["dusk-march"], ("porto", 2): f["lanes"]}
        _, second = ([Path(s["file"]).name for s in v] for v in grade.cast_shots(cast, own))
        self.assertEqual(second, ["lanes.jpg", "tower.jpg"])


if __name__ == "__main__":
    unittest.main()
