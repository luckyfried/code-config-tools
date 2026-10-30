"""The generated clips: a clip that arrived is conformed to its photograph's size and its beat's length and placed on
that photograph's card from the beat's first frame; a request no model made is named in clips.json as not made, and
its card shows the photograph still.

    python3 -I -m unittest discover -s S/tests
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import clips  # noqa: E402


def ff(*args):
    subprocess.run([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


class Clips(unittest.TestCase):
    def test_an_arrived_clip_is_placed_on_its_card_and_a_request_not_made_leaves_the_still(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            (run / "public" / "photos").mkdir(parents=True)
            (run / "clips").mkdir()
            ff("-f", "lavfi", "-i", "color=c=0x996633:s=1200x1600", "-frames:v", "1", str(run / "public/photos/a.jpg"))
            ff("-f", "lavfi", "-i", "testsrc=s=640x360:r=24:d=1", "-pix_fmt", "yuv420p", str(run / "clips/02.mp4"))
            # the studio board the clips lane reads: the beats' frames and the clip requests the board lists
            board = {"beats": [{"id": "hook", "frames": 45}, {"id": "card-1", "frames": 53}],
                     "clips": [{"id": "01", "beat": "hook", "use": "the hook's world", "image": "photos/a.jpg",
                                "prompt": "p"},
                               {"id": "02", "beat": "card-1", "use": "a still brought to life", "image": "photos/a.jpg",
                                "prompt": "p"}]}
            was_run, was_board = _env._RUN, clips.board
            _env._RUN, clips.board = run, lambda: board
            try:
                self.assertEqual(clips.cmd_normalize(argparse.Namespace(why="no video model")), 0)
            finally:
                _env._RUN, clips.board = was_run, was_board
            got = json.loads((run / "clips.json").read_text())["clips"]
            self.assertEqual(got["01"]["status"], "not made")
            self.assertEqual(got["01"]["why"], "no video model")
            self.assertEqual(got["02"]["status"], "generated")
            self.assertEqual((got["02"]["from_frame"], got["02"]["frames"]), (45, 53))
            frames = sorted((run / "public" / got["02"]["dir"]).glob("*.jpg"))
            self.assertEqual(len(frames), 53)
            size = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   str(frames[0])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(size, "1200,1600")


class Stopped(unittest.TestCase):
    def test_a_normalize_stopped_partway_leaves_clips_json_naming_whole_frames(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            run = Path(d) / "build" / "run"
            old = run / "public" / "clips" / "02"
            old.mkdir(parents=True)
            for i in range(1, 4):
                (old / f"{i:04d}.jpg").write_bytes(b"frame")
            index = {"clips": {"02": {"status": "generated", "dir": "clips/02", "frames": 3, "image": "photos/a.jpg", "from_frame": 0}}}
            (run / "clips.json").write_text(json.dumps(index))
            (run / "clips").mkdir()
            (run / "clips" / "02.mp4").write_bytes(b"x" * 2000)
            board = {"beats": [{"id": "card-1", "frames": 3}],
                     "clips": [{"id": "02", "beat": "card-1", "use": "r", "image": "photos/a.jpg", "prompt": "p"}]}

            def stopped(src, image, frames, dst):
                dst.mkdir(parents=True, exist_ok=True)
                (dst / "0001.jpg").write_bytes(b"half")
                raise KeyboardInterrupt
            was_run, was_board, was_conform = _env._RUN, clips.board, clips.conform
            _env._RUN, clips.board, clips.conform = run, lambda: board, stopped
            try:
                with self.assertRaises(KeyboardInterrupt):
                    clips.cmd_normalize(argparse.Namespace(why=None))
                got = json.loads((run / "clips.json").read_text())["clips"]["02"]
                self.assertEqual(len(list((run / "public" / got["dir"]).glob("*.jpg"))), got["frames"])
            finally:
                _env._RUN, clips.board, clips.conform = was_run, was_board, was_conform


if __name__ == "__main__":
    unittest.main()
