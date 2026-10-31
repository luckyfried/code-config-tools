"""A card stamps the month its first photograph was taken: a person whose first photograph is not the one of their
moment has that photograph's month on their card, without the moment's place; a first photograph taken in the moment's
month keeps the moment's place and month, and a photograph the index does not hold changes nothing.

    python3 -I -m unittest discover -s S/tests -p test_stamp.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import boards  # noqa: E402
from test_many_people import run_folder  # noqa: E402


class Stamp(unittest.TestCase):
    def stamps(self, index):
        here = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            os.chdir(d)
            try:
                run_folder(d, 3)
                Path(d, "photo_index.json").write_text(json.dumps(index))
                return {p.handle: p.stamp for p in boards.Ctx().people}
            finally:
                os.chdir(here)

    def test_a_first_photograph_from_another_month_stamps_its_own_month_without_the_moments_place(self):
        got = self.stamps([{"src": "matched/dani.reyes-0.jpg", "month": 3}, {"src": "matched/theo.makes-0.jpg", "month": 4}])
        self.assertEqual(got["dani.reyes"], "march")
        self.assertEqual(got["theo.makes"], "porto, april")
        self.assertEqual(got["ines.walks"], "oaxaca, may")


if __name__ == "__main__":
    unittest.main()
