// Joins geometries that share one material into one draw, keeping position, normal, uv, and color.
import * as THREE from "three";

export function paint(geometry, color) {
  const g = geometry.index ? geometry.toNonIndexed() : geometry;
  const count = g.attributes.position.count;
  const colors = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }
  g.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return g;
}

export function merge(geometries) {
  const parts = geometries.map((g) => (g.index ? g.toNonIndexed() : g));
  let total = 0;
  for (const g of parts) total += g.attributes.position.count;
  const out = new THREE.BufferGeometry();
  const names = ["position", "normal", "uv", "color"];
  for (const name of names) {
    const first = parts.find((g) => g.attributes[name]);
    if (!first) continue;
    const size = first.attributes[name].itemSize;
    const array = new Float32Array(total * size);
    let offset = 0;
    for (const g of parts) {
      const attr = g.attributes[name];
      const n = g.attributes.position.count;
      if (attr) {
        for (let i = 0; i < n * size; i++) array[offset * size + i] = attr.array[i];
      } else if (name === "color") {
        array.fill(1, offset * size, (offset + n) * size);
      }
      offset += n;
    }
    out.setAttribute(name, new THREE.BufferAttribute(array, size));
  }
  out.computeBoundingSphere();
  return out;
}

export function softSprite(size = 128, inner = 0.0, lumps = 0) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  const r = size / 2;
  if (lumps > 0) {
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < lumps; i++) {
      const a = rand() * Math.PI * 2;
      const d = rand() * r * 0.3;
      const x = r + Math.cos(a) * d;
      const y = r + Math.sin(a) * d;
      const rr = r * (0.3 + rand() * 0.25);
      const g = ctx.createRadialGradient(x, y, 0, x, y, rr);
      g.addColorStop(0, "rgba(255,255,255,0.32)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, size, size);
    }
  } else {
    const g = ctx.createRadialGradient(r, r, 0, r, r, r);
    g.addColorStop(0, "rgba(255,255,255,1)");
    g.addColorStop(Math.max(0.01, inner), "rgba(255,255,255,0.85)");
    g.addColorStop(0.45, "rgba(255,255,255,0.22)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}
