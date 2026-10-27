// Assembles the scene for a tier: sky, city, signs, streetlights, wet street, rain, splashes, drone, route, lights,
// and the post stack. One export, createWorld.
import * as THREE from "three";
import { createShared, applyPalette } from "./palette.js";
import { paintWindows, createCityMaterial, updateCityPalette, buildCity } from "./city.js";
import { paintSignAtlas, buildSigns, updateSignPalette } from "./signs.js";
import { buildLamps } from "./lamps.js";
import { buildReflectiveStreet, buildCubeStreet, createSkylineCapture, updateStreetPalette } from "./street.js";
import { buildSky } from "./sky.js";
import { buildRain, buildSplashes, RAIN_LAYER } from "./rain.js";
import { createDrone } from "./drone.js";
import { buildRoute } from "./route.js";
import { createCameraRig } from "./camera.js";
import { createRenderer } from "./renderer.js";
import { createPost } from "./post.js";
import { createRng } from "../game/rng.js";

export function createWorld({ canvas, tier, settings, plan, palette, droneModel, signWords }) {
  const renderer = createRenderer(canvas, settings.ratio);
  renderer.info.autoReset = false;
  const scene = new THREE.Scene();
  const shared = createShared();
  applyPalette(shared, palette);

  const rig = createCameraRig(plan);
  const camera = rig.camera;
  camera.layers.enable(RAIN_LAYER);

  const sky = buildSky(shared);
  scene.add(sky);

  const cityMaterial = createCityMaterial(shared, paintWindows(createRng(`windows:${plan.seed}`)));
  updateCityPalette(cityMaterial, palette);
  const city = buildCity(plan, cityMaterial);
  scene.add(city);

  const atlas = paintSignAtlas(signWords.horizontal, signWords.vertical, plan.cityName);
  const signs = buildSigns(plan, atlas, shared);
  updateSignPalette(signs, palette);
  scene.add(signs);

  const pointScale = () => renderer.domElement.height / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
  const lamps = buildLamps(plan, shared, 600);
  lamps.setPalette(palette);
  scene.add(lamps.group);

  // Light for the drone, the package, and the poles; everything else lights itself.
  const hemi = new THREE.HemisphereLight(0xffffff, 0xffffff, 1.4);
  const key = new THREE.DirectionalLight(0xffffff, 1.2);
  key.position.set(-60, 120, -40);
  scene.add(hemi, key);

  const skyline = createSkylineCapture();
  const size = new THREE.Vector2();
  renderer.getDrawingBufferSize(size);
  const street = settings.reflector ? buildReflectiveStreet(plan, shared, size.x, size.y) : buildCubeStreet(plan, shared, skyline.texture);
  updateStreetPalette(street.material, palette);
  scene.add(street.mesh);

  const rain = buildRain(shared, 6000);
  rain.setCount(settings.rain);
  rain.setPalette(palette);
  scene.add(rain.mesh);
  const splashes = buildSplashes(plan, shared, tier === "high" ? 160 : 90);
  splashes.setPalette(palette);
  scene.add(splashes.mesh);

  const drone = createDrone(droneModel, skyline.texture);
  drone.setPalette(palette);
  scene.add(drone.root, drone.holder);

  const route = buildRoute(shared);
  route.addDoors(plan.balconies, palette);
  route.setPalette(palette, palette.route);
  scene.add(route.group);

  const depthHidden = [sky, signs, lamps.heads, lamps.traffic, street.mesh, rain.mesh, splashes.mesh, route.group];
  let post = settings.post ? createPost({ renderer, scene, camera, tier, width: innerWidth, height: innerHeight, depthHidden }) : null;
  let current = palette;

  function setLights(p) {
    hemi.color.copy(p.skyHorizon).lerp(new THREE.Color(1, 1, 1), 0.35);
    hemi.groundColor.copy(p.lamp).multiplyScalar(0.6);
    hemi.intensity = p.light ? 2.2 : 1.6;
    key.color.copy(p.sign2).lerp(new THREE.Color(1, 1, 1), 0.5);
    key.intensity = p.light ? 1.6 : 1.1;
    renderer.toneMappingExposure = p.exposure;
  }
  setLights(palette);

  function captureSkyline(at) {
    skyline.capture(renderer, scene, at, [drone.root, drone.holder, route.group, rain.mesh, splashes.mesh, street.mesh]);
  }

  return {
    renderer,
    scene,
    camera,
    rig,
    shared,
    drone,
    route,
    rain,
    splashes,
    city,
    get tier() {
      return tier;
    },
    captureSkyline,
    setPalette(p) {
      current = p;
      applyPalette(shared, p);
      updateCityPalette(cityMaterial, p);
      updateSignPalette(signs, p);
      lamps.setPalette(p);
      updateStreetPalette(street.material, p);
      rain.setPalette(p);
      splashes.setPalette(p);
      drone.setPalette(p);
      route.setPalette(p, p.route);
      setLights(p);
    },
    resize(w, h) {
      renderer.setSize(w, h, false);
      rig.setSize(w, h);
      renderer.getDrawingBufferSize(size);
      street.resize(size.x, size.y);
      if (post) post.setSize(w, h);
      const s = pointScale();
      lamps.setScale(s);
      drone.setGlowScale(s);
      route.setPointScale(s);
    },
    setPixelRatio(ratio) {
      renderer.setPixelRatio(Math.min(devicePixelRatio || 1, ratio));
      if (post) post.setPixelRatio(renderer.getPixelRatio());
      this.resize(innerWidth, innerHeight);
    },
    dropPost() {
      post = null;
      rain.setCount(Math.min(settings.rain, 1500));
    },
    render(dt, time, focus, dropsAmount) {
      renderer.info.reset();
      shared.uTime.value = time;
      sky.position.copy(camera.position);
      if (post) {
        post.update(time, focus, current, dropsAmount);
        post.render(dt);
      } else {
        renderer.render(scene, camera);
      }
    },
    compile() {
      renderer.compile(scene, camera);
    },
    info() {
      return renderer.info.render;
    },
  };
}
