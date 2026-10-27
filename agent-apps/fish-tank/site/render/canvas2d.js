// The tank drawn flat, for a browser without WebGL: the same water colors, sand, plants, and flock, with food that
// sinks and fish that chase it. Pearls go straight to the counter.
import { createFlock, addFish, stepFlock } from "../sim/boids.js";

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export function createFlat(canvas, catalog, fishList) {
  const ctx = canvas.getContext("2d");
  const kinds = catalog.species;
  const kindOf = new Map(kinds.map((s, i) => [s.id, i]));
  const flock = createFlock(60);
  const bounds = { x0: 0.6, x1: 9.4, y0: 1.2, y1: 5.6, z0: -0.5, z1: 0.5 };
  const env = {
    bounds,
    species: kinds.map((s) => ({ speed: s.speed, school: s.school, depthY: 1.2 + 4.4 * s.depth })),
    time: 0, slow: 1, food: new Float32Array(32 * 3), foodAlive: new Uint8Array(32), foodCount: 32, onEat: null,
  };
  let foodNext = 0;
  let scale = 1;
  let w = 1, h = 1;
  const colors = {
    water: css("--scene-noon-water"), deep: css("--scene-noon-deep"), sand: css("--scene-sand"),
    sand2: css("--scene-sand2"), plant: css("--scene-plant"), tip: css("--scene-plant-tip"), food: css("--scene-food"),
    ray: css("--scene-ray"),
  };

  function sync(list) {
    flock.count = 0;
    list.slice(0, 30).forEach((f, n) => {
      const k = kindOf.get(f.sp);
      if (k === undefined) return;
      const s = kinds[k];
      addFish(flock, k, s.size, 1 + ((n * 2.7) % 8), env.species[k].depthY, 0, (f.id * 0.618) % 1);
    });
  }
  sync(fishList);

  function resize(width, height, dpr) {
    w = width;
    h = height;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    scale = width / 10;
    bounds.y1 = Math.min(5.6, (height / scale) * 0.82);
  }

  const X = (x) => x * scale;
  const Y = (y) => h - y * scale - h * 0.08;

  function feed(px) {
    for (let k = 0; k < 5; k++) {
      const i = foodNext++ % 32;
      env.food.set([px / scale + (Math.random() - 0.5) * 0.8, bounds.y1, 0], i * 3);
      env.foodAlive[i] = 1;
    }
  }

  function frame(dt, time) {
    env.time = time;
    for (let i = 0; i < 32; i++) {
      if (!env.foodAlive[i]) continue;
      env.food[i * 3 + 1] -= dt * 0.4;
      if (env.food[i * 3 + 1] < 0.4) env.foodAlive[i] = 0;
    }
    stepFlock(flock, dt, env);
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, colors.water);
    g.addColorStop(1, colors.deep);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = colors.ray;
    ctx.beginPath();
    ctx.moveTo(w * 0.2, 0); ctx.lineTo(w * 0.38, 0); ctx.lineTo(w * 0.5, h); ctx.lineTo(w * 0.12, h);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = colors.sand;
    ctx.fillRect(0, h * 0.86, w, h * 0.14);
    ctx.strokeStyle = colors.plant;
    ctx.lineWidth = Math.max(3, w * 0.006);
    for (let k = 0; k < 14; k++) {
      const x = (k < 7 ? 0.03 + k * 0.025 : 0.8 + (k - 7) * 0.025) * w;
      const sway = Math.sin(time * 0.9 + k) * 18;
      ctx.beginPath();
      ctx.moveTo(x, h * 0.88);
      ctx.quadraticCurveTo(x + sway * 0.5, h * 0.7, x + sway, h * (0.48 + (k % 3) * 0.06));
      ctx.stroke();
    }
    ctx.fillStyle = colors.food;
    for (let i = 0; i < 32; i++) {
      if (!env.foodAlive[i]) continue;
      ctx.beginPath();
      ctx.arc(X(env.food[i * 3]), Y(env.food[i * 3 + 1]), 3, 0, Math.PI * 2);
      ctx.fill();
    }
    for (let i = 0; i < flock.count; i++) {
      const s = kinds[flock.kind[i]];
      const x = X(flock.pos[i * 3]), y = Y(flock.pos[i * 3 + 1]);
      const dir = flock.vel[i * 3] >= 0 ? 1 : -1;
      const len = flock.size[i] * scale * 0.9, hgt = len * s.body.height * 1.1;
      const wag = Math.sin(time * s.freq * 6 + i) * hgt * 0.4;
      ctx.fillStyle = s.colors.fin;
      ctx.beginPath();
      ctx.moveTo(x - dir * len * 0.4, y);
      ctx.lineTo(x - dir * len * 0.8, y - hgt * 0.7 + wag);
      ctx.lineTo(x - dir * len * 0.8, y + hgt * 0.7 + wag);
      ctx.fill();
      ctx.fillStyle = s.colors.base;
      ctx.beginPath();
      ctx.ellipse(x, y, len * 0.5, hgt, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = s.colors.eye;
      ctx.beginPath();
      ctx.arc(x + dir * len * 0.3, y - hgt * 0.2, Math.max(1.5, hgt * 0.16), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  return { resize, frame, feed, sync };
}
