// One material per look: the poster (and its reflection), the halo, the contact shadow, the floor, the backdrop,
// the spotlight cone, and the dust in the beam. Colors arrive in uniforms from the theme's tokens.
import { ShaderMaterial, AdditiveBlending, NormalBlending, DoubleSide, Color, Vector3, Vector4 } from "three";

const posterVertex = /* glsl */ `
varying vec2 vUv;
varying float vDepth;
varying float vY;
void main() {
  vUv = uv;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vY = world.y;
  vec4 mv = viewMatrix * world;
  vDepth = -mv.z;
  gl_Position = projectionMatrix * mv;
}`;

const posterFragment = /* glsl */ `
uniform sampler2D map;
uniform vec4 uCrop;
uniform float uBlur;
uniform float uBlurAdd;
uniform float uDim;
uniform float uSpot;
uniform float uRot;
uniform float uShine;
uniform float uRimStrength;
uniform float uKey;
uniform float uMirror;
uniform float uReflect;
uniform float uFogNear;
uniform float uFogFar;
uniform vec3 uRim;
uniform vec3 uFrame;
uniform vec3 uDimColor;
uniform vec3 uFog;
varying vec2 vUv;
varying float vDepth;
varying float vY;

vec3 tap(vec2 uv, float b) { return texture2D(map, uv, b).rgb; }

void main() {
  vec2 fw = vec2(0.026, 0.0173);
  vec2 inner = (vUv - fw) / (1.0 - 2.0 * fw);
  vec2 aa = max(fwidth(inner), vec2(1e-5));
  vec2 lo = clamp(inner / aa + 0.5, 0.0, 1.0);
  vec2 hi = clamp((1.0 - inner) / aa + 0.5, 0.0, 1.0);
  float inside = lo.x * lo.y * hi.x * hi.y;
  vec2 tuv = uCrop.xy + clamp(inner, 0.0, 1.0) * uCrop.zw;
  float b = uBlur + uBlurAdd;
  vec2 o = exp2(b) * vec2(0.0012, 0.0008);
  vec3 pic = 0.25 * (tap(tuv + o, b) + tap(tuv - o, b) + tap(tuv + vec2(o.x, -o.y), b) + tap(tuv + vec2(-o.x, o.y), b));
  vec3 col = mix(uFrame, pic, inside);

  float lit = uKey * mix(0.8, 1.0, smoothstep(0.0, 0.9, vUv.y));
  lit *= 1.0 + uSpot * 0.18 * smoothstep(0.2, 1.0, vUv.y);
  col *= lit;

  float band = 1.0 - smoothstep(0.0, 0.24, abs(vUv.x * 0.9 + vUv.y * 0.42 - 0.72 + uRot * 0.7));
  col += uRim * band * uShine * 0.06;

  vec2 e = min(vUv, 1.0 - vUv);
  float edge = min(e.x * 1.5, e.y);
  float rimMask = 1.0 - smoothstep(0.0, 0.016, edge);
  float lean = clamp(abs(uRot) * 1.4, 0.0, 1.0);
  float facing = mix(1.0, uRot < 0.0 ? smoothstep(0.35, 1.0, vUv.x) : smoothstep(0.65, 0.0, vUv.x), lean);
  col += uRim * rimMask * uRimStrength * (0.35 + 0.65 * uSpot) * facing;

  col = mix(col, vec3(dot(col, vec3(0.3, 0.59, 0.11))), uDim * 0.8);
  col = mix(col, uDimColor, uDim);
  col = mix(col, uFog, smoothstep(uFogNear, uFogFar, vDepth));

  float a = 1.0;
  if (uMirror > 0.5) {
    float below = clamp(-vY / 1.45, 0.0, 1.0);
    a = uReflect * pow(1.0 - below, 2.0);
  }
  gl_FragColor = vec4(col, a);
  #include <colorspace_fragment>
}`;

// The uniforms every poster shares, so a theme change is one write.
export function posterShared() {
  return {
    uRim: { value: new Color() },
    uFrame: { value: new Color() },
    uDimColor: { value: new Color() },
    uFog: { value: new Color() },
    uRimStrength: { value: 0.5 },
    uKey: { value: 1 },
    uReflect: { value: 0.4 },
    uFogNear: { value: 10 },
    uFogFar: { value: 20 },
  };
}

export function posterOwn(texture) {
  return {
    map: { value: texture },
    uCrop: { value: new Vector4(0, 0, 1, 1) },
    uBlur: { value: 0 },
    uDim: { value: 0 },
    uSpot: { value: 0 },
    uRot: { value: 0 },
    uShine: { value: 0.6 },
  };
}

export function posterMaterial(shared, own, mirror) {
  return new ShaderMaterial({
    uniforms: { ...shared, ...own, uMirror: { value: mirror ? 1 : 0 }, uBlurAdd: { value: mirror ? 1.6 : 0 } },
    vertexShader: posterVertex,
    fragmentShader: posterFragment,
    transparent: mirror,
    depthWrite: !mirror,
    side: DoubleSide,
  });
}

const flatVertex = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

export function haloMaterial() {
  return new ShaderMaterial({
    uniforms: { uColor: { value: new Color() }, uLevel: { value: 0 } },
    vertexShader: flatVertex,
    fragmentShader: /* glsl */ `
uniform vec3 uColor;
uniform float uLevel;
varying vec2 vUv;
void main() {
  vec2 p = (vUv - 0.5) * 2.0;
  float a = pow(max(1.0 - length(p), 0.0), 2.4) * uLevel;
  gl_FragColor = vec4(uColor, a);
  #include <colorspace_fragment>
}`,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
}

export function shadowMaterial() {
  return new ShaderMaterial({
    uniforms: { uLevel: { value: 0 } },
    vertexShader: flatVertex,
    fragmentShader: /* glsl */ `
uniform float uLevel;
varying vec2 vUv;
void main() {
  vec2 p = (vUv - 0.5) * 2.0;
  float a = pow(max(1.0 - length(p), 0.0), 1.5) * uLevel;
  gl_FragColor = vec4(0.0, 0.0, 0.0, a);
}`,
    transparent: true,
    depthWrite: false,
  });
}

const worldVertex = /* glsl */ `
varying vec2 vUv;
varying vec3 vWorld;
varying float vDepth;
void main() {
  vUv = uv;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorld = world.xyz;
  vec4 mv = viewMatrix * world;
  vDepth = -mv.z;
  gl_Position = projectionMatrix * mv;
}`;

export function floorMaterial() {
  return new ShaderMaterial({
    uniforms: {
      uFloor: { value: new Color() },
      uFog: { value: new Color() },
      uPool: { value: new Color() },
      uPoolAt: { value: new Vector3(0, 0, 0) },
      uRoomDim: { value: 0 },
      uFogNear: { value: 10 },
      uFogFar: { value: 20 },
    },
    vertexShader: worldVertex,
    fragmentShader: /* glsl */ `
uniform vec3 uFloor;
uniform vec3 uFog;
uniform vec3 uPool;
uniform vec3 uPoolAt;
uniform float uRoomDim;
uniform float uFogNear;
uniform float uFogFar;
varying vec3 vWorld;
varying float vDepth;
void main() {
  vec3 col = uFloor;
  vec2 d = (vWorld.xz - uPoolAt.xy) * vec2(0.85, 1.6);
  float pool = exp(-dot(d, d) * 1.5);
  col *= 1.0 - uRoomDim * uPoolAt.z * (1.0 - pool);
  col += uPool * pool * uPoolAt.z * 0.5;
  col = mix(col, uFog, smoothstep(uFogNear, uFogFar, vDepth));
  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}`,
    depthWrite: false,
  });
}

export function backdropMaterial() {
  return new ShaderMaterial({
    uniforms: {
      uType: { value: 0 },
      uStars: { value: 0 },
      uTime: { value: 0 },
      uSpotX: { value: 0 },
      uSpotLevel: { value: 0 },
      uBeamStrength: { value: 0.5 },
      uRoomDim: { value: 0 },
      uTop: { value: new Color() },
      uBottom: { value: new Color() },
      uFold: { value: new Color() },
      uFoldLight: { value: new Color() },
      uBeam: { value: new Color() },
    },
    vertexShader: worldVertex,
    fragmentShader: /* glsl */ `
uniform float uType;
uniform float uStars;
uniform float uTime;
uniform float uSpotX;
uniform float uSpotLevel;
uniform float uBeamStrength;
uniform float uRoomDim;
uniform vec3 uTop;
uniform vec3 uBottom;
uniform vec3 uFold;
uniform vec3 uFoldLight;
uniform vec3 uBeam;
varying vec3 vWorld;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main() {
  float x = vWorld.x;
  float y = vWorld.y;
  float h = clamp(y / 8.0, 0.0, 1.0);
  vec3 col = mix(uBottom, uTop, smoothstep(0.0, 1.0, h));
  float glow = exp(-pow((x - uSpotX) / 1.5, 2.0)) * uSpotLevel;
  float dark = 1.0 - uRoomDim * uSpotLevel;
  if (uType < 0.5) {
    float f1 = sin(x * 2.2 + sin(x * 0.63) * 1.5) * 0.5 + 0.5;
    float f2 = sin(x * 5.3 + 1.3 + sin(y * 0.4)) * 0.5 + 0.5;
    float fold = pow(f1, 1.7) * 0.72 + f2 * 0.28;
    vec3 velvet = mix(uFold, uFoldLight, fold * mix(1.0, 0.45, h));
    col = mix(col, velvet, 0.8);
    col *= dark;
    col += uBeam * glow * (0.35 + fold) * 0.2 * uBeamStrength * (1.0 - h * 0.7);
  } else if (uType < 1.5) {
    vec2 cell = vec2(x, y) * 6.0;
    float s = hash(floor(cell));
    float twinkle = 0.55 + 0.45 * sin(uTime * (0.8 + s * 2.5) + s * 50.0);
    float star = step(0.986, s) * (1.0 - smoothstep(0.0, 0.14, length(fract(cell) - 0.5))) * twinkle * smoothstep(0.05, 0.4, h);
    col += vec3(star) * uStars;
    col = mix(col, uFoldLight, exp(-max(y, 0.0) * 0.9) * 0.6);
    col *= dark;
    col += uBeam * glow * 0.14 * uBeamStrength * (1.0 - h);
  } else {
    float grain = hash(floor(vWorld.xy * 120.0)) - 0.5;
    col += grain * 0.02;
    float lamp = exp(-pow((x - uSpotX) / 3.0, 2.0)) * smoothstep(0.0, 0.9, h);
    col = mix(col, uFoldLight, lamp * (0.25 + 0.4 * uSpotLevel));
    col *= dark;
    col += uBeam * glow * 0.08 * uBeamStrength;
  }
  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}`,
  });
}

export function coneMaterial(height) {
  return new ShaderMaterial({
    uniforms: {
      uColor: { value: new Color() },
      uLevel: { value: 0 },
      uDrop: { value: 0 },
      uStrength: { value: 0.5 },
      uHeight: { value: height },
    },
    vertexShader: /* glsl */ `
uniform float uHeight;
varying vec3 vN;
varying vec3 vV;
varying float vH;
void main() {
  vH = clamp(0.5 - position.y / uHeight, 0.0, 1.0);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vN = normalize(normalMatrix * normal);
  vV = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}`,
    fragmentShader: /* glsl */ `
uniform vec3 uColor;
uniform float uLevel;
uniform float uDrop;
uniform float uStrength;
varying vec3 vN;
varying vec3 vV;
varying float vH;
void main() {
  float facing = abs(dot(normalize(vN), normalize(vV)));
  float core = pow(facing, 2.6);
  float edge = smoothstep(0.02, 0.22, facing) * (1.0 - smoothstep(0.22, 0.5, facing));
  core += edge * 0.55;
  float reveal = 1.0 - smoothstep(uDrop * 1.05 - 0.1, uDrop * 1.05, vH);
  float fall = mix(1.0, 0.55, vH) * (1.0 - smoothstep(0.9, 1.0, vH));
  float a = core * reveal * fall * uLevel * uStrength * 0.42;
  gl_FragColor = vec4(uColor, a);
  #include <colorspace_fragment>
}`,
    transparent: true,
    depthWrite: false,
    side: DoubleSide,
    blending: AdditiveBlending,
  });
}

export function dustMaterial(height, topR, bottomR) {
  return new ShaderMaterial({
    uniforms: {
      uColor: { value: new Color() },
      uTime: { value: 0 },
      uLevel: { value: 0 },
      uDrop: { value: 0 },
      uPixel: { value: 1 },
      uHeight: { value: height },
      uTopR: { value: topR },
      uBottomR: { value: bottomR },
    },
    vertexShader: /* glsl */ `
attribute vec4 aSeed;
uniform float uTime;
uniform float uLevel;
uniform float uDrop;
uniform float uPixel;
uniform float uHeight;
uniform float uTopR;
uniform float uBottomR;
varying float vA;
void main() {
  float h = fract(aSeed.x + uTime * (0.006 + aSeed.w * 0.008));
  float ang = aSeed.y + uTime * (0.04 + aSeed.z * 0.07);
  float rad = mix(uTopR, uBottomR, h) * aSeed.z * 0.9;
  vec3 p = vec3(cos(ang) * rad, (0.5 - h) * uHeight, sin(ang) * rad);
  p.x += sin(uTime * 0.6 + aSeed.y * 3.0) * 0.04;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = (1.3 + aSeed.w * 2.4) * uPixel * (7.0 / -mv.z);
  float reveal = 1.0 - smoothstep(uDrop - 0.1, uDrop, h);
  float twinkle = 0.5 + 0.5 * sin(uTime * (1.2 + aSeed.w * 2.2) + aSeed.y * 9.0);
  vA = uLevel * reveal * twinkle * smoothstep(0.0, 0.15, h) * (1.0 - smoothstep(0.82, 1.0, h)) * (1.0 - aSeed.z * 0.45);
}`,
    fragmentShader: /* glsl */ `
uniform vec3 uColor;
varying float vA;
void main() {
  float d = length(gl_PointCoord - 0.5);
  float a = (1.0 - smoothstep(0.0, 0.5, d)) * vA;
  gl_FragColor = vec4(uColor, a);
  #include <colorspace_fragment>
}`,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
}

// Light rooms lay light over paper and velvet with ordinary blending; dark rooms add it.
export function setBlend(material, additive) {
  material.blending = additive ? AdditiveBlending : NormalBlending;
  material.needsUpdate = true;
}
