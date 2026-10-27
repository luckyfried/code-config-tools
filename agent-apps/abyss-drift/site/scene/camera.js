// The camera rig. Modes: "attract" circles the opening view; "follow" rides behind the sub; "viewfinder" looks out
// of the sub's camera housing; "ascent" drops below the sub and looks up at the light.
import * as THREE from "three";

const FWD = new THREE.Vector3();
const desired = new THREE.Vector3();
const lookAt = new THREE.Vector3();
const c2 = new THREE.Vector2();

export function createCameraRig(shape) {
  const camera = new THREE.PerspectiveCamera(58, innerWidth / innerHeight, 0.1, 700);
  const look = new THREE.Vector3();
  const state = {
    mode: "attract",
    lookYaw: 0,
    lookPitch: 0,
    fov: 58,
    attract: { center: new THREE.Vector3(), radius: 11, height: 1.5, speed: 0.05, angle: 0, tilt: 0 },
    snap: true,
  };

  function baseFov() {
    const aspect = camera.aspect;
    // Portrait screens get a wider vertical field so the sides of the view are not cut to a sliver.
    return aspect < 0.8 ? 74 : aspect < 1.2 ? 66 : 58;
  }

  return {
    camera,
    state,
    look,
    setMode(mode, snap = false) {
      state.mode = mode;
      if (snap) state.snap = true;
    },
    resize(w, h) {
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    },
    /** Pixels the surface sheet covers on the left and at the bottom; the view centers on what is left. */
    setInset(left, bottom) {
      const w = innerWidth, h = innerHeight;
      if (left <= 0 && bottom <= 0) {
        if (camera.view && camera.view.enabled) camera.clearViewOffset();
        return;
      }
      camera.setViewOffset(w, h, -left / 2, bottom / 2, w, h);
    },
    /**
     * sub: { pos, yaw, pitch }. dt in seconds. reduced: no sway.
     */
    update(dt, t, sub, reduced) {
      const k = state.snap ? 1 : 1 - Math.exp(-dt * 3.2);
      const kLook = state.snap ? 1 : 1 - Math.exp(-dt * 5);
      let fov = baseFov();
      FWD.set(Math.sin(sub.yaw), 0, Math.cos(sub.yaw));
      const sway = reduced ? 0 : 1;
      if (state.mode === "attract") {
        const a = state.attract;
        a.angle += dt * a.speed;
        // Tall screens stand further back so the scene above the sheet holds more than the sub.
        const reach = a.radius * (camera.aspect < 0.8 ? 1.5 : 1);
        desired.set(
          a.center.x + Math.sin(a.angle) * reach,
          a.center.y + a.height + Math.sin(t * 0.21) * 0.8 * sway,
          a.center.z + Math.cos(a.angle) * reach,
        );
        lookAt.copy(a.center);
        lookAt.y += a.tilt;
      } else if (state.mode === "viewfinder") {
        desired.copy(sub.pos).addScaledVector(FWD, 1.8);
        desired.y += 0.75;
        const yaw = sub.yaw + state.lookYaw;
        const pitch = state.lookPitch - sub.pitch * 0.5;
        lookAt.set(Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch)).multiplyScalar(20).add(desired);
        fov = baseFov() - 10;
      } else if (state.mode === "ascent") {
        desired.copy(sub.pos).addScaledVector(FWD, -7.5);
        desired.y -= 3.2;
        lookAt.copy(sub.pos).addScaledVector(FWD, 2);
        lookAt.y += 5;
      } else {
        const yaw = sub.yaw + state.lookYaw;
        desired.set(sub.pos.x - Math.sin(yaw) * 8.6, sub.pos.y + 2.5 - state.lookPitch * 6, sub.pos.z - Math.cos(yaw) * 8.6);
        lookAt.copy(sub.pos).addScaledVector(FWD, 6);
        lookAt.y += 0.6 + state.lookPitch * 8 - sub.pitch * 6;
        desired.y += Math.sin(t * 0.7) * 0.12 * sway;
      }
      // Keep the camera inside the rock.
      const d = Math.max(0, -desired.y);
      shape.center(d, c2);
      const rx = desired.x - c2.x, rz = desired.z - c2.y;
      const rr = Math.hypot(rx, rz), lim = shape.radius(d) - 7;
      if (rr > lim) {
        desired.x = c2.x + (rx / rr) * lim;
        desired.z = c2.y + (rz / rr) * lim;
      }
      desired.y = Math.min(desired.y, -1.2);
      if (state.mode === "viewfinder") {
        camera.position.lerp(desired, state.snap ? 1 : 1 - Math.exp(-dt * 10));
        look.lerp(lookAt, state.snap ? 1 : 1 - Math.exp(-dt * 12));
      } else {
        camera.position.lerp(desired, k);
        look.lerp(lookAt, kLook);
      }
      camera.lookAt(look);
      if (Math.abs(camera.fov - fov) > 0.05) {
        camera.fov += (fov - camera.fov) * (state.snap ? 1 : 1 - Math.exp(-dt * 6));
        camera.updateProjectionMatrix();
      }
      state.snap = false;
    },
  };
}
