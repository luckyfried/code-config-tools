// Constellation figures as glowing hairlines: instanced screen-space quads, one per short arc piece, so a line
// keeps its width on every screen. Each constellation has its own opacity and a draw-on progress, so lines fade in
// as the view turns toward them and draw themselves from star to star.
import * as THREE from "three";
import { PROJECTION, MASK } from "./shaders.js";
import { eqVector } from "./astro.js";

export const MAX_CONSTELLATIONS = 89;

const VERTEX = /* glsl */ `
${PROJECTION}
attribute vec2 aCorner;
attribute vec3 aStart;
attribute vec3 aEnd;
attribute float aCon;
attribute vec2 aOrder;
attribute vec2 aTrim;
uniform float uAlpha[${MAX_CONSTELLATIONS}];
uniform float uDraw[${MAX_CONSTELLATIONS}];
uniform float uWidth;
uniform float uFeather;
uniform float uGap;
uniform float uMaster;
varying float vAcross;
varying float vAlpha;
varying float vHalfWidth;
varying vec2 vPage;

void main() {
  int ci = int(aCon + 0.5);
  float alpha = uAlpha[ci] * uMaster;
  float draw = uDraw[ci];
  float seg = clamp((draw - aOrder.x) / max(aOrder.y - aOrder.x, 1e-4), 0.0, 1.0);
  vec3 ws = uSky * aStart;
  vec3 we = uSky * aEnd;
  vec3 vs = uView * ws;
  vec3 ve = uView * we;
  if (alpha < 0.002 || seg <= 0.0 || -vs.z < -0.3 || -ve.z < -0.3) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    return;
  }
  vec2 ps = projPx(vs);
  vec2 pe = projPx(ve);
  vec2 full = pe - ps;
  float len = length(full);
  if (len < 0.001) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  vec2 dir = full / len;
  vec2 nrm = vec2(-dir.y, dir.x);
  float trimS = aTrim.x * min(uGap, len * 0.35);
  float trimE = aTrim.y * min(uGap, len * 0.35);
  float a0 = trimS;
  float a1 = max(a0, (len - trimE) * seg);
  float reach = uWidth * 0.5 + uFeather;
  vec2 p = ps + dir * mix(a0, a1, aCorner.x) + nrm * aCorner.y * reach;
  vAcross = aCorner.y * reach;
  vHalfWidth = uWidth * 0.5;
  float horizon = smoothstep(-0.02, 0.06, min(ws.y, we.y) + 0.04);
  vAlpha = alpha * horizon;
  vPage = vec2(p.x + uHalf.x, uHalf.y - p.y);
  gl_Position = pxToClip(p);
}
`;

const FRAGMENT = /* glsl */ `
uniform vec2 uHalf;
${MASK}
uniform vec3 uColor;
uniform float uGlow;
uniform float uInkMode;
uniform float uFeather;
varying float vAcross;
varying float vAlpha;
varying float vHalfWidth;
varying vec2 vPage;

void main() {
  float d = abs(vAcross);
  float core = 1.0 - smoothstep(vHalfWidth - 0.6, vHalfWidth + 0.6, d);
  float glow = exp(-d / max(uFeather * 0.45, 0.5)) * uGlow;
  float a = (core * 0.62 + glow) * vAlpha * (1.0 - maskAt(vPage));
  if (a < 0.002) discard;
  if (uInkMode > 0.5) {
    gl_FragColor = vec4(uColor, clamp(a, 0.0, 1.0));
  } else {
    gl_FragColor = vec4(uColor * a, 1.0);
  }
}
`;

const PIECE = 3.0 * (Math.PI / 180);

function slerp(a, b, t) {
  const dot = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
  const th = Math.acos(dot);
  if (th < 1e-6) return a.slice();
  const s = Math.sin(th);
  const wa = Math.sin((1 - t) * th) / s;
  const wb = Math.sin(t * th) / s;
  return [a[0] * wa + b[0] * wb, a[1] * wa + b[1] * wb, a[2] * wa + b[2] * wb];
}

// Turns d3-celestial's constellation lines into arc pieces, and finds each figure's center for the fade.
export function buildLineGeometry(linesData, conIndex) {
  const starts = [], ends = [], cons = [], orders = [], trims = [];
  const centers = new Array(MAX_CONSTELLATIONS).fill(null);
  for (const feature of linesData.features) {
    const ci = conIndex.get(feature.id);
    if (ci === undefined) continue;
    const pieces = [];
    let total = 0;
    const sum = [0, 0, 0];
    let count = 0;
    for (const line of feature.geometry.coordinates) {
      for (let i = 0; i < line.length - 1; i += 1) {
        const a = eqVector(line[i][0], line[i][1]);
        const b = eqVector(line[i + 1][0], line[i + 1][1]);
        const ang = Math.acos(Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2])));
        const n = Math.max(1, Math.ceil(ang / PIECE));
        for (let k = 0; k < n; k += 1) {
          const p0 = slerp(a, b, k / n);
          const p1 = slerp(a, b, (k + 1) / n);
          pieces.push({ p0, p1, len: ang / n, trim: [k === 0 ? 1 : 0, k === n - 1 ? 1 : 0] });
          total += ang / n;
        }
        sum[0] += a[0] + b[0]; sum[1] += a[1] + b[1]; sum[2] += a[2] + b[2];
        count += 2;
      }
    }
    const l = Math.hypot(sum[0], sum[1], sum[2]) || 1;
    let spread = 0;
    const c = [sum[0] / l, sum[1] / l, sum[2] / l];
    for (const line of feature.geometry.coordinates) {
      for (const pt of line) {
        const v = eqVector(pt[0], pt[1]);
        spread = Math.max(spread, Math.acos(Math.min(1, v[0] * c[0] + v[1] * c[1] + v[2] * c[2])));
      }
    }
    centers[ci] = { dir: c, spread };
    let acc = 0;
    for (const p of pieces) {
      starts.push(...p.p0);
      ends.push(...p.p1);
      cons.push(ci);
      orders.push(acc / total, (acc + p.len) / total);
      trims.push(...p.trim);
      acc += p.len;
    }
    if (count === 0) centers[ci] = null;
  }
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.setAttribute("aCorner", new THREE.Float32BufferAttribute([0, -1, 1, -1, 0, 1, 1, 1], 2));
  geometry.setIndex([0, 1, 2, 2, 1, 3]);
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(new Array(12).fill(0), 3));
  geometry.setAttribute("aStart", new THREE.InstancedBufferAttribute(new Float32Array(starts), 3));
  geometry.setAttribute("aEnd", new THREE.InstancedBufferAttribute(new Float32Array(ends), 3));
  geometry.setAttribute("aCon", new THREE.InstancedBufferAttribute(new Float32Array(cons), 1));
  geometry.setAttribute("aOrder", new THREE.InstancedBufferAttribute(new Float32Array(orders), 2));
  geometry.setAttribute("aTrim", new THREE.InstancedBufferAttribute(new Float32Array(trims), 2));
  geometry.instanceCount = cons.length;
  return { geometry, centers };
}

export function createLines(shared, geometry) {
  const uniforms = {
    ...shared,
    uAlpha: { value: new Float32Array(MAX_CONSTELLATIONS) },
    uDraw: { value: new Float32Array(MAX_CONSTELLATIONS) },
    uWidth: { value: 1.1 },
    uFeather: { value: 3.5 },
    uGap: { value: 5 },
    uGlow: { value: 0.22 },
    uMaster: { value: 1 },
    uColor: { value: new THREE.Vector3(0.55, 0.7, 1) },
    uInkMode: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  return {
    mesh,
    uniforms,
    setStyle(style, ink) {
      const art = style === "art";
      uniforms.uWidth.value = art ? 2.2 : 0.7;
      uniforms.uFeather.value = art ? 7 : 3;
      uniforms.uGlow.value = ink ? 0.04 : art ? 0.26 : 0.16;
      uniforms.uGap.value = art ? 4 : 2.4;
      uniforms.uInkMode.value = ink ? 1 : 0;
      material.blending = ink ? THREE.NormalBlending : THREE.AdditiveBlending;
      material.needsUpdate = true;
    },
  };
}
