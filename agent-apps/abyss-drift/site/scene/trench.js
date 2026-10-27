// The trench: a winding tube of noise-displaced rock from the surface to the vent field, with vertex-color rock,
// emissive lichen that thickens with depth, hydrothermal chimneys, and their smoke.
// World units are meters; y is height, so a depth d sits at y = -d.
import * as THREE from "three";
import { ImprovedNoise } from "three/addons/math/ImprovedNoise.js";
import { underwater, shared, FOG_GLSL } from "./materials.js";
import { FLOOR_DEPTH } from "../game/species.js";

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** The trench's centerline and radius from the seed: the same numbers drive the rock, the creatures, and the sub. */
export function createTrenchShape(rng) {
  const ph = Array.from({ length: 6 }, () => rng.range(0, Math.PI * 2));
  const amp = [rng.range(10, 16), rng.range(4, 8), rng.range(10, 16), rng.range(4, 8)];
  const wobble = rng.range(0, 100);
  const center = (depth, out = new THREE.Vector2()) => {
    const d = Math.max(0, depth);
    out.set(
      amp[0] * Math.sin(d * 0.0085 + ph[0]) + amp[1] * Math.sin(d * 0.023 + ph[1]) - amp[0] * Math.sin(ph[0]) - amp[1] * Math.sin(ph[1]),
      amp[2] * Math.sin(d * 0.0075 + ph[2]) + amp[3] * Math.sin(d * 0.019 + ph[3]) - amp[2] * Math.sin(ph[2]) - amp[3] * Math.sin(ph[3]),
    );
    return out;
  };
  const radius = (depth) => {
    const d = Math.max(-10, depth);
    const top = 78 - 46 * smooth(0, 75, d);
    const mid = 4 * Math.sin(d * 0.021 + wobble);
    const vent = 18 * smooth(500, 585, d);
    return top + mid * smooth(40, 120, d) + vent;
  };
  return { center, radius, floorDepth: FLOOR_DEPTH, seedPhase: ph };
}

export function buildTrench({ shape, tier, tokens, rng }) {
  const group = new THREE.Group();
  group.name = "trench";
  const noise = new ImprovedNoise();
  const nOff = rng.range(0, 200);
  const W = tokens.world;

  // Wall: rings every ringStep meters, each with `segments` points pushed in and out by layered noise.
  const segs = tier.trenchSegments;
  const step = tier.ringStep;
  const top = -12;
  const bottom = FLOOR_DEPTH + 6;
  const rings = Math.ceil((bottom - top) / step) + 1;
  const count = rings * (segs + 1);
  const pos = new Float32Array(count * 3);
  const col = new Float32Array(count * 3);
  const lichen = new Float32Array(count);
  const uv = new Float32Array(count * 2);
  const c2 = new THREE.Vector2();
  const rockA = W.rockLight.clone();
  const rockB = W.rockDark.clone();
  const tmp = new THREE.Color();
  const sand = W.rockLight.clone().lerp(new THREE.Color(1, 0.95, 0.85), 0.35);
  let v = 0;
  for (let r = 0; r < rings; r++) {
    const depth = top + r * step;
    shape.center(depth, c2);
    const base = shape.radius(depth);
    for (let s = 0; s <= segs; s++) {
      const a = (s / segs) * Math.PI * 2;
      const ca = Math.cos(a), sa = Math.sin(a);
      // Large buttresses, mid-scale boulders, and horizontal strata ledges.
      const big = noise.noise(ca * 1.3 + nOff, sa * 1.3, depth * 0.018) * 9;
      const midN = noise.noise(ca * 3.1, sa * 3.1 + nOff, depth * 0.06) * 3.6;
      const fine = noise.noise(ca * 9 + nOff, sa * 9, depth * 0.2) * 1.1;
      const strata = Math.sign(Math.sin(depth * 0.42 + big * 0.3)) * Math.pow(Math.abs(Math.sin(depth * 0.42 + big * 0.3)), 0.25) * 0.9;
      const disp = big + midN + fine + strata;
      const rad = base + disp;
      pos[v * 3] = c2.x + ca * rad;
      pos[v * 3 + 1] = -depth;
      pos[v * 3 + 2] = c2.y + sa * rad;
      // Rock: lighter near the surface, darker and cooler below; crevices (pushed outward) darker still.
      const depthMix = smooth(-10, 420, depth);
      tmp.copy(rockA).lerp(rockB, depthMix * 0.8 + 0.1);
      const crevice = smooth(-2, 9, disp);
      tmp.multiplyScalar(1.05 - crevice * 0.55 + fine * 0.05);
      if (depth < 70) tmp.lerp(sand, 0.25 * (1 - depth / 70) * Math.max(0, -strata));
      col[v * 3] = tmp.r;
      col[v * 3 + 1] = tmp.g;
      col[v * 3 + 2] = tmp.b;
      // Lichen grows in patches and veins along the strata, sparse in the twilight and thick in the deep.
      const patch = noise.noise(ca * 4.2 + 50, sa * 4.2, depth * 0.09 + nOff);
      const vein = Math.pow(Math.max(0, 1 - Math.abs(Math.sin(depth * 0.42 + big * 0.3)) * 4), 3);
      const growth = smooth(35, 200, depth) * (1 - smooth(520, 600, depth) * 0.6);
      lichen[v] = Math.min(1.6, (smooth(0.12, 0.45, patch) * 1.2 + vein * 0.9 * smooth(0.0, 0.3, patch + 0.2)) * growth * (1 - crevice * 0.4));
      uv[v * 2] = s / segs;
      uv[v * 2 + 1] = depth / 40;
      v++;
    }
  }
  const index = [];
  for (let r = 0; r < rings - 1; r++) {
    for (let s = 0; s < segs; s++) {
      const a = r * (segs + 1) + s;
      const b = a + segs + 1;
      index.push(a, a + 1, b, a + 1, b + 1, b);
    }
  }
  const wallGeo = new THREE.BufferGeometry();
  wallGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  wallGeo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  wallGeo.setAttribute("aLichen", new THREE.BufferAttribute(lichen, 1));
  wallGeo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  wallGeo.setIndex(index);
  wallGeo.computeVertexNormals();
  flipNormalsInward(wallGeo, shape);

  const rockMat = underwater(
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.93, metalness: 0.0, side: THREE.DoubleSide }),
    { caustics: tier.caustics, lichen: W.lichen.clone().multiplyScalar(2.6), key: "rock", surface: true },
  );
  // Split the wall into depth bands so the camera only draws the stretch it can see.
  const bandRings = Math.max(8, Math.round(60 / step));
  for (let r0 = 0; r0 < rings - 1; r0 += bandRings) {
    const r1 = Math.min(rings - 1, r0 + bandRings);
    const g = new THREE.BufferGeometry();
    for (const [name, attr] of Object.entries(wallGeo.attributes)) g.setAttribute(name, attr);
    g.setIndex(index.slice(r0 * segs * 6, r1 * segs * 6));
    const d0 = top + r0 * step, d1 = top + r1 * step;
    shape.center((d0 + d1) / 2, c2);
    let maxR = 0;
    for (let d = d0; d <= d1; d += step) maxR = Math.max(maxR, shape.radius(d) + 30);
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(c2.x, -(d0 + d1) / 2, c2.y), Math.hypot((d1 - d0) / 2, maxR));
    const mesh = new THREE.Mesh(g, rockMat);
    mesh.name = "trenchWall";
    group.add(mesh);
  }

  // Floor: a noisy basin of basalt with sediment, warm near the vents.
  const floorY = -FLOOR_DEPTH;
  shape.center(FLOOR_DEPTH, c2);
  const floorCenter = c2.clone();
  const floorR = shape.radius(FLOOR_DEPTH) + 14;
  const vents = [];
  const ventCount = 6;
  for (let i = 0; i < ventCount; i++) {
    const a = (i / ventCount) * Math.PI * 2 + rng.range(-0.4, 0.4);
    const rr = rng.range(8, floorR * 0.55);
    vents.push({
      x: floorCenter.x + Math.cos(a) * rr,
      z: floorCenter.y + Math.sin(a) * rr,
      height: rng.range(7, 16),
      radius: rng.range(1.4, 2.6),
    });
  }
  const floorHeight = (x, z) => {
    let h = noise.noise(x * 0.06 + nOff, z * 0.06, 3.1) * 2.2 + noise.noise(x * 0.25, z * 0.25 + nOff, 7.7) * 0.45;
    for (const vt of vents) {
      const d = Math.hypot(x - vt.x, z - vt.z);
      h += Math.max(0, 1 - d / (vt.radius * 3.5)) * 1.6;
    }
    const edge = Math.hypot(x - floorCenter.x, z - floorCenter.y) / floorR;
    return floorY + h + smooth(0.75, 1.0, edge) * 6;
  };
  // A polar grid, so the noise has vertices to move.
  const polar = polarGrid(floorR, 26, 72);
  const fp = polar.attributes.position;
  const fcol = new Float32Array(fp.count * 3);
  const fl = new Float32Array(fp.count);
  for (let i = 0; i < fp.count; i++) {
    const x = fp.getX(i) + floorCenter.x;
    const z = fp.getZ(i) + floorCenter.y;
    const y = floorHeight(x, z);
    fp.setXYZ(i, x, y, z);
    let heat = 0;
    for (const vt of vents) heat = Math.max(heat, 1 - Math.hypot(x - vt.x, z - vt.z) / (vt.radius * 4));
    tmp.copy(rockB).multiplyScalar(0.9 + noise.noise(x * 0.4, z * 0.4, 1.3) * 0.4);
    tmp.lerp(new THREE.Color(0.55, 0.5, 0.42), Math.max(0, noise.noise(x * 0.12, z * 0.12, 9.1)) * 0.35);
    fcol[i * 3] = tmp.r;
    fcol[i * 3 + 1] = tmp.g;
    fcol[i * 3 + 2] = tmp.b;
    fl[i] = Math.pow(Math.max(0, heat), 2) * 0.9 + Math.max(0, noise.noise(x * 0.3, z * 0.3, 4.4) - 0.3) * 0.6;
  }
  polar.setAttribute("color", new THREE.BufferAttribute(fcol, 3));
  polar.setAttribute("aLichen", new THREE.BufferAttribute(fl, 1));
  polar.computeVertexNormals();
  const ventMat = underwater(
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0.05 }),
    { caustics: false, lichen: W.vent.clone().multiplyScalar(4.5), key: "vent" },
  );
  const floor = new THREE.Mesh(polar, ventMat);
  floor.name = "ventFloor";
  group.add(floor);

  // Chimneys: lathed stacks with knobbly mineral bands and glowing cracks near their mouths.
  const chimneyGeos = [];
  for (const vt of vents) {
    const pts = [];
    const n = 18;
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const r = vt.radius * (1 - t * 0.62) * (1 + 0.18 * Math.sin(t * 19 + vt.x) + 0.1 * noise.noise(t * 6, vt.z, 2));
      pts.push(new THREE.Vector2(Math.max(0.25, r), t * vt.height));
    }
    pts.push(new THREE.Vector2(0.2, vt.height - 0.3));
    const g = new THREE.LatheGeometry(pts, 20);
    const p = g.attributes.position;
    const cc = new Float32Array(p.count * 3);
    const ll = new Float32Array(p.count);
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
      const bump = noise.noise(x * 1.7 + vt.x, y * 1.2, z * 1.7) * 0.35;
      const len = Math.hypot(x, z) || 1;
      p.setXYZ(i, x + (x / len) * bump, y, z + (z / len) * bump);
      const t = y / vt.height;
      const band = 0.5 + 0.5 * Math.sin(y * 3.1 + bump * 4);
      tmp.copy(rockB).lerp(new THREE.Color(0.62, 0.52, 0.36), band * 0.4 * (1 - t));
      tmp.multiplyScalar(0.8 + bump);
      cc[i * 3] = tmp.r;
      cc[i * 3 + 1] = tmp.g;
      cc[i * 3 + 2] = tmp.b;
      const crack = Math.pow(Math.max(0, noise.noise(x * 2.4, y * 0.9 + vt.z, z * 2.4) + 0.05), 1.5) * 3;
      ll[i] = Math.min(1.8, crack * smooth(0.45, 1.0, t) + smooth(0.92, 1.0, t) * 1.5);
    }
    g.setAttribute("color", new THREE.BufferAttribute(cc, 3));
    g.setAttribute("aLichen", new THREE.BufferAttribute(ll, 1));
    g.computeVertexNormals();
    g.translate(vt.x, floorHeight(vt.x, vt.z) - 0.5, vt.z);
    vt.base = floorHeight(vt.x, vt.z) - 0.5;
    vt.top = vt.base + vt.height;
    chimneyGeos.push(g);
  }
  const chimneys = new THREE.Mesh(mergeGeometries(chimneyGeos), ventMat);
  chimneys.name = "chimneys";
  group.add(chimneys);

  // Smoke: one Points cloud for every vent, rising, widening, and fading; warm at the mouth.
  const perVent = tier.name === "high" ? 110 : 60;
  const sCount = perVent * vents.length;
  const sPos = new Float32Array(sCount * 3);
  const sSeed = new Float32Array(sCount * 4);
  for (let i = 0; i < sCount; i++) {
    const vt = vents[Math.floor(i / perVent)];
    sPos[i * 3] = vt.x;
    sPos[i * 3 + 1] = vt.top;
    sPos[i * 3 + 2] = vt.z;
    sSeed[i * 4] = rng.next();
    sSeed[i * 4 + 1] = rng.next();
    sSeed[i * 4 + 2] = rng.next();
    sSeed[i * 4 + 3] = rng.range(0.7, 1.3);
  }
  const smokeGeo = new THREE.BufferGeometry();
  smokeGeo.setAttribute("position", new THREE.BufferAttribute(sPos, 3));
  smokeGeo.setAttribute("aSeed", new THREE.BufferAttribute(sSeed, 4));
  const smokeMat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: shared.uTime,
      uVent: { value: W.vent.clone() },
      uPixel: { value: 1 },
      uFogDensity: shared.uFogDensity,
      uFogColor: shared.uFogColor,
    },
    vertexShader: /* glsl */ `
      attribute vec4 aSeed;
      uniform float uTime;
      uniform float uPixel;
      varying float vLife;
      varying float vDist;
      void main() {
        float life = fract(aSeed.x + uTime * 0.07 * aSeed.w);
        vec3 p = position;
        float rise = life * 34.0;
        float spread = 0.6 + life * 7.0;
        float a = aSeed.y * 6.2831 + life * 2.0;
        p += vec3(cos(a) * spread * aSeed.z + sin(uTime * 0.3 + aSeed.y * 9.0) * life * 2.5, rise, sin(a) * spread * aSeed.z);
        vLife = life;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vDist = -mv.z;
        gl_Position = projectionMatrix * mv;
        gl_PointSize = (2.0 + life * 13.0) * uPixel * 30.0 / max(1.0, -mv.z);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uVent;
      varying float vLife;
      varying float vDist;
      ${FOG_GLSL}
      void main() {
        vec2 c = gl_PointCoord - 0.5;
        float r = length(c);
        if (r > 0.5) discard;
        float soft = smoothstep(0.5, 0.0, r);
        vec3 smoke = mix(uVent * 3.0, uVent * 0.12 + vec3(0.06), smoothstep(0.0, 0.25, vLife));
        float alpha = soft * (1.0 - vLife) * smoothstep(0.0, 0.04, vLife) * 0.75;
        vec3 col = mix(smoke, uFogColor, fogFactor(vDist));
        gl_FragColor = vec4(col, alpha);
      }`,
    transparent: true,
    depthWrite: false,
  });
  const smoke = new THREE.Points(smokeGeo, smokeMat);
  smoke.name = "ventSmoke";
  smoke.frustumCulled = false;
  group.add(smoke);

  return {
    group,
    vents,
    floorHeight,
    rockMat,
    ventMat,
    smokeMat,
    setPixelRatio(pr) {
      smokeMat.uniforms.uPixel.value = pr;
    },
    setCameraDepth(depth) {
      for (const child of group.children) {
        if (child.name === "trenchWall") {
          const s = child.geometry.boundingSphere;
          child.visible = Math.abs(-s.center.y - depth) < s.radius + 140;
        }
      }
      const deep = depth > FLOOR_DEPTH - 180;
      floor.visible = deep;
      chimneys.visible = deep;
      smoke.visible = deep;
    },
  };
}

// The wall's triangles face the axis; computeVertexNormals follows the winding, so make sure every normal points in.
function flipNormalsInward(geo, shape) {
  const p = geo.attributes.position;
  const n = geo.attributes.normal;
  const c = new THREE.Vector2();
  let outward = 0;
  for (let i = 0; i < p.count; i += 97) {
    shape.center(-p.getY(i), c);
    const dx = p.getX(i) - c.x, dz = p.getZ(i) - c.y;
    outward += Math.sign(dx * n.getX(i) + dz * n.getZ(i));
  }
  if (outward > 0) {
    for (let i = 0; i < n.count; i++) n.setXYZ(i, -n.getX(i), -n.getY(i), -n.getZ(i));
  }
}

function polarGrid(radius, rings, segs) {
  const pos = [];
  const idx = [];
  pos.push(0, 0, 0);
  for (let r = 1; r <= rings; r++) {
    const rad = (r / rings) * radius;
    for (let s = 0; s < segs; s++) {
      const a = (s / segs) * Math.PI * 2;
      pos.push(Math.cos(a) * rad, 0, Math.sin(a) * rad);
    }
  }
  for (let s = 0; s < segs; s++) idx.push(0, 1 + ((s + 1) % segs), 1 + s);
  for (let r = 1; r < rings; r++) {
    const a0 = 1 + (r - 1) * segs, b0 = 1 + r * segs;
    for (let s = 0; s < segs; s++) {
      const s1 = (s + 1) % segs;
      idx.push(a0 + s, a0 + s1, b0 + s, a0 + s1, b0 + s1, b0 + s);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  return g;
}

/** Merges indexed or non-indexed geometries with matching attributes into one indexed geometry. */
export function mergeGeometries(geos) {
  const names = Object.keys(geos[0].attributes);
  const out = new THREE.BufferGeometry();
  let vertexCount = 0;
  const index = [];
  for (const g of geos) {
    const n = g.attributes.position.count;
    if (g.index) for (let i = 0; i < g.index.count; i++) index.push(g.index.getX(i) + vertexCount);
    else for (let i = 0; i < n; i++) index.push(i + vertexCount);
    vertexCount += n;
  }
  for (const name of names) {
    const size = geos[0].attributes[name].itemSize;
    const arr = new Float32Array(vertexCount * size);
    let o = 0;
    for (const g of geos) {
      const a = g.attributes[name];
      for (let i = 0; i < a.count; i++) for (let k = 0; k < size; k++) arr[o++] = a.array[i * size + k];
    }
    out.setAttribute(name, new THREE.BufferAttribute(arr, size));
  }
  out.setIndex(index);
  if (!out.attributes.normal) out.computeVertexNormals();
  return out;
}
