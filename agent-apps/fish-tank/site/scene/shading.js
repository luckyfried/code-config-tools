// Shared light for every material in the tank: the clock, the caustic pattern thrown down from the surface, and the
// sway that moves soft plants. One uniform object per value, shared by every program, so one write moves them all.
import * as THREE from "three";

export const shared = {
  uTime: { value: 0 },
  uCausticTime: { value: 0 },
  uCaustic: { value: 1 },
  uCausticColor: { value: new THREE.Color(1, 1, 1) },
  uSurfaceY: { value: 8 },
  uSway: { value: 1 },
  uNight: { value: 0 },
};

// Four moving sine fields at non-integer ratios, warped by a fifth, sharpened into the bright web a rippled surface
// focuses onto the floor. Two of these at different scales and speeds never line up into a repeating tile.
export const causticGLSL = /* glsl */ `
float causticLayer(vec2 p, float t) {
  vec2 q = p + 0.42 * vec2(sin(p.y * 1.37 + t * 0.61), sin(p.x * 1.13 - t * 0.53));
  float f = sin(dot(q, vec2(1.0, 0.31)) * 2.13 + t * 0.91);
  f += sin(dot(q, vec2(-0.47, 1.0)) * 1.71 - t * 0.73);
  f += sin(dot(q, vec2(0.83, -0.69)) * 2.57 + t * 1.19);
  f += sin(dot(q, vec2(-0.29, -1.0)) * 3.11 - t * 0.67);
  float c = 1.0 - abs(f * 0.25);
  return pow(max(c, 0.0), 9.0);
}
float caustics(vec3 wp, float t) {
  vec2 p = wp.xz * 0.9 + wp.y * vec2(0.13, 0.07);
  float a = causticLayer(p, t);
  float b = causticLayer(p * 1.63 + vec2(3.1, 7.7), t * 1.27 + 4.0);
  return a * 0.75 + b * 0.55 + a * b * 1.6;
}
`;

const causticVertexHead = /* glsl */ `
varying vec3 vCWorld;
`;
const causticVertexBody = /* glsl */ `
  {
    vec4 cw = vec4(transformed, 1.0);
    #ifdef USE_INSTANCING
      cw = instanceMatrix * cw;
    #endif
    vCWorld = (modelMatrix * cw).xyz;
  }
`;
const causticFragmentHead = /* glsl */ `
uniform float uCausticTime;
uniform float uCaustic;
uniform vec3 uCausticColor;
uniform float uSurfaceY;
varying vec3 vCWorld;
${causticGLSL}
`;
const causticFragmentBody = /* glsl */ `
  {
    vec3 wn = inverseTransformDirection(normal, viewMatrix);
    float up = clamp(wn.y * 0.8 + 0.35, 0.0, 1.0);
    float depthFade = 0.55 + 0.45 * clamp(vCWorld.y / max(uSurfaceY, 1.0), 0.0, 1.0);
    float c = caustics(vCWorld, uCausticTime);
    outgoingLight += diffuseColor.rgb * uCausticColor * (c * uCaustic * up * depthFade * CAUSTIC_GAIN);
  }
`;

const swayVertexHead = /* glsl */ `
uniform float uTime;
uniform float uSway;
attribute float aBend;
`;
// aBend is 0 at a plant's root and 1 at its tip; the offset grows with the square so the root stays put.
const swayVertexBody = /* glsl */ `
  {
    vec4 basePos = vec4(0.0, 0.0, 0.0, 1.0);
    #ifdef USE_INSTANCING
      basePos = instanceMatrix * basePos;
    #endif
    basePos = modelMatrix * basePos;
    float k = aBend * aBend * SWAY_GAIN * uSway;
    float ph = uTime * 0.9 + basePos.x * 0.55 + basePos.z * 0.35;
    vec3 off = vec3(k * (sin(ph) * 0.8 + sin(ph * 2.3 + 1.3) * 0.25), 0.0, k * 0.45 * sin(ph * 0.7 + 2.1));
    mat3 toWorld = mat3(modelMatrix);
    #ifdef USE_INSTANCING
      toWorld = toWorld * mat3(instanceMatrix);
    #endif
    transformed += inverse(toWorld) * off;
  }
`;

// Adds caustic light (and, with sway, the wind in the water) to a MeshStandardMaterial.
export function patchMaterial(material, { caustic = 1, sway = 0, key = "" } = {}) {
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, shared);
    shader.defines = { ...(shader.defines || {}), CAUSTIC_GAIN: caustic.toFixed(3) };
    let vs = shader.vertexShader.replace("#include <common>", `#include <common>\n${causticVertexHead}${sway ? swayVertexHead : ""}`);
    if (sway) {
      shader.defines.SWAY_GAIN = sway.toFixed(3);
      vs = vs.replace("#include <begin_vertex>", `#include <begin_vertex>\n${swayVertexBody}`);
    }
    vs = vs.replace("#include <project_vertex>", `${causticVertexBody}\n#include <project_vertex>`);
    shader.vertexShader = vs;
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${causticFragmentHead}`)
      .replace("#include <opaque_fragment>", `${causticFragmentBody}\n#include <opaque_fragment>`);
  };
  material.customProgramCacheKey = () => `caustic-${caustic}-${sway}-${key}`;
  return material;
}

export { causticVertexHead, causticVertexBody, causticFragmentHead, causticFragmentBody };
