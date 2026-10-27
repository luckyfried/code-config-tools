// Rail physics: the marble is `s` along the track and `u` across it (-1 to 1). Forward speed integrates gravity
// along the slope minus rolling friction and air drag; steering moves `u` with inertia; the bank and the dish
// push `u` back while speed through a turn pushes it out; |u| past the edge is a fall.
import {
  DISH,
  GAP_LENGTH,
  GRAVITY,
  HALF_WIDTH,
  MARBLE_RADIUS,
  PAD_HALF,
  PAD_LENGTH,
  frameAt,
  newFrame,
  surfaceHeight,
} from "./generate.js";

export const TUNING = {
  rolling: 0.014,
  drag: 0.0046,
  sideDrag: 0.9,
  centrifugal: 0.62,
  dishPull: 9,
  steerBase: 25,
  steerPerSpeed: 0.46,
  lateralDamping: 2.6,
  airSteer: 0.35,
  launch: 0.1,
  boost: 20,
  boostTime: 0.9,
  topSpeed: 46,
  startSpeed: 8,
  respawnSpeed: 12,
  fallTime: 1,
  edge: 1.06,
};

export const STEP = 1 / 60;

export class Rail {
  constructor(track) {
    this.track = track;
    this.frame = newFrame();
    this.events = [];
    this.reset();
  }

  reset(s = 0) {
    this.s = s;
    this.u = 0;
    this.v = TUNING.startSpeed;
    this.uv = 0;
    this.air = false;
    this.airY = 0;
    this.airVy = 0;
    this.airFails = false;
    this.falling = false;
    this.fallT = 0;
    this.fallPos = [0, 0, 0];
    this.fallVel = [0, 0, 0];
    this.boostT = 0;
    this.usedPads = new Set();
    this.gate = 0;
    this.checkpoint = 0;
    this.time = 0;
    this.finished = false;
    this.coasting = false;
    this.splits = [];
    this.events.length = 0;
  }

  centerY(s, u) {
    const f = frameAt(this.track, s, this.frame);
    const lift = surfaceHeight(u) + MARBLE_RADIUS;
    return f.p[1] + f.r[1] * u * HALF_WIDTH + f.n[1] * lift;
  }

  // One fixed step. `steer` is -1 (left) to 1 (right). `instantRespawn` skips the tumble.
  step(dt, steer, instantRespawn = false) {
    if (this.finished) return;
    if (this.coasting) {
      // Past the finish: the marble rolls out and settles in the runout.
      this.v = Math.max(0, this.v - 9 * dt);
      this.u *= Math.exp(-dt * 2);
      this.uv = 0;
      this.air = false;
      this.s = Math.min(this.track.last - 4, this.s + this.v * dt);
      return;
    }
    this.time += dt;
    if (this.falling) {
      this.fallT += dt;
      this.fallVel[1] -= GRAVITY * dt;
      for (let k = 0; k < 3; k += 1) this.fallPos[k] += this.fallVel[k] * dt;
      if (this.fallT >= TUNING.fallTime || instantRespawn) this.respawn();
      return;
    }
    const track = this.track;
    const f = frameAt(track, this.s, this.frame);

    // Forward: gravity along the tangent, rolling friction, drag, the cost of riding high on the dish, a boost.
    let a = -GRAVITY * f.t[1] - TUNING.rolling * GRAVITY - TUNING.drag * this.v * this.v;
    if (!this.air) a -= TUNING.sideDrag * this.u * this.u * Math.min(1, this.v / 20) * 3;
    if (this.boostT > 0) {
      a += TUNING.boost * Math.min(1, this.boostT / 0.4);
      this.boostT -= dt;
    }
    this.v = Math.max(0, Math.min(TUNING.topSpeed, this.v + a * dt));

    // Across: speed through a turn pushes out, gravity on the bank and the dish pull back, steering and damping.
    const steerAccel = steer * (TUNING.steerBase + TUNING.steerPerSpeed * this.v) * (this.air ? TUNING.airSteer : 1);
    let lat = steerAccel - TUNING.lateralDamping * this.uv;
    if (!this.air) {
      lat += -TUNING.centrifugal * this.v * this.v * f.curvature;
      lat += -GRAVITY * f.r[1];
      lat += -TUNING.dishPull * DISH * this.u * 2;
    }
    this.uv += lat * dt;
    this.u += (this.uv / HALF_WIDTH) * dt;

    const before = this.s;
    this.s += this.v * dt;

    // Gaps: launch off the lip, fly, land past the far side or drop short into the canyon.
    if (!this.air) {
      for (const gap of track.gaps) {
        if (before < gap.s0 && this.s >= gap.s0) {
          this.air = true;
          this.airY = this.centerY(gap.s0, this.u);
          this.airVy = this.v * TUNING.launch + 2;
          this.events.push({ type: "launch", speed: this.v });
        }
      }
    } else {
      this.airVy -= GRAVITY * dt;
      this.airY += this.airVy * dt;
      const gap = track.gaps.find((g) => this.s >= g.s0 - 1 && this.s <= g.s1 + GAP_LENGTH * 3);
      const ground = this.centerY(this.s, this.u);
      const overGap = gap && this.s < gap.s1;
      if (!overGap && this.airY <= ground) {
        this.air = false;
        const impact = Math.max(0, -this.airVy);
        this.v *= 0.97;
        this.events.push({ type: "land", impact });
      } else if (overGap && this.airY < ground - 2.2) {
        this.startFall(f);
        return;
      }
    }

    // Boost pads: once each, when the marble rolls over the strip.
    if (!this.air) {
      for (let i = 0; i < track.boosts.length; i += 1) {
        const pad = track.boosts[i];
        if (this.usedPads.has(i)) continue;
        if (this.s >= pad.s && this.s <= pad.s + PAD_LENGTH && Math.abs(this.u - pad.c) < PAD_HALF + 0.12) {
          this.usedPads.add(i);
          this.boostT = TUNING.boostTime;
          this.events.push({ type: "boost", index: i });
        }
      }
    }

    // Gates and the finish line.
    while (this.gate < track.gates.length && this.s >= track.gates[this.gate].s) {
      this.splits.push(this.time);
      this.checkpoint = track.gates[this.gate].s;
      this.events.push({ type: "gate", index: this.gate, time: this.time });
      this.gate += 1;
    }
    if (this.s >= track.length) {
      // The exact crossing time inside the step.
      const over = (this.s - track.length) / Math.max(1, this.v);
      this.time -= Math.min(dt, over);
      this.finished = true;
      this.events.push({ type: "finish", time: this.time });
      return;
    }

    if (Math.abs(this.u) > TUNING.edge && !this.air) this.startFall(f);
  }

  startFall(f) {
    this.falling = true;
    this.fallT = 0;
    const pos = this.position([0, 0, 0]);
    this.fallPos = pos;
    const side = Math.sign(this.u) || 1;
    for (let k = 0; k < 3; k += 1) {
      this.fallVel[k] = f.t[k] * this.v * 0.8 + f.r[k] * (this.uv * 0.8 + side * 2);
    }
    this.fallVel[1] = this.air ? this.airVy : 2;
    this.air = false;
    this.events.push({ type: "fall" });
  }

  respawn() {
    this.falling = false;
    this.s = this.checkpoint;
    this.u = 0;
    this.uv = 0;
    this.v = TUNING.respawnSpeed;
    this.boostT = 0;
    this.events.push({ type: "respawn" });
  }

  // Height above the surface (0 when rolling), for the ghost and the shadow.
  height() {
    if (!this.air) return 0;
    return this.airY - this.centerY(this.s, this.u);
  }

  // World position of the marble's center.
  position(out) {
    if (this.falling) {
      out[0] = this.fallPos[0];
      out[1] = this.fallPos[1];
      out[2] = this.fallPos[2];
      return out;
    }
    return placeOnTrack(this.track, this.s, this.u, this.air ? this.airY : null, this.frame, out);
  }
}

// World position for a marble at (s, u), optionally at an absolute height while airborne.
export function placeOnTrack(track, s, u, airY, frame, out) {
  const f = frameAt(track, s, frame);
  const lift = surfaceHeight(Math.max(-1.05, Math.min(1.05, u))) + MARBLE_RADIUS;
  for (let k = 0; k < 3; k += 1) out[k] = f.p[k] + f.r[k] * u * HALF_WIDTH + f.n[k] * lift;
  if (airY !== null) out[1] = airY;
  return out;
}
