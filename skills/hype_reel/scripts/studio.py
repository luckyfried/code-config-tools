"""The studio composition (motion/studio, built into motion/dist) as the jobs render.py draws: a run's film.json in, a
film or one frame of it out. A run's public/ folder is what the composition reads: the photographs and clips the steps
staged there, and the style faces, copied in here."""
from pathlib import Path

import clips
import grade
import storyboard


def public():
    """The run's public folder, with the kit's style faces in it."""
    storyboard.stage_assets()
    return grade.PUBLIC.resolve()


def props(board):
    """The composition's input: the film's board and the generated clips placed on its photographs."""
    return {"board": board, "clips": clips.placed()}


def still(board, frame, out, scale=1.0):
    return {"type": "still", "composition": "Film", "props": props(board), "frame": int(frame), "scale": scale,
            "out": str(Path(out).resolve())}


def video(board, out, frames, scale=1.0):
    """A film job; `frames` is the film's length, which the renderer holds the composition to."""
    return {"type": "video", "composition": "Film", "props": props(board), "frames": frames, "scale": scale,
            "out": str(Path(out).resolve())}
