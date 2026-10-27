// Weather: rain streaks in a box that travels with the camera, spray thrown up off the reef, and thunder, a flash
// with a double flicker (a gentle fade when the person asks for reduced motion) that the sound follows.
import * as THREE from "three";
import { BEAM_LIGHT } from "./glsl.js";
import { softSprite } from "./geometry.js";

const BOX = new THREE.Vector3(70, 40, 70);

function createRain(tokens, tier, beamUniforms) {
  const count = Math.round(2400 * tokens.rainAmount * tier.rain);
  const positions = new Float32Array(Math.max(count, 1) * 2 * 3);
  const ends = new Float32Array(Math.max(count, 1) * 2);
  let seed = 23;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < count; i++) {
    const x = rand() * BOX.x;
    const y = rand() * BOX.y;
    const z = rand() * BOX.z;
    for (let k = 0; k < 2; k++) {
      positions.set([x, y, z], (i * 2 + k) * 3);
      ends[i * 2 + k] = k;
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aEnd", new THREE.BufferAttribute(ends, 1));
  const uniforms = {
    ...beamUniforms,
    uTime: { value: 0 },
    uColor: { value: tokens.rain.clone() },
    uBeam: { value: tokens.beam.clone() },
    uFlash: { value: 0 },
    uFlare: { value: 0 },
    uBox: { value: BOX.clone() },
    uOrigin: { value: new THREE.Vector3() },
    uBase: { value: tokens.dark ? 0.16 : 0.32 },
    uClear: { value: new THREE.Vector4(0, 0, 0, 0) },
    uClearOn: { value: 1 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    transparent: true,
    depthWrite: false,
    blending: tokens.dark ? THREE.AdditiveBlending : THREE.NormalBlending,
    fog: false,
    vertexShader: /* glsl */ `
      attribute float aEnd;
      uniform float uTime;
      uniform vec3 uBox, uOrigin;
      varying float vLit;
      varying float vEnd;
      ${BEAM_LIGHT}
      void main() {
        vec3 p = position;
        p.y = mod(p.y - uTime * 34.0, uBox.y);
        p.x = mod(p.x + uTime * 6.0 - uOrigin.x, uBox.x);
        p.z = mod(p.z - uOrigin.z, uBox.z);
        vec3 w = vec3(uOrigin.x + p.x - uBox.x * 0.5, p.y - 2.0, uOrigin.z + p.z - uBox.z * 0.5);
        w += vec3(-0.18, 1.0, 0.0) * aEnd * 0.9;
        vLit = beamLight(w, 2.2);
        vEnd = aEnd;
        gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor, uBeam;
      uniform float uFlash, uFlare, uBase, uClearOn;
      uniform vec4 uClear;
      varying float vLit;
      varying float vEnd;
      void main() {
        // The rain thins out over the title copy (uClear: its box in drawing-buffer pixels, then the feather).
        vec2 q = gl_FragCoord.xy;
        float inX = smoothstep(uClear.x - uClear.w, uClear.x, q.x) * (1.0 - smoothstep(uClear.z, uClear.z + uClear.w, q.x));
        float inY = 1.0 - smoothstep(uClear.y, uClear.y + uClear.w, q.y);
        float a = (uBase + vLit * 0.9 + uFlash * 0.6 + uFlare * 0.3) * (0.35 + vEnd * 0.65) * (1.0 - uClearOn * inX * inY);
        gl_FragColor = vec4(uColor + uBeam * vLit * 1.5, a);
      }
    `,
  });
  const lines = new THREE.LineSegments(geometry, material);
  lines.frustumCulled = false;
  lines.renderOrder = 7;
  lines.visible = count > 0;
  return { lines, uniforms };
}

function createSpray(tokens, tier, reef, beamUniforms) {
  const count = tier.spray;
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count * 4);
  let seed = 41;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < count; i++) {
    const r = reef[i % reef.length];
    positions.set([r.x, r.y, r.z], i * 3);
    seeds.set([rand(), rand(), rand(), rand()], i * 4);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 4));
  const uniforms = {
    ...beamUniforms,
    uTime: { value: 0 },
    uMap: { value: softSprite(64, 0.1) },
    uColor: { value: tokens.seaFoam.clone() },
    uBeam: { value: tokens.beam.clone() },
    uScale: { value: 800 },
    uFlare: { value: 0 },
    uFlash: { value: 0 },
    uBase: { value: tokens.dark ? 0.35 : 0.85 },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    transparent: true,
    depthWrite: false,
    vertexShader: /* glsl */ `
      attribute vec4 aSeed;
      uniform float uTime, uScale;
      varying float vAlpha;
      varying float vLit;
      ${BEAM_LIGHT}
      void main() {
        float life = 1.5 + aSeed.w * 0.9;
        float cycle = (uTime + aSeed.x * 17.0) / life;
        float t = fract(cycle);
        float burst = step(0.45, fract(sin(floor(cycle) * 12.9898 + aSeed.y * 78.233) * 43758.5453));
        float ang = aSeed.y * 6.2831;
        vec3 v = vec3(cos(ang) * (1.2 + aSeed.z * 2.0), 5.0 + aSeed.z * 5.5, sin(ang) * (1.2 + aSeed.z * 2.0));
        float s = t * life;
        vec3 w = position + v * s + vec3(0.0, -6.5 * s * s, 0.0);
        vAlpha = burst * (1.0 - t) * smoothstep(0.0, 0.08, t) * step(-0.5, w.y);
        vLit = beamLight(w, 2.5);
        vec4 mv = viewMatrix * vec4(w, 1.0);
        gl_PointSize = uScale * (0.35 + t * 0.9) / -mv.z;
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap;
      uniform vec3 uColor, uBeam;
      uniform float uBase, uFlare, uFlash;
      varying float vAlpha;
      varying float vLit;
      void main() {
        float a = texture2D(uMap, gl_PointCoord).a * vAlpha;
        gl_FragColor = vec4(uColor * (uBase + uFlare + uFlash) + uBeam * vLit * 2.0, a * 0.75);
      }
    `,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  points.renderOrder = 3;
  return { points, uniforms };
}

export function createWeather(tokens, tier, reef, beamUniforms, reducedMotion) {
  const rain = createRain(tokens, tier, beamUniforms);
  const spray = createSpray(tokens, tier, reef, beamUniforms);
  const thunder = { at: -1, value: 0, onStrike: null };
  return {
    rain,
    spray,
    thunder,
    strike(now) {
      thunder.at = now;
      if (thunder.onStrike) thunder.onStrike();
    },
    update(time, now, camera, flare) {
      rain.uniforms.uTime.value = time;
      rain.uniforms.uOrigin.value.set(camera.position.x, 0, camera.position.z - 26);
      spray.uniforms.uTime.value = time;
      let f = 0;
      if (thunder.at >= 0) {
        const t = now - thunder.at;
        if (reducedMotion.matches) {
          f = t < 1.4 ? Math.sin((t / 1.4) * Math.PI) * 0.3 : 0;
        } else {
          f = Math.exp(-t * 7) + (t > 0.16 ? 0.75 * Math.exp(-(t - 0.16) * 6) : 0) + (t > 0.42 ? 0.35 * Math.exp(-(t - 0.42) * 4) : 0);
        }
        if (t > 2.5) thunder.at = -1;
      }
      thunder.value = Math.min(1.2, f);
      rain.uniforms.uFlash.value = thunder.value;
      rain.uniforms.uFlare.value = flare;
      spray.uniforms.uFlash.value = thunder.value;
      spray.uniforms.uFlare.value = flare;
    },
  };
}
