#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed from the picked board's style and their music brief, then
mastered to -14 LUFS, cut where the picture stops.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/music.py find [--origin "..."] # RUN/music.json: the track placed as RUN/music/source.<ext>, else make
    python3 S/scripts/music.py make [--seconds S]   # a bed composed here on real instruments, at the picked board's tempo
    python3 S/scripts/music.py analyze              # a placed track's onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master [--seconds S] # the bed cut at the board's stop, -14 LUFS by one gain, in float

find takes a track the person or the agent placed as RUN/music/source.<ext> (any audio ffmpeg reads; the person chose
it); else it makes one. make composes a bed with music_engine.py from the picked board's style card (its
`music` recipe in music/recipes.json), steered by the person's music brief (RUN/taste.json `music`: `styles` and
`avoid`), at the board's own tempo, keyed from their photographs' leading color, with its sections turning where the
film lands (the first impact of each beat) and the run's name as the seed, so the same run gives the same music. Each
make writes into a new folder, RUN/music/bed.<stamp>/, and music.json names it, so a make stopped before its index
leaves the bed the index names as it was. analyze reads a placed track's beat grid (a composed bed's grid is its own
and stays).

master trims the bed to the film, cuts it at the board's `stop` (where picture and music stop together, the held
picture after it silent) and brings it to -14 LUFS by one gain, written in 32-bit float so a peak past full scale is
kept whole: the film's mux (sfx.py) limits music and effects together, once. The board's sound effects are never in the master: film.py lays
them under the picture at the mux (sfx.py), in the music's key and on its grid. master measures them all the same:
the effects layer the mux lays (RUN/music/fx.wav) and the master, both integrated, so music.json and storyboard.md
carry both loudness numbers and the gate holds the effects FX_UNDER_BED_LU under the music. It writes the music's
energy beside the master, RUN/music/energy.json: one root mean square (0..1) a frame.

RUN/music.json names the set: `file` the track, `master` the master's file name in RUN/music/, which film.py muxes,
and for a composed bed the engine's grid (recipe, key, bpm, beats, downbeats, sections, chords, programs, removed)
and the board it was composed for.
"""
import argparse
import array
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music_engine  # noqa: E402

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = _env.b("music")
FX_UNDER_BED_LU = 8  # the effects layer's integrated loudness sits at least this far under the master's


def fresh(kind, ext):
    """A new file name in RUN/music for a `kind` (master), unique to this command."""
    return MUSIC / f"{kind}.{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}{ext}"


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
    # a track placed as RUN/music/source.<ext>; a composed bed is RUN/music/bed.<stamp>/bed.wav, reached through music.json
    placed = sorted(p for p in MUSIC.glob("source.*") if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json(_env.b("music.json")) or {}).get("origin") or "placed by the agent in RUN/music/"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json(_env.b("music.json"), info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def brief():
    """The person's music brief from taste.json: `mood`, `styles`, `avoid`."""
    return (_env.read_json(_env.b("taste.json")) or {}).get("music") or {}


def picked():
    """The picked board (winner.json), or SystemExit naming the step before."""
    import compose  # noqa: F401  (the card's faces and colors are read through it)
    style = (_env.read_json(_env.b("winner.json")) or {}).get("board")
    board = _env.read_json(_env.b("storyboards", style, "storyboard.json")) if style else None
    if not board:
        sys.exit("no picked board: run vote.py tally (or vote.py pick <style> when the person chose a look) first")
    return board


def hue(board):
    """The hue of their photographs' leading color, degrees: the key the bed is in."""
    import compose
    return music_engine.hue_of(compose.swatches_of((board.get("facts") or {}).get("look"))[0])


def edges(board):
    """Where the film lands, in seconds, so where the bed's sections turn: the first impact of each of the board's beats
    (a line landing on its print, the closer)."""
    first = {}
    for q in board.get("sound") or []:
        if q["kind"] == "impact":
            first.setdefault(q.get("beat"), q["at"] * 60 / board["bpm"])
    return sorted(first.values())


def peak(board):
    """The story's peak in seconds: where the peak print lands at its station (else where its beat starts) and where its
    beat ends, from the film's timeline, which is in beats of the board's tempo; None when the board marks no peak."""
    for bt in ((board.get("film") or {}).get("timeline") or {}).get("beats") or []:
        if bt.get("peak"):
            s = 60 / board["bpm"]
            return (bt.get("held") or [bt["at"]])[0] * s, bt["end"] * s
    return None


def cmd_make(a):
    import compose
    MUSIC.mkdir(parents=True, exist_ok=True)
    board = picked()
    style = board["style"]
    recipe_id = compose.card(style)["music"]
    m = brief()
    seconds = a.seconds or sum(x["frames"] for x in board["beats"]) / compose.FPS + 4
    book = music_engine.recipes()
    rid, _, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    seed = (board.get("facts") or {}).get("seed") or _env.b().name
    out = fresh("bed", "")
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(board), hue(board),
                                seed, bpm=board["bpm"], out=out, peak=peak(board))
    chose = "their brief" if rid != recipe_id else f"the {style} look"
    origin = (f"composed by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json(_env.b("music.json"), dict(info, file=str(out / "bed.wav"), origin=origin, board=style, seconds=round(seconds, 2)))
    print(f"music: {out / 'bed.wav'} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json(_env.b("music.json")) or {}
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
    _env.write_json(_env.b("music.json"), info)
    print(f"music: {round(bpm, 1)} bpm, {len(onsets)} onsets, {len(beats)} beats, {len(info['downbeats'])} downbeats over {total:.1f} s")
    return 0


# ------------------------------------------------------------------ master
TARGET_LUFS = -14.0


def integrated_file(path):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(found[-1]) if found else float("nan")


def effects_loudness(board, seconds, info):
    """The master's integrated loudness and the effects layer's, as film.py lays it under the picture (the board's film
    as tones/drive.fx_board reads it, in this music's key and on its grid), the layer written to RUN/music/fx.wav."""
    import sfx
    from tones import drive
    fxw = MUSIC / "fx.wav"
    fx = drive.fx_board(board["film"], board["bpm"], board.get("id", ""))
    sfx.write(fxw, sfx.lay(fx, seconds, {**info, "bpm": info.get("bpm") or board["bpm"]})[0])
    return {"bed_lufs": info["master_lufs"], "fx_lufs": round(integrated_file(fxw), 2)}


def cmd_master(a):
    info = _env.read_json(_env.b("music.json")) or {}
    if not info.get("file"):
        sys.exit("no music: run music.py find (or make) first")
    film = _env.read_json(_env.b("film.json")) or {}
    seconds = a.seconds or film.get("seconds")
    if not seconds:
        sys.exit("pass --seconds (the film length), or run storyboard.py snap first")
    ff = _env.ffmpeg()
    start, tempo = float(film.get("music_start") or 0.0), float(film.get("tempo") or 1.0)
    board = _env.read_json(_env.b("storyboards", film["board"], "storyboard.json")) if film.get("board") else None
    cues = (board or {}).get("sound") or []
    # the board's stop: the bed cuts there and the held picture after it is silent
    stop = next((c["at"] * 60 / board["bpm"] for c in cues if c["kind"] == "stop"), None)
    cut = f",afade=t=out:st={stop:.3f}:d=0.04" if stop else ""
    bed = f"atrim=start={start:.3f},asetpts=PTS-STARTPTS,atempo={tempo:.5f},atrim=0:{seconds:.3f},asetpts=PTS-STARTPTS{cut}"
    source = info["file"]
    # With a stop, the music has stopped there and the rest is silence. Without one, the music tails out over the
    # film's last two seconds at most.
    fade = min(2.0, seconds * 0.05)
    st, d = (stop + 0.3, 0.6) if stop and stop + 0.9 <= seconds else (seconds - fade, fade)
    pre = f"{bed},afade=t=out:st={st:.3f}:d={d:.3f}"

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
    out = fresh("master", ".wav")
    with _env.whole(out) as tmp:
        subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(tmp)], check=True)
    info["master"] = out.name
    info["master_seconds"] = round(seconds, 3)
    # the effects a person hears land; the stop is where the sound ends, not an effect
    info["sound_cues"] = sum(1 for c in cues if c["kind"] != "stop")
    info["master_lufs"] = round(integrated_file(out), 2)
    mixed = effects_loudness(board, seconds, info) if info["sound_cues"] else {}
    info.update(mixed)
    import sfx
    sfx.energy(ff, out, ((board or {}).get("format") or {}).get("fps") or 30, MUSIC / "energy.json")
    _env.write_json(_env.b("music.json"), info)
    md = _env.b("storyboards", film["board"], "storyboard.md") if board else None
    if md and md.exists():
        # the cut's storyboard.md: its length at the tempo the music plays in the film (the track's, brought to the
        # board's when snap stretched it) and the film's seconds, where the track came from, and the two loudness numbers
        bpm = board["bpm"]
        length = (f"{len(board['beats'])} beats at {bpm:g} bpm, {seconds:.1f} s; picture and music stop together at beat "
                  f"{(stop or seconds) * bpm / 60:.2f}")
        text = re.sub(r"(?m)^\d+ beats at [\d.]+ bpm[^,]*, [\d.]+ s; picture and music stop together at beat [\d.]+", lambda _: length, md.read_text())
        text = re.sub(r"(?m)^Music: .*$", lambda _: f"Music: {info['origin']}.", text)
        if mixed:
            said = (f"music {mixed['bed_lufs']} LUFS, effects {mixed['fx_lufs']} LUFS, {mixed['bed_lufs'] - mixed['fx_lufs']:.1f} LU under; "
                    f"{info['sound_cues']} sound effects over {len(board['beats'])} beats")
            text = re.sub(r"(?m)^Mixed: .*$", lambda _: f"Mixed: {said}.", text)
            print(f"mixed: {said}")
        _env.write_text(md, text)
    # every other master goes once music.json names this one
    for f in MUSIC.glob("master.*"):
        if f != out:
            f.unlink()
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["find", "make", "analyze", "master"])
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--origin", help="find: where a track placed at RUN/music/source.<ext> came from, for brief.md")
    a = ap.parse_args()
    global MUSIC
    _env.open_run()
    MUSIC = _env.b("music")
    return {"find": cmd_find, "make": cmd_make, "analyze": cmd_analyze, "master": cmd_master}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
