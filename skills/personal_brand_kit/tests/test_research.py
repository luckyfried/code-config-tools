"""research.py's readings of a feed that need no photographs: the posting days and the voice of an outlier."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import research  # noqa: E402


def at(day, hour, minute=0):
    return {"ts": int(dt.datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=dt.timezone.utc).timestamp())}


def every(start, weeks, step, hour, minute=0):
    d = dt.date.fromisoformat(start)
    return [at((d + dt.timedelta(weeks=w)).isoformat(), hour, minute) for w in range(0, weeks, step)]


class Cadence(unittest.TestCase):
    def test_a_light_poster_keeps_both_of_her_days(self):
        rows = every("2026-01-07", 52, 4, 19, 30) + every("2026-01-17", 52, 4, 10)  # a Wednesday and a Saturday
        cad = research.cadence(rows)
        self.assertEqual([(s["day"], s["time"]) for s in cad["slots"]], [("Wednesday", "19:30"), ("Saturday", "10:00")])
        self.assertEqual(cad["on_rhythm"], 1.0)

    def test_three_days_a_week_are_three_slots(self):
        rows = every("2026-01-06", 40, 1, 8) + every("2026-01-08", 40, 1, 12, 30) + every("2026-01-11", 40, 1, 18, 30)
        self.assertEqual([s["day"] for s in research.cadence(rows)["slots"]], ["Tuesday", "Thursday", "Sunday"])

    def test_a_stray_day_is_not_a_slot(self):
        rows = every("2026-01-06", 40, 1, 8) + [at("2026-03-05", 9)]
        self.assertEqual([s["day"] for s in research.cadence(rows)["slots"]], ["Tuesday"])


class Moments(unittest.TestCase):
    def test_the_moments_draft_is_what_they_did_where_and_with_whom(self):
        rows = [dict(at("2026-05-02", 10), caption="Cycled to Belém with @rui.costa, the river going silver 🌊 #lisbonwalks", likes=900,
                     place="Belém"),
                dict(at("2026-02-14", 19), caption="Rui's birthday ramen.\n\nwho else orders extra scallions?\n#eatlisbon", likes=12),
                dict(at("2026-03-01", 9), caption="#nofilter", likes=400),
                dict(at("2026-04-01", 9), caption="A reel with no photograph", likes=50)]
        photo_of = {0: "media/belem.jpg", 1: "media/ramen.jpg", 2: "media/x.jpg"}
        pls = [{"name": "the streets", "rows": [0]}, {"name": "the table", "rows": [1]}]
        ms = research.moments(rows, pls, photo_of)
        self.assertEqual([m["date"] for m in ms], ["2026-02-14", "2026-05-02"])
        ramen, belem = ms
        self.assertEqual(belem["line"], "Cycled to Belém with @rui.costa, the river going silver")
        self.assertEqual((belem["place"], belem["people"], belem["pillar"], belem["photo"]), ("Belém", ["@rui.costa"], "the streets", "media/belem.jpg"))
        self.assertEqual(ramen["line"], "Rui's birthday ramen.")
        self.assertEqual((ramen["row"], ramen["place"], ramen["people"]), (1, None, []))
        for m in ms:
            self.assertFalse({"likes", "comments", "times_usual", "share"} & set(m), m)


    def test_a_line_without_latin_letters_is_still_a_moment(self):
        rows = [dict(at("2026-06-01", 10), caption="40 🎂"), dict(at("2026-06-02", 10), caption="富士山の頂上で日の出"),
                dict(at("2026-06-03", 10), caption="#nofilter")]
        ms = research.moments(rows, [], {0: "a.jpg", 1: "b.jpg", 2: "c.jpg"})
        self.assertEqual([m["photo"] for m in ms], ["a.jpg", "b.jpg"])
        self.assertTrue(ms[0]["line"].startswith("40"), ms[0])


    def test_a_tagged_friend_is_one_of_their_people_never_a_pillar(self):
        walks = ["Alfama end to end", "Painted tiles below the castle", "Graça lookout at dusk", "The tram up the hill",
                 "Belém tower by the river", "Rossio fountain at night"]
        tables = ["Ramen with scallions", "Bread before nine", "Tomatoes off the vine", "Flat white with a leaf",
                  "Cauliflower cart at the market", "Herbs planted in raised beds"]
        caps = [f"{w} through the streets{' with @ines.matos' * (k < 4)} #lisbonwalks" for k, w in enumerate(walks)]
        caps += [f"{w} at the table{' with @rui.costa' * (k < 4)} #eatlisbon" for k, w in enumerate(tables)]
        pls, _ = research.pillars([{"caption": c} for c in caps])
        named = {w for p in pls for w in p["words"]}
        self.assertFalse({"ines", "matos", "rui", "costa"} & named, pls)
        self.assertTrue({"lisbonwalks", "eatlisbon"} <= named | {(p["hashtag"] or "").lstrip("#") for p in pls}, pls)

class Loud(unittest.TestCase):
    def test_place_names_are_not_shouting(self):
        self.assertFalse(research.LOUD("Pena palace, yellow walls and blue tiles against the sky. Worth the climb"))
        self.assertTrue(research.LOUD("NEW KICKS!!! link in bio"))


if __name__ == "__main__":
    unittest.main()
