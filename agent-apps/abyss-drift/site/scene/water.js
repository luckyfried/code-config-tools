// Water you are inside: the surface seen from below, sun shafts, and the two full-screen passes
// (the underwater tint with its wobble and vignette, and the radial-blur god rays).
import * as THREE from "three";
import { shared, CAUSTIC_GLSL, SURFACE_GLSL } from "./materials.js";

/** The underside of the surface: a bright Snell's window overhead, the water's own color beyond it, rippling. */
export function createSurface() {
  const geo = new THREE.PlaneGeometry(900, 900, 1, 1);
  geo.rotateX(Math.PI / 2);
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: shared.uTime,
      uSurfaceSky: shared.uSurfaceSky,
      uSurfaceFade: shared.uSurfaceFade,
      uSurfaceWater: shared.uFogColor,
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      varying vec3 vWorld;
      ${CAUSTIC_GLSL}
      ${SURFACE_GLSL}
      void main() {
        float ripple = causticAt(vec3(vWorld.x * 0.6, 0.0, vWorld.z * 0.6), uTime * 1.4);
        gl_FragColor = vec4(surfaceSeen(vWorld - cameraPosition, ripple), 1.0);
      }`,
    side: THREE.DoubleSide,
    depthWrite: true,
    fog: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.name = "surface";
  mesh.frustumCulled = false;
  return mesh;
}

/** Shafts of sunlight hanging from the surface, drawn as camera-facing ribbons in one draw call. */
export function createSunShafts(tokens, rng, count = 14) {
  const W = tokens.world;
  const pos = [];
  const data = [];
  const idx = [];
  for (let i = 0; i < count; i++) {
    const cx = rng.range(-45, 45);
    const cz = rng.range(-45, 45);
    const width = rng.range(2.5, 8);
    const length = rng.range(45, 90);
    const phase = rng.range(0, 6.28);
    const base = i * 4;
    for (const [u, v] of [[-1, 0], [1, 0], [-1, 1], [1, 1]]) {
      pos.push(cx, 0, cz);
      data.push(u, v, width, length, phase);
    }
    idx.push(base, base + 2, base + 1, base + 1, base + 2, base + 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  const d = new Float32Array(data);
  const inter = new THREE.InterleavedBuffer(d, 5);
  geo.setAttribute("aCorner", new THREE.InterleavedBufferAttribute(inter, 2, 0));
  geo.setAttribute("aShape", new THREE.InterleavedBufferAttribute(inter, 3, 2));
  geo.setIndex(idx);
  const mat = new THREE.ShaderMaterial({
    uniforms: { uTime: shared.uTime, uSun: { value: W.sun.clone() }, uStrength: { value: 1 } },
    vertexShader: /* glsl */ `
      attribute vec2 aCorner;
      attribute vec3 aShape;
      uniform float uTime;
      varying vec2 vUv;
      varying float vPhase;
      void main() {
        vec3 top = position;
        float lean = 0.32;
        vec3 down = normalize(vec3(lean * 0.6, -1.0, lean * 0.3));
        vec3 p = top + down * aCorner.y * aShape.z;
        vec3 toCam = cameraPosition - p;
        vec3 side = normalize(cross(down, toCam));
        float sway = sin(uTime * 0.35 + aShape.z) * 0.6;
        p += side * (aCorner.x * aShape.x * (1.0 + aCorner.y * 0.8) + sway * aCorner.y);
        vUv = vec2(aCorner.x * 0.5 + 0.5, aCorner.y);
        vPhase = aShape.z;
        gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform vec3 uSun;
      uniform float uStrength;
      varying vec2 vUv;
      varying float vPhase;
      void main() {
        float across = 1.0 - abs(vUv.x * 2.0 - 1.0);
        float shaft = pow(across, 2.5);
        float along = (1.0 - vUv.y) * smoothstep(0.0, 0.08, vUv.y);
        float flicker = 0.65 + 0.35 * sin(uTime * 0.8 + vPhase * 3.0);
        gl_FragColor = vec4(uSun * shaft * along * along * flicker * 0.16 * uStrength, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    fog: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.name = "sunShafts";
  mesh.frustumCulled = false;
  return mesh;
}

/** The tint pass: absorption that deepens with depth, a slight wobble, a vignette, the shutter flash, and the held breath. */
export const UnderwaterShader = {
  name: "UnderwaterShader",
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uWobble: { value: 1 },
    uTint: { value: new THREE.Color(0.4, 0.8, 1.0) },
    uTintAmount: { value: 0.4 },
    uHaze: { value: new THREE.Color(0, 0.05, 0.1) },
    uVignette: { value: 0.55 },
    uAspect: { value: 1 },
    uFlash: { value: 0 },
    uBreath: { value: 0 },
    uSurfaceGlow: { value: 0 },
    uSurfaceColor: { value: new THREE.Color(0.8, 0.95, 1.0) },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uWobble;
    uniform vec3 uTint;
    uniform float uTintAmount;
    uniform vec3 uHaze;
    uniform float uVignette;
    uniform float uAspect;
    uniform float uFlash;
    uniform float uBreath;
    uniform float uSurfaceGlow;
    uniform vec3 uSurfaceColor;
    varying vec2 vUv;
    float hash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
    float vnoise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
    }
    void main() {
      vec2 uv = vUv;
      if (uWobble > 0.0) {
        vec2 n = vec2(vnoise(uv * 7.0 + uTime * 0.35), vnoise(uv * 7.0 - uTime * 0.3 + 17.0)) - 0.5;
        uv += n * 0.0038 * uWobble;
      }
      vec3 col = texture2D(tDiffuse, uv).rgb;
      float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
      vec3 absorbed = mix(col, vec3(lum) * uTint * 1.25, uTintAmount * 0.55) * mix(vec3(1.0), uTint, uTintAmount * 0.45);
      col = absorbed + uHaze;
      vec2 d = (vUv - 0.5) * vec2(uAspect, 1.0);
      float r = length(d) / length(vec2(uAspect, 1.0) * 0.5);
      col *= mix(1.0, smoothstep(1.15, 0.35, r), uVignette);
      col *= mix(1.0, smoothstep(0.95, 0.15, r), uBreath * 0.85);
      col = mix(col, uSurfaceColor * 1.4, uSurfaceGlow);
      col += vec3(uFlash);
      gl_FragColor = vec4(col, 1.0);
    }`,
};

/** God rays: a radial blur of the bright surface toward its point on screen. */
export const GodRayShader = {
  name: "GodRayShader",
  uniforms: {
    tDiffuse: { value: null },
    uLight: { value: new THREE.Vector2(0.5, 1.4) },
    uStrength: { value: 0.0 },
    uDecay: { value: 0.955 },
    uThreshold: { value: 0.9 },
  },
  vertexShader: UnderwaterShader.vertexShader,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform vec2 uLight;
    uniform float uStrength;
    uniform float uDecay;
    uniform float uThreshold;
    varying vec2 vUv;
    #define SAMPLES 36
    void main() {
      vec3 base = texture2D(tDiffuse, vUv).rgb;
      if (uStrength <= 0.001) { gl_FragColor = vec4(base, 1.0); return; }
      vec2 delta = (vUv - uLight) / float(SAMPLES) * 0.85;
      vec2 coord = vUv;
      float illum = 1.0;
      vec3 acc = vec3(0.0);
      for (int i = 0; i < SAMPLES; i++) {
        coord -= delta;
        vec2 c = clamp(coord, 0.0, 1.0);
        vec3 s = max(texture2D(tDiffuse, c).rgb - uThreshold, 0.0);
        acc += s * illum;
        illum *= uDecay;
      }
      gl_FragColor = vec4(base + acc * uStrength / float(SAMPLES), 1.0);
    }`,
};
