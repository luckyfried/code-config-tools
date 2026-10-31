"""The film is about what they did at each stop, never a count: the moments draft is built from their captions, places
and people (never from likes); a stop runs as long as its line takes to read, the peak holding longer, and no two
spans make one length; a sound lands only where something lands; every clip request is a shot for its use (the hook's
world, a photograph brought to life) asking for the length it plays over, its move never the move before it; the
board and the storyboard carry no running count, no total and no ticks; the card's finish and ease reach the film;
the closer's still holds two seconds at any tempo; a photograph carries its own post's words and date and nothing
borrowed; an export path resolves to its own file or to nothing; a trip with only dated notes is made from them; and
the Lisbon fixture's captions carry what happened and who was there.

    python3 -I -m unittest discover -s S/tests -p test_content.py
"""
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import board_trip  # noqa: E402
import gather  # noqa: E402
import research  # noqa: E402
import storyboard  # noqa: E402
import style  # noqa: E402

LISBON = (38.71, -9.13)


def stop(name, caption, day, lat, lon, near=(0.5, 0.95), far=(0.5, 0.3)):
    return {"name": name, "place": name, "city": "lisbon", "photo": f"matched/{name}.jpg", "aspect": 1.25, "long": 2000, "date": f"mon {day} sep",
            "time": "09:00", "caption": caption, "day": day, "lat": lat, "lon": lon, "points": {"near": list(near), "far": list(far)}}


def source(captions, apart=0.02):
    """A trip of len(captions) stops in a line north, `apart` degrees of latitude between them, each with its line."""
    stops = [stop(f"stop{i}", c, i + 1, LISBON[0] + i * apart, LISBON[1], far=(0.3 + 0.1 * i, 0.3)) for i, c in enumerate(captions)]
    return {"stops": stops, "handle": "mara", "trip": {"name": "lisbon week", "label": "lisbon week", "range": "14 to 18 sep", "year": 2026}}


CARD = style.card("cinematic-letterbox")


def board(src, look="cinematic-letterbox"):
    return board_trip.board(src, style.card(look))


class Moments(unittest.TestCase):
    def test_the_moments_are_each_places_line_with_who_is_in_it_and_nothing_counted(self):
        post = lambda place, caption: {"place": place, "caption": caption, "likes": 900 if caption == "alfama" else 3}
        trip = {"days": [{"date": "2026-09-14", "places": ["Alfama, Lisbon"],
                          "items": [post("Alfama, Lisbon", "alfama"), post("Alfama, Lisbon", "alfama at seven, the lane to ourselves @ines.draws")]},
                         {"date": "2026-09-15", "places": [], "items": []},
                         {"date": "2026-09-17", "places": ["Sintra", "Belém, Lisbon"],
                          "items": [post("Sintra", "train to sintra, lost in the yellow palace"), post("Belém, Lisbon", "pastéis de nata on the way back")]}]}
        got = research.moments_of(trip)
        self.assertEqual([(m["date"], m["place"]) for m in got],
                         [("2026-09-14", "Alfama, Lisbon"), ("2026-09-17", "Sintra"), ("2026-09-17", "Belém, Lisbon")])
        self.assertEqual(got[0], {"date": "2026-09-14", "place": "Alfama, Lisbon", "with": ["ines.draws"],
                                  "line": "alfama at seven, the lane to ourselves"})
        self.assertEqual(got[2]["line"], "pastéis de nata on the way back", "a second place on one day keeps its own moment")
        for m in got:
            self.assertEqual(sorted(m), ["date", "line", "place", "with"])


def roads(*km, captions=None):
    """A trip whose legs run `km` kilometers north, one after another, each stop with its line."""
    lat, stops = LISBON[0], []
    for i, d in enumerate((0,) + km):
        lat += d / 111.2
        stops.append(stop(f"stop{i}", (captions or [""] * (len(km) + 1))[i], i + 1, lat, LISBON[1], far=(0.3 + 0.1 * i, 0.3)))
    return {"stops": stops, "handle": "mara", "trip": {"name": "lisbon week", "label": "lisbon week", "range": "14 to 18 sep", "year": 2026}}


class Timing(unittest.TestCase):
    def test_a_stop_runs_as_long_as_its_line_takes_to_read_and_the_peak_longer(self):
        b = board(roads(1, 5, 30, 4, captions=["", "", "tram up to graça, standing room only, all of us laughing", "", ""]))
        bars = {x["id"]: x["bars"] for x in b["beats"]}
        self.assertGreater(bars["stop-3"], bars["stop-2"], "a long line is held longer than a wordless photograph")
        self.assertTrue(b["beats"][3]["peak"], "the stop at the end of the longest leg is the peak")
        self.assertGreater(bars["stop-4"], bars["stop-5"], "the peak holds longer than a wordless stop after it")

    def test_each_span_starts_where_the_last_ends_and_the_spans_are_not_one_length(self):
        b = board(roads(1, 5, 30, 4))
        st = b["route"]["stops"]
        for x, s in zip(b["beats"], st):
            self.assertAlmostEqual(s["end"] - s["at"], 4 * x["bars"], delta=0.001, msg=x["id"])
        for a, z in zip(st, st[1:]):
            self.assertEqual(z["at"], a["end"])
        self.assertEqual(b["route"]["closer"]["at"], st[-1]["end"], "the closer opens where the last stop ends")
        self.assertGreater(len({x["bars"] for x in b["beats"][:-1]}), 1, [x["bars"] for x in b["beats"]])


class ClipLength(unittest.TestCase):
    def test_a_clip_request_asks_for_the_length_it_plays_over(self):
        import clips
        src = source(["", "tram up to graça, standing room only", "", "last night, the fountain lit up, we stayed"])
        b = board(src)
        for c in board_trip.clips(b["route"], src, b["bpm"]):
            _, n = clips.window({"route": b["route"], "bpm": b["bpm"]}, c)
            self.assertEqual(c["seconds"], round(n / clips.FPS, 1), f"clip {c['id']}: the request's length is the stretch it plays over")
            if c.get("prompt"):
                self.assertIn(f"One continuous {c['seconds']} second shot", c["prompt"])


class ClipShots(unittest.TestCase):
    def test_every_request_is_a_shot_for_its_use_and_no_two_in_a_row_make_one_move(self):
        src = roads(1, 30, 5, captions=["alfama at seven", "tram up to graça", "train to sintra, lost in the yellow palace", "fish at ramiro"])
        for s, sees in zip(src["stops"], ("A steep lane", "A yellow tram on a hill street; hard noon sun", "A palace on a hill", "A grill by the street")):
            s["sees"] = sees
        cs = board(src)["clips"]
        self.assertEqual([c["role"] for c in cs], ["the hook's world"] + ["the photograph brought to life"] * 3)
        moves = [c["move"] for c in cs]
        self.assertTrue(all(a != b for a, b in zip(moves, moves[1:])), moves)
        self.assertIn("A yellow tram on a hill street", cs[1]["prompt"])
        for c, s in zip(cs, src["stops"]):
            self.assertNotIn(s["caption"], c["prompt"], "a request never pastes their caption")
        self.assertEqual(len({c["prompt"] for c in cs}), len(cs), "one prompt per shot, never one sentence for all")


class Finish(unittest.TestCase):
    def test_the_cards_finish_and_ease_reach_the_film(self):
        for look in style.TRIO:
            c = style.card(look)
            s = style.system(c, {"bg": "#000000"})
            self.assertEqual((s["finish"], s["ease"], s["closer"], s["photo"]), (c["finish"], c["ease"], c["closer"], c["photo"]), look)


class Notes(unittest.TestCase):
    NOTES = ("# Norway, July 2026\n\n- Jul 11 flew to Bergen, rain. Bryggen wharf, brown wooden houses. (60.3975, 5.3243)\n"
             "- Jul 13 Flam railway down to the fjord, Emma counted 20 waterfalls. (60.8639, 7.1137)\n"
             "- Jul 15 Geiranger boat, cold wind, hot chocolate. (62.1008, 7.2059)\n")

    def test_a_trip_with_only_dated_notes_is_made_from_them(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ws = Path(d)
            (ws / "notes.md").write_text(self.NOTES)
            env = {k: v for k, v in os.environ.items() if k not in ("TR_RUN", "TR_HOME")}
            r = subprocess.run([sys.executable, str(KIT / "scripts" / "gather.py"), "--door", "instagram_account=closed: none",
                                "--door", "browser=closed: none"], cwd=ws, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            lib = json.loads(next(ws.glob("build/*/library.json")).read_text())
            self.assertEqual(lib["source"], "notes")
            posts = lib["posts"]
            self.assertEqual([p["place"] for p in posts], ["Bergen", "Flam", "Geiranger"])
            self.assertEqual([dt.datetime.fromtimestamp(p["ts"], dt.timezone.utc).date().isoformat() for p in posts],
                             ["2026-07-11", "2026-07-13", "2026-07-15"])
            self.assertEqual(posts[1]["geo"], [60.8639, 7.1137])
            self.assertTrue(all(Path(p["media"][0]).is_file() for p in posts), "each line is drawn as a card in place of a photograph")
            self.assertTrue(any("no photograph of theirs is in the film" in x for x in lib["assumptions"]))


class DefaultNear(unittest.TestCase):
    def test_where_they_stood_defaults_high_enough_for_the_landing_dot(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ph = Path(d) / "lane.jpg"
            Image.new("RGB", (80, 100), (120, 110, 100)).save(ph)
            self.assertLessEqual(storyboard.default_points(ph)["near"][1], 0.9, "a near point at the very foot starts the camera off the picture")


class OneGrade(unittest.TestCase):
    def test_the_set_is_matched_to_one_saturation_and_one_white(self):
        """A washed, cool photograph beside a saturated, warm one ends close to it in saturation, and its grays turn
        the set's white whatever its exposure is moved by."""
        from unittest import mock
        from PIL import Image
        import grade
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            g = Path(d) / "graded"
            g.mkdir()
            a = Image.new("RGB", (96, 96), (112, 118, 132))
            a.paste((150, 120, 110), (0, 0, 96, 30))
            b = Image.new("RGB", (96, 96), (126, 120, 112))
            b.paste((200, 60, 40), (0, 0, 96, 60))
            for n, im in (("a.jpg", a), ("b.jpg", b), ("c.jpg", Image.new("RGB", (96, 96), (44, 50, 62)))):
                im.save(g / n, quality=95)
            with mock.patch.object(grade, "GRADED", g), mock.patch.object(grade, "MATCHED", Path(d) / "matched"):
                grade.match_photos(["a.jpg", "b.jpg", "c.jpg"])
                after = {n: grade._stats(Path(d) / "matched" / n) for n in ("a.jpg", "b.jpg", "c.jpg")}
        sat = [s[3] for s in after.values()]
        self.assertLess(max(sat) / min(sat), 1.4, f"saturation across the set: {[round(x) for x in sat]}")
        cast = after["a.jpg"][2]
        self.assertLess(cast[2] - cast[0], 0.08, f"the cool photograph's grays: {[round(x, 3) for x in cast]}")


    def test_a_clip_on_a_matched_print_plays_in_the_prints_match(self):
        """Their own clip plays on its print where the matched photograph was, so its frames take the same match: a
        washed clip of a washed photograph comes out as saturated as the matched still, never only graded."""
        from PIL import Image, ImageStat
        import clips
        import grade
        sat = lambda im: ImageStat.Stat(im.convert("RGB").resize((96, 96)).convert("HSV")).mean[1]
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                (Path("public") / "graded").mkdir(parents=True)
                washed = Image.new("RGB", (96, 96), (128, 132, 136))
                washed.paste((150, 132, 120), (0, 0, 96, 40))
                vivid = Image.new("RGB", (96, 96), (126, 120, 112))
                vivid.paste((200, 60, 40), (0, 0, 96, 60))
                washed.save("public/graded/a.jpg", quality=95)
                vivid.save("public/graded/b.jpg", quality=95)
                grade.match_photos(["a.jpg", "b.jpg"])
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", "public/graded/a.jpg", "-frames:v", "3",
                                "-pix_fmt", "yuv444p", "-c:v", "libx264", "-qp", "0", "clip.mp4"], check=True)
                dst, got, err = clips.conform("01", Path("clip.mp4"), "matched/a.jpg", 3, "null")
                self.assertEqual((got, err), (3, ""))
                still = sat(Image.open("public/matched/a.jpg"))
                frame = sat(Image.open(dst / "0002.jpg"))
                plain = sat(Image.open("public/graded/a.jpg"))
            finally:
                os.chdir(here)
        self.assertGreater(still, plain * 1.3, "the match lifts the washed photograph")
        self.assertLess(abs(frame - still) / still, 0.15, f"clip frame {frame:.1f} against the matched still {still:.1f}")

class FirstStop(unittest.TestCase):
    def test_the_first_photographs_line_is_in_the_hook_and_the_hook_lands_on_the_first_frame(self):
        b = board(source(["alfama at seven, the lane to ourselves", "tram up to graça"]))
        self.assertEqual(b["beats"][0]["words"], "alfama at seven, the lane to ourselves")
        self.assertIn("alfama at seven, the lane to ourselves", b["beats"][0]["shows"])
        self.assertEqual((b["sound"][0]["kind"], b["sound"][0]["at"], b["sound"][0]["beat"]), ("hit", 0.0, "hook"), "the hook's landing sounds")


class Sound(unittest.TestCase):
    def test_a_sound_lands_where_something_lands_and_nowhere_else(self):
        """A hit as the hook opens and on every cut, soft notes as words settle and where the camera lands, the riser
        into the closer, its impact, its last words' hit and the stop: no span runs eight beats with nothing sounding."""
        for look in style.TRIO:
            b = board(source(["alfama at seven", "tram up to graça, standing room only", "walked the river out to belém", "fish at ramiro"]), look)
            cues, st, C = b["sound"], b["route"]["stops"], b["route"]["closer"]
            self.assertEqual({c["kind"] for c in cues}, {"hit", "riser", "impact", "stop"}, look)
            cuts = {c["at"] for c in cues if c["kind"] == "hit" and c["what"].startswith("the cut to")}
            self.assertEqual(cuts, {s["at"] for s in st[1:]}, look)
            self.assertTrue(all(c["weight"] < 0.5 for c in cues if c["what"].startswith(("the words", "the camera"))), look)
            self.assertEqual([c["kind"] for c in cues if c["beat"] == "closer"], ["impact", "hit", "stop"], look)
            self.assertEqual([c["at"] for c in cues if c["kind"] == "impact"], [C["at"]], look)
            self.assertEqual(cues, sorted(cues, key=lambda c: c["at"]))
            at = [c["at"] for c in cues if c["at"] <= C["at"]] + [C["at"]]
            self.assertLessEqual(max(b - a for a, b in zip(at, at[1:])), 8, at)


class NoCount(unittest.TestCase):
    def setUp(self):
        self.src = source(["alfama at seven", "tram up to graça, standing room only", "walked the river out to belém"])
        self.board = board(self.src)

    def test_the_board_carries_no_running_count_no_total_and_no_ticks(self):
        r = self.board["route"]
        self.assertNotIn("unit", r)
        for s in r["stops"]:
            self.assertNotIn("total", s)
        self.assertEqual([c for c in self.board["sound"] if c["kind"] == "ticks"], [])
        said = [c["what"] for c in self.board["sound"]] + [b["shows"] for b in self.board["beats"]]
        for text in said:
            self.assertNotRegex(text, r"\b(count|total)\b", text)

    def test_the_films_idea_is_the_trip_stop_by_stop(self):
        idea = board_trip.__doc__.split(". ")[0]
        self.assertIn("the trip stop by stop", idea)
        self.assertNotIn("route", idea)

    def test_the_storyboard_lists_each_stops_line_and_no_count(self):
        from unittest import mock
        import _env
        with mock.patch.object(_env, "read_json", return_value=None):
            b = storyboard.make_board("1", "cinematic-letterbox", self.src, {"swatches": ["#7b7561", "#3c2b1a", "#c7cbc7"]})
            d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
            self.addCleanup(shutil.rmtree, d, ignore_errors=True)
            storyboard.write_md(b, d / "storyboard.md")
        text = (d / "storyboard.md").read_text()
        self.assertNotRegex(text, r"\b(count|total)\b")
        self.assertIn("tram up to graça, standing room only", text)


class Fixture(unittest.TestCase):
    def test_the_lisbon_trip_carries_what_happened_and_who_was_there(self):
        spec = importlib.util.spec_from_file_location("make_trip", KIT / "evals/fixtures/make_trip.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        caps = [p["caption"] for p in mod.LISBON]
        handles = [h for c in caps for h in research.mentions(c)]
        self.assertTrue(any(handles.count(h) >= 2 for h in handles), f"someone is tagged on two or more days: {caps}")
        self.assertTrue(all(c == c.lower() and not c.rstrip().endswith((".", "!")) for c in caps), "their voice: lowercase, no end marks")
        self.assertEqual([p["place"] for p in mod.LISBON], ["Alfama, Lisbon", "Graça, Lisbon", "Belém, Lisbon", "Sintra", "Bairro Alto, Lisbon"])


def at_nine(day):
    return int(dt.datetime.fromisoformat(f"{day}T09:00:00+00:00").timestamp())


class OwnWords(unittest.TestCase):
    """A stop's photograph in a run folder: its own post's caption and date, never another post's."""

    def setUp(self):
        from PIL import Image
        self.cwd = os.getcwd()
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        self.addCleanup(os.chdir, self.cwd)
        os.chdir(d)
        (d / "photos").mkdir()
        (d / "public/matched").mkdir(parents=True)
        for n in ("alfama", "graca"):
            Image.new("RGB", (40, 50), "gray").save(d / "photos" / f"{n}.jpg")
            Image.new("RGB", (40, 50), "gray").save(d / "public/matched" / f"{n}.jpg")
        lib = lambda n: str(d / "library" / f"{n}.jpg")
        trip = {"name": "lisbon week", "from": "2026-09-14", "to": "2026-09-16",
                "places": [{"name": "Alfama, Lisbon", "lat": 38.711, "lon": -9.13, "days": ["2026-09-14", "2026-09-16"]},
                           {"name": "Graça, Lisbon", "lat": 38.7168, "lon": -9.1306, "days": ["2026-09-15"]}],
                "days": [{"date": "2026-09-14", "items": [{"ts": at_nine("2026-09-14"), "caption": "pastéis at the corner", "media": [lib("other")], "place": "Alfama, Lisbon"}]},
                         {"date": "2026-09-15", "items": [{"ts": at_nine("2026-09-15"), "caption": "", "media": [lib("graca")], "place": "Graça, Lisbon"},
                                                          {"ts": at_nine("2026-09-15") + 60, "caption": "tram up to graça", "media": [lib("tram")], "place": "Graça, Lisbon"}]},
                         {"date": "2026-09-16", "items": [{"ts": at_nine("2026-09-16"), "caption": "alfama at seven", "media": [lib("alfama")], "place": "Alfama, Lisbon"}]}]}
        picks = {"places": [{"name": "Alfama, Lisbon", "photos": ["photos/alfama.jpg"]}, {"name": "Graça, Lisbon", "photos": ["photos/graca.jpg"]}],
                 "source_of": {"photos/alfama.jpg": lib("alfama"), "photos/graca.jpg": lib("graca")},
                 "caption_of": {"photos/alfama.jpg": "alfama at seven", "photos/graca.jpg": ""}}
        taste = {"days": [{"date": "2026-09-15", "line": "tram up to graça"}]}
        points = {n: {"near": [0.5, 0.95], "far": [0.5, 0.3]} for n in ("alfama", "graca")}
        for name, data in (("trip.json", trip), ("picks.json", picks), ("taste.json", taste), ("points.json", points)):
            (d / name).write_text(json.dumps(data))
        self.stops = {s["place"]: s for s in storyboard.build_source()["stops"]}

    def test_a_photograph_with_no_caption_is_wordless_when_another_post_that_day_has_one(self):
        self.assertEqual(self.stops["Graça, Lisbon"]["caption"], "")

    def test_points_refuses_a_trip_with_no_places_in_plain_words(self):
        trip = json.loads(Path("trip.json").read_text())
        Path("trip.json").write_text(json.dumps(dict(trip, places=[])))
        with self.assertRaises(SystemExit) as e:
            storyboard.cmd_points(None)
        self.assertIn("needs two or more", str(e.exception.code))

    def test_a_stops_date_is_its_photographs_own(self):
        self.assertEqual(self.stops["Alfama, Lisbon"]["date"], "wed 16 sep", "the photograph's post is on the 16th, not the place's first day")
        self.assertEqual(self.stops["Alfama, Lisbon"]["caption"], "alfama at seven")


class Export(unittest.TestCase):
    def test_a_carousel_photograph_carries_its_posts_caption(self):
        post = {"title": "tram up to graça", "creation_timestamp": 5, "media": [{"uri": "media/posts/a.jpg", "title": ""}, {"uri": "media/posts/b.jpg"}]}
        self.assertEqual([t for _, _, t in gather.media_items(post)], ["tram up to graça", "tram up to graça"])
        self.assertEqual([ts for _, ts, _ in gather.media_items(post)], [5, 5])

    def test_a_missing_path_never_takes_a_same_named_file_from_another_folder(self):
        d = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "media/posts/202608").mkdir(parents=True)
        (d / "media/posts/202608/IMG_1.jpg").write_bytes(b"x")
        md = gather.Media(d)
        self.assertIsNone(md.resolve("media/posts/202609/IMG_1.jpg"))
        self.assertEqual(md.resolve("media/posts/202608/IMG_1.jpg"), str((d / "media/posts/202608/IMG_1.jpg").resolve()))


class Closer(unittest.TestCase):
    def test_the_closers_still_holds_two_seconds_at_the_tempo_the_film_plays_at(self):
        src = source(["alfama at seven", "tram up to graça, standing room only", "walked the river out to belém"])
        for look in style.TRIO:
            raw = board(src, look)
            b = dict(raw, source=src, music={}, system=style.system(style.card(look), {"bg": "#000000"}))
            for bpm in (140.0, 80.0):
                film = storyboard.film_of(b, {"bpm": bpm, "downbeats": [0.0]}, "reel")
                still, plays = film["route"]["closer"]["still"], film["bpm"]
                self.assertAlmostEqual(film["seconds"] - still * 60 / plays, 2.0, delta=1 / 30, msg=f"{look} at {plays:g} bpm")
                self.assertEqual([c["at"] for c in film["sound"] if c["kind"] == "stop"], [still], "the stop cue is where the still begins")


if __name__ == "__main__":
    unittest.main()
