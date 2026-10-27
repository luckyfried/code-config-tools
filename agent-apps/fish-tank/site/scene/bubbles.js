// Bubbles: instanced spheres with a bright fresnel rim, risen and wobbled on the GPU. Streams rise from the bubblers
// and the vent; bursts rise where food lands in the water.
import * as THREE from "three";
import { shared } from "./shading.js";

const PER_STREAM = 16;
const BURSTS = 48;

export function createBubbles(quality) {
  const max = PER_STREAM * 8 + BURSTS;
  const base = new THREE.IcosahedronGeometry(1, quality.phone ? 1 : 2);
  const geo = new THREE.InstancedBufferGeometry();
  geo.index = base.index;
  geo.setAttribute("position", base.attributes.position);
  geo.setAttribute("normal", base.attributes.normal);
  const origin = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
  const params = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4);
  origin.setUsage(THREE.DynamicDrawUsage);
  params.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute("iOrigin", origin);
  geo.setAttribute("iP", params);
  geo.instanceCount = 0;

  const uniforms = {
    uTime: shared.uTime,
    uSurface: { value: 8 },
    uRim: { value: new THREE.Color(0xffffff) },
    uCore: { value: new THREE.Color(0x88ccff) },
  };
  const mat = new THREE.ShaderMaterial({
    uniforms,
    transparent: true,
    depthWrite: false,
    vertexShader: /* glsl */ `
      attribute vec3 iOrigin;
      attribute vec4 iP;
      uniform float uTime, uSurface;
      varying vec3 vN;
      varying vec3 vView;
      varying float vA;
      void main() {
        float rise = max(0.5, uSurface - iOrigin.y);
        float h;
        float alive = 1.0;
        if (iP.w < 0.5) {
          h = mod(uTime * iP.y + iP.x * rise, rise);
        } else {
          float age = uTime - iP.x;
          h = age * iP.y * (1.0 + age * 0.4);
          alive = step(0.0, age) * step(h, rise);
        }
        float sz = iP.z * (0.7 + 0.5 * clamp(h / rise, 0.0, 1.0));
        float seed = fract(iP.x * 13.17 + iOrigin.x);
        vec3 c = iOrigin + vec3(sin(uTime * 3.1 + seed * 40.0) * 0.05 * (1.0 + h * 0.08), h, cos(uTime * 2.7 + seed * 30.0) * 0.04);
        vec3 p = position * vec3(sz, sz * 0.86, sz) * alive + c;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vN = normalize(normalMatrix * normal);
        vView = normalize(-mv.xyz);
        vA = alive * smoothstep(rise, rise - 0.5, h) * smoothstep(0.0, 0.12, h);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uRim, uCore;
      varying vec3 vN;
      varying vec3 vView;
      varying float vA;
      void main() {
        float f = pow(max(1.0 - abs(dot(normalize(vN), normalize(vView))), 0.0), 2.2);
        float spec = smoothstep(0.86, 0.97, dot(normalize(vN), normalize(vec3(-0.35, 0.65, 0.68))));
        vec3 col = uRim * (f * 1.25 + spec * 1.6) + uCore * 0.1;
        float a = (0.1 + f * 0.8 + spec * 0.8) * vA;
        gl_FragColor = vec4(col, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  mesh.renderOrder = 23;

  let streams = 0;
  let burstNext = 0;

  function setSources(sources, frame) {
    uniforms.uSurface.value = frame.surfaceY - 0.05;
    const list = sources.slice(0, 8);
    streams = list.length;
    let i = 0;
    for (const src of list) {
      for (let k = 0; k < PER_STREAM; k++, i++) {
        origin.setXYZ(i, src.x + (Math.random() - 0.5) * 0.06, src.y, src.z + (Math.random() - 0.5) * 0.06);
        params.setXYZW(i, k / PER_STREAM + Math.random() * 0.03, 0.9 + Math.random() * 0.5, 0.035 + Math.random() * 0.05, 0);
      }
    }
    for (let k = 0; k < BURSTS; k++) params.setXYZW(streams * PER_STREAM + k, -100, 1, 0.04, 1);
    burstNext = 0;
    origin.needsUpdate = true;
    params.needsUpdate = true;
    geo.instanceCount = streams * PER_STREAM + BURSTS;
  }

  function burst(x, y, z, n, time) {
    const offset = streams * PER_STREAM;
    for (let k = 0; k < n; k++) {
      const i = offset + (burstNext++ % BURSTS);
      origin.setXYZ(i, x + (Math.random() - 0.5) * 0.4, y + (Math.random() - 0.5) * 0.2, z + (Math.random() - 0.5) * 0.3);
      params.setXYZW(i, time + Math.random() * 0.25, 0.8 + Math.random() * 0.8, 0.03 + Math.random() * 0.05, 1);
    }
    origin.needsUpdate = true;
    params.needsUpdate = true;
  }

  function update(mood, pal) {
    uniforms.uRim.value.copy(mood.key).lerp(pal.ray, 0.5).multiplyScalar(0.7 + 0.3 * mood.day);
    uniforms.uCore.value.copy(mood.water);
  }

  return { mesh, setSources, burst, update };
}
