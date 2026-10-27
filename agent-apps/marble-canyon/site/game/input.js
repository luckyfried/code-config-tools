// Steering from one pointer path for touch and mouse (drag left or right anywhere, measured from where the drag
// began), the keyboard (Left/Right or A/D, Space, R, Escape), and tilt when the person turns it on.
export function createInput({ onStart, onRestart, onBack }) {
  const keys = { left: false, right: false };
  let drag = null;
  let dragSteer = 0;
  let tiltOn = false;
  let tiltSteer = 0;
  let value = 0;

  const isControl = (target) => target instanceof Element && target.closest("button, a, .card, input, select, textarea");

  const range = () => Math.min(innerWidth, 560) * 0.2;

  window.addEventListener("pointerdown", (event) => {
    if (isControl(event.target)) return;
    if (drag !== null) return;
    drag = { id: event.pointerId, anchor: event.clientX };
    dragSteer = 0;
    if (event.target instanceof Element && event.target.setPointerCapture) {
      try {
        event.target.setPointerCapture(event.pointerId);
      } catch {
        // The pointer ended before capture.
      }
    }
  });

  window.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    const r = range();
    let dx = event.clientX - drag.anchor;
    // Past full lock the anchor follows the finger, so reversing answers at once.
    if (dx > r) {
      drag.anchor = event.clientX - r;
      dx = r;
    } else if (dx < -r) {
      drag.anchor = event.clientX + r;
      dx = -r;
    }
    dragSteer = dx / r;
  });

  const release = (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    drag = null;
    dragSteer = 0;
  };
  window.addEventListener("pointerup", release);
  window.addEventListener("pointercancel", release);

  window.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const k = event.key;
    if (k === "ArrowLeft" || k === "a" || k === "A") {
      keys.left = true;
      event.preventDefault();
    } else if (k === "ArrowRight" || k === "d" || k === "D") {
      keys.right = true;
      event.preventDefault();
    } else if (k === " " || k === "Spacebar") {
      if (isControl(event.target) && event.target.closest("button")) return;
      event.preventDefault();
      if (!event.repeat) onStart();
    } else if (k === "r" || k === "R") {
      if (!event.repeat) onRestart();
    } else if (k === "Escape") {
      onBack();
    }
  });

  window.addEventListener("keyup", (event) => {
    const k = event.key;
    if (k === "ArrowLeft" || k === "a" || k === "A") keys.left = false;
    if (k === "ArrowRight" || k === "d" || k === "D") keys.right = false;
  });

  window.addEventListener("blur", () => {
    keys.left = false;
    keys.right = false;
    drag = null;
    dragSteer = 0;
  });

  const onTilt = (event) => {
    if (event.gamma === null) return;
    const angle = (screen.orientation && screen.orientation.angle) || window.orientation || 0;
    let lean = event.gamma;
    if (angle === 90) lean = event.beta;
    else if (angle === -90 || angle === 270) lean = -event.beta;
    const dead = 3;
    const v = Math.abs(lean) < dead ? 0 : (lean - Math.sign(lean) * dead) / 22;
    tiltSteer = Math.max(-1, Math.min(1, v));
  };

  return {
    // Steering with a little inertia: keys ramp in, a drag follows the finger closely.
    steer(dt) {
      const keyTarget = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
      let target = keyTarget;
      if (drag) target = dragSteer;
      else if (tiltOn && keyTarget === 0) target = tiltSteer;
      const rate = drag ? 16 : keyTarget !== 0 ? 7 : 10;
      value += (target - value) * (1 - Math.exp(-rate * dt));
      return value;
    },
    clear() {
      value = 0;
    },
    get dragging() {
      return drag !== null;
    },
    async enableTilt(on) {
      if (!on) {
        tiltOn = false;
        window.removeEventListener("deviceorientation", onTilt);
        return false;
      }
      const D = window.DeviceOrientationEvent;
      if (!D) return false;
      if (typeof D.requestPermission === "function") {
        try {
          const answer = await D.requestPermission();
          if (answer !== "granted") return false;
        } catch {
          return false;
        }
      }
      window.addEventListener("deviceorientation", onTilt);
      tiltOn = true;
      return true;
    },
    tiltAvailable: typeof window.DeviceOrientationEvent !== "undefined",
  };
}
