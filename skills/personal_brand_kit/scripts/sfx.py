#!/usr/bin/env python3
"""The film's sound effects, made here from the board alone, and the film's sound laid under its picture.

USAGE (S = this skill's folder; any python3 from 3.9 to 3.14, nothing to install):
    python3 S/scripts/sfx.py lay --board BOARD.json --out fx.wav [--seconds S] [--music-json music.json]
        # one stereo WAV as long as the film, every effect at its moment
    python3 S/scripts/sfx.py mux --board BOARD.json --film silent.mp4 --out film.mp4 [--music-json music.json] [--seconds S]
        # the film with the effects, over the mastered music music.json names when there is one, alone when there is none
    python3 S/scripts/sfx.py read --board BOARD.json --music-json music.json --film film.mp4 --out sound.md [--seconds S]
        # the sound read: the cuts against the beat grid, the music's end against the last frame, the effects' peaks
        # against the bed, one table (sound.md) and its numbers (sound.json)

The board says where every effect goes, the way it says where the music's cues go: its tempo turns its beats into
seconds, each beat names its form, its move, and the cut into it, and its layers carry the moments the picture lands.
- a whoosh on every cut but the closer's, peaking on the cut: soft air into a dissolve, a fade, or a burn, and a warm
  sweep into anything else (a slide, a wipe, a page turn, a hard cut); the film's first such cut takes the one bright
  sweep;
- an impact (a low thump under a short pitched knock, gone in about 0.4 s) on every slammed word (the title's slam, each
  word of slam-words and word-per-beat-slam) and on the closer's arrival;
- a pop on every mark (sticker-pop, tape-slap, doodle-draw-on) as its beat arrives;
- a shutter as every photograph arrives, unless its beat lays a mark, whose pop is its sound;
- a riser over the 1.2 s into the closer's arrival, cut off on it: the closer's way in;
- the room under the whole film, a quiet bed of air at -46 dBFS, so the silences between effects are never dead; the
  effects and the room fade to silence over the film's last half second, so its last frames are quiet. The film's
  sound is quiet under QUIET dB, above the room, and quiet_from reads where it falls quiet for good.
The effects and the music are one piece: every effect lands on the music's grid, the nearest quarter beat counted from
frame 0 at the music's tempo, and every tonal effect (the impact, the pop, the shutter's tick, the riser) is pitched to
the music's key, both read from music.json as the music engine wrote it. With no music, or a track that names no key,
the board's tempo makes the grid and the key is one the board picks once for the film.
Every effect peaks at -14 dBFS, 3 dB lower while a words beat is on screen. Under the music, the music comes down 2 dB
for 0.25 s at each impact so the hit reads, and the mux masters the whole mix, music and effects together: it measures
the mix, sets its gain so the film plays at -14 LUFS, and passes it through one limiter whose ceiling sits 4 dB under
full scale; the AAC encode runs with its noise substitution off, so the encoded film's true peak stays under -1.5 dBTP
in one encode and nothing corrects the film after it.
With no music the effects pass the same limiter at their own level. The same board and music give the same bytes.
A sound that repeats (a whoosh, a shutter, a pop, an impact) is warm and short: it passes a low-pass that leaves little
above 6 kHz. A bright sound (the bright sweep) is an accent and is used once a film, never on a repeat.
"""
import argparse
import array
import json
import math
import random
import re
import sys
import tempfile
import wave
from pathlib import Path

SR = 48000
PEAK = 10 ** (-14 / 20)  # every effect's peak
UNDER_WORDS = 10 ** (-3 / 20)  # an effect's level while a words beat is on screen
ROOM = 10 ** (-46 / 20)  # the room's level, root mean square
END_FADE = 0.5  # seconds: the effects and the room fade to silence over the film's last half second
END_FADE_DB = 60.0  # the fade falls this far, evenly in decibels, to silence by the film's last frame
# the level a film's sound is quiet under, dBFS: above the room (-46 dB root mean square, its peaks near -34 dB), so the
# room after the music stops reads quiet, and far under music mastered to -14 LUFS, which never stays under it for the
# 0.3 s quiet_from asks while it plays; every kit's film is mixed here, so the one value reads every kit's quiet
QUIET = -30.0
TARGET_LUFS = -14.0  # the film's integrated loudness with music: music and effects mastered together
MUSIC_UNDER_IMPACT = 10 ** (-2 / 20)
IMPACT_DIP = 0.25  # seconds the music sits lower from each impact
RISER = 1.2  # seconds
SOFT = {"dissolve", "long-dissolve", "long-fade", "roll-burn"}
GRID = 4  # the effects land on quarters of a beat
WARM = 3500.0  # Hz: the low-pass a repeating sound passes, twice, so little of it is left above 6 kHz
NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")  # the music engine's names for the keys
MARKS = {"sticker-pop", "tape-slap", "doodle-draw-on"}
# the film's limiter, oversampled, at a ceiling of -4 dBFS: the AAC encode, with its noise substitution off (which
# swaps noisy bands for fresh noise and throws a limited peak up to 2.7 dB over the ceiling), still overshoots it by
# about 2 dB on a dense mix of low hits under a full bed, so the film's true peak stays under -1.5 dBTP
CEILING = 10 ** (-4.0 / 20)
LIMIT = f"aresample=192000,alimiter=limit={CEILING:.4f}:attack=2:release=60:level=false,aresample=48000"


def _layer(bt):
    return (bt.get("layers") or [{}])[0]


def _at(layer, key):
    at = layer.get("at")
    if isinstance(at, dict):
        v = at.get(key)
        return v[0] if isinstance(v, list) else v
    return at if key in ("arrive", "start") else None


def beats_of(board):
    """Each beat as the effects read it: form, move, cut, start, arrival, end, the beats its words land until, and its
    words, in musical beats from the film's start."""
    out = []
    for bt in board.get("beats") or []:
        ly = _layer(bt)
        kind = ly.get("kind", "")
        start = bt.get("start", ly.get("start", _at(ly, "start")))
        if start is None:
            continue
        end = _at(ly, "end") if isinstance(ly.get("at"), dict) else ly.get("end")
        arrive = _at(ly, "arrive")
        if kind == "Title":
            words = (ly.get("title") or {}).get("text", "")
        elif kind == "Photo":
            words = ly.get("label") or ly.get("text") or ""
        elif kind == "Closer":
            words = (ly.get("signoff") or {}).get("text", "")
        else:
            words = ly.get("text") or bt.get("words") or ""
        pull = _at(ly, "pull") if kind == "Photo" else None
        out.append({"id": bt.get("id"), "form": bt.get("form") or kind.lower(), "kind": kind, "move": bt.get("move"),
                    "cut": bt.get("transition"), "start": float(start), "arrive": float(arrive if arrive is not None else start),
                    "end": None if end is None else float(end), "until": None if pull is None else float(pull),
                    "words": words, "layer": ly})
    for i, b in enumerate(out):
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        b["end"] = b["end"] if b["end"] is not None else (nxt if nxt is not None else b["start"] + 4)
        b["until"] = b["until"] if b["until"] is not None else b["end"]
    return out


def slam_lands(b):
    """The beats a slam-words beat's words land on: the first a quarter of a beat in, then one a beat, closer together
    (to the nearest quarter, never under one) when the words would take more than about the first half of the beat (the
    move's own rule; rounding half up, as the move's Math.round does)."""
    n = len(b["words"].split())
    every = max(0.25, math.floor(4 * min(1.0, 0.55 * max(0.5, b["until"] - b["start"] - 0.25) / max(1, n)) + 0.5) / 4)
    return [b["start"] + 0.25 + k * every for k in range(n)]


_PITCH = {**{n: i for i, n in enumerate(NAMES)}, "Db": 1, "D#": 3, "Gb": 6, "G#": 8, "A#": 10, "Cb": 11, "Fb": 4,
          "E#": 5, "B#": 0}


def music_of(board, record=None):
    """The music the effects play with: (tempo, tonic, where the key came from). The tempo and key are the music
    record's (music.json) when it names them; else the board's tempo and a tonic the board picks once for the film."""
    record = record or {}
    bpm = float(record.get("bpm") or board.get("bpm") or 120)
    name = str(record.get("key") or "").split(" ")[0]
    if name in _PITCH:
        return bpm, _PITCH[name], "music"
    rnd = random.Random(json.dumps(["key", board.get("id"), [b.get("id") for b in board.get("beats") or []]]))
    return bpm, rnd.randrange(12), "board"


def events(board, bpm=None):
    """Every effect the board calls for, as (seconds, kind), in time order, each on the nearest quarter beat of the
    grid counted from frame 0 at `bpm` (the board's tempo when not given), and the spans (seconds) a words beat is on
    screen."""
    sec = 60.0 / float(board.get("bpm") or 120)
    step = 60.0 / float(bpm or board.get("bpm") or 120) / GRID
    ev, words, bright = [], [], False
    bs = beats_of(board)
    for i, b in enumerate(bs):
        # the riser is the closer's way in, so the cut into the closer takes no whoosh over it
        if i > 0 and b["cut"] and b["kind"] != "Closer":
            kind = "air" if b["cut"] in SOFT else "sweep" if bright else "bright"
            bright = bright or kind == "bright"
            ev.append((b["start"] * sec, kind))
        # a photograph whose beat lays a mark arrives on the mark's pop alone, never a pop over a shutter
        if b["kind"] == "Photo" and b["move"] not in MARKS:
            ev.append((b["arrive"] * sec, "shutter"))
        if b["move"] in MARKS:
            ev.append((b["arrive"] * sec, "pop"))
        if b["move"] == "slam-words" and b["words"].strip():
            ev += [(t * sec, "impact") for t in slam_lands(b)]
        if b["move"] == "word-per-beat-slam" and b["words"].strip():
            ev += [((b["start"] + k) * sec, "impact") for k in range(len(b["words"].split())) if b["start"] + k < b["end"]]
        elif b["kind"] == "Title" and isinstance(b["layer"].get("slam"), list):
            a, n = b["layer"]["slam"]
            ev.append(((a + n) * sec, "impact"))
        if b["kind"] == "Closer":
            ev.append((b["start"] * sec, "impact"))
            ev.append((b["start"] * sec, "riser"))
        if b["form"] == "words":
            words.append((b["start"] * sec, b["end"] * sec))
    return sorted((round(round(t / step) * step, 6), k) for t, k in ev), words


def length_of(board):
    """The film's seconds as the board lays it out."""
    bs = beats_of(board)
    return (max(b["end"] for b in bs) if bs else 0.0) * 60.0 / float(board.get("bpm") or 120)


# the voices: each takes the random source and the tonic (0 = C) and returns (left, right) lists of samples at its own
# scale and the sample it lands on; `lay` brings every one to the same peak

def _hz(tonic, lo, steps=0):
    """The tonic (moved `steps` semitones) in the octave from `lo` Hz up."""
    f = 440.0 * 2 ** ((tonic + steps - 9) / 12)
    while f >= 2 * lo:
        f /= 2
    while f < lo:
        f *= 2
    return f


def _svf(x, cut, damp, tap):
    """x through a state-variable filter whose cutoff (Hz) is `cut(i)`, `damp` the inverse of its resonance; `tap` is
    'lo', 'band' or 'hi'."""
    lo = band = 0.0
    out = []
    for i, v in enumerate(x):
        f = 2 * math.sin(math.pi * min(cut(i), SR / 7) / SR)
        hi = v - lo - damp * band
        band += f * hi
        lo += f * band
        out.append(lo if tap == "lo" else band if tap == "band" else hi)
    return out


def _warm(x):
    """x through the low-pass every repeating sound passes: two stages at WARM, so its energy above 6 kHz is small."""
    return _svf(_svf(x, lambda i: WARM, 1.0, "lo"), lambda i: WARM, 1.0, "lo")


def _pan(x, at):
    """x panned by `at(i)`, 0 left to 1 right, at equal power."""
    return ([v * math.cos(at(i) * math.pi / 2) for i, v in enumerate(x)],
            [v * math.sin(at(i) * math.pi / 2) for i, v in enumerate(x)])


def whoosh(rnd, kind):
    """Air moving past: noise through a band that sweeps up into the cut and falls away after it, peaking on the cut.
    'air' is soft and low and 'sweep' warm, both repeat and pass the warm low-pass; 'bright' reaches 7 kHz and is the
    film's one accent, never repeated."""
    bright = kind == "bright"
    n = int({"air": 0.6, "sweep": 0.42, "bright": 0.42}[kind] * SR)
    pk = int(n * (0.55 if kind == "air" else 0.62))
    noise = [rnd.uniform(-1, 1) for _ in range(n)]
    lo, hi = {"air": (260.0, 1500.0), "sweep": (500.0, 3200.0), "bright": (900.0, 7000.0)}[kind]

    def cut(i):
        u = i / pk if i < pk else 1 - 0.6 * (i - pk) / (n - pk)
        return lo * (hi / lo) ** max(0.0, u)

    x = _svf(noise, cut, 1.3 if kind == "air" else 0.6, "band")
    x = x if bright else _warm(x)
    for i in range(n):
        u = i / pk if i < pk else (n - i) / (n - pk)
        x[i] *= (u ** (1.6 if kind == "air" else 2.4)) if i < pk else u ** 1.4
    d = 1 if rnd.random() < 0.5 else -1
    return _pan(x, lambda i: 0.5 + d * 0.32 * (2 * i / n - 1)), pk


def impact(rnd, tonic):
    """A landing, which repeats on slammed words, so it is warm and short: a thump that drops onto the tonic (41 to
    82 Hz) from an octave and a fifth above and dies in about 0.4 s, under a knock on the tonic four octaves up that is
    gone in 15 ms, all through the warm low-pass."""
    n = int(0.45 * SR)
    root, knock = _hz(tonic, 41.0), _hz(tonic, 41.0) * 16
    x, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * root * (1 + 2 * math.exp(-t / 0.035)) / SR
        thump = math.sin(ph) * math.exp(-t / 0.1) * min(1.0, t / 0.002)
        tick = math.sin(2 * math.pi * knock * t) * math.exp(-t / 0.005) * min(1.0, t / 0.0008) * 0.45
        x.append(thump + tick)
    x = _warm(x)
    return (x, list(x)), 0


def pop(rnd, tonic):
    """A mark landing, which repeats, so it is warm and short (0.1 s): a round pop that jumps from the tonic (262 to
    523 Hz) up a fifth, through the warm low-pass."""
    n = int(0.1 * SR)
    f0 = _hz(tonic, 262.0)
    x, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * f0 * (1 + 0.5 * (1 - math.exp(-t / 0.01))) / SR
        x.append(math.sin(ph) * math.exp(-t / 0.026) * min(1.0, t / 0.0015))
    x = _warm(x)
    return (x, list(x)), 0


def shutter(rnd, tonic):
    """A camera's shutter, which repeats on every photograph, so it is warm and short (0.12 s): the blade's click, a
    short rattle, a tick on the key's fifth (660 to 1320 Hz), and the second, softer click 60 ms later, all through the
    warm low-pass."""
    n = int(0.12 * SR)
    noise = [rnd.uniform(-1, 1) for _ in range(n)]
    x = _svf(noise, lambda i: 2600.0, 0.8, "band")
    second = int(0.06 * SR)
    fifth = _hz(tonic, 660.0, 7)
    for i in range(n):
        t = i / SR
        a = math.exp(-t / 0.004) + 0.1 * math.exp(-t / 0.025)
        if i >= second:
            a += 0.6 * math.exp(-(i - second) / SR / 0.004)
        tick = math.sin(2 * math.pi * fifth * t) * math.exp(-t / 0.006) * 0.5
        x[i] = x[i] * a + tick
    x = _warm(x)
    d = 0.5 + 0.15 * (rnd.random() * 2 - 1)
    return _pan(x, lambda i: d), 0


def riser(rnd, tonic):
    """A build of RISER seconds into the closer, once a film: noise through a band sweeping up five octaves over a tone
    gliding up two octaves onto the tonic (from 110 to 220 Hz up to four times that), swelling, cut off on the
    moment."""
    n = int(RISER * SR)
    noise = [rnd.uniform(-1, 1) for _ in range(n)]
    x = _svf(noise, lambda i: 300 * 2 ** (5 * i / n), 0.7, "band")
    base = _hz(tonic, 110.0)
    ph = 0.0
    for i in range(n):
        u = i / n
        ph += 2 * math.pi * base * 2 ** (2 * u) / SR
        tone = 0.35 * (math.sin(ph) + 0.4 * math.sin(2 * ph))
        x[i] = (x[i] + tone) * u ** 2.2 * min(1.0, (n - i) / (0.004 * SR))
    return _pan(x, lambda i: 0.5 + 0.2 * math.sin(2 * math.pi * 3 * i / n)), n


def room(rnd, n):
    """The room: noise warmed by two gentle low-pass stages, a few seconds of it repeated with crossfades, at ROOM."""
    loop = min(n, 3 * SR)
    fade = min(loop // 4, int(0.25 * SR))
    chans = []
    for _ in range(2):
        a = b = 0.0
        base = []
        for _ in range(loop + fade):
            a += 0.06 * (rnd.uniform(-1, 1) - a)
            b += 0.2 * (a - b)
            base.append(b)
        # an equal-power crossfade: the two ends are unrelated noise, so the seam keeps the room's level
        for i in range(fade):
            w = i / fade
            base[i] = base[i] * math.sqrt(w) + base[loop + i] * math.sqrt(1 - w)
        base = base[:loop]
        rms = math.sqrt(sum(v * v for v in base) / max(1, loop)) or 1.0
        base = array.array("f", (v * ROOM / rms for v in base))
        out = array.array("f", base) * (n // loop + 1)
        chans.append(out[:n])
    return chans


VOICES = {"air": lambda r, k: whoosh(r, "air"), "sweep": lambda r, k: whoosh(r, "sweep"),
          "bright": lambda r, k: whoosh(r, "bright"), "impact": impact, "pop": pop, "shutter": shutter, "riser": riser}


def lay(board, seconds=None, record=None):
    """The effects, as (left, right) arrays of float samples at SR, `seconds` long (the board's own length when not
    given), on the grid and in the key of the music `record` (music.json) describes, and the impacts' seconds."""
    seconds = float(seconds if seconds is not None else length_of(board))
    n = max(1, int(round(seconds * SR)))
    rnd = random.Random(json.dumps([board.get("id"), board.get("bpm"), [b.get("id") for b in board.get("beats") or []]]))
    bpm, tonic, _ = music_of(board, record)
    ev, words = events(board, bpm)
    fx = [array.array("f", bytes(4 * n)), array.array("f", bytes(4 * n))]
    for at, kind in ev:
        (left, right), anchor = VOICES[kind](rnd, tonic)
        top = max(1e-9, max(max(abs(v) for v in left), max(abs(v) for v in right)))
        g = PEAK / top
        i0 = int(round(at * SR)) - anchor
        for ch, x in ((0, left), (1, right)):
            buf = fx[ch]
            for k, v in enumerate(x):
                j = i0 + k
                if 0 <= j < n:
                    buf[j] += v * g
    for a, b in words:
        for buf in fx:
            for j in range(max(0, int(a * SR)), min(n, int(b * SR))):
                buf[j] *= UNDER_WORDS
    for buf, bed in zip(fx, room(rnd, n)):
        for j in range(n):
            buf[j] += bed[j]
    fade = min(n, int(END_FADE * SR))
    for k in range(fade):
        g = 10 ** (-END_FADE_DB * (k + 1) / fade / 20)
        for buf in fx:
            buf[n - fade + k] *= g
    return fx, [at for at, kind in ev if kind == "impact"]


def write(path, chans):
    """A 16-bit stereo WAV of the two channels."""
    left, right = chans
    pcm = array.array("h", bytes(4 * len(left)))
    for i in range(len(left)):
        pcm[2 * i] = max(-32767, min(32767, int(left[i] * 32767)))
        pcm[2 * i + 1] = max(-32767, min(32767, int(right[i] * 32767)))
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def mix_graph(impacts, music, tail):
    """The filter graph over the inputs film (0), effects (1) and music (2, when there is music): the music lowered at
    each impact, the effects summed onto it, then `tail`, labelled [a]."""
    if not music:
        return f"[1:a]{tail}[a]"
    dips = "+".join(f"between(t,{a:.3f},{a + IMPACT_DIP:.3f})" for a in impacts) or "0"
    return (f"[2:a]volume='if({dips},{MUSIC_UNDER_IMPACT:.4f},1)':eval=frame[m];"
            f"[m][1:a]amix=inputs=2:normalize=0:duration=first,{tail}[a]")


def mux_cmd(ffmpeg, film, fx, out, seconds, impacts, music=None, gain=0.0):
    """The ffmpeg command that lays the effects (and the music, lowered at each impact) under the film's picture, the
    whole raised by `gain` dB and passed through the limiter, encoded without noise substitution."""
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(film), "-i", str(fx)] + (["-i", str(music)] if music else [])
    return cmd + ["-filter_complex", mix_graph(impacts, music, f"volume={gain:.2f}dB,{LIMIT}"), "-map", "0:v", "-map", "[a]",
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-aac_pns", "0", "-ar", "48000", "-t", f"{seconds:.3f}",
                  "-movflags", "+faststart", str(out)]


def loudness(spawn, ffmpeg, film, fx, music, seconds, impacts, chain):
    """The integrated loudness, LUFS, of the mix mux_cmd lays, through `chain` (a filter chain, or "")."""
    tail = f"{chain + ',' if chain else ''}ebur128=framelog=quiet"
    said = spawn([ffmpeg, "-hide_banner", "-nostats", "-i", str(film), "-i", str(fx), "-i", str(music), "-filter_complex",
                  mix_graph(impacts, music, tail), "-map", "[a]", "-t", f"{seconds:.3f}", "-f", "null", "-"],
                 capture_output=True, text=True).stderr
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", said)
    if not found:
        sys.exit(f"could not measure the loudness of the film's sound over {music}")
    return float(found[-1])


def mux(spawn, film, out, seconds, board, record=None, ffmpeg="ffmpeg"):
    """The film at `out`: its picture, the board's effects, and the music under them when the music record (music.json)
    names a master that exists. With music the mix is mastered here: measured, raised or lowered onto TARGET_LUFS, and
    measured again through the limiter to take up what the limiter took off, until it lands within half a LU. The effects' file lives only while ffmpeg
    reads it. Returns whether music is in it."""
    master = (record or {}).get("master")
    music = master if master and Path(master).is_file() else None
    with tempfile.TemporaryDirectory(dir=Path(out).parent) as d:
        fx = Path(d) / "fx.wav"
        chans, impacts = lay(board, seconds, record)
        write(fx, chans)
        gain = 0.0
        if music:
            gain = TARGET_LUFS - loudness(spawn, ffmpeg, film, fx, music, seconds, impacts, "")
            # the limiter takes off more the more the gain lifts a loud stretch, so the gain is measured through it again
            # until the mix lands within half a LU of the target, three times at most
            for _ in range(3):
                off = TARGET_LUFS - loudness(spawn, ffmpeg, film, fx, music, seconds, impacts, f"volume={gain:.2f}dB,{LIMIT}")
                if abs(off) <= 0.5:
                    break
                gain += off
        spawn(mux_cmd(ffmpeg, film, fx, out, seconds, impacts, music, gain), check=True)
    return bool(music)


def quiet_from(ffmpeg, path, level=QUIET):
    """Where a film's sound falls under `level` dB for good, in seconds: the start of its last silence of 0.3 s or more,
    when that silence runs to the end (ffmpeg closes a silence that runs to the end of the stream at the stream's end);
    None when the sound is never quiet before the end."""
    import subprocess
    r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", f"silencedetect=n={level}dB:d=0.3", "-vn",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = re.findall(r"silence_start: (-?[\d.]+)", r.stderr)
    ends = re.findall(r"silence_end: (-?[\d.]+)", r.stderr)
    if not starts:
        return None
    if len(starts) > len(ends):
        return float(starts[-1])
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return float(starts[-1]) if float(ends[-1]) >= int(h) * 3600 + int(m) * 60 + float(sec) - 0.05 else None



# The sound read: what the critic's music score cites, made without ears from the board, the music record and the film.
ON_BEAT = 0.040  # seconds: a cut this close to a beat of the grid is on it
OVER_BED = 3.0  # dB: an effect is heard when its peak stands this far over the bed's level at its moment
FX_SPAN = (-0.05, 0.30)  # seconds about an effect's moment over which its peak and the bed's level are read
LEVEL_SPAN = 0.05  # seconds: the windows the music's end is read in


def grid_of(board, record=None):
    """The beat grid the cut list is read against, (first beat, step) in seconds: from the music's first beat (music.json
    `beats`), every beat of the film's tempo or of the music's, whichever is faster (a film cut at twice the music's tempo
    reads its own beats, the halves of the music's); the board's beats from frame 0 with no music."""
    record = record or {}
    film = float(board.get("bpm") or 120)
    music = float(record.get("bpm") or film)
    return float((record.get("beats") or [0.0])[0]), 60.0 / max(film, music)


def nearest(t, grid, split=1):
    """The grid's beat (or its `split`-th) nearest `t`, and how far `t` sits from it (positive: after it), in seconds."""
    first, step = grid[0], grid[1] / split
    at = first + round((t - first) / step) * step
    return at, t - at


def cut_list(board):
    """The film's cuts as the board lays them, in seconds: every beat's cut but the first's, at its start, with the moment
    its picture lands (its arrival), and the title's flashes, each the cut to its window's next photograph."""
    sec = 60.0 / float(board.get("bpm") or 120)
    out = []
    for b in beats_of(board):
        if b["start"] > 0:
            out.append({"at": b["start"] * sec, "into": b["id"], "flash": False, "lands": b["arrive"] * sec})
        if b["kind"] == "Title":
            out += [{"at": f * sec, "into": f"{b['id']}, a flash", "flash": True, "lands": f * sec}
                    for f in (b["layer"].get("flash") or [])[:-1]]
    return sorted(out, key=lambda c: c["at"])


def read_cuts(board, record=None):
    """Each cut against the grid: on the beat (within ON_BEAT), deliberately between (a flash of the title's run, which
    changes photograph faster than the beat by design, or a cut that leads its landing: the picture lands on the beat
    within ON_BEAT, less than a beat after the cut), or off the beat, which is a finding."""
    grid = grid_of(board, record)
    rows = []
    for c in cut_list(board):
        beat, off = nearest(c["at"], grid)
        land, land_off = nearest(c["lands"], grid)
        if abs(off) <= ON_BEAT:
            verdict = "on the beat"
        elif c["flash"]:
            verdict = "between, a flash of the title's run"
        elif 0 < c["lands"] - c["at"] < grid[1] and abs(land_off) <= ON_BEAT:
            verdict = f"between, it leads its landing onto the beat at {land:.3f} s"
        else:
            verdict = "off the beat"
        rows.append({"at": round(c["at"], 3), "into": c["into"], "beat": round(beat, 3), "off_ms": round(off * 1000),
                     "verdict": verdict, "pass": verdict != "off the beat"})
    return rows


def _pcm(ffmpeg, path):
    """A file's sound as mono 16-bit samples at SR."""
    import subprocess
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = array.array("h", raw[: len(raw) // 2 * 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    return pcm


def _db(rms):
    return 20 * math.log10(max(rms, 1e-9))


def _rms(pcm, a, b):
    seg = pcm[max(0, a):max(0, b)]
    return math.sqrt(sum(v * v for v in seg) / max(1, len(seg))) / 32768


def quiet_at(pcm, level=QUIET):
    """Where a sound falls under `level` dB for good, in seconds: the start of its last run of LEVEL_SPAN windows whose
    level (root mean square) is under it; None when its last window is over it, so it sounds to the end."""
    n = int(LEVEL_SPAN * SR)
    k = len(pcm) // n
    at = None
    for i in range(k - 1, -1, -1):
        if _db(_rms(pcm, i * n, (i + 1) * n)) >= level:
            break
        at = i * n / SR
    return at


def read_end(board, music_pcm, film_pcm, seconds):
    """The music's end against the last frame: the board's stop (where the picture holds still and the music lets go),
    where the music falls quiet for good, where the film's own sound does, and the film's end. It agrees when the music
    plays on to the stop and both are quiet before the last frame."""
    sec = 60.0 / float(board.get("bpm") or 120)
    stop = next((q["at"] * sec for q in board.get("sound") or [] if q.get("kind") == "stop"), None)
    music = quiet_at(music_pcm) if music_pcm is not None else None
    film = quiet_at(film_pcm) if film_pcm is not None else None
    bad = []
    if music_pcm is not None and music is None:
        bad.append(f"the music is still sounding over {QUIET:g} dB at the last frame ({seconds:.2f} s)")
    if music is not None and stop is not None and music < stop - LEVEL_SPAN:
        bad.append(f"the music falls quiet at {music:.2f} s, before the picture holds still at {stop:.2f} s")
    if film_pcm is not None and film is None:
        bad.append(f"the film's sound is still over {QUIET:g} dB at its last frame ({seconds:.2f} s)")
    r = lambda v: None if v is None else round(v, 2)
    return {"stop": r(stop), "music_quiet": r(music), "film_quiet": r(film), "last_frame": round(seconds, 2),
            "pass": not bad, "findings": bad}


def read_effects(board, record, seconds, music_pcm):
    """Each effect's peak against the bed: its peak (dBFS) as the mux lays it, and the music's level (root mean square,
    dBFS, before the mix's gain, which lifts both alike) over FX_SPAN about its moment. An effect is heard when its peak
    stands OVER_BED dB or more over the bed, or when there is no music under it."""
    chans, _ = lay(board, seconds, record)
    bpm, _, _ = music_of(board, record)
    rows = []
    for at, kind in events(board, bpm)[0]:
        a, b = int((at + FX_SPAN[0]) * SR), int((at + FX_SPAN[1]) * SR)
        peak = max([abs(v) for ch in chans for v in ch[max(0, a):max(0, b)]] or [0.0])
        bed = None if music_pcm is None else round(_db(_rms(music_pcm, a, b)), 1)
        over = None if bed is None else round(_db(peak) - bed, 1)
        rows.append({"at": round(at, 3), "kind": kind, "peak_db": round(_db(peak), 1), "bed_db": bed, "over_db": over,
                     "pass": over is None or over >= OVER_BED})
    return rows


def read(board, record=None, film=None, seconds=None, ffmpeg="ffmpeg", base="."):
    """The film's sound read: its cuts against the beat grid, the music's end against the last frame, and each effect's
    peak against the bed, with every finding in words. `record` is music.json, its master a path from `base`; `film` the
    rendered film, whose own sound the end is read in."""
    record = record or {}
    seconds = float(seconds if seconds is not None else length_of(board))
    master = record.get("master")
    master = Path(base) / master if master else None
    music_pcm = _pcm(ffmpeg, master) if master and master.is_file() else None
    film_pcm = _pcm(ffmpeg, film) if film and Path(film).is_file() else None
    cuts = read_cuts(board, record)
    end = read_end(board, music_pcm, film_pcm, seconds)
    fx = read_effects(board, record, seconds, music_pcm)
    first, step = grid_of(board, record)
    found = [f"the cut into {c['into']} at {c['at']:.3f} s is {abs(c['off_ms'])} ms {'after' if c['off_ms'] > 0 else 'before'} "
             f"the beat at {c['beat']:.3f} s" for c in cuts if not c["pass"]]
    found += end["findings"]
    found += [f"the {e['kind']} at {e['at']:.2f} s peaks {e['over_db']:+.1f} dB against the bed ({e['bed_db']:.1f} dB): the "
              "music covers it" for e in fx if not e["pass"]]
    return {"grid": {"first": round(first, 3), "step": round(step, 4), "bpm": round(60.0 / step, 2)}, "cuts": cuts,
            "end": end, "effects": fx, "findings": found}


def table(r):
    """The sound read as one markdown page: the cuts, the music's end and the effects, then the findings."""
    g = r["grid"]
    L = ["# the sound read", "",
         f"The grid: a beat every {g['step']:g} s ({g['bpm']:g} bpm) from {g['first']:g} s. A cut is on the beat within "
         f"{round(ON_BEAT * 1000)} ms; an effect is heard when its peak stands {OVER_BED:g} dB over the bed.", "",
         "## the cuts", "", "| cut into | at (s) | nearest beat (s) | off (ms) | read |", "|---|---|---|---|---|"]
    L += [f"| {c['into']} | {c['at']:.3f} | {c['beat']:.3f} | {c['off_ms']:+d} | {c['verdict']} |" for c in r["cuts"]]
    e = r["end"]
    f = lambda v: "-" if v is None else f"{v:.2f}"
    L += ["", "## the music's end", "", "| the stop (s) | the music quiet from (s) | the film's sound quiet from (s) | "
          "the last frame (s) | read |", "|---|---|---|---|---|",
          f"| {f(e['stop'])} | {f(e['music_quiet'])} | {f(e['film_quiet'])} | {e['last_frame']:.2f} | "
          f"{'agrees' if e['pass'] else '; '.join(e['findings'])} |"]
    L += ["", "## the effects against the bed", "", "| at (s) | effect | peak (dB) | bed (dB) | over the bed (dB) | read |",
          "|---|---|---|---|---|---|"]
    L += [f"| {x['at']:.2f} | {x['kind']} | {x['peak_db']:.1f} | {'-' if x['bed_db'] is None else format(x['bed_db'], '.1f')} | "
          f"{'-' if x['over_db'] is None else format(x['over_db'], '+.1f')} | {'heard' if x['pass'] else 'under the music'} |"
          for x in r["effects"]]
    L += ["", "## findings", ""] + ([f"- {x}" for x in r["findings"]] or ["- none"])
    return "\n".join(L) + "\n"


def energy(ffmpeg, wav, fps, out):
    """The music's energy, one number a frame: the root mean square of each frame's samples (mono, full scale 1, so
    0..1), written to `out` as {"fps", "rms"}."""
    import subprocess
    with tempfile.TemporaryDirectory(dir=Path(out).parent) as d:
        pcmf = Path(d) / "mono.s16le"
        subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", str(SR), "-f", "s16le", str(pcmf)],
                       check=True)
        raw = pcmf.read_bytes()
    pcm = array.array("h", raw[: len(raw) // 2 * 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    per = SR / float(fps)
    rms = []
    for k in range(int(len(pcm) / per)):
        a, b = int(k * per), int((k + 1) * per)
        rms.append(round(math.sqrt(sum(v * v for v in pcm[a:b]) / max(1, b - a)) / 32768, 4))
    Path(out).write_text(json.dumps({"fps": fps, "rms": rms}) + "\n")
    return rms


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["lay", "mux", "read"])
    ap.add_argument("--board", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--film", help="mux: the silent film; read: the rendered film")
    ap.add_argument("--music-json", help="the music record (music.json): its tempo, its key, and the master under the film")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    board = json.loads(Path(a.board).read_text())
    record = json.loads(Path(a.music_json).read_text()) if a.music_json else None
    if a.cmd == "lay":
        chans, _ = lay(board, a.seconds, record)
        write(a.out, chans)
        bpm, tonic, whence = music_of(board, record)
        print(f"sfx: {len(events(board, bpm)[0])} effects in {NAMES[tonic]} at {bpm:g} bpm (key from the {whence}) over {len(chans[0]) / SR:.2f} s -> {a.out}")
        return 0
    if a.cmd == "read":
        r = read(board, record, a.film, a.seconds, a.ffmpeg, Path(a.music_json).parent if a.music_json else ".")
        Path(a.out).write_text(table(r))
        Path(a.out).with_suffix(".json").write_text(json.dumps(r, indent=1) + "\n")
        print(f"sfx: the sound read, {len(r['cuts'])} cuts, {len(r['effects'])} effects, {len(r['findings'])} findings -> {a.out}")
        return 0
    if not a.film:
        sys.exit("mux needs --film, the silent film")
    import subprocess
    music = mux(subprocess.run, a.film, a.out, a.seconds or length_of(board), board, record, a.ffmpeg)
    print(f"sfx: {a.out}" + ("" if music else " (effects alone: no music)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
