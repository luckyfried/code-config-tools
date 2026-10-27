// Assembles the stage: renderer, camera rig, lights, tray and pedestal, cubes, bloom, sparks, and motes, all colored
// from the theme's tokens. The game talks to it through the handful of verbs it returns.
import * as THREE from "three";
import { createCameraRig } from "./camera.js";
import { createCubes } from "./cubes.js";
import { createFlares, createMotes, createPost, createSparks } from "./fx.js";
import { createLabels } from "./labels.js";
import { createLights } from "./lights.js";
import { createGovernor, TIERS } from "./quality.js";
import { createRenderer } from "./renderer.js";
import { readTokens } from "./tokens.js";
import { createTray } from "./tray.js";

export function createWorld({ canvas, tierName, size, labelSet, reduced }) {
  const tier = TIERS[tierName];
  const renderer = createRenderer(canvas, tier);
  const scene = new THREE.Scene();
  const rig = createCameraRig();
  rig.setReduced(reduced);
  const lights = createLights(scene, renderer, tier);
  const board = new THREE.Group();
  scene.add(board);
  const labels = createLabels(renderer);
  const sparks = createSparks(board);
  const motes = createMotes(scene);
  const flares = createFlares(board);
  const cubes = createCubes({ parent: board, labels, sparks, flares, lights });
  const post = createPost(renderer, scene, rig.camera, tier);
  let tokens = readTokens();
  let tray = null;
  let slot = null;
  let trayRect = null;
  let ratio = Math.min(devicePixelRatio || 1, tier.ratio);
  let dim = 0;
  let dimTo = 0;
  let boost = 0;
  let boostTo = 0;

  const governor = createGovernor({
    onStep(step) {
      if (step === "no-bloom") {
        post.setOn(false);
        cubes.configure({ bloom: false });
      }
      else {
        ratio = Math.min(devicePixelRatio || 1, step);
        resize();
      }
    },
  });

  function applyTokens() {
    tokens = readTokens();
    scene.background = tokens.bg.clone();
    renderer.toneMappingExposure = tokens.exposure;
    labels.configure({ fontFamily: tokens.fontDisplay, labelSet, inkList: tokens.cubes.map((c) => c.ink) });
    cubes.configure({ tokens, size, reduced, flash: !reduced, bloom: post.on });
    lights.apply(tokens);
    post.apply(tokens);
    motes.apply(tokens);
  }

  function buildTray() {
    tray?.dispose();
    tray = createTray({ size, tokens, renderer });
    board.add(tray.group);
    lights.apply(tokens);
  }

  let drawn = "";
  function resize() {
    const w = innerWidth;
    const h = innerHeight;
    // The buffers are reallocated only when the canvas itself changes; a slot that moves (the "Get this app" bar
    // easing in) only reframes the camera.
    const key = `${w}x${h}@${ratio}`;
    if (key !== drawn) {
      drawn = key;
      renderer.setPixelRatio(ratio);
      renderer.setSize(w, h, false);
      post.setSize(w, h, ratio);
    }
    if (slot && tray) trayRect = rig.frame(tray.box, slot, w, h);
  }

  applyTokens();
  buildTray();

  return {
    renderer,
    get tier() {
      return tierName;
    },
    /** The rect, in CSS pixels, the tray should fill; returns where the tray landed on screen. */
    setSlot(rect) {
      slot = rect;
      resize();
      return trayRect;
    },
    resize,
    restyle() {
      applyTokens();
      buildTray();
      cubes.restyle();
    },
    setLabels(next) {
      labelSet = next;
      applyTokens();
      cubes.restyle();
    },
    setSize(next, state) {
      size = next;
      cubes.configure({ size });
      buildTray();
      resize();
      cubes.sync(state, { intro: true });
    },
    show(boardState, { intro = false } = {}) {
      cubes.sync(boardState, { intro });
    },
    play(result, spawned, dir) {
      cubes.play(result, spawned, dir);
      rig.lean(dir);
    },
    bump(dir) {
      cubes.bump(dir);
      rig.lean(dir);
    },
    clear() {
      return cubes.clear();
    },
    celebrate(id) {
      cubes.celebrate(id);
      dimTo = 1;
      boostTo = reduced ? 0 : 1;
      rig.setPush(1);
    },
    settle() {
      cubes.settle();
      dimTo = 0;
      boostTo = 0;
      rig.setPush(0);
    },
    setDim(value) {
      dimTo = value;
    },
    /**
     * Compiles every shader the board will use and uploads the stage's textures, with a sample of every cube, the
     * merge's burst, and the winning cube's glow drawn once out of sight, so no later frame waits on a compile.
     */
    warm() {
      // A full board and a row of merges' worth of cubes, which are then kept for the game to dress.
      const sample = { size, score: 0, tiles: [] };
      for (let i = 0; i < size * size + size * 2; i += 1) sample.tiles.push({ id: -1 - i, value: 2 ** ((i % 12) + 1), r: Math.floor(i / size) % size, c: i % size });
      cubes.sync(sample);
      cubes.warm(true);
      flares.warm(true);
      post.render(0);
      flares.warm(false);
      cubes.warm(false);
      cubes.sync({ size, score: 0, tiles: [] });
      labels.reset();
    },
    /** Draws and uploads the face of every value, once the display face has loaded. */
    prepareFaces() {
      for (let i = 1; i <= 13; i += 1) renderer.initTexture(labels.texture(2 ** i));
    },
    get busy() {
      return cubes.busy;
    },
    get count() {
      return cubes.count;
    },
    frame(dt, ms) {
      governor.sample(ms);
      dim += (dimTo - dim) * Math.min(1, dt * 5);
      boost += (boostTo - boost) * Math.min(1, dt * 3);
      cubes.setDim(dim);
      lights.setDim(dim);
      tray?.setDim(dim);
      scene.background.copy(tokens.bg).multiplyScalar(1 - 0.3 * dim);
      post.setBoost(boost);
      cubes.update(dt);
      sparks.update(dt);
      flares.update(dt);
      motes.update(dt, reduced);
      lights.update(dt);
      rig.update(dt);
      post.render(dt);
    },
  };
}
