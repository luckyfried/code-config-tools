// The table: every snapshot a row, newest first, every account a column, and under each number its
// change from the month before, colored by whether it helped or hurt.
function cell(tag, className, parent) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  parent.appendChild(node);
  return node;
}

export function renderTable({ table, model, fmt }) {
  const { points, assets, debts } = model;
  const columns = [
    { label: "Net worth", className: "col-net", value: (p) => p.net, better: 1 },
    { label: "Assets", value: (p) => p.assets, better: 1, swatch: "var(--asset-1)" },
    { label: "Debts", value: (p) => p.debts, better: -1, swatch: "var(--debt-1)" },
    ...assets.map((a) => ({ label: a.label, value: (p) => p.balances[a.id], better: 1, swatch: a.color })),
    ...debts.map((a) => ({ label: a.label, value: (p) => p.balances[a.id], better: -1, swatch: a.color })),
  ];

  table.textContent = "";
  const head = cell("tr", "", cell("thead", "", table));
  const month = cell("th", "col-month", head);
  month.scope = "col";
  month.textContent = "Month";
  for (const column of columns) {
    const th = cell("th", column.className || "", head);
    th.scope = "col";
    const label = cell("span", column.swatch ? "col-kind" : "", th);
    label.textContent = column.label;
    if (column.swatch) label.style.setProperty("--swatch", column.swatch);
  }

  const body = cell("tbody", "", table);
  for (let i = points.length - 1; i >= 0; i -= 1) {
    const point = points[i];
    const before = points[i - 1];
    const row = cell("tr", i === points.length - 1 ? "is-latest" : "", body);
    const th = cell("th", "col-month", row);
    th.scope = "row";
    th.textContent = fmt.monthShortYear(point.idx);
    for (const column of columns) {
      const td = cell("td", column.className || "", row);
      cell("span", "cell-value", td).textContent = fmt.money(column.value(point));
      const delta = cell("span", "cell-delta", td);
      if (!before) {
        delta.textContent = "first month";
        continue;
      }
      const change = column.value(point) - column.value(before);
      delta.textContent = change === 0 ? "no change" : fmt.signed(change);
      if (change !== 0) delta.classList.add(change * column.better > 0 ? "is-up" : "is-down");
    }
  }
}
