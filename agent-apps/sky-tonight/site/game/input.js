// Looking around: one pointer-event path for mouse and touch (drag to turn, pinch or wheel to zoom, tap to name a
// star), arrow keys and +/- on the keyboard, and the phone's orientation sensor with a drag to line up its heading.
import * as THREE from "three";

const DEG = Math.PI / 180;

export function createInput(canvas, view, hooks) {
  const pointers = new Map();
  let dragging = false;
  let downAt = null;
  let pinchStart = null;
  let lastMove = 0;
  const velocity = { yaw: 0, pitch: 0 };

  const k = () => hooks.scale();

  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    hooks.interact();
    if (pointers.size === 1) {
      downAt = { x: e.clientX, y: e.clientY, t: performance.now() };
      dragging = false;
      velocity.yaw = 0;
      velocity.pitch = 0;
      view.flight = null;
    } else if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinchStart = { d: Math.hypot(a.x - b.x, a.y - b.y), fov: view.fov };
      downAt = null;
    }
  });

  canvas.addEventListener("pointermove", (e) => {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x;
    const dy = e.clientY - p.y;
    p.x = e.clientX;
    p.y = e.clientY;
    if (pointers.size === 2 && pinchStart) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      view.setFov(pinchStart.fov * (pinchStart.d / Math.max(d, 1)));
      return;
    }
    if (downAt && !dragging && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 6) dragging = true;
    if (!dragging) return;
    const kk = k();
    const dyaw = -(dx / kk) / DEG / Math.max(Math.cos(view.pitch * DEG), 0.35);
    const dpitch = (dy / kk) / DEG;
    if (view.sensor) {
      view.headingOffset += dyaw;
    } else {
      view.yaw += dyaw;
      view.pitch += dpitch;
      view.clamp();
    }
    const now = performance.now();
    const dt = Math.max(1, now - lastMove) / 1000;
    lastMove = now;
    velocity.yaw = velocity.yaw * 0.6 + (dyaw / dt) * 0.4;
    velocity.pitch = velocity.pitch * 0.6 + (dpitch / dt) * 0.4;
  });

  const end = (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinchStart = null;
    if (downAt && !dragging && e.type === "pointerup") {
      const held = performance.now() - downAt.t;
      if (held < 600) hooks.tap(e.clientX, e.clientY);
    }
    if (dragging && !view.sensor && !hooks.reducedMotion() && performance.now() - lastMove < 80) {
      view.inertia = { yaw: velocity.yaw, pitch: velocity.pitch };
    }
    if (pointers.size === 0) {
      dragging = false;
      downAt = null;
    }
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    hooks.interact();
    const factor = Math.exp(e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0016));
    view.setFov(view.fov * factor);
  }, { passive: false });

  window.addEventListener("keydown", (e) => {
    if (e.target.closest && e.target.closest("input, textarea, select, dialog, [role=slider]")) return;
    const step = e.shiftKey ? 15 : 5;
    let used = true;
    if (e.key === "ArrowLeft") view.nudge(-step, 0);
    else if (e.key === "ArrowRight") view.nudge(step, 0);
    else if (e.key === "ArrowUp") view.nudge(0, step);
    else if (e.key === "ArrowDown") view.nudge(0, -step);
    else if (e.key === "+" || e.key === "=") view.setFov(view.fov / 1.2, true);
    else if (e.key === "-" || e.key === "_") view.setFov(view.fov * 1.2, true);
    else if (e.key === "Escape") hooks.escape();
    else used = false;
    if (used) {
      hooks.interact();
      e.preventDefault();
    }
  });

  // Orientation sensor: the direction the back of the phone faces, as yaw and pitch with a level horizon.
  const euler = new THREE.Euler();
  const q = new THREE.Quaternion();
  const q1 = new THREE.Quaternion(-Math.sqrt(0.5), 0, 0, Math.sqrt(0.5));
  const q0 = new THREE.Quaternion();
  const zee = new THREE.Vector3(0, 0, 1);
  const fwd = new THREE.Vector3();
  let listening = null;

  function onOrient(e) {
    if (e.beta == null || e.gamma == null) return;
    let alpha = e.alpha || 0;
    if (typeof e.webkitCompassHeading === "number") alpha = 360 - e.webkitCompassHeading;
    const orient = (screen.orientation && screen.orientation.angle) || window.orientation || 0;
    euler.set(e.beta * DEG, alpha * DEG, -e.gamma * DEG, "YXZ");
    q.setFromEuler(euler);
    q.multiply(q1);
    q.multiply(q0.setFromAxisAngle(zee, -orient * DEG));
    fwd.set(0, 0, -1).applyQuaternion(q);
    let yaw = Math.atan2(fwd.x, -fwd.z) / DEG;
    const pitch = Math.asin(Math.max(-1, Math.min(1, fwd.y))) / DEG;
    view.sensorTarget = { yaw: yaw, pitch };
  }

  async function enableSensor() {
    const D = window.DeviceOrientationEvent;
    if (!D) return false;
    if (typeof D.requestPermission === "function") {
      try {
        const res = await D.requestPermission();
        if (res !== "granted") return false;
      } catch {
        return false;
      }
    }
    const type = "ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation";
    window.addEventListener(type, onOrient);
    listening = type;
    return true;
  }

  function disableSensor() {
    if (listening) window.removeEventListener(listening, onOrient);
    listening = null;
    view.sensorTarget = null;
  }

  return { enableSensor, disableSensor, sensorSupported: () => "DeviceOrientationEvent" in window };
}
