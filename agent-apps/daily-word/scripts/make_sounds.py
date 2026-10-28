"""Writes the game's sounds and its grain texture, offline and faster than real time.

    python3 scripts/make_sounds.py

Every sample is computed here and written as a 16-bit mono WAV under site/sound/; the grain is a small
gray-and-alpha PNG under site/img/. Standard library only, seeded, so two runs write the same bytes.
The page plays these files; it never synthesizes sound itself.
"""

import math
import random
import struct
import wave
import zlib
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
RATE = 44100


def write_wav(name, samples):
    path = SITE / "sound" / f"{name}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = 0.89 / peak
    frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * scale)) * 32767)) for s in samples)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(frames)


def lowpass(samples, cutoff):
    alpha = 1 - math.exp(-2 * math.pi * cutoff / RATE)
    out, y = [], 0.0
    for s in samples:
        y += alpha * (s - y)
        out.append(y)
    return out


def thunk(rng):
    """A soft wooden tile landing on felt: a falling body tone, a muffled knock, a short tail."""
    n = int(RATE * 0.22)
    noise = lowpass([rng.uniform(-1, 1) for _ in range(n)], 1400)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        freq = 118 + 160 * math.exp(-t * 55)
        phase += 2 * math.pi * freq / RATE
        body = math.sin(phase) * math.exp(-t * 26)
        knock = math.sin(2 * math.pi * 410 * t) * math.exp(-t * 90) * 0.35
        click = noise[i] * math.exp(-t * 160) * 0.8
        attack = min(1.0, t / 0.0015)
        out.append((body + knock + click) * attack)
    return out


def key(rng):
    """A glass chip tapped: a bright short tick with a soft low thump under it."""
    n = int(RATE * 0.07)
    out = []
    for i in range(n):
        t = i / RATE
        tick = math.sin(2 * math.pi * 2350 * t) * math.exp(-t * 140) * 0.5
        ring = math.sin(2 * math.pi * 3620 * t) * math.exp(-t * 220) * 0.25
        thump = math.sin(2 * math.pi * 180 * t) * math.exp(-t * 70) * 0.6
        air = rng.uniform(-1, 1) * math.exp(-t * 400) * 0.25
        out.append((tick + ring + thump + air) * min(1.0, t / 0.0008))
    return out


def buzz(rng):
    """A word the game will not take: two low muted knocks, the second lower."""
    n = int(RATE * 0.3)
    out = [0.0] * n
    for start, freq in ((0.0, 150), (0.12, 112)):
        s0 = int(start * RATE)
        for i in range(s0, n):
            t = (i - s0) / RATE
            v = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * freq * 2.01 * t)
            out[i] += v * math.exp(-t * 30) * min(1.0, t / 0.002)
    return lowpass(out, 900)


def chime(rng):
    """The win: four bell notes rising, each with slightly inharmonic partials and a long shimmer."""
    n = int(RATE * 1.8)
    out = [0.0] * n
    notes = (523.25, 659.25, 783.99, 1046.5)
    for k, f0 in enumerate(notes):
        s0 = int(k * 0.11 * RATE)
        for i in range(s0, n):
            t = (i - s0) / RATE
            env = math.exp(-t * 3.2) * min(1.0, t / 0.004)
            v = (
                math.sin(2 * math.pi * f0 * t)
                + 0.42 * math.sin(2 * math.pi * f0 * 2.76 * t) * math.exp(-t * 5)
                + 0.22 * math.sin(2 * math.pi * f0 * 5.4 * t) * math.exp(-t * 9)
                + 0.12 * math.sin(2 * math.pi * f0 * 0.5 * t)
            )
            out[i] += v * env * (0.9 if k < 3 else 1.05)
    return out


def write_grain():
    """A 128 px tile of fine grain: each pixel black or white at a low random alpha."""
    size = 128
    rng = random.Random(7)
    rows = []
    for _ in range(size):
        row = bytearray([0])
        for _ in range(size):
            row += bytes((255 if rng.random() < 0.5 else 0, int(rng.random() ** 1.6 * 70)))
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 4, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    path = SITE / "img" / "grain.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def main():
    rng = random.Random(42)
    write_wav("thunk", thunk(rng))
    write_wav("key", key(rng))
    write_wav("buzz", buzz(rng))
    write_wav("chime", chime(rng))
    write_grain()
    print(f"Wrote 4 sounds to {SITE / 'sound'} and the grain to {SITE / 'img'}.")


if __name__ == "__main__":
    main()
