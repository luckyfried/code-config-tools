// One pointer path for touch, pen, and mouse, plus the keyboard. The first finger (or a held mouse button) moves the
// ship by exactly its own movement, with no smoothing and no snapping to the finger; a second finger held anywhere,
// or Shift, slows time.
export function createInput(surface, handlers) {
  const keys = new Set();
  const pointers = new Map();
  let driver = null;
  let dragX = 0;
  let dragY = 0;
  const drag = [0, 0];
  const axes = [0, 0];

  function release(id) {
    if (!pointers.has(id)) return;
    pointers.delete(id);
    if (driver === id) driver = pointers.size ? pointers.keys().next().value : null;
  }

  surface.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    try {
      surface.setPointerCapture(e.pointerId);
    } catch {
      // A pointer that cannot be captured still moves the ship while it stays over the field.
    }
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (driver === null) driver = e.pointerId;
    handlers.press(e);
  });

  surface.addEventListener("pointermove", (e) => {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    if (e.pointerId === driver) {
      dragX += e.clientX - p.x;
      dragY += e.clientY - p.y;
    }
    p.x = e.clientX;
    p.y = e.clientY;
  });

  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
    surface.addEventListener(type, (e) => release(e.pointerId));
  }

  const MOVE = new Set(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "KeyW", "KeyA", "KeyS", "KeyD", "Space"]);
  addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLButtonElement && (e.code === "Space" || e.code === "Enter")) return;
    if (MOVE.has(e.code)) e.preventDefault();
    keys.add(e.code);
    if (!e.repeat) handlers.key(e);
  });
  addEventListener("keyup", (e) => keys.delete(e.code));
  addEventListener("blur", () => {
    keys.clear();
    pointers.clear();
    driver = null;
  });

  const held = (...codes) => codes.some((c) => keys.has(c));

  return {
    get slow() {
      return pointers.size >= 2 || held("ShiftLeft", "ShiftRight");
    },
    /** The finger's movement since the last step, in world units (screen y runs down, world y runs up). */
    takeDrag(pxPerUnit) {
      drag[0] = dragX / pxPerUnit;
      drag[1] = -dragY / pxPerUnit;
      dragX = 0;
      dragY = 0;
      return drag;
    },
    axes() {
      let x = (held("ArrowRight", "KeyD") ? 1 : 0) - (held("ArrowLeft", "KeyA") ? 1 : 0);
      let y = (held("ArrowUp", "KeyW") ? 1 : 0) - (held("ArrowDown", "KeyS") ? 1 : 0);
      if (x && y) {
        x *= Math.SQRT1_2;
        y *= Math.SQRT1_2;
      }
      axes[0] = x;
      axes[1] = y;
      return axes;
    },
    clearDrag() {
      dragX = 0;
      dragY = 0;
    },
  };
}
