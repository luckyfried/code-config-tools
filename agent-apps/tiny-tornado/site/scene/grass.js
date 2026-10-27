// Grass and wheat: instanced blades on a patch that travels with the storm (each blade wraps to stay inside it). A
// blade's color and height come from the ground maps, so wheat fields grow gold and roads stay bare. Every blade leans
// toward the funnel and swirls around it, harder the closer it is, under a slow wind; a pulse sends a ring outward.
import * as THREE from "three";
import { NOISE } from "./glsl.js";
import { GROUND_SIZE } from "./ground.js";

export const MAX_BLADES = 36000;
const PATCH = 70;

export function createGrass({ ground, funnel, tokens, blades }) {
  const base = new THREE.BufferGeometry();
  // Five points: two pairs up the blade and a tip; y runs 0 to 1, x is the side.
  base.setAttribute("position", new THREE.BufferAttribute(new Float32Array([
    -0.5, 0, 0, 0.5, 0, 0, -0.38, 0.45, 0, 0.38, 0.45, 0, 0, 1, 0,
  ]), 3));
  base.setIndex([0, 1, 2, 2, 1, 3, 2, 3, 4]);
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.index = base.index;
  geometry.setAttribute("position", base.getAttribute("position"));
  const seeds = new Float32Array(MAX_BLADES * 4);
  let s = 424242;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < MAX_BLADES; i++) {
    seeds[i * 4] = rnd() * PATCH;
    seeds[i * 4 + 1] = rnd() * PATCH;
    seeds[i * 4 + 2] = rnd();
    seeds[i * 4 + 3] = rnd();
  }
  geometry.setAttribute("aSeed", new THREE.InstancedBufferAttribute(seeds, 4));
  geometry.instanceCount = blades;

  const uniforms = {
    ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
    uCenter: { value: new THREE.Vector2() },
    uMap: { value: ground.mapTexture },
    uDensity: { value: ground.densityTexture },
    uFunnel: { value: new THREE.Vector2() },
    uReach: { value: 2 },
    uTime: { value: 0 },
    uPulseR: { value: -100 },
    uTip: { value: new THREE.Color() },
    uHeight: { value: 1 },
    uSunDir: { value: new THREE.Vector3(0.5, 0.5, 0.5) },
    uSun: { value: new THREE.Color(1, 1, 1) },
    uSky: { value: new THREE.Color(1, 1, 1) },
    uGroundCol: { value: new THREE.Color(0.3, 0.3, 0.3) },
    uFlash: { value: 0 },
    uFlashCol: { value: new THREE.Color(1, 1, 1) },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: /* glsl */ `
      ${NOISE}
      attribute vec4 aSeed;
      uniform vec2 uCenter;
      uniform sampler2D uMap;
      uniform sampler2D uDensity;
      uniform vec2 uFunnel;
      uniform float uReach;
      uniform float uTime;
      uniform float uPulseR;
      uniform float uHeight;
      varying vec3 vColor;
      varying float vY;
      varying float vLean;
      #include <fog_pars_vertex>
      void main() {
        vec2 p = uCenter + mod(aSeed.xy - uCenter + ${(PATCH / 2).toFixed(1)}, ${PATCH.toFixed(1)}) - ${(PATCH / 2).toFixed(1)};
        vec2 uv = vec2((p.x + ${(GROUND_SIZE / 2).toFixed(1)}) / ${GROUND_SIZE.toFixed(1)}, 1.0 - (p.y + ${(GROUND_SIZE / 2).toFixed(1)}) / ${GROUND_SIZE.toFixed(1)});
        float dens = texture2D(uDensity, uv).r;
        float edge = 1.0 - smoothstep(${(PATCH * 0.32).toFixed(1)}, ${(PATCH * 0.5).toFixed(1)}, length(p - uCenter));
        float h = dens * edge * uHeight * (0.55 + 0.75 * aSeed.z) * (dens > 0.95 ? 1.35 : 1.0);
        if (h < 0.06) {
          gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
          return;
        }
        vColor = texture2D(uMap, uv).rgb;
        vec2 toF = uFunnel - p;
        float d = length(toF);
        vec2 dirIn = toF / max(d, 0.001);
        vec2 swirl = vec2(-dirIn.y, dirIn.x);
        float near = exp(-max(d - uReach * 0.4, 0.0) / (uReach * 2.2));
        float wind = tt_noise(vec3(p * 0.09 + uTime * 0.35, uTime * 0.2)) - 0.5;
        float ring = exp(-pow((d - uPulseR) / 2.5, 2.0));
        vec2 lean = dirIn * near * 1.1 + swirl * near * 0.9 + vec2(0.5, 0.25) * wind * 0.8 - dirIn * ring * 1.4;
        lean += vec2(sin(uTime * 7.0 + aSeed.z * 30.0), cos(uTime * 6.0 + aSeed.w * 30.0)) * near * 0.18;
        float y = position.y;
        float bend = y * y;
        float ang = aSeed.z * 6.2831;
        vec2 side = vec2(cos(ang), sin(ang)) * position.x * 0.13 * (0.7 + h * 0.3);
        vec2 off = lean * bend * h;
        float drop = length(off) * 0.45;
        vec3 wp = vec3(p.x + side.x + off.x, max(y * h - drop * y, 0.0), p.y + side.y + off.y);
        vY = y;
        vLean = clamp(length(lean), 0.0, 1.0);
        vec4 mvPosition = viewMatrix * vec4(wp, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uTip;
      uniform vec3 uSun;
      uniform vec3 uSky;
      uniform vec3 uGroundCol;
      uniform vec3 uSunDir;
      uniform float uFlash;
      uniform vec3 uFlashCol;
      varying vec3 vColor;
      varying float vY;
      varying float vLean;
      #include <fog_pars_fragment>
      void main() {
        vec3 base = vColor * mix(0.62, 1.08, vY);
        base = mix(base, uTip * vColor * 1.6, vY * vY * (0.25 + 0.45 * vLean));
        vec3 light = uSky * 0.55 + uSun * max(uSunDir.y, 0.2) * 0.7 + uFlashCol * uFlash * 0.6;
        vec3 col = base * light;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
    side: THREE.DoubleSide,
    fog: true,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.visible = blades > 0;

  return {
    mesh,
    uniforms,
    applyTokens(t) {
      uniforms.uTip.value.copy(t.colors.grassTip);
      uniforms.uHeight.value = t.numbers.grassHeight || 1;
      uniforms.uFlashCol.value.copy(t.colors.flashLight);
    },
    setLighting({ sunDir, sunColor, sunI, skyColor, groundColor, hemiI }) {
      uniforms.uSunDir.value.copy(sunDir);
      uniforms.uSun.value.copy(sunColor).multiplyScalar(sunI * 0.45);
      uniforms.uSky.value.copy(skyColor).multiplyScalar(hemiI * 0.75);
      uniforms.uGroundCol.value.copy(groundColor);
    },
    setBlades(n) {
      geometry.instanceCount = Math.min(n, MAX_BLADES);
      mesh.visible = n > 0;
    },
    update(time, center, pulseR, flash) {
      uniforms.uTime.value = time;
      uniforms.uCenter.value.set(center.x, center.z);
      uniforms.uFunnel.value.set(funnel.shape.uFunnelPos.value.x, funnel.shape.uFunnelPos.value.z);
      uniforms.uReach.value = funnel.reach;
      uniforms.uPulseR.value = pulseR;
      uniforms.uFlash.value = flash;
    },
  };
}
