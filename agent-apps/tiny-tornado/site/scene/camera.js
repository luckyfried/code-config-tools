// The camera: a chase from the south that pulls back and rises as the storm grows, with shake that scales with the
// storm's mass and each strike. On the title and the report the view shifts so the storm sits in the part of the
// screen the card leaves clear (to the right of the desktop card, above the phone sheet).
import * as THREE from "three";

export function createCameraRig(camera) {
  const pos = new THREE.Vector3();
  const look = new THREE.Vector3();
  const goal = new THREE.Vector3();
  const lookGoal = new THREE.Vector3();
  const shake = new THREE.Vector3();
  let trauma = 0;
  let first = true;
  let shiftX = 0;
  let shiftY = 0;
  let blend = 0;
  let t = 0;
  let pull = 0;

  function applyOffset() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    if (blend < 0.002 || (shiftX === 0 && shiftY === 0)) {
      if (camera.view && camera.view.enabled) camera.clearViewOffset();
      return;
    }
    camera.setViewOffset(w, h, -shiftX * blend, shiftY * blend, w, h);
  }

  return {
    snap() {
      first = true;
    },
    addTrauma(v) {
      trauma = Math.min(1, trauma + v);
    },
    // Where the clear part of the screen is, as a shift from the center in CSS pixels.
    setShift(x, y) {
      shiftX = x;
      shiftY = y;
    },
    update(dt, { focus, growth, offsetBlend, reduced, shakeBase, velocity }) {
      t += dt;
      const portrait = camera.aspect < 0.9;
      const goalPull = growth;
      pull = reduced ? goalPull : pull + (goalPull - pull) * Math.min(1, dt * 0.8);
      const dist = (portrait ? 36 : 27) + pull * (portrait ? 46 : 36);
      const height = (portrait ? 11 : 8.5) + pull * 15;
      camera.fov = portrait ? 58 : 46;
      goal.set(focus.x - velocity.x * 0.25, height, focus.z + dist - velocity.z * 0.25);
      lookGoal.set(focus.x, 4.5 + pull * 9, focus.z - 6);
      if (first) {
        pos.copy(goal);
        look.copy(lookGoal);
        first = false;
      } else {
        const k = 1 - Math.exp(-dt * 2.2);
        pos.lerp(goal, k);
        look.lerp(lookGoal, 1 - Math.exp(-dt * 3.5));
      }
      trauma = Math.max(0, trauma - dt * 0.9);
      const amount = reduced ? 0 : Math.min(1, trauma * trauma + shakeBase);
      shake.set(
        Math.sin(t * 23.1) * 0.6 + Math.sin(t * 37.7) * 0.4,
        Math.sin(t * 29.3 + 1.2) * 0.6 + Math.sin(t * 41.9) * 0.4,
        Math.sin(t * 19.7 + 2.1) * 0.5,
      ).multiplyScalar(amount * (0.35 + pull * 0.5));
      camera.position.copy(pos).add(shake);
      camera.lookAt(look);
      blend = offsetBlend;
      applyOffset();
      camera.updateProjectionMatrix();
    },
  };
}
