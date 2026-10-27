// The flat board for a browser without WebGL: the same game drawn in SVG, with piece outlines taken from the lathe
// profiles and moves that slide by CSS transform. It answers the same calls main.js makes of the 3D table.
import { profiles, knightHead } from "../scene/profiles.js";

const NS = "http://www.w3.org/2000/svg";
const FILES = "abcdefgh";
const TYPES = { p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king" };

// A side view of a piece: the lathe profile mirrored, or the knight's head on its base.
function outline(type) {
  const prof = profiles[TYPES[type]];
  const right = prof.map(([r, y]) => `${(r * 0.95).toFixed(3)},${(-y).toFixed(3)}`);
  const left = [...prof].reverse().map(([r, y]) => `${(-r * 0.95).toFixed(3)},${(-y).toFixed(3)}`);
  let d = `M${right.join("L")}L${left.join("L")}Z`;
  if (type === "n") {
    const [sx, sy] = knightHead.start;
    d += ` M${-sx},${-sy}` + knightHead.path.map(([cx, cy, x, y]) => ` Q${-cx},${-cy} ${-x},${-y}`).join("") + "Z";
  }
  if (type === "k") d += " M-0.035,-1.35 h0.07 v-0.13 h0.065 v-0.06 h-0.065 v-0.08 h-0.07 v0.08 h-0.065 v0.06 h0.065 Z";
  return d;
}

export function iconFor(color, type) {
  const svg = `<svg xmlns="${NS}" viewBox="-0.6 -1.75 1.2 1.8"><path d="${outline(type)}" fill="${color === "w" ? "#f4f1ea" : "#24262b"}" stroke="${color === "w" ? "#8a8578" : "#0b0c0e"}" stroke-width="0.025"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export class FlatBoard {
  constructor(host) {
    this.host = host;
    this.listeners = new Set();
    this.side = "w";
    this.svg = document.createElementNS(NS, "svg");
    this.svg.setAttribute("viewBox", "0 0 8 8");
    this.svg.classList.add("flat-board");
    for (let f = 0; f < 8; f++) for (let r = 0; r < 8; r++) {
      const sq = document.createElementNS(NS, "rect");
      sq.setAttribute("x", f); sq.setAttribute("y", r); sq.setAttribute("width", 1); sq.setAttribute("height", 1);
      sq.classList.add((f + r) % 2 ? "flat-dark" : "flat-light");
      this.svg.append(sq);
    }
    this.marks = document.createElementNS(NS, "g");
    this.layer = document.createElementNS(NS, "g");
    this.svg.append(this.marks, this.layer);
    host.append(this.svg);
    this.pieces = new Map();
    this.icons = {};
    for (const c of "wb") for (const t of "pnbrqk") this.icons[c + t] = iconFor(c, t);
  }

  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }

  xy(sq) {
    const f = FILES.indexOf(sq[0]), r = Number(sq[1]) - 1;
    return this.side === "w" ? [f, 7 - r] : [7 - f, r];
  }

  draw(el, sq) {
    const [x, y] = this.xy(sq);
    el.style.setProperty("--x", x);
    el.style.setProperty("--y", y);
  }

  setPosition(rows) {
    this.layer.replaceChildren();
    this.pieces.clear();
    rows.forEach((row) => row.forEach((cell) => {
      if (!cell) return;
      const g = document.createElementNS(NS, "g");
      g.classList.add("flat-piece", cell.color === "w" ? "flat-white" : "flat-black");
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", outline(cell.type));
      p.setAttribute("transform", "translate(0.5 0.93) scale(0.56)");
      g.append(p);
      this.draw(g, cell.square);
      this.layer.append(g);
      this.pieces.set(cell.square, g);
    }));
  }

  async play(move, sound = () => {}) {
    const g = this.pieces.get(move.from);
    const capturedSquare = move.flags.includes("e") ? move.to[0] + move.from[1] : move.captured ? move.to : null;
    this.pieces.get(capturedSquare)?.remove();
    this.pieces.delete(move.from);
    if (g) { this.draw(g, move.to); this.pieces.set(move.to, g); }
    const castle = move.flags.includes("k") ? ["h", "f"] : move.flags.includes("q") ? ["a", "d"] : null;
    if (castle) {
      const rook = this.pieces.get(castle[0] + move.from[1]);
      if (rook) { this.pieces.delete(castle[0] + move.from[1]); this.draw(rook, castle[1] + move.from[1]); this.pieces.set(castle[1] + move.from[1], rook); }
    }
    if (move.promotion && g) g.firstChild.setAttribute("d", outline(move.promotion));
    await new Promise((r) => setTimeout(r, 220));
    sound(capturedSquare ? "capture" : "move");
  }

  setHints(state) {
    this.marks.replaceChildren();
    const mark = (sq, cls) => {
      const [x, y] = this.xy(sq);
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", x); r.setAttribute("y", y); r.setAttribute("width", 1); r.setAttribute("height", 1);
      r.classList.add(cls);
      this.marks.append(r);
    };
    for (const sq of state.last ?? []) mark(sq, "flat-last");
    if (state.selected) mark(state.selected, "flat-selected");
    for (const t of state.targets ?? []) mark(t.square, "flat-target");
    if (state.cursor) mark(state.cursor, "flat-cursor");
    if (this.check) mark(this.check, "flat-check");
  }

  setCheck(square) { this.check = square; }
  async mate() {}
  undim() {}
  setStage() {}

  setView(side) {
    this.side = side;
    for (const [sq, g] of this.pieces) this.draw(g, sq);
    return Promise.resolve();
  }

  pick(x, y) {
    const box = this.svg.getBoundingClientRect();
    const fx = Math.floor(((x - box.left) / box.width) * 8), fy = Math.floor(((y - box.top) / box.height) * 8);
    if (fx < 0 || fx > 7 || fy < 0 || fy > 7) return null;
    return this.side === "w" ? FILES[fx] + (8 - fy) : FILES[7 - fx] + (fy + 1);
  }

  screenOf(sq) {
    const box = this.svg.getBoundingClientRect();
    const [x, y] = this.xy(sq);
    return { x: box.left + ((x + 0.5) / 8) * box.width, y: box.top + ((y + 0.5) / 8) * box.height };
  }

  applyTheme() {}
}
