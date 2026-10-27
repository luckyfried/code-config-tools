// The year: per habit, 53 weeks by 7 days ending with this week, darker the longer a run has gone on.
// A folded row shows a 52-week strip instead; a cell under the pointer or a finger shows its date and what was done.
import { addDays, dayKey, monthName, tipDate } from "./dates.js";
import { glyph } from "./icons.js";
import { countOf, goal, isDone } from "./store.js";

const WEEKS = 53;
const WAVE_STEP = 11;
const WAVE_CELL = 420;
const LEAD = 60;

/** The run length step of a closed day: 1 day, 2 to 3, 4 to 6, a week or more. */
const runStep = (run) => (run <= 0 ? 0 : run === 1 ? 1 : run <= 3 ? 2 : run <= 6 ? 3 : 4);

function chevron() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "icon chev");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = '<path d="M6 9.5l6 6 6-6"/>';
  return svg;
}

export function createYear({ list, habits, tip, reduced, desktop }) {
  let rows = [];
  let frame = null;
  const watcher = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) if (entry.isIntersecting) play(entry.target, Number(entry.target.dataset.at || 0));
    },
    { threshold: 0.12 },
  );

  /** The 53 weeks ending with the week of `today`, as dates by column and row, for a week that starts on `weekStart`. */
  function frameOf(today, weekStart) {
    const first = weekStart === "sun" ? 0 : 1;
    const row = (today.getDay() - first + 7) % 7;
    const start = addDays(today, -row - (WEEKS - 1) * 7);
    const dates = [];
    for (let i = 0; i < WEEKS * 7; i += 1) dates.push(addDays(start, i));
    return { start, dates, todayIndex: (WEEKS - 1) * 7 + row };
  }

  /** Per day of the window, the habit's step 0 to 4, plus its runs and total. */
  function measure(data, habit, today) {
    const steps = [];
    let run = 0;
    let best = 0;
    let total = 0;
    for (let i = -LEAD; i < frame.dates.length; i += 1) {
      const date = i < 0 ? addDays(frame.start, i) : frame.dates[i];
      const key = dayKey(date);
      const closed = isDone(data, key, habit);
      run = closed ? run + 1 : 0;
      if (i < 0) continue;
      if (i > frame.todayIndex) {
        steps.push(-1);
        continue;
      }
      best = Math.max(best, run);
      if (closed && i > frame.todayIndex - 365) total += 1;
      steps.push(closed ? runStep(run) : habit.target && countOf(data, key, habit) > 0 ? 1 : 0);
    }
    let current = 0;
    const from = isDone(data, dayKey(today), habit) ? 0 : 1;
    for (let back = from; back < 4000; back += 1) {
      if (!isDone(data, dayKey(addDays(today, -back)), habit)) break;
      current += 1;
    }
    return { steps, best: Math.max(best, current), current, total };
  }

  function play(map, at) {
    if (!map.classList.contains("is-waiting")) return;
    map.dataset.at = "0";
    if (reduced()) {
      map.classList.remove("is-waiting");
      return;
    }
    map.style.setProperty("--wave-at", `${at}ms`);
    map.classList.remove("is-waiting");
    map.classList.add("is-waving");
    const done = at + (WEEKS - 1 + 6) * WAVE_STEP + WAVE_CELL + 60;
    setTimeout(() => map.classList.remove("is-waving"), done);
  }

  function build(data, today, weekStart, { opening }) {
    frame = frameOf(today, weekStart);
    watcher.disconnect();
    list.replaceChildren();
    const first = weekStart === "sun" ? 0 : 1;

    rows = habits.map((habit, h) => {
      const li = document.createElement("li");
      li.className = "habit-row is-open";
      li.style.setProperty("--hue", `var(--habit-${h + 1})`);
      for (let s = 1; s <= 4; s += 1) li.style.setProperty(`--h${s}`, `var(--heat-${h + 1}-${s})`);

      const head = document.createElement("button");
      head.type = "button";
      head.className = "row-head";
      head.setAttribute("aria-expanded", "true");
      head.setAttribute("aria-controls", `map-${habit.id}`);
      const badge = document.createElement("span");
      badge.className = "row-icon";
      badge.append(glyph(habit));
      const name = document.createElement("span");
      name.className = "row-name";
      name.textContent = habit.label;
      const stats = document.createElement("span");
      stats.className = "row-stats";
      head.append(badge, name, stats, chevron());

      const spark = document.createElement("div");
      spark.className = "spark";
      spark.setAttribute("aria-hidden", "true");
      const bars = [];
      for (let w = 1; w < WEEKS; w += 1) {
        const bar = document.createElement("i");
        spark.append(bar);
        bars.push(bar);
      }

      const scroller = document.createElement("div");
      scroller.className = "map-scroll";
      const map = document.createElement("div");
      map.className = "map";
      map.id = `map-${habit.id}`;
      map.setAttribute("role", "img");

      const months = document.createElement("div");
      months.className = "months";
      months.setAttribute("aria-hidden", "true");
      let lastLabel = -9;
      for (let w = 0; w < WEEKS; w += 1) {
        const top = frame.dates[w * 7];
        const firstOfMonth = [...Array(7).keys()].map((r) => frame.dates[w * 7 + r]).find((d) => d.getDate() === 1);
        if ((firstOfMonth || (w === 0 && top.getDate() <= 10 ? top : null)) && w - lastLabel >= 3) {
          const label = document.createElement("span");
          label.textContent = monthName(firstOfMonth || top);
          label.style.setProperty("--col", String(w + 1));
          months.append(label);
          lastLabel = w;
        }
      }

      const days = document.createElement("div");
      days.className = "days";
      days.setAttribute("aria-hidden", "true");
      for (let r = 0; r < 7; r += 1) {
        const span = document.createElement("span");
        const weekday = (first + r) % 7;
        span.textContent = weekday === 1 ? "Mon" : weekday === 3 ? "Wed" : weekday === 5 ? "Fri" : "";
        days.append(span);
      }

      const weeks = document.createElement("div");
      weeks.className = "weeks";
      const cells = [];
      for (let w = 0; w < WEEKS; w += 1) {
        const week = document.createElement("div");
        week.className = w === WEEKS - 1 ? "week is-now" : "week";
        week.style.setProperty("--c", String(w));
        for (let r = 0; r < 7; r += 1) {
          const i = w * 7 + r;
          const cell = document.createElement("i");
          cell.className = "cell";
          cell.dataset.i = String(i);
          week.append(cell);
          cells.push(cell);
        }
        weeks.append(week);
      }
      cells[frame.todayIndex].classList.add("is-today");

      map.append(months, days, weeks);
      scroller.append(map);
      li.append(head, spark, scroller);
      list.append(li);

      const row = { habit, li, head, stats, bars, map, scroller, cells };
      head.addEventListener("click", () => toggle(row));
      if (!reduced()) {
        map.classList.add("is-waiting");
        map.dataset.at = String(opening ? 240 + h * 70 : 0);
      }
      return row;
    });

    paint(data, today);
    rows.forEach((row) => {
      row.scroller.scrollLeft = row.scroller.scrollWidth;
      watcher.observe(row.map);
    });
    if (desktop()) fit();
  }

  /** Folds rows from the bottom until the year fits the screen's height, keeping at least one map open. */
  function fit() {
    const bottom = () => list.getBoundingClientRect().bottom + scrollY;
    for (let i = rows.length - 1; i > 0 && bottom() > innerHeight - 24; i -= 1) setOpen(rows[i], false);
  }

  function setOpen(row, open) {
    row.li.classList.toggle("is-open", open);
    row.head.setAttribute("aria-expanded", String(open));
    if (!open && !reduced()) {
      row.map.classList.remove("is-waving");
      row.map.classList.add("is-waiting");
      row.map.dataset.at = "0";
    }
    if (open) row.scroller.scrollLeft = row.scroller.scrollWidth;
  }

  function toggle(row) {
    setOpen(row, !row.li.classList.contains("is-open"));
  }

  /** Recolors every row from `data`. */
  function paint(data, today) {
    rows.forEach((row) => {
      const { habit } = row;
      const { steps, best, current, total } = measure(data, habit, today);
      row.cells.forEach((cell, i) => {
        const s = steps[i];
        cell.className = `cell${s > 0 ? ` s${s}` : ""}${s < 0 ? " later" : ""}${i === frame.todayIndex ? " is-today" : ""}`;
      });
      row.bars.forEach((bar, w) => {
        let closed = 0;
        for (let r = 0; r < 7; r += 1) if (steps[(w + 1) * 7 + r] > 0 && isDone(data, dayKey(frame.dates[(w + 1) * 7 + r]), habit)) closed += 1;
        const share = closed / 7;
        bar.className = closed === 0 ? "" : `s${Math.max(1, Math.ceil(share * 4))}`;
        bar.style.setProperty("--v", String(Math.max(0.12, share)));
      });
      row.stats.innerHTML = "";
      const part = (number, words, className) => {
        const span = document.createElement("span");
        if (className) span.className = className;
        const b = document.createElement("b");
        b.textContent = String(number);
        span.append(b, ` ${words}`);
        row.stats.append(span);
      };
      part(current, current === 1 ? "day running" : "days running");
      part(best, "best run", "row-stat-wide");
      part(total, "this year", "row-stat-extra");
      row.map.setAttribute(
        "aria-label",
        `${habit.label}: ${total} days in the last year, ${current} running now, the best run ${best} days.`,
      );
    });
  }

  // The tip.
  const tipDateEl = tip.querySelector(".tip-date");
  const tipList = tip.querySelector(".tip-list");
  let picked = null;
  let todayRef = null;
  let dataRef = null;

  function showTip(cell) {
    const i = Number(cell.dataset.i);
    if (!frame || i > frame.todayIndex) return hideTip();
    const date = frame.dates[i];
    const key = dayKey(date);
    tipDateEl.textContent = `${tipDate(date, todayRef)}${i === frame.todayIndex ? ", today" : ""}`;
    tipList.replaceChildren(
      ...habits.map((habit, h) => {
        const li = document.createElement("li");
        li.style.setProperty("--hue", `var(--habit-${h + 1})`);
        const count = countOf(dataRef, key, habit);
        const done = count >= goal(habit);
        li.className = done ? "is-done" : "";
        li.textContent = habit.target ? `${habit.label}, ${count} of ${habit.target}` : habit.label;
        return li;
      }),
    );
    picked?.classList.remove("is-picked");
    picked = cell;
    cell.classList.add("is-picked");
    tip.hidden = false;
    const box = cell.getBoundingClientRect();
    const width = tip.offsetWidth;
    const height = tip.offsetHeight;
    let x = box.left + box.width / 2 - width / 2;
    x = Math.max(8, Math.min(innerWidth - width - 8, x));
    let y = box.top - height - 10;
    if (y < 8) y = box.bottom + 10;
    tip.style.setProperty("--tx", `${Math.round(x)}px`);
    tip.style.setProperty("--ty", `${Math.round(y)}px`);
  }

  function hideTip() {
    tip.hidden = true;
    picked?.classList.remove("is-picked");
    picked = null;
  }

  list.addEventListener("pointerover", (event) => {
    if (event.pointerType !== "mouse") return;
    const cell = event.target.closest?.(".cell");
    if (cell) showTip(cell);
  });
  list.addEventListener("pointerout", (event) => {
    if (event.pointerType !== "mouse") return;
    if (event.target.closest?.(".cell") && !event.relatedTarget?.closest?.(".cell")) hideTip();
  });
  document.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse") return;
    const cell = event.target.closest?.(".habit-rows .cell");
    if (cell) showTip(cell);
    else hideTip();
  });
  addEventListener("scroll", hideTip, { passive: true, capture: true });
  addEventListener("resize", hideTip, { passive: true });

  return {
    build(data, today, weekStart, options = {}) {
      todayRef = today;
      dataRef = data;
      hideTip();
      build(data, today, weekStart, options);
    },
    paint(data, today) {
      todayRef = today;
      dataRef = data;
      paint(data, today);
    },
  };
}
