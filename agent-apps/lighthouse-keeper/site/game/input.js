// One pointer path for mouse, touch, and pen: a drag swings the beam by how far it moves, a mouse aims it where it
// points, a tap starts the night or, on the lamp, fires the flare. Keys: Left and Right swing, Space fires, Escape
// pauses.
export function createInput(canvas, handlers) {
  const keys = { left: false, right: false };
  let down = null;

  canvas.addEventListener("pointerdown", (e) => {
    if (e.button !== undefined && e.button > 0) return;
    down = { id: e.pointerId, x: e.clientX, y: e.clientY, lastX: e.clientX, t: performance.now(), type: e.pointerType, moved: 0 };
    try {
      canvas.setPointerCapture(e.pointerId);
    } catch {
      // A pointer that cannot be captured still drags while it stays over the canvas.
    }
    handlers.wake();
  });

  canvas.addEventListener("pointermove", (e) => {
    if (e.pointerType === "mouse" && (!down || down.id !== e.pointerId)) {
      handlers.aim(e.clientX, e.clientY);
      return;
    }
    if (!down || down.id !== e.pointerId) return;
    const dx = e.clientX - down.lastX;
    down.lastX = e.clientX;
    down.moved = Math.max(down.moved, Math.hypot(e.clientX - down.x, e.clientY - down.y));
    if (e.pointerType === "mouse") handlers.aim(e.clientX, e.clientY);
    else handlers.drag(dx);
  });

  const end = (e) => {
    if (!down || down.id !== e.pointerId) return;
    const quick = performance.now() - down.t < 380 && down.moved < 12;
    const at = { x: e.clientX, y: e.clientY };
    down = null;
    if (quick && e.type === "pointerup") handlers.tap(at.x, at.y);
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", end);

  addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLButtonElement && (e.key === " " || e.key === "Enter")) return;
    if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") keys.left = true;
    else if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") keys.right = true;
    else if (e.key === " ") {
      e.preventDefault();
      handlers.wake();
      handlers.space();
      return;
    } else if (e.key === "Escape") {
      handlers.escape();
      return;
    } else if (e.key === "Enter") {
      handlers.wake();
      handlers.enter();
      return;
    } else return;
    handlers.wake();
    e.preventDefault();
  });
  addEventListener("keyup", (e) => {
    if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") keys.left = false;
    if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") keys.right = false;
  });
  addEventListener("blur", () => {
    keys.left = false;
    keys.right = false;
  });

  return {
    turn() {
      return (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
    },
  };
}
