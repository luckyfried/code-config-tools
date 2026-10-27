// The beam: an additive cone that fades with distance and frays at a noise-animated edge, a SpotLight with a shadow
// map so a lit ship throws its shadow across the water, and a Lensflare on the lamp that flares when the beam faces
// the camera.
import * as THREE from "three";
import { Lensflare, LensflareElement } from "three/addons/objects/Lensflare.js";
import { NOISE } from "./glsl.js";
import { softSprite } from "./geometry.js";

export const BEAM_LENGTH = 150;
export const BEAM_HALF_ANGLE = THREE.MathUtils.degToRad(6.5);

// The cone's brightness at a pixel comes from how close the view ray passes to the beam's axis, against the cone's
// radius there, and how long the ray runs inside it, so the beam reads as a lit volume from any side.
function coneMaterial(color, strength, widthScale, axis) {
  return new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: color },
      uStrength: { value: strength },
      uTime: { value: 0 },
      uWidth: { value: widthScale },
      uFog: { value: 0.01 },
      uLampPos: axis.origin,
      uDir: axis.dir,
    },
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    fog: false,
    vertexShader: /* glsl */ `
      varying float vAlong;
      varying vec3 vWorld;
      varying vec3 vNormalW;
      uniform float uLength;
      void main() {
        vAlong = position.z / ${BEAM_LENGTH.toFixed(1)};
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        vNormalW = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * w;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uStrength, uTime, uWidth, uFog;
      uniform vec3 uLampPos, uDir;
      varying float vAlong;
      varying vec3 vWorld;
      varying vec3 vNormalW;
      ${NOISE}
      void main() {
        vec3 rd = normalize(vWorld - cameraPosition);
        vec3 perp = cross(rd, uDir);
        float nl = length(perp);
        float d = nl > 1e-4 ? abs(dot(uLampPos - cameraPosition, perp)) / nl : length(cross(cameraPosition - uLampPos, uDir));
        float bd = dot(rd, uDir);
        vec3 w0 = cameraPosition - uLampPos;
        float tAxis = (dot(uDir, w0) - bd * dot(rd, w0)) / max(1e-4, 1.0 - bd * bd);
        float near = nl > 1e-4 ? clamp(tAxis / ${BEAM_LENGTH.toFixed(1)}, 0.0, 1.0) : vAlong;
        float r = (0.75 + near * ${(BEAM_LENGTH * Math.tan(BEAM_HALF_ANGLE)).toFixed(3)}) * uWidth;
        float q = clamp(d / r, 0.0, 1.0);
        float body = (1.0 - q * q) * (1.0 - q);
        float run = min(3.0, 1.0 / max(0.33, nl));
        body *= run * 0.5;
        float fall = pow(1.0 - vAlong, 1.2) * exp(-vAlong * 0.8);
        float start = smoothstep(0.0, 0.035, vAlong);
        float n = lkFbm(vec3(vWorld.x * 0.07 - uTime * 0.35, vWorld.y * 0.12, vWorld.z * 0.07 + uTime * 0.2));
        float fray = mix(0.45, 1.25, n);
        float water = smoothstep(-0.5, 6.0, vWorld.y);
        float dist = length(cameraPosition - vWorld);
        float haze = mix(1.0, exp(-dist * uFog * 0.9), 0.55);
        float a = body * fall * start * fray * water * haze * uStrength;
        gl_FragColor = vec4(uColor * a, 1.0);
      }
    `,
  });
}

export function createBeam(tokens, tier, lampPosition) {
  const group = new THREE.Group();
  group.position.copy(lampPosition);

  const radius = BEAM_LENGTH * Math.tan(BEAM_HALF_ANGLE);
  const shell = new THREE.CylinderGeometry(0.75, radius, BEAM_LENGTH, 56, 24, true);
  shell.translate(0, -BEAM_LENGTH / 2, 0);
  shell.rotateX(-Math.PI / 2);
  const core = new THREE.CylinderGeometry(0.35, radius * 0.42, BEAM_LENGTH, 40, 16, true);
  core.translate(0, -BEAM_LENGTH / 2, 0);
  core.rotateX(-Math.PI / 2);

  const beamColor = tokens.beam.clone();
  const dir = new THREE.Vector3(0, 0, -1);
  const axis = { origin: { value: lampPosition.clone() }, dir: { value: dir } };
  const outer = coneMaterial(beamColor, 0.85 * tokens.beamPower, 1, axis);
  const inner = coneMaterial(beamColor, 0.8 * tokens.beamPower, 0.42, axis);
  const cone = new THREE.Group();
  const shellMesh = new THREE.Mesh(shell, outer);
  const coreMesh = new THREE.Mesh(core, inner);
  shellMesh.frustumCulled = false;
  coreMesh.frustumCulled = false;
  shellMesh.renderOrder = 5;
  coreMesh.renderOrder = 6;
  cone.add(shellMesh, coreMesh);
  group.add(cone);

  const spot = new THREE.SpotLight(beamColor, 9 * tokens.beamPower, 220, BEAM_HALF_ANGLE * 1.55, 0.55, 0.35);
  spot.position.set(0, 0, 0);
  group.add(spot);
  group.add(spot.target);
  if (tier.shadow > 0) {
    spot.castShadow = true;
    spot.shadow.mapSize.set(tier.shadow, tier.shadow);
    spot.shadow.camera.near = 2;
    spot.shadow.camera.far = 220;
    spot.shadow.bias = -0.0004;
    spot.shadow.normalBias = 0.04;
  }

  const glowTex = softSprite(256, 0.05);
  const ringTex = softSprite(128, 0.0);
  const flare = new Lensflare();
  const lampColor = tokens.lamp.clone();
  const elements = [
    new LensflareElement(glowTex, 360, 0, lampColor.clone()),
    new LensflareElement(glowTex, 120, 0, lampColor.clone()),
    new LensflareElement(ringTex, 70, 0.45, beamColor.clone().multiplyScalar(0.35)),
    new LensflareElement(ringTex, 110, 0.75, beamColor.clone().multiplyScalar(0.25)),
    new LensflareElement(ringTex, 50, 1.05, beamColor.clone().multiplyScalar(0.3)),
  ];
  const base = elements.map((e) => e.color.clone());
  for (const e of elements) flare.addElement(e);
  flare.position.copy(lampPosition);

  const toCamera = new THREE.Vector3();
  const state = { bearing: 0, pitch: -0.12, facing: 0, power: 1 };

  return {
    group,
    flare,
    spot,
    direction: dir,
    state,
    setFog(density) {
      outer.uniforms.uFog.value = density;
      inner.uniforms.uFog.value = density;
    },
    update(time, camera, bearing, pitch, power) {
      state.bearing = bearing;
      state.pitch = pitch;
      state.power = power;
      const cp = Math.cos(pitch);
      dir.set(Math.sin(bearing) * cp, Math.sin(pitch), -Math.cos(bearing) * cp);
      cone.lookAt(lampPosition.x + dir.x, lampPosition.y + dir.y, lampPosition.z + dir.z);
      spot.target.position.copy(dir).multiplyScalar(60);
      spot.intensity = 9 * tokens.beamPower * power;
      outer.uniforms.uTime.value = time;
      inner.uniforms.uTime.value = time;
      outer.uniforms.uStrength.value = 0.85 * tokens.beamPower * power;
      inner.uniforms.uStrength.value = 0.8 * tokens.beamPower * power;
      toCamera.subVectors(camera.position, lampPosition).normalize();
      state.facing = Math.max(0, dir.dot(toCamera));
      const f = Math.pow(state.facing, 3);
      const glow = 0.35 + f * 1.4;
      elements[0].color.copy(base[0]).multiplyScalar(0.25 + f * 1.1);
      elements[1].color.copy(base[1]).multiplyScalar(glow);
      for (let i = 2; i < elements.length; i++) elements[i].color.copy(base[i]).multiplyScalar(f * 1.6);
    },
  };
}
