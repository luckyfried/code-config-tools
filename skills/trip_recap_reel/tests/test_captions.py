"""The storyboard check measures every caption the film sets over a photograph where the film draws it, against the
pixels under it after the scrim (scripts/captions.py, motion/system/standards.md R3): a bright photograph deepens the
beat's scrim and a dark one keeps the card's, a label that does not read in the card's label color takes the line's, the
title card's words on a bright last photograph get a veil under the closer, and the check names words no scrim lifts,
every line under 32 px, and words over a photograph the run does not hold.

    python3 -I -m unittest discover -s S/tests -p test_captions.py
"""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import captions  # noqa: E402
import storyboard  # noqa: E402

LOOK = "cinematic-letterbox"
SWATCHES = ["#7b7561", "#3c2b1a", "#c7cbc7", "#6f4a1e", "#d5e9f2"]


def stop(i, name, caption, aspect=0.6667, clip=False):
    return {"name": name, "place": f"{name.title()}, Lisbon", "city": "lisbon", "photo": f"matched/{i}.jpg", "aspect": aspect,
            "long": 1350, "date": f"mon {14 + i} sep", "time": "09:00", "caption": caption, "day": i + 1,
            "lat": 38.71 + 0.01 * i, "lon": -9.13, "clip": clip, "sees": "",
            "points": {"near": [0.3 + 0.05 * i, 0.88], "far": [0.7 - 0.08 * i, 0.4 + 0.03 * i]}}


def trip():
    return {"handle": "mara.makes", "trip": {"name": "lisbon", "label": "lisbon week", "range": "14 to 18 sep", "year": 2026},
            "stops": [stop(0, "alfama", "alfama at seven, the lane to ourselves"),
                      stop(1, "graça", "tram up to graça, standing room only", aspect=1.7778, clip=True),
                      stop(2, "belém", "walked the river all the way out to belém", aspect=0.75),
                      stop(3, "sintra", "train to sintra, lost in the yellow palace"),
                      stop(4, "bairro alto", "last night, the fountain lit up, we stayed")]}


class Captions(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
        self.addCleanup(shutil.rmtree, d, True)
        cwd = os.getcwd()
        os.chdir(d)
        self.addCleanup(os.chdir, cwd)
        (Path("public") / "matched").mkdir(parents=True)
        patch = mock.patch.object(_env, "read_json", return_value=None)
        patch.start()
        self.addCleanup(patch.stop)

    def board(self, gray, **lay):
        """The letterbox board of the trip with every photograph one flat `gray` (0-255), its card's photo layout changed
        by `lay` ({"line": {"scrim": 0.3}})."""
        from PIL import Image
        for i in range(5):
            Image.new("RGB", (900, 900), (gray,) * 3).save(Path("public") / "matched" / f"{i}.jpg", quality=95)
        b = storyboard.make_board("1", LOOK, trip(), {"swatches": SWATCHES})
        for part, values in lay.items():
            b["system"]["photo"][part].update(values)
        return b

    def stops(self, b):
        return [x for x in b["beats"] if x["form"] in ("photo", "clip") and x["words"]]

    def test_a_bright_photograph_deepens_the_scrim_and_a_dark_one_keeps_the_cards(self):
        bright = self.board(255, line={"scrim": 0.3})
        captions.remedy(bright)
        self.assertTrue(self.stops(bright))
        for x in self.stops(bright):
            self.assertGreater(x.get("scrim", 0), 0.3, x["id"])
        self.assertEqual(captions.findings(bright), [])
        dark = self.board(40, line={"scrim": 0.3})
        captions.remedy(dark)
        self.assertEqual([x["id"] for x in dark["beats"] if "scrim" in x or "labelColor" in x], [])
        self.assertEqual(captions.findings(dark), [])

    def test_a_label_that_does_not_read_in_its_own_color_takes_the_lines(self):
        b = self.board(255, line={"scrim": 0.6})
        before = [t for t in captions.findings(b) if '"GRAÇA"' in t]
        self.assertTrue(before and "under the 4.5:1 a 34 px line needs" in before[0], before)
        captions.remedy(b)
        labelled = {c["beat"]["id"] for c in captions.captions(b) if c["part"] == "label"}
        self.assertTrue(labelled)
        for x in b["beats"]:
            if x["id"] in labelled:
                self.assertEqual(x.get("labelColor"), b["system"]["photo"]["line"]["color"], x["id"])
                self.assertNotIn("scrim", x, f"{x['id']}: the line's color reads at the card's scrim")
        self.assertEqual(captions.findings(b), [])
        dark = self.board(40, line={"scrim": 0.6})
        captions.remedy(dark)
        self.assertEqual([x["id"] for x in dark["beats"] if "labelColor" in x], [])

    def test_words_no_scrim_lifts_are_named_and_their_scrim_never_deepened(self):
        b = self.board(90, line={"color": "ink"})
        captions.remedy(b)
        found = captions.findings(b)
        named = [t for t in found if "a scrim never lifts dark words" in t]
        self.assertTrue(named, found)
        self.assertRegex(named[0], r'^legible: [\w-]+: ".+" reads 1\.\d:1 over the photograph under it \(scrim 0\.\d\d\), '
                                   r"under the \d(\.5)?:1 a \d+ px line needs on a phone: ")
        self.assertEqual([x["id"] for x in self.stops(b) if "scrim" in x], [])

    def test_a_line_under_32_px_is_named(self):
        b = self.board(40, label={"size": 28})
        captions.remedy(b)
        found = captions.findings(b)
        self.assertTrue([t for t in found if re.search(r'^legible: stop-\d: "[A-ZÇÉ ]+" is set at 28 px, under the 32 px a phone '
                                                       r"shows legibly", t)], found)
        ok = self.board(40)
        captions.remedy(ok)
        self.assertEqual(captions.findings(ok), [])

    def test_the_title_cards_words_on_a_bright_last_photograph_get_a_veil_under_the_closer(self):
        b = self.board(255)
        self.assertTrue([t for t in captions.findings(b) if t.startswith('legible: closer: "@mara.makes"')], captions.findings(b))
        captions.remedy(b)
        self.assertGreater(b["beats"][-1].get("scrim", 0), 0)
        self.assertEqual(captions.findings(b), [])
        dark = self.board(40)
        captions.remedy(dark)
        self.assertNotIn("scrim", dark["beats"][-1])

    def test_words_over_a_photograph_the_run_does_not_hold_are_named(self):
        b = self.board(40)
        (Path("public") / "matched" / "2.jpg").unlink()
        self.assertTrue([t for t in captions.findings(b) if "matched/2.jpg is not in public/" in t])

    def test_the_storyboard_check_writes_the_remedy_on_its_beats_and_names_nothing_it_reached(self):
        b = self.board(255, line={"scrim": 0.3})
        beats, issues = storyboard.check_board(b)
        self.assertEqual([t for t in issues if t.startswith("legible")], [])
        stops = [x for x in beats if x["form"] in ("photo", "clip") and x["words"]]
        self.assertTrue(stops)
        self.assertTrue(all(x.get("scrim", 0) > 0.3 for x in stops), [(x["id"], x.get("scrim")) for x in stops])


if __name__ == "__main__":
    unittest.main()
