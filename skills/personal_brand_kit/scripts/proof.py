"""The proof: every critic round before deliver renders the films at half size, and the deliver render is full size.
A proof paints a quarter of the film's pixels.

Each kit's round render writes its proof beside the film it stands for, in the same folder, and never over it:
of(film) names it (out/proof.mp4 for out/film.mp4, render/proof-cut.mp4 for render/cut.mp4). The stills (the frames
the critics read, the cover, the cards) render as the full render makes them, since a still is one frame. The full-size
render takes the proof's films away, so while a film's proof is beside it the newest render is the proof: the kit's
checks and critic rounds read it and say so on their first line, and deliver.py refuses it. A check that measures a
proof's pixels measures in board units: a size or a place read on the proof is divided by SCALE before it is held to
the board's.

A round's `cut` is picture(): the kit's hash of the cut (its boards) with the motion bundle that drew the film, so a
round never carries its scores to a film another bundle drew, and a film the bundle changed after is rendered again
before any round opens on it. A verdict stands only on the newest render: stale() says when its round scored another
film.
"""
import hashlib
import sys
from pathlib import Path

SCALE = 0.5
DIST = Path(__file__).resolve().parent.parent / "motion" / "dist"


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


def digest(film):
    """A rendered film's identity in a round: the first 16 hex digits of its bytes' SHA-256."""
    return hashlib.sha256(Path(film).read_bytes()).hexdigest()[:16]


def _bundle_files(dist):
    return sorted(p for p in Path(dist).rglob("*") if p.is_file())


def bundle(dist=None):
    """The motion bundle's hash: every file under `dist` (the kit's motion/dist) by its path and its bytes."""
    dist = Path(dist or DIST)
    h = hashlib.sha256()
    for p in _bundle_files(dist):
        h.update(p.relative_to(dist).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def picture(cut, film, dist=None):
    """The hash of what decides `film`'s picture, as a round records it: `cut` (the kit's hash of the cut's boards) and
    the motion bundle that drew it. A bundle file newer than the film means the bundle changed after the film was
    drawn, so the film is refused with what to run."""
    dist = Path(dist or DIST)
    made = Path(film).stat().st_mtime
    newer = [p for p in _bundle_files(dist) if p.stat().st_mtime > made]
    if newer:
        sys.exit(f"{film} was rendered before the motion bundle changed ({newer[0].relative_to(dist)} is newer): render "
                 "it again, then run vote.py cut")
    return hashlib.sha256(f"{cut}\0{bundle(dist)}".encode()).hexdigest()[:16]


def stale(data, now, film):
    """Why a verdict on round `data` cannot stand when the round scored a film other than the newest render (`film`,
    whose digest is `now`); None when it scored that film."""
    if data.get("film") == now:
        return None
    return (f"round {data.get('round')} scored another film than the newest render, {film}: run vote.py cut, which opens "
            "that film's round, and fill it in")
