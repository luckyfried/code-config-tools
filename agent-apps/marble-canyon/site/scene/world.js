// Assembles the scene for one track at one quality tier: renderer, sky, environment, lights, canyon, track,
// marble, ghost, effects, and the post stack.
import { Fog, Scene } from "three";
import { createCanyon } from "./canyon.js";
import { ChaseCamera } from "./camera.js";
import { createEffects } from "./effects.js";
import { Environment } from "./env.js";
import { createLights } from "./lights.js";
import { createGhost, createMarble } from "./marble.js";
import { createMaterials } from "./materials.js";
import { createPost } from "./post.js";
import { createRenderer } from "./renderer.js";
import { createSky } from "./sky.js";
import { createTrack } from "./track.js";

export function createWorld({ canvas, tier, tokens, track, marbleColor, seed, reducedMotion }) {
  const renderer = createRenderer(canvas, tier, tokens.exposure);
  const scene = new Scene();
  scene.fog = new Fog(tokens.fog, tokens.fogNear, tokens.fogFar);
  scene.environmentIntensity = tokens.envIntensity;

  const sky = createSky(tokens);
  scene.add(sky.mesh);
  const env = new Environment(renderer, scene);
  env.fromSky(sky.mesh);

  const lights = createLights(tokens, tier);
  scene.add(lights.hemi, lights.sun, lights.target);

  const materials = createMaterials(tier, tokens, marbleColor);
  const canyon = createCanyon(track, materials, tier, seed);
  scene.add(canyon.group);
  const trackView = createTrack(track, materials, tier, tokens);
  scene.add(trackView.group);

  const marble = createMarble(tier, materials);
  marble.sun(tokens.sunDir);
  scene.add(marble.group, marble.contact);
  const ghost = createGhost(tier, materials);
  scene.add(ghost.group, ghost.trail);

  const chase = new ChaseCamera(reducedMotion);
  scene.add(chase.camera);

  let ratio = Math.min(window.devicePixelRatio || 1, tier.pixelRatio);
  const effects = createEffects(tier, tokens, ratio);
  scene.add(...effects.objects, effects.cameraRig);

  let post = createPost(renderer, scene, chase.camera, tier, tokens.glowStrength);

  const resize = () => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    renderer.setPixelRatio(ratio);
    renderer.setSize(w, h, false);
    chase.resize(w, h);
    if (post) post.setSize(w, h, ratio);
  };
  resize();

  return {
    renderer,
    scene,
    chase,
    marble,
    ghost,
    effects,
    track: trackView,
    canyon,
    lights,
    sky,
    env,
    materials,
    get post() {
      return post;
    },
    resize,
    loadEnvironment(name) {
      return env.load(name);
    },
    warm() {
      renderer.compile(scene, chase.camera);
    },
    render() {
      sky.follow(chase.camera);
      if (post) post.render();
      else renderer.render(scene, chase.camera);
    },
    // One step down after slow frames: a lower pixel ratio, then no post stack, then no shadows.
    stepDown(step) {
      if (step === 1) ratio = Math.min(ratio, 1.5);
      else if (step === 2) ratio = Math.min(ratio, 1);
      else if (step === 3 && post) {
        post.composer.dispose();
        post = null;
      } else if (step >= 3) {
        renderer.shadowMap.enabled = false;
        lights.sun.castShadow = false;
        scene.traverse((o) => {
          if (o.material) {
            const list = Array.isArray(o.material) ? o.material : [o.material];
            for (const m of list) m.needsUpdate = true;
          }
        });
      }
      resize();
    },
    applyTokens(t) {
      scene.fog.color.copy(t.fog);
      scene.fog.near = t.fogNear;
      scene.fog.far = t.fogFar;
      scene.environmentIntensity = t.envIntensity;
      renderer.toneMappingExposure = t.exposure;
      sky.apply(t);
      lights.apply(t);
      marble.sun(t.sunDir);
      materials.apply(t);
      trackView.applyColors(t);
      canyon.recolor();
      ghost.applyColors();
      effects.applyColors(t);
      if (post) post.setGlow(t.glowStrength);
      env.fromSky(sky.mesh);
      env.name = null;
      return env.load(t.env);
    },
  };
}
