// The ship's core is the only hitbox: a distance test over the flat arrays. A shard that passes inside the graze
// ring without touching the core counts once as a graze.
import { GRAZED } from "./bullets.js";

/** Returns the index of the shard that hit the core, or -1; calls onGraze(i) for each new graze. */
export function collide(pool, sx, sy, coreR, grazeR, onGraze) {
  const { x, y, size, flags } = pool;
  const reach = grazeR + 1.5;
  const g2 = grazeR * grazeR;
  for (let i = 0; i < pool.count; i++) {
    const dx = x[i] - sx;
    if (dx > reach || dx < -reach) continue;
    const dy = y[i] - sy;
    if (dy > reach || dy < -reach) continue;
    const d2 = dx * dx + dy * dy;
    const hitR = coreR + 0.3 * size[i];
    if (d2 < hitR * hitR) return i;
    if (d2 < g2 && !(flags[i] & GRAZED)) {
      flags[i] |= GRAZED;
      onGraze(i);
    }
  }
  return -1;
}
