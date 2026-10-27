// Markup for the week grid, the grocery list, shop mode, the meal sheet, and the two printed pages.
import { escapeHtml as h, longRange, minutesText, quantity, keyOf } from "./plan.js";

const ARC_FULL = 60; // a full ring is an hour of cooking
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function arc(minutes, size) {
  const frac = Math.max(4, Math.min(100, Math.round((minutes / ARC_FULL) * 100)));
  return `<span class="arc arc-${size}" aria-hidden="true" data-arc="${frac}">
    <svg viewBox="0 0 40 40"><circle class="arc-track" cx="20" cy="20" r="16"/>
    <circle class="arc-fill" cx="20" cy="20" r="16" pathLength="100" stroke-dasharray="${frac} 100" transform="rotate(-90 20 20)"/></svg>
    <span class="arc-num">${minutes}</span></span>`;
}

// One row per ingredient; the rows that do not fit the tile are left out whole, never cut through.
function ingredientRows(meal) {
  const ings = meal.ingredients || [];
  if (!ings.length) return `<span class="tile-ings"><span class="ing"><span class="ing-n">From the fridge</span></span></span>`;
  return `<span class="tile-ings">${ings.map((i) => `<span class="ing"><span class="ing-a">${h(quantity(i.amount, (i.unit || "").trim().toLowerCase()))}</span>
    <span class="ing-n">${h(i.name.trim())}</span></span>`).join("")}</span>`;
}

function tile(day, { slot, meal, edge }) {
  const where = `${day.long} ${slot}`;
  if (!meal) {
    return `<button class="tile tile-empty" type="button" data-day="${day.index}" data-slot="${h(slot)}" aria-label="${h(where)}, open">
      <span class="tile-slot">${h(cap(slot))}</span><span class="empty-word">${h(cap(slot))}</span></button>`;
  }
  const minutes = meal.minutes ?? 0;
  return `<button class="tile" type="button" data-edge="${edge}" data-day="${day.index}" data-slot="${h(slot)}"
      aria-label="${h(`${where}: ${meal.name}, ${minutesText(minutes)}`)}">
    <span class="tile-kicker"><span class="tile-slot">${h(cap(slot))}</span><span class="tile-cuisine">${h(meal.cuisine || "")}</span></span>
    <span class="tile-name">${h(meal.name)}</span>
    ${ingredientRows(meal)}
    ${arc(minutes, "sm")}
  </button>`;
}

export function track(week, slots) {
  const labels = slots.map((s) => `<span class="slot-label">${h(cap(s))}</span>`).join("");
  const days = week.days.map((day) => `
    <div class="day${day.isToday ? " is-today" : ""}" data-day="${day.index}" role="group" aria-label="${h(`${day.long}, ${day.month} ${day.date}`)}">
      <div class="day-head"><span class="day-name">${day.short}</span><span class="day-date">${day.date}</span></div>
      ${day.meals.map((m) => tile(day, m)).join("")}
    </div>`).join("");
  return `<div class="week-track" data-week="${week.weekOf}"><div class="slot-labels" aria-hidden="true"><span class="corner"></span>${labels}</div>${days}</div>`;
}

export function strip(week, active) {
  return week.days.map((d) => `<button class="strip-day${d.index === active ? " is-active" : ""}" type="button" role="tab"
    aria-selected="${d.index === active}" data-goto="${d.index}"><span>${d.short.charAt(0)}</span><b>${d.date}</b></button>`).join("");
}

export function legend(week) {
  const seen = new Map();
  for (const d of week.days) for (const { meal, edge } of d.meals) if (meal && meal.cuisine && !seen.has(meal.cuisine)) seen.set(meal.cuisine, edge);
  return [...seen].map(([c, e]) => `<li data-edge="${e}">${h(c)}</li>`).join("");
}

function box() {
  return `<svg class="box" viewBox="0 0 24 24" aria-hidden="true"><rect class="box-frame" x="2.5" y="2.5" width="19" height="19" rx="4"/>
    <path class="box-check" d="M6.8 12.4 10.4 16 17.4 8.4" pathLength="1"/></svg>`;
}

function item(it, checked) {
  return `<li><button class="item${checked ? " is-checked" : ""}" type="button" role="checkbox" aria-checked="${checked}" data-key="${h(it.key)}">
    ${box()}<span class="item-name"><span class="item-label">${h(it.name)}</span></span>
    <span class="item-qty">${it.lines.map((l) => `<span>${h(l)}</span>`).join("")}</span></button></li>`;
}

function aisles(list, checks) {
  return list.groups.map((g) => {
    const left = g.items.filter((it) => !checks.has(it.key)).length;
    return `<section class="aisle" data-aisle="${h(g.aisle)}">
      <h3 class="aisle-head"><span>${h(g.aisle)}</span><span class="count" data-count="${h(g.aisle)}" aria-label="${left} left"><span class="num">${left}</span></span></h3>
      <ul class="items">${g.items.map((it) => item(it, checks.has(it.key))).join("")}</ul></section>`;
  }).join("");
}

function leftOf(list, checks) {
  let n = 0;
  for (const g of list.groups) for (const it of g.items) if (!checks.has(it.key)) n += 1;
  return n;
}

export function listPanel(week, people, checks) {
  const left = leftOf(week.list, checks);
  return `<div class="list-head">
      <div><h2 class="panel-title">Grocery list</h2>
      <p class="panel-meta"><span class="count" data-count="all"><span class="num">${left}</span></span> of ${week.list.count} to buy, for ${people}</p></div>
    </div>
    <div class="list-scroll">${aisles(week.list, checks)}</div>`;
}

export function shop(week, checks) {
  const left = leftOf(week.list, checks);
  return `<div class="shop-head">
      <div><h2 class="panel-title">Shop</h2>
      <p class="panel-meta"><span class="count" data-count="all"><span class="num">${left}</span></span> of ${week.list.count} left for ${h(week.name.replace(/^Week of /, "the week of "))}</p></div>
      <button class="btn" type="button" data-action="clear">Empty the cart</button>
    </div>
    <div class="shop-cols">${aisles(week.list, checks)}</div>`;
}

export function sheet(week, dayIndex, slot, pantry) {
  const day = week.days[dayIndex];
  const { meal, edge } = day.meals.find((m) => m.slot === slot);
  const close = `<button class="icon-btn sheet-close" type="button" data-action="close" aria-label="Close">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/></svg></button>`;
  if (!meal) {
    return `${close}<p class="sheet-when">${day.long}, ${day.month} ${day.date}</p>
      <h2 class="sheet-name" id="sheet-name">${h(cap(slot))} is open</h2>
      <p class="sheet-note">Tell your agent what you would like here and it adds the meal and its groceries.</p>`;
  }
  const rows = (meal.ingredients || []).map((i) => {
    const home = pantry.has(keyOf(i.name));
    return `<li${home ? ' class="is-pantry"' : ""}><span class="ing-qty">${h(quantity(i.amount, (i.unit || "").toLowerCase()))}</span>
      <span class="ing-name">${h(i.name)}</span><span class="ing-aisle">${home ? "in the pantry" : h(i.aisle)}</span></li>`;
  }).join("");
  return `${close}<div class="sheet-top" data-edge="${edge}">
      <div><p class="sheet-when">${day.long} ${h(slot)}, ${day.month} ${day.date}</p>
      <h2 class="sheet-name" id="sheet-name">${h(meal.name)}</h2>
      <p class="sheet-facts"><span class="sheet-cuisine">${h(meal.cuisine || "")}</span><span>${minutesText(meal.minutes ?? 0)}</span></p></div>
      ${arc(meal.minutes ?? 0, "lg")}
    </div>
    ${rows ? `<ul class="sheet-ings">${rows}</ul>` : `<p class="sheet-note">Nothing to buy: it comes from the fridge.</p>`}`;
}

export function printPages(week, slots, people, pantryNames) {
  const head = slots.map((s) => `<span class="pg-slot">${h(cap(s))}</span>`).join("");
  const cols = week.days.map((d) => `<div class="pg-day"><div class="pg-day-head"><b>${d.long}</b><span>${d.month.slice(0, 3)} ${d.date}</span></div>
    ${d.meals.map(({ slot, meal, edge }) => meal
      ? `<div class="pg-tile" data-edge="${edge}">${arc(meal.minutes ?? 0, "sm")}<span class="pg-name">${h(meal.name)}</span><span class="pg-cuisine">${h(meal.cuisine || "")}</span></div>`
      : `<div class="pg-tile pg-empty"><span>${h(cap(slot))}</span></div>`).join("")}</div>`).join("");
  const groups = week.list.groups.map((g) => `<section class="pg-aisle"><h3>${h(g.aisle)}</h3><ul>${g.items.map((it) =>
    `<li><span class="pg-box" aria-hidden="true"></span><span class="pg-item">${h(it.name)}</span><span class="pg-qty">${it.lines.map(h).join(", ")}</span></li>`).join("")}</ul></section>`).join("");
  const pantry = pantryNames.length ? `<p class="pg-pantry">Already in the kitchen: ${pantryNames.map(h).join(", ")}.</p>` : "";
  return `<section class="page page-week"><header class="pg-head"><h1>${h(week.name)}</h1><p>${longRange(week.weekOf)}, for ${people}</p></header>
      <div class="pg-grid"><div class="pg-slots"><span></span>${head}</div>${cols}</div></section>
    <section class="page page-list"><header class="pg-head"><h1>Groceries</h1><p>${h(week.name)}, ${week.list.count} items, for ${people}</p></header>
      <div class="pg-cols">${groups}</div>${pantry}</section>`;
}
