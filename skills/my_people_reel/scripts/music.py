#!/usr/bin/env python3
"""The film's music: the person's track, or a bed composed in the picked look's style from their music brief, with its
beat grid, mastered to -14 LUFS and stopped on the board's stop.

USAGE (from the workspace root; S = this skill's folder; R = the run folder, build/<run stamp>/):
    python3 S/scripts/music.py find [--origin "..."]   # R/music.json: the track to use and where it came from
    python3 S/scripts/music.py make [--bpm N] [--seconds S]
                                                      # a bed composed here on real instruments (music_engine.py)
    python3 S/scripts/music.py analyze                # a track they brought: onsets, tempo, beat grid and downbeats
    python3 S/scripts/music.py master [--seconds S]   # from the downbeat film.json names, -14 LUFS by one gain (float,
                                                      # the film's mux limits it with the effects), cut on the board's
                                                      # stop; music/energy.json beside it

find takes a track the person chose, placed as music/source.<ext> in the run (any audio ffmpeg reads); else it runs
`make`, which composes the bed with music_engine.py: the recipe is the picked look's style card's (`music` in
styles/<id>.json), unless the brief's `styles` words (taste.json `music`) name another; its `avoid` words take out an
instrument, the drums or a groove; the key comes from the palette's leading color, the tempo from the brief's (else the
middle of the recipe's own range), raised inside the range as far as the board needs to run within the film's longest
(a slow recipe would carry five people past thirty seconds), the sections turn where the board's effects land their
impacts, and the seed is the run's folder name. music.json's origin says which recipe and why. music.json is the index
of music/: make and master write each file under a name of its own (music/bed-<hash>.wav, music/master-<hash>.wav),
then music.json naming it, and only then remove the earlier ones; film.py cut reads the master music.json names. find
looks only at music/source.<ext>, so a file this script made never stands in for a track placed after it. brief.md
names the origin either way. make writes the bed's own beat grid (bpm, beats, downbeats, sections, key) into
music.json, so analyze leaves it as it is; analyze is for a track they brought: it reads the energy envelope (ffmpeg
decodes to mono PCM), picks onsets as peaks of its rise, takes the tempo by autocorrelation and lays a beat grid on the
strongest phase. storyboard.py snap cuts the film on that grid.

The music carries no sound effects: film.py lays the board's effects (sfx.py) over the master, on this music's grid and
in its key. master cuts the music on the board's `stop` (the closer's title settles there with its impact), and writes
music/energy.json, the master's energy, one root mean square (0..1) a frame.
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

AUDIO = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")
MUSIC = Path("music")


def duration(f):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def published(made, stem):
    """Move a finished file to music/<stem>-<first 12 hex of its sha-256><suffix>: a new name for new bytes, so the
    file music.json names stays as it is until music.json names the new one."""
    made = Path(made)
    dest = MUSIC / f"{stem}-{hashlib.sha256(made.read_bytes()).hexdigest()[:12]}{made.suffix}"
    os.replace(made, dest)
    return dest


def placed_sources():
    """The tracks a person or the agent placed: music/source.<ext> only, never a file this script named."""
    return sorted(p for p in MUSIC.iterdir() if p.stem == "source" and p.suffix.lower() in AUDIO + (".mp4", ".mov"))


def has_audio(f):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def cmd_find(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    placed = placed_sources()
    if not (placed and has_audio(placed[0])):
        return cmd_make(a)
    origin = a.origin or (_env.read_json("music.json") or {}).get("origin") or "placed by the agent in music/"
    info = {"file": str(placed[0]), "origin": origin, "seconds": round(duration(placed[0]), 2)}
    _env.write_json("music.json", info)
    print(f"music: {info['file']} ({info['seconds']} s), {info['origin']}")
    return 0


def brief():
    """The person's music brief from taste.json (`mood`, `tempo`, `styles`, `avoid`)."""
    return (_env.read_json("taste.json") or {}).get("music") or {}


# ------------------------------------------------------------------ make
def picked():
    """The picked look's style id and its music recipe id (None and None before a pick)."""
    import style
    look = (_env.read_json("winner.json") or {}).get("board")
    if not look:
        return None, None
    return look, style.card(look).get("music") or look


def hue():
    """The palette's leading color's hue, degrees (None with no palette)."""
    year = (_env.read_json("palette.json") or {}).get("year") or []
    return music_engine.hue_of(year[0]["hex"]) if year and year[0].get("hex") else None


def fitted(bpm, hi, sb):
    """`bpm`, or the slowest whole tempo above it, up to `hi`, at which the snap's cut of storyboard `sb` (its pulses at
    the tempo folded to the board's own) runs no longer than the gate's longest film, with half a second spare."""
    import qa
    import storyboard
    pulses, most = sum(b["pulses"] for b in sb["beats"]), qa.longest() - 0.5
    fits = [t for t in [bpm] + list(range(math.ceil(bpm), int(hi) + 1)) if pulses * 60 / storyboard.fold(t, sb["bpm"]) <= most]
    return float(fits[0]) if fits else bpm


def picked_board(look):
    """The picked board laid out 9:16 at its own tempo, and its storyboard (None and None before a draft)."""
    sb = (_env.read_json("film.json") or {}).get("storyboard") or (_env.read_json(f"storyboards/{look}/storyboard.json") if look else None)
    if not sb:
        return None, None
    import boards
    return boards.layout(sb, boards.Ctx(), "reel"), sb


def edges(board, bpm):
    """The board's impacts (its effects' title lands, slammed words and the wall settling), in seconds at the bed's
    tempo (the half, whole or double nearest the board's): where the film lands, so where the bed's sections turn."""
    if not (board and board.get("bpm") and board.get("effects")):
        return []
    import sfx
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    events, _ = sfx.events(board["effects"])
    return [t * board["bpm"] / (bpm * k) for t, kind in events if kind == "impact"]


def peak(board, bpm):
    """The story's peak (landing, end) in seconds at the bed's tempo (the half, whole or double nearest the board's):
    where the board's last person's beat starts, the beat the card's `once` move takes, and where it ends; None with no
    person on the board."""
    if not (board and board.get("bpm")):
        return None
    import boards
    k = min((0.5, 1, 2), key=lambda k: abs(bpm * k - board["bpm"]))
    t, at = 0, None
    for b in board.get("beats") or []:
        if b.get("comp") == "person":
            at = (t, t + b["frames"])
        t += b["frames"]
    if at is None:
        return None
    scale = board["bpm"] / (bpm * k) / boards.FPS
    return at[0] * scale, at[1] * scale


def cmd_make(a):
    MUSIC.mkdir(parents=True, exist_ok=True)
    look, recipe_id = picked()
    board, sb = picked_board(look)
    m = brief()
    seed = Path.cwd().name
    book = music_engine.recipes()
    rid, recipe, _ = music_engine.resolve(book, recipe_id, m.get("styles") or [], m.get("avoid") or [])
    lo, hi = recipe["tempo"]
    bpm = music_engine.tempo(recipe, a.bpm, m.get("tempo") or (lo + hi) / 2, seed)
    if sb and not a.bpm:
        bpm = fitted(bpm, hi, sb)
    # the snap cuts the board at the music's tempo folded to the board's own, so the bed runs the board's length at
    # that tempo, with four seconds for the downbeat the cut starts on
    if a.seconds:
        seconds = a.seconds
    elif sb:
        import storyboard
        seconds = sum(b["pulses"] for b in sb["beats"]) * 60 / storyboard.fold(bpm, sb["bpm"]) + 4
    else:
        seconds = 64
    info = music_engine.compose(recipe_id, m.get("styles") or [], m.get("avoid") or [], seconds, edges(board, bpm), hue(),
                                seed, bpm=bpm, out=MUSIC, peak=peak(board, bpm))
    # music.json is the index of music/: the bed moves in under a name of its own, music.json names it, and only then
    # do the placed sources and the earlier beds go
    src = published(MUSIC / "bed.wav", "bed")
    default = recipe_id if recipe_id in book["recipes"] else book["default"]
    chose = "their brief" if rid != default else "the look" if default == recipe_id else "the default"
    origin = (f"made by music.py from the {rid} recipe ({book['recipes'][rid]['name']}, chosen by {chose}) in {info['key']} "
              f"at {info['bpm']:g} bpm" + (f", without {', '.join(info['removed'])}" if info["removed"] else ""))
    _env.write_json("music.json", dict(info, file=str(src), origin=origin))
    for f in placed_sources() + list(MUSIC.glob("bed-*.wav")):
        if f != src:
            f.unlink()
    print(f"music: {src} ({seconds:.1f} s), {origin}; chords {' '.join(info['chords'])}")
    return 0


# ------------------------------------------------------------------ analyze
def cmd_analyze(a):
    info = _env.read_json("music.json") or {}
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
    start = float(film.get("music_start") or 0)
    ff = _env.ffmpeg()
    source = info["file"]
    reel = None
    if film.get("storyboard"):
        import boards
        ctx = boards.Ctx()
        reel = boards.layout(film["storyboard"], ctx, "reel", film["bpm"])
    # the board's stop: the music cuts there, under the impact of the closer's title settling, and the room alone
    # carries the held picture to the end
    stop = next((c["at"] * 60 / reel["bpm"] for c in (reel or {}).get("sound") or [] if c["kind"] == "stop"), None)
    # With a stop, the music cuts on it. Without one, the music tails out over the film's last bar: the fade starts on
    # the last downbeat at least a second before the end, so the closer holds while the track lets go, never on a hard
    # stop.
    bars = [d - start for d in info.get("downbeats") or [] if 0 < d - start <= seconds - 1.0]
    fade = seconds - bars[-1] if bars else min(2.0, seconds * 0.05)
    st, d = (stop, 0.04) if stop and stop + 0.5 <= seconds else (seconds - fade, fade)
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
    # film.py cut lays the master music.json names under the picture, so the master is made under its part name, moved
    # in under a name of its own and measured, music.json names it, and only then do the earlier masters go
    made = _env.part(MUSIC / "master.wav")
    subprocess.run([ff, "-y", "-v", "error", "-i", source, "-af", flt, "-ar", "48000", "-c:a", "pcm_f32le", str(made)], check=True)
    out = published(made, "master")
    info["master"] = str(out)
    info["master_seconds"] = round(seconds, 3)
    info["master_lufs"] = round(integrated_file(out), 2)
    for k in ("sound_cues", "bed_lufs", "fx_lufs"):
        info.pop(k, None)
    _env.write_json("music.json", info)
    # the music's energy, one number a frame, beside the master
    import sfx
    sfx.energy(ff, out, 30, MUSIC / "energy.json")
    if film.get("storyboard"):
        # storyboard.md's length, Music and Mixed lines are written from the cut and this mix, in one pass
        import storyboard
        _env.write_text(storyboard.sb_path(film["style"]).parent / "storyboard.md", storyboard.markdown(film["storyboard"], ctx))
    for f in list(MUSIC.glob("master-*.wav")) + [MUSIC / "master.wav"]:
        if f != out:
            f.unlink(missing_ok=True)
    print(f"mastered {seconds:.1f} s to {info['master_lufs']} LUFS -> {out}")
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
