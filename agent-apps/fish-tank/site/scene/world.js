// The renderer, the camera framed so the tank fills any screen edge to edge, the lights, the soft environment, and
// on a desktop the bloom that lets the lamp and the glowing stripes bleed into the water.
import * as THREE from "three";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

export const DEPTH_BACK = -3.2;
export const DEPTH_FRONT = 2.6;

export function createWorld(canvas, quality) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: !quality.post, powerPreference: "high-performance" });
  renderer.setPixelRatio(quality.dpr);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x3fb7c9, 0.045);
  scene.background = new THREE.Color(0x0a5876);

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 80);
  const frame = { width: 1, height: 1, aspect: 1, tankW: 10, surfaceY: 8, base: new THREE.Vector3(), target: new THREE.Vector3() };
  const bounds = { x0: -4, x1: 4, y0: 1, y1: 6, z0: -2.4, z1: 2 };

  const hemi = new THREE.HemisphereLight(0xffffff, 0x404040, 1);
  const key = new THREE.DirectionalLight(0xffffff, 2);
  key.position.set(2.5, 12, 5);
  const lamp = new THREE.PointLight(0xbfe6ff, 0, 30, 1.4);
  scene.add(hemi, key, key.target, lamp);

  let composer = null;
  let bloom = null;
  if (quality.post) {
    composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }));
    composer.addPass(new RenderPass(scene, camera));
    bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.35, 0.5, 1.25);
    composer.addPass(bloom);
    composer.addPass(new OutputPass());
  }

  // the camera stands back far enough that the front pane of the tank fills the width, and taller screens see more
  // water rather than less tank
  const ray = new THREE.Raycaster();
  const plane = new THREE.Plane();
  const hit = new THREE.Vector3();
  const rectAtZ = (z) => {
    plane.set(new THREE.Vector3(0, 0, 1), -z);
    const pts = [[-1, -1], [1, 1]].map(([x, y]) => {
      ray.setFromCamera(new THREE.Vector2(x, y), camera);
      ray.ray.intersectPlane(plane, hit);
      return hit.clone();
    });
    return { x0: pts[0].x, y0: pts[0].y, x1: pts[1].x, y1: pts[1].y };
  };

  function resize(width, height) {
    frame.width = width;
    frame.height = height;
    frame.aspect = width / height;
    renderer.setSize(width, height, false);
    camera.aspect = frame.aspect;
    camera.fov = frame.aspect < 0.8 ? 46 : 40;
    const half = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const visibleH = Math.max(8.4, 6.6 / frame.aspect);
    const dist = visibleH / (2 * half);
    camera.position.set(0, 0, dist);
    camera.lookAt(0, -visibleH * 0.05, 0);
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
    const r0 = rectAtZ(0);
    const floorShift = r0.y0 + (r0.y1 - r0.y0) * 0.12;
    camera.position.y -= floorShift;
    frame.base.copy(camera.position);
    frame.target.set(0, -visibleH * 0.05 - floorShift, 0);
    camera.lookAt(frame.target);
    camera.updateMatrixWorld();
    const back = rectAtZ(DEPTH_BACK - 0.6);
    frame.surfaceY = back.y1 - (back.y1 - back.y0) * 0.075;
    const front = rectAtZ(DEPTH_FRONT);
    const mid = rectAtZ(0);
    frame.tankW = back.x1 - back.x0;
    frame.backRect = rectAtZ(DEPTH_BACK - 1.6);
    frame.frontRect = front;
    const phone = frame.aspect < 0.8;
    bounds.x0 = front.x0 + 0.5;
    bounds.x1 = front.x1 - 0.5;
    bounds.y0 = Math.max(0.9, mid.y0 + (mid.y1 - mid.y0) * (phone ? 0.2 : 0.2));
    bounds.y1 = Math.min(frame.surfaceY - 0.9, mid.y0 + (mid.y1 - mid.y0) * (phone ? 0.8 : 0.78));
    bounds.z0 = DEPTH_BACK + 0.6;
    bounds.z1 = DEPTH_FRONT - 0.4;
    key.position.set(frame.tankW * 0.15, frame.surfaceY + 6, 4);
    key.target.position.set(0, 0, -0.5);
    lamp.position.set(0, frame.surfaceY - 0.3, 0.6);
    if (composer) {
      composer.setPixelRatio(quality.dpr);
      composer.setSize(width, height);
      bloom.resolution.set(width / 2, height / 2);
    }
  }

  const envReady = new HDRLoader().loadAsync("vendor/env/soft-water.hdr").then((tex) => {
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromEquirectangular(tex).texture;
    scene.environmentIntensity = 0.7;
    tex.dispose();
    pmrem.dispose();
  }).catch(() => {});

  function render() {
    if (composer) composer.render();
    else renderer.render(scene, camera);
  }

  return { renderer, scene, camera, frame, bounds, lights: { hemi, key, lamp }, bloom, resize, render, rectAtZ, envReady };
}
