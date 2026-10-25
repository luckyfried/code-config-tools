// The year ahead: twelve month columns starting with this one, each a stack of dots (one per charge, sized by its
// amount), the heaviest month lifted with a label, and the list of charges for the month picked.

import { bright, chargeWindow, fmtMonthLong, fmtMonthShort, fmtShort, isoDay, plural, step } from "./format.js";

const SVG = "http://www.w3.org/2000/svg";
const COL_W = 72;
const STACK_H = 260;
const GAP = 4;
const D_MAX = 60;
const D_MIN = 9;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function buildMonths(subs, today) {
  const months = [];
  for (let i = 0; i < 12; i += 1) {
    const start = new Date(today.getFullYear(), today.getMonth() + i, 1, 12);
    months.push({ start, charges: [] });
  }
  const end = new Date(today.getFullYear(), today.getMonth() + 12, 1, 12);
  const first = months[0].start;
  for (const sub of subs) {
    const { prev } = chargeWindow(sub, today);
    for (let n = 0, date = prev; date < end && n < 80; n += 1, date = step(prev, sub.every, sub.day, n)) {
      if (date < first) continue;
      const idx = (date.getFullYear() - first.getFullYear()) * 12 + date.getMonth() - first.getMonth();
      months[idx].charges.push({ sub, date, past: date < today, cents: Math.round(sub.amount * 100) });
    }
  }
  for (const m of months) m.charges.sort((a, b) => a.date - b.date || b.cents - a.cents);
  return months;
}

export function createCalendar({ strip, scroller, detail, note, subs, money, today }) {
  const months = buildMonths(subs, today);
  const maxAmount = Math.max(1, ...subs.map((s) => s.amount));
  let k = D_MAX / Math.sqrt(maxAmount);
  const diameter = (amount) => Math.max(D_MIN, k * Math.sqrt(amount));

  // Packs a month's dots into rows as wide as the column, oldest at the bottom, and returns each dot's place.
  function pack(charges) {
    const rows = [];
    let row = null;
    for (const c of charges) {
      const d = diameter(c.sub.amount);
      if (!row || row.width + GAP + d > COL_W) {
        row = { width: d, height: d, dots: [{ c, d }] };
        rows.push(row);
      } else {
        row.width += GAP + d;
        row.height = Math.max(row.height, d);
        row.dots.push({ c, d });
      }
    }
    const placed = [];
    let base = 0;
    rows.forEach((r, i) => {
      if (i) base += GAP;
      let x = (COL_W - r.width) / 2;
      for (const { c, d } of r.dots) {
        placed.push({ c, d, cx: x + d / 2, fromBottom: base + r.height / 2 });
        x += d + GAP;
      }
      base += r.height;
    });
    return { placed, height: base };
  }

  while (k > 0.5 && Math.max(...months.map((m) => pack(m.charges).height)) > STACK_H) k *= 0.96;

  let selected = 0;
  let off = new Set();
  const columns = [];

  const now = el("p", "strip-now", `Today, ${fmtShort(today)}`);
  strip.append(now);

  months.forEach((m, i) => {
    const btn = el("button", "month");
    btn.type = "button";
    btn.setAttribute("aria-pressed", String(i === selected));
    if (i === 0) btn.classList.add("is-now");
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("class", "month-stack");
    svg.setAttribute("aria-hidden", "true");
    const { placed, height } = pack(m.charges);
    const h = Math.max(height, D_MIN) + 2;
    svg.setAttribute("viewBox", `0 0 ${COL_W} ${h}`);
    svg.setAttribute("width", String(COL_W));
    svg.setAttribute("height", String(Math.round(h)));
    const circles = placed.map(({ c, d, cx, fromBottom }) => {
      const circle = document.createElementNS(SVG, "circle");
      circle.setAttribute("cx", cx.toFixed(2));
      circle.setAttribute("cy", (h - 1 - fromBottom).toFixed(2));
      circle.setAttribute("r", String(Math.max(2, d / 2 - (c.past ? 1 : 0))));
      circle.setAttribute("class", `dot hued${bright(c.sub.hue) ? " is-bright" : ""}${c.past ? " is-past" : ""}`);
      circle.style.setProperty("--hue", String(c.sub.hue));
      const title = document.createElementNS(SVG, "title");
      title.textContent = `${c.sub.name}, ${fmtShort(c.date)}, ${money.cents(c.cents)}`;
      circle.append(title);
      svg.append(circle);
      return { circle, c };
    });
    const peak = el("span", "month-peak", "Heaviest");
    peak.hidden = true;
    const name = el("span", "month-name", fmtMonthShort(m.start));
    const total = el("span", "month-total");
    btn.append(peak, svg, name, total);
    btn.addEventListener("click", () => select(i, true));
    strip.append(btn);
    columns.push({ btn, peak, total, circles, m });
  });

  function monthCents(m) {
    return m.charges.reduce((sum, c) => sum + (off.has(c.sub.id) ? 0 : c.cents), 0);
  }

  function renderDetail() {
    const m = months[selected];
    const cents = monthCents(m);
    const live = m.charges.filter((c) => !off.has(c.sub.id));
    const title = el("h3", "month-detail-title", fmtMonthLong(m.start));
    const sum = el("p", "month-detail-sum",
      m.charges.length === 0 ? "Nothing charges this month." : `${money.cents(cents)} across ${plural(live.length, "charge", "charges")}`);
    const list = el("ol", "charges");
    for (const c of m.charges) {
      const li = el("li", `charge hued${bright(c.sub.hue) ? " is-bright" : ""}${c.past ? " is-past" : ""}${off.has(c.sub.id) ? " is-off" : ""}`);
      li.style.setProperty("--hue", String(c.sub.hue));
      const dot = el("span", "charge-dot");
      const date = el("time", "charge-date", fmtShort(c.date));
      date.dateTime = isoDay(c.date);
      li.append(dot, date, el("span", "charge-name", c.sub.name), el("span", "charge-amount", money.cents(c.cents)));
      list.append(li);
    }
    detail.replaceChildren(title, sum, list);
  }

  function select(i, fromTap) {
    selected = i;
    columns.forEach((col, j) => col.btn.setAttribute("aria-pressed", String(j === i)));
    renderDetail();
    if (fromTap) center(i, true);
  }

  function center(i, smooth) {
    const btn = columns[i].btn;
    const left = btn.offsetLeft - (scroller.clientWidth - btn.offsetWidth) / 2;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    scroller.scrollTo({ left: Math.max(0, left), behavior: smooth && !reduce ? "smooth" : "auto" });
  }

  function update(nextOff) {
    off = nextOff;
    let peakIndex = -1;
    let peakCents = 0;
    columns.forEach((col, i) => {
      const cents = monthCents(col.m);
      col.total.textContent = money.round(cents);
      const count = col.m.charges.filter((c) => !off.has(c.sub.id)).length;
      col.btn.setAttribute("aria-label", `${fmtMonthLong(col.m.start)}, ${money.cents(cents)}, ${plural(count, "charge", "charges")}`);
      for (const { circle, c } of col.circles) circle.classList.toggle("is-off", off.has(c.sub.id));
      if (cents > peakCents) { peakCents = cents; peakIndex = i; }
    });
    columns.forEach((col, i) => {
      col.btn.classList.toggle("is-peak", i === peakIndex);
      col.peak.hidden = i !== peakIndex;
    });
    if (peakIndex >= 0) {
      const strongPeak = el("strong", "", fmtMonthLong(months[peakIndex].start));
      note.replaceChildren("The heaviest month is ", strongPeak, `, at ${money.cents(peakCents)}.`);
    } else {
      note.textContent = "Nothing charges in the next twelve months.";
    }
    renderDetail();
  }

  return { update, select: (i) => select(i, false), center: () => center(selected, false) };
}
