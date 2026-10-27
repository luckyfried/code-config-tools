// The ground: one plane to the horizon, painted in the shader. Main Street's packed dirt with wagon ruts and hoof
// scuffs narrows to a trail past the last building; the desert around it ripples and scatters pebbles near the eye.
import * as THREE from "three";

const common = /* glsl */ `
  uniform vec3 uGround;
  uniform vec3 uRut;
  varying vec3 vGroundWorld;
  float ghash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
  float gnoise(vec2 p) {
    vec2 i = floor(p); vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(ghash(i), ghash(i + vec2(1.0, 0.0)), u.x), mix(ghash(i + vec2(0.0, 1.0)), ghash(i + vec2(1.0, 1.0)), u.x), u.y);
  }
  float gfbm(vec2 p) {
    float v = 0.0; float a = 0.5;
    for (int i = 0; i < 4; i++) { v += a * gnoise(p); p *= 2.07; a *= 0.5; }
    return v;
  }
`;

const paint = /* glsl */ `
  vec2 wp = vGroundWorld.xz;
  float vDist = length(vGroundWorld - cameraPosition);
  float town = smoothstep(-150.0, -112.0, wp.y);
  float bend = (1.0 - town) * sin(wp.y * 0.011) * 4.0;
  float halfW = mix(2.6, 6.8, town);
  float ax = abs(wp.x - bend);
  float road = 1.0 - smoothstep(halfW, halfW + mix(2.0, 2.6, town), ax + (gnoise(wp * 0.35) - 0.5) * 1.2);

  // wheel ruts: two worn lanes, wandering a little
  float wob = (gnoise(vec2(wp.y * 0.06, 3.1)) - 0.5) * 0.45;
  float rx = abs(wp.x - bend + wob);
  float rut = 0.0;
  rut += 1.0 - smoothstep(0.06, 0.3, abs(rx - 0.78));
  rut += (1.0 - smoothstep(0.06, 0.3, abs(rx - 2.55))) * town;
  rut *= road * (0.55 + 0.45 * gnoise(wp * vec2(0.6, 0.08)));

  // hoof scuffs in the middle of the street
  float hoof = smoothstep(0.72, 0.9, gnoise(wp * 2.6)) * (1.0 - smoothstep(0.0, 1.6, abs(wp.x - bend))) * road;

  float detailFade = 1.0 - smoothstep(18.0, 70.0, vDist);
  float big = gfbm(wp * 0.018);
  float mid = gnoise(wp * 0.22);
  float fine = gnoise(wp * 3.1) * detailFade;
  float ripple = (sin(wp.x * 1.7 + gnoise(wp * 0.15) * 6.0 + wp.y * 0.4) * 0.5 + 0.5) * (1.0 - road) * detailFade;
  vec2 pc = floor(wp * 7.0);
  vec2 pf = fract(wp * 7.0) - vec2(ghash(pc), ghash(pc + 17.0)) * 0.6 - 0.2;
  float pebble = step(0.9, ghash(pc + 3.0)) * (1.0 - smoothstep(0.05, 0.13, length(pf))) * detailFade * (0.5 + 0.5 * road);

  vec3 desert = uGround * vec3(1.06, 0.98, 0.92);
  vec3 street = uGround * 0.92;
  vec3 col = mix(desert, street, road);
  col *= 0.86 + big * 0.28;
  col *= 0.94 + mid * 0.1;
  col *= 0.95 + fine * 0.1;
  col *= 1.0 - ripple * 0.05;
  col = mix(col, uRut, clamp(rut * 0.7 + hoof * 0.35, 0.0, 0.85));
  col *= 1.0 - pebble * 0.35;
  diffuseColor.rgb = col;
`;

export function createGround(tokens) {
  const uniforms = {
    uGround: { value: tokens.ground.clone() },
    uRut: { value: tokens.groundRut.clone() },
  };
  const material = new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0, envMapIntensity: 0.35 });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vGroundWorld;")
      .replace(
        "#include <fog_vertex>",
        "#include <fog_vertex>\nvGroundWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${common}`)
      .replace("#include <map_fragment>", paint);
  };
  material.customProgramCacheKey = () => "quick-draw-ground";

  const geometry = new THREE.PlaneGeometry(3000, 3000, 1, 1);
  geometry.rotateX(-Math.PI / 2);
  geometry.translate(0, 0, -1200);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = "ground";
  mesh.receiveShadow = true;

  return {
    mesh,
    apply(t) {
      uniforms.uGround.value.copy(t.ground);
      uniforms.uRut.value.copy(t.groundRut);
    },
  };
}
