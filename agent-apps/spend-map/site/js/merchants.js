// The narrow map's merchant list: under the map, the places one category's money went this month, each with its
// amount and a bar for its share of the category's largest place.
import { categoryColor, readTone } from "./color.js";
import { money } from "./format.js";

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

export function renderMerchants(root, data, month, catId) {
  root.replaceChildren();
  const cat = month.categories.find((c) => c.id === catId);
  if (!cat) return;
  const meta = data.categories.find((c) => c.id === catId);
  const tone = readTone();
  root.style.setProperty("--seg", meta ? categoryColor(meta.color, tone) : tone.other);

  const rows = cat.merchants.map((m) => ({ name: m.name, cents: m.cents }));
  if (cat.others && cat.others.cents > 0) rows.push({ name: `${cat.others.count} more`, cents: cat.others.cents, rest: true });
  const places = cat.merchants.length + (cat.others ? cat.others.count : 0);
  const top = Math.max(1, ...rows.map((r) => r.cents));

  const head = el("div", "merchants-head");
  head.append(el("span", "merchants-dot"), el("h2", "merchants-title", meta ? meta.label : "Other"), el("span", "merchants-total", money(data.currency, cat.cents)));
  const note = el("p", "merchants-note", `${places} ${places === 1 ? "place" : "places"} in ${month.label}`);
  const list = el("ol", "merchants-list");
  for (const r of rows) {
    const li = el("li", r.rest ? "merchant merchant-rest" : "merchant");
    const bar = el("span", "merchant-bar");
    const fill = el("span", "merchant-fill");
    fill.style.setProperty("--w", (r.cents / top).toFixed(4));
    bar.append(fill);
    li.append(el("span", "merchant-name", r.name), el("span", "merchant-amount", money(data.currency, r.cents)), bar);
    list.append(li);
  }
  root.append(head, note, list);
}
