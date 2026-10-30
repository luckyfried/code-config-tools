#!/usr/bin/env python3
"""The film's music: find the track they placed or make a bed with the music engine, then read its beat grid and
master it to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder, B = the run's folder, build/<run stamp>/):
    python3 S/scripts/music.py find [--origin "..."] # B/music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--board N] [--bpm N] [--seconds S]
                                                    # a bed made by the music engine from the chosen board's style
                                                    # recipe and the person's music brief, as long as the board runs
    python3 S/scripts/music.py analyze              # onsets, tempo, beat grid and downbeats into B/music.json (a made
                                                    # bed carries its own and is not read again)
    python3 S/scripts/music.py master [--seconds S] # the film's sound cues mixed under the bed, -14 LUFS (true peak
                                                    # -1.5 dB), trimmed to the film (B/film.json's length unless
                                                    # --seconds), cut at the board's stop

find takes a track the person placed as B/music/source.<ext> (any audio ffmpeg reads), the track they chose; else
`make` asks the music engine (scripts/music_engine.py, music/recipes.json) for a bed: the recipe is the chosen
board's style card's (`music`), turned by the person's music brief (B/taste.json `music`: its `styles` words can name
another recipe, its `avoid` words take instruments out), in the key of the colors the two share, at the tempo of the
recipe's range nearest the board's own, its sections turning on the board's impacts, the seed the run's folder name.
music.json carries what the engine made (recipe, key, tempo, beats, downbeats, chords, the effect files) and its
origin in one line, which brief.md names. analyze reads a placed track's energy envelope (ffmpeg decodes to mono PCM),
picks onsets as peaks of its rise, takes the tempo by autocorrelation and lays a beat grid on the strongest phase;
storyboard.py snap times the film to that tempo, folded into the style's range.

The sound design comes from the same recipe: the engine renders its four effects (riser, hit, bright, impact) in the
recipe's own voices, and master places them at the cut board's `sound` cues, each where a beat lands: `hit` (with a
`bright` layer at its weight), `riser` (the end of the build, ending on the moment it leads to), `impact` (the landing)
and `stop` (where the bed cuts and the last hit rings out into silence). master writes the trimmed bed
(B/music/bed-cut.wav) and the effects (B/music/fx.wav) scaled by loudness to FX_UNDER_BED_LU under the bed, mixes them
(B/music/mix.wav) and brings the whole to -14 LUFS; music.json and the board's storyboard.md carry both loudness numbers.
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
MUSIC = Path(f"{_env.B}/music")
FX_UNDER_BED_LU = 8  # the effects stem's integrated loudness sits this far under the bed's
RISER_GAIN = 0.6  # the build sits under the hits and the landing it leads to


def fresh(stem):
    """A name under B/music/ that no file has (the UTC second and this process), so a new source or master is made
    beside the one music.json names and replaces it only when music.json names the new one."""
    import datetime
    return MUSIC / f"{stem}.{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}.wav"


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
    # a track placed as source.<ext>; a source make wrote has a stamped name and is reached only through music.json
    placed = sorted(p for p in MUSIC.glob("source.*") if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json(f"{_env.B}/music.json") or {}).get("origin") or f"placed in {_env.B}/music/, the track they chose"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json(f"{_env.B}/music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def brief():
    """The person's music brief from B/taste.json (`tempo`, `styles`, `avoid`)."""
    return (_env.read_json(f"{_env.B}/taste.json") or {}).get("music") or {}


def planned(bid=None):
    """The board's length in seconds, the same at any tempo: the winner's, or board `bid`'s; 60 with no board."""
    bid = bid or (_env.read_json(f"{_env.B}/winner.json") or {}).get("board")
    board = _env.read_json(f"{_env.B}/storyboards/{bid}/storyboard.json") if bid else None
    return board["length"] if board else 60


# ------------------------------------------------------------------ make
def board(bid=None):
    """The chosen board (winner.json), or board `bid`; None before a vote or a pick."""
    bid = bid or (_env.read_json(f"{_env.B}/winner.json") or {}).get("board")
    return _env.read_json(f"{_env.B}/storyboards/{bid}/storyboard.json") if bid else None


def recipe_of(b):
    """The music recipe the board's style card names; the engine's default with no board."""
    if not b:
        return None
    import compose
    return compose.card(b["style"])["music"]


def hue():
    """The hue, degrees, of the leading color the two share (palette.json's together palette); None with none."""
    pal = _env.read_json(f"{_env.B}/palette.json") or {}
    rows = pal.get("together") or pal.get("mine") or []
    return music_engine.hue_of(rows[0]["hex"]) if rows else None


def edges(b, bpm):
    """The board's impacts, in seconds at the bed's tempo: where the film lands, so where the bed's sections turn."""
    if not b:
        return []
    import compose
    st = compose.lay(b, "reel")
    return [q["at"] * 60 / bpm for q in st["sound"] if q["kind"] == "impact"]


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    b = board(a.board)
    m = brief()
    recipe_id = recipe_of(b)
    seconds = a.seconds or planned(a.board) + 4
    seed = Path(_env.B).name
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    bpm = music_engine.tempo(recipe, a.bpm, m.get("tempo") or (b or {}).get("bpm"), seed)
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(b, bpm), hue(),
                                seed, bpm=bpm, out=MUSIC)
    default = recipe_id if recipe_id in book["recipes"] else book["default"]
    chose = "their brief" if rid != default else "the style" if default == recipe_id else "the default"
    origin = (f"made by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json(f"{_env.B}/music.json", dict(info, file=str(MUSIC / "bed.wav"), origin=origin))
    for f in MUSIC.glob("source.*"):  # a bed an older make wrote under a stamped name; a placed source.<ext> stays
        if f.stem != "source":
            f.unlink()
    print(f"music: {MUSIC / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json(f"{_env.B}/music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    if info.get("recipe"):
        print(f"music: made by the engine at {info['bpm']:g} bpm, its {len(info['beats'])} beats and {len(info['downbeats'])} "
              "downbeats already in music.json")
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
    _env.write_json(f"{_env.B}/music.json", info)
    print(f"music: {round(bpm, 1)} bpm, {len(onsets)} onsets, {len(beats)} beats, {len(info['downbeats'])} downbeats over {total:.1f} s")
    return 0


# ------------------------------------------------------------------ sound design
def effects(info, bpm):
    """The four effect files music.json names, or, for a track they placed, the chosen board's recipe's set rendered now."""
    fx = info.get("fx") or {}
    if all(Path(fx.get(c) or "").is_file() for c in music_engine.CUES):
        return fx
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_of(board()))
    h = hue()
    tonic = music_engine.tonic_of(h) if h is not None else music_engine.pick(music_engine.rng(Path(_env.B).name, "key"), range(12))
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


def peak_of(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    found = re.findall(r"max_volume:\s+(-?[\d.]+) dB", r.stderr)
    return 10 ** (float(found[-1]) / 20) if found else 1.0


TARGET_LUFS = -14.0


def integrated_file(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


def cmd_master(a):
    info = _env.read_json(f"{_env.B}/music.json") or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    film = _env.read_json(f"{_env.B}/film.json") or {}
    seconds = a.seconds or film.get("seconds")
    if not seconds:
        sys.exit("pass --seconds (the film length), or run storyboard.py snap first")
    ff = _env.ffmpeg()
    source, start = info["file"], 0.0
    cues = film.get("sound") or []
    sec = 60 / film["bpm"] if cues else 0
    # the board's stop: the bed cuts there, the last hit rings out over the held picture, then the film is silent
    stop = next((c["at"] * sec for c in cues if c["kind"] == "stop"), None)
    mixed = {}
    if cues:
        # the board's sound cues under the bed: the effects stem scaled so its integrated loudness is FX_UNDER_BED_LU
        # under the trimmed bed's, then the two summed as they are
        bed, fxw, mix = MUSIC / "bed-cut.wav", MUSIC / "fx.wav", MUSIC / "mix.wav"
        cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
        subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", f"atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS{cut},"
                        "aformat=sample_rates=48000:channel_layouts=stereo", "-ar", "48000", str(bed)], check=True)
        bed_lufs = integrated_file(bed)
        legs = cue_legs(cues, film["bpm"], effects(info, film["bpm"]))
        fx_stem(legs, seconds, 1.0, fxw)
        scale = 0.9 / max(1e-6, peak_of(fxw))
        fx_stem(legs, seconds, scale, fxw)
        fx_stem(legs, seconds, scale * 10 ** ((bed_lufs - FX_UNDER_BED_LU - integrated_file(fxw)) / 20), fxw)
        mixed = {"bed_lufs": round(bed_lufs, 2), "fx_lufs": round(integrated_file(fxw), 2)}
        subprocess.run([ff, "-y", "-v", "error", "-i", str(bed), "-i", str(fxw), "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0:weights=1 1[out]", "-map", "[out]", "-ar", "48000", str(mix)], check=True)
        source = str(mix)
    # With a stop, the last hit's ring fades out over the held picture and the rest is silence. Without one, the music
    # tails out over the film's last bar: the fade starts on the last downbeat at least a second before the end, so the
    # closer holds while the track lets go, never on a hard stop.
    bars = [d for d in info.get("downbeats") or [] if 0 < d <= seconds - 1.0]
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
    out = fresh("master")
    part = MUSIC / f".{out.name}.part.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", str(part)], check=True)
    os.replace(part, out)
    info.update(master=str(out), master_seconds=round(seconds, 3), sound_cues=len(cues), master_lufs=round(integrated_file(out), 2), **mixed)
    _env.write_json(f"{_env.B}/music.json", info)
    md = Path(f"{_env.B}/storyboards/{film.get('id')}/storyboard.md")
    if md.exists():  # the cut's storyboard.md, now at the music's tempo and the film's length, with its loudness
        import storyboard
        storyboard.write_md(film, md)
    if mixed:
        print(f"mixed: bed {mixed['bed_lufs']} LUFS, effects {mixed['fx_lufs']} LUFS, "
              f"{mixed['bed_lufs'] - mixed['fx_lufs']:.1f} LU under; {len(cues)} sound cues over {len(film['beats'])} beats")
    for f in MUSIC.glob("master*.wav"):  # the masters music.json does not name
        if f != out:
            f.unlink()
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--board", help="make: the storyboard to make the bed for (default: the winner)")
    ap.add_argument("--origin", help=f"find: where a track placed at {_env.B}/music/source.<ext> came from, for brief.md")
    a = ap.parse_args()
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
