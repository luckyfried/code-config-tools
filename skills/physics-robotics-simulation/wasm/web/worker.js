// Steps the simulation off the page's thread and posts body poses once per animation tick.
// Messages in: load, play, pause, reset, ctrl, dispose. Messages out: ready, frame, error, disposed.
import { assetPaths, bodyNames, loadBundle, resetToStart } from '../lib.mjs';

let mj = null;
let model = null;
let data = null;
let running = true;
let timer = null;
let simStart = 0;
let wallStart = 0;
let steps = 0;
const MAX_STEPS_PER_TICK = 2000;

async function engine(threads) {
  if (mj) return mj;
  const url = threads ? '../node_modules/@mujoco/mujoco/mt/mujoco.js' : '../node_modules/@mujoco/mujoco/mujoco.js';
  const load = (await import(url)).default;
  mj = await load();
  return mj;
}

function release() {
  clearTimeout(timer);
  timer = null;
  data?.delete();
  model?.delete();
  data = null;
  model = null;
}

function geoms() {
  const out = [];
  for (let g = 0; g < model.ngeom; g++) {
    if (model.geom_group[g] > 2) continue; // groups 3+ hold collision-only geoms
    const geom = {
      body: model.geom_bodyid[g], type: model.geom_type[g],
      size: Array.from(model.geom_size.subarray(3 * g, 3 * g + 3)),
      pos: Array.from(model.geom_pos.subarray(3 * g, 3 * g + 3)),
      quat: Array.from(model.geom_quat.subarray(4 * g, 4 * g + 4)),
      rgba: Array.from(model.geom_rgba.subarray(4 * g, 4 * g + 4)),
    };
    const mesh = model.geom_dataid[g];
    if (geom.type === mj.mjtGeom.mjGEOM_MESH.value && mesh >= 0) {
      const va = model.mesh_vertadr[mesh], vn = model.mesh_vertnum[mesh];
      const fa = model.mesh_faceadr[mesh], fn = model.mesh_facenum[mesh];
      geom.vert = Float32Array.from(model.mesh_vert.subarray(3 * va, 3 * (va + vn)));
      geom.face = Uint32Array.from(model.mesh_face.subarray(3 * fa, 3 * (fa + fn)));
    }
    out.push(geom);
  }
  return out;
}

function post() {
  const xpos = Float64Array.from(data.xpos);
  const xquat = Float64Array.from(data.xquat);
  postMessage({ type: 'frame', t: data.time, steps, ncon: data.ncon, running, xpos, xquat }, [xpos.buffer, xquat.buffer]);
}

function tick() {
  if (!model) return;
  if (running) {
    const target = simStart + (performance.now() - wallStart) / 1000;
    let n = 0;
    while (data.time < target && n < MAX_STEPS_PER_TICK) {
      mj.mj_step(model, data);
      n++;
    }
    steps += n;
    if (n === MAX_STEPS_PER_TICK) { simStart = data.time; wallStart = performance.now(); } // fell behind: slow down
    if (!Number.isFinite(data.qpos[0])) { running = false; postMessage({ type: 'error', message: 'simulation diverged; reset' }); }
  }
  post();
  timer = setTimeout(tick, 16);
}

function heapBytes() {
  const probe = new mj.DoubleBuffer(1);
  const bytes = probe.GetView().buffer.byteLength;
  probe.delete();
  return bytes;
}

function clock() { simStart = data.time; wallStart = performance.now(); }

onmessage = async ({ data: msg }) => {
  try {
    if (msg.type === 'load') {
      release();
      await engine(msg.threads);
      const xmlText = await (await fetch(`${msg.base}model.xml`)).text();
      const files = await Promise.all(assetPaths(xmlText).map(async (p) => {
        const r = await fetch(msg.base + p);
        if (!r.ok) throw new Error(`${p}: ${r.status}`);
        return [p, new Uint8Array(await r.arrayBuffer())];
      }));
      model = loadBundle(mj, new TextEncoder().encode(xmlText), files);
      data = new mj.MjData(model);
      resetToStart(mj, model, data);
      steps = 0;
      const actuators = [];
      for (let a = 0; a < model.nu; a++) {
        actuators.push({ name: mj.mj_id2name(model, mj.mjtObj.mjOBJ_ACTUATOR.value, a) || `actuator ${a}`,
          range: Array.from(model.actuator_ctrlrange.subarray(2 * a, 2 * a + 2)), value: data.ctrl[a] });
      }
      postMessage({ type: 'ready', version: mj.mj_versionString(), threads: !!msg.threads, timestep: model.opt.timestep,
        nbody: model.nbody, bodies: bodyNames(mj, model), geoms: geoms(), actuators,
        stat: { center: Array.from(model.stat.center), extent: model.stat.extent }, heapBytes: heapBytes() });
      clock();
      tick();
    } else if (msg.type === 'play') { running = true; clock(); }
    else if (msg.type === 'pause') { running = false; }
    else if (msg.type === 'reset') {
      resetToStart(mj, model, data);
      steps = 0;
      clock();
      postMessage({ type: 'reset', ctrl: Array.from(data.ctrl) });
      post();
    }
    else if (msg.type === 'ctrl') { data.ctrl[msg.index] = msg.value; }
    else if (msg.type === 'dispose') { release(); postMessage({ type: 'disposed' }); }
  } catch (e) {
    postMessage({ type: 'error', message: String(e?.message || e) });
  }
};
