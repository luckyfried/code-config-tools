// The demo driver behind the title screen: holds a racing line toward the inside of the next turn, lines up
// boost pads, and centers for jumps. `skill` below 1 drives a looser, slower line.
import { DISH, GRAVITY, frameAt, newFrame } from "./generate.js";
import { TUNING } from "./rail.js";

export class Autopilot {
  constructor(track, skill = 1) {
    this.track = track;
    this.skill = skill;
    this.frame = newFrame();
    this.ahead = newFrame();
  }

  steer(rail) {
    const track = this.track;
    const v = rail.v;
    const look = Math.max(10, v * 0.7);
    const ahead = frameAt(track, rail.s + look, this.ahead);
    let target = Math.max(-0.5, Math.min(0.5, ahead.curvature * 34)) * this.skill;
    const gap = track.gaps.find((g) => g.s0 - rail.s > 0 && g.s0 - rail.s < 60);
    if (gap) target = 0;
    for (let i = 0; i < track.boosts.length; i += 1) {
      const pad = track.boosts[i];
      const d = pad.s - rail.s;
      if (this.skill < 1 && i % 2 === 1) continue;
      if (!rail.usedPads.has(i) && d > -4 && d < 70) {
        target = pad.c;
        break;
      }
    }
    const here = frameAt(track, rail.s, this.frame);
    const need = TUNING.centrifugal * v * v * here.curvature + GRAVITY * here.r[1] + TUNING.dishPull * DISH * rail.u * 2;
    const authority = TUNING.steerBase + TUNING.steerPerSpeed * v;
    const feed = rail.air ? 0 : need / authority;
    const correct = (target - rail.u) * 3.4 - rail.uv * 0.22;
    return Math.max(-1, Math.min(1, feed + correct));
  }
}
