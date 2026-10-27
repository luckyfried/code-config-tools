// Stacked bars by category, one per month: the small strip on the Map screen and the full chart on the Months screen.
// A bar is a button; choosing it opens that month on the Map. Heights and shares are custom properties on the bars.
import { money } from "./format.js";
import { categoryColor, readTone } from "./color.js";

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};

function catColors(data) {
  const tone = readTone();
  const map = new Map(data.categories.map((c) => [c.id, categoryColor(c.color, tone)]));
  map.set("other", tone.other);
  return map;
}

const incomeOf = (m) => m.income.reduce((s, x) => s + x.cents, 0);

function scaleMax(data) {
  return Math.max(1, ...data.months.map((m) => Math.max(m.spent, incomeOf(m))));
}

function bar(month, data, colors, max, { big, onPick, index }) {
  const button = el("button", "mbar");
  button.type = "button";
  button.dataset.month = month.key;
  button.style.setProperty("--i", index);
  button.setAttribute("aria-label", `${month.label}: ${money(data.currency, month.spent)} spent`);
  const plot = el("span", "mbar-plot");
  const col = el("span", "mbar-col");
  col.style.setProperty("--h", (month.spent / max).toFixed(4));
  const ordered = [...month.categories].sort((a, b) => order(data, a.id) - order(data, b.id));
  for (const c of ordered) {
    const seg = el("span", "mbar-seg");
    seg.style.setProperty("--share", (c.cents / Math.max(1, month.spent)).toFixed(4));
    seg.style.setProperty("--seg", colors.get(c.id));
    if (big) seg.dataset.amount = money(data.currency, c.cents);
    col.appendChild(seg);
  }
  plot.appendChild(col);
  const income = incomeOf(month);
  if (income > 0) {
    const tick = el("span", "mbar-income");
    tick.style.setProperty("--at", (income / max).toFixed(4));
    if (big) tick.dataset.amount = `Income ${money(data.currency, income)}`;
    plot.appendChild(tick);
  }
  button.appendChild(plot);
  const foot = el("span", "mbar-foot");
  if (big) {
    foot.appendChild(el("span", "mbar-name mbar-name-long", month.label.split(" ")[0]));
    foot.appendChild(el("span", "mbar-name mbar-name-short", month.short));
  } else {
    foot.appendChild(el("span", "mbar-name", month.short));
  }
  foot.appendChild(el("span", "mbar-total num", money(data.currency, month.spent)));
  button.appendChild(foot);
  button.addEventListener("click", () => onPick(month.key));
  return button;
}

function order(data, id) {
  const i = data.categories.findIndex((c) => c.id === id);
  return i < 0 ? 99 : i;
}

export function renderStrip(root, data, onPick) {
  const colors = catColors(data);
  const max = scaleMax(data);
  root.replaceChildren(...data.months.map((m, i) => bar(m, data, colors, max, { big: false, onPick, index: i })));
}

export function renderChart(root, legend, data, onPick) {
  const colors = catColors(data);
  const max = scaleMax(data);
  const grid = el("div", "chart-grid");
  const step = niceStep(max / 100);
  for (let v = step; v * 100 <= max; v += step) {
    const line = el("span", "chart-line");
    line.style.setProperty("--at", ((v * 100) / max).toFixed(4));
    line.appendChild(el("span", "chart-line-value num", money(data.currency, v * 100)));
    grid.appendChild(line);
  }
  const bars = el("div", "chart-bars");
  data.months.forEach((m, i) => bars.appendChild(bar(m, data, colors, max, { big: true, onPick, index: i })));
  root.replaceChildren(grid, bars);

  const used = new Set(data.months.flatMap((m) => m.categories.map((c) => c.id)));
  const items = data.categories.filter((c) => used.has(c.id)).map((c) => ({ id: c.id, label: c.label }));
  if (used.has("other")) items.push({ id: "other", label: "Other" });
  legend.replaceChildren(...items.map((c) => {
    const li = el("li", "legend-item", c.label);
    li.style.setProperty("--seg", colors.get(c.id));
    return li;
  }));
  labelSegments(root);
}

// A segment shows its amount when it is tall enough to hold it.
export function labelSegments(root) {
  for (const seg of root.querySelectorAll(".mbar-seg")) {
    seg.classList.toggle("has-label", seg.offsetHeight >= 22);
  }
}

function niceStep(raw) {
  const target = raw / 4;
  const pow = 10 ** Math.floor(Math.log10(target));
  return [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= target) || pow * 10;
}

export function markMonth(root, key) {
  for (const b of root.querySelectorAll(".mbar")) {
    const on = b.dataset.month === key;
    b.classList.toggle("is-on", on);
    b.setAttribute("aria-pressed", String(on));
  }
}
