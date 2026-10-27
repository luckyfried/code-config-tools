// The rules of a series: best of three, five, or seven; the wait before DRAW from a seeded random between two and
// six seconds; a false start loses the round; in solo the computer draws at 400 ms, 20 ms quicker each round.
import { mulberry32 } from "./rng.js";

export const WAIT_MIN_MS = 2000;
export const WAIT_MAX_MS = 6000;
export const SOLO_START_MS = 400;
export const SOLO_STEP_MS = 20;
export const SOLO_FLOOR_MS = 120;

export class Series {
  constructor({ mode = "duel", bestOf = 5, names = ["Left", "Right"], seed = Date.now() }) {
    this.mode = mode;
    this.bestOf = [3, 5, 7].includes(bestOf) ? bestOf : 5;
    this.need = Math.ceil(this.bestOf / 2);
    this.names = names.slice(0, 2);
    this.seed = seed >>> 0;
    this.rng = mulberry32(this.seed);
    this.wins = [0, 0];
    this.round = 0;
    this.rounds = [];
    this.best = [null, null];
  }

  next() {
    this.round += 1;
    return {
      round: this.round,
      waitMs: WAIT_MIN_MS + this.rng() * (WAIT_MAX_MS - WAIT_MIN_MS),
      computerMs: this.mode === "solo" ? this.computerMs() : null,
    };
  }

  computerMs(round = this.round) {
    return Math.max(SOLO_FLOOR_MS, SOLO_START_MS - SOLO_STEP_MS * (round - 1));
  }

  /** winner: 0 or 1; times: [ms or null, ms or null]; early: the side that jumped the gun, or null. */
  record({ winner, times, early = null }) {
    this.wins[winner] += 1;
    this.rounds.push({ round: this.round, winner, times: times.slice(), early });
    times.forEach((ms, side) => {
      if (ms !== null && early !== side && (this.best[side] === null || ms < this.best[side])) this.best[side] = ms;
    });
  }

  get over() {
    return this.wins[0] >= this.need || this.wins[1] >= this.need;
  }

  get champion() {
    return this.wins[0] >= this.need ? 0 : this.wins[1] >= this.need ? 1 : null;
  }
}
