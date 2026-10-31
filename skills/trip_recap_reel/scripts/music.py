#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed for the winning look from their music brief; then its beat
grid, and the whole mastered to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/music.py find [--origin "..."] # music.json: a placed track, else a bed made for the winning look
    python3 S/scripts/music.py make [--bpm N] [--seconds S]
                                                    # a bed composed on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze              # a track they brought: onsets, bpm, beats and downbeats
    python3 S/scripts/music.py master [--seconds S] # the track from its first downbeat, -14 LUFS by one gain, in
                                                    # float, stopping on the board's stop; music/energy.json

A track the person chose or the agent fetched, saved as music/source.<ext> (any audio ffmpeg reads), is the music.
Otherwise `make` composes music/bed.wav with music_engine.py: the recipe is the winning look's (`music` in
styles/<id>.json), unless the brief's `styles` words (taste.json `music`) name another; its `avoid` words take out an
instrument, the drums or a groove; the key comes from the board's leading color, the tempo from the brief's or the
board's, the sections turn on the board's impacts, and the seed is the run's folder name. make writes the bed's own
beat grid into music.json, so analyze leaves it as it is; analyze is for a track they brought: librosa's beat tracker
when it is installed, otherwise the energy envelope (ffmpeg decodes to mono PCM), onsets as peaks of its rise, the
tempo by autocorrelation and the beat grid on the strongest phase, with the downbeat on the strongest of the four.
storyboard.py snap starts the film on a downbeat and cuts it on the beats.

The sound effects are the shared layer's (sfx.py), made from the board and laid under the picture as film.py renders:
a whoosh on every cut, a shutter as every photograph lands, an impact as the trip's name lands and as the closer opens,
a riser into it, all on the music's grid and in its key (music.json `bpm` and `key`). master writes the music alone:
music/master.wav, the track from the film's first downbeat for the film's length, cut on the board's `stop` (film.json
`sound`), where the held picture goes silent, brought to -14 LUFS by one gain and written in 32-bit float, so a peak
past full scale is kept whole for the film's mux (sfx.py), which limits music and effects together, once; and
music/energy.json, the master's energy, one root mean
square (0..1) a frame.
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
import sfx  # noqa: E402

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


def restate():
    """The winning board's storyboard.md written again from the cut (film.json, at the music's tempo and the film's
    length) or, before the cut, from the board, so its Music: and Mixed: lines state music.json."""
    win = _env.read_json("winner.json") or {}
    md = Path(f"storyboards/{win.get('board')}/storyboard.md")
    board = _env.read_json("film.json") or _env.read_json(f"storyboards/{win.get('board')}/storyboard.json")
    if md.exists() and board:
        import storyboard
        storyboard.write_md(board, md)


def publish(info):
    """music.json names the track and where it came from; the winning storyboard carries the origin on its `Music:` line."""
    _env.write_json("music.json", info)
    restate()
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")


def cmd_find(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    placed = sorted(p for p in MUSIC.glob("source.*") if p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
    publish({"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)})
    return 0


def brief():
    """The person's music brief, taste.json `music` (mood, tempo, styles, avoid); empty before research writes one."""
    return (_env.read_json("taste.json") or {}).get("music") or {}


def winner():
    """The winning board (storyboards/<n>/storyboard.json), or None before the pick."""
    won = (_env.read_json("winner.json") or {}).get("board")
    return _env.read_json(f"storyboards/{won}/storyboard.json") if won else None


def film_seconds(bpm):
    """The film's length at `bpm` from the board that won the vote (four beats a bar); a minute before there is one."""
    bars = sum(b.get("bars") or 0 for b in (winner() or {}).get("beats", []))
    return bars * 240.0 / bpm if bars else 60.0


def card():
    """The winning look's music recipe id (None before the pick)."""
    look = (winner() or {}).get("style")
    return (_env.read_json(_env.SKILL / "styles" / f"{look}.json") or {}).get("music") if look else None


def hue():
    """The hue of the board's leading color, degrees (None with no board)."""
    colors = ((winner() or {}).get("system") or {}).get("colors") or {}
    lead = (colors.get("swatches") or [{}])[0].get("hex") or colors.get("accent")
    return music_engine.hue_of(lead) if lead else None


def edges(bpm):
    """The board's impacts, in seconds at the bed's tempo: where the film lands, so where the bed's sections turn."""
    board = winner() or {}
    if not board.get("bpm"):
        return []
    return [q["at"] * 60 / bpm for q in board.get("sound") or [] if q["kind"] == "impact"]


def peak(bpm):
    """The story's peak in seconds at the bed's tempo: where the peak stop's photograph lands (its start, after the move
    that flies it in) and where the stop ends; None with no board or no peak."""
    at = 0.0
    for b in (winner() or {}).get("beats", []):
        n = 4 * (b.get("bars") or 0)
        if b.get("peak"):
            return at * 60 / bpm + (b.get("fly") or 0.0), (at + n) * 60 / bpm
        at += n
    return None


# ------------------------------------------------------------------ make
def cmd_make(a):
    """A bed composed for the winning look: its recipe, or the one the brief's words name, at the brief's tempo or the
    board's."""
    MUSIC.mkdir(parents=True, exist_ok=True)
    m = brief()
    recipe_id = card()
    target = m.get("tempo") or (winner() or {}).get("bpm")
    seed = Path.cwd().name
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    bpm = music_engine.tempo(recipe, a.bpm, target, seed)
    seconds = a.seconds or film_seconds(bpm) + 4
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(bpm), hue(),
                                seed, bpm=bpm, out=MUSIC, peak=peak(bpm))
    default = recipe_id if recipe_id in book["recipes"] else book["default"]
    chose = "their brief" if rid != default else "the look" if default == recipe_id else "the default"
    origin = (f"made by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    publish(dict(info, file=str(MUSIC / "bed.wav"), origin=origin))
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
FPS = 30


def integrated_file(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


# music.json's entries that describe music/master.wav
MASTERED = ("master", "master_seconds", "offset", "stop", "master_lufs")


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
    # the board's stop: the music cuts there on the beat, then the picture holds silent
    stop = next((c["at"] * 60 / bpm for c in film.get("sound") or [] if c["kind"] == "stop"), None)
    bed = MUSIC / "bed-cut.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", info["file"], "-af",
                    f"atrim={offset:.3f}:{offset + seconds:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo",
                    "-ar", "48000", "-c:a", "pcm_f32le", str(bed)], check=True)
    # With a stop, the music fades out over 40 ms on that beat and the held picture is silent. Without one, the music
    # tails out over the film's last bar, so the closer holds while the track lets go.
    bar = 240.0 / bpm
    st, d = (stop, 0.04) if stop and stop + 0.04 <= seconds else (seconds - max(1.0, min(3.5, bar)), max(1.0, min(3.5, bar)))
    pre = f"afade=t=out:st={st:.3f}:d={d:.3f},"

    def integrated(chain):
        r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(bed), "-af", f"{chain}ebur128=framelog=quiet",
                            "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if not found:
            sys.exit(f"could not measure the loudness of {bed}")
        return float(found[-1])

    # One gain onto -14 LUFS and nothing else: the master is written in 32-bit float, so a peak over full scale is kept
    # whole, and the film's mux (sfx.py) limits music and effects together, once.
    gain = TARGET_LUFS - integrated(pre)
    flt = f"{pre}volume={gain:.2f}dB,aformat=sample_rates=48000:channel_layouts=stereo"
    out = MUSIC / "master.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(bed), "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(_env.part(out))],
                   check=True)
    # film.py lays the master music.json names under the films: that entry goes before the new master replaces the
    # earlier one and comes back after it
    if [info.pop(k) for k in MASTERED if k in info]:
        _env.write_json("music.json", info)
    os.replace(_env.part(out), out)
    # the music's energy, one number a frame, beside the master, where the shared layer reads it
    sfx.energy(ff, out, (film.get("format") or {}).get("fps") or FPS, MUSIC / "energy.json")
    info.update({"master": str(out), "master_seconds": round(seconds, 3), "offset": offset,
                 "stop": round(stop, 3) if stop else None, "master_lufs": round(integrated_file(out), 2)})
    _env.write_json("music.json", info)
    restate()
    print(f"mastered {seconds:.1f} s from {offset:.2f} s into the track" + (f"; stopping at {stop:.2f} s" if stop else "")
          + f"; to {info['master_lufs']} LUFS -> {out}; the effects are laid under it as the film renders (sfx.py)")
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
