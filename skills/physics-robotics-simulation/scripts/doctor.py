#!/usr/bin/env python3
"""Say what this machine has and lacks for each part of the kit, and how to install what is missing.

USAGE:
  python scripts/doctor.py [--blender PATH] [--render]

Needed for simulation: Python 3.12+, mujoco 3.17.0, numpy (python -m pip install -r requirements.txt
inside a virtual environment). Needed only for their own steps: an offscreen GL backend
(quick MuJoCo renders), Blender 5.2 LTS (asset preparation and replay renders), Node 20+ with
wasm/node_modules (the WebAssembly rollout and the browser preview). --render also tries the GL
backends, which takes a few seconds. Exit 0 when simulation can run, 1 when it cannot.
"""
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(HERE))
REQ = {line.split("==")[0]: line.split("==")[1] for line in (KIT / "requirements.txt").read_text().split() if "==" in line}
rows = []


def row(part, item, ok, found, fix=""):
    rows.append((part, item, ok, found, fix))


def python_parts():
    v = sys.version_info
    row("simulation", "python", v >= (3, 12), f"{v.major}.{v.minor}.{v.micro}", "Python 3.12 or newer")
    pip = f"python -m pip install -r {os.path.relpath(KIT / 'requirements.txt')}"
    for mod, dist in (("mujoco", "mujoco"), ("numpy", "numpy"), ("OpenGL", "PyOpenGL")):
        part = "simulation" if mod != "OpenGL" else "quick render"
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            row(part, dist, ver == REQ.get(dist, ver), ver, f"{pip} (pinned {REQ.get(dist)})")
        except Exception as e:  # noqa: BLE001
            row(part, dist, False, f"missing ({type(e).__name__})", pip)


def render_parts():
    for backend in ("egl", "osmesa"):
        env = dict(os.environ, MUJOCO_GL=backend, PYOPENGL_PLATFORM=backend)
        code = ("import mujoco; m = mujoco.MjModel.from_xml_string('<mujoco><worldbody><geom size=\".1\"/>"
                "</worldbody></mujoco>'); r = mujoco.Renderer(m, 32, 32); r.update_scene(mujoco.MjData(m)); r.render()")
        try:
            p = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=60)
            ok, found = p.returncode == 0, "renders" if p.returncode == 0 else (p.stderr.strip().splitlines() or ["?"])[-1][:70]
        except subprocess.TimeoutExpired:
            ok, found = False, "timed out"
        fix = ("GPU driver with EGL, or Mesa: apt install libegl1 libgl1-mesa-dri" if backend == "egl"
               else "apt install libosmesa6 (Fedora: mesa-libOSMesa)")
        row("quick render", f"MUJOCO_GL={backend}", ok, found, fix)


def blender_part(explicit):
    import blender_run
    exe = blender_run.find_blender(explicit)
    fix = f"Blender {blender_run.LINE} LTS from https://www.blender.org/download/lts/; pass --blender or set BLENDER"
    if not exe:
        row("Blender", "blender", False, "not found", fix)
        return
    first = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout.split("\n")[0]
    found = first.replace("Blender", "").split()[0] if first.startswith("Blender") else "unknown"
    row("Blender", "blender", found.startswith(blender_run.LINE + "."), found, fix)


def node_part():
    node = shutil.which("node")
    if not node:
        row("WebAssembly", "node", False, "not found", "Node.js 20 or newer")
        return
    ver = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    row("WebAssembly", "node", int(ver.lstrip("v").split(".")[0]) >= 20, ver, "Node.js 20 or newer")
    pkg = KIT / "wasm" / "node_modules" / "@mujoco" / "mujoco" / "package.json"
    want = json.loads((KIT / "wasm" / "package.json").read_text())["dependencies"]["@mujoco/mujoco"]
    have = json.loads(pkg.read_text())["version"] if pkg.is_file() else "not installed"
    row("WebAssembly", "@mujoco/mujoco", have == want, have, f"npm --prefix {os.path.relpath(KIT / 'wasm')} ci")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender")
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    python_parts()
    if a.render:
        render_parts()
    blender_part(a.blender)
    node_part()
    for part, item, ok, found, fix in rows:
        print(f"{'ok ' if ok else 'NO '} {part:<13} {item:<18} {found}" + ("" if ok else f"\n      install: {fix}"))
    sim_ok = all(ok for part, _, ok, _, _ in rows if part == "simulation")
    print("\nsimulation can run" if sim_ok else "\nsimulation cannot run until the lines above marked NO are fixed")
    return 0 if sim_ok else 1


if __name__ == "__main__":
    sys.exit(main())
