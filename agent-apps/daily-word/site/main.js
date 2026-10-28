// The game: reads the config, keeps today's board and the endless one, takes keys and taps, and drives the board,
// keyboard, sheets, sound, and confetti.

import { COMMON } from "./data/common.js";
import { normalize, dailyWord, msToNextWord, score, hardModeProblem, letterStates, fingerprint, shareText, TRIES } from "./game/words.js";
import { load, save, readStats, recordDaily } from "./game/stats.js";
import { runDemo } from "./game/demo.js";
import { createGrid } from "./ui/grid.js";
import { createKeyboard } from "./ui/keyboard.js";
import { createToasts } from "./ui/toast.js";
import { createSheets } from "./ui/sheets.js";
import { renderModes, renderStats, renderHelp, renderSettings, miniAnswer } from "./ui/panels.js";
import { createConfetti } from "./fx/confetti.js";
import { createAudio } from "./audio.js";

const config = window.__APP_CONFIG__ || {};
const title = String(config.title || "Daily Word");
const topic = String(config.topic || "");
const words = (Array.isArray(config.words) ? config.words : []).map(normalize).filter(Boolean);
if (!words.length) words.push("GLINT", "BRAVE", "CHORD", "PLANK", "WORTH");
const allowed = new Set([...COMMON, ...words, ...(Array.isArray(config.allowExtra) ? config.allowExtra : []).map(normalize).filter(Boolean)]);

const root = document.documentElement;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const coarse = matchMedia("(pointer: coarse)");
const wide = matchMedia("(min-width: 1100px) and (min-height: 620px)");

const grid = createGrid(document.querySelector(".board"), { reduced });
const keyboard = createKeyboard(document.querySelector(".keyboard"), (key) => onKey(key), { reduced });
const toasts = createToasts(document.querySelector(".play > .toasts"));
const confetti = createConfetti(document.querySelector(".confetti"));
const audio = createAudio();
const sheets = createSheets();
const caption = document.querySelector("[data-caption]");

const resultToasts = (() => {
  const box = document.createElement("div");
  box.className = "toasts";
  box.setAttribute("role", "status");
  document.querySelector("#result .sheet-body").appendChild(box);
  return createToasts(box);
})();

let settings = load("settings", { hardMode: !!config.hardMode, highContrast: false, sound: true, scheme: "auto", palette: "" });
let mode = load("mode", { mode: "daily" }).mode === "endless" ? "endless" : "daily";
let game = null;
let current = "";
let busy = false;
let demo = null;
let resultTimer = 0;

const bind = (name, text) => document.querySelectorAll(`[data-bind="${name}"]`).forEach((n) => (n.textContent = text));
const clock = (ms) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map((n) => String(n).padStart(2, "0")).join(":");
};

/* Games */

function dailyGame() {
  const { word, day } = dailyWord(words, config.launchDate);
  const saved = load("daily", {});
  if (saved.day === day && saved.check === fingerprint(word) && Array.isArray(saved.guesses)) {
    const history = saved.guesses.map((g) => ({ guess: g, result: score(g, word) }));
    return { mode: "daily", answer: word, day, history, status: statusOf(history, word), hard: !!saved.hard };
  }
  return { mode: "daily", answer: word, day, history: [], status: "playing", hard: !!settings.hardMode };
}

function endlessGame(fresh = false) {
  const saved = load("endless", { run: 0 });
  const answer = normalize(saved.answer);
  if (!fresh && answer && Array.isArray(saved.guesses)) {
    const history = saved.guesses.map((g) => ({ guess: g, result: score(g, answer) }));
    return { mode: "endless", answer, history, status: statusOf(history, answer), hard: !!saved.hard, run: saved.run || 0 };
  }
  const today = dailyWord(words, config.launchDate).word;
  const pool = words.filter((w) => w !== today && w !== answer);
  const next = (pool.length ? pool : words)[Math.floor(Math.random() * (pool.length || words.length))];
  const game = { mode: "endless", answer: next, history: [], status: "playing", hard: !!settings.hardMode, run: saved.run || 0 };
  persist(game);
  return game;
}

function statusOf(history, answer) {
  if (history.some((h) => h.guess === answer)) return "won";
  return history.length >= TRIES ? "lost" : "playing";
}

function persist(g = game) {
  const guesses = g.history.map((h) => h.guess);
  if (g.mode === "daily") save("daily", { day: g.day, check: fingerprint(g.answer), guesses, hard: g.hard });
  else save("endless", { answer: g.answer, guesses, hard: g.hard, run: g.run });
}

/* Screens */

function captionHtml() {
  const n = game.history.length;
  const left = TRIES - n;
  if (game.status === "won") return `<strong>Got it in ${n}.</strong> ${game.mode === "daily" ? "A new word arrives at midnight." : `Run of ${game.run}.`}`;
  if (game.status === "lost") return `The word was <strong>${game.answer}</strong>.`;
  const lead = game.mode === "daily" ? `<strong>Day ${game.day}.</strong>` : "<strong>Endless.</strong>";
  if (n === 0) return `${lead} ${game.mode === "daily" ? "Six tries at today's word." : "Six tries at a fresh word."}`;
  return `${lead} ${left === 1 ? "Last try." : `${left} tries left.`}`;
}

function paint() {
  if (!demo) caption.innerHTML = captionHtml();
  bind("dayline", game.mode === "daily" ? `Day ${game.day}` : `Endless, run of ${game.run}`);
  bind("day", game.mode === "daily" ? `Day ${game.day}` : "Endless");
  renderModes(mode, setMode);
  const stats = readStats(dailyWord(words, config.launchDate).day);
  renderStats(stats, { highlight: game.mode === "daily" && game.status === "won" ? game.history.length : 0 });
  renderSettings(settings, { hardLocked: game.history.length > 0 && game.status === "playing" }, changeSettings);
  tick();
}

async function show({ animated = false } = {}) {
  current = "";
  await grid.clear({ animated });
  game.history.forEach((h, r) => grid.showRow(r, h.guess, h.result));
  keyboard.setStates(letterStates(game.history));
  paint();
}

function tick() {
  const left = clock(msToNextWord());
  bind("countdown", left);
  bind("next", game.mode === "daily" ? `Next word in ${left}` : `Run of ${game.run}`);
  if (game.mode === "daily" && !busy && !demo && dailyWord(words, config.launchDate).day !== game.day) {
    game = dailyGame();
    show({ animated: true });
  }
}

/* Input */

function onKey(key) {
  audio.unlock();
  if (demo) return endDemo();
  if (sheets.anyOpen()) return;
  if (busy) return;
  if (game.status !== "playing") {
    if (key === "Enter") openResult();
    return;
  }
  const row = game.history.length;
  if (key === "Enter") return submit();
  if (key === "Backspace") {
    if (!current) return;
    current = current.slice(0, -1);
    grid.setLetter(row, current.length, "");
    audio.play("key", { gain: 0.35, rate: 0.85 });
    return;
  }
  if (/^[A-Z]$/.test(key) && current.length < 5) {
    grid.setLetter(row, current.length, key);
    current += key;
    audio.play("key", { gain: 0.5, rate: 0.95 + Math.random() * 0.1 });
  }
}

function refuse(message) {
  toasts.show(message);
  audio.play("buzz", { gain: 0.6 });
  grid.shake(game.history.length);
}

async function submit() {
  if (current.length < 5) return refuse("Not enough letters");
  if (!allowed.has(current)) return refuse("Not in the word list");
  if (game.hard) {
    const problem = hardModeProblem(current, game.history);
    if (problem) return refuse(problem);
  }
  const guess = current;
  const row = game.history.length;
  const result = score(guess, game.answer);
  const before = game.history.slice();
  game.history.push({ guess, result });
  current = "";
  game.status = statusOf(game.history, game.answer);
  if (game.mode === "endless" && game.status !== "playing") game.run = game.status === "won" ? game.run + 1 : 0;
  persist();
  if (game.mode === "daily" && game.status !== "playing") recordDaily(game.day, game.status === "won", game.history.length);

  busy = true;
  await grid.revealRow(row, guess, result, (c) => {
    audio.play("thunk", { gain: 0.9, rate: 0.94 + c * 0.03 });
    keyboard.setStates(letterStates([...before, { guess: guess.slice(0, c + 1), result: result.slice(0, c + 1) }]));
  });
  busy = false;
  paint();

  if (game.status === "won") celebrate(row);
  else if (game.status === "lost") {
    toasts.show(game.answer, { persist: true });
    resultTimer = setTimeout(openResult, 1700);
  }
}

const PRAISE = ["Genius", "Magnificent", "Impressive", "Splendid", "Great", "Phew"];

function celebrate(row) {
  toasts.show(PRAISE[row] || "Nice", { ms: 1800 });
  audio.play("chime", { gain: 0.8 });
  if (!reduced.matches) {
    const rect = grid.rowRect(row);
    confetti.burst(rect.left + rect.width / 2, rect.top + rect.height / 2, { count: innerWidth < 700 ? 110 : 170 });
  }
  grid.win(row);
  resultTimer = setTimeout(openResult, reduced.matches ? 900 : 2000);
}

function openResult() {
  clearTimeout(resultTimer);
  if (demo || game.status === "playing") return;
  const n = game.history.length;
  const won = game.status === "won";
  bind("result-title", won ? `Got it in ${n}` : "Not this time");
  bind("result-sub", game.mode === "daily" ? (won ? `Day ${game.day}${game.hard ? ", hard mode" : ""}. Your streak is safe.` : `Day ${game.day}. The word was:`) : won ? `Run of ${game.run}.` : "The word was:");
  document.querySelector('[data-bind="result-answer"]').innerHTML = won ? "" : miniAnswer(game.answer);
  document.querySelector("[data-endless]").textContent = game.mode === "daily" ? "Play endless" : "Next word";
  document.querySelector("[data-next-row]").hidden = game.mode !== "daily";
  sheets.open("result");
}

/* Modes and settings */

async function setMode(next) {
  if (busy || next === mode) return;
  if (demo) endDemo();
  mode = next;
  save("mode", { mode });
  game = mode === "daily" ? dailyGame() : endlessGame();
  toasts.clear();
  await show({ animated: true });
}

function changeSettings(patch) {
  if ("hardMode" in patch) {
    if (game.history.length > 0 && game.status === "playing") return;
    game.hard = patch.hardMode;
    persist();
  }
  if ("palette" in patch && patch.palette === settings.palette) patch.palette = "";
  settings = { ...settings, ...patch };
  save("settings", settings);
  root.classList.toggle("high-contrast", !!settings.highContrast);
  if (settings.scheme === "light" || settings.scheme === "dark") root.setAttribute("data-theme", settings.scheme);
  else root.removeAttribute("data-theme");
  const link = document.getElementById("theme");
  const href = settings.palette ? `./themes/${settings.palette}.css` : "./theme.css";
  if (link.getAttribute("href") !== href) link.setAttribute("href", href);
  audio.setEnabled(settings.sound !== false);
  renderSettings(settings, { hardLocked: game.history.length > 0 && game.status === "playing" }, changeSettings);
}

async function share() {
  const text = shareText({
    title,
    label: game.mode === "daily" ? String(game.day) : "Endless",
    history: game.history,
    won: game.status === "won",
    hard: game.hard,
    highContrast: !!settings.highContrast,
  });
  let copied = false;
  try {
    await navigator.clipboard.writeText(text);
    copied = true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.className = "visually-hidden";
    document.querySelector("#result").appendChild(area);
    area.select();
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }
    area.remove();
  }
  resultToasts.show(copied ? "Copied. Paste it anywhere." : "Your browser blocked copying here.", { ms: 1800 });
}

/* The opening round */

function startDemo() {
  if (demo) return;
  clearTimeout(resultTimer);
  toasts.clear();
  grid.clear();
  keyboard.setStates({});
  caption.innerHTML = `<strong>Here's how a round goes.</strong> ${coarse.matches ? "Tap anywhere to play." : "Press any key to play."}`;
  demo = runDemo({
    grid,
    keyboard,
    toasts,
    confetti,
    reduced,
    avoid: game.answer,
    onWin: (n) => {
      caption.innerHTML = `<strong>Got it in ${n}.</strong> Now it's your turn.`;
    },
  });
  demo.done.then((finished) => {
    if (finished && demo) finishDemo(true);
  });
}

function endDemo() {
  if (!demo) return;
  demo.stop();
  confetti.stop();
  finishDemo(false);
}

async function finishDemo(natural) {
  demo = null;
  save("seen", { done: true });
  toasts.clear();
  await show({ animated: true });
  if (natural && !wide.matches && !sheets.anyOpen()) setTimeout(() => sheets.open("help"), 250);
}

/* The "Get this app" badge: keep room for it while it shows, then let the game ease into the space. The layout
   changes once; the board and keyboard glide from where they were by transform, so no frame lays the page out. */

function watchBadge() {
  if (!document.querySelector('script[src$="badge.js"]')) return;
  let shown = false;
  const moving = [document.querySelector(".board"), document.querySelector(".keyboard")];
  const gone = (on) => {
    if (root.classList.contains("badge-gone") === on) return;
    const before = reduced.matches ? null : moving.map((n) => n.getBoundingClientRect());
    root.classList.toggle("badge-gone", on);
    grid.fit();
    before?.forEach((a, i) => {
      const b = moving[i].getBoundingClientRect();
      if (!b.width) return;
      const dx = a.left + a.width / 2 - (b.left + b.width / 2);
      const dy = a.top + a.height / 2 - (b.top + b.height / 2);
      const s = a.width / b.width;
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5 && Math.abs(s - 1) < 0.002) return;
      moving[i].animate([{ transform: `translate(${dx}px, ${dy}px) scale(${s})` }, { transform: "none" }], {
        duration: 380,
        easing: "cubic-bezier(0.32, 0.72, 0, 1)",
      });
    });
  };
  const fallback = setTimeout(() => {
    if (!document.querySelector(".code-config-toast")) gone(true);
  }, 2500);
  const follow = (toast) => {
    clearTimeout(fallback);
    const check = () => {
      const away = toast.classList.contains("away");
      if (!away) shown = true;
      gone(!toast.isConnected || (shown && away));
    };
    new MutationObserver(check).observe(toast, { attributes: true, attributeFilter: ["class"] });
    check();
  };
  const existing = document.querySelector(".code-config-toast");
  if (existing) follow(existing);
  new MutationObserver((records) => {
    for (const record of records) {
      record.addedNodes.forEach((n) => n.classList?.contains("code-config-toast") && follow(n));
      record.removedNodes.forEach((n) => n.classList?.contains("code-config-toast") && gone(true));
    }
  }).observe(document.body, { childList: true });
}

/* Wiring */

document.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.target.closest?.("dialog")) return;
  const key = event.key.length === 1 ? event.key.toUpperCase() : event.key;
  if (key === "Enter" || key === "Backspace" || /^[A-Z]$/.test(key)) {
    if (key === "Enter" && event.target.closest?.("button") && !demo) {
      event.target.blur();
    }
    event.preventDefault();
    if (!demo && !sheets.anyOpen()) keyboard.press(key);
    onKey(key);
  } else if (demo && !["Shift", "Tab", "CapsLock"].includes(event.key)) {
    endDemo();
  }
});

document.addEventListener("pointerdown", (event) => {
  audio.unlock();
  if (demo && !event.target.closest(".keyboard")) endDemo();
});

document.querySelector("[data-share]").addEventListener("click", share);
document.querySelector("[data-endless]").addEventListener("click", async () => {
  sheets.close("result");
  if (mode === "endless") {
    game = endlessGame(true);
    toasts.clear();
    await show({ animated: true });
  } else {
    await setMode("endless");
  }
});
document.querySelector("[data-replay]").addEventListener("click", () => {
  sheets.close("help");
  if (!busy) setTimeout(startDemo, 200);
});

bind("title", title);
bind("topic", topic);
document.title = title;
renderHelp();
watchBadge();

game = mode === "daily" ? dailyGame() : endlessGame();
changeSettings({});
show();
setInterval(tick, 1000);

if (!load("seen", { done: false }).done && mode === "daily" && game.history.length === 0) startDemo();

