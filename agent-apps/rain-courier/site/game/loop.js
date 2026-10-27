// The loop: a fixed 60 Hz update with an accumulator, one render per animation frame, paused while the page is hidden.
const STEP = 1 / 60;

export function createLoop({ update, render, frame }) {
  let last = 0;
  let acc = 0;
  let running = false;
  let hidden = document.hidden;

  function tick(now) {
    if (!running) return;
    requestAnimationFrame(tick);
    const ms = last ? now - last : 16.7;
    last = now;
    if (hidden) return;
    frame?.(ms);
    acc += Math.min(ms / 1000, 0.1);
    let steps = 0;
    while (acc >= STEP && steps < 5) {
      update(STEP);
      acc -= STEP;
      steps++;
    }
    if (steps === 5) acc = 0;
    render(Math.min(ms / 1000, 0.1));
  }

  document.addEventListener("visibilitychange", () => {
    hidden = document.hidden;
    last = 0;
  });

  return {
    start() {
      if (running) return;
      running = true;
      last = 0;
      requestAnimationFrame(tick);
    },
  };
}
