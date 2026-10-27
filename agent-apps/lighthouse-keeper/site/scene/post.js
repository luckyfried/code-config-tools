// The post stack: bloom catches the lamp, the lanterns, and the burning edges; a radial blur centered on the lamp
// draws god rays when the beam faces the camera; the output pass tone maps once. The low tier renders direct.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const GodRayShader = {
  uniforms: {
    tDiffuse: { value: null },
    uLight: { value: new THREE.Vector2(0.5, 0.5) },
    uStrength: { value: 0 },
    uTint: { value: new THREE.Color(1, 1, 1) },
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
    uniform vec2 uLight;
    uniform float uStrength;
    uniform vec3 uTint;
    varying vec2 vUv;
    void main() {
      vec4 base = texture2D(tDiffuse, vUv);
      if (uStrength < 0.002) { gl_FragColor = base; return; }
      vec2 delta = (vUv - uLight) * (0.9 / 48.0);
      // Only light near the lamp feeds the rays, so a burning ship never smears into a row of copies.
      vec2 uv = vUv;
      float decay = 1.0;
      vec3 acc = vec3(0.0);
      for (int i = 0; i < 48; i++) {
        uv -= delta;
        vec3 s = texture2D(tDiffuse, uv).rgb;
        acc += max(s - 0.8, 0.0) * decay * (1.0 - smoothstep(0.03, 0.1, distance(uv, uLight)));
        decay *= 0.976;
      }
      gl_FragColor = vec4(base.rgb + acc * uTint * (uStrength / 48.0) * 2.2, base.a);
    }
  `,
};

export function createPost(renderer, scene, camera, tier, tokens) {
  if (!tier.post) {
    return {
      bloom: null,
      setSize() {},
      render() {
        renderer.render(scene, camera);
      },
      setGodRays() {},
      setBloom() {},
    };
  }
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const size = renderer.getSize(new THREE.Vector2());
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x, size.y), 0.75, 0.55, 0.9);
  composer.addPass(bloom);
  let rays = null;
  if (tier.godRays) {
    rays = new ShaderPass(GodRayShader);
    rays.uniforms.uTint.value.copy(tokens.beam);
    composer.addPass(rays);
  }
  composer.addPass(new OutputPass());
  const baseStrength = 0.75;
  return {
    bloom,
    setSize(w, h) {
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(w, h);
    },
    render() {
      composer.render();
    },
    setGodRays(x, y, strength) {
      if (!rays) return;
      rays.uniforms.uLight.value.set(x, y);
      rays.uniforms.uStrength.value = strength;
      rays.enabled = strength > 0.002;
    },
    setBloom(extra, floor) {
      bloom.strength = baseStrength + extra;
      bloom.threshold = Math.max(floor, 0.9 - extra * 0.25);
    },
  };
}
