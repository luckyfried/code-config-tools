// The year grid: one button per day placed by month and date, the opening stagger, and the ribbon of months.
import { SHORT_MONTHS, MONTHS, yearDays, daysIn, iso, longDate } from "./dates.js";

const LABEL_DAYS = new Set([1, 5, 10, 15, 20, 25, 30]);
const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function createGrid(gridEl, ribbonEl, moods) {
  let cells = new Map();
  let segs = [];

  function label(day, entry) {
    const mood = entry ? moods[entry.mood - 1].label : "No mood yet";
    return `${longDate(day)}, ${mood}${entry && entry.note ? `. ${entry.note}` : ""}`;
  }

  function paint(cell, entry) {
    if (entry) cell.dataset.mood = String(entry.mood);
    else delete cell.dataset.mood;
    cell.setAttribute("aria-label", label(cell.dataset.day, entry));
  }

  function render(year, days, today) {
    const frag = document.createDocumentFragment();
    const thisMonth = today.startsWith(String(year)) ? Number(today.slice(5, 7)) - 1 : -1;
    const thisDate = thisMonth >= 0 ? Number(today.slice(8, 10)) : -1;

    SHORT_MONTHS.forEach((name, m) => {
      const el = document.createElement("div");
      el.className = "m-label" + (m === thisMonth ? " is-now" : "");
      el.textContent = name;
      el.style.setProperty("--m-line", String(m + 2));
      el.setAttribute("aria-hidden", "true");
      frag.append(el);
    });
    for (let d = 1; d <= 31; d++) {
      const el = document.createElement("div");
      el.className = "d-label" + (d === thisDate ? " is-now" : "");
      el.textContent = LABEL_DAYS.has(d) || d === thisDate ? String(d) : "";
      el.style.setProperty("--d-line", String(d + 1));
      el.setAttribute("aria-hidden", "true");
      frag.append(el);
    }

    cells = new Map();
    for (const { day, month, date } of yearDays(year)) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.dataset.day = day;
      cell.tabIndex = -1;
      cell.style.setProperty("--m-line", String(month + 2));
      cell.style.setProperty("--d-line", String(date + 1));
      if (day > today) {
        cell.dataset.future = "";
        cell.setAttribute("aria-disabled", "true");
      }
      if (day === today) cell.classList.add("is-today");
      paint(cell, days[day]);
      cells.set(day, cell);
      frag.append(cell);
    }
    gridEl.replaceChildren(frag);
    gridEl.setAttribute("aria-label", `${year}, one square a day`);

    const segFrag = document.createDocumentFragment();
    segs = MONTHS.map((name, m) => {
      const seg = document.createElement("div");
      seg.className = "seg";
      seg.style.setProperty("--m-line", String(m + 2));
      const bar = document.createElement("div");
      bar.className = "seg-bar";
      const caption = document.createElement("span");
      caption.className = "seg-name";
      caption.textContent = SHORT_MONTHS[m];
      seg.append(bar, caption);
      segFrag.append(seg);
      return bar;
    });
    ribbonEl.replaceChildren(segFrag);
    ribbon(year, days);
    return cells;
  }

  // Each month as a gradient of its moods, from the roughest to the best, in proportion.
  function ribbon(year, days) {
    segs.forEach((bar, m) => {
      const counts = [0, 0, 0, 0, 0];
      let n = 0;
      for (let d = 1; d <= daysIn(year, m); d++) {
        const e = days[iso(year, m, d)];
        if (e) {
          counts[e.mood - 1]++;
          n++;
        }
      }
      if (!n) {
        bar.style.setProperty("--ribbon-stops", "transparent, transparent");
        return;
      }
      const stops = [];
      let at = 0;
      counts.forEach((c, i) => {
        if (!c) return;
        const from = (at / n) * 100;
        const to = ((at + c) / n) * 100;
        const color = `var(--mood-${i + 1})`;
        stops.push(`${color} ${(from + Math.min(8, (to - from) / 3)).toFixed(1)}%`, `${color} ${(to - Math.min(8, (to - from) / 3)).toFixed(1)}%`);
        at += c;
      });
      bar.style.setProperty("--ribbon-stops", stops.join(", "));
    });
  }

  // Filled days pop in from zero scale, 2 ms apart down each month in turn, the whole opening taking one second.
  function stagger() {
    if (reduceMotion()) return Promise.resolve();
    const filled = [...cells.values()].filter((c) => c.dataset.mood);
    const step = 2;
    const duration = Math.max(260, 1000 - step * filled.length);
    const runs = filled.map((cell, i) =>
      cell.animate(
        [{ transform: "scale(0)" }, { transform: "scale(1.12)", offset: 0.7 }, { transform: "scale(1)" }],
        { duration, delay: i * step, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" },
      ),
    );
    segs.forEach((bar, m) =>
      bar.animate([{ transform: "scale(0, 0)", opacity: 0 }, { transform: "scale(1, 1)", opacity: 1 }], {
        duration: 420,
        delay: 420 + m * 45,
        easing: "cubic-bezier(0.23, 1, 0.32, 1)",
        fill: "backwards",
      }),
    );
    return Promise.all(runs.map((a) => a.finished.catch(() => {})));
  }

  function pop(cell) {
    if (reduceMotion()) return;
    cell.animate([{ transform: "scale(1.6)" }, { transform: "scale(0.86)", offset: 0.45 }, { transform: "scale(1)" }], {
      duration: 360,
      easing: "cubic-bezier(0.23, 1, 0.32, 1)",
    });
  }

  return { render, paint, ribbon, stagger, pop, cells: () => cells };
}
