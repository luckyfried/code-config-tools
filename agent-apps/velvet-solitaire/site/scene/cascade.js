// The win cascade: every card fires off the foundations, bounces on the table's bottom edge
// with decaying restitution, and trails its last six positions as fading ghost quads, all
// ghosts in one instanced draw. Buffers are made once; a frame allocates nothing.

import * as THREE from "three";
import { ATLAS_COLS, ATLAS_ROWS, CARD_W, CARD_H } from "./card.js";

const GHOSTS = 6;
const COUNT = 52 * GHOSTS;

export function createCascade(atlas) {
  const geometry = new THREE.PlaneGeometry(CARD_W, CARD_H);
  const face = new THREE.InstancedBufferAttribute(new Float32Array(COUNT), 1);
  const alpha = new THREE.InstancedBufferAttribute(new Float32Array(COUNT), 1);
  face.setUsage(THREE.DynamicDrawUsage);
  alpha.setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute("aFace", face);
  geometry.setAttribute("aAlpha", alpha);
  const material = new THREE.ShaderMaterial({
    uniforms: {
      uMap: { value: atlas.texture },
      uInset: { value: new THREE.Vector2(atlas.pad / atlas.cellW, atlas.pad / atlas.cellH) },
    },
    vertexShader: `
attribute float aFace;
attribute float aAlpha;
uniform vec2 uInset;
varying vec2 vUv;
varying vec2 vLocal;
varying float vAlpha;
void main() {
  vec2 cellXY = vec2(mod(aFace, ${ATLAS_COLS}.0), floor(aFace / ${ATLAS_COLS}.0));
  vec2 card = vec2(uv.x, 1.0 - uv.y);
  vUv = (cellXY + uInset + card * (1.0 - 2.0 * uInset)) / vec2(${ATLAS_COLS}.0, ${ATLAS_ROWS}.0);
  vLocal = (uv - 0.5) * vec2(${CARD_W}.0, ${CARD_H}.0);
  vAlpha = aAlpha;
  gl_Position = projectionMatrix * viewMatrix * modelMatrix * instanceMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform sampler2D uMap;
varying vec2 vUv;
varying vec2 vLocal;
varying float vAlpha;
void main() {
  vec2 q = abs(vLocal) - vec2(${CARD_W / 2 - 3.4}, ${CARD_H / 2 - 3.4});
  float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 3.4;
  float edge = clamp(0.5 - d, 0.0, 1.0);
  vec4 c = texture2D(uMap, vUv);
  gl_FragColor = vec4(c.rgb, vAlpha * edge);
  #include <colorspace_fragment>
}`,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new THREE.InstancedMesh(geometry, material, COUNT);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.visible = false;
  mesh.renderOrder = 2;

  const st = {
    mesh,
    face,
    alpha,
    running: false,
    order: [],
    launched: 0,
    clock: 0,
    nextLaunch: 0,
    interval: 0.075,
    trailClock: 0,
    // Trail ring buffers: x, y, z, rot per ghost.
    tx: new Float32Array(COUNT),
    ty: new Float32Array(COUNT),
    tz: new Float32Array(COUNT),
    tr: new Float32Array(COUNT),
    tn: new Uint8Array(52),
    th: new Uint8Array(52),
    spin: new Float32Array(52),
    bounces: new Uint8Array(52),
    done: new Uint8Array(52),
    gone: 0,
    onLaunch: null,
    onDone: null,
    bounds: { left: 0, right: 0, floor: 0, cardW: 60 },
  };
  return st;
}

function rand(seed) {
  const x = Math.sin(seed * 91.17 + 7.3) * 43758.5453;
  return x - Math.floor(x);
}

/** Starts the cascade from the foundations: kings first, one card from each pile in turn. */
export function startCascade(st, motion, state, layout, { onLaunch, onDone }) {
  st.order.length = 0;
  for (let rank = 12; rank >= 0; rank -= 1) {
    for (let f = 0; f < 4; f += 1) {
      const card = state.foundations[f][rank];
      if (card !== undefined) st.order.push(card);
    }
  }
  st.launched = 0;
  st.clock = 0;
  st.nextLaunch = 0.15;
  st.trailClock = 0;
  st.gone = 0;
  st.tn.fill(0);
  st.th.fill(0);
  st.done.fill(0);
  st.bounces.fill(0);
  st.alpha.array.fill(0);
  st.alpha.needsUpdate = true;
  st.onLaunch = onLaunch;
  st.onDone = onDone;
  const area = layout.area;
  st.bounds = {
    left: area.x - layout.cardW * 0.7,
    right: area.x + area.w + layout.cardW * 0.7,
    floor: area.y + area.h - layout.cardH * 0.5 - 2,
    cardW: layout.cardW,
  };
  st.running = true;
  st.mesh.visible = true;
}

export function stopCascade(st, motion) {
  st.running = false;
  st.mesh.visible = false;
  for (let i = 0; i < 52; i += 1) {
    motion.free[i] = 0;
    motion.visible[i] = 1;
  }
}

function launch(st, motion, card, k) {
  const w = st.bounds.cardW;
  const dir = rand(k * 3.1) < 0.5 ? -1 : 1;
  motion.free[card] = 1;
  motion.vx[card] = dir * w * (1.7 + rand(k * 5.7) * 2.1);
  motion.vy[card] = -w * (1.5 + rand(k * 2.3) * 5.5);
  motion.vz[card] = 0;
  motion.z[card] = 12 + k * 0.45;
  motion.flip[card] = 0;
  motion.lift[card] = 0;
  motion.tiltX[card] = 0;
  motion.tiltY[card] = 0;
  st.spin[card] = (rand(k * 9.1) - 0.5) * 0.5;
  st.tn[card] = 0;
  st.th[card] = 0;
}

/** Advances the cascade by dt seconds; returns whether it is still running. */
export function stepCascade(st, motion, dt) {
  if (!st.running) return false;
  st.clock += dt;
  while (st.launched < st.order.length && st.clock >= st.nextLaunch) {
    const card = st.order[st.launched];
    launch(st, motion, card, st.launched);
    st.launched += 1;
    st.nextLaunch += st.interval;
    if (st.onLaunch) st.onLaunch(card, st.launched, st.order.length);
  }
  const g = st.bounds.cardW * 16;
  st.trailClock += dt;
  const record = st.trailClock >= 0.034;
  if (record) st.trailClock = 0;
  for (let k = 0; k < st.launched; k += 1) {
    const i = st.order[k];
    if (st.done[i]) continue;
    motion.vy[i] += g * dt;
    motion.x[i] += motion.vx[i] * dt;
    motion.y[i] += motion.vy[i] * dt;
    motion.rot[i] += st.spin[i] * dt;
    if (motion.y[i] > st.bounds.floor && motion.vy[i] > 0) {
      motion.y[i] = st.bounds.floor;
      st.bounces[i] = Math.min(st.bounces[i] + 1, 20);
      // Each bounce keeps less of its height than the one before.
      const restitution = Math.max(0.35, 0.78 - st.bounces[i] * 0.07);
      motion.vy[i] = -motion.vy[i] * restitution;
      st.spin[i] *= 0.7;
    }
    if (record) {
      const slot = i * GHOSTS + st.th[i];
      st.tx[slot] = motion.x[i];
      st.ty[slot] = motion.y[i];
      st.tz[slot] = motion.z[i];
      st.tr[slot] = motion.rot[i];
      st.th[i] = (st.th[i] + 1) % GHOSTS;
      st.tn[i] = Math.min(GHOSTS, st.tn[i] + 1);
    }
    if (motion.x[i] < st.bounds.left || motion.x[i] > st.bounds.right) {
      st.done[i] = 1;
      motion.visible[i] = 0;
      st.tn[i] = 0;
      st.gone += 1;
    }
  }
  if (st.gone >= st.order.length) {
    st.running = false;
    st.mesh.visible = false;
    if (st.onDone) st.onDone();
    return false;
  }
  return true;
}

const tmpM = new THREE.Matrix4();
const tmpQ = new THREE.Quaternion();
const tmpP = new THREE.Vector3();
const tmpS = new THREE.Vector3(1, 1, 1);
const Z = new THREE.Vector3(0, 0, 1);

/** Writes the ghost quads; `toWorld(x, y, out)` maps screen pixels to table units. */
export function drawGhosts(st, toWorld, scale) {
  if (!st.mesh.visible) return;
  tmpS.set(scale, scale, 1);
  for (let i = 0; i < 52; i += 1) {
    for (let k = 0; k < GHOSTS; k += 1) {
      const slot = i * GHOSTS + k;
      // Age 1 is the newest ghost, GHOSTS the oldest.
      const age = (st.th[i] - k + GHOSTS - 1) % GHOSTS + 1;
      const live = k < st.tn[i] || st.tn[i] === GHOSTS;
      if (!live || st.tn[i] === 0 || age > st.tn[i]) {
        st.alpha.array[slot] = 0;
        continue;
      }
      toWorld(st.tx[slot], st.ty[slot], tmpP);
      tmpP.z = st.tz[slot] - 0.6 - age * 0.05;
      tmpQ.setFromAxisAngle(Z, -st.tr[slot]);
      tmpM.compose(tmpP, tmpQ, tmpS);
      st.mesh.setMatrixAt(slot, tmpM);
      st.face.array[slot] = i;
      st.alpha.array[slot] = 0.5 * (1 - (age - 1) / GHOSTS);
    }
  }
  st.mesh.instanceMatrix.needsUpdate = true;
  st.face.needsUpdate = true;
  st.alpha.needsUpdate = true;
}
