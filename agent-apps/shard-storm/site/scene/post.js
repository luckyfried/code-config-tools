// The post stack: the render, UnrealBloom (half resolution on the mid tier), an RGB shift that pulses for 80 ms on a
// graze, and the output pass. Glow themes bloom from threshold 0.6; day themes bloom only what burns past white, the
// shards' cores, so the pale field stays clean. The low tier draws straight to the screen unless the shift is pulsing.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { RGBShiftShader } from "three/addons/shaders/RGBShiftShader.js";

export function createPost(renderer, scene, camera) {
  const composer = new EffectComposer(renderer);
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.8, 0.45, 0.6);
  const shift = new ShaderPass(RGBShiftShader);
  shift.uniforms.amount.value = 0;
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(bloom);
  composer.addPass(shift);
  composer.addPass(new OutputPass());
  let bloomScale = 1;
  let width = 1;
  let height = 1;
  const baseSetSize = bloom.setSize.bind(bloom);
  bloom.setSize = (w, h) => baseSetSize(Math.max(1, Math.round(w * bloomScale)), Math.max(1, Math.round(h * bloomScale)));

  return {
    bloom,
    shift,
    setSize(w, h) {
      width = w;
      height = h;
      composer.setPixelRatio(renderer.getPixelRatio());
      composer.setSize(w, h);
    },
    setBloomScale(scale) {
      bloomScale = scale;
      composer.setSize(width, height);
    },
    /** mode: "glow" or "day"; shiftAmount: the RGB split this frame (0 for none). */
    render(useComposer, mode, shiftAmount) {
      if (!useComposer) {
        renderer.render(scene, camera);
        return;
      }
      const glow = mode === "glow";
      bloom.threshold = glow ? 0.6 : 0.985;
      bloom.strength = glow ? 0.8 : 0.7;
      bloom.radius = glow ? 0.45 : 0.6;
      shift.enabled = shiftAmount > 0;
      shift.uniforms.amount.value = shiftAmount;
      composer.render();
    },
  };
}
