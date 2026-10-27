// The computer's search: a 0x88 board, legal move generation, a piece-square evaluation, and a negamax with
// alpha-beta, iterative deepening, capture ordering, and a quiescence search on captures. It reads a FEN and
// returns one move as { from, to, promotion }. Pure module: the worker and the tests import it.

const EMPTY = 0, P = 1, N = 2, B = 3, R = 4, Q = 5, K = 6;
const BLACK = 8;
const MATE = 100000;
const VALUE = [0, 100, 320, 330, 500, 900, 20000];

const N_OFF = [-33, -31, -18, -14, 14, 18, 31, 33];
const B_OFF = [-17, -15, 15, 17];
const R_OFF = [-16, -1, 1, 16];
const K_OFF = [-17, -16, -15, -1, 1, 15, 16, 17];

// Piece-square tables from white's side, a8 first (row 0 is rank 8).
const PST = {
  [P]: [0, 0, 0, 0, 0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 10, 10, 20, 30, 30, 20, 10, 10, 5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0, 5, -5, -10, 0, 0, -10, -5, 5, 5, 10, 10, -20, -20, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
  [N]: [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40, -30, 0, 10, 15, 15, 10, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30, -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50],
  [B]: [-20, -10, -10, -10, -10, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 10, 10, 5, 0, -10, -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10, -10, 10, 10, 10, 10, 10, 10, -10, -10, 5, 0, 0, 0, 0, 5, -10, -20, -10, -10, -10, -10, -10, -10, -20],
  [R]: [0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, 10, 10, 10, 10, 5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, 0, 0, 0, 5, 5, 0, 0, 0],
  [Q]: [-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 5, 5, 5, 0, -10, -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5, -10, 5, 5, 5, 5, 5, 0, -10, -10, 0, 5, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20],
  [K]: [-30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30, -20, -30, -30, -40, -40, -30, -30, -20, -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20, 20, 30, 10, 0, 0, 10, 30, 20],
};
const KING_END = [-50, -40, -30, -20, -20, -30, -40, -50, -30, -20, -10, 0, 0, -10, -20, -30, -30, -10, 20, 30, 30, 20, -10, -30,
  -30, -10, 30, 40, 40, 30, -10, -30, -30, -10, 30, 40, 40, 30, -10, -30, -30, -10, 20, 30, 30, 20, -10, -30,
  -30, -30, 0, 0, 0, 0, -30, -30, -50, -30, -30, -30, -30, -30, -30, -50];

const LETTERS = "abcdefgh";
const sqName = (s) => LETTERS[s & 7] + (8 - (s >> 4));
const sqIndex = (name) => (8 - Number(name[1])) * 16 + LETTERS.indexOf(name[0]);
const to64 = (s) => (s >> 4) * 8 + (s & 7);
const mirror64 = (i) => (7 - (i >> 3)) * 8 + (i & 7);

const PIECE_OF = { p: P, n: N, b: B, r: R, q: Q, k: K };
const CHAR_OF = ["", "p", "n", "b", "r", "q", "k"];

// Move flags packed above from (7 bits), to (7 bits), and promotion (3 bits).
const F_CAPTURE = 1, F_EP = 2, F_CASTLE = 4, F_DOUBLE = 8;
const pack = (from, to, promo, flags) => from | (to << 7) | (promo << 14) | (flags << 17);
const mFrom = (m) => m & 127;
const mTo = (m) => (m >> 7) & 127;
const mPromo = (m) => (m >> 14) & 7;
const mFlags = (m) => m >> 17;

export class Position {
  constructor(fen) {
    this.board = new Int8Array(128);
    this.stack = [];
    const [placement, side, castling, ep] = fen.trim().split(/\s+/);
    let r = 0, f = 0;
    for (const ch of placement) {
      if (ch === "/") { r++; f = 0; continue; }
      if (/\d/.test(ch)) { f += Number(ch); continue; }
      const lower = ch.toLowerCase();
      this.board[r * 16 + f] = PIECE_OF[lower] | (ch === lower ? BLACK : 0);
      f++;
    }
    this.side = side === "b" ? BLACK : 0;
    this.castle = (castling.includes("K") ? 1 : 0) | (castling.includes("Q") ? 2 : 0) |
      (castling.includes("k") ? 4 : 0) | (castling.includes("q") ? 8 : 0);
    this.ep = ep && ep !== "-" ? sqIndex(ep) : -1;
    this.kings = [0, 0];
    for (let s = 0; s < 128; s++) {
      if (s & 0x88) { s += 7; continue; }
      const pc = this.board[s];
      if ((pc & 7) === K) this.kings[pc & BLACK ? 1 : 0] = s;
    }
  }

  attacked(sq, by) {
    const b = this.board;
    const pawn = P | by;
    const dir = by ? -16 : 16;
    for (const d of [dir - 1, dir + 1]) {
      const s = sq + d;
      if (!(s & 0x88) && b[s] === pawn) return true;
    }
    for (const d of N_OFF) { const s = sq + d; if (!(s & 0x88) && b[s] === (N | by)) return true; }
    for (const d of K_OFF) { const s = sq + d; if (!(s & 0x88) && b[s] === (K | by)) return true; }
    for (const d of B_OFF) {
      for (let s = sq + d; !(s & 0x88); s += d) {
        const pc = b[s];
        if (pc) { if (pc === (B | by) || pc === (Q | by)) return true; break; }
      }
    }
    for (const d of R_OFF) {
      for (let s = sq + d; !(s & 0x88); s += d) {
        const pc = b[s];
        if (pc) { if (pc === (R | by) || pc === (Q | by)) return true; break; }
      }
    }
    return false;
  }

  inCheck(side = this.side) {
    return this.attacked(this.kings[side ? 1 : 0], side ^ BLACK);
  }

  // Pseudo-legal moves; makeMove refuses the ones that leave the king in check.
  moves(capturesOnly = false) {
    const out = [];
    const b = this.board, us = this.side, them = us ^ BLACK;
    for (let s = 0; s < 128; s++) {
      if (s & 0x88) { s += 7; continue; }
      const pc = b[s];
      if (!pc || (pc & BLACK) !== us) continue;
      const type = pc & 7;
      if (type === P) {
        const fwd = us ? 16 : -16;
        const startRank = us ? 1 : 6, lastRank = us ? 7 : 0;
        const t = s + fwd;
        if (!(t & 0x88) && !b[t]) {
          if ((t >> 4) === lastRank) for (const pr of [Q, N, R, B]) out.push(pack(s, t, pr, 0));
          else if (!capturesOnly) {
            out.push(pack(s, t, 0, 0));
            const t2 = t + fwd;
            if ((s >> 4) === startRank && !b[t2]) out.push(pack(s, t2, 0, F_DOUBLE));
          }
        }
        for (const d of [fwd - 1, fwd + 1]) {
          const c = s + d;
          if (c & 0x88) continue;
          if (b[c] && (b[c] & BLACK) === them) {
            if ((c >> 4) === lastRank) for (const pr of [Q, N, R, B]) out.push(pack(s, c, pr, F_CAPTURE));
            else out.push(pack(s, c, 0, F_CAPTURE));
          } else if (c === this.ep) out.push(pack(s, c, 0, F_CAPTURE | F_EP));
        }
        continue;
      }
      const offs = type === N ? N_OFF : type === B ? B_OFF : type === R ? R_OFF : K_OFF;
      const slide = type === B || type === R || type === Q;
      for (const d of offs) {
        for (let t = s + d; !(t & 0x88); t += d) {
          const tp = b[t];
          if (tp) {
            if ((tp & BLACK) === them) out.push(pack(s, t, 0, F_CAPTURE));
            break;
          }
          if (!capturesOnly) out.push(pack(s, t, 0, 0));
          if (!slide) break;
        }
      }
      if (type === K && !capturesOnly) {
        const home = us ? 4 : 116;
        if (s === home && !this.attacked(s, them)) {
          const kSide = us ? 4 : 1, qSide = us ? 8 : 2;
          if ((this.castle & kSide) && !b[s + 1] && !b[s + 2] && b[s + 3] === (R | us) &&
            !this.attacked(s + 1, them) && !this.attacked(s + 2, them)) out.push(pack(s, s + 2, 0, F_CASTLE));
          if ((this.castle & qSide) && !b[s - 1] && !b[s - 2] && !b[s - 3] && b[s - 4] === (R | us) &&
            !this.attacked(s - 1, them) && !this.attacked(s - 2, them)) out.push(pack(s, s - 2, 0, F_CASTLE));
        }
      }
    }
    return out;
  }

  // Plays m; returns false (and takes it back) when it leaves the mover's king in check.
  make(m) {
    const b = this.board, from = mFrom(m), to = mTo(m), promo = mPromo(m), flags = mFlags(m);
    const pc = b[from], us = this.side;
    let captured = b[to], capSq = to;
    if (flags & F_EP) { capSq = to + (us ? -16 : 16); captured = b[capSq]; b[capSq] = EMPTY; }
    this.stack.push([m, captured, capSq, this.castle, this.ep]);
    b[to] = promo ? (promo | us) : pc;
    b[from] = EMPTY;
    if ((pc & 7) === K) {
      this.kings[us ? 1 : 0] = to;
      if (flags & F_CASTLE) {
        if (to > from) { b[from + 1] = b[from + 3]; b[from + 3] = EMPTY; }
        else { b[from - 1] = b[from - 4]; b[from - 4] = EMPTY; }
      }
      this.castle &= us ? ~12 : ~3;
    }
    const touch = (sq) => {
      if (sq === 112) this.castle &= ~2; else if (sq === 119) this.castle &= ~1;
      else if (sq === 0) this.castle &= ~8; else if (sq === 7) this.castle &= ~4;
    };
    touch(from); touch(to);
    this.ep = flags & F_DOUBLE ? (from + to) >> 1 : -1;
    this.side ^= BLACK;
    if (this.attacked(this.kings[us ? 1 : 0], this.side)) { this.unmake(); return false; }
    return true;
  }

  unmake() {
    const [m, captured, capSq, castle, ep] = this.stack.pop();
    const b = this.board, from = mFrom(m), to = mTo(m), flags = mFlags(m);
    this.side ^= BLACK;
    const us = this.side;
    const moved = b[to];
    b[from] = mPromo(m) ? (P | us) : moved;
    b[to] = EMPTY;
    b[capSq] = captured;
    if ((moved & 7) === K) {
      this.kings[us ? 1 : 0] = from;
      if (flags & F_CASTLE) {
        if (to > from) { b[from + 3] = b[from + 1]; b[from + 1] = EMPTY; }
        else { b[from - 4] = b[from - 1]; b[from - 1] = EMPTY; }
      }
    }
    this.castle = castle;
    this.ep = ep;
  }

  evaluate() {
    const b = this.board;
    let score = 0, nonPawn = 0;
    for (let s = 0; s < 128; s++) {
      if (s & 0x88) { s += 7; continue; }
      const pc = b[s];
      if (pc && (pc & 7) !== P && (pc & 7) !== K) nonPawn += VALUE[pc & 7];
    }
    const endgame = nonPawn <= 2600;
    for (let s = 0; s < 128; s++) {
      if (s & 0x88) { s += 7; continue; }
      const pc = b[s];
      if (!pc) continue;
      const type = pc & 7, black = pc & BLACK;
      const i = black ? mirror64(to64(s)) : to64(s);
      const table = type === K && endgame ? KING_END : PST[type];
      const v = VALUE[type] + table[i];
      score += black ? -v : v;
    }
    return this.side ? -score : score;
  }
}

const orderScore = (pos, m) => {
  const flags = mFlags(m);
  let s = 0;
  if (flags & F_CAPTURE) {
    const victim = flags & F_EP ? P : pos.board[mTo(m)] & 7;
    s += 10 * VALUE[victim] - VALUE[pos.board[mFrom(m)] & 7] / 10 + 100000;
  }
  if (mPromo(m)) s += VALUE[mPromo(m)] + 50000;
  return s;
};

const sortMoves = (pos, moves, first) => {
  const scored = moves.map((m) => [m === first ? 1e9 : orderScore(pos, m), m]);
  scored.sort((a, c) => c[0] - a[0]);
  return scored.map((x) => x[1]);
};

class Stop extends Error {}

class Searcher {
  constructor(pos, deadline) {
    this.pos = pos;
    this.deadline = deadline;
    this.nodes = 0;
  }

  tick() {
    if ((++this.nodes & 1023) === 0 && performance.now() > this.deadline) throw new Stop();
  }

  quiesce(alpha, beta, depth) {
    this.tick();
    const stand = this.pos.evaluate();
    if (stand >= beta) return beta;
    if (stand > alpha) alpha = stand;
    if (depth >= 8) return alpha;
    for (const m of sortMoves(this.pos, this.pos.moves(true), 0)) {
      if (!this.pos.make(m)) continue;
      const score = -this.quiesce(-beta, -alpha, depth + 1);
      this.pos.unmake();
      if (score >= beta) return beta;
      if (score > alpha) alpha = score;
    }
    return alpha;
  }

  negamax(depth, alpha, beta, ply) {
    this.tick();
    const checked = this.pos.inCheck();
    if (depth <= 0 && (!checked || depth < -3)) return this.quiesce(alpha, beta, 0);
    let legal = 0;
    for (const m of sortMoves(this.pos, this.pos.moves(), 0)) {
      if (!this.pos.make(m)) continue;
      legal++;
      const score = -this.negamax(depth - 1, -beta, -alpha, ply + 1);
      this.pos.unmake();
      if (score >= beta) return beta;
      if (score > alpha) alpha = score;
    }
    if (!legal) return checked ? -MATE + ply : 0;
    return alpha;
  }

  // Scores every legal root move at this depth, best first.
  // A move more than `margin` below the best so far fails low and is scored below the margin.
  root(depth, first, margin) {
    const results = [];
    let alpha = -MATE - 1;
    for (const m of sortMoves(this.pos, this.pos.moves(), first)) {
      if (!this.pos.make(m)) continue;
      const score = -this.negamax(depth - 1, -MATE - 1, -(alpha - margin) + 1, 1);
      this.pos.unmake();
      results.push([score, m]);
      if (score > alpha) alpha = score;
    }
    results.sort((a, c) => c[0] - a[0]);
    return results;
  }
}

// Strength 1 to 4 is the depth; the two lower strengths pick among near-equal moves so they play like people.
const NOISE = { 1: 90, 2: 25, 3: 0, 4: 0 };

export function bestMove(fen, strength = 2, { timeMs = 1800, random = Math.random } = {}) {
  const pos = new Position(fen);
  const depthGoal = Math.max(1, Math.min(4, Math.round(strength)));
  const searcher = new Searcher(pos, performance.now() + timeMs);
  const noise = NOISE[depthGoal];
  let ranked = null;
  for (let depth = 1; depth <= depthGoal; depth++) {
    try {
      ranked = searcher.root(depth, ranked ? ranked[0][1] : 0, noise);
    } catch (e) {
      if (!(e instanceof Stop)) throw e;
      break;
    }
    if (ranked.length && ranked[0][0] > MATE - 100) break;
  }
  if (!ranked || !ranked.length) return null;
  let pick = ranked[0];
  if (noise && ranked[0][0] < MATE - 100) {
    const close = ranked.filter((r) => r[0] >= ranked[0][0] - noise);
    pick = close[Math.floor(random() * close.length)];
  }
  const m = pick[1];
  return {
    from: sqName(mFrom(m)),
    to: sqName(mTo(m)),
    promotion: mPromo(m) ? CHAR_OF[mPromo(m)] : undefined,
    score: pick[0],
    nodes: searcher.nodes,
  };
}

// Counts leaf nodes to a depth; the tests compare it with the published perft numbers.
export function perft(fen, depth) {
  const pos = new Position(fen);
  const walk = (d) => {
    if (d === 0) return 1;
    let n = 0;
    for (const m of pos.moves()) {
      if (!pos.make(m)) continue;
      n += walk(d - 1);
      pos.unmake();
    }
    return n;
  };
  return walk(depth);
}
