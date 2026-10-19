#!/usr/bin/env python3
"""The film's music: find it, or make a bed, then read its beat grid and master it to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py find                 # build/music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--mood calm|drive|film] [--bpm N] [--seconds S]
                                                    # a bed made here (keys, bass, drums) when no music was found
    python3 S/scripts/music.py analyze              # onsets, tempo, beat grid and downbeats into build/music.json
    python3 S/scripts/music.py master --seconds S   # loudness to -14 LUFS (true peak -1.5 dB), trimmed and faded

The music comes from whatever the person or the agent has: a track the agent fetched or generated saved as
build/music/source.<ext> (any audio ffmpeg reads), else the longest audio file under the workspace that is
30 s or longer (their own library), else `make`, which writes a warm bed in the winning storyboard's tempo and
mood. brief.md names the origin either way. analyze reads the energy envelope (ffmpeg decodes to mono PCM),
picks onsets as peaks of its rise, takes the tempo by autocorrelation and lays a beat grid on the strongest
phase; storyboard.py snap cuts the film on that grid.
"""
import argparse
import array
import json
import math
import random
import re
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = Path("build/music")
SKIP = {"build", "out", ".claude", ".git", "node_modules", ".venv", ".cache"}


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
    placed = sorted(p for p in MUSIC.glob("source.*") if p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if placed and has_audio(placed[0]):
        origin = (_env.read_json("build/music.json") or {}).get("origin") or "placed by the agent in build/music/"
        info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    else:
        found = []
        for p in Path(".").rglob("*"):
            if any(part in SKIP for part in p.parts) or not p.is_file() or p.suffix.lower() not in AUDIO:
                continue
            d = duration(p)
            if d >= 30:
                found.append((d, p))
        if not found:
            print("no music in the workspace. Put a track at build/music/source.<ext> (one you have, or one your "
                  "music tool makes), or run: python3 " + str(_env.SKILL / "scripts" / "music.py") + " make")
            _env.write_json("build/music.json", {"file": None, "origin": None})
            return 3
        d, p = max(found)
        info = {"file": str(p), "origin": f"their own library: {p}", "seconds": round(d, 2)}
    _env.write_json("build/music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


# ------------------------------------------------------------------ make
MOODS = {
    "calm": {"bpm": 84, "chords": [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],
             "kick": [0, 2.5], "snare": [1, 3], "hat": 0.5, "stab": [0, 1.5, 2.5], "bright": 0.25},
    "drive": {"bpm": 118, "chords": [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 60], [55, 59, 62, 67]],
              "kick": [0, 1, 2, 3], "snare": [1, 3], "hat": 0.25, "stab": [0, 0.75, 1.5, 2.5, 3.25], "bright": 0.6},
    "film": {"bpm": 92, "chords": [[50, 57, 62, 65], [46, 53, 58, 62], [53, 57, 60, 65], [48, 55, 60, 64]],
             "kick": [0, 2], "snare": [], "hat": 0, "stab": [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5], "bright": 0.15},
}


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def synth(mood, bpm, sr=22050):
    """Eight bars (two passes of four chords) of keys, bass and drums, as mono floats."""
    m = MOODS[mood]
    beat = 60.0 / bpm
    bars = 8
    n = int(sr * beat * 4 * bars)
    out = [0.0] * n
    rnd = random.Random(7)

    def add(start, dur, fn, gain):
        i0 = int(start * sr)
        for i in range(max(0, i0), min(n, i0 + int(dur * sr))):
            out[i] += gain * fn((i - i0) / sr)

    for bar in range(bars):
        chord = m["chords"][bar % 4]
        t0 = bar * 4 * beat
        for k, at in enumerate(m["stab"]):
            notes = chord if mood != "film" else [chord[(k % 3) + 1]]
            for note in notes:
                f = midi_hz(note + (12 if mood == "film" else 0))
                dec = 2.6 if mood != "drive" else 5.0
                add(t0 + at * beat, beat * 1.6,
                    lambda t, f=f, dec=dec: math.exp(-dec * t) * (math.sin(2 * math.pi * f * t) + m["bright"] * math.sin(4 * math.pi * f * t))
                    * (1 + 0.15 * math.sin(2 * math.pi * 5 * t)), 0.09 / len(notes) * 4 / (1 + 0.3 * len(notes)))
        root = midi_hz(chord[0] - 12)
        for at in (0, 2.5) if mood != "drive" else (0, 0.5, 1.5, 2, 2.5, 3.5):
            add(t0 + at * beat, beat * 0.9, lambda t, f=root: math.exp(-3 * t) * math.sin(2 * math.pi * f * t) * min(1, t * 200), 0.22)
        for at in m["kick"]:
            add(t0 + at * beat, 0.35, lambda t: math.exp(-9 * t) * math.sin(2 * math.pi * (45 * t + 60 * (1 - math.exp(-30 * t)) / 30 * 2)), 0.55)
        for at in m["snare"]:
            add(t0 + at * beat, 0.25, lambda t: math.exp(-18 * t) * (rnd.uniform(-1, 1) * 0.8 + 0.3 * math.sin(2 * math.pi * 190 * t)), 0.18)
        if m["hat"]:
            k = 0.0
            while k < 4:
                if abs(k - round(k)) > 0.01 or mood == "drive":
                    add(t0 + k * beat, 0.05, lambda t: math.exp(-60 * t) * rnd.uniform(-1, 1), 0.05)
                k += m["hat"]
    peak = max(abs(x) for x in out) or 1
    return [x / peak * 0.8 for x in out], sr


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    win = _env.read_json("build/winner.json") or {}
    board = _env.read_json(f"build/storyboards/{win.get('board')}/storyboard.json") if win.get("board") else None
    bm = (board or {}).get("music", {})
    mood = a.mood or bm.get("mood") or "calm"
    bpm = a.bpm or bm.get("bpm") or MOODS[mood]["bpm"]
    seconds = a.seconds or ((board and sum(b["frames"] for b in board["beats"]) / 30) or 60) + 4
    samples, sr = synth(mood, bpm)
    loop = MUSIC / "loop.wav"
    with wave.open(str(loop), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(array.array("h", (int(x * 32767) for x in samples)).tobytes())
    src = MUSIC / "source.wav"
    flt = ("lowpass=f=7000,aecho=0.8:0.6:60|120:0.25|0.15,highpass=f=35,"
           "pan=stereo|c0=c0|c1=c0,aformat=sample_rates=48000,afade=t=in:d=0.6")
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-stream_loop", "-1", "-i", str(loop), "-t", f"{seconds:.2f}",
                    "-af", flt, str(src)], check=True)
    for f in MUSIC.glob("source.*"):
        if f != src:
            f.unlink()
    origin = f"made by music.py: a {mood} bed at {bpm} bpm (keys, bass, drums) because no music was found"
    _env.write_json("build/music.json", {"file": str(src), "origin": origin, "seconds": round(seconds, 2), "bpm": bpm})
    print(f"music: {src} ({seconds:.1f} s), {origin}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json("build/music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
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
    _env.write_json("build/music.json", info)
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
    info = _env.read_json("build/music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    seconds = a.seconds or (_env.read_json("build/film.json") or {}).get("seconds")
    if not seconds:
        sys.exit("pass --seconds (the film length)")
    ff = _env.ffmpeg()
    fade = min(2.0, seconds * 0.05)
    pre = f"atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={seconds - fade:.3f}:d={fade:.3f}"
    def integrated(chain):
        r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", info["file"], "-af", f"{chain},ebur128=framelog=quiet",
                            "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if not found:
            sys.exit(f"could not measure the loudness of {info['file']}")
        return float(found[-1])

    # Gain past the target, a fast peak limiter at about -2 dBFS, then a trim down onto -14 LUFS, so a track with
    # sharp drum peaks still reaches the target without clipping.
    gain = TARGET_LUFS - integrated(pre) + 1.5
    limited = f"{pre},volume={gain:.2f}dB,alimiter=limit=0.79:attack=1:release=60:level=false"
    trim = TARGET_LUFS - integrated(limited)
    flt = f"{limited},volume={trim:.2f}dB,aformat=sample_rates=48000:channel_layouts=stereo"
    out = MUSIC / "master.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", info["file"], "-af", flt, "-ar", "48000", str(out)], check=True)
    info["master"] = str(out)
    info["master_seconds"] = round(seconds, 3)
    _env.write_json("build/music.json", info)
    info["master_lufs"] = round(integrated_file(out), 2)
    _env.write_json("build/music.json", info)
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--mood", choices=list(MOODS))
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    a = ap.parse_args()
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
