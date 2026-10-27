// The keeper the title screen shows: a ship already burning in the beam, a sweep of the beam past the camera, a
// thunderclap, and a flare, then a steady watch that keeps turning ships back until the person takes the lamp.
import { bearingOf, angleDiff } from "./paths.js";

const SWEEP_START = 4.3;
const SWEEP_SLOW = 5.2;
const SWEEP_FAST = 6.6;
const SWEEP_END = 7.6;
const THUNDER_AT = 7.1;
const FLARE_AT = 8.2;

const ease = (t) => t * t * (3 - 2 * t);

export function createAttract() {
  let clock = 0;
  let sweepFrom = 0;
  let cameraBearing = Math.PI;
  let thundered = false;
  let flared = false;
  return {
    begin(state, camBearing) {
      clock = 0;
      thundered = false;
      flared = false;
      cameraBearing = camBearing;
      sweepFrom = state.bearing;
    },
    // Returns the bearing the beam should hold this step and the events due now.
    step(state, dt, events) {
      clock += dt;
      if (clock >= THUNDER_AT && !thundered) {
        thundered = true;
        events.thunder = true;
      }
      if (clock >= FLARE_AT && !flared) {
        flared = true;
        events.flare = true;
      }
      if (clock >= SWEEP_START && clock < SWEEP_END) {
        let cam = cameraBearing;
        while (cam < sweepFrom) cam += Math.PI * 2;
        const a = cam - 0.45;
        const b = cam + 0.45;
        const end = sweepFrom + Math.PI * 2;
        let bearing;
        if (clock < SWEEP_SLOW) bearing = sweepFrom + (a - sweepFrom) * ease((clock - SWEEP_START) / (SWEEP_SLOW - SWEEP_START));
        else if (clock < SWEEP_FAST) bearing = a + (b - a) * ((clock - SWEEP_SLOW) / (SWEEP_FAST - SWEEP_SLOW));
        else bearing = b + (end - b) * ease((clock - SWEEP_FAST) / (SWEEP_END - SWEEP_FAST));
        return { bearing, direct: true };
      }
      return { bearing: watch(state), direct: false };
    },
  };
}

// The steady watch: the nearest ship not yet turned, or the one already in the beam until it is done.
function watch(state) {
  let best = null;
  let bestScore = Infinity;
  for (const s of state.ships) {
    if (!s.active || s.turned || s.wrecked || !s.visible) continue;
    const d = Math.hypot(s.x, s.z);
    const b = bearingOf(s.x, s.z);
    const held = s.fill > 0.05 ? -60 : 0;
    const score = d + held + Math.abs(angleDiff(b, state.bearing)) * 25;
    if (score < bestScore) {
      bestScore = score;
      best = b;
    }
  }
  return best === null ? state.targetBearing : best;
}
