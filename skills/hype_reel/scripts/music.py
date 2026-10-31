#!/usr/bin/env python3
"""The film's music: the track they placed, else a bed composed here on real instruments from the chosen board's style
and their music brief; its beat grid; and its master, the music alone, to -14 LUFS.

USAGE (in a run; S = this skill's folder):
    python3 S/scripts/music.py find [--origin "..."] # music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--seconds S]    # a bed composed by music_engine.py at the chosen board's tempo
    python3 S/scripts/music.py analyze              # a track they brought: onsets, bpm, beats and downbeats
    python3 S/scripts/music.py master [--seconds S] # from the first beat, -14 LUFS by one gain, in float, the
                                                    # picture and the music stopping together

music.json names the run's music: the track (`file`), its grid and its master (`master`). make composes into a folder
of its own name and master writes a master of its own name; each publishes music.json naming its files, then removes
the ones it named before.

find takes a track the person chose, placed as music/source.<ext> (any audio ffmpeg reads); else it runs make. make
composes with music_engine.py: the recipe is the chosen board's style card's (`music`), unless the words of their music
brief (taste.json `music.styles`) name another, and its `avoid` words take out an instrument, the drums or a groove;
the tempo is the board's, the key comes from the board's accent color, the sections turn on the board's impacts, and
the seed is the run's folder name, so a second make of the same board is the same bed. make writes the bed's own grid
(bpm, beats, downbeats, sections, key) into music.json, so analyze leaves it as it is; analyze is for a track they
brought: librosa's beat tracker when it is installed, otherwise the energy envelope (ffmpeg decodes to mono PCM),
onsets as peaks of its rise, the tempo by autocorrelation and the beat grid on the strongest phase, with the downbeat on
the strongest of the four. storyboard.py snap cuts the film on the beats.

The sound effects are the shared layer's (sfx.py), made from the film's beats and laid under the picture as film.py
renders: a whoosh on each cut, a shutter as each photograph lands, an impact on each slammed word and on the closer, a
riser into it, all on the music's grid and in its key. master writes the music alone: the track from the film's first
beat for the film's length (music/mix.wav), cut on the board's `stop` (film.json `sound`), where the held picture goes
silent, or else tailing out over the last bar, brought to -14 LUFS by one gain and written in 32-bit float so a peak
past full scale is kept whole: the film's mux (sfx.py) masters the music and the effects together, once. music.json
carries the music's loudness before (`bed_lufs`) and after (`master_lufs`).
"""
import argparse
import array
import math
import os
import re
import shutil
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
    placed = sorted(p for p in MUSIC.glob("source.*") if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def brief():
    """Their music brief from taste.json: `styles` (words that choose the sound) and `avoid` (words that take it out)."""
    m = (_env.read_json("taste.json") or {}).get("music") or {}
    return m if isinstance(m, dict) else {}


def board():
    """The chosen board (winner.json carries it)."""
    b = (_env.read_json("winner.json") or {}).get("storyboard")
    if not b:
        sys.exit("no board chosen: run vote.py tally (or vote.py pick N) first")
    return b


def hue(b):
    accent = ((b.get("system") or {}).get("colors") or {}).get("accent")
    return music_engine.hue_of(accent) if accent else None


def peak(b):
    """The story's peak in seconds: where the board's peak beat starts (its photograph lands there) and where it ends;
    None when the board marks no peak."""
    bpm = float(b["bpm"])
    for x in b.get("beats") or []:
        if x.get("peak"):
            return x["start"] * 60.0 / bpm, (x["start"] + x["len"]) * 60.0 / bpm
    return None


# ------------------------------------------------------------------ make
def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    b = board()
    m = brief()
    recipe_id = (b.get("music") or {}).get("recipe") or b.get("style")
    bpm = float(b["bpm"])
    beats = sum(x.get("len") or 0 for x in b["beats"])
    seconds = a.seconds or beats * 60.0 / bpm + 4
    edges = [c["at"] * 60.0 / bpm for c in b.get("sound") or [] if c["kind"] == "impact"]
    book = music_engine.recipes()
    rid, _, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    out = MUSIC / f"made-{os.urandom(4).hex()}"
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges, hue(b),
                                Path.cwd().name, bpm=bpm, out=out, peak=peak(b))
    chose = "their brief" if rid != recipe_id else "the board's style"
    origin = (f"composed by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in "
              f"{info['key']} at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json("music.json", dict(info, file=str(out / "bed.wav"), origin=origin, board=b.get("id")))
    # the folders an older make wrote go once music.json names this one; a placed source.<ext> stays
    for f in MUSIC.glob("made-*"):
        if f != out:
            shutil.rmtree(f, ignore_errors=True)
    for f in MUSIC.glob("master*"):
        f.unlink()
    print(f"music: {out / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ analyze
def analyze_librosa(info):
    """The beat grid from librosa's tracker, with the downbeat on the strongest of the four beats of a bar."""
    import librosa
    y, sr = librosa.load(info["file"], sr=22050, mono=True)
    env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, frames = librosa.beat.beat_track(onset_envelope=env, sr=sr, units="frames")
    beats = [round(float(t), 3) for t in librosa.frames_to_time(frames, sr=sr)]
    onsets = [round(float(t), 3) for t in librosa.onset.onset_detect(onset_envelope=env, sr=sr, units="time")]
    strength = [sum(float(env[f]) for f in frames[o::4]) for o in range(4)]
    o = strength.index(max(strength))
    bpm = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    info.update({"bpm": round(bpm, 2), "onsets": onsets, "beats": beats, "downbeats": beats[o::4],
                 "analyzed_seconds": round(len(y) / sr, 2), "tracker": "librosa"})
    return info


def cmd_analyze(a):
    info = _env.read_json("music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    if info.get("recipe"):
        print(f"music: {info['file']} was composed here, and its grid is its own: {info['bpm']:g} bpm, "
              f"{len(info['downbeats'])} downbeats")
        return 0
    try:
        import librosa  # noqa: F401
    except ImportError:
        librosa = None
    if librosa is not None:
        info = analyze_librosa(info)
        _env.write_json("music.json", info)
        print(f"music: {info['bpm']} bpm (librosa), {len(info['onsets'])} onsets, {len(info['beats'])} beats, "
              f"{len(info['downbeats'])} downbeats over {info['analyzed_seconds']:.1f} s")
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
                 "downbeats": beats[o::4], "analyzed_seconds": round(total, 2), "tracker": "autocorrelation"})
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
    ff = _env.ffmpeg()
    offset = float(film.get("music_offset") or 0)
    bpm = float(film.get("bpm") or info.get("bpm") or 100)
    bar = 240.0 / bpm
    fade = max(1.0, min(3.5, bar))
    mix = MUSIC / "mix.wav"
    cues = film.get("sound") or []
    # the board's stop: the music cuts there on the beat and the held picture after it is silent; without one, the
    # music tails out over the film's last bar
    stop = next((c["at"] * 60 / bpm for c in cues if c["kind"] == "stop"), None)
    cut = f"afade=t=out:st={stop:.3f}:d=0.04" if stop else f"afade=t=out:st={seconds - fade:.3f}:d={fade:.3f}"
    subprocess.run([ff, "-y", "-v", "error", "-i", info["file"], "-af", f"atrim={offset:.3f}:{offset + seconds:.3f},asetpts=PTS-STARTPTS,"
                    f"aformat=sample_rates=48000:channel_layouts=stereo,{cut}", "-ar", "48000", "-c:a", "pcm_f32le", str(mix)],
                   check=True)

    def integrated(chain):
        r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(mix), "-af", f"{chain}ebur128=framelog=quiet",
                            "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if not found:
            sys.exit(f"could not measure the loudness of {mix}")
        return float(found[-1])

    # One gain onto -14 LUFS and nothing else: the master is written in 32-bit float, so a peak over full scale is kept
    # whole, and the film's mux (sfx.py) limits everything under the picture together, once.
    bed_lufs = integrated("")
    gain = TARGET_LUFS - bed_lufs
    flt = f"volume={gain:.2f}dB,aformat=sample_rates=48000:channel_layouts=stereo"
    # a master of its own name, then music.json naming it, then the old masters go
    out = MUSIC / f"master-{os.urandom(4).hex()}.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(mix), "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(out)], check=True)
    for k in ("fx_lufs", "sound_cues", "fx", "fx_recipe"):
        info.pop(k, None)
    info.update({"master": str(out), "master_seconds": round(seconds, 3), "offset": offset, "stop": round(stop, 3) if stop else None,
                 "bed_lufs": round(bed_lufs, 2), "master_lufs": round(integrated_file(out), 2)})
    _env.write_json("music.json", info)
    for f in MUSIC.glob("master*"):
        if f != out:
            f.unlink()
    print(f"mastered {seconds:.1f} s from {offset:.2f} s into the track, the music alone"
          + (f", the picture and the music stopping at {stop:.2f} s" if stop else f", the last {fade:.1f} s tailing out")
          + f", to {info['master_lufs']} LUFS -> {out}; the effects are laid under it as the film renders (sfx.py)")
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
