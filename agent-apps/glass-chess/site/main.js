// Glass Chess: opens on a famous game playing itself on the glass set, and turns into the person's own game the
// moment they pick an opponent. This file connects the table, the rules, the computer, the panels, and the sound.
import { World, detectTier } from "./scene/world.js";
import { FlatBoard } from "./render/svg.js";
import { Game, load, store, settingsFrom } from "./game/state.js";
import { Chess } from "./vendor/chess.js";
import { bindPointer, bindKeys, parseTyped } from "./game/input.js";
import { Panel } from "./ui/panel.js";
import { Setup, askPromotion } from "./ui/setup.js";
import { Sound } from "./audio.js";

const config = window.__APP_CONFIG__ ?? {};
const saved = load();
let settings = settingsFrom(config, saved?.settings);
const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

// Légal's mate (Paris, 1750): White gives up the queen and mates with three minor pieces.
const DEMO = {
  moves: ["e4", "e5", "Nf3", "d6", "Bc4", "Bg4", "Nc3", "g6", "Nxe5", "Bxd1", "Bxf7+", "Ke7", "Nd5#"],
  from: 8,
  names: { w: "Kermur de Légal", b: "Saint Brie" },
};

const panel = new Panel();
const sound = new Sound(settings.sound);
const play = (kind) => sound.play(kind);
let world;
let game = null;
let mode = "attract";
let attractRun = 0;
let demo = null;
let selected = null;
let targets = [];
let cursor = null;
let busy = false;
let thinkId = 0;
let worker = null;

document.title = settings.title;
$("title").textContent = settings.title;

function themeLink(name) {
  const link = $("theme");
  const href = `./themes/${name}.css`;
  if (link.getAttribute("href") === href) return Promise.resolve();
  return new Promise((resolve) => {
    const next = link.cloneNode();
    next.href = href;
    next.addEventListener("load", () => { link.remove(); next.id = "theme"; resolve(); }, { once: true });
    next.addEventListener("error", () => { next.remove(); resolve(); }, { once: true });
    link.after(next);
  });
}

async function setTheme(name) {
  await themeLink(name);
  world.applyTheme();
}

function refreshIcons() {
  panel.setIcons(world.icons);
  setup.setIcons(world.icons);
  render();
}

function save() {
  if (!game) return;
  const { title, ...keep } = settings;
  store({ settings: keep, game: game.save(performance.now()) });
}

function lastMoveSquares(history) {
  const m = history[history.length - 1];
  return m ? [m.from, m.to] : null;
}

function refreshHints() {
  const history = mode === "attract" ? demo?.history ?? [] : game.history;
  world.setHints({ last: lastMoveSquares(history), selected, targets, cursor });
}

function render() {
  if (!game && !demo) return;
  const far = world.side === "w" ? "b" : "w";
  panel.render({ game, attract: mode === "attract", far, demo });
  $("act-undo").disabled = mode !== "play" || !game.history.length;
  $("act-resign").disabled = mode !== "play" || game.over;
}

// ---- The famous game that plays while the person decides.

async function attract() {
  const run = ++attractRun;
  const chess = new Chess();
  for (const san of DEMO.moves.slice(0, DEMO.from)) chess.move(san);
  const status = () => {
    if (chess.isCheckmate()) return { title: "Checkmate", line: "White gave up the queen and mated with three minor pieces." };
    return { title: chess.inCheck() ? "Check" : "Légal's mate", line: "Kermur de Légal against Saint Brie, Paris, 1750." };
  };
  demo = { names: DEMO.names, history: chess.history({ verbose: true }), turn: chess.turn(), over: false, status: status() };
  world.setPosition(chess.board());
  world.setCheck(null);
  refreshHints();
  render();
  await sleep(350);
  for (const san of DEMO.moves.slice(DEMO.from)) {
    if (run !== attractRun) return;
    const mv = chess.move(san);
    demo.history = chess.history({ verbose: true });
    demo.turn = chess.turn();
    demo.status = status();
    await world.play(mv, play);
    if (run !== attractRun) return;
    world.setCheck(chess.inCheck() ? kingOf(chess, chess.turn()) : null);
    refreshHints();
    render();
    await sleep(260);
  }
  if (run !== attractRun) return;
  demo.over = true;
  render();
  const last = demo.history[demo.history.length - 1];
  const tipped = world.mate(kingOf(chess, chess.turn()), last.to);
  await sleep(500);
  if (run !== attractRun) return;
  panel.showResult("Checkmate", "Légal's mate, Paris, 1750. Pick an opponent and play your own.", { actions: false });
  world.setView("b").then(() => { if (run === attractRun) render(); });
  await tipped;
  await sleep(2600);
  if (run !== attractRun) return;
  // The table fades out, turns back to White while hidden, and fades in on the opening position.
  panel.hideResult();
  document.body.classList.add("curtain");
  await sleep(reduced ? 0 : 450);
  if (run !== attractRun) { document.body.classList.remove("curtain"); return; }
  world.undim({ instant: true });
  await world.setView("w", { animate: false });
  attract();
  document.body.classList.remove("curtain");
}

function kingOf(chess, side) {
  for (const row of chess.board()) for (const c of row) if (c && c.type === "k" && c.color === side) return c.square;
  return null;
}

// ---- The person's game.

function startGame(values) {
  settings = { ...settings, ...values };
  sound.enabled = settings.sound;
  attractRun++;
  mode = "play";
  thinkId++;
  busy = false;
  selected = null;
  targets = [];
  game = new Game(settings);
  panel.hideResult();
  world.undim();
  world.setPosition(game.chess.board());
  world.setCheck(null);
  world.setView(settings.opponent === "computer" ? settings.human : "w").then(render);
  refreshHints();
  render();
  save();
  maybeThink();
}

function resume() {
  mode = "play";
  game = new Game(settings, saved.game);
  world.setPosition(game.chess.board());
  world.setCheck(game.checkSquare());
  const side = settings.opponent === "computer" ? settings.human : settings.turnBoard ? game.turn : "w";
  world.setView(side, { animate: false });
  if (game.history.length && !game.over) game.clock.start(game.turn, performance.now());
  refreshHints();
  render();
  if (game.over) showEnd(null, { instant: true });
  else maybeThink();
}

function select(sq) {
  selected = sq;
  targets = sq ? game.legalFrom(sq).map((m) => ({ square: m.to, capture: Boolean(m.captured) })) : [];
  refreshHints();
}

function onSquare(sq) {
  if (mode !== "play") return;
  cursor = cursor ? sq : null;
  if (busy || game.over || game.isComputer(game.turn)) { refreshHints(); return; }
  if (selected && targets.some((t) => t.square === sq)) { tryMove(selected, sq); return; }
  const piece = game.chess.get(sq);
  if (piece && piece.color === game.turn && sq !== selected) select(sq);
  else select(null);
}

async function tryMove(from, to) {
  const options = game.legalFrom(from).filter((m) => m.to === to);
  if (!options.length) return;
  let promotion;
  if (options[0].promotion) {
    promotion = await askPromotion(game.turn, world.icons);
    if (!promotion) return;
  }
  await commit({ from, to, promotion });
}

async function commit(input) {
  const mv = game.move(input, performance.now());
  if (!mv) return;
  busy = true;
  select(null);
  render();
  await world.play(mv, play);
  afterMove(mv);
}

async function afterMove(mv) {
  const check = game.checkSquare();
  world.setCheck(check);
  if (check) play("check");
  refreshHints();
  save();
  render();
  if (game.over) { busy = false; showEnd(mv); return; }
  if (settings.opponent === "friend" && settings.turnBoard) await world.setView(game.turn);
  busy = false;
  render();
  maybeThink();
}

function maybeThink() {
  if (mode !== "play" || game.over || !game.isComputer(game.turn)) return;
  const id = ++thinkId;
  const started = performance.now();
  worker ??= new Worker(new URL("./game/engine.worker.js", import.meta.url), { type: "module" });
  worker.onmessage = async (e) => {
    if (e.data.id !== thinkId || mode !== "play") return;
    const wait = 420 - (performance.now() - started);
    if (wait > 0) await sleep(wait);
    if (e.data.id !== thinkId || !e.data.move) return;
    const { from, to, promotion } = e.data.move;
    commit({ from, to, promotion: promotion || undefined });
  };
  worker.postMessage({ id, fen: game.chess.fen(), strength: settings.strength });
  render();
}

async function showEnd(mv, { instant = false } = {}) {
  const r = game.result;
  const loser = r.winner === "w" ? "b" : r.winner === "b" ? "w" : null;
  // Every ending dims the room; a mate or a resignation also tips the beaten king.
  const tips = !instant && loser && (r.reason === "checkmate" || r.reason === "resigned");
  world.mate(tips ? kingOf(game.chess, loser) : null, r.reason === "checkmate" && mv ? mv.to : null);
  if (!instant) await sleep(900);
  if (mode !== "play" || game.result !== r) return;
  const s = game.status();
  panel.showResult(s.title, s.line);
  render();
}

function undo() {
  if (mode !== "play" || busy || !game.history.length) return;
  thinkId++;
  game.undo();
  panel.hideResult();
  world.undim();
  world.setPosition(game.chess.board());
  world.setCheck(game.checkSquare());
  select(null);
  save();
  render();
  maybeThink();
}

let resignTimer = 0;
function resign() {
  if (mode !== "play" || game.over) return;
  const btn = $("act-resign");
  if (!btn.hasAttribute("data-confirm")) {
    btn.dataset.confirm = "";
    btn.querySelector("span").textContent = "Tap again";
    clearTimeout(resignTimer);
    resignTimer = setTimeout(() => { delete btn.dataset.confirm; btn.querySelector("span").textContent = "Resign"; }, 3000);
    return;
  }
  clearTimeout(resignTimer);
  delete btn.dataset.confirm;
  btn.querySelector("span").textContent = "Resign";
  thinkId++;
  const side = settings.opponent === "computer" ? settings.human : game.turn;
  game.resign(side);
  save();
  render();
  showEnd(null);
}

// ---- Panels and controls.

const setup = new Setup({
  onStart: (values) => startGame(values),
  onSettings: (values) => {
    settings = { ...settings, theme: values.theme, sound: values.sound, turnBoard: values.turnBoard };
    sound.enabled = settings.sound;
    save();
  },
  onTryTheme: (name) => setTheme(name),
});

$("play-computer").addEventListener("click", () => startGame({ opponent: "computer" }));
$("play-friend").addEventListener("click", () => startGame({ opponent: "friend" }));
$("more-options").addEventListener("click", () => setup.open("new", settings));
$("act-new").addEventListener("click", () => setup.open("new", settings));
$("act-settings").addEventListener("click", () => setup.open("settings", settings));
$("act-undo").addEventListener("click", undo);
$("act-flip").addEventListener("click", () => world.setView(world.side === "w" ? "b" : "w").then(render));
$("act-resign").addEventListener("click", resign);
$("result-new").addEventListener("click", () => setup.open("new", settings));
$("result-close").addEventListener("click", () => panel.hideResult());

$("san").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("san-input");
  const note = $("san-note");
  const text = input.value;
  if (mode !== "play") { note.textContent = "Pick an opponent above to start your own game."; return; }
  if (game.over) { note.textContent = "This game is over. Start a new one to keep playing."; return; }
  if (busy || game.isComputer(game.turn)) { note.textContent = "The computer is still moving."; return; }
  const mv = parseTyped(text, game.chess.moves({ verbose: true }));
  if (!mv) { note.textContent = `${text.trim() || "That"} is not a legal move for ${game.turn === "w" ? "White" : "Black"} here.`; return; }
  note.textContent = "";
  input.value = "";
  commit({ from: mv.from, to: mv.to, promotion: mv.promotion });
});

addEventListener("pagehide", save);
document.addEventListener("visibilitychange", () => { if (document.hidden) save(); });

// ---- Start.

async function boot() {
  if (settings.theme !== config.theme) await themeLink(settings.theme);
  await Promise.race([document.fonts.load('600 20px "Hanken Grotesk"'), sleep(1200)]).catch(() => {});
  const canvas = $("table");
  try {
    world = new World(canvas, { tier: detectTier(), reduced });
    await world.init();
  } catch {
    canvas.remove();
    const host = $("flat");
    $("stage").prepend(host);
    host.hidden = false;
    world = new FlatBoard(host);
  }
  world.on((kind, now) => {
    if (kind === "theme") refreshIcons();
    if (kind === "frame") frame(now);
  });
  // The board fills the stage below the result card, so the card never sits on the board.
  const stage = $("stage");
  const result = $("result");
  let reserved = 0;
  const fit = () => {
    const r = stage.getBoundingClientRect();
    const top = result.hidden ? 0 : result.offsetTop + result.offsetHeight;
    const animate = top !== reserved && !document.body.classList.contains("curtain");
    reserved = top;
    world.setStage({ x: r.left, y: r.top + top, w: r.width, h: r.height - top }, { animate });
  };
  const watch = new ResizeObserver(fit);
  watch.observe(stage);
  watch.observe(result);
  fit();
  const flat = world instanceof FlatBoard;
  if (flat) setInterval(frame, 100);
  bindPointer(world.canvas ?? $("flat"), world, { onSquare, canOrbit: () => !flat && detectTier() === "desktop" });
  bindKeys(world.canvas ?? $("flat"), {
    getCursor: () => cursor,
    setCursor: (sq) => { cursor = sq; refreshHints(); },
    getSide: () => world.side,
    onSquare: (sq) => { cursor = sq; onSquare(sq); },
    onEscape: () => { select(null); cursor = null; refreshHints(); },
  });
  refreshIcons();
  document.body.classList.add("ready");
  if (saved?.game) resume();
  else attract();
}

function frame() {
  if (mode === "attract") {
    world.view.drift = reduced ? 0 : 0.07 * Math.sin(performance.now() / 1000 * 0.42);
  } else if (world.view) {
    world.view.drift *= 0.96;
  }
  if (mode === "play" && game && !game.over) {
    const now = performance.now();
    const flag = game.clock.flagged(now);
    if (flag) {
      thinkId++;
      game.finish(flag === "w" ? "b" : "w", "time", now);
      save();
      render();
      showEnd(null);
    }
    panel.tick(game, now, play);
  }
}

boot();
