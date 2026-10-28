// Shared helpers: the data, dates, number words, DOM and SVG builders, easing, and the Catmull-Rom curve.
export const DATA = window.__REPO_PULSE__;
export const CONFIG = window.__APP_CONFIG__ || {};

const DAY_MS = 86400000;
const [sy, sm, sd] = DATA.start.split("-").map(Number);
export const START_MS = Date.UTC(sy, sm - 1, sd);

export const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
export const phoneQuery = window.matchMedia("(max-width: 699px)");
export const fineHover = window.matchMedia("(hover: hover) and (pointer: fine)");
// The day card docks: under the map on a phone or a touch screen, in a column beside it on a wide screen.
export const dockQuery = window.matchMedia("(max-width: 699px), (hover: none), (min-width: 1100px)");
export const sideQuery = window.matchMedia("(min-width: 1100px)");
export const docked = () => dockQuery.matches;

export const isPhone = () => phoneQuery.matches;
export const calm = () => reducedMotion.matches;

export function dayDate(i) {
  return new Date(START_MS + i * DAY_MS);
}

/** Monday is 0. */
export function weekday(date) {
  return (date.getUTCDay() + 6) % 7;
}

const numberFormat = new Intl.NumberFormat("en-US");
export const fmt = (n) => numberFormat.format(n);

export function compact(n) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M`;
  if (n >= 1e4) return `${(n / 1e3).toFixed(n >= 1e5 ? 0 : 1)}k`;
  return fmt(n);
}

const dateFormats = {};
export function fmtDate(date, options) {
  const key = JSON.stringify(options);
  dateFormats[key] ||= new Intl.DateTimeFormat("en-US", { timeZone: "UTC", ...options });
  return dateFormats[key].format(date);
}

export const longDay = (i) => fmtDate(dayDate(i), { weekday: "short", month: "short", day: "numeric", year: "numeric" });
export const shortDay = (i) => fmtDate(dayDate(i), { month: "short", day: "numeric" });

export function monthDate(key) {
  const [y, m] = key.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1));
}

export const monthShort = (key) => fmtDate(monthDate(key), { month: "short" });
export const monthLong = (key) => fmtDate(monthDate(key), { month: "long", year: "numeric" });

export function plural(n, one, many = `${one}s`) {
  return `${fmt(n)} ${n === 1 ? one : many}`;
}

export function shortName(name) {
  if (name.includes("[bot]")) return name;
  const parts = name.trim().split(/\s+/);
  const last = parts[parts.length - 1];
  if (parts.length < 2 || last.length <= 2) return name;
  return `${parts[0]} ${last[0]}.`;
}

export function initials(name) {
  const parts = name.replace(/\[bot\]/, "").trim().split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

/** The color an author is drawn in: the top eight have their own, everyone else shares the neutral band. */
export function authorColor(index) {
  return index < 8 ? `var(--cat-${index + 1})` : "var(--cat-rest)";
}

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";
export function svg(tag, attrs = {}, className) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (className) node.setAttribute("class", className);
  return node;
}

export const setVars = (node, vars) => {
  for (const [key, value] of Object.entries(vars)) node.style.setProperty(key, value);
};

export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const round = (v) => Math.round(v * 100) / 100;

export const ease = {
  out: (t) => 1 - Math.pow(1 - t, 4),
  inOut: (t) => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2),
};

/** One rAF tween; resolves when done. Reduced motion jumps to the end. */
export function tween({ duration, delay = 0, easing = ease.out, update }) {
  return new Promise((resolve) => {
    if (calm()) {
      update(1);
      resolve();
      return;
    }
    let start = null;
    const step = (now) => {
      if (start === null) start = now + delay;
      const t = clamp((now - start) / duration, 0, 1);
      if (now >= start) update(easing(t));
      if (t < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  });
}

/** Points [[x, y], …] as a smooth path through every point: Catmull-Rom turned into cubic Béziers. */
export function catmullRom(points, move = true) {
  if (points.length === 0) return "";
  let d = move ? `M${round(points[0][0])},${round(points[0][1])}` : `L${round(points[0][0])},${round(points[0][1])}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    // Control points stay within the segment's own height, so a curve never swings past the values it joins.
    const lo = Math.min(p1[1], p2[1]);
    const hi = Math.max(p1[1], p2[1]);
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = clamp(p1[1] + (p2[1] - p0[1]) / 6, lo, hi);
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = clamp(p2[1] - (p3[1] - p1[1]) / 6, lo, hi);
    d += `C${round(c1x)},${round(c1y)} ${round(c2x)},${round(c2y)} ${round(p2[0])},${round(p2[1])}`;
  }
  return d;
}

/** A width for mono text at a size, without measuring: JetBrains Mono advances 0.6em per glyph. */
export const monoWidth = (text, size) => text.length * size * 0.6;

/** Calls fn after the element's size settles, and on every later change. */
export function onResize(node, fn) {
  let frame = 0;
  let last = "";
  const observer = new ResizeObserver((entries) => {
    const box = entries[0].contentRect;
    const key = `${Math.round(box.width)}x${Math.round(box.height)}`;
    if (key === last) return;
    last = key;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => fn(box.width, box.height));
  });
  observer.observe(node);
  return observer;
}

/** The shared tooltip that follows the pointer over the river, the treemap, and the bars. */
const tip = document.getElementById("tip");
export function showTip(html, clientX, clientY) {
  tip.innerHTML = html;
  tip.classList.add("is-on");
  const w = tip.offsetWidth;
  const h = tip.offsetHeight;
  let x = clientX + 14;
  let y = clientY - h - 12;
  if (x + w > window.innerWidth - 8) x = clientX - w - 14;
  if (y < 8) y = clientY + 18;
  tip.style.setProperty("--tx", `${Math.round(clamp(x, 8, window.innerWidth - w - 8))}px`);
  tip.style.setProperty("--ty", `${Math.round(y)}px`);
}
export function hideTip() {
  tip.classList.remove("is-on");
}

export function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

/** Runs fn once, the first time a quarter of the element is on screen. */
export function whenSeen(node, fn) {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        observer.disconnect();
        fn();
      }
    },
    { threshold: 0.25 },
  );
  observer.observe(node);
}
