// Wires the sheet to its controls: search, the platform toggle, Learn, and Print. Choices persist on this device.

import { createSheet } from "./sheet.js";
import { pickWord, playIntro } from "./intro.js";
import { load, save } from "./store.js";

const config = window.__APP_CONFIG__;
const saved = load();
const $ = (id) => document.getElementById(id);

const root = $("sheet");
const input = $("q");
const box = $("search-box");
const sub = $("sub");
const learnBtn = $("learn");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

const platforms = ["mac", "windows", "linux"];
let platform = platforms.includes(saved.platform) ? saved.platform : config.platform;
let learning = saved.learn === true;

$("print-title").textContent = config.title;

const sheet = createSheet({ root, config: { ...config, platform } });
const noun = (n) => (n === 1 ? "entry" : "entries");

function report(shown, q) {
  const empty = $("empty");
  if (!q) {
    sub.textContent = `${sheet.total} shortcuts and commands`;
    empty.hidden = true;
    return;
  }
  sub.textContent = shown ? `${shown} of ${sheet.total} ${noun(sheet.total)} match` : `Nothing matches "${q}"`;
  empty.hidden = shown > 0;
  $("empty-text").textContent = `Nothing on this sheet matches "${q}".`;
}

function runFilter(value) {
  const shown = sheet.filter(value);
  report(shown, value.trim());
  return shown;
}

function setSearch(value, { persist = true } = {}) {
  input.value = value;
  box.classList.toggle("has-query", value !== "");
  runFilter(value);
  if (persist) save({ query: value });
}

function paintPlatform() {
  for (const b of document.querySelectorAll("#platform button")) {
    const on = b.dataset.platform === platform;
    b.setAttribute("aria-checked", String(on));
    b.tabIndex = on ? 0 : -1;
  }
}

function setPlatform(next, { persist = true } = {}) {
  if (next === platform) return;
  platform = next;
  paintPlatform();
  const shown = sheet.setPlatform(platform);
  report(shown, input.value.trim());
  if (persist) save({ platform });
}

let waveTimer = 0;
function setLearning(on, { persist = false } = {}) {
  learning = on;
  sheet.stampWave();
  root.classList.add("is-waving");
  clearTimeout(waveTimer);
  waveTimer = setTimeout(() => root.classList.remove("is-waving"), 1500);
  root.classList.toggle("is-learning", on);
  learnBtn.setAttribute("aria-pressed", String(on));
  if (!on) for (const r of root.querySelectorAll(".row.is-revealed")) r.classList.remove("is-revealed");
  if (persist) save({ learn: on });
}

// First paint: the saved state, then the opening settle.
paintPlatform();
root.classList.toggle("is-learning", learning);
learnBtn.setAttribute("aria-pressed", String(learning));
setSearch(typeof saved.query === "string" ? saved.query : "", { persist: false });
if (!reducedMotion) {
  root.classList.add("is-opening");
  setTimeout(() => root.classList.remove("is-opening"), 2200);
}

input.addEventListener("input", () => setSearch(input.value));
input.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { setSearch(""); input.blur(); }
});
$("clear").addEventListener("click", (e) => { e.preventDefault(); setSearch(""); input.focus(); });
$("empty-clear").addEventListener("click", () => { setSearch(""); input.focus(); });

const seg = $("platform");
seg.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-platform]");
  if (b) setPlatform(b.dataset.platform);
});
seg.addEventListener("keydown", (e) => {
  const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
  if (!step) return;
  e.preventDefault();
  const next = platforms[(platforms.indexOf(platform) + step + platforms.length) % platforms.length];
  setPlatform(next);
  seg.querySelector(`[data-platform="${next}"]`).focus();
});

learnBtn.addEventListener("click", () => setLearning(!learning, { persist: true }));

root.addEventListener("click", (e) => {
  const row = e.target.closest(".row");
  if (!row) return;
  if (!learning) { sheet.play(row); return; }
  row.classList.toggle("is-revealed");
  sheet.turn(row);
});

// With a mouse, Learn turns a row's caps up as the pointer comes onto the row and back down as it leaves.
if (matchMedia("(hover: hover) and (pointer: fine)").matches) {
  for (const { row } of sheet.rows()) {
    for (const type of ["pointerenter", "pointerleave"]) {
      row.addEventListener(type, (e) => {
        if (learning && e.pointerType === "mouse" && !row.classList.contains("is-revealed")) sheet.turn(row);
      });
    }
  }
}

$("print").addEventListener("click", () => window.print());

document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== input && !e.metaKey && !e.ctrlKey && !e.altKey) {
    e.preventDefault();
    input.focus();
    input.select();
  }
});

// The first visit plays the sheet once on its own; the person's first tap or key press ends it and restores their state.
if (!saved.introSeen && !reducedMotion && !learning && !input.value) {
  const stop = new AbortController();
  const end = () => {
    if (stop.signal.aborted) return;
    stop.abort();
    save({ introSeen: true });
    box.classList.remove("is-demo");
    setSearch(input.value && document.activeElement === input ? input.value : "", { persist: false });
    if (learning) setLearning(false);
  };
  for (const type of ["pointerdown", "keydown"]) addEventListener(type, end, { capture: true, once: true });
  playIntro({
    word: pickWord(sheet.rows()),
    input,
    box,
    filter: (v) => { box.classList.toggle("has-query", v !== ""); runFilter(v); },
    setLearning: (on) => setLearning(on),
    rows: sheet.rows,
    play: sheet.play,
    turn: sheet.turn,
    signal: stop.signal,
  }).then(() => { stop.abort(); save({ introSeen: true }); }).catch(() => {});
}
