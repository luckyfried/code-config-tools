// Tiny Tornado: the screens, the storm's motion, the run's clock and score, the attract storm behind the title, and
// the wiring between the world, the lift rules, input, the HUD, and sound.
import * as THREE from "three";
import WebGL from "three/addons/capabilities/WebGL.js";
import { readTokens } from "../scene/tokens.js";
import { createAdaptive, pickTier, tierSettings } from "../scene/quality.js";
import { createWorld } from "../scene/world.js";
import { generateTown, TOWN_EDGE } from "./generation.js";
import { createLift, levelFor, growthFor, LEVEL_MASS } from "./lift.js";
import { createTally, massText, numberWord, listWords } from "./scoring.js";
import { createInput } from "./input.js";
import { createHud } from "./hud.js";
import { createLoop } from "./loop.js";
import { createAudio } from "../audio/synth.js";

const DEFAULTS = { title: "Tiny Tornado", playerName: "You", townName: "Millbrook", theme: "plains", seed: "", runSeconds: 60 };
const config = { ...DEFAULTS, ...(window.__APP_CONFIG__ || {}) };
const townName = String(config.townName || DEFAULTS.townName);
const seed = String(config.seed || townName);
const runSeconds = Math.max(15, Math.min(600, Number(config.runSeconds) || DEFAULTS.runSeconds));
const STORE = "tiny-tornado";
const LEVEL_TOASTS = ["", "", "Level 2: cows and trees lift now", "Level 3: cars and trucks lift now", "Level 4: barns, houses, and silos lift now"];
const PULSE_COOLDOWN = 4;
const ATTRACT_RESET = 40;

const $ = (id) => document.getElementById(id);
const screens = { title: $("screen-title"), pause: $("screen-pause"), report: $("screen-report") };
const hudRoot = $("hud");
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const touch = matchMedia("(pointer: coarse)").matches;

function loadStore() {
  try {
    const value = JSON.parse(localStorage.getItem(STORE) || "{}");
    return { best: value.best && typeof value.best === "object" ? value.best : {}, sound: value.sound !== false };
  } catch {
    return { best: {}, sound: true };
  }
}
function saveStore(store) {
  try {
    localStorage.setItem(STORE, JSON.stringify(store));
  } catch {
    // A browser with storage turned off still plays; the best simply is not kept.
  }
}

function setScreen(name) {
  document.body.dataset.screen = name;
  screens.title.inert = !(name === "title" || name === "loading");
  screens.pause.inert = name !== "pause";
  screens.report.inert = name !== "report";
  hudRoot.inert = name !== "run";
}

function inTownText(town) {
  const count = (types) => town.props.filter((p) => types.includes(p.type)).length;
  const parts = [
    [count(["cow"]), "cow", "cows"],
    [count(["barn"]), "barn", "barns"],
    [count(["house", "houseB"]), "house", "houses"],
  ].map(([n, one, many]) => `${numberWord(n)} ${n === 1 ? one : many}`);
  const text = listWords(parts);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function failToStart() {
  setScreen("title");
  $("title-lede").textContent = "This browser could not start 3D graphics, so the storm can't be drawn here. A current Chrome, Edge, Firefox, or Safari can draw it.";
  $("start-label").textContent = "3D graphics are off";
  $("title-controls").textContent = "";
}

function boot() {
  const store = loadStore();
  document.title = `${config.title}: ${townName}`;
  $("title-app").textContent = config.title;
  $("town-name").textContent = townName;
  $("title-lede").textContent = `${numberWord(runSeconds).replace(/^./, (c) => c.toUpperCase())} seconds of storm over ${townName}. Lift fences and hay first, then cows and cars, and grow big enough to take the barns.`;
  const best = Number(store.best[townName]) || 0;
  $("best-mass").textContent = best > 0 ? `${massText(best)} tons` : "None yet";
  $("title-controls").textContent = touch
    ? "Drag anywhere to steer the storm."
    : "Steer with WASD, the arrow keys, or a drag. Space sends a pulse.";
  document.body.classList.toggle("is-touch", touch);
  setScreen("loading");
  if (!WebGL.isWebGL2Available()) {
    failToStart();
    return;
  }

  const town = generateTown(seed);
  $("in-town").textContent = inTownText(town);
  const settings = tierSettings(pickTier());
  let reduced = reducedQuery.matches;
  let tokens = readTokens();
  let world;
  try {
    world = createWorld($("scene"), settings, tokens, { town, townName, seed, reducedMotion: reduced });
  } catch (error) {
    console.warn(error);
    failToStart();
    return;
  }
  const audio = createAudio();
  audio.setEnabled(store.sound);
  const tally = createTally();
  const hud = createHud();
  const adaptive = createAdaptive(settings, (q) => world.applyQuality(q));

  const storm = {
    pos: new THREE.Vector3(),
    vel: new THREE.Vector3(),
    lean: new THREE.Vector2(),
    mass: 0,
    level: 1,
    growth: 0,
    pulse: 0,
    pulseR: -100,
    cooldown: 0,
  };
  let screen = "loading";
  let clock = 0;
  let timeLeft = runSeconds;
  let attractTime = 0;
  let nextStrike = 0.9;
  let offsetBlend = 1;
  let runTime = 0;
  let lastImpact = 0;
  let toastTimer = 0;

  const lift = createLift({
    town,
    meshes: world.meshes,
    funnel: world.funnel,
    sparks: world.sparks,
    events: {
      lifted(it) {
        storm.mass += it.kind.mass;
        if (screen === "run") tally.add(it.type);
        if (it.type === "cow") audio.moo();
        if (it.type === "barn" || it.type === "house" || it.type === "houseB") {
          audio.splinter();
          world.rig.addTrauma(0.45);
        }
      },
      landed(it) {
        if (clock - lastImpact < 0.08) return;
        lastImpact = clock;
        audio.impact(it.kind.mass);
        if (it.kind.mass >= 1) world.rig.addTrauma(Math.min(0.3, it.kind.mass * 0.05));
      },
    },
  });
  lift.setPlankColors(tokens);

  const input = createInput(document.body, {
    onPulse: pulse,
    onPause: () => {
      if (screen === "run") pause();
      else if (screen === "pause") resume();
    },
    active: () => screen === "run",
  });

  function pulse() {
    if (screen !== "run" || storm.cooldown > 0) return;
    storm.pulse = 1;
    storm.pulseR = 0;
    storm.cooldown = PULSE_COOLDOWN;
    audio.pulse();
    world.rig.addTrauma(0.3);
  }

  function placeStorm(at) {
    storm.pos.set(at.x, 0, at.z);
    storm.vel.set(0, 0, 0);
    storm.lean.set(0, 0);
    world.rig.snap();
  }

  function startAttract() {
    lift.reset();
    placeStorm(town.attractStart);
    storm.mass = 4;
    storm.level = levelFor(storm.mass);
    storm.growth = growthFor(storm.mass);
    attractTime = 0;
    nextStrike = 0.9;
  }

  function strike(near) {
    const ahead = new THREE.Vector3(storm.pos.x + (Math.random() - 0.5) * 50, 0, storm.pos.z - 14 - Math.random() * 34);
    world.sky.strike(ahead, world.camera.position);
    world.rig.addTrauma(near ? 0.28 : 0.15);
    audio.thunder(near ? 1 : 0.6);
  }

  function toast(text) {
    hud.toast(text);
    toastTimer = 2.4;
  }

  // Auto-steering for the title and report: head for the best thing this storm can lift.
  const aim = new THREE.Vector3();
  const keyDir = { x: 0, z: 0 };
  const push = { x: 0, z: 0 };
  function steerAuto(dt) {
    const target = lift.nearest(storm.pos, storm.level, 70);
    if (target) aim.set(target.x - storm.pos.x, 0, target.z - storm.pos.z);
    else aim.set(-storm.pos.x, 0, -storm.pos.z);
    const d = aim.length() || 1;
    aim.multiplyScalar(1 / d);
    const want = Math.min(7 + storm.growth * 4, d * 1.4);
    storm.vel.x += (aim.x * want - storm.vel.x) * Math.min(1, dt * 1.6);
    storm.vel.z += (aim.z * want - storm.vel.z) * Math.min(1, dt * 1.6);
  }

  function steerPlayer(dt) {
    input.keyDir(keyDir);
    input.takePush(push);
    const accel = 26 + storm.growth * 8;
    storm.vel.x += keyDir.x * accel * dt + push.x * 2.4;
    storm.vel.z += keyDir.z * accel * dt + push.z * 2.4;
    const damp = keyDir.x || keyDir.z || input.dragging ? 1.6 : 0.9;
    storm.vel.multiplyScalar(Math.exp(-dt * damp));
  }

  function step(dt) {
    clock += dt;
    if (screen === "pause") return;
    const auto = screen !== "run";
    if (auto) {
      attractTime += dt;
      if (screen !== "report") storm.mass += dt * 2.6;
      if (screen !== "report" && attractTime > ATTRACT_RESET) startAttract();
      steerAuto(dt);
    } else steerPlayer(dt);

    const maxSpeed = 11 + storm.growth * 6;
    const speed = Math.hypot(storm.vel.x, storm.vel.z);
    if (speed > maxSpeed) storm.vel.multiplyScalar(maxSpeed / speed);
    storm.pos.x += storm.vel.x * dt;
    storm.pos.z += storm.vel.z * dt;
    const edge = TOWN_EDGE - 6;
    if (Math.abs(storm.pos.x) > edge) {
      storm.pos.x = Math.sign(storm.pos.x) * edge;
      storm.vel.x *= -0.4;
    }
    if (Math.abs(storm.pos.z) > edge) {
      storm.pos.z = Math.sign(storm.pos.z) * edge;
      storm.vel.z *= -0.4;
    }
    storm.lean.x += (-storm.vel.x * 0.06 - storm.lean.x) * Math.min(1, dt * 2);
    storm.lean.y += (-storm.vel.z * 0.06 - storm.lean.y) * Math.min(1, dt * 2);

    const level = levelFor(storm.mass);
    if (level > storm.level && screen === "run") {
      toast(LEVEL_TOASTS[level]);
      world.rig.addTrauma(0.25);
    }
    storm.level = level;
    storm.growth += (growthFor(storm.mass) - storm.growth) * Math.min(1, dt * 1.4);
    storm.pulse = Math.max(0, storm.pulse - dt / 0.8);
    storm.cooldown = Math.max(0, storm.cooldown - dt);
    storm.pulseR = storm.pulseR >= 0 && storm.pulseR < 60 ? storm.pulseR + dt * 38 : -100;

    lift.drive(dt);
    lift.grab(clock, storm.level, world.funnel.reach);
    lift.update(dt, storm.pulse);

    nextStrike -= dt;
    if (nextStrike <= 0) {
      strike(screen === "run");
      nextStrike = 2 + Math.random() * 2.2 + (screen === "run" ? 1.2 : 0);
    }

    if (screen === "run") {
      runTime += dt;
      timeLeft = Math.max(0, timeLeft - dt);
      if (runTime > 4.5) hud.hideHint();
      if (timeLeft <= 0) finish();
    }
    if (toastTimer > 0) {
      toastTimer -= dt;
      if (toastTimer <= 0) hud.hideToast();
    }
  }

  const frameState = { pos: storm.pos, growth: 0, lean: storm.lean, pulse: 0, pulseR: -100, offsetBlend: 1, reduced, shakeBase: 0, velocity: storm.vel };
  function render(dt, ms) {
    adaptive.frame(ms);
    const wantOffset = screen === "run" || screen === "pause" ? 0 : 1;
    offsetBlend += (wantOffset - offsetBlend) * Math.min(1, dt * (reduced ? 20 : 2.5));
    frameState.growth = storm.growth;
    frameState.pulse = storm.pulse;
    frameState.pulseR = storm.pulseR;
    frameState.offsetBlend = offsetBlend;
    frameState.reduced = reduced;
    frameState.shakeBase = screen === "pause" ? 0 : 0.04 + storm.growth * 0.12;
    lift.flush();
    world.frame(dt, clock, frameState);
    hud.flash(world.sky.flash);
    if (screen === "run") {
      const level = storm.level;
      const lo = LEVEL_MASS[level - 1];
      const hi = LEVEL_MASS[level] ?? lo;
      hud.update({
        mass: storm.mass,
        level,
        fill: hi > lo ? (storm.mass - lo) / (hi - lo) : 1,
        timeLeft,
        ready: 1 - storm.cooldown / PULSE_COOLDOWN,
      });
      const speed = Math.min(1, Math.hypot(storm.vel.x, storm.vel.z) / 14);
      audio.roar(speed, storm.growth, 1);
    } else {
      audio.roar(0.3, storm.growth, screen === "report" ? 0.5 : 0);
    }
  }

  function measureShift() {
    const card = screen === "report" ? $("report-card") : $("title-card");
    const rect = card.getBoundingClientRect();
    const w = window.innerWidth;
    const h = window.innerHeight;
    if (rect.width > w * 0.8) world.rig.setShift(0, Math.max(0, (h - rect.top) / 2 - 10));
    else world.rig.setShift(Math.max(0, rect.right / 2), 0);
  }

  function startRun() {
    audio.start();
    lift.reset();
    tally.clear();
    placeStorm(town.playStart);
    storm.mass = 0;
    storm.level = 1;
    storm.growth = 0;
    storm.cooldown = 0;
    timeLeft = runSeconds;
    runTime = 0;
    nextStrike = 2.5;
    input.clear();
    hud.reset(touch ? "Drag anywhere to steer into the fences" : "Steer into the fences with WASD or the arrow keys");
    screen = "run";
    setScreen("run");
  }

  function finish() {
    screen = "report";
    const mass = storm.mass;
    const prior = Number(store.best[townName]) || 0;
    const isBest = mass > prior;
    if (isBest) {
      store.best[townName] = Math.round(mass * 10) / 10;
      saveStore(store);
    }
    $("report-eyebrow").textContent = `Damage report: ${townName}`;
    $("report-mass").textContent = massText(mass);
    const sentence = tally.sentence();
    const who = String(config.playerName || "You");
    const owner = who.toLowerCase() === "you" ? "Your" : `${who}'s`;
    $("report-text").textContent = sentence
      ? `${owner} tornado lifted ${sentence}.`
      : `${owner} tornado lifted nothing at all. Steer into a fence to get it started.`;
    const best = Math.max(prior, mass);
    $("report-best").textContent = isBest && mass > 0 ? `New best for ${townName}` : `Best for ${townName}: ${massText(best)} tons`;
    $("report-best").classList.toggle("is-new", isBest && mass > 0);
    const list = $("tally");
    list.replaceChildren(
      ...tally.rows().map(({ label, n }) => {
        const li = document.createElement("li");
        const b = document.createElement("b");
        b.textContent = String(n);
        li.append(b, label);
        return li;
      }),
    );
    $("best-mass").textContent = `${massText(best)} tons`;
    attractTime = 0;
    setScreen("report");
    measureShift();
    $("again-button").focus({ preventScroll: true });
  }

  function pause() {
    screen = "pause";
    setScreen("pause");
    $("resume-button").focus({ preventScroll: true });
  }
  function resume() {
    screen = "run";
    setScreen("run");
  }
  function toTitle() {
    screen = "title";
    startAttract();
    setScreen("title");
    measureShift();
  }

  $("start-button").addEventListener("click", startRun);
  $("again-button").addEventListener("click", startRun);
  $("title-button").addEventListener("click", toTitle);
  $("pause-button").addEventListener("click", pause);
  $("resume-button").addEventListener("click", resume);
  $("quit-button").addEventListener("click", toTitle);
  $("pulse-button").addEventListener("click", pulse);
  const soundButton = $("sound-button");
  const showSound = () => {
    soundButton.textContent = audio.enabled ? "Sound on" : "Sound off";
    soundButton.setAttribute("aria-pressed", String(audio.enabled));
  };
  showSound();
  soundButton.addEventListener("click", () => {
    audio.setEnabled(!audio.enabled);
    store.sound = audio.enabled;
    saveStore(store);
    showSound();
  });

  window.addEventListener("resize", () => {
    world.resize();
    measureShift();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && screen === "run") pause();
  });
  darkQuery.addEventListener("change", () => {
    tokens = readTokens();
    world.applyTokens(tokens);
    lift.setPlankColors(tokens);
  });
  reducedQuery.addEventListener("change", () => {
    reduced = reducedQuery.matches;
  });

  // The storm is already turning when the first frame is drawn: two seconds of it run before anything is shown.
  startAttract();
  nextStrike = 99;
  for (let i = 0; i < 120; i++) step(1 / 60);
  nextStrike = 0.9;
  screen = "title";
  setScreen("title");
  measureShift();
  const loop = createLoop({ step, render });
  const ready = () => {
    loop.start();
    $("start-button").disabled = false;
    $("start-label").textContent = "Start the storm";
  };
  world.warm().then(ready, ready);
}

boot();
