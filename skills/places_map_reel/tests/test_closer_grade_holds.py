"""The closer reads at any count of stops, the grade brings the stops to one light, each stop holds for what its
photograph carries, and the photograph fills its card's picture box:
  - the closer names its places beside their pins, never under the type floor and never one label over another; a name
    the route crosses everywhere still stands, where the route crosses it least; with many stops the labels thin to the
    ones that find room, the farthest, the first and the last first
  - grade.py balances each photograph toward the cast's median temperature and lightness, so the spread across the
    stops narrows and a cool place stays the coolest; a vivid photograph in a muted cast keeps at least 0.65 of its
    chroma, so the peak's sunset stays in color
  - a stop holds longer for more words, a busier photograph and a bigger change from the stop before, all scaled to
    the length taste.json asks for, or as near it as the stops make; a trip too small for 20 s runs as long as its
    photographs carry; the peak holds the most beats and the hook no more than the peak; the closer's map holds only as
    long as its words need
  - every photograph covers its style card's picture box, or stands enlarged ENLARGE times in it when it has too few
    pixels

    python3 -I -m unittest discover -s S/tests -p test_closer_grade_holds.py
"""
import copy
import json
import math
import os
import shutil
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(KIT / "evals" / "fixtures"))
import board_drive  # noqa: E402
import bounds  # noqa: E402
import look  # noqa: E402
import storyboard  # noqa: E402
import trip as trip_mod  # noqa: E402

SOURCE = json.loads((KIT / "tests" / "data" / "trip.json").read_text())
# two seeds' source.json as gather.py and research.py drafted them from the seeds' own posts
NURSE = json.loads((KIT / "tests" / "data" / "travel-nurse.json").read_text())
YEAR = json.loads((KIT / "tests" / "data" / "video-of-my-year.json").read_text())
READ = (0.3, 0.12)  # the seconds a line of n words needs on screen: READ[0] + READ[1] * n


def first_stops(n):
    """The source cut to its first n stops, the places list to the places they reach."""
    src = copy.deepcopy(SOURCE)
    pl = src["places"]
    pl["route_visits"] = pl["route_visits"][:n]
    keep = {v["place"] for v in pl["route_visits"]}
    pl["places"] = [p for p in pl["places"] if p["id"] in keep]
    src["photos"] = [ph for ph in src["photos"] if ph["place"] in keep]
    src["moments"] = [m for m in src["moments"] if m["place"] in keep]
    return src


def hold_seconds(board):
    """Each stop's hold in seconds, without the camera's travel across a leap."""
    sec = 60 / board["bpm"]
    out = {}
    for c, b in zip(board["route"]["cards"], board["beats"]):
        leap = c["go"] == board_drive.LEAP_GO
        out[(c["place"], c["n"])] = (4 * b["bars"] - (board_drive.LEAP if leap else 0)) * sec
    return out


class TheCloserReads(unittest.TestCase):
    def test_the_closers_line_names_every_place_once_in_the_order_first_reached(self):
        # the closer's shape sets the title, this line and the handle around the map's window; the map itself carries
        # no names, so the place names stand once in the frame
        for src in [first_stops(n) for n in (3, 7, 12)] + [YEAR]:
            tr = trip_mod.Trip(src["places"], src["photos"])
            names = {p["id"]: p["name"] for p in src["places"]["places"]}
            want = list(dict.fromkeys(names[s["place"]] for s in tr.stops))
            for fmt in storyboard.FORMATS:
                board = storyboard.plan(src, fmt)["board"]
                closer = board["route"]["closer"]
                self.assertEqual(closer["signoff"].split(" · "), want, fmt)
                self.assertNotIn("lines", closer, fmt)
                self.assertEqual([x for x in bounds.check(board) if x.startswith(("safe", "floor"))], [], fmt)

    def test_the_floor_is_legible_at_1080_by_1920(self):
        self.assertGreaterEqual(bounds.FLOOR * 1080, 32.4 - 1e-9)


def temperature(im):
    """The mean (R - B) / 255 of the photograph's mid-tones, its lightness the median luma / 255."""
    import grade
    px = grade.pixels(im.convert("RGB").resize((96, 96)))
    luma = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px]
    mid = [p for p, v in zip(px, luma) if 30 < v < 243]
    return (statistics.fmean((r - b) / 255 for r, g, b in mid), statistics.median(luma) / 255,
            statistics.fmean((max(p) - min(p)) / 255 for p in mid))


class OneGradeAcrossTheStops(unittest.TestCase):
    def test_each_photograph_is_balanced_toward_the_casts_median_temperature_and_lightness(self):
        import _env
        import grade
        import make_person as mp
        from PIL import Image
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        here = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, here)
        visits, sources = [], {}
        for seed, (name, p) in enumerate(mp.PLACES.items()):
            k = trip_mod_slug(name)
            path = Path(tmp.name) / "set" / f"{k}.jpg"
            mp.draw_scene((path, 480, 600, p[4][0], [mp.COLORS[c] for c in p[3]], seed + 1, name == "Lisbon"))
            visits.append({"place": k, "n": 1, "shots": [str(path)]})
            sources[k] = path
        Path("cast.json").write_text(json.dumps({"visits": visits}))
        Path("places.json").write_text(json.dumps({"home": "lisbon"}))
        rows = grade.grade_cast(own={})
        before = {r["place"]: temperature(Image.open(sources[r["place"]])) for r in rows}
        after = {r["place"]: temperature(Image.open(Path("public") / r["file"])) for r in rows}
        sd = lambda d, i: statistics.pstdev(v[i] for v in d.values())
        # every photograph of this cast is vivid and keeps at least 0.7 of its saturation: the temperature spread across
        # the stops narrows to under 0.85 of the sources', the lightness spread narrows, and the chroma spread grows by
        # under a third
        self.assertLess(sd(after, 0), 0.85 * sd(before, 0), (sd(before, 0), sd(after, 0)))
        self.assertLess(sd(after, 1), sd(before, 1), (sd(before, 1), sd(after, 1)))
        self.assertLess(sd(after, 2), 4 / 3 * sd(before, 2), (sd(before, 2), sd(after, 2)))
        # no hue is moved: the cool place stays the coolest and the warm ones stay warm
        self.assertEqual(min(after, key=lambda k: after[k][0]), "lisbon")
        self.assertTrue(all(after[k][0] > 0 for k in after if k != "lisbon"), after)

    def test_a_vivid_photograph_in_a_muted_cast_keeps_most_of_its_color(self):
        import grade
        from PIL import Image, ImageOps
        tmp = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, tmp)
        # one vivid photograph and three muted ones, all at the same temperature and lightness with a white band and a
        # black band, so the levels, the white balance and the exposure leave the vivid one as it is and only the
        # saturation moves it
        across = Image.linear_gradient("L").rotate(90).resize((300, 200))
        vivid = Image.merge("RGB", [across, Image.linear_gradient("L").resize((300, 200)), ImageOps.invert(across)])
        vivid.paste((255, 255, 255), (0, 0, 300, 12))
        vivid.paste((0, 0, 0), (0, 188, 300, 200))
        vivid.save(tmp / "vivid.jpg", quality=95)
        for k, gray in enumerate((0.88, 0.91, 0.94)):
            Image.blend(vivid, vivid.convert("L").convert("RGB"), gray).save(tmp / f"muted{k}.jpg", quality=95)
        toned = {n: grade.toned(tmp / f"{n}.jpg") for n in ("vivid", "muted0", "muted1", "muted2")}
        out = grade.finish(*toned["vivid"], grade.target_of(list(toned.values())))
        kept = temperature(out)[2] / temperature(Image.open(tmp / "vivid.jpg"))[2]
        self.assertGreaterEqual(kept, 0.65, kept)


def trip_mod_slug(name):
    import unicodedata
    s = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
    return s.lower()


class HoldsFromThePhotograph(unittest.TestCase):
    def look(self, light, busy):
        return {"light": [[light] * 6 for _ in range(6)], "busy": [[busy] * 6 for _ in range(6)]}

    def with_looks(self, change=None):
        src = first_stops(8)
        for ph in src["photos"]:
            ph["look"] = self.look(0.5, 0.2)
        for (place, n), look in (change or {}).items():
            for ph in src["photos"]:
                if (ph["place"], ph["n"]) == (place, n):
                    ph["look"] = look
        return src

    def test_a_stop_holds_longer_for_more_words_a_busier_photograph_and_a_bigger_change(self):
        base = hold_seconds(storyboard.plan(self.with_looks(), "reel")["board"])
        busy = hold_seconds(storyboard.plan(self.with_looks({("aveiro", 1): self.look(0.5, 0.6)}), "reel")["board"])
        self.assertGreater(busy[("aveiro", 1)], base[("aveiro", 1)])
        # a stop that looks like the one before it changes least and holds shorter than one that changes the light
        same = hold_seconds(storyboard.plan(self.with_looks({("granada", 1): self.look(0.5, 0.2)}), "reel")["board"])
        moved = hold_seconds(storyboard.plan(self.with_looks({("granada", 1): self.look(0.95, 0.2)}), "reel")["board"])
        self.assertGreater(moved[("granada", 1)], same[("granada", 1)])
        # their words: the same stop without its line holds shorter
        src = self.with_looks()
        for m in src["moments"]:
            if (m["place"], m["n"]) == ("aveiro", 1):
                m["line"] = None
        quiet = hold_seconds(storyboard.plan(src, "reel")["board"])
        self.assertLess(quiet[("aveiro", 1)], base[("aveiro", 1)])

    def test_the_holds_scale_to_the_length_she_asked_for(self):
        got = {}
        for asked in (24, 32):
            src = first_stops(8)
            src["seconds"] = asked
            for bpm in (None, 120):
                p = storyboard.plan(src, "reel", bpm)
                beat = 60 / p["board"]["bpm"]
                self.assertLessEqual(p["seconds"], asked + 1 / 30, (asked, bpm))
                self.assertGreater(p["seconds"], asked - beat - 1 / 30, (asked, bpm))
            got[asked] = hold_seconds(storyboard.plan(src, "reel")["board"])
        self.assertTrue(all(got[32][k] >= got[24][k] - 1e-9 for k in got[24]))
        self.assertGreater(sum(got[32].values()), sum(got[24].values()))

    def test_a_trip_too_small_for_twenty_seconds_drafts_as_long_as_its_holds_reach(self):
        for asked in (None, 20):
            src = first_stops(2)
            src["seconds"] = asked
            for bpm in (None, 92, 120):
                p = storyboard.plan(src, "reel", bpm)
                board = p["board"]
                sec = 60 / board["bpm"]
                cards = board["route"]["cards"]
                closer = next(b for b in board["beats"] if b["id"] == "closer")
                leaps = sum(1 for c in cards if c["go"] == board_drive.LEAP_GO)
                reach = sum(board_drive.MOST[c["kind"]] for c in cards) + (4 * closer["bars"] + board_drive.LEAP * leaps) * sec
                self.assertLess(p["seconds"], 20, (asked, bpm))
                self.assertLessEqual(abs(p["seconds"] - reach), 1.0, (asked, bpm, p["seconds"], reach))
                self.assertTrue(storyboard.in_band(p["seconds"], board["length"]), (asked, bpm))
                said = storyboard.length_said(p["seconds"], asked, len(cards))
                self.assertEqual("20 s asked" in said, asked == 20, said)

    def test_a_length_these_places_cannot_make_is_made_as_near_as_they_make_it_and_named(self):
        made = {}
        for asked in (8, 20, board_drive.LENGTH[1], 90):
            src = copy.deepcopy(SOURCE)
            src["seconds"] = asked
            p = storyboard.plan(src, "reel")
            self.assertTrue(storyboard.in_band(p["seconds"], p["board"]["length"]), asked)
            made[asked] = p["seconds"]
            said = storyboard.length_said(p["seconds"], asked, len(p["board"]["route"]["cards"]))
            self.assertEqual(f"{asked} s asked" in said, abs(p["seconds"] - asked) >= 0.05, said)
            self.assertNotIn("\n", said)
        # under the shortest film these stops make, the shortest; over the longest, the longest
        self.assertEqual(made[8], made[20])
        self.assertEqual(made[90], made[board_drive.LENGTH[1]])
        self.assertIn("8 s asked", storyboard.length_said(made[8], 8, 14))

    def test_the_peak_holds_the_most_beats_and_the_hook_no_more_than_the_peak(self):
        def holds(board):
            # a stop's own hold: a stop the camera leaves across a leap carries the camera's travel on top of it
            return {c["id"]: 4 * b["bars"] - (board_drive.LEAP if c["go"] == board_drive.LEAP_GO else 0)
                    for c, b in zip(board["route"]["cards"], board["beats"])}
        trip7 = first_stops(7)
        sources = {"travel-nurse": NURSE}
        for m in trip7["moments"][1:7]:
            src = copy.deepcopy(trip7)
            for x in src["moments"]:
                x["peak"] = (x["place"], x["n"]) == (m["place"], m["n"])
            sources[f"trip7 {m['place']}"] = src
        for name, src in sources.items():
            for bpm in (None, 92, 120):
                board = storyboard.plan(src, "reel", bpm)["board"]
                held = holds(board)
                peak = next(c["id"] for c in board["route"]["cards"] if c["kind"] == "peak")
                self.assertEqual(held[peak], max(held.values()), (name, bpm, held))
                self.assertLessEqual(held["hook"], held[peak], (name, bpm, held))

    def test_the_closers_map_holds_only_as_long_as_its_words_need(self):
        for bpm in (45, 60, 90, 120, 180):
            board = storyboard.plan(first_stops(7), "reel", bpm)["board"]
            sec = 60 / bpm
            closer = next(b for b in board["beats"] if b["id"] == "closer")
            still = (4 * closer["bars"] - board["route"]["closer"]["route"]) * sec
            cl = board["route"]["closer"]
            words = len(cl["title"].split()) + len(cl["signoff"].split()) + len((board["handle"] or "").split())
            need = READ[0] + READ[1] * words - (board["route"]["closer"]["route"] - 0.75) * sec
            self.assertGreaterEqual(still, 1.0 - 1e-6, bpm)
            self.assertLessEqual(still, max(1.0, need) + sec + 1e-6, bpm)


class TheCardLaysThePhotographInItsPictureBox(unittest.TestCase):
    def test_every_photograph_covers_its_cards_picture_box_or_stands_at_ENLARGE(self):
        # the style card's picture box is the photograph's: covered whole by a photograph with the pixels to, and one
        # without stands enlarged ENLARGE times in the box's middle, never more
        for style in look.TRIO:
            lay0 = look.card(style)["photo"]
            photos = {ph["file"]: ph for ph in SOURCE["photos"]}
            for fmt in storyboard.FORMATS:
                b = storyboard.plan(SOURCE, fmt, None, style)["board"]
                W, H = b["format"]["width"], b["format"]["height"]
                fr = {"width": W, "height": H, **board_drive.SAFE[fmt]}
                for c in b["route"]["cards"]:
                    lay = board_drive.layout_of(lay0, photos[c["file"]], W, H)
                    pbox = board_drive.picture_box(fr, lay["picture"])
                    self.assertLessEqual(c["scale"], board_drive.ENLARGE, (style, fmt, c["id"]))
                    if c["scale"] < board_drive.ENLARGE:
                        self.assertEqual(c["box"], pbox, (style, fmt, c["id"]))
                    else:
                        self.assertTrue(pbox[0] <= c["box"][0] and c["box"][2] <= pbox[2] and pbox[1] <= c["box"][1] and c["box"][3] <= pbox[3], (style, fmt, c["id"]))


if __name__ == "__main__":
    unittest.main()
