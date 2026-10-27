// Pointer and keyboard on one path. A mouse previews on hover and places on click; a touch previews while held and
// places on a quick tap; arrow keys move a cursor, Space or Enter places, U undoes, H hints.
const HOLD_MS = 320;

export function bindInput({ stage, pick, intents }) {
  let down = null;

  stage.addEventListener("pointermove", (event) => {
    const square = pick(event.clientX, event.clientY);
    if (event.pointerType === "mouse" || down) intents.hover(square);
    if (down && square !== down.square) down.moved = true;
  });

  stage.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    intents.wakeAudio();
    const square = pick(event.clientX, event.clientY);
    down = { id: event.pointerId, square, at: performance.now(), type: event.pointerType, moved: false };
    intents.hover(square);
    try {
      stage.setPointerCapture(event.pointerId);
    } catch (error) {
      // Capture is a nicety; the tap still lands without it.
    }
  });

  stage.addEventListener("pointerup", (event) => {
    if (!down || down.id !== event.pointerId) return;
    const square = pick(event.clientX, event.clientY);
    const held = performance.now() - down.at;
    const isTouch = down.type !== "mouse";
    // A long touch is a look at the preview; letting go does not commit it.
    if (square >= 0 && square === down.square && !(isTouch && held > HOLD_MS)) intents.place(square);
    if (isTouch) intents.hover(-1);
    down = null;
  });

  stage.addEventListener("pointercancel", () => {
    down = null;
    intents.hover(-1);
  });

  stage.addEventListener("pointerleave", (event) => {
    if (event.pointerType === "mouse") intents.hover(-1);
  });

  window.addEventListener("keydown", (event) => {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
    const target = event.target;
    if (target && target.closest && target.closest("input, select, textarea, dialog, .setup")) return;
    const moves = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    if (moves[event.key]) {
      event.preventDefault();
      intents.wakeAudio();
      intents.cursor(...moves[event.key]);
    } else if (event.key === " " || event.key === "Enter") {
      if (target && target.closest && target.closest("button, a")) return;
      event.preventDefault();
      intents.wakeAudio();
      intents.cursorPlace();
    } else if (event.key === "u" || event.key === "U") {
      intents.undo();
    } else if (event.key === "h" || event.key === "H") {
      intents.hint();
    }
  });
}
