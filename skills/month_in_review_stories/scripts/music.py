#!/usr/bin/env python3
"""The music under the reel, the series and every animated card: the person's own track when they placed one, else a
bed composed here on real instruments (music_engine.py) in the recipe of the winning look's style card, and the board's
sound cues played from the engine's sound effects and mixed under it.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py make [--seconds S]

make refuses until the vote has a winner. A track the person placed as music/source.<ext> wins: music.json names it.
Otherwise make composes music/bed.wav and its effects (music/fx/riser.wav, hit.wav, bright.wav, impact.wav) with
music_engine.compose: the recipe is the winning style card's `music`, unless the `styles` words of taste.json `music`
name another; its `avoid` words take out an instrument, the drums or a groove; the tempo is the board's music tempo
(storyboard.json `music.bpm`, so every cut lands on the bed's beat); the key comes from the board's accent color, the
sections turn on the reel's impact, and the seed is the run's folder name. music.json carries the file, its origin and
the bed's grid, and storyboard.md's Music line carries the origin.

film.py masters each render's sound with `master`: the bed from the render's first frame and, with the render's cues,
the effects stem scaled so its integrated loudness sits FX_UNDER_BED_LU under the bed's and summed with it, the whole
at -14 LUFS under a peak limiter at about -2 dBFS; on the reel the bed cuts at the board's `stop` cue and the last hit
rings out over RING s into silence over the held picture, and on a card cut from the series the bed fades over the
last 1.2 s. The stems stay beside the master: <name>.bed.wav, <name>.fx.wav and <name>.mix.wav. A track the person
brought gets the card's effects rendered at master.

The board builder (scripts/compose/reel.py, scripts/compose/stories.py) places one cue where each beat lands: `hit`
(with the bright ring when `bright`), `riser` (the build into the month's peak, cutting off into it), `impact` (the
line landing on the peak), `stop` (the bed cuts, the picture holds). Words rise and the camera moves without a sound of
their own.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music_engine  # noqa: E402

FX_UNDER_BED_LU = 8  # the effects stem's integrated loudness sits this far under the bed's
RING = 0.4  # after the reel's stop, the last hit rings out over this many seconds and the picture holds in silence
RISER_GAIN = 0.6  # the build sits under the hits and the landing it leads to


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
    """Where the bed's sections turn: the reel's impact, in seconds."""
    r = board.get("reel") or {}
    return [c["at"] * 60 / r["bpm"] for c in r.get("sound") or [] if c["kind"] == "impact"]


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
                                    run.name, bpm=board["music"]["bpm"], out=music)
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


# ------------------------------------------------------------------ sound design
# The storyboard places the film's sound where its beats land (a board's `sound` cues); each cue plays one of the
# engine's effect files. Nothing is laid automatically per move: a cue sounds only where the board puts one.
def duration(f, spawn=subprocess.run):
    r = spawn([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
              capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def effects(run, bpm):
    """The four effect files music.json names, or, for a track the person brought, the winning card's set rendered
    now at `bpm`."""
    info = _env.read_json(run / "music.json") or {}
    fx = info.get("fx") or {}
    if all(Path(fx.get(c) or "").is_file() for c in music_engine.CUES):
        return fx
    won = (_env.read_json(run / "winner.json") or {}).get("board")
    board = _env.read_json(run / "storyboards" / str(won) / "storyboard.json") or {}
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, (board.get("music") or {}).get("recipe"))
    h = hue(board)
    tonic = music_engine.tonic_of(h) if h is not None else music_engine.pick(music_engine.rng(run.name, "key"), range(12))
    music_engine.place(music_engine.render_fx(book, recipe, tonic, bpm, run / "music"))
    info.update(fx={c: str((run / "music" / "fx" / f"{c}.wav").resolve()) for c in music_engine.CUES}, fx_recipe=rid)
    _env.write_json(run / "music.json", info)
    return info["fx"]


def legs_of(cues, bpm, fx, spawn=subprocess.run):
    """Each cue as (file, from, at, gain): the file from `from` seconds, placed at `at` in the render, read at `bpm`.
    A riser is the end of riser.wav, as long as the cue's beats, ending on the moment it leads to."""
    sec, legs = 60 / bpm, []
    for c in cues:
        at = c["at"] * sec
        if c["kind"] == "hit":
            legs.append((fx["hit"], 0.0, at, c.get("weight", 0.6)))
            if c.get("bright"):
                legs.append((fx["bright"], 0.0, at, c["bright"]))
        elif c["kind"] == "riser":
            want, have = c["beats"] * sec, duration(fx["riser"], spawn)
            use = min(want, have)
            legs.append((fx["riser"], have - use, at + want - use, RISER_GAIN))
        elif c["kind"] == "impact":
            legs.append((fx["impact"], 0.0, at, 1.0))
    return legs


def fx_stem(legs, seconds, scale, dst, spawn=subprocess.run):
    """The legs summed over `seconds` of silence and scaled by `scale`, as a float stereo stem."""
    inputs = ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    graph = []
    for i, (f, f0, at, gain) in enumerate(legs, 1):
        inputs += ["-i", str(f)]
        graph.append(f"[{i}:a]atrim=start={f0:.4f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                     f"volume={gain:.4f},adelay={round(at * 1000)}:all=1[c{i}]")
    mixed = "[0:a]" + "".join(f"[c{i}]" for i in range(1, len(legs) + 1))
    graph.append(f"{mixed}amix=inputs={len(legs) + 1}:normalize=0:duration=first,volume={scale:.6f}[out]")
    spawn([_env.ffmpeg(), "-y", "-v", "error", *inputs, "-filter_complex", ";".join(graph), "-map", "[out]",
           "-ar", "48000", "-c:a", "pcm_f32le", str(dst)], check=True)


# ------------------------------------------------------------------ master
TARGET_LUFS = -14.0
FADE = 1.2


def integrated_file(path, spawn=subprocess.run):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
               "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


def master(bed, seconds, out, start=0.0, cues=(), bpm=None, fx=None, spawn=subprocess.run):
    """`out` (a wav): `seconds` of the bed from `start`; with cues (beats at `bpm` from the render's first frame), the
    cues played from the effect files `fx` names (music_engine.CUES) into an effects stem scaled so its integrated loudness sits FX_UNDER_BED_LU under the bed's and
    summed with it and, at a `stop` cue, the bed cut and the last hit ringing out over RING s into silence; without a
    stop, faded over the last FADE s. Brought to -14 LUFS under a fast limiter at about -2 dBFS. Returns the integrated
    loudness measured on `out` (`lufs`) and, with cues, the bed's and the effects' (`bed_lufs`, `fx_lufs`). Every
    ffmpeg starts through `spawn`."""
    ff = _env.ffmpeg()
    out = Path(out)
    source = str(bed)
    stop = next((c["at"] * 60 / bpm for c in cues if c["kind"] == "stop"), None) if cues else None
    mixed = {}
    if cues:
        bedw, fxw, mix = out.with_suffix(".bed.wav"), out.with_suffix(".fx.wav"), out.with_suffix(".mix.wav")
        cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
        spawn([ff, "-y", "-v", "error", "-i", source, "-af", f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS{cut},"
               "aformat=sample_rates=48000:channel_layouts=stereo", "-ar", "48000", str(bedw)], check=True)
        bed_lufs = integrated_file(bedw, spawn)
        legs = legs_of(cues, bpm, fx, spawn)
        # loudness gating is not linear in gain, so the stem is scaled again until it sits FX_UNDER_BED_LU under the bed
        scale = 1.0
        for _ in range(5):
            fx_stem(legs, seconds, scale, fxw, spawn)
            fx_lufs = integrated_file(fxw, spawn)
            if not legs or abs(bed_lufs - fx_lufs - FX_UNDER_BED_LU) < 0.04:
                break
            scale *= 10 ** ((bed_lufs - FX_UNDER_BED_LU - fx_lufs) / 20)
        mixed = {"bed_lufs": round(bed_lufs, 2), "fx_lufs": round(fx_lufs, 2)}
        spawn([ff, "-y", "-v", "error", "-i", str(bedw), "-i", str(fxw), "-filter_complex",
               "[0:a][1:a]amix=inputs=2:normalize=0:weights=1 1[out]", "-map", "[out]", "-ar", "48000", str(mix)], check=True)
        source, start = str(mix), 0.0
    st, d = (stop + 0.1, RING - 0.1) if stop and stop + RING <= seconds else (seconds - FADE, FADE)
    pre = f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={st:.3f}:d={d:.3f}"

    def integrated(chain):
        r = spawn([ff, "-hide_banner", "-nostats", "-i", source, "-af", f"{chain},ebur128=framelog=quiet",
                   "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if not found:
            sys.exit(f"could not measure the loudness of {source}")
        return float(found[-1])

    # gain past the target, a fast peak limiter, then a trim down onto -14 LUFS, so sharp hits reach the target unclipped
    gain = TARGET_LUFS - integrated(pre) + 1.5
    limited = f"{pre},volume={gain:.2f}dB,alimiter=limit=0.79:attack=1:release=60:level=false"
    trim = TARGET_LUFS - integrated(limited)
    flt = f"{limited},volume={trim:.2f}dB,aformat=sample_rates=48000:channel_layouts=stereo"
    spawn([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", str(out)], check=True)
    return {"lufs": integrated_file(out, spawn), **mixed}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["make"])
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    a = ap.parse_args()
    return cmd_make(a)


if __name__ == "__main__":
    sys.exit(main())
