// The whole scene: renderer, camera rig, ground, wind, and the place marker, driven by one render(dt) call.
import * as THREE from "three";
import { createRenderer, readTokens } from "./renderer.js";
import { createCamera } from "./camera.js";
import { createGround, canvasTexture } from "./ground.js";
import { createWind } from "./wind.js";
import { createMarker } from "./marker.js";

export function createWorld({ canvas, tier }) {
  const renderer = createRenderer(canvas, tier);
  const maxAniso = renderer.capabilities.getMaxAnisotropy();
  let tokens = readTokens();
  const scene = new THREE.Scene();
  const rig = createCamera();
  const ground = createGround(tokens);
  const marker = createMarker(tokens);
  const wind = createWind(renderer, tier);
  scene.add(ground.mesh, marker.mesh);
  renderer.setClearColor(new THREE.Color().setRGB(tokens.edge.x, tokens.edge.y, tokens.edge.z, THREE.SRGBColorSpace));

  // layer switches ease in and out rather than snapping
  const layers = { radar: 1, wind: 1, clouds: 0 };
  const shown = { radar: 1, wind: 1, clouds: 0 };
  let time = 0;
  let boxAge = 0;
  let windActive = true;
  let frameTextures = [];

  const world = {
    rig,
    renderer,
    get tokens() {
      return tokens;
    },
    refreshTokens() {
      tokens = readTokens();
      ground.setTokens(tokens);
      marker.setTokens(tokens);
      renderer.setClearColor(new THREE.Color().setRGB(tokens.edge.x, tokens.edge.y, tokens.edge.z, THREE.SRGBColorSpace));
    },
    resize(w, h, top, bottom) {
      renderer.setSize(w, h, false);
      rig.resize(w, h, top, bottom);
      boxAge = 1e9;
    },
    setTier(t) {
      renderer.setPixelRatio(t.ratio);
      renderer.setSize(rig.width, rig.height, false);
      wind.setTier(t);
      ground.uniforms.uGlow.value = t.glow ? 1 : 0;
    },
    setMap(map) {
      const land = map.land ? canvasTexture(map.land, { anisotropy: maxAniso }) : null;
      const roads = map.roads ? canvasTexture(map.roads, { anisotropy: maxAniso }) : null;
      const base = map.base ? canvasTexture(map.base, { anisotropy: maxAniso }) : null;
      ground.setMap({ land, roads, base });
    },
    setFrames(frames) {
      for (const t of frameTextures) t?.dispose();
      frameTextures = frames.map((f) => (f.ok ? canvasTexture(f.image, { premultiply: true }) : null));
      // upload every frame now so the loop never stalls on its first pass
      for (const t of frameTextures) if (t) renderer.initTexture(t);
    },
    showFrames(a, b, mix) {
      ground.setFrames(frameTextures[a], frameTextures[b], mix);
    },
    setWind(u, v) {
      wind.setField(u, v);
    },
    setClouds(cover) {
      ground.setClouds(cover);
    },
    setLayers(next) {
      Object.assign(layers, next);
    },
    setWindActive(on) {
      windActive = on;
    },
    // a few seconds of wind drawn at once, for a still map under reduced motion
    settleWind(seconds) {
      wind.setBox(rig.visibleBox());
      for (let t = 0; t < seconds; t += 1 / 30) wind.step(1 / 30, true);
    },
    placeOnScreen() {
      return rig.project(new THREE.Vector3(0, 0, 0));
    },
    render(dt, { animate = true } = {}) {
      time += dt;
      for (const k of Object.keys(layers)) {
        const goal = layers[k] ? 1 : 0;
        shown[k] += (goal - shown[k]) * Math.min(1, dt * 6);
        if (Math.abs(goal - shown[k]) < 0.002) shown[k] = goal;
      }
      boxAge += dt;
      if (boxAge > 0.5) {
        wind.setBox(rig.visibleBox());
        boxAge = 0;
      }
      if (animate && windActive && shown.wind > 0) wind.step(dt, true);
      const u = ground.uniforms;
      const d = rig.distance();
      u.uFogNear.value = d * 1.05;
      u.uFogFar.value = d * 1.95;
      u.uTime.value = time;
      u.uRadar.value = shown.radar;
      u.uWind.value = shown.wind;
      u.uCloud.value = shown.clouds;
      u.uTrail.value = wind.texture;
      const px = rig.unitsPerPixel();
      marker.update(animate ? time : 0.35, px * 76);
      marker.uniforms.uPulse.value = animate ? 1 : 0;
      renderer.render(scene, rig.camera);
    },
  };
  world.setTier(tier);
  return world;
}
