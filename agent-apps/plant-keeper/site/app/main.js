// Plant Keeper: the plants come from config.js; the waterings live in this browser.
import { calm, dropWater, placeLine, rollTo } from "./motion.js";
import { drawingFor, loadSprite, ringMarkup, setFill } from "./plants.js";
import { openSheet, refreshSheet, setupSheet } from "./sheet.js";
import * as store from "./store.js";
import { DAY, daysBetween, fmt, standing } from "./time.js";
import { agendaMarkup, daysMarkup, dueDays, initialFor, plantListMarkup, roomMarkup, tabsMarkup } from "./views.js";

const $ = (id) => document.getElementById(id);

/* ---------- The plants, from config.js ---------- */

function readConfig() {
  const cfg = window.__APP_CONFIG__ ?? {};
  const slug = (s) => String(s).trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "room";
  const plants = (Array.isArray(cfg.plants) ? cfg.plants : [])
    .filter((p) => p && typeof p.id === "string" && typeof p.name === "string")
    .map((p) => ({
      id: p.id,
      name: p.name,
      type: p.type ?? "",
      intervalDays: Math.max(1, Math.round(Number(p.intervalDays) || 7)),
      light: typeof p.light === "string" ? p.light : "",
      room: typeof p.room === "string" && p.room.trim() ? p.room.trim() : "Home",
      notes: typeof p.notes === "string" ? p.notes : "",
      wateredDaysAgo: Number.isFinite(Number(p.wateredDaysAgo)) ? Math.max(0, Number(p.wateredDaysAgo)) : 0,
    }));
  const names = [...(Array.isArray(cfg.rooms) ? cfg.rooms.filter((r) => typeof r === "string" && r.trim()).map((r) => r.trim()) : [])];
  for (const p of plants) if (!names.includes(p.room)) names.push(p.room);
  const rooms = names.filter((n) => plants.some((p) => p.room === n)).map((name) => ({ id: slug(name), name }));
  return { name: typeof cfg.name === "string" && cfg.name.trim() ? cfg.name.trim() : "My plants", plants, rooms };
}

const config = readConfig();
const roomOf = (plant) => config.rooms.find((r) => r.name === plant.room);
const roomName = (name) => name;
const sameDay = (a, b) => daysBetween(a, b) === 0;

const state = {
  now: Date.now(),
  log: store.loadLog(),
  notes: store.loadNotes(),
  room: "all",
  info: new Map(),
  thirsty: 0,
};

/** A plant with no waterings yet starts with a full ring now, or partway when the inputs say it was watered days ago. */
function seed(plants, now) {
  let changed = false;
  for (const p of plants) {
    if (store.lastWatering(state.log, p.id) !== null) continue;
    state.log[p.id] = [new Date(now - p.wateredDaysAgo * DAY).toISOString()];
    changed = true;
  }
  if (changed) store.saveLog(state.log);
}

function measure() {
  state.info.clear();
  for (const p of config.plants) state.info.set(p.id, standing(store.lastWatering(state.log, p.id), p.intervalDays, state.now));
}

/* ---------- Header ---------- */

function setCount(n) {
  const before = state.thirsty;
  state.thirsty = n;
  rollTo($("thirst-num"), n === 0 ? "No" : String(n), n > before);
  $("thirst-words").textContent = `${n === 1 ? "plant" : "plants"} thirsty today`;
  $("thirst").classList.toggle("is-calm", n === 0);
}

const thirstyCount = () => [...state.info.values()].filter((i) => i.state === "thirsty").length;

/* ---------- Cards ---------- */

const cardEl = (id) => document.querySelector(`.card[data-id="${CSS.escape(id)}"]`);

/** Paints a card from its standing. `f` overrides the ring while the opening drains it. */
function paintCard(el, info, { f = info.f, droop = info.state === "thirsty" } = {}) {
  setFill(el, f);
  el.dataset.state = info.state;
  el.classList.toggle("is-droopy", droop);
  el.querySelector(".card-status").textContent = info.text;
  el.dataset.fraction = info.f.toFixed(3);
}

function renderTabs() {
  const counts = new Map();
  for (const p of config.plants) {
    if (state.info.get(p.id).state !== "thirsty") continue;
    const id = roomOf(p).id;
    counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  const tabs = $("tabs");
  const line = $("tab-line");
  tabs.innerHTML = tabsMarkup(config.rooms, counts, state.room);
  tabs.prepend(line);
  placeLine(line, tabs.querySelector('[aria-selected="true"]'));
  $("rooms").setAttribute("aria-labelledby", `tab-${state.room}`);
  markEdges(tabs);
}

function renderRoomMeta() {
  for (const section of document.querySelectorAll(".room")) {
    const plants = config.plants.filter((p) => roomOf(p).id === section.dataset.room);
    const thirsty = plants.filter((p) => state.info.get(p.id).state === "thirsty").length;
    const count = `${plants.length} ${plants.length === 1 ? "plant" : "plants"}`;
    section.querySelector(".room-meta").textContent = thirsty ? `${count}, ${thirsty} thirsty` : count;
  }
}

function showRoom(id) {
  state.room = id;
  for (const section of document.querySelectorAll(".room")) section.hidden = id !== "all" && section.dataset.room !== id;
  $("rooms").classList.toggle("is-single", id !== "all");
  renderTabs();
}

function renderRooms() {
  $("rooms").setAttribute("role", "tabpanel");
  $("rooms").innerHTML = config.rooms.map((r) => roomMarkup(r, config.plants.filter((p) => p.room === r.name))).join("");
}

/* ---------- The strips fade at an edge while more lies past it ---------- */

function markEdges(el) {
  el.classList.toggle("has-before", el.scrollLeft > 2);
  el.classList.toggle("has-after", el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
}

/* ---------- The fourteen days, Schedule, and Settings ---------- */

function renderSchedule() {
  const days = dueDays(config.plants, state.info, state.now);
  $("strip").innerHTML = daysMarkup(days, state.now);
  markEdges($("strip"));
  $("calendar").innerHTML = daysMarkup(days, state.now);
  $("agenda").innerHTML = agendaMarkup(days, roomName);
}

function renderSettings() {
  const total = Object.values(state.log).reduce((n, list) => n + list.length, 0);
  const first = Math.min(...Object.values(state.log).flat().map((v) => Date.parse(v)));
  $("log-summary").textContent = total
    ? `${total} ${total === 1 ? "watering" : "waterings"} logged for ${config.plants.length} ${config.plants.length === 1 ? "plant" : "plants"} since ${fmt.monthDay(first)}.`
    : "Nothing logged yet.";
  $("plant-list").innerHTML = plantListMarkup(config.plants, roomName);
}

/** Brings every view up to date with the log, without the opening's drain. */
function refresh() {
  measure();
  for (const p of config.plants) {
    const el = cardEl(p.id);
    if (el) paintCard(el, state.info.get(p.id));
  }
  setCount(thirstyCount());
  renderTabs();
  renderRoomMeta();
  renderSchedule();
  renderSettings();
  refreshSheet();
}

/* ---------- Watering ---------- */

async function water(id, ring = cardEl(id)?.querySelector(".ring")) {
  const now = Date.now();
  state.now = now;
  store.addWatering(state.log, id, now, sameDay);
  store.saveLog(state.log);
  if (ring) await dropWater(ring);
  refresh();
}

function logChanged() {
  store.saveLog(state.log);
  state.now = Date.now();
  refresh();
}

/* ---------- The opening: every ring drains from full to where it stands ---------- */

function opening() {
  const cards = [...document.querySelectorAll(".card")];
  if (calm()) {
    for (const el of cards) paintCard(el, state.info.get(el.dataset.id));
    return;
  }
  for (const el of cards) {
    paintCard(el, state.info.get(el.dataset.id), { f: 0, droop: false });
    el.classList.add("is-opening");
  }
  const drain = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--motion-drain")) || 1000;
  requestAnimationFrame(() => {
    cards.forEach((el, i) => {
      const info = state.info.get(el.dataset.id);
      const start = 120 + i * 45;
      setTimeout(() => paintCard(el, info, { droop: false }), start);
      setTimeout(() => {
        el.classList.remove("is-opening");
        if (info.state !== "thirsty") return;
        el.classList.add("is-droopy");
      }, start + drain * 0.45);
    });
  });
}

/* ---------- Views and keys ---------- */

function route() {
  const view = ["plants", "schedule", "settings"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "plants";
  for (const v of ["plants", "schedule", "settings"]) $(`view-${v}`).hidden = v !== view;
  document.body.dataset.view = view;
  for (const a of document.querySelectorAll(".view-link")) {
    if (a.dataset.view === view) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  if (view === "plants") placeLine($("tab-line"), $("tabs").querySelector('[aria-selected="true"]'));
}

function wire() {
  $("rooms").addEventListener("click", (event) => {
    const card = event.target.closest(".card");
    if (!card) return;
    if (event.target.closest(".water")) water(card.dataset.id);
    else if (event.target.closest(".card-open")) openSheet(card.dataset.id);
  });

  $("tabs").addEventListener("click", (event) => {
    const tab = event.target.closest(".tab");
    if (tab) showRoom(tab.dataset.room);
  });
  $("tabs").addEventListener("keydown", (event) => {
    const tabs = [...$("tabs").querySelectorAll(".tab")];
    const at = tabs.indexOf(document.activeElement);
    if (at < 0) return;
    const to = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 }[event.key];
    if (to === undefined) return;
    event.preventDefault();
    const next = tabs[(to + tabs.length) % tabs.length];
    showRoom(next.dataset.room);
    $("tabs").querySelector(`[data-room="${CSS.escape(next.dataset.room)}"]`).focus();
  });

  for (const el of [$("tabs"), $("strip")]) {
    el.addEventListener("scroll", () => markEdges(el), { passive: true });
    new ResizeObserver(() => markEdges(el)).observe(el);
  }

  addEventListener("hashchange", route);
  addEventListener("resize", () => placeLine($("tab-line"), $("tabs").querySelector('[aria-selected="true"]')));

  $("export").addEventListener("click", () => {
    const blob = new Blob([store.exportFile(state.log, state.notes, Date.now())], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `plant-keeper-log-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  $("import").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const note = $("import-note");
    try {
      const { added, plants } = store.mergeImport(await file.text(), state.log, state.notes);
      store.saveNotes(state.notes);
      logChanged();
      note.classList.remove("is-error");
      note.textContent = added
        ? `Added ${added} ${added === 1 ? "watering" : "waterings"} across ${plants} ${plants === 1 ? "plant" : "plants"}.`
        : "Everything in that file was already here.";
    } catch (error) {
      note.classList.add("is-error");
      note.textContent = error.message;
    }
  });

  $("clear").addEventListener("click", () => $("confirm").showModal());
  $("confirm").addEventListener("close", () => {
    if ($("confirm").returnValue !== "clear") return;
    store.clearAll();
    state.log = {};
    state.notes = {};
    const now = Date.now();
    for (const p of config.plants) state.log[p.id] = [new Date(now).toISOString()];
    logChanged();
    $("import-note").textContent = "The log starts over today.";
  });

  setInterval(tick, 60000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) tick();
  });
}

let shownDay = Date.now();
function tick() {
  state.now = Date.now();
  if (!sameDay(shownDay, state.now)) {
    shownDay = state.now;
    $("today").textContent = fmt.long(state.now);
  }
  refresh();
}

/* ---------- Start ---------- */

async function start() {
  document.title = config.name;
  $("title").textContent = config.name;
  $("today").textContent = fmt.long(state.now);
  // The header shows the true count before anything else is drawn.
  seed(config.plants, state.now);
  measure();
  setCount(thirstyCount());
  try {
    await loadSprite("./assets/plants.svg");
  } catch {
    // The rings and names still show; only the drawings are missing.
  }
  renderRooms();
  renderTabs();
  renderRoomMeta();
  renderSchedule();
  renderSettings();
  setupSheet({
    plantById: (id) => config.plants.find((p) => p.id === id),
    state,
    ringMarkup: (plant) => ringMarkup(drawingFor(plant.type, plant.name), initialFor(plant, drawingFor(plant.type, plant.name))),
    water,
    logChanged,
    saveNotes: () => store.saveNotes(state.notes),
    sameDay,
  });
  route();
  wire();
  opening();
  document.documentElement.classList.add("is-ready");
}

start();
