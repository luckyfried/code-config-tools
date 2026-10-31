"""The proof: every critic round before deliver renders the films at half size, and the deliver render is full size.
A proof paints a quarter of the film's pixels.

Each kit's round render writes its proof beside the film it stands for, in the same folder, and never over it:
of(film) names it (out/proof.mp4 for out/film.mp4, render/proof-cut.mp4 for render/cut.mp4). The stills (the frames
the critics read, the cover, the cards) render as the full render makes them, since a still is one frame. The full-size
render takes the proof's films away, so while a film's proof is beside it the newest render is the proof: the kit's
checks and critic rounds read it and say so on their first line, and deliver.py refuses it. A check that measures a
proof's pixels measures in board units: a size or a place read on the proof is divided by SCALE before it is held to
the board's.
"""
from pathlib import Path

SCALE = 0.5


def of(film):
    """The proof's file for a film's: out/film.mp4 is out/proof.mp4, out/film-square.mp4 is out/proof-square.mp4, and
    any other name takes proof- in front (out/series.mp4 is out/proof-series.mp4)."""
    p = Path(film)
    return p.with_name("proof" + p.name[len("film"):] if p.name.startswith("film") else "proof-" + p.name)


def films(out="out"):
    """Every proof film in the folder `out`."""
    return sorted(Path(out).glob("proof*.mp4"))


def scale(film="out/film.mp4"):
    """The scale of the newest render of `film`: SCALE while its proof is beside it, else 1."""
    return SCALE if of(film).exists() else 1


def newest(film="out/film.mp4"):
    """The newest render of `film`: its proof while the proof is beside it, else the film."""
    return of(film) if of(film).exists() else Path(film)


def board(px, at):
    """A measurement in px of a render at scale `at`, in board units: (540, 960) of a half-size proof is (1080, 1920)."""
    return tuple(round(v / at) for v in px)


def reading(film):
    """The first line of a command that reads a proof."""
    return f"reading the half-size proof {film}: every size below is in board units, as the full-size film's would be"


def refusal(film="out/film.mp4", then="film.py render for the full-size film, then qa.py check and vote.py cut, where the "
                                     "critics read the type at full size, then deliver.py again"):
    """What deliver.py says when the newest render is a proof: what to run instead."""
    return f"not delivered: the newest render is the half-size proof {of(film)}; run {then}"
