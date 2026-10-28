// The run and its rules: the demo run the autopilot flies behind the title, the attract storm behind the result
// card, waves every twelve seconds, score and multiplier, the clear at the end of the run, and the death sequence. Real time comes in; the game decides how fast its own
// clock runs (hit-stop, slow time, the slow-motion death).
import { PATTERNS, PATTERN_NAMES } from "./patterns.js";
import { collide } from "./collision.js";
import { createPilot } from "./autopilot.js";
import { createRng } from "./rng.js";
import { clamp, easeInOutCubic, easeOutCubic } from "./ease.js";
import { CORE_RADIUS, GRAZE_RADIUS } from "../scene/ship.js";

export const WAVE_SECONDS = 12;
const ATTRACT_SECONDS = 6.5;
const QUIET_TAIL = 1.3;
const HIT_STOP = 0.12;
const DEATH_SLOW = 1.7;
const SHIP_SPEED = 46;
const GRAZE_POINTS = 25;
const SURVIVAL_POINTS = 100;
const MAX_MULT = 8;
// The demo run: the autopilot holds slow time for DEMO_SLOW_FOR seconds out of every DEMO_SLOW_EVERY, the first hold
// starting DEMO_SLOW_AT seconds after the page opens, and its storm runs DEMO_LEVEL denser than a first run.
const DEMO_SLOW_EVERY = 7.5;
const DEMO_SLOW_FOR = 2.6;
const DEMO_SLOW_AT = 0.9;
const DEMO_LEVEL = 1.1;
const DEMO_SPEED = 40;

export function createGame({ pool, config, colors, reducedMotion, events }) {
  const order = config.patterns.filter((name) => PATTERNS[name]);
  const names = order.length ? order : PATTERN_NAMES;
  const pilot = createPilot(pool.capacity);
  let rng = createRng(20261027);

  const g = {
    mode: "attract",
    W: 80,
    H: 50,
    shipX: 0,
    shipY: -20,
    shipVisible: true,
    time: 0,
    fxTime: 0,
    runTime: 0,
    runSeconds: config.runSeconds,
    cleared: false,
    wave: -1,
    waveName: "",
    score: 0,
    mult: 1,
    grazes: 0,
    streak: 0,
    longest: 0,
    sinceGraze: 99,
    slow: false,
    dolly: 0,
    focusX: 0,
    focusY: 0,
    trauma: 0,
    shift: 0,
    shiftCool: 0,
    pulse: 0,
    attractIndex: 0,
    attractClock: 0,
    deathClock: 0,
    demoClock: 0,
    fadeOut: 0,
    fadeIn: 0,
    result: null,
  };

  let emitter = null;
  let emitterClock = 0;
  let level = 1;
  let speed = 1;
  let anchorX = 0;
  let anchorY = 0;
  let runOrder = names.slice();
  let warming = false;

  // Palette blends in linear color: u runs from the first shard color to the second; k pulls toward the third.
  const scratch = [0, 0, 0];
  const ctx = {
    pool,
    rng,
    W: 80,
    H: 50,
    ax: 0,
    ay: 0,
    sx: 0,
    sy: 0,
    level: 1,
    speed: 1,
    emit: 1,
    fire(x, y, h, s, st, sk, w, size, col) {
      pool.spawn(x, y, h, s, st, sk, w, size, col);
    },
    color(u) {
      const { a, b } = colors;
      scratch[0] = a.r + (b.r - a.r) * u;
      scratch[1] = a.g + (b.g - a.g) * u;
      scratch[2] = a.b + (b.b - a.b) * u;
      return scratch;
    },
    accent(u, k) {
      ctx.color(u);
      const { c } = colors;
      scratch[0] += (c.r - scratch[0]) * k;
      scratch[1] += (c.g - scratch[1]) * k;
      scratch[2] += (c.b - scratch[2]) * k;
      return scratch;
    },
  };

  function setColors(next) {
    colors = next;
  }

  function wide() {
    return g.W > g.H * 1.15;
  }

  function attractAnchor() {
    if (wide()) return [g.W * 0.34, g.H * 0.04];
    return [0, -g.H * 0.02];
  }

  /** Where the attract pilot likes to fly: in the open below the eye, clear of the type and the buttons. */
  function attractHome() {
    const [ax, ay] = attractAnchor();
    if (wide()) return [ax - g.W * 0.22, ay - g.H * 0.36];
    return [ax + g.W * 0.42, ay - g.H * 0.06];
  }

  /** Where the demo run's pilot hovers: low in the field like a player's thumb, above the Play bar. */
  function demoHome() {
    if (wide()) return [g.W * 0.12 * Math.sin(g.demoClock * 0.35), -g.H * 0.12];
    return [g.W * 0.25 * Math.sin(g.demoClock * 0.35), -g.H * 0.22];
  }

  function startEmitter(name, lvl, spd, ax, ay) {
    emitter = PATTERNS[name]();
    emitterClock = 0;
    level = lvl;
    speed = spd;
    anchorX = ax;
    anchorY = ay;
  }

  function beginAttract(index) {
    g.attractIndex = index % names.length;
    g.attractClock = 0;
    const [ax, ay] = attractAnchor();
    startEmitter(names[g.attractIndex], 3, 1, ax, ay);
    events.attractWave(names[g.attractIndex], g.attractIndex, names.length);
  }

  function emitterStep(dt, emit) {
    if (!emitter) return;
    emitterClock += dt;
    ctx.W = g.W;
    ctx.H = g.H;
    ctx.ax = anchorX;
    ctx.ay = anchorY;
    ctx.sx = g.shipX;
    ctx.sy = g.shipY;
    ctx.level = level;
    ctx.speed = speed;
    ctx.emit = emit;
    ctx.rng = rng;
    emitter.step(dt, ctx);
  }

  function onGraze(i) {
    const bx = pool.x[i];
    const by = pool.y[i];
    const heading = Math.atan2(by - g.shipY, bx - g.shipX);
    if (!warming) events.graze(bx, by, heading, pool.r[i], pool.g[i], pool.b[i]);
    if (g.mode !== "run" && g.mode !== "demo") return;
    g.streak = g.sinceGraze < 2 ? g.streak + 1 : 1;
    g.longest = Math.max(g.longest, g.streak);
    g.sinceGraze = 0;
    g.mult = Math.min(MAX_MULT, g.mult + 0.1);
    g.grazes++;
    g.score += Math.round(GRAZE_POINTS * g.mult);
    // The RGB split pulses for 80 ms, at most twice a second, so a long streak flickers rather than smears.
    if (!reducedMotion() && g.shiftCool <= 0) {
      g.shift = 0.08;
      g.shiftCool = 0.5;
    }
    if (!warming) events.grazeScored(g.mult, Math.round(GRAZE_POINTS * g.mult), g.shipX, g.shipY, g.mode === "demo");
  }

  function clampShip() {
    g.shipX = clamp(g.shipX, -g.W + 2, g.W - 2);
    g.shipY = clamp(g.shipY, -g.H + 3, g.H - 6);
  }

  function nextWave() {
    g.wave++;
    const name = runOrder[g.wave % runOrder.length];
    const lvl = 1 + 0.26 * g.wave + (g.cleared ? 0.5 : 0) + (g.mode === "demo" ? DEMO_LEVEL : 0);
    const spd = (1 + 0.04 * g.wave) * (g.cleared ? 1.25 : 1);
    startEmitter(name, lvl, spd, 0, g.H * 0.4);
    g.waveName = name;
    g.pulse = 1;
    if (!warming) events.wave(name, g.wave, g.mode === "demo");
  }

  function updateAttract(dt) {
    g.attractClock += dt;
    if (g.attractClock > ATTRACT_SECONDS) beginAttract(g.attractIndex + 1);
    const emit = g.attractClock < ATTRACT_SECONDS - 0.35 ? 1 : 0;
    emitterStep(dt, emit);
    pool.update(dt);
    if (g.shipVisible) {
      const [homeX, homeY] = attractHome();
      const [vx, vy] = pilot.steer(pool, g.shipX, g.shipY, homeX, homeY, g.W, g.H, 40, dt);
      // The demo pilot stays in its open patch of sky, where the title shots can see it.
      g.shipX = clamp(g.shipX + vx * dt, homeX - g.W * 0.3, homeX + g.W * 0.3);
      g.shipY = clamp(g.shipY + vy * dt, homeY - g.H * 0.12, homeY + g.H * 0.14);
      clampShip();
      collide(pool, g.shipX, g.shipY, CORE_RADIUS, GRAZE_RADIUS, onGraze);
    }
  }

  function updateRun(dt, input) {
    const demo = g.mode === "demo";
    // Slow time costs score: the multiplier bleeds while it is held.
    if (demo) {
      g.demoClock += dt;
      const into = (((g.demoClock - DEMO_SLOW_AT) % DEMO_SLOW_EVERY) + DEMO_SLOW_EVERY) % DEMO_SLOW_EVERY;
      g.slow = into < DEMO_SLOW_FOR;
    } else g.slow = input.slow;
    const scale = g.slow ? 0.5 : 1;
    const sim = dt * scale;
    if (demo) {
      const [homeX, homeY] = demoHome();
      const [vx, vy] = pilot.steer(pool, g.shipX, g.shipY, homeX, homeY, g.W, g.H, DEMO_SPEED, sim);
      // The autopilot keeps to the open middle of the field, clear of the HUD and the Play bar.
      g.shipX = clamp(g.shipX + vx * sim, homeX - g.W * 0.4, homeX + g.W * 0.4);
      g.shipY = clamp(g.shipY + vy * sim, homeY - g.H * 0.14, homeY + g.H * 0.2);
    } else {
      const [dx, dy] = input.takeDrag(g.pxPerUnit);
      const [kx, ky] = input.axes();
      g.shipX += dx + kx * SHIP_SPEED * sim;
      g.shipY += dy + ky * SHIP_SPEED * sim;
    }
    clampShip();

    g.runTime += sim;
    if (g.fadeOut > 0) {
      g.fadeOut = Math.max(0, g.fadeOut - dt);
      if (g.fadeOut === 0) pool.clear();
    }
    if (g.runTime >= 0) {
      const waveIndex = Math.floor(g.runTime / WAVE_SECONDS);
      if (waveIndex > g.wave) nextWave();
      if (!g.cleared && g.runTime >= g.runSeconds) {
        g.cleared = true;
        level += 0.5;
        speed *= 1.25;
        if (!demo) events.cleared();
      }
      const into = g.runTime - g.wave * WAVE_SECONDS;
      const emit = clamp(into / 0.8, 0, 1) * (into < WAVE_SECONDS - QUIET_TAIL ? 1 : 0);
      emitterStep(sim, emit);
      g.score += SURVIVAL_POINTS * sim * (g.slow ? 0.5 : 1);
    }
    pool.update(sim);

    g.sinceGraze += sim;
    if (g.sinceGraze > 2) g.mult = Math.max(1, g.mult - 0.6 * sim);
    if (g.slow) g.mult = Math.max(1, g.mult - 0.5 * dt);

    // The title's storm fades out harmlessly; only the run's own shards can hit.
    if (g.fadeOut > 0) return sim;
    // The autopilot is never shot down; a demo run that touches a shard flies on.
    const hit = collide(pool, g.shipX, g.shipY, CORE_RADIUS, GRAZE_RADIUS, onGraze);
    if (hit >= 0 && !demo) die();
    return sim;
  }

  function die() {
    g.mode = "dying";
    g.deathClock = 0;
    g.focusX = g.shipX;
    g.focusY = g.shipY;
    g.slow = false;
    if (!reducedMotion()) g.trauma = 0.85;
    events.died(g.shipX, g.shipY);
    if (reducedMotion()) finishDeath();
  }

  function finishDeath() {
    pool.clear();
    events.fade(1);
    g.mode = "result";
    g.shipVisible = false;
    g.result = {
      score: Math.round(g.score),
      grazes: g.grazes,
      longest: g.longest,
      survived: Math.max(0, g.runTime),
      cleared: g.cleared,
    };
    events.result(g.result);
    beginAttract(g.attractIndex + 1);
    // The next pattern is already blooming behind the card, faded up rather than popped in.
    for (let t = 0; t < 2.4; t += 1 / 60) updateAttract(1 / 60);
    g.fadeIn = 0.7;
  }

  function updateDying(dt) {
    g.deathClock += dt;
    if (g.deathClock < HIT_STOP) return 0;
    const t = (g.deathClock - HIT_STOP) / DEATH_SLOW;
    const sim = dt * 0.25;
    pool.blast(g.focusX, g.focusY, sim, 90);
    pool.update(sim);
    g.dolly = easeInOutCubic(clamp(t / 0.75, 0, 1));
    events.fade(1 - easeOutCubic(clamp(t, 0, 1)));
    if (t >= 1) finishDeath();
    return sim;
  }

  /** Clears the score and the clock for a new run or demo run; the storm on screen fades out over `fadeOut` seconds. */
  function reset(mode, runTime, fadeOut) {
    Object.assign(g, {
      mode,
      runTime,
      cleared: false,
      wave: -1,
      waveName: "",
      score: 0,
      mult: 1,
      grazes: 0,
      streak: 0,
      longest: 0,
      sinceGraze: 99,
      slow: false,
      dolly: 0,
      result: null,
      fadeOut,
    });
    emitter = null;
  }

  const api = {
    state: g,
    setColors,
    setField(field) {
      const first = g.W === 80 && g.H === 50;
      g.W = field.W;
      g.H = field.H;
      g.pxPerUnit = field.pxPerUnit;
      if (first) [g.shipX, g.shipY] = attractHome();
      clampShip();
      if (g.mode === "attract" || g.mode === "result") {
        const [ax, ay] = attractAnchor();
        anchorX = ax;
        anchorY = ay;
      }
    },
    eye() {
      return [anchorX, anchorY];
    },
    start() {
      if (g.mode === "run" || g.mode === "dying") return;
      rng = createRng((Date.now() & 0xffffff) + 1);
      const rest = names.filter((n) => n !== "Lotus");
      for (let i = rest.length - 1; i > 0; i--) {
        const j = Math.floor(rng.next() * (i + 1));
        [rest[i], rest[j]] = [rest[j], rest[i]];
      }
      runOrder = names.includes("Lotus") ? ["Lotus", ...rest] : rest;
      reset("run", -1.1, 0.45);
      if (!g.shipVisible) {
        g.shipX = 0;
        g.shipY = -g.H * 0.55;
      }
      g.shipVisible = true;
      pilot.reset();
      events.started();
    },
    /**
     * Starts the demo run the autopilot flies: the run's own rules in the patterns' set order. `into` seconds of it
     * are played before the first frame, so the page opens on a run already in progress; with none, the old storm
     * fades and the demo's first wave arrives as a run's does.
     */
    demo(into = 0) {
      if (g.mode === "run" || g.mode === "dying") return;
      rng = createRng(20261027);
      runOrder = names.slice();
      const fresh = into > 0;
      reset("demo", fresh ? 0 : -1.1, fresh ? 0 : 0.45);
      if (fresh) pool.clear();
      g.demoClock = -into;
      if (fresh || !g.shipVisible) [g.shipX, g.shipY] = demoHome();
      g.shipVisible = true;
      pilot.reset();
      warming = true;
      const dt = 1 / 60;
      for (let t = 0; t < into; t += dt) updateRun(dt, null);
      warming = false;
      g.demoClock = 0;
    },
    get demoSeconds() {
      return g.mode === "demo" ? g.runTime : 0;
    },
    pause() {
      if (g.mode !== "run") return;
      g.mode = "paused";
      g.slow = false;
    },
    resume() {
      if (g.mode === "paused") g.mode = "run";
    },
    quit() {
      if (g.mode !== "paused") return;
      g.focusX = g.shipX;
      g.focusY = g.shipY;
      finishDeath();
    },
    /** One fixed step of real time; returns how far the game's own clock moved. */
    step(dt, input) {
      g.time += dt;
      let sim = dt;
      if (g.mode === "attract" || g.mode === "result") updateAttract(dt);
      else if (g.mode === "run" || g.mode === "demo") sim = updateRun(dt, input);
      else if (g.mode === "dying") sim = updateDying(dt);
      else sim = 0;
      if (g.mode === "result" && g.dolly > 0) g.dolly = Math.max(0, g.dolly - dt * 2);
      g.fxTime += sim;
      g.trauma = Math.max(0, g.trauma - dt * 1.3);
      g.shift = Math.max(0, g.shift - dt);
      g.shiftCool -= dt;
      g.pulse = Math.max(0, g.pulse - dt * 1.5);
      g.fadeIn = Math.max(0, g.fadeIn - dt);
      return sim;
    },
    beginAttract,
    get fadeLevel() {
      if ((g.mode === "run" || g.mode === "demo") && g.fadeOut > 0) return g.fadeOut / 0.45;
      if (g.mode === "result" && g.fadeIn > 0) return 1 - g.fadeIn / 0.7;
      return 1;
    },
  };
  return api;
}
