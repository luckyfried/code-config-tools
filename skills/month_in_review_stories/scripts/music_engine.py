#!/usr/bin/env python3
"""The music engine: a bed and its sound effects composed from a recipe and played on real instruments.

USAGE (S = this skill's folder; any python3 from 3.9 to 3.14, nothing to install):
    python3 S/scripts/music_engine.py make --out DIR --seconds 45 [--style ID] [--styles "words" ...] [--avoid "words" ...]
                                           [--edges 8.2 21.5 ...] [--hue 210 | --color "#3a6ea5"] [--seed RUN] [--bpm N]
                                           [--target-bpm N]
        # DIR/bed.wav, DIR/fx/{riser,hit,bright,impact}.wav, and DIR/../music.json's grid (or --json-out FILE)
    python3 S/scripts/music_engine.py fx --out DIR [--style ID] [--hue H] [--seed RUN] [--bpm N]   # the effects alone
    python3 S/scripts/music_engine.py recipes                                                        # the recipes and their words

A recipe (music/recipes.json, one per style card id) is all a style sounds like: its tempo range, mode, chord
progressions, grooves, instruments per role, drum kit, effects chain and sound-effect voices. This file only plays
one, and has no style of its own. The instruments are music/instruments.sf3, played by tinysoundfont, whose compiled
module for this python and this machine is loaded from vendor/tinysoundfont/<cpXY>-<platform>/.

What decides the music:
- the recipe: the card's (`style`, a style card id) unless the brief's `styles` words name another; the brief wins.
  A phrase like "no drums" inside a style phrase counts as an avoid word.
- `avoid` words remove what recipes.json maps them to: a role, the drum kit, a groove or a step of the effects chain,
  never the last instrument or the last groove.
- the key: the photos' dominant hue, its place on the colour wheel taken as a place on the circle of fifths.
- the tempo: `bpm` exactly; else the brief's or the board's tempo moved by octaves into the recipe's range, the
  nearest; else a pick in the range.
- the form: the film's section edges (seconds) split the bed into sections, each starting on a bar line and a new
  pass of its progression, with a drum fill into it and a crash on it; the recipe's `arc` gives each section's energy,
  which picks its groove and decides which roles play.
- the seed (the run id): the progressions, the grooves among equals, the melodies and the small velocity changes. The
  same inputs give the same bytes.
"""
import argparse
import colorsys
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

S = Path(__file__).resolve().parents[1]
RECIPES = S / "music" / "recipes.json"
FONT = S / "music" / "instruments.sf3"
VENDOR = S / "vendor" / "tinysoundfont"
PLATFORMS = {("Linux", "x86_64"): "linux_x86_64", ("Darwin", "arm64"): "macos_arm64"}
SR = 48000
BED_LUFS = -16.0  # the bed as the engine writes it; mastering brings the whole film to -14
FX_LUFS = -18.0  # each effect file, so a cue's weight in the score is its level
PEAK = 0.84  # -1.5 dB: the limiter's ceiling on everything the engine writes
# the limiter runs at four times the rate, so the peaks between samples stay under the ceiling too (-1.5 dBTP)
LIMIT = f"aresample={4 * SR},alimiter=limit={PEAK}:attack=2:release=60:level=false,aresample={SR}"
GAIN_DB = -9.0  # the synthesizer's output gain, headroom for a full arrangement before the chain
CUES = ("riser", "hit", "bright", "impact")
FX_SECONDS = {"hit": 1.6, "bright": 1.2, "impact": 3.0}  # the riser is two bars at the bed's tempo
FX_TAIL = 1.0  # seconds a hit or an impact rings on through the chain's room
STEPS = 16  # a bar's steps
LEVEL = {"X": 1.0, "x": 0.82, "o": 0.6}
MODES = {"ionian": (0, 2, 4, 5, 7, 9, 11), "dorian": (0, 2, 3, 5, 7, 9, 10), "phrygian": (0, 1, 3, 5, 7, 8, 10),
         "lydian": (0, 2, 4, 6, 7, 9, 11), "mixolydian": (0, 2, 4, 5, 7, 9, 10), "aeolian": (0, 2, 3, 5, 7, 8, 10)}
NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
DEFAULT_EDGES = (0.2, 0.5, 0.8)  # with no section edges, the bed's own form: intro, lift, peak, out


class Refusal(SystemExit):
    """The engine stops with one plain sentence."""


# ------------------------------------------------------------------ the player
def player():
    """tinysoundfont's compiled module for this python on this machine, from vendor/."""
    v, where = sys.version_info, PLATFORMS.get((platform.system(), platform.machine()))
    folder = VENDOR / f"cp{v[0]}{v[1]}-{where}" / "tinysoundfont"
    if not where or not any(folder.glob("_tinysoundfont.*")):
        have = sorted(p.name for p in VENDOR.glob("cp*-*") if p.is_dir())
        raise Refusal(f"The music engine has no instrument player for Python {v[0]}.{v[1]} on {platform.system()} "
                      f"{platform.machine()}; run it with one of these: {', '.join(have)}.")
    sys.path.insert(0, str(folder))
    try:
        import _tinysoundfont
    except ImportError as e:
        raise Refusal(f"The music engine's instrument player for Python {v[0]}.{v[1]} would not load on this machine ({e}).")
    finally:
        sys.path.remove(str(folder))
    return _tinysoundfont


# ------------------------------------------------------------------ choices
def recipes():
    return json.loads(RECIPES.read_text())


def rng(seed, *purpose):
    """A random stream for one purpose of one seed: the same stream on every python version and machine."""
    import random
    return random.Random(int(hashlib.sha256(":".join(map(str, (seed,) + purpose)).encode()).hexdigest()[:16], 16))


def pick(r, seq):
    return seq[int(r.random() * len(seq))]


def words_in(word, phrase):
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", phrase) is not None


def split_styles(styles):
    """The style phrases with their "no X" / "without X" parts taken out, and those parts as avoid phrases."""
    keep, avoid = [], []
    for p in styles or []:
        p = p.lower()
        avoid += [m.strip() for m in re.findall(r"\b(?:no|without|not)\s+([a-z][a-z \-]*)", p)]
        keep.append(re.sub(r"\b(?:no|without|not)\s+[a-z][a-z \-]*", " ", p))
    return keep, avoid


def choose(book, card, styles):
    """The recipe id: the one whose words the brief's style phrases name most, the card's on a tie or with none."""
    order = list(book["recipes"])
    card = card if card in book["recipes"] else book["default"]
    score = {rid: sum(words_in(w, p) for p in styles for w in book["styles"].get(rid, [])) for rid in order}
    best = max(score.values()) if score else 0
    if best == 0 or score[card] == best:
        return card
    return next(rid for rid in order if score[rid] == best)


def constrain(book, recipe, avoid):
    """The recipe with what the avoid words map to removed, and the tags that removed something."""
    tags = set()
    for phrase in avoid or []:
        phrase = phrase.lower()
        for word, t in book["avoid"].items():
            if words_in(word, phrase):
                tags |= set(t)
    r = json.loads(json.dumps(recipe))
    hit = lambda x: bool(tags & set(x.get("tags") or []))
    roles = {k: v for k, v in r["roles"].items() if not hit(v)}
    r["roles"] = roles or dict([next(iter(r["roles"].items()))])
    if r.get("drums") is not None and hit(r["drums"]):
        r["drums"] = None
    r["grooves"] = [g for g in r["grooves"] if not hit(g)] or r["grooves"][:1]
    r["chain"] = [c for c in r["chain"] if not hit(c)]
    used = {t for x in list(recipe["roles"].values()) + recipe["grooves"] + recipe["chain"] + [recipe.get("drums") or {}]
            for t in (x.get("tags") or []) if t in tags}
    return r, sorted(used)


def hue_of(color):
    c = color.lstrip("#")
    h, _, _ = colorsys.rgb_to_hls(*(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    return h * 360


def tonic_of(hue):
    """The key's pitch class: the hue's twelfth of the colour wheel read as a step round the circle of fifths."""
    return round((hue % 360) / 30) % 12 * 7 % 12


def tempo(recipe, bpm=None, target=None, seed=""):
    lo, hi = recipe["tempo"]
    if bpm:
        return float(bpm)
    if target:
        # the tempo in range whose half, whole or double lands nearest the target, the whole first on a tie
        best = min(((min(hi, max(lo, target / k)), k) for k in (1, 0.5, 2)), key=lambda ck: abs(math.log(ck[0] * ck[1] / target)))
        return float(round(best[0]))
    return float(round(lo + rng(seed, "tempo").random() * (hi - lo)))


# ------------------------------------------------------------------ harmony
def base_of(tonic, octave):
    """The MIDI note of the tonic nearest the C of `octave`."""
    return 12 * (octave + 1) + (tonic + 6) % 12 - 6


def scale_note(base, mode, step):
    return base + 12 * (step // 7) + mode[step % 7]


def fold(n, lo, hi):
    while n < lo:
        n += 12
    while n >= hi:
        n -= 12
    return n


def chord_notes(base, mode, degree, voicing):
    notes = sorted({fold(scale_note(base, mode, degree - 1 + v), base - 4, base + 12) for v in voicing})
    return notes


def chord_name(tonic, mode, degree, voicing):
    m = MODES[mode]
    step = lambda k: scale_note(0, m, degree - 1 + k) - scale_note(0, m, degree - 1)
    third, fifth, seventh = step(2), step(4), step(6)
    q = {(4, 7): "", (3, 7): "m", (3, 6): "dim", (4, 8): "aug"}.get((third, fifth), "sus")
    if 6 in voicing:
        q = {"": "maj7" if seventh == 11 else "7", "m": "m7", "dim": "m7b5"}.get(q, q + "7")
    if voicing and max(voicing) == 6 and 2 not in voicing:
        q = "sus4(7)"
    return NAMES[(tonic + m[(degree - 1) % 7]) % 12] + q


# ------------------------------------------------------------------ the arrangement
def pattern(text):
    """[(step, level, steps held)] of a pattern."""
    out = []
    for i, ch in enumerate(text):
        if ch in LEVEL:
            n = 1
            while i + n < len(text) and text[i + n] == "-":
                n += 1
            out.append((i, LEVEL[ch], n))
    return out


def form(recipe, seconds, edges, bpm):
    """The sections [(first bar, end bar, energy)] and the bar count."""
    bar = 240 / bpm
    bars = max(1, math.ceil(seconds / bar))
    cuts = [round(e / bar) for e in (edges if edges else [f * seconds for f in DEFAULT_EDGES])]
    starts = [0]
    for c in sorted(set(cuts)):
        if c - starts[-1] >= 2 and bars - c >= 1:
            starts.append(c)
    arc, n = recipe["arc"], len(starts)
    energy = [arc[round(i * (len(arc) - 1) / (n - 1))] if n > 1 else arc[0] for i in range(n)]
    return [(s, (starts + [bars])[i + 1], energy[i]) for i, s in enumerate(starts)], bars


def arrange(book, recipe, tonic, bpm, seconds, edges, seed):
    """The bed as note events [(seconds, order, kind, channel, a, b)], its channels' presets, and what it played."""
    mode = MODES[recipe["mode"]]
    sections, bars = form(recipe, seconds, edges, bpm)
    step_s = 60 / bpm / 4
    swing = recipe.get("swing", 0.0)
    r = rng(seed, "progression")
    progs = recipe["progressions"]
    main = pick(r, range(len(progs)))
    lift = pick(r, [i for i in range(len(progs)) if i != main] or [main])
    groove_r, vel_r = rng(seed, "groove"), rng(seed, "velocity")
    roles = recipe["roles"]
    channels = {}
    for name in roles:
        channels[name] = len(channels) + (1 if len(channels) >= 9 else 0)
    drums = recipe.get("drums")
    dmap = book["drum_map"]
    presets = {channels[n]: (v.get("bank", 0), v["program"]) for n, v in roles.items()}
    if drums:
        presets[9] = (128, drums["kit"])
    events, chords, plan = [], [], []
    when = lambda bar, step: (bar * STEPS + step + (swing if step % 2 else 0.0)) * step_s

    def note(t0, t1, ch, key, vel):
        vel = max(0.05, min(1.0, vel * (1 + (vel_r.random() - 0.5) * 0.08)))
        if 0 <= key <= 127:
            events.append((round(t0 * SR), 2, "on", ch, key, vel))
            events.append((round(t1 * SR), 0, "off", ch, key, 0))

    for si, (first, end, energy) in enumerate(sections):
        near = min(abs(g["energy"] - energy) for g in recipe["grooves"])
        groove = pick(groove_r, [g for g in recipe["grooves"] if abs(g["energy"] - energy) == near])
        pi = lift if energy >= 2 else main
        prog = progs[pi]
        span = recipe["bars_per_chord"]
        plan.append({"start": round(first * 240 / bpm, 3), "energy": energy, "groove": groove["name"],
                     "progression": pi})
        loud = 0.82 + 0.06 * energy
        for bar in range(first, end):
            k = (bar - first) // span
            degree = prog[k % len(prog)]
            span_start = first + k * span
            span_end = min(end, span_start + span)
            if bar == span_start:
                chords.append(chord_name(tonic, recipe["mode"], degree, recipe["voicing"]))
            for name, role in roles.items():
                if role["enter"] > energy:
                    continue
                ch, base = channels[name], base_of(tonic, role["octave"])
                text = groove["roles"].get(name, role["pattern"])
                offset = (bar - span_start) * STEPS % len(text)
                hits = [(s - offset, lv, n) for s, lv, n in pattern(text) if offset <= s < offset + STEPS]
                notes = chord_notes(base, mode, degree, recipe["voicing"])
                mr = rng(seed, "melody", name, pi, k % len(prog))
                last = notes[len(notes) // 2]
                for idx, (s16, lv, n) in enumerate(hits):
                    t0 = when(bar, s16)
                    t1 = min(t0 + n * step_s, span_end * STEPS * step_s)
                    vel = role["velocity"] * lv * loud
                    play = role["play"]
                    if play == "chord":
                        for key in notes:
                            note(t0, t1, ch, key, vel)
                    elif play == "arp":
                        seq = notes + [x + 12 for x in notes]
                        if role.get("order") == "updown":
                            seq = seq + seq[-2:0:-1]
                        at = (bar - span_start) * len(hits) + idx
                        note(t0, t1, ch, seq[at % len(seq)], vel)
                    elif play == "bass":
                        note(t0, t1, ch, fold(scale_note(base, mode, degree - 1), base - 5, base + 7), vel)
                    elif play == "melody":
                        pcs = {x % 12 for x in notes}
                        pool = [scale_note(base, mode, i) for i in range(0, 10)]
                        if s16 % 4 == 0:
                            cands = [x for x in pool if x % 12 in pcs]
                        else:
                            cands = [x for x in pool if abs(x - last) <= 4 and x != last] or pool
                        cands.sort(key=lambda x: abs(x - last))
                        last = cands[min(len(cands) - 1, int(mr.random() * min(3, len(cands))))]
                        note(t0, t1, ch, last, vel)
            if drums and drums["enter"] <= energy:
                fill = bar == end - 1 and si + 1 < len(sections)
                kit = dict(groove.get("drums") or {})
                if fill:
                    kit.update(drums.get("fill") or {})
                for piece, text in kit.items():
                    for s, lv, n in pattern(text):
                        if s < STEPS:
                            t0 = when(bar, s)
                            note(t0, t0 + 2 * step_s, 9, dmap[piece], drums["velocity"] * lv * loud)
                if bar == first and si > 0 and drums.get("crash"):
                    note(when(bar, 0), when(bar, 0) + 8 * step_s, 9, dmap[drums["crash"]], drums["velocity"])
    return events, presets, {"sections": plan, "chords": chords, "bars": bars}


# ------------------------------------------------------------------ playing and writing
def instruments(tsf):
    """music/instruments.sf3 loaded once (its samples are decoded on load, about 0.4 s) for every render of a run."""
    sf = tsf.SoundFont(str(FONT))
    sf.set_output(tsf.OutputMode.StereoInterleaved, SR, GAIN_DB)
    sf.set_max_voices(192)
    return sf


def render(sf, events, presets, seconds, ramps=()):
    """The events played on the loaded soundfont: `seconds` of 48 kHz stereo float32 bytes. `ramps` are expression
    changes [(seconds, channel, value)]."""
    sf.reset()
    sf.render(bytearray(SR // 10 * 8), False)  # the quick release of whatever the previous render left sounding
    for ch, (bank, prog) in sorted(presets.items()):
        index = sf.get_preset_index(bank, prog)
        if index < 0:
            raise Refusal(f"music/instruments.sf3 has no instrument at bank {bank} program {prog}: rebuild it with "
                          "scripts/dev/trim_soundfont.py trim")
        sf.channel_set_preset_index(ch, index)
        sf.channel_midi_control(ch, 7, 127)
    total = int(round(seconds * SR))
    todo = sorted(events + [(round(t * SR), 1, "cc", ch, 11, v) for t, ch, v in ramps], key=lambda e: (e[0], e[1], e[3], e[4]))
    buf = bytearray(total * 8)
    view = memoryview(buf)
    at = 0
    for frame, _, kind, ch, a, b in todo:
        frame = max(0, min(total, frame))
        if frame > at:
            sf.render(view[at * 8:frame * 8], False)
            at = frame
        if kind == "on":
            sf.channel_note_on(ch, a, b)
        elif kind == "off":
            sf.channel_note_off(ch, a)
        else:
            sf.channel_midi_control(ch, a, int(b))
    if total > at:
        sf.render(view[at * 8:total * 8], False)
    return bytes(buf)


def ffmpeg():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _env
    return _env.ffmpeg()


RAW = ["-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-"]


def loudness(ff, pcm, chain):
    r = subprocess.run([ff, "-hide_banner", "-nostats", *RAW, "-af", f"{chain},ebur128=framelog=quiet", "-f", "null", "-"],
                       input=pcm, capture_output=True)
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", (r.stderr or b"").decode("utf-8", "replace"))
    return float(found[-1]) if found else None


def write(pcm, chain, lufs, dst, tail=""):
    """The float stream through the recipe's chain, brought to `lufs` and limited under LIMIT, written beside `dst` as
    16-bit 48 kHz stereo WAV (bit-exact). Returns (written, dst) for place()."""
    ff = ffmpeg()
    chain = chain or "anull"
    have = loudness(ff, pcm, chain)
    gain = 0.0 if have is None or have < -70 else lufs - have
    part = dst.with_name(dst.stem + ".part.wav")
    subprocess.run([ff, "-y", "-v", "error", *RAW, "-af",
                    f"{chain},volume={gain:.2f}dB,{LIMIT}{tail}",
                    "-ar", str(SR), "-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-f", "wav", str(part)],
                   input=pcm, check=True)
    return part, dst


def place(written):
    """Every written file moved onto its name at once, after all of them are whole, so a stopped run leaves the last
    set as it was."""
    for part, dst in written:
        os.replace(part, dst)


def chain_of(recipe):
    return ",".join(step["filter"] for step in recipe["chain"])


def fx_events(book, recipe, cue, tonic, bpm):
    """One sound effect's events, presets, expression ramps and length."""
    seconds = 8 * 60 / bpm if cue == "riser" else FX_SECONDS[cue]
    events, presets, ramps = [], {}, []
    for ch, v in enumerate(recipe["fx"][cue]):
        ch = ch + (1 if ch >= 9 else 0)
        presets[ch] = (128, v["kit"]) if "kit" in v else (v.get("bank", 0), v["program"])
        keys = [book["drum_map"][n] for n in v["notes"]] if "kit" in v else [base_of(tonic, v.get("octave", 4)) + n for n in v["notes"]]
        vel = v.get("velocity", 0.9)
        on = lambda t0, t1, key, vv: events.extend([(round(t0 * SR), 2, "on", ch, key, max(0.05, min(1.0, vv))),
                                                     (round(t1 * SR), 0, "off", ch, key, 0)])
        if v["play"] == "hit":
            for key in keys:
                on(0.0, seconds * 0.7, key, vel)
        elif v["play"] == "swell":
            for key in keys:
                on(0.0, seconds, key, vel)
            ramps += [(seconds * i / 48, ch, round(12 + 115 * (i / 48) ** 2)) for i in range(49)]
        elif v["play"] == "run":
            n = len(keys)
            times = [seconds * (i / n) ** 0.55 for i in range(n)] + [seconds]
            for i, key in enumerate(keys):
                on(times[i], times[i + 1], key, vel * (0.55 + 0.45 * i / max(1, n - 1)))
    return events, presets, ramps, seconds


def render_fx(book, recipe, tonic, bpm, out, sf=None):
    """music/fx/<cue>.wav for every cue, in the recipe's voices and through its chain, written for place()."""
    sf = sf or instruments(player())
    (out / "fx").mkdir(parents=True, exist_ok=True)
    chain = chain_of(recipe) or "anull"
    written = []
    for cue in CUES:
        events, presets, ramps, seconds = fx_events(book, recipe, cue, tonic, bpm)
        if cue == "riser":
            pcm = render(sf, events, presets, seconds, ramps)
            written.append(write(pcm, chain, FX_LUFS, out / "fx" / f"{cue}.wav",
                                 tail=f",atrim=0:{seconds:.4f},afade=t=out:st={seconds - 0.012:.4f}:d=0.012"))
        else:
            pcm = render(sf, events, presets, seconds + FX_TAIL, ramps)
            written.append(write(pcm, chain, FX_LUFS, out / "fx" / f"{cue}.wav",
                                 tail=f",afade=t=out:st={seconds + FX_TAIL - 0.3:.4f}:d=0.3"))
    return written


def resolve(book, style=None, styles=(), avoid=()):
    """The recipe id, the recipe with the avoid words applied, and what decided both."""
    kept, more = split_styles(styles)
    rid = choose(book, style, kept)
    recipe, removed = constrain(book, book["recipes"][rid], list(avoid or []) + more)
    return rid, recipe, removed


def compose(style=None, styles=(), avoid=(), seconds=60.0, edges=(), hue=None, seed="", bpm=None, target_bpm=None,
            out=Path("music")):
    """The bed (out/bed.wav) and its effects (out/fx/*.wav). Returns what music.json carries about them: the recipe,
    key, tempo, beats, downbeats, sections, chords, programs, and what the brief removed."""
    book = recipes()
    sf = instruments(player())
    rid, recipe, removed = resolve(book, style, styles, avoid)
    tonic = tonic_of(hue) if hue is not None else pick(rng(seed, "key"), range(12))
    bpm = tempo(recipe, bpm, target_bpm, seed)
    events, presets, made = arrange(book, recipe, tonic, bpm, seconds, edges, seed)
    out.mkdir(parents=True, exist_ok=True)
    bed = write(render(sf, events, presets, seconds), chain_of(recipe), BED_LUFS, out / "bed.wav")
    place([bed] + render_fx(book, recipe, tonic, bpm, out, sf))
    beat = 60 / bpm
    beats = [round(i * beat, 3) for i in range(int(seconds / beat) + 1)]
    return {"recipe": rid, "key": f"{NAMES[tonic]} {recipe['mode']}", "bpm": bpm, "seconds": round(seconds, 2),
            "beats": beats, "downbeats": beats[::4], "sections": made["sections"], "chords": made["chords"],
            "programs": sorted({f"{b}:{p}" for b, p in presets.values()}), "removed": removed,
            "fx": {c: str(out / "fx" / f"{c}.wav") for c in CUES}, "fx_recipe": rid}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["make", "fx", "recipes"])
    ap.add_argument("--out", type=Path, default=Path("music"))
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--style")
    ap.add_argument("--styles", nargs="*", default=[])
    ap.add_argument("--avoid", nargs="*", default=[])
    ap.add_argument("--edges", nargs="*", type=float, default=[])
    ap.add_argument("--hue", type=float)
    ap.add_argument("--color")
    ap.add_argument("--seed", default="")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--target-bpm", type=float)
    ap.add_argument("--json-out", type=Path)
    a = ap.parse_args()
    book = recipes()
    if a.cmd == "recipes":
        for rid, r in book["recipes"].items():
            print(f"{rid}: {r['name']}, {r['tempo'][0]}-{r['tempo'][1]} bpm, {r['mode']}; words: {', '.join(book['styles'][rid])}")
        return 0
    hue = a.hue if a.hue is not None else hue_of(a.color) if a.color else None
    if a.cmd == "fx":
        rid, recipe, _ = resolve(book, a.style)
        tonic = tonic_of(hue) if hue is not None else pick(rng(a.seed, "key"), range(12))
        place(render_fx(book, recipe, tonic, tempo(recipe, a.bpm, a.target_bpm, a.seed), a.out))
        print(f"{rid}: {', '.join(str(a.out / 'fx' / f'{c}.wav') for c in CUES)}")
        return 0
    info = compose(a.style, a.styles, a.avoid, a.seconds, a.edges, hue, a.seed, a.bpm, a.target_bpm, a.out)
    dst = a.json_out or a.out.parent / "music.json"
    dst.write_text(json.dumps(dict(info, file=str(a.out / "bed.wav")), indent=2) + "\n")
    print(f"{info['recipe']} in {info['key']} at {info['bpm']:g} bpm, {info['seconds']} s: {' '.join(info['chords'])}"
          f"{'; removed ' + ', '.join(info['removed']) if info['removed'] else ''} -> {a.out / 'bed.wav'}, {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
