// The churn treemap: lines changed per folder, squarified. It opens as one block that splits into the top folders,
// which split again into theirs (FLIP). Hovering a folder shows its contents one level down.
import { DATA, el, fmt, compact, calm, setVars, showTip, hideTip, escapeHtml } from "./util.js";

const SPLIT = "cubic-bezier(0.77, 0, 0.175, 1)";
// Names are measured in the face they are drawn in; numbers are mono, so they are counted.
const ruler = document.createElement("canvas").getContext("2d");
const textWidth = (text, size, weight = 620) => {
  ruler.font = `${weight} ${size}px "Inter Variable", Inter, system-ui, sans-serif`;
  return ruler.measureText(text).width;
};
const monoText = (text, size) => text.length * size * 0.6;
const amount = (n) => (n >= 1000 && n < 10000 ? `${(n / 1000).toFixed(1)}k` : compact(n));
const OUT = "cubic-bezier(0.23, 1, 0.32, 1)";

/** Squarified layout of nodes (largest first) in a rectangle. */
export function squarify(nodes, x, y, w, h) {
  const total = nodes.reduce((sum, nd) => sum + nd.s, 0);
  if (total <= 0 || w <= 0 || h <= 0) return [];
  const scale = (w * h) / total;
  const items = nodes.filter((nd) => nd.s > 0).map((nd) => ({ node: nd, a: nd.s * scale }));
  const out = [];
  const worst = (row, side) => {
    let sum = 0;
    let max = 0;
    let min = Infinity;
    for (const r of row) {
      sum += r.a;
      max = Math.max(max, r.a);
      min = Math.min(min, r.a);
    }
    return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
  };
  let i = 0;
  while (i < items.length) {
    const side = Math.min(w, h);
    const row = [items[i]];
    let j = i + 1;
    while (j < items.length && worst([...row, items[j]], side) <= worst(row, side)) {
      row.push(items[j]);
      j += 1;
    }
    const area = row.reduce((sum, r) => sum + r.a, 0);
    if (w >= h) {
      const cw = area / h;
      let cy = y;
      for (const r of row) {
        const rh = r.a / cw;
        out.push({ node: r.node, x, y: cy, w: cw, h: rh });
        cy += rh;
      }
      x += cw;
      w -= cw;
    } else {
      const rh = area / w;
      let cx = x;
      for (const r of row) {
        const rw = r.a / rh;
        out.push({ node: r.node, x: cx, y, w: rw, h: rh });
        cx += rw;
      }
      y += rh;
      h -= rh;
    }
    i = j;
  }
  return out;
}

/** A folder holding one folder and little else shows that folder instead. */
function descend(node, path) {
  let at = node;
  let p = path;
  while (at.c && at.c.length === 1 && at.c[0].c) {
    at = at.c[0];
    p = `${p}${at.n}/`;
  }
  return { node: at, path: p };
}

/**
 * Where each block starts its split: the box around itself and every block laid out after it. Squarify carves blocks
 * off from the top left, so each one keeps its own top-left corner and only its far edges travel; with earlier
 * blocks drawn over later ones, the one block reads as cut apart in turn, and no two blocks ever cross.
 */
function rests(rects) {
  const out = [];
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (let i = rects.length - 1; i >= 0; i -= 1) {
    const r = rects[i];
    x0 = Math.min(x0, r.x);
    y0 = Math.min(y0, r.y);
    x1 = Math.max(x1, r.x + r.w);
    y1 = Math.max(y1, r.y + r.h);
    out[i] = { x: r.x, y: r.y, w: x1 - r.x, h: y1 - r.y };
  }
  return out;
}

// The same box as a share of its parent, so it keeps filling the parent while the parent itself moves.
const shareOf = (r, size) => ({ left: `${(r.x / size.w) * 100}%`, top: `${(r.y / size.h) * 100}%`, width: `${(r.w / size.w) * 100}%`, height: `${(r.h / size.h) * 100}%` });
const boxOf = (r) => ({ left: `${r.x.toFixed(1)}px`, top: `${r.y.toFixed(1)}px`, width: `${r.w.toFixed(1)}px`, height: `${r.h.toFixed(1)}px` });

export function rootOf(tree) {
  return descend(tree, "");
}

export function createTreemap(container, { big = false } = {}) {
  const { node: root, path: rootPath } = rootOf(DATA.tree);
  const total = DATA.tree.s;
  const box = el("div", "tree-box");
  box.setAttribute("role", "img");
  box.setAttribute("aria-label", `Lines changed by folder, ${fmt(total)} in all`);
  box.dataset.root = root.s;
  if (!calm()) box.classList.add("is-waiting");
  container.replaceChildren(box);
  let played = false;
  let size = { w: 0, h: 0 };
  let revealed = null;
  let splitting = false;
  let pending = null;

  // Ramp levels by rank, so a big folder and a small one never share a step by accident.
  const levelOf = (() => {
    const values = [];
    for (const a of root.c || []) {
      if (a.c) for (const b of a.c) values.push(b.s);
      else values.push(a.s);
    }
    values.sort((a, b) => a - b);
    const cut = (p) => values[Math.floor(p * (values.length - 1))] || 0;
    const cuts = [cut(0.3), cut(0.55), cut(0.78), cut(0.93)];
    return (s) => 1 + cuts.filter((c) => s > c).length;
  })();

  const isDir = (nd) => Boolean(nd.d);
  const label = (nd) => (nd.r ? `${nd.n}` : isDir(nd) ? `${nd.n}/` : nd.n);

  /** How a cell's label sits: stacked, on one line, upright along a tall cell, or not at all. */
  function labelFit(nd, rect, holding = false) {
    const header = holding;
    const name = label(nd);
    const value = header ? compact(nd.s) : amount(nd.s);
    const room = rect.w - 13;
    if (header) {
      const nameW = textWidth(name, 13);
      if (nameW + monoText(value, 11) + 12 <= room - 3) return { mode: "header", value };
      return nameW <= room ? { mode: "header", value: "" } : { mode: null, value };
    }
    const nameW = textWidth(name, 12);
    const valueW = monoText(value, 11);
    const large = rect.w >= 180 && rect.h >= 120 && textWidth(name, 16) <= room;
    if (rect.h >= 36 && nameW <= room && valueW <= room) return { mode: "stack", value, large };
    if (rect.h >= 22 && nameW + 6 + valueW <= room) return { mode: "line", value };
    if (rect.w >= 22 && nameW + 6 + valueW <= rect.h - 12) return { mode: "up", value };
    return { mode: null, value };
  }

  /** Squarified, then the smallest entries folded into one "more" cell until every cell can carry its label. */
  function fitted(nodes, x, y, w, h, gap) {
    let list = nodes.filter((nd) => nd.s > 0);
    for (;;) {
      const cells = squarify(list, x, y, w, h);
      const tooSmall = cells.some((c) => !labelFit(c.node, { w: c.w - gap, h: c.h - gap }).mode);
      if (!tooSmall || list.length < 3) return cells;
      // One "more" cell takes the smallest entry each round.
      const folded = list.find((nd) => nd.more);
      const small = list.filter((nd) => !nd.more).slice(-(folded ? 1 : 2));
      const parts = folded ? [folded, ...small] : small;
      const count = parts.reduce((sum, nd) => sum + (nd.r || 1), 0);
      const rest = { n: `${count} more`, s: parts.reduce((sum, nd) => sum + nd.s, 0), r: count, more: true };
      list = [...list.filter((nd) => !parts.includes(nd)), rest].sort((p, q) => q.s - p.s);
    }
  }

  function nodeEl(nd, rect, depth, path, lv) {
    const node = el("div", `tree-node d${depth}${isDir(nd) ? " is-dir" : " is-file"}${nd.r ? " is-rest" : ""}`);
    node.dataset.path = path;
    node.dataset.lines = nd.s;
    if (lv) node.classList.add(`lv${lv}`);
    setVars(node, { "--x": `${rect.x.toFixed(1)}px`, "--y": `${rect.y.toFixed(1)}px`, "--w": `${rect.w.toFixed(1)}px`, "--h": `${rect.h.toFixed(1)}px` });
    // A name shows whole with its count, or not at all; the tooltip carries both either way.
    const fit = labelFit(nd, rect, depth === 1 && lv === 0);
    if (fit.large) node.classList.add("is-large");
    if (fit.mode) {
      const tag = el("div", `tree-label is-${fit.mode}`);
      tag.append(el("span", "tree-name", label(nd)));
      if (fit.value) tag.append(el("span", "tree-value", fit.value));
      node.append(tag);
    }
    node.addEventListener("pointerenter", (event) => {
      if (event.pointerType === "mouse") hover(node, nd, path, depth);
    });
    node.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse") return;
      const share = ((nd.s / total) * 100).toFixed(nd.s / total < 0.01 ? 1 : 0);
      const what = nd.r ? `${nd.r} smaller entries` : escapeHtml(path || DATA.title);
      showTip(`<strong>${what}</strong><span>${fmt(nd.s)} lines changed</span><span>${share}% of all</span>`, event.clientX, event.clientY);
      event.stopPropagation();
    });
    node.addEventListener("pointerleave", (event) => {
      if (event.pointerType !== "mouse") return;
      hideTip();
      if (depth === 2) unreveal(node);
    });
    node.addEventListener("click", () => {
      if (depth === 2 && nd.c) {
        if (revealed === node) unreveal(node);
        else hover(node, nd, path, depth);
      }
    });
    return node;
  }

  function hover(node, nd, path, depth) {
    if (depth !== 2 || !nd.c) return;
    reveal(node, nd, path);
  }

  function reveal(node, nd, path) {
    if (revealed && revealed !== node) unreveal(revealed);
    if (revealed === node) return;
    // A folder that is nearly all one folder opens that one, so the peek shows real contents.
    let target = nd;
    let shown = path;
    while (target.c && target.c[0]?.c && target.c[0].s >= target.s * 0.85) {
      target = target.c[0];
      shown = `${shown}${target.n}/`;
    }
    const w = parseFloat(node.style.getPropertyValue("--w"));
    const h = parseFloat(node.style.getPropertyValue("--h"));
    if (w < 48 || h < 40 || !target.c) return;
    const tag = node.querySelector(":scope > .tree-label");
    const name = tag?.querySelector(".tree-name");
    if (name && shown !== path) {
      const short = shown.slice(path.length - nd.n.length - 1);
      if (textWidth(short, 12) <= w - 14) {
        name.dataset.was = name.textContent;
        name.textContent = short;
      }
    }
    const layer = el("div", "tree-reveal");
    const top = tag ? Math.min(h / 2, tag.offsetTop + tag.offsetHeight + 4) : 2;
    const kids = squarify(target.c, 2, top, w - 4, h - top - 2);
    const max = Math.max(...target.c.map((k) => k.s));
    kids.forEach((k, idx) => {
      const lv = 1 + Math.min(4, Math.floor((k.node.s / max) * 4.999));
      const kid = el("div", `tree-kid lv${lv}${isDir(k.node) ? " is-dir" : ""}`);
      setVars(kid, { "--x": `${(k.x + 1).toFixed(1)}px`, "--y": `${(k.y + 1).toFixed(1)}px`, "--w": `${Math.max(0, k.w - 2).toFixed(1)}px`, "--h": `${Math.max(0, k.h - 2).toFixed(1)}px`, "--i": idx });
      if (k.h >= 16 && textWidth(label(k.node), 11) <= k.w - 12) kid.append(el("span", "tree-name", label(k.node)));
      layer.append(kid);
    });
    node.append(layer);
    node.classList.add("is-open");
    box.classList.add("is-peeking");
    revealed = node;
  }

  function unreveal(node) {
    node.classList.remove("is-open");
    const name = node.querySelector(":scope > .tree-label .tree-name");
    if (name?.dataset.was) {
      name.textContent = name.dataset.was;
      delete name.dataset.was;
    }
    node.querySelector(".tree-reveal")?.remove();
    if (revealed === node) revealed = null;
    box.classList.remove("is-peeking");
  }

  function build(w, h, animate) {
    box.replaceChildren();
    const gap = big ? 6 : 4;
    const blocks = fitted(root.c || [root], 0, 0, w, h, gap);
    const firstLevel = [];
    const secondLevel = [];
    for (const b of blocks) {
      const rect = { x: b.x + gap / 2, y: b.y + gap / 2, w: Math.max(0, b.w - gap), h: Math.max(0, b.h - gap) };
      const path = `${rootPath}${b.node.n}${isDir(b.node) ? "/" : ""}`;
      // A folder opens into its contents where each of them can carry its name and count.
      const head = 24;
      const kids = b.node.c && rect.w > 70 && rect.h > 58 ? fitted(b.node.c, 0, 0, rect.w - 6, rect.h - head - 3, 2) : [];
      const holds = kids.length > 0 && kids.every((k) => labelFit(k.node, { w: k.w - 2, h: k.h - 2 }).mode);
      const node = nodeEl(b.node, rect, 1, path, holds ? 0 : levelOf(b.node.s));
      if (holds) {
        node.classList.add("is-holding");
        const inner = el("div", "tree-inner");
        for (const k of kids) {
          const kr = { x: k.x + 1, y: k.y + 1, w: Math.max(0, k.w - 2), h: Math.max(0, k.h - 2) };
          const kidPath = `${path}${k.node.n}${isDir(k.node) ? "/" : ""}`;
          const kid = nodeEl(k.node, kr, 2, kidPath, levelOf(k.node.s));
          inner.append(kid);
          secondLevel.push({ el: kid, rect: kr, inner: { w: rect.w - 6, h: rect.h - head - 3 } });
        }
        node.append(inner);
      }
      box.append(node);
      firstLevel.push({ el: node, rect });
    }

    if (!animate) return;

    // The split moves each block's real box, never a scale, so corners and names stay true at every frame. Every
    // top folder starts as itself and everything after it, and gives the rest away; then its contents do the same.
    // A folder's contents wait inside it as its first entry, so a folder is never an empty frame.
    const whole = el("div", "tree-whole");
    whole.append(el("span", "tree-whole-name", rootPath ? rootPath.replace(/\/$/, "") : DATA.title), el("span", "tree-whole-value", `${fmt(root.s)} lines changed`));
    box.append(whole);
    box.classList.add("is-splitting");
    const t0 = 260;
    const t1 = 840;
    const from = rests(firstLevel.map((item) => item.rect));
    firstLevel.forEach(({ el: node, rect }, idx) => {
      setVars(node, { "--z": firstLevel.length - idx });
      node.animate([boxOf(from[idx]), boxOf(rect)], { duration: 640, delay: t0 + idx * 24, easing: SPLIT, fill: "backwards" });
    });
    whole.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, delay: t0, easing: "linear", fill: "forwards" });
    const groups = new Map();
    for (const item of secondLevel) {
      const parent = item.el.closest(".tree-node.d1");
      if (!groups.has(parent)) groups.set(parent, []);
      groups.get(parent).push(item);
    }
    [...groups.values()].forEach((items, g) => {
      const kidsFrom = rests(items.map((item) => item.rect));
      items.forEach(({ el: node, rect, inner }, idx) => {
        setVars(node, { "--z": items.length - idx });
        node.animate([shareOf(kidsFrom[idx], inner), boxOf(rect)], { duration: 560, delay: t1 + g * 40 + idx * 18, easing: SPLIT, fill: "backwards" });
      });
    });
    // A name arrives once the blocks drawn over it have moved off, so it is never shown cut.
    for (const label of box.querySelectorAll(".tree-label")) {
      const d1 = firstLevel.findIndex((item) => item.el === label.closest(".d1"));
      label.animate([{ opacity: 0, transform: "translateY(3px)" }, { opacity: 1, transform: "none" }], { duration: 260, delay: label.closest(".d2") ? t1 + 480 : t0 + 540 + d1 * 24, easing: OUT, fill: "backwards" });
    }
    window.setTimeout(() => {
      whole.remove();
      box.classList.remove("is-splitting");
    }, 2000);
  }

  function render(w, h, animate = false) {
    if (w < 40 || h < 40) return;
    // A resize during the split waits for it to land, then lays out once at the new size.
    if (splitting && !animate) {
      pending = { w, h };
      return;
    }
    size = { w, h };
    revealed = null;
    const moving = animate && !calm();
    build(w, h, moving);
    if (moving) {
      splitting = true;
      window.setTimeout(() => {
        splitting = false;
        if (pending && (pending.w !== size.w || pending.h !== size.h)) render(pending.w, pending.h);
        pending = null;
      }, 2050);
    }
  }

  return {
    render,
    play() {
      if (played) return;
      played = true;
      box.classList.remove("is-waiting");
      const r = container.getBoundingClientRect();
      render(r.width, r.height, true);
    },
    get played() {
      return played;
    },
    /** Opens the biggest folder's contents, as a hover would. */
    peekBiggest() {
      const candidates = [...box.querySelectorAll(".tree-node.d2.is-dir")];
      const best = candidates.sort((a, b) => Number(b.dataset.lines) - Number(a.dataset.lines))[0];
      if (!best) return null;
      const path = best.dataset.path;
      const nd = findNode(path);
      if (nd) reveal(best, nd, path);
      return best;
    },
    closePeek() {
      if (revealed) unreveal(revealed);
    },
    box,
  };

  function findNode(path) {
    const parts = path.replace(/\/$/, "").split("/");
    let at = DATA.tree;
    for (const part of parts) {
      at = at.c?.find((k) => k.n === part);
      if (!at) return null;
    }
    return at;
  }
}
