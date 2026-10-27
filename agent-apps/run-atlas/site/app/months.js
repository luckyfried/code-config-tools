// The Months screen: every year as twelve bars, with the year's totals beside them.
import * as f from "./format.js";

export function renderMonths(root, data, { units, sport, latest, sportLabel }) {
  const pool = data.activities.filter((a) => a.date && (sport === "all" || a.sport === sport));
  const metersOf = (key) => {
    const slot = data.months[key];
    if (!slot) return 0;
    return Object.entries(slot).reduce((s, [k, m]) => s + (sport === "all" || k === sport ? m : 0), 0);
  };
  const years = data.years;
  const allMonths = years.flatMap((y) => Array.from({ length: 12 }, (_, m) => metersOf(`${y}-${String(m + 1).padStart(2, "0")}`)));
  const max = Math.max(1, ...allMonths);
  const [ly, lm, ld] = latest ? latest.split("-").map(Number) : [0, 0, 0];

  const head = document.createElement("div");
  head.className = "months-head";
  const title = document.createElement("h2");
  title.className = "months-title";
  title.textContent = sport === "all" ? "Distance by month" : `${sportLabel[sport]} by month`;
  head.append(title);

  // How this year stands against last year on the same day.
  if (years.length > 1 && years[0] === ly) {
    const cut = `${String(lm).padStart(2, "0")}-${String(ld).padStart(2, "0")}`;
    const upTo = (y) => pool.filter((a) => a.date.startsWith(String(y)) && a.date.slice(5) <= cut).reduce((s, a) => s + a.distance, 0);
    const now = upTo(ly);
    const before = upTo(ly - 1);
    if (before > 0) {
      const diff = now - before;
      const p = document.createElement("p");
      p.className = "months-compare";
      p.textContent = `${f.distance(Math.abs(diff), units, 0)} ${units} ${diff >= 0 ? "ahead of" : "behind"} ${ly - 1} on ${f.monthShort(lm - 1)} ${ld}`;
      head.append(p);
    }
  }

  const list = document.createElement("div");
  list.className = "years";
  years.forEach((y, yi) => {
    const items = pool.filter((a) => a.date.startsWith(String(y)));
    const meters = items.reduce((s, a) => s + a.distance, 0);
    const moving = items.reduce((s, a) => s + (a.duration || 0), 0);
    const gain = items.reduce((s, a) => s + a.gain, 0);
    const longest = items.reduce((b, a) => (!b || a.distance > b.distance ? a : b), null);

    const card = document.createElement("section");
    card.className = "year";
    card.setAttribute("aria-label", String(y));

    const side = document.createElement("div");
    side.className = "year-side";
    const name = document.createElement("h3");
    name.className = "year-name";
    name.textContent = String(y);
    const total = document.createElement("p");
    total.className = "year-total";
    total.innerHTML = `<span class="num"></span><span class="unit"></span>`;
    total.firstChild.textContent = f.distance(meters, units, 0);
    total.lastChild.textContent = units;
    const facts = document.createElement("dl");
    facts.className = "year-facts";
    const c = f.climb(gain, units);
    const rows = [
      [items.length === 1 ? "Activity" : "Activities", f.count(items.length)],
      ["Moving time", f.hours(moving)],
      ["Climb", `${c.value} ${c.unit}`],
      ["Longest", longest ? `${f.distance(longest.distance, units)} ${units}` : "None"],
    ];
    for (const [k, v] of rows) {
      const wrap = document.createElement("div");
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      dd.textContent = v;
      wrap.append(dt, dd);
      facts.append(wrap);
    }
    side.append(name, total, facts);

    const chart = document.createElement("div");
    chart.className = "year-bars";
    chart.setAttribute("role", "list");
    for (let m = 0; m < 12; m += 1) {
      const value = metersOf(`${y}-${String(m + 1).padStart(2, "0")}`);
      const future = y > ly || (y === ly && m + 1 > lm);
      const col = document.createElement("div");
      col.className = "ybar";
      col.setAttribute("role", "listitem");
      if (future) col.classList.add("is-future");
      if (y === ly && m + 1 === lm) col.classList.add("is-now");
      col.style.setProperty("--h", (value / max).toFixed(4));
      col.style.setProperty("--i", String(yi * 12 + m));
      const v = document.createElement("span");
      v.className = "ybar-value";
      v.textContent = value ? f.distance(value, units, 0) : "";
      const fill = document.createElement("span");
      fill.className = "ybar-fill";
      const label = document.createElement("span");
      label.className = "ybar-label";
      label.textContent = f.monthShort(m);
      col.setAttribute("aria-label", `${f.monthLong(m)} ${y}: ${value ? `${f.distance(value, units)} ${units}` : "nothing recorded"}`);
      col.append(v, fill, label);
      chart.append(col);
    }
    card.append(side, chart);
    list.append(card);
  });

  root.replaceChildren(head, list);
}
