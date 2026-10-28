// Wires the page together: config, theme tokens, the world, the game, input, sound, and the HUD.
import { BulletPool } from "./bullets.js";
import { createGame } from "./state.js";
import { createInput } from "./input.js";
import { createHud } from "./hud.js";
import { startLoop } from "./loop.js";
import { createRng } from "./rng.js";
import { load, save } from "./storage.js";
import { PATTERN_NAMES } from "./patterns.js";
import { createWorld } from "../scene/world.js";
import { readTokens } from "../scene/tokens.js";
import { firstTier, warmedTier, createProbe } from "../scene/quality.js";
import { createSound } from "../audio/sound.js";

const given = window.__APP_CONFIG__ || {};
const config = {
  title: typeof given.title === "string" && given.title.trim() ? given.title.trim() : "Shard Storm",
  playerName: typeof given.playerName === "string" && given.playerName.trim() ? given.playerName.trim() : "Pilot",
  shipColor: /^#[0-9a-f]{6}$/i.test(given.shipColor || "") ? given.shipColor : null,
  runSeconds: Number.isFinite(given.runSeconds) && given.runSeconds >= 10 ? given.runSeconds : 60,
  patterns: Array.isArray(given.patterns) && given.patterns.length ? given.patterns : PATTERN_NAMES,
};

const rootEl = document.documentElement;
if (config.shipColor) rootEl.style.setProperty("--ship", config.shipColor);
document.title = config.title;

const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const reducedMotion = () => reducedQuery.matches;
const canvas = document.getElementById("stage");
const app = document.querySelector(".app");
const veil = document.querySelector(".veil");
const titleBlock = document.querySelector(".title-block");
const startBlock = document.querySelector(".start-block");
const calloutEl = document.querySelector(".callout");
const resultCard = document.querySelector(".result-card");
const pauseCard = document.querySelector(".pause-card");
const demoBar = document.querySelector(".demo-bar");
const streakEl = document.querySelector(".hud-streak");
const titleScreen = document.querySelector(".title-screen");

let tokens = readTokens(config.shipColor);
let tier = firstTier();
const pool = new BulletPool(8192);
pool.limit = tier.bullets;
const world = createWorld({ canvas, tier, tokens, pool });
const hud = createHud(app);
const sound = createSound();
const fxRng = createRng(99);
let best = load("best", 0);
let resultAt = 0;
let bestStreak = load("bestStreak", 0);

/** Switches screens; the quiet zone follows the type of the new screen. */
function show(name) {
  hud.setScreen(name);
  requestAnimationFrame(updateQuiet);
}

hud.setTitle(config.title);
hud.setPlayer(config.playerName, best, bestStreak);
document.querySelector(".best dt").textContent = `${config.playerName}'s best`;

const game = createGame({
  pool,
  config,
  colors: tokens,
  reducedMotion,
  events: {
    attractWave(name, index, count) {
      if (hud.screen === "title") hud.callout(`Pattern ${index + 1} of ${count}`, name);
    },
    graze(x, y, heading, r, g, b) {
      const tint = { r, g, b };
      world.sparks.burst(x, y, 11, 30, tokens.spark, tint, fxRng, heading, 0.85);
      world.ship.graze();
    },
    grazeScored(mult, points, x, y, demo) {
      if (!demo) sound.play("graze", Math.pow(2, Math.min(24, (mult - 1) * 3.4) / 12), 0.42);
      hud.multPop();
      hud.scorePop(points, x, y, world.field);
    },
    wave(name, index, demo) {
      if (hud.screen !== "title") hud.callout(`Wave ${index + 1}`, name);
      if (demo) return;
      sound.play("wave", 1, 0.7);
      sound.droneTo(index);
    },
    cleared() {
      hud.callout(`${config.runSeconds} seconds survived`, "Storm cleared");
      sound.play("clear", 1, 0.8);
    },
    started() {
      show("run");
      hud.clearCallout();
      sound.play("start", 1, 0.6);
      sound.droneOn(0);
      input.clearDrag();
      offerFullscreen();
    },
    died(x, y) {
      show("dying");
      world.sparks.burst(x, y, 110, 58, tokens.ship, tokens.spark, fxRng);
      world.ship.hit();
      sound.play("death", 1, 0.9);
      sound.droneOff();
    },
    fade(v) {
      world.shared.uFade.value = v;
    },
    result(r) {
      const isBest = r.score > best;
      if (isBest) {
        best = r.score;
        save("best", best);
      }
      if (r.longest > bestStreak) {
        bestStreak = r.longest;
        save("bestStreak", bestStreak);
      }
      const g = game.state;
      hud.result(r, {
        best,
        isBest: isBest && r.score > 0,
        instant: reducedMotion(),
        kicker: `${config.playerName}, wave ${Math.max(1, g.wave + 1)}${g.waveName ? `: ${g.waveName}` : ""}`,
      });
      hud.setPlayer(config.playerName, best, bestStreak);
      show("result");
      resultAt = performance.now();
      hud.setShareLabel("Copy score");
    },
  },
});

const input = createInput(canvas, {
  press(e) {
    const mode = game.state.mode;
    if (mode === "attract" || mode === "result" || mode === "demo") {
      if (mode === "result" && (e.pointerType === "mouse" || performance.now() - resultAt < 900)) return;
      game.start();
    }
  },
  key(e) {
    const mode = game.state.mode;
    if ((e.code === "Space" || e.code === "Enter") && (mode === "attract" || mode === "result" || mode === "demo")) game.start();
    else if ((e.code === "Escape" || e.code === "KeyP") && mode === "run") pause("The storm waits for you.");
    else if ((e.code === "Escape" || e.code === "KeyP" || e.code === "Space") && mode === "paused") resume();
  },
});

function pause(line) {
  game.pause();
  if (game.state.mode !== "paused") return;
  document.querySelector('[data-bind="pause-line"]').textContent = line;
  show("paused");
  sound.droneOff();
}

function resume() {
  game.resume();
  show("run");
  sound.droneOn(Math.max(0, game.state.wave));
  input.clearDrag();
}

const canFullscreen = !!(rootEl.requestFullscreen && document.fullscreenEnabled);
app.classList.toggle("no-fullscreen", !canFullscreen);
let offered = false;
const offer = document.querySelector(".offer");
function toggleFullscreen() {
  if (!canFullscreen) return;
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else rootEl.requestFullscreen({ navigationUI: "hide" }).catch(() => {});
}
function offerFullscreen() {
  if (offered || !canFullscreen || document.fullscreenElement || !matchMedia("(pointer: coarse)").matches) return;
  offered = true;
  offer.classList.add("is-on");
  setTimeout(() => offer.classList.remove("is-on"), 4000);
}
document.addEventListener("fullscreenchange", () => app.classList.toggle("is-fullscreen", !!document.fullscreenElement));

// Browsers let sound start only on a finished gesture: a finger lifting, a click, or a key.
for (const type of ["pointerup", "keydown", "click"]) addEventListener(type, () => sound.unlock(), { capture: true });

app.addEventListener("click", async (e) => {
  const button = e.target.closest("button[data-action]");
  if (!button) return;
  sound.play("tick", 1, 0.35);
  const action = button.dataset.action;
  if (action === "start" || action === "again") game.start();
  else if (action === "pause") pause("The storm waits for you.");
  else if (action === "resume") resume();
  else if (action === "quit") {
    game.quit();
    sound.droneOff();
  } else if (action === "fullscreen") {
    offer.classList.remove("is-on");
    toggleFullscreen();
  }
  else if (action === "sound") {
    sound.setMuted(!sound.muted);
    syncSound();
  } else if (action === "share") share();
});

function syncSound() {
  const button = document.querySelector('[data-action="sound"]');
  button.setAttribute("aria-pressed", String(!sound.muted));
  button.setAttribute("aria-label", sound.muted ? "Sound on" : "Sound off");
}
syncSound();

async function share() {
  const r = game.state.result;
  if (!r) return;
  const line = `${config.playerName} scored ${r.score.toLocaleString("en-US")} in ${config.title}: ${r.grazes} grazes, longest streak ${r.longest}.`;
  try {
    await navigator.clipboard.writeText(line);
    hud.setShareLabel("Score copied");
  } catch {
    hud.toast(line);
  }
}

// The quiet zone dims the storm behind the type so the title, the demo's bar and streak, and the cards always read.
// A real run never dims its field: every shard that can hit the ship stays in full view.
let quietTarget = 0;
function updateQuiet() {
  const screen = hud.screen;
  let rects = [];
  if (screen === "title") {
    const pad = Math.min(innerWidth, innerHeight) * 0.04;
    rects = [hud.ndcRect(titleBlock, pad, pad), hud.ndcRect(startBlock, 12, 12), hud.ndcRect(calloutEl, 16, 10)];
  } else if (screen === "demo") rects = [hud.ndcRect(demoBar, 16, 16), hud.ndcRect(streakEl, 24, 12)];
  else if (screen === "result") rects = [hud.ndcRect(resultCard, 12, 12)];
  else if (screen === "paused") rects = [hud.ndcRect(pauseCard, 12, 12)];
  world.shared.uQuiet.value.forEach((v, i) => (rects[i] ? v.set(...rects[i]) : v.set(-3, -3, -3, -3)));
  quietTarget = rects.length ? 1 : 0;
}

let lastW = 0;
let lastH = 0;
function resize() {
  const w = innerWidth;
  const h = innerHeight;
  if (w === lastW && h === lastH) return;
  const turned = lastW && (w > h) !== (lastW > lastH);
  lastW = w;
  lastH = h;
  const field = world.resize(w, h);
  game.setField(field);
  const [ex, ey] = game.eye();
  world.setEye(ex, ey);
  updateQuiet();
  if (turned && game.state.mode === "run") pause("Paused while the screen turned.");
}
addEventListener("resize", resize);
resize();

function relook() {
  tokens = readTokens(config.shipColor);
  game.setColors(tokens);
  world.setLook(tokens);
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", relook);

// The page opens on the title over a demo run already seven seconds in; the title then gives the screen to the run
// and its HUD, and comes back for a few seconds between stretches of the demo. How long those seven seconds take to
// simulate is the first measure of the device: a slow one opens a tier or two lower, before any frame is drawn.
const TITLE_HOLD_MS = 900;
const DEMO_HOLD_MS = 26000;
const TITLE_BACK_MS = 6000;
const warmFrom = performance.now();
game.demo(7);
const warmed = warmedTier(tier, performance.now() - warmFrom);
if (warmed !== tier) {
  tier = warmed;
  world.setTier(tier);
  game.setField(world.field);
  pool.count = Math.min(pool.count, pool.limit);
}
hud.setCadence(tier.hudEvery);
let cycleAt = performance.now() + TITLE_HOLD_MS;
updateQuiet();

const probe = createProbe(tier, (next) => {
  tier = next;
  world.setTier(next);
  hud.setCadence(next.hudEvery);
});

/** The title and the demo run take turns while nobody is playing. */
function cycle(now) {
  if (game.state.mode !== "demo" || now < cycleAt) return;
  if (hud.screen === "title") {
    if (game.demoSeconds > config.runSeconds * 0.6) game.demo();
    show("demo");
    cycleAt = now + DEMO_HOLD_MS;
  } else if (hud.screen === "demo") {
    titleScreen.classList.add("is-back");
    show("title");
    cycleAt = now + TITLE_BACK_MS;
  }
}

let quiet = 1;
world.shared.uQuietAmt.value = 1;
function draw(elapsed) {
  const g = game.state;
  probe.sample(elapsed * 1000);
  if (g.mode === "attract" || g.mode === "result" || g.mode === "paused") {
    const [ex, ey] = game.eye();
    world.setEye(ex, ey);
  }
  quiet += (quietTarget - quiet) * Math.min(1, elapsed * 6);
  world.shared.uQuietAmt.value = quiet;
  if (g.mode === "run" || g.mode === "demo" || g.mode === "result") world.shared.uFade.value = game.fadeLevel;
  const slow = g.slow && (g.mode === "run" || g.mode === "demo");
  veil.classList.toggle("is-slow", slow);
  app.classList.toggle("is-slow", slow);
  const still = reducedMotion();
  const shake = still ? 0 : g.trauma * g.trauma;
  const n = g.time * 31;
  world.ship.update(g.shipX, g.shipY, elapsed, g.time, g.shipVisible && !(g.mode === "dying" && g.deathClock > 0.12));
  world.ship.setSlow(slow);
  world.render({
    time: g.time,
    fxTime: g.fxTime,
    pulse: g.pulse,
    drift: still ? 0.4 : 1,
    dolly: g.dolly,
    fx: g.focusX,
    fy: g.focusY,
    sx: shake * 1.4 * Math.sin(n * 1.7) * Math.cos(n * 0.6),
    sy: shake * 1.4 * Math.sin(n * 1.3 + 2),
    roll: shake * 0.035 * Math.sin(n * 0.9 + 4),
    shift: g.shift > 0 && !still ? (world.mode === "glow" ? 0.0042 : 0.003) : 0,
  });
  if (g.mode === "run" || g.mode === "demo" || g.mode === "dying" || g.mode === "paused") hud.run(g);
  const now = performance.now();
  hud.tick(now);
  cycle(now);
}

// One frame drawn before the page finishes loading, and every program a tier step or a graze can need compiled with
// it, so the first animated frames are on time and no later frame pays for a shader.
world.prewarm();
draw(1 / 60);
startLoop({
  step(dt) {
    game.step(dt, input);
  },
  render: draw,
  hidden() {
    if (game.state.mode === "run") pause("The storm waits for you.");
  },
});
