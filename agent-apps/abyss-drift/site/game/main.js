// Abyss Drift: the page's entry. Reads config.js, builds the world, opens on the live trench behind the surface
// sheet, and runs Surface → Dive → Surface again.
import * as THREE from "three";
import WebGL from "three/addons/capabilities/WebGL.js";
import { pickTier, createGovernor } from "../scene/quality.js";
import { readTokens, isDark } from "../scene/tokens.js";
import { createWorld } from "../scene/world.js";
import { SPECIES, SPECIES_BY_ID } from "./species.js";
import { createRng } from "./rng.js";
import { createHud } from "./hud.js";
import { createInput } from "./input.js";
import { createLoop } from "./loop.js";
import { createDive, MOTION } from "./dive.js";
import { loadLog, recordPhoto, recordDive } from "./log.js";
import { evaluate, composeFrame, toPng, thumbnail, savePhoto } from "./photo.js";
import { createSynth } from "../audio/synth.js";

const config = readConfig();
const include = new Set(config.species);
const hud = createHud({ species: include, config });
const log = loadLog();
hud.renderSurface(log);
hud.show("surface");

boot().catch((err) => {
  hud.els.status.textContent = "The trench could not be drawn on this device.";
  console.error(err);
});

async function boot() {
  if (!WebGL.isWebGL2Available()) {
    hud.els.status.textContent = "This dive needs WebGL 2, which this browser has turned off.";
    return;
  }
  const canvas = document.getElementById("scene");
  const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
  let reduced = reducedQuery.matches;
  const tier = pickTier();
  const tokens = readTokens();
  document.fonts?.load("600 40px Fraunces");
  document.fonts?.load("500 20px Saira");
  const world = await createWorld({ canvas, tier, tokens, seed: config.seed, include, reduced });
  const dive = createDive(world, config.airSeconds);
  const synth = createSynth();
  const rng = createRng(`${config.seed}:attract`);
  const shape = world.shape;
  const rig = world.rig;
  const accent = getComputedStyle(document.documentElement).getPropertyValue("--world-glow").trim() || "#4ce8ff";

  const game = {
    screen: "surface",
    paused: false,
    slowmo: 1,
    slowmoTarget: 1,
    flash: 0,
    breath: 0,
    surfaceGlow: 0,
    surfaceFade: 0,
    worldTime: 0,
    roll: [],
    spotted: new Set(),
    shot: new Map(),
    spotTimer: 0,
    vfTimer: 0,
    armedUntil: 0,
    attract: { pos: new THREE.Vector3(), yaw: 0, sink: null },
    muted: false,
  };
  const shutter = { down: false, open: false, openedAt: 0, busy: false };
  const frame = {
    sub: { pos: new THREE.Vector3(), yaw: 0, pitch: 0, roll: 0 },
    thrust: 0, lampsOn: true, wobble: 1, flash: 0, breath: 0, surfaceGlow: 0, surfaceFade: 0, focusDist: 10,
  };

  // The opening view: sunlit shallows with the manta, the school, and the whale for the light scheme, which then sinks
  // to the lichen-lit trench wall and the jellies below; the glowing jelly band for the dark one. The sub hangs in the
  // middle with its lamps on.
  function setupAttract() {
    game.attract.sink = null;
    const dark = isDark();
    const c = new THREE.Vector2();
    const school = world.creatures.get("school");
    const jellies = world.creatures.get("jellyfish");
    const whale = world.creatures.get("whale");
    if (dark) {
      const d = 124;
      shape.center(d, c);
      const center = new THREE.Vector3(c.x, -d, c.y);
      game.attract.pos.copy(center);
      game.attract.yaw = 1.15;
      jellies?.gatherAround(center.clone().add(new THREE.Vector3(0, 1.2, 0)), rng);
      Object.assign(rig.state.attract, { center: center.clone().add(new THREE.Vector3(0, 0.8, 0)), radius: 12, height: 1.4, speed: 0.05, angle: 0.5, tilt: 1.4 });
    } else {
      const d = 34;
      shape.center(d, c);
      const center = new THREE.Vector3(c.x, -d, c.y);
      game.attract.pos.copy(center);
      game.attract.yaw = -0.6;
      school?.setCenter(center.clone().add(new THREE.Vector3(7, 4, -8)));
      whale?.setPhase(-Math.PI / 2 - 0.42);
      Object.assign(rig.state.attract, { center: center.clone().add(new THREE.Vector3(0, 1, 0)), radius: 13.5, height: -2.4, speed: 0.035, angle: 0, tilt: 3.2 });
      if (!reduced) {
        // The sink: a beat in the sun, then down to where the wall stands about sixteen meters behind the sub.
        const deep = 160;
        shape.center(deep, c);
        const away = 0.3;
        const back = new THREE.Vector3(-Math.sin(away), 0, -Math.cos(away));
        const to = new THREE.Vector3(c.x, -deep, c.y).addScaledVector(back, shape.radius(deep) - 16);
        // The jellies gather off to the camera's right of the sub, so they frame it instead of hiding it.
        const right = new THREE.Vector3(Math.cos(away), 0, -Math.sin(away));
        jellies?.gatherAround(to.clone().addScaledVector(back, 4).addScaledVector(right, 11).add(new THREE.Vector3(0, 2.5, 0)), rng);
        game.attract.sink = { from: center, to, start: game.worldTime + 1.9, end: game.worldTime + 7.2, height: [-2.4, 1.2], tilt: [3.2, 1.2] };
      }
    }
    rig.setMode("attract", true);
  }
  setupAttract();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (game.screen !== "dive") setupAttract();
  });
  reducedQuery.addEventListener("change", (e) => (reduced = e.matches));

  const input = createInput({
    canvas,
    els: hud.els,
    on: {
      inDive: () => game.screen === "dive" && !game.paused,
      unlock: () => synth.unlock(),
      shutterDown,
      shutterUp,
      pause: () => setPaused(true),
    },
  });

  // Surface screen and results.
  hud.els.diveStart.disabled = false;
  hud.els.diveStart.addEventListener("click", startDive);
  hud.els.again.addEventListener("click", startDive);
  hud.els.pauseBtn.addEventListener("click", () => setPaused(true));
  hud.els.resume.addEventListener("click", () => setPaused(false));
  hud.els.end.addEventListener("click", () => {
    setPaused(false);
    surfaceNow(false);
  });
  hud.els.soundBtn.addEventListener("click", () => {
    game.muted = !game.muted;
    synth.setMuted(game.muted);
    hud.els.soundBtn.setAttribute("aria-pressed", String(game.muted));
    hud.els.soundBtn.setAttribute("aria-label", game.muted ? "Sound on" : "Sound off");
  });
  hud.els.surfaceBtn.addEventListener("click", () => {
    if (performance.now() < game.armedUntil) {
      game.armedUntil = 0;
      hud.armSurface(false);
      surfaceNow(false);
    } else {
      game.armedUntil = performance.now() + 3000;
      hud.armSurface(true);
      setTimeout(() => {
        if (game.armedUntil && performance.now() >= game.armedUntil) hud.armSurface(false);
      }, 3100);
    }
  });
  hud.els.roll.addEventListener("click", (e) => {
    const open = e.target.closest("[data-i]");
    const save = e.target.closest("[data-save]");
    if (open) {
      viewing = game.roll[Number(open.dataset.i)];
      hud.openViewer(viewing);
    } else if (save) {
      savePhoto(game.roll[Number(save.dataset.save)]);
    }
  });
  let viewing = null;
  hud.els.viewerSave.addEventListener("click", () => viewing && savePhoto(viewing));
  hud.els.viewerClose.addEventListener("click", () => hud.els.viewer.close());

  async function startDive() {
    if (game.screen === "dive") return;
    synth.unlock();
    hud.veil(true);
    await wait(reduced ? 0 : 420);
    world.creatures.get("school")?.setCenter(null);
    dive.start(0);
    for (const p of game.roll) URL.revokeObjectURL(p.url);
    game.roll = [];
    game.spotted = new Set();
    game.shot = new Map();
    game.breath = game.surfaceGlow = game.surfaceFade = 0;
    game.paused = false;
    rig.state.lookYaw = rig.state.lookPitch = 0;
    rig.setMode("follow", true);
    hud.resetDive(log);
    hud.show("dive");
    document.activeElement?.blur?.();
    game.screen = "dive";
    synth.startDive();
    hud.keysHint(true);
    setTimeout(() => hud.keysHint(false), 6500);
    hud.veil(false);
    hud.banner("Hold the dive button to go down. The creatures live in depth bands.", false, 4200);
  }

  function setPaused(p) {
    if (game.screen !== "dive" || game.paused === p) return;
    game.paused = p;
    input.releaseAll();
    if (p) closeViewfinder();
    hud.setPaused(p);
  }

  function surfaceNow(forced) {
    if (game.screen !== "dive") return;
    if (dive.beginAscent(forced)) {
      closeViewfinder();
      synth.play("blow", { gain: 0.7 });
      hud.banner(forced ? "Air reserve reached. Surfacing now." : "Blowing ballast. Surfacing.", forced, 3200);
    }
  }

  function shutterDown() {
    if (game.screen !== "dive" || game.paused || shutter.busy) return;
    shutter.down = true;
    openViewfinder();
  }
  function shutterUp() {
    if (!shutter.down) return;
    shutter.down = false;
    shutter.busy = true;
    const settle = reduced ? 140 : 380;
    setTimeout(takePhoto, Math.max(0, settle - (performance.now() - shutter.openedAt)));
  }
  function openViewfinder() {
    if (shutter.open) return;
    shutter.open = true;
    shutter.openedAt = performance.now();
    game.slowmoTarget = reduced ? 1 : 0.3;
    hud.viewfinder(true);
  }
  function closeViewfinder() {
    shutter.open = false;
    shutter.down = false;
    game.slowmoTarget = 1;
    hud.viewfinder(false);
  }

  async function takePhoto() {
    if (game.screen !== "dive") {
      shutter.busy = false;
      return;
    }
    const info = evaluate(world, true);
    const depth = Math.round(dive.depth());
    const now = new Date();
    const dateText = `${now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}, ${now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
    frame.flash = 0;
    world.update(0, game.worldTime, frameFor(0));
    const canvasOut = composeFrame(world, info, { depth, dateText, diver: config.diverName, title: config.title, accent });
    synth.play("shutter", { gain: 0.8 });
    game.flash = reduced ? 0.25 : 0.9;
    setTimeout(closeViewfinder, 260);
    let blob;
    try {
      blob = await toPng(canvasOut);
    } catch {
      shutter.busy = false;
      hud.banner("That photo could not be saved.", true);
      return;
    }
    const thumb = thumbnail(canvasOut);
    const slug = (info ? info.name : "open water").toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const photo = {
      species: info ? info.species : null,
      name: info ? info.name : "Open water",
      stars: info ? info.stars : 0,
      depth,
      blob,
      bytes: blob.size,
      url: URL.createObjectURL(blob),
      thumb,
      date: now.toISOString(),
      dateText,
      filename: `abyss-drift-${slug}-${now.toISOString().slice(0, 10)}.png`,
      w: canvasOut.width,
      h: canvasOut.height,
    };
    game.roll.push(photo);
    if (info) {
      const prev = game.shot.get(info.species) || 0;
      if (info.stars > prev) game.shot.set(info.species, info.stars);
      game.spotted.add(info.species);
      hud.markPhoto(info.species, thumb, Math.max(prev, info.stars));
      recordPhoto(log, photo);
      if (!prev) synth.play("chime", { gain: 0.45 });
      const verdict = info.stars === 3 ? "a three-star frame" : info.stars === 2 ? "two stars: light it for three" : "one star: center it and get closer";
      hud.banner(`${info.name}, ${verdict}.`, false, 2600);
    } else {
      hud.banner("Open water. Center a creature in the frame.", false, 2200);
    }
    shutter.busy = false;
  }

  async function finishDive() {
    game.screen = "results";
    closeViewfinder();
    input.releaseAll();
    synth.endDive();
    hud.veil(true);
    await wait(reduced ? 0 : 420);
    game.breath = game.surfaceGlow = game.surfaceFade = 0;
    const stars = [...game.shot.values()].reduce((a, b) => a + b, 0);
    const isBest = recordDive(log, { species: game.shot.size, stars, depth: Math.round(dive.st.maxDepth), photos: game.roll.length, date: new Date().toISOString() });
    const lede = game.shot.size === hud.total
      ? `Every species in one dive. The log is complete.`
      : `${game.shot.size} of ${hud.total} species photographed${isBest && game.shot.size ? ". Your best dive yet." : "."}`;
    hud.showResults({ lede, photos: game.roll, stars, logged: Object.keys(log.species).filter((k) => include.has(k)).length, depth: Math.round(dive.st.maxDepth) });
    hud.renderSurface(log);
    hud.show("results");
    setupAttract();
    hud.veil(false);
  }

  function frameFor(dt) {
    if (game.screen === "dive") {
      frame.sub.pos.copy(dive.sub.pos);
      frame.sub.yaw = dive.sub.yaw;
      frame.sub.pitch = dive.sub.pitch;
      frame.sub.roll = dive.sub.roll;
      frame.thrust = input.intent.thrust + input.intent.descend * 0.5;
      frame.focusDist = shutter.open ? viewfinderFocus() : rig.camera.position.distanceTo(dive.sub.pos);
    } else {
      const a = game.attract;
      const t = game.worldTime;
      if (a.sink) {
        const s = a.sink;
        const x = Math.min(1, Math.max(0, (t - s.start) / (s.end - s.start)));
        const k = x * x * (3 - 2 * x);
        const ra = rig.state.attract;
        a.pos.lerpVectors(s.from, s.to, k);
        ra.center.copy(a.pos).y += 1;
        ra.height = s.height[0] + (s.height[1] - s.height[0]) * k;
        ra.tilt = s.tilt[0] + (s.tilt[1] - s.tilt[0]) * k;
        // The camera rides the sink exactly, so the sub holds its place in the frame.
        if (x > 0) rig.state.snap = true;
        if (x >= 1) a.sink = null;
      }
      frame.sub.pos.copy(a.pos);
      frame.sub.pos.y += Math.sin(t * 0.8) * (reduced ? 0 : 0.18);
      frame.sub.yaw = a.yaw + Math.sin(t * 0.13) * 0.25;
      frame.sub.pitch = Math.sin(t * 0.5) * 0.03;
      frame.sub.roll = Math.sin(t * 0.37) * 0.04;
      frame.thrust = 0.15;
      frame.focusDist = rig.camera.position.distanceTo(a.pos);
    }
    frame.lampsOn = true;
    frame.wobble = 1;
    frame.flash = game.flash;
    frame.breath = game.breath;
    frame.surfaceGlow = game.surfaceGlow;
    frame.surfaceFade = game.surfaceFade;
    void dt;
    return frame;
  }

  // Where the surface or results sheet sits, so the opening view centers in the open water beside or above it.
  function updateInset() {
    if (game.screen === "dive") {
      rig.setInset(0, 0);
      return;
    }
    const sheet = (game.screen === "results" ? hud.els.results : hud.els.surface).querySelector(".sheet");
    const r = sheet.getBoundingClientRect();
    const wide = r.width < innerWidth * 0.75;
    rig.setInset(wide ? r.right : 0, wide ? 0 : Math.max(0, innerHeight - r.top));
  }

  let lastInfo = null;
  function viewfinderFocus() {
    return lastInfo ? lastInfo.dist : 12;
  }

  // Fixed-step rules.
  function step(dt) {
    if (game.screen !== "dive" || game.paused) return;
    const intent = input.poll(dt);
    rig.state.lookYaw = intent.lookYaw;
    rig.state.lookPitch = intent.lookPitch;
    const gdt = dt * game.slowmo;
    const events = dive.step(gdt, intent);
    for (const ev of events) {
      if (ev === "reserve") {
        closeViewfinder();
        synth.play("blow", { gain: 0.7 });
        hud.banner("Air reserve reached. Surfacing now.", true, 3600);
      } else if (ev === "surfaced") {
        finishDive();
        return;
      }
    }
    const depth = dive.depth();
    if (dive.st.ascending) {
      const remain = depth / MOTION.ascent;
      game.breath = Math.min(1, Math.max(0, (20 - remain) / 6)) * (1 - Math.min(1, Math.max(0, (2 - remain) / 2)));
      game.surfaceGlow = Math.max(0, 1 - depth / 80);
      game.surfaceFade = Math.max(0, 1 - depth / 7);
    }
    rig.setMode(shutter.open ? "viewfinder" : dive.st.ascending ? "ascent" : "follow");
  }

  // Per-frame: spotting, sonar, HUD, then the world.
  const loop = createLoop({
    renderer: world.renderer,
    update: step,
    render(dt) {
      game.slowmo += (game.slowmoTarget - game.slowmo) * (1 - Math.exp(-dt * 10));
      game.flash *= Math.exp(-dt * 7);
      const wdt = Math.min(dt, 0.05) * (game.screen === "dive" && game.paused ? 0 : game.slowmo);
      game.worldTime += wdt;
      updateInset();
      world.update(wdt, game.worldTime, frameFor(wdt));
      if (game.screen === "dive") perFrameDive(dt);
      world.render(dt);
    },
    onFrame: (ms) => governor.sample(ms),
  });
  const governor = createGovernor(tier, () => world.applyTier());

  function perFrameDive(dt) {
    const depth = dive.depth();
    hud.update({ depth, air: dive.st.air, airTotal: dive.st.airTotal, reserve: dive.reserve(), reach: dive.reach(), breath: game.breath });
    if (shutter.open) {
      game.vfTimer -= dt;
      if (game.vfTimer <= 0) {
        lastInfo = evaluate(world, true);
        hud.viewfinder(true, lastInfo && lastInfo.stars === 3, lastInfo ? `${lastInfo.name}, ${Math.round(lastInfo.dist)} m` : "");
        game.vfTimer = 0.1;
      }
    }
    game.spotTimer -= dt;
    let nearest = Infinity;
    let whaleNear = false;
    if (game.spotTimer <= 0) {
      game.spotTimer = 0.25;
      const cam = world.camera;
      cam.updateMatrixWorld();
      const p = new THREE.Vector3();
      for (const c of world.creatures.list) {
        if (!c.active) continue;
        const sp = SPECIES_BY_ID[c.id];
        for (const tg of c.targets) {
          const ds = tg.pos.distanceTo(dive.sub.pos);
          if (!game.shot.has(c.id)) nearest = Math.min(nearest, ds);
          if (c.id === "whale" && ds < 70) whaleNear = true;
          if (game.spotted.has(c.id)) continue;
          const dc = tg.pos.distanceTo(cam.position);
          if (dc > sp.maxDist * 1.2) continue;
          p.copy(tg.pos).project(cam);
          if (p.z > 1 || Math.abs(p.x) > 1 || Math.abs(p.y) > 1) continue;
          game.spotted.add(c.id);
          hud.markSpotted(c.id);
          hud.banner(`${sp.name} spotted. Frame it and press the shutter.`, false, 2600);
          synth.play("ping", { gain: 0.4, rate: 1.25 });
        }
      }
      game.nearest = nearest;
      game.whaleNear = whaleNear;
    }
    synth.update({
      dt, thrust: input.intent.thrust, descend: input.intent.descend, depth,
      nearest: game.nearest ?? Infinity, airLow: dive.st.air <= dive.reserve() + 8 && !dive.st.ascending,
      breath: game.breath, whaleNear: game.whaleNear, paused: game.paused,
    });
  }

  // A turn of the phone pauses the dive so the new layout settles first; a toolbar sliding away does not.
  let landscape = innerWidth > innerHeight;
  addEventListener("resize", () => {
    world.resize();
    const now = innerWidth > innerHeight;
    if (now !== landscape && game.screen === "dive" && !game.paused) setPaused(true);
    landscape = now;
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && game.screen === "dive" && !game.paused) setPaused(true);
  });
  loop.start();

  // A read-only view of the dive for checks run from the browser's console or an automated browser.
  window.abyssDrift = {
    tier: tier.name,
    state: () => ({
      screen: game.screen,
      depth: Math.round(dive.depth()),
      air: Math.round(dive.st.air),
      spotted: [...game.spotted],
      photographed: Object.fromEntries(game.shot),
      photos: game.roll.map((p) => ({ species: p.species, stars: p.stars, bytes: p.bytes })),
    }),
  };
  installTour(world, game, rig);
}

// Moves the opening view to a species, for looking at each one in turn. Only with ?tour in the address.
function installTour(world, game, rig) {
  if (!new URLSearchParams(location.search).has("tour")) return;
  window.abyssDrift.world = world;
  window.abyssDrift.tour = (id, radius = 14, angle = 0.3) => {
    const c = world.creatures.get(id);
    if (!c) return false;
    const mid = (c.species.band[0] + c.species.band[1]) / 2;
    const far = new THREE.Vector3(0, -mid, 0);
    for (let i = 0; i < 3; i++) world.creatures.update(0.016, game.worldTime, { camPos: far, camDepth: mid, subPos: far, subFwd: new THREE.Vector3(0, 0, 1), lampOn: true });
    const p = c.targets[0].pos.clone();
    game.attract.pos.copy(p).add(new THREE.Vector3(0, 1, radius + 10));
    Object.assign(rig.state.attract, { center: p, radius, height: 1, speed: 0.04, angle, tilt: 0 });
    rig.setMode("attract", true);
    return true;
  };
}

function readConfig() {
  const raw = window.__APP_CONFIG__ || {};
  const all = SPECIES.map((s) => s.id);
  const text = (v, d) => (typeof v === "string" && v.trim() ? v.trim().slice(0, 60) : d);
  let species = all;
  if (Array.isArray(raw.species)) species = raw.species.filter((id) => all.includes(id));
  if (!species.length) species = all;
  const air = Math.round(Number(raw.airSeconds));
  return {
    title: text(raw.title, "Abyss Drift"),
    diverName: text(raw.diverName, "Diver"),
    seed: text(raw.seed, "abyss"),
    airSeconds: Number.isFinite(air) && air > 0 ? Math.min(600, Math.max(45, air)) : 120,
    species,
  };
}

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
