// The camera rig: a long lens looking down on the tray at 54 degrees (steeper, 72, in a tall phone slot, so the tray
// stands taller there), framed so the tray fills the board slot the page lays out (a box in the HTML), leaning two
// degrees into each swipe and easing back. The tray stays square to the lens: at load the camera only settles in,
// a short push along its own line of sight.
import * as THREE from "three";

const ELEVATION = THREE.MathUtils.degToRad(54);
const TALL_ELEVATION = THREE.MathUtils.degToRad(72);
const LEAN = THREE.MathUtils.degToRad(2);
const LEAN_PEAK = 0.11; // seconds from the swipe to the deepest lean

export function createCameraRig() {
  const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 200);
  const target = new THREE.Vector3(0, 0, 0);
  const kicks = []; // { az, el, t }
  let distance = 20;
  let push = 0; // 0..1, the slow push-in of the 2048 moment
  let pushTo = 0;
  let intro = 1; // 1 at load, eased to 0
  let reduced = false;
  let time = 0;
  let elevation = ELEVATION;
  const corners = [];
  const tmp = new THREE.Vector3();

  function place(az, el, d) {
    const e = elevation + el;
    camera.position.set(Math.sin(az) * Math.cos(e) * d, Math.sin(e) * d, Math.cos(az) * Math.cos(e) * d).add(target);
    camera.up.set(0, 1, 0);
    camera.lookAt(target);
    camera.updateMatrixWorld();
  }

  /** Projects the box at distance d, with no view offset: its extent and center in pixels. */
  function measure(d, vw, vh) {
    camera.clearViewOffset();
    camera.aspect = vw / vh;
    camera.updateProjectionMatrix();
    place(0, 0, d);
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const c of corners) {
      tmp.copy(c).project(camera);
      minX = Math.min(minX, tmp.x);
      maxX = Math.max(maxX, tmp.x);
      minY = Math.min(minY, tmp.y);
      maxY = Math.max(maxY, tmp.y);
    }
    return {
      w: ((maxX - minX) / 2) * vw,
      h: ((maxY - minY) / 2) * vh,
      cx: (((minX + maxX) / 2 + 1) / 2) * vw,
      cy: ((1 - (minY + maxY) / 2) / 2) * vh,
    };
  }

  let offset = { x: 0, y: 0, vw: 1, vh: 1 };

  return {
    camera,
    target,
    setReduced(value) {
      reduced = value;
    },
    /** Frames the box (min, max corners) into the slot rect, in CSS pixels of a vw by vh viewport. */
    frame(box, slot, vw, vh) {
      corners.length = 0;
      for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) corners.push(new THREE.Vector3(x, y, z));
      target.set(0, (box.min.y + box.max.y) * 0.25, 0);
      const tall = slot.height > slot.width * 1.1;
      elevation = tall ? TALL_ELEVATION : ELEVATION;
      let lo = 3;
      let hi = 200;
      for (let i = 0; i < 40; i += 1) {
        const mid = (lo + hi) / 2;
        const m = measure(mid, vw, vh);
        if (m.w > slot.width || m.h > slot.height) lo = mid;
        else hi = mid;
      }
      distance = hi;
      const m = measure(distance, vw, vh);
      // A slot with room to spare puts the tray in its upper part, so the pedestal below fills the rest; a tall phone
      // slot lifts it right up under the score.
      const spare = slot.height - m.h;
      const lift = tall ? Math.min(spare * 0.04, 10) : Math.min(spare * 0.22, 60);
      const cy = spare > 40 ? slot.top + m.h / 2 + lift : slot.top + slot.height / 2;
      offset = { x: slot.left + slot.width / 2 - m.cx, y: cy - m.cy, vw, vh };
      camera.setViewOffset(vw, vh, -offset.x, -offset.y, vw, vh);
      camera.updateProjectionMatrix();
      return { left: m.cx - m.w / 2 + offset.x, top: m.cy - m.h / 2 + offset.y, width: m.w, height: m.h };
    },
    lean(dir) {
      if (reduced) return;
      const az = dir === "left" ? -LEAN : dir === "right" ? LEAN : 0;
      const el = dir === "up" ? -LEAN : dir === "down" ? LEAN : 0;
      kicks.push({ az, el, t: 0 });
    },
    setPush(value) {
      pushTo = reduced ? 0 : value;
    },
    skipIntro() {
      intro = 0;
    },
    update(dt) {
      time += dt;
      let az = 0;
      let el = 0;
      for (let i = kicks.length - 1; i >= 0; i -= 1) {
        const k = kicks[i];
        k.t += dt;
        const x = k.t / LEAN_PEAK;
        const shape = x * Math.exp(1 - x); // rises to 1 at the peak, then eases home
        az += k.az * shape;
        el += k.el * shape;
        if (x > 8) kicks.splice(i, 1);
      }
      if (intro > 0) intro = reduced ? 0 : Math.max(0, intro - dt / 0.9);
      const e = intro * intro * intro; // the intro's ease-out: fast settle, long tail
      push += (pushTo - push) * Math.min(1, dt * 2.5);
      const drift = reduced ? 0 : Math.sin(time * 0.35) * THREE.MathUtils.degToRad(0.5);
      place(az + drift, el, distance * (1 + e * 0.06 - push * 0.07));
    },
  };
}
