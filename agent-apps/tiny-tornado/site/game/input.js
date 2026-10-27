// Steering. A drag anywhere pushes the storm the way the finger or mouse moves (the push is the drag's distance, so
// the storm carries momentum after the finger lifts); WASD or the arrow keys push it while held. Space, or the pulse
// button on a phone, sends a pulse. Escape pauses.
export function createInput(surface, { onPulse, onPause, active }) {
  const keys = new Set();
  const push = { x: 0, z: 0 };
  let pointer = null;
  let lastX = 0;
  let lastY = 0;

  const KEYMAP = {
    KeyW: [0, -1], ArrowUp: [0, -1], KeyS: [0, 1], ArrowDown: [0, 1],
    KeyA: [-1, 0], ArrowLeft: [-1, 0], KeyD: [1, 0], ArrowRight: [1, 0],
  };

  window.addEventListener("keydown", (e) => {
    if (e.code === "Escape") {
      onPause();
      return;
    }
    if (!active()) return;
    if (KEYMAP[e.code]) {
      keys.add(e.code);
      e.preventDefault();
    }
    if (e.code === "Space") {
      e.preventDefault();
      if (!e.repeat) onPulse();
    }
  });
  window.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("blur", () => keys.clear());

  surface.addEventListener("pointerdown", (e) => {
    if (!active() || e.target.closest("button")) return;
    pointer = e.pointerId;
    lastX = e.clientX;
    lastY = e.clientY;
  });
  window.addEventListener("pointermove", (e) => {
    if (e.pointerId !== pointer) return;
    const scale = 26 / Math.max(320, Math.min(window.innerWidth, window.innerHeight));
    push.x += (e.clientX - lastX) * scale;
    push.z += (e.clientY - lastY) * scale;
    lastX = e.clientX;
    lastY = e.clientY;
  });
  const end = (e) => {
    if (e.pointerId === pointer) pointer = null;
  };
  window.addEventListener("pointerup", end);
  window.addEventListener("pointercancel", end);

  return {
    // The held-key direction, unit length or zero.
    keyDir(out) {
      let x = 0;
      let z = 0;
      for (const k of keys) {
        x += KEYMAP[k][0];
        z += KEYMAP[k][1];
      }
      const l = Math.hypot(x, z);
      out.x = l ? x / l : 0;
      out.z = l ? z / l : 0;
      return out;
    },
    // The drag distance since the last step, in meters of push.
    takePush(out) {
      out.x = push.x;
      out.z = push.z;
      push.x = 0;
      push.z = 0;
      return out;
    },
    get dragging() {
      return pointer !== null;
    },
    clear() {
      keys.clear();
      push.x = 0;
      push.z = 0;
      pointer = null;
    },
  };
}
