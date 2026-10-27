// The plant sheet: its ring, light and room, notes, a watering on another day, and the water log.
import { ago, fmt, inputDate, standing } from "./time.js";
import { removeWatering, addWatering, lastWatering } from "./store.js";
import { setFill } from "./plants.js";

const $ = (id) => document.getElementById(id);
let ctx = null;
let openId = null;
let saveTimer = 0;

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function setupSheet(context) {
  ctx = context;
  const dialog = $("sheet");
  $("sheet-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    flushNotes();
    const card = document.querySelector(`.card[data-id="${CSS.escape(openId ?? "")}"] .card-open`);
    openId = null;
    card?.focus({ preventScroll: true });
  });
  $("sheet-notes").addEventListener("input", () => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flushNotes, 400);
  });
  $("log-add").addEventListener("submit", (event) => {
    event.preventDefault();
    const value = $("log-date").value;
    if (!openId || !value) return;
    const [y, m, d] = value.split("-").map(Number);
    const when = new Date(y, m - 1, d, 9, 0, 0).getTime();
    const now = Date.now();
    addWatering(ctx.state.log, openId, ctx.sameDay(when, now) ? now : Math.min(when, now), ctx.sameDay);
    ctx.logChanged();
  });
  $("sheet-water").addEventListener("click", () => {
    if (openId) ctx.water(openId, $("sheet-ring").querySelector(".ring"));
  });
  $("sheet-log").addEventListener("click", (event) => {
    const button = event.target.closest(".log-remove");
    if (!button || !openId) return;
    removeWatering(ctx.state.log, openId, button.dataset.when);
    ctx.logChanged();
  });
}

function flushNotes() {
  clearTimeout(saveTimer);
  if (!openId) return;
  const text = $("sheet-notes").value;
  const plant = ctx.plantById(openId);
  if (text === (ctx.state.notes[openId] ?? plant.notes)) return;
  ctx.state.notes[openId] = text;
  ctx.saveNotes();
}

export function openSheet(id) {
  const plant = ctx.plantById(id);
  if (!plant) return;
  openId = id;
  $("sheet-ring").innerHTML = `<div class="ring-wrap">${ctx.ringMarkup(plant)}</div>`;
  $("sheet-name").textContent = plant.name;
  $("sheet-notes").value = ctx.state.notes[id] ?? plant.notes;
  $("log-date").max = inputDate(Date.now());
  $("log-date").value = inputDate(Date.now() - 86400000);
  refreshSheet();
  $("sheet").showModal();
}

export function refreshSheet() {
  if (!openId) return;
  const plant = ctx.plantById(openId);
  const now = Date.now();
  const last = lastWatering(ctx.state.log, openId);
  const info = standing(last, plant.intervalDays, now);
  const ring = $("sheet-ring");
  setFill(ring, info.f);
  ring.classList.toggle("is-droopy", info.state === "thirsty");

  const kind = plant.type ? `${plant.type.charAt(0).toUpperCase()}${plant.type.slice(1)}, ` : "";
  $("sheet-kind").textContent = `${kind}every ${plant.intervalDays === 1 ? "day" : `${plant.intervalDays} days`}`;
  $("sheet-status").textContent = info.next ? `${info.text}. ${info.next}.` : info.text;
  $("sheet-status").classList.toggle("is-thirsty", info.state === "thirsty");
  const done = info.state === "fresh";
  $("sheet-water").dataset.done = String(done);
  $("sheet-water").textContent = done ? "Watered today" : "Watered";

  const facts = [
    ["Room", plant.room],
    ["Light", plant.light || "Any light"],
    ["Last watered", `${fmt.short(last)}, ${ago(last, now)}`],
    ["Next", info.state === "thirsty" ? "Now" : fmt.long(info.due)],
  ];
  $("sheet-facts").innerHTML = facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");

  const list = [...(ctx.state.log[openId] ?? [])].reverse();
  $("sheet-log").innerHTML = list.length
    ? list
        .slice(0, 30)
        .map(
          (iso) =>
            `<li><span><span class="log-when">${esc(fmt.long(Date.parse(iso)))}</span><span class="log-ago">${esc(ago(Date.parse(iso), now))}</span></span>${
              list.length > 1 ? `<button class="log-remove" type="button" data-when="${esc(iso)}" aria-label="Remove ${esc(fmt.long(Date.parse(iso)))}">Remove</button>` : ""
            }</li>`,
        )
        .join("")
    : `<li class="log-empty">No waterings yet.</li>`;
}
