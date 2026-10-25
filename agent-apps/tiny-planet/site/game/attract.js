// The title screen's autopilot and film. The explorer runs from crystal to crystal on its own from the first frame,
// hopping now and then, so the planet turns under the orbit shot at once. Half a second in, the camera starts down:
// a slow drift toward the planet that keeps it whole in its frame, then the dive over the explorer's shoulder so the
// curved horizon rises into view, a run with it, and the climb back out to orbit.
import * as THREE from "three";

// Seconds: the first orbit hold, then a repeating cycle of drift, dive, walk, climb, and orbit.
const FIRST_ORBIT = 0.5;
const DRIFT = 2.0;
const DIVE = 2.6;
const WALK = 7.5;
const CLIMB = 2.6;
const ORBIT = 6;
const CYCLE = DRIFT + DIVE + WALK + CLIMB + ORBIT;
// How far down the drift takes the camera, on the dive's 0 to 1 scale: the planet grows by about a fifth.
const DRIFT_DEPTH = 0.15;

const ease = (x) => THREE.MathUtils.smootherstep(x, 0, 1);

// The film's dive, eased: 0 is the orbit shot, 1 is over the explorer's shoulder.
export function filmDive(time) {
  if (time < FIRST_ORBIT) return 0;
  let c = (time - FIRST_ORBIT) % CYCLE;
  if (c < DRIFT) return DRIFT_DEPTH * (c / DRIFT);
  c -= DRIFT;
  if (c < DIVE) return DRIFT_DEPTH + (1 - DRIFT_DEPTH) * ease(c / DIVE);
  c -= DIVE;
  if (c < WALK) return 1;
  c -= WALK;
  if (c < CLIMB) return 1 - ease(c / CLIMB);
  return 0;
}

export function createAttract(targets) {
  let index = 0;
  let hop = 2.6;
  const flat = new THREE.Vector3();
  const side = new THREE.Vector3();

  return {
    read(dt, state) {
      const target = targets[index % targets.length];
      flat.copy(target).addScaledVector(state.up, -target.dot(state.up));
      if (target.dot(state.up) > 0.9985 || flat.lengthSq() < 1e-6) {
        index++;
        return { x: 0, y: 0.4, run: false, jump: false, yaw: 0, pitch: 0, dragging: false };
      }
      flat.normalize();
      side.crossVectors(state.forward, state.up);
      const x = THREE.MathUtils.clamp(flat.dot(side) * 1.6, -0.8, 0.8);
      const y = THREE.MathUtils.clamp(flat.dot(state.forward) + 0.6, 0.35, 1);
      hop -= dt;
      const jump = hop < 0;
      if (jump) hop = 3 + Math.random() * 2.5;
      return { x, y, run: true, jump, yaw: 0, pitch: 0, dragging: false };
    },
  };
}
