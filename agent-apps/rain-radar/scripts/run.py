"""Builds Rain Radar into out/rain-radar/ from the inputs file in the current folder.

Usage: cd <project> && python3 <app>/scripts/run.py

Reads rain-radar.inputs.json, checks every key, copies site/ to out/rain-radar/, writes theme.css from the chosen
theme and config.js from the inputs, and draws the sample loop (sixteen radar frames of rain moving in from the
west) into out/rain-radar/sample/. Running it twice on the same inputs gives the same folder, byte for byte.
"""

import json
import math
import random
import shutil
import struct
import sys
import zlib
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
INPUTS = "rain-radar.inputs.json"
OUT = Path("out") / "rain-radar"
KEYS = {
    "place": "the place's name as it shows at the top, 1 to 80 characters",
    "lat": "the place's latitude, a number from -85 to 85",
    "lon": "the place's longitude, a number from -180 to 180",
    "zoom": '"town" (about 250 km across) or "region" (about 1,000 km across)',
    "layers": 'a list of the layers shown at the start, from "radar", "wind", and "clouds"',
    "units": '"metric" (mm and km/h) or "imperial" (inches and mph)',
    "theme": "the look: one of the themes",
    "sample": "true to play the sample loop and never ask the live feeds, false for the live radar",
}
REQUIRED = ("place", "lat", "lon")
DEFAULTS = {"zoom": "town", "layers": ["radar", "wind"], "units": "metric", "theme": "auto", "sample": False}


def themes():
    return sorted(p.stem for p in (SITE / "themes").glob("*.css"))


def number(value, lo, hi):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and lo <= value <= hi


def check(data):
    if not isinstance(data, dict):
        return ["The inputs file must hold one object, like the one in inputs.example.json."]
    problems = []
    for k in data:
        if not k.startswith("_") and k not in KEYS:
            problems.append(f'{INPUTS} has the key "{k}", which this app does not read. The keys are: {", ".join(KEYS)}.')
    for k in REQUIRED:
        if k not in data:
            problems.append(f'{INPUTS} is missing the key "{k}": {KEYS[k]}.')
    if "place" in data and not (isinstance(data["place"], str) and 1 <= len(data["place"].strip()) <= 80):
        problems.append(f'"place" should be {KEYS["place"]}.')
    if "lat" in data and not number(data["lat"], -85, 85):
        problems.append(f'"lat" should be {KEYS["lat"]}.')
    if "lon" in data and not number(data["lon"], -180, 180):
        problems.append(f'"lon" should be {KEYS["lon"]}.')
    if "zoom" in data and data["zoom"] not in ("town", "region"):
        problems.append(f'"zoom" should be {KEYS["zoom"]}.')
    if "layers" in data and not (
        isinstance(data["layers"], list) and all(x in ("radar", "wind", "clouds") for x in data["layers"])
    ):
        problems.append(f'"layers" should be {KEYS["layers"]}.')
    if "units" in data and data["units"] not in ("metric", "imperial"):
        problems.append(f'"units" should be {KEYS["units"]}.')
    if "theme" in data and data["theme"] not in themes():
        problems.append(f'"theme" should be one of: {", ".join(themes())}.')
    if "sample" in data and not isinstance(data["sample"], bool):
        problems.append(f'"sample" should be {KEYS["sample"]}.')
    return problems


# The sample loop: a band of rain with stronger cells inside it moves in from the west and reaches the middle of
# the map (the place) 24 minutes after "now", led by a squall line along its edge; earlier showers cross the middle
# of the map and drift off to the east.

SIZE = 512
OFFSETS = [m * 60 for m in range(-120, 31, 10)]  # seconds from now, ten minutes apart
DRIFT = 0.0024  # map widths a minute, toward the east
ARRIVAL = 24  # minutes from now that the band's edge reaches the place
RAMP = [
    (0.06, (120, 210, 255, 0)),
    (0.12, (120, 210, 255, 150)),
    (0.30, (60, 160, 245, 205)),
    (0.48, (30, 95, 220, 232)),
    (0.64, (255, 222, 70, 245)),
    (0.80, (255, 150, 40, 255)),
    (0.95, (228, 52, 46, 255)),
]


def color(i):
    if i < RAMP[0][0]:
        return (0, 0, 0, 0)
    for (a, ca), (b, cb) in zip(RAMP, RAMP[1:]):
        if i <= b:
            t = (i - a) / (b - a)
            return tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))
    return RAMP[-1][1]


def noise_field(rng, width, height, cells):
    """A random field, width by height samples, from bilinear value noise over four octaves."""
    out = [[0.0] * width for _ in range(height)]
    for octave, amp in ((cells, 0.5), (cells * 2, 0.27), (cells * 4, 0.14), (cells * 8, 0.09)):
        gw = octave * width // height + 2
        lattice = [[rng.random() for _ in range(gw)] for _ in range(octave + 2)]
        for y in range(height):
            fy = y / height * octave
            j = int(fy)
            ty = fy - j
            ty = ty * ty * (3 - 2 * ty)
            row0 = lattice[j]
            row1 = lattice[j + 1]
            line = out[y]
            for x in range(width):
                fx = x / height * octave
                i = int(fx)
                tx = fx - i
                tx = tx * tx * (3 - 2 * tx)
                top = row0[i] + (row0[i + 1] - row0[i]) * tx
                bottom = row1[i] + (row1[i + 1] - row1[i]) * tx
                line[x] += (top + (bottom - top) * ty) * amp
    return out


def png(width, height, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    head = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def draw_sample(folder):
    rng = random.Random(20261021)
    shift_max = int(DRIFT * 150 * SIZE) + 2
    field = noise_field(rng, SIZE + shift_max, SIZE, 7)
    cores = [
        (rng.uniform(0.08, 0.92), rng.uniform(0.03, 0.2), rng.uniform(0.018, 0.034), rng.uniform(0.2, 0.42), rng.uniform(0, 6.3))
        for _ in range(9)
    ]
    # showers that cross the middle of the map in the first hour and are past the place well before now
    showers = [
        (rng.uniform(0.38, 0.66), rng.uniform(0.12, 0.88), rng.uniform(0.035, 0.07), rng.uniform(0.7, 1.15))
        for _ in range(9)
    ]
    files = []
    for n, offset in enumerate(OFFSETS):
        t = offset / 60
        shift = round(DRIFT * (t + 120) * SIZE)
        edge_x = 0.5 + DRIFT * (t - ARRIVAL)
        rows = []
        for py in range(SIZE):
            y = (py + 0.5) / SIZE
            line = field[py]
            ragged = (line[12] - 0.5) * 0.16
            edge = edge_x + 0.045 * math.sin((y - 0.5) * 5.5) + 0.12 * (y - 0.5) ** 2 + ragged
            row = bytearray(SIZE * 4)
            for px in range(SIZE):
                x = (px + 0.5) / SIZE
                d = edge - x
                i = 0.0
                if -0.02 < d < 0.6:
                    nz = line[px + shift_max - shift]
                    rise = min(1.0, max(0.0, (d + 0.02 * (nz - 0.5)) / 0.02))
                    tail = math.exp(-max(0.0, d - 0.1) ** 2 / 0.028)
                    body = max(0.0, min(1.0, (nz - 0.28) / 0.42))
                    i = rise * tail * (0.06 + 0.5 * body * body)
                    squall = (d - 0.025) / 0.018
                    if squall * squall < 9:
                        i += 0.45 * math.exp(-squall * squall) * (0.6 + 0.6 * nz) * rise
                    for cy, back, r, amp, phase in cores:
                        dx = d - back
                        dy = y - cy
                        q = (dx * dx + dy * dy * 0.45) / (r * r)
                        if q < 9:
                            i += amp * (0.65 + 0.35 * math.sin(t / 35 + phase)) * math.exp(-q) * rise * (0.5 + body)
                for sx, sy, r, amp in showers:
                    cx = sx + DRIFT * (t + 120)
                    dx = x - cx
                    dy = y - sy
                    q = (dx * dx + dy * dy) / (r * r)
                    if q < 9:
                        fade = max(0.0, 1 - (t + 120) / 170)
                        i += amp * fade * math.exp(-q) * max(0.0, line[px + shift_max - shift] * 1.6 - 0.45)
                row[px * 4 : px * 4 + 4] = bytes(color(min(1.0, i)))
            rows.append(row)
        name = f"frame-{n:02d}.png"
        (folder / name).write_bytes(png(SIZE, SIZE, rows))
        files.append(name)
    (folder / "frames.json").write_text(json.dumps({"offsets": OFFSETS, "files": files}) + "\n", encoding="utf-8")
    return len(files)


def main():
    path = Path(INPUTS)
    if not path.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        print(f"{INPUTS} is not valid JSON (line {getattr(err, 'lineno', '?')}). Check the commas and quotes.")
        return 2
    problems = check(data)
    if problems:
        print("\n".join(problems))
        return 2

    config = dict(DEFAULTS)
    config.update({k: (v.strip() if isinstance(v, str) else v) for k, v in data.items() if not k.startswith("_")})

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, OUT)
    shutil.copyfile(APP / "assets" / "icon.svg", OUT / "icon.svg")
    shutil.copyfile(SITE / "themes" / f"{config['theme']}.css", OUT / "theme.css")
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, sort_keys=True)};\n", encoding="utf-8")
    sample = OUT / "sample"
    sample.mkdir()
    draw_sample(sample)

    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote out/rain-radar/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/rain-radar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
