// Subscription Wall: reads window.__APP_CONFIG__ (the inputs) and window.__APP_DATA__ (what run.py worked out from
// them), draws the three screens, and keeps the what-if toggles in memory only; a reload resets them.

import { moneyFormat, chargeWindow, plural, todayLocal } from "./format.js";
import { createOdometer } from "./odometer.js";
import { createWall } from "./wall.js";
import { createCalendar } from "./calendar.js";
import { createCategories } from "./categories.js";
import { createYearStrip } from "./yearstrip.js";

const config = window.__APP_CONFIG__ || {};
const data = window.__APP_DATA__;
const $ = (id) => document.getElementById(id);
const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function start() {
  const subs = data.subscriptions;
  const money = moneyFormat(data.currency || config.currency || "USD");
  const today = todayLocal();
  const off = new Set();
  let sort = data.sort === "renewal" ? "renewal" : "cost";

  const yearly = subs.reduce((sum, s) => sum + s.yearlyCents, 0);
  const headline = $("headline");
  const stated = Math.round(Number(headline.dataset.yearly) * 100);
  if (headline.dataset.yearly && stated !== yearly) {
    console.error(`The headline total ${headline.dataset.yearly} does not match the subscriptions, ${yearly / 100}.`);
  }

  const odo = createOdometer($("odo"), money.cents);
  const totalText = $("total-text");

  const wall = createWall({ root: $("wall"), subs, money, today, onToggle: toggle });
  const calendar = createCalendar({
    strip: $("strip"), scroller: $("strip-scroll"), detail: $("month-detail"), note: $("calendar-note"), subs, money, today,
  });
  const year = createYearStrip({
    root: $("year-strip"), caption: $("year-caption"), subs, money, today,
    onPick: (i) => { calendar.select(i); location.hash = "calendar"; },
  });
  const cats = createCategories({ root: $("cats"), note: $("category-note"), subs, categories: data.categories, money });

  $("wall-empty").hidden = subs.length > 0;

  function idsFor(mode) {
    const list = subs.slice();
    if (mode === "renewal") {
      const nextOf = new Map(subs.map((s) => [s.id, chargeWindow(s, today).next]));
      list.sort((a, b) => nextOf.get(a.id) - nextOf.get(b.id) || a.rank - b.rank);
    } else {
      list.sort((a, b) => a.rank - b.rank);
    }
    return list.map((s) => s.id);
  }

  function setSort(mode, animate) {
    sort = mode;
    document.querySelectorAll("[data-sort]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sort === mode)));
    wall.reorder(idsFor(mode), animate && !reduce());
  }

  function headlineCopy(kept) {
    const label = $("headline-label");
    const sub = $("headline-sub");
    const n = off.size;
    const left = subs.length - n;
    totalText.textContent = `${money.cents(kept)} a year`;
    if (n === 0) {
      label.textContent = "Your subscriptions cost";
      const strong = document.createElement("strong");
      strong.textContent = plural(subs.length, "subscription", "subscriptions");
      sub.replaceChildren(strong, `, about ${money.round(kept / 12)} a month.`);
    } else {
      label.textContent = `If you cancel ${n}, your subscriptions cost`;
      const saves = document.createElement("span");
      saves.className = "saves";
      saves.textContent = `${money.cents(yearly - kept)} a year`;
      sub.replaceChildren("You keep ", saves, `. ${plural(left, "subscription", "subscriptions")} left, about ${money.round(kept / 12)} a month.`);
    }
    $("keep-all").hidden = n === 0;
  }

  function refresh(animateTotal) {
    const kept = subs.reduce((sum, s) => sum + (off.has(s.id) ? 0 : s.yearlyCents), 0);
    headlineCopy(kept);
    calendar.update(off);
    year.update(off);
    cats.update(off);
    if (animateTotal) odo.to(kept, 700);
    return kept;
  }

  function flip(id) {
    const now = !off.has(id);
    if (now) off.add(id); else off.delete(id);
    wall.setOff(id, now);
    refresh(true);
  }

  function toggle(id) {
    stopPreview();
    flip(id);
  }

  $("keep-all").addEventListener("click", () => {
    stopPreview();
    for (const id of Array.from(off)) wall.setOff(id, false);
    off.clear();
    refresh(true);
    document.querySelector(".seg-btn[aria-pressed='true']")?.focus();
  });

  document.querySelectorAll("[data-sort]").forEach((b) => {
    b.addEventListener("click", () => { if (b.dataset.sort !== sort) setSort(b.dataset.sort, true); });
  });

  const screens = { wall: $("screen-wall"), calendar: $("screen-calendar"), category: $("screen-category") };
  function route() {
    const name = location.hash.slice(1);
    const current = screens[name] ? name : "wall";
    for (const [key, node] of Object.entries(screens)) node.hidden = key !== current;
    document.querySelectorAll(".tab").forEach((t) => {
      if (t.dataset.screen === current) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
    });
    if (current === "calendar") calendar.center();
    if (current === "category") cats.reveal();
  }
  addEventListener("hashchange", () => { route(); scrollTo({ top: 0 }); });

  setSort(sort, false);
  refresh(false);
  route();
  odo.rollUp(yearly, reduce() ? 0 : 1400);
  wall.fillBars(reduce());
  year.reveal(reduce());
  preview();

  // Once per visit, a few seconds in, the most expensive charge plays its own "What if I cancel?" for three seconds:
  // its tile goes gray, the total counts down, and the year strip drops its dots. A touch, click, or key keeps what is
  // on screen and ends the preview.
  function preview() {
    const top = subs.find((s) => s.rank === 1);
    let seen = true;
    try { seen = sessionStorage.getItem("subscription-wall-preview") === "1"; sessionStorage.setItem("subscription-wall-preview", "1"); } catch { seen = false; }
    if (!top || subs.length < 2 || seen || reduce()) return;
    timers.push(setTimeout(() => { flip(top.id); timers.push(setTimeout(() => { flip(top.id); stopPreview(); }, 3000)); }, 4200));
    addEventListener("pointerdown", stopPreview, { once: true });
    addEventListener("keydown", stopPreview, { once: true });
  }
}

const timers = [];
function stopPreview() {
  while (timers.length) clearTimeout(timers.pop());
}

if (data && Array.isArray(data.subscriptions)) {
  start();
} else {
  $("headline-label").textContent = "Nothing to show yet";
  $("headline-sub").textContent = "Run scripts/run.py from your project folder to write this page.";
}
