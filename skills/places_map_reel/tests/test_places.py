"""places.py keeps the person's own spelling of a place: the name they write in their captions stands on the map and
in every caption over the gazetteer's, and --rename takes the name as they type it. A check-in or a photo's file name
puts its place on the map without a geotag, a place they add at its coordinates takes the rows that name it (a pair
that is not a latitude and a longitude, or one written the wrong way round, is refused), and a
place with no photograph of theirs is named before a draft. gather.py keeps the handle they give without its "@", and
with every door closed writes the run's brief.md beside out/.

    python3 -I -m unittest discover -s S/tests
"""
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
import places  # noqa: E402

DAY = 86400 * (365 * 56 + 14)  # 2026-01-01


def post(day, caption, lat, lon):
    return {"ts": DAY + 86400 * day, "caption": caption, "media": [f"{day}.jpg"], "lat": lat, "lon": lon}


LISBON, FEZ = (38.72, -9.14), (34.06, -5.00)


class TheirSpelling(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        self.addCleanup(os.chdir, here)
        self.home = Path(tmp.name)
        (self.home / "build" / "r").mkdir(parents=True)
        (self.home / "build" / "RUN").write_text("r\n")
        patch = mock.patch.object(places._env, "HOME", self.home)
        patch.start()
        self.addCleanup(patch.stop)

    def run_places(self, posts, *args):
        (self.home / "build" / "r" / "library.json").write_text(json.dumps({"year": 2026, "bio": "Lisbon", "posts": posts}))
        with mock.patch.object(sys, "argv", ["places.py", *args]), mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            places.main()
        return {p["id"]: p for p in json.loads((self.home / "build" / "r" / "places.json").read_text())["places"]}

    def test_their_spelling_stands_and_rename_takes_the_name_as_typed(self):
        # their captions say Fes where the gazetteer says Fez: Fes stands, at Fez's coordinates
        got = self.run_places([post(1, "home", *LISBON), post(40, "lost in the medina in Fes", *FEZ),
                               post(41, "mint tea in Fes again", *FEZ)])
        self.assertEqual(got["fes"]["name"], "Fes")
        self.assertEqual((got["fes"]["lat"], got["fes"]["lon"]), (34.0565, -5.0023))
        self.assertEqual(got["lisbon"]["name"], "Lisbon")
        # a lowercase caption keeps their letters and stands capitalized like any name
        got = self.run_places([post(1, "home", *LISBON), post(40, "the medina #fes", *FEZ)], "--reset")
        self.assertEqual(got["fes"]["name"], "Fes")
        # geotags alone give the gazetteer's name; their rename shows their spelling and keeps the place where it is
        got = self.run_places([post(1, "home", *LISBON), post(40, "the medina", *FEZ)], "--reset")
        self.assertEqual(got["fez"]["name"], "Fez")
        got = self.run_places([post(1, "home", *LISBON), post(40, "the medina", *FEZ)], "--reset", "--rename", "Fez=Fes")
        self.assertEqual((got["fes"]["name"], got["fes"]["lat"], got["fes"]["source"]), ("Fes", 34.0565, "renamed by you"))
        # a name the gazetteer lacks is taken as typed too, and the rename is replayed on the next run
        got = self.run_places([post(1, "home", *LISBON), post(40, "the medina", *FEZ)], "--reset", "--rename", "Fez=Fès el Bali")
        self.assertEqual((got["fes-el-bali"]["name"], got["fes-el-bali"]["lat"]), ("Fès el Bali", 34.0565))
        got = self.run_places([post(1, "home", *LISBON), post(40, "the medina", *FEZ)])
        self.assertEqual(got["fes-el-bali"]["name"], "Fès el Bali")
        # a rename to another place in the gazetteer still moves the place there, under the name as typed
        got = self.run_places([post(1, "home", *LISBON), post(40, "the river", 41.18, -8.69)], "--reset", "--rename", "Porto=braga")
        self.assertEqual((got["braga"]["name"], got["braga"]["lat"]), ("braga", 41.555))
        self.assertNotIn("porto", got)


class WhereTheyWere(unittest.TestCase):
    """A check-in, a folder or a file name says they were there; one caption naming a place does not."""

    setUp = TheirSpelling.setUp
    run_places = TheirSpelling.run_places

    def run_json(self, rows, *args):
        self.run_places(rows, *args)
        return json.loads((self.home / "build" / "r" / "places.json").read_text())

    def test_a_check_in_without_a_geotag_puts_its_place_on_the_map(self):
        got = self.run_json([{"ts": DAY + 86400, "caption": "the 28 tram", "place": "Lisbon, Portugal", "media": ["a.jpg"]},
                             {"ts": DAY + 86400 * 90, "caption": "rented a bike", "place": "Amsterdam, Netherlands", "media": ["b.jpg"]},
                             {"ts": DAY + 86400 * 120, "caption": "I miss Vienna", "media": ["c.jpg"]}])
        self.assertEqual([p["name"] for p in got["places"]], ["Lisbon", "Amsterdam"])
        self.assertEqual([m["name"] for m in got["mentioned"]], ["Vienna"])

    def test_a_place_they_add_at_its_coordinates_takes_the_rows_that_name_it(self):
        rows = [{"ts": DAY + 86400, "caption": "home", "place": "Lisbon, Portugal", "media": ["a.jpg"]},
                {"ts": DAY + 86400 * 40, "caption": "lost in the fog around the palace", "place": "Sintra, Portugal", "media": ["b.jpg"]}]
        got = self.run_json(rows)
        self.assertEqual([p["name"] for p in got["places"]], ["Lisbon"])
        self.assertIn('Sintra (1 row) is not in the kit\'s gazetteer and has no geotag: places.py --add "Sintra@lat,lon" puts it '
                      'on the map.', got["assumptions"])
        got = self.run_json(rows, "--add", "Sintra@38.80,-9.38")
        sintra = next(p for p in got["places"] if p["name"] == "Sintra")
        self.assertEqual((sintra["lat"], sintra["rows"]), (38.8, 1))
        self.assertEqual(got["unplaced"], 0)

    def test_a_photo_file_name_gives_its_date_and_its_place(self):
        from PIL import Image
        import gather
        folder = self.home / "trips"
        folder.mkdir()
        for name in ("2026-03-08_lisbon-belem.jpg", "2026-05-17_fes.jpg", "IMG_4512.jpg"):
            Image.new("RGB", (8, 8)).save(folder / name)
        rows, _ = gather.read_photos(folder)
        by = {Path(r["media"][0]).name: r for r in rows}
        self.assertEqual(by["2026-05-17_fes.jpg"]["ts"], DAY + 86400 * 136 + 43200)
        self.assertEqual((by["2026-03-08_lisbon-belem.jpg"]["file"], by["2026-05-17_fes.jpg"]["file"]), ("lisbon belem", "fes"))
        self.assertNotIn("file", by["IMG_4512.jpg"])
        got = self.run_json(rows)
        self.assertEqual([p["name"] for p in got["places"]], ["Lisbon", "Fes"])

    def test_a_place_with_no_photograph_of_theirs_is_named_before_the_draft(self):
        import storyboard
        run = self.home / "work"
        (run / "public").mkdir(parents=True)
        (run / "places.json").write_text(json.dumps({"year": 2026, "home": None, "route": ["sintra", "dolomites"], "places": [
            {"id": "sintra", "name": "Sintra", "country": "", "lat": 38.8, "lon": -9.38},
            {"id": "dolomites", "name": "Dolomites", "country": "", "lat": 46.69, "lon": 12.08}]}))
        (run / "public" / "photos.json").write_text(json.dumps({"photos": [{"place": "sintra", "n": 1, "k": 1, "file": "photos/s.jpg"}]}))
        os.chdir(run)
        with self.assertRaises(SystemExit) as e:
            storyboard.build_source({})
        self.assertIn("Dolomites has no photograph of theirs", str(e.exception))


class ThePlacesTheyAddAtCoordinates(unittest.TestCase):
    HOME = {"lat": LISBON[0], "lon": LISBON[1]}

    @classmethod
    def setUpClass(cls):
        cls.grid = places.Grid(places.load_gazetteer()[0])

    def refused(self, fn, *args):
        with self.assertRaises(SystemExit) as e:
            fn(*args)
        return str(e.exception)

    def test_a_pair_that_is_not_two_numbers_is_refused_with_how_to_write_it(self):
        for at in ("38.7", "lisbon,portugal", "38.7,-9.1,4", ""):
            self.assertIn("two numbers, latitude first", self.refused(places.coords, "Lisbon", at), at)

    def test_a_pair_out_of_range_is_refused_with_which_comes_first(self):
        for at in ("95,10", "-91,10", "10,200", "10,-181"):
            self.assertIn("latitude comes first", self.refused(places.coords, "Lisbon", at), at)

    def test_a_pair_in_range_is_its_latitude_and_longitude(self):
        self.assertEqual(places.coords("Lisbon", "38.72,-9.14"), LISBON)
        self.assertEqual(places.coords("Lisbon", " 38.72 , -9.14"), LISBON)

    def test_a_place_inside_the_region_is_said_with_its_nearest_town(self):
        said = places.where_added(self.grid, {"name": "Porto", "lat": 41.15, "lon": -8.61}, self.HOME, [])
        self.assertIn("from Porto, Portugal", said)
        self.assertIn("inside the route's region", said)

    def test_a_swapped_latitude_and_longitude_is_refused_with_the_pair_the_right_way_round(self):
        why = self.refused(places.where_added, self.grid, {"name": "Porto", "lat": -8.61, "lon": 41.15}, self.HOME, [])
        self.assertIn("latitude and longitude look swapped", why)
        self.assertIn('"Porto@41.15,-8.61"', why)

    def test_a_far_place_is_kept_only_near_another_place_of_the_route(self):
        tokyo = {"name": "Tokyo", "lat": 35.68, "lon": 139.69}
        self.assertIn("a far trip", places.where_added(self.grid, tokyo, self.HOME, [{"lat": 35.0, "lon": 135.77}]))
        self.assertIn("Check the coordinates", self.refused(places.where_added, self.grid, tokyo, self.HOME, []))


class GatherKeepsTheirOwn(unittest.TestCase):
    """A handle given with its "@" is kept without it, so nothing that shows it shows "@@"; with every door closed the
    run's brief.md stands beside out/, which holds only the deliverables."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.addCleanup(os.chdir, Path.cwd())

    def gather(self, *args):
        import gather
        out = io.StringIO()
        with mock.patch.dict(os.environ), mock.patch.object(gather._env, "HOME", self.home), \
                mock.patch.object(sys, "argv", ["gather.py", *args]), mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            rc = gather.main()
        return rc, self.home / "build" / (self.home / "build" / "RUN").read_text().strip(), out.getvalue()

    def test_a_handle_given_with_its_at_is_kept_without_it(self):
        (self.home / "pulled").mkdir()
        (self.home / "pulled" / "1.jpg").write_bytes(b"x")
        post = {"ts": DAY + 86400 * 40, "caption": "the bridge at dusk", "media": ["1.jpg"], "lat": 41.15, "lon": -8.61}
        (self.home / "pulled" / "items.json").write_text(json.dumps({"source": "instagram account", "handle": "@maya.walks",
                                                                     "posts": [post]}))
        rc, run, said = self.gather("--pulled", "pulled", "--year", "2026")
        self.assertEqual(rc, 0)
        lib = json.loads((run / "library.json").read_text())
        self.assertEqual(lib["handle"], "maya.walks")
        self.assertIn("Handle: @maya.walks.", lib["assumptions"])
        self.assertIn("handle: @maya.walks ", said)
        self.assertNotIn("@@", said)

    def test_with_every_door_closed_the_runs_brief_stands_beside_out(self):
        rc, run, said = self.gather()
        self.assertEqual(rc, 3)
        self.assertIn("no data found", (run / "brief.md").read_text())
        self.assertFalse((run / "out" / "brief.md").exists())


if __name__ == "__main__":
    unittest.main()
