// Tiny Planet: the screens, the run, and the wiring between the world, the walker, the input, the HUD, and sound.
import * as THREE from "three";
import WebGL from "three/addons/capabilities/WebGL.js";
import { readTokens } from "../scene/tokens.js";
import { createAdaptive, pickTier, tierSettings } from "../scene/quality.js";
import { createWorld } from "../scene/world.js";
import { createWalker } from "./walking.js";
import { createInput } from "./input.js";
import { createAttract, filmDive } from "./attract.js";
import { createHud, clockText } from "./hud.js";
import { createLoop } from "./loop.js";
import { createAudio } from "../audio/synth.js";

const DEFAULTS = {
  title: "Tiny Planet",
  planetName: "Pebble",
  playerName: "Explorer",
  theme: "meadow",
  seed: "pebble",
  daySeconds: 120,
  crystals: 7,
};
const config = { ...DEFAULTS, ...(window.__APP_CONFIG__ || {}) };
const total = Math.max(1, Math.min(24, Math.round(Number(config.crystals) || DEFAULTS.crystals)));
const daySeconds = Math.max(20, Number(config.daySeconds) || DEFAULTS.daySeconds);
const seed = String(config.seed);

const SUN_NOON = 62;
const SUN_DROP = 98;
const COLLECT_RADIUS = 1.7;
const LATE_SECONDS = 20;
const BEST_KEY = `tiny-planet:best:${seed}`;

const $ = (id) => document.getElementById(id);
const screens = { title: $("screen-title"), pause: $("screen-pause"), result: $("screen-result") };
const hudRoot = $("hud");
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const darkQuery = matchMedia("(prefers-color-scheme: dark)");

const NUMBER_WORDS = [
  "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
  "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty", "Twenty-one",
  "Twenty-two", "Twenty-three", "Twenty-four",
];

function fillTitle() {
  document.title = `${config.title}: ${config.planetName}`;
  $("title-app").textContent = config.title;
  $("planet-name").textContent = config.planetName;
  $("seed-word").textContent = seed;
  // The seed word is shown only when it is not simply the planet's name.
  $("seed-row").classList.toggle("is-hidden", seed.trim().toLowerCase() === String(config.planetName).trim().toLowerCase());
  $("title-lede").textContent =
    total === 1
      ? `One crystal is hidden on ${config.planetName}. Find it before the sun goes down.`
      : `${NUMBER_WORDS[total]} crystals are hidden on ${config.planetName}. Find them all before the sun goes down.`;
  const best = Number(localStorage.getItem(BEST_KEY));
  $("best-time").textContent = best > 0 ? clockText(best) : "None yet";
}

function setControlsText(touch) {
  $("title-controls").textContent = touch
    ? "Drag on the left to walk, drag on the right to look around, and tap the right side to jump."
    : "WASD or the arrow keys to walk, Shift to run, Space to jump, and drag to look around.";
}

function setScreen(name) {
  document.body.dataset.screen = name;
  screens.title.inert = !(name === "title" || name === "loading");
  screens.pause.inert = name !== "pause";
  screens.result.inert = name !== "result";
  hudRoot.inert = name !== "run";
}

function failToStart() {
  setScreen("title");
  $("title-lede").textContent =
    "This browser could not start 3D graphics, so the planet can't be drawn here. A current Chrome, Edge, Firefox, or Safari can draw it.";
  $("start-label").textContent = "3D graphics are off";
  $("title-controls").textContent = "";
}

function boot() {
  fillTitle();
  setControlsText(matchMedia("(pointer: coarse)").matches);
  setScreen("loading");
  if (!WebGL.isWebGL2Available()) {
    failToStart();
    return;
  }

  const settings = tierSettings(pickTier());
  let world;
  try {
    world = createWorld($("scene"), settings, readTokens(), { seed, crystalCount: total });
  } catch (error) {
    console.warn(error);
    failToStart();
    return;
  }

  const walker = createWalker(world.terrain);
  const firstCrystal = world.crystals.items[0].dir;
  walker.reset(world.start, firstCrystal);
  const state = walker.state;
  const crystalTargets = world.crystals.items.map((item) => item.dir);
  const attract = createAttract([...crystalTargets.slice(1), crystalTargets[0]]);
  const hud = createHud(total);
  const audio = createAudio();
  const adaptive = createAdaptive(settings, (q) => world.applyQuality(q));

  let screen = "title";
  let reduced = reducedQuery.matches;
  let titlePhase = readTokens().numbers.worldTitlePhase;
  let phase = titlePhase;
  let blend = 1;
  let elapsed = 0;
  let found = 0;
  let hitstop = 0;
  let endTimer = -1;
  let time = 0;
  const prevPos = new THREE.Vector3().copy(state.pos);
  const drawPos = new THREE.Vector3();
  const gemPos = new THREE.Vector3();
  const flat = new THREE.Vector3();
  const right = new THREE.Vector3();
  let lit = { night: 0 };
  let filmTime = 0;
  const titleAz = new THREE.Vector3();
  const drawAz = new THREE.Vector3();
  const titleCard = screens.title.querySelector(".title-card");

  // The part of the screen the title card leaves clear: right of it on wide screens, above it on phones. The
  // planet is framed to fill a circle there.
  function fitFrame() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const card = titleCard.getBoundingClientRect();
    if (w >= 768 && w / h > 1) {
      const left = card.right;
      world.rig.setFrame({ cx: (left + w) / 2, cy: h / 2, radius: Math.min((w - left) / 2, h / 2) * 0.88 });
    } else {
      const bottom = Math.max(card.top, h * 0.35);
      world.rig.setFrame({ cx: w / 2, cy: bottom / 2, radius: Math.min(w / 2, bottom / 2) * 0.92 });
    }
  }
  new ResizeObserver(fitFrame).observe(titleCard);

  reducedQuery.addEventListener("change", (e) => (reduced = e.matches));
  darkQuery.addEventListener("change", () => (titlePhase = readTokens().numbers.worldTitlePhase));

  const input = createInput($("scene"), {
    stick: $("stick"),
    knob: $("stick-knob"),
    jumpButton: $("jump-button"),
    onPause: () => {
      if (screen === "run") pause(true);
      else if (screen === "pause") pause(false);
    },
  });

  function go(name) {
    if (name === "title" && screen !== "title") filmTime = 0;
    screen = name;
    setScreen(name);
    input.setEnabled(name === "run");
  }

  function startRun() {
    audio.start();
    walker.reset(world.start, firstCrystal);
    world.rig.snap();
    prevPos.copy(state.pos);
    world.crystals.reset();
    hud.reset();
    elapsed = 0;
    found = 0;
    endTimer = -1;
    hitstop = 0;
    go("run");
    hud.setFound(0);
    hud.setClock(daySeconds, false);
    setControlsText(input.touch);
    hud.hint(input.touch ? "Drag on the left to walk. Follow the beams of light." : "Follow the beams of light to the crystals.");
    $("scene").focus?.();
  }

  function pause(on) {
    if (on) {
      go("pause");
      audio.pause(true);
      $("resume-button").focus();
    } else {
      go("run");
      audio.pause(false);
    }
  }

  function finish(won) {
    go("result");
    const remaining = Math.max(0, daySeconds - elapsed);
    let stars;
    if (won) stars = elapsed <= daySeconds * 0.6 ? 3 : 2;
    else stars = found >= total / 2 ? 1 : 0;
    [...$("stars").children].forEach((star, i) => star.classList.toggle("is-on", i < stars));
    $("stars").setAttribute("aria-label", `${stars} of 3 stars`);
    $("result-crystals").textContent = `${found} of ${total}`;
    $("result-player").textContent = config.playerName;
    const best = $("result-best");
    if (won) {
      $("result-heading").textContent = "A planet saved";
      $("result-text").textContent = `${config.playerName} found every crystal on ${config.planetName} with ${clockText(remaining)} of daylight to spare.`;
      $("result-time").textContent = clockText(elapsed);
      const previous = Number(localStorage.getItem(BEST_KEY));
      if (!(previous > 0) || elapsed < previous) {
        localStorage.setItem(BEST_KEY, String(elapsed));
        best.textContent = "New best time";
      } else {
        best.textContent = `Best time ${clockText(previous)}`;
      }
      best.classList.remove("is-hidden");
      audio.win();
    } else {
      $("result-heading").textContent = `Night fell on ${config.planetName}`;
      $("result-text").textContent =
        found > 0
          ? `${config.playerName} found ${found} of ${total} crystals before dark. The rest are still glowing out there.`
          : `${config.playerName} found no crystals before dark. Their beams are easiest to spot from high ground.`;
      $("result-time").textContent = "Nightfall";
      best.classList.add("is-hidden");
      audio.nightfall();
    }
    fillTitle();
    $("again-button").focus();
  }

  function collect(item) {
    found++;
    world.crystals.collect(item);
    gemPos.copy(item.root.position).addScaledVector(item.dir, 1.1);
    world.fx.burst(gemPos, item.dir);
    hitstop = 0.06;
    if (!reduced) world.rig.punch(1);
    world.explorer.kick(reduced ? 0 : 2.6);
    audio.chime(found - 1);
    hud.setFound(found);
    hud.toast(found < total ? `Crystal ${found} of ${total}` : "Every crystal found");
    if (found >= total) endTimer = 1.3;
  }

  function handle(events) {
    for (const event of events) {
      if (event.type === "step") {
        audio.step(event.surface, event.run);
        if (event.surface !== "water") world.fx.puff(state.pos, state.up, event.run ? 3 : 2, event.run ? 1.1 : 0.7);
      } else if (event.type === "jump") {
        audio.jump();
        if (!reduced) world.explorer.kick(2.4);
        world.fx.puff(state.pos, state.up, 4, 1);
      } else if (event.type === "land") {
        audio.land(event.impact);
        if (!reduced) world.explorer.kick(-Math.min(event.impact * 0.38, 3.4));
        if (event.impact > 3 && event.surface !== "water") world.fx.puff(state.pos, state.up, 7, 1.6);
      }
    }
  }

  function step(dt) {
    time += dt;
    if (screen === "pause") return;
    hud.update(dt);
    if (hitstop > 0) {
      hitstop -= dt;
      return;
    }
    prevPos.copy(state.pos);
    const controls = screen === "run" ? input.read() : attract.read(dt, state);
    handle(walker.step(dt, controls));

    if (screen === "run") {
      if (endTimer < 0) elapsed += dt;
      for (const item of world.crystals.items) {
        if (item.found) continue;
        gemPos.copy(item.root.position).addScaledVector(item.dir, 0.9);
        if (gemPos.distanceTo(state.pos) < COLLECT_RADIUS) collect(item);
      }
      if (endTimer >= 0) {
        endTimer -= dt;
        if (endTimer < 0) finish(true);
      } else if (elapsed >= daySeconds) {
        finish(false);
      }
    }
  }

  function nearestBearing() {
    let best = null;
    let bestDot = -2;
    for (const item of world.crystals.items) {
      if (item.found) continue;
      const d = item.dir.dot(state.up);
      if (d > bestDot) {
        bestDot = d;
        best = item.dir;
      }
    }
    if (!best) return 0;
    flat.copy(best).addScaledVector(state.up, -best.dot(state.up));
    right.crossVectors(state.forward, state.up);
    return THREE.MathUtils.radToDeg(Math.atan2(flat.dot(right), flat.dot(state.forward)));
  }

  function render(alpha, dt, ms) {
    adaptive.frame(ms);
    const playing = screen === "run" || screen === "pause";
    blend = THREE.MathUtils.damp(blend, playing ? 0 : 1, playing ? 1.9 : 1.2, dt);
    const target = screen === "title" ? titlePhase : screen === "result" ? phase : elapsed / daySeconds;
    phase = THREE.MathUtils.damp(phase, Math.min(target, 1), screen === "run" ? 3 : 1.5, dt);
    const elevation = THREE.MathUtils.degToRad(SUN_NOON - SUN_DROP * phase * phase * phase);

    if (screen === "title") filmTime += dt;
    // On the title the sun stands a little to the right of the way the explorer walks, so the over-the-shoulder
    // shot looks toward it; in play it keeps its own bearing.
    titleAz.copy(state.forward).applyAxisAngle(state.up, -0.38);
    drawAz.copy(state.sunAz).lerp(titleAz, blend).addScaledVector(state.up, -drawAz.dot(state.up)).normalize();

    const r = THREE.MathUtils.lerp(prevPos.length(), state.pos.length(), alpha);
    drawPos.copy(prevPos).lerp(state.pos, alpha).setLength(r);
    lit = world.draw({
      pos: drawPos,
      ground: world.radius + Math.max(world.terrain.height(state.up.x, state.up.y, state.up.z), 0),
      heading: state.heading,
      forward: state.forward,
      pitch: state.pitch,
      blend,
      dive: reduced ? 0 : filmDive(filmTime),
      sunElevation: elevation,
      sunAz: drawAz,
      time,
      dt: screen === "pause" ? 0 : dt,
      reduced,
      motion: {
        speed: state.speed, turn: state.turn, grounded: state.grounded, vy: state.vy, slopePitch: state.slopePitch,
        slopeRoll: state.slopeRoll, reduced, time,
      },
    });
    audio.update(dt, lit.night, screen === "run");
    if (screen === "run") {
      const remaining = daySeconds - elapsed;
      hud.setClock(remaining, remaining <= LATE_SECONDS);
      hud.setCompass(nearestBearing());
    }
  }

  $("start-button").addEventListener("click", startRun);
  $("again-button").addEventListener("click", startRun);
  $("resume-button").addEventListener("click", () => pause(false));
  $("pause-button").addEventListener("click", () => pause(true));
  $("quit-button").addEventListener("click", () => {
    audio.pause(false);
    go("title");
    fillTitle();
    $("start-button").focus();
  });
  $("title-button").addEventListener("click", () => {
    go("title");
    $("start-button").focus();
  });
  const sound = $("sound-button");
  const showSound = () => {
    sound.setAttribute("aria-pressed", String(!audio.muted));
    sound.textContent = audio.muted ? "Sound off" : "Sound on";
  };
  showSound();
  sound.addEventListener("click", () => {
    audio.setMuted(!audio.muted);
    showSound();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && screen === "run") pause(true);
  });
  window.addEventListener("resize", () => {
    world.resize();
    fitFrame();
  });

  const loop = createLoop({ step, render });
  world.resize();
  fitFrame();
  loop.start();
  go("title");
  $("start-label").textContent = "Start exploring";
  $("start-button").disabled = false;
}

requestAnimationFrame(() => setTimeout(boot, 0));
