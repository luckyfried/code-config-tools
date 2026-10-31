#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed from the picked style and their music brief, with its beat
grid, mastered to -14 LUFS and cut at the board's stop, with its energy a frame for the shared layer.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/music.py find [--origin "..."]   # music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--bpm N] [--seconds S]
                                                      # a bed composed here on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze                # a track they brought: onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master [--seconds S]   # the music at -14 LUFS by one gain, cut at the board's stop,
                                                      # and music/energy.json

find takes a track the person or the agent placed at music/source.<ext> in the run (any audio ffmpeg reads; --origin
says where it came from) since music.json was written, else keeps the track music.json names, else runs `make`; a bed
`make` composed for another look than the one picked is made again for the picked one.
make composes a bed with music_engine.py into a folder of its own (music/bed-<n>/bed.wav): the
recipe is the picked style's (`music` in its card, else the style's id), unless the brief's `styles` words (taste.json
`music`) name another; its `avoid` words take out an instrument, the drums or a groove; the key comes from the year's
leading color, the tempo from the brief's or the board's, the sections from the board's `turn` marks (the peak's
landing and the closer's), and the seed is the run's folder name. make writes the bed's own beat grid (bpm, beats,
downbeats, sections, key) into music.json, so analyze leaves it as it is; analyze is for a track they brought: it reads
the energy envelope (ffmpeg decodes to mono PCM), picks onsets as peaks of its rise, takes the tempo by autocorrelation
and lays a beat grid on the strongest phase. storyboard.py snap starts the film on the grid.

master brings the music to -14 LUFS by one gain and cuts it at the board's `stop`, where the picture and the music stop
together: the music lets go over the 0.6 s after it, and the rest is silence. Nothing limits it: it is written in 32-bit
float, so a peak past full scale is kept whole for the film's mux to limit with the effects, once. It writes
music/master-<n>.wav, which music.json names, and music/energy.json, the master's loudness a frame (sfx.energy), which
the shared layer reads. The film's sound effects are the shared layer's (sfx.py): film.py lays them over the master as
it muxes each film, on the music's grid and in its key, so the master carries the music alone.
"""
import argparse
import array
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import look  # noqa: E402
import music_engine  # noqa: E402
import sfx  # noqa: E402
from board_drive import BPM, FPS, LENGTH  # noqa: E402

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
    index = Path("music.json")
    named = (_env.read_json(index) or {}).get("file")
    # A person places a track at music/source.<ext>, the one fixed name. A track there older than music.json is one the
    # current music.json already names or replaced (make removes it after its music.json), unless --origin says it was
    # just placed; otherwise the track music.json names stays the music.
    since = index.stat().st_mtime_ns if index.exists() and not a.origin else -1
    placed = [p for p in MUSIC.glob("source.*")
              if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov") and p.stat().st_mtime_ns > since]
    newest = max(placed, key=lambda p: p.stat().st_mtime_ns, default=None)
    if newest and has_audio(newest):
        info = {"file": str(newest), "origin": a.origin or "placed by the agent in music/", "seconds": round(duration(newest), 2)}
    elif named and Path(named).is_file() and has_audio(named) and not remade():
        print(f"music: {named}, the track music.json names")
        return 0
    else:
        return cmd_make(a)
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def remade():
    """Whether the bed music.json names was made for another look than the one picked: a bed `make` composed carries
    the style it was made for, and a pick of another look makes the bed again; a track the person brought stays."""
    info = _env.read_json("music.json") or {}
    return bool(info.get("recipe")) and info.get("style") != card()[0]


def brief():
    """The person's music brief from taste.json (`mood`, `tempo`, `styles`, `avoid`)."""
    return (_env.read_json("taste.json") or {}).get("music") or {}


# ------------------------------------------------------------------ make
def card():
    """The picked style and its music recipe id (the card's `music`, else the style's id); None and None before a pick."""
    style = (_env.read_json("winner.json") or {}).get("board")
    if not style:
        return None, None
    return style, look.card(style).get("music") or style


def hue():
    """The year's leading color's hue, degrees (None with no year palette)."""
    year = ((_env.read_json("taste.json") or {}).get("palette") or {}).get("year") or []
    return music_engine.hue_of(year[0]["hex"]) if year else None


def edges(board, bpm):
    """The board's `turn` marks, in seconds at the bed's tempo (the half, whole or double nearest the board's): where
    the film lands, so where the bed's sections turn."""
    if not (board and board.get("bpm")):
        return []
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    return [q["at"] * 60 / (bpm * k) for q in board.get("sound") or [] if q["kind"] == "turn"]


def peak(board, bpm):
    """The story's peak beat on the board, (landing, end) in seconds at the bed's tempo (the half, whole or double
    nearest the board's), where the bed lifts; None when the board marks no peak."""
    if not (board and board.get("bpm")):
        return None
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    at = 0.0
    for b in board.get("beats") or []:
        if b.get("peak"):
            return at * 60 / (bpm * k), (at + b["bars"] * 4) * 60 / (bpm * k)
        at += b["bars"] * 4
    return None


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    style, recipe_id = card()
    board = _env.read_json(f"storyboards/{style}/board-reel.json") if style else None
    m = brief()
    target = m.get("tempo") or (board or {}).get("bpm") or BPM
    # make runs before snap fixes the film's length, so the bed runs past the longest film, with four seconds for the
    # start the cut takes on a downbeat, and master trims it
    seconds = a.seconds or LENGTH[1] + 4
    seed = Path.cwd().name
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    bpm = music_engine.tempo(recipe, a.bpm, target, seed)
    # the bed takes a folder of its own, so the track the current music.json names stays whole until
    # the new music.json names the bed, and goes only after
    made = MUSIC / f"bed-{time.time_ns():x}"
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(board, bpm), hue(),
                                seed, bpm=bpm, out=made, peak=peak(board, bpm))
    default = recipe_id if recipe_id in book["recipes"] else book["default"]
    chose = "their brief" if rid != default else "the look" if default == recipe_id else "the kit's default"
    origin = (f"made for this film ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    # the engine plays its own effects beside the bed; the film's effects are the shared layer's, so music.json names
    # only the bed
    keep = {k: v for k, v in info.items() if k not in ("fx", "fx_recipe")}
    _env.write_json("music.json", dict(keep, file=str(made / "bed.wav"), origin=origin, style=style))
    for f in [*MUSIC.glob("source.*"), *MUSIC.glob("bed-*")]:
        if f != made:
            shutil.rmtree(f) if f.is_dir() else f.unlink()
    print(f"music: {made / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
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


def integrated_file(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
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
    bpm = film.get("bpm") or info.get("bpm") or BPM
    start = float(film.get("music_start") or 0)
    ff = _env.ffmpeg()
    source = info["file"]
    stop = next((c["at"] * 60 / bpm for c in film.get("sound") or [] if c["kind"] == "stop"), None)
    # With a stop, the music lets go over the held picture and the rest is silence. Without one, the music
    # tails out over the film's last bar: the fade starts on the last downbeat at least a second before the end, so the
    # closer holds while the track lets go, never on a hard stop.
    bars = [d - start for d in info.get("downbeats") or [] if 0 < d - start <= seconds - 1.0]
    fade = seconds - bars[-1] if bars else min(2.0, seconds * 0.05)
    st, d = (stop + 0.3, 0.6) if stop and stop + 0.9 <= seconds else (seconds - fade, fade)
    pre = f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={st:.3f}:d={d:.3f}"
    def integrated(chain):
        r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", source, "-af", f"{chain},ebur128=framelog=quiet",
                            "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if not found:
            sys.exit(f"could not measure the loudness of {source}")
        return float(found[-1])

    # One gain onto -14 LUFS and nothing else: the master is written in 32-bit float, so a peak over full scale is kept
    # whole, and the film's mux (sfx.py) limits music and effects together, once.
    gain = TARGET_LUFS - integrated(pre)
    flt = f"{pre},volume={gain:.2f}dB,aformat=sample_rates=48000:channel_layouts=stereo"
    # the master takes a name of its own, so the one the current music.json names stays whole until the new music.json
    # names this one, and goes only after
    out = MUSIC / f"master-{time.time_ns():x}.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(out)], check=True)
    info["master"] = str(out)
    info["master_seconds"] = round(seconds, 3)
    info["master_lufs"] = round(integrated_file(out), 2)
    for k in ("sound_cues", "bed_lufs", "fx_lufs", "fx", "fx_recipe"):
        info.pop(k, None)
    _env.write_json("music.json", info)
    sfx.energy(ff, out, FPS, MUSIC / "energy.json")
    for f in [*MUSIC.glob("master-*.wav"), MUSIC / "master.wav"]:
        if f != out:
            f.unlink(missing_ok=True)
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}; its energy a frame -> {MUSIC / 'energy.json'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--origin", help="find: where a track placed at music/source.<ext> came from, for brief.md")
    a = ap.parse_args()
    _env.enter_run()
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
