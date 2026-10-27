// Flocking for the tank: separation, alignment, cohesion, wall avoidance, a slow wander, a preferred depth, and a
// food attractor that draws hungry fish into a swirl around each pellet. Pure: typed arrays in and out, no DOM and no
// three.js, so tests/boids.html runs it headless.

export function createFlock(capacity) {
  return {
    capacity,
    count: 0,
    pos: new Float32Array(capacity * 3),
    vel: new Float32Array(capacity * 3),
    kind: new Uint8Array(capacity),
    size: new Float32Array(capacity),
    seed: new Float32Array(capacity),
    hungry: new Uint8Array(capacity),
    eating: new Float32Array(capacity),
  };
}

export function addFish(flock, kind, size, x, y, z, seed) {
  if (flock.count >= flock.capacity) return -1;
  const i = flock.count++;
  flock.pos.set([x, y, z], i * 3);
  const a = seed * Math.PI * 2;
  flock.vel.set([Math.cos(a) * 0.4, 0, Math.sin(a) * 0.2], i * 3);
  flock.kind[i] = kind;
  flock.size[i] = size;
  flock.seed[i] = seed;
  flock.hungry[i] = 1;
  flock.eating[i] = 0;
  return i;
}

export function clearFlock(flock) {
  flock.count = 0;
}

const R_NEAR = 2.2;

// env: { bounds: {x0, x1, y0, y1, z0, z1}, species: [{ speed, school, depthY }], time, slow,
//        food: Float32Array xyz, foodAlive: Uint8Array, foodCount, onEat(fish, pellet) }
export function stepFlock(flock, dt, env) {
  const { pos, vel, kind, size, seed, hungry, eating } = flock;
  const n = flock.count;
  const b = env.bounds;
  const slow = env.slow ?? 1;
  const t = env.time;
  const foodCount = env.foodCount || 0;
  for (let i = 0; i < n; i++) {
    const i3 = i * 3;
    const px = pos[i3], py = pos[i3 + 1], pz = pos[i3 + 2];
    let vx = vel[i3], vy = vel[i3 + 1], vz = vel[i3 + 2];
    const sp = env.species[kind[i]];
    const si = size[i];
    let sx = 0, sy = 0, sz = 0;
    let ax = 0, ay = 0, az = 0, cx = 0, cy = 0, cz = 0, same = 0;
    const r = R_NEAR + si;
    const r2 = r * r;
    for (let j = 0; j < n; j++) {
      if (j === i) continue;
      const j3 = j * 3;
      const dx = pos[j3] - px, dy = pos[j3 + 1] - py, dz = pos[j3 + 2] - pz;
      const d2 = dx * dx + dy * dy + dz * dz;
      if (d2 > r2 || d2 < 1e-8) continue;
      const d = Math.sqrt(d2);
      const room = (si + size[j]) * 0.75;
      if (d < room) {
        const push = (room - d) / room;
        sx -= (dx / d) * push;
        sy -= (dy / d) * push;
        sz -= (dz / d) * push;
      }
      if (kind[j] === kind[i]) {
        ax += vel[j3]; ay += vel[j3 + 1]; az += vel[j3 + 2];
        cx += pos[j3]; cy += pos[j3 + 1]; cz += pos[j3 + 2];
        same++;
      }
    }
    let fx = sx * 3.2, fy = sy * 3.2, fz = sz * 3.2;
    if (same > 0) {
      const w = sp.school;
      fx += (ax / same - vx) * 0.9 * w + (cx / same - px) * 0.42 * w;
      fy += (ay / same - vy) * 0.9 * w + (cy / same - py) * 0.42 * w;
      fz += (az / same - vz) * 0.9 * w + (cz / same - pz) * 0.42 * w;
    }
    // soft walls: the push grows as the fish nears a side
    const m = 1.1 + si * 0.5;
    if (px < b.x0 + m) fx += ((b.x0 + m - px) / m) * 4;
    if (px > b.x1 - m) fx -= ((px - (b.x1 - m)) / m) * 4;
    if (py < b.y0 + m * 0.6) fy += ((b.y0 + m * 0.6 - py) / m) * 4;
    if (py > b.y1 - m * 0.6) fy -= ((py - (b.y1 - m * 0.6)) / m) * 4;
    const mz = 0.8;
    if (pz < b.z0 + mz) fz += ((b.z0 + mz - pz) / mz) * 3;
    if (pz > b.z1 - mz) fz -= ((pz - (b.z1 - mz)) / mz) * 3;
    // each fish keeps to its own band of water
    fy += (sp.depthY - py) * 0.12;
    // a slow wander so a calm tank still moves
    const wa = t * (0.16 + seed[i] * 0.12) + seed[i] * 40;
    fx += Math.cos(wa) * 0.55;
    fy += Math.sin(wa * 1.7) * 0.18;
    fz += Math.sin(wa * 0.8) * 0.35;

    let maxSpeed = sp.speed * slow;
    eating[i] = Math.max(0, eating[i] - dt);
    if (hungry[i] && foodCount > 0) {
      let best = -1, bestD2 = 49;
      for (let k = 0; k < foodCount; k++) {
        if (!env.foodAlive[k]) continue;
        const dx = env.food[k * 3] - px, dy = env.food[k * 3 + 1] - py, dz = env.food[k * 3 + 2] - pz;
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < bestD2) { bestD2 = d2; best = k; }
      }
      if (best >= 0) {
        const dx = env.food[best * 3] - px, dy = env.food[best * 3 + 1] - py, dz = env.food[best * 3 + 2] - pz;
        const d = Math.sqrt(bestD2) || 1e-4;
        const pull = 4.2;
        fx += (dx / d) * pull; fy += (dy / d) * pull; fz += (dz / d) * pull;
        // a turn around the pellet: the swirl
        if (d < 2.4) {
          const dir = seed[i] > 0.5 ? 1 : -1;
          const swirl = 2.6 * (1 - d / 2.4);
          fx += (-dz / d) * swirl * dir;
          fz += (dx / d) * swirl * dir;
        }
        maxSpeed *= 1.7;
        if (d < 0.22 + si * 0.28) {
          env.foodAlive[best] = 0;
          eating[i] = 0.6;
          if (env.onEat) env.onEat(i, best);
        }
      }
    }

    vx += fx * dt; vy += fy * dt; vz += fz * dt;
    // fish swim level: vertical speed stays a fraction of the whole
    vy *= 1 - Math.min(1, dt * 1.4);
    let s = Math.hypot(vx, vy, vz);
    const minSpeed = maxSpeed * 0.32;
    if (s > maxSpeed) { const k = maxSpeed / s; vx *= k; vy *= k; vz *= k; s = maxSpeed; }
    else if (s < minSpeed) {
      if (s < 1e-5) { vx = minSpeed; s = minSpeed; }
      else { const k = minSpeed / s; vx *= k; vy *= k; vz *= k; s = minSpeed; }
    }
    const vyMax = s * 0.55;
    if (vy > vyMax) vy = vyMax; else if (vy < -vyMax) vy = -vyMax;
    vel[i3] = vx; vel[i3 + 1] = vy; vel[i3 + 2] = vz;
    pos[i3] = Math.min(b.x1, Math.max(b.x0, px + vx * dt));
    pos[i3 + 1] = Math.min(b.y1, Math.max(b.y0, py + vy * dt));
    pos[i3 + 2] = Math.min(b.z1, Math.max(b.z0, pz + vz * dt));
  }
}
