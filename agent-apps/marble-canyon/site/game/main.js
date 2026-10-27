// Marble Canyon: title over a live run of the canyon, countdown, the run against the ghost, and the result.
import WebGL from "three/addons/capabilities/WebGL.js";
import { createSynth } from "../audio/synth.js";
import { FrameWatch, pickTier } from "../scene/quality.js";
import { readTokens } from "../scene/tokens.js";
import { createWorld } from "../scene/world.js";
import { Autopilot } from "./autopilot.js";
import { frameAt, generateTrack, medalTimes, newFrame } from "./generate.js";
import { GhostPlayer, GhostRecorder, loadBest, loadSetting, saveBest, saveSetting } from "./ghost.js";
import { createHud, medalFor } from "./hud.js";
import { createInput } from "./input.js";
import { startLoop } from "./loop.js";
import { Rail, STEP, TUNING, placeOnTrack } from "./rail.js";

const DEFAULTS = {
  title: "Marble Canyon",
  racerName: "Racer",
  theme: "canyon",
  seed: "",
  trackLength: "medium",
  marbleColor: "#2f6fdb",
};
const config = { ...DEFAULTS, ...(window.__APP_CONFIG__ || {}) };
const seed = String(config.seed || config.racerName || "canyon").trim() || "canyon";
const lengthName = ["short", "medium", "long"].includes(config.trackLength) ? config.trackLength : "medium";
const JUMP_MIN = 20;
// ?drive=auto lets the demo driver take a run, for checking the full loop in a browser.
const autoDrive = new URLSearchParams(location.search).get("drive") === "auto";
const COUNT_BEAT = 0.8;
const ATTRACT_SPEED = 36;
const GHOST_LEAD = 10;

const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const coarse = matchMedia("(pointer: coarse)").matches;
const track = generateTrack(seed, lengthName);
const medals = medalTimes(track);
let best = loadBest(seed, lengthName);
const hud = createHud({ track, medals, config, seed, coarse });
hud.showBest(best);
hud.screen("title");

const canvas = document.getElementById("scene");
if (!WebGL.isWebGL2Available()) {
  const note = document.createElement("p");
  note.className = "no-webgl";
  note.textContent = "Marble Canyon draws its canyon with WebGL 2, which this browser has turned off.";
  canvas.replaceWith(note);
  document.getElementById("start").disabled = true;
} else {
  run();
}

function run() {
  const tier = pickTier();
  const tokens = readTokens();
  const world = createWorld({
    canvas,
    tier,
    tokens,
    track,
    marbleColor: config.marbleColor,
    seed,
    reducedMotion: reducedQuery.matches,
  });
  world.loadEnvironment(tokens.env);

  const synth = createSynth(loadSetting("sound", true));
  hud.sound(synth.enabled);

  const player = new Rail(track);
  const recorder = new GhostRecorder();
  let pilot = new Autopilot(track, 1);
  let ghost = best ? new GhostPlayer(best.ghost) : null;

  let screen = "title";
  let attract = true;
  let ghostClock = 0;
  let ghostOffset = 0;
  let countT = 0;
  let countShown = -1;
  let hitstop = 0;
  let finishedRuns = 0;
  let tiltOn = false;
  let reduced = reducedQuery.matches;
  let lastPoint = null;
  let lastGhostPoint = null;
  let runGhost = null;
  let previousBest = best;

  const frame = newFrame();
  const ghostFrame = newFrame();
  const point = [0, 0, 0];
  const ghostPoint = [0, 0, 0];
  const v3 = { x: 0, y: 0, z: 0 };
  const heading = world.chase.camera.position.clone();
  const up = heading.clone();
  const posVec = heading.clone();
  const ghostVec = heading.clone();
  const screenVec = heading.clone();
  const tumbleAxis = heading.clone().set(0.6, 0.2, 0.77).normalize();

  const input = createInput({
    onStart: () => {
      if (screen === "title" || screen === "result") beginRun();
    },
    onRestart: () => {
      if (screen === "run" || screen === "countdown" || screen === "result") beginRun();
    },
    onBack: () => {
      if (screen === "run" || screen === "countdown" || screen === "result") showTitle();
    },
  });

  document.getElementById("start").addEventListener("click", beginRun);
  document.getElementById("again").addEventListener("click", beginRun);
  document.getElementById("restart").addEventListener("click", () => {
    beginRun();
    canvas.focus({ preventScroll: true });
  });
  document.getElementById("sound").addEventListener("click", () => {
    synth.start();
    synth.enabled = !synth.enabled;
    saveSetting("sound", synth.enabled);
    hud.sound(synth.enabled);
  });
  document.getElementById("tilt").addEventListener("click", async () => {
    tiltOn = await input.enableTilt(!tiltOn);
    saveSetting("tilt", tiltOn);
    hud.offerTilt(true, tiltOn);
  });

  // Framing: on the title and result screens the marble sits clear of the card.
  const frameFor = () => {
    if (screen === "run" || screen === "countdown") return [0, 0];
    const w = innerWidth;
    const h = innerHeight;
    if (h <= 520 && w > h) return [-0.2, 0.04];
    if (w >= 900 && h >= 520) return [-Math.min(0.2, 210 / w + 0.04), 0.03];
    return [0, 0.25];
  };

  // The live run behind the title starts where the demo driver's first nine seconds spend longest near top speed,
  // so the wide lens, the radial blur, and the speed lines all show before the first run.
  const attractStart = (() => {
    const sim = new Rail(track);
    const driver = new Autopilot(track, 1);
    let pick = 80;
    let most = -1;
    for (let s0 = 30; s0 < track.length - 520; s0 += 40) {
      sim.reset(s0);
      sim.v = ATTRACT_SPEED;
      sim.checkpoint = s0;
      let score = 0;
      for (let i = 0; i < 540 && !sim.finished; i += 1) {
        sim.step(STEP, driver.steer(sim), true);
        if (sim.events.some((e) => e.type === "fall")) {
          score = -1;
          break;
        }
        sim.events.length = 0;
        if (sim.v > TUNING.topSpeed * 0.86) score += i < 150 ? 2 : 1;
      }
      if (score > most) {
        most = score;
        pick = s0;
      }
    }
    return pick;
  })();

  // Until there is a best to race, the run behind the title races a demo ghost: the driver on a looser line from
  // the same start, so the see-through marble and its trail roll beside the demo marble.
  const demoGhost = (() => {
    const sim = new Rail(track);
    const driver = new Autopilot(track, 0.85);
    const tape = new GhostRecorder();
    sim.reset(attractStart);
    sim.v = ATTRACT_SPEED;
    sim.checkpoint = attractStart;
    while (!sim.finished && !sim.coasting && sim.s < track.length - 5 && sim.time < 300) {
      sim.step(STEP, driver.steer(sim), true);
      sim.events.length = 0;
      if (!sim.falling) tape.record(sim.time, sim.s, sim.u, sim.height(), sim.v);
    }
    return new GhostPlayer(tape.finish());
  })();

  function startAttract() {
    attract = true;
    const startS = attractStart;
    player.reset(startS);
    player.v = ATTRACT_SPEED;
    player.checkpoint = startS;
    player.gate = track.gates.filter((g) => g.s <= startS).length;
    pilot = new Autopilot(track, 1);
    runGhost = ghost || demoGhost;
    ghostOffset = 0;
    ghostClock = 0;
    world.ghost.show(Boolean(runGhost));
    world.ghost.reset();
    world.effects.clearConfetti();
    lastPoint = null;
    lastGhostPoint = null;
    placeNow(true);
  }

  function showTitle() {
    screen = "title";
    hud.screen("title");
    hud.count(null);
    hud.showBest(best);
    startAttract();
    world.chase.frame(...frameFor());
  }

  function beginRun() {
    synth.start();
    screen = "countdown";
    attract = false;
    hud.screen("countdown");
    previousBest = best;
    runGhost = ghost;
    hud.reset(Boolean(runGhost));
    player.reset(0);
    recorder.reset();
    input.clear();
    ghostClock = 0;
    ghostOffset = 0;
    world.ghost.show(Boolean(runGhost));
    world.ghost.reset();
    world.effects.clearConfetti();
    countT = 0;
    countShown = -1;
    lastPoint = null;
    lastGhostPoint = null;
    placeNow(true);
    world.chase.frame(0, 0);
    canvas.focus({ preventScroll: true });
  }

  function finishRun(time) {
    screen = "result";
    finishedRuns += 1;
    const splits = player.splits.slice(0, track.gates.length);
    const medal = medalFor(time, medals);
    const isBest = !previousBest || time < previousBest.time;
    if (isBest) {
      best = { time, splits, name: config.racerName, ghost: recorder.finish() };
      saveBest(seed, lengthName, best);
      ghost = new GhostPlayer(best.ghost);
    }
    hud.finishTick();
    hud.screen("result");
    hud.result({ time, splits, previous: previousBest, medal, isBest });
    hud.offerTilt(coarse && input.tiltAvailable, tiltOn);
    synth.finish(medal);
    frameAt(track, track.length, frame);
    placeOnTrack(track, track.length, 0, null, frame, point);
    world.effects.finish(point, frame);
    world.track.flashGate(track.gates.length + 1);
    world.chase.frame(...frameFor());
    player.finished = false;
    player.coasting = true;
  }

  // Applies the rail's events to sound, effects, camera, and the HUD.
  function handleEvents() {
    for (const e of player.events) {
      if (e.type === "boost") {
        world.effects.boost(point, frame);
        if (!attract) synth.boost();
        world.chase.punch(0.12);
      } else if (e.type === "launch") {
        world.marble.squash(1.18);
      } else if (e.type === "land") {
        world.effects.landing(point, frame, e.impact);
        world.marble.squash(0.8);
        world.chase.punch(Math.min(0.35, 0.1 + e.impact * 0.015));
        if (!attract) synth.land(e.impact);
      } else if (e.type === "gate") {
        world.track.flashGate(e.index + 1);
        if (!attract) {
          synth.gate(e.index);
          const then = previousBest?.splits?.[e.index];
          hud.gate(e.index, e.time, typeof then === "number" ? e.time - then : null);
        }
      } else if (e.type === "fall") {
        if (!reduced) hitstop = 0.09;
        world.chase.punch(0.65);
        world.chase.hold = true;
        if (!attract) synth.fall();
      } else if (e.type === "respawn") {
        world.chase.hold = false;
        placeNow(true);
      } else if (e.type === "finish") {
        if (!attract) finishRun(e.time);
      }
    }
    player.events.length = 0;
  }

  function placeNow(snap) {
    frameAt(track, player.s, frame);
    player.position(point);
    v3.x = point[0];
    v3.y = point[1];
    v3.z = point[2];
    if (snap) world.chase.snap(v3, frame);
  }

  const fixed = (dt) => {
    if (hitstop > 0) {
      hitstop -= dt;
      return;
    }
    if (screen === "countdown") {
      countT += dt;
      const beat = Math.floor(countT / COUNT_BEAT);
      if (beat !== countShown && beat <= 3) {
        countShown = beat;
        hud.count(beat < 3 ? String(3 - beat) : "Go");
        synth.countdown(beat === 3);
      }
      if (countT >= COUNT_BEAT * 3) {
        screen = "run";
        hud.screen("run");
        setTimeout(() => {
          if (screen === "run") hud.count(null);
        }, 650);
      }
      return;
    }
    if (screen === "title" && attract) {
      player.step(dt, pilot.steer(player), reduced);
      ghostClock += dt;
      if (player.coasting || player.finished || player.s > track.length - 5) startAttract();
    } else if (screen === "run") {
      player.step(dt, autoDrive ? pilot.steer(player) : input.steer(dt), reduced);
      ghostClock = player.time;
      if (!player.finished && !player.falling) recorder.record(player.time, player.s, player.u, player.height(), player.v);
    } else if (screen === "result") {
      player.step(dt, pilot.steer(player), true);
      ghostClock += dt;
    }
    handleEvents();
  };

  const watch = new FrameWatch((step) => world.stepDown(step));

  const render = (dt) => {
    watch.push(dt * 1000);
    frameAt(track, player.s, frame);
    player.position(point);
    v3.x = point[0];
    v3.y = point[1];
    v3.z = point[2];
    posVec.set(point[0], point[1], point[2]);

    // The marble: placed, rolled by the distance it moved, tumbling while it falls.
    world.marble.group.position.copy(posVec);
    if (player.falling) {
      world.marble.spin.rotateOnWorldAxis(tumbleAxis, dt * 14);
    } else if (lastPoint) {
      const dist = posVec.distanceTo(lastPoint);
      heading.set(frame.t[0], frame.t[1], frame.t[2]);
      up.set(frame.n[0], frame.n[1], frame.n[2]);
      world.marble.roll(Math.min(dist, 3), heading, up);
    }
    lastPoint = lastPoint || posVec.clone();
    lastPoint.copy(posVec);
    world.marble.update(dt, reduced);
    world.marble.contact.visible = !player.falling;
    if (!player.falling) world.marble.shadow(posVec, frame, Math.max(0, player.height()), player.u);

    // The ghost, replayed from its samples.
    let ghostS = null;
    if (runGhost && world.ghost.group.visible) {
      // Behind the title the ghost rolls a little ahead of the demo marble, in view; in a run it keeps its own time.
      const ghostTime = attract ? runGhost.timeAt(Math.min(track.length, player.s + GHOST_LEAD)) : Math.max(0, ghostClock + ghostOffset);
      const sample = runGhost.at(ghostTime);
      ghostS = sample.s;
      frameAt(track, sample.s, ghostFrame);
      placeOnTrack(track, sample.s, sample.u, null, ghostFrame, ghostPoint);
      ghostPoint[1] += sample.h;
      ghostVec.set(ghostPoint[0], ghostPoint[1], ghostPoint[2]);
      const moved = lastGhostPoint ? Math.min(3, ghostVec.distanceTo(lastGhostPoint)) : 0;
      lastGhostPoint = lastGhostPoint || ghostVec.clone();
      lastGhostPoint.copy(ghostVec);
      world.ghost.place(ghostVec, ghostFrame, moved);
    }

    world.chase.update(dt, v3, frame, player.falling ? 0 : player.v, TUNING.topSpeed);
    if (runGhost) world.ghost.fade(world.chase.camera.position);
    world.lights.follow(posVec);
    const fast = Math.max(0, Math.min(1, (player.v / TUNING.topSpeed - 0.8) / 0.2));
    world.effects.update(dt, world.chase.camera, player.falling ? 0 : fast, player.v);
    if (world.post) {
      world.post.setSpeed(reduced ? 0 : fast);
      screenVec.copy(posVec).project(world.chase.camera);
      world.post.setCenter(screenVec.x * 0.5 + 0.5, screenVec.y * 0.5 + 0.5);
    }
    world.track.update(dt);

    if (screen === "run" || screen === "countdown") {
      const jumpAhead = track.gaps.some((g) => g.s0 - player.s > 0 && g.s0 - player.s < 110);
      let delta = null;
      if (runGhost && screen === "run" && player.s > 5) delta = player.time - runGhost.timeAt(player.s);
      hud.frame({
        time: player.time,
        s: Math.max(0, player.s),
        ghostS: runGhost ? ghostS : null,
        delta,
        speed: player.falling ? 0 : player.v,
        topSpeed: TUNING.topSpeed,
        jump: jumpAhead && screen === "run",
        jumpMin: JUMP_MIN,
      });
    }
    synth.roll(player.v, !player.air && !player.falling && screen !== "title" && screen !== "countdown");
    world.render();
  };

  window.addEventListener("resize", () => {
    world.resize();
    world.chase.frame(...frameFor());
  });
  reducedQuery.addEventListener("change", (e) => {
    reduced = e.matches;
    world.chase.reduced = reduced;
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    world.applyTokens(readTokens());
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) synth.suspend();
    else synth.resume();
  });

  if (loadSetting("tilt", false) && coarse) {
    input.enableTilt(true).then((ok) => {
      tiltOn = ok;
    });
  }

  showTitle();
  world.warm();
  startLoop({ fixed, frame: render });
}

