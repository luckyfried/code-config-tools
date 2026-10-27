// The flock: fish stay inside the glass, schools hold together, and hungry fish find the food.
import { createFlock, addFish, stepFlock } from "../sim/boids.js";
import { createReport } from "./report.js";

const report = createReport();
const bounds = { x0: -5, x1: 5, y0: 1, y1: 6, z0: -2, z1: 2 };
const species = [{ speed: 1.1, school: 0.9, depthY: 3.5 }, { speed: 0.8, school: 0.1, depthY: 2.5 }];

function makeFlock() {
  const flock = createFlock(40);
  let s = 7;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 30; i++) addFish(flock, i < 20 ? 0 : 1, 0.6, -4 + rnd() * 8, 1.5 + rnd() * 4, -1.5 + rnd() * 3, rnd());
  return flock;
}

const flock = makeFlock();
const none = { food: new Float32Array(3), foodAlive: new Uint8Array(1), foodCount: 1 };
let outside = 0;
let fastest = 0;
for (let step = 0; step < 1200; step++) {
  stepFlock(flock, 1 / 60, { bounds, species, time: step / 60, slow: 1, ...none });
  for (let i = 0; i < flock.count; i++) {
    const x = flock.pos[i * 3], y = flock.pos[i * 3 + 1], z = flock.pos[i * 3 + 2];
    if (x < bounds.x0 - 0.6 || x > bounds.x1 + 0.6 || y < bounds.y0 - 0.6 || y > bounds.y1 + 0.6 || z < bounds.z0 - 0.6 || z > bounds.z1 + 0.6) outside++;
    fastest = Math.max(fastest, Math.hypot(flock.vel[i * 3], flock.vel[i * 3 + 1], flock.vel[i * 3 + 2]));
  }
}
report.check("every fish stays inside the glass for 20 seconds", outside === 0, `${outside} fish-frames outside`);
report.check("no fish swims faster than twice its kind's speed", fastest < 2.3, fastest.toFixed(2));

function spread(kind) {
  const pts = [];
  for (let i = 0; i < flock.count; i++) if (flock.kind[i] === kind) pts.push([flock.pos[i * 3], flock.pos[i * 3 + 1], flock.pos[i * 3 + 2]]);
  const c = pts.reduce((a, p) => a.map((v, k) => v + p[k] / pts.length), [0, 0, 0]);
  return pts.reduce((a, p) => a + Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]), 0) / pts.length;
}
report.check("the schooling kind swims closer together than the loner kind", spread(0) < spread(1), `${spread(0).toFixed(2)} against ${spread(1).toFixed(2)}`);

const hungry = makeFlock();
const food = new Float32Array([0, 3, 0, 2, 3.5, 0.5, -2, 3, -0.5]);
const alive = new Uint8Array([1, 1, 1]);
let eaten = 0;
let firstBite = -1;
for (let step = 0; step < 600 && eaten < 3; step++) {
  stepFlock(hungry, 1 / 60, { bounds, species, time: step / 60, slow: 1, food, foodAlive: alive, foodCount: 3, onEat: () => { eaten++; if (firstBite < 0) firstBite = step / 60; } });
}
report.check("hungry fish eat all three pellets within 10 seconds", eaten === 3, `${eaten} eaten`);
report.check("the first pellet is eaten within 2 seconds", firstBite >= 0 && firstBite <= 2, `${firstBite.toFixed(2)} s`);
report.done();
