// The tank floor: a sand bank that rises toward the back glass, with rippled grain from a generated normal map and
// the caustic web moving across it.
import * as THREE from "three";
import { patchMaterial } from "./shading.js";
import { DEPTH_BACK, DEPTH_FRONT } from "./world.js";

export function sandHeight(x, z) {
  const back = THREE.MathUtils.clamp((DEPTH_FRONT - z) / (DEPTH_FRONT - DEPTH_BACK), 0, 1.4);
  return 0.95 * Math.pow(back, 1.4)
    + 0.13 * Math.sin(0.7 * x + 0.4 * z)
    + 0.06 * Math.sin(1.9 * x - 1.1 * z + 1.3)
    + 0.035 * Math.sin(3.3 * x + 2.3 * z + 0.4);
}

function hash(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

function valueNoise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

// Sand ripples: wavy parallel crests with grain, as a tiling height field turned into normals.
function rippleTextures(size, sand, sand2) {
  const h = new Float32Array(size * size);
  const tau = Math.PI * 2;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = x / size, v = y / size;
      const wave = Math.sin(tau * (u * 5 + 0.18 * Math.sin(tau * v * 2) + 0.07 * Math.sin(tau * (v * 3 + u))));
      const crest = Math.pow(wave * 0.5 + 0.5, 1.6);
      const grain = hash(x % size, y % size);
      h[y * size + x] = crest * 0.85 + grain * 0.12 + 0.2 * Math.sin(tau * (v * 2 + u)) * 0.5;
    }
  }
  const normal = new Uint8Array(size * size * 4);
  const color = new Uint8Array(size * size * 4);
  const a = sand.clone().convertLinearToSRGB();
  const b = sand2.clone().convertLinearToSRGB();
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = y * size + x;
      const l = h[y * size + ((x - 1 + size) % size)], r = h[y * size + ((x + 1) % size)];
      const d = h[((y - 1 + size) % size) * size + x], u = h[((y + 1) % size) * size + x];
      const nx = (l - r) * 2.2, ny = (d - u) * 2.2, nz = 1;
      const len = Math.hypot(nx, ny, nz);
      normal[i * 4] = ((nx / len) * 0.5 + 0.5) * 255;
      normal[i * 4 + 1] = ((ny / len) * 0.5 + 0.5) * 255;
      normal[i * 4 + 2] = ((nz / len) * 0.5 + 0.5) * 255;
      normal[i * 4 + 3] = 255;
      const patch = valueNoise((x / size) * 6, (y / size) * 6);
      const speck = hash(x * 3.1, y * 1.7) > 0.93 ? 0.35 : 0;
      const t = THREE.MathUtils.clamp(0.25 + patch * 0.45 + (1 - h[i]) * 0.25 + speck, 0, 1);
      color[i * 4] = (a.r + (b.r - a.r) * t) * 255;
      color[i * 4 + 1] = (a.g + (b.g - a.g) * t) * 255;
      color[i * 4 + 2] = (a.b + (b.b - a.b) * t) * 255;
      color[i * 4 + 3] = 255;
    }
  }
  const mk = (data, srgb) => {
    const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.generateMipmaps = true;
    tex.anisotropy = 4;
    if (srgb) tex.colorSpace = THREE.SRGBColorSpace;
    tex.needsUpdate = true;
    return tex;
  };
  return { normal: mk(normal, false), color: mk(color, true) };
}

export function createFloor(pal) {
  const tex = rippleTextures(256, pal.sand, pal.sand2);
  tex.color.repeat.set(7, 3.5);
  tex.normal.repeat.set(7, 3.5);
  const material = patchMaterial(new THREE.MeshStandardMaterial({
    map: tex.color,
    normalMap: tex.normal,
    normalScale: new THREE.Vector2(0.9, 0.9),
    roughness: 0.94,
    metalness: 0,
    envMapIntensity: 0.4,
  }), { caustic: 1.7, key: "sand" });
  let mesh = null;
  const group = new THREE.Group();

  function layout(frame) {
    if (mesh) {
      group.remove(mesh);
      mesh.geometry.dispose();
    }
    const w = Math.max(frame.backRect.x1 - frame.backRect.x0, 8) + 4;
    const z0 = DEPTH_BACK - 2.2, z1 = DEPTH_FRONT + 4;
    const geo = new THREE.PlaneGeometry(w, z1 - z0, 96, 40);
    geo.rotateX(-Math.PI / 2);
    geo.translate(0, 0, (z0 + z1) / 2);
    const p = geo.attributes.position;
    for (let i = 0; i < p.count; i++) p.setY(i, sandHeight(p.getX(i), p.getZ(i)));
    geo.computeVertexNormals();
    // world-scaled UVs keep the ripples the same size on every screen
    const uv = geo.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, p.getX(i) / 14, p.getZ(i) / 14);
    mesh = new THREE.Mesh(geo, material);
    mesh.renderOrder = -5;
    group.add(mesh);
  }

  return { group, layout, material };
}
