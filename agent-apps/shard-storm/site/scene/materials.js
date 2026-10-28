// One export per look. Each takes the theme's mode: "glow" (light on a dark field: additive, bloomed) or "day"
// (light on a pale field: white-hot cores that bloom, vivid colored rims, and a soft colored glow under each shard). `shared` holds the uniforms every layer reads:
// the quiet rectangle behind the title type, how quiet it is, and the fade of a death.
import * as THREE from "three";

export const shared = {
  uQuiet: { value: [0, 1, 2].map(() => new THREE.Vector4(-3, -3, -3, -3)) },
  uQuietAmt: { value: 0 },
  uFade: { value: 1 },
};

const QUIET = /* glsl */ `
  uniform vec4 uQuiet[3];
  uniform float uQuietAmt;
  float quietRect(vec2 ndc, vec4 r) {
    vec2 lo = smoothstep(r.xy - 0.16, r.xy + 0.03, ndc);
    vec2 hi = 1.0 - smoothstep(r.zw - 0.03, r.zw + 0.16, ndc);
    return lo.x * lo.y * hi.x * hi.y;
  }
  float quietMask(vec4 clip) {
    vec2 ndc = clip.xy / clip.w;
    float q = max(quietRect(ndc, uQuiet[0]), max(quietRect(ndc, uQuiet[1]), quietRect(ndc, uQuiet[2])));
    return 1.0 - uQuietAmt * q;
  }
`;

const dayDefines = (mode) => (mode === "day" ? { DAY: 1 } : {});

/** The shards: octahedra with a white-hot core, over black in glow and over the pale field in day. */
export function shardMaterial(mode) {
  return new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: { uQuiet: shared.uQuiet, uQuietAmt: shared.uQuietAmt, uFade: shared.uFade },
    vertexShader: /* glsl */ `
      ${QUIET}
      varying vec3 vColor;
      varying vec3 vNormal;
      varying vec3 vView;
      varying float vQuiet;
      void main() {
        vec4 world = modelMatrix * instanceMatrix * vec4(position, 1.0);
        vColor = instanceColor;
        vNormal = normalize(mat3(modelMatrix * instanceMatrix) * normal);
        vec4 mv = viewMatrix * world;
        vView = -mv.xyz;
        gl_Position = projectionMatrix * mv;
        vQuiet = quietMask(gl_Position);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uFade;
      varying vec3 vColor;
      varying vec3 vNormal;
      varying vec3 vView;
      varying float vQuiet;
      void main() {
        vec3 n = normalize(vNormal);
        vec3 v = normalize(vView);
        float facing = abs(dot(n, v));
        #ifdef DAY
          // The rim keeps the shard's full color; the face burns to white past 1.0, which the bloom spreads as light.
          float core = pow(facing, 4.0);
          vec3 col = mix(vColor * (0.95 + 0.4 * facing), vec3(1.0), core * 0.8);
          col *= 1.0 + 0.9 * core;
          gl_FragColor = vec4(col, uFade * mix(0.16, 1.0, vQuiet));
        #else
          vec3 col = vColor * (0.5 + 0.95 * facing * facing) + vec3(pow(facing, 6.0) * 0.75);
          gl_FragColor = vec4(col * uFade * mix(0.14, 1.0, vQuiet), 1.0);
        #endif
      }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: mode === "day" ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
}

/** The soft light under every shard, drawn from the shard's own position and size: added in glow, a colored haze in day. */
export function haloMaterial(mode) {
  const m = new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: { uQuiet: shared.uQuiet, uQuietAmt: shared.uQuietAmt, uFade: shared.uFade },
    vertexShader: /* glsl */ `
      ${QUIET}
      varying vec2 vUv;
      varying vec3 vColor;
      varying float vQuiet;
      void main() {
        vec3 center = (modelMatrix * vec4(instanceMatrix[3].xyz, 1.0)).xyz;
        float size = length(instanceMatrix[0].xyz);
        float span = size * 3.4;
        vec3 world = center + vec3(position.xy * span, -0.02);
        vUv = position.xy * 2.0;
        vColor = instanceColor;
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
        vQuiet = quietMask(gl_Position);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uFade;
      varying vec2 vUv;
      varying vec3 vColor;
      varying float vQuiet;
      void main() {
        float r2 = dot(vUv, vUv);
        if (r2 > 1.0) discard;
        float falloff = exp(-r2 * 4.0) - 0.018;
        #ifdef DAY
          // A tint lighter than the field around each shard, so the storm lifts the page instead of staining it.
          gl_FragColor = vec4(mix(vColor * 1.15, vec3(1.0), 0.4), falloff * 0.5 * uFade * mix(0.12, 1.0, vQuiet));
        #else
          gl_FragColor = vec4(vColor * falloff * 0.075 * uFade * mix(0.1, 1.0, vQuiet), 1.0);
        #endif
      }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  m.blending = mode === "day" ? THREE.NormalBlending : THREE.AdditiveBlending;
  return m;
}

/** Graze sparks: streaks animated wholly in the vertex shader from their birth time, origin, and velocity. */
export function sparkMaterial(mode) {
  return new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: { uTime: { value: 0 } },
    vertexShader: /* glsl */ `
      uniform float uTime;
      attribute vec4 aMotion;
      attribute vec2 aLife;
      attribute vec3 aColor;
      varying float vAlpha;
      varying float vAcross;
      varying vec3 vColor;
      void main() {
        float age = uTime - aLife.x;
        float t = age / aLife.y;
        if (t < 0.0 || t > 1.0) {
          gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
          return;
        }
        const float drag = 3.2;
        vec2 vel = aMotion.zw;
        vec2 p = aMotion.xy + vel * (1.0 - exp(-drag * age)) / drag;
        vec2 v = vel * exp(-drag * age);
        float speed = length(v);
        vec2 dir = speed > 0.001 ? v / speed : vec2(1.0, 0.0);
        vec2 side = vec2(-dir.y, dir.x);
        float len = 0.2 + speed * 0.075;
        float wide = 0.16 * (1.0 - t);
        vec2 world = p + dir * position.x * len + side * position.y * wide;
        vAlpha = (1.0 - t) * (1.0 - t);
        vAcross = position.y * 2.0;
        vColor = aColor;
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 0.06, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      varying float vAlpha;
      varying float vAcross;
      varying vec3 vColor;
      void main() {
        float edge = 1.0 - vAcross * vAcross;
        #ifdef DAY
          gl_FragColor = vec4(vColor, vAlpha * edge);
        #else
          gl_FragColor = vec4(vColor * 1.5 * vAlpha * edge + vec3(0.3) * vAlpha * edge * edge, 1.0);
        #endif
      }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: mode === "day" ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
}

/** Stars: soft round points that twinkle and scroll down, wrapping inside their layer's extent. */
export function starMaterial(mode, color, speed, size) {
  return new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: color.clone() },
      uSpeed: { value: speed },
      uSize: { value: size },
      uExtent: { value: new THREE.Vector2(100, 100) },
      uRatio: { value: 1 },
      uFade: shared.uFade,
    },
    vertexShader: /* glsl */ `
      uniform float uTime;
      uniform float uSpeed;
      uniform float uSize;
      uniform vec2 uExtent;
      uniform float uRatio;
      attribute float aSeed;
      varying float vTwinkle;
      void main() {
        vec2 unit = position.xy;
        unit.y = mod(unit.y - uTime * uSpeed + 1.0, 2.0) - 1.0;
        vec4 mv = modelViewMatrix * vec4(unit * uExtent, position.z, 1.0);
        gl_Position = projectionMatrix * mv;
        float big = step(0.93, aSeed);
        gl_PointSize = uSize * uRatio * (0.6 + 0.8 * fract(aSeed * 13.7) + big * 1.4);
        vTwinkle = 0.55 + 0.45 * sin(uTime * (0.8 + aSeed * 2.6) + aSeed * 40.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uFade;
      varying float vTwinkle;
      void main() {
        float d = length(gl_PointCoord - 0.5);
        float a = smoothstep(0.5, 0.0, d);
        #ifdef DAY
          gl_FragColor = vec4(uColor, a * a * 0.55 * vTwinkle);
        #else
          gl_FragColor = vec4(uColor * a * a * vTwinkle * (0.5 + 0.5 * uFade), 1.0);
        #endif
      }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: mode === "day" ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
}

/** The far backdrop: a lit gradient, a faint grid that scrolls, and rings that breathe out from the storm's eye. */
export function backdropMaterial(mode, tokens) {
  return new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: {
      uBg: { value: tokens.bg.clone() },
      uBg2: { value: tokens.bg2.clone() },
      uGrid: { value: tokens.grid.clone() },
      uTime: { value: 0 },
      uEye: { value: new THREE.Vector2() },
      uSpan: { value: 100 },
      uPulse: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vPos;
      void main() {
        vPos = (modelMatrix * vec4(position, 1.0)).xy;
        gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uBg;
      uniform vec3 uBg2;
      uniform vec3 uGrid;
      uniform float uTime;
      uniform vec2 uEye;
      uniform float uSpan;
      uniform float uPulse;
      varying vec2 vPos;
      float hash(vec2 p) {
        return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
      }
      float lines(vec2 p, float cell) {
        vec2 g = abs(fract(p / cell - 0.5) - 0.5) * cell;
        vec2 w = fwidth(p) * 1.2;
        vec2 l = 1.0 - smoothstep(vec2(0.0), w, g);
        return max(l.x, l.y);
      }
      void main() {
        vec2 rel = vPos - uEye;
        float r = length(rel) / uSpan;
        #ifdef DAY
          vec3 col = mix(uBg, uBg2, smoothstep(0.15, 1.25, r));
        #else
          vec3 col = mix(uBg2, uBg, smoothstep(0.0, 1.05, r));
        #endif
        vec2 scroll = vec2(0.0, uTime * 2.2);
        float grid = lines(vPos + scroll, 12.0) + 0.5 * lines(vPos + scroll, 60.0);
        float rr = length(rel);
        float ringPhase = rr / 22.0 - uTime * 0.12;
        float ringDist = abs(fract(ringPhase) - 0.5) * 22.0;
        float ring = 1.0 - smoothstep(0.0, fwidth(rr) * 1.6, ringDist);
        float fade = 1.0 - smoothstep(0.1, 1.15, r);
        #ifdef DAY
          float amount = (grid * 0.085 + ring * 0.07) * (0.35 + 0.65 * fade);
          col = mix(col, uGrid, amount);
          col *= 1.0 - 0.035 * hash(floor(vPos * 6.0));
        #else
          float amount = (grid * 0.07 + ring * (0.08 + 0.12 * uPulse)) * fade;
          col = mix(col, uGrid, amount);
          col += uGrid * 0.06 * uPulse * fade;
        #endif
        gl_FragColor = vec4(col, 1.0);
      }
    `,
    depthTest: false,
    depthWrite: false,
  });
}

/** The ship's hull: flat-shaded facets in its own color, bright enough to bloom in glow. */
export function hullMaterial(mode, color) {
  return new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: { uColor: { value: color.clone() }, uFlash: { value: 0 } },
    vertexShader: /* glsl */ `
      varying vec3 vView;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vView = mv.xyz;
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uFlash;
      varying vec3 vView;
      void main() {
        vec3 n = normalize(cross(dFdx(vView), dFdy(vView)));
        float light = 0.45 + 0.55 * max(dot(n, normalize(vec3(-0.4, 0.6, 0.7))), 0.0);
        #ifdef DAY
          vec3 col = uColor * (0.55 + 0.6 * light);
        #else
          vec3 col = uColor * (0.7 + 1.1 * light);
        #endif
        gl_FragColor = vec4(mix(col, vec3(1.6), uFlash), 1.0);
      }
    `,
    side: THREE.DoubleSide,
    depthTest: false,
    depthWrite: false,
  });
}

/** A flat color layer for the ship's core, rings, trail, and engine; additive in glow. */
export function flatMaterial(mode, color, opacity, additive = true) {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    depthTest: false,
    depthWrite: false,
    blending: additive && mode !== "day" ? THREE.AdditiveBlending : THREE.NormalBlending,
    side: THREE.DoubleSide,
    // Flat shapes facing the camera need one pass; two would recompile their program state twice every frame.
    forceSinglePass: true,
  });
}

/** The ship's wake: a tapering ribbon whose alpha runs out along its length. */
export function trailMaterial(mode, color) {
  return new THREE.ShaderMaterial({
    defines: dayDefines(mode),
    uniforms: { uColor: { value: color.clone() } },
    vertexShader: /* glsl */ `
      attribute float aAlong;
      varying float vAlong;
      void main() {
        vAlong = aAlong;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      varying float vAlong;
      void main() {
        float a = pow(1.0 - vAlong, 1.6);
        #ifdef DAY
          gl_FragColor = vec4(uColor, a * 0.55);
        #else
          gl_FragColor = vec4(uColor * a * 1.4, 1.0);
        #endif
      }
    `,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: mode === "day" ? THREE.NormalBlending : THREE.AdditiveBlending,
  });
}
