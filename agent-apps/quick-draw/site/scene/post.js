// The post stack, built by tier: render, depth of field during the wait (desktop), bloom on the sun and the
// muzzle flash, then one last pass for heat shimmer near the horizon, vignette, grain, and the output transform
// (tone mapping and color space), straight to the screen.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";

const ShimmerShader = {
  name: "ShimmerGradeShader",
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uHorizon: { value: new THREE.Vector2(0.5, 0.5) },
    uStrength: { value: 1 },
    uResolution: { value: new THREE.Vector2(1, 1) },
    uVignette: { value: 0.9 },
    uGrain: { value: 0.018 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform vec2 uHorizon;
    uniform float uStrength;
    uniform vec2 uResolution;
    uniform float uVignette;
    uniform float uGrain;
    varying vec2 vUv;
    float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    float noise(vec2 p) {
      vec2 i = floor(p); vec2 f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
    }
    void main() {
      vec2 uv = vUv;
      // a thin band just above the horizon at the far end of the street, gone a few percent of the screen up
      // and off to the sides, so the porches and posts nearer the camera stay straight
      float aspect = uResolution.x / max(1.0, uResolution.y);
      float above = uv.y - uHorizon.y;
      float band = smoothstep(-0.004, 0.004, above) * (1.0 - smoothstep(0.006, 0.03, above));
      band *= 1.0 - smoothstep(0.07, 0.17, abs(uv.x - uHorizon.x) * aspect);
      float n1 = noise(vec2(uv.x * 34.0 * aspect, uv.y * 140.0 - uTime * 2.4));
      float n2 = noise(vec2(uv.x * 66.0 * aspect + 7.0, uv.y * 240.0 - uTime * 3.9));
      vec2 off = vec2((n1 - 0.5) * 0.0018, (n2 - 0.5) * 0.004) * uStrength * band;
      vec3 col = texture2D(tDiffuse, uv + off).rgb;
      vec2 q = uv - 0.5;
      q.x *= mix(1.0, aspect, 0.35);
      col *= clamp(1.0 - dot(q, q) * uVignette, 0.0, 1.0);
      col += (hash(uv * uResolution + fract(uTime * 7.13)) - 0.5) * uGrain;
      gl_FragColor = vec4(max(col, 0.0), 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }
  `,
};

export function createPost(renderer, scene, camera, tier, tokens) {
  if (!tier.post) return null;
  const size = renderer.getSize(new THREE.Vector2());
  // multisampled targets: the canvas's own antialiasing never reaches a frame drawn through the post stack
  const target = new THREE.WebGLRenderTarget(size.x * renderer.getPixelRatio(), size.y * renderer.getPixelRatio(), {
    type: THREE.HalfFloatType,
    samples: tier.samples || 0,
  });
  const composer = new EffectComposer(renderer, target);
  composer.setPixelRatio(renderer.getPixelRatio());
  composer.setSize(size.x, size.y);

  const render = new RenderPass(scene, camera);
  composer.addPass(render);

  let bokeh = null;
  if (tier.dof) {
    bokeh = new BokehPass(scene, camera, { focus: 9, aperture: 0.00018, maxblur: 0.0065 });
    bokeh.enabled = false;
    composer.addPass(bokeh);
  }

  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x * 0.5, size.y * 0.5), tokens.bloom, 0.55, 0.92);
  bloom.enabled = tier.bloom;
  composer.addPass(bloom);

  const grade = new ShaderPass(ShimmerShader);
  grade.uniforms.uStrength.value = tokens.shimmer;
  composer.addPass(grade);

  return {
    composer,
    bokeh,
    bloom,
    grade,
    setSize(w, h) {
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(w, h);
      grade.uniforms.uResolution.value.set(w * renderer.getPixelRatio(), h * renderer.getPixelRatio());
    },
    apply(t) {
      bloom.strength = t.bloom;
      grade.uniforms.uStrength.value = t.shimmer;
    },
  };
}
