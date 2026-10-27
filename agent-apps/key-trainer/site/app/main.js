// Key Trainer: reads the setup from config.js, runs the drill, shows results and history, and keeps settings.

import { LAYOUTS, loadLayout, codeForStat, capLabel } from "./layout.js";
import { passagesFor, drillText, weakText } from "./text.js";
import { Keyboard } from "./keyboard.js";
import { Line } from "./line.js";
import { Drill } from "./drill.js";
import { Ghost } from "./ghost.js";
import { Chart } from "./chart.js";
import * as store from "./store.js";

const config = window.__APP_CONFIG__ || {};
const $ = (id) => document.getElementById(id);
const root = document.documentElement;

const LAYOUT_NAMES = { qwerty: "QWERTY", qwertz: "QWERTZ", azerty: "AZERTY", dvorak: "Dvorak", colemak: "Colemak" };
const MODE_NAMES = { prose: "Prose", code: "Code", weak: "Weak keys" };
const MODE_NOTES = {
  prose: "Plain sentences with capitals and punctuation.",
  code: "Short programs with their indentation, brackets, and symbols. Enter ends each line.",
};

const desktopQuery = matchMedia("(min-width: 900px) and (min-height: 541px)");
const landscapeQuery = matchMedia("(orientation: landscape) and (max-height: 540px)");
const coarse = matchMedia("(pointer: coarse)");
const reduced = matchMedia("(prefers-reduced-motion: reduce)");

const state = {
  settings: null,
  layout: null,
  passages: [],
  passageAt: 0,
  drill: null,
  kind: "prose",
  weak: [],
  phase: "idle",
  rows: [],
  sample: true,
  sawKeys: false,
  lastDown: { code: "", at: 0 },
  timer: 0,
  hold: 0,
  resultsAt: 0,
  ghostRuns: 0,
  sampleDay: false,
  view: "drill",
};

const sink = $("sink");
const stage = $("stage");
const board = $("board");
const line = new Line($("line"), $("track"), $("caret"));
const kbDrill = new Keyboard($("kb-drill"), { fitHeight: fitBoard });
const kbHist = new Keyboard($("kb-history"), { maxUnit: 58 });
const chartSide = new Chart($("chart-side"));
const chartMain = new Chart($("chart-main"), { big: true });
const ghost = new Ghost({ type: (ch) => ghostType(ch), done: () => state.drill?.finish() });

/** How tall the drill keyboard may be: its grid cell on a desktop, what is left of the screen on a phone on its side. */
function fitBoard(host) {
  if (desktopQuery.matches) return host.clientHeight;
  if (landscapeQuery.matches) {
    const top = host.getBoundingClientRect().top + window.scrollY;
    return Math.max(150, window.innerHeight - top - 52);
  }
  return Infinity;
}

function settingsNow() {
  const saved = store.readSettings();
  const seconds = Number(saved.seconds || config.drillSeconds || 60);
  return {
    layout: LAYOUTS.includes(saved.layout) ? saved.layout : LAYOUTS.includes(config.layout) ? config.layout : "qwerty",
    mode: saved.mode === "code" || saved.mode === "prose" ? saved.mode : config.mode === "code" ? "code" : "prose",
    seconds: Number.isFinite(seconds) ? Math.min(600, Math.max(15, Math.round(seconds))) : 60,
    theme: saved.theme === "dark" || saved.theme === "light" ? saved.theme : "",
  };
}

function greet() {
  const hour = new Date().getHours();
  const part = hour < 5 ? "Good evening" : hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const name = typeof config.name === "string" ? config.name.trim() : "";
  $("greet").textContent = name ? `${part}, ${name}.` : `${part}.`;
}

function syncScheme() {
  const scheme = getComputedStyle(root).colorScheme || "";
  root.dataset.scheme = scheme.includes("dark") ? "dark" : "light";
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta) meta.setAttribute("content", state.settings.theme ? (state.settings.theme === "dark" ? "dark" : "light") : "light dark");
}

const fmtClock = (s) => {
  const whole = Math.max(0, Math.ceil(s));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
};
const fmtLength = (s) => (s % 60 === 0 ? (s === 60 ? "1 minute" : `${s / 60} minutes`) : `${s} seconds`);
const touchFirst = () => coarse.matches && !desktopQuery.matches;

/* The drill */

function newDrill(kind = "prose", same = null) {
  clearInterval(state.timer);
  const mode = state.settings.mode;
  let text = same;
  state.kind = kind;
  if (kind === "weak" && !text) {
    state.weak = store.weakKeys(store.pool(state.rows));
    text = weakText(state.weak, state.settings.seconds, mode);
    if (!text) state.kind = "prose";
  }
  if (!text) {
    text = drillText(state.passages, state.passageAt, state.settings.seconds, mode);
    state.passageAt = (state.passageAt + 1) % state.passages.length;
  }
  state.sawKeys = false;
  state.drill = new Drill({
    text,
    layout: state.layout,
    mode: state.kind === "weak" ? "weak" : mode,
    seconds: state.settings.seconds,
    handlers: { start: onStart, advance: onAdvance, wrong: onWrong, finish: onFinish },
  });
  line.setText(state.drill.chars, mode);
  kbDrill.showHeat(false);
  board.classList.remove("is-heat");
  kbDrill.setNext(state.drill.expected);
  $("kb-note").textContent = "The next key lights up as you go";
  $("clock").textContent = fmtClock(state.settings.seconds);
  $("clock-label").textContent = "to go";
  $("live-wpm").textContent = "0";
  $("live-acc").textContent = "100%";
  $("progress").style.setProperty("--p", "0");
  const chip = $("chip-mode");
  chip.textContent = state.kind === "weak" ? `Weak keys: ${state.weak.slice(0, 3).map((w) => capLabel(w.name)).join(" ")}` : MODE_NAMES[mode];
  chip.classList.toggle("is-weak", state.kind === "weak");
  $("chip-layout").textContent = LAYOUT_NAMES[state.layout.id];
}

function setHint() {
  const hint = $("hint");
  if (state.phase === "ghost") hint.textContent = touchFirst() ? "Sample run. Tap the line to type." : "Sample run. Start typing to take over.";
  else if (state.phase === "ready") {
    if (state.kind === "weak") hint.textContent = `Built from your weakest keys: ${state.weak.map((w) => capLabel(w.name)).join(", ")}.`;
    else hint.textContent = touchFirst() ? "Tap the line to bring up your keyboard." : "The clock starts with your first key.";
  } else if (state.phase === "running") hint.textContent = touchFirst() ? "Keep going. The clock is running." : "Esc starts over.";
}

function onStart() {
  line.typing(true);
  clearInterval(state.timer);
  state.timer = setInterval(tick, 200);
  if (state.phase === "ready") {
    state.phase = "running";
    setHint();
  }
}

function tick() {
  const d = state.drill;
  if (!d || d.finished) return;
  const now = performance.now();
  const used = d.elapsed(now);
  $("clock").textContent = fmtClock(d.seconds - used);
  $("live-wpm").textContent = used < 2 ? "0" : String(Math.round(d.wpm(now)));
  $("progress").style.setProperty("--p", Math.min(1, used / d.seconds).toFixed(4));
  if (used >= d.seconds) d.finish(now);
}

function onAdvance(index, missed, ch) {
  line.advance(index, missed);
  kbDrill.setNext(state.drill.expected);
  if (performance.now() - state.lastDown.at > 120) kbDrill.pressChar(ch);
  $("live-acc").textContent = `${Math.round(state.drill.accuracy() * 100)}%`;
}

function onWrong(index, typed) {
  line.wrong(index);
  if (performance.now() - state.lastDown.at < 120 && state.lastDown.code) kbDrill.flashCode(state.lastDown.code);
  else kbDrill.flash(typed);
  $("live-acc").textContent = `${Math.round(state.drill.accuracy() * 100)}%`;
}

function onFinish() {
  clearInterval(state.timer);
  tick();
  line.done();
  line.typing(false);
  const isGhost = state.phase === "ghost";
  const d = state.drill;
  const input = !isGhost && coarse.matches && !state.sawKeys ? "touch" : "keys";
  const { row, slow, missed } = d.result({ input });
  let pooledRows;
  if (isGhost) {
    pooledRows = state.rows.concat([row]);
  } else {
    if (row.chars >= 5) {
      state.rows = store.addDrill(row);
      state.sample = false;
    }
    pooledRows = state.rows;
  }
  $("clock").textContent = fmtClock(d.elapsed());
  $("clock-label").textContent = "typed";
  showResults(row, slow, missed, isGhost);
  const heat = codeHeat(store.heatByName(store.pool(pooledRows)));
  setTimeout(() => {
    if (state.drill !== d) return;
    if (isGhost && state.sample) showSampleDay(row);
    kbDrill.setNext(null);
    kbDrill.setHeat(heat);
    kbDrill.showHeat(true);
    board.classList.add("is-heat");
    $("kb-note").textContent = state.sample ? "Sample month" : "Your last 30 days";
  }, 280);
  if (!isGhost) {
    state.phase = "results";
    state.resultsAt = performance.now();
    refreshHistory({ draw: "grow" });
  } else {
    clearTimeout(state.hold);
    state.hold = setTimeout(() => {
      if (state.phase !== "ghost") return;
      hideResults();
      startGhost();
    }, 4200);
  }
}

function codeHeat(byName) {
  const out = new Map();
  for (const [name, v] of byName) {
    const code = codeForStat(state.layout, name);
    if (code) out.set(code, Math.max(out.get(code) || 0, v));
  }
  return out;
}

function chip(name, note, hot) {
  const li = document.createElement("li");
  li.className = `cap-chip${hot ? " is-hot" : ""}`;
  const key = document.createElement("span");
  key.className = "cap-chip-key";
  key.textContent = capLabel(name);
  const small = document.createElement("span");
  small.className = "cap-chip-note";
  small.textContent = note;
  li.append(key, small);
  return li;
}

function fillCaps(list, items, empty) {
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "caps-empty";
    li.textContent = empty;
    list.replaceChildren(li);
    return;
  }
  list.replaceChildren(...items);
}

function rollUp(node, to, decimals, ms = 950) {
  if (reduced.matches) {
    node.textContent = to.toFixed(decimals);
    return;
  }
  const began = performance.now();
  const frame = (now) => {
    const p = Math.min(1, (now - began) / ms);
    node.textContent = (to * (1 - Math.pow(1 - p, 3))).toFixed(decimals);
    if (p < 1) requestAnimationFrame(frame);
  };
  node.textContent = (0).toFixed(decimals);
  requestAnimationFrame(frame);
}

function showResults(row, slow, missed, isGhost) {
  const results = $("results");
  results.classList.remove("is-leaving");
  results.hidden = false;
  stage.classList.add("show-results");
  $("results-title").textContent = isGhost ? "Sample run" : "Your drill";
  const parts = [MODE_NAMES[row.mode] || "Prose", LAYOUT_NAMES[row.layout] || "", `${Math.round(row.seconds)} seconds`];
  if (row.input === "touch") parts.push("touch");
  $("results-sub").textContent = isGhost ? "Now you try. Start typing whenever you like." : parts.filter(Boolean).join(", ");
  rollUp($("res-wpm"), Math.round(row.wpm), 0);
  rollUp($("res-acc"), Math.round(row.accuracy * 1000) / 10, 1);
  fillCaps($("res-slow"), slow.map((s) => chip(s.name, `${Math.round(s.ms)} ms`, false)), "Too short to tell");
  fillCaps($("res-missed"), missed.map((m) => chip(m.name, m.errors === 1 ? "1 miss" : `${m.errors} misses`, true)), "No misses");
  $("btn-again").hidden = isGhost;
  $("btn-weak").hidden = isGhost;
}

function hideResults() {
  if (state.sampleDay) showSampleDay(null);
  const results = $("results");
  if (results.hidden) return;
  stage.classList.remove("show-results");
  results.classList.add("is-leaving");
  setTimeout(() => {
    results.hidden = true;
    results.classList.remove("is-leaving");
  }, 180);
}

function startGhost() {
  state.phase = "ghost";
  newDrill("prose");
  setHint();
  state.ghostRuns += 1;
  const chars = state.drill.chars;
  ghost.start(chars, {
    ms: 5200,
    seed: state.ghostRuns,
    slips: state.ghostRuns === 1 ? [8, 27] : [6, 23],
    wrongFor: (ch) => neighbor(ch),
  });
}

/** The character on the key just right of the one that types `ch`: the slip a real hand makes. */
function neighbor(ch) {
  const lower = ch.toLowerCase();
  for (const row of state.layout.rows) {
    const i = row.findIndex((k) => k.base === lower);
    if (i >= 0) {
      const next = row[i + 1] && row[i + 1].base && row[i + 1].base.length === 1 ? row[i + 1] : row[i - 1];
      if (next && next.base && next.base.length === 1 && next.base !== "\n") return next.base;
    }
  }
  return "x";
}

function ghostType(ch) {
  if (state.phase !== "ghost" || !state.drill) return;
  state.drill.type(ch);
}

/** The person takes over from the sample run on the same passage, from its first character. */
function takeOver() {
  ghost.stop();
  clearTimeout(state.hold);
  hideResults();
  newDrill("prose", state.drill ? state.drill.chars.join("") : null);
  state.phase = "ready";
  setHint();
}

function realInput(ch) {
  if (state.view !== "drill") return;
  if (state.phase === "ghost" || state.phase === "idle") takeOver();
  if (state.phase === "results") {
    if (performance.now() - state.resultsAt < 700) return;
    again(state.kind === "weak" ? "weak" : "prose");
    if (ch === "\n") return;
  }
  if (!state.drill || state.drill.finished) return;
  state.drill.type(ch);
}

function again(kind) {
  ghost.stop();
  clearTimeout(state.hold);
  hideResults();
  newDrill(kind);
  state.phase = "ready";
  setHint();
  focusSink();
}

function focusSink() {
  if (state.view !== "drill") return;
  if (touchFirst()) return;
  sink.focus({ preventScroll: true });
}

/* History */

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function when(date) {
  const d = new Date(date);
  const today = store.dayKey(Date.now());
  const yesterday = store.dayKey(Date.now() - 86400000);
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  const key = store.dayKey(d);
  if (key === today) return `Today, ${time}`;
  if (key === yesterday) return `Yesterday, ${time}`;
  return `${DAY_NAMES[d.getDay()]} ${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

function totalsInto(dl, t, big) {
  const items = [
    ["Drills", String(t.drills), ""],
    ["Minutes", String(t.minutes), ""],
    ["Best", String(t.best), "wpm"],
  ];
  if (big) items.push(["Accuracy", t.drills ? `${Math.round(t.accuracy * 1000) / 10}` : "0", "%"]);
  dl.replaceChildren(
    ...items.map(([label, value, unit]) => {
      const div = document.createElement("div");
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      if (unit) {
        const small = document.createElement("small");
        small.textContent = unit;
        dd.appendChild(small);
      }
      div.append(dt, dd);
      return div;
    }),
  );
}

/** On the sample month, the sample run's day is drawn onto the line while its results show, and taken off after. */
function showSampleDay(row) {
  state.sampleDay = Boolean(row);
  const rows = row ? state.rows.concat([row]) : state.rows;
  const days = store.lastDays(rows);
  const draw = row ? "grow" : "none";
  chartSide.setDays(days, { draw });
  chartMain.setDays(days, { draw });
  const t = store.totals(rows);
  totalsInto($("totals-side"), t, false);
  totalsInto($("totals-main"), t, true);
}

function refreshHistory({ draw = "none" } = {}) {
  state.sampleDay = false;
  const days = store.lastDays(state.rows);
  chartSide.setDays(days, { draw });
  chartMain.setDays(days, { draw });
  const t = store.totals(state.rows);
  totalsInto($("totals-side"), t, false);
  totalsInto($("totals-main"), t, true);
  for (const id of ["hist-status", "hist-status-2"]) {
    const s = $(id);
    s.textContent = state.sample ? "Sample month" : `${t.drills} ${t.drills === 1 ? "drill" : "drills"}`;
    s.classList.toggle("is-sample", state.sample);
  }
  const pooled = store.pool(state.rows);
  kbHist.setHeat(codeHeat(store.heatByName(pooled)));
  kbHist.showHeat(true);
  const weak = store.weakKeys(pooled);
  fillCaps(
    $("weak-list"),
    weak.map((w) => chip(w.name, `${Math.round(w.raw * 100)}% missed`, w.samples >= store.SETTLED)),
    "No weak keys yet. Finish a drill to see yours.",
  );
  $("btn-weak-2").hidden = weak.length === 0;
  const list = state.rows.slice(-12).reverse();
  $("drill-list").replaceChildren(
    ...list.map((r) => {
      const li = document.createElement("li");
      const a = document.createElement("span");
      a.className = "when";
      a.textContent = when(r.date);
      if (r.input === "touch") {
        const tag = document.createElement("span");
        tag.className = "touch-tag";
        tag.textContent = "touch";
        a.appendChild(tag);
      }
      const b = document.createElement("span");
      b.className = "what";
      b.textContent = `${MODE_NAMES[r.mode] || "Prose"}, ${LAYOUT_NAMES[r.layout] || "QWERTY"}`;
      const c = document.createElement("span");
      c.className = "speed";
      c.textContent = `${Math.round(r.wpm)} wpm`;
      const e = document.createElement("span");
      e.className = "acc-cell";
      e.textContent = `${Math.round(r.accuracy * 100)}%`;
      li.append(a, b, c, e);
      return li;
    }),
  );
}

/* Views and settings */

function showView(name) {
  if (name === state.view) return;
  if (state.view === "drill") {
    if (state.phase === "ghost") {
      ghost.stop();
      clearTimeout(state.hold);
      hideResults();
      newDrill("prose");
      state.phase = "ready";
      setHint();
    } else if (state.phase === "running") {
      again(state.kind);
    }
  }
  state.view = name;
  for (const view of ["drill", "history", "settings"]) {
    $(`view-${view}`).hidden = view !== name;
    $(`view-${view}`).classList.toggle("is-active", view === name);
  }
  document.querySelectorAll(".tab").forEach((tab) => {
    if (tab.dataset.view === name) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  });
  if (name === "drill") {
    kbDrill.resize(true);
    focusSink();
  }
  if (name === "history") kbHist.resize(true);
}

function markSeg(id, value) {
  $(id).querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.value === String(value))));
}

function syncSettings() {
  const s = state.settings;
  markSeg("set-layout", s.layout);
  markSeg("set-mode", s.mode);
  markSeg("set-seconds", s.seconds);
  markSeg("set-theme", s.theme);
  $("mode-note").textContent = MODE_NOTES[s.mode];
}

async function applyLayout(id) {
  state.layout = await loadLayout(id);
  state.passages = passagesFor(state.settings.mode, config.passages, state.layout.hasAccents);
  state.passageAt = 0;
  kbDrill.setLayout(state.layout);
  kbHist.setLayout(state.layout);
}

async function changeSetting(patch) {
  store.writeSettings(patch);
  state.settings = settingsNow();
  syncSettings();
  if ("theme" in patch) {
    if (state.settings.theme) root.setAttribute("data-theme", state.settings.theme);
    else root.removeAttribute("data-theme");
    syncScheme();
    return;
  }
  ghost.stop();
  clearTimeout(state.hold);
  hideResults();
  if ("layout" in patch) await applyLayout(state.settings.layout);
  else state.passages = passagesFor(state.settings.mode, config.passages, state.layout.hasAccents);
  newDrill("prose");
  state.phase = "ready";
  setHint();
  refreshHistory();
}

function buildSettings() {
  const seg = $("set-layout");
  seg.replaceChildren(
    ...LAYOUTS.map((id) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "radio");
      b.dataset.value = id;
      b.textContent = LAYOUT_NAMES[id];
      return b;
    }),
  );
  seg.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) changeSetting({ layout: b.dataset.value });
  });
  $("set-mode").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) changeSetting({ mode: b.dataset.value });
  });
  $("set-seconds").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) changeSetting({ seconds: Number(b.dataset.value) });
  });
  $("set-theme").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) changeSetting({ theme: b.dataset.value });
  });
  $("btn-export").addEventListener("click", () => {
    const rows = store.readHistory();
    const status = $("io-status");
    if (!rows.length) {
      status.textContent = "There are no drills to export yet. Finish one first.";
      return;
    }
    const blob = new Blob([JSON.stringify(rows, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `key-trainer-history-${store.dayKey(Date.now())}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    status.textContent = `Saved ${rows.length} ${rows.length === 1 ? "drill" : "drills"} to a file.`;
  });
  $("file-import").addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    const status = $("io-status");
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const rows = Array.isArray(data) ? data : Array.isArray(data.drills) ? data.drills : [];
      const added = store.importRows(rows);
      if (!rows.length) status.textContent = "That file has no drills in it.";
      else status.textContent = added ? `Added ${added} ${added === 1 ? "drill" : "drills"}.` : "Those drills are already here.";
      const real = store.readHistory();
      if (real.length) {
        state.rows = real;
        state.sample = false;
        refreshHistory({ draw: "full" });
      }
    } catch (error) {
      status.textContent = "That file is not a Key Trainer export.";
    }
    e.target.value = "";
  });
}

/* Input */

function flush() {
  const value = sink.value;
  if (!value) return;
  sink.value = "";
  for (const ch of Array.from(value.normalize("NFC"))) realInput(ch === "\r" ? "\n" : ch);
}

function wireInput() {
  sink.addEventListener("beforeinput", (e) => {
    const type = e.inputType || "";
    if (type === "insertLineBreak" || type === "insertParagraph") {
      e.preventDefault();
      realInput("\n");
    } else if (type.startsWith("delete")) {
      e.preventDefault();
    }
  });
  sink.addEventListener("input", (e) => {
    if (e.isComposing) return;
    flush();
  });
  sink.addEventListener("compositionend", () => flush());

  $("line-wrap").addEventListener("click", () => {
    sink.focus({ preventScroll: true });
    if (state.phase === "ghost") takeOver();
  });

  document.addEventListener("keydown", (e) => {
    if (e.isComposing) return;
    const real = e.code && e.key !== "Unidentified" && e.keyCode !== 229;
    if (real) {
      state.sawKeys = true;
      state.lastDown = { code: e.code, at: performance.now() };
      if (state.view === "drill" && document.activeElement === sink) kbDrill.press(e.code);
    }
    if (state.view !== "drill") return;
    if (e.key === "Escape") {
      if (state.phase === "running" || state.phase === "results") again(state.kind);
      return;
    }
    if (document.activeElement === sink) return;
    const control = e.target instanceof Element && e.target.closest("button, input, select, textarea, a, label");
    if (control && (e.key === "Enter" || e.key === " " || e.key === "Tab")) return;
    if (e.ctrlKey || e.metaKey) return;
    if (e.key.length === 1 || e.key === "Enter" || e.key === "Dead") {
      sink.focus({ preventScroll: true });
      if (e.key.length === 1 || e.key === "Dead") kbDrill.press(e.code);
    }
  });

  $("btn-again").addEventListener("click", () => again("prose"));
  $("btn-weak").addEventListener("click", () => again("weak"));
  $("btn-weak-2").addEventListener("click", () => {
    showView("drill");
    again("weak");
  });
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => showView(tab.dataset.view)));
  $("theme-btn").addEventListener("click", () => {
    const dark = root.dataset.scheme === "dark";
    changeSetting({ theme: dark ? "light" : "dark" });
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncScheme);
}

/* Start */

/** The thirty-day line draws once the page has finished loading, so it is not spent before anyone sees it. */
async function drawHistoryOnceSettled() {
  const loaded = document.readyState === "complete" ? null : new Promise((done) => addEventListener("load", done, { once: true }));
  await Promise.all([loaded, document.fonts.ready]);
  chartSide.play(450);
  chartMain.play(450);
}

async function start() {
  state.settings = settingsNow();
  greet();
  syncScheme();
  buildSettings();
  syncSettings();
  wireInput();
  const real = store.readHistory();
  state.sample = real.length === 0;
  state.rows = state.sample ? store.sampleMonth() : real;
  await applyLayout(state.settings.layout);
  refreshHistory({ draw: "held" });
  drawHistoryOnceSettled();
  if (reduced.matches) {
    newDrill("prose");
    state.phase = "ready";
    setHint();
    kbDrill.setHeat(codeHeat(store.heatByName(store.pool(state.rows))));
    kbDrill.showHeat(true);
    board.classList.add("is-heat");
    $("kb-note").textContent = state.sample ? "Sample month" : "Your last 30 days";
  } else {
    startGhost();
  }
  focusSink();
}

start().catch((error) => {
  $("hint").textContent = error && error.message ? error.message : "The keyboard layout did not load.";
});
