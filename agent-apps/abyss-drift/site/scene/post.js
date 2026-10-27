// The post stack, built by tier: render, depth of field, god rays, bloom, the underwater tint, and the output.
// Mid drops depth of field and god rays; low keeps only the tint pass.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";
import { UnderwaterShader, GodRayShader } from "./water.js";

export function createPost(renderer, scene, camera, tier) {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const target = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: tier.msaa });
  const composer = new EffectComposer(renderer, target);
  composer.setPixelRatio(renderer.getPixelRatio());
  composer.setSize(innerWidth, innerHeight);
  composer.addPass(new RenderPass(scene, camera));

  const bokeh = new BokehPass(scene, camera, { focus: 10, aperture: 0.0016, maxblur: 0.0065 });
  bokeh.enabled = tier.bokeh;
  composer.addPass(bokeh);

  const godRays = new ShaderPass(GodRayShader);
  godRays.enabled = tier.godRays;
  composer.addPass(godRays);

  const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.85, 0.55, 0.62);
  bloom.enabled = tier.bloom;
  composer.addPass(bloom);

  const underwater = new ShaderPass(UnderwaterShader);
  composer.addPass(underwater);
  composer.addPass(new OutputPass());

  const lightNdc = new THREE.Vector3();
  return {
    composer,
    bokeh,
    godRays,
    bloom,
    underwater,
    applyTier(t) {
      bokeh.enabled = t.bokeh;
      godRays.enabled = t.godRays;
      bloom.enabled = t.bloom;
    },
    setSize(w, h, pr) {
      composer.setPixelRatio(pr);
      composer.setSize(w, h);
      underwater.uniforms.uAspect.value = w / h;
    },
    /** Places the god rays' source straight above the camera, wherever that lands on (or off) the screen. */
    aimGodRays(cam, strength) {
      godRays.uniforms.uStrength.value = strength;
      if (strength <= 0) return;
      lightNdc.copy(cam.position).add(new THREE.Vector3(8, 160, 4)).project(cam);
      const behind = lightNdc.z > 1;
      const x = THREE.MathUtils.clamp(lightNdc.x * 0.5 + 0.5, -1.5, 2.5);
      const y = THREE.MathUtils.clamp(lightNdc.y * 0.5 + 0.5, -1.0, 3.0);
      godRays.uniforms.uLight.value.set(behind ? 1 - x : x, behind ? 2.5 : y);
    },
    render(dt) {
      composer.render(dt);
    },
  };
}
