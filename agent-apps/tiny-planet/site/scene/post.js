// Bloom on the crystals, the beams, the sun, and the atmosphere at dusk. The composer is made only when the tier asks for it.
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
    const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 0 });
    composer = new EffectComposer(renderer, target);
    composer.addPass(new RenderPass(scene, camera));
    bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.85, 0.5, 1.5);
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
    // The blur's reach is counted in its own pixels, so a smaller bloom buffer reaches further across the screen;
    // its radius and strength shrink with it, and the sun's glow covers the same part of a phone as of a desktop.
    const reach = Math.min(1, w / 1600);
    bloom.radius = 0.5 * reach;
    bloom.strength = 0.85 * (0.6 + 0.4 * reach);
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
