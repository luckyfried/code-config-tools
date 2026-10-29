// MuJoCo WASM helpers shared by the Node scripts and the browser worker.
// Every MjModel, MjData, MjVFS, DoubleBuffer and contact copy owns WASM memory that the garbage
// collector never frees: each one is released with .delete(), exactly once.

export const PINNED_MUJOCO = '3.17.0';

// The files model.xml names, as paths relative to the bundle, by the rule scripts/simlib.py
// referenced_files uses: mesh, hfield and skin files under meshdir, textures under texturedir.
export function assetPaths(xmlText) {
  const dir = (attr) => (xmlText.match(new RegExp(`<compiler\\b[^>]*\\b${attr}\\s*=\\s*(["'])(.*?)\\1`)) || [])[2] || '';
  const out = [];
  const mesh = dir('meshdir');
  for (const [tag, base] of [['mesh', mesh], ['hfield', mesh], ['skin', mesh], ['texture', dir('texturedir')]]) {
    for (const [, , f] of xmlText.matchAll(new RegExp(`<${tag}\\b[^>]*\\bfile\\s*=\\s*(["'])(.+?)\\1`, 'g'))) {
      out.push(base ? `${base.replace(/\/$/, '')}/${f}` : f);
    }
  }
  return out;
}

// Load model.xml and the files it names into a fresh VFS. files: [[relativePath, Uint8Array]].
export function loadBundle(mj, xmlBytes, files) {
  const vfs = new mj.MjVFS();
  try {
    vfs.addBuffer('model.xml', xmlBytes);
    for (const [path, bytes] of files) vfs.addBuffer(path, bytes);
    const model = mj.MjModel.mj_loadXML('model.xml', vfs);
    if (!model) throw new Error('model.xml did not compile');
    return model;
  } finally {
    vfs.delete();
  }
}

export function stateSpec(mj) {
  return mj.mjtState.mjSTATE_INTEGRATION.value;
}

export function getState(mj, model, data) {
  const spec = stateSpec(mj);
  const buf = new mj.DoubleBuffer(mj.mj_stateSize(model, spec));
  try {
    mj.mj_getState(model, data, buf, spec);
    return Float64Array.from(buf.GetView());
  } finally {
    buf.delete();
  }
}

export function setState(mj, model, data, values) {
  mj.mj_setState(model, data, Array.from(values), stateSpec(mj));
}

// Keyframe "start" when the model has one, the model's defaults otherwise (same rule as simlib).
export function resetToStart(mj, model, data) {
  const key = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY.value, 'start');
  if (key >= 0) mj.mj_resetDataKeyframe(model, data, key);
  else mj.mj_resetData(model, data);
  mj.mj_forward(model, data);
}

export function bodyNames(mj, model) {
  const out = [];
  for (let b = 1; b < model.nbody; b++) out.push(mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY.value, b) || `body${b}`);
  return out;
}

// One observation row in the same shape and timing as simlib.observe:
// u_i written to ctrl, mj_forward, then the row; the caller steps after.
export function observe(mj, model, data, names) {
  const bodies = {};
  for (let b = 1; b < model.nbody; b++) {
    bodies[names[b - 1]] = {
      pos: Array.from(data.xpos.subarray(3 * b, 3 * b + 3)),
      quat_wxyz: Array.from(data.xquat.subarray(4 * b, 4 * b + 4)),
    };
  }
  return {
    t: data.time,
    qpos: Array.from(data.qpos),
    qvel: Array.from(data.qvel),
    ctrl: Array.from(data.ctrl),
    actuator_force: Array.from(data.actuator_force),
    energy: Array.from(data.energy),
    ncon: data.ncon,
    bodies,
  };
}
