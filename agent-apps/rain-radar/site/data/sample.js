// The sample loop: frames run.py draws (rain cells drifting east), with a wind field and a forecast to match.
// It plays with ?demo=1, with "sample": true in the setup, and whenever none of the live feeds answer.
import { loadImage } from "./tiles.js";

export async function sampleFrames() {
  const res = await fetch("./sample/frames.json");
  if (!res.ok) throw new Error("no sample");
  const list = await res.json();
  const now = Math.round(Date.now() / 60000) * 60000;
  const images = await Promise.all(list.files.map((f) => loadImage(`./sample/${f}`)));
  return list.offsets.map((off, i) => ({
    time: now + off * 1000,
    nowcast: off > 0,
    image: images[i],
    ok: true,
  }));
}

export function sampleForecast() {
  const u = new Float32Array(49);
  const v = new Float32Array(49);
  const cloud = new Float32Array(49);
  for (let j = 0; j < 7; j++) {
    for (let i = 0; i < 7; i++) {
      const k = j * 7 + i;
      const x = i / 6 - 0.5;
      const y = 0.5 - j / 6;
      // a westerly flow bending around a low to the north
      const dx = x + 0.1;
      const dy = y - 0.85;
      const r2 = dx * dx + dy * dy;
      const swirl = 5.5 / (0.35 + r2);
      u[k] = 6.2 + (-dy / Math.sqrt(r2)) * swirl * 0.35 + Math.sin(y * 7.0) * 1.2;
      v[k] = 1.4 + (dx / Math.sqrt(r2)) * swirl * 0.35 + Math.cos(x * 6.0) * 1.0;
      cloud[k] = Math.min(1, Math.max(0, 0.55 + 0.4 * Math.sin(x * 5 + 1.1) * Math.cos(y * 4 - 0.4) - x * 0.5));
    }
  }
  const start = Math.round(Date.now() / 60000) * 60000;
  const rates = [0, 0.4, 2.8, 3.4, 2.2, 1.0, 0.3, 0];
  const minutely = rates.map((rate, i) => ({ time: start + i * 15 * 60 * 1000, rate }));
  const speed = Math.hypot(u[24], v[24]);
  const from = (Math.atan2(-u[24], -v[24]) * 180) / Math.PI;
  return { u, v, cloud, minutely, windNow: { speed, from: (from + 360) % 360 } };
}
