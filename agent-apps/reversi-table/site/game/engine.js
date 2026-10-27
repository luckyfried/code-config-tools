// The computer opponent: negamax with alpha-beta over a corner-and-edge weight table and mobility. Depth 2, 4, or 6
// by strength; the last empties of a strength-3 game are searched to the end. Pure, so the worker and the rules
// test page run the same code.
import { EMPTY, BLACK, WHITE, SIZE, DIRECTIONS } from "./reversi.js";

export const DEPTH_BY_STRENGTH = { 1: 2, 2: 4, 3: 6 };
const EXACT_EMPTIES = 10;
const WIN = 100000;

// Corners are worth the most; the squares that hand a corner to the opponent cost the most.
export const WEIGHTS = [
  120, -20, 20, 5, 5, 20, -20, 120,
  -20, -40, -5, -5, -5, -5, -40, -20,
  20, -5, 15, 3, 3, 15, -5, 20,
  5, -5, 3, 3, 3, 3, -5, 5,
  5, -5, 3, 3, 3, 3, -5, 5,
  20, -5, 15, 3, 3, 15, -5, 20,
  -20, -40, -5, -5, -5, -5, -40, -20,
  120, -20, 20, 5, 5, 20, -20, 120,
];

// Neighbor walks precomputed per square and direction, so the hot loop only reads arrays.
const RAYS = [];
for (let square = 0; square < SIZE * SIZE; square += 1) {
  const r0 = Math.floor(square / SIZE);
  const c0 = square % SIZE;
  const rays = [];
  for (const [dr, dc] of DIRECTIONS) {
    const ray = [];
    let r = r0 + dr;
    let c = c0 + dc;
    while (r >= 0 && r < SIZE && c >= 0 && c < SIZE) {
      ray.push(r * SIZE + c);
      r += dr;
      c += dc;
    }
    if (ray.length >= 2) rays.push(ray);
  }
  RAYS.push(rays);
}

const ORDER = Array.from({ length: SIZE * SIZE }, (_, i) => i).sort((a, b) => WEIGHTS[b] - WEIGHTS[a]);

/** Flips for `color` on `square` into `out` (an Int8Array stack), returning how many; 0 means illegal. */
function flipsInto(board, square, color, out, at) {
  const other = 3 - color;
  let n = 0;
  for (const ray of RAYS[square]) {
    let k = 0;
    while (k < ray.length && board[ray[k]] === other) k += 1;
    if (k > 0 && k < ray.length && board[ray[k]] === color) {
      for (let j = 0; j < k; j += 1) out[at + n++] = ray[j];
    }
  }
  return n;
}

function canPlay(board, square, color) {
  if (board[square] !== EMPTY) return false;
  const other = 3 - color;
  for (const ray of RAYS[square]) {
    let k = 0;
    while (k < ray.length && board[ray[k]] === other) k += 1;
    if (k > 0 && k < ray.length && board[ray[k]] === color) return true;
  }
  return false;
}

function mobility(board, color) {
  let n = 0;
  for (let s = 0; s < 64; s += 1) if (canPlay(board, s, color)) n += 1;
  return n;
}

function evaluate(board, color) {
  const other = 3 - color;
  let positional = 0;
  let mine = 0;
  let theirs = 0;
  for (let s = 0; s < 64; s += 1) {
    if (board[s] === color) {
      positional += WEIGHTS[s];
      mine += 1;
    } else if (board[s] === other) {
      positional -= WEIGHTS[s];
      theirs += 1;
    }
  }
  const myMoves = mobility(board, color);
  const theirMoves = mobility(board, other);
  const mobilityScore = myMoves + theirMoves === 0 ? 0 : (100 * (myMoves - theirMoves)) / (myMoves + theirMoves + 2);
  // Disc count matters little until the board fills up.
  const filled = mine + theirs;
  const discs = filled > 52 ? 4 * (mine - theirs) : 0;
  return positional + mobilityScore + discs;
}

function finalScore(board, color) {
  let diff = 0;
  for (let s = 0; s < 64; s += 1) {
    if (board[s] === color) diff += 1;
    else if (board[s] !== EMPTY) diff -= 1;
  }
  return diff > 0 ? WIN + diff : diff < 0 ? -WIN + diff : 0;
}

/**
 * Searches the position for `color` and answers `{ square, score, nodes }`; square is -1 when `color` has no move.
 * `options.depth` overrides the strength's depth; `options.random` (0..1 source) lets strength 1 vary its play.
 */
export function chooseMove(cells, color, strength = 2, options = {}) {
  const board = Int8Array.from(cells);
  let empties = 0;
  for (let s = 0; s < 64; s += 1) if (board[s] === EMPTY) empties += 1;
  let depth = options.depth ?? DEPTH_BY_STRENGTH[strength] ?? 4;
  const exact = strength >= 3 && empties <= EXACT_EMPTIES;
  if (exact) depth = empties + 2;
  const stack = new Int8Array(64 * 64);
  let nodes = 0;

  function search(side, d, alpha, beta, sp, passed) {
    nodes += 1;
    if (d === 0) return exact ? finalScore(board, side) : evaluate(board, side);
    let any = false;
    let best = -Infinity;
    for (const s of ORDER) {
      if (board[s] !== EMPTY) continue;
      const n = flipsInto(board, s, side, stack, sp);
      if (n === 0) continue;
      any = true;
      board[s] = side;
      for (let j = 0; j < n; j += 1) board[stack[sp + j]] = side;
      const value = -search(3 - side, d - 1, -beta, -alpha, sp + n, false);
      board[s] = EMPTY;
      for (let j = 0; j < n; j += 1) board[stack[sp + j]] = 3 - side;
      if (value > best) best = value;
      if (value > alpha) alpha = value;
      if (alpha >= beta) break;
    }
    if (!any) {
      if (passed) return finalScore(board, side);
      return -search(3 - side, d, -beta, -alpha, sp, true);
    }
    return best;
  }

  const scored = [];
  let alpha = -Infinity;
  for (const s of ORDER) {
    if (board[s] !== EMPTY) continue;
    const n = flipsInto(board, s, color, stack, 0);
    if (n === 0) continue;
    board[s] = color;
    for (let j = 0; j < n; j += 1) board[stack[j]] = color;
    // A full window at the root keeps every move's score comparable for strength 1's variety.
    const value = -search(3 - color, depth - 1, -Infinity, strength === 1 ? Infinity : -alpha, n, false);
    board[s] = EMPTY;
    for (let j = 0; j < n; j += 1) board[stack[j]] = 3 - color;
    scored.push({ square: s, score: value });
    if (value > alpha) alpha = value;
  }
  if (scored.length === 0) return { square: -1, score: 0, nodes };
  scored.sort((a, b) => b.score - a.score || a.square - b.square);
  let pick = scored[0];
  if (strength === 1 && options.random) {
    const close = scored.filter((m) => m.score >= scored[0].score - 30);
    pick = close[Math.floor(options.random() * close.length) % close.length];
  }
  return { square: pick.square, score: pick.score, nodes };
}

export { BLACK, WHITE };
