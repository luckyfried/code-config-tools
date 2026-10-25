// Keyboard, mouse, and touch, read into one shape each step: { x, y, run, jump, yaw, pitch, dragging }.
// Touch: a stick appears where the left thumb lands; dragging on the right half looks around; a tap there or the
// round button jumps.
// Mouse: drag anywhere to look around.

const STICK_RADIUS = 46;

export function createInput(canvas, { stick, knob, jumpButton, onPause }) {
  const keys = new Set();
  let jumpQueued = false;
  let yaw = 0;
  let pitch = 0;
  let enabled = false;
  const stickState = { id: null, ox: 0, oy: 0, x: 0, y: 0 };
  const look = { id: null, lx: 0, ly: 0, t: 0, moved: 0, touch: false };

  const coarse = matchMedia("(pointer: coarse)");
  const markTouch = (on) => document.body.classList.toggle("is-touch", on);
  markTouch(coarse.matches);
  coarse.addEventListener("change", (e) => markTouch(e.matches));

  window.addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLButtonElement && (e.code === "Space" || e.code === "Enter")) return;
    if (e.code === "Escape" || e.code === "KeyP") {
      onPause();
      return;
    }
    if (!enabled) return;
    if (e.code === "Space") {
      if (!e.repeat) jumpQueued = true;
      e.preventDefault();
    }
    if (e.code.startsWith("Arrow")) e.preventDefault();
    keys.add(e.code);
  });
  window.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("blur", () => keys.clear());

  function setStick(cx, cy) {
    stick.style.setProperty("--stick-x", `${cx}px`);
    stick.style.setProperty("--stick-y", `${cy}px`);
  }

  canvas.addEventListener("pointerdown", (e) => {
    if (!enabled) return;
    if (e.pointerType === "touch") markTouch(true);
    canvas.setPointerCapture(e.pointerId);
    if (e.pointerType === "touch" && e.clientX < window.innerWidth * 0.5 && stickState.id === null) {
      Object.assign(stickState, { id: e.pointerId, ox: e.clientX, oy: e.clientY, x: 0, y: 0 });
      setStick(e.clientX, e.clientY);
      stick.classList.add("is-active");
      return;
    }
    if (look.id === null) {
      Object.assign(look, { id: e.pointerId, lx: e.clientX, ly: e.clientY, t: performance.now(), moved: 0, touch: e.pointerType === "touch" });
    }
  });

  canvas.addEventListener("pointermove", (e) => {
    if (e.pointerId === stickState.id) {
      let dx = e.clientX - stickState.ox;
      let dy = e.clientY - stickState.oy;
      const l = Math.hypot(dx, dy);
      if (l > STICK_RADIUS) {
        dx *= STICK_RADIUS / l;
        dy *= STICK_RADIUS / l;
      }
      stickState.x = dx / STICK_RADIUS;
      stickState.y = -dy / STICK_RADIUS;
      knob.style.setProperty("--knob-x", `${dx}px`);
      knob.style.setProperty("--knob-y", `${dy}px`);
    } else if (e.pointerId === look.id) {
      const scale = e.pointerType === "touch" ? 0.009 : 0.0055;
      look.moved += Math.abs(e.clientX - look.lx) + Math.abs(e.clientY - look.ly);
      yaw += (e.clientX - look.lx) * scale;
      pitch += (e.clientY - look.ly) * scale * 0.5;
      look.lx = e.clientX;
      look.ly = e.clientY;
    }
  });

  function release(e) {
    if (e.pointerId === stickState.id) {
      Object.assign(stickState, { id: null, x: 0, y: 0 });
      stick.classList.remove("is-active");
      stick.style.removeProperty("--stick-x");
      stick.style.removeProperty("--stick-y");
      knob.style.setProperty("--knob-x", "0px");
      knob.style.setProperty("--knob-y", "0px");
    }
    if (e.pointerId === look.id) {
      // A quick tap on the right half jumps.
      if (enabled && look.touch && e.type === "pointerup" && look.moved < 14 && performance.now() - look.t < 260) jumpQueued = true;
      look.id = null;
    }
  }
  canvas.addEventListener("pointerup", release);
  canvas.addEventListener("pointercancel", release);

  jumpButton.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    if (!enabled) return;
    jumpQueued = true;
    jumpButton.classList.add("is-pressed");
  });
  const unpress = () => jumpButton.classList.remove("is-pressed");
  jumpButton.addEventListener("pointerup", unpress);
  jumpButton.addEventListener("pointercancel", unpress);
  jumpButton.addEventListener("pointerleave", unpress);

  const held = (...codes) => codes.some((c) => keys.has(c));

  return {
    get touch() {
      return document.body.classList.contains("is-touch");
    },
    setEnabled(on) {
      enabled = on;
      if (!on) {
        keys.clear();
        jumpQueued = false;
        release({ pointerId: stickState.id });
        look.id = null;
      }
    },
    read() {
      let x = (held("KeyD", "ArrowRight") ? 1 : 0) - (held("KeyA", "ArrowLeft") ? 1 : 0);
      let y = (held("KeyW", "ArrowUp") ? 1 : 0) - (held("KeyS", "ArrowDown") ? 1 : 0);
      let run = held("ShiftLeft", "ShiftRight");
      if (stickState.id !== null) {
        x = stickState.x;
        y = stickState.y;
        run = Math.hypot(x, y) > 0.92;
      }
      const out = { x, y, run, jump: jumpQueued, yaw, pitch, dragging: look.id !== null };
      jumpQueued = false;
      yaw = 0;
      pitch = 0;
      return out;
    },
  };
}
