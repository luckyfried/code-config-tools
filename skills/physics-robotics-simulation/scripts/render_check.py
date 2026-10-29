#!/usr/bin/env python3
"""Render a bundle offscreen with MuJoCo's own renderer, without a display.

USAGE:
  python scripts/render_check.py BUNDLE --out FILE.png [--camera NAME] [--width 320] [--height 240]
                                 [--backend egl|osmesa]

Tries MUJOCO_GL=egl (GPU, or Mesa's EGL) first, then MUJOCO_GL=osmesa (software), each in a
fresh process because the GL backend is fixed when mujoco is first imported. The first backend
that renders a frame with real contrast wins. If neither does, it says what to install and
exits 2. This is a quick look at the scene; the finished render is Blender's job.
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
INSTALL = {
    "egl": "a GPU driver with EGL (NVIDIA, or Mesa: apt install libegl1 libgl1-mesa-dri) and PyOpenGL",
    "osmesa": "Mesa's software renderer: apt install libosmesa6 (Fedora: mesa-libOSMesa) and PyOpenGL",
}


def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def child(a):
    sys.path.insert(0, str(HERE))
    import mujoco
    import simlib
    model = simlib.load_model(Path(a.bundle))
    data = mujoco.MjData(model)
    simlib.reset_to_start(model, data)
    mujoco.mj_forward(model, data)
    with mujoco.Renderer(model, a.height, a.width) as r:
        r.update_scene(data, camera=a.camera if a.camera else -1)
        rgb = r.render()
    lum = rgb.mean(axis=2) / 255.0
    write_png(a.out, rgb)
    print(json.dumps({"backend": os.environ.get("MUJOCO_GL"), "size": [int(rgb.shape[1]), int(rgb.shape[0])],
                      "luminance_spread": round(float(lum.max() - lum.min()), 4),
                      "mean": round(float(lum.mean()), 4)}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle")
    ap.add_argument("--out", required=True)
    ap.add_argument("--camera")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--backend", choices=["egl", "osmesa"])
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.child:
        return child(a)
    tried = []
    for backend in [a.backend] if a.backend else ["egl", "osmesa"]:
        env = dict(os.environ, MUJOCO_GL=backend, PYOPENGL_PLATFORM=backend)
        cmd = [sys.executable, str(Path(__file__).resolve()), a.bundle, "--out", a.out, "--width", str(a.width),
               "--height", str(a.height), "--child"] + (["--camera", a.camera] if a.camera else [])
        try:
            p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            tried.append((backend, "timed out after 120 s"))
            continue
        if p.returncode == 0:
            info = json.loads(p.stdout.strip().splitlines()[-1])
            if info["luminance_spread"] >= 0.05:
                print(f"rendered {a.out} with MUJOCO_GL={backend}: {info}")
                for b, why in tried:
                    print(f"  ({b} was tried first: {why})")
                return 0
            tried.append((backend, f"rendered a flat frame {info}"))
            continue
        last = (p.stderr.strip().splitlines() or ["no output"])[-1]
        tried.append((backend, f"exit {p.returncode}: {last}"))
    print("could not render offscreen with any backend:", file=sys.stderr)
    for b, why in tried:
        print(f"  MUJOCO_GL={b}: {why}\n    needs {INSTALL[b]}", file=sys.stderr)
    print("the simulation itself does not need a renderer; scripts/simulate.py runs without one", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
