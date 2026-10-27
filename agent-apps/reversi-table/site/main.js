// The table's controller: reads the config, builds the 3D table (or the 2D one when WebGL is missing), runs the
// opening replay under the setup panel, and plays the game: turns, the computer's replies from its worker, passes,
// undo, hints, the counting wave, and saving to the device.
import {
  BLACK, WHITE, EMPTY, initialBoard, legalMoves, play, nextToMove, replay, count, winner, opponent, flipLines,
} from "./game/reversi.js";
import { Table } from "./game/table.js";
import { DEMO_MOVES, DEMO_FAST, DEMO_TIMING } from "./game/demo.js";
import { loadGame, saveGame, loadPrefs, savePrefs } from "./game/state.js";
import { startLoop } from "./game/loop.js";
import { bindInput } from "./game/input.js";
import { createAudio } from "./audio.js";
import { createHud } from "./ui/hud.js";
import { readTokens } from "./scene/tokens.js";
import { pickTier, tierSettings, FrameWatch } from "./scene/quality.js";

const THEMES = ["lacquer-green", "walnut", "neon"];
const STRENGTH_NAMES = { 1: "Easy", 2: "Club", 3: "Master" };
const THINK_MS = 520;

// The config run.py writes; the page plays with sensible values when a key is missing.
function readConfig() {
  const raw = window.__APP_CONFIG__ || {};
  const players = raw.players && typeof raw.players === "object" ? raw.players : {};
  const isComputer = (name) => typeof name === "string" && name.trim().toLowerCase() === "computer";
  const black = typeof players.black === "string" && players.black.trim() ? players.black.trim() : "You";
  const white = typeof players.white === "string" && players.white.trim() ? players.white.trim() : "computer";
  const strength = [1, 2, 3].includes(raw.strength) ? raw.strength : 2;
  return {
    title: typeof raw.title === "string" && raw.title.trim() ? raw.title.trim() : "Reversi Table",
    black,
    white,
    blackComputer: isComputer(black),
    whiteComputer: isComputer(white),
    strength,
    theme: THEMES.includes(raw.theme) ? raw.theme : "lacquer-green",
    sound: raw.sound !== false,
  };
}

const isComputerName = (name) => name.trim().toLowerCase() === "computer";
const config = readConfig();
const prefs = { theme: config.theme, scheme: "auto", sound: config.sound, ...loadPrefs() };
if (!THEMES.includes(prefs.theme)) prefs.theme = config.theme;

const stage = document.getElementById("stage");
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const audio = createAudio({ enabled: prefs.sound });
const table = new Table({ reduced: reducedQuery.matches, onSound: (kind, index, pace) => audio.sound(kind, index, pace) });
let tokens = readTokens();
let view = null;

const game = {
  mode: "demo",
  opponent: config.blackComputer || config.whiteComputer ? "computer" : "friend",
  human: config.blackComputer ? WHITE : BLACK,
  strength: config.strength,
  moves: [],
  board: initialBoard(),
  toMove: BLACK,
  over: false,
  epoch: 0,
  searchId: 0,
  thinking: false,
};

const sideNames = () => ({ [BLACK]: tokens.sideDark, [WHITE]: tokens.sideLight });
const computerSide = () => (game.opponent === "computer" ? opponent(game.human) : EMPTY);
const isComputerTurn = () => game.mode === "play" && !game.over && game.toMove === computerSide();
const humanName = () => {
  const name = game.human === BLACK ? config.black : config.white;
  return isComputerName(name) ? "You" : name;
};

function players() {
  const sides = sideNames();
  if (game.mode === "demo") {
    // The replay's sides by color, each with the player the config names there, or "Computer".
    const player = (name) => (isComputerName(name) ? "Computer" : name);
    return { [BLACK]: { name: sides[BLACK], note: player(config.black) }, [WHITE]: { name: sides[WHITE], note: player(config.white) } };
  }
  if (game.opponent === "computer") {
    const out = {};
    out[game.human] = { name: humanName(), note: sides[game.human] };
    out[computerSide()] = { name: "Computer", note: `${STRENGTH_NAMES[game.strength]} strength` };
    return out;
  }
  // Two names in the config name the two people; a config made for the computer leaves both sides by color.
  const both = !config.blackComputer && !config.whiteComputer;
  const named = (color) => (both ? (color === BLACK ? config.black : config.white) : sides[color]);
  return {
    [BLACK]: { name: named(BLACK), note: named(BLACK) === sides[BLACK] ? "" : sides[BLACK] },
    [WHITE]: { name: named(WHITE), note: named(WHITE) === sides[WHITE] ? "" : sides[WHITE] },
  };
}

const nameOf = (color) => players()[color].name;

const hud = createHud({
  onStart: (choice) => startGame(choice),
  onUndo: () => undo(),
  onHint: () => hint(),
  onNew: () => openSetup(),
  onBack: () => closeSetup(),
  onSetupResize: () => {
    lastLayout = "";
    requestAnimationFrame(() => layout(false));
  },
  onAgain: () => startGame({ opponent: game.opponent, human: game.human, strength: game.strength }),
  onSettings: () => hud.openSettings(prefs),
  onTheme: (name) => setTheme(name),
  onScheme: (scheme) => setScheme(scheme),
  onSound: (on) => {
    prefs.sound = on;
    audio.setEnabled(on);
    savePrefs(prefs);
  },
});
hud.setTitle(config.title);

// ---- The engine worker ----------------------------------------------------------------------------------------

let worker = null;
const pending = new Map();
function engine(board, color, strength) {
  if (!worker) {
    worker = new Worker(new URL("./game/engine.worker.js", import.meta.url), { type: "module" });
    worker.addEventListener("message", (event) => {
      const done = pending.get(event.data.id);
      pending.delete(event.data.id);
      if (done) done(event.data);
    });
  }
  game.searchId += 1;
  const id = game.searchId;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    worker.postMessage({ id, board, color, strength });
  });
}

// ---- Layout -----------------------------------------------------------------------------------------------------

function freeRect(width, height, mode) {
  const pad = width < 760 ? 10 : 24;
  let top = Math.max(hud.mastheadBottom() + 8, pad);
  let bottom = height - pad;
  let left = pad;
  let right = width - pad;
  const railShown = game.mode === "play";
  const r = hud.railRect();
  if (railShown && r.height > 0 && r.top > height * 0.5) bottom = Math.min(bottom, r.top - 6);
  if (railShown && r.height > r.width && r.left > width * 0.6) right = Math.min(right, r.left - 8);
  if (hud.setupShown()) {
    const s = hud.setupRect();
    if (s.top > height * 0.3 && s.width > width * 0.8) bottom = Math.min(bottom, s.top - 4);
    else if (s.left > width * 0.4) right = Math.min(right, s.left - 8);
  }
  if (mode === "wide" && top < height * 0.18) top = Math.max(top, 16);
  return { x: left, y: top, width: Math.max(80, right - left), height: Math.max(80, bottom - top) };
}

let lastLayout = "";
function layout(immediate = false) {
  if (!view) return;
  const width = window.innerWidth;
  const height = window.innerHeight;
  const mode = width >= height * 1.02 ? "wide" : "tall";
  // Short landscape screens keep the bottom strip for the page's notes, so the cards go above the trays there.
  const cardsAbove = height <= 520;
  const rect = freeRect(width, height, mode);
  const key = `${width}x${height}:${mode}:${Math.round(rect.x)},${Math.round(rect.y)},${Math.round(rect.width)},${Math.round(rect.height)}`;
  if (key === lastLayout) return;
  lastLayout = key;
  view.frame({ width, height, rect, mode, cardsAbove, now: performance.now(), immediate });
  hud.placeCards(view.anchors());
  loop.wake();
}

// ---- The frame -----------------------------------------------------------------------------------------------

const watch = new FrameWatch((step) => view && view.stepDown(step));
let lastVersion = -1;
const loop = startLoop({
  step(now, dirty) {
    if (!view) return false;
    const moving = table.update(now);
    const camera = view.cameraMoving(now);
    const preview = table.preview !== null;
    if (moving || camera || dirty || preview || table.version !== lastVersion) {
      view.render(table, now);
      lastVersion = table.version;
    }
    if (camera) hud.placeCards(view.anchors());
    hud.setCounts(table.trayCount(BLACK, now), table.trayCount(WHITE, now));
    return moving || camera || preview;
  },
  onFrame: (ms) => watch.add(ms),
});

// ---- The opening replay ---------------------------------------------------------------------------------------

function startDemo() {
  game.mode = "demo";
  game.epoch += 1;
  const epoch = game.epoch;
  table.setBoard(initialBoard());
  hud.setPlayers(players());
  hud.setTurn(null);
  hud.setStatus("Replaying a finished game");
  hud.showRail(false);
  hud.hideResult();
  let board = initialBoard();
  let toMove = BLACK;
  let t = performance.now() + DEMO_TIMING.hold;
  DEMO_MOVES.forEach((square, i) => {
    const fast = i < DEMO_FAST;
    const at = t;
    if (!fast) {
      const mover = toMove;
      const flipsNow = board.slice();
      table.schedule(at - DEMO_TIMING.preview, () => {
        if (game.epoch !== epoch) return;
        const flips = flipLines(flipsNow, square, mover).flatMap((line) => line.squares);
        table.setPreview({ square, color: mover, flips });
      });
    }
    const result = play(board, square, toMove);
    const mover = toMove;
    table.schedule(at, (now) => {
      if (game.epoch !== epoch) return;
      // A late frame starts the move now rather than half-finished.
      table.place(square, mover, result.lines, Math.max(at, now - 16), fast ? DEMO_TIMING.fastPace : 1);
      if (!fast) hud.setTurn(opponent(mover));
    });
    const next = nextToMove(result.board, toMove);
    board = result.board;
    toMove = next.color;
    t += fast ? DEMO_TIMING.fastStep : DEMO_TIMING.slowStep;
    if (next.passed) {
      const passed = next.passed;
      table.schedule(at + 520, () => {
        if (game.epoch !== epoch) return;
        table.passShake(passed, at + 520);
        hud.toast(`${sideNames()[passed]} has no move`);
      });
      t += 320;
    }
  });
  const final = board;
  const endAt = t - DEMO_TIMING.slowStep + DEMO_TIMING.afterEnd;
  table.schedule(endAt, () => {
    if (game.epoch !== epoch) return;
    hud.setTurn(null);
    const done = table.endWave(final, endAt);
    const { black, white } = count(final);
    const win = winner(final);
    table.schedule(done - 900, () => {
      if (game.epoch !== epoch) return;
      hud.showResult(win === EMPTY ? "A draw" : `${sideNames()[win]} wins`, `${Math.max(black, white)} to ${Math.min(black, white)}`, false);
      hud.setStatus(win === EMPTY ? `A draw, ${black} to ${white}` : `${sideNames()[win]} won this one`);
    });
    table.schedule(done + DEMO_TIMING.rest, () => {
      if (game.epoch !== epoch) return;
      hud.hideResult();
      const cleared = table.syncTo(initialBoard(), done + DEMO_TIMING.rest, { stagger: 14 });
      table.schedule(cleared + 300, () => {
        if (game.epoch === epoch) startDemo();
      });
    });
  });
  loop.wake();
}

// ---- Playing ----------------------------------------------------------------------------------------------------

function save() {
  if (game.mode !== "play") return;
  saveGame({ v: 1, opponent: game.opponent, human: game.human, strength: game.strength, moves: game.moves, over: game.over });
}

function refreshRail() {
  const humanTurn = game.mode === "play" && !game.over && !isComputerTurn();
  const hasHumanMove = game.opponent === "friend" ? game.moves.length > 0 : game.moves.some((_, i) => replay(game.moves.slice(0, i)).toMove === game.human);
  hud.setRail({ undo: game.mode === "play" && hasHumanMove, hint: humanTurn });
}

function statusForTurn() {
  if (isComputerTurn()) return hud.setStatus("The computer is thinking", game.toMove);
  if (game.opponent === "computer") return hud.setStatus("Your move", game.toMove);
  hud.setStatus(`${nameOf(game.toMove)} to move`, game.toMove);
}

function beginTurn() {
  if (game.mode !== "play") return;
  const now = performance.now();
  hud.setTurn(game.over ? null : game.toMove);
  refreshRail();
  if (game.over || game.toMove === null) {
    finish();
    return;
  }
  statusForTurn();
  if (isComputerTurn()) {
    table.setLegal([], game.toMove, now);
    const epoch = game.epoch;
    const asked = performance.now();
    engine(game.board, game.toMove, game.strength).then(({ square }) => {
      if (game.epoch !== epoch || game.mode !== "play") return;
      const wait = Math.max(0, THINK_MS - (performance.now() - asked));
      setTimeout(() => {
        if (game.epoch !== epoch || game.mode !== "play") return;
        if (square >= 0) commitMove(square);
      }, wait);
    });
  } else {
    table.setLegal(legalMoves(game.board, game.toMove), game.toMove, now);
    syncPreview();
  }
  loop.wake();
}

function commitMove(square) {
  const result = play(game.board, square, game.toMove);
  if (!result) return;
  const now = performance.now();
  const mover = game.toMove;
  const end = table.place(square, mover, result.lines, now);
  game.board = result.board;
  game.moves.push(square);
  const next = nextToMove(game.board, mover);
  game.toMove = next.color;
  game.over = next.color === null;
  save();
  hud.setTurn(null);
  refreshRail();
  const epoch = game.epoch;
  if (next.passed) {
    table.schedule(end + 60, (t) => {
      if (game.epoch !== epoch) return;
      table.passShake(next.passed, t);
      const passer = nameOf(next.passed);
      hud.toast(game.opponent === "computer" && next.passed === game.human ? "You have no move" : `${passer} has no move`);
      hud.setStatus(`${passer} passes`, next.passed);
    });
    table.schedule(end + 1000, () => game.epoch === epoch && beginTurn());
  } else {
    table.schedule(end + 30, () => game.epoch === epoch && beginTurn());
  }
  loop.wake();
}

function finish() {
  game.over = true;
  save();
  const now = performance.now();
  const final = game.board;
  const done = table.endWave(final, now + 200);
  const { black, white } = count(final);
  const win = winner(final);
  const epoch = game.epoch;
  hud.setTurn(null);
  refreshRail();
  hud.setStatus(win === EMPTY ? `A draw, ${black} to ${white}` : `${nameOf(win)} wins, ${Math.max(black, white)} to ${Math.min(black, white)}`, win || null);
  table.schedule(done - 500, () => {
    if (game.epoch !== epoch) return;
    let line = win === EMPTY ? "A draw" : `${nameOf(win)} wins`;
    if (game.opponent === "computer" && win !== EMPTY) line = win === game.human ? "You win" : "The computer wins";
    hud.showResult(line, `${Math.max(black, white)} to ${Math.min(black, white)}`, true);
  });
  loop.wake();
}

function canHumanAct() {
  return game.mode === "play" && !game.over && !isComputerTurn() && performance.now() >= table.busyUntil && !hud.setupShown();
}

function placeHuman(square) {
  if (!canHumanAct()) return;
  if (!legalMoves(game.board, game.toMove).includes(square)) return;
  commitMove(square);
}

let hoverSquare = -1;
function syncPreview() {
  const square = hoverSquare >= 0 ? hoverSquare : table.cursor.visible ? table.cursor.square : -1;
  if (square < 0 || !canHumanAct() || game.board[square] !== EMPTY) {
    table.setPreview(null);
    stage.classList.remove("is-pointing");
    loop.wake();
    return;
  }
  const lines = flipLines(game.board, square, game.toMove);
  if (lines.length === 0) {
    table.setPreview(null);
    stage.classList.remove("is-pointing");
  } else {
    table.setPreview({ square, color: game.toMove, flips: lines.flatMap((line) => line.squares) });
    stage.classList.add("is-pointing");
  }
  loop.wake();
}

function undo() {
  if (game.mode !== "play" || game.moves.length === 0) return;
  let k = game.moves.length;
  let state;
  do {
    k -= 1;
    state = replay(game.moves.slice(0, k));
  } while (game.opponent === "computer" && k > 0 && state.toMove !== game.human);
  game.epoch += 1;
  game.moves = game.moves.slice(0, k);
  game.board = state.board;
  game.toMove = state.toMove;
  game.over = false;
  hud.hideResult();
  table.clearEvents();
  const end = table.syncTo(game.board, performance.now());
  save();
  hud.setStatus("Taking it back", null);
  const epoch = game.epoch;
  table.schedule(end + 40, () => game.epoch === epoch && beginTurn());
  loop.wake();
}

function hint() {
  if (!canHumanAct()) return;
  const epoch = game.epoch;
  const moveCount = game.moves.length;
  engine(game.board, game.toMove, 3).then(({ square }) => {
    if (game.epoch !== epoch || game.moves.length !== moveCount || square < 0) return;
    table.setHint(square, performance.now());
    loop.wake();
  });
}

function startGame({ opponent: who, human, strength }) {
  game.mode = "play";
  game.opponent = who === "friend" ? "friend" : "computer";
  game.human = human === WHITE ? WHITE : BLACK;
  game.strength = [1, 2, 3].includes(strength) ? strength : 2;
  game.epoch += 1;
  game.moves = [];
  game.board = initialBoard();
  game.toMove = BLACK;
  game.over = false;
  hud.hideResult();
  hud.hideSetup();
  hud.showRail(true);
  hud.setPlayers(players());
  hud.setStatus("Setting the opening four", null);
  table.clearEvents();
  const end = table.syncTo(game.board, performance.now(), { stagger: 16 });
  save();
  const epoch = game.epoch;
  table.schedule(end + 60, () => game.epoch === epoch && beginTurn());
  lastLayout = "";
  requestAnimationFrame(() => layout(false));
  loop.wake();
}

function openSetup() {
  table.setPreview(null);
  hud.hideResult();
  hud.showSetup({ opponent: game.opponent, human: game.human, strength: game.strength, theme: prefs.theme, demo: game.mode === "demo", back: game.mode === "play" });
  lastLayout = "";
  requestAnimationFrame(() => layout(false));
}

function closeSetup() {
  hud.hideSetup();
  lastLayout = "";
  requestAnimationFrame(() => layout(false));
  if (game.over && game.mode === "play") finish();
}

function resumeOrDemo() {
  const saved = loadGame();
  if (saved && saved.v === 1 && Array.isArray(saved.moves) && !saved.over) {
    const state = replay(saved.moves.filter((m) => Number.isInteger(m)));
    if (state && state.toMove !== null) {
      game.mode = "play";
      game.opponent = saved.opponent === "friend" ? "friend" : "computer";
      game.human = saved.human === WHITE ? WHITE : BLACK;
      game.strength = [1, 2, 3].includes(saved.strength) ? saved.strength : 2;
      game.moves = saved.moves.slice();
      game.board = state.board;
      game.toMove = state.toMove;
      game.over = false;
      table.setBoard(game.board);
      hud.hideSetup();
      hud.showRail(true);
      hud.setPlayers(players());
      beginTurn();
      return;
    }
  }
  hud.showSetup({ opponent: game.opponent, human: game.human, strength: game.strength, theme: prefs.theme, demo: true, back: false });
  startDemo();
}

// ---- Theme, light, and motion ---------------------------------------------------------------------------------

function retheme() {
  tokens = readTokens();
  if (view) view.applyTokens(tokens);
  hud.setSideNames(sideNames());
  hud.setPlayers(players());
  if (game.mode === "play" && !game.over && game.toMove !== null && performance.now() >= table.busyUntil) statusForTurn();
  loop.wake();
}

function setTheme(name) {
  if (!THEMES.includes(name)) return;
  prefs.theme = name;
  savePrefs(prefs);
  hud.syncThemeChoice(name);
  const sheet = document.getElementById("theme-sheet");
  const href = name === config.theme ? "./theme.css" : `./themes/${name}.css`;
  if (sheet.getAttribute("href") === href) return;
  const next = document.createElement("link");
  next.rel = "stylesheet";
  next.href = href;
  next.addEventListener("load", () => {
    sheet.remove();
    next.id = "theme-sheet";
    retheme();
  });
  sheet.after(next);
}

function setScheme(scheme) {
  prefs.scheme = scheme;
  savePrefs(prefs);
  if (scheme === "light" || scheme === "dark") document.documentElement.setAttribute("data-theme", scheme);
  else document.documentElement.removeAttribute("data-theme");
  retheme();
}

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => prefs.scheme === "auto" && retheme());
reducedQuery.addEventListener("change", () => {
  table.reduced = reducedQuery.matches;
});

// ---- Start --------------------------------------------------------------------------------------------------------

function hasWebGL() {
  try {
    const probe = document.createElement("canvas");
    return Boolean(probe.getContext("webgl2") || probe.getContext("webgl"));
  } catch (error) {
    return false;
  }
}

async function createView() {
  const settings = tierSettings(pickTier());
  try {
    if (!hasWebGL()) throw new Error("no WebGL");
    const { createWorld } = await import("./scene/world.js");
    return await createWorld({ host: stage, settings, tokens, envUrl: "./vendor/env/studio.hdr" });
  } catch (error) {
    stage.replaceChildren();
    const { createCanvasView } = await import("./render/canvas2d.js");
    return createCanvasView({ host: stage, tokens });
  }
}

async function main() {
  hud.setSideNames(sideNames());
  hud.setPlayers(players());
  hud.setCounts(2, 2);
  hud.syncThemeChoice(prefs.theme);
  view = await createView();
  table.setBoard(initialBoard());
  layout(true);
  await view.warm();
  view.render(table, performance.now());
  resumeOrDemo();
  layout(true);

  bindInput({
    stage,
    pick: (x, y) => view.pick(x, y),
    intents: {
      wakeAudio: () => audio.unlock(),
      hover(square) {
        hoverSquare = square;
        if (square >= 0) table.setCursor(table.cursor.square, false);
        syncPreview();
      },
      place: (square) => placeHuman(square),
      cursor(dr, dc) {
        const s = table.cursor.square;
        const row = Math.min(7, Math.max(0, Math.floor(s / 8) + dr));
        const col = Math.min(7, Math.max(0, (s % 8) + dc));
        hoverSquare = -1;
        table.setCursor(row * 8 + col, true);
        syncPreview();
      },
      cursorPlace() {
        if (!table.cursor.visible) {
          table.setCursor(table.cursor.square, true);
          syncPreview();
          return;
        }
        placeHuman(table.cursor.square);
      },
      undo: () => undo(),
      hint: () => hint(),
    },
  });

  let resizeFrame = 0;
  const onResize = () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => layout(true));
  };
  window.addEventListener("resize", onResize);
  if (window.visualViewport) window.visualViewport.addEventListener("resize", onResize);
  document.addEventListener("visibilitychange", () => {
    // A replay left running in a hidden tab would fire its whole backlog at once; start it fresh instead.
    if (!document.hidden && game.mode === "demo") startDemo();
  });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => {
    lastLayout = "";
    layout(true);
  });
  loop.wake();
}

main();
