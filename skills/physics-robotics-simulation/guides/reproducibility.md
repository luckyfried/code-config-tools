# Reproducibility and export

A result is reproducible when someone else can rerun it and get the same numbers, or can see
exactly which input differs. Every `simulate.py` run writes `run.json` beside its trace:

| field | what it pins |
|---|---|
| `engine` | MuJoCo version (and the Python package version) |
| `host` | Python, numpy and platform strings |
| `model.sha256` | the bytes of model.xml |
| `model.compiled_sha256` | the compiled model: every numeric array MuJoCo built, minus the stored file paths, plus the options. Two folders holding the same bundle give the same value; a changed mesh, inertia or option does not |
| `model.assets` | each file model.xml names, with its own hash |
| `options` | timestep, integrator, solver, cone, iterations, tolerance, noslip, gravity, flags |
| `initial_state` | the full `mjSTATE_INTEGRATION` vector the run started from |
| `controls` | the planned control sequence and its hash; includes unused rows if the run stops early |
| `observation_timing` | the rule each row follows (see `python-simulation.md`) |
| `steps_run`, `stopped`, `warnings`, `wall_s` | how the run ended |

## Rules

- Pin the engine. The kit refuses any mujoco but 3.17.0 (`requirements.txt`,
  `wasm/package.json` and its lock file, `bundle.json` `engine`). An upgrade is a deliberate change:
  bump all three, rerun `check_examples.py`, `contract_check.py` and a WebAssembly comparison, and
  reseal the bundles.
- Same engine, model, initial state and controls give the same trace bit for bit on one machine
  (checked for all three examples). Across machines and between the Python and WebAssembly builds,
  expect rounding-level differences (largest measured: 3.6e-15) and compare with
  `compare_traces.py` at its stated tolerances, never with `==`.
- Keep runs out of the bundle folder (`runs/` is ignored by git). A bundle is inputs only.
- Never hand-edit a trace. Rerun.

## Replays and video

A replay takes a trace and draws it; it never steps physics again. `blender/replay_render.py`
keys Blender objects from the trace, proves the keyed poses match the trace, and renders frames
whose `frames.json` names, for each frame, the time, the trace row and the state. A frame is
exact when its time matches a recorded row. At 50 fps with every 0.002 s step recorded, all
frames are exact; a decimated trace may require interpolation even at that rate. Between
recorded times, positions interpolate linearly and rotations by slerp. The report counts exact frames. Assemble frames into
a video after installing [FFmpeg](https://ffmpeg.org/download.html), for example
`ffmpeg -framerate 10 -pattern_type glob -i 'runs/replay/frames/frame_*.png' -pix_fmt yuv420p arm.mp4`
when every fifth frame of 50 fps was rendered. The quoted glob includes the sparse frame numbers;
use a fresh replay output folder so images from another run cannot enter the video. Keep
`frames.json` and `run.json` with the video.

## Exporting a result

Ship the bundle folder, `run.json`, `trace.json`, and (for a video) `frames.json` and
`replay_report.json`. With those, anyone can rerun `simulate.py`, replay in WebAssembly, or
re-render, and `compare_traces.py` says whether they got the same result.
