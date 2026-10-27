// The table without WebGL: the same faces, flips, and moves on CSS preserve-3d transforms.
// Every live value goes through a custom property; the stylesheet does the transforms.
// The cascade is WebGL's alone, so a win here goes straight to the win card.

import { drawFace, drawBack, drawEdge } from "../faces.js";
import { paintPrint as paintFeltPrint } from "../scene/table.js";

const COLS = 8;
const ROWS = 7;

export function createCss3dRenderer({ host, cardCssWidth }) {
  const root = document.createElement("div");
  root.className = "css-table";
  root.setAttribute("aria-hidden", "true");
  const print = document.createElement("canvas");
  print.className = "css-print";
  root.appendChild(print);
  const cards = [];
  for (let i = 0; i < 52; i += 1) {
    const el = document.createElement("div");
    el.className = "css-card";
    const front = document.createElement("div");
    front.className = "css-face css-front";
    const back = document.createElement("div");
    back.className = "css-face css-back";
    el.append(front, back);
    el.style.setProperty("--cell-x", String(i % COLS));
    el.style.setProperty("--cell-y", String(Math.floor(i / COLS)));
    root.appendChild(el);
    cards.push(el);
  }
  const halos = {};
  for (const name of ["hintFrom", "hintTo", "cursor"]) {
    const el = document.createElement("div");
    el.className = `css-halo css-halo--${name}`;
    root.appendChild(el);
    halos[name] = el;
  }
  host.appendChild(root);

  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const cellW = Math.max(120, Math.min(320, Math.ceil(cardCssWidth * ratio * 2)));
  const cellH = Math.round((cellW * 88) / 63);
  const atlas = document.createElement("canvas");
  atlas.width = cellW * COLS;
  atlas.height = cellH * ROWS;
  let atlasUrl = null;
  let layout = null;
  const view = { pxW: 1, pxH: 1 };
  const fakeTable = { printCanvas: print, printTexture: { needsUpdate: false } };

  function paintAtlas(look, back) {
    const ctx = atlas.getContext("2d");
    for (let cell = 0; cell < 54; cell += 1) {
      const x = (cell % COLS) * cellW;
      const y = Math.floor(cell / COLS) * cellH;
      if (cell < 52) drawFace(ctx, cell, x, y, cellW, cellH, look);
      else if (cell === 52) drawBack(ctx, x, y, cellW, cellH, look, back.style, back.initials, back.image);
      else drawEdge(ctx, x, y, cellW, cellH, look);
    }
    atlas.toBlob((blob) => {
      if (!blob) return;
      if (atlasUrl) URL.revokeObjectURL(atlasUrl);
      atlasUrl = URL.createObjectURL(blob);
      root.style.setProperty("--atlas", `url("${atlasUrl}")`);
    });
  }

  const api = {
    kind: "css3d",
    dirty: true,
    setLayout(next, pxW, pxH) {
      layout = next;
      view.pxW = pxW;
      view.pxH = pxH;
      root.style.setProperty("--card-w", `${next.cardW}px`);
      root.style.setProperty("--card-h", `${next.cardH}px`);
      api.dirty = true;
    },
    applyTheme(tok, look, back) {
      paintAtlas(look, back);
      api.dirty = true;
    },
    repaintCards(look, back) {
      paintAtlas(look, back);
    },
    paintPrint(tok, info) {
      if (!layout) return;
      paintFeltPrint(fakeTable, layout, view, tok, info);
    },
    setHalos(spec) {
      for (const [name, el] of Object.entries(halos)) {
        const h = spec[name];
        el.classList.toggle("is-on", !!h);
        if (!h) continue;
        el.style.setProperty("--x", h.x.toFixed(1));
        el.style.setProperty("--y", (h.y - (layout ? layout.scroll || 0 : 0)).toFixed(1));
        el.style.setProperty("--o", String(h.power ?? 1));
      }
    },
    startCascade(motion, state, opts) {
      if (opts.onDone) opts.onDone();
    },
    stopCascade() {},
    stepCascade() {
      return false;
    },
    cascadeRunning: false,
    draw(motion) {
      const scale = layout ? layout.scale : 1;
      const scroll = layout ? layout.scroll || 0 : 0;
      for (let i = 0; i < 52; i += 1) {
        const el = cards[i];
        const z = motion.z[i] + motion.lift[i];
        const rise = Math.max(0, z - motion.rz[i]);
        el.style.setProperty("--x", motion.x[i].toFixed(1));
        el.style.setProperty("--y", (motion.y[i] - scroll - z * scale * 0.24).toFixed(1));
        el.style.setProperty("--z", (z * scale).toFixed(1));
        el.style.setProperty("--ry", `${motion.flip[i].toFixed(3)}rad`);
        el.style.setProperty("--rx", `${(-motion.tiltX[i]).toFixed(3)}rad`);
        el.style.setProperty("--rz", `${motion.rot[i].toFixed(3)}rad`);
        el.style.setProperty("--s", (1 + Math.min(0.08, rise * 0.0024)).toFixed(3));
        el.style.setProperty("--o", motion.visible[i] ? motion.opacity[i].toFixed(2) : "0");
        el.style.setProperty("--lift", Math.min(1, rise / 30).toFixed(2));
      }
      api.dirty = false;
    },
  };
  return api;
}
