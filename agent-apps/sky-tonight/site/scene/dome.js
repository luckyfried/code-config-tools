// The sky dome: one full-screen pass that turns each pixel back into a direction and colors it by the Sun's
// altitude, the Moon, the glow of the horizon, and the Milky Way panorama in galactic coordinates.
import * as THREE from "three";
import { PROJECTION, SKY_COLOR, DITHER, FULLSCREEN_VERTEX } from "./shaders.js";
import { EQ_TO_GAL } from "./astro.js";

const FRAGMENT = /* glsl */ `
${PROJECTION}
${SKY_COLOR}
${DITHER}
uniform sampler2D uMW;
uniform float uMWAmt;
uniform mat3 uGal;
uniform vec3 cInk;
uniform float uMono;
uniform vec3 uTint;

void main() {
  vec3 d = dirFromFrag(gl_FragCoord.xy);
  vec3 col = skyColor(d);

  if (uMWAmt > 0.001) {
    vec3 eq = transpose(uSky) * d;
    vec3 g = uGal * eq;
    float l = atan(g.y, g.x);
    float b = asin(clamp(g.z, -1.0, 1.0));
    vec2 uv = vec2(0.5 - l / 6.2831853, 0.5 + b / 3.1415927);
    vec2 uv2 = vec2(fract(uv.x + 0.5), uv.y);
    vec2 dx = dFdx(uv), dy = dFdy(uv);
    vec2 dx2 = dFdx(uv2), dy2 = dFdy(uv2);
    if (abs(dx2.x) + abs(dy2.x) < abs(dx.x) + abs(dy.x)) { dx = dx2; dy = dy2; }
    vec3 mw = textureGrad(uMW, uv, dx * 5.0, dy * 5.0).rgb;
    mw = max(mw - vec3(0.035), vec3(0.0));
    float lum = dot(mw, vec3(0.299, 0.587, 0.114));
    mw = mix(mix(vec3(lum), mw, 0.8), uTint * lum * 1.2, uMono);
    float t2 = smoothstep(-13.0, -6.0, uSunAlt);
    float hz = smoothstep(0.0, 0.22, d.y);
    float amt = uMWAmt * (1.0 - t2) * (1.0 - 0.75 * uMoonLight) * hz;
    vec3 add = pow(mw, vec3(1.15)) * 1.35 * amt;
    col = mix(col + add, mix(col, cInk, clamp(lum * 1.6 * amt, 0.0, 0.5)), uInkMode);
  }

  col += (hash12(gl_FragCoord.xy) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}
`;

export function createDome(shared, skyUniforms) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const uniforms = {
    ...shared,
    ...skyUniforms,
    uMW: { value: null },
    uMWAmt: { value: 0 },
    uGal: { value: new THREE.Matrix3().set(...EQ_TO_GAL) },
    cInk: { value: new THREE.Vector3() },
    uMono: { value: 0 },
    uTint: { value: new THREE.Vector3(1, 1, 1) },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: FULLSCREEN_VERTEX,
    fragmentShader: FRAGMENT,
    depthTest: false,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  return {
    mesh,
    uniforms,
    setTexture(texture) {
      uniforms.uMW.value = texture;
    },
  };
}
