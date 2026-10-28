// Planets as small colored discs with a soft glow, and the Moon as a lit sphere: the LRO map on its face, its phase
// from the Sun's direction, its north toward the celestial pole, and a halo of scattered moonlight.
import * as THREE from "three";
import { PROJECTION, MASK } from "./shaders.js";
import { PLANETS } from "./astro.js";

const PLANET_COLORS = {
  Mercury: [0.86, 0.8, 0.74],
  Venus: [1.0, 0.97, 0.88],
  Mars: [1.0, 0.62, 0.42],
  Jupiter: [1.0, 0.9, 0.74],
  Saturn: [0.98, 0.86, 0.6],
  Uranus: [0.7, 0.92, 0.94],
  Neptune: [0.58, 0.72, 1.0],
};

const PLANET_VERTEX = /* glsl */ `
${PROJECTION}
${MASK}
attribute vec3 aColor;
attribute float aMag;
uniform float uZoom;
uniform float uFade;
uniform float uMono;
uniform vec3 uTint;
varying vec3 vColor;
varying float vRadius;
varying float vSize;
varying float vBright;

void main() {
  vec3 w = uSky * position;
  vec3 v = uView * w;
  if (-v.z < 0.0 || w.y < -0.05) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
  vec2 at = projPx(v);
  gl_Position = pxToClip(at);
  float r = (1.9 + 0.75 * clamp(1.5 - aMag, 0.0, 6.0)) * uZoom;
  vRadius = r * uDpr;
  vSize = (r * 7.0) * uDpr + 2.0;
  vBright = clamp(1.2 - 0.12 * aMag, 0.35, 1.0) * uFade * (1.0 - maskAt(pxToPage(at)));
  vColor = mix(aColor, uTint, uMono);
  gl_PointSize = vSize;
}
`;

const PLANET_FRAGMENT = /* glsl */ `
uniform float uInkMode;
varying vec3 vColor;
varying float vRadius;
varying float vSize;
varying float vBright;

void main() {
  float d = length(gl_PointCoord - 0.5) * vSize;
  float disc = 1.0 - smoothstep(vRadius * 0.62 - 0.8, vRadius * 0.62 + 0.8, d);
  float glow = exp(-d / (vRadius * 0.9)) * 0.55;
  if (uInkMode > 0.5) {
    float ring = 1.0 - smoothstep(0.7, 1.6, abs(d - vRadius * 0.95));
    float a = max(disc, ring) * vBright;
    if (a < 0.01) discard;
    gl_FragColor = vec4(vColor, a);
    return;
  }
  vec3 c = vColor * (disc * 1.1 + glow) * vBright;
  if (max(c.r, max(c.g, c.b)) < 0.003) discard;
  gl_FragColor = vec4(c, 1.0);
}
`;

const MOON_VERTEX = /* glsl */ `
${PROJECTION}
attribute vec2 aCorner;
uniform vec3 uMoonEq;
uniform vec3 uSunEq;
uniform vec3 uPoleEq;
uniform float uRadius;
uniform float uScale;
varying vec2 vUv;
varying vec3 vLight;
varying float vScale;

void main() {
  vec3 m = uView * (uSky * uMoonEq);
  if (-m.z < 0.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  vec2 c = projPx(m);
  vec3 s = uView * (uSky * uSunEq);
  vec3 pole = uView * (uSky * uPoleEq);
  vec3 ez = -m;
  vec3 ey = normalize(pole - dot(pole, m) * m);
  vec3 ex = normalize(cross(ey, ez));
  // Screen axes of the disc: north on the sky maps to the projected direction of the pole.
  vec2 cp = projPx(normalize(m + ey * 0.01)) - c;
  vec2 ny = normalize(cp);
  vec2 nx = vec2(ny.y, -ny.x);
  vec2 p = c + (nx * aCorner.x + ny * aCorner.y) * uRadius * uScale;
  vUv = aCorner * uScale;
  vLight = vec3(dot(s, ex), dot(s, ey), dot(s, ez));
  vScale = uScale;
  gl_Position = pxToClip(p);
}
`;

const MOON_FRAGMENT = /* glsl */ `
uniform sampler2D uMap;
uniform float uHasMap;
uniform float uFade;
uniform float uInkMode;
uniform float uMono;
uniform vec3 uTint;
uniform vec3 uInk;
uniform float uHaloAmt;
uniform float uInkLight;
varying vec2 vUv;
varying vec3 vLight;
varying float vScale;

void main() {
  float r = length(vUv);
  vec3 L = normalize(vLight);
  if (r > 1.0) {
    if (uInkMode > 0.5) discard;
    float halo = exp(-(r - 1.0) * 2.4) * 0.16 + exp(-(r - 1.0) * 9.0) * 0.12;
    float lit = clamp(0.5 + 0.5 * L.z, 0.05, 1.0);
    vec3 hc = mix(vec3(0.82, 0.86, 0.95), uTint, uMono) * halo * lit * uFade * uHaloAmt;
    if (max(hc.r, max(hc.g, hc.b)) < 0.002) discard;
    gl_FragColor = vec4(hc, 0.0);
    return;
  }
  float z = sqrt(1.0 - r * r);
  vec3 n = vec3(vUv, z);
  float lon = atan(n.x, n.z);
  float lat = asin(clamp(n.y, -1.0, 1.0));
  vec2 uv = vec2(0.5 + lon / 6.2831853, 0.5 + lat / 3.1415927);
  vec3 albedo = uHasMap > 0.5 ? texture(uMap, uv).rgb : vec3(0.62);
  albedo = mix(vec3(dot(albedo, vec3(0.333))), albedo, 0.35);
  float ndl = dot(n, L);
  float day = smoothstep(-0.04, 0.12, ndl);
  float shade = day * (0.35 + 0.75 * max(ndl, 0.0));
  float earthshine = 0.11;
  vec3 col = albedo * (shade * 2.3 + earthshine);
  float edge = 1.0 - smoothstep(0.985, 1.0, r);
  if (uInkMode > 0.5) {
    float ink = mix((1.0 - day) * 0.28, day * 0.85 + 0.08, uInkLight);
    float rim = 1.0 - smoothstep(0.0, 0.035, abs(r - 0.975));
    gl_FragColor = vec4(uInk, max(ink * edge, rim) * uFade);
    return;
  }
  col = mix(col, uTint * dot(col, vec3(0.4, 0.45, 0.15)) * 1.4, uMono);
  gl_FragColor = vec4(col * edge * uFade, edge * uFade * (0.3 + 0.7 * day));
}
`;

export function createPlanets(shared) {
  const n = PLANETS.length;
  const geometry = new THREE.BufferGeometry();
  const pos = new Float32Array(n * 3);
  const col = new Float32Array(n * 3);
  const mag = new Float32Array(n).fill(9);
  PLANETS.forEach((name, i) => col.set(PLANET_COLORS[name], i * 3));
  geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
  geometry.setAttribute("aMag", new THREE.BufferAttribute(mag, 1));
  const uniforms = {
    ...shared,
    uZoom: { value: 1 },
    uFade: { value: 1 },
    uMono: { value: 0 },
    uTint: { value: new THREE.Vector3(1, 1, 1) },
    uInkMode: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: PLANET_VERTEX,
    fragmentShader: PLANET_FRAGMENT,
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
    update(bodies) {
      PLANETS.forEach((name, i) => {
        const b = bodies[name];
        pos.set(b.dir, i * 3);
        mag[i] = name === "Uranus" || name === "Neptune" ? Math.max(b.mag, 5.6) + 1.5 : b.mag;
      });
      geometry.attributes.position.needsUpdate = true;
      geometry.attributes.aMag.needsUpdate = true;
    },
    setInk(ink) {
      uniforms.uInkMode.value = ink ? 1 : 0;
      material.blending = ink ? THREE.NormalBlending : THREE.AdditiveBlending;
      material.needsUpdate = true;
    },
  };
}

export function createMoon(shared) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("aCorner", new THREE.Float32BufferAttribute([-1, -1, 1, -1, -1, 1, 1, 1], 2));
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(new Array(12).fill(0), 3));
  geometry.setIndex([0, 1, 2, 2, 1, 3]);
  const uniforms = {
    ...shared,
    uMoonEq: { value: new THREE.Vector3(1, 0, 0) },
    uSunEq: { value: new THREE.Vector3(-1, 0, 0) },
    uPoleEq: { value: new THREE.Vector3(0, 0, 1) },
    uRadius: { value: 14 },
    uScale: { value: 1 },
    uMap: { value: null },
    uHasMap: { value: 0 },
    uFade: { value: 1 },
    uInkMode: { value: 0 },
    uMono: { value: 0 },
    uTint: { value: new THREE.Vector3(1, 1, 1) },
    uInk: { value: new THREE.Vector3(0, 0, 0) },
    uHaloAmt: { value: 1 },
    uInkLight: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: MOON_VERTEX,
    fragmentShader: MOON_FRAGMENT,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.CustomBlending,
    blendEquation: THREE.AddEquation,
    blendSrc: THREE.OneFactor,
    blendDst: THREE.OneMinusSrcAlphaFactor,
  });
  const disc = new THREE.Mesh(geometry, material);
  disc.frustumCulled = false;

  return {
    disc,
    uniforms,
    setMap(texture) {
      uniforms.uMap.value = texture;
      uniforms.uHasMap.value = texture ? 1 : 0;
    },
    update(moon, sun, radiusPx) {
      uniforms.uMoonEq.value.set(...moon.dir);
      uniforms.uSunEq.value.set(...sun.dir);
      uniforms.uRadius.value = radiusPx;
    },
    setInk(ink) {
      uniforms.uInkMode.value = ink ? 1 : 0;
      material.blending = ink ? THREE.NormalBlending : THREE.CustomBlending;
      if (!ink) {
        material.blendEquation = THREE.AddEquation;
        material.blendSrc = THREE.OneFactor;
        material.blendDst = THREE.OneMinusSrcAlphaFactor;
      }
      material.needsUpdate = true;
    },
  };
}
