// Marine snow: thousands of motes in a box that wraps around the camera, drifting down, brightest inside the beams.
import * as THREE from "three";
import { shared, FOG_GLSL } from "./materials.js";
import { HEADLIGHT } from "./lights.js";

export function createSnow(tokens, rng, count) {
  const box = 56;
  const pos = new Float32Array(count * 3);
  const seed = new Float32Array(count * 2);
  for (let i = 0; i < count; i++) {
    pos[i * 3] = rng.range(0, box);
    pos[i * 3 + 1] = rng.range(0, box);
    pos[i * 3 + 2] = rng.range(0, box);
    seed[i * 2] = rng.next();
    seed[i * 2 + 1] = rng.range(0.4, 1.6);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 2));
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: shared.uTime,
      uCam: { value: new THREE.Vector3() },
      uBox: { value: box },
      uColor: { value: tokens.world.snow.clone() },
      uPixel: { value: 1 },
      uLampPos: { value: [new THREE.Vector3(), new THREE.Vector3()] },
      uLampDir: { value: [new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 1)] },
      uLampOn: { value: 1 },
      uAmbient: { value: 0.3 },
      uFogDensity: shared.uFogDensity,
      uFogColor: shared.uFogColor,
    },
    vertexShader: /* glsl */ `
      attribute vec2 aSeed;
      uniform float uTime;
      uniform vec3 uCam;
      uniform float uBox;
      uniform float uPixel;
      uniform vec3 uLampPos[2];
      uniform vec3 uLampDir[2];
      uniform float uLampOn;
      varying float vLit;
      varying float vDist;
      varying float vTwinkle;
      float beam(vec3 p, vec3 o, vec3 d) {
        vec3 v = p - o;
        float along = dot(v, d);
        if (along <= 0.0) return 0.0;
        float perp = length(v - d * along);
        float cone = max(along * ${HEADLIGHT.beamTan.toFixed(3)}, 0.04);
        return exp(-(perp * perp) / (cone * cone) * 1.6) * pow(1.0 - clamp(along / ${HEADLIGHT.range.toFixed(1)}, 0.0, 1.0), 1.5);
      }
      void main() {
        vec3 drift = vec3(sin(uTime * 0.11 + aSeed.x * 40.0) * 0.6, -uTime * 0.35 * aSeed.y, cos(uTime * 0.09 + aSeed.x * 30.0) * 0.6);
        vec3 p = mod(position + drift - uCam + uBox * 0.5, uBox) - uBox * 0.5 + uCam;
        vLit = (beam(p, uLampPos[0], uLampDir[0]) + beam(p, uLampPos[1], uLampDir[1])) * uLampOn;
        vTwinkle = 0.7 + 0.3 * sin(uTime * 2.0 * aSeed.y + aSeed.x * 50.0);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vDist = -mv.z;
        gl_Position = projectionMatrix * mv;
        gl_PointSize = clamp((1.2 + aSeed.y * 1.4) * uPixel * 26.0 / max(0.5, -mv.z), 1.0, 9.0 * uPixel);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uAmbient;
      varying float vLit;
      varying float vDist;
      varying float vTwinkle;
      ${FOG_GLSL}
      void main() {
        vec2 c = gl_PointCoord - 0.5;
        float a = smoothstep(0.5, 0.1, length(c));
        float b = (uAmbient + vLit * 3.4) * vTwinkle * (1.0 - fogFactor(vDist) * 0.85);
        gl_FragColor = vec4(uColor * b * a, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geo, mat);
  points.name = "marineSnow";
  points.frustumCulled = false;
  return {
    points,
    update(camPos, lampPos, lampDir, lampOn, ambient) {
      mat.uniforms.uCam.value.copy(camPos);
      mat.uniforms.uLampPos.value[0].copy(lampPos[0]);
      mat.uniforms.uLampPos.value[1].copy(lampPos[1]);
      mat.uniforms.uLampDir.value[0].copy(lampDir[0]);
      mat.uniforms.uLampDir.value[1].copy(lampDir[1]);
      mat.uniforms.uLampOn.value = lampOn;
      mat.uniforms.uAmbient.value = ambient;
    },
    setPixelRatio(pr) {
      mat.uniforms.uPixel.value = pr;
    },
  };
}
