#!/usr/bin/env python3
"""The music under the reel, the series and every animated card: the person's own track when they placed one, else a
bed composed here on real instruments (music_engine.py) in the recipe of the winning look's style card.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py make [--seconds S]

make refuses until the vote has a winner. A track the person placed as music/source.<ext> wins: music.json names it.
Otherwise make composes music/bed.wav with music_engine.compose: the recipe is the winning style card's `music`,
unless the `styles` words of taste.json `music` name another; its `avoid` words take out an instrument, the drums or a
groove; the tempo is the board's music tempo (storyboard.json `music.bpm`, so every cut lands on the bed's beat); the
key comes from the board's accent color, the sections turn on the reel's impacts, the bed lifts into the peak beat (from
where its photograph lands to its end), and the seed is the run's folder
name. music.json carries the file, its origin, the bed's key and grid, and storyboard.md's Music line carries the
origin. The engine's own effect files (music/fx/) are not played: the films' effects are sfx.py's.

film.py masters each render's music with `master`: the bed from the render's first frame, the music alone, at -14 LUFS
by one gain, written in 32-bit float. On the reel the bed cuts at the board's stop; on a card cut from the series and
on the series it fades over the last 1.2 s. The film's mux (sfx.mux) then lays the board's sound effects over it and
masters the two together through one limiter.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music_engine  # noqa: E402


def brief(run):
    """The person's music brief from taste.json: `styles` and `avoid` words."""
    return (_env.read_json(run / "taste.json") or {}).get("music") or {}


def noted(md, said):
    """storyboard.md's line that starts with the label of `said` (its text up to the first colon), written as `said`."""
    if md.exists():
        label = said.split(":")[0]
        _env.write_text(md, re.sub(rf"(?m)^{re.escape(label)}: .*$", lambda _: said, md.read_text()))


def hue(board):
    """The hue of the board's accent color, degrees (None with no colors)."""
    colors = (board.get("look") or {}).get("colors") or {}
    lead = colors.get("accent") or colors.get("ink")
    return music_engine.hue_of(lead) if lead else None


def edges(board):
    """Where the bed's sections turn: the reel's impacts, in seconds."""
    r = board.get("reel") or {}
    return [c["at"] * 60 / r["bpm"] for c in r.get("sound") or [] if c["kind"] == "impact"]


def peak(board):
    """The story's peak, in seconds: where the peak beat's photograph lands (its landing sound, else its hold's start,
    else the beat's start) and where the beat ends; None when the board marks no peak."""
    r = board.get("reel") or {}
    beat = next((b for b in (r.get("timeline") or {}).get("beats") or [] if b.get("peak")), None)
    if not beat:
        return None
    cue = next((b for b in (r.get("fx") or {}).get("beats") or [] if b["id"] == beat["id"]), None)
    arrive = ((cue or {}).get("layers") or [{}])[0].get("at", {}).get("arrive")
    land = arrive if arrive is not None else (beat.get("held") or [beat["at"]])[0]
    return round(land * 60 / r["bpm"], 3), round(beat["end"] * 60 / r["bpm"], 3)


# ------------------------------------------------------------------ make
def cmd_make(a):
    run = _env.writable_run()
    won = (_env.read_json(run / "winner.json") or {}).get("board")
    if not won:
        sys.exit("no winner: the boards have not passed the vote; run vote.py ballot, fill it in, then vote.py tally")
    music = run / "music"
    music.mkdir(parents=True, exist_ok=True)
    board = _env.read_json(run / "storyboards" / won / "storyboard.json")
    if not board:
        sys.exit(f"{run / 'storyboards' / won / 'storyboard.json'} is missing: run storyboard.py draft")
    md = run / "storyboards" / won / "storyboard.md"
    if a.seconds is not None and a.seconds <= 0:
        sys.exit("--seconds is the bed's length, more than 0")
    # as long as the longest render it plays under: the series or the reel
    seconds = a.seconds or max(sum(c.get("frames", 450) for c in board["beats"]), board["reel"]["frames"]) / 30 + 1
    placed = sorted(p for p in music.glob("source.*") if p.stem == "source")
    if placed:
        origin = f"their own track, music/{placed[0].name}"
        _env.write_json(run / "music.json", {"file": str(placed[0].resolve()), "origin": origin})
        noted(md, f"Music: {origin}.")
        print(f"music: {placed[0]}, {origin}")
        return 0
    m = brief(run)
    card = board["music"]["recipe"]
    book = music_engine.recipes()
    try:
        info = music_engine.compose(card, m.get("styles") or [], m.get("avoid") or [], seconds, edges(board), hue(board),
                                    run.name, bpm=board["music"]["bpm"], out=music, peak=peak(board))
    except music_engine.Refusal as e:
        sys.exit(str(e))
    rid = info["recipe"]
    chose = "the look" if rid == card else "their brief"
    origin = (f"made by music.py from the {book['recipes'][rid]['name']} recipe (chosen by {chose}) in {info['key']} at "
              f"{info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json(run / "music.json", dict(info, file=str((music / "bed.wav").resolve()), origin=origin))
    noted(md, f"Music: {origin}.")
    print(f"music: {music / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ master
TARGET_LUFS = -14.0
FADE = 1.2


def integrated_file(path, spawn=subprocess.run):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
               "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


def master(bed, seconds, out, start=0.0, stop=None, spawn=subprocess.run):
    """`out` (a wav): `seconds` of the bed from `start`, the music alone. At `stop` (seconds from the render's first
    frame) the bed cuts; without a stop it fades over the last FADE s. Brought to -14 LUFS by one gain from one loudness
    read, and written in 32-bit float so a peak over full scale is kept whole: the film's mux (sfx.mux) lays the effects
    over it and limits music and effects together, once. Returns the integrated loudness measured on `out` (`lufs`).
    Every ffmpeg starts through `spawn`."""
    ff = _env.ffmpeg()
    end = f"afade=t=out:st={stop:.3f}:d=0.04" if stop and stop < seconds else f"afade=t=out:st={max(0.0, seconds - FADE):.3f}:d={min(FADE, seconds):.3f}"
    pre = f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS,{end},aformat=sample_rates=48000:channel_layouts=stereo"
    r = spawn([ff, "-hide_banner", "-nostats", "-i", str(bed), "-af", f"{pre},ebur128=framelog=quiet", "-f", "null", "-"],
              capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    if not found:
        sys.exit(f"could not measure the loudness of {bed}")
    gain = TARGET_LUFS - float(found[-1])
    spawn([ff, "-y", "-v", "error", "-i", str(bed), "-af", f"{pre},volume={gain:.2f}dB", "-ar", "48000", "-c:a", "pcm_f32le",
           str(out)], check=True)
    return {"lufs": integrated_file(out, spawn)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["make"])
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    a = ap.parse_args()
    return cmd_make(a)


if __name__ == "__main__":
    sys.exit(main())
