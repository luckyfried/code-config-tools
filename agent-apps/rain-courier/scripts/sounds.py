"""Renders Rain Courier's sounds to WAV files in site/audio/, offline and faster than real time.

Standard library only. The same run always writes the same bytes.

    python3 scripts/sounds.py

rotor.wav    a detuned pair of saws chopped at the blade rate; it loops, and the page runs it through a lowpass
             that follows the throttle
rain.wav     rain hiss, a loop
thunder.wav  a far rumble with a crack at the front
chime.wav    the delivery chime, two bell notes
pickup.wav   the package hooked: a short rising blip
crash.wav    the crunch of a drone hitting a wall
"""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path(__file__).resolve().parents[1] / "site" / "audio"


def write(name, samples):
    peak = max(1e-9, max(abs(s) for s in samples))
    gain = 0.89 / peak
    frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * gain)) * 32767)) for s in samples)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)


def saw(phase):
    return 2.0 * (phase - math.floor(phase + 0.5))


def lowpass(samples, cutoff):
    a = 1.0 - math.exp(-2.0 * math.pi * cutoff / RATE)
    y = 0.0
    out = []
    for s in samples:
        y += a * (s - y)
        out.append(y)
    return out


def highpass(samples, cutoff):
    low = lowpass(samples, cutoff)
    return [s - l for s, l in zip(samples, low)]


def rotor():
    # One second, whole cycles of every frequency, so the loop has no seam.
    n = RATE
    out = []
    for i in range(n):
        t = i / RATE
        a = saw(t * 140.0) + saw(t * 143.0)
        b = 0.5 * saw(t * 281.0)
        chop = 0.62 + 0.38 * (0.5 + 0.5 * math.cos(2 * math.pi * 47.0 * t)) ** 3
        out.append((a + b) * chop)
    return lowpass(lowpass(out, 2600), 2600)


def rain():
    rng = random.Random(7)
    n = RATE * 4
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    hiss = highpass(lowpass(noise, 5200), 500)
    # Scattered drops on top of the hiss.
    for _ in range(900):
        at = rng.randrange(n - 400)
        amp = rng.uniform(0.2, 0.9)
        freq = rng.uniform(1800, 4200)
        for k in range(300):
            hiss[at + k] += amp * math.exp(-k / 40.0) * math.sin(2 * math.pi * freq * k / RATE) * 0.5
    # Crossfade the tail into the head so it loops.
    fade = RATE // 2
    for k in range(fade):
        w = k / fade
        hiss[k] = hiss[k] * w + hiss[n - fade + k] * (1 - w)
    return hiss[: n - fade]


def thunder():
    rng = random.Random(11)
    n = int(RATE * 5.5)
    brown = []
    y = 0.0
    for _ in range(n):
        y = (y + rng.uniform(-1, 1) * 0.08) * 0.995
        brown.append(y)
    out = []
    for i in range(n):
        t = i / RATE
        env = (1 - math.exp(-t * 9)) * math.exp(-t * 0.75) * (0.75 + 0.25 * math.sin(t * 5.3) * math.sin(t * 2.1))
        crack = math.exp(-t * 14) * rng.uniform(-1, 1) * 0.6 if t < 0.4 else 0.0
        out.append(brown[i] * env * 3.0 + crack)
    return lowpass(out, 900)


def bell(freq, t):
    partials = [(1.0, 1.0, 1.4), (2.76, 0.45, 2.6), (5.4, 0.22, 4.0), (8.93, 0.1, 6.0)]
    return sum(a * math.exp(-t * d) * math.sin(2 * math.pi * freq * r * t) for r, a, d in partials)


def chime():
    n = int(RATE * 1.8)
    out = []
    for i in range(n):
        t = i / RATE
        s = bell(1318.5, t) * 0.8
        if t > 0.11:
            s += bell(1975.5, t - 0.11)
        out.append(s * min(1.0, t * 400))
    return out


def pickup():
    n = int(RATE * 0.4)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = 520 + 900 * min(1.0, t / 0.18)
        phase += f / RATE
        env = min(1.0, t * 300) * math.exp(-t * 7)
        out.append((math.sin(2 * math.pi * phase) + 0.3 * math.sin(4 * math.pi * phase)) * env)
    return out


def crash():
    rng = random.Random(3)
    n = int(RATE * 0.9)
    out = []
    for i in range(n):
        t = i / RATE
        thump = math.sin(2 * math.pi * (70 - 30 * t) * t) * math.exp(-t * 9) * 1.2
        grit = rng.uniform(-1, 1) * math.exp(-t * 11) * (0.6 + 0.4 * (rng.random() < 0.3))
        clank = (math.sin(2 * math.pi * 870 * t) + 0.7 * math.sin(2 * math.pi * 1310 * t)) * math.exp(-t * 16) * 0.35
        out.append(thump + grit + clank)
    return lowpass(out, 4200)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write("rotor.wav", rotor())
    write("rain.wav", rain())
    write("thunder.wav", thunder())
    write("chime.wav", chime())
    write("pickup.wav", pickup())
    write("crash.wav", crash())
    print(f"Wrote six sounds to {OUT}")


if __name__ == "__main__":
    main()
