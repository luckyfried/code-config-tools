// The rules of the board, pure: no DOM, no time, no randomness of its own. A board is
// { size, tiles: [{ id, value, r, c }], score, nextId }. A move returns the next board and a trace
// the renderer animates: where every cube went, and which pairs became which new cube.

export const DIRECTIONS = {
  left: { dr: 0, dc: -1 },
  right: { dr: 0, dc: 1 },
  up: { dr: -1, dc: 0 },
  down: { dr: 1, dc: 0 },
};

export function emptyBoard(size) {
  return { size, tiles: [], score: 0, nextId: 1 };
}

/** A board from rows of numbers, 0 for an empty cell; ids run in reading order from 1. */
export function fromGrid(rows, score = 0) {
  const size = rows.length;
  const tiles = [];
  let nextId = 1;
  rows.forEach((row, r) =>
    row.forEach((value, c) => {
      if (value) tiles.push({ id: nextId++, value, r, c });
    }),
  );
  return { size, tiles, score, nextId };
}

/** Rows of numbers, 0 for an empty cell. */
export function toGrid(board) {
  const rows = Array.from({ length: board.size }, () => new Array(board.size).fill(0));
  for (const t of board.tiles) rows[t.r][t.c] = t.value;
  return rows;
}

export function cloneBoard(board) {
  return { size: board.size, score: board.score, nextId: board.nextId, tiles: board.tiles.map((t) => ({ ...t })) };
}

/** The cells of each line, ordered from the edge the cubes slide toward. */
function lines(size, dir) {
  const out = [];
  for (let i = 0; i < size; i += 1) {
    const line = [];
    for (let j = 0; j < size; j += 1) {
      if (dir === "left") line.push([i, j]);
      else if (dir === "right") line.push([i, size - 1 - j]);
      else if (dir === "up") line.push([j, i]);
      else line.push([size - 1 - j, i]);
    }
    out.push(line);
  }
  return out;
}

/**
 * Slides every cube toward `dir`. Two equal cubes that meet become one of twice the value, and each cube merges at
 * most once per move. Returns { board, moved, gained, trace, merges }:
 * trace: one entry per cube that was on the board, { id, value, from: [r, c], to: [r, c], into } (into: the new
 * cube's id when it merged, else null); merges: { id, value, r, c, from: [idA, idB] } in the order they happened
 * along each line, lowest value first across the move.
 */
export function move(board, dir) {
  const size = board.size;
  const grid = Array.from({ length: size }, () => new Array(size).fill(null));
  for (const t of board.tiles) grid[t.r][t.c] = t;
  let nextId = board.nextId;
  let gained = 0;
  let moved = false;
  const tiles = [];
  const trace = [];
  const merges = [];
  for (const line of lines(size, dir)) {
    let k = 0;
    let last = null; // { tile placed at line[k - 1], merged }
    for (const [r, c] of line) {
      const t = grid[r][c];
      if (!t) continue;
      if (last && !last.merged && last.tile.value === t.value) {
        const [tr, tc] = line[k - 1];
        const value = t.value * 2;
        const made = { id: nextId++, value, r: tr, c: tc };
        // The cube already placed there merges too: it keeps its slide, and both point at the new cube.
        const first = trace.find((e) => e.id === last.tile.id);
        first.into = made.id;
        trace.push({ id: t.id, value: t.value, from: [r, c], to: [tr, tc], into: made.id });
        tiles.splice(tiles.indexOf(last.tile), 1, made);
        merges.push({ id: made.id, value, r: tr, c: tc, from: [last.tile.id, t.id] });
        gained += value;
        moved = true;
        last = { tile: made, merged: true };
      } else {
        const [tr, tc] = line[k];
        k += 1;
        if (tr !== r || tc !== c) moved = true;
        const placed = { id: t.id, value: t.value, r: tr, c: tc };
        tiles.push(placed);
        trace.push({ id: t.id, value: t.value, from: [r, c], to: [tr, tc], into: null });
        last = { tile: placed, merged: false };
      }
    }
  }
  merges.sort((a, b) => a.value - b.value);
  const next = { size, tiles, score: board.score + gained, nextId };
  return { board: moved ? next : board, moved, gained, trace, merges };
}

export function emptyCells(board) {
  const taken = new Set(board.tiles.map((t) => t.r * board.size + t.c));
  const cells = [];
  for (let i = 0; i < board.size * board.size; i += 1) if (!taken.has(i)) cells.push([Math.floor(i / board.size), i % board.size]);
  return cells;
}

/**
 * Puts a new cube on an empty cell: a 2 nine times in ten, else a 4. `random` returns [0, 1). `at` and `value`
 * place it exactly (the scripted opening uses them); a taken `at` is ignored. Returns { board, tile }, tile null on a
 * full board.
 */
export function spawn(board, random, at = null, value = null) {
  const cells = emptyCells(board);
  if (cells.length === 0) return { board, tile: null };
  const free = at && cells.some(([r, c]) => r === at[0] && c === at[1]);
  const [r, c] = free ? at : cells[Math.min(cells.length - 1, Math.floor(random() * cells.length))];
  const v = value ?? (random() < 0.9 ? 2 : 4);
  const tile = { id: board.nextId, value: v, r, c };
  return { board: { ...board, tiles: [...board.tiles, tile], nextId: board.nextId + 1 }, tile };
}

export function canMove(board) {
  if (board.tiles.length < board.size * board.size) return true;
  const grid = toGrid(board);
  for (let r = 0; r < board.size; r += 1) {
    for (let c = 0; c < board.size; c += 1) {
      const v = grid[r][c];
      if ((c + 1 < board.size && grid[r][c + 1] === v) || (r + 1 < board.size && grid[r + 1][c] === v)) return true;
    }
  }
  return false;
}

export function highest(board) {
  return board.tiles.reduce((m, t) => Math.max(m, t.value), 0);
}

/** A small seeded generator (mulberry32), so a game can be replayed from its seed. */
export function seeded(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A fresh game: two cubes on an empty board. */
export function newGame(size, random) {
  let board = emptyBoard(size);
  board = spawn(board, random).board;
  board = spawn(board, random).board;
  return board;
}
