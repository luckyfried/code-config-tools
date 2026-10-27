"""Writes the table's four sounds into site/sound/ as WAV files, sample by sample.

The card snap, the slide across the felt, the stock flip, and the cascade whoosh are
synthesized here from filtered noise and short tones, faster than real time, with a fixed
seed, so every run writes the same bytes. Standard library only:

    python3 scripts/make_sounds.py
"""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parents[1] / "site" / "sound"


class Biquad:
    """An RBJ cookbook filter: "lowpass", "highpass", or "bandpass"."""

    def __init__(self, kind, freq, q=0.707):
        self.kind = kind
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0
        self.set(freq, q)

    def set(self, freq, q):
        w = 2 * math.pi * min(freq, RATE * 0.45) / RATE
        alpha = math.sin(w) / (2 * q)
        cos = math.cos(w)
        if self.kind == "lowpass":
            b0, b1, b2 = (1 - cos) / 2, 1 - cos, (1 - cos) / 2
        elif self.kind == "highpass":
            b0, b1, b2 = (1 + cos) / 2, -(1 + cos), (1 + cos) / 2
        else:
            b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1 + alpha, -2 * cos, 1 - alpha
        self.b0, self.b1, self.b2 = b0 / a0, b1 / a0, b2 / a0
        self.a1, self.a2 = a1 / a0, a2 / a0

    def __call__(self, x):
        y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 - self.a1 * self.y1 - self.a2 * self.y2
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y


def write(name, samples, peak=0.9):
    top = max(1e-9, max(abs(s) for s in samples))
    gain = peak / top
    # A 3 ms fade at each end so nothing clicks where the sample starts or stops.
    fade = int(RATE * 0.003)
    data = bytearray()
    for i, s in enumerate(samples):
        edge = min(1.0, i / fade if fade else 1.0, (len(samples) - 1 - i) / fade if fade else 1.0)
        v = max(-1.0, min(1.0, s * gain * edge))
        data += struct.pack("<h", int(round(v * 32767)))
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(data))


def snap(rng):
    """A card landing on a pile: a papery tick with a little body under it."""
    n = int(RATE * 0.12)
    band = Biquad("bandpass", 3200, 0.9)
    body = Biquad("lowpass", 900, 0.8)
    out = []
    for i in range(n):
        t = i / RATE
        noise = rng.uniform(-1, 1)
        tick = band(noise) * math.exp(-t / 0.011)
        second = band(noise) * 0.35 * math.exp(-max(0.0, t - 0.007) / 0.008) if t > 0.007 else 0.0
        thump = body(noise) * 0.9 * math.exp(-t / 0.03) + math.sin(2 * math.pi * 170 * t) * 0.25 * math.exp(-t / 0.025)
        out.append(tick * 1.4 + second + thump)
    return out


def slide(rng):
    """A card pushed across the felt: soft, broad noise that swells and drops away."""
    n = int(RATE * 0.24)
    lo = Biquad("lowpass", 2600, 0.6)
    hi = Biquad("highpass", 380, 0.6)
    out = []
    grain = 0.0
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.03) * math.exp(-max(0.0, t - 0.05) / 0.07)
        grain = grain * 0.97 + rng.uniform(-1, 1) * 0.03
        out.append(hi(lo(rng.uniform(-1, 1))) * env * (0.8 + grain * 6))
    return out


def flip(rng):
    """The stock card turned over: a quick rising flick, then the tick of it landing."""
    n = int(RATE * 0.16)
    band = Biquad("bandpass", 1200, 1.4)
    tick = Biquad("bandpass", 3800, 1.0)
    out = []
    for i in range(n):
        t = i / RATE
        band.set(1200 + 3200 * min(1.0, t / 0.09), 1.4)
        whoosh = band(rng.uniform(-1, 1)) * math.sin(math.pi * min(1.0, t / 0.09)) * 0.9
        land = tick(rng.uniform(-1, 1)) * math.exp(-max(0.0, t - 0.095) / 0.012) * 1.5 if t > 0.095 else 0.0
        out.append(whoosh + land)
    return out


def whoosh(rng):
    """A card leaving the foundation in the cascade: air that rises and falls."""
    n = int(RATE * 0.7)
    band = Biquad("bandpass", 300, 1.1)
    out = []
    for i in range(n):
        t = i / RATE
        x = t / 0.7
        band.set(300 + 1300 * math.sin(math.pi * x) ** 1.5, 1.1)
        env = math.sin(math.pi * x) ** 2
        out.append(band(rng.uniform(-1, 1)) * env)
    return out


def main():
    rng = random.Random(52)
    write("snap.wav", snap(rng))
    write("slide.wav", slide(rng), peak=0.6)
    write("flip.wav", flip(rng), peak=0.75)
    write("whoosh.wav", whoosh(rng), peak=0.55)
    print(f"Wrote 4 sounds to {OUT}")


if __name__ == "__main__":
    main()
