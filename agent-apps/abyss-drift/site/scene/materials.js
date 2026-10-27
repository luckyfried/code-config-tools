// Shared looks. `shared` holds the uniforms every injected shader reads, so one write a frame reaches all of them.
// `underwater(material, opts)` adds the world-space caustics (a scrolling sum of sines that fades with depth) and,
// where the geometry carries an aLichen attribute, glowing lichen, to a stock MeshStandardMaterial.
import * as THREE from "three";

export const shared = {
  uTime: { value: 0 },
  uCausticStrength: { value: 1 },
  uCausticColor: { value: new THREE.Color(1, 1, 1) },
  uLichenStrength: { value: 1 },
  uFogDensity: { value: 0.02 },
  uFogColor: { value: new THREE.Color(0, 0, 0) },
  uSurfaceSky: { value: new THREE.Color(1, 1, 1) },
  uSurfaceFade: { value: 1 },
  uRimColor: { value: new THREE.Color(0, 0, 0) },
};

/**
 * What the underside of the surface shows along a ray from the camera: Snell's window overhead, and beyond it water the
 * color of the fog, so the far surface and the top of the trench walls melt into the same water with no seam.
 */
export const SURFACE_GLSL = /* glsl */ `
uniform vec3 uSurfaceSky;
uniform float uSurfaceFade;
uniform vec3 uSurfaceWater;
vec3 surfaceSeen(vec3 toFrag, float ripple) {
  float cosA = toFrag.y / max(length(toFrag), 1e-4);
  float window = smoothstep(0.5, 0.8, cosA);
  vec3 sky = uSurfaceSky * (1.25 + ripple * 0.9);
  vec3 mirror = uSurfaceWater * (0.97 + ripple * 0.18);
  return mix(uSurfaceWater, mix(mirror, sky, window), uSurfaceFade);
}
`;

export const CAUSTIC_GLSL = /* glsl */ `
float uwHash(vec3 p) {
  p = fract(p * 0.3183099 + 0.1);
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float uwNoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(uwHash(i), uwHash(i + vec3(1, 0, 0)), f.x), mix(uwHash(i + vec3(0, 1, 0)), uwHash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(uwHash(i + vec3(0, 0, 1)), uwHash(i + vec3(1, 0, 1)), f.x), mix(uwHash(i + vec3(0, 1, 1)), uwHash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
float causticAt(vec3 wp, float t) {
  vec2 p = wp.xz * 0.21 + vec2(wp.y * 0.04, -wp.y * 0.03);
  float a = sin(p.x * 2.1 + t * 0.9 + sin(p.y * 1.7 + t * 0.7) * 1.3)
          + sin(p.y * 2.3 - t * 0.8 + sin(p.x * 1.5 - t * 0.6) * 1.2)
          + sin((p.x + p.y) * 1.6 + t * 1.1);
  float b = sin(p.x * 3.7 - t * 1.3 + sin(p.y * 2.9 + t)) + sin(p.y * 3.3 + t * 1.2 + sin(p.x * 2.6 - t * 0.9));
  return pow(1.0 - abs(a) / 3.0, 9.0) + 0.6 * pow(1.0 - abs(b) / 2.0, 12.0);
}
`;

/**
 * Adds caustics and lichen to a MeshStandardMaterial.
 * opts.caustics: whether the tier draws caustics. opts.lichen: a THREE.Color for the aLichen attribute's glow.
 * opts.key: a name for the program cache. opts.vertex: extra GLSL run after begin_vertex (may move `transformed`).
 * opts.normal: GLSL run after beginnormal_vertex (may set `objectNormal`). opts.color: GLSL run after color_fragment
 * (may set `diffuseColor` or discard). opts.surface: fade the top meters into the surface's look. opts.rim: an edge glow in shared.uRimColor. opts.vertexHead / opts.fragmentHead / opts.uniforms: what that GLSL needs.
 */
export function underwater(material, opts = {}) {
  const {
    caustics = true, lichen = null, key = "plain", vertex = "", vertexHead = "", normal = "", fragmentHead = "", color = "",
    uniforms = {}, surface = false, rim = false,
  } = opts;
  const lichenUniform = { value: lichen ? lichen.clone() : new THREE.Color(0, 0, 0) };
  material.userData.lichenColor = lichenUniform;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = shared.uTime;
    shader.uniforms.uCausticStrength = shared.uCausticStrength;
    shader.uniforms.uCausticColor = shared.uCausticColor;
    shader.uniforms.uLichenStrength = shared.uLichenStrength;
    shader.uniforms.uLichenColor = lichenUniform;
    Object.assign(shader.uniforms, uniforms);
    if (rim) shader.uniforms.uRimColor = shared.uRimColor;
    if (surface) {
      shader.uniforms.uSurfaceSky = shared.uSurfaceSky;
      shader.uniforms.uSurfaceFade = shared.uSurfaceFade;
      shader.uniforms.uSurfaceWater = shared.uFogColor;
    }
    material.userData.shader = shader;
    shader.vertexShader =
      `uniform float uTime;\nvarying vec3 vWorldPos;\nvarying vec3 vWorldN;\n${lichen ? "attribute float aLichen;\nvarying float vLichen;\n" : ""}${vertexHead}\n` +
      shader.vertexShader
        .replace("#include <beginnormal_vertex>", `#include <beginnormal_vertex>\n${normal}`)
        .replace("#include <begin_vertex>", `#include <begin_vertex>\n${vertex}\n${lichen ? "vLichen = aLichen;" : ""}`)
        .replace(
          "#include <project_vertex>",
          `#include <project_vertex>
          vec4 uwWorld = vec4(transformed, 1.0);
          #ifdef USE_INSTANCING
            uwWorld = instanceMatrix * uwWorld;
          #endif
          uwWorld = modelMatrix * uwWorld;
          vWorldPos = uwWorld.xyz;
          vWorldN = normalize(mat3(modelMatrix) * objectNormal);`,
        );
    shader.fragmentShader =
      `uniform float uTime;\nuniform float uCausticStrength;\nuniform vec3 uCausticColor;\nuniform float uLichenStrength;\nuniform vec3 uLichenColor;\nvarying vec3 vWorldPos;\nvarying vec3 vWorldN;\n${lichen ? "varying float vLichen;\n" : ""}${fragmentHead}\n${CAUSTIC_GLSL}\n${surface ? SURFACE_GLSL : ""}\n${rim ? "uniform vec3 uRimColor;\n" : ""}` +
      shader.fragmentShader
        .replace("#include <color_fragment>", `#include <color_fragment>\n${color}`)
        .replace(
          "#include <emissivemap_fragment>",
          `#include <emissivemap_fragment>
          ${rim ? `float uwEdge = 1.0 - abs(dot(normal, normalize(vViewPosition)));
          totalEmissiveRadiance += uRimColor * pow(uwEdge, 3.0);` : ""}
          ${lichen ? `float lichenPulse = 0.65 + 0.35 * sin(uTime * 0.9 + vWorldPos.y * 0.21 + vWorldPos.x * 0.17);
          // The vertex weight says where lichen grows; low-frequency noise gathers it into colonies, and each colony is
          // a scatter of soft round points of light. A point never shrinks below about a pixel: far away it widens and
          // dims by the same area, so distant colonies melt into a soft glow instead of flickering specks.
          const mat3 uwRot = mat3(0.00, 0.80, 0.60, -0.80, 0.36, -0.48, -0.60, -0.48, 0.64);
          vec3 lp = uwRot * vWorldPos;
          float colony = uwNoise(lp * 0.42) * 0.6 + uwNoise(uwRot * lp * 1.15 + 5.0) * 0.4;
          float grow = smoothstep(0.42, 0.66, colony) * min(vLichen * 1.4, 1.2);
          float lichenDots = 0.0;
          if (grow > 0.001) {
            vec3 q = lp / 0.75;
            float r = max(0.16, length(fwidth(q)) * 1.1);
            vec3 cell = floor(q - 0.5);
            for (int i = 0; i < 8; i++) {
              vec3 c = cell + vec3(mod(float(i), 2.0), mod(floor(float(i) / 2.0), 2.0), floor(float(i) / 4.0));
              float h = uwHash(c + 0.37);
              vec3 dd = q - (c + 0.25 + 0.5 * vec3(uwHash(c + 3.1), uwHash(c + 7.7), uwHash(c + 12.9)));
              lichenDots += exp(-dot(dd, dd) / (r * r)) * step(0.3, h) * (0.4 + h);
            }
            lichenDots *= 0.0256 / (r * r);
          }
          totalEmissiveRadiance += uLichenColor * (lichenDots * 1.5 + 0.05) * grow * lichenPulse * uLichenStrength;` : ""}`,
        )
        .replace(
          "#include <opaque_fragment>",
          `${caustics ? `float uwDepth = max(-vWorldPos.y, 0.0);
          float uwFade = exp(-uwDepth / 32.0) * uCausticStrength;
          if (uwFade > 0.002) {
            float uwFacing = 0.3 + 0.7 * clamp(vWorldN.y * 0.6 + 0.5, 0.0, 1.0);
            outgoingLight += diffuseColor.rgb * uCausticColor * causticAt(vWorldPos, uTime) * uwFade * uwFacing * 2.2;
          }` : ""}
          #include <opaque_fragment>`,
        )
        .replace(
          "#include <fog_fragment>",
          `#include <fog_fragment>
          ${surface ? `// The last meters below the surface fade into what the surface itself shows there.
          float uwRim = smoothstep(-24.0, -1.0, vWorldPos.y);
          if (uwRim > 0.0) gl_FragColor.rgb = mix(gl_FragColor.rgb, surfaceSeen(vWorldPos - cameraPosition, 0.0), uwRim);` : ""}`,
        );
  };
  material.customProgramCacheKey = () => `underwater:${key}:${caustics ? 1 : 0}:${lichen ? 1 : 0}:${surface ? 1 : 0}:${rim ? 1 : 0}`;
  return material;
}

/** Exponential-squared fog for hand-written shaders, matching the scene's FogExp2. */
export const FOG_GLSL = /* glsl */ `
uniform float uFogDensity;
uniform vec3 uFogColor;
float fogFactor(float dist) {
  float f = uFogDensity * dist;
  return 1.0 - exp(-f * f);
}
`;
