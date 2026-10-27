// The whole 3D world in one place: renderer, sky, ground, grass, the town, the water tower, the funnel, sparks, and
// bloom. The game moves the storm and calls frame(); a theme or quality change goes through applyTokens and
// applyQuality.
import * as THREE from "three";
import { createRenderer } from "./renderer.js";
import { createPost } from "./post.js";
import { createCameraRig } from "./camera.js";
import { createLights } from "./lights.js";
import { createSky } from "./sky.js";
import { createGround } from "./ground.js";
import { createGrass } from "./grass.js";
import { createFunnel } from "./funnel.js";
import { createPropMaterial, createTownMeshes, createWaterTower } from "./town.js";
import { createSparks } from "./sparks.js";
import { seedRandom } from "../game/generation.js";

export function createWorld(canvas, settings, tokens, { town, townName, seed, reducedMotion }) {
  const renderer = createRenderer(canvas, settings);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xffffff, 60, 240);
  const camera = new THREE.PerspectiveCamera(46, window.innerWidth / window.innerHeight, 0.5, 1200);
  const rig = createCameraRig(camera);
  const lights = createLights({ tokens, shadowSize: settings.shadowSize });
  const sky = createSky({ tokens, rain: settings.rain, reducedMotion });
  const ground = createGround({ town, tokens, rnd: seedRandom(`${seed}:ground`), anisotropy: Math.min(8, renderer.capabilities.getMaxAnisotropy()) });
  const funnel = createFunnel({ tokens, chips: settings.chips });
  const grass = createGrass({ ground, funnel, tokens, blades: settings.blades });
  const propMaterial = createPropMaterial(tokens);
  const meshes = createTownMeshes({ town, propMaterial, shadows: settings.shadowSize > 0 });
  const tower = createWaterTower({ town, name: townName, tokens, shadows: settings.shadowSize > 0 });
  const sparks = createSparks(tokens);
  scene.add(lights.group, sky.group, ground.mesh, grass.mesh, meshes.group, tower.group, funnel.group, sparks.points);
  const post = createPost(renderer, scene, camera);
  post.set(settings.post, settings.bloomScale);

  const center = new THREE.Vector3();
  let quality = { ...settings };

  function applyTokens(t) {
    scene.fog.color.copy(t.colors.fog);
    scene.fog.near = t.numbers.fogNear;
    scene.fog.far = t.numbers.fogFar;
    renderer.toneMappingExposure = t.numbers.exposure || 1;
    lights.applyTokens(t);
    sky.applyTokens(t);
    sky.setSun(lights.dir);
    ground.applyTokens(t);
    grass.applyTokens(t);
    funnel.applyTokens(t);
    propMaterial.applyTokens(t);
    tower.applyTokens(t);
    sparks.applyTokens(t);
    const l = lights.lighting();
    funnel.setLighting(l);
    grass.setLighting(l);
  }

  function resize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    renderer.setPixelRatio(quality.ratio);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    post.resize();
    const px = h * renderer.getPixelRatio();
    sky.setResolution(w * renderer.getPixelRatio(), px);
    funnel.setPxScale(px * 0.5);
    sparks.setPxScale(px * 0.9);
  }

  applyTokens(tokens);
  resize();

  return {
    renderer,
    scene,
    camera,
    rig,
    funnel,
    sky,
    grass,
    sparks,
    lights,
    meshes,
    applyTokens,
    resize,
    applyQuality(q) {
      quality = { ...q };
      funnel.setChips(q.chips);
      grass.setBlades(q.blades);
      sky.setRain(q.rain);
      post.set(q.post, q.bloomScale);
      if (!q.shadowSize && renderer.shadowMap.enabled) {
        renderer.shadowMap.enabled = false;
        lights.sun.castShadow = false;
        scene.traverse((o) => {
          if (o.material) o.material.needsUpdate = true;
        });
      }
      resize();
    },
    // Compile every program before the first frame, so the first seconds of the storm never stall.
    async warm() {
      await renderer.compileAsync(scene, camera);
    },
    frame(dt, time, s) {
      funnel.update(time, s.pos, s.growth, s.lean, s.pulse, sky.flash);
      propMaterial.shared.uFunnelP.value.set(s.pos.x, 0, s.pos.z);
      propMaterial.shared.uReach.value = funnel.reach;
      propMaterial.shared.uTime.value = time;
      rig.update(dt, { focus: s.pos, growth: s.growth, offsetBlend: s.offsetBlend, reduced: s.reduced, shakeBase: s.shakeBase, velocity: s.velocity });
      center.set(s.pos.x * 0.7 + camera.position.x * 0.3, 0, s.pos.z * 0.75 + camera.position.z * 0.25);
      grass.update(time, center, s.pulseR, sky.flash);
      sky.update(dt, time, camera.position, center);
      sparks.update(dt);
      lights.follow(s.pos);
      post.render();
    },
  };
}
