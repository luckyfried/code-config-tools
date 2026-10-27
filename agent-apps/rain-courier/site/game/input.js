// Input as intents: keyboard, a drag on the scene to look, and on phones a left-thumb stick and a right-thumb lift
// slider. Mouse and touch share one pointer-event path.
export function createInput({ canvas, stick, lift, onLook, onAction }) {
  const intents = { forward: 0, turn: 0, lift: 0, yaw: 0 };
  const keys = new Set();
  const touch = { forward: 0, turn: 0, lift: 0 };
  let used = false;

  const KEYMAP = {
    KeyW: ["forward", 1], ArrowUp: ["forward", 1],
    KeyS: ["forward", -1], ArrowDown: ["forward", -1],
    KeyA: ["turn", -1], ArrowLeft: ["turn", -1],
    KeyD: ["turn", 1], ArrowRight: ["turn", 1],
    Space: ["lift", 1], ShiftLeft: ["lift", -1], ShiftRight: ["lift", -1], KeyQ: ["lift", -1], KeyE: ["lift", 1],
  };

  addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLButtonElement && (e.code === "Space" || e.code === "Enter")) return;
    if (KEYMAP[e.code]) {
      keys.add(e.code);
      used = true;
      e.preventDefault();
    }
    if (e.code === "Escape") onAction("escape");
    if (e.code === "KeyR") onAction("route");
    if (e.code === "Enter") onAction("enter");
  });
  addEventListener("keyup", (e) => keys.delete(e.code));
  const clear = () => {
    keys.clear();
    resetStick();
    resetLift();
  };
  addEventListener("blur", clear);
  document.addEventListener("visibilitychange", () => document.hidden && clear());

  // Drag on the scene: across turns the drone, up and down tilts the camera.
  let dragId = null;
  let lastX = 0, lastY = 0;
  canvas.addEventListener("pointerdown", (e) => {
    if (dragId !== null) return;
    dragId = e.pointerId;
    lastX = e.clientX;
    lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
    onAction("drag");
  });
  canvas.addEventListener("pointermove", (e) => {
    if (e.pointerId !== dragId) return;
    const dx = e.clientX - lastX, dy = e.clientY - lastY;
    lastX = e.clientX;
    lastY = e.clientY;
    intents.yaw -= dx * 0.0045;
    onLook(dy * 0.004);
    used = true;
  });
  const endDrag = (e) => {
    if (e.pointerId === dragId) dragId = null;
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  canvas.addEventListener("lostpointercapture", endDrag);

  // Stick: pushed up flies forward, to the side turns.
  let stickId = null;
  let stickRect = null;
  function moveStick(e) {
    const r = stickRect;
    const radius = r.width / 2;
    let x = (e.clientX - (r.left + radius)) / (radius * 0.72);
    let y = (e.clientY - (r.top + radius)) / (radius * 0.72);
    const len = Math.hypot(x, y);
    if (len > 1) {
      x /= len;
      y /= len;
    }
    touch.turn = Math.abs(x) < 0.12 ? 0 : x;
    touch.forward = Math.abs(y) < 0.12 ? 0 : -y;
    stick.style.setProperty("--knob-x", `${(x * radius * 0.72).toFixed(1)}px`);
    stick.style.setProperty("--knob-y", `${(y * radius * 0.72).toFixed(1)}px`);
  }
  function resetStick() {
    stickId = null;
    touch.turn = touch.forward = 0;
    stick.style.setProperty("--knob-x", "0px");
    stick.style.setProperty("--knob-y", "0px");
    stick.classList.remove("is-active");
  }
  stick.addEventListener("pointerdown", (e) => {
    stickId = e.pointerId;
    stickRect = stick.getBoundingClientRect();
    stick.setPointerCapture(e.pointerId);
    stick.classList.add("is-active");
    used = true;
    moveStick(e);
    onAction("drag");
  });
  stick.addEventListener("pointermove", (e) => e.pointerId === stickId && moveStick(e));
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) stick.addEventListener(type, (e) => e.pointerId === stickId && resetStick());

  // Lift slider: springs back to hover when let go.
  let liftId = null;
  let liftRect = null;
  function moveLift(e) {
    const r = liftRect;
    const half = r.height / 2;
    let y = (e.clientY - (r.top + half)) / (half * 0.78);
    y = Math.max(-1, Math.min(1, y));
    touch.lift = Math.abs(y) < 0.1 ? 0 : -y;
    lift.style.setProperty("--knob-y", `${(y * half * 0.78).toFixed(1)}px`);
  }
  function resetLift() {
    liftId = null;
    touch.lift = 0;
    lift.style.setProperty("--knob-y", "0px");
    lift.classList.remove("is-active");
  }
  lift.addEventListener("pointerdown", (e) => {
    liftId = e.pointerId;
    liftRect = lift.getBoundingClientRect();
    lift.setPointerCapture(e.pointerId);
    lift.classList.add("is-active");
    used = true;
    moveLift(e);
    onAction("drag");
  });
  lift.addEventListener("pointermove", (e) => e.pointerId === liftId && moveLift(e));
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) lift.addEventListener(type, (e) => e.pointerId === liftId && resetLift());

  return {
    intents,
    get used() {
      return used;
    },
    // Folds keys and touch into the intents for this step.
    read() {
      let f = 0, t = 0, l = 0;
      for (const code of keys) {
        const [axis, v] = KEYMAP[code];
        if (axis === "forward") f += v;
        else if (axis === "turn") t += v;
        else l += v;
      }
      intents.forward = Math.max(-1, Math.min(1, f + touch.forward));
      intents.turn = Math.max(-1, Math.min(1, t + touch.turn));
      intents.lift = Math.max(-1, Math.min(1, l + touch.lift));
      return intents;
    },
    clear,
  };
}
