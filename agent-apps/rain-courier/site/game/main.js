// Rain Courier: dispatch over a live city, the shift against the clock, and the shift-over card.
import * as THREE from "three";
import { pickTier, tierSettings, createGovernor } from "../scene/quality.js";
import { readPalette } from "../scene/palette.js";
import { createWorld } from "../scene/world.js";
import { loadDroneModel } from "../scene/drone.js";
import { generateCity, PITCH, SIGN_WORDS, VERTICAL_WORDS } from "./gen.js";
import { createRng } from "./rng.js";
import { createFlight, createAutopilot } from "./flight.js";
import { createDispatch } from "./deliveries.js";
import { createInput } from "./input.js";
import { createHud } from "./hud.js";
import { createLoop } from "./loop.js";
import { createSound } from "../audio/synth.js";

const SIGN_LISTS = { horizontal: SIGN_WORDS, vertical: VERTICAL_WORDS };
const BEST_KEY = "rain-courier:best";
const DELIVERY_SECONDS = 15;
const CRASH_SECONDS = 5;

function readConfig() {
  const raw = window.__APP_CONFIG__ || {};
  const text = (v, fallback, max = 40) => (typeof v === "string" && v.trim() ? v.trim().slice(0, max) : fallback);
  const seconds = Number(raw.shiftSeconds);
  return {
    title: text(raw.title, "Rain Courier", 32),
    pilotName: text(raw.pilotName, "Courier", 28),
    cityName: text(raw.cityName, "Neo Harbor", 22),
    seed: text(raw.seed, "rain", 60),
    shiftSeconds: Number.isFinite(seconds) && seconds >= 20 ? Math.min(600, Math.round(seconds)) : 90,
  };
}

function readBest() {
  try {
    const best = JSON.parse(localStorage.getItem(BEST_KEY) || "null");
    return best && typeof best.score === "number" ? best : null;
  } catch {
    return null;
  }
}

async function boot() {
  const config = readConfig();
  document.title = config.title;
  const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
  const darkQuery = matchMedia("(prefers-color-scheme: dark)");
  const touchQuery = matchMedia("(pointer: coarse)");
  document.body.classList.toggle("is-touch", touchQuery.matches);

  const hud = createHud();
  let best = readBest();
  let palette = readPalette();
  hud.setDispatch({ ...config, best, light: palette.light });

  const tier = pickTier();
  const settings = tierSettings(tier);
  const plan = generateCity({ seed: config.seed, cityName: config.cityName, blocksX: settings.blocks[0], blocksZ: settings.blocks[1] });

  // The sign atlas is painted with the display font, so wait for it briefly.
  await Promise.race([document.fonts.load('800 100px "Big Shoulders"'), new Promise((r) => setTimeout(r, 1500))]).catch(() => {});
  const droneModel = await loadDroneModel("./models/drone.glb");

  const canvas = document.getElementById("scene");
  const world = createWorld({ canvas, tier, settings, plan, palette, droneModel, signWords: SIGN_LISTS });
  const { rig, drone, route } = world;
  const sound = createSound();
  hud.setMuted(sound.muted);

  const flight = createFlight(plan);
  const autopilot = createAutopilot(plan);
  const dispatch = createDispatch(plan, createRng(`route:${config.seed}`));

  // Open low in a street canyon, already flying toward a pickup on a roof that fronts the street.
  const opening = dispatch.opening();
  let task;
  let sx, sz;
  if (opening) {
    task = opening.task;
    sx = opening.start.x;
    sz = opening.start.z;
    const heading = Math.atan2(task.approach.x - sx, task.approach.z - sz);
    flight.place(sx, opening.start.y, sz, heading);
    flight.state.vel.set(Math.sin(heading) * 12, 0, Math.cos(heading) * 12);
  } else {
    sx = Math.round((plan.downtown.x + plan.halfX) / PITCH) * PITCH - plan.halfX;
    sz = Math.round((plan.downtown.z + plan.halfZ) / PITCH) * PITCH - plan.halfZ;
    task = dispatch.firstPickup({ x: sx, z: sz }, true);
    const heading = Math.atan2(task.point.x - sx, task.point.z - sz);
    flight.place(sx, Math.max(26, task.point.y + 6), sz, heading);
  }
  route.setTarget(task, task.kind, task.kind === "pickup" ? palette.pickup : palette.drop);

  const game = {
    mode: "dispatch",
    left: config.shiftSeconds,
    delivered: 0,
    bonus: 0,
    hitStop: 0,
    time: 0,
    thunderAt: 4.5,
    flashAge: 99,
    started: false,
  };
  const intents = { forward: 0, turn: 0, lift: 0, yaw: 0 };
  const events = [];
  const tmp = new THREE.Vector3();

  const input = createInput({
    canvas,
    stick: document.getElementById("stick"),
    lift: document.getElementById("lift"),
    onLook: (d) => rig.addPitch(d),
    onAction(action) {
      wake();
      if (action === "escape") {
        if (game.mode === "shift") setMode("pause");
        else if (game.mode === "pause") setMode("shift");
      } else if (action === "route") route.reveal();
      else if (action === "enter" && (game.mode === "dispatch" || game.mode === "over")) startShift();
    },
  });

  function wake() {
    if (!game.started) {
      game.started = true;
      sound.start();
    } else sound.resume();
  }
  addEventListener("pointerdown", wake, { capture: true });

  function setMode(mode) {
    game.mode = mode;
    hud.setMode(mode);
    frame();
    if (mode === "shift") canvas.focus({ preventScroll: true });
  }

  function startShift() {
    game.left = config.shiftSeconds;
    game.delivered = 0;
    game.bonus = 0;
    hud.setTally(0, 0);
    hud.showKeysHint();
    if (!drone.carrying && task.kind === "drop") task = dispatch.nextPickup(flight.state.pos);
    route.setTarget(task, task.kind, task.kind === "pickup" ? palette.pickup : palette.drop);
    setMode("shift");
  }

  function endShift() {
    const score = game.delivered * 100 + game.bonus;
    const newBest = !best || score > best.score;
    if (newBest) {
      best = { score, delivered: game.delivered };
      try {
        localStorage.setItem(BEST_KEY, JSON.stringify(best));
      } catch {
        // Private windows can refuse storage; the card still shows this shift.
      }
    }
    hud.showOver({ pilotName: config.pilotName, score, delivered: game.delivered, bonus: game.bonus, best: best.score, newBest });
    hud.setDispatch({ ...config, best, light: palette.light });
    setMode("over");
    document.getElementById("againButton").focus({ preventScroll: true });
  }

  document.getElementById("startButton").addEventListener("click", () => {
    wake();
    startShift();
  });
  document.getElementById("againButton").addEventListener("click", startShift);
  document.getElementById("resumeButton").addEventListener("click", () => setMode("shift"));
  document.getElementById("endButton").addEventListener("click", () => endShift());
  document.getElementById("pauseButton").addEventListener("click", () => setMode("pause"));
  document.getElementById("objective").addEventListener("click", () => route.reveal());
  document.getElementById("soundButton").addEventListener("click", () => {
    wake();
    sound.setMuted(!sound.muted);
    hud.setMuted(sound.muted);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      sound.suspend();
      if (game.mode === "shift") setMode("pause");
    }
  });

  // Where the open part of the screen is, so the drone sits in it and not under a panel.
  function frame() {
    const w = innerWidth, h = innerHeight;
    const card = document.querySelector(".dispatch-card").getBoundingClientRect();
    let x = 0, y = 0;
    if (game.mode === "dispatch") {
      if (w >= 900) x = Math.min(card.right, w * 0.45) / 2;
      else if (h <= 520) x = -(w - card.left) / 2;
      else y = (h - card.top) / 2 + h * 0.04;
    } else if (game.mode === "shift" || game.mode === "pause") {
      if (touchQuery.matches && h > w) y = h * 0.06;
    }
    rig.setFraming(x, y);
  }

  function resize() {
    world.resize(innerWidth, innerHeight);
    frame();
  }
  addEventListener("resize", resize);
  resize();
  rig.snap(flight.state);

  darkQuery.addEventListener("change", () => {
    palette = readPalette();
    world.setPalette(palette);
    route.setTarget(task, task.kind, task.kind === "pickup" ? palette.pickup : palette.drop);
    world.captureSkyline(tmp.set(sx, 3, sz));
    hud.setDispatch({ ...config, best, light: palette.light });
  });

  const governor = createGovernor((step) => {
    if (step === "ratio-1.5") world.setPixelRatio(1.5);
    else if (step === "ratio-1") world.setPixelRatio(1);
    else world.dropPost();
  });

  function deliverOrPickup() {
    const s = flight.state;
    if (task.kind === "pickup") {
      drone.attachPackage(task.base.clone().add(tmp.set(0, 0.3, 0)));
      sound.pickup();
      route.burstAt(task.base);
      if (game.mode === "shift") hud.toast("Hooked", task.name, "good");
      task = dispatch.nextDrop(s.pos, game.mode !== "shift");
    } else {
      drone.releasePackage();
      sound.chime();
      route.burstAt(task.base);
      if (game.mode === "shift") {
        game.delivered++;
        game.left += DELIVERY_SECONDS;
        hud.toast(`+${DELIVERY_SECONDS} s`, "Delivered", "good");
        hud.setTally(game.delivered, game.bonus);
        if (!reducedQuery.matches) game.hitStop = 0.14;
      }
      task = dispatch.nextPickup(s.pos);
    }
    route.setTarget(task, task.kind, task.kind === "pickup" ? palette.pickup : palette.drop);
  }

  function update(dt) {
    game.time += dt;
    if (game.mode === "pause") return;
    if (game.hitStop > 0) {
      game.hitStop -= dt;
      return;
    }
    const s = flight.state;
    const piloted = game.mode === "shift";
    if (piloted) {
      const i = input.read();
      intents.forward = i.forward;
      intents.turn = i.turn;
      intents.lift = i.lift;
      intents.yaw = i.yaw;
      i.yaw = 0;
      if (input.used && game.left < config.shiftSeconds - 4) hud.hideKeysHint();
    } else {
      autopilot.intents(dt, s, task, intents);
      intents.yaw = 0;
      input.read().yaw = 0;
    }
    events.length = 0;
    flight.step(dt, intents, events);
    drone.step(dt);

    for (const e of events) {
      if (e.type === "crash") {
        route.sparksAt(e.at, 1);
        sound.crash(Math.min(1, e.impact / 14));
        rig.kick(0.9);
        if (piloted) {
          game.left -= CRASH_SECONDS;
          hud.toast(`−${CRASH_SECONDS} s`, "Crash", "bad");
        }
      } else if (e.type === "scrape") {
        route.sparksAt(e.at, 0.4);
        rig.kick(0.25);
      } else if (e.type === "near" && piloted) {
        const pts = Math.round((25 + 50 * e.closeness) / 5) * 5;
        game.bonus += pts;
        hud.toast(`+${pts}`, "Near miss");
        hud.setTally(game.delivered, game.bonus);
        sound.whoosh();
      }
    }

    if (dispatch.reached(task, s.pos)) deliverOrPickup();

    if (piloted) {
      game.left -= dt;
      if (game.left <= 0) {
        game.left = 0;
        endShift();
      }
    }

    // Thunder every so often: a one-frame flash across the skyline, or a slow fade when motion is reduced.
    if (game.time >= game.thunderAt) {
      game.flashAge = 0;
      game.thunderAt = game.time + 11 + Math.random() * 13;
      sound.thunder(0.5 + Math.random() * 1.2);
    }
  }

  let lastFrameMs = 16.7;
  function render(dt) {
    const s = flight.state;
    const reduced = reducedQuery.matches;
    const t = game.time;
    const attract = game.mode !== "shift" && game.mode !== "pause";
    rig.setYawOffset(attract ? 0.3 + Math.sin(t * 0.22) * 0.12 : 0);
    rig.update(dt, s, { reduced, attract });
    drone.update(dt, s, t, reduced);
    route.update(dt, s.pos, task, autopilot.cruise());
    world.rain.update(world.camera.position, s.vel);
    world.splashes.update(t, s.pos);

    game.flashAge += dt;
    const a = game.flashAge;
    let flash = 0;
    if (reduced) flash = a < 2 ? 0.3 * Math.sin(Math.min(1, a / 2) * Math.PI) : 0;
    else flash = a < 0.034 ? 1 : a < 0.09 ? 0.08 : a < 0.14 ? 0.7 : 0.7 * Math.exp(-(a - 0.14) * 5);
    world.shared.uFlash.value = flash;

    // The HUD: clock, objective, and the arrow pointing to it.
    tmp.copy(task.point).sub(s.pos);
    const distance = tmp.length();
    const h = s.heading;
    const fx = Math.sin(h), fz = Math.cos(h);
    const bearing = (Math.atan2(tmp.x * -fz + tmp.z * fx, tmp.x * fx + tmp.z * fz) * 180) / Math.PI;
    hud.setObjective(task, distance, bearing, attract);
    if (!attract) hud.setClock(game.left, config.shiftSeconds);
    sound.throttle(s.throttle, Math.max(0, 1 - s.nearest / 3));

    const focus = world.camera.position.distanceTo(s.pos);
    world.render(dt, t, focus, 0.85);
    governor.sample(lastFrameMs);
  }

  world.captureSkyline(tmp.set(sx, 3, sz));
  world.compile();
  hud.setMode("dispatch");
  frame();
  createLoop({ update, render, frame: (ms) => (lastFrameMs = ms) }).start();
  document.documentElement.classList.add("is-ready");
  // ?inspect exposes the running game to a test browser; nothing on the page shows it.
  if (new URLSearchParams(location.search).has("inspect")) window.__rainCourier = { world, plan, flight, game, tier };
}

boot();
