// The horizon: a silhouette painted once into a canvas laid out in azimuth and altitude, then a full-screen ground
// pass that hides everything below it. Red holds how far a layer is (far ridges take the haze), green holds lit
// windows and farm lights, blue marks open water, which reflects the sky and the Moon.
import * as THREE from "three";
import { PROJECTION, SKY_COLOR, DITHER, FULLSCREEN_VERTEX } from "./shaders.js";

export const SIL_MIN = -8;
export const SIL_MAX = 16;

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function seedFrom(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// A ridge line that wraps cleanly at north: a sum of sines with whole-number periods around the circle.
function ridge(random, base, amp, terms = [2, 3, 5, 8, 13, 21, 34, 55]) {
  const parts = terms.map((k) => ({ k, a: amp / Math.pow(k, 0.85), p: random() * Math.PI * 2 }));
  return (az) => {
    const t = (az * Math.PI) / 180;
    let h = base;
    for (const { k, a, p } of parts) h += a * Math.sin(k * t + p);
    return h;
  };
}

export function paintSilhouette(kind, seed, width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const g = canvas.getContext("2d");
  const random = rng(seed);
  const X = (az) => (az / 360) * width;
  const Y = (alt) => ((SIL_MAX - alt) / (SIL_MAX - SIL_MIN)) * height;
  const pxPerDeg = width / 360;
  const fill = (depth, light = 0, water = 0) => `rgb(${Math.round(depth * 255)}, ${Math.round(light * 255)}, ${water * 255})`;

  const band = (fn, depth, step = 0.25) => {
    g.fillStyle = fill(depth);
    g.beginPath();
    g.moveTo(X(0), Y(SIL_MIN - 1));
    for (let az = 0; az <= 360.001; az += step) g.lineTo(X(az), Y(fn(az)));
    g.lineTo(X(360), Y(SIL_MIN - 1));
    g.closePath();
    g.fill();
  };

  const pine = (az, baseAlt, h, depth) => {
    const w = h * (0.28 + random() * 0.1);
    const tiers = 6 + Math.floor(random() * 4);
    g.fillStyle = fill(depth);
    g.beginPath();
    const top = baseAlt + h;
    g.moveTo(X(az), Y(top));
    for (let i = 1; i <= tiers; i += 1) {
      const t = i / tiers;
      const y = top - h * 0.86 * t;
      const half = (w / 2) * (0.25 + 0.75 * t) * (0.85 + random() * 0.3);
      g.lineTo(X(az + half), Y(y));
      g.lineTo(X(az + half * 0.45), Y(y + h * 0.05));
    }
    g.lineTo(X(az + w * 0.06), Y(baseAlt - 0.3));
    g.lineTo(X(az - w * 0.06), Y(baseAlt - 0.3));
    for (let i = tiers; i >= 1; i -= 1) {
      const t = i / tiers;
      const y = top - h * 0.86 * t;
      const half = (w / 2) * (0.25 + 0.75 * t) * (0.85 + random() * 0.3);
      g.lineTo(X(az - half * 0.45), Y(y + h * 0.05));
      g.lineTo(X(az - half), Y(y));
    }
    g.closePath();
    g.fill();
  };

  const roundTree = (az, baseAlt, h, depth) => {
    g.fillStyle = fill(depth);
    const r = h * 0.42;
    g.fillRect(X(az) - pxPerDeg * 0.05, Y(baseAlt + h * 0.5), pxPerDeg * 0.1, Y(baseAlt - 0.3) - Y(baseAlt + h * 0.5));
    for (let i = 0; i < 4; i += 1) {
      g.beginPath();
      const cx = az + (random() - 0.5) * r * 0.9;
      const cy = baseAlt + h - r * (0.6 + random() * 0.5);
      g.ellipse(X(cx), Y(cy), r * pxPerDeg * (0.7 + random() * 0.3), r * (height / (SIL_MAX - SIL_MIN)) * (0.6 + random() * 0.3), 0, 0, Math.PI * 2);
      g.fill();
    }
  };

  const wrapDraw = (az, draw) => {
    draw(az);
    if (az < 6) draw(az + 360);
    if (az > 354) draw(az - 360);
  };

  if (kind === "hill") {
    const massif = random() * 360;
    const far = ridge(random, 2.1, 1.6);
    const peaks = (az) => {
      let d = Math.abs(((az - massif + 540) % 360) - 180);
      return 5.6 * Math.exp(-(d * d) / (2 * 11 * 11)) + 1.6 * Math.exp(-((d - 16) ** 2) / (2 * 5 * 5));
    };
    band((az) => far(az) + peaks(az), 0.9);
    const mid = ridge(random, 1.1, 1.3);
    band(mid, 0.55);
    const near = ridge(random, 0.15, 0.7);
    band(near, 0.0);
    const groves = ridge(random, 0, 1, [3, 7, 11, 17]);
    for (let az = 0; az < 360; az += 0.32 + random() * 0.55) {
      if (groves(az) < -0.15) continue;
      const h = 0.9 + random() * 1.9 + Math.max(0, groves(az)) * 0.8;
      const a = az;
      wrapDraw(a, (x) => pine(x, near(a) - 0.1, h, 0.0));
    }
    // a cabin with one warm window
    const cabin = (massif + 150 + random() * 60) % 360;
    const cb = near(cabin);
    g.fillStyle = fill(0);
    g.beginPath();
    g.moveTo(X(cabin - 0.9), Y(cb - 0.2));
    g.lineTo(X(cabin - 0.9), Y(cb + 0.65));
    g.lineTo(X(cabin), Y(cb + 1.15));
    g.lineTo(X(cabin + 0.9), Y(cb + 0.65));
    g.lineTo(X(cabin + 0.9), Y(cb - 0.2));
    g.fill();
    g.fillStyle = fill(0, 1);
    g.fillRect(X(cabin - 0.45), Y(cb + 0.45), pxPerDeg * 0.32, Y(cb + 0.15) - Y(cb + 0.45));
  } else if (kind === "sea") {
    g.fillStyle = fill(0.2, 0, 1);
    g.fillRect(0, Y(0), width, height - Y(0));
    const head = random() * 360;
    const land = (az) => {
      const d = ((az - head + 540) % 360) - 180;
      if (d < -30 || d > 34) return -1;
      const edge = Math.min(1, (d + 30) / 6, (34 - d) / 14);
      return (0.6 + 1.1 * Math.sin(((d + 30) / 64) * Math.PI)) * edge + 0.15 * Math.sin(d * 0.9);
    };
    g.fillStyle = fill(0.75);
    g.beginPath();
    g.moveTo(X(0), Y(0));
    for (let az = 0; az <= 360; az += 0.2) {
      const h = land(az);
      g.lineTo(X(az), Y(h > 0 ? h : 0));
    }
    g.lineTo(X(360), Y(-0.05));
    g.lineTo(X(0), Y(-0.05));
    g.fill();
    // a lighthouse and a few lights on the headland
    const lh = (head + 20) % 360;
    g.fillStyle = fill(0.75);
    g.fillRect(X(lh) - pxPerDeg * 0.12, Y(land(lh) + 1.3), pxPerDeg * 0.24, Y(land(lh)) - Y(land(lh) + 1.3));
    g.fillStyle = fill(0.75, 1);
    g.fillRect(X(lh) - pxPerDeg * 0.14, Y(land(lh) + 1.45), pxPerDeg * 0.28, pxPerDeg * 0.16);
    for (let i = 0; i < 14; i += 1) {
      const az = (head - 22 + random() * 44 + 360) % 360;
      const h = land(az);
      if (h < 0.3) continue;
      g.fillStyle = fill(0.75, 0.5 + random() * 0.5);
      g.fillRect(X(az), Y(h * (0.2 + random() * 0.5)), pxPerDeg * 0.08, pxPerDeg * 0.06);
    }
  } else if (kind === "city") {
    const downtown = random() * 360;
    const base = ridge(random, 0.2, 0.3);
    band(base, 0.3);
    let az = 0;
    while (az < 360) {
      const d = Math.abs(((az - downtown + 540) % 360) - 180);
      const density = Math.exp(-(d * d) / (2 * 40 * 40));
      const w = 0.5 + random() * (1.4 - density * 0.6);
      const h = 0.35 + random() * 0.8 + density * (0.6 + random() * 4.2) * (random() < 0.85 ? 1 : 0.4);
      const depth = 0.2 + random() * 0.6;
      const b = base(az) - 0.2;
      const drawBuilding = (x0) => {
        g.fillStyle = fill(depth);
        g.fillRect(X(x0), Y(b + h), w * pxPerDeg, Y(b) - Y(b + h));
        if (h > 2.2 && random() < 0.35) {
          g.fillRect(X(x0 + w / 2) - 1, Y(b + h + 0.9), 2, Y(b + h) - Y(b + h + 0.9));
          g.fillStyle = fill(depth, 0.9);
          g.fillRect(X(x0 + w / 2) - 2, Y(b + h + 0.95), 4, 3);
        }
        const rows = Math.floor(h / 0.24);
        const cols = Math.max(1, Math.floor(w / 0.2));
        for (let r = 1; r < rows; r += 1) {
          for (let c = 0; c < cols; c += 1) {
            if (random() > 0.16 + density * 0.12) continue;
            g.fillStyle = fill(depth, 0.35 + random() * 0.65);
            g.fillRect(X(x0 + (c + 0.35) * (w / cols)), Y(b + r * 0.24 + 0.1), Math.max(1, pxPerDeg * 0.07), Math.max(1, pxPerDeg * 0.06));
          }
        }
      };
      wrapDraw(az, drawBuilding);
      az += w + random() * 0.15;
    }
  } else {
    const ground = ridge(random, 0.25, 0.25);
    band(ground, 0.4);
    const near = ridge(random, -0.1, 0.12);
    band(near, 0);
    const groves = ridge(random, 0, 1, [2, 5, 9, 14]);
    for (let az = 0; az < 360; az += 0.8 + random() * 3.5) {
      if (groves(az) < 0.35) continue;
      const h = 0.7 + random() * 1.2;
      const a = az;
      wrapDraw(a, (x) => roundTree(x, ground(a), h, 0.35));
    }
    // a fence line along the near ground
    g.fillStyle = fill(0);
    for (let az = 0; az < 360; az += 1.6) g.fillRect(X(az), Y(near(az) + 0.42), Math.max(1, pxPerDeg * 0.05), Y(near(az)) - Y(near(az) + 0.42));
    g.fillRect(0, Y(0.3), width, Math.max(1, pxPerDeg * 0.025));
    const farm = random() * 360;
    g.fillStyle = fill(0.35);
    g.fillRect(X(farm), Y(ground(farm) + 0.55), pxPerDeg * 1.2, Y(ground(farm)) - Y(ground(farm) + 0.55));
    g.fillStyle = fill(0.35, 1);
    g.fillRect(X(farm + 0.3), Y(ground(farm) + 0.35), pxPerDeg * 0.18, pxPerDeg * 0.12);
  }

  // Everything well below the horizon is solid ground (or open water at sea).
  g.fillStyle = kind === "sea" ? fill(0.2, 0, 1) : fill(0);
  g.fillRect(0, Y(-2.5), width, height - Y(-2.5));
  return canvas;
}

const FRAGMENT = /* glsl */ `
${PROJECTION}
${SKY_COLOR}
${DITHER}
uniform sampler2D uSil;
uniform vec3 cGround;
uniform vec3 cGroundHaze;
uniform vec3 cLight;
uniform vec3 cInk;
uniform float uSea;
uniform float uTime;

void main() {
  vec3 d = dirFromFrag(gl_FragCoord.xy);
  float alt = degrees(asin(clamp(d.y, -1.0, 1.0)));
  if (alt > ${SIL_MAX.toFixed(1)}) discard;
  float az = degrees(atan(d.x, -d.z));
  if (az < 0.0) az += 360.0;
  float v = (alt - ${SIL_MIN.toFixed(1)}) / ${(SIL_MAX - SIL_MIN).toFixed(1)};
  vec4 s = v < 0.0 ? vec4(uSea * 0.2, 0.0, uSea, 1.0) : texture(uSil, vec2(az / 360.0, v));
  if (s.a < 0.004) discard;

  float depth = s.r;
  vec3 col = mix(cGround, cGroundHaze, depth * 0.8);
  float below = max(-alt, 0.0);
  col = mix(col, cGroundHaze, (0.3 * exp(-below / 3.0) + 0.22 * exp(-below / 14.0)) * (1.0 - uInkMode));

  if (s.b > 0.5) {
    vec3 r = normalize(vec3(d.x, -d.y, d.z));
    float grazing = 1.0 - clamp(below / 25.0, 0.0, 1.0);
    vec3 sky = skyColor(r);
    col = mix(cGround, sky, (0.2 + 0.6 * pow(grazing, 3.0)) * (1.0 - 0.6 * uInkMode));
    float ripple = sin(az * 9.0 + uTime * 0.7 + sin(below * 6.0 + uTime) * 2.0) * 0.5 + 0.5;
    float sparkle = step(0.9, hash12(floor(vec2(az * 30.0, below * 60.0 + uTime * 1.5))));
    vec3 md = uMoonDir;
    float dAz = mod(az - degrees(atan(md.x, -md.z)) + 540.0, 360.0) - 180.0;
    float path = exp(-pow(dAz / (1.2 + below * 0.6), 2.0));
    col += vec3(0.85, 0.88, 0.95) * path * (0.25 + 0.75 * sparkle * ripple) * uMoonLight * 1.6 * step(0.0, md.y) * (1.0 - uInkMode);
  }

  col += cLight * s.g * 1.5;
  if (uInkMode > 0.5) {
    float hatch = step(0.82, fract((gl_FragCoord.x + gl_FragCoord.y) / (5.0 * uDpr)));
    col = mix(col, cInk, hatch * 0.35 * s.a);
  }
  col += (hash12(gl_FragCoord.xy) - 0.5) / 255.0;
  gl_FragColor = vec4(col, s.a);
}
`;

export function createGround(shared, skyUniforms) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const uniforms = {
    ...shared,
    ...skyUniforms,
    uSil: { value: null },
    cGround: { value: new THREE.Vector3() },
    cGroundHaze: { value: new THREE.Vector3() },
    cLight: { value: new THREE.Vector3() },
    cInk: { value: new THREE.Vector3() },
    uSea: { value: 0 },
    uTime: { value: 0 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: FULLSCREEN_VERTEX,
    fragmentShader: FRAGMENT,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  let texture = null;
  return {
    mesh,
    uniforms,
    setSilhouette(kind, seed, width, height) {
      const canvas = paintSilhouette(kind, seed, width, height);
      if (texture) texture.dispose();
      texture = new THREE.CanvasTexture(canvas);
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = false;
      texture.colorSpace = THREE.NoColorSpace;
      uniforms.uSil.value = texture;
      uniforms.uSea.value = kind === "sea" ? 1 : 0;
    },
  };
}
