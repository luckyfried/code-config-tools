// Fish: each species is a parameter set (body profile, fins, tail shape, colors, markings) turned into one
// geometry, drawn as an InstancedMesh. A traveling sine wave along the spine, stronger toward the tail, bends every
// vertex in the vertex shader, so each fish swims rather than slides; the markings are painted in the fragment shader.
import * as THREE from "three";
import { shared, causticVertexHead, causticVertexBody, causticFragmentHead, causticFragmentBody } from "./shading.js";

const TAU = Math.PI * 2;

function profile(spec) {
  const b = spec.body;
  const peak = b.peak;
  const half = (d) => {
    if (d >= peak) {
      const s = Math.min(1, (1 - d) / (1 - peak));
      return Math.max(0.05, Math.pow(Math.sin((s * Math.PI) / 2), 1 / b.nose));
    }
    const s = d / peak;
    return b.stalk + (1 - b.stalk) * Math.pow(Math.sin((s * Math.PI) / 2), 0.9);
  };
  const top = (d) => b.height * half(d);
  const bump = (d) => Math.sin(Math.PI * THREE.MathUtils.clamp((d - 0.12) / 0.8, 0, 1));
  const bottom = (d) => b.height * half(d) * (1 + ((b.belly ?? 1) - 1) * bump(d));
  const width = (d) => b.height * half(d) * b.flat * (d > 0.6 ? 1 + (d - 0.6) * 0.3 : 1);
  return { top, bottom, width };
}

class Builder {
  constructor() {
    this.pos = []; this.d = []; this.v = []; this.part = []; this.idx = []; this.nrm = [];
  }
  add(geo, part) {
    // geo: { pos: [], d: [], v: [], idx: [] } in one part, normals computed within the part only
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(geo.pos, 3));
    g.setIndex(geo.idx);
    g.computeVertexNormals();
    // a vertex where a ring closes to a point gets a zero normal; it faces outward from the fish's spine instead
    const n = g.attributes.normal.array;
    for (let i = 0; i < n.length; i += 3) {
      if (Math.hypot(n[i], n[i + 1], n[i + 2]) > 1e-6) continue;
      const x = geo.pos[i], y = geo.pos[i + 1];
      const len = Math.hypot(x, y) || 1;
      n[i] = Math.hypot(x, y) > 1e-6 ? x / len : 0;
      n[i + 1] = Math.hypot(x, y) > 1e-6 ? y / len : 1;
      n[i + 2] = 0;
    }
    const base = this.pos.length / 3;
    this.pos.push(...geo.pos);
    this.nrm.push(...g.attributes.normal.array);
    this.d.push(...geo.d);
    this.v.push(...geo.v);
    for (let i = 0; i < geo.d.length; i++) this.part.push(part);
    for (const i of geo.idx) this.idx.push(base + i);
    g.dispose();
  }
  build() {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(this.pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(this.nrm, 3));
    g.setAttribute("aD", new THREE.Float32BufferAttribute(this.d, 1));
    g.setAttribute("aV", new THREE.Float32BufferAttribute(this.v, 1));
    g.setAttribute("aPart", new THREE.Float32BufferAttribute(this.part, 1));
    g.setIndex(this.idx);
    g.computeBoundingSphere();
    g.boundingSphere.radius += 0.4;
    return g;
  }
}

// a grid of (cols+1) x (rows+1) vertices from a function of (c, r) in [0, 1]^2
function grid(cols, rows, fn) {
  const pos = [], d = [], v = [], idx = [];
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c <= cols; c++) {
      const p = fn(c / cols, r / rows);
      pos.push(p[0], p[1], p[2]);
      d.push(p[2] + 0.5);
      v.push(p[3]);
    }
  }
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const a = r * (cols + 1) + c;
      idx.push(a, a + 1, a + cols + 1, a + 1, a + cols + 2, a + cols + 1);
    }
  }
  return { pos, d, v, idx };
}

export function fishGeometry(spec) {
  const pr = profile(spec);
  const b = new Builder();
  const rings = 30, seg = 18, n = 2.5;
  // body: superellipse rings from the stalk (d = 0) to the nose (d = 1), z = d - 0.5
  {
    const pos = [], d = [], v = [], idx = [];
    for (let i = 0; i <= rings; i++) {
      const dd = i / rings;
      const z = dd - 0.5;
      const t = pr.top(dd), bo = pr.bottom(dd), w = pr.width(dd);
      for (let j = 0; j <= seg; j++) {
        const th = (j / seg) * TAU;
        const s = Math.sin(th), c = Math.cos(th);
        const x = Math.sign(s) * Math.pow(Math.abs(s), 2 / n) * w;
        const yy = Math.sign(c) * Math.pow(Math.abs(c), 2 / n);
        const y = yy >= 0 ? yy * t : yy * bo;
        pos.push(x, y, z);
        d.push(dd);
        v.push(yy);
      }
    }
    for (let i = 0; i < rings; i++) {
      for (let j = 0; j < seg; j++) {
        const a = i * (seg + 1) + j, c2 = a + seg + 1;
        idx.push(a, c2, a + 1, a + 1, c2, c2 + 1);
      }
    }
    b.add({ pos, d, v, idx }, 0);
  }
  // tail
  {
    const tl = spec.tail;
    const sh = spec.body.height * spec.body.stalk;
    const spread = tl.size * (tl.shape === "fan" ? 1.25 : 1.05);
    const L = (av) => {
      switch (tl.shape) {
        case "round": return 0.55 + 0.45 * Math.sqrt(Math.max(0, 1 - av * av));
        case "fork": return 0.42 + 0.78 * Math.pow(av, 1.3);
        case "spade": return 0.72 + 0.4 * av * av;
        case "lyre": return 0.38 + 1.35 * Math.pow(av, 3);
        default: return 0.82 + 0.25 * av;
      }
    };
    const g = grid(8, 6, (c, r) => {
      const vv = c * 2 - 1;
      const y = vv * (sh + (spread - sh) * Math.pow(r, 0.65));
      const z = -0.5 - r * tl.size * L(Math.abs(vv)) * 1.15;
      return [0, y, z, r];
    });
    b.add(g, 1);
  }
  // dorsal and anal fins
  const fin = (f, up) => {
    if (!f) return;
    const span = f.to - f.from;
    const hp = (c) => {
      if (f.streamer) return 0.14 + 0.86 * Math.exp(-Math.pow((c - 0.86) / 0.11, 2));
      if (f.sail) return Math.pow(Math.sin(Math.PI * (0.12 + 0.88 * c)), 0.35) * (0.55 + 0.45 * c);
      let h = Math.pow(Math.sin(Math.PI * c), 0.55);
      if (f.notch) h *= 1 - f.notch * 0.6 * Math.exp(-Math.pow((c - 0.5) / 0.12, 2));
      return h;
    };
    const rake = f.streamer ? 1.1 : f.sail ? 0.7 : 0.35;
    const g = grid(10, 4, (c, r) => {
      const dd = f.from + span * c;
      const base = up ? pr.top(dd) - 0.008 : -pr.bottom(dd) + 0.008;
      const h = f.height * hp(c) * r;
      return [0, base + (up ? h : -h), dd - 0.5 - h * rake, r];
    });
    b.add(g, 1);
  };
  fin(spec.dorsal, true);
  fin(spec.anal, false);
  // pectoral fins, one each side
  {
    const p = spec.pectoral || 0.1;
    const dd = 0.7;
    const y0 = -pr.bottom(dd) * 0.25;
    for (const side of [-1, 1]) {
      const x0 = side * pr.width(dd) * 0.92;
      const g = grid(3, 3, (c, r) => {
        const z = dd - 0.5 + 0.05 - c * 0.08 - r * p * 0.9;
        const y = y0 - c * p * 0.35 + r * 0.02;
        const x = x0 + side * r * p * 0.45;
        return [x, y, z, r];
      });
      b.add(g, 2);
    }
  }
  // a glowing lure on a stalk: over the head, or hanging from the chin
  if (spec.lure) {
    const len = spec.lure.length;
    const chin = spec.lure.from === "chin";
    const start = chin ? [0, -pr.bottom(0.94), 0.44] : [0, pr.top(0.86), 0.36];
    const path = (t) => chin
      ? [0, start[1] - Math.sin(t * 1.4) * len * 0.7, start[2] - t * len * 0.55]
      : [0, start[1] + Math.sin(t * 2.2) * len * 0.42, start[2] + t * len * 0.75];
    const rr = 0.012;
    const g = grid(5, 10, (c, r) => {
      const p = path(r);
      const a = c * TAU;
      return [p[0] + Math.cos(a) * rr, p[1] + Math.sin(a) * rr, p[2], 0];
    });
    b.add(g, 3);
    const end = path(1);
    const bulb = grid(8, 6, (c, r) => {
      const th = r * Math.PI, ph = c * TAU, br = 0.07;
      return [end[0] + Math.sin(th) * Math.cos(ph) * br, end[1] + Math.cos(th) * br, end[2] + Math.sin(th) * Math.sin(ph) * br, 1];
    });
    b.add(bulb, 4);
  }
  const geo = b.build();
  const eyeD = 0.89 - (spec.body.nose < 1.3 ? 0.03 : 0);
  geo.userData.eye = [eyeD - 0.5, pr.top(eyeD) * 0.3, THREE.MathUtils.clamp(spec.body.height * 0.17, 0.034, 0.07)];
  return geo;
}

const col = (hex, fallback = "#000000") => new THREE.Color(hex || fallback);

export function fishMaterial(spec, eye) {
  const m = new THREE.MeshStandardMaterial({
    side: THREE.DoubleSide,
    roughness: spec.rough ?? 0.35,
    metalness: spec.metal ?? 0.1,
    envMapIntensity: 1.1,
  });
  const c = spec.colors;
  const bands = spec.bands || { at: [], width: [], color: "#ffffff", edge: "#000000", edgeWidth: 0 };
  const glow = spec.glow || {};
  const u = {
    uWiggle: { value: 0.07 * (spec.wiggle ?? 1) },
    uWaveK: { value: 5.0 },
    uBase: { value: col(c.base) }, uBelly: { value: col(c.belly) }, uFin: { value: col(c.fin) },
    uFinEdge: { value: col(c.finEdge) }, uEyeColor: { value: col(c.eye) },
    uGlowColor: { value: col(glow.color, c.base) },
    uBands: { value: new THREE.Vector4(bands.at[0] ?? -9, bands.at[1] ?? -9, bands.at[2] ?? -9, bands.at.length) },
    uBandW: { value: new THREE.Vector4(bands.width[0] ?? 0, bands.width[1] ?? 0, bands.width[2] ?? 0, bands.edgeWidth ?? 0) },
    uBandColor: { value: col(bands.color) }, uBandEdge: { value: col(bands.edge) },
    uMark: { value: new THREE.Vector4(spec.mark?.from ?? 0, spec.mark?.to ?? 0, spec.mark?.v ?? 0, spec.mark?.arc ?? 0) },
    uMarkW: { value: new THREE.Vector2(spec.mark?.width ?? 0, spec.mark ? 1 : 0) },
    uMarkColor: { value: col(spec.mark?.color) }, uMarkGlow: { value: glow.mark ?? 0 },
    uRear: { value: new THREE.Vector4(spec.rear?.from ?? 0, spec.rear?.to ?? 0, spec.rear?.vMax ?? 1, spec.rear ? 1 : 0) },
    uRearColor: { value: col(spec.rear?.color) },
    uLine: { value: new THREE.Vector4(spec.line?.v ?? 0, spec.line?.width ?? 0, spec.line?.from ?? 0, spec.line?.to ?? 0) },
    uLineX: { value: new THREE.Vector3(spec.line?.repeat ?? 1, spec.line?.glow ?? 0, spec.line ? 1 : 0) },
    uLineColor: { value: col(spec.line?.color) },
    uSpots: { value: new THREE.Vector4(spec.spots?.scale ?? 1, spec.spots?.threshold ?? 2, spec.spots?.glow ?? 0, spec.spots?.below ?? 9) },
    uSpotColor: { value: col(spec.spots?.color) }, uSpotOn: { value: spec.spots ? 1 : 0 },
    uEye: { value: new THREE.Vector4(eye[0], eye[1], eye[2], glow.eye ?? 0) },
    uLureGlow: { value: glow.lure ?? 0 },
  };
  m.userData.uniforms = u;
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, shared, u);
    shader.defines = { ...(shader.defines || {}), CAUSTIC_GAIN: "0.55" };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", /* glsl */ `#include <common>
        ${causticVertexHead}
        attribute float aD;
        attribute float aV;
        attribute float aPart;
        attribute vec3 iSwim;
        uniform float uWiggle;
        uniform float uWaveK;
        varying float vD;
        varying float vV;
        varying float vPart;
        varying float vSeed;
        varying vec3 vObj;`)
      .replace("#include <beginnormal_vertex>", /* glsl */ `
        vec3 objectNormal = vec3(normal);
        float sS = 1.0 - aD;
        float sEnv = 0.1 + 0.9 * sS * sS;
        float sPh = iSwim.x - sS * uWaveK;
        float sSlope = -(uWiggle * (1.8 * sS * sin(sPh) - sEnv * cos(sPh) * uWaveK) + 2.0 * iSwim.y * sS);
        float sTh = atan(sSlope);
        float sC = cos(sTh), sN = sin(sTh);
        objectNormal = vec3(objectNormal.x * sC + objectNormal.z * sN, objectNormal.y, -objectNormal.x * sN + objectNormal.z * sC);`)
      .replace("#include <begin_vertex>", /* glsl */ `
        vec3 transformed = vec3(position);
        transformed.x += uWiggle * sEnv * sin(sPh) + iSwim.y * sS * sS;
        if (aPart > 1.5 && aPart < 2.5) {
          float fl = sin(iSwim.x * 0.8 + 1.0);
          transformed.x += sign(position.x) * aV * 0.05 * fl;
          transformed.y += aV * 0.02 * fl;
        } else if (aPart > 0.5 && aPart < 1.5) {
          transformed.x += aV * 0.02 * sin(iSwim.x * 0.6 - sS * 7.0);
        }
        vObj = position;
        vD = aD;
        vV = aV;
        vPart = aPart;
        vSeed = iSwim.z;`)
      .replace("#include <project_vertex>", `${causticVertexBody}\n#include <project_vertex>`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", /* glsl */ `#include <common>
        ${causticFragmentHead}
        uniform float uNight;
        uniform vec3 uBase, uBelly, uFin, uFinEdge, uEyeColor, uGlowColor, uBandColor, uBandEdge, uMarkColor, uRearColor, uLineColor, uSpotColor;
        uniform vec4 uBands, uBandW, uMark, uRear, uLine, uSpots, uEye;
        uniform vec2 uMarkW;
        uniform vec3 uLineX;
        uniform float uMarkGlow, uSpotOn, uLureGlow;
        varying float vD;
        varying float vV;
        varying float vPart;
        varying float vSeed;
        varying vec3 vObj;
        float fHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float fNoise(vec2 p) {
          vec2 i = floor(p), f = fract(p);
          vec2 w = f * f * (3.0 - 2.0 * f);
          return mix(mix(fHash(i), fHash(i + vec2(1.0, 0.0)), w.x), mix(fHash(i + vec2(0.0, 1.0)), fHash(i + vec2(1.0, 1.0)), w.x), w.y);
        }
        vec3 fishColor(out vec3 glow) {
          glow = vec3(0.0);
          float d = vD, v = vV;
          bool body = vPart < 0.5;
          bool fin = vPart > 0.5 && vPart < 2.5;
          vec3 c;
          if (body) {
            c = mix(uBase, uBelly, smoothstep(0.1, -0.75, v));
            c *= mix(1.0, 0.8, smoothstep(0.35, 1.0, v));
          } else if (fin) {
            c = mix(uFin, uFinEdge, smoothstep(0.6, 1.0, v));
          } else {
            c = uFin * 0.8;
          }
          if (uRear.w > 0.5 && d >= uRear.x && d <= uRear.y && (fin || v <= uRear.z)) c = uRearColor;
          for (int k = 0; k < 3; k++) {
            if (float(k) >= uBands.w) break;
            float dist = abs(d - uBands[k]);
            if (dist < uBandW[k]) c = uBandColor;
            else if (dist < uBandW[k] + uBandW.w) c = uBandEdge;
          }
          if (body && uMarkW.y > 0.5 && d >= uMark.x && d <= uMark.y) {
            float s = (d - uMark.x) / (uMark.y - uMark.x);
            float mid = uMark.z + uMark.w * sin(3.14159 * s);
            float halfW = uMarkW.x * sqrt(max(sin(3.14159 * s), 0.0));
            float m = smoothstep(halfW, halfW - 0.04, abs(v - mid));
            c = mix(c, uMarkColor, m);
            glow += uMarkColor * uMarkGlow * m;
          }
          if (body && uLineX.z > 0.5 && d >= uLine.z && d <= uLine.w) {
            float ph = (v - uLine.x) * uLineX.x * 0.5;
            float dist = abs(ph - floor(ph + 0.5)) * 2.0 / uLineX.x;
            float taper = smoothstep(uLine.z, uLine.z + 0.06, d) * smoothstep(uLine.w, uLine.w - 0.06, d);
            float m = smoothstep(uLine.y * 0.5, uLine.y * 0.5 - 0.03, dist) * taper;
            c = mix(c, uLineColor, m);
            glow += uLineColor * uLineX.y * m;
          }
          if (uSpotOn > 0.5 && body && v < uSpots.w) {
            float nz = fNoise(vec2(d * uSpots.x, v * uSpots.x * 0.4) + vSeed * 13.0);
            float m = smoothstep(uSpots.y, uSpots.y + 0.05, nz);
            c = mix(c, uSpotColor, m);
            glow += uSpotColor * uSpots.z * m;
          }
          if (body) {
            float r = uEye.z;
            vec2 e = vec2(vObj.z - uEye.x, vObj.y - uEye.y);
            float ed = length(e);
            if (ed < r) {
              c = ed > r * 0.8 ? mix(uBase, vec3(0.85), 0.5) : uEyeColor;
              if (ed < r * 0.5) c = vec3(0.01);
              if (length(e - vec2(r * 0.22, r * 0.28)) < r * 0.2) c = vec3(1.0);
              glow += uGlowColor * uEye.w * step(ed, r * 0.8);
            }
            c *= 0.95 + 0.05 * sin(d * 150.0 + v * 30.0) * sin(v * 70.0 - d * 90.0);
          }
          if (vPart > 3.5) {
            c = uGlowColor;
            glow += uGlowColor * uLureGlow;
          }
          glow *= 0.6 + 0.7 * uNight;
          return c;
        }`)
      .replace("vec4 diffuseColor = vec4( diffuse, opacity );", "vec3 fishGlow;\nvec4 diffuseColor = vec4( fishColor(fishGlow), opacity );")
      .replace("vec3 totalEmissiveRadiance = emissive;", "vec3 totalEmissiveRadiance = emissive + fishGlow;")
      .replace("#include <opaque_fragment>", `${causticFragmentBody}\n#include <opaque_fragment>`);
  };
  m.customProgramCacheKey = () => "fish";
  return m;
}

// One species' instanced fish, with the per-instance swim phase, bend, and seed.
export function speciesMesh(spec, max) {
  const geo = fishGeometry(spec);
  const swim = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
  swim.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute("iSwim", swim);
  const mesh = new THREE.InstancedMesh(geo, fishMaterial(spec, geo.userData.eye), max);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.count = 0;
  mesh.frustumCulled = false;
  return mesh;
}
