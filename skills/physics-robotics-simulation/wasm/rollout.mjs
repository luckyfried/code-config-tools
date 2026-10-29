#!/usr/bin/env node
// Replay a Python run in WebAssembly and write its trace.
//
// USAGE: node rollout.mjs BUNDLE_DIR RUN_JSON OUT_TRACE_JSON
//
// Loads BUNDLE_DIR/model.xml and every asset RUN_JSON lists into the VFS, refuses when a file's
// hash differs from the run's, restores the run's initial state, and replays its per-step
// controls with the same timing as scripts/simulate.py (write u_i, mj_forward, record, mj_step).
// scripts/compare_traces.py then compares the two traces.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import loadMujoco from '@mujoco/mujoco';
import { PINNED_MUJOCO, bodyNames, loadBundle, observe, setState } from './lib.mjs';

const [bundle, runPath, outPath] = process.argv.slice(2);
if (!outPath) {
  console.error('usage: node rollout.mjs BUNDLE_DIR RUN_JSON OUT_TRACE_JSON');
  process.exit(1);
}
const run = JSON.parse(readFileSync(runPath, 'utf8'));
const sha = (b) => createHash('sha256').update(b).digest('hex');
const xml = readFileSync(join(bundle, 'model.xml'));
if (sha(xml) !== run.model.sha256) {
  console.error('model.xml differs from the one the run used; rerun scripts/simulate.py first');
  process.exit(1);
}
const files = run.model.assets.map(({ path, sha256 }) => {
  const bytes = readFileSync(join(bundle, path));
  if (sha(bytes) !== sha256) {
    console.error(`${path} differs from the file the run used`);
    process.exit(1);
  }
  return [path, new Uint8Array(bytes)];
});

const mj = await loadMujoco();
const version = mj.mj_versionString();
if (version !== PINNED_MUJOCO || version !== run.engine.version) {
  console.error(`engine ${version}; the kit pins ${PINNED_MUJOCO} and the run used ${run.engine.version}`);
  process.exit(1);
}
const model = loadBundle(mj, new Uint8Array(xml), files);
const data = new mj.MjData(model);
try {
  setState(mj, model, data, run.initial_state.values);
  const names = bodyNames(mj, model);
  const controls = run.controls.per_step;
  const rows = [];
  const t0 = performance.now();
  for (let i = 0; i < run.steps_run; i++) {
    if (model.nu) data.ctrl.set(controls[i]);
    mj.mj_forward(model, data);
    rows.push(observe(mj, model, data, names));
    mj.mj_step(model, data);
  }
  if (model.nu) data.ctrl.set(controls[run.steps_run - 1]);
  mj.mj_forward(model, data);
  rows.push(observe(mj, model, data, names));
  const wall = performance.now() - t0;
  writeFileSync(outPath, JSON.stringify({
    meta: { engine: `mujoco ${version} wasm`, timestep: model.opt.timestep, steps: run.steps_run, wall_ms: wall },
    rows,
  }));
  const last = rows[rows.length - 1];
  console.log(`wasm mujoco ${version}: ${run.steps_run} steps in ${wall.toFixed(1)} ms, ` +
    `t=${last.t.toFixed(3)} qpos=[${last.qpos.slice(0, 3).map((v) => v.toFixed(5)).join(' ')}]`);
} finally {
  data.delete();
  model.delete();
}
