// Where every pile sits, in CSS pixels on the screen, for the table area the page gives it.
// The phone gets seven columns across its width; the desktop a fixed card size that fills
// the felt beside the rail. Card positions are centers; z is height above the felt in table units.

import { CARD_ASPECT } from "../faces.js";

/** The camera looks at the felt from this many degrees off straight down, so a stack shows its edge. */
export const TILT_DEG = 14;
const COS_TILT = Math.cos((TILT_DEG * Math.PI) / 180);

/** A card's thickness and the step between stacked cards, in table units (a card is 63 wide). */
export const CARD_THICK = 0.6;
const STACK_STEP = 0.64;
const FAN_STEP = 0.72;

export const PILES = ["stock", "waste", "f0", "f1", "f2", "f3", "t0", "t1", "t2", "t3", "t4", "t5", "t6"];

// A small, fixed scatter per card so a stack looks hand-squared rather than machine-stacked.
const JITTER = Array.from({ length: 52 }, (_, i) => {
  const a = Math.sin(i * 12.9898) * 43758.5453;
  const b = Math.sin(i * 78.233) * 12543.1234;
  const c = Math.sin(i * 39.425) * 24634.6345;
  return [a - Math.floor(a) - 0.5, b - Math.floor(b) - 0.5, c - Math.floor(c) - 0.5];
});

/**
 * Builds the layout for a table area { x, y, w, h } in CSS pixels.
 * `compact` is the phone's portrait arrangement.
 */
export function makeLayout(area, { compact, draw }) {
  const pad = compact ? Math.max(6, Math.round(area.w * 0.022)) : Math.round(Math.min(48, Math.max(16, area.w * 0.035)));
  const gapRatio = compact ? 0.11 : 0.2;
  const byWidth = (area.w - pad * 2) / (7 + 6 * gapRatio);
  const heightNeed = (compact ? 4.3 : 4.5) * CARD_ASPECT * COS_TILT;
  const byHeight = (area.h - pad * 2) / heightNeed;
  const cardW = Math.max(28, Math.floor(Math.min(byWidth, byHeight)));
  const cardH = cardW * CARD_ASPECT * COS_TILT;
  const gap = Math.round(cardW * gapRatio);
  const gridW = cardW * 7 + gap * 6;
  const left = area.x + Math.round((area.w - gridW) / 2);
  const topY = area.y + pad + (compact ? 2 : Math.round(cardH * 0.08));
  const rowGap = Math.round(cardH * (compact ? 0.2 : 0.22));
  const colX = (c) => left + c * (cardW + gap) + cardW / 2;
  const anchors = {
    stock: { x: colX(0), y: topY + cardH / 2 },
    waste: { x: colX(1), y: topY + cardH / 2 },
  };
  for (let f = 0; f < 4; f += 1) anchors[`f${f}`] = { x: colX(3 + f), y: topY + cardH / 2 };
  const tabTop = topY + cardH + rowGap;
  for (let t = 0; t < 7; t += 1) anchors[`t${t}`] = { x: colX(t), y: tabTop + cardH / 2 };
  return {
    area,
    compact,
    draw,
    pad,
    cardW,
    cardH,
    gap,
    left,
    gridW,
    anchors,
    tabTop,
    bottom: area.y + area.h - pad,
    downGap: cardH * (compact ? 0.17 : 0.11),
    upGap: cardH * (compact ? 0.33 : 0.25),
    minDown: cardH * 0.06,
    minUp: cardH * (compact ? 0.19 : 0.17),
    wasteFan: cardW * (compact ? 0.24 : 0.3),
    // Pixels per table unit: a card is 63 units wide.
    scale: cardW / 63,
    cosTilt: COS_TILT,
    scrollMax: 0,
  };
}

/** The face-down and face-up steps for one column so it ends above the table's bottom edge. */
export function columnSteps(layout, cards, up) {
  const down = cards.filter((c) => !up[c]).length;
  const ups = cards.length - down;
  let dg = layout.downGap;
  let ug = layout.upGap;
  const room = layout.bottom - layout.tabTop - layout.cardH;
  const need = () => down * dg + Math.max(0, ups - 1) * ug;
  if (need() > room && ups > 1) ug = Math.max(layout.minUp, (room - down * dg) / (ups - 1));
  if (need() > room && down > 0) dg = Math.max(layout.minDown, (room - Math.max(0, ups - 1) * ug) / down);
  return { dg, ug, overflow: Math.max(0, need() - room) };
}

/**
 * Where every card rests for a state: an array of 52 { pile, index, x, y, z, up, rot }.
 * Also sets layout.scrollMax, how far a tall column runs past the bottom.
 */
export function restTargets(layout, state) {
  const out = new Array(52);
  const put = (card, pile, index, x, y, z, rot) => {
    const j = JITTER[card];
    out[card] = { pile, index, x, y, z, up: !!state.up[card], rot, shade: 1 };
    return j;
  };
  const stackJitter = (card) => JITTER[card];
  const piled = (pile, cards) => {
    const a = layout.anchors[pile];
    cards.forEach((card, i) => {
      const j = stackJitter(card);
      const scatter = layout.cardW * 0.012;
      put(card, pile, i, a.x + j[0] * scatter, a.y + j[1] * scatter, i * STACK_STEP, j[2] * 0.02);
      // A stack casts one shadow, from its bottom card; the rest would only darken it.
      if (i > 0) out[card].shade = 0;
    });
  };
  piled("stock", state.stock);
  for (let f = 0; f < 4; f += 1) piled(`f${f}`, state.foundations[f]);
  // The waste: in draw three, the last three turned fan out to the right.
  const wa = layout.anchors.waste;
  const fanFrom = layout.draw === 3 ? Math.max(0, state.waste.length - 3) : state.waste.length;
  state.waste.forEach((card, i) => {
    const j = stackJitter(card);
    const shift = i >= fanFrom ? (i - fanFrom) * layout.wasteFan : 0;
    put(card, "waste", i, wa.x + shift + j[0] * layout.cardW * 0.01, wa.y + j[1] * layout.cardW * 0.01, i * STACK_STEP, j[2] * 0.016);
    if (i > 0 && i < fanFrom + 1) out[card].shade = 0;
  });
  let overflow = 0;
  for (let t = 0; t < 7; t += 1) {
    const cards = state.tableau[t];
    const a = layout.anchors[`t${t}`];
    const { dg, ug, overflow: over } = columnSteps(layout, cards, state.up);
    overflow = Math.max(overflow, over);
    let y = a.y;
    cards.forEach((card, i) => {
      const j = JITTER[card];
      put(card, `t${t}`, i, a.x + j[0] * layout.cardW * 0.012, y, i * FAN_STEP, j[2] * 0.012);
      y += state.up[card] ? ug : dg;
    });
  }
  layout.scrollMax = Math.ceil(overflow + (overflow > 0 ? layout.pad : 0));
  return out;
}

/** The rectangle a card at a target covers, for hit tests: { x0, y0, x1, y1 }. */
export function cardRect(layout, t) {
  return { x0: t.x - layout.cardW / 2, y0: t.y - layout.cardH / 2, x1: t.x + layout.cardW / 2, y1: t.y + layout.cardH / 2 };
}

/** The rectangle of an empty pile's spot. */
export function pileRect(layout, pile) {
  const a = layout.anchors[pile];
  return { x0: a.x - layout.cardW / 2, y0: a.y - layout.cardH / 2, x1: a.x + layout.cardW / 2, y1: a.y + layout.cardH / 2 };
}
