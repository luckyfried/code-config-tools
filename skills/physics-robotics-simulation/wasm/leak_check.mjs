#!/usr/bin/env node
// Load, step, reset and dispose a bundle many times and measure whether WASM memory grows.
//
// USAGE: node --expose-gc leak_check.mjs BUNDLE_DIR [--cycles 200] [--steps 200]
//
// Each cycle: load the bundle, make data, step, read state, reset to "start", copy a contact,
// then delete everything. WASM memory never shrinks, so its size after a warm-up and again after
// the remaining cycles is a high-water mark: it stays flat when every cycle frees what it made. A second pass skips .delete() on purpose, the negative
// control that shows the measure sees a leak. Exit 1 when the clean pass grows.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import loadMujoco from '@mujoco/mujoco';
import { assetPaths, getState, loadBundle, resetToStart } from './lib.mjs';

const args = process.argv.slice(2);
const bundle = args[0];
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 ? Number(args[i + 1]) : dflt;
};
const cycles = opt('--cycles', 200);
const steps = opt('--steps', 200);
if (!bundle) {
  console.error('usage: node --expose-gc leak_check.mjs BUNDLE_DIR [--cycles N] [--steps N]');
  process.exit(1);
}

function assetsOf(dir) {
  const xml = readFileSync(join(dir, 'model.xml'), 'utf8');
  return assetPaths(xml).map((rel) => [rel, new Uint8Array(readFileSync(join(dir, rel)))]);
}

const mj = await loadMujoco();
const xml = new Uint8Array(readFileSync(join(bundle, 'model.xml')));
const files = assetsOf(bundle);
// The module exports no heap handle; any buffer view's .buffer is the WASM memory itself.
const heap = () => {
  const probe = new mj.DoubleBuffer(1);
  const bytes = probe.GetView().buffer.byteLength;
  probe.delete();
  return bytes;
};

function cycle(dispose) {
  const model = loadBundle(mj, xml, files);
  const data = new mj.MjData(model);
  for (let i = 0; i < steps; i++) mj.mj_step(model, data);
  getState(mj, model, data);
  const contact = data.ncon > 0 ? data.contact : null;
  resetToStart(mj, model, data);
  if (dispose) {
    if (contact && contact.delete) contact.delete();
    data.delete();
    model.delete();
  }
}

function pass(dispose, n) {
  const warm = Math.min(20, n);
  for (let i = 0; i < warm; i++) cycle(dispose);
  globalThis.gc?.();
  const before = heap();
  for (let i = warm; i < n; i++) cycle(dispose);
  globalThis.gc?.();
  return { before, after: heap(), cycles: n - warm };
}

const clean = pass(true, cycles);
const growth = clean.after - clean.before;
console.log(`with .delete(): ${clean.cycles} cycles after warm-up, WASM heap ${clean.before} -> ${clean.after} bytes ` +
  `(growth ${growth})`);
const leaky = pass(false, Math.min(cycles, 60));
const leak = leaky.after - leaky.before;
console.log(`without .delete() (negative control): ${leaky.cycles} cycles, WASM heap ${leaky.before} -> ${leaky.after} ` +
  `bytes (growth ${leak})`);
if (growth > 0) {
  console.error('the WASM heap grew while every object was deleted: something is not released');
  process.exit(1);
}
if (leak <= 0) {
  console.error('the negative control did not grow the heap: this measure cannot see a leak');
  process.exit(1);
}
console.log('no growth with disposal; the negative control grows, so the measure sees leaks');
