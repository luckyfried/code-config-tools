#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed for the winning look from their music brief; then its beat
grid, the board's sound cues under it, and the whole mastered to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/music.py find [--origin "..."] # music.json: a placed track, else a bed made for the winning look
    python3 S/scripts/music.py make [--bpm N] [--seconds S]
                                                    # a bed composed on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze              # a track they brought: onsets, bpm, beats and downbeats
    python3 S/scripts/music.py master [--seconds S] # the track from its first downbeat, the board's sound cues under it,
                                                    # -14 LUFS (true peak under -1.5 dBTP), stopping on the board's stop

A track the person chose or the agent fetched, saved as music/source.<ext> (any audio ffmpeg reads), is the music.
Otherwise `make` composes music/bed.wav with music_engine.py: the recipe is the winning look's (`music` in
styles/<id>.json), unless the brief's `styles` words (taste.json `music`) name another; its `avoid` words take out an
instrument, the drums or a groove; the key comes from the board's leading color, the tempo from the brief's or the
board's, the sections turn on the board's impacts, and the seed is the run's folder name. make writes the bed's own
beat grid into music.json, so analyze leaves it as it is; analyze is for a track they brought: librosa's beat tracker
when it is installed, otherwise the energy envelope (ffmpeg decodes to mono PCM), onsets as peaks of its rise, the
tempo by autocorrelation and the beat grid on the strongest phase, with the downbeat on the strongest of the four.
storyboard.py snap starts the film on a downbeat and cuts it on the beats.

The sound effects are the engine's too, played in the recipe's own instruments: music/fx/riser.wav (a build that cuts
off into the moment it leads to), hit.wav, bright.wav (the ring a `bright` hit adds) and impact.wav (the landing); a
track they brought gets its set rendered at master. The board's `sound` cues (film.json) place them where something
lands; `stop` is where the bed cuts on the beat and the hit on it ends before it rings, into silence. master writes
the trimmed bed (music/bed-cut.wav) and the effects (music/fx.wav) scaled so their integrated loudness sits
FX_UNDER_BED_LU under the bed's, sums them (music/mix.wav), records both numbers in music.json and the storyboard's
`Mixed:` line, and brings the whole to -14 LUFS.
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
                                seed, bpm=bpm, out=MUSIC)
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
RISER_GAIN = 0.6  # the build sits under the hits and the landing it leads to
# the effects stem's integrated loudness sits this far under the bed's; the gate's audio row holds a film to within 1 LU of it
FX_UNDER_BED_LU = 8


def effects(info, bpm):
    """The four effect files music.json names, or, for a track they brought, the winning look's set rendered now."""
    fx = info.get("fx") or {}
    if all(Path(fx.get(c) or "").is_file() for c in music_engine.CUES):
        return fx
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, card())
    h = hue()
    tonic = music_engine.tonic_of(h) if h is not None else music_engine.pick(music_engine.rng(Path.cwd().name, "key"), range(12))
    music_engine.place(music_engine.render_fx(book, recipe, tonic, bpm, MUSIC))
    info.update(fx={c: str(MUSIC / "fx" / f"{c}.wav") for c in music_engine.CUES}, fx_recipe=rid)
    return info["fx"]


def cue_legs(cues, bpm, fx):
    """Each cue as [(file, from, at, gain)]: the file from `from` seconds, placed at `at` in the film, `at` and `beats`
    read at `bpm`. A riser is the end of riser.wav, as long as the cue's beats, ending on the moment it leads to."""
    sec, legs = 60 / bpm, []
    for c in cues:
        at = c["at"] * sec
        if c["kind"] == "hit":
            legs.append((fx["hit"], 0.0, at, c.get("weight", 0.6)))
            if c.get("bright"):
                legs.append((fx["bright"], 0.0, at, c["bright"]))
        elif c["kind"] == "riser":
            want, have = c["beats"] * sec, duration(fx["riser"])
            use = min(want, have)
            legs.append((fx["riser"], have - use, at + want - use, RISER_GAIN))
        elif c["kind"] == "impact":
            legs.append((fx["impact"], 0.0, at, 1.0))
    return legs


def fx_stem(legs, seconds, scale, dst):
    """The legs summed over `seconds` of silence and scaled by `scale`, as a float stereo stem."""
    inputs = ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    graph = []
    for i, (f, f0, at, gain) in enumerate(legs, 1):
        inputs += ["-i", str(f)]
        graph.append(f"[{i}:a]atrim=start={f0:.4f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                     f"volume={gain:.4f},adelay={round(at * 1000)}:all=1[c{i}]")
    mixed = "[0:a]" + "".join(f"[c{i}]" for i in range(1, len(legs) + 1))
    graph.append(f"{mixed}amix=inputs={len(legs) + 1}:normalize=0:duration=first,volume={scale:.6f}[out]")
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", *inputs, "-filter_complex", ";".join(graph), "-map", "[out]",
                    "-ar", "48000", "-c:a", "pcm_f32le", str(dst)], check=True)


def integrated_file(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


# music.json's entries that describe music/master.wav and the stems under it
MASTERED = ("master", "master_seconds", "offset", "sound_cues", "stop", "master_lufs", "bed_lufs", "fx_lufs")


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
    cues = film.get("sound") or []
    # the board's stop: the bed cuts there on the beat, the hit on it ends before it rings, then the film is silent
    stop = next((c["at"] * 60 / bpm for c in cues if c["kind"] == "stop"), None)
    cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
    mix = bed = MUSIC / "bed-cut.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", info["file"], "-af",
                    f"atrim={offset:.3f}:{offset + seconds:.3f},asetpts=PTS-STARTPTS{cut},aformat=sample_rates=48000:channel_layouts=stereo",
                    "-ar", "48000", str(bed)], check=True)
    mixed = {}
    said = "no sound cues; the bed alone"
    if cues:
        # the effects stem under the bed, measured and scaled twice so its integrated loudness sits FX_UNDER_BED_LU
        # under the bed's (the meter's gates drop the quiet tails as the stem turns down); the two are summed as they are
        fxw = MUSIC / "fx.wav"
        legs = cue_legs(cues, bpm, effects(info, bpm))
        bed_lufs = integrated_file(bed)
        scale = 1.0
        for _ in range(2 if legs else 0):
            fx_stem(legs, seconds, scale, fxw)
            scale *= 10 ** ((bed_lufs - FX_UNDER_BED_LU - integrated_file(fxw)) / 20)
        fx_stem(legs, seconds, scale, fxw)
        mixed = {"bed_lufs": round(bed_lufs, 1), "fx_lufs": round(integrated_file(fxw), 1)}
        mix = MUSIC / "mix.wav"
        subprocess.run([ff, "-y", "-v", "error", "-i", str(bed), "-i", str(fxw), "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0:weights=1 1[out]", "-map", "[out]", "-ar", "48000", str(mix)], check=True)
        said = (f"bed {mixed['bed_lufs']} LUFS, effects {mixed['fx_lufs']} LUFS, {mixed['bed_lufs'] - mixed['fx_lufs']:.1f} LU under; "
                f"{len(cues)} sound cues over {len(film.get('beats') or [])} beats")
    # With a stop, the bed cuts on that beat and the hit that lands on it (the full stop) is cut 120 ms later, before
    # it rings: the held picture is silent. Without one, the music tails out over the film's last bar, so the closer
    # holds while the track lets go.
    bar = 240.0 / bpm
    st, d = (stop + 0.12, 0.05) if stop and stop + 0.17 <= seconds else (seconds - max(1.0, min(3.5, bar)), max(1.0, min(3.5, bar)))
    pre = f"afade=t=out:st={st:.3f}:d={d:.3f},"

    def integrated(chain):
        r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(mix), "-af", f"{chain}ebur128=framelog=quiet",
                            "-f", "null", "-"], capture_output=True, text=True)
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if not found:
            sys.exit(f"could not measure the loudness of {mix}")
        return float(found[-1])

    # Gain past the target, a fast peak limiter at about -2 dBFS, a trim onto -14 LUFS, then a last limiter at -2.2 dBFS
    # (sampled at 4x, so it holds the peaks between samples too) that leaves the AAC encode's overshoot under
    # -1.5 dBTP, so a track with sharp drum peaks (and the hits on top) reaches the target without clipping.
    gain = TARGET_LUFS - integrated(pre) + 1.5
    limited = f"{pre}volume={gain:.2f}dB,alimiter=limit=0.79:attack=1:release=60:level=false"
    trim = TARGET_LUFS - integrated(limited + ",")
    ceiling = "aresample=192000,alimiter=limit=0.78:attack=1:release=60:level=false,aresample=48000"
    for _ in range(2):
        trim += TARGET_LUFS - integrated(f"{limited},volume={trim:.2f}dB,{ceiling},")
    flt = f"{limited},volume={trim:.2f}dB,{ceiling},aformat=sample_rates=48000:channel_layouts=stereo"
    out = MUSIC / "master.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(mix), "-af", flt, "-ar", "48000", str(_env.part(out))], check=True)
    # film.py lays the master music.json names under the films: that entry goes before the new master replaces the
    # earlier one and comes back after it
    if [info.pop(k) for k in MASTERED if k in info]:
        _env.write_json("music.json", info)
    os.replace(_env.part(out), out)
    info.update({"master": str(out), "master_seconds": round(seconds, 3), "offset": offset, "sound_cues": len(cues),
                 "stop": round(stop, 3) if stop else None, "master_lufs": round(integrated_file(out), 2), **mixed})
    _env.write_json("music.json", info)
    restate()
    print(f"mastered {seconds:.1f} s from {offset:.2f} s into the track; {said}"
          + (f"; stopping at {stop:.2f} s" if stop else "") + f"; to {info['master_lufs']} LUFS -> {out}")
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
