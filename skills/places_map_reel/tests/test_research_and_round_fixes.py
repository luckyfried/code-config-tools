"""Four producers that wrote a shape their reader could not take:
  - places.py: a home guessed from the bio with no post there is not a place and not a stop
  - picks.py: a cast.json is always written with its visits, even when the year has none
  - vote.py: a scored round under the bar opens round 2 only on a new film, and round 2 finishes the gate
  - the gazetteer: Hakuba and Zermatt are rows of data/places.tsv, built from data/towns.tsv by data/build_data.py

    python3 -I -m unittest discover -s S/tests -p test_research_and_round_fixes.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import picks  # noqa: E402
import places  # noqa: E402
import vote  # noqa: E402

DAY = 86400 * (365 * 56 + 14)  # 2026-01-01


def post(day, caption, lat, lon):
    return {"ts": DAY + 86400 * day, "caption": caption, "media": [f"{day}.jpg"], "lat": lat, "lon": lon}


class InAWorkspace(unittest.TestCase):
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

    def run_places(self, posts, bio="Lisbon"):
        (self.home / "build" / "r" / "library.json").write_text(json.dumps({"year": 2026, "bio": bio, "posts": posts}))
        with mock.patch.object(sys, "argv", ["places.py", "--reset"]), mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            places.main()
        return json.loads((self.home / "build" / "r" / "places.json").read_text())


class AHomeIsAStopOnlyWithAPost(InAWorkspace):
    def test_a_home_the_bio_names_with_no_post_there_is_not_a_place_or_a_stop(self):
        got = self.run_places([post(10, "the bridge at dusk", 41.15, -8.61), post(40, "the medina", 34.06, -5.00)])
        ids = [p["id"] for p in got["places"]]
        self.assertNotIn("lisbon", ids)
        self.assertNotIn("lisbon", got["route"])
        self.assertEqual(got["count"], 2)
        self.assertIsNone(got["home"])

    def test_a_home_with_posts_is_a_place(self):
        got = self.run_places([post(1, "home", 38.72, -9.14), post(10, "the bridge", 41.15, -8.61), post(20, "home again", 38.72, -9.14)])
        self.assertIn("lisbon", [p["id"] for p in got["places"]])
        self.assertEqual(got["home"], "lisbon")


class TheGazetteerHasTheTowns(InAWorkspace):
    def test_hakuba_and_zermatt_resolve_through_the_gazetteer(self):
        rows, names = places.load_gazetteer()
        self.assertEqual({g["country"] for g in names["hakuba"]}, {"Japan"})
        self.assertEqual({g["country"] for g in names["zermatt"]}, {"Switzerland"})
        got = self.run_places([post(1, "home", 38.72, -9.14), post(30, "first tracks in Hakuba", 36.70, 137.86),
                               post(60, "under the matterhorn #zermatt", 46.02, 7.75), post(90, "home", 38.72, -9.14)])
        named = {p["id"]: (p["name"], p["country"]) for p in got["places"]}
        self.assertEqual(named.get("hakuba"), ("Hakuba", "Japan"))
        self.assertEqual(named.get("zermatt"), ("Zermatt", "Switzerland"))

    def test_the_towns_file_is_built_into_the_gazetteer_by_the_data_build(self):
        sys.path.insert(0, str(KIT / "data"))
        import build_data
        towns = build_data.town_rows(set())
        plain = {r.split("\t")[1] for r in towns}
        self.assertTrue({"hakuba", "zermatt"} <= plain)
        built = set((KIT / "data" / "places.tsv").read_text().splitlines())
        self.assertTrue(all(r in built for r in towns))


class ACastAlwaysHasItsVisits(unittest.TestCase):
    def test_a_year_with_no_visits_writes_a_cast_with_an_empty_visits_list(self):
        wrote = {}
        with mock.patch.object(picks._env, "read_json", return_value=None), \
                mock.patch.object(picks._env, "write_json", side_effect=lambda name, v: wrote.update({name: v})), \
                mock.patch.object(picks, "contact") as contact:
            cast = picks.write_cast({"route_visits": [], "route": []}, {}, None, [])
        self.assertEqual(wrote["cast.json"]["visits"], [])
        self.assertEqual(contact.call_args[0][0]["visits"], [])
        self.assertEqual(cast["visits"], [])

    def test_a_cast_json_without_visits_is_written_again_from_the_rule(self):
        wrote = {}
        with mock.patch.object(picks._env, "read_json", return_value={"set": None}), \
                mock.patch.object(picks._env, "write_json", side_effect=lambda name, v: wrote.update({name: v})), \
                mock.patch.object(picks, "contact"):
            picks.write_cast({"route_visits": [], "route": []}, {}, None, [])
        self.assertEqual(wrote["cast.json"]["visits"], [])


def fill(path, score, fixed=None):
    data = json.loads(Path(path).read_text())
    for c in data["critics"].values():
        e = c["boards"]["film"]
        e["scores"] = {k: score for k in e["scores"]}
        e["paragraph"] = " ".join(["the cut holds its places and its music agrees with the moves it makes"] * 3)
    data["seen"] = data["frames"]
    if score < vote.BAR:
        data["lever"] = {"name": "closer.map", "change": "the closer opens on the whole year's map"}
    if fixed is not None:
        data["fixed"] = fixed
    Path(path).write_text(json.dumps(data))


class TheRoundGateFinishes(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        for path, text in (("render/film-report.json", "{}"), ("out/film.mp4", "reel a")):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text)
        cut = mock.patch.object(vote, "cut_frames", lambda film, into: [f"f{i + 1:02d}.jpg" for i in range(vote.CUT_FRAMES)])
        cut.start()
        self.addCleanup(cut.stop)

    def test_a_scored_round_opens_round_two_only_on_a_new_film_and_round_two_finishes(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(vote.cmd_cut(None), 0)
            fill("critic/cut-1.json", 3)
            self.assertEqual(vote.cmd_verdict(None), 2)  # FIX ONCE
            # round 2 reads the frames of the film the lever's change made, never the scored film again
            with self.assertRaises(SystemExit) as e:
                vote.cmd_cut(None)
            self.assertIn("closer.map", str(e.exception.code))
            Path("out/film.mp4").write_text("reel b")
            self.assertEqual(vote.cmd_cut(None), 0)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])
        self.assertEqual(json.loads(Path("critic/cut-2.json").read_text())["round"], 2)
        with mock.patch("sys.stdout"):
            fill("critic/cut-2.json", 3, fixed="")
            self.assertEqual(vote.cmd_verdict(None), 1)  # round 2 says what changed, or why the film could not
            fill("critic/cut-2.json", 3, fixed="the music cue moved one beat earlier, and the render came out byte for byte the same")
            self.assertEqual(vote.cmd_verdict(None), 0)  # the one fix is spent: ship
            self.assertEqual(vote.cmd_cut(None), 0)  # no third round
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json", "cut-2.json"])

    def test_an_unscored_round_on_the_same_film_is_kept(self):
        with mock.patch("sys.stdout"):
            vote.cmd_cut(None)
            vote.cmd_cut(None)
        self.assertEqual([p.name for p in vote.rounds()], ["cut-1.json"])


if __name__ == "__main__":
    unittest.main()
