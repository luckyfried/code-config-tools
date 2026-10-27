// Drifting fog banks: soft billboards in layers at three heights, each layer on its own wind, lit where the beam
// passes through them, so the beam cuts through visible fog rather than a flat tint.
import * as THREE from "three";
import { BEAM_LIGHT } from "./glsl.js";
import { softSprite } from "./geometry.js";

const SPAN = 380;

export function createFogBanks(tokens, tier, beamUniforms) {
  const layers = tier.fogLayers;
  const count = tier.fogSprites;
  const base = new THREE.PlaneGeometry(1, 1);
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.index = base.index;
  geometry.setAttribute("position", base.attributes.position);
  geometry.setAttribute("uv", base.attributes.uv);
  const offsets = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const seeds = new Float32Array(count);
  const winds = new Float32Array(count * 2);
  let seed = 11;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < count; i++) {
    const layer = i % layers;
    const heights = layers === 1 ? [4.5] : [2.5, 7, 13];
    offsets[i * 3] = (rand() - 0.5) * SPAN;
    offsets[i * 3 + 1] = heights[layer] + (rand() - 0.5) * 2.5;
    offsets[i * 3 + 2] = (rand() - 0.5) * SPAN - 40;
    sizes[i] = 40 + rand() * 44 + layer * 10;
    seeds[i] = rand();
    const speed = [1.6, 1.0, 0.55][layer];
    winds[i * 2] = speed;
    winds[i * 2 + 1] = speed * 0.35;
  }
  geometry.setAttribute("aOffset", new THREE.InstancedBufferAttribute(offsets, 3));
  geometry.setAttribute("aSize", new THREE.InstancedBufferAttribute(sizes, 1));
  geometry.setAttribute("aSeed", new THREE.InstancedBufferAttribute(seeds, 1));
  geometry.setAttribute("aWind", new THREE.InstancedBufferAttribute(winds, 2));
  geometry.instanceCount = count;

  const uniforms = {
    ...beamUniforms,
    uMap: { value: softSprite(256, 0, 9) },
    uTime: { value: 0 },
    uColor: { value: tokens.fog.clone() },
    uBeam: { value: tokens.beam.clone() },
    uOpacity: { value: (tokens.dark ? 0.26 : 0.28) * tokens.fogLayer * (layers === 1 ? 1.5 : 1) },
    uFlash: { value: 0 },
    uFlare: { value: 0 },
    uThick: { value: 1 },
    uCenter: { value: new THREE.Vector3() },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    transparent: true,
    depthWrite: false,
    fog: false,
    vertexShader: /* glsl */ `
      attribute vec3 aOffset;
      attribute float aSize;
      attribute float aSeed;
      attribute vec2 aWind;
      uniform float uTime;
      uniform vec3 uCenter;
      varying vec2 vUv;
      varying float vLit;
      varying float vAlpha;
      varying float vWorldY;
      ${BEAM_LIGHT}
      void main() {
        vec3 c = aOffset;
        c.xz += aWind * uTime;
        c.xz = mod(c.xz - uCenter.xz + ${(SPAN / 2).toFixed(1)}, ${SPAN.toFixed(1)}) - ${(SPAN / 2).toFixed(1)} + uCenter.xz;
        c.y += sin(uTime * 0.2 + aSeed * 30.0) * 0.6;
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        float ang = aSeed * 6.2831 + uTime * 0.02 * (aSeed - 0.5);
        vec2 q = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * position.xy;
        vec3 w = c + (right * q.x + up * q.y * 0.6) * aSize;
        vWorldY = w.y;
        vUv = uv;
        vLit = beamLight(c, 1.8) + beamLight(w, 1.4) * 0.5;
        float d = length(cameraPosition - c);
        vAlpha = smoothstep(16.0, 70.0, d) * (1.0 - smoothstep(180.0, 300.0, d));
        gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap;
      uniform vec3 uColor, uBeam;
      uniform float uOpacity, uFlash, uFlare, uThick;
      varying vec2 vUv;
      varying float vLit;
      varying float vAlpha;
      varying float vWorldY;
      void main() {
        float rim = 1.0 - smoothstep(0.18, 0.5, length(vUv - 0.5));
        float a = texture2D(uMap, vUv).a * rim * rim * vAlpha * uOpacity * uThick * smoothstep(-0.5, 4.0, vWorldY);
        vec3 col = uColor * (1.0 + uFlare * 0.6) + uBeam * vLit * 1.6 + vec3(0.8, 0.85, 1.0) * uFlash * 0.8;
        gl_FragColor = vec4(col, a * (1.0 + vLit * 0.8));
      }
    `,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.renderOrder = 4;
  return {
    mesh,
    uniforms,
    update(time, camera) {
      uniforms.uTime.value = time;
      uniforms.uCenter.value.set(camera.position.x, 0, camera.position.z - 120);
    },
  };
}
