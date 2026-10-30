"""The export reader (scripts/gather.py): a post's media file is the file at the exact path the post names, the
largest folder of photos under the workspace is found however few photos it holds, and a folder of photos the person
names is their subject's timeline, dated by its file names and captioned from the captions kept beside it.

    python3 -m unittest discover -s S/tests        (S = this skill's folder)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import gather  # noqa: E402


class Media(unittest.TestCase):
    def test_a_post_takes_the_file_at_its_exact_path_and_never_a_namesake(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            root = Path(d)
            (root / "media" / "posts" / "202501").mkdir(parents=True)
            (root / "media" / "reels" / "202502").mkdir(parents=True)
            here = root / "media" / "posts" / "202501" / "a.jpg"
            here.write_bytes(b"a")
            (root / "media" / "reels" / "202502" / "b.jpg").write_bytes(b"b")
            m = gather.Media(root)
            self.assertEqual(m.resolve("media/posts/202501/a.jpg"), str(here.resolve()))
            self.assertIsNone(m.resolve("media/posts/202501/b.jpg"))
            self.assertIsNone(m.resolve("https://example.com/a.jpg"))


class PhotoFolder(unittest.TestCase):
    def test_a_folder_of_a_few_photos_is_found(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            root = Path(d)
            (root / "progress").mkdir()
            for name in ("before.jpg", "during.jpg", "after.jpg"):
                (root / "progress" / name).write_bytes(b"jpg")
            (root / "notes").mkdir()
            (root / "notes" / "one.png").write_bytes(b"png")
            (root / "empty").mkdir()
            self.assertEqual(gather.largest_photo_folder(root), root / "progress")
            self.assertIsNone(gather.largest_photo_folder(root / "empty"))

    def test_a_folder_named_by_date_with_its_captions_is_the_subjects_timeline_from_its_first_photo(self):
        from PIL import Image
        said = {"2025-11-02": "day one: bare roof and six empty pots", "2026-02-14": "beds are in and the kitchen garden is planted",
                "2026-06-20": "first tomatoes, finally", "2026-09-30": "everything in bloom"}
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ws = Path(d)
            (ws / "posts").mkdir()
            for i, day in enumerate(said):
                Image.new("RGB", (300, 200), (40 + 50 * i, 120, 90)).save(ws / "posts" / f"{day}.jpg")
            # a caption with an unquoted comma, as a person types it
            (ws / "posts" / "captions.csv").write_text("date,caption\n" + "".join(f"{k},{v}\n" for k, v in said.items()))
            env = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
            for args in (["gather.py", "--photos", "posts"], ["timeline.py", "--subject", "garden"]):
                r = subprocess.run([sys.executable, str(KIT / "scripts" / args[0]), *args[1:]], cwd=ws, env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            run = ws / "build" / (ws / "build" / "RUN").read_text().strip()
            lib = json.loads((run / "library.json").read_text())
            import datetime as dt
            self.assertEqual([(dt.datetime.fromtimestamp(p["ts"], dt.timezone.utc).date().isoformat(), p["caption"]) for p in lib["posts"]],
                             list(said.items()))
            sub = json.loads((run / "subject.json").read_text())
            self.assertEqual((sub["first"]["date"], sub["latest"]["date"], len(sub["posts"])), ("2025-11-02", "2026-09-30", 4))


if __name__ == "__main__":
    unittest.main()
