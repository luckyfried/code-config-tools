#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed from the chosen look's style and their music brief, with its
beat grid, mastered to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py find --run R [--origin "..."]  # music.json: the track to use and where it came from
    python3 S/scripts/music.py make --run R [--bpm N] [--seconds S]
                                                             # a bed composed here on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze --run R               # a track they brought: onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master --run R [--seconds S]  # from the first downbeat, cut at the board's stop,
                                                             # -14 LUFS by one gain, in float, the end faded

find takes the track the person chose, placed as music/source.<ext> in the run (any audio ffmpeg reads); else `make`
composes music/bed.wav with music_engine.py: the recipe is the chosen look's style card's (`music` in
styles/<id>.json, else the style id itself), unless the brief's `styles` words (taste.json `music`) name another; its
`avoid` words take out an instrument, the drums or a groove; the key comes from the palette's leading color, the tempo
from the brief's or the story's, the sections from the effects' impacts (sfx.py over story.fx_board), and the seed is the run's folder name. make
writes the bed's own beat grid (bpm, beats, downbeats, sections, key) into music.json, so analyze leaves it as it is;
analyze is for a track they brought: it reads the energy envelope (ffmpeg decodes to mono PCM), picks onsets as peaks
of its rise, takes the tempo by autocorrelation and lays a beat grid on the strongest phase. storyboard.py snap cuts the
film on the grid.

The sound effects are not the music's: film.py lays the shared layer's (sfx.py) under each film at render, from the
board, on this music's grid and in its key. The board's one cue, `stop`, is where the bed cuts and the closer's impact
rings out into silence. master brings the trimmed music to -14 LUFS by one gain, writes it as music/master.<id>.wav in
32-bit float (a peak past full scale kept whole: the film's mux limits the music and the effects together), and writes
the music's energy, one number a frame at the board's rate, to music/energy.json beside it ({"fps", "rms"}), where the
shared layer reads it.
"""
import argparse
import array
import math
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music_engine  # noqa: E402
import sfx  # noqa: E402

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = Path("music")
FX_UNDER_BED_LU = 8  # the effects' integrated loudness sits this far under the music's
TARGET_LUFS = -14.0


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
    # only the name a person places a track under, any file ffprobe finds audio in: a bed make wrote (source.TAG.wav)
    # is reached through music.json
    placed = sorted(p for p in MUSIC.glob("source.*") if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def brief():
    """The person's music brief from taste.json (`tempo`, `styles`, `avoid`)."""
    return (_env.read_json("taste.json") or {}).get("music") or {}


# ------------------------------------------------------------------ make
def card():
    """The chosen look's style id and its music recipe id (None and None before a look is chosen)."""
    style = (_env.read_json("winner.json") or {}).get("board")
    if not style:
        return None, None
    return style, (_env.read_json(_env.SKILL / "styles" / f"{style}.json") or {}).get("music") or style


def hue():
    """The palette's leading color's hue, degrees (None with no palette)."""
    year = (_env.read_json("palette.json") or {}).get("year") or []
    return music_engine.hue_of(year[0]["hex"]) if year else None


def reel_of(style):
    """The chosen look's reel board (None before a draft)."""
    return _env.read_json(f"storyboards/{style}/board-reel.json") if style else None


def edges(style, bpm):
    """The effects' impacts (sfx.py over the board), in seconds at the bed's tempo (the half, whole or double nearest the
    board's): where the film lands, so where the bed's sections turn."""
    from story import fx_board
    board = reel_of(style)
    if not (board and board.get("bpm")):
        return []
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    ev, _ = sfx.events(fx_board(board), board["bpm"])
    return [t * board["bpm"] / (bpm * k) for t, kind in ev if kind == "impact"]


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    from story import BPM
    style, recipe_id = card()
    if not style:
        sys.exit("no look chosen: show out/boards.png and run vote.py pick --board <style> first")
    plan = (_env.read_json(f"storyboards/{style}/plan.json") or {}).get("reel") or {}
    m = brief()
    target = m.get("tempo") or BPM
    # the snap fits the nine to the asked length at the music's tempo, so the bed runs past the cut, with four seconds
    # for the start the cut takes on a downbeat
    seconds = a.seconds or (plan.get("seconds") or (_env.read_json("taste.json") or {}).get("seconds") or 30) + 4
    seed = Path.cwd().name
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    bpm = music_engine.tempo(recipe, a.bpm, target, seed)
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(style, bpm), hue(),
                                seed, bpm=bpm, out=MUSIC)
    default = recipe_id if recipe_id in book["recipes"] else book["default"]
    chose = "their brief" if rid != default else "the look" if default == recipe_id else "the default"
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
    if info.get("recipe") and info.get("beats"):
        print(f"music: {info['file']} is a bed make composed; its own grid stands ({info['bpm']:g} bpm, {len(info['beats'])} beats)")
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


def integrated_file(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


# ------------------------------------------------------------------ master
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
    source = info["file"]
    reel = _env.read_json((film.get("boards") or {}).get("reel", "")) if (film.get("boards") or {}).get("reel") else None
    cues = (reel or {}).get("sound") or []
    # the board's stop: the music cuts there, the closer's impact rings out over the held picture, then the film is silent
    stop = next((c["at"] * 60 / reel["bpm"] for c in cues if c["kind"] == "stop"), None)
    if stop:
        # the music cut at the stop with a short fade, so the cut is clean before the master's own fade
        bed = MUSIC / "bed-cut.wav"
        subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS,"
                        f"afade=t=out:st={stop:.3f}:d=0.04,aformat=sample_rates=48000:channel_layouts=stereo", "-ar", "48000", "-c:a", "pcm_f32le",
                        str(bed)],
                       check=True)
        source, start = str(bed), 0.0
    # With a stop, the music's last ring fades out over the held picture and the rest is silence. Without one, the music
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
    # a name of this master's own: the film's mux reads the master music.json names, which stays the last one until
    # this one is written and measured
    out = MUSIC / f"master.{time.time_ns():x}.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(out)], check=True)
    # the music's energy, one number a frame, beside the master
    sfx.energy(ff, out, (reel or {}).get("fps") or 30, MUSIC / "energy.json")
    for k in ("sound_cues", "bed_lufs", "fx_lufs"):
        info.pop(k, None)
    info.update(master=str(out), master_seconds=round(seconds, 3), master_lufs=round(integrated_file(out), 2))
    _env.write_json("music.json", info)
    for f in MUSIC.glob("master.*"):
        if f != out:
            f.unlink()
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}, its energy a frame -> {MUSIC / 'energy.json'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--origin", help="find: where a track placed at music/source.<ext> came from, for brief.md")
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
