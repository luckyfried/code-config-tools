// The Categories screen: the month's totals by category, their share of spending, the monthly average across the
// window, and where most of it went. Every column but the last sorts; the order is kept with the rest of the state.
import { exact, money, percent } from "./format.js";
import { categoryColor, readTone } from "./color.js";

const cell = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};

export function renderTable({ rowsEl, footEl, captionEl, headEl }, data, month, sort) {
  const tone = readTone();
  const meta = new Map(data.categories.map((c) => [c.id, { label: c.label, color: categoryColor(c.color, tone) }]));
  meta.set("other", { label: "Other", color: tone.other });
  const n = data.months.length;
  const ids = new Set(data.months.flatMap((m) => m.categories.map((c) => c.id)));
  const rows = [...ids].map((id) => {
    const here = month.categories.find((c) => c.id === id);
    const sum = data.months.reduce((s, m) => s + (m.categories.find((c) => c.id === id)?.cents || 0), 0);
    const top = here ? [...here.merchants].sort((a, b) => b.cents - a.cents)[0] : null;
    return { id, label: meta.get(id).label, color: meta.get(id).color, spent: here ? here.cents : 0, share: here ? here.cents / Math.max(1, month.spent) : 0, avg: sum / n, top };
  });
  const dir = sort.dir === "asc" ? 1 : -1;
  rows.sort((a, b) => (sort.key === "label" ? a.label.localeCompare(b.label) : a[sort.key] - b[sort.key]) * dir || b.spent - a.spent);
  const maxShare = Math.max(0.0001, ...rows.map((r) => r.share));

  rowsEl.replaceChildren(...rows.map((r) => {
    const tr = cell("tr", r.spent ? "" : "is-quiet");
    tr.style.setProperty("--seg", r.color);
    const name = cell("th", "col-name");
    name.scope = "row";
    name.appendChild(cell("span", "chip"));
    name.appendChild(cell("span", "cat-name", r.label));
    if (r.top) name.appendChild(cell("span", "cat-top", r.top.name));
    tr.appendChild(name);
    tr.appendChild(cell("td", "col-spent num", exact(data.currency, r.spent)));
    const share = cell("td", "col-share");
    const meter = cell("span", "meter");
    const fill = cell("span", "meter-fill");
    fill.style.setProperty("--w", (r.share / maxShare).toFixed(4));
    meter.appendChild(fill);
    share.appendChild(meter);
    share.appendChild(cell("span", "meter-value num", percent(r.spent, month.spent)));
    tr.appendChild(share);
    tr.appendChild(cell("td", "col-avg num", money(data.currency, r.avg)));
    tr.appendChild(cell("td", "col-top", r.top ? `${r.top.name}, ${money(data.currency, r.top.cents)}` : ""));
    return tr;
  }));

  const income = month.income.reduce((s, x) => s + x.cents, 0);
  const avgSpent = data.months.reduce((s, m) => s + m.spent, 0) / n;
  const tr = cell("tr");
  const th = cell("th", "col-name", "All spending");
  th.scope = "row";
  tr.appendChild(th);
  tr.appendChild(cell("td", "col-spent num", exact(data.currency, month.spent)));
  tr.appendChild(cell("td", "col-share num", income > 0 ? `${percent(month.spent, income)} of income` : ""));
  tr.appendChild(cell("td", "col-avg num", money(data.currency, avgSpent)));
  tr.appendChild(cell("td", "col-top"));
  footEl.replaceChildren(tr);
  captionEl.textContent = `${month.label}, by category`;

  for (const b of headEl.querySelectorAll("[data-sort]")) {
    const on = b.dataset.sort === sort.key;
    b.closest("th").setAttribute("aria-sort", on ? (sort.dir === "asc" ? "ascending" : "descending") : "none");
    b.classList.toggle("is-on", on);
    b.dataset.dir = on ? sort.dir : "";
  }
}
