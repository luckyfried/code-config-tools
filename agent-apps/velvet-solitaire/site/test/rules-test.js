// The rules' fixed cases. Open test/rules.html on the served page to see them pass, or run
// this file with Node; each case names what it checks.

import * as R from "../game/rules.js";

// A fixed deck: card ids in dealing order, so every case knows exactly where each card is.
// Rows deal left to right: t0 gets deck[0]; t1 gets deck[1] and deck[7]; and so on.
function deckWith(placements) {
  const deck = new Array(52).fill(-1);
  const used = new Set();
  for (const [at, card] of placements) {
    deck[at] = card;
    used.add(card);
  }
  const rest = Array.from({ length: 52 }, (_, i) => i).filter((c) => !used.has(c));
  for (let i = 0; i < 52; i += 1) if (deck[i] < 0) deck[i] = rest.shift();
  return deck;
}

const card = (rank, suit) => ["spades", "hearts", "diamonds", "clubs"].indexOf(suit) * 13 + rank - 1;

export const cases = [
  [
    "A legal tableau move: a red 7 onto a black 8",
    () => {
      // Top cards: t0 = 8 of spades (deck[0]), t1's top = 7 of hearts (deck[7]).
      const s = R.deal({ deck: deckWith([[0, card(8, "spades")], [7, card(7, "hearts")]]) });
      const m = { from: "t1", index: 1, to: "t0" };
      const ok = R.canMove(s, m);
      const n = R.move(s, m);
      return ok && n.tableau[0].length === 2 && R.top(n.tableau[0]) === card(7, "hearts") && n.up[n.tableau[1][0]] === 1;
    },
  ],
  [
    "An illegal tableau move: a black 7 onto a black 8 is refused",
    () => {
      const s = R.deal({ deck: deckWith([[0, card(8, "spades")], [7, card(7, "clubs")]]) });
      const m = { from: "t1", index: 1, to: "t0" };
      return !R.canMove(s, m) && R.move(s, m) === s;
    },
  ],
  [
    "A foundation send: an ace goes up and the card under it turns over",
    () => {
      const s = R.deal({ deck: deckWith([[7, card(1, "diamonds")]]), scoring: "standard" });
      const n = R.sendToFoundation(s, "t1");
      return n.foundations.some((f) => f.length === 1 && f[0] === card(1, "diamonds")) && n.tableau[1].length === 1 && n.up[n.tableau[1][0]] === 1 && n.score === 15;
    },
  ],
  [
    "An undo: the state before a move comes back whole",
    () => {
      const s = R.deal({ deck: deckWith([[0, card(8, "spades")], [7, card(7, "hearts")]]) });
      const history = [s];
      const n = R.move(s, { from: "t1", index: 1, to: "t0" });
      const back = history.pop();
      return n !== s && JSON.stringify(back) === JSON.stringify(R.deal({ deck: deckWith([[0, card(8, "spades")], [7, card(7, "hearts")]]) }));
    },
  ],
  [
    "A Vegas game ends at -$52 + $5 for each card sent",
    () => {
      let s = R.deal({ seed: 150, draw: 1, scoring: "vegas" });
      const start = s.score;
      const { state } = R.playOut(s);
      s = state;
      return start === -52 && s.won && s.sent === 52 && s.score === -52 + 5 * s.sent && s.score === 208;
    },
  ],
  [
    "Vegas draw one allows one pass through the stock",
    () => {
      let s = R.deal({ seed: 9, draw: 1, scoring: "vegas" });
      while (s.stock.length) s = R.flip(s);
      return !R.canFlip(s) && R.flip(s) === s;
    },
  ],
  [
    "Vegas draw three allows three passes",
    () => {
      let s = R.deal({ seed: 9, draw: 3, scoring: "vegas" });
      let recycles = 0;
      for (let i = 0; i < 200 && R.canFlip(s); i += 1) {
        if (!s.stock.length) recycles += 1;
        s = R.flip(s);
      }
      return recycles === 2 && s.passes === 3;
    },
  ],
  [
    "Standard scoring allows unlimited passes and takes 100 for each in draw one",
    () => {
      let s = R.deal({ seed: 9, draw: 1, scoring: "standard" });
      s = { ...s, score: 300 };
      for (let i = 0; i < 24 * 3 + 3; i += 1) s = R.flip(s);
      return R.canFlip(s) && s.passes === 4 && s.score === 0;
    },
  ],
  [
    "A king, and only a king, fills an empty column",
    () => {
      const s = R.deal({ deck: deckWith([[0, card(1, "clubs")], [7, card(13, "hearts")], [13, card(12, "spades")]]) });
      const empty = R.sendToFoundation(s, "t0");
      return empty.tableau[0].length === 0 && R.canMove(empty, { from: "t1", index: 1, to: "t0" }) && !R.canMove(empty, { from: "t2", index: 2, to: "t0" });
    },
  ],
];

export function runAll() {
  return cases.map(([name, fn]) => {
    let pass = false;
    let error = "";
    try {
      pass = fn() === true;
    } catch (e) {
      error = String(e);
    }
    return { name, pass, error };
  });
}

if (typeof document === "undefined") {
  const results = runAll();
  for (const r of results) console.log(`${r.pass ? "pass" : "FAIL"}  ${r.name}${r.error ? `  (${r.error})` : ""}`);
  const failed = results.filter((r) => !r.pass).length;
  console.log(`${results.length - failed} of ${results.length} pass`);
  if (failed && typeof process !== "undefined") process.exitCode = 1;
}
