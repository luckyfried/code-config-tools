"""The caption and the words the gate reads: a person who never uses a hashtag gets none, and the English word "none"
is not a leaked value.

    python3 -I -m unittest discover -s S/tests
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import deliver  # noqa: E402
import qa  # noqa: E402

TASTE = {"year": 2026, "people": [{"handle": "ze.do.largo"}, {"handle": "tomas.surf"}]}


def drafted(hashtags):
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            return deliver.caption(dict(TASTE, register={"lowercase": True, "hashtags": hashtags}), {})
        finally:
            os.chdir(here)


class CaptionGate(unittest.TestCase):
    def test_a_person_who_never_uses_a_hashtag_gets_none(self):
        self.assertNotIn("#", drafted([]))

    def test_a_person_who_uses_hashtags_gets_theirs(self):
        self.assertIn("#portra", drafted(["#portra"]))

    def test_the_word_none_is_english_and_python_none_is_a_leak(self):
        self.assertIsNone(qa.PLACEHOLDER.search("closed: none under the workspace"))
        self.assertIsNotNone(qa.PLACEHOLDER.search("their best line: None"))


if __name__ == "__main__":
    unittest.main()
