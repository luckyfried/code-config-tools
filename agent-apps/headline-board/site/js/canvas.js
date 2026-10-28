// The board's flaps drawn on one canvas, for touch screens. Each letter in each color is drawn once into an atlas from
// the same tokens the stylesheet uses; a module at rest is one copy from the atlas, and a landing is the old top
// folding down to the hinge and the new bottom dropping from it, drawn frame by frame. A phone then turns hundreds of
// modules with no layout, no paint of the page, and one layer, while the rows above it stay links.

import { DRUM, LAND_MS } from "./flaps.js";

// The share of a landing the old top takes to fold down to the hinge; the new bottom then drops and settles.
const FOLD = 0.3;
const TONES = 7;
const ATLAS_COLS = 10;
const ATLAS_ROWS = Math.ceil(DRUM.length / ATLAS_COLS);
const SLOT = new Map([...DRUM].map((letter, index) => [letter, index]));

const mix = (a, b, t) => a + (b - a) * t;
const easeIn = (t) => t * t;
const easeOut = (t) => 1 - (1 - t) * (1 - t);

// How far the new bottom has dropped at landing progress p: it falls to the stack, lifts a little, and settles, as in
// the land keyframes in board.css.
function drop(p) {
  if (p < 0.52) return easeIn((p - FOLD) / (0.52 - FOLD));
  if (p < 0.68) return mix(1, 0.95, easeOut((p - 0.52) / 0.16));
  if (p < 0.82) return mix(0.95, 1, easeIn((p - 0.68) / 0.14));
  if (p < 0.91) return mix(1, 0.99, easeOut((p - 0.82) / 0.09));
  return mix(0.99, 1, easeIn((p - 0.91) / 0.09));
}

// The shadow the falling leaf casts on the old bottom, as in the under keyframes in board.css.
function under(p) {
  if (p < 0.3) return mix(0, 0.18, p / 0.3);
  if (p < 0.48) return mix(0.18, 0.55, (p - 0.3) / 0.18);
  if (p < 0.54) return mix(0.55, 0, (p - 0.48) / 0.06);
  return 0;
}

// "rgba(255, 160, 30, 0.5) 0px 0px 6.4px" as the canvas's shadow settings; "none" as none.
function shadow(text) {
  const match = /^(rgba?\([^)]*\)|#[0-9a-f]+|[a-z]+)\s+(-?[\d.]+)px\s+(-?[\d.]+)px(?:\s+([\d.]+)px)?/i.exec(text || "");
  if (!match || match[1] === "none") return null;
  return { color: match[1], x: Number(match[2]), y: Number(match[3]), blur: Number(match[4] || 0) };
}

// A module drawn on the board's canvas. Flaps turns it exactly as it turns a module in the page.
export class PaintedTile {
  constructor(board, kind = "") {
    this.board = board;
    this.kind = kind;
    this.letter = " ";
    this.tone = 0;
    this.queue = [];
    this.nextTone = 0;
    this.at = 0;
    this.toneShown = 0;
    this.from = " ";
    this.fromTone = 0;
    this.landAt = -1;
    this.x = 0;
    this.y = 0;
  }

  snap(letter, tone = 0) {
    this.letter = letter;
    this.queue.length = 0;
    this.tone = tone;
    this.nextTone = tone;
    this.toneShown = tone;
    this.landAt = -1;
    this.board.landing.delete(this);
    this.board.dirty.add(this);
  }

  // A spin shows the next letter in place; the landing folds.
  turn(from, to, last, light, now) {
    this.fromTone = this.toneShown;
    this.toneShown = this.tone;
    if (last) {
      this.from = from;
      this.landAt = now;
      this.board.landing.add(this);
    } else {
      this.landAt = -1;
      this.board.landing.delete(this);
      this.board.dirty.add(this);
    }
  }

  rest() {
    if (this.landAt < 0) this.board.dirty.add(this);
  }
}

export class PaintedBoard {
  constructor(host) {
    this.host = host;
    this.canvas = document.createElement("canvas");
    this.canvas.className = "flaps";
    this.canvas.setAttribute("aria-hidden", "true");
    this.ctx = this.canvas.getContext("2d");
    // One atlas per color, each holding the whole drum, drawn in one go the first time the color is needed, so no
    // atlas changes while the board turns.
    this.atlases = [];
    this.probe = document.createElement("span");
    this.probe.className = "t probe";
    this.probe.setAttribute("aria-hidden", "true");
    this.probe.innerHTML = '<span class="h u"><b>A</b></span>';
    this.tiles = [];
    this.dirty = new Set();
    this.landing = new Set();
    this.looks = [];
    this.cw = 0;
    this.ch = 0;
    this.dpr = 1;
  }

  // The canvas and the probe go first in the rows' container, under the rows.
  mount() {
    this.host.prepend(this.canvas, this.probe);
  }

  // Places every module of `rows` on the canvas, from where the page laid out each line.
  layout(rows, shape) {
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const box = this.host.getBoundingClientRect();
    const width = Math.round(box.width * dpr);
    const height = Math.round(box.height * dpr);
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    } else {
      this.ctx.clearRect(0, 0, width, height);
    }
    const cw = Math.round(shape.tw * dpr);
    const ch = Math.round(shape.th * dpr);
    if (cw !== this.cw || ch !== this.ch || dpr !== this.dpr) {
      this.cw = cw;
      this.ch = ch;
      this.dpr = dpr;
      this.restyle();
    }
    this.tiles = [];
    this.dirty.clear();
    this.landing.clear();
    const pitch = shape.tw + shape.tgap;
    for (const row of rows) {
      const lines = row.el.querySelectorAll(".line");
      const spots = [...lines].map((line) => line.getBoundingClientRect());
      for (const tile of row.tiles) {
        const spot = spots[tile.line];
        tile.x = Math.round((spot.left - box.left + tile.col * pitch) * dpr);
        tile.y = Math.round((spot.top - box.top) * dpr);
        tile.landAt = -1;
        this.tiles.push(tile);
        this.dirty.add(tile);
      }
    }
  }

  // Reads the look from the stylesheet again (a theme or a light/dark change) and redraws every module.
  restyle() {
    this.looks = [];
    for (let tone = 0; tone < TONES; tone += 1) {
      this.probe.className = tone ? `t probe tag tone-${tone}` : "t probe";
      const style = getComputedStyle(this.probe);
      const glyph = getComputedStyle(this.probe.querySelector("b"));
      const token = (name) => style.getPropertyValue(name).trim();
      this.looks.push({
        top: token("--flap-top"),
        top2: token("--flap-top-2"),
        bot: token("--flap-bot"),
        bot2: token("--flap-bot-2"),
        edge: token("--flap-edge"),
        hinge: token("--hinge"),
        shade: token("--shade"),
        radius: parseFloat(style.borderTopLeftRadius) || 3,
        ink: glyph.color,
        glow: shadow(glyph.textShadow),
        font: `${glyph.fontWeight} ${parseFloat(glyph.fontSize) * this.dpr}px ${glyph.fontFamily}`,
      });
    }
    this.atlases = [];
    const mid = Math.round(this.ch / 2);
    this.underFill = this.ctx.createLinearGradient(0, 0, 0, this.ch - mid);
    this.underFill.addColorStop(0, this.looks[0].shade);
    this.underFill.addColorStop(0.85, "transparent");
    for (const tile of this.tiles) this.dirty.add(tile);
  }

  // The atlas cell holding `letter` at rest in `tone`.
  cell(letter, tone) {
    const atlas = this.atlases[tone] || this.drawAtlas(tone);
    const index = SLOT.get(letter) ?? 0;
    return { img: atlas, x: (index % ATLAS_COLS) * this.cw, y: Math.floor(index / ATLAS_COLS) * this.ch };
  }

  drawAtlas(tone) {
    const atlas = document.createElement("canvas");
    atlas.width = this.cw * ATLAS_COLS;
    atlas.height = this.ch * ATLAS_ROWS;
    const g = atlas.getContext("2d");
    const look = this.looks[tone] || this.looks[0];
    [...DRUM].forEach((letter, index) => {
      this.drawCell(g, letter, look, { x: (index % ATLAS_COLS) * this.cw, y: Math.floor(index / ATLAS_COLS) * this.ch });
    });
    this.atlases[tone] = atlas;
    return atlas;
  }

  drawCell(g, letter, look, { x, y }) {
    const { cw, ch, dpr } = this;
    const half = ch / 2 - 0.5 * dpr;
    g.save();
    g.translate(x, y);
    g.clearRect(0, 0, cw, ch);
    g.beginPath();
    g.roundRect(0, 0, cw, ch, look.radius * dpr);
    g.clip();
    g.fillStyle = look.hinge;
    g.fillRect(0, 0, cw, ch);
    const top = g.createLinearGradient(0, 0, 0, half);
    top.addColorStop(0, look.top);
    top.addColorStop(1, look.top2);
    g.fillStyle = top;
    g.fillRect(0, 0, cw, half);
    g.fillStyle = look.edge;
    g.fillRect(0, 0, cw, dpr);
    const low = ch - half - dpr;
    const bottom = g.createLinearGradient(0, half + dpr, 0, ch);
    bottom.addColorStop(0, look.bot);
    bottom.addColorStop(1, look.bot2);
    g.fillStyle = bottom;
    g.fillRect(0, half + dpr, cw, low);
    if (look !== this.looks[0]) {
      const shade = g.createLinearGradient(0, half + dpr, 0, ch);
      shade.addColorStop(0, look.shade);
      shade.addColorStop(0.7, "transparent");
      g.globalAlpha = 0.18;
      g.fillStyle = shade;
      g.fillRect(0, half + dpr, cw, low);
      g.globalAlpha = 1;
    }
    if (letter !== " ") {
      g.font = look.font;
      g.textAlign = "center";
      g.textBaseline = "alphabetic";
      const metrics = g.measureText(letter);
      const ascent = metrics.fontBoundingBoxAscent;
      const descent = metrics.fontBoundingBoxDescent;
      if (look.glow) {
        g.shadowColor = look.glow.color;
        g.shadowOffsetX = look.glow.x * dpr;
        g.shadowOffsetY = look.glow.y * dpr;
        g.shadowBlur = look.glow.blur * dpr;
      }
      g.fillStyle = look.ink;
      g.fillText(letter, cw / 2, (ch - ascent - descent) / 2 + ascent);
      g.shadowColor = "transparent";
      // The hinge runs across the letter, as on a module at rest in the page.
      g.fillStyle = look.hinge;
      g.fillRect(0, half, cw, dpr);
    }
    g.restore();
  }

  // One frame: modules that changed are copied from the atlas, and every landing module draws its fold.
  draw(now) {
    if (!this.dirty.size && !this.landing.size) return;
    const ctx = this.ctx;
    const { cw, ch } = this;
    for (const tile of this.landing) {
      if (now - tile.landAt >= LAND_MS) {
        this.landing.delete(tile);
        tile.landAt = -1;
        this.dirty.add(tile);
      }
    }
    for (const tile of this.dirty) {
      if (this.landing.has(tile)) continue;
      const spot = this.cell(tile.letter, tile.toneShown);
      ctx.clearRect(tile.x, tile.y, cw, ch);
      ctx.drawImage(spot.img, spot.x, spot.y, cw, ch, tile.x, tile.y, cw, ch);
    }
    this.dirty.clear();
    if (!this.landing.size) return;
    const mid = Math.round(ch / 2);
    const low = ch - mid;
    const shade = this.looks[0].shade;
    for (const tile of this.landing) {
      const p = Math.max(0, (now - tile.landAt) / LAND_MS);
      const old = this.cell(tile.from, tile.fromTone);
      const next = this.cell(tile.letter, tile.toneShown);
      const { x, y } = tile;
      ctx.clearRect(x, y, cw, ch);
      ctx.drawImage(next.img, next.x, next.y, cw, mid, x, y, cw, mid);
      ctx.drawImage(old.img, old.x, old.y + mid, cw, low, x, y + mid, cw, low);
      const dark = under(p);
      if (dark > 0) {
        ctx.globalAlpha = dark;
        ctx.fillStyle = this.underFill;
        ctx.translate(x, y + mid);
        ctx.fillRect(0, 0, cw, low);
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalAlpha = 1;
      }
      if (p < FOLD) {
        const fold = 1 - easeIn(p / FOLD);
        const h = mid * fold;
        if (h >= 1) {
          ctx.drawImage(old.img, old.x, old.y, cw, mid, x, y + mid - h, cw, h);
          ctx.globalAlpha = 0.34 * (1 - fold);
          ctx.fillStyle = shade;
          ctx.fillRect(x, y + mid - h, cw, h);
          ctx.globalAlpha = 1;
        }
      } else {
        const fall = drop(p);
        const h = low * fall;
        if (h >= 1) {
          ctx.drawImage(next.img, next.x, next.y + mid, cw, low, x, y + mid, cw, h);
          if (fall < 1) {
            ctx.globalAlpha = 0.22 * (1 - fall);
            ctx.fillStyle = shade;
            ctx.fillRect(x, y + mid, cw, h);
            ctx.globalAlpha = 1;
          }
        }
      }
    }
  }
}
