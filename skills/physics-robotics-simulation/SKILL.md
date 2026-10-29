---
name: physics-robotics-simulation
description: Use when building, running, or checking a physics or robotics simulation with MuJoCo - writing MJCF models (units, mass and inertia, joints, actuators, contacts, sensors), stepping them in Python with bounded controls, reset and checkpoints, previewing the same model in a browser with the official @mujoco/mujoco WebAssembly bindings and three.js, preparing meshes in Blender and rendering replays of recorded poses with `blender -b`, and keeping runs reproducible. Use when the user says "simulate", "MuJoCo", "MJCF", "URDF", "robot arm", "pendulum", "contact", "physics in the browser", "replay in Blender", or "render the simulation".
---

# Physics & robotics simulation

One model folder (a bundle) is read the same way by MuJoCo in Python, by MuJoCo in the browser,
and by Blender. Physics runs in MuJoCo only; the browser shows it, Blender draws recorded poses.
Every number you report comes from a script in this folder that you ran, never from reading a
model and guessing.

## What the person installs

| for | install | check |
|---|---|---|
| simulation (always) | Python 3.12+ and, in a virtual environment, `pip install -r requirements.txt` (mujoco 3.17.0, numpy, PyOpenGL) | `python scripts/doctor.py` |
| quick headless renders | a GPU driver with EGL, or OSMesa (`apt install libosmesa6`) | `python scripts/doctor.py --render` |
| browser preview | Node 20+; `npm --prefix wasm ci` | the rollout and comparison in `guides/browser-wasm.md` |
| assets and final renders | Blender 5.2 LTS (5.2.3 tested), the portable build from blender.org is fine; put it on `PATH` or set `BLENDER` | `python scripts/blender_run.py blender/render_probe.py -- --out runs/probe.png` |

Run these commands from this skill's folder (the one containing this `SKILL.md`). Create the
simulation environment after checking that `python3 --version` reports Python 3.12 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/doctor.py
```

On Windows, create it with `py -3.12 -m venv .venv` and activate it in PowerShell with
`.venv\Scripts\Activate.ps1`. The pinned NumPy requires Python 3.12 or newer.

Run `doctor.py` first. Tell the person which rows are missing and what each one unlocks; the
simulation row is the only one every task needs.

## The playbook

1. **Describe the mechanism.** Bodies, how they connect (hinge, slide, ball, free), what drives
   them (motor torque, position servo), what touches what, and what question the run answers
   (a period, a settling height, a contact force, a reachable pose). Write the expected number
   down before simulating.
2. **Choose Python, the browser, or both.** Python for anything measured; the browser to look
   and play with controls; both when someone else will open it in a browser. The browser runs
   the same engine and matches Python rollouts to rounding (`guides/browser-wasm.md`).
3. **Prepare assets in Blender** when the model needs real shapes: meters, Z up, origin at the
   joint, scale applied, export OBJ with the recorded settings (`guides/blender-assets-and-render.md`).
   Visual meshes only; collision is MJCF primitives.
4. **Build a small validated model.** Start from the nearest example and change one thing at a
   time (`guides/model-authoring.md`). A model with Blender meshes is a bundle with a
   `bundle.json` (copy `examples/arm`); seal and check it after every change:
   `python scripts/bundle.py seal BUNDLE && python scripts/bundle.py check BUNDLE`. A model made of
   primitives alone (like `examples/pendulum`) needs only `model.xml`.
5. **Simulate** with bounds: `python scripts/simulate.py BUNDLE --seconds 3 --out runs/NAME`
   (`guides/python-simulation.md`). It refuses an engine mismatch, stops on divergence or a wall
   time bound, and writes the trace and `run.json`.
6. **Inspect** the numbers against what you wrote in step 1: energy, contacts and their forces,
   sensors, actuator saturation, warnings. Check reset and checkpoints the way
   `scripts/check_examples.py` does.
7. **Preview in the browser**: `node wasm/serve.mjs BUNDLE`, open `http://127.0.0.1:8765/`; play,
   pause, reset, move the sliders. Prove the browser run matches with `wasm/rollout.mjs` and
   `scripts/compare_traces.py`.
8. **Replay and render in Blender**: `blender/replay_render.py` keys every body from the trace,
   checks every keyed pose against it, and renders frames whose `frames.json` names each frame's
   time and trace row.
9. **Iterate**: change the model or controls, reseal, rerun from step 5. Keep each run's folder;
   `run.json` says exactly what produced it (`guides/reproducibility.md`).

## Examples (all run headless)

| example | shows | check |
|---|---|---|
| `examples/pendulum` | hinge, gravity, energy, sensors | period equals the exact large-angle value; energy drift ~1e-12 |
| `examples/drop` | free body, contact, restitution, resting | first contact time, rest height, contact force equals weight |
| `examples/arm` | two-link arm from Blender meshes, position actuators, force limits, contact | holds a pose, presses a pad with a measured force, releases |

`python scripts/check_examples.py` runs all three, prints the state as it progresses, and checks
each one's numbers and that reset, checkpoint restore and rerun give identical states. Exit 0 only
when every check passes. The end-to-end arm path is: `blender/make_assets.py` (meshes) ->
`examples/arm/model.xml` -> `simulate.py` -> `wasm/rollout.mjs` + `compare_traces.py` ->
`blender/replay_render.py` (frames with matching times).

## Scripts

| script | does |
|---|---|
| `scripts/doctor.py` | what is installed and what it unlocks |
| `scripts/simulate.py` | one bounded rollout; trace + run record |
| `scripts/check_examples.py` | the three examples with their checks |
| `scripts/bundle.py seal/check` | the exchange contract for one bundle |
| `scripts/contract_check.py` | proves the contract catches wrong axes, units, mirrored meshes, broken bundles |
| `scripts/compare_traces.py` | two traces row by row at stated tolerances |
| `scripts/render_check.py` | a quick MuJoCo render: EGL, then OSMesa, else a plain error |
| `scripts/blender_run.py` | runs a bpy script in `blender -b --factory-startup` with an exit code and a time bound |
| `blender/make_assets.py`, `replay_render.py`, `render_probe.py` | asset export, trace replay and render, engine probe |
| `wasm/rollout.mjs`, `leak_check.mjs`, `serve.mjs` | browser engine rollout, disposal check, local preview |

## Guides

- `guides/model-authoring.md`: MJCF units, inertia, joints, actuators, contacts, sensors, URDF.
- `guides/python-simulation.md`: running, observation timing, controls, bounds, reset, checkpoints.
- `guides/browser-wasm.md`: the WebAssembly API in practice, worker stepping, disposal, threads.
- `guides/reproducibility.md`: what `run.json` pins, comparing runs, replays and video.
- `guides/blender-assets-and-render.md`: Blender batch scripts, export settings, replay and render.
- `guides/exchange-contract.md`: the bundle format and its checks.
- `guides/mcp-adapters.md`: the Playwright and Blender MCP servers, safety checklist, the optional
  MuJoCo MCP.

## Related skills in this toolkit

- `blender-current-api`: current bpy names before writing any Blender script.
- `blender-verify`: read back and look at a Blender result before calling it done.
- `threejs-current-api`: current three.js names before changing the browser preview.

## Rules

- Never report a simulation result you did not run. Quote the command, its exit code, and the
  numbers it printed.
- Physics comes from MuJoCo. Blender and three.js only draw poses MuJoCo produced.
- Keep the engine pinned (3.17.0) across Python, the browser and every `bundle.json`.
- A render or a screenshot that failed is reported as failed; never draw a stand-in image.
- The product runs none of these checks for you. Run `bundle.py check` and `contract_check.py`
  yourself before trusting a new export.
- MCP servers here run with your permissions and no isolation; follow `guides/mcp-adapters.md`.
