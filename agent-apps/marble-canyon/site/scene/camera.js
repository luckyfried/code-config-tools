// The chase camera: a damped spring that lags on acceleration and tightens on braking, FOV that widens with speed
// on an eased curve, a bank of up to eight degrees in turns, a punch on a fall, and a framing offset that moves the
// marble clear of the title card.
import { MathUtils, PerspectiveCamera, Vector3 } from "three";

const BANK_LIMIT = MathUtils.degToRad(8);

export class ChaseCamera {
  constructor(reducedMotion) {
    this.camera = new PerspectiveCamera(62, 1, 0.1, 1500);
    this.reduced = reducedMotion;
    this.pos = new Vector3();
    this.vel = new Vector3();
    this.look = new Vector3();
    this.desired = new Vector3();
    this.lastDesired = new Vector3();
    this.desiredVel = new Vector3();
    this.target = new Vector3();
    this.baseFov = 62;
    this.fov = 62;
    this.bank = 0;
    this.trauma = 0;
    this.time = 0;
    this.lastSpeed = 0;
    this.frameX = 0;
    this.frameY = 0;
    this.wantX = 0;
    this.wantY = 0;
    this.width = 1;
    this.height = 1;
    this.orbit = 0;
    this.hold = false;
  }

  resize(width, height) {
    this.width = width;
    this.height = height;
    this.camera.aspect = width / height;
    this.baseFov = width / height < 0.8 ? 72 : 62;
    this.applyView();
  }

  // Where the subject should sit: x and y as shares of the screen to shift the view by.
  frame(x, y) {
    this.wantX = x;
    this.wantY = y;
  }

  punch(amount) {
    if (this.reduced) return;
    this.trauma = Math.min(1, this.trauma + amount);
  }

  snap(point, frame) {
    this.compute(point, frame, 0);
    this.pos.copy(this.desired);
    this.lastDesired.copy(this.desired);
    this.vel.set(0, 0, 0);
    this.look.copy(this.target);
  }

  compute(point, f, speed) {
    const back = 7 + speed * 0.06;
    const up = 2.5 + speed * 0.015;
    const side = this.orbit;
    this.desired.set(
      point.x - f.t[0] * back + f.n[0] * up + f.r[0] * side,
      point.y - f.t[1] * back + Math.max(f.n[1] * up, up * 0.8) + f.r[1] * side,
      point.z - f.t[2] * back + f.n[2] * up + f.r[2] * side,
    );
    const ahead = 7 + speed * 0.12;
    this.target.set(point.x + f.t[0] * ahead + f.n[0] * 0.7, point.y + f.t[1] * ahead + 0.7, point.z + f.t[2] * ahead + f.n[2] * 0.7);
  }

  update(dt, point, f, speed, topSpeed) {
    this.time += dt;
    const accel = (speed - this.lastSpeed) / Math.max(dt, 1e-3);
    this.lastSpeed = speed;
    if (!this.hold) {
      this.compute(point, f, speed);
      // Softer while speeding up (the camera falls back), stiffer while slowing (it closes in).
      const k = accel > 0.5 ? 26 : accel < -0.5 ? 90 : 48;
      const c = 2 * Math.sqrt(k) * 0.92;
      // The spring chases the target's own velocity too, so it holds its distance at a steady speed.
      this.desiredVel.subVectors(this.desired, this.lastDesired).divideScalar(Math.max(dt, 1e-3));
      if (this.desiredVel.lengthSq() > 10000) this.desiredVel.set(0, 0, 0);
      this.lastDesired.copy(this.desired);
      // Short substeps keep the spring steady through a long frame (a shader compile, a stalled tab).
      const n = Math.ceil(dt / (1 / 120));
      const h = dt / n;
      for (let i = 0; i < n; i += 1) {
        const goal = (n - 1 - i) * h;
        this.vel.x += (k * (this.desired.x - this.desiredVel.x * goal - this.pos.x) + c * (this.desiredVel.x - this.vel.x)) * h;
        this.vel.y += (k * (this.desired.y - this.desiredVel.y * goal - this.pos.y) + c * (this.desiredVel.y - this.vel.y)) * h;
        this.vel.z += (k * (this.desired.z - this.desiredVel.z * goal - this.pos.z) + c * (this.desiredVel.z - this.vel.z)) * h;
        this.pos.addScaledVector(this.vel, h);
      }
      this.look.lerp(this.target, 1 - Math.exp(-dt * 14));
    } else {
      this.look.lerp(point, 1 - Math.exp(-dt * 6));
    }

    const cam = this.camera;
    cam.position.copy(this.pos);
    cam.up.set(0, 1, 0);
    cam.lookAt(this.look);

    const want = MathUtils.clamp(-f.curvature * speed * speed * 0.004, -BANK_LIMIT, BANK_LIMIT);
    this.bank += (want - this.bank) * (1 - Math.exp(-dt * 3));
    cam.rotateZ(this.bank);

    if (this.trauma > 0) {
      this.trauma = Math.max(0, this.trauma - dt * 1.6);
      const shake = this.trauma * this.trauma;
      const n = (seed) => Math.sin(this.time * 47 + seed * 12.9898) * Math.sin(this.time * 31 + seed * 4.1);
      cam.position.x += n(1) * 0.6 * shake;
      cam.position.y += n(2) * 0.6 * shake;
      cam.rotateZ(n(3) * 0.08 * shake);
    }

    const t = MathUtils.clamp(speed / topSpeed, 0, 1);
    const eased = t * t * (3 - 2 * t);
    const fovWant = this.reduced ? this.baseFov : this.baseFov + eased * 16;
    this.fov += (fovWant - this.fov) * (1 - Math.exp(-dt * 4));

    const ease = 1 - Math.exp(-dt * 3);
    this.frameX += (this.wantX - this.frameX) * ease;
    this.frameY += (this.wantY - this.frameY) * ease;
    this.applyView();
  }

  applyView() {
    const cam = this.camera;
    cam.fov = this.fov;
    if (Math.abs(this.frameX) > 1e-4 || Math.abs(this.frameY) > 1e-4) {
      cam.setViewOffset(this.width, this.height, this.frameX * this.width, this.frameY * this.height, this.width, this.height);
    } else if (cam.view) {
      cam.clearViewOffset();
    }
    cam.updateProjectionMatrix();
  }
}
