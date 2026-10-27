// Focus Blocks: the timer, its controls, and the record it leaves.
import { chime, unlockAudio } from "./chime.js";
import { dayTotal, renderList, renderStrip, renderWeek } from "./record.js";
import { createRing } from "./ring.js";
import { sampleState } from "./sample.js";
import { isBlock, load, merge, save } from "./store.js";
import { MINUTE, clock, duration, greeting, isoDate, startOfDay, timeOfDay } from "./time.js";

const raw = window.__APP_CONFIG__ || {};
const cfg = {
  name: typeof raw.name === "string" ? raw.name.trim() : "",
  blockLengths: (Array.isArray(raw.blockLengths) ? raw.blockLengths : []).filter((n) => Number.isInteger(n) && n > 0 && n <= 240),
  labels: (Array.isArray(raw.labels) ? raw.labels : []).filter((s) => typeof s === "string" && s.trim()).map((s) => s.trim()),
  dayStart: Number.isInteger(raw.dayStart) ? raw.dayStart : 6,
  dayEnd: Number.isInteger(raw.dayEnd) ? raw.dayEnd : 24,
  chime: raw.chime === "off" ? "off" : "soft",
  sample: raw.sample === true,
};
if (!cfg.blockLengths.length) cfg.blockLengths = [25, 50, 90];
if (!(cfg.dayStart >= 0 && cfg.dayEnd <= 24 && cfg.dayEnd > cfg.dayStart)) Object.assign(cfg, { dayStart: 6, dayEnd: 24 });

const $ = (id) => document.getElementById(id);
const root = document.documentElement;
const coarse = matchMedia("(pointer: coarse)").matches;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");

if (!(window.CSS && CSS.registerProperty)) root.classList.add("no-mesh-motion");
if (getComputedStyle(root).getPropertyValue("--mesh-opacity").trim() === "0") root.classList.add("no-mesh");

let state = load();
if (!state) {
  state = cfg.sample ? sampleState(cfg, Date.now()) : { blocks: [], active: null, pick: null };
  save(state);
}
if (!state.pick) state.pick = { minutes: cfg.blockLengths[0], label: "" };

const ring = createRing({ fill: $("ring-fill"), sec: $("ring-sec"), ticks: $("ticks"), scope: root });
const ui = {
  greet: $("greet"),
  helloSub: $("hello-sub"),
  ring: $("ring"),
  label: $("ring-label"),
  time: $("ring-time"),
  status: $("ring-state"),
  controls: $("controls"),
  pause: $("pause"),
  giveUp: $("give-up"),
  setup: $("setup"),
  minutes: $("minutes"),
  labelInput: $("label"),
  lengths: $("lengths"),
  labelPicks: $("label-picks"),
  start: $("start"),
};

const FINAL_MS = 12_000; // the last stretch of a block, when the whole dial burns ember
let note = null; // { text, until } shown under the clock for a while
let escArmed = 0;
let stripTicks = [];
let renderedDay = 0;
let lastSecond = -1;

// Time left in the active block, from its start timestamp and the clock, never from counted ticks.
function remaining(a, now) {
  const paused = a.pausedMs + (a.pausedAt ? now - a.pausedAt : 0);
  return a.ms - (now - a.start - paused);
}

function clampMinutes(n) {
  return Math.min(240, Math.max(1, Math.round(n) || cfg.blockLengths[0]));
}

function withTransition(fn) {
  if (document.startViewTransition && !reduced.matches && !document.hidden) document.startViewTransition(fn);
  else fn();
}

/* Setup controls */
function buildSetup() {
  const minutesField = ui.minutes.closest(".minutes");
  for (const m of cfg.blockLengths) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.dataset.minutes = String(m);
    chip.append(`${m} `);
    const unit = document.createElement("span");
    unit.className = "chip__unit";
    unit.textContent = "min";
    chip.append(unit);
    chip.addEventListener("click", () => setMinutes(m));
    ui.lengths.insertBefore(chip, minutesField);
  }
  for (const name of cfg.labels) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.dataset.label = name;
    chip.textContent = name;
    chip.addEventListener("click", () => setLabel(ui.labelInput.value.trim() === name ? "" : name));
    ui.labelPicks.append(chip);
  }
  ui.labelPicks.hidden = cfg.labels.length === 0;
  ui.minutes.value = String(state.pick.minutes);
  ui.labelInput.value = state.pick.label;
  ui.minutes.addEventListener("input", () => {
    const n = Number(ui.minutes.value);
    if (n >= 1 && n <= 240) setMinutes(n, { keepField: true });
  });
  ui.minutes.addEventListener("change", () => setMinutes(clampMinutes(Number(ui.minutes.value))));
  ui.labelInput.addEventListener("input", () => setLabel(ui.labelInput.value, { keepField: true }));
  ui.setup.addEventListener("submit", (e) => {
    e.preventDefault();
    startBlock();
  });
  syncSetup();
}

function setMinutes(m, { keepField = false } = {}) {
  state.pick.minutes = clampMinutes(m);
  if (!keepField) ui.minutes.value = String(state.pick.minutes);
  save(state);
  syncSetup();
  tick();
}

function setLabel(text, { keepField = false } = {}) {
  state.pick.label = text.slice(0, 40);
  if (!keepField) ui.labelInput.value = state.pick.label;
  save(state);
  syncSetup();
  tick();
}

function syncSetup() {
  for (const chip of ui.lengths.querySelectorAll(".chip")) {
    chip.setAttribute("aria-pressed", String(Number(chip.dataset.minutes) === state.pick.minutes));
  }
  for (const chip of ui.labelPicks.querySelectorAll(".chip")) {
    chip.setAttribute("aria-pressed", String(chip.dataset.label === state.pick.label.trim()));
  }
  ui.start.textContent = `Start ${state.pick.minutes}-minute block`;
}

/* The block */
function startBlock() {
  unlockAudio();
  const minutes = clampMinutes(Number(ui.minutes.value) || state.pick.minutes);
  const label = ui.labelInput.value.trim();
  state.pick = { minutes, label };
  state.active = { start: Date.now(), ms: minutes * MINUTE, label, pausedAt: null, pausedMs: 0 };
  note = null;
  save(state);
  withTransition(() => {
    renderMode();
    tick();
  });
  renderRecord();
  ensureLoop();
}

function pauseBlock() {
  const a = state.active;
  if (!a || a.pausedAt) return;
  a.pausedAt = Date.now();
  save(state);
  renderMode();
  tick();
}

function resumeBlock() {
  const a = state.active;
  if (!a || !a.pausedAt) return;
  unlockAudio();
  a.pausedMs += Date.now() - a.pausedAt;
  a.pausedAt = null;
  save(state);
  renderMode();
  ensureLoop();
  tick();
}

function giveUp() {
  if (!state.active) return;
  state.active = null;
  escArmed = 0;
  note = { text: "Given up. Nothing was added.", until: Date.now() + 5000 };
  save(state);
  withTransition(() => {
    renderMode();
    tick();
  });
  renderRecord();
}

function finish(away) {
  const a = state.active;
  const block = { start: a.start, end: a.start + a.ms + a.pausedMs, label: a.label };
  state.blocks.push(block);
  state.blocks.sort((x, y) => x.start - y.start);
  // A block that names the next one (the sample's does) hands the ring straight to it, full and cool.
  const next = !away && a.next ? a.next : null;
  state.active = next ? { start: Date.now(), ms: next.minutes * MINUTE, label: next.label, pausedAt: null, pausedMs: 0 } : null;
  save(state);
  if (!away && cfg.chime === "soft") chime();
  const what = `${duration(a.ms)}${a.label ? ` of ${a.label}` : ""}`;
  note = { text: away ? `Finished while you were away: ${what}.` : `Done: ${what}.`, until: Date.now() + 9000 };
  withTransition(() => {
    renderMode();
    tick();
    if (!away) bloom();
  });
  renderRecord({ landed: block.start });
}

// The finish: the ring snaps back to full and a ring of light blooms out of it, while the block lands on the strip.
let bloomTimer = 0;
function bloom() {
  if (reduced.matches || document.hidden) return;
  clearTimeout(bloomTimer);
  root.classList.remove("is-complete");
  void root.offsetWidth;
  root.classList.add("is-complete");
  bloomTimer = setTimeout(() => root.classList.remove("is-complete"), 1800);
}

function toggle() {
  const a = state.active;
  if (!a) startBlock();
  else if (a.pausedAt) resumeBlock();
  else pauseBlock();
}

// Giving up takes two presses of Esc or two taps of Give up within 2.5 s, so one stray press never loses a block.
function armGiveUp() {
  const now = Date.now();
  if (escArmed && now - escArmed < 2500) {
    giveUp();
    return;
  }
  escArmed = now;
  tick();
}

/* Drawing */
function renderMode() {
  const a = state.active;
  root.classList.toggle("is-running", Boolean(a));
  root.classList.toggle("is-paused", Boolean(a && a.pausedAt));
  ui.controls.hidden = !a;
  ui.pause.textContent = a && a.pausedAt ? "Resume" : "Pause";
  ui.ring.setAttribute("aria-label", !a ? "Start the block" : a.pausedAt ? "Resume the block" : "Pause the block");
  ui.greet.textContent = greeting(Date.now(), cfg.name);
}

// `grow` grows every block into place; `landed` is the start of the block that just ended.
function renderRecord({ grow = false, landed = null } = {}) {
  const now = Date.now();
  const day0 = startOfDay(now);
  renderedDay = day0;
  const live = state.active ? { start: state.active.start } : null;
  const blocks = state.blocks;
  stripTicks = [renderStrip($("today-strip"), { blocks, day0, cfg, grow, landed, live, labels: true, nowLine: true })];
  renderList($("today-list"), blocks, day0, { grow, landed });
  const week = renderWeek($("week-rows"), $("week-sum"), { blocks, day0, cfg, grow, landed, live, nowLine: true });
  const peek = renderWeek($("peek-rows"), null, { blocks, day0, cfg, grow, landed, tag: "span", live, nowLine: true });
  stripTicks.push(...week.updaters, ...peek.updaters);
  $("today-total").textContent = duration(dayTotal(blocks, day0));
  $("peek-total").textContent = duration(week.total);
  $("week-total").textContent = duration(week.total);
  const todayMs = dayTotal(blocks, day0);
  ui.helloSub.textContent = todayMs > 0 ? `${duration(todayMs)} of deep work today.` : "Pick a length and start your first block.";
  for (const t of stripTicks) t(now);
}

function tick() {
  const now = Date.now();
  if (startOfDay(now) !== renderedDay) renderRecord();
  const a = state.active;
  if (note && now > note.until) note = null;
  if (escArmed && now - escArmed >= 2500) escArmed = 0;

  if (a) {
    const left = remaining(a, now);
    if (left <= 0) {
      finish(false);
      return;
    }
    const frac = left / a.ms;
    ring.fill(frac);
    ring.seconds(a.ms - left);
    const second = Math.ceil(left / 1000);
    if (second !== lastSecond) {
      lastSecond = second;
      ring.heat((1 - frac) ** 2.2);
      ring.final(1 - left / FINAL_MS);
      const text = clock(left);
      ui.time.textContent = text;
      ui.time.classList.toggle("is-long", text.length > 5);
      ui.label.textContent = a.label || "Focus";
      document.title = `${a.pausedAt ? "Paused " : ""}${text} · ${a.label || "focus"}`;
      for (const t of stripTicks) t(now);
    }
    ui.giveUp.textContent = escArmed ? "Give up now" : "Give up";
    ui.giveUp.classList.toggle("is-armed", Boolean(escArmed));
    ui.status.textContent = escArmed
      ? coarse
        ? "Tap Give up again to end it"
        : "Press Esc or click Give up again to end it"
      : a.pausedAt
        ? "Paused"
        : note
          ? note.text
          : `Until ${timeOfDay(now + left)}`;
    return;
  }

  lastSecond = -1;
  ring.fill(1);
  ring.heat(0);
  ring.final(0);
  ring.seconds(null);
  const text = clock(state.pick.minutes * MINUTE);
  ui.time.textContent = text;
  ui.time.classList.toggle("is-long", text.length > 5);
  ui.label.textContent = state.pick.label.trim() || "Focus";
  ui.status.textContent = note ? note.text : coarse ? "Tap to start" : "Press space to start";
  document.title = "Focus Blocks";
}

let raf = 0;
function loop() {
  raf = 0;
  tick();
  ensureLoop();
}
function ensureLoop() {
  if (!raf && state.active && !state.active.pausedAt && !document.hidden) raf = requestAnimationFrame(loop);
}

/* The phone sheet */
function setSheet(open) {
  root.classList.toggle("is-sheet-open", open);
  $("peek").setAttribute("aria-expanded", String(open));
  if (open) $("sheet-close").focus({ preventScroll: true });
  else if (document.activeElement && $("sheet").contains(document.activeElement)) $("peek").focus({ preventScroll: true });
}
const sheetOpen = () => root.classList.contains("is-sheet-open");

/* Export and import */
function exportBlocks() {
  const name = `focus-blocks-${isoDate(Date.now())}.json`;
  const body = JSON.stringify({ app: "focus-blocks", exported: new Date().toISOString(), blocks: state.blocks }, null, 2);
  const url = URL.createObjectURL(new Blob([body], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
  ioNote(`Saved ${state.blocks.length} ${state.blocks.length === 1 ? "block" : "blocks"} to ${name}.`);
}

async function importBlocks(file) {
  let data;
  try {
    data = JSON.parse(await file.text());
  } catch {
    ioNote(`${file.name} is not a Focus Blocks export. Pick a file the Export button saved.`, true);
    return;
  }
  const list = Array.isArray(data) ? data : data && Array.isArray(data.blocks) ? data.blocks : null;
  if (!list || !list.some(isBlock)) {
    ioNote(`${file.name} has no blocks in it. Pick a file the Export button saved.`, true);
    return;
  }
  const added = merge(state.blocks, list);
  save(state);
  renderRecord({ grow: true });
  ioNote(added ? `Added ${added} ${added === 1 ? "block" : "blocks"} from ${file.name}.` : `Every block in ${file.name} is already here.`);
}

function ioNote(text, error = false) {
  const n = $("io-note");
  n.textContent = text;
  n.classList.toggle("is-error", error);
}

/* Wiring */
ui.ring.addEventListener("click", () => toggle());
ui.pause.addEventListener("click", () => toggle());
ui.giveUp.addEventListener("click", armGiveUp);
$("peek").addEventListener("click", () => setSheet(true));
$("sheet-close").addEventListener("click", () => setSheet(false));
$("scrim").addEventListener("click", () => setSheet(false));
$("export").addEventListener("click", exportBlocks);
$("import-file").addEventListener("change", (e) => {
  const file = e.target.files && e.target.files[0];
  if (file) importBlocks(file);
  e.target.value = "";
});

document.addEventListener("pointerdown", unlockAudio, { passive: true });
document.addEventListener("keydown", (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const tag = e.target && e.target.tagName;
  if (e.key === "Escape") {
    if (sheetOpen()) {
      setSheet(false);
      return;
    }
    if (state.active) {
      e.preventDefault();
      armGiveUp();
    }
    return;
  }
  if (e.code === "Space" || e.key === " ") {
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "BUTTON" || tag === "SELECT" || tag === "LABEL") return;
    if (sheetOpen()) return;
    e.preventDefault();
    unlockAudio();
    toggle();
  }
});

document.addEventListener("visibilitychange", () => {
  root.classList.toggle("is-hidden", document.hidden);
  tick();
  ensureLoop();
});
matchMedia("(min-width: 960px)").addEventListener("change", (e) => {
  if (e.matches) setSheet(false);
});

// A block that ended while the page was closed is recorded now, at its true end.
if (state.active && !state.active.pausedAt && remaining(state.active, Date.now()) <= 0) finish(true);

buildSetup();
renderMode();
renderRecord({ grow: true });
tick();
ensureLoop();
setInterval(() => {
  tick();
  ensureLoop();
}, 500);
