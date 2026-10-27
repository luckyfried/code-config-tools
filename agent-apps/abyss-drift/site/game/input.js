// Input as intents. One pointer path serves touch and mouse: a touch drag on the water steers (a stick appears where
// it began), a mouse drag looks around. Keys: WASD or arrows steer, Space descends, Shift or E rises, Enter is the
// shutter, P or Escape pauses. Buttons: hold to descend, tap or hold the shutter, tap Surface twice.

export function createInput({ canvas, els, on }) {
  const intent = { thrust: 0, turn: 0, descend: 0, rise: 0, lookYaw: 0, lookPitch: 0 };
  const keys = new Set();
  const stick = { id: null, x0: 0, y0: 0, dx: 0, dy: 0 };
  const look = { id: null, x: 0, y: 0 };
  let descendHeld = false;
  let shutterHeld = false;

  const isTyping = (e) => e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;

  addEventListener("keydown", (e) => {
    if (isTyping(e) || e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.code;
    if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(k) && on.inDive()) e.preventDefault();
    if (k === "Enter" && on.inDive() && document.activeElement === document.body) e.preventDefault();
    if (e.repeat) return;
    keys.add(k);
    if (k === "Enter" && on.inDive() && document.activeElement === document.body) on.shutterDown("key");
    if ((k === "KeyP" || k === "Escape") && on.inDive()) on.pause();
  });
  addEventListener("keyup", (e) => {
    keys.delete(e.code);
    if (e.code === "Enter" && on.inDive()) on.shutterUp("key");
  });
  addEventListener("blur", () => {
    keys.clear();
    releaseAll();
  });

  // Steering and looking on the water.
  canvas.addEventListener("pointerdown", (e) => {
    on.unlock();
    if (!on.inDive()) return;
    if (e.pointerType === "mouse") {
      if (look.id !== null) return;
      look.id = e.pointerId;
      look.x = e.clientX;
      look.y = e.clientY;
    } else {
      if (stick.id !== null) return;
      stick.id = e.pointerId;
      stick.x0 = e.clientX;
      stick.y0 = e.clientY;
      stick.dx = stick.dy = 0;
      els.stick.style.setProperty("--sx", `${e.clientX}px`);
      els.stick.style.setProperty("--sy", `${e.clientY}px`);
      els.stickKnob.style.setProperty("--kx", "0px");
      els.stickKnob.style.setProperty("--ky", "0px");
      els.stick.classList.add("on");
    }
    capture(canvas, e.pointerId);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (e.pointerId === stick.id) {
      const max = 56;
      let dx = e.clientX - stick.x0, dy = e.clientY - stick.y0;
      const len = Math.hypot(dx, dy);
      if (len > max) {
        dx = (dx / len) * max;
        dy = (dy / len) * max;
      }
      stick.dx = dx / max;
      stick.dy = dy / max;
      els.stickKnob.style.setProperty("--kx", `${dx}px`);
      els.stickKnob.style.setProperty("--ky", `${dy}px`);
    } else if (e.pointerId === look.id) {
      intent.lookYaw = clamp(intent.lookYaw - (e.clientX - look.x) * 0.004, -1.2, 1.2);
      intent.lookPitch = clamp(intent.lookPitch - (e.clientY - look.y) * 0.003, -0.5, 0.6);
      look.x = e.clientX;
      look.y = e.clientY;
    }
  });
  const endPointer = (e) => {
    if (e.pointerId === stick.id) {
      stick.id = null;
      stick.dx = stick.dy = 0;
      els.stick.classList.remove("on");
    }
    if (e.pointerId === look.id) look.id = null;
  };
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) canvas.addEventListener(type, endPointer);

  // Hold to descend.
  const descendOn = (e) => {
    e.preventDefault();
    on.unlock();
    descendHeld = true;
    els.descend.classList.add("held");
    capture(els.descend, e.pointerId);
  };
  const descendOff = () => {
    descendHeld = false;
    els.descend.classList.remove("held");
  };
  els.descend.addEventListener("pointerdown", descendOn);
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) els.descend.addEventListener(type, descendOff);
  els.descend.addEventListener("contextmenu", (e) => e.preventDefault());

  // Shutter: a tap shoots after the viewfinder settles; a long press holds the viewfinder until release.
  els.shutter.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    on.unlock();
    shutterHeld = true;
    els.shutter.classList.add("held");
    capture(els.shutter, e.pointerId);
    on.shutterDown("pointer");
  });
  const shutterOff = () => {
    if (!shutterHeld) return;
    shutterHeld = false;
    els.shutter.classList.remove("held");
    on.shutterUp("pointer");
  };
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) els.shutter.addEventListener(type, shutterOff);
  els.shutter.addEventListener("contextmenu", (e) => e.preventDefault());
  els.shutter.addEventListener("keydown", (e) => {
    if ((e.code === "Enter" || e.code === "Space") && !e.repeat) {
      e.preventDefault();
      e.stopPropagation();
      on.shutterDown("button-key");
      on.shutterUp("button-key");
    }
  });

  function releaseAll() {
    descendOff();
    shutterOff();
    stick.id = null;
    stick.dx = stick.dy = 0;
    els.stick.classList.remove("on");
    look.id = null;
  }

  return {
    intent,
    releaseAll,
    /** Folds keys, stick, and buttons into this step's intent. */
    poll(dt) {
      const k = (...codes) => codes.some((c) => keys.has(c));
      let thrust = (k("KeyW", "ArrowUp") ? 1 : 0) - (k("KeyS", "ArrowDown") ? 1 : 0);
      let turn = (k("KeyD", "ArrowRight") ? 1 : 0) - (k("KeyA", "ArrowLeft") ? 1 : 0);
      if (stick.id !== null) {
        thrust = clamp(thrust - stick.dy, -1, 1);
        turn = clamp(turn + stick.dx, -1, 1);
      }
      intent.thrust = thrust;
      intent.turn = turn;
      intent.descend = k("Space") || descendHeld ? 1 : 0;
      intent.rise = k("ShiftLeft", "ShiftRight", "KeyE") ? 1 : 0;
      if (look.id === null) {
        const back = 1 - Math.exp(-dt * 2.5);
        intent.lookYaw -= intent.lookYaw * back;
        intent.lookPitch -= intent.lookPitch * back;
      }
      return intent;
    },
  };
}

// Capture keeps a held control held when the finger slides off it; a pointer the browser no longer tracks is skipped.
function capture(el, id) {
  try {
    el.setPointerCapture(id);
  } catch {
    // Nothing to capture.
  }
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}
