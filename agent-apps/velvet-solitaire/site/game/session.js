// One sitting at the table: the game in play, its undo history, the clock, the bank, the
// house's demo hand, and what a tap, a drag, or a key does. Rules come from rules.js;
// where cards sit comes from layout.js; how they get there is motion.js.

import * as R from "./rules.js";
import { makeLayout, restTargets, cardRect, pileRect, PILES } from "./layout.js";
import { snapAll, setTargets, dragTo, release, hold, createMotion } from "./motion.js";

const SLUG = "velvet-solitaire";
const KEY_GAME = `${SLUG}:game`;
const KEY_STATS = `${SLUG}:stats`;
// The house's demo hands: deals its own play wins, draw one in one pass and draw three in three.
const DEMO_SEED = { 1: 150, 3: 1652 };

function load(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // A full or blocked store leaves the game playable; it simply is not kept.
  }
}

export function freshStats() {
  return { played: 0, won: 0, streak: 0, bestStreak: 0, bestTime: 0, bestScore: 0, bank: 0 };
}

export function createSession({ renderer, audio, hud, prefs, reduced, player = "" }) {
  const motion = createMotion({ reduced });
  const stats = { ...freshStats(), ...(load(KEY_STATS) || {}) };
  const s = {
    motion,
    prefs,
    stats,
    mode: "play",
    state: null,
    history: [],
    elapsed: 0,
    clockRunning: false,
    layout: null,
    targets: null,
    drag: null,
    held: null,
    cursor: { row: 1, col: 0, depth: -1, shown: false },
    hint: null,
    hintTime: 0,
    finishing: false,
    finishClock: 0,
    demo: null,
    won: 0,
    wonPaid: 0,
    lastSecond: -1,
    pendingSnap: false,
  };

  motion.onLand = () => {
    s.pendingSnap = true;
  };

  // ---- Layout -------------------------------------------------------------------------

  function areaRects() {
    const area = hud.tableArea();
    return { area, rails: hud.railRects() };
  }

  s.relayout = () => {
    const { area, rails } = areaRects();
    const compact = hud.isCompact();
    const keep = s.layout ? s.layout.scroll || 0 : 0;
    s.layout = makeLayout(area, { compact, draw: s.state ? s.state.draw : prefs.draw });
    s.layout.scroll = 0;
    renderer.setLayout(s.layout, window.innerWidth, window.innerHeight, rails);
    if (s.state) {
      s.targets = restTargets(s.layout, s.state);
      s.layout.scroll = Math.min(keep, s.layout.scrollMax);
      if (s.mode === "won" && renderer.cascadeRunning) return;
      if (!s.drag) setTargets(motion, s.targets, { flipDur: 0.001 });
      for (let i = 0; i < 52; i += 1) {
        if (motion.free[i]) continue;
        motion.x[i] = s.targets[i].x;
        motion.y[i] = s.targets[i].y;
      }
      paintPrint();
    }
    renderer.dirty = true;
  };

  function paintPrint() {
    const st = s.state;
    const spent = st && !st.stock.length && !R.canFlip(st);
    hud.paintPrint({ stockState: spent ? "spent" : "ok", draw: st ? st.draw : prefs.draw, scoring: st ? st.scoring : prefs.scoring });
  }

  // ---- Showing the state ----------------------------------------------------------------

  function sync(opts = {}) {
    s.targets = restTargets(s.layout, s.state);
    if (s.layout.scroll > s.layout.scrollMax) s.layout.scroll = s.layout.scrollMax;
    setTargets(motion, s.targets, opts);
    updateHud();
    if (!opts.quiet) persist();
  }

  function score() {
    const st = s.state;
    if (st.scoring === "vegas") return st.score;
    return R.standardScore(st, Math.floor(s.elapsed));
  }

  function updateHud() {
    const st = s.state;
    const vegas = st.scoring === "vegas";
    const demo = s.mode === "demo";
    hud.setNumbers({
      vegas,
      demo,
      bank: demo ? s.demo.bank : stats.bank,
      won: vegas ? st.sent * R.VEGAS_PAY : 0,
      score: vegas ? 0 : score(),
      seconds: Math.floor(s.elapsed),
      moves: st.moves,
    });
    hud.setControls({
      undo: !demo && !vegas && s.history.length > 0 && s.mode === "play",
      undoOff: vegas,
      finish: !demo && s.mode === "play" && R.canAutoFinish(st),
      hint: !demo && s.mode === "play",
      demo,
    });
    hud.setStats(stats, player);
  }

  function persist() {
    if (s.mode === "demo") return;
    if (s.mode === "won" || !s.state || s.state.won) {
      save(KEY_GAME, null);
    } else {
      save(KEY_GAME, {
        state: s.state,
        history: s.state.scoring === "vegas" ? [] : s.history.slice(-300),
        elapsed: s.elapsed,
      });
    }
    save(KEY_STATS, stats);
  }

  // ---- Games ----------------------------------------------------------------------------

  /** Fans every card out of the stock to its place, the deal a dealer makes. */
  function dealIn(state) {
    const start = s.layout.anchors.stock;
    const stacked = [];
    const order = [];
    for (let row = 0; row < 7; row += 1) for (let col = row; col < 7; col += 1) order.push(state.tableau[col][row]);
    const all = [...state.stock, ...order.slice().reverse()];
    all.forEach((card, i) => {
      stacked[card] = { x: start.x, y: start.y, z: i * 0.64, up: false, rot: 0, shade: i === 0 ? 1 : 0 };
    });
    snapAll(motion, stacked);
    const delays = new Array(52).fill(0);
    order.forEach((card, k) => {
      delays[card] = 0.06 + k * 0.026;
    });
    sync({ delays, flipDur: 0.26 });
  }

  /** Closes the books on the game in play before another is dealt. */
  function settleGame() {
    const st = s.state;
    if (!st || s.mode !== "play") return;
    if (st.scoring === "vegas") stats.bank += st.sent * R.VEGAS_PAY;
    if (st.moves > 0 && !st.won) stats.streak = 0;
  }

  s.newGame = ({ seed = null, animate = true } = {}) => {
    stopDemo();
    if (renderer.cascadeRunning) renderer.stopCascade(motion);
    settleGame();
    s.mode = "play";
    s.state = R.deal({ seed: seed ?? (Date.now() % 2147483647), draw: prefs.draw, scoring: prefs.scoring });
    if (s.state.scoring === "vegas") stats.bank -= R.VEGAS_BUY;
    s.history = [];
    s.elapsed = 0;
    s.clockRunning = false;
    s.finishing = false;
    clearHint();
    dropHeld();
    hud.hideWin();
    s.layout.draw = s.state.draw;
    s.layout.scroll = 0;
    paintPrint();
    if (animate) dealIn(s.state);
    else {
      s.targets = restTargets(s.layout, s.state);
      snapAll(motion, s.targets);
      updateHud();
      persist();
    }
    persist();
    hud.say("New deal. Good luck.");
  };

  /** Brings back the game saved on this device, or returns false when there is none. */
  s.restore = () => {
    const saved = load(KEY_GAME);
    if (!saved || !saved.state || saved.state.won) return false;
    s.state = saved.state;
    s.history = saved.history || [];
    s.elapsed = saved.elapsed || 0;
    s.mode = "play";
    s.clockRunning = s.state.moves > 0;
    s.layout.draw = s.state.draw;
    s.targets = restTargets(s.layout, s.state);
    snapAll(motion, s.targets);
    paintPrint();
    updateHud();
    hud.say("Your game is where you left it.");
    return true;
  };

  function commit(next, opts = {}) {
    if (next === s.state) return false;
    if (s.state.scoring === "standard" && s.mode === "play") s.history.push(s.state);
    s.state = next;
    if (s.mode === "play" && !s.clockRunning) {
      s.clockRunning = true;
      if (next.moves === 1) stats.played += 1;
    }
    clearHint();
    sync(opts);
    paintPrint();
    if (next.won) onWin();
    else if (s.mode === "play" && R.isStuck(next)) hud.say("No plays left on this deal. Deal again from the menu.");
    return true;
  }

  s.flip = () => {
    if (s.mode !== "play" || s.finishing) return;
    if (!R.canFlip(s.state)) {
      hud.say(s.state.stock.length || s.state.waste.length ? "That was the last pass through the deck." : "The stock is empty.");
      return;
    }
    const recycling = s.state.stock.length === 0;
    commit(R.flip(s.state), { flipDur: 0.22 });
    audio.play(recycling ? "slide" : "flip");
  };

  s.tryMove = (m, opts = {}) => {
    if (s.mode !== "play" || s.finishing) return false;
    if (!R.canMove(s.state, m)) return false;
    commit(R.move(s.state, m), opts);
    return true;
  };

  s.undo = () => {
    if (s.mode !== "play" || s.finishing) return;
    if (s.state.scoring === "vegas") {
      hud.say("Vegas scoring plays every card for keeps. Undo is off.");
      return;
    }
    const prev = s.history.pop();
    if (!prev) return;
    // The clock and the move count keep running: an undo is a move too.
    s.state = { ...prev, moves: s.state.moves + 1 };
    clearHint();
    dropHeld();
    sync();
    paintPrint();
    audio.play("slide");
  };

  // ---- Hints and auto-finish ------------------------------------------------------------

  function clearHint() {
    s.hint = null;
    renderer.setHalos(haloSpec());
  }

  s.showHint = () => {
    if (s.mode !== "play") return;
    const m = R.bestMove(s.state);
    if (!m) {
      hud.say("No plays left on this deal. Deal again from the menu.");
      return;
    }
    s.hint = m;
    s.hintTime = 0;
    if (m.flip) hud.say(s.state.stock.length ? "Turn the stock." : "Turn the waste back over.");
    else {
      const card = R.pile(s.state, m.from)[m.index];
      const target = m.to[0] === "f" ? "its foundation" : R.pile(s.state, m.to).length ? `the ${R.cardName(R.top(R.pile(s.state, m.to)))}` : "the empty column";
      hud.say(`Move the ${R.cardName(card)} to ${target}.`);
    }
    renderer.setHalos(haloSpec());
  };

  s.autoFinish = () => {
    if (s.mode !== "play" || !R.canAutoFinish(s.state)) return;
    s.finishing = true;
    s.finishClock = 0.05;
    hud.setControls({ undo: false, finish: false, hint: false, demo: false, undoOff: s.state.scoring === "vegas" });
  };

  function finishStep() {
    const from = R.autoFinishStep(s.state);
    if (!from) {
      s.finishing = false;
      return;
    }
    const cards = R.pile(s.state, from);
    const m = { from, index: cards.length - 1, to: `f${R.foundationFor(s.state, R.top(cards))}` };
    commit(R.move(s.state, m));
    audio.play("slide", { gain: 0.35 });
    if (s.state.won) s.finishing = false;
  }

  // ---- Winning --------------------------------------------------------------------------

  function onWin() {
    const st = s.state;
    const seconds = Math.floor(s.elapsed);
    s.clockRunning = false;
    s.finishing = false;
    clearHint();
    const demo = s.mode === "demo";
    s.mode = demo ? "demo" : "won";
    let bonus = 0;
    if (!demo) {
      stats.won += 1;
      stats.streak += 1;
      stats.bestStreak = Math.max(stats.bestStreak, stats.streak);
      if (!stats.bestTime || seconds < stats.bestTime) stats.bestTime = seconds;
      if (st.scoring === "standard") {
        bonus = R.timeBonus(seconds);
        stats.bestScore = Math.max(stats.bestScore, R.standardScore(st, seconds) + bonus);
      }
      save(KEY_GAME, null);
      save(KEY_STATS, stats);
    }
    const vegas = st.scoring === "vegas";
    const before = demo ? s.demo.bank : stats.bank;
    const base = vegas ? 0 : R.standardScore(st, seconds);
    const payout = vegas ? st.sent * R.VEGAS_PAY : bonus;
    if (!demo && vegas) stats.bank += payout;
    if (demo && vegas) s.demo.bank += payout;
    const summary = { seconds, moves: st.moves, vegas, bonus, score: base + bonus, bank: vegas ? before + payout : stats.bank, payout };
    // The cascade, with the rail rolling the winnings in as the cards fly.
    if (renderer.kind === "webgl" && !reduced) {
      setTimeout(() => {
        if (s.state !== st) return;
        renderer.startCascade(motion, st, {
          onLaunch: (card, k, total) => {
            const share = Math.round((payout * k) / total);
            if (vegas) {
              hud.rollBank(before + share);
              hud.setWon(payout - share);
            } else hud.rollScore(base + share);
            if (k % 6 === 1) audio.play("whoosh", { gain: 0.35 });
          },
          onDone: () => {
            if (demo) s.demoAfterCascade();
            else hud.showWin(summary, stats);
          },
        });
      }, 380);
    } else {
      if (vegas) hud.rollBank(summary.bank);
      else hud.rollScore(summary.score);
      if (demo) setTimeout(() => s.demoAfterCascade(), 1600);
      else hud.showWin(summary, stats);
    }
    if (!demo) save(KEY_STATS, stats);
  }

  // ---- The house's demo hand -----------------------------------------------------------

  function stopDemo() {
    if (!s.demo) return;
    if (s.drag && s.drag.demo) {
      release(motion, s.drag.cards);
      s.drag = null;
    }
    s.demo = null;
    hud.setDemo(false);
  }

  s.startDemo = () => {
    const draw = prefs.draw === 3 ? 3 : 1;
    const start = R.deal({ seed: DEMO_SEED[draw], draw, scoring: prefs.scoring });
    const plan = R.playOut(start).plays;
    s.mode = "demo";
    s.state = start;
    s.history = [];
    s.elapsed = 0;
    s.demo = { plays: plan, at: 0, clock: -0.85, bank: prefs.scoring === "vegas" ? -R.VEGAS_BUY : 0, gestured: 0 };
    s.layout.draw = draw;
    paintPrint();
    hud.setDemo(true);
    dealIn(start);
  };

  s.demoAfterCascade = () => {
    if (s.mode !== "demo") return;
    setTimeout(() => {
      if (s.mode === "demo" && s.demo) s.startDemo();
    }, 1200);
  };

  /** Ends the demo and deals the person's own game. */
  s.dealIn = () => {
    if (s.mode !== "demo") return;
    stopDemo();
    if (renderer.cascadeRunning) renderer.stopCascade(motion);
    s.mode = "play";
    s.state = null;
    s.newGame();
  };

  function demoStep(dt) {
    const d = s.demo;
    if (!d || s.state.won) return;
    if (s.drag && s.drag.demo) {
      // A drag the house makes by hand: lift, carry along a slight arc, drop.
      const g = s.drag;
      g.t = Math.min(1, g.t + dt / g.dur);
      const e = g.t < 0.5 ? 2 * g.t * g.t : 1 - Math.pow(-2 * g.t + 2, 2) / 2;
      const x = g.x0 + (g.x1 - g.x0) * e;
      const y = g.y0 + (g.y1 - g.y0) * e - Math.sin(Math.PI * g.t) * s.layout.cardH * 0.35;
      dragTo(motion, g.cards, x, y, s.layout.upGap);
      if (g.t >= 1) {
        release(motion, g.cards);
        s.drag = null;
        s.state = R.move(s.state, g.move);
        sync({ quiet: true });
        afterDemoPlay();
      }
      return;
    }
    d.clock += dt;
    // The first plays go by hand, slow enough to watch; the rest of the hand plays out fast.
    const handPaced = d.at < 4;
    const gap = handPaced ? 0.28 : d.at < 9 ? 0.11 : 0.022;
    if (d.clock < gap) return;
    d.clock = 0;
    const m = d.plays[d.at];
    if (!m) return;
    d.at += 1;
    if (m.flip) {
      s.state = R.flip(s.state);
      sync({ quiet: true, flipDur: 0.22 });
      afterDemoPlay();
      return;
    }
    if (handPaced && m.to[0] === "t") {
      const cards = R.pile(s.state, m.from).slice(m.index);
      const from = s.targets[cards[0]];
      const destCards = R.pile(s.state, m.to);
      const dest = destCards.length ? s.targets[R.top(destCards)] : null;
      const anchor = s.layout.anchors[m.to];
      const x1 = anchor.x;
      const y1 = dest ? dest.y + s.layout.upGap : anchor.y;
      s.drag = { demo: true, cards, move: m, t: 0, dur: 0.46, x0: from.x, y0: from.y, x1, y1 };
      return;
    }
    s.state = R.move(s.state, m);
    sync({ quiet: true });
    afterDemoPlay();
  }

  function afterDemoPlay() {
    const st = s.state;
    if (st.scoring === "vegas") s.demo.bank = -R.VEGAS_BUY;
    paintPrint();
    updateHud();
    if (st.won) onWin();
  }

  // ---- Pointer --------------------------------------------------------------------------

  /** What sits under a point: { pile, index } for a card, { pile, index: -1 } for an empty spot, or null. */
  s.hit = (x, y) => {
    if (!s.state) return null;
    const yy = y + (s.layout.scroll || 0);
    const inside = (r) => x >= r.x0 && x <= r.x1 && yy >= r.y0 && yy <= r.y1;
    // Top piles and columns, topmost card first.
    for (const pile of PILES) {
      const cards = R.pile(s.state, pile);
      for (let i = cards.length - 1; i >= 0; i -= 1) {
        const t = s.targets[cards[i]];
        if (inside(cardRect(s.layout, t))) return { pile, index: i, card: cards[i] };
        if (pile === "stock" || pile === "waste" || pile[0] === "f") break;
      }
      if (!cards.length || pile === "stock") {
        if (inside(pileRect(s.layout, pile))) return { pile, index: -1, card: -1 };
      }
    }
    return null;
  };

  s.canPick = (h) => {
    if (!h || s.mode !== "play" || s.finishing || h.index < 0 || h.pile === "stock") return null;
    return R.runFrom(s.state, h.pile, h.index);
  };

  s.dragStart = (h, x, y) => {
    const run = s.canPick(h);
    if (!run) return false;
    clearHint();
    dropHeld();
    const t = s.targets[run[0]];
    s.drag = { cards: run, from: h.pile, index: h.index, dx: t.x - x, dy: t.y - (y + (s.layout.scroll || 0)) };
    dragTo(motion, run, x + s.drag.dx, y + (s.layout.scroll || 0) + s.drag.dy, s.layout.upGap);
    audio.play("slide", { gain: 0.28 });
    return true;
  };

  s.dragMove = (x, y) => {
    if (!s.drag || s.drag.demo) return;
    dragTo(motion, s.drag.cards, x + s.drag.dx, y + (s.layout.scroll || 0) + s.drag.dy, s.layout.upGap);
  };

  /** The pile a dragged run lands on: the legal pile its card overlaps most. */
  function dropTarget() {
    const d = s.drag;
    const first = d.cards[0];
    const cx = motion.x[first];
    const cy = motion.y[first];
    const w = s.layout.cardW;
    const h = s.layout.cardH;
    let best = null;
    let bestArea = 0;
    for (const pile of PILES) {
      if (pile === "stock" || pile === "waste" || pile === d.from) continue;
      const cards = R.pile(s.state, pile);
      let r = cards.length ? cardRect(s.layout, s.targets[R.top(cards)]) : pileRect(s.layout, pile);
      if (pile[0] === "t") r = { ...r, y1: r.y1 + h * 0.5 };
      const ox = Math.max(0, Math.min(cx + w / 2, r.x1) - Math.max(cx - w / 2, r.x0));
      const oy = Math.max(0, Math.min(cy + h / 2, r.y1) - Math.max(cy - h / 2, r.y0));
      const area = ox * oy;
      const m = { from: d.from, index: d.index, to: pile };
      if (area > bestArea && R.canMove(s.state, m)) {
        best = m;
        bestArea = area;
      }
    }
    return best;
  }

  s.dragEnd = () => {
    const d = s.drag;
    if (!d || d.demo) return;
    const m = dropTarget();
    release(motion, d.cards);
    s.drag = null;
    if (m && s.tryMove(m)) return;
    // Back where it came from, with the same spring.
    setTargets(motion, s.targets);
    audio.play("slide", { gain: 0.25 });
  };

  s.dragCancel = () => {
    if (!s.drag || s.drag.demo) return;
    release(motion, s.drag.cards);
    s.drag = null;
    setTargets(motion, s.targets);
  };

  /** A tap: the stock turns; a card goes to its foundation, or else to the best column. */
  s.tap = (h) => {
    if (!h) return;
    if (h.pile === "stock") {
      s.flip();
      return;
    }
    const run = s.canPick(h);
    if (!run) return;
    if (run.length === 1 && h.pile[0] !== "f") {
      const f = R.foundationFor(s.state, run[0]);
      if (f >= 0 && s.tryMove({ from: h.pile, index: h.index, to: `f${f}` })) return;
    }
    const options = [];
    for (let t = 0; t < 7; t += 1) {
      const m = { from: h.pile, index: h.index, to: `t${t}` };
      if (R.canMove(s.state, m)) options.push(m);
    }
    options.sort((a, b) => R.pile(s.state, b.to).length - R.pile(s.state, a.to).length);
    if (options.length && s.tryMove(options[0])) return;
    nudge(run);
  };

  /** A small shake for a card that has nowhere to go. */
  function nudge(cards) {
    if (reduced) return;
    for (const c of cards) motion.vx[c] += s.layout.cardW * 4;
    motion.active = true;
    audio.play("snap", { gain: 0.25, pitch: 0.7 });
  }

  s.scrollBy = (dy) => {
    if (!s.layout || !s.layout.scrollMax) return;
    s.layout.scroll = Math.max(0, Math.min(s.layout.scrollMax, (s.layout.scroll || 0) + dy));
    renderer.dirty = true;
    renderer.setHalos(haloSpec());
  };

  // ---- Keyboard -------------------------------------------------------------------------

  const TOP = ["stock", "waste", null, "f0", "f1", "f2", "f3"];
  function cursorPile() {
    return s.cursor.row === 0 ? TOP[s.cursor.col] : `t${s.cursor.col}`;
  }
  function cursorIndex() {
    const pile = cursorPile();
    const cards = R.pile(s.state, pile);
    if (s.cursor.row === 1 && s.cursor.depth >= 0 && s.cursor.depth < cards.length) return s.cursor.depth;
    return cards.length - 1;
  }

  function dropHeld() {
    if (!s.held) return;
    hold(motion, s.held.cards, false);
    s.held = null;
  }

  s.key = (key) => {
    if (s.mode === "demo") {
      s.dealIn();
      return true;
    }
    if (!s.state || s.mode !== "play") {
      if (key === "n") hud.confirmNew();
      return key === "n";
    }
    const c = s.cursor;
    const move = (dc) => {
      do c.col = (c.col + dc + 7) % 7;
      while (c.row === 0 && TOP[c.col] === null);
      c.depth = -1;
    };
    switch (key) {
      case "ArrowLeft":
        move(-1);
        break;
      case "ArrowRight":
        move(1);
        break;
      case "ArrowUp": {
        if (c.row === 1) {
          const cards = R.pile(s.state, `t${c.col}`);
          const idx = cursorIndex();
          if (idx > 0 && s.state.up[cards[idx - 1]]) c.depth = idx - 1;
          else {
            c.row = 0;
            if (TOP[c.col] === null) c.col = 1;
          }
        }
        break;
      }
      case "ArrowDown": {
        if (c.row === 0) {
          c.row = 1;
          c.depth = -1;
        } else {
          const cards = R.pile(s.state, `t${c.col}`);
          const idx = cursorIndex();
          c.depth = idx < cards.length - 1 ? idx + 1 : -1;
        }
        break;
      }
      case " ":
      case "Enter": {
        const pile = cursorPile();
        if (s.held) {
          const m = { from: s.held.from, index: s.held.index, to: pile };
          const cards = s.held.cards;
          dropHeld();
          if (!s.tryMove(m)) nudge(cards);
        } else if (pile === "stock") s.flip();
        else {
          const index = cursorIndex();
          const run = s.canPick({ pile, index });
          if (run) {
            s.held = { from: pile, index, cards: run };
            hold(motion, run, true);
            audio.play("slide", { gain: 0.2 });
          }
        }
        break;
      }
      case "f":
        dropHeld();
        if (cursorPile() !== "stock") {
          const next = R.sendToFoundation(s.state, cursorPile());
          if (next !== s.state) commit(next);
        }
        break;
      case "u":
        s.undo();
        break;
      case "h":
        s.showHint();
        break;
      case "n":
        hud.confirmNew();
        break;
      case "Escape":
        if (!s.held) return false;
        dropHeld();
        break;
      default:
        return false;
    }
    c.shown = true;
    renderer.setHalos(haloSpec());
    return true;
  };

  s.hideCursor = () => {
    if (!s.cursor.shown) return;
    s.cursor.shown = false;
    renderer.setHalos(haloSpec());
  };

  function spotFor(pile, index) {
    const cards = R.pile(s.state, pile);
    const i = index ?? cards.length - 1;
    if (i >= 0 && cards[i] !== undefined) {
      const c = cards[i];
      return { x: motion.x[c], y: motion.y[c], z: motion.z[c] };
    }
    const a = s.layout.anchors[pile];
    return { x: a.x, y: a.y, z: 0 };
  }

  function haloSpec() {
    const spec = { hintFrom: null, hintTo: null, cursor: null };
    if (!s.state || !s.layout) return spec;
    if (s.hint) {
      const fade = Math.max(0, 1 - Math.max(0, s.hintTime - 2.6) / 0.6);
      if (s.hint.flip) spec.hintFrom = { ...spotFor("stock"), power: fade };
      else {
        spec.hintFrom = { ...spotFor(s.hint.from, s.hint.index), power: fade };
        spec.hintTo = { ...spotFor(s.hint.to), power: fade * 0.8 };
      }
    }
    if (s.cursor.shown && s.mode === "play") spec.cursor = { ...spotFor(cursorPile(), cursorIndex()), power: 1 };
    return spec;
  }

  // ---- Clock ----------------------------------------------------------------------------

  s.tick = (dt) => {
    if (s.mode === "demo") demoStep(dt);
    if (s.clockRunning && s.mode === "play" && !document.hidden) {
      s.elapsed += dt;
      const sec = Math.floor(s.elapsed);
      if (sec !== s.lastSecond) {
        s.lastSecond = sec;
        updateHud();
        if (sec % 5 === 0) persist();
      }
    }
    if (s.finishing) {
      s.finishClock -= dt;
      if (s.finishClock <= 0) {
        s.finishClock = 0.085;
        finishStep();
      }
    }
    if (s.hint) {
      s.hintTime += dt;
      if (s.hintTime > 3.2) clearHint();
      else renderer.setHalos(haloSpec());
    } else if (s.held || s.cursor.shown) renderer.setHalos(haloSpec());
    if (s.pendingSnap) {
      s.pendingSnap = false;
      if (s.mode !== "demo") audio.play("snap");
    }
  };

  s.updateHud = updateHud;
  s.persist = persist;
  s.isBusy = () => !!(s.hint || s.held || s.cursor.shown || s.finishing || s.mode === "demo");
  return s;
}
