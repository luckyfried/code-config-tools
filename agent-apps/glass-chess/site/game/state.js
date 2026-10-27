// The game and its settings: the moves so far (chess.js checks every rule), who plays which side, the clock, and
// the result. Everything a person would want back after a reload lives under one localStorage key.
import { Chess } from "../vendor/chess.js";
import { Clock } from "./clock.js";

export const STORE_KEY = "glass-chess:state";
export const THEMES = ["glass-noir", "glass-amber", "ice"];
export const CLOCK_NAMES = { none: "No clock", "5+0": "5 min", "10+0": "10 min", "15+10": "15 | 10" };

export function load() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) ?? null; } catch { return null; }
}

export function store(data) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch { /* a full or blocked store keeps the game in memory */ }
}

// Settings from the person's inputs file, then from what they last picked in the app.
export function settingsFrom(config, saved) {
  const players = config.players ?? {};
  const computer = players.white === "computer" ? "w" : players.black === "computer" ? "b" : null;
  const base = {
    title: config.title || "Glass Chess",
    opponent: computer ? "computer" : "friend",
    human: computer === "w" ? "b" : "w",
    names: {
      w: players.white && players.white !== "computer" ? players.white : "White",
      b: players.black && players.black !== "computer" ? players.black : "Black",
    },
    strength: Math.min(4, Math.max(1, Number(config.strength) || 2)),
    clock: config.clock in CLOCK_NAMES ? config.clock : "none",
    theme: THEMES.includes(config.theme) ? config.theme : "glass-noir",
    sound: config.sound !== false,
    turnBoard: true,
  };
  return { ...base, ...(saved ?? {}), names: { ...base.names, ...(saved?.names ?? {}) }, title: base.title };
}

export class Game {
  constructor(settings, saved) {
    this.settings = settings;
    this.chess = new Chess();
    for (const san of saved?.moves ?? []) {
      try { this.chess.move(san); } catch { break; }
    }
    this.result = saved?.result ?? null;
    this.clock = new Clock(settings.clock, saved?.clock);
  }

  get turn() { return this.chess.turn(); }
  get history() { return this.chess.history({ verbose: true }); }
  get over() { return Boolean(this.result); }

  isComputer(side) { return this.settings.opponent === "computer" && side !== this.settings.human; }

  nameOf(side) {
    if (this.isComputer(side)) return `Computer, level ${this.settings.strength}`;
    if (this.settings.opponent === "computer") return "You";
    return this.settings.names[side];
  }

  legalFrom(square) {
    return this.chess.moves({ square, verbose: true });
  }

  // Plays a SAN string or {from, to, promotion}; returns the verbose move, or null when it is not legal here.
  move(input, now = performance.now()) {
    if (this.over) return null;
    let mv;
    try { mv = this.chess.move(input); } catch { return null; }
    if (this.history.length === 1) this.clock.start(this.turn, now);
    else this.clock.press(mv.color, now);
    this.settle(now);
    return mv;
  }

  // Ends the game when the position itself ends it.
  settle(now) {
    const c = this.chess;
    if (c.isCheckmate()) this.finish(c.turn() === "w" ? "b" : "w", "checkmate", now);
    else if (c.isStalemate()) this.finish(null, "stalemate", now);
    else if (c.isInsufficientMaterial()) this.finish(null, "insufficient", now);
    else if (c.isThreefoldRepetition()) this.finish(null, "repetition", now);
    else if (c.isDraw()) this.finish(null, "fifty", now);
  }

  finish(winner, reason, now = performance.now()) {
    this.clock.stop(now);
    this.result = { winner, reason };
  }

  resign(side) { this.finish(side === "w" ? "b" : "w", "resigned"); }

  // Takes back the last move, or the last two against the computer so it is the person's turn again.
  undo() {
    const plies = this.settings.opponent === "computer" && this.history.length >= 2 && this.turn === this.settings.human ? 2 : 1;
    let undone = 0;
    for (let i = 0; i < plies; i++) if (this.chess.undo()) undone++;
    if (undone) this.result = null;
    return undone;
  }

  checkSquare() {
    if (!this.chess.inCheck()) return null;
    const side = this.turn;
    for (const row of this.chess.board()) for (const cell of row) if (cell && cell.type === "k" && cell.color === side) return cell.square;
    return null;
  }

  // One plain sentence for the status line.
  status() {
    const r = this.result;
    const name = (s) => (this.settings.opponent === "computer" ? (this.isComputer(s) ? "The computer" : "You") : this.settings.names[s]);
    if (r) {
      if (r.reason === "checkmate") return { title: "Checkmate", line: this.settings.opponent === "computer" ? (this.isComputer(r.winner) ? "The computer wins." : "You win.") : `${name(r.winner)} wins.` };
      if (r.reason === "resigned") return { title: "Resigned", line: `${name(r.winner)} ${this.settings.opponent === "computer" && !this.isComputer(r.winner) ? "win" : "wins"}.` };
      if (r.reason === "time") return { title: "Out of time", line: `${name(r.winner)} ${this.settings.opponent === "computer" && !this.isComputer(r.winner) ? "win" : "wins"} on the clock.` };
      const draws = { stalemate: "Stalemate", insufficient: "Too few pieces to mate", repetition: "Same position three times", fifty: "Fifty moves without a capture" };
      return { title: "Draw", line: `${draws[r.reason]}.` };
    }
    const mover = this.turn;
    const check = this.chess.inCheck();
    let line;
    if (this.settings.opponent === "computer") line = this.isComputer(mover) ? "The computer is thinking." : "Your move.";
    else line = `${this.settings.names[mover]} to move.`;
    return { title: check ? "Check" : mover === "w" ? "White to move" : "Black to move", line };
  }

  save(now = performance.now()) {
    return { moves: this.chess.history(), result: this.result, clock: this.clock.save(now) };
  }
}
