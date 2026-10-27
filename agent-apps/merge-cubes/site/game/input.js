// One path for touch and mouse: a swipe anywhere on the screen that is not on a button. Arrow keys and WASD slide,
// U (or Ctrl Z) undoes, N starts over. Nothing fires while a dialog is open.
const KEYS = {
  ArrowLeft: "left",
  ArrowRight: "right",
  ArrowUp: "up",
  ArrowDown: "down",
  a: "left",
  d: "right",
  w: "up",
  s: "down",
};
const FIRE = 26;
const SETTLE = 14;

export function createInput({ onMove, onUndo, onNew, onAny, blocked }) {
  let start = null;

  function interactive(target) {
    return target instanceof Element && target.closest("button, a, input, label, dialog, .code-config-toast");
  }

  function dirOf(dx, dy) {
    return Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : dy > 0 ? "down" : "up";
  }

  addEventListener("pointerdown", (event) => {
    onAny?.();
    if (blocked() || interactive(event.target) || (event.pointerType === "mouse" && event.button !== 0)) return;
    start = { id: event.pointerId, x: event.clientX, y: event.clientY, fired: false };
  });

  addEventListener("pointermove", (event) => {
    if (!start || start.id !== event.pointerId || start.fired) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.hypot(dx, dy) >= FIRE) {
      start.fired = true;
      onMove(dirOf(dx, dy));
    }
  });

  const end = (event) => {
    if (!start || start.id !== event.pointerId) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (!start.fired && event.type === "pointerup" && Math.hypot(dx, dy) >= SETTLE) onMove(dirOf(dx, dy));
    start = null;
  };
  addEventListener("pointerup", end);
  addEventListener("pointercancel", end);
  addEventListener("blur", () => {
    start = null;
  });

  addEventListener("keydown", (event) => {
    onAny?.();
    if (blocked() || event.altKey || event.metaKey) {
      if (!(event.metaKey && event.key.toLowerCase() === "z")) return;
    }
    const target = event.target;
    if (target instanceof HTMLInputElement) return;
    const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    if ((event.ctrlKey || event.metaKey) && key === "z") {
      event.preventDefault();
      onUndo();
      return;
    }
    if (event.ctrlKey) return;
    if (KEYS[key]) {
      event.preventDefault();
      onMove(KEYS[key]);
    } else if (key === "u" || key === "Backspace") {
      event.preventDefault();
      onUndo();
    } else if (key === "n") {
      event.preventDefault();
      onNew();
    }
  });
}
