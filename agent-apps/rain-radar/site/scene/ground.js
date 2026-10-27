// The ground: the map, the radar frames crossfading with their glow, the clouds, and the wind trails, in one
// shader over one plane. The map square spans world x and z from -1 to 1; uv runs 0 to 1, x east and y south.
import * as THREE from "three";

const vertexShader = /* glsl */ `
varying vec2 vMap;
varying float vDepth;
void main() {
  vec4 w = modelMatrix * vec4(position, 1.0);
  vMap = vec2(w.x * 0.5 + 0.5, w.z * 0.5 + 0.5);
  vec4 v = viewMatrix * w;
  vDepth = -v.z;
  gl_Position = projectionMatrix * v;
}`;

const fragmentShader = /* glsl */ `
uniform sampler2D uLand;
uniform sampler2D uRoads;
uniform sampler2D uBase;
uniform sampler2D uFrameA;
uniform sampler2D uFrameB;
uniform sampler2D uTrail;
uniform sampler2D uClouds;
uniform float uFogNear, uFogFar, uLive, uMix, uRadar, uWind, uCloud, uTime, uGlow, uPaper, uHasA, uHasB;
uniform vec3 cWater, cWaterDeep, cLand, cLand2, cTown, cStreet, cRoad, cShore, cEdge, cTint, cWind, cCloud;
varying vec2 vMap;
varying float vDepth;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
  float s = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    s += a * noise(p);
    p = p * 2.03 + 17.1;
    a *= 0.5;
  }
  return s / 0.9375;
}

vec3 mapColor(vec2 uv) {
  if (uLive > 0.5) {
    vec3 b = texture(uBase, uv).rgb;
    return mix(b * cTint, b * cTint * 0.92 + cLand * 0.08, uPaper);
  }
  float f = texture(uLand, uv).r;
  float w = max(fwidth(f), 1e-4) * 1.25;
  float land = smoothstep(0.5 - w, 0.5 + w, f);
  vec3 water = mix(cWater, cWaterDeep, smoothstep(0.46, 0.18, f));
  vec3 ground = mix(cLand, cLand2, smoothstep(0.56, 0.95, f));
  vec4 r = texture(uRoads, uv);
  ground = mix(ground, cTown, r.b * 1.3);
  ground = mix(ground, cStreet, clamp(r.r * 1.15, 0.0, 1.0));
  ground = mix(ground, cRoad, clamp(r.g * 1.1, 0.0, 1.0));
  // open paper water carries fine ink hatching, so no flat blue reads as rain
  float phase = (uv.x - uv.y) * 2600.0;
  float broad = 1.0 - smoothstep(0.3, 0.45, textureLod(uLand, uv, 3.0).r);
  float hatch = smoothstep(0.55, 0.95, sin(phase)) * (1.0 - smoothstep(0.9, 1.8, fwidth(phase))) * broad * uPaper;
  water = mix(water, cShore, hatch * 0.32);
  vec3 c = mix(water, ground, land);
  float shore = 1.0 - smoothstep(0.0, w * 2.6, abs(f - 0.5));
  return mix(c, cShore, shore * 0.85);
}

void main() {
  vec2 uv = vMap;
  vec3 c = mapColor(clamp(uv, 0.0, 1.0));

  if (uCloud > 0.001) {
    float cover = texture(uClouds, uv).r;
    float n = fbm(uv * 7.0 + vec2(-uTime * 0.012, uTime * 0.004));
    float amt = smoothstep(0.62 - cover * 0.5, 0.95 - cover * 0.45, n) * cover * uCloud;
    c = mix(c, cCloud, amt * mix(0.42, 0.62, uPaper));
  }

  if (uRadar > 0.001) {
    vec4 a = texture(uFrameA, uv) * uHasA;
    vec4 b = texture(uFrameB, uv) * uHasB;
    vec4 rad = mix(a, b, uMix) * uRadar;
    vec4 g1 = mix(textureLod(uFrameA, uv, 2.5) * uHasA, textureLod(uFrameB, uv, 2.5) * uHasB, uMix) * uRadar;
    vec4 g2 = mix(textureLod(uFrameA, uv, 4.5) * uHasA, textureLod(uFrameB, uv, 4.5) * uHasB, uMix) * uRadar;
    if (uPaper > 0.5) {
      // watercolor: the rain is a pigment laid on the paper, darker where a wash dries at its edge
      vec3 pigment = vec3(1.0) - rad.a * 0.9 + rad.rgb * 0.9;
      float rim = clamp((rad.a - g1.a) * 2.2, 0.0, 1.0);
      vec3 halo = vec3(1.0) - g2.a * 0.22 + g2.rgb * 0.22;
      c *= mix(vec3(1.0), halo, uGlow);
      c *= pigment;
      c *= 1.0 - rim * 0.22;
    } else {
      // night: the rain is light over a dark map, with a bloom around every cell
      c = c * (1.0 - rad.a * 0.9) + rad.rgb * 1.05;
      c += (g1.rgb * 0.24 + g2.rgb * 0.3) * uGlow;
    }
  }

  if (uWind > 0.001) {
    float t = texture(uTrail, uv).r * uWind;
    c = mix(c + cWind * t * 0.45, mix(c, cWind, t * 0.4), uPaper);
  }

  if (uPaper > 0.5) {
    c *= 0.975 + 0.035 * noise(uv * 1400.0) + 0.02 * fbm(uv * 60.0);
  }

  float e = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
  c = mix(cEdge, c, smoothstep(0.0, 0.09, e));
  // the far side of the map fades into the background, like haze toward a horizon
  c = mix(c, cEdge, smoothstep(uFogNear, uFogFar, vDepth));
  gl_FragColor = vec4(c, 1.0);
}`;

function emptyTexture() {
  const t = new THREE.DataTexture(new Uint8Array([0, 0, 0, 0]), 1, 1, THREE.RGBAFormat);
  t.needsUpdate = true;
  return t;
}

export function canvasTexture(canvas, { mips = true, premultiply = false, anisotropy = 1 } = {}) {
  const t = new THREE.CanvasTexture(canvas);
  t.flipY = false;
  t.premultiplyAlpha = premultiply;
  t.colorSpace = THREE.NoColorSpace;
  t.generateMipmaps = mips;
  t.minFilter = mips ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.anisotropy = anisotropy;
  return t;
}

export function createGround(tokens) {
  const empty = emptyTexture();
  const clouds = new THREE.DataTexture(new Uint8Array(49 * 4), 7, 7, THREE.RGBAFormat);
  clouds.magFilter = clouds.minFilter = THREE.LinearFilter;
  clouds.needsUpdate = true;

  const uniforms = {
    uLand: { value: empty },
    uRoads: { value: empty },
    uBase: { value: empty },
    uFrameA: { value: empty },
    uFrameB: { value: empty },
    uTrail: { value: empty },
    uClouds: { value: clouds },
    uFogNear: { value: 10 },
    uFogFar: { value: 20 },
    uLive: { value: 0 },
    uMix: { value: 0 },
    uRadar: { value: 1 },
    uWind: { value: 1 },
    uCloud: { value: 0 },
    uTime: { value: 0 },
    uGlow: { value: 1 },
    uPaper: { value: 0 },
    uHasA: { value: 0 },
    uHasB: { value: 0 },
  };
  const colorNames = { cWater: "water", cWaterDeep: "water-deep", cLand: "land", cLand2: "land-2", cTown: "town", cStreet: "street", cRoad: "road", cShore: "shore", cEdge: "edge", cTint: "tint", cWind: "wind", cCloud: "cloud" };
  for (const u of Object.keys(colorNames)) uniforms[u] = { value: new THREE.Vector3() };

  const material = new THREE.ShaderMaterial({ uniforms, vertexShader, fragmentShader });
  const geometry = new THREE.PlaneGeometry(8, 8, 1, 1);
  geometry.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;

  const ground = {
    mesh,
    uniforms,
    setTokens(t) {
      for (const [u, name] of Object.entries(colorNames)) uniforms[u].value.copy(t[name]);
      uniforms.uPaper.value = t.paper;
    },
    setMap({ land, roads, base }) {
      for (const k of ["uLand", "uRoads", "uBase"]) if (uniforms[k].value !== empty) uniforms[k].value.dispose();
      uniforms.uLand.value = land ?? empty;
      uniforms.uRoads.value = roads ?? empty;
      uniforms.uBase.value = base ?? empty;
      uniforms.uLive.value = base ? 1 : 0;
    },
    setFrames(a, b, mix) {
      uniforms.uFrameA.value = a ?? empty;
      uniforms.uFrameB.value = b ?? empty;
      uniforms.uHasA.value = a ? 1 : 0;
      uniforms.uHasB.value = b ? 1 : 0;
      uniforms.uMix.value = mix;
    },
    setClouds(cover) {
      const d = clouds.image.data;
      for (let k = 0; k < 49; k++) {
        const v = Math.round(Math.max(0, Math.min(1, cover[k] ?? 0)) * 255);
        d[k * 4] = d[k * 4 + 1] = d[k * 4 + 2] = v;
        d[k * 4 + 3] = 255;
      }
      clouds.needsUpdate = true;
    },
  };
  ground.setTokens(tokens);
  return ground;
}
