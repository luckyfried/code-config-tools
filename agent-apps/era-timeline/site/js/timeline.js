// The timeline drawing: era bands, the semantic axis, the pins in their lanes, and the count badges, all in one SVG
// sized one unit to one pixel. Time runs along x when horizontal and along y when vertical; everything below is
// written in (along, across) and swapped at the last step, so both orientations share one layout.

import { pxOf } from "./camera.js";
import { contextTicks, pickStep, ticks } from "./time.js";
import { clearBadges, countOverlaps, layoutLanes } from "./lanes.js";

const NS = "http://www.w3.org/2000/svg";
const PIN_FONT = '500 14px "Inter Variable", system-ui, sans-serif';
const PIN_FONT_BIG = '500 15.5px "Inter Variable", system-ui, sans-serif';
const PIN_FONT_SMALL = '500 13px "Inter Variable", system-ui, sans-serif';
const ERA_FONT = '600 13px "Fraunces Variable", Georgia, serif';
const ERA_FONT_SMALL = '600 11.5px "Fraunces Variable", Georgia, serif';
const CONTEXT_FONT = '650 13px "Inter Variable", system-ui, sans-serif';
const TICK_FONT_MAJOR = '700 12px "Inter Variable", system-ui, sans-serif';
const FADE_MS = 260;

const svgEl = (name, attrs = {}, parent = null) => {
  const el = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  if (parent) parent.appendChild(el);
  return el;
};
const set = (el, key, value) => {
  const text = typeof value === "number" ? String(Math.round(value * 10) / 10) : value;
  if (el.getAttribute(key) !== text) el.setAttribute(key, text);
};

const measure = (() => {
  const ctx = document.createElement("canvas").getContext("2d");
  const cache = new Map();
  const fn = (text, font) => {
    const key = `${font}|${text}`;
    let width = cache.get(key);
    if (width === undefined) {
      ctx.font = font;
      width = ctx.measureText(text).width;
      cache.set(key, width);
    }
    return width;
  };
  fn.clear = () => cache.clear();
  return fn;
})();
export { measure };

/** `text` cut with an ellipsis to fit `max` pixels in `font`. */
export function fitText(text, font, max) {
  if (measure(text, font) <= max) return text;
  let lo = 0;
  let hi = text.length;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (measure(`${text.slice(0, mid).trimEnd()}…`, font) <= max) lo = mid;
    else hi = mid - 1;
  }
  return lo === 0 ? "…" : `${text.slice(0, lo).trimEnd()}…`;
}

/** `text` broken at spaces into lines no wider than `max` pixels in `font`; a word wider than that is cut short. */
export function wrapText(text, font, max) {
  const lines = [];
  for (const word of text.split(/\s+/)) {
    const last = lines[lines.length - 1];
    if (last !== undefined && measure(`${last} ${word}`, font) <= max) lines[lines.length - 1] = `${last} ${word}`;
    else lines.push(word);
  }
  return lines.map((line) => fitText(line, font, max));
}

/** Assigns each era a layer: the first, in the order given, that it does not overlap. */
export function eraLayers(eras) {
  const layers = [];
  for (const era of eras) {
    let layer = layers.findIndex((taken) => taken.every((other) => era.t >= other.end || era.end <= other.t));
    if (layer < 0) {
      layer = layers.length;
      layers.push([]);
    }
    layers[layer].push(era);
    era.layer = layer;
  }
  return layers.length;
}

export class Timeline {
  constructor(svg, data, { onPin, onCluster, reduced }) {
    this.svg = svg;
    this.data = data;
    this.onPin = onPin;
    this.onCluster = onCluster;
    this.reduced = reduced;
    this.selected = null;
    this.matches = null;
    this.layerCount = eraLayers(data.eras);
    this.tickEls = new Map();
    this.contextEls = new Map();
    this.level = null;
    this.settled = true;
    this.lastFrame = 0;
    this.build();
  }

  build() {
    const svg = this.svg;
    svg.replaceChildren();
    this.gTint = svgEl("g", { class: "era-tints" }, svg);
    this.gEdges = svgEl("g", { class: "era-edges" }, svg);
    this.gAxis = svgEl("g", { class: "axis", "data-level": "" }, svg);
    this.axisLine = svgEl("line", { class: "axis-line" }, this.gAxis);
    this.gTicks = svgEl("g", { class: "ticks" }, this.gAxis);
    this.gStems = svgEl("g", { class: "stems" }, svg);
    this.gDots = svgEl("g", { class: "dots" }, svg);
    this.gFlags = svgEl("g", { class: "flags" }, svg);
    this.gClusters = svgEl("g", { class: "clusters" }, svg);
    this.gStrips = svgEl("g", { class: "era-strips" }, svg);
    // The context labels sit on top, so the chip that holds the year or month in force stays readable over the bands.
    this.gContext = svgEl("g", { class: "context" }, svg);

    for (const era of this.data.eras) {
      const hue = { "data-hue": era.hue };
      era.el = {
        tint: svgEl("rect", { class: "era-tint", ...hue }, this.gTint),
        edgeA: svgEl("line", { class: "era-edge", ...hue }, this.gEdges),
        edgeB: svgEl("line", { class: "era-edge", ...hue }, this.gEdges),
        strip: svgEl("rect", { class: "era-strip", rx: 6, ...hue }, this.gStrips),
        label: svgEl("text", { class: "era-label" }, this.gStrips),
      };
      if (era.custom) for (const el of Object.values(era.el)) el.style.setProperty("--hue", era.custom);
    }

    for (const [index, event] of this.data.events.entries()) {
      const stem = svgEl("line", { class: "stem" }, this.gStems);
      const dot = svgEl("circle", { class: "dot", r: 4.5, "data-hue": event.hue }, this.gDots);
      const flag = svgEl("g", { class: "flag", tabindex: "0", role: "button", "data-id": event.id, "aria-label": `${event.when}: ${event.label}` }, this.gFlags);
      const body = svgEl("g", { class: "flag-body" }, flag);
      body.style.setProperty("--i", String(index));
      const pill = svgEl("rect", { class: "pill", rx: 15 }, body);
      const hue = svgEl("circle", { class: "pill-hue", r: 4, "data-hue": event.hue }, body);
      const label = svgEl("text", { class: "pill-label" }, body);
      if (event.customHue) for (const el of [dot, hue]) el.style.setProperty("--hue", event.customHue);
      event.el = { stem, dot, flag, body, pill, hue, label };
      event.cross = null;
      event.text = null;
      flag.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this.onPin(event, "key");
        }
      });
    }
    this.clusterEls = [];
  }

  /** Lays out for a stage of `width` by `height` pixels, time running `orient` ("h" or "v"). */
  resize(width, height, orient, compact) {
    this.W = width;
    this.H = height;
    this.orient = orient;
    this.compact = compact;
    const g = {};
    if (orient === "h") {
      g.length = width;
      g.stripSize = compact ? 14 : 24;
      g.stripStart = compact ? 5 : 12;
      g.stripGap = compact ? 2 : 4;
      g.stripEnd = g.stripStart + this.layerCount * (g.stripSize + g.stripGap);
      g.axis = height - (compact ? 36 : 58);
      g.big = width >= 1700 && height >= 700;
      g.pillH = compact ? 22 : g.big ? 34 : 30;
      g.badge = compact ? 11 : 14;
      // Badges float just above the axis, clear of every dot on it, and the lowest flag clears the badges.
      g.lift = g.badge + (compact ? 7 : 9);
      g.rise = g.lift + g.badge + (compact ? 2 : 5);
      // Up to six lanes, spread over the whole height between the era bands and the badges, so the top lane sits
      // right under the bands at every stage size.
      const room = g.axis - g.rise - g.stripEnd - (compact ? 4 : 12);
      const tight = g.pillH + (compact ? 4 : 8);
      g.rows = Math.max(1, Math.min(6, Math.floor((room + tight - g.pillH) / tight)));
      g.pitch = Math.max(tight, Math.floor((room - g.pillH) / Math.max(1, g.rows - 1)));
    } else {
      g.length = height;
      g.stripSize = 16;
      g.stripStart = 6;
      g.stripGap = 3;
      g.stripEnd = g.stripStart + this.layerCount * (g.stripSize + g.stripGap);
      // The year labels sit between the era columns and the axis with room to spare for the widest of them.
      const years = [this.data.min, this.data.max].map((t) => new Date(t).getUTCFullYear());
      const widest = Math.max(...years.map((year) => measure(year > 0 ? `${year}s` : `${1 - year} BCE`, TICK_FONT_MAJOR)), measure("8888s", TICK_FONT_MAJOR));
      g.axis = g.stripEnd + 12 + Math.ceil(widest) + 18;
      g.pillH = 32;
      g.lineH = 18;
      g.badge = 14;
      // Badges float to the left of the axis, clear of every dot on it.
      g.lift = g.badge + 9;
      g.packFrom = g.axis + 14;
      g.packTo = width - 5;
    }
    this.g = g;
    this.eraFont = orient === "v" || compact ? ERA_FONT_SMALL : ERA_FONT;
    this.pinFont = g.big ? PIN_FONT_BIG : orient === "h" && compact ? PIN_FONT_SMALL : PIN_FONT;
    this.svg.classList.toggle("is-big", Boolean(g.big));
    this.svg.classList.toggle("is-compact", orient === "h" && compact);
    this.svg.classList.toggle("is-small-eras", this.eraFont === ERA_FONT_SMALL);
    set(this.svg, "viewBox", `0 0 ${width} ${height}`);
    this.svg.setAttribute("width", String(width));
    this.svg.setAttribute("height", String(height));
    for (const event of this.data.events) {
      event.cross = null;
      event.lines = null;
    }
    for (const item of this.clusterEls) item.el.querySelector("circle").setAttribute("r", String(g.badge));
  }

  /** The pixel box of (along, across) ranges, in x and y. */
  box(a0, a1, c0, c1) {
    return this.orient === "h" ? { x: a0, y: c0, w: a1 - a0, h: c1 - c0 } : { x: c0, y: a0, w: c1 - c0, h: a1 - a0 };
  }

  point(a, c) {
    return this.orient === "h" ? [a, c] : [c, a];
  }

  /** Draws the camera `cam`. Returns true while something is still moving. */
  render(cam) {
    const g = this.g;
    if (!g) return false;
    const L = g.length;
    const t0 = cam.t0;
    const t1 = cam.t0 + L * cam.k;
    let moving = false;
    this.renderEras(cam, t0, t1);
    moving = this.renderAxis(cam, t0, t1) || moving;
    moving = this.renderPins(cam) || moving;
    this.settled = !moving;
    return moving;
  }

  renderEras(cam) {
    const g = this.g;
    const L = g.length;
    const crossEnd = this.orient === "h" ? g.axis : this.W;
    for (const era of this.data.eras) {
      const a0 = pxOf(cam, era.t);
      const a1 = pxOf(cam, era.end);
      const visible = a1 > -50 && a0 < L + 50;
      const el = era.el;
      for (const node of Object.values(el)) node.classList.toggle("is-off", !visible);
      if (!visible) continue;
      const v0 = Math.max(-8, a0);
      const v1 = Math.min(L + 8, a1);
      const s0 = g.stripStart + era.layer * (g.stripSize + g.stripGap);
      const tint = this.box(v0, v1, s0, crossEnd);
      set(el.tint, "x", tint.x);
      set(el.tint, "y", tint.y);
      set(el.tint, "width", Math.max(0, tint.w));
      set(el.tint, "height", Math.max(0, tint.h));
      const clipped = this.box(Math.max(-12, a0 + 1), Math.min(L + 12, a1 - 1), s0, s0 + g.stripSize);
      set(el.strip, "x", clipped.x);
      set(el.strip, "y", clipped.y);
      set(el.strip, "width", Math.max(2, clipped.w));
      set(el.strip, "height", Math.max(2, clipped.h));
      const edgeFrom = s0 + g.stripSize;
      for (const [line, at] of [[el.edgeA, a0], [el.edgeB, a1]]) {
        const [x1, y1] = this.point(at, edgeFrom);
        const [x2, y2] = this.point(at, crossEnd);
        set(line, "x1", x1);
        set(line, "y1", y1);
        set(line, "x2", x2);
        set(line, "y2", y2);
      }
      // The label slides along to stay in view, held inside its band.
      const room = Math.max(0, a1 - a0 - 20);
      const font = this.eraFont;
      const text = fitText(era.label, font, room);
      if (el.label.textContent !== text) el.label.textContent = text;
      const width = measure(text, font);
      const along = Math.min(Math.max(a0 + 10, 10), a1 - 10 - width);
      el.label.classList.toggle("is-off", room < 28);
      const mid = s0 + g.stripSize / 2;
      const lift = this.eraFont === ERA_FONT ? 4.5 : 4;
      if (this.orient === "h") {
        set(el.label, "transform", `translate(${Math.round(along)} ${Math.round(mid + lift)})`);
      } else {
        set(el.label, "transform", `translate(${Math.round(mid - lift)} ${Math.round(along)}) rotate(90)`);
      }
    }
  }

  renderAxis(cam, t0, t1) {
    const g = this.g;
    const L = g.length;
    const [ax1, ay1] = this.point(-10, g.axis);
    const [ax2, ay2] = this.point(L + 10, g.axis);
    set(this.axisLine, "x1", ax1);
    set(this.axisLine, "y1", ay1);
    set(this.axisLine, "x2", ax2);
    set(this.axisLine, "y2", ay2);

    const minPx = this.orient === "h" ? (this.compact ? 64 : 76) : 46;
    const step = pickStep(cam.k, minPx);
    if (this.level !== step.level) {
      this.level = step.level;
      this.gAxis.setAttribute("data-level", step.level);
      this.svg.dispatchEvent(new CustomEvent("levelchange", { detail: step.level }));
    }
    const pad = 200 * cam.k;
    const wanted = ticks(t0 - pad, t1 + pad, step);
    const now = performance.now();
    const keep = new Set();
    for (const tick of wanted) {
      keep.add(tick.key);
      let el = this.tickEls.get(tick.key);
      if (!el) {
        // Time running down has no room for a context row, so a tick that opens a year or a month says so itself.
        const words = this.orient === "v" && tick.major ? tick.major : tick.words;
        el = this.makeTick(this.gTicks, words, "tick");
        el.g.classList.toggle("is-major", Boolean(tick.major));
        // The drawn width, with the label's own weight and figures.
        el.size = el.g.querySelector("text").getComputedTextLength();
        this.tickEls.set(tick.key, el);
      }
      el.leaving = 0;
      el.g.classList.remove("is-out");
      this.placeTick(el, pxOf(cam, tick.t));
    }
    this.retire(this.tickEls, keep, now, (el, key) => this.placeTick(el, pxOf(cam, Number(key.split(":")[1]))));

    // The context row: "1911" over months, "May 1911" over days; the label in force sticks to the start edge until
    // the next one pushes it on. Time running down keeps only the label in force, as a chip at the top.
    const context = contextTicks(t0, t1 + pad, step);
    const keepContext = new Set();
    const shown = this.orient === "h" ? context : context.filter((item, index) => !context[index + 1] || pxOf(cam, context[index + 1].t) > 34).slice(0, 1);
    for (const [index, item] of shown.entries()) {
      keepContext.add(item.key);
      let el = this.contextEls.get(item.key);
      if (!el) {
        el = this.makeTick(this.gContext, item.words, "context-label");
        this.contextEls.set(item.key, el);
      }
      el.leaving = 0;
      el.g.classList.remove("is-out");
      if (this.orient === "h") {
        const size = measure(item.words, CONTEXT_FONT);
        const next = shown[index + 1];
        let at = Math.max(pxOf(cam, item.t) + 6, 12);
        if (next) at = Math.min(at, pxOf(cam, next.t) - size - 14);
        set(el.g, "transform", `translate(${Math.round(at)} ${g.axis + 48})`);
        el.g.classList.toggle("is-cut", at < 0 || at + size > L);
      } else {
        set(el.g, "transform", `translate(${g.stripStart} 8)`);
      }
    }
    this.retire(this.contextEls, keepContext, now, () => {});
    return [...this.tickEls.values(), ...this.contextEls.values()].some((el) => el.leaving);
  }

  /** Puts a tick at `at` along the axis; its label shows only when it fits whole inside the stage. */
  placeTick(el, at) {
    const g = this.g;
    const L = g.length;
    const a = Math.round(at);
    let cut;
    if (this.orient === "h") {
      set(el.g, "transform", `translate(${a} ${g.axis})`);
      cut = a + 5 < 0 || a + 5 + el.size > L;
    } else {
      set(el.g, "transform", `translate(${g.axis} ${a})`);
      cut = a < 0 || a + 20 > L;
    }
    el.at = a;
    el.g.classList.toggle("is-cut", cut);
  }

  makeTick(parent, words, kind) {
    const g = svgEl("g", { class: `${kind} is-new` }, parent);
    if (kind === "tick") {
      if (this.orient === "h") {
        svgEl("line", { class: "tick-line", x1: 0, y1: 0, x2: 0, y2: 8 }, g);
        svgEl("text", { class: "tick-label", x: 5, y: 29 }, g).textContent = words;
      } else {
        svgEl("line", { class: "tick-line", x1: 0, y1: 0, x2: -7, y2: 0 }, g);
        svgEl("text", { class: "tick-label", x: -18, y: 15, "text-anchor": "end" }, g).textContent = words;
      }
    } else if (this.orient === "h") {
      svgEl("text", { class: "context-text", x: 0, y: 0 }, g).textContent = words;
    } else {
      const width = measure(words, CONTEXT_FONT) + 20;
      svgEl("rect", { class: "context-chip", x: 0, y: 0, width, height: 26, rx: 13 }, g);
      svgEl("text", { class: "context-text", x: 10, y: 17.5 }, g).textContent = words;
    }
    // Fade in from the next frame, so the transition has a start.
    requestAnimationFrame(() => g.classList.remove("is-new"));
    return { g, leaving: 0, size: 0 };
  }

  /** Fades out every label in `map` not in `keep`, still following the camera, and removes it once faded. */
  retire(map, keep, now, follow) {
    for (const [key, el] of map) {
      if (keep.has(key)) continue;
      if (!el.leaving) {
        el.leaving = now;
        el.g.classList.add("is-out");
      }
      if (this.reduced() || now - el.leaving > FADE_MS) {
        el.g.remove();
        map.delete(key);
      } else {
        follow(el, key);
      }
    }
  }

  renderPins(cam) {
    const g = this.g;
    const L = g.length;
    const events = this.data.events;
    const vertical = this.orient === "v";
    const items = [];
    for (const event of events) {
      const at = pxOf(cam, event.t);
      event.at = at;
      if (at < -400 || at > L + 400) continue;
      let size;
      let thick;
      if (vertical) {
        // Time running down: a title too long for the width breaks onto more lines, so every title shows whole.
        if (!event.lines) event.lines = wrapText(event.label, this.pinFont, g.packTo - g.packFrom - 37);
        size = 37 + Math.max(...event.lines.map((line) => measure(line, this.pinFont)));
        thick = g.pillH + (event.lines.length - 1) * g.lineH;
      } else {
        const full = 24 + measure(event.label, this.pinFont) + 13;
        size = Math.min(full, g.big ? 300 : 260);
      }
      items.push({ id: event.id, at, size, thick, first: this.selected === event.id });
    }
    const layout = vertical
      ? layoutLanes(items, { mode: "pack", thick: g.pillH, gap: 5, from: g.packFrom, to: g.packTo, minSize: Infinity, badge: 2 * g.badge + 16, slide: 12 })
      : layoutLanes(items, { mode: "rows", rows: g.rows, lead: 14, gap: 6, badge: 2 * g.badge + 16, edge: L - 10, start: 10, slide: true, short: true });
    // Badges float off the axis, so every dot stays in sight. Across, they keep clear of every shown pin's stem where
    // they can, and never take in a pin that has a lane; down, they sit left of the axis between the year labels.
    if (vertical) {
      layout.clusters = this.clearLabels(layout.clusters);
    } else {
      const dots = [...layout.placed.keys()].map((id) => ({ at: this.data.byId.get(id).at }));
      layout.clusters = clearBadges(layout.clusters, dots, { radius: g.badge, dot: 6.5, gap: 3, reach: g.badge * 2 });
    }
    const byId = this.data.byId;
    for (const event of events) {
      const el = event.el;
      const spot = layout.placed.get(event.id);
      const offscreen = event.at < -400 || event.at > L + 400;
      const [dx, dy] = this.point(event.at, g.axis);
      set(el.dot, "cx", dx);
      set(el.dot, "cy", dy);
      el.dot.classList.toggle("is-off", offscreen);
      const shown = Boolean(spot);
      el.flag.classList.toggle("is-hidden", !shown);
      el.stem.classList.toggle("is-hidden", !shown);
      el.flag.classList.toggle("is-selected", this.selected === event.id);
      el.dot.classList.toggle("is-selected", this.selected === event.id);
      el.flag.classList.toggle("is-dim", this.matches !== null && !this.matches.has(event.id));
      el.flag.classList.toggle("is-match", this.matches !== null && this.matches.has(event.id));
      el.flag.setAttribute("tabindex", shown ? "0" : "-1");
      if (!shown) {
        event.cross = null;
        continue;
      }
      // Every frame draws the lanes just laid out, so no flag passes over another on its way to a new lane.
      event.cross = vertical ? spot.lane : g.axis - g.rise - spot.lane * g.pitch - g.pillH;
      const width = spot.size;
      const lines = vertical ? event.lines : [fitText(event.label, this.pinFont, width - 36)];
      const text = lines.join("\n");
      if (event.text !== text) {
        el.label.replaceChildren(...lines.map((line, index) => {
          const span = svgEl("tspan", { x: 24, dy: index === 0 ? 0 : g.lineH });
          span.textContent = line;
          return span;
        }));
        event.text = text;
      }
      const h = g.pillH + (lines.length - 1) * (g.lineH ?? 0);
      set(el.pill, "width", width);
      set(el.pill, "height", h);
      set(el.pill, "rx", Math.min(h, g.pillH) / 2);
      set(el.hue, "cx", 13);
      set(el.hue, "cy", h / 2);
      set(el.label, "x", 24);
      set(el.label, "y", h / 2 + (g.big ? 5.5 : this.pinFont === PIN_FONT_SMALL ? 4.5 : 5) - ((lines.length - 1) * (g.lineH ?? 0)) / 2);
      let fx;
      let fy;
      let sx2;
      let sy2;
      if (!vertical) {
        fx = spot.from;
        fy = event.cross;
        sx2 = event.at;
        sy2 = event.cross + h;
      } else {
        fx = event.cross;
        fy = spot.from;
        sx2 = event.cross;
        sy2 = event.at;
      }
      set(el.flag, "transform", `translate(${Math.round(fx * 2) / 2} ${Math.round(fy * 2) / 2})`);
      event.box = { x: fx, y: fy, w: width, h };
      set(el.stem, "x1", dx);
      set(el.stem, "y1", dy);
      set(el.stem, "x2", sx2);
      set(el.stem, "y2", sy2);
    }

    // Count badges on the axis for the pins with no room; a tap zooms in until they have it.
    const clusters = layout.clusters;
    while (this.clusterEls.length < clusters.length) {
      const el = svgEl("g", { class: "cluster", tabindex: "0", role: "button" }, this.gClusters);
      svgEl("circle", { class: "cluster-ring", r: g.badge }, el);
      svgEl("text", { class: "cluster-count", y: 4.5 }, el);
      const index = this.clusterEls.length;
      const open = () => this.onCluster(this.clusterEls[index].ids);
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      });
      el.dataset.index = String(index);
      this.clusterEls.push({ el, ids: [] });
    }
    for (const [index, item] of this.clusterEls.entries()) {
      const c = clusters[index];
      item.el.classList.toggle("is-hidden", !c);
      if (!c) {
        item.ids = [];
        continue;
      }
      item.ids = c.ids;
      const [x, y] = this.point(c.at, g.axis - g.lift);
      set(item.el, "transform", `translate(${Math.round(x)} ${Math.round(y)})`);
      const count = `+${c.ids.length}`;
      const label = item.el.querySelector("text");
      if (label.textContent !== count) label.textContent = count;
      const names = c.ids.map((id) => byId.get(id).label);
      item.el.setAttribute("aria-label", `${c.ids.length} more ${c.ids.length === 1 ? "event" : "events"} here: ${names.join(", ")}. Zoom in to see them.`);
      item.box = { x: x - g.badge, y: y - g.badge, w: 2 * g.badge, h: 2 * g.badge };
    }
    this.layout = layout;
    return false;
  }

  /**
   * Time running down: slides each badge along the axis, no further than a badge's width, to the nearest spot where
   * it clears the year labels and the badge before it. A label no spot can clear is hidden while the badge holds it.
   */
  clearLabels(clusters) {
    const r = this.g.badge;
    const reach = 2 * r + 6;
    const ticks = [...this.tickEls.values()].filter((el) => !el.leaving && el.at !== undefined);
    const spans = ticks.map((el) => [el.at + 2, el.at + 19]);
    const out = [];
    for (const c of clusters) {
      const blocks = [...spans, ...out.map((b) => [b.at - r - 4, b.at + r + 4])];
      const clear = (p) => blocks.every(([a, b]) => p + r + 3 <= a || p - r - 3 >= b);
      const tries = [c.at, ...blocks.flatMap(([a, b]) => [a - r - 3, b + r + 3])].filter((p) => Math.abs(p - c.at) <= reach).sort((p, q) => Math.abs(p - c.at) - Math.abs(q - c.at));
      out.push({ at: tries.find(clear) ?? c.at, ids: c.ids });
    }
    for (const el of ticks) {
      const covered = out.some((b) => el.at + 2 < b.at + r + 3 && el.at + 19 > b.at - r - 3);
      el.g.classList.toggle("is-covered", covered);
    }
    return out;
  }

  /** The bounding-box pass: pairs of drawn flags and badges that overlap, read from the drawn elements. */
  overlaps() {
    const boxes = [];
    for (const event of this.data.events) {
      const flag = event.el.flag;
      if (flag.classList.contains("is-hidden")) continue;
      const box = event.el.pill.getBBox();
      const m = /translate\(([-\d.]+) ([-\d.]+)\)/.exec(flag.getAttribute("transform") || "");
      if (!m) continue;
      boxes.push({ x: box.x + Number(m[1]), y: box.y + Number(m[2]), w: box.width, h: box.height });
    }
    for (const item of this.clusterEls) {
      if (item.el.classList.contains("is-hidden")) continue;
      const box = item.el.getBBox();
      const m = /translate\(([-\d.]+) ([-\d.]+)\)/.exec(item.el.getAttribute("transform") || "");
      if (!m) continue;
      boxes.push({ x: box.x + Number(m[1]), y: box.y + Number(m[2]), w: box.width, h: box.height });
    }
    return countOverlaps(boxes);
  }

  /** Whether an event is drawn as a flag now (not gathered into a badge). */
  isShown(id) {
    return Boolean(this.layout && this.layout.placed.has(id));
  }
}
