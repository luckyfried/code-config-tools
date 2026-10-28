// The pilot that flies the ship behind the title: it scores a handful of headings against where nearby shards will
// be over the next half second, likes to pass close for grazes, and drifts home between threats.
const CANDIDATES = [[0, 0]];
for (let k = 0; k < 12; k++) {
  const a = (k / 12) * Math.PI * 2;
  CANDIDATES.push([Math.cos(a), Math.sin(a)], [Math.cos(a) * 0.45, Math.sin(a) * 0.45]);
}
const HORIZONS = [0.1, 0.22, 0.38, 0.55];
const NEAR = 22;

export function createPilot(capacity) {
  const near = new Int32Array(capacity);
  let vx = 0;
  let vy = 0;
  let best = 0;
  let plan = 0;
  return {
    reset() {
      vx = 0;
      vy = 0;
      plan = 0;
    },
    /** Returns the velocity to fly at this step, as [vx, vy] in world units per second. */
    steer(pool, sx, sy, hx, hy, W, H, speed, dt) {
      // It re-plans every other step, 30 times a second: the horizons look half a second ahead, so the plan holds.
      if (plan++ % 2 === 0) best = choose(pool, sx, sy, hx, hy, W, H, speed);
      const k = Math.min(1, dt * 14);
      vx += (CANDIDATES[best][0] * speed - vx) * k;
      vy += (CANDIDATES[best][1] * speed - vy) * k;
      return [vx, vy];
    },
  };

  /** The index of the candidate heading with the lowest cost. */
  function choose(pool, sx, sy, hx, hy, W, H, speed) {
    const { x, y, cos, sin, s } = pool;
    let n = 0;
    for (let i = 0; i < pool.count; i++) {
      const dx = x[i] - sx;
      const dy = y[i] - sy;
      if (dx < NEAR && dx > -NEAR && dy < NEAR && dy > -NEAR) near[n++] = i;
    }
    let choice = 0;
    let bestCost = Infinity;
    for (let c = 0; c < CANDIDATES.length; c++) {
      const cx = CANDIDATES[c][0] * speed;
      const cy = CANDIDATES[c][1] * speed;
      let cost = 0;
      for (let h = 0; h < HORIZONS.length; h++) {
        const t = HORIZONS[h];
        const px = Math.max(-W + 3, Math.min(W - 3, sx + cx * t));
        const py = Math.max(-H + 3, Math.min(H - 6, sy + cy * t));
        const weight = 1 / (h + 1);
        for (let j = 0; j < n; j++) {
          const i = near[j];
          const bx = x[i] + cos[i] * s[i] * t - px;
          const by = y[i] + sin[i] * s[i] * t - py;
          const d2 = bx * bx + by * by;
          if (d2 < 2.2) cost += 400 * weight;
          else if (d2 < 9) cost += (6 / d2) * weight;
          else if (d2 < 20) cost -= 0.35 * weight;
        }
        if (h === HORIZONS.length - 1) {
          const ex = px - hx;
          const ey = py - hy;
          cost += 0.03 * (ex * ex + ey * ey);
          if (Math.abs(px) > W - 6 || py < -H * 0.72 || py > H - 10) cost += 6;
        }
      }
      if (cost < bestCost) {
        bestCost = cost;
        choice = c;
      }
    }
    return choice;
  }
}
