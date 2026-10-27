// The printed strip: the whole timeline at one fixed scale, left to right, with the title block at its left. It is
// drawn once, shown by the Print view on screen, and is the only thing on the page in print.

import { contextTicks, dateWords, pickStep, ticks, YEAR, DAY } from "./time.js";
import { layoutLanes } from "./lanes.js";
import { fitText, measure } from "./timeline.js";

const NS = "http://www.w3.org/2000/svg";
const PIN_FONT = '500 13px "Inter Variable", system-ui, sans-serif';
const ERA_FONT = '600 13px "Fraunces Variable", Georgia, serif';
const TITLE_FONT = (size) => `650 ${size}px "Fraunces Variable", Georgia, serif`;
const SUB_FONT = '400 15px "Inter Variable", system-ui, sans-serif';

const add = (name, attrs, parent, text) => {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, typeof value === "number" ? String(Math.round(value * 10) / 10) : value);
  if (text !== undefined) node.textContent = text;
  parent.appendChild(node);
  return node;
};

/** Words broken into lines no wider than `max` in `font`. */
function wrap(text, font, max) {
  const lines = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && measure(next, font) > max) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** The fixed scale: about 9,000 pixels for the whole span, never more than 60 pixels a day, and short of 18,000 in all. */
export function stripScale(span) {
  const perMs = Math.min(9000 / span, 60 / DAY, 17000 / span);
  return 1 / perMs;
}

export function drawStrip(host, data, config) {
  const span = data.max - data.min;
  const k = stripScale(span);
  const titleW = 380;
  const pad = 48;
  const lead = titleW + pad;
  const lengthPx = span / k;
  const width = Math.ceil(lead + lengthPx + pad * 2);
  const rowsMax = 8;
  const pillH = 28;
  const laneGap = 7;
  const layers = Math.max(1, ...data.eras.map((era) => era.layer + 1));
  const stripTop = 40;
  const stripEnd = stripTop + layers * 28;
  const axis = stripEnd + 40 + rowsMax * (pillH + laneGap) + 40;
  const height = Math.ceil(axis + 76);
  const at = (t) => lead + pad + (t - data.min) / k;

  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${config.title}, the whole timeline`);

  // The title block, at the left.
  let y = 72;
  const titleSize = config.title.length > 28 ? 34 : 42;
  for (const line of wrap(config.title, TITLE_FONT(titleSize), titleW - 24)) {
    add("text", { class: "strip-title", x: 40, y, "font-size": titleSize }, svg, line);
    y += titleSize * 1.08;
  }
  if (config.subtitle) {
    y += 8;
    for (const line of wrap(config.subtitle, SUB_FONT, titleW - 40)) {
      add("text", { class: "strip-sub", x: 40, y }, svg, line);
      y += 21;
    }
  }
  y += 14;
  const first = data.events[0];
  const last = data.events[data.events.length - 1];
  if (first && last) {
    add("text", { class: "strip-range", x: 40, y }, svg, `${dateWords(first.t, "year")} to ${dateWords(last.t, "year")}, ${data.events.length} events`);
    y += 30;
  }
  for (const era of data.eras) {
    if (y > height - 30) break;
    const dot = add("circle", { class: "pill-hue", "data-hue": era.hue, cx: 46, cy: y - 4.5, r: 5 }, svg);
    if (era.custom) dot.style.setProperty("--hue", era.custom);
    add("text", { class: "strip-legend", x: 60, y }, svg, fitText(era.label, '400 13px "Inter Variable", system-ui, sans-serif', titleW - 80));
    y += 22;
  }
  add("line", { class: "strip-rule", x1: titleW + 8, x2: titleW + 8, y1: 32, y2: height - 32 }, svg);

  // Era bands.
  for (const era of data.eras) {
    const a0 = at(era.t);
    const a1 = Math.max(a0 + 2, at(era.end));
    const s0 = stripTop + era.layer * 28;
    const hue = { "data-hue": era.hue };
    const nodes = [
      add("rect", { class: "era-tint", ...hue, x: a0, y: s0, width: a1 - a0, height: axis - s0 }, svg),
      add("rect", { class: "era-strip", ...hue, rx: 6, x: a0 + 1, y: s0, width: Math.max(2, a1 - a0 - 2), height: 24 }, svg),
    ];
    if (era.custom) for (const node of nodes) node.style.setProperty("--hue", era.custom);
    const text = fitText(era.label, ERA_FONT, a1 - a0 - 16);
    if (a1 - a0 > 40) add("text", { class: "era-label", x: a0 + 9, y: s0 + 16.5 }, svg, text);
  }

  // The axis at the fixed scale.
  add("line", { class: "axis-line", x1: lead + pad - 10, x2: width - pad + 10, y1: axis, y2: axis }, svg);
  const step = pickStep(k, 64);
  for (const tick of ticks(data.min, data.max, step)) {
    const x = at(tick.t);
    if (x < lead + pad - 2) continue;
    add("line", { class: "tick-line", x1: x, x2: x, y1: axis, y2: axis + 7 }, svg);
    add("text", { class: "tick-label", x: x + 5, y: axis + 29 }, svg, tick.words);
  }
  for (const item of contextTicks(data.min, data.max, step)) {
    const x = Math.max(at(item.t), lead + pad);
    add("text", { class: "context-text", x: x + 6, y: axis + 48 }, svg, item.words);
  }

  // Pins in lanes at this scale; any that still have no room share a badge.
  const items = data.events.map((event) => ({ id: event.id, at: at(event.t), size: Math.min(250, 24 + measure(event.label, PIN_FONT) + 14) }));
  const layout = layoutLanes(items, { mode: "rows", rows: rowsMax, lead: 14, gap: 6, badge: 34, edge: width - 10, start: titleW + 16, slide: true, short: true });
  const stems = add("g", {}, svg);
  const flags = add("g", {}, svg);
  for (const event of data.events) {
    const x = at(event.t);
    const dot = add("circle", { class: "dot", "data-hue": event.hue, cx: x, cy: axis, r: 4.5 }, svg);
    if (event.customHue) dot.style.setProperty("--hue", event.customHue);
    const spot = layout.placed.get(event.id);
    if (!spot) continue;
    const top = axis - 42 - spot.lane * (pillH + laneGap) - pillH;
    add("line", { class: "stem", x1: x, x2: x, y1: axis, y2: top + pillH }, stems);
    const g = add("g", { class: "flag", transform: `translate(${Math.round(spot.from)} ${Math.round(top)})` }, flags);
    add("rect", { class: "pill", width: spot.size, height: pillH, rx: pillH / 2 }, g);
    const hue = add("circle", { class: "pill-hue", "data-hue": event.hue, cx: 13, cy: pillH / 2, r: 4 }, g);
    if (event.customHue) hue.style.setProperty("--hue", event.customHue);
    add("text", { class: "pill-label", x: 23, y: pillH / 2 + 4.5, "font-size": 13 }, g, fitText(event.label, PIN_FONT, spot.size - 36));
  }
  // A badge floats just above the axis, so every dot stays in sight under it.
  for (const c of layout.clusters) {
    const g = add("g", { class: "cluster", transform: `translate(${Math.round(c.at)} ${axis - 23})` }, svg);
    add("circle", { class: "cluster-ring", r: 14 }, g);
    add("text", { class: "cluster-count", y: 4.5 }, g, `+${c.ids.length}`);
  }

  host.replaceChildren(svg);

  // The paper is the strip's own size, so it prints as one long page.
  let sheet = document.getElementById("page-size");
  if (!sheet) {
    sheet = document.createElement("style");
    sheet.id = "page-size";
    document.head.appendChild(sheet);
  }
  sheet.textContent = `@media print { @page { size: ${width}px ${height}px; margin: 0; } }`;
  return { width, height, years: span / YEAR };
}
