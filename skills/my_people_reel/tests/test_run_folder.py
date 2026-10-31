"""The run folders: a film drafted or snapped again on a run that delivered one (another board, another track, another
order) starts a new run carrying its people, board and vote, and leaves the delivered film where it is.

    python3 -I -m unittest discover -s S/tests
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _env  # noqa: E402


def delivered_workspace(root):
    run = Path(root, "build", "20260101T000000Z")
    for d in ("out", "render", "qa", "storyboards/drive", "music"):
        (run / d).mkdir(parents=True)
    for f in ("out/film.mp4", "film.json", "winner.json", "people.json", "storyboards/drive/storyboard.json", "music/source.wav"):
        (run / f).write_text(f)
    Path(root, "build", "current").write_text(run.name + "\n")
    return run


def enter(root, **kw):
    os.environ.pop("MPR_RUN", None)
    _env.WORKSPACE = root
    return _env.enter_run(**kw)


def test_second_film_starts_its_own_run():
    here = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as root:
        try:
            first = delivered_workspace(root)
            second = enter(root, again=True)
            assert second != first.resolve()
            assert Path(root, "build", "current").read_text().strip() == second.name
            assert (first / "out" / "film.mp4").read_text() == "out/film.mp4"
            assert sorted(p.name for p in second.iterdir()) == ["music", "people.json", "storyboards", "winner.json"]
            assert enter(root, again=True) == second   # the new run holds no film yet, so the next step stays in it
            assert enter(root) == second
        finally:
            os.chdir(here)


def test_a_run_with_no_film_is_entered_as_it_is():
    here = os.getcwd()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as root:
        try:
            first = delivered_workspace(root)
            (first / "out" / "film.mp4").unlink()
            # the sheets put the three looks in out/boards.png before any film is cut: that run has delivered nothing
            (first / "out" / "boards.png").write_bytes(b"png")
            assert enter(root, again=True) == first.resolve()
        finally:
            os.chdir(here)


class RunFolders(unittest.TestCase):
    def test_second_film_starts_its_own_run(self):
        test_second_film_starts_its_own_run()

    def test_a_run_with_no_film_is_entered_as_it_is(self):
        test_a_run_with_no_film_is_entered_as_it_is()

    def test_a_new_draft_on_a_delivered_run_starts_its_own_run(self):
        from unittest import mock
        import storyboard
        for cmd, again in (("draft", True), ("snap", True), ("check", False), ("sheets", False)):
            with mock.patch.object(storyboard._env, "enter_run") as entered, \
                    mock.patch.object(storyboard, f"cmd_{cmd}", return_value=0), mock.patch.object(sys, "argv", ["storyboard.py", cmd]):
                storyboard.main()
            entered.assert_called_once_with(again=again)


if __name__ == "__main__":
    unittest.main()
