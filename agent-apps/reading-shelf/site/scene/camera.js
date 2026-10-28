// The camera rig. On a wide screen it frames the whole wall and scrolls along it; on a phone it frames one row and
// swipes along that row, stepping between rows. It looks a little behind where it is going, which gives the near
// boards, the motes, and the back panel their parallax, and it leans gently toward the pointer.
import * as THREE from "three";
import { CASE } from "./shelf.js";
import { damp, ease, clamp, reducedMotion } from "./motion.js";

export class CameraRig {
  constructor() {
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.03, 40);
    this.mode = "wall";
    this.geo = null;
    this.x = 0;
    this.xTarget = 0;
    this.y = 0.6;
    this.yTarget = 0.6;
    this.dist = 2.4;
    this.row = 0;
    this.px = 0;
    this.py = 0;
    this.pxs = 0;
    this.pys = 0;
    this.lookLag = 0;
    this.intro = 1;
    this.introStart = -1;
    this.width = 1;
    this.height = 1;
    this.insets = { top: 0, bottom: 0, left: 0, right: 0 };
    this.window = 0;
    this.front = 0;
    this.velocity = 0;
  }

  setGeometry(geo) {
    this.geo = geo;
    this.clampTargets();
  }

  resize(width, height, mode, insets) {
    this.width = width;
    this.height = height;
    this.mode = mode;
    this.insets = { left: 0, right: 0, ...insets };
    this.camera.aspect = width / height;
    this.camera.fov = mode === "row" ? (width < height ? 34 : 30) : 30;
    this.camera.updateProjectionMatrix();
    this.column = mode === "row" && width < height;
    this.frame();
  }

  /** Works out the distance and height that frame the wall or the current row. */
  frame() {
    if (!this.geo) return;
    const tan = Math.tan((this.camera.fov * Math.PI) / 360);
    const usable = 1 - (this.insets.top + this.insets.bottom) / this.height;
    if (this.mode === "row") {
      // A window of whole bays whose screen edges land on the uprights (or on the wall past the case), measured at the
      // front of the case so nothing of the next bay shows. Upright: every row of one bay. On its side: one row.
      const geo = this.geo;
      const front = CASE.depth / 2 + 0.006;
      const across = 1 - (this.insets.left + this.insets.right) / this.width;
      const [lo, hi] = this.box();
      const byHeight = (hi - lo) / Math.max(0.4, usable) / (2 * tan);
      const byWidth = (w) => w / (2 * tan * this.camera.aspect * Math.max(0.5, across));
      const step = CASE.bayW + CASE.divider;
      // Upright, the column is one bay fitted to the room the header and dock leave; the pager reaches the others.
      let pick = this.column && geo.bays > 1 ? { k: 1, d: Math.max(byWidth(step), byHeight) } : null;
      for (let k = 1; !pick && k < geo.bays; k += 1) {
        const d = byWidth(k * step);
        if (d >= byHeight * (this.column ? 0.9 : 0.97)) {
          pick = { k, d };
          break;
        }
        if (this.column) break;
      }
      if (!pick) pick = { k: geo.bays, d: Math.max(byHeight, byWidth(geo.outerW + 0.1)) };
      this.window = pick.k;
      this.front = front;
      this.dist = front + pick.d;
    } else {
      this.window = 0;
      this.front = 0;
      const span = this.geo.height + 0.12;
      const visH = span / Math.max(0.5, usable * 0.98);
      const byHeight = visH / (2 * tan);
      const wantW = Math.min(this.geo.outerW + 0.9, 2.6);
      const byWidth = wantW / (2 * tan * this.camera.aspect);
      this.dist = Math.max(byHeight, Math.min(byWidth, byHeight * 1.12));
    }
    this.yTarget = this.centerY();
    this.clampTargets();
  }

  /** The heights a row view must show: every row of the case upright, the current row on its side. */
  box() {
    const geo = this.geo;
    if (this.column) return [geo.floorY(CASE.rows - 1) - 0.004, geo.floorY(0) + CASE.rowH - 0.004];
    const floor = geo.floorY(this.row);
    return [floor - CASE.board * 1.5 - 0.012, floor + CASE.rowH + 0.012];
  }

  /** The world height at the middle of the screen, shifted so the content sits in the space the HUD leaves. */
  centerY() {
    const tan = Math.tan((this.camera.fov * Math.PI) / 360);
    const visH = 2 * (this.dist - (this.front || 0)) * tan;
    const shift = ((this.insets.top - this.insets.bottom) / 2 / this.height) * visH;
    if (this.mode === "row") {
      const [lo, hi] = this.box();
      return (lo + hi) / 2 + shift;
    }
    return this.geo.height / 2 + shift;
  }

  visibleWidth() {
    const tan = Math.tan((this.camera.fov * Math.PI) / 360);
    return 2 * (this.dist - (this.front || 0)) * tan * this.camera.aspect;
  }

  /** How far the camera sits right of the content's centre, so the content centres in the space the HUD leaves. */
  offsetX() {
    return ((this.insets.right - this.insets.left) / 2 / this.width) * this.visibleWidth();
  }

  /** The centres of the bay windows a row view rests on, left to right. */
  windows() {
    const geo = this.geo;
    const k = this.window || 1;
    if (k >= geo.bays) return [0];
    const span = k * CASE.bayW + (k - 1) * CASE.divider;
    return Array.from({ length: geo.bays - k + 1 }, (_, i) => geo.bayX(i) + span / 2);
  }

  range() {
    if (!this.geo) return [0, 0];
    if (this.mode === "row") {
      const w = this.windows();
      return [w[0], w[w.length - 1]];
    }
    const half = this.visibleWidth() / 2;
    const extent = this.geo.outerW / 2 + 0.3;
    const lo = -extent + half - 0.05;
    const hi = extent - half + 0.05;
    return lo > hi ? [0, 0] : [lo, hi];
  }

  clampTargets() {
    const [lo, hi] = this.range();
    this.xTarget = clamp(this.xTarget, lo, hi);
  }

  canScroll() {
    const [lo, hi] = this.range();
    return hi - lo > 0.01;
  }

  /** In a row view, a swipe settles on the nearest window of whole bays. */
  snapToBay() {
    if (this.mode !== "row" || !this.geo) return;
    this.xTarget = this.nearestWindow(this.xTarget);
  }

  nearestWindow(x) {
    return this.windows().reduce((best, c) => (Math.abs(c - x) < Math.abs(best - x) ? c : best));
  }

  scrollBy(dx) {
    this.xTarget += dx;
    this.clampTargets();
  }

  lookAtX(x, soft = false) {
    if (this.mode === "row" && this.geo) {
      this.xTarget = this.nearestWindow(x);
      return;
    }
    const half = this.visibleWidth() / 2;
    if (soft && Math.abs(x - this.xTarget) < half * 0.6) return;
    this.xTarget = x;
    this.clampTargets();
  }

  setRow(row) {
    const rows = CASE.rows;
    this.row = clamp(row, 0, rows - 1);
    if (this.geo) this.yTarget = this.centerY();
  }

  pointer(nx, ny) {
    this.px = nx;
    this.py = ny;
  }

  startIntro(now) {
    this.introStart = now;
    this.intro = reducedMotion() ? 1 : 0;
  }

  snap() {
    this.x = this.xTarget;
    this.y = this.yTarget;
  }

  update(dt, now) {
    if (this.introStart >= 0 && this.intro < 1) this.intro = clamp((now - this.introStart) / 1.3, 0, 1);
    const k = reducedMotion() ? 1000 : 5.5;
    const prevX = this.x;
    this.x = damp(this.x, this.xTarget, k, dt);
    this.y = damp(this.y, this.yTarget, k * 0.9, dt);
    this.velocity = dt > 0 ? (this.x - prevX) / dt : 0;
    this.lookLag = damp(this.lookLag, clamp(this.velocity * 0.12, -0.12, 0.12), 4, dt);
    this.pxs = damp(this.pxs, reducedMotion() ? 0 : this.px, 3, dt);
    this.pys = damp(this.pys, reducedMotion() ? 0 : this.py, 3, dt);
    const e = ease.outCubic(this.intro);
    const swing = this.mode === "row" ? 0.025 : 0.06;
    const pull = (1 - e) * this.dist * 0.16;
    const rise = (1 - e) * -0.1;
    const ox = this.offsetX();
    this.camera.position.set(this.x + ox + this.pxs * swing, this.y + rise - this.pys * swing * 0.5, this.dist + pull);
    this.camera.lookAt(this.x + ox - this.lookLag + this.pxs * swing * 0.25, this.y + rise * 0.4, -0.35);
    this.camera.updateMatrixWorld();
  }
}
