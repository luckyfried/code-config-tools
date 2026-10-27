// Markup for the room tabs, the cards, the fourteen-day strip, the Schedule view, and the Settings plant list.
import { drawingFor, miniMarkup, ringMarkup } from "./plants.js";
import { addDays, daysBetween, fmt, startOfDay } from "./time.js";

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const SUN = `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4"/></svg>`;
const DROP = `<svg viewBox="0 0 24 24" aria-hidden="true"><path class="icon-drop" d="M12 2.8c-.3 0-6.3 7.3-6.3 11.7a6.3 6.3 0 0 0 12.6 0C18.3 10.1 12.3 2.8 12 2.8z"/><path class="icon-check" d="M5 12.5l4.5 4.5L19 7.5"/></svg>`;

export function tabsMarkup(rooms, counts, current) {
  const tab = (id, label, n) => {
    const on = id === current;
    return `<button class="tab" role="tab" type="button" id="tab-${esc(id)}" data-room="${esc(id)}" aria-selected="${on}" aria-controls="rooms" tabindex="${on ? 0 : -1}">${esc(label)}${n ? `<span class="tab-count" aria-label="${n} thirsty">${n}</span>` : ""}</button>`;
  };
  const total = rooms.reduce((sum, r) => sum + (counts.get(r.id) ?? 0), 0);
  return tab("all", "All rooms", total) + rooms.map((r) => tab(r.id, r.name, counts.get(r.id) ?? 0)).join("");
}

/** The neutral leaf carries the plant's initial on its pot; every other drawing speaks for itself. */
export const initialFor = (plant, drawing) => (drawing === "leaf" ? esc(plant.name.trim().charAt(0).toUpperCase()) : "");

export function cardMarkup(plant) {
  const drawing = drawingFor(plant.type, plant.name);
  return `<li class="card" data-id="${esc(plant.id)}">
  <div class="ring-wrap">${ringMarkup(drawing, initialFor(plant, drawing))}</div>
  <div class="card-body">
    <h3 class="card-name"><button class="card-open" type="button" aria-haspopup="dialog">${esc(plant.name)}</button></h3>
    <p class="card-status"></p>
    <p class="card-light">${SUN}<span>${esc(plant.light || "Any light")}</span></p>
  </div>
  <button class="water" type="button" aria-label="Watered ${esc(plant.name)}">${DROP}<span>Watered</span></button>
</li>`;
}

export function roomMarkup(room, plants) {
  return `<section class="room" data-room="${esc(room.id)}" aria-labelledby="room-${esc(room.id)}">
  <div class="room-head"><h2 class="room-name" id="room-${esc(room.id)}">${esc(room.name)}</h2><span class="room-meta"></span></div>
  <ul class="cards">${plants.map(cardMarkup).join("")}</ul>
</section>`;
}

/** Every due day in the next fourteen, per plant: an overdue plant is due today, then every interval after. */
export function dueDays(plants, info, now) {
  const today = startOfDay(now);
  const end = addDays(today, 14);
  const days = Array.from({ length: 14 }, (_, i) => ({ t: addDays(today, i), items: [] }));
  for (const p of plants) {
    const { due, state } = info.get(p.id);
    let d = Math.max(startOfDay(due), today);
    let overdue = state === "thirsty" && startOfDay(due) < today;
    while (d < end) {
      days[daysBetween(today, d)]?.items.push({ plant: p, overdue });
      overdue = false;
      d = addDays(d, p.intervalDays);
    }
  }
  for (const day of days) day.items.sort((a, b) => Number(b.overdue) - Number(a.overdue) || a.plant.name.localeCompare(b.plant.name));
  return days;
}

const mini = ({ plant, overdue }) =>
  `<span class="mini${overdue ? " is-overdue" : ""}" title="${esc(plant.name)}">${miniMarkup(drawingFor(plant.type, plant.name))}</span>`;

export function daysMarkup(days, now, slots = 4) {
  return days
    .map((day, i) => {
      const shown = day.items.length > slots ? day.items.slice(0, slots - 1) : day.items;
      const more = day.items.length - shown.length;
      const names = day.items.map((x) => x.plant.name).join(", ");
      const label = `${i === 0 ? "Today" : fmt.long(day.t)}: ${names || "nothing due"}`;
      return `<li class="day${i === 0 ? " is-today" : ""}" aria-label="${esc(label)}">
  <span class="dow" aria-hidden="true">${i === 0 ? "Today" : esc(fmt.dow(day.t))}</span>
  <span class="dnum" aria-hidden="true">${new Date(day.t).getDate()}</span>
  <span class="due" aria-hidden="true">${shown.map(mini).join("")}${more ? `<span class="mini-more">+${more}</span>` : ""}</span>
</li>`;
    })
    .join("");
}

export function agendaMarkup(days, roomName) {
  const filled = days.map((d, i) => ({ ...d, i })).filter((d) => d.items.length);
  if (!filled.length) return `<li class="agenda-empty">Nothing needs water in the next two weeks.</li>`;
  return filled
    .map((day) => {
      const head = day.i === 0 ? `Today, ${fmt.monthDay(day.t)}` : day.i === 1 ? `Tomorrow, ${fmt.monthDay(day.t)}` : fmt.long(day.t);
      const rows = day.items
        .map(({ plant, overdue }) => {
          const tag = overdue ? "Overdue" : `Every ${plant.intervalDays === 1 ? "day" : `${plant.intervalDays} days`}`;
          return `<li class="agenda-row">${mini({ plant, overdue })}<div><p class="agenda-name">${esc(plant.name)}</p><p class="agenda-sub">${esc(roomName(plant.room))}</p></div><span class="agenda-tag${overdue ? " is-overdue" : ""}">${tag}</span></li>`;
        })
        .join("");
      return `<li class="agenda-day${day.i === 0 ? " is-today" : ""}"><h3>${esc(head)}</h3><ul class="agenda-rows">${rows}</ul></li>`;
    })
    .join("");
}

export function plantListMarkup(plants, roomName) {
  return plants
    .map((p) => {
      const every = p.intervalDays === 1 ? "Every day" : `Every ${p.intervalDays} days`;
      return `<li>${mini({ plant: p, overdue: false })}<div><p class="agenda-name">${esc(p.name)}</p><p class="agenda-sub">${esc(roomName(p.room))}</p></div><span class="agenda-sub">${every}</span></li>`;
    })
    .join("");
}
