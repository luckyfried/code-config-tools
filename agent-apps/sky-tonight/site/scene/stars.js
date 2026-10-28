// The star field: one Points draw of every catalog star. Size and brightness come from the real magnitude, color
// from the B-V index, and each star carries its own twinkle phase. The sky's rotation is a uniform, so the CPU does
// nothing per star.
import * as THREE from "three";
import { PROJECTION, MASK } from "./shaders.js";
import { bvToRgb, eqVector } from "./astro.js";

const VERTEX = /* glsl */ `
${PROJECTION}
${MASK}
attribute float aMag;
attribute vec3 aColor;
attribute float aPhase;
uniform float uTime;
uniform float uMagLimit;
uniform float uMagCut;
uniform float uZoom;
uniform float uTwinkle;
uniform float uGain;
uniform float uMono;
uniform vec3 uTint;
varying vec3 vColor;
varying float vIntensity;
varying float vSigma;
varying float vHalo;
varying float vSize;

void main() {
  vec3 w = uSky * position;
  vec3 v = uView * w;
  if (-v.z < 0.0 || w.y < -0.03 || aMag > uMagCut) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    gl_PointSize = 0.0;
    return;
  }
  vec2 at = projPx(v);
  float hidden = maskAt(pxToPage(at));
  if (hidden > 0.995) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    gl_PointSize = 0.0;
    return;
  }
  gl_Position = pxToClip(at);

  float s = max(w.y, 0.0);
  float airmass = 1.0 / (s + 0.025 * exp(-11.0 * s));
  float ext = min(0.22 * (airmass - 1.0), 3.0);
  float m = aMag + ext;
  float L = pow(10.0, -0.4 * (m - uMagLimit));

  float scint = mix(0.34, 0.1, smoothstep(0.0, 0.55, s));
  float f1 = 2.2 + fract(aPhase * 7.31) * 2.6;
  float f2 = 3.7 + fract(aPhase * 3.17) * 2.1;
  float tw = 0.62 * sin(uTime * f1 + aPhase * 6.2832) + 0.38 * sin(uTime * f2 + aPhase * 17.13);
  float twinkle = 1.0 + uTwinkle * scint * tw;

  float I = clamp(0.2 * pow(L, 0.58), 0.0, 1.35) * twinkle * uGain;
  I *= smoothstep(0.0, 0.6, L);
  float r = (0.72 + 0.5 * log2(1.0 + L)) * uZoom;
  float sigma = max(0.62, 0.36 * r);
  float halo = smoothstep(25.0, 600.0, L) * 0.4;
  float extent = max(sigma * 3.2, halo > 0.0 ? r * 3.4 : 0.0);

  vec3 c = aColor;
  float redden = 1.0 - smoothstep(0.0, 0.3, s);
  c *= mix(vec3(1.0), vec3(1.0, 0.74, 0.52), redden * 0.8);
  float lum = dot(c, vec3(0.3, 0.59, 0.11));
  vColor = mix(c, uTint * (0.55 + 0.45 * lum), uMono);
  vIntensity = I * (1.0 - hidden);
  vSigma = sigma * uDpr;
  vHalo = halo;
  vSize = extent * 2.0 * uDpr + 2.0;
  gl_PointSize = vSize;
}
`;

const FRAGMENT = /* glsl */ `
uniform float uInkMode;
varying vec3 vColor;
varying float vIntensity;
varying float vSigma;
varying float vHalo;
varying float vSize;

void main() {
  float d = length(gl_PointCoord - 0.5) * vSize;
  float core = exp(-(d * d) / (2.0 * vSigma * vSigma));
  float halo = vHalo * exp(-d / (vSigma * 2.6));
  float a = core * vIntensity + halo * min(vIntensity, 1.0);
  if (a < 0.003) discard;
  if (uInkMode > 0.5) {
    gl_FragColor = vec4(vColor, clamp(a * 1.15, 0.0, 1.0));
  } else {
    gl_FragColor = vec4(vColor * a, 1.0);
  }
}
`;

export function buildStarGeometry(features) {
  const n = features.length;
  const pos = new Float32Array(n * 3);
  const mag = new Float32Array(n);
  const col = new Float32Array(n * 3);
  const phase = new Float32Array(n);
  const vectors = new Float32Array(n * 3);
  const ids = new Int32Array(n);
  for (let i = 0; i < n; i += 1) {
    const f = features[i];
    const [ra, dec] = f.geometry.coordinates;
    const v = eqVector(ra, dec);
    pos.set(v, i * 3);
    vectors.set(v, i * 3);
    mag[i] = f.properties.mag;
    const bv = parseFloat(f.properties.bv);
    col.set(bvToRgb(Number.isFinite(bv) ? bv : 0.6), i * 3);
    phase[i] = ((f.id * 0.6180339887) % 1 + 1) % 1;
    ids[i] = f.id;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geometry.setAttribute("aMag", new THREE.BufferAttribute(mag, 1));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
  geometry.setAttribute("aPhase", new THREE.BufferAttribute(phase, 1));
  return { geometry, vectors, mags: mag, ids };
}

export function createStars(shared, geometry) {
  const uniforms = {
    ...shared,
    uTime: { value: 0 },
    uMagLimit: { value: 6.2 },
    uMagCut: { value: 6.5 },
    uZoom: { value: 1 },
    uTwinkle: { value: 1 },
    uGain: { value: 1 },
    uMono: { value: 0 },
    uTint: { value: new THREE.Vector3(1, 1, 1) },
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
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  return {
    points,
    uniforms,
    setInk(ink) {
      uniforms.uInkMode.value = ink ? 1 : 0;
      material.blending = ink ? THREE.NormalBlending : THREE.AdditiveBlending;
      material.needsUpdate = true;
    },
  };
}
