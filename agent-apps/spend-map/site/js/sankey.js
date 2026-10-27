// The Sankey for one month. buildModel turns a month of data.js into three columns of nodes (income, categories,
// merchants, or the first two alone when cap is null) and the links between them; layout places them in two passes: one scale for every column, chosen so the
// fullest column still gives each label its room, then each column's nodes stacked by value and centered.

const OTHER = { id: "other", label: "Other" };

export function buildModel(month, data, cap) {
  const cats = new Map(data.categories.map((c) => [c.id, c]));
  const incomeTotal = month.income.reduce((sum, s) => sum + s.cents, 0);
  const spent = month.spent;
  const total = Math.max(incomeTotal, spent);

  const col0 = month.income.map((s, i) => ({ id: `in:${s.name}`, col: 0, label: s.name, value: s.cents, kind: "income", rank: i }));
  if (spent > incomeTotal) col0.push({ id: "in:~savings", col: 0, label: "From savings", value: spent - incomeTotal, kind: "saved" });

  const ranked = [...month.categories].sort((a, b) => (a.id === "other") - (b.id === "other") || b.cents - a.cents);
  const col1 = ranked.map((c) => {
    const meta = cats.get(c.id) || OTHER;
    return { id: `cat:${c.id}`, col: 1, label: meta.label, value: c.cents, kind: c.id === "other" ? "other" : "cat", cat: c.id, color: meta.color };
  });
  if (incomeTotal > spent) col1.push({ id: "cat:~saved", col: 1, label: "Saved", value: incomeTotal - spent, kind: "saved" });

  const col2 = [];
  const links = [];
  for (const c of cap === null ? [] : ranked) {
    const meta = cats.get(c.id) || OTHER;
    const named = c.merchants;
    const keep = cap >= named.length ? named.length : named.length - cap === 1 && !c.others ? named.length : cap;
    named.slice(0, keep).forEach((m, i) => {
      col2.push({ id: `m:${c.id}:${m.name}`, col: 2, label: m.name, value: m.cents, kind: c.id === "other" ? "other" : "merchant", cat: c.id, color: meta.color, rank: i });
    });
    const folded = named.slice(keep);
    const restCount = folded.length + (c.others ? c.others.count : 0);
    const restValue = folded.reduce((sum, m) => sum + m.cents, 0) + (c.others ? c.others.cents : 0);
    if (restValue > 0) {
      const label = keep === 0 ? `${restCount} ${restCount === 1 ? "merchant" : "merchants"}` : `${restCount} more`;
      col2.push({ id: `m:${c.id}:~rest`, col: 2, label, value: restValue, kind: c.id === "other" ? "other" : "merchant", cat: c.id, color: meta.color, rank: keep, rest: true });
    }
  }
  for (const n of col2) links.push({ id: `cat:${n.cat}>${n.id}`, source: `cat:${n.cat}`, target: n.id, value: n.value });
  for (const s of col0) {
    for (const c of col1) {
      const value = (s.value * c.value) / total;
      if (value > 0) links.push({ id: `${s.id}>${c.id}`, source: s.id, target: c.id, value });
    }
  }
  return { columns: [col0, col1, col2], links, total, spent, income: incomeTotal };
}

// How many merchants each category can name before the merchant column runs out of room for its labels.
export function fitCap(month, data, across, slot, gap) {
  for (let cap = 8; cap >= 0; cap -= 1) {
    const n = buildModel(month, data, cap).columns[2].length;
    if (n * slot + (n - 1) * gap <= across) return cap;
  }
  return 0;
}

// geo: { along: [a0, a1, a2] (where each column starts along the flow), thick, gutter: [g0, g1, g2] (the clear room
// after each column's nodes, where its labels sit, before its ribbons leave), start, across, slots, gaps }
export function layout(model, geo) {
  const cols = model.columns;
  const slots = cols.map((col, i) => {
    const need = col.length * geo.slots[i] + Math.max(0, col.length - 1) * geo.gaps[i];
    return need > geo.across && col.length ? (geo.across - (col.length - 1) * geo.gaps[i]) / col.length : geo.slots[i];
  });
  const size = (k) => cols.map((col, i) => col.reduce((sum, n) => sum + Math.max(n.value * k, slots[i]), 0) + Math.max(0, col.length - 1) * geo.gaps[i]);
  let lo = 0;
  let hi = geo.across / Math.max(1, model.total);
  for (let i = 0; i < 40; i += 1) {
    const mid = (lo + hi) / 2;
    if (Math.max(...size(mid)) <= geo.across) lo = mid;
    else hi = mid;
  }
  const k = lo;
  const sizes = size(k);
  const nodes = new Map();
  cols.forEach((col, i) => {
    let at = geo.start + (geo.across - sizes[i]) / 2;
    for (const n of col) {
      const extent = n.value * k;
      const slot = Math.max(extent, slots[i]);
      nodes.set(n.id, { ...n, a: geo.along[i], c: at + (slot - extent) / 2, e: extent, slotStart: at, slot });
      at += slot + geo.gaps[i];
    }
  });

  const out = new Map();
  const into = new Map();
  for (const l of model.links) {
    if (!out.has(l.source)) out.set(l.source, []);
    if (!into.has(l.target)) into.set(l.target, []);
    out.get(l.source).push(l);
    into.get(l.target).push(l);
  }
  const placed = new Map(model.links.map((l) => [l.id, { ...l, w: l.value * k }]));
  for (const [id, list] of out) {
    const node = nodes.get(id);
    let at = node.c;
    list.sort((x, y) => nodes.get(x.target).c - nodes.get(y.target).c);
    for (const l of list) {
      const p = placed.get(l.id);
      p.c0 = at + p.w / 2;
      at += p.w;
    }
  }
  for (const [id, list] of into) {
    const node = nodes.get(id);
    let at = node.c;
    list.sort((x, y) => nodes.get(x.source).c - nodes.get(y.source).c);
    for (const l of list) {
      const p = placed.get(l.id);
      p.c1 = at + p.w / 2;
      at += p.w;
    }
  }
  for (const p of placed.values()) {
    const s = nodes.get(p.source);
    const t = nodes.get(p.target);
    p.a0 = s.a + geo.thick + geo.gutter[s.col];
    p.a1 = t.a;
    p.stage = s.col;
  }
  return { nodes, links: placed, k };
}
