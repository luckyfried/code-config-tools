// The board: six rows of five slab tiles, and every way they move.

import { LENGTH, TRIES } from "../game/words.js";

export const FLIP_MS = 620;
export const STAGGER_MS = 220;
const LAND_AT = 0.76;
const LIFT_SCALE = 0.95;
const SAY = { correct: "in the right spot", present: "in the word, wrong spot", absent: "not in the word" };

function el(tag, className, parent) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (parent) parent.appendChild(node);
  return node;
}

function buildTile(parent) {
  const tile = el("div", "tile", parent);
  tile.dataset.state = "empty";
  tile.setAttribute("role", "gridcell");
  const slab = el("div", "slab", tile);
  const front = el("div", "face face-front", slab);
  const frontGlyph = el("span", "glyph", front);
  const frontSheen = el("i", "sheen", front);
  const back = el("div", "face face-back", slab);
  const backGlyph = el("span", "glyph", back);
  const backSheen = el("i", "sheen", back);
  const sides = ["top", "bottom", "left", "right"].map((side) => el("i", `side side-${side}`, slab));
  return { el: tile, slab, front, back, frontGlyph, backGlyph, frontSheen, backSheen, sides };
}

export function createGrid(board, { reduced }) {
  const rows = [];
  for (let r = 0; r < TRIES; r += 1) {
    const row = el("div", "row", board);
    row.setAttribute("role", "row");
    const tiles = [];
    for (let c = 0; c < LENGTH; c += 1) tiles.push(buildTile(row));
    rows.push({ el: row, tiles });
  }

  // The tile size, in px, from the room the layout leaves the board (tiles.css holds the same rule in container
  // units for a page without this script). A container-unit size restyles every slab whenever that room changes
  // height, even when the tiles stay the same size (the badge leaving); this touches them only on a real change.
  const wrap = board.parentElement;
  const shortLandscape = matchMedia("(orientation: landscape) and (max-height: 560px)");
  let fitted = "";
  function fit() {
    const cs = getComputedStyle(wrap);
    const w = wrap.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const h = wrap.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    if (w <= 0 || h <= 0) return;
    const max = parseFloat(getComputedStyle(board).getPropertyValue("--tile-max")) || 76;
    const gap = shortLandscape.matches ? 6 : Math.min(10, Math.max(5, 0.015 * Math.min(w, h)));
    const tile = Math.max(0, Math.min((w - 4 * gap) / 5, (h - 5 * gap) / 6, max));
    const next = `${gap.toFixed(2)}px ${tile.toFixed(2)}px`;
    if (next === fitted) return;
    fitted = next;
    board.style.setProperty("--gap", `${gap.toFixed(2)}px`);
    board.style.setProperty("--tile", `${tile.toFixed(2)}px`);
  }
  new ResizeObserver(fit).observe(wrap);
  fit();

  const tileSize = () => rows[0].tiles[0].el.getBoundingClientRect().width || 60;
  const springEase = getComputedStyle(document.documentElement).getPropertyValue("--ease-spring").trim() || "ease-out";
  const timers = new Set();
  const later = (fn, ms) => {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, ms);
    timers.add(id);
  };

  function label(t, letter, result) {
    t.el.setAttribute("aria-label", letter ? (result ? `${letter}, ${SAY[result]}` : letter) : "empty");
  }

  function setLetter(r, c, letter, { pop = true } = {}) {
    const t = rows[r].tiles[c];
    t.frontGlyph.textContent = letter;
    t.backGlyph.textContent = letter;
    t.el.dataset.state = letter ? "filled" : "empty";
    label(t, letter);
    if (letter && pop && !reduced.matches) {
      t.el.animate(
        [
          { transform: "scale(1)", easing: "cubic-bezier(0.23, 1, 0.32, 1)" },
          { transform: "scale(1.12)", offset: 0.16, easing: springEase },
          { transform: "scale(1)" },
        ],
        { duration: 440 },
      );
    }
  }

  /** Sets a finished row with no motion: a saved game coming back. */
  function showRow(r, guess, result) {
    rows[r].tiles.forEach((t, c) => {
      setLetter(r, c, guess[c], { pop: false });
      t.el.dataset.result = result[c];
      t.el.classList.add("is-revealed");
      label(t, guess[c], result[c]);
    });
  }

  /** Flips the row tile by tile, 220 ms apart; `onLand(c)` fires as each slab lands. Resolves when the last settles. */
  function revealRow(r, guess, result, onLand = () => {}) {
    const lift = Math.round(tileSize() * 0.3);
    return Promise.all(
      rows[r].tiles.map(
        (t, c) =>
          new Promise((done) => {
            later(() => {
              t.el.dataset.result = result[c];
              label(t, guess[c], result[c]);
              if (reduced.matches) {
                t.el.classList.add("is-revealed");
                t.back.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 180, easing: "ease-out" });
                onLand(c);
                done();
                return;
              }
              t.el.classList.add("is-turning");
              // The edge shows while the slab is on its side and is gone before it lies flat, so a nearly
              // settled slab never reads as a face with a strip above it.
              t.sides.forEach((side) =>
                side.animate(
                  [
                    { opacity: 0 },
                    { opacity: 1, offset: 0.1 },
                    { opacity: 1, offset: 0.55 },
                    { opacity: 0, offset: 0.67 },
                    { opacity: 0 },
                  ],
                  { duration: FLIP_MS },
                ),
              );
              const flip = t.slab.animate(
                [
                  { transform: "translateZ(0px) rotateX(0deg) scale(1)", easing: "cubic-bezier(0.33, 0, 0.67, 1)" },
                  { transform: "translateZ(0px) rotateX(14deg) scale(1)", offset: 0.13, easing: "cubic-bezier(0.55, 0, 0.4, 1)" },
                  // Drawn in a little as it lifts, so the slab's near edge never reaches past its own socket.
                  { transform: `translateZ(${lift}px) rotateX(-96deg) scale(${LIFT_SCALE})`, offset: 0.47, easing: "cubic-bezier(0.3, 0, 0.35, 1)" },
                  { transform: "translateZ(0px) rotateX(-188deg) scale(1)", offset: LAND_AT, easing: "cubic-bezier(0.3, 0, 0.4, 1)" },
                  { transform: "translateZ(0px) rotateX(-180deg) scale(1)" },
                ],
                { duration: FLIP_MS, fill: "forwards" },
              );
              t.frontSheen.animate(
                [
                  { transform: "translateY(-80%)", opacity: 0 },
                  { transform: "translateY(0%)", opacity: 1, offset: 0.5 },
                  { transform: "translateY(80%)", opacity: 0 },
                ],
                { duration: FLIP_MS * 0.45, delay: FLIP_MS * 0.08, easing: "ease-in-out" },
              );
              t.backSheen.animate(
                [
                  { transform: "translateY(-80%)", opacity: 0 },
                  { transform: "translateY(0%)", opacity: 1, offset: 0.45 },
                  { transform: "translateY(80%)", opacity: 0 },
                ],
                { duration: FLIP_MS * 0.5, delay: FLIP_MS * 0.5, easing: "ease-out" },
              );
              later(() => onLand(c), FLIP_MS * LAND_AT);
              flip.finished
                .then(() => {
                  t.el.classList.add("is-revealed");
                  t.el.classList.remove("is-turning");
                  flip.cancel();
                })
                .catch(() => {})
                .finally(done);
            }, c * STAGGER_MS);
          }),
      ),
    );
  }

  /** A word the game will not take: the row shakes and the slabs' rims flash red. */
  function shake(r) {
    const row = rows[r];
    row.tiles.forEach((t) => t.el.classList.add("is-invalid"));
    later(() => row.tiles.forEach((t) => t.el.classList.remove("is-invalid")), 700);
    if (reduced.matches) return Promise.resolve();
    const s = tileSize() * 0.17;
    return row.el
      .animate(
        [0, -1, 0.9, -0.7, 0.5, -0.3, 0.12, 0].map((k) => ({ transform: `translateX(${(k * s).toFixed(1)}px)` })),
        { duration: 460, easing: "cubic-bezier(0.25, 0.6, 0.4, 1)" },
      )
      .finished.catch(() => {});
  }

  /** The win: the row lifts and each tile hops in turn. */
  function win(r) {
    if (reduced.matches) return Promise.resolve();
    const row = rows[r];
    const size = tileSize();
    row.el.animate([{ transform: "translateY(0px)" }, { transform: `translateY(${-Math.round(size * 0.06)}px)` }], {
      duration: 420,
      easing: "cubic-bezier(0.23, 1, 0.32, 1)",
      fill: "forwards",
    });
    const h = Math.round(size * 0.24);
    return Promise.all(
      row.tiles.map(
        (t, c) =>
          t.el.animate(
            [
              { transform: "translateY(0px) scale(1, 1)", easing: "cubic-bezier(0.2, 0.7, 0.35, 1)" },
              { transform: `translateY(${-h}px) scale(0.96, 1.05)`, offset: 0.36, easing: "cubic-bezier(0.6, 0, 0.85, 0.45)" },
              { transform: "translateY(0px) scale(1.07, 0.91)", offset: 0.6, easing: "cubic-bezier(0.2, 0.7, 0.35, 1)" },
              { transform: `translateY(${-Math.round(h * 0.2)}px) scale(0.99, 1.01)`, offset: 0.8, easing: "cubic-bezier(0.5, 0, 0.75, 0.4)" },
              { transform: "translateY(0px) scale(1, 1)" },
            ],
            { duration: 640, delay: 120 + c * 95 },
          ).finished,
      ),
    ).catch(() => {});
  }

  function resetTile(t) {
    t.el.getAnimations().forEach((a) => a.cancel());
    t.slab.getAnimations().forEach((a) => a.cancel());
    t.frontGlyph.textContent = "";
    t.backGlyph.textContent = "";
    t.el.dataset.state = "empty";
    delete t.el.dataset.result;
    t.el.classList.remove("is-revealed", "is-invalid", "is-turning");
    label(t, "");
  }

  function cancel() {
    timers.forEach((id) => clearTimeout(id));
    timers.clear();
    for (const row of rows) {
      row.el.getAnimations().forEach((a) => a.cancel());
      row.tiles.forEach((t) => [t.el, t.slab, t.back, t.frontSheen, t.backSheen, ...t.sides].forEach((n) => n.getAnimations().forEach((a) => a.cancel())));
    }
  }

  /** Empties the board; animated, the filled slabs sink away in a wave and the empty sockets rise back in. */
  async function clear({ animated = false } = {}) {
    cancel();
    const filled = rows.flatMap((row, r) => row.tiles.map((t, c) => ({ t, r, c }))).filter(({ t }) => t.el.dataset.state !== "empty");
    if (animated && !reduced.matches && filled.length) {
      await Promise.all(
        filled.map(({ t, r, c }) =>
          t.el
            .animate(
              [
                { transform: "translateY(0px) scale(1)", opacity: 1 },
                { transform: "translateY(10px) scale(0.86)", opacity: 0 },
              ],
              { duration: 260, delay: r * 45 + c * 30, easing: "cubic-bezier(0.55, 0, 0.75, 0.3)", fill: "forwards" },
            )
            .finished.catch(() => {}),
        ),
      );
      rows.forEach((row) => {
        row.el.getAnimations().forEach((a) => a.cancel());
        row.tiles.forEach(resetTile);
      });
      rows.forEach((row, r) =>
        row.tiles.forEach((t, c) =>
          t.el.animate(
            [
              { transform: "scale(0.9)", opacity: 0 },
              { transform: "scale(1)", opacity: 1 },
            ],
            { duration: 320, delay: r * 30 + c * 20, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" },
          ),
        ),
      );
      return;
    }
    rows.forEach((row) => {
      row.el.getAnimations().forEach((a) => a.cancel());
      row.tiles.forEach(resetTile);
    });
  }

  function rowRect(r) {
    return rows[r].el.getBoundingClientRect();
  }

  return { setLetter, showRow, revealRow, shake, win, clear, cancel, rowRect, fit };
}
