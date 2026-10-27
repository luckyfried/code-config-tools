// The post stack on the high tier: the scene, a soft bloom for the sun and the lit strips, a radial blur that
// fades in above 80% of top speed, and the output pass (tone mapping and color space).
import { HalfFloatType, Vector2, WebGLRenderTarget } from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

const RadialBlurShader = {
  name: "RadialBlurShader",
  uniforms: {
    tDiffuse: { value: null },
    center: { value: new Vector2(0.5, 0.48) },
    strength: { value: 0 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform vec2 center;
    uniform float strength;
    varying vec2 vUv;
    void main() {
      vec2 dir = vUv - center;
      float edge = smoothstep(0.12, 0.7, length(dir));
      vec2 stepUv = dir * strength * edge / 10.0;
      vec4 sum = vec4(0.0);
      float total = 0.0;
      for (int i = 0; i < 10; i++) {
        float w = 1.0 - float(i) / 12.0;
        sum += texture2D(tDiffuse, vUv - stepUv * float(i)) * w;
        total += w;
      }
      gl_FragColor = sum / total;
    }
  `,
};

export function createPost(renderer, scene, camera, tier, glowStrength) {
  if (!tier.post) return null;
  const size = renderer.getDrawingBufferSize(new Vector2());
  const target = new WebGLRenderTarget(size.x, size.y, { type: HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new Vector2(size.x / 2, size.y / 2), 0.22 + glowStrength * 0.1, 0.45, 1.05);
  composer.addPass(bloom);
  const radial = new ShaderPass(RadialBlurShader);
  radial.enabled = false;
  if (tier.radialBlur) composer.addPass(radial);
  composer.addPass(new OutputPass());
  return {
    composer,
    bloom,
    setSize(w, h, ratio) {
      composer.setPixelRatio(ratio);
      composer.setSize(w, h);
    },
    setGlow(g) {
      bloom.strength = 0.22 + g * 0.1;
    },
    // amount: 0 to 1, the share of the last 20% of top speed the marble is using.
    setSpeed(amount) {
      radial.uniforms.strength.value = amount * 0.06;
      radial.enabled = tier.radialBlur && amount > 0.02;
    },
    // Centers the blur on the marble's place on screen (0 to 1), so the marble itself stays sharp.
    setCenter(x, y) {
      radial.uniforms.center.value.set(x, y);
    },
    render() {
      composer.render();
    },
  };
}
