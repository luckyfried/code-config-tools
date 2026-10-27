// The game: reads the config, builds the stage (or the CSS board without WebGL), plays the scripted climb until the
// person takes over, then runs their game: swipe or keys, merges, a new cube, one undo, the 2048 moment, and a board
// with no moves left. Saves on this device after every move.
import { canMove, cloneBoard, highest, move, newGame, spawn } from "./board.js";
import { createDemo } from "./demo.js";
import { createInput } from "./input.js";
import { forget, load, save } from "./store.js";
import { createAudio } from "../audio.js";
import { createHud } from "../ui/hud.js";
import { createMoment } from "../ui/moment.js";
import { createSettings } from "../ui/settings.js";
import { textFor } from "../scene/labels.js";
import { pickTier } from "../scene/quality.js";
import { createWorld } from "../scene/world.js";

const THEMES = ["night-gold", "sorbet", "cyber"];
const config = Object.assign({ title: "Merge Cubes", size: 4, theme: "night-gold", labels: "numbers", sound: true }, window.__APP_CONFIG__ || {});
const settings = Object.assign({ appearance: "auto" }, load("settings", {}));
const coarse = matchMedia("(pointer: coarse)").matches;
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const labels = Array.isArray(config.labels) && config.labels.length === 12 ? config.labels.map(String) : "numbers";

const clampSize = (n) => Math.min(6, Math.max(3, Math.round(Number(n) || 4)));
let size = clampSize(settings.size ?? config.size);
let theme = THEMES.includes(settings.theme) ? settings.theme : config.theme;

const root = document.body;
const hud = createHud(root);
const moment = createMoment(root);
const audio = createAudio({ enabled: settings.sound ?? config.sound !== false });
const live = root.querySelector("[data-live]");
const slotEl = root.querySelector("[data-slot]");

// While the "Get this app" bar is up, the page keeps room for it under the buttons (hud.css).
const toastRoom = () => document.documentElement.toggleAttribute("data-toast", Boolean(document.querySelector(".code-config-toast")));
new MutationObserver(toastRoom).observe(document.body, { childList: true });
toastRoom();

document.title = config.title;
root.querySelector("[data-title]").textContent = config.title;
hud.setLabels(labels);

let world = null;
let mode = "demo"; // demo | play | won | over | busy
let game = null; // { board, prev, won }
let demo = null;
let demoTimer = 0;
let demoRun = 0;

const numbers = new Intl.NumberFormat("en-US");
const fmt = (n) => numbers.format(n);
const bestOf = (n) => load(`best:${n}`, 0);
const isDark = () => document.documentElement.dataset.theme === "dark" || (document.documentElement.dataset.theme !== "light" && darkQuery.matches);

let laidOut = "";
function layout() {
  const r = slotEl.getBoundingClientRect();
  const rect = { left: r.left, top: r.top, width: r.width, height: r.height };
  const key = `${rect.left},${rect.top},${rect.width},${rect.height},${innerWidth},${innerHeight}`;
  if (key === laidOut) return;
  laidOut = key;
  const style = document.documentElement.style;
  style.setProperty("--slot-left", `${rect.left}px`);
  style.setProperty("--slot-top", `${rect.top}px`);
  style.setProperty("--slot-width", `${rect.width}px`);
  style.setProperty("--slot-height", `${rect.height}px`);
  // Where the tray landed, so the moment card can sit clear of it.
  const tray = world?.setSlot(rect) ?? rect;
  style.setProperty("--tray-top", `${tray.top}px`);
  style.setProperty("--tray-bottom", `${tray.top + tray.height}px`);
  style.setProperty("--tray-left", `${tray.left}px`);
  style.setProperty("--tray-right", `${tray.left + tray.width}px`);
}

function showScores(board, gained = 0, opts = {}) {
  hud.setScore(board.score, gained, opts);
  hud.setHighest(highest(board));
  const best = bestOf(size);
  if (mode === "demo") {
    // The board that plays itself counts as a run: its Best keeps pace with its score once the score passes it.
    if (board.score > best) hud.setBest(board.score, false, { live: true, floor: best });
    else hud.setBest(best, false);
    return;
  }
  if (board.score > best) {
    save(`best:${size}`, board.score);
    hud.setBest(board.score, true, { live: true, floor: best });
  } else hud.setBest(best, false);
}

function persist() {
  if (game) save(`game:${size}`, game);
}

// The scripted climb ------------------------------------------------------------------------------------------

function demoHint() {
  hud.setHint(coarse ? "Swipe to play" : "Press an arrow key to play");
}

function startDemo() {
  mode = "demo";
  game = null;
  const run = ++demoRun;
  demo = createDemo(size);
  hud.setUndo(false);
  demoHint();
  world.show(demo.board, { intro: true });
  showScores(demo.board, 0, { instant: true });
  demoTimer = setTimeout(() => demoStep(run, demo.board), 1150);
}

function demoStep(run, board) {
  if (run !== demoRun || mode !== "demo") return;
  const step = demo.next(board);
  if (!step) {
    world.setDim(0.5);
    demoTimer = setTimeout(() => restartDemo(run), 1400);
    return;
  }
  const result = move(board, step.dir);
  const placed = step.spawnAt ? spawn(result.board, Math.random, step.spawnAt, step.spawnValue) : spawn(result.board, step.random);
  world.play(result, placed.tile, step.dir);
  showScores(placed.board, result.gained);
  const top = result.merges.find((m) => m.value >= 2048);
  if (top) {
    demoTimer = setTimeout(() => {
      if (run !== demoRun) return;
      world.celebrate(top.id);
      hud.setHint("");
      moment.show({
        kicker: "Made it to",
        title: textFor(2048, labels),
        line: coarse ? "Your turn. Swipe anywhere to start." : "Your turn. Press an arrow key to start.",
        first: { label: "Play", onClick: () => takeOver() },
        focus: false,
      });
      demoTimer = setTimeout(() => {
        if (run !== demoRun) return;
        moment.hide();
        world.settle();
        demoHint();
        demoTimer = setTimeout(() => restartDemo(run), 700);
      }, 3100);
    }, 260);
    return;
  }
  if (!canMove(placed.board)) {
    demoTimer = setTimeout(() => restartDemo(run), 1200);
    return;
  }
  demoTimer = setTimeout(() => demoStep(run, placed.board), size === 4 ? 520 : 560);
}

async function restartDemo(run) {
  if (run !== demoRun || mode !== "demo") return;
  await world.clear();
  world.setDim(0);
  if (run !== demoRun || mode !== "demo") return;
  startDemo();
}

function stopDemo() {
  demoRun += 1;
  clearTimeout(demoTimer);
  hud.setHint("");
  moment.hide();
  world.settle();
  world.setDim(0);
}

async function takeOver() {
  if (mode !== "demo") return;
  stopDemo();
  await startGame(null);
}

// The person's game ---------------------------------------------------------------------------------------------

async function startGame(saved) {
  mode = "busy";
  moment.hide();
  world.settle();
  world.setDim(0);
  await world.clear();
  game = saved ?? { board: newGame(size, Math.random), prev: null, won: false };
  world.show(game.board, { intro: true });
  mode = "play";
  hud.setUndo(Boolean(game.prev));
  hud.disarmNew();
  showScores(game.board, 0, { instant: true });
  persist();
  if (!canMove(game.board)) setTimeout(() => gameOver(), 600);
}

function slide(dir) {
  if (mode === "demo") {
    takeOver();
    return;
  }
  if (mode === "won") {
    keepGoing();
    return;
  }
  if (mode !== "play") return;
  audio.unlock();
  hud.disarmNew();
  const result = move(game.board, dir);
  if (!result.moved) {
    world.bump(dir);
    audio.thud();
    return;
  }
  const placed = spawn(result.board, Math.random);
  game.prev = { board: cloneBoard(game.board), won: game.won };
  game.board = placed.board;
  world.play(result, placed.tile, dir);
  audio.merges(result.merges, size);
  if (placed.tile) audio.drop();
  showScores(game.board, result.gained);
  hud.setUndo(true);
  const top = !game.won && result.merges.find((m) => m.value >= 2048);
  if (top) {
    game.won = true;
    mode = "won";
    persist();
    setTimeout(() => celebrate(top.id), 260);
    return;
  }
  persist();
  if (!canMove(game.board)) {
    mode = "over";
    setTimeout(() => gameOver(), 420);
  }
}

function celebrate(id) {
  world.celebrate(id);
  audio.win();
  live.textContent = `You made ${textFor(2048, labels)}.`;
  moment.show({
    kicker: "You made",
    title: textFor(2048, labels),
    line: `Keep going for ${textFor(4096, labels)}.`,
    first: { label: "Keep going", onClick: () => keepGoing() },
    second: { label: "New game", onClick: () => requestNew(true) },
  });
}

function keepGoing() {
  if (mode !== "won") return;
  moment.hide();
  world.settle();
  mode = "play";
  if (!canMove(game.board)) {
    mode = "over";
    setTimeout(() => gameOver(), 420);
  }
}

function gameOver() {
  if (mode !== "over" && mode !== "play") return;
  mode = "over";
  world.setDim(0.6);
  audio.thud();
  const best = bestOf(size);
  const isBest = game.board.score > 0 && game.board.score >= best;
  live.textContent = `No moves left. Score ${fmt(game.board.score)}.`;
  moment.show({
    kicker: "No moves left",
    title: fmt(game.board.score),
    line: isBest ? "That is your best yet." : `Your best is ${fmt(best)}.`,
    first: { label: "Try again", onClick: () => requestNew(true) },
    second: game.prev ? { label: "Undo", onClick: () => undo() } : null,
  });
}

function undo() {
  if (!game?.prev || (mode !== "play" && mode !== "over" && mode !== "won")) return;
  audio.unlock();
  moment.hide();
  world.settle();
  world.setDim(0);
  game.board = game.prev.board;
  game.won = game.prev.won;
  game.prev = null;
  world.show(game.board);
  mode = "play";
  hud.setUndo(false);
  showScores(game.board, 0);
  persist();
}

function requestNew(now = false) {
  audio.unlock();
  if (mode === "demo") {
    takeOver();
    return;
  }
  if (mode === "busy") return;
  const underway = game && game.board.score > 0 && mode === "play";
  if (underway && !now && !hud.armed) {
    hud.armNew();
    return;
  }
  hud.disarmNew();
  forget(`game:${size}`);
  startGame(null);
}

// Settings ------------------------------------------------------------------------------------------------------

function saveSettings() {
  save("settings", settings);
}

function swapTheme(name) {
  const link = document.getElementById("theme");
  const next = name === config.theme ? "./theme.css" : `./themes/${name}.css`;
  if (link.getAttribute("href") === next) {
    world.restyle();
    return;
  }
  link.addEventListener("load", () => world.restyle(), { once: true });
  link.setAttribute("href", next);
}

const sheet = createSettings(root, {
  get: () => ({ size, theme, appearance: settings.appearance, sound: audio.enabled, best: bestOf(size), dark: isDark() }),
  onSize(n) {
    if (n === size) return;
    persist();
    stopDemoIfRunning();
    size = n;
    settings.size = n;
    saveSettings();
    const saved = load(`game:${size}`, null);
    game = saved?.board?.tiles?.length ? saved : { board: newGame(size, Math.random), prev: null, won: false };
    world.setSize(size, game.board);
    layout();
    mode = "play";
    hud.setUndo(Boolean(game.prev));
    showScores(game.board, 0, { instant: true });
    persist();
  },
  onTheme(name) {
    theme = name;
    settings.theme = name;
    saveSettings();
    swapTheme(name);
  },
  onAppearance(value) {
    settings.appearance = value;
    saveSettings();
    if (value === "auto") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = value;
    world.restyle();
  },
  onSound(on) {
    settings.sound = on;
    saveSettings();
    audio.setEnabled(on);
    if (on) audio.unlock();
  },
  onResetBest() {
    save(`best:${size}`, 0);
    hud.setBest(0, false);
  },
  onOpen() {
    clearTimeout(demoTimer);
  },
  onClose() {
    if (mode === "demo") {
      const run = demoRun;
      startDemoAfterSettings(run);
    }
  },
});

function stopDemoIfRunning() {
  if (mode === "demo") stopDemo();
}

function startDemoAfterSettings(run) {
  if (run !== demoRun) return;
  restartDemo(run);
}

// Start ---------------------------------------------------------------------------------------------------------

/** The stage, built before the page finishes loading so the lit tray is in its first frame; the CSS board without WebGL. */
function makeWorld() {
  const canvas = root.querySelector("[data-stage]");
  try {
    const probe = document.createElement("canvas").getContext("webgl2");
    if (!probe) throw new Error("no WebGL2");
    return createWorld({ canvas, tierName: pickTier(), size, labelSet: labels, reduced: reducedQuery.matches });
  } catch {
    canvas.hidden = true;
    return import("../render/dom.js").then(({ createDomWorld }) => createDomWorld({ el: root.querySelector("[data-dom-board]"), size, labelSet: labels }));
  }
}

const FONTS = ['760 100px "Bricolage Grotesque"', '600 16px "Instrument Sans"'];
const fontsReady = () => !document.fonts || FONTS.every((f) => document.fonts.check(f));

async function boot(made) {
  // The cube faces are drawn in the display face, so the board waits for it (it is preloaded, so this is rarely a wait).
  if (!fontsReady()) {
    await Promise.race([Promise.all(FONTS.map((f) => document.fonts.load(f))), new Promise((resolve) => setTimeout(resolve, 1200))]);
  }
  world = await made;
  world.prepareFaces?.();
  layout();
  addEventListener("resize", () => layout());
  // The tray reframes as the room kept for the "Get this app" bar opens and closes.
  new ResizeObserver(() => layout()).observe(slotEl);
  darkQuery.addEventListener("change", () => world.restyle());

  createInput({
    onMove: (dir) => {
      audio.unlock();
      slide(dir);
    },
    onUndo: () => undo(),
    onNew: () => requestNew(),
    onAny: () => audio.unlock(),
    blocked: () => sheet.open || mode === "busy",
  });
  root.querySelector("[data-undo]").addEventListener("click", () => undo());
  root.querySelector("[data-new]").addEventListener("click", () => requestNew());
  root.querySelector("[data-open-settings]").addEventListener("click", () => sheet.show());
  addEventListener("keydown", (event) => {
    if (event.key === "Escape" && moment.open && mode === "won") keepGoing();
  });

  const saved = load(`game:${size}`, null);
  if (saved?.board?.tiles?.length && saved.board.size === size) {
    game = saved;
    mode = "play";
    world.show(game.board, { intro: true });
    hud.setUndo(Boolean(game.prev));
    showScores(game.board, 0, { instant: true });
    if (!canMove(game.board)) setTimeout(() => gameOver(), 900);
  } else {
    startDemo();
  }
}

function run() {
  let last = performance.now();
  const frame = (now) => {
    const ms = now - last;
    last = now;
    world?.frame(Math.min(0.05, ms / 1000), ms);
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
  document.addEventListener("visibilitychange", () => {
    last = performance.now();
  });
}

const made = makeWorld();
if (!(made instanceof Promise)) {
  // Laid out, compiled, and drawn once now, before the load event, so the first frame shows the lit tray.
  world = made;
  layout();
  world.warm();
  if (fontsReady()) world.prepareFaces();
  world.frame(0, 16);
}
run();
boot(made);
