// Klondike as pure functions over a plain game state. Nothing here touches the page,
// so the same rules run the table, the house's demo hand, and the test page.
//
// A card is a number 0..51: suit = floor(card / 13) in the order spades, hearts,
// diamonds, clubs; rank = card % 13 + 1 (1 is the ace, 13 the king).
// A state is { seed, draw, scoring, stock, waste, foundations[4], tableau[7], up[52],
// score, sent, passes, moves, won }. Every function returns a new state and never
// changes the one it was given.

export const SUITS = ["spades", "hearts", "diamonds", "clubs"];
export const RANK_NAMES = ["", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"];

export const suitOf = (card) => Math.floor(card / 13);
export const rankOf = (card) => (card % 13) + 1;
export const isRed = (card) => suitOf(card) === 1 || suitOf(card) === 2;
const RANK_WORDS = ["", "ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king"];
export const cardName = (card) => `${RANK_WORDS[rankOf(card)]} of ${SUITS[suitOf(card)]}`;

// Vegas: the deck costs $52 and each card on a foundation pays $5.
export const VEGAS_BUY = 52;
export const VEGAS_PAY = 5;

// Standard scoring, as the desktop game has always counted it.
export const STANDARD = {
  wasteToTableau: 5,
  toFoundation: 10,
  turnOver: 5,
  foundationToTableau: -15,
  recycleDrawOne: -100,
  recycleDrawThree: -20,
};

/** A small seeded generator (mulberry32) so a deal is the same deal everywhere. */
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffledDeck(seed) {
  const deck = Array.from({ length: 52 }, (_, i) => i);
  const next = rng(seed);
  for (let i = deck.length - 1; i > 0; i -= 1) {
    const j = Math.floor(next() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

/** How many times the waste may go back to the stock: Vegas allows one pass on draw one and three on draw three. */
export function passLimit(state) {
  if (state.scoring !== "vegas") return Infinity;
  return state.draw === 3 ? 3 : 1;
}

/** Deals a new game from a seed. `deck` overrides the shuffle (the tests use it). */
export function deal({ seed = 1, draw = 1, scoring = "standard", deck = null } = {}) {
  const cards = deck ? deck.slice() : shuffledDeck(seed);
  const tableau = [[], [], [], [], [], [], []];
  const up = new Array(52).fill(0);
  let at = 0;
  for (let row = 0; row < 7; row += 1) {
    for (let col = row; col < 7; col += 1) {
      tableau[col].push(cards[at]);
      if (col === row) up[cards[at]] = 1;
      at += 1;
    }
  }
  return {
    seed,
    draw: draw === 3 ? 3 : 1,
    scoring: scoring === "vegas" ? "vegas" : "standard",
    stock: cards.slice(at).reverse(),
    waste: [],
    foundations: [[], [], [], []],
    tableau,
    up,
    score: scoring === "vegas" ? -VEGAS_BUY : 0,
    sent: 0,
    passes: 1,
    moves: 0,
    won: false,
  };
}

function clone(state) {
  return {
    ...state,
    stock: state.stock.slice(),
    waste: state.waste.slice(),
    foundations: state.foundations.map((p) => p.slice()),
    tableau: state.tableau.map((p) => p.slice()),
    up: state.up.slice(),
  };
}

/** The pile array a pile name points at: "stock", "waste", "f0".."f3", "t0".."t6". */
export function pile(state, name) {
  if (name === "stock") return state.stock;
  if (name === "waste") return state.waste;
  const index = Number(name.slice(1));
  if (name[0] === "f") return state.foundations[index];
  if (name[0] === "t") return state.tableau[index];
  return null;
}

export const top = (cards) => (cards.length ? cards[cards.length - 1] : -1);

/** Whether `card` may go onto the foundation `f` (0..3). */
export function fitsFoundation(state, card, f) {
  const target = state.foundations[f];
  if (target.length === 0) return rankOf(card) === 1;
  const last = top(target);
  return suitOf(last) === suitOf(card) && rankOf(card) === rankOf(last) + 1;
}

/** Whether a run whose first card is `card` may go onto tableau column `t`. */
export function fitsTableau(state, card, t) {
  const target = state.tableau[t];
  if (target.length === 0) return rankOf(card) === 13;
  const last = top(target);
  if (!state.up[last]) return false;
  return isRed(last) !== isRed(card) && rankOf(card) === rankOf(last) - 1;
}

/** The foundation a card would go to, or -1. Its own suit's pile first, then the first empty one. */
export function foundationFor(state, card) {
  for (let f = 0; f < 4; f += 1) {
    if (state.foundations[f].length && suitOf(state.foundations[f][0]) === suitOf(card) && fitsFoundation(state, card, f)) return f;
  }
  if (rankOf(card) === 1) {
    for (let f = 0; f < 4; f += 1) if (state.foundations[f].length === 0) return f;
  }
  return -1;
}

/** The cards a move from `from` starting at `index` would carry, or null when they cannot be picked up. */
export function runFrom(state, from, index) {
  const cards = pile(state, from);
  if (!cards || cards.length === 0) return null;
  if (from === "stock") return null;
  if (from === "waste" || from[0] === "f") {
    if (index !== cards.length - 1) return null;
    return [top(cards)];
  }
  if (index < 0 || index >= cards.length) return null;
  const run = cards.slice(index);
  if (!state.up[run[0]]) return null;
  for (let i = 1; i < run.length; i += 1) {
    const a = run[i - 1];
    const b = run[i];
    if (!state.up[b] || isRed(a) === isRed(b) || rankOf(b) !== rankOf(a) - 1) return null;
  }
  return run;
}

/** Whether a move { from, index, to } is legal. */
export function canMove(state, move) {
  if (state.won) return false;
  const { from, to } = move;
  if (from === to) return false;
  const run = runFrom(state, from, move.index);
  if (!run) return false;
  if (to[0] === "f") {
    if (run.length !== 1) return false;
    return fitsFoundation(state, run[0], Number(to.slice(1)));
  }
  if (to[0] === "t") return fitsTableau(state, run[0], Number(to.slice(1)));
  return false;
}

/** Whether the stock can be turned: cards in it, or a waste that may go back for another pass. */
export function canFlip(state) {
  if (state.won) return false;
  if (state.stock.length) return true;
  return state.waste.length > 0 && state.passes < passLimit(state);
}

function finish(next) {
  next.won = next.foundations.every((p) => p.length === 13);
  return next;
}

/** Turns the stock: `draw` cards to the waste, or the waste back to the stock for the next pass. */
export function flip(state) {
  if (!canFlip(state)) return state;
  const next = clone(state);
  if (next.stock.length) {
    const n = Math.min(next.draw, next.stock.length);
    for (let i = 0; i < n; i += 1) {
      const card = next.stock.pop();
      next.up[card] = 1;
      next.waste.push(card);
    }
  } else {
    while (next.waste.length) {
      const card = next.waste.pop();
      next.up[card] = 0;
      next.stock.push(card);
    }
    next.passes += 1;
    if (next.scoring === "standard") {
      next.score = Math.max(0, next.score + (next.draw === 3 ? STANDARD.recycleDrawThree : STANDARD.recycleDrawOne));
    }
  }
  next.moves += 1;
  return next;
}

/** Applies a legal move { from, index, to }; an illegal one returns the state unchanged. */
export function move(state, m) {
  if (!canMove(state, m)) return state;
  const next = clone(state);
  const source = pile(next, m.from);
  const run = source.splice(m.index);
  pile(next, m.to).push(...run);
  const toFoundation = m.to[0] === "f";
  const fromFoundation = m.from[0] === "f";
  if (next.scoring === "vegas") {
    if (toFoundation && !fromFoundation) {
      next.score += VEGAS_PAY;
      next.sent += 1;
    }
    if (fromFoundation && !toFoundation) {
      next.score -= VEGAS_PAY;
      next.sent -= 1;
    }
  } else {
    let delta = 0;
    if (toFoundation && !fromFoundation) delta += STANDARD.toFoundation;
    if (m.from === "waste" && m.to[0] === "t") delta += STANDARD.wasteToTableau;
    if (fromFoundation && !toFoundation) delta += STANDARD.foundationToTableau;
    if (toFoundation && !fromFoundation) next.sent += 1;
    if (fromFoundation && !toFoundation) next.sent -= 1;
    next.score = Math.max(0, next.score + delta);
  }
  // The card a move uncovers turns face up by itself.
  if (m.from[0] === "t" && source.length && !next.up[top(source)]) {
    next.up[top(source)] = 1;
    if (next.scoring === "standard") next.score += STANDARD.turnOver;
  }
  next.moves += 1;
  return finish(next);
}

/** Sends the top card of `from` to its foundation when that is legal. */
export function sendToFoundation(state, from) {
  const cards = pile(state, from);
  if (!cards || !cards.length || from === "stock") return state;
  const card = top(cards);
  const f = foundationFor(state, card);
  if (f < 0) return state;
  return move(state, { from, index: cards.length - 1, to: `f${f}` });
}

/** Every legal move from the state, flips excluded. */
export function legalMoves(state) {
  const out = [];
  if (state.won) return out;
  const sources = ["waste", "t0", "t1", "t2", "t3", "t4", "t5", "t6", "f0", "f1", "f2", "f3"];
  for (const from of sources) {
    const cards = pile(state, from);
    if (!cards.length) continue;
    const starts = from[0] === "t" ? cards.map((_, i) => i).filter((i) => state.up[cards[i]]) : [cards.length - 1];
    for (const index of starts) {
      const run = runFrom(state, from, index);
      if (!run) continue;
      if (run.length === 1 && from[0] !== "f") {
        const f = foundationFor(state, run[0]);
        if (f >= 0) out.push({ from, index, to: `f${f}` });
      }
      for (let t = 0; t < 7; t += 1) {
        const to = `t${t}`;
        if (to !== from && fitsTableau(state, run[0], t)) out.push({ from, index, to });
      }
    }
  }
  return out;
}

/** How useful a move is, for hints and the house's hand; below zero is a move not worth making. */
export function moveValue(state, m) {
  const fromCards = pile(state, m.from);
  const run = fromCards.slice(m.index);
  const first = run[0];
  if (m.to[0] === "f") {
    // A foundation card from the tableau that uncovers a face-down card is the best play there is.
    if (m.from[0] === "t" && m.index > 0 && !state.up[fromCards[m.index - 1]]) return 100;
    return 80 - rankOf(first);
  }
  if (m.from[0] === "f") return -1;
  if (m.from === "waste") return 40 + (rankOf(first) === 13 ? 5 : 0);
  // Tableau to tableau: only worth it when it uncovers a card or clears a column for a king.
  const below = m.index > 0 ? fromCards[m.index - 1] : -1;
  if (below >= 0 && !state.up[below]) return 60 + m.index;
  if (below < 0) {
    if (rankOf(first) === 13) return -1;
    const kingWaiting = kingCouldUse(state, m.from);
    return kingWaiting ? 30 : -1;
  }
  // Moving a face-up run off another face-up card frees that card for its foundation.
  if (foundationFor(state, below) >= 0) return 35;
  return -1;
}

function kingCouldUse(state, emptying) {
  if (state.waste.length && rankOf(top(state.waste)) === 13) return true;
  return state.tableau.some((cards, t) => {
    if (`t${t}` === emptying) return false;
    const i = cards.findIndex((c) => state.up[c]);
    return i > 0 && rankOf(cards[i]) === 13;
  });
}

/**
 * The next play worth making: a move, { flip: true }, or null when nothing helps.
 * Hints light it; the house's demo hand plays it.
 */
export function bestMove(state) {
  if (state.won) return null;
  let best = null;
  let bestValue = -1;
  for (const m of legalMoves(state)) {
    const value = moveValue(state, m);
    if (value > bestValue) {
      best = m;
      bestValue = value;
    }
  }
  if (best && bestValue >= 0) return best;
  if (canFlip(state)) return { flip: true };
  return null;
}

/** Every card left is face up and nothing waits in the stock or waste: the rest goes up by itself. */
export function canAutoFinish(state) {
  if (state.won) return false;
  if (state.stock.length || state.waste.length) return false;
  return state.tableau.every((cards) => cards.every((c) => state.up[c]));
}

/** The next foundation send of an auto-finish, lowest rank first, or null. */
export function autoFinishStep(state) {
  let best = null;
  let low = 99;
  for (const from of ["waste", "t0", "t1", "t2", "t3", "t4", "t5", "t6"]) {
    const cards = pile(state, from);
    if (!cards.length) continue;
    const card = top(cards);
    if (foundationFor(state, card) >= 0 && rankOf(card) < low) {
      low = rankOf(card);
      best = from;
    }
  }
  return best;
}

/** Whether the table is stuck: no move worth making, and the stock cannot be turned. */
export function isStuck(state) {
  if (state.won) return false;
  if (canFlip(state)) return false;
  return legalMoves(state).every((m) => moveValue(state, m) < 0);
}

/** Standard score with the clock: two points off every ten seconds, never below zero. */
export function standardScore(state, seconds) {
  return Math.max(0, state.score - 2 * Math.floor(seconds / 10));
}

/** The bonus a standard win earns for speed: 700,000 divided by the seconds, for games of 30 seconds or more. */
export function timeBonus(seconds) {
  return seconds >= 30 ? Math.floor(700000 / seconds) : 0;
}

/** Plays the house's hand to the end or until stuck; returns the plays. Used to pick the demo deal. */
export function playOut(state, limit = 600) {
  const plays = [];
  let s = state;
  let quiet = 0;
  while (!s.won && plays.length < limit) {
    if (canAutoFinish(s)) {
      const from = autoFinishStep(s);
      if (!from) break;
      const m = { from, index: pile(s, from).length - 1, to: `f${foundationFor(s, top(pile(s, from)))}` };
      plays.push(m);
      s = move(s, m);
      continue;
    }
    const m = bestMove(s);
    if (!m) break;
    if (m.flip) {
      quiet += 1;
      if (quiet > s.stock.length + s.waste.length + 2) break;
      plays.push(m);
      s = flip(s);
    } else {
      quiet = 0;
      plays.push(m);
      s = move(s, m);
    }
  }
  return { plays, state: s };
}
