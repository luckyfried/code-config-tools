# The Blender <-> MuJoCo exchange contract

A bundle is one folder that MuJoCo, the browser preview and Blender all read the same way:

```
my_robot/
  model.xml          MJCF; every file path in it is relative and inside this folder
  meshes/*.obj       visual meshes exported from Blender
  bundle.json        the contract: units, frame, engine, body and joint mapping, hashes
```

`examples/arm/` is the worked bundle; copy it to start a new one.

## What the contract says

| topic | rule |
|---|---|
| units | SI: meters, kilograms, seconds, radians. A Blender scene in centimeters is a 100x error in length and a 1,000,000x error in inertia |
| frame | right-handed, +Z up, +Y forward; quaternions are `w x y z` everywhere (MuJoCo order). Blender's `rotation_quaternion` is also `w x y z`; three.js is `x y z w` and the preview converts |
| scale | applied in Blender before export, `global_scale=1.0`; the export settings are written to `source.export` |
| visual vs collision | OBJ meshes are visual only (`contype="0" conaffinity="0" density="0"`, in a display group: the example uses group 1 for visual and 3 for collision). Collision is MJCF primitives (box, capsule, cylinder, sphere) on the same body. The visual mesh's box must match its collision primitives within `tolerances.visual_outside_collision_m` (0.005 m in the example) |
| body frame | the OBJ file's coordinates are the body frame: no `scale` on the MJCF `<mesh>` and no `pos`/`quat` on the visual geom, because Blender draws the file as it is. `check` compares where MuJoCo puts the mesh with the file's own coordinates (within 1e-5 m) |
| mass | every moving body has an authored `<inertial>` (mass, diagonal inertia, position); the center of mass lies inside the collision geometry |
| body mapping | `bodies.<mujoco body>` names its `blender_object`, `visual_geom`, `visual_mesh` and `collision_geoms`; one Blender object per body |
| joint mapping | `joints.<name>` gives `parent`, `child`, `type`, `axis`, and must equal the compiled model; every non-free joint is mapped |
| engine | `engine.mujoco` is the exact version the bundle was checked with |
| hashes | `assets` lists every file `model.xml` names with its sha256; `compiled_sha256` is the compiled model |
| scenery | `static` lists the world-body geoms (floor, pads) so Blender can draw them without parsing MJCF |
| camera | `camera.pos`, `look_at`, `lens_mm` for the Blender render |

## Seal and check

```
python scripts/bundle.py seal examples/arm      # after any change to model.xml or a mesh
python scripts/bundle.py check examples/arm     # exit 0 only when every rule passes
```

`check` prints one line per rule: `layout`, `engine`, `compile`, `assets` (relative, inside,
present, hash as sealed), `inertia` (present, positive, triangle inequality, COM inside),
`visual_collision` (including the body-frame placement), `joints`, `portability` (a copy in a fresh folder compiles to the same
model, so nothing outside the folder is read). `--json` gives the same as data.

`simulate.py` records the model and asset hashes in `run.json`; `wasm/rollout.mjs` verifies
its inputs against that run record before it runs. Run `bundle.py check` to verify the sealed
bundle; `replay_render.py` builds
its scene from `bundle.json` and checks the mesh frame and every keyed pose (see
`blender-assets-and-render.md`).

## Proving the checks work

```
python scripts/contract_check.py
```

Part 1 uses `examples/fixtures/orientation/`: an asymmetric shape of known size (0.30 x 0.20 x
0.10 m, tall block at -X, tab toward +Y) exported three ways from Blender. The good export
matches the fixture's extents, volume (2.55e-3 m^3) and center of volume, and MuJoCo puts its
center of mass at the same point. The wrong-axes export ("axes swapped"), the centimeter export
("100x"), a mirrored copy and a mirrored, rewound copy are each refused with the reason.

Part 2 copies the arm bundle and breaks it 15 ways (missing asset, absolute meshdir, meshdir
outside the folder, edited asset, nonphysical inertia, COM outside the body, no inertial, a
visual geom that collides, wrong axis, wrong parent, unmapped joint, a mesh with Y and Z swapped
and resealed, a mesh in centimeters and resealed, a `scale` on the MJCF mesh, a `pos` on the
visual geom); each must fail the rule named for it. On the test machine: 22 of 22 expectations
held.

Two MuJoCo facts the fixture caught:

- MuJoCo computes a mesh's inertia from its convex hull unless the mesh says `inertia="exact"`.
  For a concave part the hull's center of mass is off (6 mm on the fixture). Author `<inertial>`
  explicitly, or set `inertia="exact"` on a closed, consistently wound mesh.
- A swapped axis on a part that is symmetric in those axes changes nothing measurable. The
  fixture is asymmetric for that reason; test a new export pipeline on it, not on your model.

## What runs these checks

You do, or your agent does. The product has no test step for toolkit content: nothing runs
`bundle.py check` or `contract_check.py` when the toolkit is installed or launched. Run them
before trusting a new export, after changing a model, and before rendering a result you will
share.
