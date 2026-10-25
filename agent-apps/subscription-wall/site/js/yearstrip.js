// The year at a glance, on the wall under the headline: one column per month starting with this one, a dot per charge
// sized by its amount, and the heaviest month lifted with its total. Picking a month opens the Calendar on it.

import { buildMonths } from "./calendar.js";
import { bright, fmtMonthLong, fmtMonthOnly, fmtMonthShort, fmtShort, plural } from "./format.js";

const SVG = "http://www.w3.org/2000/svg";
const COL_W = 40;
const GAP = 3;
const D_MAX = 22;
const D_MIN = 5;
const STACK_H = 84;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function createYearStrip({ root, caption, subs, money, today, onPick }) {
  const months = buildMonths(subs, today);
  const maxAmount = Math.max(1, ...subs.map((s) => s.amount));
  let k = D_MAX / Math.sqrt(maxAmount);
  const diameter = (amount) => Math.max(D_MIN, k * Math.sqrt(amount));

  // Packs a month's dots into rows as wide as the column, the earliest charge at the bottom.
  function pack(charges) {
    const rows = [];
    let row = null;
    for (const c of charges) {
      const d = diameter(c.sub.amount);
      if (!row || row.width + GAP + d > COL_W) {
        row = { width: d, height: d, dots: [] };
        rows.push(row);
      } else {
        row.width += GAP + d;
        row.height = Math.max(row.height, d);
      }
      row.dots.push({ c, d });
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

  while (k > 0.3 && Math.max(...months.map((m) => pack(m.charges).height)) > STACK_H) k *= 0.95;
  const h = Math.max(...months.map((m) => pack(m.charges).height), D_MIN) + 2;

  let off = new Set();
  const columns = months.map((m, i) => {
    const btn = el("button", `ym${i === 0 ? " is-now" : ""}`);
    btn.type = "button";
    btn.style.setProperty("--i", String(i));
    const peak = el("span", `ym-peak${i < 2 ? " is-start" : i > 9 ? " is-end" : ""}`);
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("class", "ym-stack");
    svg.setAttribute("viewBox", `0 0 ${COL_W} ${h.toFixed(2)}`);
    svg.setAttribute("aria-hidden", "true");
    const dots = pack(m.charges).placed.map(({ c, d, cx, fromBottom }) => {
      const circle = document.createElementNS(SVG, "circle");
      circle.setAttribute("cx", cx.toFixed(2));
      circle.setAttribute("cy", (h - 1 - fromBottom).toFixed(2));
      circle.setAttribute("r", (d / 2).toFixed(2));
      circle.setAttribute("class", `dot hued${bright(c.sub.hue) ? " is-bright" : ""}${c.past ? " is-past" : ""}`);
      circle.style.setProperty("--hue", String(c.sub.hue));
      const title = document.createElementNS(SVG, "title");
      title.textContent = `${c.sub.name}, ${fmtShort(c.date)}, ${money.cents(c.cents)}`;
      circle.append(title);
      svg.append(circle);
      return { circle, c };
    });
    btn.append(peak, svg, el("span", "ym-name", fmtMonthShort(m.start)));
    btn.addEventListener("click", () => onPick(i));
    root.append(btn);
    return { btn, peak, dots, m };
  });

  const monthCents = (m) => m.charges.reduce((sum, c) => sum + (off.has(c.sub.id) ? 0 : c.cents), 0);

  function update(nextOff) {
    off = nextOff;
    let peakIndex = -1;
    let peakCents = 0;
    columns.forEach((col, i) => {
      const cents = monthCents(col.m);
      for (const { circle, c } of col.dots) circle.classList.toggle("is-off", off.has(c.sub.id));
      const live = col.m.charges.filter((c) => !off.has(c.sub.id)).length;
      col.btn.setAttribute("aria-label", `${fmtMonthLong(col.m.start)}, ${money.cents(cents)}, ${plural(live, "charge", "charges")}. Open it in the Calendar.`);
      if (cents > peakCents) { peakCents = cents; peakIndex = i; }
    });
    columns.forEach((col, i) => {
      col.btn.classList.toggle("is-peak", i === peakIndex);
      col.peak.textContent = i === peakIndex ? money.round(peakCents) : "";
    });
    if (peakIndex >= 0) {
      const strong = el("strong", "", fmtMonthOnly(months[peakIndex].start));
      caption.replaceChildren("Next twelve months. The heaviest is ", strong, ".");
    } else {
      caption.textContent = "Nothing charges in the next twelve months.";
    }
  }

  // Drops the month columns in from the left as the total rolls up.
  function reveal(reduce) {
    if (reduce) return;
    columns.forEach((col, i) => {
      col.btn.querySelector(".ym-stack").animate(
        [{ opacity: 0, transform: "translateY(12px) scale(0.92)" }, { opacity: 1, transform: "none" }],
        { duration: 520, delay: 120 + i * 45, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" },
      );
    });
  }

  return { update, reveal };
}
