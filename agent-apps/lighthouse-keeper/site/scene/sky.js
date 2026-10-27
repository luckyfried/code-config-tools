// The sky dome: a night gradient into the fog at the horizon, the moon and its halo, stars, moving cloud, the
// lightning flash, the flare's glow, and the pink of dawn as the night ends.
import * as THREE from "three";
import { NOISE } from "./glsl.js";

export function createSky(tokens) {
  const uniforms = {
    uTop: { value: tokens.skyTop.clone() },
    uHorizon: { value: tokens.skyHorizon.clone() },
    uGlow: { value: tokens.skyGlow.clone() },
    uFog: { value: tokens.fog.clone() },
    uDawnTop: { value: tokens.dawnTop.clone() },
    uDawnHorizon: { value: tokens.dawnHorizon.clone() },
    uMoon: { value: tokens.moon.clone() },
    uMoonDir: { value: new THREE.Vector3(0, 0.3, -1).normalize() },
    uStars: { value: tokens.stars },
    uTime: { value: 0 },
    uFlash: { value: 0 },
    uFlare: { value: 0 },
    uDawn: { value: 0 },
    uCloud: { value: tokens.dark ? 0.55 : 0.4 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        gl_Position = p.xyww;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uTop, uHorizon, uGlow, uFog, uDawnTop, uDawnHorizon, uMoon, uMoonDir;
      uniform float uStars, uTime, uFlash, uFlare, uDawn, uCloud;
      varying vec3 vDir;
      ${NOISE}
      void main() {
        vec3 d = normalize(vDir);
        float h = clamp(d.y, -1.0, 1.0);
        vec3 top = mix(uTop, uDawnTop, uDawn);
        vec3 hor = mix(uHorizon, uDawnHorizon, uDawn);
        vec3 col = mix(hor, top, pow(smoothstep(0.0, 0.62, h), 0.7));
        vec2 md = normalize(uMoonDir.xz);
        vec2 dd = normalize(d.xz + 1e-4);
        float toward = dot(md, dd) * 0.5 + 0.5;
        col += uGlow * pow(toward, 4.0) * (1.0 - smoothstep(0.0, 0.45, h)) * 0.5;
        col += uDawnHorizon * uDawn * pow(toward, 2.0) * (1.0 - smoothstep(0.0, 0.3, h)) * 0.6;
        float moonDot = dot(d, normalize(uMoonDir));
        float disc = smoothstep(0.99955, 0.99975, moonDot);
        float halo = pow(max(moonDot, 0.0), 220.0) * 0.6 + pow(max(moonDot, 0.0), 18.0) * 0.12;
        vec2 cuv = d.xz / (h + 0.18) * 1.6 + vec2(uTime * 0.012, uTime * 0.004);
        float cloud = smoothstep(0.42, 0.85, lkFbm(vec3(cuv, uTime * 0.01))) * smoothstep(0.02, 0.25, h);
        vec3 starCell = floor(d * 260.0);
        float star = step(0.9975, lkHash(starCell)) * smoothstep(0.08, 0.4, h);
        star *= 0.55 + 0.45 * sin(uTime * 2.3 + lkHash(starCell + 3.1) * 40.0);
        col += uStars * star * (1.0 - cloud) * vec3(0.9, 0.95, 1.0) * (1.0 - uDawn);
        col += uMoon * (disc * 2.2 + halo) * (1.0 - cloud * 0.7);
        col = mix(col, mix(col, uFog, 0.55) + uMoon * halo * 0.3, cloud * uCloud);
        col = mix(col, uFog, 1.0 - smoothstep(-0.02, 0.16, h));
        col += vec3(0.85, 0.9, 1.0) * uFlash * (0.6 + cloud * 0.9);
        col += uGlow * uFlare * 0.55;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(900, 48, 24), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -10;
  return {
    mesh,
    uniforms,
    update(time, camera) {
      uniforms.uTime.value = time;
      mesh.position.copy(camera.position);
    },
  };
}
