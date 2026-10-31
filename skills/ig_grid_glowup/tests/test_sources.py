"""Where the film's words and photographs come from: a photograph's own caption or none, the band reading the library
caption whole, else the caption the post goes up with, a named folder's photographs carrying the words the person put with them (a
note beside the photograph, its embedded description) or none and never an encoder's signature, a carousel's slides kept apart from a photograph of one name in another folder,
an export's media found by its exact path, and the before grid carrying only what the film shows.

Run from anywhere: python3 -m unittest discover -s S/tests
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import storyboard as B  # noqa: E402
import gather  # noqa: E402
import plan as P  # noqa: E402
import qa  # noqa: E402
import drive  # noqa: E402


LONG = ("raced the 28 up the hill to graça with leonor and rita, the whole tram singing, and we got off at the top "
        "laughing so hard we missed the view")


def scratch():
    return tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))


class Sources(unittest.TestCase):
    def test_a_photo_with_no_words_of_its_own_borrows_no_other_posts_caption(self):
        pool = P.Pool.__new__(P.Pool)
        pool.captions = {"lib/a-0.jpg": "the fountain after midnight"}
        pool.lib = {"posts": [{"ts": 1000, "caption": "ana and rui said yes"}]}
        self.assertEqual(pool.words_for({"src": "lib/b-0.jpg", "ts": 1000}, set()), "")
        self.assertEqual(pool.words_for({"src": "lib/a-0.jpg", "ts": 1000}, set()), "the fountain after midnight")

    def test_the_film_band_reads_the_library_caption_else_the_caption_the_post_goes_up_with(self):
        slots = [{"n": n, "photo": f"photos/{n}.jpg", "size": [1200, 1600], "crop45": [0, 0, 1], "crop34": [0, 0, 1],
                  "focal": [0.5, 0.5], "date": "2026-10-27", "caption": "walked up beside the tram, it won",
                  "said": said, "follows": 1, "place": "calm"}
                 for n, said in ((1, ""), (2, "ana and rui said yes @ana.costa"))]
        stub = mock.Mock(graded_name=lambda p: "graded/" + Path(p).name)
        with mock.patch.object(B, "grade", stub):
            nine = B.next_posts({"slots": slots})
        self.assertEqual(nine[0]["caption"], "walked up beside the tram, it won")
        self.assertEqual(nine[1]["caption"], "ana and rui said yes @ana.costa")
        self.assertEqual(nine[0]["moment"], "walked up beside the tram, it won")

    def test_a_carousel_and_a_photo_of_one_name_in_another_folder_are_two_posts(self):
        self.assertEqual(P.parent("posts/x-1.jpg"), P.parent("posts/x-2.jpg"))
        self.assertNotEqual(P.parent("posts/x-1.jpg"), P.parent("photos/x-0.jpg"))

    def test_a_media_uri_resolves_by_its_exact_path_only(self):
        with scratch() as d:
            root = Path(d)
            (root / "media" / "posts").mkdir(parents=True)
            (root / "media" / "posts" / "b.jpg").write_bytes(b"x")
            md = gather.Media(root)
            self.assertEqual(md.resolve("media/posts/b.jpg"), str((root / "media" / "posts" / "b.jpg").resolve()))
            self.assertIsNone(md.resolve("media/stories/b.jpg"))

    def test_the_before_grid_carries_no_date(self):
        with scratch() as d:
            cells = [{"pos": 0, "ts": 1792698717, "caption": "new flat, same chaos", "a": {"colors": [{"rgb": [200, 190, 180]}]}}]
            with mock.patch.object(B, "PUBLIC", Path(d)):
                before = B.before_posts({"cells": cells})
        self.assertEqual(before[0]["caption"], "new flat, same chaos")
        self.assertFalse({"date", "full"} & set(before[0]))


    def photo(self, folder, name, **save):
        from PIL import Image
        Image.new("RGB", (40, 50), (180, 120, 90)).save(folder / name, **save)

    def test_a_named_photograph_carries_the_first_line_of_the_note_beside_it(self):
        with scratch() as d:
            root = Path(d)
            self.photo(root, "tram.jpg")
            (root / "tram.txt").write_text("raced the 28 up to graça with leonor, 2026\nsecond line stays off\n")
            self.photo(root, "fountain.jpg")
            posts, _ = gather.read_photos(root)
        said = {Path(r["media"][0]).name: r["caption"] for r in posts}
        self.assertEqual(said, {"tram.jpg": "raced the 28 up to graça with leonor, 2026", "fountain.jpg": ""})

    def test_a_named_photograph_carries_its_embedded_description(self):
        from PIL import Image
        with scratch() as d:
            root = Path(d)
            ex = Image.Exif()
            ex[270] = "rosa's focaccia, the figs from her tree"
            self.photo(root, "focaccia.jpg", exif=ex)
            posts, _ = gather.read_photos(root)
        self.assertEqual(posts[0]["caption"], "rosa's focaccia, the figs from her tree")

    def test_an_encoders_signature_in_a_photographs_comment_is_never_its_words(self):
        # ffmpeg writes its encoder into the comment of every JPEG it makes, the gd library its own; a caption there is theirs
        with scratch() as d:
            root = Path(d)
            self.photo(root, "dunes.jpg", comment=b"Lavc62.11.100\x00")
            self.photo(root, "tram.jpg", comment=b"CREATOR: gd-jpeg v1.0 (using IJG JPEG v62), quality = 82\n")
            self.photo(root, "figs.jpg", comment=b"the figs from rosa's tree")
            posts, _ = gather.read_photos(root)
        said = {Path(r["media"][0]).name: r["caption"] for r in posts}
        self.assertEqual(said, {"dunes.jpg": "", "tram.jpg": "", "figs.jpg": "the figs from rosa's tree"})

    def test_a_named_photograph_with_no_words_of_its_own_is_wordless(self):
        with scratch() as d:
            root = Path(d)
            self.photo(root, "2026-10-21-the-long-walk-home.jpg")
            posts, _ = gather.read_photos(root)
        self.assertEqual(posts[0]["caption"], "")

    def test_the_draft_reads_a_named_photographs_words_and_a_line_set_in_taste(self):
        pool = P.Pool.__new__(P.Pool)
        lib = {"photos": [{"ts": 1, "caption": "the nata came out at six, tomás timed it", "media": ["lib/photos/a.jpg"]},
                          {"ts": 2, "caption": "", "media": ["lib/photos/b.jpg"]}]}
        pool.captions = P.Pool.captions_of(lib, {"said": {"lib/photos/b.jpg": "rui's first loaf, flat and perfect"}})
        self.assertEqual(pool.captions["lib/photos/a.jpg"], "the nata came out at six, tomás timed it")
        self.assertEqual(pool.captions["lib/photos/b.jpg"], "rui's first loaf, flat and perfect")

    def test_the_band_shows_a_photographs_line_whole_never_its_first_clause(self):
        slots = [{"n": 1, "photo": "photos/1.jpg", "size": [1200, 1600], "crop45": [0, 0, 1], "crop34": [0, 0, 1],
                  "focal": [0.5, 0.5], "date": "2026-10-27", "caption": "the tram", "follows": 1, "place": "calm",
                  "said": LONG}]
        with mock.patch.object(B, "grade", mock.Mock(graded_name=lambda p: "graded/" + Path(p).name)):
            nine = B.next_posts({"slots": slots})
        self.assertEqual(nine[0]["caption"], LONG)

    def test_cards_name_the_pages_that_lost_their_line_when_the_photographs_came_with_words(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import test_storyboard as T
        before, nine, plan, breaks = T.people(nxt=[""] * 9)
        fb = drive.build("reel", before, nine, plan, None, breaks, None, None, "maren.okafor", T.BIO)
        self.assertEqual(qa.words_lost(fb, nine), [])
        # a held post's page shows its photograph's words; a post the frame passes carries none
        worded = [dict(p, caption=f"line {p['n']}") if p["n"] in (1, 4, 5) else p for p in nine]
        self.assertEqual(qa.words_lost(fb, worded), ["post-1", "post-5"])

if __name__ == "__main__":
    unittest.main()
