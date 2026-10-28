// Assembles the scene: renderer, camera rig, backdrop, stars, shards, sparks, ship, and post. The field is sized so a
// phone and a desktop hold about the same area of play: the shorter side is never cramped and the wider screen sees
// more of the storm.
import * as THREE from "three";
import { createRenderer } from "./renderer.js";
import { createCameraRig } from "./camera.js";
import { createBackdrop } from "./backdrop.js";
import { createStars } from "./stars.js";
import { createShards } from "./shards.js";
import { createSparks } from "./sparks.js";
import { createShip } from "./ship.js";
import { createPost } from "./post.js";
import { shared } from "./materials.js";

const FIELD_AREA = 160 * 100;

export function createWorld({ canvas, tier, tokens, pool }) {
  let mode = tokens.mode;
  let current = tier;
  const renderer = createRenderer(canvas, tier);
  renderer.setClearColor(tokens.bg, 1);
  const scene = new THREE.Scene();
  const rig = createCameraRig();
  const backdrop = createBackdrop(mode, tokens);
  const stars = createStars(mode, tokens);
  const shards = createShards(pool, mode);
  const sparks = createSparks(mode);
  const ship = createShip(mode, tokens);
  scene.add(backdrop.mesh, stars.group, shards.halo, shards.mesh, ship.trail, sparks.mesh, ship.group);
  const post = createPost(renderer, scene, rig.camera);
  const field = { W: 80, H: 50, pxPerUnit: 9, width: 1, height: 1 };

  function resize(width, height) {
    field.width = width;
    field.height = height;
    field.pxPerUnit = Math.sqrt((width * height) / FIELD_AREA);
    field.W = width / 2 / field.pxPerUnit;
    field.H = height / 2 / field.pxPerUnit;
    renderer.setSize(width, height, false);
    rig.fit(field.H, width / height);
    backdrop.fit(field.W, field.H, rig.distance);
    stars.fit(field.W, field.H, rig.distance, renderer.getPixelRatio());
    post.setSize(width, height);
    pool.setField(field.W, field.H);
    return field;
  }

  return {
    field,
    ship,
    sparks,
    shared,
    get tier() {
      return current;
    },
    get mode() {
      return mode;
    },
    resize,
    /** Shards over the new cap fly on until they leave; only a change of pixel ratio or bloom size resizes. */
    setTier(next) {
      const resized = next.dpr !== current.dpr || next.bloomScale !== current.bloomScale;
      current = next;
      pool.limit = Math.min(pool.capacity, next.bullets);
      if (!resized) return;
      renderer.setPixelRatio(Math.min(devicePixelRatio || 1, next.dpr));
      post.setBloomScale(next.bloomScale);
      resize(field.width, field.height);
    },
    setLook(next) {
      mode = next.mode;
      renderer.setClearColor(next.bg, 1);
      backdrop.setLook(mode, next);
      stars.setLook(mode, next);
      shards.setLook(mode);
      sparks.setLook(mode);
      ship.setLook(mode, next);
    },
    setEye(x, y) {
      backdrop.setEye(x, y, rig.distance);
    },
    /** One frame: f carries time, fxTime, pulse, drift, dolly, focus, shake, and the RGB shift amount. */
    render(f) {
      shards.write();
      sparks.update(f.fxTime);
      stars.update(f.time);
      backdrop.mesh.material.uniforms.uTime.value = f.time;
      backdrop.mesh.material.uniforms.uPulse.value = f.pulse;
      rig.update(f.time, f.drift, f.dolly, f.fx, f.fy, f.sx, f.sy, f.roll);
      post.render(current.post, mode, f.shift);
    },
    /**
     * Before the first frame: draws through the bloom with the RGB split on, then straight to the screen, so every
     * program any tier or a graze can need is compiled while the page loads rather than in the middle of a run.
     */
    prewarm() {
      shards.write();
      post.render(true, mode, 0.01);
      post.render(false, mode, 0);
      // Waits for the graphics process to link those programs now, not during the first frames.
      renderer.getContext().finish();
    },
  };
}
