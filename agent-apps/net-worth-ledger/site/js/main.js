// Net worth: reads the ledger, draws the chart, the headline, the donut, and the table, and plays the
// opening once: the chart sweeps in from the left while the month cursor rides its edge.
import { makeFormat } from "./format.js";
import { readLedger } from "./ledger.js";
import { createChart } from "./chart.js";
import { createScrubber } from "./scrubber.js";
import { createDonut } from "./donut.js";
import { createRoll } from "./roll.js";
import { renderTable } from "./table.js";

const $ = (id) => document.getElementById(id);
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const reduced = () => motionQuery.matches;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

const model = readLedger();
const fmt = makeFormat(model.currency);
const { points } = model;
const n = points.length;
const latest = points[n - 1];

if (model.title) $("ledger-title").textContent = model.title;
document.documentElement.dataset.latestNet = latest ? String(latest.net) : "";

// Headline and legend for one month.
const roll = createRoll($("headline-roll"));
const legend = $("legend");
const legendRows = new Map();

function buildLegend() {
  const group = (name, list, totalKey) => {
    const box = document.createElement("div");
    box.className = "legend-group";
    const head = document.createElement("p");
    head.className = "legend-head";
    const title = document.createElement("span");
    title.textContent = name;
    const total = document.createElement("span");
    total.className = "legend-total";
    head.append(title, total);
    box.appendChild(head);
    legendRows.set(totalKey, total);
    for (const account of list) {
      const row = document.createElement("p");
      row.className = "legend-row";
      const swatch = document.createElement("span");
      swatch.className = "legend-swatch";
      swatch.style.setProperty("--swatch", account.color);
      const label = document.createElement("span");
      label.className = "legend-label";
      label.textContent = account.label;
      const value = document.createElement("span");
      value.className = "legend-value";
      row.append(swatch, label, value);
      box.appendChild(row);
      legendRows.set(account.id, { row, value });
    }
    legend.appendChild(box);
  };
  if (model.assets.length) group("Assets", model.assets, "assets");
  if (model.debts.length) group("Debts", model.debts, "debts");
}
buildLegend();

const donut = createDonut({ svg: $("donut-svg"), model, reduced });

let rollMs = 320;
let rollEase = "var(--ease-out)";
let donutMs = 420;

function showMonth(i) {
  const point = points[i];
  if (!point) return;
  const before = points[i - 1];
  const headline = $("headline-net");
  headline.dataset.net = String(point.net);
  headline.dataset.month = point.month;
  $("headline-month").textContent = i === n - 1 ? `${fmt.monthLong(point.idx)}, latest` : fmt.monthLong(point.idx);
  $("headline-net-text").textContent = `Net worth ${fmt.money(point.net)}`;
  roll.set(fmt.money(point.net), reduced() ? 0 : rollMs, rollEase);
  const delta = $("headline-delta");
  delta.classList.remove("is-up", "is-down");
  if (before) {
    const change = point.net - before.net;
    delta.textContent = change === 0 ? `No change since ${fmt.monthOnly(before.idx)}` : `${fmt.signed(change)} since ${fmt.monthOnly(before.idx)}`;
    if (change !== 0) delta.classList.add(change > 0 ? "is-up" : "is-down");
  } else {
    delta.textContent = "The first month on record";
  }
  $("total-assets").textContent = fmt.money(point.assets);
  $("total-debts").textContent = fmt.money(point.debts);
  for (const account of model.accounts) {
    const entry = legendRows.get(account.id);
    entry.value.textContent = fmt.money(point.balances[account.id]);
    entry.row.classList.toggle("is-zero", point.balances[account.id] === 0);
  }
  if (legendRows.has("assets")) legendRows.get("assets").textContent = fmt.money(point.assets);
  if (legendRows.has("debts")) legendRows.get("debts").textContent = fmt.money(point.debts);
  $("donut-value").textContent = point.assets > 0 ? fmt.percent(point.debts / point.assets) : "None";
  donut.show(point, donutMs);
  scrubber.setText(fmt.monthLong(point.idx));
}

// Chart and scrubber.
const plot = $("chart-plot");
const chart = createChart({ svg: $("chart-svg"), plot, model, fmt });
let opening = 0;
let openingNow = false;
let touched = false;
let hint = 0;

function finishOpening() {
  cancelAnimationFrame(opening);
  openingNow = false;
  chart.setReveal(1);
}

function grab() {
  touched = true;
  clearTimeout(hint);
  if (openingNow) scrubber.resync();
  finishOpening();
}

const scrubber = createScrubber({
  root: $("scrubber"),
  track: $("scrubber-track"),
  ticksBox: $("scrubber-ticks"),
  fill: $("scrubber-fill"),
  thumb: $("scrubber-thumb"),
  plot,
  chart,
  count: n,
  reduced,
  onMove: (pos) => chart.setCursor(pos),
  onSelect: (i) => {
    if (!openingNow) showMonth(i);
  },
  onGrab: grab,
});

renderTable({ table: $("ledger-table"), model, fmt });

function layout() {
  chart.render();
  scrubber.layout();
}

/** Once, a few seconds in and only if nothing was touched: the thumb glides back a stretch and returns, showing it moves. */
function scheduleHint() {
  if (n < 4) return;
  hint = setTimeout(() => {
    if (touched || reduced() || document.hidden) return;
    const back = Math.max(0, Math.round((n - 1) * 0.45));
    scrubber.glide(back, 1100);
    hint = setTimeout(() => {
      if (!touched) scrubber.glide(n - 1, 1100);
    }, 1900);
  }, 3300);
}

if (n > 0) {
  layout();
  new ResizeObserver(() => layout()).observe(plot);
  if (reduced() || n < 2) {
    showMonth(n - 1);
    finishOpening();
  } else {
    // The opening, 1.4 s: the chart sweeps in from the left with the cursor on its edge, while the headline
    // counts up to the latest month and the donut grows into it.
    const duration = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--motion-reveal")) || 1400;
    rollMs = duration;
    rollEase = "var(--ease-in-out)";
    donutMs = duration;
    showMonth(n - 1);
    rollMs = 320;
    rollEase = "var(--ease-out)";
    donutMs = 420;
    openingNow = true;
    chart.setReveal(0);
    scrubber.follow(0);
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const p = easeInOut(t);
      chart.setReveal(p);
      scrubber.follow(chart.posAtShare(p));
      if (t < 1) opening = requestAnimationFrame(step);
      else finishOpening();
    };
    opening = requestAnimationFrame(step);
    scheduleHint();
  }
}

// Views: Chart and Table, kept in the address's hash so a reload stays put.
const tabs = [$("tab-chart"), $("tab-table")];
function showView(name) {
  const table = name === "table";
  $("view-chart").hidden = table;
  $("view-table").hidden = !table;
  tabs.forEach((tab) => {
    const on = (tab.id === "tab-table") === table;
    tab.setAttribute("aria-selected", String(on));
    tab.tabIndex = on ? 0 : -1;
  });
  if (!table) layout();
}
tabs.forEach((tab, k) => {
  tab.addEventListener("click", () => {
    const name = k === 1 ? "table" : "chart";
    history.replaceState(null, "", name === "table" ? "#table" : "#chart");
    showView(name);
  });
  tab.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    const other = tabs[1 - k];
    other.focus();
    other.click();
  });
});
window.addEventListener("hashchange", () => showView(location.hash === "#table" ? "table" : "chart"));
if (location.hash === "#table") showView("table");
