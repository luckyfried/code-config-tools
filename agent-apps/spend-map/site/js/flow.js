// Draws the Sankey into the page's SVG. The first month draws on: each ribbon's stroke-dashoffset runs along its
// path, income first, then categories, then merchants, over --motion-draw. Every later month tweens each node and
// ribbon from where it is to where it goes over --motion-slow, so the map breathes instead of redrawing. Hovering or
// tapping a ribbon dims the others to 25 % and sets its amount on the ribbon itself. Every label is horizontal and sits
// in clear room beside its node: income to the left, categories on a tinted plate right of their nodes, merchants to
// the right. A narrow map (the phone) draws income to categories only, and a tap on a category names it to onPick.
import { buildModel, fitCap, layout } from "./sankey.js";
import { categoryColor, merchantColor, readTone } from "./color.js";
import { clip, money } from "./format.js";

const NS = "http://www.w3.org/2000/svg";
const make = (name, attrs = {}, parent = null) => {
  const el = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (parent) parent.appendChild(el);
  return el;
};
const ms = (name, fallback) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!v) return fallback;
  return v.endsWith("ms") ? parseFloat(v) : parseFloat(v) * 1000;
};
const easeOut = (t) => 1 - (1 - t) ** 3;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const clamp01 = (t) => Math.min(1, Math.max(0, t));
const lerp = (a, b, t) => a + (b - a) * t;

export function createFlow(root, data, { onPick } = {}) {
  const svg = root.querySelector("svg.sankey");
  const gGrad = svg.querySelector(".gradients");
  const gLinks = svg.querySelector(".links");
  const gNodes = svg.querySelector(".nodes");
  const gLabels = svg.querySelector(".labels");
  const tag = svg.querySelector(".tag");
  const tagBox = tag.querySelector(".tag-box");
  const tagAmount = tag.querySelector(".tag-amount");
  const tagRoute = tag.querySelector(".tag-route");
  const currency = data.currency;

  const els = new Map(); // id -> { kind: "link" | "node", el, label?, grad? }
  let geo = null;
  let shown = null; // { nodes: Map, links: Map } as drawn right now
  let target = null;
  let monthKey = null;
  let frame = 0;
  let lead = 0; // the wait while leaving labels fade out, before a switch moves anything
  let drawing = false;
  let focused = null;
  let tone = readTone();
  let gradSeq = 0;
  let room = null; // the widest label each column shows across every month, measured once the fonts are in
  let picked = null;

  function measure() {
    const t = make("text", { class: "label", x: 0, y: -999 }, gLabels);
    const name = make("tspan", { class: "label-name" }, t);
    const amount = make("tspan", { class: "label-amount" }, t);
    const widest = (col, items, oneLine) => {
      t.setAttribute("class", `label label-${col}`);
      let max = 0;
      for (const [label, cents] of items) {
        name.textContent = label;
        amount.textContent = money(currency, cents);
        const a = name.getComputedTextLength();
        const b = amount.getComputedTextLength();
        max = Math.max(max, oneLine ? a + 7 + b : Math.max(a, b));
      }
      return Math.ceil(max);
    };
    const labels = new Map(data.categories.map((c) => [c.id, c.label]));
    const income = [];
    const cats = [];
    const merchants = [];
    for (const m of data.months) {
      const inc = m.income.reduce((sum, x) => sum + x.cents, 0);
      for (const x of m.income) income.push([x.name, x.cents]);
      income.push(["From savings", Math.max(0, m.spent - inc)]);
      cats.push(["Saved", Math.max(0, inc - m.spent)]);
      for (const c of m.categories) {
        cats.push([labels.get(c.id) || "Other", c.cents]);
        for (const x of c.merchants) merchants.push([x.name, x.cents]);
      }
    }
    const out = { income: widest(0, income), cats: widest(1, cats), merchants: widest(2, merchants, true) };
    t.remove();
    return out.cats > 0 ? out : null;
  }

  function geometry() {
    const w = Math.max(1, root.clientWidth);
    const h = Math.max(1, root.clientHeight);
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("width", w);
    svg.setAttribute("height", h);
    room = room || measure();
    const r = room || { income: 90, cats: 110, merchants: 190 };
    if (w < 720) {
      const thick = 12;
      const left = Math.min(r.income + 12, Math.round(w * 0.37));
      const right = Math.min(r.cats + 12, Math.round(w * 0.37));
      const a1 = w - right - thick;
      return { compact: true, w, h, thick, along: [left, a1, a1], gutter: [0, 0, 0], start: 0, across: h, slots: [44, 36, 0], gaps: [12, 6, 0], room: [left - 10, right - 10, 0] };
    }
    const thick = 14;
    const left = Math.min(r.income + 14, Math.round(w * 0.16));
    const gutter = Math.min(r.cats + 24, Math.round(w * 0.16));
    const right = Math.min(r.merchants + 14, Math.round(w * 0.22));
    const a0 = left;
    const a2 = w - right - thick;
    const a1 = a0 + thick + (a2 - a0 - 2 * thick - gutter) / 2;
    return { compact: false, w, h, thick, along: [a0, a1, a2], gutter: [0, gutter, 0], start: 4, across: h - 8, slots: [44, 40, 17], gaps: [14, 10, 3], room: [left - 10, gutter - 20, right - 10] };
  }

  function compute(month) {
    const cap = geo.compact ? null : fitCap(month, data, geo.across, geo.slots[2], geo.gaps[2]);
    return layout(buildModel(month, data, cap), geo);
  }

  function colorOf(n) {
    if (n.kind === "income") return tone.income;
    if (n.kind === "saved") return tone.saved;
    if (n.kind === "other") return tone.other;
    if (n.kind === "cat") return categoryColor(n.color, tone);
    return merchantColor(n.color, tone, n.rank || 0);
  }

  function ensure(id, kind, item) {
    let rec = els.get(id);
    if (rec) return rec;
    if (kind === "link") {
      const gid = `ribbon-${(gradSeq += 1)}`;
      const grad = make("linearGradient", { id: gid, gradientUnits: "userSpaceOnUse" }, gGrad);
      make("stop", { offset: "0" }, grad);
      make("stop", { offset: "1" }, grad);
      const el = make("path", { class: `link link-${item.stage}`, stroke: `url(#${gid})`, "data-id": id }, gLinks);
      rec = { kind, el, grad };
    } else {
      const plate = item.col === 1 ? make("rect", { class: "plate", "data-id": id }, gNodes) : null;
      const el = make("rect", { class: `node node-${item.col} node-${item.kind}`, "data-id": id }, gNodes);
      // A new label starts hidden; it shows once its node has settled where it goes.
      const label = make("text", { class: `label label-${item.col} label-${item.kind}`, "data-id": id, opacity: 0 }, gLabels);
      const name = make("tspan", { class: "label-name" }, label);
      const amount = make("tspan", { class: "label-amount" }, label);
      rec = { kind, el, plate, label, name, amount };
    }
    els.set(id, rec);
    return rec;
  }

  // A name longer than its column's room loses letters from the end; the measured rooms mean that happens only when
  // the window is too narrow for the longest name.
  function paintNode(rec, n, { text = true } = {}) {
    rec.color = colorOf(n);
    rec.el.setAttribute("fill", rec.color);
    if (rec.plate) rec.plate.setAttribute("fill", rec.color);
    if (!text) return;
    rec.amount.textContent = money(currency, n.value);
    const fits = n.col === 2 ? geo.room[2] - 7 - rec.amount.getComputedTextLength() : geo.room[n.col];
    rec.name.textContent = n.label;
    for (let keep = n.label.length; keep > 4 && rec.name.getComputedTextLength() > fits; keep -= 1) {
      rec.name.textContent = clip(n.label, keep);
    }
  }

  function paintLink(rec, l, nodes) {
    const s = nodes.get(l.source);
    const t = nodes.get(l.target);
    const [a, b] = rec.grad.children;
    a.setAttribute("stop-color", colorOf(s));
    b.setAttribute("stop-color", colorOf(t));
    rec.grad.setAttribute("x1", l.a0); rec.grad.setAttribute("x2", l.a1);
    rec.grad.setAttribute("y1", 0); rec.grad.setAttribute("y2", 0);
  }

  function pathOf(l) {
    const m = (l.a0 + l.a1) / 2;
    return `M${l.a0.toFixed(1)},${l.c0.toFixed(2)}C${m.toFixed(1)},${l.c0.toFixed(2)} ${m.toFixed(1)},${l.c1.toFixed(2)} ${l.a1.toFixed(1)},${l.c1.toFixed(2)}`;
  }

  function placeLabel(rec, n) {
    const L = rec.label;
    const mid = n.c + n.e / 2;
    const two = n.col < 2;
    const x = n.col === 0 ? n.a - 10 : n.a + geo.thick + 10;
    L.setAttribute("text-anchor", n.col === 0 ? "end" : "start");
    L.setAttribute("x", x);
    L.setAttribute("y", two ? mid - 3 : mid + 4.5);
    if (two) {
      rec.amount.setAttribute("x", x);
      rec.amount.setAttribute("dy", "1.3em");
      rec.amount.setAttribute("dx", "0");
    } else {
      rec.amount.removeAttribute("x");
      rec.amount.setAttribute("dy", "0");
      rec.amount.setAttribute("dx", "7");
    }
  }

  function apply(state) {
    for (const [id, n] of state.nodes) {
      const rec = els.get(id);
      rec.el.setAttribute("x", n.a); rec.el.setAttribute("y", n.c);
      rec.el.setAttribute("width", geo.thick); rec.el.setAttribute("height", Math.max(0, n.e));
      if (rec.plate) {
        rec.plate.setAttribute("x", n.a + geo.thick); rec.plate.setAttribute("y", n.c);
        rec.plate.setAttribute("width", geo.gutter[1]); rec.plate.setAttribute("height", Math.max(0, n.e));
      }
      placeLabel(rec, n);
    }
    for (const [id, l] of state.links) {
      const rec = els.get(id);
      rec.el.setAttribute("d", pathOf(l));
      rec.el.setAttribute("stroke-width", l.w > 0.02 ? Math.max(1, l.w).toFixed(2) : 0);
    }
  }

  function syncElements(next, options) {
    for (const n of next.nodes.values()) paintNode(ensure(n.id, "node", n), n, options);
    for (const l of next.links.values()) paintLink(ensure(l.id, "link", l), l, next.nodes);
  }

  function prune(keep) {
    for (const [id, rec] of els) {
      if (keep.nodes.has(id) || keep.links.has(id)) continue;
      rec.el.remove();
      if (rec.plate) rec.plate.remove();
      if (rec.label) rec.label.remove();
      if (rec.grad) rec.grad.remove();
      els.delete(id);
    }
  }

  function stopFrame() {
    cancelAnimationFrame(frame);
    clearTimeout(lead);
    frame = 0;
    lead = 0;
    if (drawing) {
      drawing = false;
      for (const rec of els.values()) {
        rec.el.removeAttribute("stroke-dasharray");
        rec.el.removeAttribute("stroke-dashoffset");
        rec.el.removeAttribute("opacity");
        if (rec.plate) rec.plate.removeAttribute("opacity");
        if (rec.label) rec.label.removeAttribute("opacity");
      }
    }
  }

  function drawOn(state) {
    const total = ms("--motion-draw", 1200);
    apply(state);
    if (total <= 0) return;
    drawing = true;
    const links = [...state.links.values()].map((l) => {
      const rec = els.get(l.id);
      const len = rec.el.getTotalLength() + 2;
      rec.el.setAttribute("stroke-dasharray", `${len.toFixed(1)} ${len.toFixed(1)}`);
      rec.el.setAttribute("stroke-dashoffset", len.toFixed(1));
      return { rec, len, stage: l.stage, order: l.stage === 0 ? state.nodes.get(l.target).c : l.c1 };
    });
    for (const stage of [0, 1]) {
      const list = links.filter((x) => x.stage === stage).sort((a, b) => a.order - b.order);
      list.forEach((x, i) => {
        const spread = list.length > 1 ? i / (list.length - 1) : 0;
        x.from = stage === 0 ? spread * 0.12 : 0.42 + spread * 0.12;
        x.to = stage === 0 ? 0.5 + spread * 0.08 : 0.88 + spread * 0.12;
      });
    }
    const windows = [[0, 0.16], [0.34, 0.52], [0.8, 1]];
    const nodes = [...state.nodes.values()].map((n) => ({ rec: els.get(n.id), win: windows[n.col] }));
    const fade = (rec, p) => {
      for (const el of [rec.el, rec.plate, rec.label]) if (el) el.setAttribute("opacity", p);
    };
    for (const x of nodes) fade(x.rec, 0);
    const t0 = performance.now();
    const tick = (now) => {
      const t = (now - t0) / total;
      for (const x of links) {
        const p = easeOut(clamp01((t - x.from) / (x.to - x.from)));
        x.rec.el.setAttribute("stroke-dashoffset", (x.len * (1 - p)).toFixed(1));
      }
      for (const x of nodes) {
        fade(x.rec, easeOut(clamp01((t - x.win[0]) / (x.win[1] - x.win[0]))).toFixed(3));
      }
      if (t < 1) frame = requestAnimationFrame(tick);
      else stopFrame();
    };
    frame = requestAnimationFrame(tick);
  }

  // The labels that ride with their nodes through a switch: in both months, and in the longest run of each column
  // whose order is the same in both. Two such labels keep their order and at least the smaller of their two spacings
  // in every frame, so no two ever meet; every other label fades out before anything moves and back in once it has
  // settled.
  function riders(from, to) {
    const ride = new Set();
    for (const col of [0, 1, 2]) {
      const ids = [...to.nodes.values()].filter((n) => n.col === col && from.nodes.has(n.id)).map((n) => n.id);
      const before = [...ids].sort((x, y) => from.nodes.get(x).c - from.nodes.get(y).c);
      const rank = new Map([...ids].sort((x, y) => to.nodes.get(x).c - to.nodes.get(y).c).map((id, i) => [id, i]));
      const run = before.map(() => 1);
      const prev = before.map(() => -1);
      before.forEach((id, i) => {
        for (let j = 0; j < i; j += 1) {
          if (rank.get(before[j]) < rank.get(id) && run[j] + 1 > run[i]) { run[i] = run[j] + 1; prev[i] = j; }
        }
      });
      for (let i = run.indexOf(Math.max(0, ...run)); i >= 0; i = prev[i]) ride.add(before[i]);
    }
    return ride;
  }

  function showLabels() {
    for (const rec of els.values()) if (rec.label) rec.label.removeAttribute("opacity");
  }

  function tween(from, to) {
    const duration = ms("--motion-slow", 400);
    const nodes = new Map();
    const links = new Map();
    for (const [id, n] of to.nodes) {
      const a = from.nodes.get(id);
      nodes.set(id, { a: a || { ...n, c: n.c + n.e / 2, e: 0 }, b: n });
    }
    for (const [id, n] of from.nodes) if (!to.nodes.has(id)) nodes.set(id, { a: n, b: { ...n, c: n.c + n.e / 2, e: 0 } });
    for (const [id, l] of to.links) {
      const a = from.links.get(id);
      links.set(id, { a: a || { ...l, w: 0 }, b: l });
    }
    for (const [id, l] of from.links) if (!to.links.has(id)) links.set(id, { a: l, b: { ...l, w: 0 } });
    const mix = (t) => {
      const state = { nodes: new Map(), links: new Map() };
      for (const [id, { a, b }] of nodes) state.nodes.set(id, { ...b, c: lerp(a.c, b.c, t), e: lerp(a.e, b.e, t) });
      for (const [id, { a, b }] of links) state.links.set(id, { ...b, c0: lerp(a.c0, b.c0, t), c1: lerp(a.c1, b.c1, t), w: lerp(a.w, b.w, t) });
      return state;
    };
    if (duration <= 0) {
      apply(to);
      prune(to);
      shown = to;
      showLabels();
      return;
    }
    const ride = riders(from, to);
    for (const [id, rec] of els) if (rec.label && !ride.has(id)) rec.label.setAttribute("opacity", 0);
    lead = setTimeout(() => {
      lead = 0;
      const t0 = performance.now();
      const tick = (now) => {
        const t = clamp01((now - t0) / duration);
        shown = mix(easeInOut(t));
        apply(shown);
        if (t < 1) frame = requestAnimationFrame(tick);
        else {
          frame = 0;
          shown = to;
          prune(to);
          showLabels();
        }
      };
      frame = requestAnimationFrame(tick);
    }, ms("--motion-fast", 120));
  }

  function snapshot() {
    return shown || target;
  }

  function show(month, { draw = false } = {}) {
    clearFocus();
    const first = !shown;
    const from = snapshot();
    stopFrame();
    if (first || !geo) geo = geometry();
    target = compute(month);
    monthKey = month.key;
    svg.classList.toggle("is-compact", geo.compact);
    syncElements(target);
    markPicked(picked);
    if (first || draw) {
      prune(target);
      shown = target;
      drawOn(target);
    } else {
      tween(from, target);
    }
  }

  function relayout(month) {
    const next = geometry();
    if (geo && next.w === geo.w && next.h === geo.h) return;
    stopFrame();
    clearFocus();
    const shape = geo && geo.compact !== next.compact;
    geo = next;
    svg.classList.toggle("is-compact", geo.compact);
    if (shape) { prune({ nodes: new Map(), links: new Map() }); shown = null; }
    target = compute(month);
    syncElements(target);
    markPicked(picked);
    prune(target);
    apply(target);
    shown = target;
    showLabels();
  }

  function recolor() {
    tone = readTone();
    if (!target) return;
    syncElements(target, { text: false });
  }

  function focusOn(id) {
    const state = snapshot();
    if (!state) return;
    const l = state.links.get(id);
    const n = state.nodes.get(id);
    if (!l && !n) return;
    focused = id;
    svg.classList.add("is-focus");
    for (const rec of els.values()) heat(rec, false);
    const hot = new Set();
    let amount;
    let route;
    let x;
    let y;
    if (l) {
      hot.add(l.id); hot.add(l.source); hot.add(l.target);
      const s = state.nodes.get(l.source);
      const t = state.nodes.get(l.target);
      amount = money(currency, l.value);
      route = `${clip(s.label, 18)} to ${clip(t.label, 18)}`;
      x = (l.a0 + l.a1) / 2;
      y = (l.c0 + l.c1) / 2;
    } else {
      hot.add(n.id);
      for (const link of state.links.values()) {
        if (link.source === n.id || link.target === n.id) { hot.add(link.id); hot.add(link.source); hot.add(link.target); }
      }
      amount = money(currency, n.value);
      route = clip(n.label, 26);
      // The tag sits over the node's own ribbons, clear of its label.
      const leftward = n.col === 2 || (geo.compact && n.col === 1);
      x = leftward ? n.a - 80 : n.a + geo.thick + geo.gutter[n.col] + 80;
      y = n.c + n.e / 2;
    }
    for (const hid of hot) {
      const rec = els.get(hid);
      if (rec) heat(rec, true);
    }
    tagAmount.textContent = amount;
    tagRoute.textContent = route;
    tagAmount.setAttribute("x", 0); tagAmount.setAttribute("y", 0);
    tagRoute.setAttribute("x", 0); tagRoute.setAttribute("y", 0);
    const a = tagAmount.getBBox();
    const r = tagRoute.getBBox();
    const width = Math.max(a.width, r.width) + 24;
    const height = 50;
    const left = Math.min(geo.w - width - 4, Math.max(4, x - width / 2));
    const top = Math.min(geo.h - height - 4, Math.max(4, y - height / 2));
    tagBox.setAttribute("x", left); tagBox.setAttribute("y", top);
    tagBox.setAttribute("width", width); tagBox.setAttribute("height", height);
    tagAmount.setAttribute("x", left + width / 2); tagAmount.setAttribute("y", top + 22);
    tagRoute.setAttribute("x", left + width / 2); tagRoute.setAttribute("y", top + 39);
    tag.classList.add("is-on");
  }

  function clearFocus() {
    if (!focused) return;
    focused = null;
    svg.classList.remove("is-focus");
    tag.classList.remove("is-on");
    for (const rec of els.values()) heat(rec, false);
  }

  function heat(rec, on) {
    for (const el of [rec.el, rec.plate, rec.label]) if (el) el.classList.toggle("is-hot", on);
  }

  // The category a node or ribbon belongs to: a category node itself, a ribbon into or out of one, or a merchant.
  function categoryAt(id) {
    const state = snapshot();
    if (!state || !id) return null;
    const l = state.links.get(id);
    const n = l ? [state.nodes.get(l.target), state.nodes.get(l.source)].find((x) => x.col === 1) : state.nodes.get(id);
    return n && n.cat ? n.cat : null;
  }

  function markPicked(cat) {
    picked = cat;
    for (const [id, rec] of els) if (rec.label) rec.label.classList.toggle("is-picked", Boolean(geo && geo.compact) && id === `cat:${cat}`);
  }

  const idAt = (el) => el && el.closest && el.closest("[data-id]") ? el.closest("[data-id]").dataset.id : null;
  svg.addEventListener("pointerover", (e) => {
    if (e.pointerType === "touch" || drawing || frame || lead) return;
    const id = idAt(e.target);
    if (id && id !== focused) focusOn(id);
  });
  svg.addEventListener("pointerout", (e) => {
    if (e.pointerType === "touch") return;
    if (!idAt(e.relatedTarget)) clearFocus();
  });
  svg.addEventListener("pointerdown", (e) => {
    const id = idAt(e.target);
    const cat = categoryAt(id);
    if (cat && onPick) onPick(cat);
    if (e.pointerType !== "touch") return;
    if (id && id !== focused) focusOn(id);
    else clearFocus();
  });

  // The widest ribbon of the last stage drawn (category to merchant, or income to category on a narrow map): the one
  // the page lights once after it draws.
  function focusWidest() {
    const state = snapshot();
    if (!state) return;
    const links = [...state.links.values()];
    const last = Math.max(...links.map((l) => l.stage));
    const widest = links.filter((l) => l.stage === last).sort((a, b) => b.value - a.value)[0];
    if (widest) focusOn(widest.id);
  }

  return {
    show, relayout, recolor, clearFocus, focusWidest, markPicked,
    get month() { return monthKey; },
    get compact() { return Boolean(geo && geo.compact); },
  };
}
