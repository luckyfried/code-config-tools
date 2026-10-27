// Card faces and backs, drawn from SVG suit paths onto a 2D canvas. The WebGL table packs
// them into one atlas; the CSS 3D table turns each into an image. Both draw the same card.

import { rankOf, suitOf, isRed, RANK_NAMES } from "./game/rules.js";

// Suit shapes in a 100 x 100 box, as SVG path data.
export const SUIT_PATHS = [
  // spade
  "M50 2 C58 20 98 40 98 64 C98 78 87 88 74 88 C65 88 58 84 54 77 C55 88 60 94 70 99 L30 99 C40 94 45 88 46 77 C42 84 35 88 26 88 C13 88 2 78 2 64 C2 40 42 20 50 2 Z",
  // heart
  "M50 96 C24 72 2 52 2 30 C2 14 14 3 28 3 C39 3 46 10 50 19 C54 10 61 3 72 3 C86 3 98 14 98 30 C98 52 76 72 50 96 Z",
  // diamond
  "M50 1 C59 19 72 35 88 50 C72 65 59 81 50 99 C41 81 28 65 12 50 C28 35 41 19 50 1 Z",
  // club
  "M50 4 C62 4 72 14 72 26 C72 33 69 38 65 42 C68 41 71 40 74 40 C87 40 97 50 97 63 C97 76 87 86 74 86 C64 86 57 81 54 73 C55 86 60 93 70 99 L30 99 C40 93 45 86 46 73 C43 81 36 86 26 86 C13 86 3 76 3 63 C3 50 13 40 26 40 C29 40 32 41 35 42 C31 38 28 33 28 26 C28 14 38 4 50 4 Z",
];

const CROWN = "M8 78 L4 30 L26 52 L50 14 L74 52 L96 30 L92 78 Z";
const TIARA = "M10 78 C10 52 22 36 34 46 C38 28 46 20 50 20 C54 20 62 28 66 46 C78 36 90 52 90 78 Z";
const PLUME = "M50 8 C66 26 74 46 70 66 C68 74 62 80 50 84 C38 80 32 74 30 66 C26 46 34 26 50 8 Z";

let pathCache = null;
function suitPath(suit) {
  if (!pathCache) pathCache = SUIT_PATHS.map((d) => new Path2D(d));
  return pathCache[suit];
}
const shapeCache = new Map();
function shape(d) {
  if (!shapeCache.has(d)) shapeCache.set(d, new Path2D(d));
  return shapeCache.get(d);
}

// Pip centers, as fractions of the pip area (x: 0 left, 0.5 middle, 1 right; y: 0 top, 1 bottom).
const PIPS = {
  2: [[0.5, 0], [0.5, 1]],
  3: [[0.5, 0], [0.5, 0.5], [0.5, 1]],
  4: [[0, 0], [1, 0], [0, 1], [1, 1]],
  5: [[0, 0], [1, 0], [0.5, 0.5], [0, 1], [1, 1]],
  6: [[0, 0], [1, 0], [0, 0.5], [1, 0.5], [0, 1], [1, 1]],
  7: [[0, 0], [1, 0], [0.5, 0.25], [0, 0.5], [1, 0.5], [0, 1], [1, 1]],
  8: [[0, 0], [1, 0], [0.5, 0.25], [0, 0.5], [1, 0.5], [0.5, 0.75], [0, 1], [1, 1]],
  9: [[0, 0], [1, 0], [0, 1 / 3], [1, 1 / 3], [0.5, 0.5], [0, 2 / 3], [1, 2 / 3], [0, 1], [1, 1]],
  10: [[0, 0], [1, 0], [0.5, 1 / 6], [0, 1 / 3], [1, 1 / 3], [0, 2 / 3], [1, 2 / 3], [0.5, 5 / 6], [0, 1], [1, 1]],
};

/** Card proportions: 63 x 88, as the table's cards are. */
export const CARD_ASPECT = 88 / 63;

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawSuit(ctx, suit, cx, cy, size, flipped = false) {
  ctx.save();
  ctx.translate(cx, cy);
  if (flipped) ctx.rotate(Math.PI);
  ctx.scale(size / 100, size / 100);
  ctx.translate(-50, -50);
  ctx.fill(suitPath(suit));
  ctx.restore();
}

function drawShape(ctx, d, cx, cy, size) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(size / 100, size / 100);
  ctx.translate(-50, -50);
  ctx.fill(shape(d));
  ctx.restore();
}

/**
 * Draws one card face into the box (x, y, w, h).
 * `look` holds the colors and fonts read from the theme's tokens.
 */
export function drawFace(ctx, card, x, y, w, h, look) {
  const rank = rankOf(card);
  const suit = suitOf(card);
  const ink = isRed(card) ? look.red : look.black;
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = look.face;
  ctx.fillRect(0, 0, w, h);
  // A hairline inside the edge, as printed cards carry.
  ctx.strokeStyle = look.hairline;
  ctx.lineWidth = Math.max(1, w * 0.006);
  roundRect(ctx, w * 0.025, w * 0.025, w * 0.95, h - w * 0.05, w * 0.06);
  ctx.stroke();

  ctx.fillStyle = ink;
  // The index: a large rank with its suit beside it, readable where a fanned card shows only its top.
  const rankText = RANK_NAMES[rank];
  const indexSize = h * 0.2;
  ctx.font = `700 ${indexSize}px ${look.indexFont}`;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  const tight = rankText === "10" ? -w * 0.02 : 0;
  ctx.save();
  if (rankText === "10") {
    ctx.translate(w * 0.05, 0);
    ctx.scale(0.86, 1);
    ctx.fillText(rankText, 0, h * 0.195);
  } else {
    ctx.fillText(rankText, w * 0.065, h * 0.195);
  }
  ctx.restore();
  const rankWidth = rankText === "10" ? ctx.measureText("10").width * 0.86 + tight : ctx.measureText(rankText).width;
  const indexSuit = h * 0.135;
  drawSuit(ctx, suit, Math.min(w * 0.9, w * 0.07 + rankWidth + indexSuit * 0.62), h * 0.118, indexSuit);

  // The small index in the far corner.
  ctx.save();
  ctx.translate(w, h);
  ctx.rotate(Math.PI);
  ctx.font = `700 ${h * 0.1}px ${look.indexFont}`;
  ctx.textAlign = "center";
  ctx.fillText(rankText, w * 0.1, h * 0.1);
  drawSuit(ctx, suit, w * 0.1, h * 0.155, h * 0.065);
  ctx.restore();

  if (rank === 1) {
    const size = suit === 0 ? w * 0.56 : w * 0.46;
    if (suit === 0) {
      ctx.strokeStyle = ink;
      ctx.lineWidth = w * 0.008;
      ctx.beginPath();
      ctx.arc(w * 0.5, h * 0.58, size * 0.62, 0, Math.PI * 2);
      ctx.stroke();
    }
    drawSuit(ctx, suit, w * 0.5, h * 0.58, size);
  } else if (rank <= 10) {
    const left = w * 0.3;
    const right = w * 0.7;
    const topY = h * 0.335;
    const bottomY = h * 0.86;
    const pip = w * (rank >= 9 ? 0.17 : 0.19);
    for (const [px, py] of PIPS[rank]) {
      const cx = left + (right - left) * px;
      const cy = topY + (bottomY - topY) * py;
      drawSuit(ctx, suit, cx, cy, pip, py > 0.5);
    }
  } else {
    drawCourt(ctx, card, w, h, look, ink);
  }
  ctx.restore();
}

function drawCourt(ctx, card, w, h, look, ink) {
  const rank = rankOf(card);
  const suit = suitOf(card);
  const px = w * 0.2;
  const py = h * 0.27;
  const pw = w * 0.6;
  const ph = h * 0.64;
  ctx.fillStyle = look.courtBg;
  roundRect(ctx, px, py, pw, ph, w * 0.03);
  ctx.fill();
  // Fine hatching, the engraved ground of a court card.
  ctx.save();
  roundRect(ctx, px, py, pw, ph, w * 0.03);
  ctx.clip();
  ctx.strokeStyle = look.courtLine;
  ctx.lineWidth = Math.max(1, w * 0.004);
  ctx.beginPath();
  for (let d = -ph; d < pw + ph; d += w * 0.035) {
    ctx.moveTo(px + d, py);
    ctx.lineTo(px + d - ph, py + ph);
  }
  ctx.stroke();
  ctx.restore();
  ctx.strokeStyle = ink;
  ctx.lineWidth = w * 0.012;
  roundRect(ctx, px, py, pw, ph, w * 0.03);
  ctx.stroke();
  ctx.lineWidth = w * 0.005;
  roundRect(ctx, px + w * 0.025, py + w * 0.025, pw - w * 0.05, ph - w * 0.05, w * 0.02);
  ctx.stroke();

  const cx = w * 0.5;
  // Crown or plume above the letter, in the court's gold.
  ctx.fillStyle = look.court;
  drawShape(ctx, rank === 13 ? CROWN : rank === 12 ? TIARA : PLUME, cx, py + ph * 0.2, pw * 0.42);
  ctx.strokeStyle = ink;
  ctx.lineWidth = w * 0.006;
  ctx.save();
  ctx.translate(cx - pw * 0.21, py + ph * 0.2 - pw * 0.21);
  ctx.scale((pw * 0.42) / 100, (pw * 0.42) / 100);
  ctx.stroke(shape(rank === 13 ? CROWN : rank === 12 ? TIARA : PLUME));
  ctx.restore();

  ctx.fillStyle = ink;
  ctx.font = `italic 400 ${ph * 0.42}px ${look.courtFont}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(RANK_NAMES[rank], cx, py + ph * 0.72);
  drawSuit(ctx, suit, cx, py + ph * 0.86, pw * 0.2);
}

/** The card back: classic, lattice, monogram, or the person's own image. */
export function drawBack(ctx, x, y, w, h, look, style, initials = "", image = null) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = look.backFrame;
  ctx.fillRect(0, 0, w, h);
  const m = w * 0.06;
  const iw = w - m * 2;
  const ih = h - m * 2;
  ctx.fillStyle = look.back;
  roundRect(ctx, m, m, iw, ih, w * 0.04);
  ctx.fill();
  ctx.save();
  roundRect(ctx, m, m, iw, ih, w * 0.04);
  ctx.clip();
  if (style === "image" && image) {
    const scale = Math.max(iw / image.width, ih / image.height);
    const dw = image.width * scale;
    const dh = image.height * scale;
    ctx.drawImage(image, m + (iw - dw) / 2, m + (ih - dh) / 2, dw, dh);
  } else if (style === "lattice") {
    ctx.strokeStyle = look.backInk;
    ctx.lineWidth = w * 0.022;
    const step = w * 0.16;
    ctx.beginPath();
    for (let d = -h; d < w + h; d += step) {
      ctx.moveTo(d, 0);
      ctx.lineTo(d + h, h);
      ctx.moveTo(d, h);
      ctx.lineTo(d + h, 0);
    }
    ctx.stroke();
    ctx.fillStyle = look.backFrame;
    for (let row = -1; row * step * 0.5 < h + step; row += 1) {
      for (let col = -1; col * step < w + step; col += 1) {
        const ox = (row % 2 === 0 ? 0 : step / 2) + col * step;
        const oy = row * step * 0.5;
        ctx.beginPath();
        ctx.arc(ox, oy, w * 0.016, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  } else {
    // Classic: a fine crosshatch with a medallion, or a monogram ring.
    ctx.strokeStyle = look.backInk;
    ctx.lineWidth = Math.max(1, w * 0.007);
    const step = w * 0.045;
    ctx.beginPath();
    for (let d = -h; d < w + h; d += step) {
      ctx.moveTo(d, 0);
      ctx.lineTo(d + h, h);
      ctx.moveTo(d, h);
      ctx.lineTo(d + h, 0);
    }
    ctx.stroke();
    const cx = w / 2;
    const cy = h / 2;
    ctx.fillStyle = look.back;
    ctx.beginPath();
    ctx.ellipse(cx, cy, iw * 0.34, ih * 0.27, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = look.backInk;
    ctx.lineWidth = w * 0.014;
    ctx.stroke();
    ctx.lineWidth = w * 0.006;
    ctx.beginPath();
    ctx.ellipse(cx, cy, iw * 0.3, ih * 0.235, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = look.backInk;
    if (style === "monogram" && initials) {
      ctx.font = `italic 400 ${ih * (initials.length > 2 ? 0.17 : 0.22)}px ${look.courtFont}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(initials, cx, cy + ih * 0.01);
    } else {
      const s = w * 0.15;
      drawSuit(ctx, 0, cx, cy - s * 0.62, s);
      drawSuit(ctx, 1, cx + s * 0.62, cy, s);
      drawSuit(ctx, 3, cx - s * 0.62, cy, s);
      drawSuit(ctx, 2, cx, cy + s * 0.62, s);
    }
  }
  ctx.restore();
  ctx.strokeStyle = look.backInk;
  ctx.lineWidth = w * 0.01;
  roundRect(ctx, m, m, iw, ih, w * 0.04);
  ctx.stroke();
  ctx.restore();
}

/** The paper edge of a card, seen when it turns or in the side of a stack. */
export function drawEdge(ctx, x, y, w, h, look) {
  ctx.fillStyle = look.edge;
  ctx.fillRect(x, y, w, h);
}

/** The initials for a monogram back: "Ada Lovelace" makes "AL". */
export function initialsOf(name) {
  return String(name || "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3)
    .map((part) => part[0].toUpperCase())
    .join("");
}

/** Reads the card colors and fonts from the theme's tokens. */
export function cardLook(read) {
  return {
    face: read("--card-face"),
    hairline: read("--card-hairline"),
    black: read("--card-ink"),
    red: read("--card-red"),
    court: read("--card-court"),
    courtBg: read("--card-court-ground"),
    courtLine: read("--card-court-line"),
    back: read("--card-back"),
    backInk: read("--card-back-ink"),
    backFrame: read("--card-back-frame"),
    edge: read("--card-edge"),
    indexFont: read("--font-card"),
    courtFont: read("--font-display"),
  };
}
