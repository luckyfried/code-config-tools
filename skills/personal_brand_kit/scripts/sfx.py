#!/usr/bin/env python3
"""The film's sound effects, made here from the board alone, and the film's sound laid under its picture.

USAGE (S = this skill's folder; any python3 from 3.9 to 3.14, nothing to install):
    python3 S/scripts/sfx.py lay --board BOARD.json --out fx.wav [--seconds S] [--music-json music.json]
        # one stereo WAV as long as the film, every effect at its moment
    python3 S/scripts/sfx.py mux --board BOARD.json --film silent.mp4 --out film.mp4 [--music-json music.json] [--seconds S]
        # the film with the effects, over the mastered music music.json names when there is one, alone when there is none

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
- the room under the whole film, a quiet bed of air at -46 dBFS, so the silences between effects are never dead.
The effects and the music are one piece: every effect lands on the music's grid, the nearest quarter beat counted from
frame 0 at the music's tempo, and every tonal effect (the impact, the pop, the shutter's tick, the riser) is pitched to
the music's key, both read from music.json as the music engine wrote it. With no music, or a track that names no key,
the board's tempo makes the grid and the key is one the board picks once for the film.
Every effect peaks at -14 dBFS, 3 dB lower while a words beat is on screen. Under the music, the music comes down 2 dB
for 0.25 s at each impact so the hit reads, and the whole mix passes the music engine's limiter. The same board and
music give the same bytes.
A sound that repeats (a whoosh, a shutter, a pop, an impact) is warm and short: it passes a low-pass that leaves little
above 6 kHz. A bright sound (the bright sweep) is an accent and is used once a film, never on a repeat.
"""
import argparse
import array
import json
import math
import random
import sys
import tempfile
import wave
from pathlib import Path

SR = 48000
PEAK = 10 ** (-14 / 20)  # every effect's peak
UNDER_WORDS = 10 ** (-3 / 20)  # an effect's level while a words beat is on screen
ROOM = 10 ** (-46 / 20)  # the room's level, root mean square
MUSIC_UNDER_IMPACT = 10 ** (-2 / 20)
IMPACT_DIP = 0.25  # seconds the music sits lower from each impact
RISER = 1.2  # seconds
SOFT = {"dissolve", "long-dissolve", "long-fade", "roll-burn"}
GRID = 4  # the effects land on quarters of a beat
WARM = 3500.0  # Hz: the low-pass a repeating sound passes, twice, so little of it is left above 6 kHz
NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")  # the music engine's names for the keys
MARKS = {"sticker-pop", "tape-slap", "doodle-draw-on"}
# the music engine's limiter: the ceiling the mixed film never passes
LIMIT = "aresample=192000,alimiter=limit=0.84:attack=2:release=60:level=false,aresample=48000"


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


def mux_cmd(ffmpeg, film, fx, out, seconds, impacts, music=None):
    """The ffmpeg command that lays the effects (and the music, lowered at each impact) under the film's picture."""
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(film), "-i", str(fx)]
    if music:
        dips = "+".join(f"between(t,{a:.3f},{a + IMPACT_DIP:.3f})" for a in impacts) or "0"
        cmd += ["-i", str(music)]
        graph = (f"[2:a]volume='if({dips},{MUSIC_UNDER_IMPACT:.4f},1)':eval=frame[m];"
                 f"[m][1:a]amix=inputs=2:normalize=0:duration=first,{LIMIT}[a]")
    else:
        graph = f"[1:a]{LIMIT}[a]"
    return cmd + ["-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                  "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart", str(out)]


def mux(spawn, film, out, seconds, board, record=None, ffmpeg="ffmpeg"):
    """The film at `out`: its picture, the board's effects, and the mastered music under them when the music record
    (music.json) names one that exists. The effects' file lives only while ffmpeg reads it. Returns whether music is in
    it."""
    master = (record or {}).get("master")
    music = master if master and Path(master).is_file() else None
    with tempfile.TemporaryDirectory(dir=Path(out).parent) as d:
        fx = Path(d) / "fx.wav"
        chans, impacts = lay(board, seconds, record)
        write(fx, chans)
        spawn(mux_cmd(ffmpeg, film, fx, out, seconds, impacts, music), check=True)
    return bool(music)


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
    ap.add_argument("cmd", choices=["lay", "mux"])
    ap.add_argument("--board", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--film")
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
    if not a.film:
        sys.exit("mux needs --film, the silent film")
    import subprocess
    music = mux(subprocess.run, a.film, a.out, a.seconds or length_of(board), board, record, a.ffmpeg)
    print(f"sfx: {a.out}" + ("" if music else " (effects alone: no music)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
