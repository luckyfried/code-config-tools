// The camera rig: a fixed tilt over the table, framed so the board, the trays, and the player cards fit the part of
// the screen the page leaves free, and eased between framings when that part changes.
import { PerspectiveCamera, Vector3, MathUtils } from "three";

const FOV = 30;
const corner = new Vector3();

export class CameraRig {
  constructor() {
    this.camera = new PerspectiveCamera(FOV, 1, 1, 400);
    this.from = null;
    this.to = null;
    this.start = 0;
    this.duration = 700;
    this.size = { width: 1, height: 1 };
  }

  /** Where the framing would put the camera: distance and the view shift that centers the content in `rect`. */
  solve({ width, height, rect, box, elevation }) {
    const cam = this.camera;
    cam.aspect = width / height;
    cam.clearViewOffset();
    cam.updateProjectionMatrix();
    const target = new Vector3((box.min.x + box.max.x) / 2, 0, (box.min.z + box.max.z) / 2);
    const dir = new Vector3(0, Math.sin(elevation), Math.cos(elevation));
    const measure = (distance) => {
      cam.position.copy(target).addScaledVector(dir, distance);
      cam.lookAt(target);
      cam.updateMatrixWorld();
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (let i = 0; i < 8; i += 1) {
        corner.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z);
        corner.project(cam);
        x0 = Math.min(x0, corner.x);
        x1 = Math.max(x1, corner.x);
        y0 = Math.min(y0, corner.y);
        y1 = Math.max(y1, corner.y);
      }
      return { x0, x1, y0, y1 };
    };
    const fitsW = (2 * rect.width) / width;
    const fitsH = (2 * rect.height) / height;
    let lo = 4;
    let hi = 400;
    for (let k = 0; k < 28; k += 1) {
      const mid = (lo + hi) / 2;
      const m = measure(mid);
      if (m.x1 - m.x0 <= fitsW && m.y1 - m.y0 <= fitsH) hi = mid;
      else lo = mid;
    }
    const m = measure(hi);
    const px = (((m.x0 + m.x1) / 2 + 1) / 2) * width;
    const py = ((1 - (m.y0 + m.y1) / 2) / 2) * height;
    return {
      distance: hi,
      elevation,
      tx: target.x,
      tz: target.z,
      offX: px - (rect.x + rect.width / 2),
      offY: py - (rect.y + rect.height / 2),
    };
  }

  frame(params, now, immediate) {
    this.size = { width: params.width, height: params.height };
    const next = this.solve(params);
    if (immediate || this.to === null) {
      this.from = next;
      this.to = next;
      this.start = now - this.duration;
    } else {
      this.from = this.current(now);
      this.to = next;
      this.start = now;
    }
    this.apply(now);
  }

  current(now) {
    const p = Math.min(1, Math.max(0, (now - this.start) / this.duration));
    const e = 1 - Math.pow(1 - p, 3);
    const out = {};
    for (const key of Object.keys(this.to)) out[key] = MathUtils.lerp(this.from[key], this.to[key], e);
    return out;
  }

  moving(now) {
    return now < this.start + this.duration;
  }

  apply(now) {
    const c = this.current(now);
    const { width, height } = this.size;
    const cam = this.camera;
    cam.aspect = width / height;
    const target = new Vector3(c.tx, 0, c.tz);
    cam.position.set(c.tx, Math.sin(c.elevation) * c.distance, c.tz + Math.cos(c.elevation) * c.distance);
    cam.lookAt(target);
    cam.setViewOffset(width, height, c.offX, c.offY, width, height);
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
  }
}
