// Era Timeline: reads the timeline from data.js and the settings from config.js, then runs the camera, the input,
// the card, the list, search, story, and print.

import { clampCamera, fit, flight, panBy, pinch, pxOf, timeAt, zoomAt } from "./camera.js";
import { DAY, YEAR, dateWords, parseDate, spanWords } from "./time.js";
import { Timeline, measure } from "./timeline.js";
import { Minimap } from "./minimap.js";
import { drawStrip } from "./print.js";

const config = window.__APP_CONFIG__ ?? {};
const source = window.__APP_DATA__ ?? { eras: [], events: [] };
const HUES = ["red", "orange", "gold", "green", "teal", "blue", "violet", "rose"];
const LEVEL_WORDS = { century: "Centuries", decade: "Decades", year: "Years", month: "Months", day: "Days" };
const STORY_DWELL = 2400;
const OPENING_MS = 1300;
const AUTOPLAY_AFTER = 2600;

const $ = (id) => document.getElementById(id);
const app = $("app");
const stage = $("stage");
const svg = $("timeline");
const card = $("card");
const driver = $("camera-driver");
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
const reduced = () => reducedQuery.matches;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// ---------------------------------------------------------------------------------------------------------------
// The data

function normalize(raw) {
  const eras = [];
  for (const [index, era] of (raw.eras ?? []).entries()) {
    const from = parseDate(era.from);
    const to = parseDate(era.to);
    if (!from || !to) continue;
    const named = HUES.includes(era.color);
    const hex = !named && /^#[0-9a-f]{6}$/i.test(era.color ?? "");
    eras.push({ id: `era-${index}`, label: String(era.label ?? ""), t: from.t, end: Math.max(to.end, from.t + DAY), hue: named ? era.color : hex ? "none" : HUES[index % HUES.length], custom: hex ? era.color : null });
  }
  const events = [];
  for (const event of raw.events ?? []) {
    const when = parseDate(event.date);
    if (!when || !event.label) continue;
    events.push({ ...when, label: String(event.label), body: event.text ? String(event.text) : "", image: event.image ?? null, eraName: event.era ?? null, raw: event });
  }
  events.sort((a, b) => a.t - b.t);
  const byId = new Map();
  for (const [index, event] of events.entries()) {
    event.id = `event-${index + 1}`;
    event.index = index;
    event.when = dateWords(event.t, event.precision);
    let era = event.eraName ? eras.find((e) => e.label === event.eraName) : null;
    if (!era) {
      const holding = eras.filter((e) => event.t >= e.t && event.t < e.end).sort((a, b) => a.end - a.t - (b.end - b.t));
      era = holding[0] ?? null;
    }
    event.era = era;
    event.hue = era ? era.hue : "none";
    event.customHue = era?.custom ?? null;
    byId.set(event.id, event);
  }
  const times = [...eras.flatMap((e) => [e.t, e.end]), ...events.flatMap((e) => [e.t, e.end])];
  const min = times.length ? Math.min(...times) : Date.UTC(2000, 0, 1);
  const max = times.length ? Math.max(...times) : Date.UTC(2001, 0, 1);
  return { eras, events, byId, min, max: Math.max(max, min + 30 * DAY) };
}

const data = normalize(source);
const title = String(config.title ?? "Era Timeline");
document.title = title;
$("title").textContent = title;
$("subtitle").textContent = config.subtitle ?? "";
const first = data.events[0];
const last = data.events[data.events.length - 1];
const statusWords = data.events.length
  ? `${data.events.length} ${data.events.length === 1 ? "event" : "events"} across ${data.eras.length} ${data.eras.length === 1 ? "era" : "eras"}, ${dateWords(first.t, "year")} to ${dateWords(last.t, "year")}`
  : "No events yet";
$("status").textContent = statusWords;
document.documentElement.dataset.pins = String(data.events.length);

// ---------------------------------------------------------------------------------------------------------------
// The drawing and the camera

const timeline = new Timeline(svg, data, {
  onPin: (event) => openEvent(event, { from: "pin" }),
  onCluster: (ids) => zoomToCluster(ids),
  reduced,
});
const minimap = new Minimap($("minimap-svg"), data, {
  onDrag: (t) => {
    stopMotion();
    pauseStory();
    centerOn(t);
  },
  onJump: (t) => {
    pauseStory();
    const length = timeline.g.length;
    flyTo({ t0: t - (length / 2) * cam.k, k: cam.k }, { duration: 320, easing: css("--ease-out") });
  },
  onKey: (e) => stageKeys(e),
});

let orient = "h";
let cam = { t0: data.min, k: YEAR / 10 };
let home = cam;
let tween = null;
let fling = null;
let opened = false;

function chooseOrient() {
  const wanted = config.orientation === "horizontal" ? "h" : config.orientation === "vertical" ? "v" : innerWidth >= innerHeight ? "h" : "v";
  app.dataset.orient = wanted;
  app.classList.toggle("is-narrow", wanted === "h" && innerWidth < 720);
  return wanted;
}

function limits() {
  const length = timeline.g.length;
  const span = data.max - data.min;
  return { kMin: (3 * DAY) / length, kMax: Math.max(span * 3, 60 * DAY) / length, tMin: data.min, tMax: data.max, length };
}

/** The camera that shows the inputs' start and end across the stage, clear of the edges. */
function homeCamera() {
  const start = parseDate(config.start ?? "") ?? { t: data.min };
  const end = parseDate(config.end ?? "") ?? { t: data.max };
  const g = timeline.g;
  if (orient === "h") return fit(start.t, end.t, 28, g.length - 28);
  return fit(start.t, end.t, 20, g.length - 72);
}

function layout() {
  // A stage with no size (hidden while printing) keeps the last layout.
  const size = stage.getBoundingClientRect();
  if (size.width < 40 || size.height < 40) return;
  const before = timeline.g ? { mid: timeAt(cam, timeline.g.length / 2), span: cam.k * timeline.g.length } : null;
  orient = chooseOrient();
  const rect = stage.getBoundingClientRect();
  const compact = rect.height < 360;
  timeline.resize(Math.round(rect.width), Math.round(rect.height), orient, compact);
  const mm = $("minimap-svg").getBoundingClientRect();
  minimap.resize(Math.round(mm.width), Math.round(mm.height), orient, timeline.layerCount);
  home = clampCamera(homeCamera(), limits());
  if (before) {
    const k = before.span / timeline.g.length;
    cam = clampCamera({ t0: before.mid - (timeline.g.length / 2) * k, k }, limits());
  }
  requestFrame();
}

// ---------------------------------------------------------------------------------------------------------------
// The frame loop: draws only when something changed, and keeps going while anything moves.

let queued = false;
let lastFrame = performance.now();
let pinchDue = false;
let settleTimer = 0;

function requestFrame() {
  if (queued) return;
  queued = true;
  requestAnimationFrame(frame);
}

function frame(now) {
  queued = false;
  const dt = Math.min(64, now - lastFrame);
  lastFrame = now;
  if (tween) {
    const progress = tween.anim.effect.getComputedTiming().progress;
    cam = tween.path(progress === null ? 1 : progress);
  }
  if (fling) stepFling(dt);
  if (pinchDue) applyPinch();
  const moving = timeline.render(cam);
  const length = timeline.g.length;
  minimap.render(cam.t0, timeAt(cam, length));
  if (moving || tween || fling || pinchDue) requestFrame();
  else {
    clearTimeout(settleTimer);
    settleTimer = setTimeout(settle, 140);
  }
}

/** Runs when the camera has come to rest: the bounding-box pass, exposed as data-overlaps. */
function settle() {
  if (tween || fling || !timeline.settled) return;
  const overlaps = timeline.overlaps();
  svg.dataset.overlaps = String(overlaps);
  document.documentElement.dataset.overlaps = String(overlaps);
}

svg.addEventListener("levelchange", (e) => {
  $("zoom-level").textContent = LEVEL_WORDS[e.detail] ?? "";
  document.documentElement.dataset.level = e.detail;
});

/** Eases the camera to `target` with the Web Animations API driving the progress; resolves true when it arrives. */
function flyTo(target, { duration = 600, easing = css("--ease-in-out") || "ease-in-out" } = {}) {
  stopMotion();
  const to = clampCamera(target, limits());
  if (reduced() || duration <= 0) {
    cam = to;
    requestFrame();
    return Promise.resolve(true);
  }
  const anim = driver.animate([{ opacity: 0 }, { opacity: 1 }], { duration, easing, fill: "forwards" });
  const mine = { anim, path: flight(cam, to, timeline.g.length), to };
  tween = mine;
  requestFrame();
  return anim.finished.then(
    () => {
      if (tween !== mine) return false;
      cam = to;
      tween = null;
      anim.cancel();
      requestFrame();
      return true;
    },
    () => false,
  );
}

function stopMotion() {
  if (tween) {
    const going = tween;
    tween = null;
    going.anim.cancel();
  }
  fling = null;
}

function setCamera(next) {
  cam = clampCamera(next, limits());
  requestFrame();
}

function centerOn(t) {
  const length = timeline.g.length;
  setCamera({ t0: t - (length / 2) * cam.k, k: cam.k });
}

function zoomBy(factor, { animate = true } = {}) {
  pauseStory();
  const base = tween ? tween.to : cam;
  const anchor = focusPx();
  const target = clampCamera(zoomAt(base, anchor, factor), limits());
  if (!animate) {
    stopMotion();
    setCamera(target);
    return;
  }
  flyTo(target, { duration: 220, easing: css("--ease-out") });
}

/** The pixel along the time axis that the eye rests on: the middle, or the middle of what the card leaves open. */
function focusPx() {
  const g = timeline.g;
  if (!card.classList.contains("is-open") && !cardWanted) return g.length / 2;
  if (orient === "h" && !app.classList.contains("is-narrow")) {
    const cardWidth = Math.min(400, innerWidth * 0.44) + 40;
    return Math.max(120, (g.length - cardWidth) / 2);
  }
  const sheet = Math.min(innerHeight * 0.52, 520);
  const stageTop = stage.getBoundingClientRect().top;
  const open = innerHeight - sheet - stageTop;
  return orient === "v" ? Math.max(80, open / 2) : g.length / 2;
}

/** The camera for one event: close enough that its nearest neighbor sits a little way off. */
function eventCamera(event) {
  const events = data.events;
  const gaps = [];
  if (event.index > 0) gaps.push(event.t - events[event.index - 1].t);
  if (event.index < events.length - 1) gaps.push(events[event.index + 1].t - event.t);
  const homeSpan = home.k * timeline.g.length;
  const nearest = gaps.length ? Math.min(...gaps) : homeSpan;
  const span = Math.min(homeSpan, Math.max(12 * DAY, nearest * 5));
  const k = span / timeline.g.length;
  return { t0: event.t - focusPx() * k, k };
}

function zoomToCluster(ids) {
  pauseStory();
  const times = ids.map((id) => data.byId.get(id).t);
  const lo = Math.min(...times);
  const hi = Math.max(...times);
  const length = timeline.g.length;
  const currentSpan = cam.k * length;
  const span = Math.max(8 * DAY, Math.min(currentSpan / 3, (hi - lo) * 3));
  const k = span / length;
  flyTo({ t0: (lo + hi) / 2 - (length / 2) * k, k }, { duration: 600 });
}

// ---------------------------------------------------------------------------------------------------------------
// Pointer input: one code path for mouse, pen, and touch. One pointer pans; two pinch.

const pointers = new Map();
let drag = null;
let pinchStart = null;

const local = (e) => {
  const r = svg.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
};
const alongOf = (p) => (orient === "h" ? p.x : p.y);

svg.addEventListener("pointerdown", (e) => {
  if (e.pointerType === "mouse" && e.button !== 0) return;
  touched();
  svg.setPointerCapture(e.pointerId);
  const p = local(e);
  pointers.set(e.pointerId, p);
  stopMotion();
  if (pointers.size === 1) {
    drag = { id: e.pointerId, last: alongOf(p), moved: 0, started: performance.now(), samples: [], target: e.target };
  } else if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinchStart = { cam: { ...cam }, a: { ...a }, b: { ...b } };
    drag = null;
  }
});

svg.addEventListener("pointermove", (e) => {
  if (!pointers.has(e.pointerId)) return;
  const p = local(e);
  pointers.set(e.pointerId, p);
  if (pinchStart) {
    // One frame of debounce: the pinch applies the latest two positions once per frame.
    pinchDue = true;
    requestFrame();
    return;
  }
  if (!drag || drag.id !== e.pointerId) return;
  const along = alongOf(p);
  const delta = along - drag.last;
  drag.last = along;
  drag.moved += Math.abs(delta);
  if (drag.moved > 6) stage.classList.add("is-dragging");
  const now = performance.now();
  drag.samples.push({ now, delta });
  while (drag.samples.length && now - drag.samples[0].now > 90) drag.samples.shift();
  setCamera(panBy(cam, delta));
});

function applyPinch() {
  pinchDue = false;
  if (!pinchStart || pointers.size < 2) return;
  const [a, b] = [...pointers.values()];
  cam = clampCamera(pinch(pinchStart, a, b, orient === "h" ? "x" : "y"), limits());
}

function release(e) {
  if (!pointers.has(e.pointerId)) return;
  pointers.delete(e.pointerId);
  stage.classList.remove("is-dragging");
  if (pinchStart) {
    if (pointers.size < 2) {
      pinchStart = null;
      const rest = [...pointers.entries()][0];
      // The finger left on the glass carries on panning, never counted as a tap.
      drag = rest ? { id: rest[0], last: alongOf(rest[1]), moved: 99, started: 0, samples: [], target: null } : null;
    }
    return;
  }
  if (!drag || drag.id !== e.pointerId) return;
  const ended = drag;
  drag = null;
  const quick = performance.now() - ended.started < 700;
  if (ended.moved < 6 && quick && e.type === "pointerup") {
    tap(ended.target);
    return;
  }
  const span = ended.samples.length > 1 ? ended.samples[ended.samples.length - 1].now - ended.samples[0].now : 0;
  const sum = ended.samples.reduce((total, s) => total + s.delta, 0);
  const velocity = span > 0 ? sum / span : 0;
  if (!reduced() && Math.abs(velocity) > 0.25) {
    fling = { velocity: Math.max(-6, Math.min(6, velocity)) };
    requestFrame();
  }
}
svg.addEventListener("pointerup", release);
svg.addEventListener("pointercancel", release);

function stepFling(dt) {
  setCamera(panBy(cam, fling.velocity * dt));
  fling.velocity *= Math.exp(-dt / 325);
  if (Math.abs(fling.velocity) < 0.02) fling = null;
}

function tap(target) {
  const flag = target?.closest?.(".flag");
  if (flag) {
    const event = data.byId.get(flag.dataset.id);
    if (event) openEvent(event, { from: "pin" });
    return;
  }
  const badge = target?.closest?.(".cluster");
  if (badge) {
    const item = timeline.clusterEls[Number(badge.dataset.index)];
    if (item?.ids.length) zoomToCluster(item.ids);
    return;
  }
  if (card.classList.contains("is-open") && !story) closeCard();
}

svg.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    touched();
    stopMotion();
    let dx = e.deltaX;
    let dy = e.deltaY;
    if (e.deltaMode === 1) {
      dx *= 33;
      dy *= 33;
    } else if (e.deltaMode === 2) {
      dx *= 400;
      dy *= 400;
    }
    const along = alongOf(local(e));
    if (!e.ctrlKey && orient === "h" && Math.abs(dx) > Math.abs(dy)) {
      setCamera(panBy(cam, -dx));
      return;
    }
    if (!e.ctrlKey && e.shiftKey) {
      setCamera(panBy(cam, -(dy || dx)));
      return;
    }
    const factor = Math.min(2, Math.max(0.5, Math.exp(-dy * (e.ctrlKey ? 0.012 : 0.0045))));
    setCamera(zoomAt(cam, along, factor));
  },
  { passive: false },
);

// ---------------------------------------------------------------------------------------------------------------
// Keys

function stageKeys(e) {
  const length = timeline.g.length;
  const forward = orient === "h" ? ["ArrowRight"] : ["ArrowDown"];
  const back = orient === "h" ? ["ArrowLeft"] : ["ArrowUp"];
  const step = e.shiftKey ? length * 0.5 : length * 0.15;
  if (forward.includes(e.key)) setCamera(panBy(cam, -step));
  else if (back.includes(e.key)) setCamera(panBy(cam, step));
  else if (e.key === "+" || e.key === "=") zoomBy(2, { animate: false });
  else if (e.key === "-" || e.key === "_") zoomBy(0.5, { animate: false });
  else if (e.key === "Home" || e.key === "0") setCamera(home);
  else return;
  e.preventDefault();
  touched();
  stopMotion();
}
stage.addEventListener("keydown", (e) => {
  if (e.target.closest?.(".flag, .cluster") && (e.key === "Enter" || e.key === " ")) return;
  stageKeys(e);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (closeTop()) e.preventDefault();
    return;
  }
  const typing = e.target.matches?.("input, textarea");
  if (typing) return;
  if (e.key === "/") {
    e.preventDefault();
    openSearch();
    return;
  }
  if (story && (e.key === "ArrowRight" || e.key === "ArrowDown") && !stage.contains(e.target)) {
    e.preventDefault();
    storyStep(1);
  } else if (story && (e.key === "ArrowLeft" || e.key === "ArrowUp") && !stage.contains(e.target)) {
    e.preventDefault();
    storyStep(-1);
  }
});

for (const button of document.querySelectorAll("[data-zoom]")) {
  button.addEventListener("click", () => {
    touched();
    const kind = button.dataset.zoom;
    if (kind === "in") zoomBy(2);
    else if (kind === "out") zoomBy(0.5);
    else {
      pauseStory();
      const length = timeline.g.length;
      const span = data.max - data.min;
      const k = (span * 1.08) / (length - 40);
      flyTo({ t0: data.min - span * 0.04 - 20 * k, k }, { duration: 600 });
    }
  });
}

// ---------------------------------------------------------------------------------------------------------------
// The event card

let current = null;
let cardWanted = false;
let cardTimer = 0;

function fillCard(event) {
  current = event;
  const era = event.era;
  $("card-title").textContent = event.label;
  $("card-text").textContent = event.body;
  const date = $("card-date");
  date.textContent = event.when;
  date.setAttribute("datetime", event.raw.date);
  const chip = $("card-era");
  chip.hidden = !era;
  if (era) {
    $("card-era-name").textContent = era.label;
    const dot = $("card-era-dot");
    dot.dataset.hue = era.hue;
    if (era.custom) dot.style.setProperty("--hue", era.custom);
    else dot.style.removeProperty("--hue");
  }
  const img = $("card-img");
  card.classList.toggle("no-image", !event.image);
  if (event.image) {
    img.src = event.image;
    img.alt = event.label;
  } else {
    img.removeAttribute("src");
    img.alt = "";
  }
  $("card-goto").href = `#${event.id}`;
  $("card-goto").textContent = `Go to ${event.when}`;
  $("card-pos").textContent = `${event.index + 1} of ${data.events.length}`;
  $("card-prev").disabled = event.index === 0;
  $("card-next").disabled = event.index === data.events.length - 1;
  timeline.selected = event.id;
  requestFrame();
}

function showCard() {
  clearTimeout(cardTimer);
  cardWanted = true;
  if (card.hidden) {
    card.hidden = false;
    card.style.removeProperty("--sheet-drag");
    void card.offsetWidth;
  }
  card.classList.add("is-open");
}

function closeCard() {
  cardWanted = false;
  card.classList.remove("is-open");
  timeline.selected = null;
  current = null;
  requestFrame();
  clearTimeout(cardTimer);
  cardTimer = setTimeout(() => {
    if (!card.classList.contains("is-open")) card.hidden = true;
  }, reduced() ? 0 : 420);
  if (story) endStory();
}

/** Opens `event`'s card. From a pin the camera only moves when the card would cover the pin. */
function openEvent(event, { from }) {
  touched();
  if (story && from !== "story") endStory({ keepCard: true });
  const wasOpen = card.classList.contains("is-open");
  cardWanted = true;
  fillCard(event);
  showCard();
  if (from === "pin") {
    const at = pxOf(cam, event.t);
    const length = timeline.g.length;
    const focus = focusPx();
    const covered = orient === "h" && !app.classList.contains("is-narrow") ? at > length - Math.min(400, innerWidth * 0.44) - 60 : at > focus * 2 - 40;
    if (covered) flyTo({ t0: event.t - focus * cam.k, k: cam.k }, { duration: 420, easing: css("--ease-out") });
  } else {
    flyTo(eventCamera(event), { duration: 600 });
  }
  if (!wasOpen && from !== "pin") card.focus?.();
}

$("card-close").addEventListener("click", () => closeCard());
$("card-goto").addEventListener("click", (e) => {
  e.preventDefault();
  if (current) {
    pauseStory();
    flyTo(eventCamera(current), { duration: 600 });
  }
});
$("card-prev").addEventListener("click", () => step(-1));
$("card-next").addEventListener("click", () => step(1));
$("card-play").addEventListener("click", () => {
  if (!story) return;
  if (story.playing) pauseStory();
  else {
    story.playing = true;
    syncStoryButtons();
    storyStep(1);
  }
});

function step(direction) {
  if (story) {
    pauseStory();
    storyStep(direction);
    return;
  }
  if (!current) return;
  const next = data.events[current.index + direction];
  if (next) openEvent(next, { from: "step" });
}

// The sheet follows a drag down and closes past a third of its height.
(() => {
  let start = null;
  card.addEventListener("pointerdown", (e) => {
    const sheet = orient === "v" || app.classList.contains("is-narrow");
    if (!sheet || e.target.closest("button, a")) return;
    const scroll = $("card-scroll");
    if (scroll.scrollTop > 0 && !e.target.closest(".card-grip, .card-figure")) return;
    start = { y: e.clientY, id: e.pointerId, h: card.offsetHeight };
  });
  card.addEventListener("pointermove", (e) => {
    if (!start || e.pointerId !== start.id) return;
    const dy = Math.max(0, e.clientY - start.y);
    if (dy > 4) {
      card.classList.add("is-dragging");
      card.setPointerCapture(e.pointerId);
    }
    card.style.setProperty("--sheet-drag", `${dy}px`);
  });
  const end = (e) => {
    if (!start || e.pointerId !== start.id) return;
    const dy = Math.max(0, e.clientY - start.y);
    card.classList.remove("is-dragging");
    card.style.setProperty("--sheet-drag", "0px");
    if (dy > start.h / 3) closeCard();
    start = null;
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", end);
})();

// ---------------------------------------------------------------------------------------------------------------
// Story: walks every event in order, the camera easing from one to the next (600 ms, ease-in-out) and the card
// opening as it arrives.

let story = null;
const visited = new Set();

function startStory({ playing = true, from = 0 } = {}) {
  closeSearch();
  closeList();
  story = { index: from - 1, playing, token: 0, timer: 0 };
  app.classList.add("is-story");
  card.classList.add("is-story");
  $("btn-story").setAttribute("aria-pressed", "true");
  syncStoryButtons();
  storyStep(1);
}

function syncStoryButtons() {
  card.classList.toggle("is-playing", Boolean(story?.playing));
  $("card-play").setAttribute("aria-label", story?.playing ? "Pause the story" : "Play the story");
}

async function storyStep(direction) {
  if (!story) return;
  clearTimeout(story.timer);
  const index = story.index + direction;
  if (index < 0) return;
  if (index >= data.events.length) {
    endStory();
    closeCard();
    flyTo(home, { duration: 600 });
    return;
  }
  story.index = index;
  const token = ++story.token;
  const event = data.events[index];
  timeline.selected = event.id;
  cardWanted = true;
  const arrived = await flyTo(eventCamera(event), { duration: 600 });
  if (!story || story.token !== token || (!arrived && tween)) return;
  const swapping = card.classList.contains("is-open");
  fillCard(event);
  showCard();
  if (swapping && !reduced()) {
    $("card-scroll").scrollTop = 0;
    $("card-scroll").animate([{ opacity: 0, transform: "translateY(6px)" }, { opacity: 1, transform: "none" }], { duration: 240, easing: css("--ease-out") });
  }
  visited.add(event.id);
  document.documentElement.dataset.storyVisited = String(visited.size);
  document.documentElement.dataset.storyIndex = String(index + 1);
  if (story.playing) story.timer = setTimeout(() => storyStep(1), STORY_DWELL);
}

function pauseStory() {
  if (!story || !story.playing) return;
  story.playing = false;
  clearTimeout(story.timer);
  syncStoryButtons();
}

function endStory({ keepCard = false } = {}) {
  if (!story) return;
  clearTimeout(story.timer);
  story = null;
  app.classList.remove("is-story");
  card.classList.remove("is-story", "is-playing");
  $("btn-story").setAttribute("aria-pressed", "false");
  if (!keepCard) cardWanted = card.classList.contains("is-open");
}

$("btn-story").addEventListener("click", () => {
  touched();
  if (story) {
    endStory();
    closeCard();
  } else {
    const start = current ? current.index : 0;
    startStory({ playing: true, from: start });
  }
});

// ---------------------------------------------------------------------------------------------------------------
// The list: every event by date.

const scrim = $("scrim");
const list = $("list");
let lastFocus = null;

function buildList() {
  const host = $("list-items");
  host.replaceChildren();
  let group = null;
  for (const event of data.events) {
    const decade = Math.floor(event.year / 10) * 10;
    const words = decade > 0 ? `${decade}s` : dateWords(event.t, "year");
    if (words !== group) {
      group = words;
      const head = document.createElement("li");
      head.className = "list-group";
      head.textContent = words;
      host.appendChild(head);
    }
    const li = document.createElement("li");
    const row = document.createElement("button");
    row.type = "button";
    row.className = "list-row";
    row.dataset.id = event.id;
    const date = document.createElement("span");
    date.className = "list-date";
    date.textContent = event.when;
    const label = document.createElement("span");
    label.className = "list-label";
    const dot = document.createElement("span");
    dot.className = "chip-dot";
    dot.dataset.hue = event.hue;
    if (event.customHue) dot.style.setProperty("--hue", event.customHue);
    label.append(dot, document.createTextNode(event.label));
    row.append(date, label);
    row.addEventListener("click", () => {
      closeList();
      openEvent(event, { from: "list" });
    });
    li.appendChild(row);
    host.appendChild(li);
  }
  const span = data.events.length > 1 ? spanWords(last.t - first.t) : "";
  $("list-sub").textContent = data.events.length ? `${data.events.length} events over ${span}` : "No events yet";
}

function openList() {
  touched();
  pauseStory();
  closeSearch();
  lastFocus = document.activeElement;
  list.hidden = false;
  scrim.hidden = false;
  void list.offsetWidth;
  list.classList.add("is-open");
  scrim.classList.add("is-open");
  for (const row of list.querySelectorAll(".list-row")) row.classList.toggle("is-current", row.dataset.id === current?.id);
  const target = list.querySelector(".list-row.is-current") ?? list.querySelector(".list-row");
  target?.focus({ preventScroll: false });
  target?.scrollIntoView({ block: "center" });
}

function closeList() {
  if (list.hidden) return false;
  list.classList.remove("is-open");
  scrim.classList.remove("is-open");
  setTimeout(() => {
    if (!list.classList.contains("is-open")) {
      list.hidden = true;
      scrim.hidden = true;
    }
  }, reduced() ? 0 : 420);
  lastFocus?.focus?.();
  return true;
}

$("btn-list").addEventListener("click", openList);
$("list-close").addEventListener("click", closeList);
scrim.addEventListener("click", closeList);
list.addEventListener("keydown", (e) => {
  if (e.key !== "Tab") return;
  const items = [...list.querySelectorAll("button")];
  const firstItem = items[0];
  const lastItem = items[items.length - 1];
  if (e.shiftKey && document.activeElement === firstItem) {
    e.preventDefault();
    lastItem.focus();
  } else if (!e.shiftKey && document.activeElement === lastItem) {
    e.preventDefault();
    firstItem.focus();
  }
});

// ---------------------------------------------------------------------------------------------------------------
// Search

const search = $("search");
const results = $("results");
let found = [];
let active = 0;

const fold = (text) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
for (const event of data.events) event.haystack = fold(`${event.label} ${event.body} ${event.era?.label ?? ""} ${event.when}`);

function runSearch() {
  const query = fold(search.value.trim());
  if (!query) {
    found = [];
    timeline.matches = null;
    results.hidden = true;
    search.setAttribute("aria-expanded", "false");
    requestFrame();
    return;
  }
  const words = query.split(/\s+/);
  found = data.events.filter((event) => words.every((word) => event.haystack.includes(word)));
  timeline.matches = new Set(found.map((event) => event.id));
  active = 0;
  results.replaceChildren();
  if (!found.length) {
    const none = document.createElement("li");
    none.className = "result-empty";
    none.textContent = "No event matches that.";
    results.appendChild(none);
  }
  for (const [index, event] of found.slice(0, 8).entries()) {
    const li = document.createElement("li");
    li.className = "result";
    li.id = `result-${index}`;
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", index === active ? "true" : "false");
    const label = document.createElement("span");
    label.className = "result-label";
    label.textContent = event.label;
    const date = document.createElement("span");
    date.className = "result-date";
    date.textContent = event.era ? `${event.when}, ${event.era.label}` : event.when;
    li.append(label, date);
    li.addEventListener("pointerdown", (e) => e.preventDefault());
    li.addEventListener("click", () => choose(event));
    results.appendChild(li);
  }
  results.hidden = false;
  search.setAttribute("aria-expanded", "true");
  search.setAttribute("aria-activedescendant", found.length ? "result-0" : "");
  requestFrame();
}

function choose(event) {
  closeSearch({ keepQuery: true });
  openEvent(event, { from: "search" });
}

function closeSearch({ keepQuery = false } = {}) {
  results.hidden = true;
  search.setAttribute("aria-expanded", "false");
  if (!keepQuery) {
    search.value = "";
    timeline.matches = null;
    requestFrame();
  }
  app.classList.remove("is-searching");
}

function openSearch() {
  app.classList.add("is-searching");
  search.focus();
}

search.addEventListener("input", () => {
  touched();
  pauseStory();
  runSearch();
});
search.addEventListener("keydown", (e) => {
  const shown = Math.min(8, found.length);
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    if (!shown) return;
    e.preventDefault();
    active = (active + (e.key === "ArrowDown" ? 1 : shown - 1)) % shown;
    for (const [index, li] of [...results.querySelectorAll(".result")].entries()) li.setAttribute("aria-selected", index === active ? "true" : "false");
    search.setAttribute("aria-activedescendant", `result-${active}`);
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (found[active]) choose(found[active]);
  } else if (e.key === "Escape") {
    e.stopPropagation();
    closeSearch();
    search.blur();
  }
});
search.addEventListener("blur", () => {
  setTimeout(() => {
    if (document.activeElement !== search) {
      results.hidden = true;
      if (!search.value) app.classList.remove("is-searching");
    }
  }, 120);
});
$("btn-search").addEventListener("click", () => {
  if (app.classList.contains("is-searching")) closeSearch();
  else openSearch();
});

// ---------------------------------------------------------------------------------------------------------------
// Print

const printview = $("printview");
let stripDrawn = false;

function ensureStrip() {
  if (stripDrawn) return;
  drawStrip($("strip"), data, { title, subtitle: config.subtitle ?? "" });
  stripDrawn = true;
}

$("btn-print").addEventListener("click", () => {
  touched();
  pauseStory();
  ensureStrip();
  lastFocus = document.activeElement;
  printview.hidden = false;
  $("print-go").focus();
});
$("print-go").addEventListener("click", () => {
  ensureStrip();
  window.print();
});
$("print-close").addEventListener("click", closePrint);
function closePrint() {
  if (printview.hidden) return false;
  printview.hidden = true;
  lastFocus?.focus?.();
  return true;
}
addEventListener("beforeprint", ensureStrip);
matchMedia("print").addEventListener("change", (e) => {
  if (e.matches) ensureStrip();
});

/** Escape closes the top-most thing open; true when something closed. */
function closeTop() {
  if (!results.hidden || app.classList.contains("is-searching")) {
    closeSearch();
    return true;
  }
  if (closePrint()) return true;
  if (closeList()) return true;
  if (card.classList.contains("is-open")) {
    closeCard();
    stage.focus();
    return true;
  }
  if (story) {
    endStory();
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------------------------------------------
// The opening: the camera starts wide on the whole span and settles on the inputs' start and end while the pins rise
// into their lanes; then, when autoplay is on and nobody has touched anything, the story walk begins.

let untouched = true;
let autoplayTimer = 0;
function touched() {
  untouched = false;
  clearTimeout(autoplayTimer);
  if (story?.playing) pauseStory();
}

function open() {
  layout();
  buildList();
  const wide = (() => {
    const length = timeline.g.length;
    const mid = timeAt(home, length / 2);
    const k = Math.min(limits().kMax, home.k * 3.2);
    return { t0: mid - (length / 2) * k, k };
  })();
  if (reduced()) {
    cam = home;
    requestFrame();
  } else {
    cam = clampCamera(wide, limits());
    app.classList.add("is-opening");
    requestFrame();
    flyTo(home, { duration: OPENING_MS, easing: css("--ease-out") });
    setTimeout(() => app.classList.remove("is-opening"), OPENING_MS + 1400);
  }
  opened = true;
  if (config.autoplay && !reduced() && data.events.length) {
    autoplayTimer = setTimeout(() => {
      if (untouched && !story) startStory({ playing: true, from: 0 });
    }, AUTOPLAY_AFTER);
  }
  const idle = window.requestIdleCallback ?? ((fn) => setTimeout(fn, 400));
  idle(() => ensureStrip());
}

new ResizeObserver(() => {
  if (opened) layout();
}).observe(stage);
addEventListener("resize", () => {
  if (opened && chooseOrient() !== orient) layout();
});
reducedQuery.addEventListener("change", () => requestFrame());

// Text is measured for the lanes, so the fonts are in before the first layout (never more than a moment's wait).
Promise.race([document.fonts.ready, new Promise((done) => setTimeout(done, 700))]).then(() => {
  measure.clear();
  open();
  document.fonts.addEventListener?.("loadingdone", () => {
    measure.clear();
    for (const event of data.events) {
      event.text = null;
      event.lines = null;
    }
    requestFrame();
  });
});
