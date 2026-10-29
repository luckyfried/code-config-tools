# Browser and WebAssembly (`@mujoco/mujoco`)

The official bindings, `@mujoco/mujoco` 3.17.0 on npm, are the same engine as the Python package
compiled to WebAssembly. The kit's `wasm/` folder pins it with `three` 0.186.1:

```
npm --prefix wasm ci
python scripts/simulate.py examples/arm --seconds 3.5 --out runs/arm
node wasm/rollout.mjs examples/arm runs/arm/run.json runs/arm/trace_wasm.json
python scripts/compare_traces.py runs/arm/trace.json runs/arm/trace_wasm.json
node --expose-gc wasm/leak_check.mjs examples/drop
node wasm/serve.mjs examples/arm            # http://127.0.0.1:8765/
```

## Same run, two engines

`rollout.mjs` reads a Python `run.json`, refuses when model.xml, an asset, or the engine version
differs from the run's, restores the run's initial state, and replays its stored per-step controls
with the same observation timing (write u_i, `mj_forward`, record, `mj_step`).
`compare_traces.py` then checks every row: positions, joint angles and body orientations within
1e-6, velocities within 1e-5, actuator forces within 1e-4, contact counts equal. Measured on the
three examples, the largest difference was 3.6e-15 (arm actuator force); pendulum and drop agree
bit for bit in position. A difference above rounding means the inputs differ, or a long
contact-rich run has let rounding grow; compare a shorter run before suspecting the engine.

## The API in practice

```js
import loadMujoco from '@mujoco/mujoco';            // single-threaded build
const mj = await loadMujoco();
const vfs = new mj.MjVFS();
vfs.addBuffer('model.xml', xmlBytes);                // Uint8Array
vfs.addBuffer('meshes/base.obj', objBytes);          // same relative path as on disk
const model = mj.MjModel.mj_loadXML('model.xml', vfs);
vfs.delete();
const data = new mj.MjData(model);
mj.mj_step(model, data);
// data.qpos, data.xpos, data.ctrl ... are live views into WASM memory: copy before you keep them.
data.delete(); model.delete();
```

- Enums are objects: pass `mj.mjtObj.mjOBJ_BODY.value`, not the object.
- Out-parameters need a WASM buffer: `const b = new mj.DoubleBuffer(n); mj.mj_getState(m, d, b,
  spec); b.GetView(); b.delete()`. A plain `Float64Array` is copied in and the result is lost.
- Statistics are under `model.stat.center` and `model.stat.extent`.
- `data.contact` returns a new copy each time it is read. Delete it, or every read leaks: 300000
  reads without `delete()` grew the heap by 750 MB in the kit's measurement.
- Everything made with `new`, `mj_loadXML`, or a `contact` read owns WASM memory the garbage
  collector never frees. Call `.delete()` exactly once. `lib.mjs` wraps load, state, reset and
  observation the way the Python side does them.

## Disposal, measured

`leak_check.mjs` loads, steps, checkpoints, resets, reads contacts and disposes a bundle 200 times
and reads the size of WASM memory, which never shrinks, after a warm-up and at the end. With every
`.delete()` the heap stayed at 17629184 bytes; the negative control (no `.delete()`) grew it by
560 MB in 40 cycles, so the measure does see a leak.

## The browser preview

`serve.mjs` serves the page, the worker, `node_modules`, and the bundle under `/bundle/` on
127.0.0.1 only. The page (`web/`):

- runs the simulation in a module worker (`web/worker.js`) that steps to keep simulated time level
  with wall time, at most 2000 steps a tick, and posts body poses once a tick as transferred
  arrays;
- draws with Three.js (+Z up, MuJoCo's `w x y z` quaternions converted to Three's `x y z w`),
  visual geoms only (groups 0 to 2; collision geoms in group 3 stay hidden);
- has Play/Pause, Reset (back to keyframe `start`, sliders back to its controls), one slider per
  actuator over its `ctrlrange`, an orbit camera, and "Reload x20", which disposes and reloads the
  model twenty times;
- disposes the worker's model and data and every Three geometry, material and the renderer on
  `pagehide`;
- exposes its state as `window.__preview` (time, steps, contacts, loads, the WASM heap size at each
  load, errors) so a headless browser can check it.

What was checked in a headless browser through the Playwright MCP server: the page loads mujoco
3.17.0 single-threaded, steps (t advancing with wall time), the sliders drive the arm onto the pad
(one contact) and off it, Pause holds t, Reset returns t to 0 and the sliders to 0, and twenty
reloads leave the WASM heap at its first size.

## Threads

Single-threaded is the default. The multi-threaded build (`@mujoco/mujoco/mt`) uses
`SharedArrayBuffer`, which a browser allows only on a cross-origin isolated page: the page must be
served with `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy:
require-corp`. `node wasm/serve.mjs BUNDLE --isolate` sends both, and `?threads=1` then loads the mt
build. Without the headers the page says so and stays single-threaded. Isolation also blocks
cross-origin images and scripts that do not send CORP headers, so a page that embeds third-party
content cannot simply turn it on. Small models gain nothing from threads; measure before you
switch.
