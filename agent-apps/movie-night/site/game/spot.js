// The spotlight's timing, shared by the 3D wall and the flat wall: it lifts off one poster, drops onto the next from
// the top down, and strikes with a short flicker when it reaches the floor.
import { easeOutCubic } from "./motion.js";

const DROP = 0.8;

export class Spot {
  constructor() {
    this.index = -1;
    this.pending = -1;
    this.drop = 0;
    this.flick = 1;
    this.phase = "idle";
    this.t = 0;
    this.delay = 0;
  }

  // force re-lands on the poster already lit, as a fresh pick of the same film does.
  land(i, delay = 0, force = false) {
    if (!force && i === this.index && this.phase !== "lifting" && this.phase !== "idle") return;
    this.pending = i;
    this.delay = delay;
    this.phase = this.drop > 0.01 ? "lifting" : "waiting";
  }

  // The list changed under the light: keep it on the same film at its new place.
  move(i) {
    this.index = i;
    if (this.pending >= 0) this.pending = i;
  }

  step(dt) {
    if (this.phase === "lifting") {
      this.drop = Math.max(0, this.drop - dt * 3.4);
      if (this.drop === 0) this.phase = "waiting";
    } else if (this.phase === "waiting") {
      this.delay -= dt;
      if (this.delay <= 0) {
        this.index = this.pending;
        this.phase = "landing";
        this.t = 0;
      }
    } else if (this.phase === "landing") {
      this.t += dt;
      this.drop = easeOutCubic(Math.min(this.t / DROP, 1));
      const s = this.t - DROP;
      this.flick = s > 0 ? 1 - 0.4 * Math.exp(-s * 7) * Math.abs(Math.sin(s * 34)) : 0.85;
      if (s > 0.6) {
        this.flick = 1;
        this.phase = "lit";
      }
    }
  }

  get level() {
    return this.drop * this.flick;
  }

  get landed() {
    return this.phase === "lit";
  }
}
