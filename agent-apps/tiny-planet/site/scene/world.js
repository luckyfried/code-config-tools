// Builds the whole world from the seed and the theme, and draws it each frame from the game's state.
import * as THREE from "three";
import { createTerrain, pickStart, placeCrystals, RADIUS } from "../game/generation.js";
import { createRenderer } from "./renderer.js";
import { createCameraRig } from "./camera.js";
import { buildLights } from "./lights.js";
import { buildPlanet, buildSeaGeometry } from "./planet.js";
import { buildSky } from "./sky.js";
import { buildFlora } from "./flora.js";
import { buildExplorer } from "./explorer.js";
import { buildCrystals } from "./crystals.js";
import { buildFx } from "./fx.js";
import { createPost } from "./post.js";
import { seaMaterial, shared } from "./materials.js";

export function createWorld(canvas, settings, tokens, { seed, crystalCount }) {
  const { colors, numbers } = tokens;
  const terrain = createTerrain(seed, { landBias: numbers.worldLandBias, snowline: numbers.worldSnowline });
  const start = pickStart(terrain);
  const crystalDirs = placeCrystals(terrain, start, crystalCount);

  const renderer = createRenderer(canvas, settings);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 900);
  const rig = createCameraRig(camera);

  const planet = buildPlanet(terrain, colors, settings.detail);
  const sea = new THREE.Mesh(buildSeaGeometry(terrain, settings.seaDetail), seaMaterial(colors, numbers.worldSeaGlow));
  sea.receiveShadow = true;
  sea.renderOrder = 2;
  const sky = buildSky(colors, settings, terrain.random);
  const lights = buildLights(settings);
  const flora = buildFlora(planet.samplerMesh, colors, terrain.random, settings.flora);
  const explorer = buildExplorer(colors);
  const crystals = buildCrystals(terrain, crystalDirs, colors);
  const fx = buildFx(colors);

  scene.add(sky.group, planet.group, sea, flora.group, explorer.root, explorer.contact, crystals.group, fx.group, sky.rim, ...lights.group);

  const post = createPost(renderer, scene, camera);
  post.set(settings.post, settings.bloomScale);
  // Every shader is compiled before the first frame, so nothing stalls once the planet is on screen.
  renderer.compile(scene, camera);

  const sunDir = new THREE.Vector3();
  const up = new THREE.Vector3();
  const basis = new THREE.Matrix4();
  const side = new THREE.Vector3();
  const skySun = new THREE.Vector3();
  const lightDir = new THREE.Vector3();
  const anchor = new THREE.Vector3();
  const lowSun = new THREE.Vector3();
  const across = new THREE.Vector3();
  const moonAnchor = new THREE.Vector3();
  const camForward = new THREE.Vector3();
  const res = new THREE.Vector2();
  const smooth = THREE.MathUtils.smoothstep;
  const PLANET_EDGE = RADIUS + 0.3;

  // The direction from the camera through a point on the screen, in CSS px.
  function screenDir(x, y, out) {
    out.set((x / window.innerWidth) * 2 - 1, 1 - (y / window.innerHeight) * 2, 0.5).unproject(camera);
    return out.sub(camera.position).normalize();
  }

  function applyQuality(q) {
    renderer.setPixelRatio(q.ratio);
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    const shadows = q.shadowSize > 0;
    lights.setShadowSize(q.shadowSize);
    if (renderer.shadowMap.enabled !== shadows) {
      renderer.shadowMap.enabled = shadows;
      scene.traverse((o) => {
        if (o.material && !Array.isArray(o.material)) o.material.needsUpdate = true;
      });
    }
    flora.setDensity(q.flora);
    post.set(q.post, q.bloomScale);
  }

  function resize() {
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    rig.resize();
    post.resize();
  }

  // view: { pos, ground, heading, forward, pitch, blend, dive, sunElevation, sunAz, time, dt, reduced, motion }
  // ground: the radius of the ground (or the sea's surface) under the explorer.
  function draw(view) {
    shared.time.value = view.time;
    shared.sway.value = view.reduced ? 0 : 1;
    up.copy(view.pos).normalize();

    explorer.root.position.copy(view.pos);
    side.crossVectors(up, view.heading).normalize();
    basis.makeBasis(side, up, view.heading);
    explorer.root.quaternion.setFromRotationMatrix(basis);
    explorer.update(view.dt, view.motion);
    explorer.placeContact(up, view.ground, view.pos.length() - view.ground);

    const e = Math.sin(view.sunElevation);
    sunDir.copy(up).multiplyScalar(e).addScaledVector(view.sunAz, Math.cos(view.sunElevation)).normalize();

    const orbit = rig.update(view.dt, {
      focus: view.pos, localUp: up, forward: view.forward, blend: view.blend, pitch: view.pitch, dive: view.dive,
    });
    const evening = 1 - smooth(e, 0.12, 0.55);
    camera.getWorldDirection(camForward);

    // From orbit the sun hangs in the clear sky at noon, and at dusk sits just behind the planet's edge; the light
    // comes from its side of the screen, swung toward the camera at noon so the face of the planet is lit, and
    // across the disk at dusk so a clear line between day and night runs over it.
    const { cx, cy, radius } = rig.frame;
    const edge = radius * (PLANET_EDGE / 25.5);
    const w = window.innerWidth;
    const h = window.innerHeight;
    const wide = cx - radius * 1.4 > w * 0.12;
    const noonX = wide ? Math.max(cx - radius * 1.5, w * 0.14) : w * 0.1;
    const noonY = wide ? Math.max(cy - radius * 0.78, h * 0.07) : h * 0.035;
    const duskX = cx - edge * 0.72;
    const duskY = cy - edge * 0.72;
    screenDir(THREE.MathUtils.lerp(noonX, duskX, evening), THREE.MathUtils.lerp(noonY, duskY, evening), anchor);
    screenDir(wide ? Math.max(cx - radius * 1.75, w * 0.1) : w * 0.84, wide ? h * 0.17 : Math.max(cy - radius * 1.05, h * 0.06), moonAnchor);
    lightDir.copy(anchor).addScaledVector(camForward, -1.35).normalize();
    across.copy(anchor).addScaledVector(camForward, -anchor.dot(camForward)).normalize().addScaledVector(camForward, -0.24).normalize();
    lightDir.lerp(across, evening).normalize();
    lightDir.lerp(sunDir, 1 - orbit).normalize();

    // Over the shoulder on the title at dusk, the sun's disk sits just above the planet's edge ahead.
    const camLen = camera.position.length();
    const dip = camLen > PLANET_EDGE ? Math.sqrt(1 - (PLANET_EDGE / camLen) ** 2) : 0;
    skySun.copy(sunDir);
    const walkTitle = Math.max(0, view.blend - orbit) * evening;
    if (walkTitle > 0.001 && camLen > PLANET_EDGE) {
      const cf = camera.position.dot(view.sunAz);
      const cu = camera.position.dot(up);
      const horizon = Math.atan2(-cu, -cf) + Math.asin(PLANET_EDGE / camLen);
      const low = Math.min(view.sunElevation, horizon + 0.07);
      lowSun.copy(up).multiplyScalar(Math.sin(low)).addScaledVector(view.sunAz, Math.cos(low));
      skySun.lerp(lowSun, walkTitle).normalize();
    }
    skySun.lerp(anchor, orbit).normalize();

    renderer.getDrawingBufferSize(res);
    const lit = sky.update({
      camera, up, skySun, lightDir, sunAz: view.sunAz, e, orbit, title: view.blend, evening, moonAnchor, dip, res,
      frameRadius: radius,
    });
    lights.update({ focus: view.pos, up, sunDir: lightDir, e, sky: lit, orbit, evening });
    crystals.update(view.dt, view.time, view.reduced);
    fx.update(view.dt, up);
    renderer.toneMappingExposure = THREE.MathUtils.lerp(1.05, 1.25, lit.night);
    post.render();
    return lit;
  }

  return {
    renderer, scene, camera, rig, terrain, start, crystalDirs, explorer, crystals, fx, post,
    radius: RADIUS, applyQuality, resize, draw,
  };
}
