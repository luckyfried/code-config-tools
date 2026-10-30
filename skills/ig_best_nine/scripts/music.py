#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed from the chosen look's style and their music brief, with its
beat grid and its sound effects, mastered to -14 LUFS.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py find --run R [--origin "..."]  # music.json: the track to use and where it came from
    python3 S/scripts/music.py make --run R [--bpm N] [--seconds S]
                                                             # a bed composed here on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze --run R               # a track they brought: onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master --run R [--seconds S]  # from the first downbeat, the board's sound cues mixed under the bed,
                                                             # -14 LUFS (true peak -1.5 dB), trimmed, the last bar faded

find takes the track the person chose, placed as music/source.<ext> in the run (any audio ffmpeg reads); else `make`
composes music/bed.wav with music_engine.py: the recipe is the chosen look's style card's (`music` in
styles/<id>.json, else the style id itself), unless the brief's `styles` words (taste.json `music`) name another; its
`avoid` words take out an instrument, the drums or a groove; the key comes from the palette's leading color, the tempo
from the brief's or the story's, the sections from the board's impacts, and the seed is the run's folder name. make
writes the bed's own beat grid (bpm, beats, downbeats, sections, key) into music.json, so analyze leaves it as it is;
analyze is for a track they brought: it reads the energy envelope (ffmpeg decodes to mono PCM), picks onsets as peaks
of its rise, takes the tempo by autocorrelation and lays a beat grid on the strongest phase. storyboard.py snap cuts the
film on the grid.

The sound effects are the engine's too, played in the recipe's own instruments: music/fx/riser.wav (a build that cuts
off into the moment it leads to), hit.wav, bright.wav (the ring a `bright` hit adds) and impact.wav (the landing); a
track they brought gets its set rendered at master. The board's `sound` cues place them where a beat lands; `stop` is
where the bed cuts and the last hit rings out into silence. master writes the trimmed bed (music/bed-cut.wav) and the
effects (music/fx.wav) scaled by loudness to FX_UNDER_BED_LU under the bed, sums them (music/mix.wav) and brings the
whole to -14 LUFS; music.json and storyboard.md carry both loudness numbers.
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

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = Path("music")
FX_UNDER_BED_LU = 8  # the effects stem's integrated loudness sits this far under the bed's
RISER_GAIN = 0.8  # the riser under a hit's full weight: it builds toward the moment, and the impact lands it
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
    """The board's impacts, in seconds at the bed's tempo (the half, whole or double nearest the board's): where the
    film lands, so where the bed's sections turn."""
    board = reel_of(style)
    if not (board and board.get("bpm")):
        return []
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    return [q["at"] * 60 / (bpm * k) for q in board.get("sound") or [] if q["kind"] == "impact"]


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


# ------------------------------------------------------------------ sound design
def effects(info, bpm):
    """The four effect files music.json names, or, for a track they brought, the winning card's set rendered now."""
    fx = info.get("fx") or {}
    if all(Path(fx.get(c) or "").is_file() for c in music_engine.CUES):
        return fx
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, card()[1])
    h = hue()
    tonic = music_engine.tonic_of(h) if h is not None else music_engine.pick(music_engine.rng(Path.cwd().name, "key"), range(12))
    music_engine.place(music_engine.render_fx(book, recipe, tonic, bpm, MUSIC))
    info.update(fx={c: str(MUSIC / "fx" / f"{c}.wav") for c in music_engine.CUES}, fx_recipe=rid)
    return info["fx"]


def cue_legs(cues, bpm, fps, fx):
    """Each cue as [(file, from, at, gain)]: the file from `from` seconds, placed at `at` in the film. `at` and `beats`
    are read at `bpm`; with the board's `fps`, a cue starts on its own `frame`. A riser is the end of riser.wav, as long
    as the cue's beats, ending on the moment it leads to."""
    sec, legs = 60 / bpm, []
    for c in cues:
        at = c["frame"] / fps if fps and "frame" in c else c["at"] * sec
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
    # the board's stop: the bed cuts there, the last hit rings out over the held picture, then the film is silent
    stop = next((c["at"] * 60 / reel["bpm"] for c in cues if c["kind"] == "stop"), None)
    mixed = {}
    if cues:
        # the board's sound cues under the bed: the effects stem scaled so its integrated loudness is FX_UNDER_BED_LU
        # under the trimmed bed's, then the two summed as they are, in float so a sum past full scale reaches the limiter
        bed, fxw, mix = MUSIC / "bed-cut.wav", MUSIC / "fx.wav", MUSIC / "mix.wav"
        cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
        subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", f"atrim={start:.3f}:{start + seconds:.3f},asetpts=PTS-STARTPTS{cut},"
                        "aformat=sample_rates=48000:channel_layouts=stereo", "-ar", "48000", str(bed)], check=True)
        bed_lufs = integrated_file(bed)
        legs = cue_legs(cues, reel["bpm"], reel.get("fps"), effects(info, reel["bpm"]))
        # measured and scaled twice: the meter is not linear in the gain (its gates drop the quiet tails as the stem
        # turns down), so one scaling lands it up to a few tenths louder than asked
        scale = 1.0
        for _ in range(2 if legs else 0):
            fx_stem(legs, seconds, scale, fxw)
            scale *= 10 ** ((bed_lufs - FX_UNDER_BED_LU - integrated_file(fxw)) / 20)
        fx_stem(legs, seconds, scale, fxw)
        mixed = {"bed_lufs": round(bed_lufs, 2), "fx_lufs": round(integrated_file(fxw), 2)}
        stems = [bed, fxw]
        ins = [x for st in stems for x in ("-i", str(st))]
        subprocess.run([ff, "-y", "-v", "error", *ins, "-filter_complex",
                        "".join(f"[{i}:a]" for i in range(len(stems))) + f"amix=inputs={len(stems)}:normalize=0[out]",
                        "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(mix)], check=True)
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
    # a name of this master's own: the film's mux reads the master music.json names, which stays the last one until
    # this one is written and measured
    out = MUSIC / f"master.{time.time_ns():x}.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", str(out)], check=True)
    info.update(master=str(out), master_seconds=round(seconds, 3), sound_cues=len(cues), master_lufs=round(integrated_file(out), 2), **mixed)
    _env.write_json("music.json", info)
    if mixed:
        said = (f"bed {mixed['bed_lufs']} LUFS, effects {mixed['fx_lufs']} LUFS, "
                f"{mixed['bed_lufs'] - mixed['fx_lufs']:.1f} LU under; {len(cues)} sound cues over {len(reel['beats'])} beats")
        md = Path(film["boards"]["reel"]).with_name("storyboard.md")
        if md.exists():
            _env.write_text(md, re.sub(r"(?m)^Mixed: .*$", lambda _: f"Mixed: {said}.", md.read_text()))
    for f in MUSIC.glob("master.*"):
        if f != out:
            f.unlink()
    if mixed:
        print(f"mixed: bed {mixed['bed_lufs']} LUFS, effects {mixed['fx_lufs']} LUFS, {mixed['bed_lufs'] - mixed['fx_lufs']:.1f} LU under; "
              f"{len(cues)} sound cues over {len(reel['beats'])} beats")
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
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
