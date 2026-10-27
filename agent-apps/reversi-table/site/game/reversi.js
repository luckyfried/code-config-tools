// The rules of Reversi on an 8x8 board, with no DOM and no rendering, so the page, the engine worker, and the
// rules test page all share one copy. Squares are 0..63, row-major from a1 (top left) to h8 (bottom right).

export const EMPTY = 0;
export const BLACK = 1;
export const WHITE = 2;
export const SIZE = 8;

/** The eight directions as [row step, column step], clockwise from north. */
export const DIRECTIONS = [
  [-1, 0], [-1, 1], [0, 1], [1, 1],
  [1, 0], [1, -1], [0, -1], [-1, -1],
];

export const opponent = (color) => (color === BLACK ? WHITE : BLACK);
export const colorName = (color) => (color === BLACK ? "Black" : "White");
export const rowOf = (square) => Math.floor(square / SIZE);
export const colOf = (square) => square % SIZE;
export const squareAt = (row, col) => row * SIZE + col;

/** "f5" for square 37. */
export const squareName = (square) => `${"abcdefgh"[colOf(square)]}${rowOf(square) + 1}`;

/** 37 for "f5"; -1 for anything that names no square. */
export function parseSquare(name) {
  const match = /^([a-h])([1-8])$/i.exec(String(name).trim());
  if (!match) return -1;
  return squareAt(Number(match[2]) - 1, "abcdefgh".indexOf(match[1].toLowerCase()));
}

/** The standard opening: White on d4 and e5, Black on e4 and d5. */
export function initialBoard() {
  const board = new Array(SIZE * SIZE).fill(EMPTY);
  board[squareAt(3, 3)] = WHITE;
  board[squareAt(4, 4)] = WHITE;
  board[squareAt(3, 4)] = BLACK;
  board[squareAt(4, 3)] = BLACK;
  return board;
}

/**
 * The lines a disc of `color` placed on `square` captures: each `{ dir, squares }`, the squares in order outward
 * from the placed disc. Empty when the square is taken or the move captures nothing.
 */
export function flipLines(board, square, color) {
  if (board[square] !== EMPTY) return [];
  const other = opponent(color);
  const row = rowOf(square);
  const col = colOf(square);
  const lines = [];
  for (const dir of DIRECTIONS) {
    let r = row + dir[0];
    let c = col + dir[1];
    const run = [];
    while (r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[squareAt(r, c)] === other) {
      run.push(squareAt(r, c));
      r += dir[0];
      c += dir[1];
    }
    if (run.length > 0 && r >= 0 && r < SIZE && c >= 0 && c < SIZE && board[squareAt(r, c)] === color) {
      lines.push({ dir, squares: run });
    }
  }
  return lines;
}

/** Every square `color` may play, in square order. */
export function legalMoves(board, color) {
  const moves = [];
  for (let square = 0; square < SIZE * SIZE; square += 1) {
    if (board[square] === EMPTY && flipLines(board, square, color).length > 0) moves.push(square);
  }
  return moves;
}

export const hasMove = (board, color) => legalMoves(board, color).length > 0;

/** The board after `color` plays `square`, and the lines it captured; null when the move is not legal. */
export function play(board, square, color) {
  const lines = flipLines(board, square, color);
  if (lines.length === 0) return null;
  const next = board.slice();
  next[square] = color;
  for (const line of lines) for (const s of line.squares) next[s] = color;
  return { board: next, lines };
}

export function count(board) {
  let black = 0;
  let white = 0;
  for (const cell of board) {
    if (cell === BLACK) black += 1;
    else if (cell === WHITE) white += 1;
  }
  return { black, white, empty: board.length - black - white };
}

/**
 * Who moves after `mover` played: the opponent when it has a move, the mover again when only it has one (the
 * opponent passes), and null when neither does (the game is over).
 */
export function nextToMove(board, mover) {
  const other = opponent(mover);
  if (hasMove(board, other)) return { color: other, passed: null };
  if (hasMove(board, mover)) return { color: mover, passed: other };
  return { color: null, passed: null };
}

/**
 * Replays `moves` (square numbers) from the opening, Black first, passing automatically when a side has no move.
 * Returns every step's board and capture lines, or null at the first illegal move.
 */
export function replay(moves) {
  let board = initialBoard();
  let toMove = BLACK;
  const steps = [];
  for (const square of moves) {
    if (toMove === null) return null;
    const result = play(board, square, toMove);
    if (result === null) return null;
    const next = nextToMove(result.board, toMove);
    steps.push({ square, color: toMove, lines: result.lines, board: result.board, passed: next.passed });
    board = result.board;
    toMove = next.color;
  }
  return { board, toMove, steps };
}

/** The winner's color, or EMPTY for a draw. */
export function winner(board) {
  const { black, white } = count(board);
  if (black === white) return EMPTY;
  return black > white ? BLACK : WHITE;
}

/**
 * The final count laid out the way players count a finished board: the occupied squares in reading order, the
 * winner's discs first. Returns the color each occupied square shows afterwards.
 */
export function countedOut(board) {
  const { black, white } = count(board);
  const first = black >= white ? BLACK : WHITE;
  const firstCount = first === BLACK ? black : white;
  const out = board.slice();
  let seen = 0;
  for (let square = 0; square < board.length; square += 1) {
    if (board[square] === EMPTY) continue;
    out[square] = seen < firstCount ? first : opponent(first);
    seen += 1;
  }
  return out;
}
