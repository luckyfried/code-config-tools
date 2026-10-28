// The chart for screens without WebGL: the same catalog and the same stereographic projection drawn with Canvas 2D,
// stars as dots sized by magnitude, constellation lines, the Moon and planets, and the ground.
import { apply, project } from "../scene/astro.js";

const css = (c) => `rgb(${Math.round(c[0] * 255)}, ${Math.round(c[1] * 255)}, ${Math.round(c[2] * 255)})`;

export function createChart(canvas, catalog, lineData, palette) {
  const g = canvas.getContext("2d");
  let p = palette;
  let dpr = Math.min(devicePixelRatio || 1, 2);
  const stars = catalog.stars;
  const segs = [];
  for (const f of catalog.lines.features) {
    const ci = catalog.conIndex.get(f.id);
    for (const line of f.geometry.coordinates) {
      for (let i = 0; i < line.length - 1; i += 1) segs.push([ci, line[i], line[i + 1]]);
    }
  }
  const D = Math.PI / 180;
  const vec = (ra, dec) => [Math.cos(dec * D) * Math.cos(ra * D), Math.cos(dec * D) * Math.sin(ra * D), Math.sin(dec * D)];
  const starVecs = stars.map((s) => vec(s.ra, s.dec));
  const segVecs = segs.map(([ci, a, b]) => [ci, vec(a[0], a[1]), vec(b[0], b[1])]);
  const w1 = [0, 0, 0], v1 = [0, 0, 0], w2 = [0, 0, 0], v2 = [0, 0, 0];
  const pa = { x: 0, y: 0, f: 0, visible: false };
  const pb = { x: 0, y: 0, f: 0, visible: false };

  return {
    resize(w, h) {
      dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    },
    setPalette(next) {
      p = next;
    },
    draw({ sky, view, k, width, height, conAlpha, bodies }) {
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      const cx = width / 2, cy = height / 2;
      const grad = g.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, css(p.nightZ));
      grad.addColorStop(1, css(p.nightH));
      g.fillStyle = grad;
      g.fillRect(0, 0, width, height);
      const ink = p.inkMode > 0.5;
      const starColor = ink || p.starMono > 0.5 ? css(p.starTint) : "rgb(240, 244, 255)";

      g.lineWidth = 1;
      for (const [ci, a, b] of segVecs) {
        const alpha = conAlpha[ci];
        if (alpha < 0.05) continue;
        apply(view, apply(sky, a, w1), v1);
        apply(view, apply(sky, b, w2), v2);
        if (w1[1] < 0 && w2[1] < 0) continue;
        project(v1, k, pa);
        project(v2, k, pb);
        if (!pa.visible || !pb.visible || pa.f < 0 || pb.f < 0) continue;
        g.strokeStyle = css(p.line);
        g.globalAlpha = alpha * 0.7;
        g.beginPath();
        g.moveTo(cx + pa.x, cy - pa.y);
        g.lineTo(cx + pb.x, cy - pb.y);
        g.stroke();
      }
      g.globalAlpha = 1;
      g.fillStyle = starColor;
      for (let i = 0; i < stars.length; i += 1) {
        apply(sky, starVecs[i], w1);
        if (w1[1] < 0) continue;
        apply(view, w1, v1);
        project(v1, k, pa);
        if (!pa.visible || pa.f < 0) continue;
        const r = Math.max(0.5, 3.1 - stars[i].mag * 0.45);
        g.globalAlpha = Math.min(1, 0.35 + (6 - stars[i].mag) * 0.16);
        g.beginPath();
        g.arc(cx + pa.x, cy - pa.y, r, 0, Math.PI * 2);
        g.fill();
      }
      g.globalAlpha = 1;
      if (bodies) {
        for (const name of ["Moon", "Venus", "Mars", "Jupiter", "Saturn", "Mercury"]) {
          apply(sky, bodies[name].dir, w1);
          if (w1[1] < 0) continue;
          project(apply(view, w1, v1), k, pa);
          if (!pa.visible || pa.f < 0) continue;
          g.fillStyle = name === "Moon" ? "rgb(236, 232, 220)" : css(p.light);
          g.beginPath();
          g.arc(cx + pa.x, cy - pa.y, name === "Moon" ? 9 : 3.5, 0, Math.PI * 2);
          g.fill();
        }
      }
      // Ground: everything below the horizon line.
      g.fillStyle = css(p.ground);
      g.beginPath();
      let started = false;
      const yaw = Math.atan2(-view[6], view[8]) / D;
      for (let az = yaw - 170; az <= yaw + 170; az += 2) {
        const a = az * D;
        const wv = [Math.sin(a), 0, -Math.cos(a)];
        project(apply(view, wv, v1), k, pa);
        if (!pa.visible || pa.f < -0.2) continue;
        const x = cx + pa.x, y = cy - pa.y;
        if (!started) { g.moveTo(x, y); started = true; } else g.lineTo(x, y);
      }
      if (started) {
        g.lineTo(width + 50, height + 50);
        g.lineTo(-50, height + 50);
        g.closePath();
        g.fill();
      }
    },
  };
}
