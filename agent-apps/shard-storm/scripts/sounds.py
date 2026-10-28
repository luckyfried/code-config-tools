"""Renders Shard Storm's sounds offline into site/audio/ as WAV files.

Every sound is computed sample by sample, faster than real time, and written
once; the page only plays the files. Standard library only, seeded, so two
renders give byte-identical files.

    python3 scripts/sounds.py
"""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / "site" / "audio"
TAU = math.tau


def write(name, samples):
    peak = max(1e-9, max(abs(s) for s in samples))
    gain = 0.89 / peak
    frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * gain)) * 32767)) for s in samples)
    with wave.open(str(OUT / name), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(RATE)
        file.writeframes(frames)


def lowpass(samples, cutoff):
    """One-pole low-pass; cutoff is a number or a function of the sample index."""
    out = []
    y = 0.0
    for i, x in enumerate(samples):
        fc = cutoff(i) if callable(cutoff) else cutoff
        a = 1.0 - math.exp(-TAU * fc / RATE)
        y += a * (x - y)
        out.append(y)
    return out


def saw(phase):
    return 2.0 * (phase - math.floor(phase + 0.5))


def drone():
    """A four-second loop: every partial completes whole cycles, so the seam is silent."""
    seconds = 4.0
    n = int(RATE * seconds)
    voices = [(55.0, 0.5), (55.25, 0.45), (82.5, 0.28), (110.0, 0.16), (164.75, 0.07)]
    raw = []
    for i in range(n):
        t = i / RATE
        s = 0.0
        for freq, amp in voices:
            s += amp * saw(freq * t)
        swell = 0.75 + 0.25 * math.sin(TAU * 0.25 * t)
        raw.append(s * swell)
    # Filter twice around the loop so the filter state at the seam matches the start.
    filtered = lowpass(raw + raw, lambda i: 420 + 260 * math.sin(TAU * 0.25 * (i % n) / RATE))
    return filtered[n:]


def graze():
    n = int(RATE * 0.11)
    out = []
    for i in range(n):
        t = i / RATE
        freq = 1480 * (1 + 0.35 * math.exp(-t * 60))
        env = math.exp(-t * 34) * min(1.0, t * 900)
        s = math.sin(TAU * freq * t) + 0.35 * math.sin(TAU * freq * 2.01 * t) * math.exp(-t * 80)
        out.append(s * env)
    return out


def wave_hit():
    rng = random.Random(7)
    n = int(RATE * 1.4)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    noise = lowpass(noise, lambda i: 6000 * math.exp(-i / RATE * 9) + 200)
    out = []
    phase = 0.0
    chord = [220.0, 277.18, 329.63, 440.0, 554.37]
    for i in range(n):
        t = i / RATE
        freq = 48 + 120 * math.exp(-t * 18)
        phase += freq / RATE
        thump = math.sin(TAU * phase) * math.exp(-t * 7)
        shimmer = sum(math.sin(TAU * f * t + k) for k, f in enumerate(chord)) / len(chord)
        shimmer *= 0.32 * math.exp(-t * 2.6) * min(1.0, t * 40)
        out.append(thump * 0.9 + noise[i] * 0.55 * math.exp(-t * 10) + shimmer)
    return out


def death():
    rng = random.Random(11)
    n = int(RATE * 2.6)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    swept = lowpass(lowpass(noise, lambda i: 2400 * math.exp(-i / RATE * 1.7) + 60), lambda i: 3000 * math.exp(-i / RATE * 1.4) + 80)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        freq = 30 + 70 * math.exp(-t * 2.2)
        phase += freq / RATE
        sub = math.sin(TAU * phase) * math.exp(-t * 1.3)
        crack = rng.uniform(-1, 1) * math.exp(-t * 40)
        env = min(1.0, t * 300) * (1 - t / 2.6) ** 1.5
        out.append((swept[i] * 3.2 + sub * 0.8 + crack * 0.6) * env)
    return out


def start():
    rng = random.Random(3)
    n = int(RATE * 0.7)
    noise = lowpass([rng.uniform(-1, 1) for _ in range(n)], lambda i: 300 + 5200 * (i / n) ** 2)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        freq = 220 * 2 ** (t / 0.7 * 2)
        phase += freq / RATE
        env = math.sin(math.pi * min(1.0, t / 0.7)) ** 1.2
        out.append((noise[i] * 1.6 + 0.4 * math.sin(TAU * phase)) * env)
    return out


def clear():
    n = int(RATE * 1.8)
    notes = [523.25, 659.25, 783.99, 1046.5, 1318.5]
    out = [0.0] * n
    for k, f in enumerate(notes):
        begin = int(RATE * 0.07 * k)
        for i in range(begin, n):
            t = (i - begin) / RATE
            env = math.exp(-t * 3.2) * min(1.0, t * 400)
            out[i] += (math.sin(TAU * f * t) + 0.3 * math.sin(TAU * f * 2 * t)) * env * 0.5
    return out


def tick():
    n = int(RATE * 0.05)
    return [math.sin(TAU * 2200 * i / RATE) * math.exp(-i / RATE * 120) for i in range(n)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, render in [("drone.wav", drone), ("graze.wav", graze), ("wave.wav", wave_hit), ("death.wav", death),
                         ("start.wav", start), ("clear.wav", clear), ("tick.wav", tick)]:
        write(name, render())
        print(f"Wrote site/audio/{name}")


if __name__ == "__main__":
    main()
