"""The sound a board lays under its music, in the shape the shared effects (scripts/sfx.py) read: one beat each for the
title, every photograph, the wall and the closer, with the moments the picture lands. sfx.py makes every effect from
it, keyed to the music and on its grid: a whoosh on each cut, a shutter as a photograph arrives (a pop where its move
lays a mark), an impact as the title's line lands and on every slammed word, and a riser into the closer with an
impact on it. `cues` turns those effects into the storyboard's sound lines, so the board says where every sound goes
and the master plays exactly those."""
import sfx

# what each effect is, as the storyboard says it
SAID = {"bright": "the first cut's bright sweep", "sweep": "a warm sweep on the cut", "air": "soft air into the dissolve",
        "shutter": "the photograph lands", "pop": "the mark lands on the photograph", "impact": "an impact",
        "riser": "the build into the close"}


def beat(bid, kind, start, form=None, move=None, cut=None, arrive=None, end=None, pull=None, **layer):
    """One beat of an effects board: its layer `kind` (Title, Photo, Words, Wall, Closer) and its moments in beats: its
    start, the photograph's arrival, its end, and the beat its words start to leave (`pull`, which a slam-words move's
    words land before)."""
    at = {"arrive": round(start if arrive is None else arrive, 4)}
    for key, v in (("end", end), ("pull", pull)):
        if v is not None:
            at[key] = round(v, 4)
    return {"id": bid, "form": form or kind.lower(), "move": move, "transition": cut, "start": round(start, 4),
            "layers": [{"kind": kind, "at": at, **layer}]}


def board(bid, bpm, beats):
    """An effects board: its id (the seed of its sounds' variation), its tempo and its beats."""
    return {"id": bid, "bpm": bpm, "beats": beats}


def cues(fx, music_bpm, stop=None):
    """The storyboard's sound lines for the effects board `fx`: every effect sfx.py lays, at its beat of the board (on
    the music's grid), the beat it sounds on and what it is; with `stop`, the beat picture and sound stop together, last."""
    sec = 60.0 / fx["bpm"]
    starts = [(b["start"], b["id"]) for b in fx["beats"]]
    out = []
    for t, kind in sfx.events(fx, music_bpm)[0]:
        at = t / sec
        # an effect sounds on the latest beat that has begun by then (a cut's whoosh peaks on the cut itself)
        on = max((s for s in starts if s[0] <= at + 0.26), default=starts[0])[1]
        out.append({"kind": kind, "at": round(at, 3), "beat": on, "what": SAID[kind]})
    if stop is not None:
        out.append({"kind": "stop", "at": round(stop, 3), "beat": fx["beats"][-1]["id"], "what": "picture and sound stop together"})
    return out
