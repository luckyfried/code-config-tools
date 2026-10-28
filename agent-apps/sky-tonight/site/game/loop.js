// The frame loop: a fixed 60 Hz update with an accumulator for anything that steps (easing, inertia), a render on
// every animation frame, and a pause while the page is hidden.

export function createLoop({ update, render, onFrameTime }) {
  const STEP = 1 / 60;
  let acc = 0;
  let last = 0;
  let running = false;
  let id = 0;

  function frame(now) {
    id = requestAnimationFrame(frame);
    const dt = last ? Math.min((now - last) / 1000, 0.1) : STEP;
    if (last && onFrameTime) onFrameTime(now - last);
    last = now;
    acc += dt;
    let steps = 0;
    while (acc >= STEP && steps < 6) {
      update(STEP);
      acc -= STEP;
      steps += 1;
    }
    if (steps === 6) acc = 0;
    render(dt, now / 1000);
  }

  function start() {
    if (running) return;
    running = true;
    last = 0;
    id = requestAnimationFrame(frame);
  }

  function stop() {
    running = false;
    cancelAnimationFrame(id);
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });

  return { start, stop };
}
