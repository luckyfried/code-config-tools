# Blender: asset preparation and batch rendering

Blender is used two ways in this kit, and they stay separate:

1. **Batch scripts** (`blender -b`, through `scripts/blender_run.py`): asset building, export,
   replay and final renders. This is the path every result in the kit comes from. It needs no
   add-on and no MCP server; `--factory-startup` ignores the person's own add-ons and startup file.
2. **The Blender MCP server** for looking around and editing interactively in an open Blender
   (see `mcp-adapters.md`). Nothing the kit verifies depends on it.

Tested on Blender 5.2.3 LTS (Linux portable build). For current bpy, read the
`blender-current-api` skill before writing a script, and `blender-verify` before you call a
scene done.

## Running a script

```
python scripts/blender_run.py blender/render_probe.py -- --out runs/probe.png
```

`blender_run.py` finds Blender from `--blender`, then `$BLENDER`, then `PATH`, refuses a release
outside 5.2 unless you pass `--any-version` (and then treat the result as untested), runs
`blender -b --factory-startup --python-exit-code 1 -P SCRIPT -- ARGS` so a Python error is a
non-zero exit, and stops it at `--max-wall-s` (default 600 s, exit 124). Without Blender it says
where to get it and exits 2. `render_probe.py` renders a 64 x 48 frame and checks its pixels;
Cycles (CPU), EEVEE and Workbench all rendered headless on the test machine.

## Preparing assets

`blender/make_assets.py` is the worked example: it builds the arm's three visual meshes and the
orientation fixture with bmesh, in each body's own frame, and exports OBJ.

- Model in meters, Z up, +Y forward. Put each part's origin at its joint, with the link along +X
  (or whatever the MJCF body frame is). Then the OBJ's coordinates are the body frame and the MJCF
  needs no `pos`/`quat` on the visual geom.
- Apply object scale before export (`bpy.ops.object.transform_apply(scale=True)`); the exporter
  writes mesh data, and an unapplied scale is a silent unit error.
- Export with `bpy.ops.wm.obj_export(filepath=..., export_selected_objects=True,
  forward_axis='Y', up_axis='Z', global_scale=1.0, apply_modifiers=True, export_materials=False,
  export_triangulated_mesh=True)`. Record the axes and scale in `bundle.json` `source.export`.
- Visual meshes only. Collision is primitives authored in MJCF (see `exchange-contract.md`).
- Keep polygon counts modest; the browser preview draws every visual mesh every frame.
- Rerunning the script must give the same files: `make_assets.py` rebuilt all six OBJ files byte
  for byte on the test machine.

After export: `python scripts/bundle.py seal examples/arm` (records hashes and the static
scenery), then `python scripts/bundle.py check examples/arm`.

## Replay and render

```
python scripts/simulate.py examples/arm --seconds 3.5 --out runs/arm
python scripts/blender_run.py blender/replay_render.py -- examples/arm runs/arm/trace.json \
    --out runs/replay --fps 50 --render-every 5 --size 480x270 --samples 16
```

`replay_render.py` builds the scene from `bundle.json` alone (the same OBJ files MuJoCo loaded,
the static scenery, the camera), keys every body on every frame from the trace, then checks two
things before it renders:

- each imported mesh sits where the file's coordinates put it (an import with other axes moved the
  base 0.09 m and was refused);
- `matrix_world` of every body on every frame equals the trace pose within 1e-5 m and 1e-4 rad.

It renders with Cycles on the CPU by default (`--engine` for EEVEE or Workbench), writes
`frames/frame_NNNN.png`, `frames.json` and `replay_report.json`, and exits 1 when a check fails or
the trace names other bodies. On the test machine: 176 frames, all exact, error 0 m and 0 rad,
mesh frame within 1.3e-8 m (OBJ's float precision), 36 frames rendered at 480 x 270 in 20 s on
the CPU.

## Headless rendering on a server

Cycles on the CPU needs no display or GPU. EEVEE and Workbench need an OpenGL or Vulkan context;
Blender 5 creates one headless through EGL where the driver offers it. If EEVEE fails without a
display, render with Cycles, or run under a virtual display (`xvfb-run -a blender -b ...`).
