// The camera rig: framing composed for each screen shape (a tall poster on a phone held upright, a wide street on
// a landscape screen), shots that blend into one another, the slow dolly of the wait, the orbit around the
// bullet, and a trauma shake for the punch of a gunshot or a jammed gun.
import * as THREE from "three";

const lerp = (a, b, t) => a + (b - a) * t;
export const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const easeOut = (t) => 1 - Math.pow(1 - t, 3);

// the top edge of the saloon's banner across the street, and how far down the street it hangs
const BANNER_TOP = 8.85;
const BANNER_Z = 8.6;

export function pose(pos, target, fov, shift = 0) {
  return { pos: pos.clone(), target: target.clone(), fov, shift };
}

function copyPose(out, p) {
  out.pos.copy(p.pos);
  out.target.copy(p.target);
  out.fov = p.fov;
  out.shift = p.shift;
  return out;
}

export class CameraRig {
  constructor(camera) {
    this.camera = camera;
    this.now = { pos: new THREE.Vector3(0, 1.4, 9), target: new THREE.Vector3(0, 1.4, -30), fov: 36, shift: 0 };
    this.from = { pos: new THREE.Vector3(), target: new THREE.Vector3(), fov: 36, shift: 0 };
    this.shot = () => this.frame.wide;
    this.blend = 1;
    this.blendDur = 1;
    this.ease = easeInOut;
    this.trauma = 0;
    this.kick = 0;
    this.time = 0;
    this.width = 1;
    this.height = 1;
    this.layout(window.innerWidth, window.innerHeight);
  }

  /** Composes the duel for this screen: how far apart the gunslingers stand and where the camera sits. */
  layout(w, h) {
    this.width = w;
    this.height = h;
    const a = w / h;
    const k = THREE.MathUtils.smoothstep(a, 0.62, 1.45);
    const vfov = lerp(50, 35, k);
    const duelX = lerp(1.6, 2.8, k);
    let margin = lerp(0.62, 1.7, k) + Math.max(0, a - 1.6) * 1.4;
    const hc = lerp(1.45, 1.25, k);
    const feet = lerp(0.6, 0.8, k);
    const t = Math.tan(THREE.MathUtils.degToRad(vfov / 2));
    let dist = (duelX + margin) / (t * a);
    let horizon = feet - (0.5 * hc) / (dist * t);
    // pull back until the banner with the town's name sits wholly inside the frame
    for (let i = 0; i < 40; i += 1) {
      const bannerTop = horizon - (0.5 * (BANNER_TOP - hc)) / ((dist + BANNER_Z) * t);
      if (bannerTop >= 0.035) break;
      margin += 0.2;
      dist = (duelX + margin) / (t * a);
      horizon = feet - (0.5 * hc) / (dist * t);
    }
    const shift = horizon - 0.5;
    const wide = pose(new THREE.Vector3(0, hc, dist), new THREE.Vector3(0, hc, dist - 60), vfov, shift);
    const close = pose(new THREE.Vector3(0, hc - 0.12, dist * 0.68), new THREE.Vector3(0, hc - 0.12, dist * 0.68 - 60), vfov - 3, shift + 0.015);
    this.frame = { wide, close, duelX, dist, vfov, aspect: a, portrait: a < 0.9 };
    this.camera.aspect = a;
    return this.frame;
  }

  /** Blends from wherever the camera is now into a shot over `dur` seconds of real time; 0 cuts. */
  to(shot, dur = 1, ease = easeInOut) {
    copyPose(this.from, this.now);
    this.shot = typeof shot === "function" ? shot : () => shot;
    this.blendDur = Math.max(0.0001, dur);
    this.blendStart = performance.now();
    this.blend = dur <= 0 ? 1 : 0;
    this.ease = ease;
  }

  punch(amount = 0.5, fovKick = 0) {
    this.trauma = Math.min(1, this.trauma + amount);
    this.kick += fovKick;
  }

  update(real) {
    this.time += real;
    const want = this.shot(this.time);
    if (this.blend < 1) {
      // wall-clock progress, so a slow first frame (shaders compiling) never stalls a move
      this.blend = Math.min(1, (performance.now() - this.blendStart) / 1000 / this.blendDur);
      const e = this.ease(this.blend);
      this.now.pos.lerpVectors(this.from.pos, want.pos, e);
      this.now.target.lerpVectors(this.from.target, want.target, e);
      this.now.fov = lerp(this.from.fov, want.fov, e);
      this.now.shift = lerp(this.from.shift, want.shift, e);
    } else {
      copyPose(this.now, want);
    }
    this.trauma = Math.max(0, this.trauma - real * 1.6);
    this.kick *= Math.exp(-real * 7);

    const cam = this.camera;
    const s = this.trauma * this.trauma;
    const tt = this.time * 38;
    cam.position.copy(this.now.pos);
    cam.position.x += s * 0.12 * (Math.sin(tt * 1.1) + Math.sin(tt * 2.3 + 1.3) * 0.5);
    cam.position.y += s * 0.09 * (Math.sin(tt * 1.7 + 0.7) + Math.sin(tt * 2.9) * 0.5);
    cam.lookAt(this.now.target);
    cam.rotation.z += s * 0.03 * Math.sin(tt * 1.3 + 2.1);
    cam.fov = this.now.fov - this.kick;
    const shiftPx = -this.now.shift * this.height;
    cam.setViewOffset(this.width, this.height, 0, shiftPx, this.width, this.height);
    cam.updateProjectionMatrix();
  }
}
