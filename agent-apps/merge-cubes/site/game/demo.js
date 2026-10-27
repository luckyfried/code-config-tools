// The board that plays itself until the person takes over. On 4 × 4 it is a scripted climb: eight swipes cascade
// 8 + 8 up the snake to 1024 + 1024, so the page opens on a lit, crowded board and reaches 2048 in a few seconds.
// On the other sizes a small player picks each swipe from a mid-game board.
import { canMove, emptyCells, fromGrid, move, newGame, seeded, spawn } from "./board.js";

const OPENING = {
  grid: [
    [1024, 512, 256, 128],
    [8, 16, 32, 64],
    [8, 4, 4, 2],
    [2, 0, 0, 0],
  ],
  score: 18432,
  moves: ["up", "right", "right", "right", "up", "left", "left", "left"],
  // Every new cube lands on a cell the swipe before it left empty.
  spawns: [[3, 1, 2], [3, 0, 2], [3, 1, 2], [3, 1, 4], [3, 0, 2], [3, 3, 2], [3, 2, 4], [3, 1, 2]],
};

/** How good a board looks to the small player: room to move, big cubes in a corner, neighbors that match. */
function judge(board) {
  const n = board.size;
  const grid = Array.from({ length: n }, () => new Array(n).fill(0));
  for (const t of board.tiles) grid[t.r][t.c] = Math.log2(t.value);
  let score = emptyCells(board).length * 2.7;
  for (let r = 0; r < n; r += 1) {
    for (let c = 0; c < n; c += 1) {
      const v = grid[r][c];
      score += v * (n - r) * 0.08 + v * (n - c) * 0.05;
      if (c + 1 < n && grid[r][c + 1] === v && v) score += 1.2;
      if (r + 1 < n && grid[r + 1][c] === v && v) score += 1.2;
    }
  }
  return score;
}

export function createDemo(size) {
  if (size === 4) {
    let i = 0;
    return {
      board: fromGrid(OPENING.grid, OPENING.score),
      next(board) {
        if (i >= OPENING.moves.length) return null;
        const dir = OPENING.moves[i];
        const [r, c, v] = OPENING.spawns[i];
        i += 1;
        return { dir, spawnAt: [r, c], spawnValue: v };
      },
    };
  }
  const random = seeded(2048 + size);
  let board = newGame(size, random);
  const pick = (b) => {
    let best = null;
    for (const dir of ["up", "left", "right", "down"]) {
      const m = move(b, dir);
      if (!m.moved) continue;
      const value = judge(m.board) + m.gained * 0.02;
      if (!best || value > best.value) best = { dir, value };
    }
    return best?.dir ?? null;
  };
  // Play forward out of sight to a lively mid-game board.
  for (let k = 0; k < size * size * 9 && emptyCells(board).length > Math.ceil(size / 2); k += 1) {
    const dir = pick(board);
    if (!dir) break;
    const after = spawn(move(board, dir).board, random).board;
    if (!canMove(after)) break;
    board = after;
  }
  return {
    board,
    next(b) {
      const dir = pick(b);
      if (!dir) return null;
      return { dir, random };
    },
  };
}
