"""Renders the dive's sounds to WAV files in site/audio/, offline and faster than real time.

python3 scripts/make_sounds.py

Standard library only. Every sound is synthesized here from sines, noise, and filters; the page plays the files and
only changes their gain and rate. A fixed random seed makes two runs write the same bytes.
"""

import math
import random
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "site" / "audio"
TAU = math.pi * 2


def write(name, samples, rate):
    peak = max(1e-9, max(abs(s) for s in samples))
    gain = 0.89 / peak
    frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * gain)) * 32767)) for s in samples)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    print(f"{name}: {len(samples) / rate:.2f} s")


class Biquad:
    """RBJ biquad: kind is 'lowpass', 'highpass', or 'bandpass'."""

    def __init__(self, kind, freq, q, rate):
        self.kind, self.q, self.rate = kind, q, rate
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0
        self.set(freq)

    def set(self, freq):
        w = TAU * freq / self.rate
        alpha = math.sin(w) / (2 * self.q)
        c = math.cos(w)
        if self.kind == "lowpass":
            b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
        elif self.kind == "highpass":
            b0, b1, b2 = (1 + c) / 2, -(1 + c), (1 + c) / 2
        else:
            b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1 + alpha, -2 * c, 1 - alpha
        self.b0, self.b1, self.b2, self.a1, self.a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    def __call__(self, x):
        y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 - self.a1 * self.y1 - self.a2 * self.y2
        self.x2, self.x1, self.y2, self.y1 = self.x1, x, self.y1, y
        return y


def reverb(samples, rate, mix=0.35, size=1.0):
    """A small Schroeder reverb: four combs into two allpasses."""
    combs = [int(rate * t * size) for t in (0.0297, 0.0371, 0.0411, 0.0437)]
    feedback = [0.84, 0.82, 0.8, 0.78]
    tail = int(rate * 1.5 * size)
    src = samples + [0.0] * tail
    wet = [0.0] * len(src)
    for delay, fb in zip(combs, feedback):
        buf = [0.0] * delay
        i = 0
        lp = 0.0
        for n, x in enumerate(src):
            y = buf[i]
            lp = y * 0.7 + lp * 0.3
            buf[i] = x + lp * fb
            i = (i + 1) % delay
            wet[n] += y
    for delay in (int(rate * 0.005), int(rate * 0.0017)):
        buf = [0.0] * delay
        i = 0
        for n, x in enumerate(wet):
            y = buf[i]
            buf[i] = x + y * 0.5
            i = (i + 1) % delay
            wet[n] = y - x * 0.5
    return [d * (1 - mix) + w * mix * 0.25 for d, w in zip(src, wet)]


def loop_crossfade(samples, rate, fade_s):
    """Folds the tail over the head so the file loops without a click."""
    f = int(rate * fade_s)
    body = samples[: len(samples) - f]
    for i in range(f):
        k = i / f
        body[i] = body[i] * k + samples[len(samples) - f + i] * (1 - k)
    return body


def motor(rng):
    rate = 22050
    n = int(rate * 2.25)
    lp = Biquad("lowpass", 380, 0.9, rate)
    out = []
    for i in range(n):
        t = i / rate
        wob = 1 + 0.04 * math.sin(TAU * 7 * t)
        tone = (math.sin(TAU * 55 * t) * 0.55 + math.sin(TAU * 110 * t) * 0.3 + math.sin(TAU * 165 * t + 0.4) * 0.18
                + math.sin(TAU * 330 * t) * 0.05) * wob
        whine = math.sin(TAU * 880 * t + 2 * math.sin(TAU * 3 * t)) * 0.02
        out.append(tone + lp(rng.uniform(-1, 1)) * 0.6 + whine)
    return loop_crossfade(out, rate, 0.25), rate


def ambience(rng):
    rate = 22050
    n = int(rate * 9.0)
    lp = Biquad("lowpass", 160, 0.7, rate)
    lp2 = Biquad("lowpass", 900, 0.5, rate)
    brown = 0.0
    out = []
    for i in range(n):
        t = i / rate
        brown = (brown + rng.uniform(-1, 1) * 0.02) * 0.998
        swell = 0.65 + 0.35 * math.sin(TAU * t / 9.0 * 2 + 1.0) * math.sin(TAU * t / 9.0 * 3)
        hiss = lp2(rng.uniform(-1, 1)) * 0.04
        out.append(lp(brown) * 6 * swell + hiss + math.sin(TAU * 31 * t) * 0.03)
    return loop_crossfade(out, rate, 1.0), rate


def creak(rng):
    rate = 44100
    dur = 1.7
    n = int(rate * dur)
    bp1 = Biquad("bandpass", 420, 9, rate)
    bp2 = Biquad("bandpass", 980, 7, rate)
    bp3 = Biquad("bandpass", 190, 4, rate)
    phase = 0.0
    jerk = 0.0
    out = []
    for i in range(n):
        t = i / rate
        f = 74 - 22 * (t / dur) + 3 * math.sin(TAU * 1.3 * t)
        if rng.random() < 0.0009:
            jerk = 1.0
        jerk *= 0.9993
        phase += f / rate
        saw = 2 * (phase % 1.0) - 1
        env = math.sin(math.pi * min(1.0, t / dur)) ** 0.6
        x = saw * (0.4 + 0.6 * jerk) * env
        out.append(bp1(x) * 1.0 + bp2(x) * 0.6 + bp3(x) * 0.8)
    return reverb(out, rate, 0.45, 1.3), rate


def ping(rng):
    rate = 44100
    n = int(rate * 1.2)
    out = [0.0] * n
    for i in range(n):
        t = i / rate
        env = min(1.0, t / 0.004) * math.exp(-t / 0.22)
        out[i] = (math.sin(TAU * 1240 * t) + 0.18 * math.sin(TAU * 2480 * t)) * env
    for delay, gain in ((0.38, 0.28), (0.76, 0.12)):
        lp = Biquad("lowpass", 1800, 0.7, rate)
        d = int(rate * delay)
        for i in range(n):
            j = i + d
            if j < n:
                out[j] += lp(out[i]) * gain
    return reverb(out, rate, 0.5, 1.6), rate


def shutter(rng):
    rate = 44100
    n = int(rate * 0.32)
    hp = Biquad("highpass", 2500, 0.8, rate)
    bp = Biquad("bandpass", 1600, 3, rate)
    out = []
    for i in range(n):
        t = i / rate
        click1 = math.exp(-t / 0.004) if t < 0.03 else 0.0
        t2 = t - 0.13
        click2 = math.exp(-t2 / 0.005) if 0 <= t2 < 0.04 else 0.0
        whirr = 0.18 * math.sin(TAU * 210 * t) * (1 if 0.02 < t < 0.12 else 0) * math.exp(-(t - 0.02) / 0.08)
        noise = rng.uniform(-1, 1)
        out.append(hp(noise) * (click1 + click2 * 0.8) + bp(noise) * (click1 + click2) * 0.6 + whirr
                   + math.sin(TAU * 2200 * t) * click1 * 0.3)
    return out, rate


def whale(rng):
    rate = 44100
    dur = 4.6
    n = int(rate * dur)
    form1 = Biquad("bandpass", 600, 5, rate)
    form2 = Biquad("bandpass", 1300, 6, rate)
    phase = 0.0
    out = []
    for i in range(n):
        t = i / rate
        u = t / dur
        if u < 0.35:
            f = 150 + (390 - 150) * (u / 0.35) ** 1.4
        elif u < 0.6:
            f = 390 - 40 * (u - 0.35) / 0.25
        else:
            f = 350 - 150 * ((u - 0.6) / 0.4) ** 0.8
        f *= 1 + 0.012 * math.sin(TAU * 5.2 * t)
        phase += f / rate
        x = math.sin(TAU * phase) + 0.45 * math.sin(TAU * phase * 2) + 0.2 * math.sin(TAU * phase * 3)
        env = min(1.0, t / 0.6) * min(1.0, (dur - t) / 1.2)
        if i % 256 == 0:
            form1.set(520 + 380 * math.sin(math.pi * u))
            form2.set(1150 + 300 * u)
        out.append((x * 0.35 + form1(x) * 1.2 + form2(x) * 0.5) * env)
    return reverb(out, rate, 0.6, 2.2), rate


def alarm(rng):
    rate = 44100
    n = int(rate * 0.62)
    out = []
    for i in range(n):
        t = i / rate
        f = 880 if t < 0.28 else 660
        local = t if t < 0.28 else t - 0.3
        env = min(1.0, local / 0.01) * math.exp(-local / 0.12) if local >= 0 else 0.0
        out.append((math.sin(TAU * f * t) + 0.3 * math.sin(TAU * f * 3 * t)) * env)
    return out, rate


def chime(rng):
    rate = 44100
    n = int(rate * 1.4)
    out = []
    partials = ((1046.5, 1.0, 0.5), (1568.0, 0.6, 0.4), (2093.0, 0.35, 0.3), (2637.0, 0.2, 0.25))
    for i in range(n):
        t = i / rate
        s = 0.0
        for f, a, d in partials:
            s += a * math.sin(TAU * f * t) * math.exp(-t / d)
        out.append(s * min(1.0, t / 0.003))
    return reverb(out, rate, 0.35, 1.1), rate


def heartbeat(rng):
    rate = 22050
    n = int(rate * 1.0)
    out = []
    for i in range(n):
        t = i / rate
        s = 0.0
        for start, amp in ((0.0, 1.0), (0.22, 0.7)):
            u = t - start
            if u >= 0:
                s += amp * math.sin(TAU * (48 + 30 * math.exp(-u / 0.03)) * u) * math.exp(-u / 0.07)
        out.append(s)
    return out, rate


def blow(rng):
    rate = 44100
    dur = 2.4
    n = int(rate * dur)
    bp = Biquad("bandpass", 500, 1.2, rate)
    lp = Biquad("lowpass", 1400, 0.7, rate)
    bubbles = []
    for _ in range(70):
        start = rng.uniform(0.05, dur - 0.2)
        bubbles.append((start, rng.uniform(300, 1100), rng.uniform(0.02, 0.06), rng.uniform(0.2, 1.0)))
    out = [0.0] * n
    for i in range(n):
        t = i / rate
        env = min(1.0, t / 0.08) * math.exp(-t / 1.1)
        out[i] = lp(bp(rng.uniform(-1, 1))) * env * 2.2
    for start, f0, life, amp in bubbles:
        s0 = int(start * rate)
        for k in range(int(life * rate * 3)):
            j = s0 + k
            if j >= n:
                break
            u = k / rate
            f = f0 * (1 + u / life * 0.8)
            out[j] += amp * 0.25 * math.sin(TAU * f * u) * math.exp(-u / life)
    return reverb(out, rate, 0.3, 1.0), rate


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("motor.wav", motor), ("ambience.wav", ambience), ("creak.wav", creak), ("ping.wav", ping),
                     ("shutter.wav", shutter), ("whale.wav", whale), ("alarm.wav", alarm), ("chime.wav", chime),
                     ("heartbeat.wav", heartbeat), ("blow.wav", blow)):
        samples, rate = fn(random.Random(name))
        write(name, samples, rate)


if __name__ == "__main__":
    main()
