// The camera rig. It frames the front poster inside the part of the screen the wall owns (left of the Tonight panel
// on a wide screen, above the sheet on a phone), and springs to the new framing when that part changes.
import { PerspectiveCamera } from "three";
import { POSTER_H, POSTER_W, POSTER_BASE, FRONT_Z, spring } from "../game/motion.js";

const FOV = 30;
const TAN = Math.tan((FOV / 2) * (Math.PI / 180));

export class Rig {
  constructor() {
    this.camera = new PerspectiveCamera(FOV, 1, 0.1, 90);
    this.w = 1;
    this.h = 1;
    this.phone = false;
    this.right = { x: 0, v: 0 };
    this.bottom = { x: 0, v: 0 };
    this.floor = { x: 0, v: 0 };
    this.goalFloor = 0;
    this.goalRight = 0;
    this.goalBottom = 0;
    this.dist = 8;
  }

  resize(w, h, phone) {
    this.w = w;
    this.h = h;
    this.phone = phone;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // right: pixels the panel covers on the right; bottom: pixels the sheet or the title card covers at the bottom.
  // floor: pixels the phone's title card covers at the bottom; the front poster always ends above it.
  setCover(right, bottom, instant, floor = 0) {
    this.goalRight = right;
    this.goalBottom = bottom;
    this.goalFloor = floor;
    if (instant) {
      this.right.x = right;
      this.bottom.x = bottom;
      this.floor.x = floor;
      this.right.v = this.bottom.v = this.floor.v = 0;
    }
  }

  update(dt) {
    spring(this.right, this.goalRight, 70, 0.92, dt);
    spring(this.bottom, this.goalBottom, 70, 0.92, dt);
    spring(this.floor, this.goalFloor, 70, 0.92, dt);
    const { w, h, phone } = this;
    const availW = Math.max(200, w - this.right.x);
    const top = phone ? 64 : 72;
    const availH = Math.max(200, h - this.bottom.x - top);
    let posterPx = phone ? 0.42 * h : 0.5 * h;
    posterPx = Math.min(posterPx, (phone ? 0.64 : 0.31) * availW * (POSTER_H / POSTER_W), (phone ? 0.66 : 0.9) * availH);
    const cx = availW / 2;
    let cy = top + availH * (phone ? (this.bottom.x > 1 ? 0.5 : 0.34) : 0.5);
    if (this.floor.x > 0) {
      const limit = h - this.floor.x;
      posterPx = Math.min(posterPx, 0.9 * (limit - top));
      cy = Math.min(cy, limit - posterPx / 2);
    }
    const dist = (POSTER_H * h) / (posterPx * 2 * TAN);
    const ppu = h / (2 * dist * TAN);
    const centerY = POSTER_BASE + POSTER_H / 2;
    const ndcY = 1 - (2 * cy) / h;
    const cam = this.camera;
    cam.position.set((w / 2 - cx) / ppu, centerY - ndcY * dist * TAN, FRONT_Z + dist);
    cam.lookAt(cam.position.x, cam.position.y, FRONT_Z);
    this.dist = dist;
  }
}
