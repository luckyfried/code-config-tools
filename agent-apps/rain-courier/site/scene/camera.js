// The chase camera: on a damped spring behind the drone, leaning into turns and widening with speed, kept out of
// the buildings, and framed around whatever panel sits over the scene.
import * as THREE from "three";

export function createCameraRig(plan) {
  const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 2600);
  const pos = new THREE.Vector3(0, 60, -20);
  const vel = new THREE.Vector3();
  const desired = new THREE.Vector3();
  const look = new THREE.Vector3();
  const lookVel = new THREE.Vector3();
  const lookAt = new THREE.Vector3();
  const tmp = new THREE.Vector3();
  let roll = 0;
  let fov = 62;
  let shake = 0;
  let shakeTime = 0;
  let yawOffset = 0;
  let pitch = 0.24;
  const frame = { x: 0, y: 0, tx: 0, ty: 0 };
  let width = 1, height = 1;

  function insideBox(p) {
    let hit = false;
    plan.grid.query(p.x, p.z, 0.6, (i) => {
      const b = plan.boxes[i];
      if (p.x > b.x - b.w / 2 - 0.4 && p.x < b.x + b.w / 2 + 0.4 && p.z > b.z - b.d / 2 - 0.4 && p.z < b.z + b.d / 2 + 0.4 && p.y > b.y0 - 0.4 && p.y < b.y1 + 0.4) hit = true;
    });
    return hit;
  }

  return {
    camera,
    get pitch() {
      return pitch;
    },
    setSize(w, h) {
      width = w;
      height = h;
      camera.aspect = w / h;
      applyFrame();
    },
    // Moves the projection center so the drone sits in the open part of the screen, in CSS pixels.
    setFraming(x, y) {
      frame.tx = x;
      frame.ty = y;
    },
    addPitch(d) {
      pitch = Math.min(1.1, Math.max(-0.15, pitch + d));
    },
    setYawOffset(v) {
      yawOffset = v;
    },
    kick(amount) {
      shake = Math.min(1, shake + amount);
    },
    snap(flight) {
      this.update(0, flight, { reduced: true, snap: true });
    },
    update(dt, flight, { reduced, snap = false, attract = false }) {
      const speed = Math.hypot(flight.vel.x, flight.vel.z);
      const heading = flight.heading + yawOffset;
      const fx = Math.sin(heading), fz = Math.cos(heading);
      const dist = (attract ? 4.6 : 4.4) + Math.min(speed, 26) * 0.06;
      const p = attract ? 0.16 : pitch;
      desired.set(
        flight.pos.x - fx * dist * Math.cos(p),
        flight.pos.y + 1.4 + dist * Math.sin(p),
        flight.pos.z - fz * dist * Math.cos(p),
      );
      // Pull the camera in along the boom until it is clear of every wall.
      for (let k = 0; k < 6 && insideBox(desired); k++) desired.lerp(flight.pos, 0.3);
      if (desired.y < 0.8) desired.y = 0.8;
      lookAt.set(flight.pos.x + fx * 3.5, flight.pos.y + 0.4, flight.pos.z + fz * 3.5);
      if (snap || dt === 0) {
        pos.copy(desired);
        vel.set(0, 0, 0);
        look.copy(lookAt);
        lookVel.set(0, 0, 0);
      } else {
        const k = 42, c = 2 * Math.sqrt(k);
        tmp.copy(desired).sub(pos).multiplyScalar(k * dt).addScaledVector(vel, -c * dt);
        vel.add(tmp);
        pos.addScaledVector(vel, dt);
        const k2 = 90, c2 = 2 * Math.sqrt(k2);
        tmp.copy(lookAt).sub(look).multiplyScalar(k2 * dt).addScaledVector(lookVel, -c2 * dt);
        lookVel.add(tmp);
        look.addScaledVector(lookVel, dt);
      }
      camera.position.copy(pos);
      if (!reduced && shake > 0) {
        shakeTime += dt * 60;
        const a = shake * shake * 0.35;
        camera.position.x += Math.sin(shakeTime * 1.7) * a;
        camera.position.y += Math.sin(shakeTime * 2.3 + 1) * a;
        camera.position.z += Math.sin(shakeTime * 1.3 + 2) * a;
      }
      shake = Math.max(0, shake - dt * 1.8);
      camera.lookAt(look);
      const targetRoll = reduced ? 0 : -flight.turnRate * 0.07 * Math.min(1, speed / 14);
      roll += (targetRoll - roll) * Math.min(1, dt * 5);
      camera.rotateZ(roll);
      const targetFov = reduced ? 62 : 62 + Math.min(speed, 26) * 0.42;
      fov += (targetFov - fov) * Math.min(1, dt * 3);
      frame.x += (frame.tx - frame.x) * Math.min(1, dt * 4 || 1);
      frame.y += (frame.ty - frame.y) * Math.min(1, dt * 4 || 1);
      if (Math.abs(camera.fov - fov) > 0.01 || snap || dt > 0) {
        camera.fov = fov;
        applyFrame();
      }
    },
  };

  function applyFrame() {
    if (Math.abs(frame.x) < 0.5 && Math.abs(frame.y) < 0.5) {
      camera.clearViewOffset();
    } else {
      camera.setViewOffset(width, height, -frame.x, frame.y, width, height);
    }
    camera.updateProjectionMatrix();
  }
}
