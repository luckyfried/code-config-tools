// The frame loop: draws on requestAnimationFrame while anything moves and sleeps when the table is still. Paused while
// the tab is hidden.
export function startLoop({ step, onFrame }) {
  let running = false;
  let handle = 0;
  let last = 0;
  let dirty = true;

  function frame(now) {
    handle = 0;
    const moving = step(now, dirty);
    dirty = false;
    if (last > 0 && moving) onFrame(now - last);
    last = moving ? now : 0;
    if (moving && running) handle = requestAnimationFrame(frame);
  }

  function wake() {
    dirty = true;
    if (running && handle === 0) handle = requestAnimationFrame(frame);
  }

  function setRunning(value) {
    running = value;
    if (running) wake();
    else if (handle) {
      cancelAnimationFrame(handle);
      handle = 0;
      last = 0;
    }
  }

  document.addEventListener("visibilitychange", () => setRunning(!document.hidden));
  setRunning(!document.hidden);
  return { wake };
}
