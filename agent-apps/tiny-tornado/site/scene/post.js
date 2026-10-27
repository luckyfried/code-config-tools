// Bloom on the lightning, the sparks, and lit windows at night: a half-float target with multisampling, a bloom pass
// that only catches what is brighter than white, and the output pass for tone mapping. Off on the low tier.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

export function createPost(renderer, scene, camera) {
  let composer = null;
  let bloom = null;
  let scale = 1;

  function build() {
    const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
    composer = new EffectComposer(renderer, target);
    composer.addPass(new RenderPass(scene, camera));
    bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.7, 0.4, 1.0);
    composer.addPass(bloom);
    composer.addPass(new OutputPass());
  }

  function size() {
    if (!composer) return;
    composer.setPixelRatio(renderer.getPixelRatio());
    composer.setSize(window.innerWidth, window.innerHeight);
    const w = Math.max(1, Math.round(window.innerWidth * renderer.getPixelRatio() * scale));
    const h = Math.max(1, Math.round(window.innerHeight * renderer.getPixelRatio() * scale));
    bloom.setSize(w, h);
  }

  return {
    get enabled() {
      return composer !== null;
    },
    set(on, bloomScale) {
      scale = bloomScale;
      if (on && !composer) build();
      if (!on && composer) {
        composer.dispose();
        composer = null;
        bloom = null;
      }
      size();
    },
    resize: size,
    render() {
      if (composer) composer.render();
      else renderer.render(scene, camera);
    },
  };
}
