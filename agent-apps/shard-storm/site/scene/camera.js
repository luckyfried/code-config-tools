// The camera rig: a narrow perspective lens fitted so the play plane fills the screen, a slow two-degree drift so the
// field is never still, trauma shake, and the dolly toward the ship when it breaks.
import * as THREE from "three";

const FOV = 30;
const DRIFT = THREE.MathUtils.degToRad(2);

export function createCameraRig() {
  const camera = new THREE.PerspectiveCamera(FOV, 1, 1, 1000);
  const target = new THREE.Vector3();
  let dist = 100;
  return {
    camera,
    get distance() {
      return dist;
    },
    fit(H, aspect) {
      camera.aspect = aspect;
      dist = H / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
      camera.far = dist + 600;
      camera.updateProjectionMatrix();
    },
    /** drift 0..1, dolly 0..1 toward (fx, fy), shake as offsets in world units and roll in radians. */
    update(time, drift, dolly, fx, fy, sx, sy, roll) {
      const yaw = Math.sin(time * 0.13) * DRIFT * drift;
      const pitch = Math.sin(time * 0.097 + 1.3) * DRIFT * 0.75 * drift;
      target.set(fx * dolly + sx, fy * dolly + sy, 0);
      const d = dist * (1 - 0.58 * dolly);
      camera.position.set(
        target.x + d * Math.sin(yaw) * Math.cos(pitch),
        target.y + d * Math.sin(pitch),
        d * Math.cos(yaw) * Math.cos(pitch),
      );
      camera.up.set(Math.sin(roll), Math.cos(roll), 0);
      camera.lookAt(target);
    },
  };
}
