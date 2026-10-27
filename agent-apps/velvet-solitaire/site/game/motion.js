// How each card moves: a critically damped spring toward where it rests, an arc over the
// table while it travels, a tilt toward its motion, a flip with a lift, and a finger to follow
// while it is dragged. Both renderers draw what this holds; nothing here allocates per frame.

const N = 52;
const DEG = Math.PI / 180;

export function createMotion({ reduced = false } = {}) {
  const m = {
    reduced,
    // Current pose, CSS pixels for x and y, table units for z.
    x: new Float32Array(N),
    y: new Float32Array(N),
    z: new Float32Array(N),
    vx: new Float32Array(N),
    vy: new Float32Array(N),
    vz: new Float32Array(N),
    tx: new Float32Array(N),
    ty: new Float32Array(N),
    tz: new Float32Array(N),
    // Where the card rests, so a renderer knows how far off the felt it has risen.
    rz: new Float32Array(N),
    rot: new Float32Array(N),
    shade: new Float32Array(N).fill(1),
    trot: new Float32Array(N),
    tiltX: new Float32Array(N),
    tiltY: new Float32Array(N),
    // Flip angle: 0 is face up, PI face down.
    flip: new Float32Array(N),
    flipFrom: new Float32Array(N),
    flipTo: new Float32Array(N),
    flipT: new Float32Array(N).fill(1),
    flipDur: new Float32Array(N).fill(0.3),
    delay: new Float32Array(N),
    opacity: new Float32Array(N).fill(1),
    lift: new Float32Array(N),
    landing: new Uint8Array(N),
    dragging: new Uint8Array(N),
    held: new Uint8Array(N),
    // Cards the cascade flies; the springs leave them alone.
    free: new Uint8Array(N),
    visible: new Uint8Array(N).fill(1),
    pending: new Array(N).fill(null),
    stiffness: 19,
    onLand: null,
    active: true,
  };
  return m;
}

/** Puts every card at its target at once, with no motion (a restored game, a resize). */
export function snapAll(m, targets) {
  for (let i = 0; i < N; i += 1) {
    const t = targets[i];
    m.x[i] = m.tx[i] = t.x;
    m.y[i] = m.ty[i] = t.y;
    m.z[i] = m.tz[i] = m.rz[i] = t.z;
    m.rot[i] = m.trot[i] = t.rot;
    m.shade[i] = t.shade ?? 1;
    m.vx[i] = m.vy[i] = m.vz[i] = 0;
    m.tiltX[i] = m.tiltY[i] = 0;
    const a = t.up ? 0 : Math.PI;
    m.flip[i] = m.flipFrom[i] = m.flipTo[i] = a;
    m.flipT[i] = 1;
    m.delay[i] = 0;
    m.pending[i] = null;
    m.opacity[i] = 1;
    m.landing[i] = 0;
    m.free[i] = 0;
    m.visible[i] = 1;
  }
  m.active = true;
}

function startFlip(m, i, up, dur) {
  const to = up ? 0 : Math.PI;
  if (Math.abs(m.flipTo[i] - to) < 1e-3) return;
  m.flipFrom[i] = m.flip[i];
  m.flipTo[i] = to;
  m.flipT[i] = 0;
  m.flipDur[i] = dur;
}

function applyTarget(m, i, t, opts) {
  const moved = Math.abs(m.tx[i] - t.x) > 0.5 || Math.abs(m.ty[i] - t.y) > 0.5;
  m.tx[i] = t.x;
  m.ty[i] = t.y;
  m.tz[i] = t.z;
  m.rz[i] = t.z;
  m.trot[i] = t.rot;
  m.shade[i] = t.shade ?? 1;
  if (m.reduced && moved) {
    // Reduced motion: the card fades out where it was and in where it goes.
    m.x[i] = t.x;
    m.y[i] = t.y;
    m.z[i] = t.z;
    m.vx[i] = m.vy[i] = m.vz[i] = 0;
    m.opacity[i] = 0;
    m.flip[i] = m.flipFrom[i] = m.flipTo[i] = t.up ? 0 : Math.PI;
    m.flipT[i] = 1;
    return;
  }
  if (moved) m.landing[i] = 1;
  if (m.reduced) {
    m.flip[i] = m.flipFrom[i] = m.flipTo[i] = t.up ? 0 : Math.PI;
    m.flipT[i] = 1;
    return;
  }
  startFlip(m, i, t.up, opts.flipDur ?? 0.3);
  if (opts.kick && moved) m.vz[i] += opts.kick;
}

/**
 * Sends every card toward its resting target. `delays` (seconds per card, optional) staggers
 * a deal; `flipDur` sets how long a turn takes.
 */
export function setTargets(m, targets, opts = {}) {
  for (let i = 0; i < N; i += 1) {
    if (m.free[i]) continue;
    const t = targets[i];
    const d = opts.delays ? opts.delays[i] || 0 : 0;
    if (d > 0 && !m.reduced) {
      m.delay[i] = d;
      m.pending[i] = { t, opts };
    } else {
      m.delay[i] = 0;
      m.pending[i] = null;
      applyTarget(m, i, t, opts);
    }
  }
  m.active = true;
}

/** Holds a run of cards under the pointer; (x, y) is where the first card's center should be. */
export function dragTo(m, cards, x, y, fanStep) {
  for (let k = 0; k < cards.length; k += 1) {
    const i = cards[k];
    m.dragging[i] = 1;
    m.tx[i] = x;
    m.ty[i] = y + k * fanStep;
    m.tz[i] = 26 + k * 0.72;
  }
  m.active = true;
}

export function release(m, cards) {
  for (const i of cards) m.dragging[i] = 0;
  m.active = true;
}

/** Lifts a run a little off the table, as a keyboard pick does. */
export function hold(m, cards, on) {
  for (const i of cards) m.held[i] = on ? 1 : 0;
  m.active = true;
}

/** Advances every card by dt seconds. Returns whether anything is still moving. */
export function step(m, dt) {
  const w = m.stiffness;
  let moving = false;
  const maxTilt = 7 * DEG;
  for (let i = 0; i < N; i += 1) {
    if (m.free[i]) {
      moving = true;
      continue;
    }
    if (m.delay[i] > 0) {
      m.delay[i] -= dt;
      moving = true;
      if (m.delay[i] <= 0) {
        m.delay[i] = 0;
        const p = m.pending[i];
        m.pending[i] = null;
        if (p) applyTarget(m, i, p.t, p.opts);
      }
      continue;
    }
    if (m.opacity[i] < 1) {
      m.opacity[i] = Math.min(1, m.opacity[i] + dt / 0.18);
      moving = true;
    }
    let tz = m.tz[i] + (m.held[i] ? 10 : 0);
    if (m.dragging[i]) {
      // Follow the finger closely; the lag that remains is what tilts the card.
      const k = 1 - Math.exp(-dt * 34);
      const nx = m.x[i] + (m.tx[i] - m.x[i]) * k;
      const ny = m.y[i] + (m.ty[i] - m.y[i]) * k;
      m.vx[i] = (nx - m.x[i]) / Math.max(dt, 1e-4);
      m.vy[i] = (ny - m.y[i]) / Math.max(dt, 1e-4);
      m.x[i] = nx;
      m.y[i] = ny;
      tz = m.tz[i];
      moving = true;
    } else {
      // Critically damped: x'' = -w^2 (x - t) - 2 w x'.
      const dx = m.x[i] - m.tx[i];
      const dy = m.y[i] - m.ty[i];
      const dist = Math.hypot(dx, dy);
      m.vx[i] += (-w * w * dx - 2 * w * m.vx[i]) * dt;
      m.vy[i] += (-w * w * dy - 2 * w * m.vy[i]) * dt;
      m.x[i] += m.vx[i] * dt;
      m.y[i] += m.vy[i] * dt;
      // An arc over the table while the card travels, so it never drags through a pile.
      tz += Math.min(30, dist * 0.09);
      const speed = Math.abs(m.vx[i]) + Math.abs(m.vy[i]);
      if (dist > 0.3 || speed > 4) moving = true;
      if (m.landing[i] && dist < 2.5) {
        m.landing[i] = 0;
        if (m.onLand) m.onLand(i);
      }
    }
    // Height: a stiffer spring, so a dropped card settles onto the pile without bouncing.
    const wz = w * 1.25;
    const dz = m.z[i] - tz;
    m.vz[i] += (-wz * wz * dz - 2 * wz * m.vz[i]) * dt;
    m.z[i] += m.vz[i] * dt;
    if (Math.abs(dz) > 0.05 || Math.abs(m.vz[i]) > 0.5) moving = true;
    m.rot[i] += (m.trot[i] - m.rot[i]) * Math.min(1, dt * 12);
    // Tilt toward the motion, a few degrees at most.
    let gx = 0;
    let gy = 0;
    if (!m.reduced) {
      gx = Math.max(-maxTilt, Math.min(maxTilt, m.vy[i] * 0.00016));
      gy = Math.max(-maxTilt, Math.min(maxTilt, m.vx[i] * 0.00016));
    }
    const kt = Math.min(1, dt * 16);
    m.tiltX[i] += (gx - m.tiltX[i]) * kt;
    m.tiltY[i] += (gy - m.tiltY[i]) * kt;
    if (Math.abs(m.tiltX[i]) + Math.abs(m.tiltY[i]) > 1e-3) moving = true;
    // The turn: eased, lifting the card by its half-width times the sine of the turn, so it
    // pivots on its edge and never cuts into the pile under it.
    if (m.flipT[i] < 1) {
      m.flipT[i] = Math.min(1, m.flipT[i] + dt / m.flipDur[i]);
      const t = m.flipT[i];
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      m.flip[i] = m.flipFrom[i] + (m.flipTo[i] - m.flipFrom[i]) * e;
      m.lift[i] = 32 * Math.abs(Math.sin(m.flip[i])) + Math.sin(Math.PI * t) * 2;
      moving = true;
    } else {
      m.flip[i] = m.flipTo[i];
      m.lift[i] = 0;
    }
  }
  m.active = moving;
  return moving;
}

/** Whether any card is mid-move. */
export const busy = (m) => m.active;
