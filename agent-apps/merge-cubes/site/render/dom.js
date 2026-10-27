// The board without WebGL: a CSS grid of cubes in the slot, colored from the same tokens, sliding for the same
// 110 ms, popping on a merge and dropping in when new. It answers the same verbs as the 3D world.
import { textFor } from "../scene/labels.js";
import { stepOf } from "../scene/tokens.js";

const SLIDE_MS = 110;

export function createDomWorld({ el, size, labelSet }) {
  const cubes = new Map();
  let n = size;
  let labels = labelSet;
  el.hidden = false;

  function place(node, r, c) {
    const pitch = 100 / n;
    node.style.setProperty("--x", `${c * 100 * (1 / 0.9)}%`);
    node.style.setProperty("--y", `${r * 100 * (1 / 0.9)}%`);
    node.style.setProperty("--cell", `${pitch * 0.9}%`);
  }

  function cells() {
    el.textContent = "";
    for (let r = 0; r < n; r += 1) {
      for (let c = 0; c < n; c += 1) {
        const cell = document.createElement("div");
        cell.className = "dom-cell";
        place(cell, r, c);
        el.append(cell);
      }
    }
  }

  function make(tile, kind) {
    const node = document.createElement("div");
    node.className = `dom-cube${kind ? ` is-${kind}` : ""}`;
    const step = stepOf(tile.value) + 1;
    node.style.setProperty("--cube-bg", `var(--cube-${step})`);
    node.style.setProperty("--cube-ink", `var(--cube-ink-${step})`);
    const text = textFor(tile.value, labels);
    node.style.setProperty("--cube-font", `calc(var(--slot-size) / ${n} * ${text.length <= 2 ? 0.42 : text.length === 3 ? 0.34 : 0.27})`);
    node.textContent = text;
    place(node, tile.r, tile.c);
    el.append(node);
    cubes.set(tile.id, node);
    return node;
  }

  function sync(board) {
    for (const node of cubes.values()) node.remove();
    cubes.clear();
    for (const t of board.tiles) make(t, "new");
  }

  cells();

  return {
    tier: "dom",
    setSlot(rect) {
      const s = Math.min(rect.width, rect.height);
      const root = document.documentElement;
      root.style.setProperty("--slot-size", `${s}px`);
      el.style.setProperty("--slot-left", `${rect.left + (rect.width - s) / 2}px`);
      el.style.setProperty("--slot-top", `${rect.top + (rect.height - s) / 2}px`);
    },
    resize() {},
    restyle() {},
    setLabels(next) {
      labels = next;
    },
    setSize(next, board) {
      n = next;
      cells();
      sync(board);
    },
    show(board) {
      sync(board);
    },
    play(result, spawned) {
      const made = new Map(result.merges.map((m) => [m.id, m]));
      for (const e of result.trace) {
        const node = cubes.get(e.id);
        if (!node) continue;
        place(node, e.to[0], e.to[1]);
        if (e.into) {
          cubes.delete(e.id);
          setTimeout(() => node.remove(), SLIDE_MS);
        }
      }
      setTimeout(() => {
        for (const m of made.values()) make(m, "merged");
        if (spawned) make(spawned, "new");
      }, SLIDE_MS);
    },
    bump() {},
    clear() {
      for (const node of cubes.values()) node.remove();
      cubes.clear();
      return Promise.resolve();
    },
    celebrate() {},
    settle() {},
    setDim() {},
    skipIntro() {},
    get busy() {
      return false;
    },
    get count() {
      return cubes.size;
    },
    frame() {},
  };
}
