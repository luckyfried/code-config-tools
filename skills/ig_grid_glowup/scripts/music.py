#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed for the picked board's style, with its beat grid, mastered
to -14 LUFS and cut on the board's stop.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py find [--origin "..."] # music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--seconds S]    # a bed composed on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze              # a track they brought: onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master [--seconds S] # from the first downbeat, on the board's tempo, -14 LUFS by one
                                                    # gain, in float, cut on the board's stop; music/energy.json beside it

find takes a track placed at music/source.<ext> (any audio ffmpeg reads: the one the person gave you or asked for),
else `make`. make composes music/bed.wav with music_engine.py: the recipe is the picked board's style card's, unless
the brief's `styles` words (taste.json `music`) name another; its `avoid` words take out an instrument, the drums or a
groove; the key comes from the palette's leading color, the tempo is the board's (the tempo its cut is timed on), the
sections turn where the film's beats start, and the seed is the run's folder name, so a rerun of one run makes the
same bed. make writes the bed's own beat grid into music.json, and analyze leaves it as it is; analyze is for a track
they brought: it reads the energy envelope (ffmpeg decodes to mono PCM), picks onsets as peaks of its rise, takes the
tempo by autocorrelation and lays a beat grid on the strongest phase. master starts a brought track at its first
downbeat and stretches it onto the board's tempo (by at most a fifth either way; a track further off plays at its own
tempo, and the cuts do not follow it).

The sound effects are the shared layer's (sfx.py), laid by film.py render from the board's `fx` over this master, on
its grid and in its key, so master mixes none. master cuts the bed on the board's stop (the picture holds in silence
after it), brings it to -14 LUFS by one gain as music/master.<key>.wav, named by its content and written in 32-bit
float so a peak past full scale is kept whole (the film's mux, sfx.py, limits music and effects together, once),
writes music/energy.json beside it (the master's root mean square, one number a frame, where the shared layer reads
it), and lays the reel board's effects alone (music/fx.wav) to measure them: both loudness numbers go into music.json
and the storyboard's `Mixed:` line, the effects FX_UNDER_BED_LU or more under the master.
"""
import argparse
import array
import hashlib
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music_engine  # noqa: E402
import sfx  # noqa: E402

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = Path("music")
# the effects sit at least this many LU of integrated loudness under the master they play over
FX_UNDER_BED_LU = 8


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
    # only the name a person places, music/source.<ext>: a source.<key>.<ext> make wrote is reached through music.json
    placed = sorted(p for p in MUSIC.glob("source.*") if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


# ------------------------------------------------------------------ make
def keyed(tmp, stem):
    """The whole file `tmp` moved onto music/<stem>.<digest of its bytes><its suffix>: a name of its own, so music.json
    names the old file, whole, until it names this one."""
    dst = MUSIC / f"{stem}.{hashlib.sha256(Path(tmp).read_bytes()).hexdigest()[:12]}{Path(tmp).suffix}"
    os.replace(tmp, dst)
    return dst


def brief():
    """The person's music brief from taste.json (`mood`, `tempo`, `styles`, `avoid`)."""
    return (_env.read_json("taste.json") or {}).get("music") or {}


def hue():
    """The palette's leading color's hue, degrees (None with no palette)."""
    year = (_env.read_json("palette.json") or {}).get("year") or []
    return music_engine.hue_of(year[0]["hex"]) if year else None


def picked():
    board = _env.read_json("board.json")
    if not board:
        sys.exit("no board picked: run storyboard.py pick first")
    return board


def edges(board):
    """Where the reel's beats start, seconds: where the film turns, so where the bed's sections turn."""
    reel = board["boards"]["reel"]
    starts, at = [], 0
    for b in reel["beats"][:-1]:
        at += b["frames"]
        starts.append(at / reel["format"]["fps"])
    return starts


def peak(board):
    """The story's peak in seconds: where the peak post's photograph lands (its beat's start, plus its trailer move's
    hand back when it takes one) and where its beat ends; None when the board marks no peak. The timeline is in beats
    of the board's tempo, the hand back in seconds."""
    for bt in (board["boards"]["reel"].get("timeline") or {}).get("beats") or []:
        if bt.get("peak"):
            s = 60 / board["tempo"]
            return bt["at"] * s + (bt.get("hand") or 0), bt["end"] * s
    return None


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    board = picked()
    m = brief()
    seconds = a.seconds or board["seconds"] + 2
    seed = Path.cwd().name
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, board["style"], m.get("styles") or [], m.get("avoid") or [])
    info = music_engine.compose(board["style"], m.get("styles") or [], m.get("avoid") or [], seconds, edges(board), hue(),
                                seed, bpm=board["tempo"], out=MUSIC, peak=peak(board))
    chose = "their brief" if rid != board["style"] else "the board's style"
    origin = (f"made by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json("music.json", dict(info, file=str(MUSIC / "bed.wav"), origin=origin, made=True))
    print(f"music: {MUSIC / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json("music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    if info.get("made"):
        print(f"music: a bed made at {info['bpm']:g} bpm carries its own grid ({len(info['beats'])} beats)")
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
    board = picked()
    seconds = a.seconds or board["seconds"]
    ff = _env.ffmpeg()
    reel = board["boards"]["reel"]
    tempo_ = board["tempo"]
    ratio = tempo_ / info["bpm"] if info.get("bpm") and info.get("downbeats") else 1.0
    fit = 0.8 <= ratio <= 1.25
    start = info["downbeats"][0] if info.get("downbeats") and fit else 0.0
    stretch = f"atempo={ratio:.4f}," if fit and abs(ratio - 1) > 0.005 else ""
    # on the film's tempo: a bed made at it, or a found track analyzed and stretched onto it
    info["on_cut_tempo"] = bool(info.get("bpm") and (abs(info["bpm"] - tempo_) < 0.5 or (fit and info.get("downbeats"))))
    source = info["file"]
    bed = f"atrim=start={start:.3f},asetpts=PTS-STARTPTS,{stretch}atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS"
    # the board's stop: the bed cuts there and the picture holds in silence after it
    stop = reel.get("stop_seconds")
    stop = stop if stop and stop < seconds else None
    if stop:
        bed += f",afade=t=out:st={stop:.3f}:d=0.04"
    # Without a stop, the music tails out over the film's last two seconds.
    pre = bed if stop else f"{bed},afade=t=out:st={seconds - min(2.0, seconds * 0.05):.3f}:d={min(2.0, seconds * 0.05):.3f}"

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
    tmp = _env.part(MUSIC / "master.wav")
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(tmp)], check=True)
    out = keyed(tmp, "master")
    # the music's energy, one number a frame, beside the master
    sfx.energy(ff, out, (reel.get("format") or {}).get("fps") or 30, MUSIC / "energy.json")
    master_lufs = round(integrated_file(out), 2)
    # the reel's effects alone, as film.py render lays them over this master, measured against it
    fx = reel.get("fx") or {"beats": []}
    record = dict(info, bpm=tempo_) if info["on_cut_tempo"] else info
    fx_wav = MUSIC / "fx.wav"
    sfx.write(fx_wav, sfx.lay(fx, seconds, record)[0])
    effects = len(sfx.events(fx, sfx.music_of(fx, record)[0])[0])
    mixed = {"bed_lufs": master_lufs, "fx_lufs": round(integrated_file(fx_wav), 2)}
    said = (f"music {mixed['bed_lufs']} LUFS, effects {mixed['fx_lufs']} LUFS, {mixed['bed_lufs'] - mixed['fx_lufs']:.1f} LU under; "
            f"{effects} effects over {len(reel.get('beats') or [])} beats")
    for k in ("sound_cues", "fx", "fx_recipe"):
        info.pop(k, None)
    info.update(master=str(out), master_seconds=round(seconds, 3), effects=effects, master_lufs=master_lufs, **mixed)
    _env.write_json("music.json", info)
    md = Path("storyboard.md")
    if md.exists():
        text = re.sub(r"(?m)^Music: .*$", lambda _: f"Music: {info['origin']}.", md.read_text())
        _env.write_text(md, re.sub(r"(?m)^Mixed: .*$", lambda _: f"Mixed: {said}.", text))
    # film.py render lays the master music.json names: the other masters go once it names this one
    for f in MUSIC.glob("master.*"):
        if f != out:
            f.unlink()
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
    print(f"mixed: {said}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--origin", help="find: where a track placed at music/source.<ext> came from, for brief.md")
    a = ap.parse_args()
    _env.enter_run()
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
