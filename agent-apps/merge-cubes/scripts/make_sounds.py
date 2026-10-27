"""Renders Merge Cubes' sounds into site/sound/ as WAV files, offline and faster than real time.

    python3 scripts/make_sounds.py

The page plays these files and never synthesizes in real time: mallet.wav is one struck note (C5) that the page
pitches up a pentatonic scale for each merge, thud.wav is a swipe that moves nothing, drop.wav is a new cube landing,
and win.wav is the 2048 moment. Standard library only; the same script always writes the same bytes.
"""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / "site" / "sound"


def mallet(freq, seconds, bright=1.0):
    """A struck bar: a fundamental with the bar's inharmonic overtones, each dying faster than the last, and a glassy
    octave that rings longest, so a merge sounds like a lit cube being tapped."""
    partials = (
        (1.0, 1.0, 0.62),
        (2.0, 0.16, 0.9),
        (3.93, 0.34 * bright, 0.15),
        (9.2, 0.12 * bright, 0.04),
    )
    n = int(seconds * RATE)
    out = [0.0] * n
    for ratio, amp, tau in partials:
        f = freq * ratio
        if f > RATE / 2.2:
            continue
        w = 2 * math.pi * f / RATE
        for i in range(n):
            t = i / RATE
            attack = min(1.0, t / 0.0015)
            out[i] += amp * attack * math.exp(-t / tau) * math.sin(w * i)
    rng = random.Random(7)
    click = int(0.006 * RATE)
    for i in range(click):
        out[i] += 0.18 * bright * (1 - i / click) ** 3 * (rng.random() * 2 - 1)
    return out


def thud(seconds=0.34):
    n = int(seconds * RATE)
    out = [0.0] * n
    phase = 0.0
    rng = random.Random(11)
    low = 0.0
    for i in range(n):
        t = i / RATE
        f = 46 + 50 * math.exp(-t / 0.05)
        phase += 2 * math.pi * f / RATE
        body = math.sin(phase) * math.exp(-t / 0.09)
        low += 0.06 * ((rng.random() * 2 - 1) - low)
        out[i] = 0.9 * body + 0.5 * low * math.exp(-t / 0.03)
    return out


def drop(seconds=0.16):
    n = int(seconds * RATE)
    out = [0.0] * n
    for ratio, amp, tau in ((1.0, 1.0, 0.035), (2.7, 0.35, 0.015), (5.1, 0.15, 0.008)):
        w = 2 * math.pi * 196 * ratio / RATE
        for i in range(n):
            t = i / RATE
            out[i] += amp * math.exp(-t / tau) * math.sin(w * i)
    return out


def win(seconds=3.2):
    n = int(seconds * RATE)
    out = [0.0] * n
    c5 = 523.25
    steps = (0, 4, 7, 9, 12, 16, 19, 24)
    for k, semis in enumerate(steps):
        note = mallet(c5 * 2 ** (semis / 12), 2.2, bright=0.8)
        start = int(k * 0.085 * RATE)
        gain = 0.55 + 0.05 * k
        for i, v in enumerate(note):
            if start + i < n:
                out[start + i] += gain * v
    # A held fifth under the run, swelling in and out, so the moment lands on a chord.
    for semis, amp in ((0, 0.22), (7, 0.16), (12, 0.12)):
        w = 2 * math.pi * (c5 / 2) * 2 ** (semis / 12) / RATE
        for i in range(n):
            t = i / RATE
            env = min(1.0, t / 0.5) * math.exp(-max(0.0, t - 0.6) / 1.1)
            out[i] += amp * env * (math.sin(w * i) + 0.25 * math.sin(2 * w * i + 0.3))
    return out


def write(name, samples, peak=0.89):
    top = max(abs(v) for v in samples) or 1.0
    fade = int(0.01 * RATE)
    data = bytearray()
    for i, v in enumerate(samples):
        tail = min(1.0, (len(samples) - i) / fade)
        data += struct.pack("<h", int(round(max(-1.0, min(1.0, v / top * peak * tail)) * 32767)))
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(bytes(data))


def main():
    write("mallet.wav", mallet(523.25, 1.6))
    write("thud.wav", thud(), peak=0.8)
    write("drop.wav", drop(), peak=0.7)
    write("win.wav", win())
    print(f"Wrote mallet.wav, thud.wav, drop.wav, and win.wav into {OUT}")


if __name__ == "__main__":
    main()
