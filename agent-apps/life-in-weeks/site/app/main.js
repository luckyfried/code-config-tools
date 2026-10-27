// Life in Weeks: reads config.js, draws the grid, sizes it to the screen, runs the sweep, and wires the theme and print.

import { count, longDate, ordinal, parseDay, yearOf } from "./life.js";
import { buildModel, readConfig } from "./model.js";
import { createGrid } from "./grid.js";
import { createMargins } from "./margins.js";
import { createTip } from "./tip.js";

const STORE = "life-in-weeks:theme";
const MARGIN_LEFT = 19;
const MARGIN_RIGHT = 20;
const SIDE_PAD = 1.5;
const ROWS_AROUND = 5;
const NARROW_MARGIN = 18;

const root = document.documentElement;
const $ = (selector) => document.querySelector(selector);
const clamp = (low, value, high) => Math.min(high, Math.max(low, value));
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

const { config, sample } = readConfig();
const model = buildModel(config);
const paper = ["A2", "A3", "A4", "Letter"].includes(config.paper) ? config.paper : "A3";

root.dataset.paper = paper;
root.style.setProperty("--rows", String(model.rows));
root.style.setProperty("--margin-l", String(MARGIN_LEFT));
root.style.setProperty("--margin-r", String(MARGIN_RIGHT));

// The words: the name, the birthdate, the tally, the key, and the line.
function writeText() {
  const name = String(config.name ?? "").trim();
  $(".name").textContent = name;
  document.title = name ? `${name}, in weeks` : "Life in Weeks";
  $(".born").textContent = `Born ${longDate(parseDay(config.birthdate))}`;
  if (sample) {
    const status = $(".status");
    status.textContent = "Sample life";
    status.hidden = false;
  }

  const ahead = Math.max(0, model.cells - model.lived - (model.now === null ? 0 : 1));
  $('[data-tally="lived"]').textContent = count.format(model.lived);
  $('[data-tally="ahead"]').textContent = ahead
    ? `${count.format(ahead)} more to reach ${model.rows}`
    : `Every week to ${model.rows} is lived`;
  if (model.now !== null) {
    const { age, week } = model.life.spanOf(model.now);
    $('[data-tally="now"]').textContent = `This week: age ${age}, the ${ordinal(week + 1)} week`;
  } else {
    $(".tally-now").hidden = true;
  }

  $(".key-eras").replaceChildren(...model.eras.map((era) => {
    const item = document.createElement("li");
    item.className = "key-era";
    const swatch = document.createElement("span");
    swatch.className = "swatch swatch-era";
    swatch.setAttribute("aria-hidden", "true");
    swatch.style.setProperty("--era-c", era.color);
    const label = document.createElement("span");
    label.className = "key-label";
    label.textContent = era.label;
    const years = document.createElement("span");
    years.className = "key-years";
    const from = yearOf(era.firstDay);
    const to = era.still ? "now" : String(yearOf(era.lastDay));
    years.textContent = String(from) === to ? to : `${from}–${to}`;
    item.append(swatch, label, years);
    return item;
  }));

  // Where the right margin is off (a phone), the days to remember are listed under the tally instead.
  $(".key-events").replaceChildren(...model.events.map((event) => {
    const item = document.createElement("li");
    item.className = event.cell < model.lived ? "key-event" : "key-event ahead";
    const swatch = document.createElement("span");
    swatch.className = "swatch swatch-event";
    swatch.setAttribute("aria-hidden", "true");
    const label = document.createElement("span");
    label.textContent = event.label;
    const year = document.createElement("span");
    year.className = "key-years";
    year.textContent = String(yearOf(event.day));
    item.append(swatch, label, year);
    return item;
  }));
  $(".key-events").hidden = model.events.length === 0;

  const quote = String(config.quote ?? "").trim();
  if (quote) {
    const split = quote.lastIndexOf(" — ");
    const line = split > 0 ? quote.slice(0, split) : quote;
    const by = split > 0 ? quote.slice(split + 3).trim() : "";
    $(".quote-line").textContent = line;
    if (by) {
      $(".quote-by").textContent = by;
      $(".quote-by").hidden = false;
    }
    $(".quote").hidden = false;
  }

  $(".tool-print .tool-label").textContent = "Print";
  const more = document.createElement("span");
  more.className = "tool-more";
  more.textContent = ` the ${paper} poster`;
  $(".tool-print .tool-label").append(more);

  const svg = $(".weeks");
  svg.setAttribute("aria-label", `${name || "A life"}: ${count.format(model.lived)} of ${count.format(model.cells)} weeks lived.`);
}

writeText();

const svg = $(".weeks");
const wrap = $(".grid-wrap");
const ring = $(".now-ring");
const grid = createGrid(svg, model);
const margins = createMargins({ left: $(".margin-left"), right: $(".margin-right"), ticks: $(".week-ticks") }, model);
const tip = createTip({ wrap, svg, tip: $(".tip"), cursor: $(".cursor"), live: $("[data-live]") }, model);

if (model.now !== null) {
  ring.style.setProperty("--nx", String(model.now % model.columns));
  ring.style.setProperty("--ny", String(Math.floor(model.now / model.columns)));
} else {
  ring.hidden = true;
}

// Sizing: the whole life fits the screen's height on a desktop; on a phone 52 weeks fill the width; a phone on its
// side puts the words beside the grid.
let current = { mode: "", pitch: 0 };
let words = [];

function fit() {
  const w = root.clientWidth;
  const h = window.innerHeight;
  const across = MARGIN_LEFT + model.columns + MARGIN_RIGHT + 2 * SIDE_PAD;
  let mode;
  let pitch;
  if (w >= 1100 && h >= 600) {
    mode = "wide";
    const aside = clamp(320, w * 0.28, 460);
    const byHeight = Math.floor((h - 40) / (model.rows + ROWS_AROUND));
    const byWidth = Math.floor((w - 64 - aside - 64) / across);
    pitch = clamp(6, Math.min(byHeight, byWidth), 14);
  } else if (w >= 680 && h < 600 && w > h) {
    mode = "side";
    const aside = clamp(220, w * 0.34, 340);
    pitch = clamp(5, Math.floor((w - aside - 80 - 18) / model.columns), 10);
  } else if (w >= 680) {
    mode = "mid";
    pitch = clamp(6, Math.floor((Math.min(w, 1100) - 48) / across), 12);
  } else {
    mode = "narrow";
    pitch = clamp(4, Math.floor((w - 26) / model.columns), 9);
  }
  if (mode === current.mode && pitch === current.pitch) return;
  current = { mode, pitch };
  root.dataset.mode = mode;
  root.style.setProperty("--pitch", `${pitch}px`);

  // Label line heights in rows, from the type sizes chart.css sets for this pitch.
  const eraRows = (Math.max(13, 1.55 * pitch) * 1.3) / pitch;
  const wordRows = (Math.max(12, 1.3 * pitch) * 1.4) / pitch;
  words = margins.layout({ eraRows, wordRows });
  const compact = mode === "narrow" || mode === "side";
  grid.layout({ pitch, marginLeft: compact ? NARROW_MARGIN / pitch : MARGIN_LEFT, wordRows: words });
  tip.refresh();
}

// On paper every layout carries its full margins, so the bands reach the era labels there too.
function paperLayout() {
  grid.layout({ pitch: current.pitch, marginLeft: MARGIN_LEFT, wordRows: words });
}

function screenLayout() {
  current = { mode: "", pitch: 0 };
  fit();
}

window.addEventListener("beforeprint", paperLayout);
window.addEventListener("afterprint", screenLayout);
window.matchMedia("print").addEventListener("change", (event) => (event.matches ? paperLayout() : screenLayout()));

let pending = 0;
window.addEventListener("resize", () => {
  cancelAnimationFrame(pending);
  pending = requestAnimationFrame(fit);
});
fit();

// The sweep: the lived weeks arrive diagonal by diagonal from the top-left corner, within 1.5 s.
function settle() {
  svg.classList.remove("is-sweeping");
  wrap.classList.add("is-settled");
}

// The sweep waits for the page to finish loading and its type to settle, then plays on a still page.
function sweep() {
  svg.classList.add("is-sweeping");
  const length = parseFloat(getComputedStyle(root).getPropertyValue("--motion-sweep")) || 1500;
  setTimeout(settle, length + 60);
}

if (reduceMotion.matches || model.lived === 0) {
  settle();
} else {
  svg.classList.add("is-waiting");
  const loaded = document.readyState === "complete" ? Promise.resolve() : new Promise((go) => window.addEventListener("load", go, { once: true }));
  Promise.all([loaded, document.fonts.ready]).then(() => {
    setTimeout(() => {
      svg.classList.remove("is-waiting");
      sweep();
    }, 300);
  });
}

// The theme: the inputs pick the default; the switch flips it and this device remembers.
function scheme() {
  const picked = root.getAttribute("data-theme");
  if (picked === "light" || picked === "dark") return picked;
  if (config.theme === "paper") return "light";
  if (config.theme === "ink") return "dark";
  return systemDark.matches ? "dark" : "light";
}

function showScheme() {
  const now = scheme();
  root.dataset.scheme = now;
  $(".tool-theme").setAttribute("aria-label", now === "dark" ? "Switch to the paper theme" : "Switch to the ink theme");
}

$(".tool-theme").addEventListener("click", () => {
  const next = scheme() === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try {
    localStorage.setItem(STORE, next);
  } catch (error) {
    // Storage can be off; the switch still holds for this visit.
  }
  showScheme();
});
systemDark.addEventListener("change", showScheme);
showScheme();

$(".tool-print").addEventListener("click", () => {
  tip.hide();
  window.print();
});

// What run.py worked out on the day it ran, beside what the page filled today (data-lived), for a check to compare.
const data = window.__LIFE_DATA__;
if (data && typeof data.lived === "number") {
  svg.dataset.livedOnRun = String(data.lived);
  svg.dataset.runDay = String(data.asOf);
}
