// The planet: an icosphere displaced by the terrain's height function, faceted, colored per face by height, slope,
// and moisture, with ambient occlusion baked into the colors. It is cut into twenty chunks (one per icosahedron face)
// so the far side and anything outside the shadow camera are culled.
import * as THREE from "three";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { RADIUS } from "../game/generation.js";
import { terrainMaterial } from "./materials.js";

export function buildPlanet(terrain, colors, detail) {
  const base = mergeVertices(new THREE.IcosahedronGeometry(1, detail), 1e-6);
  const unit = base.attributes.position;
  const index = base.index.array;
  const vertCount = unit.count;

  const heights = new Float32Array(vertCount);
  const pos = new Float32Array(vertCount * 3);
  for (let i = 0; i < vertCount; i++) {
    let x = unit.getX(i);
    let y = unit.getY(i);
    let z = unit.getZ(i);
    const l = Math.hypot(x, y, z);
    x /= l; y /= l; z /= l;
    const h = terrain.height(x, y, z);
    heights[i] = h;
    const r = RADIUS + h;
    pos[i * 3] = x * r;
    pos[i * 3 + 1] = y * r;
    pos[i * 3 + 2] = z * r;
  }

  // Concavity from the neighbor mean: valleys darken, ridges lighten.
  const neighborSum = new Float32Array(vertCount);
  const neighborCount = new Uint16Array(vertCount);
  for (let f = 0; f < index.length; f += 3) {
    const a = index[f], b = index[f + 1], c = index[f + 2];
    neighborSum[a] += heights[b] + heights[c];
    neighborSum[b] += heights[a] + heights[c];
    neighborSum[c] += heights[a] + heights[b];
    neighborCount[a] += 2; neighborCount[b] += 2; neighborCount[c] += 2;
  }
  const ao = new Float32Array(vertCount);
  for (let i = 0; i < vertCount; i++) {
    const d = heights[i] - neighborSum[i] / neighborCount[i];
    ao[i] = THREE.MathUtils.clamp(0.9 + d * 1.6, 0.62, 1.08);
  }

  const faceCount = index.length / 3;
  const allPos = new Float32Array(faceCount * 9);
  const allNormal = new Float32Array(faceCount * 9);
  const allColor = new Float32Array(faceCount * 9);
  const wTree = new Float32Array(faceCount * 3);
  const wPine = new Float32Array(faceCount * 3);
  const wRock = new Float32Array(faceCount * 3);
  const wTuft = new Float32Array(faceCount * 3);
  const faceBiome = new Array(faceCount);

  const palette = {
    floor: colors.worldFloor, shore: colors.worldShore, meadow: colors.worldMeadow, forest: colors.worldForest,
    rock: colors.worldRock, snow: colors.worldSnow,
  };
  const va = new THREE.Vector3(), vb = new THREE.Vector3(), vc = new THREE.Vector3();
  const e1 = new THREE.Vector3(), e2 = new THREE.Vector3(), n = new THREE.Vector3(), center = new THREE.Vector3();
  const col = new THREE.Color();
  const hsl = { h: 0, s: 0, l: 0 };
  let jitter = 0x9e3779b9;
  const rnd = () => {
    jitter ^= jitter << 13; jitter ^= jitter >>> 17; jitter ^= jitter << 5;
    return ((jitter >>> 0) % 10000) / 10000;
  };

  for (let f = 0; f < faceCount; f++) {
    const ia = index[f * 3], ib = index[f * 3 + 1], ic = index[f * 3 + 2];
    va.fromArray(pos, ia * 3); vb.fromArray(pos, ib * 3); vc.fromArray(pos, ic * 3);
    e1.subVectors(vb, va); e2.subVectors(vc, va);
    n.crossVectors(e1, e2).normalize();
    center.addVectors(va, vb).add(vc).multiplyScalar(1 / 3);
    const h = (heights[ia] + heights[ib] + heights[ic]) / 3;
    const dir = center.clone().normalize();
    const flatness = n.dot(dir);
    const wet = terrain.moisture(dir.x, dir.y, dir.z);
    const biome = terrain.biome(h, flatness, wet);
    faceBiome[f] = biome;

    col.copy(palette[biome]);
    if (biome === "shore" && h > 0.16) col.lerp(palette.meadow, (h - 0.16) / 0.12 * 0.5);
    if (biome === "floor") col.lerp(palette.shore, THREE.MathUtils.clamp(1 + h / 1.2, 0, 1) * 0.55);
    if (biome === "meadow" || biome === "forest") col.lerp(palette.rock, THREE.MathUtils.clamp((h - 1.6) / 2.4, 0, 0.35));
    col.getHSL(hsl);
    col.setHSL(hsl.h + (rnd() - 0.5) * 0.012, hsl.s, THREE.MathUtils.clamp(hsl.l + (rnd() - 0.5) * 0.05, 0, 1));
    const shade = (ao[ia] + ao[ib] + ao[ic]) / 3;
    col.multiplyScalar(shade);

    const o = f * 9;
    allPos.set([va.x, va.y, va.z, vb.x, vb.y, vb.z, vc.x, vc.y, vc.z], o);
    for (let k = 0; k < 3; k++) {
      allNormal[o + k * 3] = n.x; allNormal[o + k * 3 + 1] = n.y; allNormal[o + k * 3 + 2] = n.z;
      allColor[o + k * 3] = col.r; allColor[o + k * 3 + 1] = col.g; allColor[o + k * 3 + 2] = col.b;
    }
    const flat = THREE.MathUtils.clamp((flatness - 0.8) / 0.2, 0, 1);
    const t = biome === "meadow" ? 0.35 * flat : 0;
    const p = biome === "forest" ? 1.6 * flat : biome === "meadow" ? 0.08 * flat : 0;
    const r = biome === "rock" ? 0.9 : biome === "meadow" ? 0.12 : biome === "shore" ? 0.1 : biome === "snow" ? 0.15 : 0;
    const g = biome === "meadow" ? 1 * flat : biome === "forest" ? 0.3 * flat : biome === "shore" && h > 0.1 ? 0.25 : 0;
    for (let k = 0; k < 3; k++) {
      wTree[f * 3 + k] = t; wPine[f * 3 + k] = p; wRock[f * 3 + k] = r; wTuft[f * 3 + k] = g;
    }
  }

  // The sampler mesh carries every face and the per-kind weights; it is never added to the scene.
  const full = new THREE.BufferGeometry();
  full.setAttribute("position", new THREE.BufferAttribute(allPos, 3));
  full.setAttribute("normal", new THREE.BufferAttribute(allNormal, 3));
  full.setAttribute("wTree", new THREE.BufferAttribute(wTree, 1));
  full.setAttribute("wPine", new THREE.BufferAttribute(wPine, 1));
  full.setAttribute("wRock", new THREE.BufferAttribute(wRock, 1));
  full.setAttribute("wTuft", new THREE.BufferAttribute(wTuft, 1));
  const samplerMesh = new THREE.Mesh(full);

  const group = new THREE.Group();
  group.name = "planet";
  const material = terrainMaterial();
  const perChunk = faceCount / 20;
  for (let c = 0; c < 20; c++) {
    const from = Math.round(c * perChunk) * 9;
    const to = Math.round((c + 1) * perChunk) * 9;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(allPos.slice(from, to), 3));
    g.setAttribute("normal", new THREE.BufferAttribute(allNormal.slice(from, to), 3));
    g.setAttribute("color", new THREE.BufferAttribute(allColor.slice(from, to), 3));
    g.computeBoundingSphere();
    const mesh = new THREE.Mesh(g, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
  base.dispose();

  return { group, samplerMesh, faceBiome };
}

// The sea shell carries the terrain height under each vertex so the shader can tint depth and draw the foam band.
export function buildSeaGeometry(terrain, detail) {
  const g = new THREE.IcosahedronGeometry(RADIUS, detail);
  const p = g.attributes.position;
  const depth = new Float32Array(p.count);
  const v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i).normalize();
    depth[i] = terrain.height(v.x, v.y, v.z);
  }
  g.setAttribute("aDepth", new THREE.BufferAttribute(depth, 1));
  return g;
}
