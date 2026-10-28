// Assembles the sky: dome, stars (with trails), constellation lines, planets, the Moon, and the ground, drawn in
// that order with one shared projection. `createWorld({ tier, tokens })` is the one entry point.
import * as THREE from "three";
import { createRenderer } from "./renderer.js";
import { createDome } from "./dome.js";
import { createStars } from "./stars.js";
import { createLines } from "./lines.js";
import { createPlanets, createMoon } from "./bodies.js";
import { createGround } from "./horizon.js";
import { createTrails } from "./trails.js";
import { MASK_COUNT } from "./shaders.js";

const v3 = (c) => new THREE.Vector3(c[0], c[1], c[2]);

export function createWorld({ canvas, tier, tokens, starGeometry, lineGeometry }) {
  const renderer = createRenderer(canvas, tier);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  const shared = {
    uSky: { value: new THREE.Matrix3() },
    uView: { value: new THREE.Matrix3() },
    uK: { value: 500 },
    uHalf: { value: new THREE.Vector2(1, 1) },
    uDpr: { value: tier.pixelRatio },
    uMask: { value: Array.from({ length: MASK_COUNT }, () => new THREE.Vector4(0, 0, 0, 0)) },
    uMaskAmt: { value: new Float32Array(MASK_COUNT) },
  };
  const sky = {
    cNightZ: { value: new THREE.Vector3() },
    cNightH: { value: new THREE.Vector3() },
    cAstroZ: { value: new THREE.Vector3() },
    cAstroH: { value: new THREE.Vector3() },
    cNautZ: { value: new THREE.Vector3() },
    cNautH: { value: new THREE.Vector3() },
    cCivilRim: { value: new THREE.Vector3() },
    cDayZ: { value: new THREE.Vector3() },
    cDayH: { value: new THREE.Vector3() },
    cGlow: { value: new THREE.Vector3() },
    uSunAlt: { value: -30 },
    uSunDir: { value: new THREE.Vector3(0, -1, 0) },
    uMoonDir: { value: new THREE.Vector3(0, -1, 0) },
    uMoonLight: { value: 0 },
    uGlowAmt: { value: 0.6 },
    uInkMode: { value: 0 },
  };

  const dome = createDome(shared, sky);
  const stars = createStars(shared, starGeometry);
  const lines = createLines(shared, lineGeometry);
  const planets = createPlanets(shared);
  const moon = createMoon(shared);
  const ground = createGround(shared, sky);
  const trails = createTrails(renderer);

  const domeScene = new THREE.Scene();
  domeScene.add(dome.mesh);
  const starScene = new THREE.Scene();
  starScene.add(stars.points);
  const overlayScene = new THREE.Scene();
  lines.mesh.renderOrder = 1;
  planets.points.renderOrder = 2;
  moon.disc.renderOrder = 3;
  overlayScene.add(lines.mesh, planets.points, moon.disc);
  const groundScene = new THREE.Scene();
  groundScene.add(ground.mesh);

  let ink = false;
  let lineStyle = "lines";
  let trailing = false;

  function setTokens(p) {
    sky.cNightZ.value.copy(v3(p.nightZ));
    sky.cNightH.value.copy(v3(p.nightH));
    sky.cAstroZ.value.copy(v3(p.astroZ));
    sky.cAstroH.value.copy(v3(p.astroH));
    sky.cNautZ.value.copy(v3(p.nautZ));
    sky.cNautH.value.copy(v3(p.nautH));
    sky.cCivilRim.value.copy(v3(p.civilRim));
    sky.cDayZ.value.copy(v3(p.dayZ));
    sky.cDayH.value.copy(v3(p.dayH));
    sky.cGlow.value.copy(v3(p.glow));
    ink = p.inkMode > 0.5;
    sky.uInkMode.value = ink ? 1 : 0;
    dome.uniforms.cInk.value.copy(v3(p.ink));
    ground.uniforms.cGround.value.copy(v3(p.ground));
    ground.uniforms.cGroundHaze.value.copy(v3(p.groundHaze));
    ground.uniforms.cLight.value.copy(v3(p.light));
    ground.uniforms.cInk.value.copy(v3(p.ink));
    lines.uniforms.uColor.value.copy(v3(lineStyle === "art" ? p.lineArt : p.line));
    stars.uniforms.uMono.value = p.starMono;
    stars.uniforms.uTint.value.copy(v3(p.starTint));
    stars.uniforms.uGain.value = p.starGain || 1;
    planets.uniforms.uMono.value = p.starMono;
    planets.uniforms.uTint.value.copy(v3(p.starTint));
    moon.uniforms.uMono.value = ink ? 0 : p.starMono;
    moon.uniforms.uTint.value.copy(v3(p.starTint));
    moon.uniforms.uInk.value.copy(v3(p.ink));
    moon.uniforms.uInkLight.value = p.ink[0] * 0.3 + p.ink[1] * 0.59 + p.ink[2] * 0.11 > 0.5 ? 1 : 0;
    dome.uniforms.uMono.value = ink ? 0 : p.starMono;
    dome.uniforms.uTint.value.copy(v3(p.starTint));
    stars.setInk(ink);
    planets.setInk(ink);
    moon.setInk(ink);
    lines.setStyle(lineStyle, ink);
    trails.setInk(ink, p.ink);
    world.palette = p;
  }

  function resize(w, h) {
    renderer.setPixelRatio(tier.pixelRatio);
    renderer.setSize(w, h, false);
    shared.uHalf.value.set(w / 2, h / 2);
    shared.uDpr.value = tier.pixelRatio;
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    trails.resize(size.x, size.y);
  }

  function setMatrix(target, m) {
    target.set(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8]);
  }

  const world = {
    renderer,
    palette: null,
    setTokens,
    resize,
    setTier(next) {
      Object.assign(tier, next);
      resize(shared.uHalf.value.x * 2, shared.uHalf.value.y * 2);
    },
    setMilkyWay(texture) {
      dome.setTexture(texture);
    },
    // rects: up to MASK_COUNT of [left, top, right, bottom, amount] in css pixels.
    setMask(rects) {
      for (let i = 0; i < MASK_COUNT; i += 1) {
        const r = rects[i];
        if (r) shared.uMask.value[i].set(r[0], r[1], r[2], r[3]);
        shared.uMaskAmt.value[i] = r ? r[4] : 0;
      }
    },
    setMoonMap(texture) {
      moon.setMap(texture);
    },
    setHorizon(kind, seed) {
      ground.setSilhouette(kind, seed, tier.silhouette[0], tier.silhouette[1]);
    },
    setLineStyle(style) {
      lineStyle = style;
      if (world.palette) lines.uniforms.uColor.value.copy(v3(style === "art" ? world.palette.lineArt : world.palette.line));
      lines.setStyle(style, ink);
    },
    updateBodies(bodies) {
      planets.update(bodies);
      moon.update(bodies.Moon, bodies.Sun, moon.uniforms.uRadius.value);
    },
    render(f) {
      setMatrix(shared.uSky.value, f.sky);
      setMatrix(shared.uView.value, f.view);
      shared.uK.value = f.k;

      sky.uSunAlt.value = f.sunAlt;
      sky.uSunDir.value.set(...f.sunWorld);
      sky.uMoonDir.value.set(...f.moonWorld);
      sky.uMoonLight.value = ink ? 0 : f.moonLight;
      sky.uGlowAmt.value = f.glow;
      dome.uniforms.uMWAmt.value = tier.milkyWay && dome.uniforms.uMW.value ? f.milkyWay : 0;

      const su = stars.uniforms;
      su.uTime.value = f.time;
      su.uMagLimit.value = f.magLimit;
      su.uMagCut.value = Math.min(tier.magCut, f.magCut);
      su.uZoom.value = f.zoom;
      su.uTwinkle.value = f.twinkle;

      lines.uniforms.uAlpha.value.set(f.conAlpha);
      lines.uniforms.uDraw.value.set(f.conDraw);
      lines.uniforms.uMaster.value = f.lineMaster;

      planets.uniforms.uZoom.value = f.zoom;
      planets.uniforms.uFade.value = f.planetFade;
      moon.uniforms.uRadius.value = f.moonRadius;
      moon.uniforms.uScale.value = ink ? 1.05 : 4.5;
      moon.uniforms.uPoleEq.value.set(0, 0, 1);
      moon.uniforms.uHaloAmt.value = f.moonHalo;
      ground.uniforms.uTime.value = f.time;

      renderer.setRenderTarget(null);
      renderer.autoClear = false;
      renderer.clear(true, false, false);
      renderer.render(domeScene, camera);
      const wantTrails = f.trail > 0.01;
      if (wantTrails) {
        if (!trailing) trails.reset();
        trailing = true;
        const dpr = shared.uDpr.value;
        shared.uDpr.value = dpr * 0.5;
        trails.accumulate(starScene, f.trailDecay);
        shared.uDpr.value = dpr;
        renderer.setRenderTarget(null);
      } else {
        trailing = false;
      }
      renderer.render(starScene, camera);
      if (wantTrails) trails.drawComposite();
      renderer.render(overlayScene, camera);
      renderer.render(groundScene, camera);
    },
  };
  setTokens(tokens);
  return world;
}
