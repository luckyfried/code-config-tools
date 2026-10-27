// The sea: Gerstner waves moved in the vertex shader with analytic normals, lit by the moon and the beam through
// three.js lights and shadows, with a fresnel blend to the sky, foam on the crests, and a foam ring on the reef.
import * as THREE from "three";
import { GERSTNER, NOISE, WAVES } from "./glsl.js";

// The beam's own pool on the water: the spot light's diffuse share, kept apart from the moon's, so the sea scatters
// the beam into a lit patch and a ship in it lays a long shadow across that patch.
const LIGHT_CALL = "RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );";
function withBeamPool(chunk) {
  const at = chunk.indexOf(LIGHT_CALL, chunk.indexOf("NUM_SPOT_LIGHTS > 0"));
  if (at < 0) return chunk;
  const end = at + LIGHT_CALL.length;
  return `${chunk.slice(0, end)}\nseaBeamPool += directLight.color * saturate( dot( geometryNormal, directLight.direction ) );${chunk.slice(end)}`;
}

export function createSea(tokens, tier) {
  const segments = tier.seaSegments;
  const radius = 700;
  const geometry = new THREE.PlaneGeometry(2, 2, segments, segments);
  geometry.rotateX(-Math.PI / 2);
  const pos = geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const r = Math.max(Math.abs(x), Math.abs(z));
    const s = r > 0 ? Math.pow(r, 2.2) / r : 0;
    pos.setXYZ(i, x * s * radius, 0, z * s * radius);
  }
  geometry.computeBoundingSphere();

  const uniforms = {
    uTime: { value: 0 },
    uWaves: { value: WAVES.map((w) => new THREE.Vector4(...w)) },
    uRough: { value: tokens.seaRough },
    uGridStep: { value: (2.2 * radius * 2) / segments },
    uSkyHorizon: { value: tokens.skyHorizon.clone() },
    uSkyGlow: { value: tokens.skyGlow.clone() },
    uFoam: { value: tokens.seaFoam.clone() },
    uShallow: { value: tokens.seaShallow.clone() },
    uFlare: { value: 0 },
    uFlash: { value: 0 },
  };

  const material = new THREE.MeshPhongMaterial({
    color: tokens.seaDeep,
    specular: tokens.seaSpec.clone().multiplyScalar(0.75),
    shininess: tier.godRays ? 140 : 70,
  });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uTime;
        varying vec3 vSeaWorld;
        varying float vCrest;
        ${GERSTNER}`,
      )
      .replace(
        "#include <beginnormal_vertex>",
        `vec3 seaNormal;
        float seaCrest;
        vec3 seaOffset = gerstner(position.xz, uTime, seaNormal, seaCrest);
        vec3 objectNormal = seaNormal;
        vCrest = seaCrest;`,
      )
      .replace(
        "#include <begin_vertex>",
        `vec3 transformed = position + seaOffset;
        vSeaWorld = transformed;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform vec3 uSkyHorizon, uSkyGlow, uFoam, uShallow;
        uniform float uTime, uFlare, uFlash;
        vec3 seaBeamPool = vec3(0.0);
        varying vec3 vSeaWorld;
        varying float vCrest;
        ${NOISE}`,
      )
      .replace(
        "#include <normal_fragment_maps>",
        `#include <normal_fragment_maps>
        {
          const mat2 rotA = mat2(0.8, -0.6, 0.6, 0.8);
          const mat2 rotB = mat2(0.34, 0.94, -0.94, 0.34);
          vec2 rp = vSeaWorld.xz * 0.55;
          float rt = uTime * 0.6;
          float r0 = lkNoise(vec3(rotA * rp, rt)) + 0.5 * lkNoise(vec3(rotB * rp * 2.3, rt * 1.4));
          float rx = lkNoise(vec3(rotA * (rp + vec2(0.35, 0.0)), rt)) + 0.5 * lkNoise(vec3(rotB * (rp + vec2(0.35, 0.0)) * 2.3, rt * 1.4));
          float rz = lkNoise(vec3(rotA * (rp + vec2(0.0, 0.35)), rt)) + 0.5 * lkNoise(vec3(rotB * (rp + vec2(0.0, 0.35)) * 2.3, rt * 1.4));
          float rippleFade = 1.0 - smoothstep(50.0, 240.0, length(vViewPosition));
          vec3 ripple = vec3(r0 - rx, 0.0, r0 - rz) * 0.75 * rippleFade;
          normal = normalize(normal + (viewMatrix * vec4(ripple, 0.0)).xyz);
        }`,
      )
      .replace("#include <lights_fragment_begin>", withBeamPool(THREE.ShaderChunk.lights_fragment_begin))
      .replace(
        "#include <opaque_fragment>",
        `float fres = pow(1.0 - clamp(dot(normal, geometryViewDir), 0.0, 1.0), 4.0);
        float lift = smoothstep(-0.2, 1.0, vCrest);
        outgoingLight += uShallow * lift * 0.18;
        outgoingLight = mix(outgoingLight, uSkyHorizon * 0.55 + uSkyGlow * 0.15, fres * 0.75);
        outgoingLight += seaBeamPool * 1.8 * (1.0 - fres * 0.5);
        float r = length(vSeaWorld.xz);
        float foamNoise = lkNoise(vec3(vSeaWorld.xz * 0.35, uTime * 0.35));
        float reef = (1.0 - smoothstep(5.5, 16.0 + foamNoise * 5.0, r)) * smoothstep(0.35, 0.75, foamNoise + 0.25);
        // Crest foam breaks into streaks, so a swell's top never reads as one smooth oval.
        float streak = lkNoise(vec3(vSeaWorld.xz * vec2(0.9, 2.4), uTime * 0.5)) * 0.6 + lkNoise(vec3(vSeaWorld.xz * 2.7, uTime * 0.8)) * 0.4;
        float crest = smoothstep(0.6, 1.05, vCrest + foamNoise * 0.3) * smoothstep(0.38, 0.78, streak);
        float foam = max(reef * 0.9, crest * 0.4);
        outgoingLight = mix(outgoingLight, uFoam * (0.25 + 0.75 * (reflectedLight.directDiffuse + reflectedLight.indirectDiffuse) * 6.0 + uFlare), foam * 0.7);
        outgoingLight += uSkyGlow * uFlare * (0.2 + 0.6 * fres);
        outgoingLight += vec3(0.75, 0.8, 0.9) * uFlash * (0.15 + fres * 0.6);
        #include <opaque_fragment>`,
      );
  };
  material.customProgramCacheKey = () => "lk-sea";

  const mesh = new THREE.Mesh(geometry, material);
  mesh.receiveShadow = tier.shadow > 0;
  mesh.frustumCulled = false;
  return {
    mesh,
    uniforms,
    update(time) {
      uniforms.uTime.value = time;
    },
  };
}
