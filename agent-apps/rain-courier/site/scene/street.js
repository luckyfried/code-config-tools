// Wet streets. Desktop: a planar reflection of the city through Reflector, blurred along the view and rippled by
// the rain. Phones: the skyline rendered once into a cube map and read off a glossy plane, which still looks wet.
import * as THREE from "three";
import { Reflector } from "three/addons/objects/Reflector.js";
import { FOG_GLSL } from "./palette.js";
import { PITCH, STREET } from "../game/gen.js";

const STREET_GLSL = /* glsl */ `
uniform vec3 uStreet;
uniform vec3 uLamp;
uniform vec2 uHalf;
uniform float uTime;
float h21(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
// Raindrop rings on the puddles: one ring per cell, each on its own clock.
vec2 ripples(vec2 p) {
  vec2 n = vec2(0.0);
  for (int k = 0; k < 2; k++) {
    vec2 q = p * (k == 0 ? 0.9 : 1.7) + float(k) * 7.31;
    vec2 cell = floor(q);
    vec2 f = fract(q) - 0.5;
    float h = h21(cell);
    vec2 c = vec2(h21(cell + 3.1), h21(cell + 7.7)) - 0.5;
    vec2 d = f - c * 0.5;
    float t = fract(uTime * (0.9 + h * 0.6) + h * 10.0);
    float r = length(d);
    float ring = sin((r - t * 0.45) * 60.0) * smoothstep(0.08, 0.0, abs(r - t * 0.45)) * (1.0 - t);
    n += normalize(d + 0.0001) * ring;
  }
  return n;
}
struct StreetLook { vec3 base; float wet; vec2 bump; };
StreetLook streetLook(vec3 world) {
  vec2 g = mod(world.xz + uHalf, ${PITCH.toFixed(1)});
  vec2 toStreet = min(g, ${PITCH.toFixed(1)} - g);
  float onX = step(toStreet.x, ${(STREET / 2).toFixed(1)});
  float onZ = step(toStreet.y, ${(STREET / 2).toFixed(1)});
  float inside = step(abs(world.x), uHalf.x + 1.0) * step(abs(world.z), uHalf.y + 1.0);
  float road = max(onX, onZ);
  float crossing = onX * onZ;
  vec3 base = uStreet;
  float wear = vnoise(world.xz * 0.15);
  base *= 0.85 + 0.3 * wear;
  // Pavement inside the blocks is lighter and less wet than the road.
  base = mix(base * 1.9 + 0.012, base, road);
  float curb = road < 0.5 ? 0.0 : 1.0;
  float kerbX = smoothstep(0.25, 0.0, abs(toStreet.x - ${(STREET / 2).toFixed(1)}));
  float kerbZ = smoothstep(0.25, 0.0, abs(toStreet.y - ${(STREET / 2).toFixed(1)}));
  base += uStreet * 1.5 * max(kerbX, kerbZ) * inside;
  // Lane markings: a dashed center line, and zebra crossings at every corner.
  float dashX = onX * (1.0 - onZ) * step(toStreet.x, 0.12) * step(fract(world.z / 6.0), 0.5);
  float dashZ = onZ * (1.0 - onX) * step(toStreet.y, 0.12) * step(fract(world.x / 6.0), 0.5);
  float zebraX = onX * step(toStreet.y, ${(STREET / 2 + 3.2).toFixed(1)}) * step(${(STREET / 2 + 0.6).toFixed(1)}, toStreet.y) * step(fract(world.x / 1.1), 0.5) * step(toStreet.x, ${(STREET / 2 - 0.8).toFixed(1)});
  float zebraZ = onZ * step(toStreet.x, ${(STREET / 2 + 3.2).toFixed(1)}) * step(${(STREET / 2 + 0.6).toFixed(1)}, toStreet.x) * step(fract(world.z / 1.1), 0.5) * step(toStreet.y, ${(STREET / 2 - 0.8).toFixed(1)});
  float paint = max(max(dashX, dashZ), max(zebraX, zebraZ)) * inside * (0.6 + 0.4 * vnoise(world.xz * 3.0));
  base = mix(base, vec3(0.32) + uStreet, paint * 0.8);
  // Pools of lamplight along both kerbs.
  float alongX = mod(world.z + uHalf.y, 19.0);
  float alongZ = mod(world.x + uHalf.x, 19.0);
  float poolX = onX * exp(-pow(toStreet.x - ${(STREET / 2 - 2.6).toFixed(1)}, 2.0) * 0.12) * exp(-pow(min(alongX, 19.0 - alongX) - 0.0, 2.0) * 0.03);
  float poolZ = onZ * exp(-pow(toStreet.y - ${(STREET / 2 - 2.6).toFixed(1)}, 2.0) * 0.12) * exp(-pow(min(alongZ, 19.0 - alongZ) - 0.0, 2.0) * 0.03);
  base += uLamp * 0.10 * max(poolX, poolZ) * inside;
  float wet = mix(0.45, 0.95, road) * (0.7 + 0.3 * smoothstep(0.35, 0.7, wear));
  wet = mix(wet, 0.25, paint);
  vec2 bump = ripples(world.xz) * 0.35 + (vec2(vnoise(world.xz * 0.6), vnoise(world.zx * 0.6 + 4.0)) - 0.5) * 0.25;
  StreetLook look;
  look.base = base;
  look.wet = wet;
  look.bump = bump;
  return look;
}
`;

function streetUniforms(shared, plan) {
  return {
    ...shared,
    uStreet: { value: new THREE.Color() },
    uLamp: { value: new THREE.Color() },
    uHalf: { value: new THREE.Vector2(plan.halfX, plan.halfZ) },
  };
}

export function buildReflectiveStreet(plan, shared, width, height) {
  const size = Math.max(plan.halfX, plan.halfZ) * 2 + 1400;
  const geometry = new THREE.PlaneGeometry(size, size);
  const shader = {
    name: "WetStreetReflector",
    uniforms: {
      color: { value: null },
      tDiffuse: { value: null },
      textureMatrix: { value: null },
      ...streetUniforms(shared, plan),
    },
    vertexShader: /* glsl */ `
      uniform mat4 textureMatrix;
      varying vec4 vUv;
      varying vec3 vWorld;
      void main() {
        vUv = textureMatrix * vec4(position, 1.0);
        vec4 world = modelMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 color;
      uniform sampler2D tDiffuse;
      varying vec4 vUv;
      varying vec3 vWorld;
      ${FOG_GLSL}
      ${STREET_GLSL}
      void main() {
        StreetLook look = streetLook(vWorld);
        vec4 uv = vUv;
        uv.xy += look.bump * 0.035 * uv.w;
        // A short vertical blur: wet asphalt smears lights into streaks toward the viewer.
        vec3 refl = vec3(0.0);
        float total = 0.0;
        for (int i = -4; i <= 4; i++) {
          float w = 1.0 - abs(float(i)) / 5.0;
          refl += texture2DProj(tDiffuse, uv + vec4(0.0, float(i) * 0.006 * uv.w, 0.0, 0.0)).rgb * w;
          total += w;
        }
        refl /= total;
        vec3 view = normalize(vWorld - cameraPosition);
        float fres = mix(0.35, 1.0, pow(1.0 - abs(view.y), 4.0));
        vec3 c = look.base + refl * look.wet * fres * 0.85;
        c += uFlashColor * uFlash * 0.12;
        c = applyFog(c, vWorld, cameraPosition);
        gl_FragColor = vec4(c, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  };
  const street = new Reflector(geometry, {
    shader,
    textureWidth: Math.max(256, Math.round(width / 2)),
    textureHeight: Math.max(256, Math.round(height / 2)),
    clipBias: 0.003,
    multisample: 0,
  });
  // Reflector clones its uniforms; point the shared ones back at the shared objects so time and thunder reach it.
  for (const key of Object.keys(shared)) street.material.uniforms[key] = shared[key];
  street.rotation.x = -Math.PI / 2;
  street.name = "street";
  return {
    mesh: street,
    material: street.material,
    resize(w, h) {
      street.getRenderTarget().setSize(Math.max(256, Math.round(w / 2)), Math.max(256, Math.round(h / 2)));
    },
  };
}

export function buildCubeStreet(plan, shared, envTexture) {
  const size = Math.max(plan.halfX, plan.halfZ) * 2 + 1400;
  const geometry = new THREE.PlaneGeometry(size, size).rotateX(-Math.PI / 2);
  const material = new THREE.ShaderMaterial({
    uniforms: { ...streetUniforms(shared, plan), uEnv: { value: envTexture } },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform samplerCube uEnv;
      varying vec3 vWorld;
      ${FOG_GLSL}
      ${STREET_GLSL}
      void main() {
        StreetLook look = streetLook(vWorld);
        vec3 view = normalize(vWorld - cameraPosition);
        vec3 n = normalize(vec3(look.bump.x * 0.6, 1.0, look.bump.y * 0.6));
        vec3 r = reflect(view, n);
        r.y = max(r.y, 0.02);
        vec3 refl = textureLod(uEnv, r, 1.5).rgb;
        float fres = mix(0.35, 1.0, pow(1.0 - abs(view.y), 4.0));
        vec3 c = look.base + refl * look.wet * fres * 0.75;
        c += uFlashColor * uFlash * 0.12;
        c = applyFog(c, vWorld, cameraPosition);
        gl_FragColor = vec4(c, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = "street";
  return { mesh, material, resize() {} };
}

// The skyline rendered once into a cube map from street level: the phone street and the drone's paint read it.
export function createSkylineCapture() {
  const target = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
  const cubeCamera = new THREE.CubeCamera(1, 2000, target);
  return {
    texture: target.texture,
    capture(renderer, scene, at, hide = []) {
      hide.forEach((o) => (o.visible = false));
      cubeCamera.position.copy(at);
      cubeCamera.update(renderer, scene);
      hide.forEach((o) => (o.visible = true));
    },
  };
}

export function updateStreetPalette(material, palette) {
  material.uniforms.uStreet.value.copy(palette.street);
  material.uniforms.uLamp.value.copy(palette.lamp);
}
