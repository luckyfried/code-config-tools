// The camera rig. In play it rides behind and above the explorer with the camera's up set to the explorer's local
// up, so the horizon curves away on every side. On the title screen it moves between two shots: the whole planet
// from orbit, fitted into the part of the screen the title card leaves clear, and a low shot over the explorer's
// shoulder with the planet's curved edge across the frame ahead. `dive` runs 0 (orbit) to 1 (over the shoulder);
// `blend` runs 0 (play) to 1 (title). The title's frame (where the clear part of the screen is) comes from setFrame.
import * as THREE from "three";

const PLAY = { dist: 6.6, height: 3.1, look: 1.1, ahead: 1.6, fov: 58 };
// High above and behind the explorer, looking down at the ground just ahead of it: from this height the planet's
// edge arcs across the upper third of the frame with the sky above it, and hills rise over that arc as it walks.
const SHOULDER = { dist: 7, height: 13, look: 0, ahead: 2.3, fov: 60 };
// Orbit: the camera sits above and behind the explorer at `tilt` radians from its local up, looking at the planet's
// center, at the distance that makes a sphere of `bound` (the atmosphere's edge) fill the frame's circle.
const ORBIT = { fov: 36, tilt: 0.6, bound: 25.5 };

const ease = (x) => THREE.MathUtils.smootherstep(x, 0, 1);

export function createCameraRig(camera) {
  const position = new THREE.Vector3();
  const target = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);
  const goal = new THREE.Vector3();
  const lookGoal = new THREE.Vector3();
  const upGoal = new THREE.Vector3();
  const orbitDir = new THREE.Vector3();
  const orbitUp = new THREE.Vector3();
  const shoulder = new THREE.Vector3();
  const shoulderLook = new THREE.Vector3();
  const play = new THREE.Vector3();
  const playLook = new THREE.Vector3();
  const titlePos = new THREE.Vector3();
  const titleLook = new THREE.Vector3();
  const titleUp = new THREE.Vector3();
  const nearDir = new THREE.Vector3();
  const frame = { cx: window.innerWidth / 2, cy: window.innerHeight / 2, radius: Math.min(window.innerWidth, window.innerHeight) * 0.4 };
  let first = true;
  let punch = 0;
  let offsetBlend = -1;

  function frameOffset(blend) {
    const w = window.innerWidth;
    const h = window.innerHeight;
    if (blend < 0.002) {
      if (camera.view && camera.view.enabled) camera.clearViewOffset();
      return;
    }
    camera.setViewOffset(w, h, (w / 2 - frame.cx) * blend, (h / 2 - frame.cy) * blend, w, h);
  }

  function orbitDistance() {
    const half = window.innerHeight / 2;
    const tanA = (frame.radius / half) * Math.tan(THREE.MathUtils.degToRad(ORBIT.fov / 2));
    return ORBIT.bound / Math.sin(Math.atan(tanA));
  }

  return {
    // A short widening of the field of view, for a collect.
    punch(amount) {
      punch = Math.max(punch, amount);
    },
    snap() {
      first = true;
    },
    // The clear part of the screen on the title: its center and the radius of the circle the planet fills, in CSS px.
    setFrame(next) {
      Object.assign(frame, next);
      offsetBlend = -1;
    },
    get frame() {
      return frame;
    },
    // dive: 0 orbit to 1 over the shoulder, already eased (title only); pitch runs 0 (low) to 1 (high), from the drag.
    update(dt, { focus, localUp, forward, blend, pitch, dive }) {
      const t = ease(blend);
      const s = dive;
      const portrait = Math.min(1, camera.aspect);

      // Play pose.
      const pitchHeight = THREE.MathUtils.lerp(0.45, 1.9, pitch);
      const playDist = PLAY.dist * THREE.MathUtils.lerp(1.12, 0.86, pitch);
      play.copy(focus).addScaledVector(forward, -playDist).addScaledVector(localUp, PLAY.height * pitchHeight);
      playLook.copy(focus).addScaledVector(localUp, PLAY.look).addScaledVector(forward, PLAY.ahead);
      const playFov = PLAY.fov + (1 - portrait) * 22;

      // Over-the-shoulder pose.
      shoulder.copy(focus).addScaledVector(forward, -SHOULDER.dist).addScaledVector(localUp, SHOULDER.height);
      shoulderLook.copy(focus).addScaledVector(localUp, SHOULDER.look).addScaledVector(forward, SHOULDER.ahead);
      const shoulderFov = SHOULDER.fov + (1 - portrait) * 14;

      // Orbit pose, then the dive between it and the shoulder: the direction swings, the distance falls
      // geometrically (a steady zoom), and the look point slides from the planet's center to the ground ahead.
      orbitDir.copy(localUp).multiplyScalar(Math.cos(ORBIT.tilt)).addScaledVector(forward, -Math.sin(ORBIT.tilt));
      orbitUp.copy(forward).multiplyScalar(Math.cos(ORBIT.tilt)).addScaledVector(localUp, Math.sin(ORBIT.tilt));
      const far = orbitDistance();
      const near = shoulder.length();
      nearDir.copy(shoulder).normalize();
      titlePos.copy(orbitDir).lerp(nearDir, s).normalize().multiplyScalar(far * Math.pow(near / far, s));
      titleLook.copy(shoulderLook).multiplyScalar(THREE.MathUtils.smoothstep(s, 0.15, 0.95));
      titleUp.copy(orbitUp).lerp(localUp, THREE.MathUtils.smoothstep(s, 0.2, 0.9)).normalize();
      const titleFov = THREE.MathUtils.lerp(ORBIT.fov, shoulderFov, THREE.MathUtils.smoothstep(s, 0.3, 1));

      goal.copy(play).lerp(titlePos, t);
      lookGoal.copy(playLook).lerp(titleLook, t);
      upGoal.copy(localUp).lerp(titleUp, t).normalize();

      if (first) {
        position.copy(goal);
        target.copy(lookGoal);
        up.copy(upGoal);
        first = false;
      } else {
        position.lerp(goal, 1 - Math.exp(-dt * 7));
        target.lerp(lookGoal, 1 - Math.exp(-dt * 12));
        up.lerp(upGoal, 1 - Math.exp(-dt * 6)).normalize();
      }
      camera.position.copy(position);
      camera.up.copy(up);
      camera.lookAt(target);

      punch = Math.max(0, punch - dt * 3.2);
      const fov = THREE.MathUtils.lerp(playFov, titleFov, t) + punch * 7;
      if (Math.abs(camera.fov - fov) > 0.01) {
        camera.fov = fov;
        camera.updateProjectionMatrix();
      }
      if (Math.abs(offsetBlend - t) > 0.001 || (t > 0.002 && !camera.view?.enabled)) {
        offsetBlend = t;
        frameOffset(t);
      }
      camera.updateMatrixWorld();
      // How much of the orbit shot is on screen: 1 at the title's orbit, 0 over the shoulder and in play.
      return t * (1 - s);
    },
    resize() {
      camera.aspect = window.innerWidth / window.innerHeight;
      offsetBlend = -1;
      camera.updateProjectionMatrix();
    },
  };
}
