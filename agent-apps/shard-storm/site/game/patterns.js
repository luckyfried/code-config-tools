// The eight patterns. Each is one exported function that returns an emitter: `step(dt, c)` fires shards through
// `c.fire(x, y, heading, speed, targetSpeed, easeRate, turn, size, color)`. The context carries the field's half
// size (c.W, c.H), the pattern's anchor (c.ax, c.ay), the ship (c.sx, c.sy), the wave's density (c.level), a speed
// scale (c.speed), how hard to emit right now (c.emit, 0 to 1), a seeded generator (c.rng), and the palette:
// c.color(u) blends the theme's first shard color into its second, c.accent(u, k) pulls a color toward the third.
// A new pattern is one more function here and one more line in PATTERNS.
import { easeInOutSine } from "./ease.js";

const TAU = Math.PI * 2;

/** Calls `fire` once per `interval` of emitting time; returns the leftover so emission is frame-rate independent. */
function every(state, dt, emit, interval, fire) {
  state.acc += dt * emit;
  while (state.acc >= interval) {
    state.acc -= interval;
    fire();
  }
}

const angleGap = (a, b) => Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b)));

/** Rings that burst out fast and settle into slow five-petal blooms, turning as they go. */
export function lotus() {
  const st = { acc: 0 };
  let t = 0;
  let phase = 0;
  let ring = 0;
  return {
    name: "Lotus",
    step(dt, c) {
      t += dt;
      phase += dt * (0.2 + 0.16 * easeInOutSine((Math.sin(t * 0.35) + 1) / 2));
      every(st, dt, c.emit, 0.2 / Math.sqrt(c.level), () => {
        ring++;
        const n = Math.round(42 + 13 * c.level);
        const base = (10.5 + 2.2 * c.level) * c.speed;
        const twist = ring % 2 ? 0.06 : -0.06;
        const u = ring % 2 ? 0.08 : 0.92;
        for (let k = 0; k < n; k++) {
          const th = phase + (k / n) * TAU;
          const petal = Math.pow(Math.abs(Math.cos(2.5 * (th - phase * 1.7))), 1.5);
          const target = base * (0.42 + 0.58 * petal);
          c.fire(c.ax, c.ay, th, target * 2.4, target, 2.2, twist, 0.95 + 0.25 * petal, c.accent(u, petal * petal * 0.75));
        }
      });
    },
  };
}

/** Six arms swing one way, slow, and swing back, with a counter-wheel underneath. */
export function vortex() {
  const st = { acc: 0 };
  let t = 0;
  let rot = 0;
  let counter = 0;
  return {
    name: "Vortex",
    step(dt, c) {
      t += dt;
      const swing = Math.sin(t * 0.42);
      rot += dt * 2.3 * swing;
      counter -= dt * (0.9 + 0.5 * Math.cos(t * 0.3));
      every(st, dt, c.emit, 0.05 / Math.sqrt(c.level), () => {
        const s = (12 + 2 * c.level) * c.speed;
        for (let a = 0; a < 6; a++) {
          const th = rot + (a * TAU) / 6;
          c.fire(c.ax, c.ay, th, s * 0.55, s, 1.6, 0.11 * Math.sign(swing || 1), 1, c.color(a / 5));
        }
        for (let a = 0; a < 4; a++) {
          const th = counter + (a * TAU) / 4 + 0.4;
          c.fire(c.ax, c.ay, th, s * 0.4, s * 0.7, 1.2, -0.12, 0.8, c.accent(0.5, 0.6));
        }
      });
    },
  };
}

/** Shards fall from the top edge, leaving one winding channel that drifts side to side. */
export function rain() {
  const st = { acc: 0 };
  let t = 0;
  return {
    name: "Rain",
    step(dt, c) {
      t += dt;
      const lane = c.W * 0.55 * Math.sin(t * 0.45);
      const half = 6.5;
      const slant = 0.16 * Math.sin(t * 0.3);
      every(st, dt, c.emit, 1 / (95 * c.level), () => {
        let x = c.rng.range(-c.W - 4, c.W + 4);
        if (Math.abs(x - lane) < half) x = lane + Math.sign(x - lane || 1) * (half + c.rng.range(0, 3));
        const s = c.rng.range(15, 25) * c.speed;
        c.fire(x, c.H + 6, -Math.PI / 2 + slant, s, s, 0, 0, c.rng.range(0.8, 1.25), c.color((x + c.W) / (2 * c.W)));
      });
    },
  };
}

/** Two emitters circle each other, each spinning a four-arm spiral the other way round. */
export function twinSpirals() {
  const st = { acc: 0 };
  let t = 0;
  let spin = 0;
  return {
    name: "Twin Spirals",
    step(dt, c) {
      t += dt;
      spin += dt * (1.5 + 0.5 * Math.sin(t * 0.5));
      const orbit = t * 0.55;
      const R = Math.min(c.W * 0.42, 38);
      every(st, dt, c.emit, 0.055 / Math.sqrt(c.level), () => {
        const s = (11 + 2 * c.level) * c.speed;
        for (const side of [1, -1]) {
          const ex = c.ax + side * R * Math.cos(orbit);
          const ey = c.ay + side * R * 0.45 * Math.sin(orbit);
          for (let k = 0; k < 4; k++) {
            const th = side * spin + (k * TAU) / 4;
            c.fire(ex, ey, th, s * 0.5, s, 1.4, side * 0.08, 0.95, c.color(side > 0 ? 0.04 : 0.96));
          }
        }
      });
    },
  };
}

/** Falling teeth that sway together; halfway through, a second comb crosses from the side. */
export function comb() {
  const down = { acc: 0 };
  const across = { acc: 0 };
  let t = 0;
  return {
    name: "Comb",
    step(dt, c) {
      t += dt;
      const gap = 10;
      const off = gap * easeInOutSine((Math.sin(t * 0.7) + 1) / 2);
      every(down, dt, c.emit, 0.12 / Math.sqrt(c.level), () => {
        const s = 17 * c.speed;
        for (let x = -c.W - gap + off; x <= c.W + gap; x += gap) c.fire(x, c.H + 6, -Math.PI / 2, s, s, 0, 0, 0.9, c.color(0.12));
      });
      if (t > 4) {
        const rowGap = 15;
        const yOff = rowGap * easeInOutSine((Math.sin(t * 0.5 + 1) + 1) / 2);
        every(across, dt, c.emit, 0.16 / Math.sqrt(c.level), () => {
          const s = 14 * c.speed;
          for (let y = -c.H - rowGap + yOff; y <= c.H * 0.35; y += rowGap) c.fire(-c.W - 6, y, 0, s, s, 0, 0, 0.9, c.color(0.88));
        });
      }
    },
  };
}

/** Rings burst from points across the top, each with its opening turned toward the ship. */
export function pulseRings() {
  const st = { acc: 0 };
  let ring = 0;
  return {
    name: "Pulse Rings",
    step(dt, c) {
      every(st, dt, c.emit, 0.62 / Math.pow(c.level, 0.45), () => {
        ring++;
        const ox = c.ax + c.rng.range(-c.W * 0.55, c.W * 0.55);
        const oy = c.ay + c.rng.range(-c.H * 0.08, c.H * 0.18);
        const aim = Math.atan2(c.sy - oy, c.sx - ox);
        const n = Math.round(58 + 12 * c.level);
        const s = (14 + 1.5 * c.level) * c.speed;
        const u = ring % 2 ? 0.1 : 0.9;
        for (let k = 0; k < n; k++) {
          const th = aim + (k / n) * TAU;
          if (angleGap(th, aim) < 0.36) continue;
          c.fire(ox, oy, th, s * 0.35, s, 1.1, 0, 1.05, c.accent(u, ring % 3 === 0 ? 0.7 : 0));
        }
      });
    },
  };
}

/** A loose sprinkle from the middle, and three emitters that fire fans straight at the ship. */
export function scatter() {
  const sprinkle = { acc: 0 };
  const fans = [{ acc: 0.0 }, { acc: 0.25 }, { acc: 0.5 }];
  let t = 0;
  return {
    name: "Scatter",
    step(dt, c) {
      t += dt;
      every(sprinkle, dt, c.emit, 1 / (70 * c.level), () => {
        const s = c.rng.range(6, 12) * c.speed;
        c.fire(c.ax, c.ay, c.rng.range(0, TAU), s * 1.8, s, 1.5, c.rng.range(-0.15, 0.15), c.rng.range(0.7, 1.1), c.color(c.rng.next()));
      });
      fans.forEach((fan, i) => {
        const ex = c.ax + (i - 1) * Math.min(c.W * 0.6, 50);
        const ey = c.ay + c.H * 0.12 + Math.sin(t * 1.3 + i * 2) * 4;
        every(fan, dt, c.emit, 0.75, () => {
          const aim = Math.atan2(c.sy - ey, c.sx - ex);
          const s = (17 + 1.5 * c.level) * c.speed;
          for (let k = -3; k <= 3; k++) c.fire(ex, ey, aim + k * 0.15, s * 1.5, s, 2, 0, 1.15, c.accent(0.5, 0.85));
        });
      });
    },
  };
}

/** Rows that fill the width and fall, each with one gap that wanders from row to row. */
export function wall() {
  const st = { acc: 0 };
  let gap = 0;
  let goal = 0;
  let row = 0;
  return {
    name: "Wall",
    step(dt, c) {
      every(st, dt, c.emit, 0.62 / Math.sqrt(c.level), () => {
        row++;
        if (row % 3 === 1) goal = c.rng.range(-c.W + 10, c.W - 10);
        gap += Math.max(-7, Math.min(7, goal - gap));
        const half = 6;
        const s = 12.5 * c.speed;
        const step = 2.4;
        const shift = row % 2 ? 0 : step / 2;
        for (let x = -c.W - 4 + shift; x <= c.W + 4; x += step) {
          if (Math.abs(x - gap) < half) continue;
          c.fire(x, c.H + 6, -Math.PI / 2, s, s, 0, 0, 0.95, c.color(row % 2 ? 0.25 : 0.75));
        }
      });
    },
  };
}

export const PATTERNS = {
  Lotus: lotus,
  Vortex: vortex,
  Rain: rain,
  "Twin Spirals": twinSpirals,
  Comb: comb,
  "Pulse Rings": pulseRings,
  Scatter: scatter,
  Wall: wall,
};

export const PATTERN_NAMES = Object.keys(PATTERNS);
