// The game: the attract keeper on the title, the night the person keeps, and the dawn or lost card, over one
// world that never stops moving.
import * as THREE from "three";
import WebGL from "three/addons/capabilities/WebGL.js";
import { pickTier } from "../scene/quality.js";
import { createWorld } from "../scene/world.js";
import { LAMP_HEIGHT } from "../scene/lighthouse.js";
import { BEAM_HALF_ANGLE, BEAM_LENGTH } from "../scene/beam.js";
import { emptyShip, launch, steer, hold, bearingOf, angleDiff } from "./paths.js";
import { pace } from "./waves.js";
import { loadSave, writeSave, recordNight } from "./scoring.js";
import { createAttract } from "./attract.js";
import { createInput } from "./input.js";
import { createHud } from "./hud.js";
import { synth } from "../audio/synth.js";

const DEFAULTS = { title: "Lighthouse Keeper", lighthouseName: "Gull Rock Light", playerName: "Keeper", theme: "night", shipsToLose: 3, nightMinutes: 5 };
const config = { ...DEFAULTS, ...(window.__APP_CONFIG__ || {}) };
const canvas = document.getElementById("scene");

if (!WebGL.isWebGL2Available()) {
  const note = document.createElement("p");
  note.className = "no-webgl";
  note.textContent = "Lighthouse Keeper draws its sea with WebGL 2. Open it in a current Chrome, Safari, Firefox, or Edge.";
  document.body.append(note);
} else {
  start();
}

function start() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  const tier = pickTier();
  const world = createWorld(canvas, tier, config);
  const save = loadSave();
  synth.setMuted(save.muted);
  const hud = createHud(config, save, coarse);
  const attract = createAttract();
  const nightSeconds = config.nightMinutes * 60;
  const FLARE_RECHARGE = 20;
  const FLARE_LENGTH = 2;

  const state = {
    mode: "title",
    time: 0,
    now: 0,
    bearing: 0,
    targetBearing: 0,
    pitch: -0.13,
    beamPower: 1,
    flare: 0,
    flareAt: -10,
    charge: 1,
    fogThick: 1,
    dawn: 0,
    shake: 0,
    ships: Array.from({ length: world.shipPool }, emptyShip),
    night: { seconds: 0, turned: 0, lost: 0, spawnIn: 0, level: 0 },
    dawnAt: -1,
  };

  const tmp = new THREE.Vector3();
  const lamp = new THREE.Vector2();
  const ndc = new THREE.Vector3();
  let rand = mulberry(20261022);

  // A bearing whose point at this distance sits at the asked screen x, so a ship is placed where the person sees it.
  function bearingForScreen(x, distance) {
    const cam = world.camera;
    cam.updateMatrixWorld();
    let best = 0;
    let bestErr = Infinity;
    for (let i = 0; i < 360; i += 2) {
      const b = THREE.MathUtils.degToRad(i - 180);
      ndc.set(Math.sin(b) * distance, 3, -Math.cos(b) * distance).project(cam);
      if (ndc.z >= 1 || ndc.z <= -1) continue;
      const err = Math.abs(ndc.x - x);
      if (err < bestErr) {
        bestErr = err;
        best = b;
      }
    }
    return best;
  }

  function freeShip() {
    return state.ships.find((s) => !s.active) || null;
  }

  function activeCount() {
    let n = 0;
    for (const s of state.ships) if (s.active && !s.turned && !s.wrecked) n++;
    return n;
  }

  function spawn(speed, distance = 165) {
    const ship = freeShip();
    if (!ship) return null;
    const margin = world.rig.wide ? 0.78 : 0.62;
    const x = (rand() * 2 - 1) * margin;
    const bearing = bearingForScreen(x, distance);
    const curve = (rand() * 2 - 1) * (world.rig.wide ? 0.42 : 0.18);
    launch(ship, bearing, distance, speed * (0.9 + rand() * 0.2), curve, rand() * 6.28);
    return ship;
  }

  function stageAttract() {
    for (const s of state.ships) s.active = false;
    world.camera.updateMatrixWorld();
    world.rig.update(0, 0);
    world.camera.updateMatrixWorld();
    const wide = world.rig.wide;
    const layout = wide
      ? [[0.5, 38, 0.12, 0.42], [-0.1, 92, 0, 1], [0.8, 128, 0, 1], [-0.6, 72, 0, 1]]
      : [[0.38, 36, 0.12, 0.42], [-0.42, 86, 0, 1], [0.5, 120, 0, 1], [-0.05, 150, 0, 1]];
    layout.forEach(([x, d, fill, rate], i) => {
      const ship = state.ships[i];
      const b = bearingForScreen(x, d);
      launch(ship, b, d, 3.2, (i % 2 ? 1 : -1) * 0.2, i * 1.7);
      ship.heading = b + Math.PI + (i % 2 ? 0.35 : -0.5);
      ship.fill = fill;
      ship.burn = fill * 0.42;
      ship.holdRate = rate;
      ship.age = 4;
    });
    state.bearing = state.targetBearing = bearingOf(state.ships[0].x, state.ships[0].z);
    state.pitch = aimPitch(Math.hypot(state.ships[0].x, state.ships[0].z));
    state.night.spawnIn = 4;
    attract.begin(state, bearingOf(world.camera.position.x, world.camera.position.z));
  }

  function aimPitch(distance) {
    return Math.atan2(7 - LAMP_HEIGHT, Math.max(18, distance));
  }

  function fireFlare(fromPerson) {
    if (fromPerson && state.charge < 1) return;
    state.flareAt = state.now;
    if (fromPerson) state.charge = 0;
    synth.flare();
  }

  function strike() {
    world.weather.strike(state.now);
    synth.thunder();
  }

  function setMode(mode) {
    state.mode = mode;
    hud.mode(mode);
  }

  function beginNight() {
    synth.wake();
    for (const s of state.ships) {
      if (s.active && !s.turned && !s.wrecked) {
        s.turned = true;
      }
    }
    state.night = { seconds: 0, turned: 0, lost: 0, spawnIn: 0.6, level: 0 };
    state.charge = 1;
    state.dawn = 0;
    state.dawnAt = -1;
    rand = mulberry(Math.floor(performance.now()));
    hud.reset();
    hud.showCard("result", false);
    hud.showCard("pause", false);
    setMode("night");
    nextThunder = state.now + 6 + rand() * 6;
    setTimeout(() => {
      if (state.mode === "night") {
        spawn(pace(0).speed, 135);
        synth.foghorn();
      }
    }, 400);
  }

  function endNight(dawn) {
    const newBest = recordNight(save, state.night.turned, state.night.seconds, dawn);
    hud.result(dawn, state.night, save, newBest);
    hud.showBest(save);
    setMode("over");
    hud.showCard("result", true);
    if (dawn) synth.dawn();
  }

  function pause(on) {
    if (on && state.mode === "night") {
      setMode("paused");
      hud.showCard("pause", true);
      synth.suspend();
    } else if (!on && state.mode === "paused") {
      hud.showCard("pause", false);
      setMode("night");
      synth.resume();
    }
  }

  function toTitle() {
    hud.showCard("result", false);
    hud.showCard("pause", false);
    setMode("title");
    stageAttract();
  }

  // Input.
  const input = createInput(canvas, {
    wake: () => synth.wake(),
    aim(x, y) {
      if (state.mode !== "night") return;
      const p = world.seaPoint(x, y, tmp);
      if (p) state.targetBearing = unwrapNear(bearingOf(p.x, p.z), state.bearing);
    },
    drag(dx) {
      if (state.mode !== "night") return;
      state.targetBearing += dx * (coarse ? 0.0105 : 0.008);
    },
    tap(x, y) {
      if (state.mode === "title") {
        beginNight();
        return;
      }
      if (state.mode !== "night") return;
      world.lampScreen(lamp);
      if (Math.hypot(lamp.x - x, lamp.y - y) < 70) fireFlare(true);
    },
    space() {
      if (state.mode === "title") beginNight();
      else if (state.mode === "night") fireFlare(true);
    },
    enter() {
      if (state.mode === "title") beginNight();
    },
    escape() {
      if (state.mode === "night") pause(true);
      else if (state.mode === "paused") pause(false);
      else if (state.mode === "over") toTitle();
    },
  });

  document.getElementById("start").addEventListener("click", beginNight);
  document.getElementById("again").addEventListener("click", beginNight);
  document.getElementById("to-title").addEventListener("click", toTitle);
  document.getElementById("resume").addEventListener("click", () => pause(false));
  document.getElementById("quit").addEventListener("click", () => {
    hud.showCard("pause", false);
    endNight(false);
  });
  document.getElementById("pause-btn").addEventListener("click", () => pause(true));
  document.getElementById("flare-btn").addEventListener("click", () => {
    synth.wake();
    fireFlare(true);
  });
  const soundButtons = document.querySelectorAll(".sound-toggle");
  const showSound = () => {
    soundButtons.forEach((b) => {
      b.setAttribute("aria-pressed", String(save.muted));
      b.setAttribute("aria-label", save.muted ? "Turn sound on" : "Turn sound off");
    });
  };
  showSound();
  soundButtons.forEach((b) =>
    b.addEventListener("click", () => {
      save.muted = !save.muted;
      writeSave(save);
      synth.wake();
      synth.setMuted(save.muted);
      showSound();
    }),
  );
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      pause(true);
      synth.suspend();
    }
  });

  let nextThunder = 6;
  const thunderEvery = world.tokens.thunderEvery;
  const events = { thunder: false, flare: false };

  function simulate(dt) {
    const playing = state.mode === "night";
    const frozen = state.mode === "paused";
    if (frozen) return;

    events.thunder = false;
    events.flare = false;
    let direct = false;
    if (state.mode === "title" || state.mode === "over") {
      const aim = attract.step(state, dt, events);
      if (aim.direct) {
        state.bearing = aim.bearing;
        state.targetBearing = aim.bearing;
        direct = true;
      } else {
        state.targetBearing = unwrapNear(aim.bearing, state.bearing);
      }
      if (events.thunder && thunderEvery > 0) strike();
      if (events.flare) fireFlare(false);
    } else {
      state.targetBearing += input.turn() * 2.1 * dt;
      state.night.seconds += dt;
      state.charge = Math.min(1, state.charge + dt / FLARE_RECHARGE);
    }

    // Magnetism: the beam leans a little toward a ship it is almost on.
    let lean = 0;
    let nearest = Infinity;
    for (const s of state.ships) {
      if (!s.active || s.turned || s.wrecked) continue;
      const d = angleDiff(bearingOf(s.x, s.z), state.bearing);
      if (Math.abs(d) < BEAM_HALF_ANGLE * 2.2 && Math.abs(d) < Math.abs(nearest)) nearest = d;
    }
    if (nearest !== Infinity && playing) lean = nearest * 0.35;

    if (!direct) {
      const gap = state.targetBearing - state.bearing + lean;
      const speed = Math.max(-2.5, Math.min(2.5, gap * 5.5));
      state.bearing += speed * dt;
    }

    // Each ship: steer, then the beam's hold.
    let held = 0;
    let heldDistance = 85;
    const flareOn = state.now - state.flareAt < FLARE_LENGTH;
    for (const s of state.ships) {
      if (!s.active) continue;
      s.visible = world.onScreen(s.x, 3, s.z, 1.05);
      const result = steer(s, dt);
      if (result === "wreck") {
        if (playing) {
          state.night.lost += 1;
          state.shake = 1;
          synth.wreck();
        }
        continue;
      }
      if (s.turned || s.wrecked) continue;
      const d = Math.hypot(s.x, s.z);
      const off = Math.abs(angleDiff(bearingOf(s.x, s.z), state.bearing));
      const width = Math.max(BEAM_HALF_ANGLE * 1.15, Math.atan2(3.2, d));
      const inBeam = off < width && d < BEAM_LENGTH * 0.92;
      const lit = inBeam || (flareOn && s.visible);
      const rate = s.holdRate;
      if (flareOn && !inBeam && s.visible) s.holdRate = rate * 0.5;
      if (hold(s, lit, dt)) {
        if (playing) state.night.turned += 1;
        synth.turned();
      }
      s.holdRate = rate;
      if (inBeam && s.fill > held) {
        held = s.fill;
        heldDistance = d;
      }
    }
    synth.burn(held);
    // The title sweep dips the beam below the camera, so it rakes rays and a flare across the view without
    // swallowing it whole.
    const pitchWant = direct ? -0.36 : aimPitch(held > 0 ? heldDistance : 85);
    state.pitch += (pitchWant - state.pitch) * Math.min(1, dt * 3);

    // Spawning.
    const p = pace(playing ? state.night.seconds : 40);
    state.night.spawnIn -= dt;
    const want = playing ? p.most : 4;
    if (state.night.spawnIn <= 0 && activeCount() < want) {
      spawn(p.speed);
      if (rand() < p.pair) spawn(p.speed, 175);
      if (playing) synth.foghorn();
      state.night.spawnIn = playing ? p.every * (0.8 + rand() * 0.4) : 3.2;
    }
    if (playing && p.level !== state.night.level) {
      state.night.level = p.level;
      hud.notice(p.level === 2 ? "The fog thickens. Two may come at once." : "The fog thickens");
    }
    state.fogThick += ((playing ? p.fog : 1) - state.fogThick) * Math.min(1, dt * 0.5);

    // Thunder on the theme's own clock.
    if (playing && thunderEvery > 0 && state.now > nextThunder) {
      strike();
      nextThunder = state.now + thunderEvery * (0.6 + rand() * 0.8);
    }

    // Night's end.
    if (playing) {
      state.dawn = Math.pow(Math.max(0, (state.night.seconds - nightSeconds * 0.7) / (nightSeconds * 0.3)), 1.6) * 0.85;
      if (state.night.lost >= config.shipsToLose) endNight(false);
      else if (state.night.seconds >= nightSeconds) endNight(true);
      hud.update(state.night, state.charge, nightSeconds);
    } else if (state.mode === "title") {
      state.dawn = 0;
    }
  }

  stageAttract();
  world.compile();

  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    state.now += dt;
    state.time += dt;
    simulate(dt);
    const f = state.now - state.flareAt;
    state.flare = f < 0 ? 0 : f < 0.15 ? f / 0.15 : f < FLARE_LENGTH ? 1 - Math.pow((f - 0.15) / (FLARE_LENGTH - 0.15), 2) * 0.35 : Math.max(0, 0.65 - (f - FLARE_LENGTH) * 0.9);
    state.shake = Math.max(0, state.shake - dt * 2.5) + world.weather.thunder.value * 0.15;
    world.frame(state, dt);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function unwrapNear(angle, ref) {
  return ref + angleDiff(angle, ref);
}

function mulberry(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
