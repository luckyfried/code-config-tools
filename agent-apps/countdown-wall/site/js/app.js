// The wall: the nearest event in the hero, the rest as tiles by date, the past as "since" tiles, and a full-screen
// view of one event. Events come from data.js, the title and hour format from config.js.
import { Clock } from "./flap.js";
import { eventTokens, paint } from "./color.js";
import { occurrence, remaining, progress, parts, daysSince, formatters } from "./time.js";

const config = window.__APP_CONFIG__ ?? {};
const data = window.__APP_DATA__ ?? {};
const events = Array.isArray(data.events) ? data.events : [];
const fmt = formatters(Number(config.hourFormat) === 24 ? 24 : 12);
const title = typeof config.title === "string" && config.title.trim() ? config.title.trim() : "Countdown Wall";

const root = document.documentElement;
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
const SPRING = "cubic-bezier(0.32, 0.72, 0, 1)";
const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const LARGE_WITHIN_DAYS = 30;
const SVG = "http://www.w3.org/2000/svg";

const $ = (selector) => document.querySelector(selector);
const hero = $("#hero");
const wall = $("#wall");
const sinceRow = $("#since");
const sinceBoard = $("#since-board");
const stage = $("#stage");

/** Updaters for everything on screen that changes with the clock; each runs once a second. */
let live = [];
let stageLive = null;
let view = { hero: null, wall: [], since: [], signature: "" };
let timer = 0;
let opener = null;
let openedFrom = null;
let enteredFullscreen = false;
/** True when the full-screen view was opened from a tile or the hero, so closing it goes back. */
let pushed = false;
let lastScreen = "#/";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function icon(name) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG, "use");
  use.setAttribute("href", `./icons/sprite.svg#${name}`);
  svg.append(use);
  return svg;
}

function motionMs(token) {
  if (reduce.matches) return 0;
  const value = getComputedStyle(root).getPropertyValue(token).trim();
  return value.endsWith("ms") ? parseFloat(value) : 0;
}

function classify(now) {
  const all = events.map((ev) => ({ ev, occ: occurrence(ev, now) }));
  const future = all.filter((e) => !e.occ.past).sort((a, b) => a.occ.at - b.occ.at);
  const past = all.filter((e) => e.occ.past).sort((a, b) => b.occ.at - a.occ.at);
  return {
    hero: future[0] ?? null,
    wall: future.slice(1),
    since: past,
    signature: `${future.map((e) => e.ev.id).join(",")}|${past.map((e) => e.ev.id).join(",")}`,
  };
}

function setBar(bar, value) {
  bar.firstChild.style.setProperty("--p", value.toFixed(4));
}

function bar() {
  const node = el("div", "bar");
  node.append(el("i"));
  return node;
}

function sinceWords(occ, now) {
  const days = daysSince(occ, now);
  if (days >= 1) return [String(days), days === 1 ? "day since" : "days since"];
  const hours = Math.floor((now - occ.at) / 3600000);
  if (hours >= 1) return [String(hours), hours === 1 ? "hour since" : "hours since"];
  return ["0", "hours since"];
}

// The hero

function renderHero(entry, now) {
  hero.replaceChildren();
  hero.removeAttribute("data-id");
  const glow = el("div", "hero-glow");
  const surface = el("div", "hero-surface");
  surface.append(el("div", "mesh"));
  hero.append(glow, surface);

  if (!entry) {
    const block = el("div", "hero-title-block");
    const heading = el("h1", "hero-title", events.length ? "Nothing coming up" : "Nothing on the wall yet");
    const note = el(
      "p",
      "hero-empty",
      events.length
        ? "Everything here has happened. Add the next date you're waiting for and it counts down here."
        : "Add the dates you're waiting for and they count down here, the nearest one up top.",
    );
    block.append(heading, note);
    hero.append(block);
    return null;
  }

  const { ev, occ } = entry;
  paint(hero, ev.color);
  hero.dataset.id = ev.id;
  hero.setAttribute("aria-label", `Next up: ${ev.title}`);

  const head = el("div", "hero-head");
  const block = el("div", "hero-title-block");
  const heading = el("h1", "hero-title");
  if (ev.icon) heading.append(icon(ev.icon));
  heading.append(document.createTextNode(ev.title));
  const when = el("p", "hero-when", fmt.long(occ, now));
  block.append(heading, when);

  const full = el("button", "chip-button");
  full.type = "button";
  full.setAttribute("aria-label", `Show ${ev.title} full screen`);
  full.append(icon("maximize-2"), el("span", "chip-label", "Full screen"));
  full.addEventListener("click", () => {
    opener = full;
    openedFrom = surface.getBoundingClientRect();
    if (root.requestFullscreen && !document.fullscreenElement) {
      root
        .requestFullscreen()
        .then(() => {
          enteredFullscreen = true;
        })
        .catch(() => {});
    }
    pushed = true;
    location.hash = `#/event/${encodeURIComponent(ev.id)}`;
  });
  head.append(block, full);

  const clock = new Clock({ className: "clock-hero", units: 4 });
  hero.append(head, clock.node);

  let lastWhen = when.textContent;
  return {
    clock,
    surface,
    head,
    update(now, opts) {
      const occNow = occurrence(ev, now);
      clock.update(remaining(occNow, now), opts);
      const text = fmt.long(occNow, now);
      if (text !== lastWhen) when.textContent = lastWhen = text;
    },
  };
}

// The tiles

function tileLink(entry, className) {
  const { ev } = entry;
  const tile = el("a", `tile ${className}`);
  tile.href = `#/event/${encodeURIComponent(ev.id)}`;
  tile.dataset.id = ev.id;
  paint(tile, ev.color);
  return tile;
}

function iconBadge(name) {
  const badge = el("span", "tile-icon");
  badge.append(icon(name || "calendar"));
  return badge;
}

function largeTile(entry, now) {
  const { ev } = entry;
  const tile = tileLink(entry, "tile-large");
  const top = el("div", "tile-top");
  const when = el("span", "tile-when", fmt.short(entry.occ, now));
  top.append(iconBadge(ev.icon), when);
  const heading = el("h3", "tile-title", ev.title);
  const clock = new Clock({ className: "clock-mini", units: 3, minDayDigits: 2 });
  const progressBar = bar();
  tile.append(top, heading, clock.node, progressBar);
  tile.setAttribute("aria-label", `${ev.title}, ${when.textContent}`);
  return {
    tile,
    update(now, opts) {
      const occ = occurrence(ev, now);
      clock.update(remaining(occ, now), opts);
      setBar(progressBar, progress(occ, now));
    },
  };
}

function smallTile(entry, now) {
  const { ev } = entry;
  const tile = tileLink(entry, "tile-small");
  const head = el("div", "tile-head");
  const heading = el("h3", "tile-title", ev.title);
  head.append(iconBadge(ev.icon));
  const count = el("div", "tile-count");
  const num = el("span", "count-num");
  const unit = el("span", "count-unit");
  count.append(num, unit);
  const foot = el("div", "tile-foot");
  const when = el("p", "tile-when", fmt.short(entry.occ, now));
  foot.append(heading, when);
  const progressBar = bar();
  tile.append(head, count, foot, progressBar);
  return {
    tile,
    update(now) {
      const occ = occurrence(ev, now);
      const days = remaining(occ, now).days;
      const text = String(days);
      if (num.textContent !== text) {
        num.textContent = text;
        unit.textContent = days === 1 ? "day" : "days";
      }
      setBar(progressBar, progress(occ, now));
    },
  };
}

function sinceTile(entry) {
  const { ev, occ } = entry;
  const tile = tileLink(entry, "tile-since");
  const meta = el("div", "tile-meta");
  meta.append(el("h3", "tile-title", ev.title), el("p", "tile-when", fmt.since(occ)));
  const count = el("div", "tile-count");
  const num = el("span", "count-num");
  const unit = el("span", "count-unit");
  count.append(num, unit);
  tile.append(meta, count);
  return {
    tile,
    update(now) {
      const [n, words] = sinceWords(occ, now);
      if (num.textContent !== n) num.textContent = n;
      if (unit.textContent !== words) unit.textContent = words;
    },
  };
}

function pastTile(entry) {
  const { ev, occ } = entry;
  const tile = tileLink(entry, "tile-past");
  const head = el("div", "tile-head");
  const meta = el("div", "tile-meta");
  meta.append(el("h3", "tile-title", ev.title), el("p", "tile-when", fmt.since(occ)));
  head.append(iconBadge(ev.icon), meta);
  const clock = new Clock({ className: "clock-mini", units: 4, minDayDigits: 2 });
  tile.append(head, clock.node);
  return {
    tile,
    update(now, opts) {
      clock.update(parts(now - occ.at, true), opts);
    },
  };
}

// Rendering the screens

function render(next, now) {
  live = [];
  view = next;
  const heroLive = renderHero(next.hero, now);
  if (heroLive) live.push(heroLive.update);

  const tiles = next.wall.map((entry) => {
    const large = remaining(entry.occ, now).days < LARGE_WITHIN_DAYS;
    return large ? largeTile(entry, now) : smallTile(entry, now);
  });
  wall.replaceChildren(...tiles.map((t) => t.tile));
  live.push(...tiles.map((t) => t.update));
  $("#coming").hidden = tiles.length === 0;
  $("#coming .section-note").textContent = tiles.length === 1 ? "1 more" : `${tiles.length} more`;

  const since = next.since.map(sinceTile);
  sinceRow.replaceChildren(...since.map((t) => t.tile));
  live.push(...since.map((t) => t.update));
  $("#since-row").hidden = since.length === 0;
  $("#since-row .section-note").textContent = since.length === 1 ? "1 behind you" : `${since.length} behind you`;
  $(".tab-count").textContent = next.since.length ? String(next.since.length) : "";

  const past = next.since.map(pastTile);
  if (past.length) sinceBoard.replaceChildren(...past.map((t) => t.tile));
  else sinceBoard.replaceChildren(el("p", "empty-note", "Nothing has passed yet. When an event's moment comes, it moves here and counts up."));
  live.push(...past.map((t) => t.update));
  $("#since-screen .screen-lede").textContent = past.length
    ? `${past.length === 1 ? "One date" : `${past.length} dates`} behind you, counting up.`
    : "";

  for (const update of live) update(now, { animate: false });
  return heroLive;
}

/** The FLIP: plays `target` from the rect it was at (`from`) to where it is now. */
function liftFrom(target, from, duration) {
  if (!from || duration === 0) return;
  const to = target.getBoundingClientRect();
  if (to.width === 0 || to.height === 0) return;
  const dx = from.left - to.left;
  const dy = from.top - to.top;
  const sx = from.width / to.width;
  const sy = from.height / to.height;
  target.animate([{ transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})` }, { transform: "none" }], {
    duration,
    easing: SPRING,
  });
}

function enter(node, delay, duration = 420) {
  node.animate(
    [
      { opacity: 0, transform: "translateY(16px)" },
      { opacity: 1, transform: "none" },
    ],
    { duration, delay, easing: EASE_OUT, fill: "backwards" },
  );
}

function revealHero(heroLive, from, now) {
  const lift = motionMs("--motion-lift");
  if (!heroLive) return;
  if (lift === 0) return;
  liftFrom(heroLive.surface, from, lift);
  hero.querySelector(".hero-glow").animate([{ opacity: 0 }, { opacity: 1 }], {
    duration: lift,
    delay: lift * 0.4,
    easing: EASE_OUT,
    fill: "backwards",
  });
  enter(heroLive.head, lift * 0.28, 460);
  enter(heroLive.clock.node, lift * 0.36, 460);
  // The board powers on at zero and every other digit falls to the time, left to right.
  for (const unit of heroLive.clock.units) for (const flap of unit.flaps) flap.set("0", { animate: false });
  heroLive.clock.update(remaining(occurrence(view.hero.ev, now), now), { animate: true, delay: lift * 0.45, stagger: 42 });
}

function firstLoad(now) {
  const next = classify(now);
  const heroLive = render(next, now);
  if (motionMs("--motion-lift") === 0) return;
  // The nearest event lifts out of the wall's first place into the hero, and the wall settles in behind it.
  const first = wall.firstElementChild;
  const from = first ? first.getBoundingClientRect() : null;
  revealHero(heroLive, from, now);
  [...wall.children, ...sinceRow.children].slice(0, 16).forEach((tile, i) => enter(tile, 240 + i * 45));
}

/** An event passed: the next tile lifts into the hero and the wall closes up behind it. */
function transition(next, now) {
  const before = new Map();
  for (const tile of document.querySelectorAll("#wall [data-id], #since [data-id]")) {
    before.set(tile.dataset.id, tile.getBoundingClientRect());
  }
  const from = next.hero ? before.get(next.hero.ev.id) : null;
  const heroLive = render(next, now);
  const lift = motionMs("--motion-lift");
  if (lift === 0) return;
  revealHero(heroLive, from ?? null, now);
  let fresh = 0;
  for (const tile of document.querySelectorAll("#wall [data-id], #since [data-id]")) {
    const was = before.get(tile.dataset.id);
    if (was) {
      const is = tile.getBoundingClientRect();
      const dx = was.left - is.left;
      const dy = was.top - is.top;
      if (dx || dy) {
        tile.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], {
          duration: lift,
          easing: SPRING,
        });
      }
    } else {
      enter(tile, lift * 0.5 + fresh * 40);
      fresh += 1;
    }
  }
  if (stageLive) openStage(stageLive.id, { replace: true });
}

// The full-screen view

function ordered() {
  return [...(view.hero ? [view.hero] : []), ...view.wall, ...view.since];
}

function stageButton(name, label) {
  const button = el("button", "icon-button");
  button.type = "button";
  button.setAttribute("aria-label", label);
  button.append(icon(name));
  return button;
}

function openStage(id, { replace = false } = {}) {
  const list = ordered();
  const index = list.findIndex((e) => e.ev.id === id);
  if (index < 0) {
    location.replace("#/");
    return;
  }
  const { ev } = list[index];
  const wasOpen = !stage.hidden;
  stage.replaceChildren();
  stage.removeAttribute("style");
  paint(stage, ev.color);
  stage.classList.toggle("has-image", Boolean(ev.image));

  const surface = el("div", "stage-surface");
  if (ev.image) {
    const img = el("img", "stage-image");
    img.src = ev.image;
    img.alt = "";
    img.decoding = "async";
    surface.append(img);
  }
  surface.append(el("div", "mesh"));

  const top = el("div", "stage-top");
  const count = el("p", "stage-count", `${index + 1} of ${list.length}`);
  const close = stageButton("x", "Close");
  close.addEventListener("click", closeStage);
  top.append(count, close);

  const body = el("div", "stage-body");
  const heading = el("h2", "stage-title");
  heading.id = "stage-title";
  if (ev.icon) heading.append(icon(ev.icon));
  heading.append(document.createTextNode(ev.title));
  const clock = new Clock({ className: "clock-stage", units: 4 });
  const when = el("p", "stage-when");
  body.append(heading, clock.node, when);

  const foot = el("div", "stage-foot");
  const prev = stageButton("chevron-left", "Previous event");
  const nextButton = stageButton("chevron-right", "Next event");
  prev.disabled = index === 0;
  nextButton.disabled = index === list.length - 1;
  prev.addEventListener("click", () => step(-1));
  nextButton.addEventListener("click", () => step(1));
  const progressBox = el("div", "stage-progress");
  const progressBar = bar();
  const progressLabel = el("p", "stage-progress-label");
  progressBox.append(progressBar, progressLabel);
  foot.append(prev, progressBox, nextButton);

  stage.append(surface, top, body, foot);
  stage.hidden = false;
  document.body.classList.add("is-staged");

  const update = (now, opts) => {
    const occ = occurrence(ev, now);
    if (occ.past) {
      clock.update(parts(now - occ.at, true), opts);
      when.textContent = `Since ${fmt.long(occ, now)}`;
      setBar(progressBar, 1);
      progressLabel.textContent = "Done";
    } else {
      clock.update(remaining(occ, now), opts);
      when.textContent = fmt.long(occ, now);
      const p = progress(occ, now);
      setBar(progressBar, p);
      progressLabel.textContent = `${Math.floor(p * 100)}% of the wait behind you`;
    }
  };
  const now = new Date();
  update(now, { animate: false });
  stageLive = { id: ev.id, update };

  if (!wasOpen && !replace) {
    const lift = motionMs("--motion-lift");
    if (lift && openedFrom) liftFrom(surface, openedFrom, lift * 0.8);
    if (lift) {
      enter(body, lift * 0.25, 460);
      enter(foot, lift * 0.35, 460);
      top.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 300, delay: lift * 0.3, fill: "backwards" });
    }
    stage.focus({ preventScroll: true });
  } else if (wasOpen && !replace) {
    const lift = motionMs("--motion-base");
    if (lift) body.animate([{ opacity: 0 }, { opacity: 1 }], { duration: lift, easing: EASE_OUT });
  }
  openedFrom = null;
}

function step(delta) {
  const list = ordered();
  const index = list.findIndex((e) => e.ev.id === stageLive?.id);
  const target = list[index + delta];
  if (target) location.replace(`#/event/${encodeURIComponent(target.ev.id)}`);
}

function hideStage() {
  if (stage.hidden) return;
  stage.hidden = true;
  stage.replaceChildren();
  stageLive = null;
  document.body.classList.remove("is-staged");
  if (document.fullscreenElement && enteredFullscreen) document.exitFullscreen().catch(() => {});
  enteredFullscreen = false;
  if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
  opener = null;
}

function closeStage() {
  if (pushed) history.back();
  else location.replace(lastScreen);
}

// Routes: #/ the wall, #/since the past, #/event/<id> one event full screen.

function route() {
  const match = /^#\/event\/(.+)$/.exec(location.hash);
  if (match) {
    openStage(decodeURIComponent(match[1]));
    return;
  }
  pushed = false;
  hideStage();
  const since = location.hash === "#/since";
  lastScreen = since ? "#/since" : "#/";
  $("#wall-screen").hidden = since;
  $("#since-screen").hidden = !since;
  for (const tab of document.querySelectorAll(".tab")) {
    if ((tab.dataset.tab === "since") === since) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  }
}

// The clock

const nowLabel = $(".now");

function tick(animate) {
  const now = new Date();
  const next = classify(now);
  if (next.signature !== view.signature) transition(next, now);
  else for (const update of live) update(now, { animate });
  stageLive?.update(now, { animate });
  const label = fmt.today(now);
  if (nowLabel.textContent !== label) nowLabel.textContent = label;
  schedule();
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(() => tick(true), 1000 - (Date.now() % 1000) + 8);
}

// Start

function themeColor() {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = getComputedStyle(root).getPropertyValue("--color-bg").trim();
}

function start() {
  document.title = title;
  $(".brand-name").textContent = title;
  if (window.CSS && typeof CSS.registerProperty === "function") root.classList.add("mesh-live");
  const accent = getComputedStyle(root).getPropertyValue("--color-accent").trim();
  if (/^#[0-9a-f]{6}$/i.test(accent)) {
    for (const [name, value] of Object.entries(eventTokens(accent))) root.style.setProperty(name, value);
  }
  themeColor();
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeColor);

  const now = new Date();
  nowLabel.textContent = fmt.today(now);
  firstLoad(now);
  route();
  schedule();

  window.addEventListener("hashchange", route);
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#/event/"]');
    if (!link) return;
    opener = link;
    openedFrom = link.getBoundingClientRect();
    pushed = stage.hidden;
  });
  document.addEventListener("keydown", (event) => {
    if (stage.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeStage();
    } else if (event.key === "ArrowLeft") step(-1);
    else if (event.key === "ArrowRight") step(1);
    else if (event.key === "Tab") {
      const focusable = [...stage.querySelectorAll("button:not(:disabled)")];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement && enteredFullscreen) {
      enteredFullscreen = false;
      if (!stage.hidden) closeStage();
    }
  });
  // The seconds run only while the page is visible; coming back shows the time at once, without a cascade.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      clearTimeout(timer);
      timer = 0;
    } else {
      tick(false);
    }
  });
}

start();
