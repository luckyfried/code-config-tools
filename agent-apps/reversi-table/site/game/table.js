// What the table shows over time: every disc's flip, drop, and lift, the tray stacks, the legal dots, the preview,
// the last-move glow, and the hint. Both renderers (the 3D scene and the 2D fallback) read poses from here, so the
// wave, the stagger, and the ticks are the same in either.
import { EMPTY, BLACK, WHITE, opponent, rowOf, colOf, countedOut } from "./reversi.js";

export const TIMING = {
  flip: 380, // one disc's half-turn
  stagger: 45, // between neighbors along a captured line
  drop: 190, // a placed disc landing
  lift: 260, // a disc leaving the board
  fade: 150, // reduced motion: the color cross-fade
  tray: 220, // a disc joining or leaving a stack
  shake: 560, // a pass rattles the passing side's tray
  endStagger: 15, // the counting wave at the end of a game
  glow: 1400, // the last move's glow
};

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const easeInOutCubic = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const easeOutCubic = (x) => 1 - Math.pow(1 - x, 3);
const easeInCubic = (x) => x * x * x;
export const DISC_RADIUS = 0.42;

export class Table {
  constructor({ reduced = false, onSound = () => {} } = {}) {
    this.reduced = reduced;
    this.onSound = onSound;
    this.cells = Array.from({ length: 64 }, () => ({ color: EMPTY, anim: null }));
    this.trays = { [BLACK]: [], [WHITE]: [] };
    this.shake = { [BLACK]: -1e9, [WHITE]: -1e9 };
    this.events = [];
    this.legal = [];
    this.legalAt = 0;
    this.legalColor = BLACK;
    this.preview = null;
    this.last = { square: -1, at: -1e9 };
    this.hint = { square: -1, at: -1e9 };
    this.cursor = { square: 27, visible: false };
    this.busyUntil = 0;
    this.version = 0;
  }

  /** Runs `fn` at time `at` (ms, performance.now() clock). */
  schedule(at, fn) {
    this.events.push({ at, fn });
    this.events.sort((a, b) => a.at - b.at);
  }

  clearEvents() {
    this.events.length = 0;
  }

  /** Shows `board` at once: no motion. */
  setBoard(board) {
    this.clearEvents();
    for (let i = 0; i < 64; i += 1) this.cells[i] = { color: board[i], anim: null };
    let black = 0;
    let white = 0;
    for (const c of board) {
      if (c === BLACK) black += 1;
      else if (c === WHITE) white += 1;
    }
    this.trays[BLACK] = Array.from({ length: black }, () => ({ born: -1e9, dying: null }));
    this.trays[WHITE] = Array.from({ length: white }, () => ({ born: -1e9, dying: null }));
    this.legal = [];
    this.preview = null;
    this.last = { square: -1, at: -1e9 };
    this.hint = { square: -1, at: -1e9 };
    this.busyUntil = 0;
    this.version += 1;
  }

  trayAdd(color, at) {
    this.trays[color].push({ born: at, dying: null });
  }

  trayRemove(color, at) {
    const stack = this.trays[color];
    for (let j = stack.length - 1; j >= 0; j -= 1) {
      if (stack[j].dying === null) {
        stack[j].dying = at;
        return;
      }
    }
  }

  /** Living discs in a tray at time `now`: what the stacks read as. */
  trayCount(color, now) {
    let n = 0;
    for (const d of this.trays[color]) if (d.born <= now && (d.dying === null || d.dying > now)) n += 1;
    return n;
  }

  /**
   * `color` plays `square`, capturing `lines` (from the rules). Each line flips outward from the placed disc with the
   * stagger, each disc a half-turn about the line's axis; the trays trade a disc as each one lands. `pace` below 1
   * plays faster (the replay's fast-forward). Returns the time the last disc settles.
   */
  place(square, color, lines, now, pace = 1) {
    const other = opponent(color);
    const drop = TIMING.drop * pace;
    this.cells[square] = { color, anim: { type: "drop", start: now, dur: drop } };
    this.trayAdd(color, now + drop * 0.5);
    this.schedule(now + drop * 0.9, () => this.onSound("place", 0, pace));
    this.last = { square, at: now + drop * 0.7 };
    this.legal = [];
    this.preview = null;
    this.hint = { square: -1, at: -1e9 };
    let end = now + drop;
    if (this.reduced) {
      const start = now + drop;
      for (const line of lines) {
        for (const sq of line.squares) {
          this.cells[sq] = { color, anim: { type: "fade", from: other, to: color, start, dur: TIMING.fade } };
          this.trayRemove(other, start + TIMING.fade);
          this.trayAdd(color, start + TIMING.fade);
        }
      }
      this.schedule(start, () => this.onSound("tick", 0, pace));
      end = start + TIMING.fade;
    } else {
      const flip = TIMING.flip * pace;
      const stagger = TIMING.stagger * pace;
      const ticks = new Map();
      for (const line of lines) {
        const [dr, dc] = line.dir;
        const len = Math.hypot(dr, dc);
        const ax = dr / len;
        const az = -dc / len;
        line.squares.forEach((sq, k) => {
          const start = now + drop * 0.75 + k * stagger;
          this.cells[sq] = { color, anim: { type: "flip", from: other, to: color, start, dur: flip, ax, az, turn: Math.PI } };
          this.trayRemove(other, start + flip * 0.55);
          this.trayAdd(color, start + flip * 0.55);
          ticks.set(k, start + flip * 0.92);
          end = Math.max(end, start + flip);
        });
      }
      for (const [k, at] of ticks) this.schedule(at, () => this.onSound("tick", k, pace));
    }
    this.busyUntil = Math.max(this.busyUntil, end + 40);
    this.version += 1;
    return end;
  }

  /**
   * Moves the shown board to `board` (an undo, a new game): discs that change color flip back in a quick sweep,
   * discs that leave lift away, discs that arrive drop in, and the trays follow. Returns the settle time.
   */
  syncTo(board, now, { stagger = 26, order = "distance" } = {}) {
    const changes = [];
    for (let i = 0; i < 64; i += 1) {
      const shown = this.cells[i].color;
      if (shown !== board[i]) changes.push(i);
    }
    const key = (i) => (order === "distance" ? Math.hypot(rowOf(i) - 3.5, colOf(i) - 3.5) : i);
    changes.sort((a, b) => key(b) - key(a));
    let end = now;
    changes.forEach((i, k) => {
      const start = now + k * stagger;
      const from = this.cells[i].color;
      const to = board[i];
      if (from === EMPTY) {
        this.cells[i] = { color: to, anim: { type: "drop", start, dur: TIMING.drop } };
        this.trayAdd(to, start + TIMING.drop * 0.5);
        end = Math.max(end, start + TIMING.drop);
      } else if (to === EMPTY) {
        this.cells[i] = { color: EMPTY, anim: { type: "lift", start, dur: TIMING.lift, from } };
        this.trayRemove(from, start + TIMING.lift * 0.3);
        end = Math.max(end, start + TIMING.lift);
      } else if (this.reduced) {
        this.cells[i] = { color: to, anim: { type: "fade", from, to, start, dur: TIMING.fade } };
        this.trayRemove(from, start + TIMING.fade);
        this.trayAdd(to, start + TIMING.fade);
        end = Math.max(end, start + TIMING.fade);
      } else {
        this.cells[i] = { color: to, anim: { type: "flip", from, to, start, dur: TIMING.flip, ax: 1, az: 0, turn: Math.PI } };
        this.trayRemove(from, start + TIMING.flip * 0.5);
        this.trayAdd(to, start + TIMING.flip * 0.5);
        end = Math.max(end, start + TIMING.flip);
      }
    });
    if (changes.length > 0) this.schedule(now + 60, () => this.onSound("tick", 0, 1));
    this.legal = [];
    this.preview = null;
    this.last = { square: -1, at: -1e9 };
    this.hint = { square: -1, at: -1e9 };
    this.busyUntil = Math.max(this.busyUntil, end + 40);
    this.version += 1;
    return end;
  }

  /**
   * The end of a game: one long wave in reading order turns every disc to its counted color, the winner's discs
   * first, so the finished board reads as the score. Discs already showing their color hop in place.
   */
  endWave(board, now) {
    const target = countedOut(board);
    let k = 0;
    let end = now;
    for (let i = 0; i < 64; i += 1) {
      if (board[i] === EMPTY) continue;
      const start = now + k * TIMING.endStagger;
      const from = this.cells[i].color;
      const to = target[i];
      if (this.reduced) {
        if (from !== to) this.cells[i] = { color: to, anim: { type: "fade", from, to, start: now, dur: TIMING.fade } };
        end = Math.max(end, now + TIMING.fade);
      } else {
        const turn = from === to ? 2 * Math.PI : Math.PI;
        this.cells[i] = { color: to, anim: { type: "flip", from, to, start, dur: TIMING.flip * 1.25, ax: Math.SQRT1_2, az: -Math.SQRT1_2, turn } };
        if (k % 3 === 0) this.schedule(start + TIMING.flip, () => this.onSound("tick", Math.min(12, Math.floor(k / 5)), 1));
        end = Math.max(end, start + TIMING.flip * 1.25);
      }
      k += 1;
    }
    this.legal = [];
    this.preview = null;
    this.busyUntil = Math.max(this.busyUntil, end + 40);
    this.version += 1;
    return end;
  }

  passShake(color, now) {
    this.shake[color] = now;
    this.onSound("pass", 0, 1);
    this.version += 1;
  }

  setLegal(squares, color, now) {
    this.legal = squares;
    this.legalColor = color;
    this.legalAt = now;
    this.version += 1;
  }

  setPreview(preview) {
    const same =
      (preview === null && this.preview === null) ||
      (preview && this.preview && preview.square === this.preview.square && preview.color === this.preview.color);
    if (same) return;
    this.preview = preview;
    this.version += 1;
  }

  setHint(square, now) {
    this.hint = { square, at: now };
    this.version += 1;
  }

  setCursor(square, visible) {
    if (this.cursor.square === square && this.cursor.visible === visible) return;
    this.cursor = { square, visible };
    this.version += 1;
  }

  /** Runs due events; answers whether anything is still moving, so the loop knows to keep drawing. */
  update(now) {
    while (this.events.length > 0 && this.events[0].at <= now) this.events.shift().fn(now);
    let moving = this.events.length > 0;
    for (const cell of this.cells) {
      if (cell.anim === null) continue;
      if (now >= cell.anim.start + cell.anim.dur) cell.anim = null;
      else moving = true;
    }
    for (const color of [BLACK, WHITE]) {
      const stack = this.trays[color];
      for (let j = stack.length - 1; j >= 0; j -= 1) {
        const d = stack[j];
        if (d.dying !== null && now > d.dying + TIMING.tray) stack.splice(j, 1);
        else if (now < d.born + TIMING.tray || (d.dying !== null && now >= d.dying - 1)) moving = true;
        else if (d.dying !== null) moving = true;
      }
      if (now < this.shake[color] + TIMING.shake) moving = true;
    }
    if (now < this.last.at + TIMING.glow) moving = true;
    if (this.hint.square >= 0 && now < this.hint.at + 2400) moving = true;
    if (this.legal.length > 0 && now < this.legalAt + 260) moving = true;
    return moving;
  }

  /**
   * One square's disc at `now`: `show` (the face color it rests on before any turn), `angle` about the axis
   * (ax, 0, az), `lift` above resting height, `scale`, and for reduced motion a `fade` toward `to`.
   */
  pose(i, now, out) {
    const cell = this.cells[i];
    out.visible = cell.color !== EMPTY;
    out.show = cell.color;
    out.to = cell.color;
    out.angle = 0;
    out.ax = 1;
    out.az = 0;
    out.lift = 0;
    out.scale = 1;
    out.fade = 0;
    const a = cell.anim;
    if (a === null) return out;
    const p = clamp01((now - a.start) / a.dur);
    if (a.type === "flip") {
      out.show = a.from;
      out.to = a.to;
      if (now < a.start) return out;
      const e = easeInOutCubic(p);
      out.angle = a.turn * e;
      out.ax = a.ax;
      out.az = a.az;
      // Lift enough that the rim clears the board through the turn, plus a small hop.
      out.lift = DISC_RADIUS * Math.abs(Math.sin(out.angle)) + 0.16 * Math.sin(Math.PI * p);
    } else if (a.type === "drop") {
      if (now < a.start) {
        out.visible = false;
        return out;
      }
      out.lift = (1 - easeOutCubic(p)) * 0.9;
    } else if (a.type === "lift") {
      out.visible = p < 1;
      out.show = a.from;
      out.to = a.from;
      if (now < a.start) return out;
      out.lift = easeInCubic(p) * 0.7;
      out.scale = 1 - easeInCubic(p);
    } else if (a.type === "fade") {
      out.show = a.from;
      out.to = a.to;
      out.fade = now < a.start ? 0 : p;
    }
    return out;
  }

  /** One tray disc: its slot `j` in the stack, its drop or lift, and the tray's pass shake. */
  trayPose(color, j, now, out) {
    const d = this.trays[color][j];
    out.visible = d !== undefined && now >= d.born;
    out.lift = 0;
    out.scale = 1;
    if (!out.visible) return out;
    // A disc leaving a stack goes at once, at full size: one shrinking or rising over its stack reads, from above,
    // as a dot or ring on the top disc's face. The board's flip already shows where it went.
    if (d.dying !== null && now >= d.dying) {
      out.visible = false;
      return out;
    }
    const pIn = clamp01((now - d.born) / TIMING.tray);
    out.lift = (1 - easeOutCubic(pIn)) * 0.1;
    return out;
  }

  shakeOffset(color, now) {
    const t = now - this.shake[color];
    if (t < 0 || t > TIMING.shake) return 0;
    const p = t / TIMING.shake;
    return Math.sin(p * Math.PI * 7) * 0.16 * (1 - p);
  }

  glowLevel(now) {
    const t = now - this.last.at;
    if (this.last.square < 0 || t < 0 || t > TIMING.glow) return 0;
    const p = t / TIMING.glow;
    return p < 0.15 ? p / 0.15 : 1 - (p - 0.15) / 0.85;
  }

  hintLevel(now) {
    const t = now - this.hint.at;
    if (this.hint.square < 0 || t < 0 || t > 2400) return 0;
    return 0.5 - 0.5 * Math.cos((t / 800) * Math.PI * 2);
  }

  legalLevel(now) {
    return easeOutCubic(clamp01((now - this.legalAt) / 260));
  }
}
