// Run Atlas: the wall, the summary above it, the filters, and which screen is showing.
import * as f from "./format.js";
import { createDetail } from "./detail.js";
import { renderMonths } from "./months.js";

const DATA = window.__RUN_ATLAS__ ?? { sample: false, units: "km", years: [], sports: [], months: {}, activities: [] };
const CONFIG = window.__APP_CONFIG__ ?? {};
const UNITS = CONFIG.units === "mi" || CONFIG.units === "km" ? CONFIG.units : DATA.units;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const wide = matchMedia("(min-width: 1100px)");

const $ = (id) => document.getElementById(id);
const app = $("app");
const wall = $("wall");
const byId = new Map(DATA.activities.map((a) => [a.id, a]));
const latest = DATA.activities.find((a) => a.date)?.date ?? null;

const state = {
  year: DATA.years.includes(CONFIG.year) ? CONFIG.year : DATA.years[0] ?? "all",
  sport: "all",
  screen: "wall",
  selected: null,
};

let shown = [];
let booted = false;

// ---------- filters ----------

function chip(label, pressed, onPress) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.textContent = label;
  b.setAttribute("aria-pressed", String(pressed));
  b.addEventListener("click", onPress);
  return b;
}

const SPORT_LABEL = { all: "All sports", run: "Runs", ride: "Rides", walk: "Walks", hike: "Hikes" };

function renderFilters() {
  const years = $("years");
  years.replaceChildren(
    ...DATA.years.map((y) => chip(String(y), state.year === y, () => setFilter({ year: y }))),
    chip("All years", state.year === "all", () => setFilter({ year: "all" })),
  );
  const sports = $("sports");
  const list = DATA.sports.length > 1 ? ["all", ...DATA.sports] : [];
  sports.replaceChildren(...list.map((s) => chip(SPORT_LABEL[s], state.sport === s, () => setFilter({ sport: s }))));
  sports.hidden = list.length === 0;
}

function setFilter(change) {
  Object.assign(state, change);
  renderFilters();
  render();
}

const inSport = (a) => state.sport === "all" || a.sport === state.sport;
const inYear = (a) => state.year === "all" || (a.date && a.date.startsWith(String(state.year)));

// ---------- the summary: twelve bars, the rolling total, the bests ----------

function windowEnd() {
  if (!latest) return null;
  const [ly, lm] = latest.split("-").map(Number);
  if (state.year === "all" || state.year >= ly) return { y: ly, m: lm };
  return { y: state.year, m: 12 };
}

function monthTotal(key) {
  const slot = DATA.months[key];
  if (!slot) return 0;
  return Object.entries(slot).reduce((sum, [sport, m]) => sum + (state.sport === "all" || sport === state.sport ? m : 0), 0);
}

// The bars rise one at a time and the total counts up with them: on load they wait for the wall to start drawing.
const RISE_FIRST = { delay: 600, step: 90, ms: 420 };
const RISE_AGAIN = { delay: 120, step: 55, ms: 640 };

let countFrame = 0;
function countUp(el, parts, digits, rise) {
  cancelAnimationFrame(countFrame);
  const to = parts.reduce((s, x) => s + x, 0);
  const format = (v, d) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  if (reduced.matches) {
    el.textContent = format(to, digits);
    return;
  }
  const start = performance.now();
  const end = rise.delay + (parts.length - 1) * rise.step + rise.ms;
  const step = (now) => {
    const t = now - start;
    let value = 0;
    parts.forEach((part, i) => {
      const p = Math.min(1, Math.max(0, (t - rise.delay - i * rise.step) / rise.ms));
      value += part * (1 - Math.pow(1 - p, 4));
    });
    el.textContent = t < end ? format(value, 0) : format(to, digits);
    if (t < end) countFrame = requestAnimationFrame(step);
  };
  el.textContent = "0";
  countFrame = requestAnimationFrame(step);
}

function renderSummary() {
  const end = windowEnd();
  const bars = $("bars");
  const months = [];
  if (end) {
    for (let k = 11; k >= 0; k -= 1) {
      const d = new Date(Date.UTC(end.y, end.m - 1 - k, 1));
      const key = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
      months.push({ key, m: d.getUTCMonth(), y: d.getUTCFullYear(), meters: monthTotal(key) });
    }
  }
  const max = Math.max(1, ...months.map((x) => x.meters));
  const rise = booted ? RISE_AGAIN : RISE_FIRST;
  bars.style.setProperty("--bar-delay", `${rise.delay}ms`);
  bars.style.setProperty("--bar-step", `${rise.step}ms`);
  bars.style.setProperty("--bar-ms", `${rise.ms}ms`);
  bars.replaceChildren(
    ...months.map((x, i) => {
      const bar = document.createElement("div");
      bar.className = "bar";
      if (!x.meters) bar.classList.add("is-empty");
      if (i === months.length - 1) bar.classList.add("is-last");
      bar.style.setProperty("--h", (x.meters / max).toFixed(4));
      bar.style.setProperty("--i", String(i));
      bar.title = `${f.monthLong(x.m)} ${x.y}: ${f.distance(x.meters, UNITS)} ${UNITS}`;
      const fill = document.createElement("div");
      fill.className = "bar-fill";
      const label = document.createElement("div");
      label.className = "bar-label";
      label.textContent = f.monthLetter(x.m);
      bar.append(fill, label);
      return bar;
    }),
  );
  const total = months.reduce((s, x) => s + x.meters, 0);
  const value = total / f.UNIT_M[UNITS];
  countUp($("total-number"), months.map((x) => x.meters / f.UNIT_M[UNITS]), value < 100 ? 1 : 0, rise);
  $("total-unit").textContent = UNITS;
  const sportWords = state.sport === "all" ? "" : ` of ${SPORT_LABEL[state.sport].toLowerCase()}`;
  if (!end) $("total-label").textContent = "";
  else if (end.m === 12 && state.year !== "all" && end.y === state.year && latest && Number(latest.slice(0, 4)) > end.y) {
    $("total-label").textContent = `${end.y}${sportWords}, month by month`;
  } else {
    const first = months[0];
    $("total-label").textContent = `${f.monthShort(first.m)} ${first.y} to ${f.monthShort(end.m - 1)} ${end.y}${sportWords}, the last twelve months`;
  }
  bars.setAttribute("aria-label", `Distance by month, ${f.distance(total, UNITS)} ${UNITS} in all`);
  renderBests();
}

function renderBests() {
  const pool = DATA.activities.filter(inSport);
  const effortSport = state.sport === "all" ? "run" : state.sport;
  const efforts = pool.filter((a) => a.best && a.sport === effortSport);
  const fastest = efforts.reduce((b, a) => (!b || a.best < b.best ? a : b), null);
  const longest = pool.reduce((b, a) => (!b || a.distance > b.distance ? a : b), null);
  const climb = pool.reduce((b, a) => (!b || a.gain > b.gain ? a : b), null);
  const effortKm = effortSport === "ride" ? 20 : 5;
  const items = [
    { label: `Fastest ${effortKm} km`, a: fastest, value: fastest ? f.clock(fastest.best) : "" },
    { label: "Longest", a: longest, value: longest ? `${f.distance(longest.distance, UNITS)} ${UNITS}` : "" },
    { label: "Most climb", a: climb, value: climb ? (({ value, unit }) => `${value} ${unit}`)(f.climb(climb.gain, UNITS)) : "" },
  ];
  $("bests").replaceChildren(
    ...items.map((item) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.className = "best";
      b.disabled = !item.a;
      const label = document.createElement("span");
      label.className = "best-label";
      label.textContent = item.label;
      const value = document.createElement("span");
      value.className = "best-value";
      value.textContent = item.value || "None yet";
      const date = document.createElement("span");
      date.className = "best-date";
      date.textContent = item.a ? f.shortDate(item.a.date) : "";
      if (item.a) {
        const name = document.createElement("span");
        name.className = "best-name";
        name.textContent = `, ${item.a.name}`;
        date.append(name);
      }
      b.append(label, value, date);
      if (item.a) {
        b.setAttribute("aria-label", `${item.label}: ${item.value}, ${item.a.name}, ${f.shortDate(item.a.date)}`);
        b.addEventListener("click", () => openFromWall(item.a.id));
      }
      li.append(b);
      return li;
    }),
  );
}

// ---------- the wall ----------

const SVG_NS = "http://www.w3.org/2000/svg";

function lengthTint(meters, max) {
  const lo = 1500;
  if (meters <= lo || max <= lo) return 0;
  return Math.min(1, Math.log(meters / lo) / Math.log(max / lo));
}

function tileFor(a, i, max) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "tile";
  b.dataset.id = a.id;
  b.tabIndex = -1;
  b.style.setProperty("--len", lengthTint(a.distance, max).toFixed(3));
  b.style.setProperty("--i", String(i));
  b.setAttribute("aria-label", `${a.name}, ${f.shortDate(a.date)}, ${f.distance(a.distance, UNITS)} ${UNITS}`);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "-70 -70 1140 1140");
  svg.setAttribute("aria-hidden", "true");
  const line = document.createElementNS(SVG_NS, "polyline");
  line.setAttribute("points", a.points.map((p) => `${p[0]},${p[1]}`).join(" "));
  line.setAttribute("pathLength", "1");
  svg.append(line);
  const km = document.createElement("span");
  km.className = "tile-km";
  km.textContent = `${f.distance(a.distance, UNITS)}`;
  const date = document.createElement("span");
  date.className = "tile-date";
  date.textContent = f.tileDate(a.date);
  b.append(svg, km, date);
  return b;
}

function renderWall() {
  shown = DATA.activities.filter((a) => inSport(a) && inYear(a));
  const max = Math.max(1, ...DATA.activities.filter(inSport).map((a) => a.distance));
  const frag = document.createDocumentFragment();
  shown.forEach((a, i) => frag.append(tileFor(a, i, max)));
  wall.replaceChildren(frag);
  const first = wall.firstElementChild;
  if (first) first.tabIndex = 0;
  markSelected();
  sizeStrokes();

  const what = state.sport === "all" ? (shown.length === 1 ? "activity" : "activities") : f.sportWord(state.sport, shown.length);
  const when = state.year === "all" ? "in every year" : `in ${state.year}`;
  $("wall-title").textContent = `${f.count(shown.length)} ${what} ${when}`;
  const empty = $("empty");
  empty.hidden = shown.length > 0;
  if (!shown.length) {
    $("empty-text").textContent = `No ${state.sport === "all" ? "activities" : SPORT_LABEL[state.sport].toLowerCase()} ${when}.`;
    $("empty-reset").hidden = state.sport === "all";
  }
}

function markSelected() {
  for (const t of wall.children) {
    if (t.dataset.id === state.selected) t.setAttribute("aria-current", "true");
    else t.removeAttribute("aria-current");
  }
}

// Every route is drawn 1.5 px wide whatever the tile's size: the stroke is set in the tile's own units.
function sizeStrokes() {
  const t = wall.firstElementChild;
  if (!t) return;
  const w = t.getBoundingClientRect().width;
  if (w > 0) wall.style.setProperty("--sw", `${((1.5 * VIEW) / w).toFixed(2)}px`);
  if (w > 0) clearLabels(w);
}

// The routes sit in a 0 to 1000 square with a 70 margin. A route that runs under its distance label is drawn
// smaller, held to the tile's top right corner, until the line and its stroke clear the label.
const VIEW = 1140;

function segmentHits(x1, y1, x2, y2, r) {
  let lo = 0;
  let hi = 1;
  const dx = x2 - x1;
  const dy = y2 - y1;
  for (const [p, q] of [[-dx, x1 - r.x0], [dx, r.x1 - x1], [-dy, y1 - r.y0], [dy, r.y1 - y1]]) {
    if (p === 0) {
      if (q < 0) return false;
    } else {
      const k = q / p;
      if (p < 0) lo = Math.max(lo, k);
      else hi = Math.min(hi, k);
      if (lo > hi) return false;
    }
  }
  return true;
}

function routeHits(points, r) {
  if (points.length === 1) return segmentHits(points[0][0], points[0][1], points[0][0], points[0][1], r);
  for (let i = 1; i < points.length; i += 1) {
    if (segmentHits(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1], r)) return true;
  }
  return false;
}

function clearLabels(w) {
  for (const tile of wall.children) {
    const a = byId.get(tile.dataset.id);
    const km = tile.querySelector(".tile-km");
    const svg = tile.querySelector("svg");
    if (!a || !km || !svg || !a.points.length) continue;
    const pad = 3 + 0.75;
    const box = { x0: km.offsetLeft - pad, x1: km.offsetLeft + km.offsetWidth + pad, y0: km.offsetTop - pad, y1: km.offsetTop + km.offsetHeight + pad };
    let size = VIEW;
    for (; size < VIEW * 2; size += 30) {
      const x = VIEW - 70 - size;
      const k = size / w;
      if (!routeHits(a.points, { x0: x + box.x0 * k, x1: x + box.x1 * k, y0: -70 + box.y0 * k, y1: -70 + box.y1 * k })) break;
    }
    svg.setAttribute("viewBox", `${VIEW - 70 - size} -70 ${size} ${size}`);
    if (size === VIEW) tile.style.removeProperty("--sw");
    else tile.style.setProperty("--sw", `${((1.5 * size) / w).toFixed(2)}px`);
  }
}

new ResizeObserver(sizeStrokes).observe(wall);
document.fonts?.ready.then(sizeStrokes);

function columns() {
  return getComputedStyle(wall).gridTemplateColumns.split(" ").filter(Boolean).length || 1;
}

wall.addEventListener("keydown", (event) => {
  const tiles = [...wall.children];
  const at = tiles.indexOf(document.activeElement);
  if (at < 0) return;
  const cols = columns();
  const moves = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols };
  let to = null;
  if (event.key in moves) to = at + moves[event.key];
  else if (event.key === "Home") to = 0;
  else if (event.key === "End") to = tiles.length - 1;
  if (to === null) return;
  event.preventDefault();
  event.stopPropagation();
  to = Math.max(0, Math.min(tiles.length - 1, to));
  tiles[at].tabIndex = -1;
  tiles[to].tabIndex = 0;
  tiles[to].focus();
});

wall.addEventListener("click", (event) => {
  const tile = event.target.closest(".tile");
  if (tile) openFromWall(tile.dataset.id, tile);
});

wall.addEventListener("pointerover", (event) => {
  const tile = event.target.closest(".tile");
  if (tile) detail.prefetch(byId.get(tile.dataset.id));
});

wall.addEventListener("focusin", (event) => {
  const tile = event.target.closest(".tile");
  if (!tile) return;
  for (const t of wall.children) t.tabIndex = t === tile ? 0 : -1;
  detail.prefetch(byId.get(tile.dataset.id));
});

$("empty-reset").addEventListener("click", () => setFilter({ sport: "all" }));

// ---------- the activity ----------

const detail = createDetail({
  units: UNITS,
  reduced,
  wide,
  onClose: () => closeSheet(),
  onStep: (dir) => step(dir),
});

function tileOf(id) {
  return wall.querySelector(`.tile[data-id="${CSS.escape(id)}"]`);
}

function openFromWall(id, tile = tileOf(id)) {
  if (!wide.matches) {
    if (location.hash !== `#/a/${id}`) {
      pendingTile = tile;
      location.hash = `#/a/${id}`;
      return;
    }
  }
  select(id, tile);
}

let pendingTile = null;

function select(id, tile = null, { replace = true } = {}) {
  const a = byId.get(id);
  if (!a) return;
  state.selected = id;
  markSelected();
  const index = shown.findIndex((x) => x.id === id);
  detail.show(a, {
    from: tile && tile.isConnected ? tile.querySelector("svg") : null,
    newer: index > 0,
    older: index >= 0 && index < shown.length - 1,
  });
  if (wide.matches && replace && location.hash !== `#/a/${id}`) history.replaceState(null, "", `#/a/${id}`);
}

function step(dir) {
  const index = shown.findIndex((x) => x.id === state.selected);
  if (index < 0) return;
  const next = shown[index + dir];
  if (!next) return;
  if (wide.matches) {
    select(next.id);
    tileOf(next.id)?.scrollIntoView({ block: "nearest", behavior: reduced.matches ? "auto" : "smooth" });
  } else {
    history.replaceState(null, "", `#/a/${next.id}`);
    select(next.id);
  }
}

function closeSheet() {
  if (wide.matches) return;
  const id = state.selected;
  if (history.state?.pushedSheet) history.back();
  else history.replaceState(null, "", "#/");
  detail.hide(tileOf(id)?.querySelector("svg") ?? null);
  tileOf(id)?.focus({ preventScroll: true });
}

// ---------- screens ----------

function route() {
  const hash = location.hash.replace(/^#\/?/, "");
  if (hash === "months") {
    showScreen("months");
    return;
  }
  showScreen("wall");
  const m = /^a\/(.+)$/.exec(hash);
  if (m && byId.has(decodeURIComponent(m[1]))) {
    const id = decodeURIComponent(m[1]);
    const a = byId.get(id);
    if (!shown.some((x) => x.id === id)) {
      state.year = a.date ? Number(a.date.slice(0, 4)) : "all";
      state.sport = "all";
      renderFilters();
      render();
    }
    if (!wide.matches) history.replaceState({ pushedSheet: Boolean(pendingTile) }, "", location.hash);
    select(id, pendingTile ?? tileOf(id), { replace: false });
    pendingTile = null;
  } else if (!wide.matches && detail.isOpen()) {
    detail.hide(tileOf(state.selected)?.querySelector("svg") ?? null);
  }
}

function showScreen(screen) {
  state.screen = screen;
  app.dataset.screen = screen;
  $("wall-screen").hidden = screen !== "wall";
  $("months-screen").hidden = screen !== "months";
  $("to-wall").toggleAttribute("aria-current", screen === "wall");
  $("to-months").toggleAttribute("aria-current", screen === "months");
  if (screen === "wall") $("to-wall").setAttribute("aria-current", "page");
  if (screen === "months") {
    $("to-months").setAttribute("aria-current", "page");
    renderMonths($("months-screen"), DATA, { units: UNITS, sport: state.sport, latest, sportLabel: SPORT_LABEL });
    if (!wide.matches && detail.isOpen()) detail.hide(null);
  }
}

function render() {
  renderSummary();
  renderWall();
  if (state.screen === "months") {
    renderMonths($("months-screen"), DATA, { units: UNITS, sport: state.sport, latest, sportLabel: SPORT_LABEL });
  }
  if (booted && wide.matches && shown.length && !shown.some((a) => a.id === state.selected)) {
    select(shown[0].id, tileOf(shown[0].id));
  } else markSelected();
}

document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented || event.altKey || event.metaKey || event.ctrlKey) return;
  const inWall = wall.contains(document.activeElement);
  if (event.key === "Escape" && !wide.matches && detail.isOpen()) {
    event.preventDefault();
    closeSheet();
    return;
  }
  if (inWall || state.screen !== "wall") return;
  if (!state.selected || (!wide.matches && !detail.isOpen())) return;
  if (event.key === "ArrowRight") {
    event.preventDefault();
    step(1);
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    step(-1);
  }
});

function measureTop() {
  app.style.setProperty("--top-h", `${Math.ceil(document.querySelector(".top").getBoundingClientRect().height)}px`);
}

new ResizeObserver(measureTop).observe(document.querySelector(".top"));
wide.addEventListener("change", () => {
  if (wide.matches) {
    detail.dock();
    if (state.selected) select(state.selected);
    else if (shown.length) select(shown[0].id);
  } else {
    detail.undock();
  }
});
window.addEventListener("hashchange", route);

// ---------- start ----------

$("status").textContent = DATA.sample ? "Sample year" : "";
renderFilters();
render();
measureTop();
const startHash = location.hash.replace(/^#\/?/, "");
if (startHash) route();
// On desktop the newest activity flies into the column beside the wall once the wall has drawn in.
if (wide.matches && !startHash && shown.length) {
  state.selected = null;
  detail.dock();
  setTimeout(() => {
    if (!state.selected) select(shown[0].id, tileOf(shown[0].id));
  }, reduced.matches ? 0 : 280);
} else if (wide.matches) {
  detail.dock();
}
booted = true;
