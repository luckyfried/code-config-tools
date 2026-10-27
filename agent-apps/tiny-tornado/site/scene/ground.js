// The ground: one painted map of the county (roads, lanes, pastures, crop rows, yards, and lawns) on a wide plane
// whose rim rises into low hills under the fog. A second, smaller map holds where grass grows and how tall, for the
// grass blades to read. Both maps are painted on canvases from the town's layout and repainted on a theme change.
import * as THREE from "three";
import { TOWN_EDGE, ROAD_WIDTH } from "../game/generation.js";

export const GROUND_SIZE = 640;
const MAP_PX = 2048;
const DENSITY_PX = 512;

export function hillHeight(x, z) {
  const r = Math.hypot(x, z);
  const rise = Math.min(1, Math.max(0, (r - 150) / 120));
  const wave = Math.sin(x * 0.021) * Math.cos(z * 0.017) * 0.5 + Math.sin(x * 0.047 + z * 0.031) * 0.3 + 0.6;
  return rise * rise * (10 + wave * 26);
}

export function createGround({ town, tokens, rnd, anisotropy }) {
  const map = document.createElement("canvas");
  map.width = map.height = MAP_PX;
  const dens = document.createElement("canvas");
  dens.width = dens.height = DENSITY_PX;
  const mapTexture = new THREE.CanvasTexture(map);
  mapTexture.colorSpace = THREE.SRGBColorSpace;
  mapTexture.anisotropy = anisotropy;
  mapTexture.generateMipmaps = true;
  mapTexture.minFilter = THREE.LinearMipmapLinearFilter;
  const densityTexture = new THREE.CanvasTexture(dens);
  densityTexture.colorSpace = THREE.NoColorSpace;

  // Speckle for the far fields, fixed per town.
  const speckles = [];
  for (let i = 0; i < 2600; i++) speckles.push([rnd() * GROUND_SIZE - GROUND_SIZE / 2, rnd() * GROUND_SIZE - GROUND_SIZE / 2, 0.6 + rnd() * 2.2, rnd()]);
  const outerFields = [];
  for (let gx = -320; gx < 320; gx += 44) {
    for (let gz = -320; gz < 320; gz += 40) {
      if (Math.abs(gx + 22) < TOWN_EDGE + 10 && Math.abs(gz + 20) < TOWN_EDGE + 10) continue;
      outerFields.push({ x0: gx + 1, z0: gz + 1, x1: gx + 43, z1: gz + 39, k: Math.floor(rnd() * 5), rows: rnd() < 0.5 ? "x" : "z" });
    }
  }

  const css = (c) => `#${c.getHexString(THREE.SRGBColorSpace)}`;

  function paint(t) {
    const g = map.getContext("2d");
    const s = MAP_PX / GROUND_SIZE;
    const X = (x) => (x + GROUND_SIZE / 2) * s;
    const rect = (r, color) => {
      g.fillStyle = color;
      g.fillRect(X(r.x0), X(r.z0), (r.x1 - r.x0) * s, (r.z1 - r.z0) * s);
    };
    const c = t.colors;
    g.fillStyle = css(c.groundHill);
    g.fillRect(0, 0, MAP_PX, MAP_PX);
    const cropColor = { cropA: c.groundCropA, cropB: c.groundCropB, cropC: c.groundCropC, cropD: c.groundCropD };
    const outerKinds = [c.groundCropA, c.groundCropB, c.groundCropC, c.groundPasture2, c.groundCropD];
    const rows = (f, base) => {
      rect(f, css(base));
      const dark = base.clone().multiplyScalar(0.82);
      g.strokeStyle = css(dark);
      g.lineWidth = Math.max(1, 0.55 * s);
      g.beginPath();
      if (f.rows === "x") for (let z = f.z0 + 0.9; z < f.z1; z += 1.8) { g.moveTo(X(f.x0), X(z)); g.lineTo(X(f.x1), X(z)); }
      else for (let x = f.x0 + 0.9; x < f.x1; x += 1.8) { g.moveTo(X(x), X(f.z0)); g.lineTo(X(x), X(f.z1)); }
      g.stroke();
    };
    for (const f of outerFields) rows(f, outerKinds[f.k]);
    rect({ x0: -TOWN_EDGE, z0: -TOWN_EDGE, x1: TOWN_EDGE, z1: TOWN_EDGE }, css(c.groundPasture2));
    for (const f of town.fields) rows(f, cropColor[f.kind]);
    for (const p of town.pastures) rect(p, css(c.groundPasture));
    for (const l of town.lawns) rect(l, css(c.groundLawn));
    for (const y of town.yards) rect(y, css(c.groundYard));
    for (const l of town.lanes) rect(l, css(c.groundLane));
    for (const [x, z, r, k] of speckles) {
      g.fillStyle = css(k < 0.5 ? c.groundPasture : c.groundHill.clone().multiplyScalar(0.88));
      g.globalAlpha = 0.35;
      g.beginPath();
      g.arc(X(x), X(z), r * s, 0, Math.PI * 2);
      g.fill();
    }
    g.globalAlpha = 1;
    const half = ROAD_WIDTH / 2;
    rect({ x0: -GROUND_SIZE / 2, z0: -half, x1: GROUND_SIZE / 2, z1: half }, css(c.groundRoad));
    rect({ x0: -half, z0: -GROUND_SIZE / 2, x1: half, z1: GROUND_SIZE / 2 }, css(c.groundRoad));
    g.fillStyle = css(c.groundLane);
    for (let x = -GROUND_SIZE / 2; x < GROUND_SIZE / 2; x += 6) {
      if (Math.abs(x) > half + 1) {
        g.fillRect(X(x), X(-0.12), 3 * s, 0.24 * s);
        g.fillRect(X(-0.12), X(x), 0.24 * s, 3 * s);
      }
    }
    mapTexture.needsUpdate = true;

    const d = dens.getContext("2d");
    const ds = DENSITY_PX / GROUND_SIZE;
    const DX = (x) => (x + GROUND_SIZE / 2) * ds;
    const drect = (r, v) => {
      d.fillStyle = `rgb(${v},${v},${v})`;
      d.fillRect(DX(r.x0), DX(r.z0), (r.x1 - r.x0) * ds, (r.z1 - r.z0) * ds);
    };
    d.fillStyle = "rgb(150,150,150)";
    d.fillRect(0, 0, DENSITY_PX, DENSITY_PX);
    for (const f of outerFields) drect(f, f.k === 3 ? 200 : f.k === 0 ? 255 : 40);
    drect({ x0: -TOWN_EDGE, z0: -TOWN_EDGE, x1: TOWN_EDGE, z1: TOWN_EDGE }, 190);
    for (const f of town.fields) drect(f, f.kind === "cropA" ? 255 : f.kind === "cropC" ? 150 : 30);
    for (const p of town.pastures) drect(p, 230);
    for (const l of town.lawns) drect(l, 120);
    for (const y of town.yards) drect(y, 0);
    for (const l of town.lanes) drect(l, 0);
    drect({ x0: -GROUND_SIZE / 2, z0: -half - 0.6, x1: GROUND_SIZE / 2, z1: half + 0.6 }, 0);
    drect({ x0: -half - 0.6, z0: -GROUND_SIZE / 2, x1: half + 0.6, z1: GROUND_SIZE / 2 }, 0);
    densityTexture.needsUpdate = true;
  }

  const geometry = new THREE.PlaneGeometry(GROUND_SIZE, GROUND_SIZE, 120, 120);
  geometry.rotateX(-Math.PI / 2);
  const pos = geometry.getAttribute("position");
  for (let i = 0; i < pos.count; i++) pos.setY(i, hillHeight(pos.getX(i), pos.getZ(i)));
  geometry.computeVertexNormals();
  const material = new THREE.MeshStandardMaterial({ map: mapTexture, roughness: 0.95, metalness: 0 });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.receiveShadow = true;
  paint(tokens);

  return {
    mesh,
    mapTexture,
    densityTexture,
    applyTokens: paint,
  };
}
