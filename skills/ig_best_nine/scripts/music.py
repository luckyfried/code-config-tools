#!/usr/bin/env python3
"""The film's music: find it, or make a bed, then read its beat grid and master it to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py find --run R [--origin "..."]  # music.json: the track to use and where it came from
    python3 S/scripts/music.py make --run R [--bpm N] [--seconds S]
                                                             # a bed made here (keys, bass, drums) when no music was found
    python3 S/scripts/music.py analyze --run R               # onsets, tempo, beat grid and downbeats into music.json
    python3 S/scripts/music.py master --run R [--seconds S]  # from the first downbeat, the board's sound cues mixed over the bed ducked
                                                             # under its hits, -14 LUFS (true peak -1.5 dB), trimmed, the last bar faded

The music comes from whatever the person or the agent has: a track the agent fetched or generated saved as
music/source.<ext> in the run (any audio ffmpeg reads), else the longest audio file under the workspace that is
30 s or longer (their own library), else `make`, which writes a drive bed at the drive tempo.
brief.md names the origin either way. analyze reads the energy envelope (ffmpeg decodes to mono PCM),
picks onsets as peaks of its rise, takes the tempo by autocorrelation and lays a beat grid on the strongest
phase; storyboard.py snap cuts the film on that grid.

The sound design is synthesised here too, from the cut board's `sound` cues, each placed by the storyboard at a named
beat: `hit` (a body thump with a click, and a metallic ring for the blade), `whoosh` (a swept band of air, panned the
way the camera travels), `riser` (a build that cuts off into the moment it leads to), `ticks` (a tick-up under a
rolling count), `impact` (the landing), `stop` (where the bed cuts and the last hit rings out into silence) and `sidechain` (the key
that ducks the bed under every hit). master mixes
them over the ducked bed (music/fx.wav, music/key.wav, music/mix.wav) before it brings the whole to -14 LUFS.
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
MUSIC = Path("music")
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
        origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
        info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    else:
        found = []
        root = Path((_env.read_json("library.json") or {}).get("root") or _env.WORKSPACE)
        for p in root.rglob("*"):
            if any(part in SKIP for part in p.relative_to(root).parts) or not p.is_file() or p.suffix.lower() not in AUDIO:
                continue
            d = duration(p)
            if d >= 30:
                found.append((d, p))
        if not found:
            print(f"no music in the workspace. Put a track at {MUSIC.resolve()}/source.<ext> (one you have, or one your "
                  "music tool makes), or run: python3 " + str(_env.SKILL / "scripts" / "music.py") + " make")
            _env.write_json("music.json", {"file": None, "origin": None})
            return 3
        d, p = max(found)
        info = {"file": str(p), "origin": f"their own library: {p}", "seconds": round(d, 2)}
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


# ------------------------------------------------------------------ make
# the drive bed: four chords, kick on every beat, snare on two and four, sixteenth hats, the stabs in beats
BED = {"chords": [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 60], [55, 59, 62, 67]],
       "kick": [0, 1, 2, 3], "snare": [1, 3], "hat": 0.25, "stab": [0, 0.75, 1.5, 2.5, 3.25], "bright": 0.6}


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def synth(bpm, sr=22050):
    """Eight bars (two passes of four chords) of keys, bass and drums, as mono floats."""
    m = BED
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
        for at in m["stab"]:
            for note in chord:
                f = midi_hz(note)
                add(t0 + at * beat, beat * 1.6,
                    lambda t, f=f: math.exp(-5.0 * t) * (math.sin(2 * math.pi * f * t) + m["bright"] * math.sin(4 * math.pi * f * t))
                    * (1 + 0.15 * math.sin(2 * math.pi * 5 * t)), 0.09 / len(chord) * 4 / (1 + 0.3 * len(chord)))
        root = midi_hz(chord[0] - 12)
        for at in (0, 0.5, 1.5, 2, 2.5, 3.5):
            add(t0 + at * beat, beat * 0.9, lambda t, f=root: math.exp(-3 * t) * math.sin(2 * math.pi * f * t) * min(1, t * 200), 0.22)
        for at in m["kick"]:
            add(t0 + at * beat, 0.35, lambda t: math.exp(-9 * t) * math.sin(2 * math.pi * (45 * t + 60 * (1 - math.exp(-30 * t)) / 30 * 2)), 0.55)
        for at in m["snare"]:
            add(t0 + at * beat, 0.25, lambda t: math.exp(-18 * t) * (rnd.uniform(-1, 1) * 0.8 + 0.3 * math.sin(2 * math.pi * 190 * t)), 0.18)
        k = 0.0
        while k < 4:
            add(t0 + k * beat, 0.05, lambda t: math.exp(-60 * t) * rnd.uniform(-1, 1), 0.05)
            k += m["hat"]
    peak = max(abs(x) for x in out) or 1
    return [x / peak * 0.8 for x in out], sr


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    from tones.drive import BPM
    plan = (_env.read_json("storyboards/drive/plan.json") or {}).get("reel")
    bpm = a.bpm or BPM
    seconds = a.seconds or ((plan or {}).get("seconds") or 60) + 4
    samples, sr = synth(bpm)
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
    origin = f"made by music.py: a drive bed at {bpm} bpm (keys, bass, drums) because no music was found"
    _env.write_json("music.json", {"file": str(src), "origin": origin, "seconds": round(seconds, 2), "bpm": bpm})
    print(f"music: {src} ({seconds:.1f} s), {origin}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json("music.json") or {}
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
    _env.write_json("music.json", info)
    print(f"music: {round(bpm, 1)} bpm, {len(onsets)} onsets, {len(beats)} beats, {len(info['downbeats'])} downbeats over {total:.1f} s")
    return 0


# ------------------------------------------------------------------ sound design
# The storyboard places the film's sound at named beats (a board's `sound` cues); each cue is synthesised here, like
# the bed, and mixed under it. Nothing is laid automatically per move: a cue sounds only where the board puts one.
SR = 48000


class Stereo:
    """A stereo buffer of `seconds` that sounds are added into, each panned from -1 (left) to 1 (right)."""

    def __init__(self, seconds):
        self.n = int(seconds * SR) + 1
        self.L = array.array("f", bytes(4 * self.n))
        self.R = array.array("f", bytes(4 * self.n))

    def add(self, at, samples, pan=0.0, gain=1.0):
        i0 = int(at * SR)
        m = len(samples)
        for k in range(max(0, -i0), min(m, self.n - i0)):
            p = pan(k / m) if callable(pan) else pan
            a = (p + 1) * math.pi / 4
            v = samples[k] * gain
            self.L[i0 + k] += v * math.cos(a)
            self.R[i0 + k] += v * math.sin(a)

    def peak(self):
        return max(max(map(abs, self.L)), max(map(abs, self.R))) or 1.0

    def write(self, path, scale=1.0):
        pcm = array.array("h", bytes(4 * self.n))
        for i in range(self.n):
            pcm[2 * i] = max(-32767, min(32767, int(self.L[i] * scale * 32767)))
            pcm[2 * i + 1] = max(-32767, min(32767, int(self.R[i] * scale * 32767)))
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())


def _noise(seed):
    rnd = random.Random(seed)
    return lambda: rnd.uniform(-1, 1)


def _band(samples, centre, q):
    """`samples` through a state-variable band-pass whose centre (Hz) is `centre(u)` over the sound's progress u."""
    low = band = 0.0
    out = []
    m = len(samples)
    for k, x in enumerate(samples):
        f = 2 * math.sin(math.pi * min(0.45 * SR, centre(k / m)) / SR)
        high = x - low - band / q
        band += f * high
        low += f * band
        out.append(band)
    return out


def hit(weight=0.6, bright=0.0, seed=1):
    """A hit: a pitched-down body thump, a click on the attack and, when `bright`, a short metallic ring (the blade).
    `weight` 0 to 1 sets its depth and length."""
    n = int((0.35 + 0.6 * weight) * SR)
    noise = _noise(seed)
    out = []
    phase = 0.0
    hp = prev = 0.0
    for k in range(n):
        t = k / SR
        phase += 2 * math.pi * (42 + 120 * math.exp(-t * 32)) / SR
        body = math.sin(phase) * math.exp(-t * (9 - 4 * weight)) * min(1.0, t * 2000)
        x = noise()
        hp = 0.85 * (hp + x - prev)
        prev = x
        click = hp * math.exp(-t * 260)
        ring = sum(math.sin(2 * math.pi * 2300 * r * t) * math.exp(-t * (16 + 7 * r)) for r in (1.0, 1.51, 2.37, 3.13)) / 4 if bright else 0.0
        out.append(weight * body + 0.35 * click + 0.5 * bright * ring)
    return out


def whoosh(seconds, seed=2):
    """Air moving past the lens for `seconds`: noise through a band-pass that opens and closes as the move peaks just
    past its middle."""
    n = max(1, int(seconds * SR))
    noise = _noise(seed)
    raw = [noise() for _ in range(n)]
    swept = _band(raw, lambda u: 260 + 2600 * math.sin(math.pi * u ** 0.8) ** 1.6, 1.4)
    return [x * math.sin(math.pi * (k / n) ** 0.8) ** 2 * 1.6 for k, x in enumerate(swept)]


def riser(seconds, seed=3):
    """A build over `seconds` that cuts off at its end: noise opening upward and a rising tone two octaves high,
    swelling to the cut."""
    n = max(1, int(seconds * SR))
    noise = _noise(seed)
    air = _band([noise() for _ in range(n)], lambda u: 220 * (5200 / 220) ** u, 2.0)
    out = []
    phase = 0.0
    for k in range(n):
        u = k / n
        phase += 2 * math.pi * 110 * 4 ** (u ** 1.4) / SR
        tone = sum(math.sin(phase * h) / h for h in range(1, 7)) * 0.35
        swell = u ** 2.2 * min(1.0, (n - k) / (0.012 * SR))
        out.append(swell * (0.9 * air[k] + 0.55 * tone))
    return out


def ticks(seconds, count, seed=4):
    """A tick-up under a count rolling for `seconds`: `count` ticks, close together while the figures spin and spreading
    as the roll settles (the drum's ease, 1 - (1 - x) cubed)."""
    n = max(1, int(seconds * SR))
    out = [0.0] * n
    noise = _noise(seed)
    for j in range(1, count + 1):
        i0 = int((1 - (1 - j / (count + 1)) ** (1 / 3)) * n)
        f = 3000 + 260 * (j % 3)
        for k in range(int(0.02 * SR)):
            if i0 + k >= n:
                break
            t = k / SR
            out[i0 + k] += (math.sin(2 * math.pi * f * t) * math.exp(-t * 420) + 0.4 * noise() * math.exp(-t * 900)) * (0.6 + 0.4 * j / count)
    return out


def impact(seed=5):
    """The landing: a deep body falling in pitch with a long tail, a dark burst of noise, a faint high shimmer."""
    n = int(2.6 * SR)
    noise = _noise(seed)
    out = []
    phase = 0.0
    lp = 0.0
    shimmer = _band([noise() for _ in range(n)], lambda u: 3200, 3.0)
    for k in range(n):
        t = k / SR
        phase += 2 * math.pi * (31 + 70 * math.exp(-t * 9)) / SR
        lp += 0.06 * (noise() - lp)
        out.append(math.sin(phase) * math.exp(-t * 2.1) * min(1.0, t * 1500) + 1.4 * lp * math.exp(-t * 11) + 0.25 * shimmer[k] * math.exp(-t * 2.8))
    return out


def sidechain(cues, seconds, sec):
    """The key that ducks the bed: a short full-scale pulse at every hit of weight 0.5 or more and at the impact, for
    ffmpeg's sidechaincompress to pull the bed down under the kick and let it back over about a fifth of a second."""
    key = Stereo(seconds)
    pulse = [math.sin(2 * math.pi * 60 * k / SR) for k in range(int(0.06 * SR))]
    for c in cues:
        if c["kind"] == "impact" or (c["kind"] == "hit" and c.get("weight", 0) >= 0.5):
            key.add(c["at"] * sec, pulse)
    return key, "sidechaincompress=threshold=0.08:ratio=6:attack=3:release=220:makeup=1"


def score(cues, seconds, bpm):
    """The board's cues synthesised into one stereo buffer, `at` and `beats` read at `bpm`."""
    sec = 60 / bpm
    fx = Stereo(seconds)
    for i, c in enumerate(cues):
        at = c["at"] * sec
        if c["kind"] == "hit":
            fx.add(at, hit(c.get("weight", 0.6), c.get("bright", 0.0), seed=i), gain=0.9)
        elif c["kind"] == "whoosh":
            p0, p1 = c.get("pan", [0, 0])
            fx.add(at, whoosh(c["beats"] * sec, seed=i), pan=lambda u, p0=p0, p1=p1: p0 + (p1 - p0) * u, gain=0.45)
        elif c["kind"] == "riser":
            fx.add(at, riser(c["beats"] * sec, seed=i), gain=0.5)
        elif c["kind"] == "ticks":
            fx.add(at, ticks(c["beats"] * sec, c.get("n", 8), seed=i), gain=0.35)
        elif c["kind"] == "impact":
            fx.add(at, impact(seed=i), gain=1.0)
    return fx


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
    start = float(film.get("music_start") or 0)
    ff = _env.ffmpeg()
    source = info["file"]
    reel = _env.read_json((film.get("boards") or {}).get("reel", "")) if (film.get("boards") or {}).get("reel") else None
    cues = (reel or {}).get("sound") or []
    # the board's stop: the bed cuts there, the last hit rings out over the held picture, then the film is silent
    stop = next((c["at"] * 60 / reel["bpm"] for c in cues if c["kind"] == "stop"), None)
    if cues:
        # the board's sound cues over the bed, the bed ducked under the hits by the sidechain key
        fx = score(cues, seconds, reel["bpm"])
        key, duck = sidechain(cues, seconds, 60 / reel["bpm"])
        fx.write(MUSIC / "fx.wav", 0.9 / fx.peak())
        key.write(MUSIC / "key.wav")
        mix = MUSIC / "mix.wav"
        cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
        graph = (f"[0:a]atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS{cut},aformat=sample_rates=48000:channel_layouts=stereo[bed];"
                 f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo[key];[bed][key]{duck}[duck];"
                 f"[duck][1:a]amix=inputs=2:normalize=0:weights=1 0.8[out]")
        subprocess.run([ff, "-y", "-v", "error", "-i", source, "-i", str(MUSIC / "fx.wav"), "-i", str(MUSIC / "key.wav"),
                        "-filter_complex", graph, "-map", "[out]", "-ar", "48000", str(mix)], check=True)
        source, start = str(mix), 0.0
    # With a stop, the last hit's ring fades out over the held picture and the rest is silence. Without one, the music
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

    # Gain past the target, a fast peak limiter at about -2 dBFS, then a trim down onto -14 LUFS, so a track with
    # sharp drum peaks still reaches the target without clipping.
    gain = TARGET_LUFS - integrated(pre) + 1.5
    limited = f"{pre},volume={gain:.2f}dB,alimiter=limit=0.79:attack=1:release=60:level=false"
    trim = TARGET_LUFS - integrated(limited)
    flt = f"{limited},volume={trim:.2f}dB,aformat=sample_rates=48000:channel_layouts=stereo"
    out = MUSIC / "master.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", str(out)], check=True)
    info["master"] = str(out)
    info["master_seconds"] = round(seconds, 3)
    info["sound_cues"] = len(cues)
    _env.write_json("music.json", info)
    info["master_lufs"] = round(integrated_file(out), 2)
    _env.write_json("music.json", info)
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS" + (f" with {len(cues)} sound cues over the ducked bed" if cues else "") + f" -> {out}")
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
