#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed from the winning board's style and their music brief, with
its beat grid, mastered to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder; the files named here are in build/):
    python3 S/scripts/music.py find [--origin "..."]  # music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--bpm N] [--seconds S]  # a bed composed here on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze               # a track they brought: onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master [--seconds S]  # from the first downbeat, the music alone cut at the board's stop
                                                     # (else its last bar faded), -14 LUFS by one gain, 32-bit float

find takes a track the person or the agent placed as build/music/source.<ext> (any audio ffmpeg reads); else `make`
composes music/bed.wav with music_engine.py: the recipe is the winning board's style card's (`music` in
styles/<id>.json), unless the brief's `styles` words (taste.json `music`) name another; its `avoid` words take out an
instrument, the drums or a groove; the key comes from the palette's leading color, the tempo from the brief's or the
board's, the sections turn on the board's impacts, the bed lifts into the story's peak (from where the peak month's
photograph opens to where its beat ends), and the seed is the board's style. make writes the bed's own beat
grid (bpm, beats, downbeats, sections, key) into music.json, so analyze leaves it as it is; analyze is for a track
they brought: it reads the energy envelope (ffmpeg decodes to mono PCM), picks onsets as peaks of its rise, takes the
tempo by autocorrelation and lays a beat grid on the strongest phase. storyboard.py snap cuts the film on the grid.

The sound effects are scripts/sfx.py's: film.py render lays them where the board's `sound` cues land, over the
master, and the shared mux masters the music and the effects together once (one gain onto -14 LUFS, one limiter, AAC
without noise substitution). So master writes the music alone: the trimmed bed (music/bed-cut.wav, 32-bit float) cut on
the board's `stop`, brought to -14 LUFS by one gain from one loudness read, with no limiter and no trim, and written in
32-bit float so a peak past full scale is kept whole for the mux's limiter. music.json and storyboard.md's `Mixed:` line
carry the music's loudness before the gain.
"""
import argparse
import array
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music_engine  # noqa: E402

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = Path("music")


def duration(f):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def has_audio(f):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def cmd_find(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    # only the person-facing name, source.<ext>: a bed make wrote (source.<stamp>.wav) is reached through music.json alone
    placed = sorted(p for p in MUSIC.glob("source.*") if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def brief():
    """The person's music brief from taste.json (`mood`, `tempo`, `styles`, `avoid`)."""
    return (_env.read_json("taste.json") or {}).get("music") or {}



# ------------------------------------------------------------------ make
def card():
    """The winning board's style card id and its music recipe id (None and None before a vote)."""
    won = (_env.read_json("winner.json") or {}).get("board")
    if not won:
        return None, None
    return won, (_env.read_json(_env.SKILL / "styles" / f"{won}.json") or {}).get("music") or won


def plan_of(won):
    return (_env.read_json(f"storyboards/{won}/plan.json") or {}).get("reel") if won else None


def hue():
    """The palette's leading color's hue, degrees (None with no palette)."""
    year = ((_env.read_json("taste.json") or {}).get("palette") or {}).get("year") or []
    return music_engine.hue_of(year[0]["hex"]) if year else None


def edges(won, bpm):
    """The board's impacts, in seconds at the bed's tempo (the half, whole or double nearest the board's): where the
    film lands, so where the bed's sections turn."""
    board = _env.read_json(f"storyboards/{won}/board-reel.json") if won else None
    if not (board and board.get("bpm")):
        return []
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    return [q["at"] * 60 / (bpm * k) for q in board.get("sound") or [] if q["kind"] == "impact"]


def peak(won, bpm):
    """The story's peak in seconds at the bed's tempo (the half, whole or double nearest the board's): where the peak
    month's photograph opens and where its beat ends; None when the board marks no peak."""
    board = _env.read_json(f"storyboards/{won}/board-reel.json") if won else None
    if not (board and board.get("bpm")):
        return None
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    m = next((m for m in (board.get("year") or {}).get("months") or [] if m.get("peak")), None)
    if not m:
        return None
    return m["at"]["open"][0] * 60 / (bpm * k), m["at"]["end"] * 60 / (bpm * k)


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    won, recipe_id = card()
    if not won:
        sys.exit("no winner: the bed is composed for the board that won the vote; run vote.py tally (or vote.py pick) first")
    plan = plan_of(won) or {}
    board = _env.read_json(f"storyboards/{won}/board-reel.json") or {}
    m = brief()
    target = m.get("tempo") or board.get("bpm")
    # snap moves the cut to the half, whole or double of the bed's tempo nearest the board's, so the bed runs past the
    # board's length at any of them, with four seconds for the start the cut takes on a downbeat
    seconds = a.seconds or (plan.get("seconds") or 60) * 1.5 + 4
    seed = won
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    bpm = music_engine.tempo(recipe, a.bpm, target, seed)
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(won, bpm), hue(),
                                seed, bpm=bpm, out=MUSIC, peak=peak(won, bpm))
    default = recipe_id if recipe_id in book["recipes"] else book["default"]
    chose = "their brief" if rid != default else "the card" if default == recipe_id else "the default"
    origin = (f"made by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json("music.json", dict(info, file=str(MUSIC / "bed.wav"), origin=origin))
    # a bed an older make wrote under its own name goes once music.json names this one; a placed source.<ext> stays
    for f in MUSIC.glob("source.*.wav"):
        if f.stem != "source":
            f.unlink()
    print(f"music: {MUSIC / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json("music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    if info.get("recipe"):
        print(f"music: {info['file']} was composed here, and its grid is its own: {info['bpm']:g} bpm, "
              f"{len(info['downbeats'])} downbeats")
        return 0
    sr, hop = 11025, 256
    raw = subprocess.run([_env.ffmpeg(), "-v", "error", "-i", info["file"], "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = array.array("h")
    pcm.frombytes(raw[: len(raw) // 2 * 2])
    frames = len(pcm) // hop
    energy = []
    for i in range(frames):
        seg = pcm[i * hop:(i + 1) * hop]
        energy.append(math.log1p(sum(x * x for x in seg) / hop))
    flux = [0.0] + [max(0.0, energy[i] - energy[i - 1]) for i in range(1, frames)]
    rate = sr / hop
    w = int(rate * 0.5)
    onsets = []
    for i in range(1, frames - 1):
        lo, hi = max(0, i - w), min(frames, i + w)
        local = flux[lo:hi]
        thr = sum(local) / len(local) * 1.6 + 0.02
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            if not onsets or (i / rate - onsets[-1][0]) > 0.1:
                onsets.append((i / rate, flux[i]))
    best, bpm, bpm_auto = 0.0, info.get("bpm") or 0, 100
    for cand in range(70, 161):
        lag = rate * 60 / cand
        s = 0.0
        for i in range(frames):
            j = int(i + lag)
            if j >= frames:
                break
            s += flux[i] * flux[j]
        s /= max(1, frames - lag)
        if s > best:
            best, bpm_auto = s, cand
    if not bpm:
        bpm = bpm_auto
    while bpm > 140:
        bpm /= 2
    while bpm < 70:
        bpm *= 2
    period = 60 / bpm
    total = frames / rate
    phases = [k * period / 32 for k in range(32)]
    def score(ph):
        return sum(v for t, v in onsets if abs(((t - ph + period / 2) % period) - period / 2) < 0.04)
    phase = max(phases, key=score)
    beats = [round(phase + k * period, 3) for k in range(int((total - phase) / period) + 1)]
    bar_scores = [sum(v for t, v in onsets if any(abs(t - b) < 0.05 for b in beats[o::4])) for o in range(4)]
    o = bar_scores.index(max(bar_scores))
    info.update({"bpm": round(bpm, 2), "onsets": [round(t, 3) for t, _ in onsets], "beats": beats,
                 "downbeats": beats[o::4], "analyzed_seconds": round(total, 2)})
    _env.write_json("music.json", info)
    print(f"music: {round(bpm, 1)} bpm, {len(onsets)} onsets, {len(beats)} beats, {len(info['downbeats'])} downbeats over {total:.1f} s")
    return 0


# ------------------------------------------------------------------ master
TARGET_LUFS = -14.0


def integrated_file(path, chain="anull"):
    """The integrated loudness, LUFS, of `path` through the filter chain `chain`; nan when it cannot be read."""
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", f"{chain},ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


def cmd_master(a):
    info = _env.read_json("music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    film = _env.read_json("film.json") or {}
    seconds = a.seconds or film.get("seconds")
    if not seconds:
        sys.exit("pass --seconds (the film length), or run storyboard.py snap first")
    start = float(film.get("music_start") or 0)
    ff = _env.ffmpeg()
    reel = _env.read_json((film.get("boards") or {}).get("reel", "")) if (film.get("boards") or {}).get("reel") else None
    cues = (reel or {}).get("sound") or []
    # the board's stop: the music cuts there and the film holds its picture to the end
    stop = next((c["at"] * 60 / reel["bpm"] for c in cues if c["kind"] == "stop"), None)
    bed = MUSIC / "bed-cut.wav"
    cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
    subprocess.run([ff, "-y", "-v", "error", "-i", info["file"], "-af", f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS{cut},"
                    "aformat=sample_rates=48000:channel_layouts=stereo", "-ar", "48000", "-c:a", "pcm_f32le", str(bed)], check=True)
    for old in (MUSIC / "fx.wav", MUSIC / "mix.wav"):
        old.unlink(missing_ok=True)
    # With a stop, the music has cut on it and the rest is silence. Without one, the music tails out over the film's last
    # bar: the fade starts on the last downbeat at least a second before the end, so the closer holds while the track lets
    # go, never on a hard stop.
    bars = [d - start for d in info.get("downbeats") or [] if 0 < d - start <= seconds - 1.0]
    fade = seconds - bars[-1] if bars else min(2.0, seconds * 0.05)
    pre = "anull" if stop and stop < seconds else f"afade=t=out:st={seconds - fade:.3f}:d={fade:.3f}"
    bed_lufs = integrated_file(bed, pre)
    if math.isnan(bed_lufs):
        sys.exit(f"could not measure the loudness of {bed}")
    # One gain onto -14 LUFS and nothing else: the master is written in 32-bit float, so a peak over full scale is kept
    # whole, and the film's mux (sfx.py) lays the effects over it and limits the two together, once.
    gain = TARGET_LUFS - bed_lufs
    out = MUSIC / f"master.{_env.stamp()}.wav"
    part = MUSIC / f".{out.stem}.part.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(bed), "-af", f"{pre},volume={gain:.2f}dB", "-ar", "48000", "-c:a", "pcm_f32le",
                    str(part)], check=True)
    os.replace(part, out)
    for k in ("fx_lufs", "sound_cues"):
        info.pop(k, None)
    info.update(master=str(out), master_seconds=round(seconds, 3), master_lufs=round(integrated_file(out), 2), bed_lufs=round(bed_lufs, 2))
    _env.write_json("music.json", info)
    if reel:
        import storyboard  # the reel's storyboard.md carries the music's loudness on its Mixed line
        md = Path(film["boards"]["reel"]).with_name("storyboard.md")
        if md.exists():
            _env.write_text(md, re.sub(r"(?m)^Mixed: .*$", lambda _: f"Mixed: {storyboard.mixed(info)}.", md.read_text()))
    for p in MUSIC.glob("master*.wav"):  # the master files music.json does not name
        if p != out:
            p.unlink()
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--origin", help="find: where a track placed at music/source.<ext> came from, for brief.md")
    a = ap.parse_args()
    _env.enter_build()
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
