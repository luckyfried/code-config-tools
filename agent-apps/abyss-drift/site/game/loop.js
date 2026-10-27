// A fixed 60 Hz update with an accumulator and one render per animation frame, paused while the page is hidden.

export function createLoop({ renderer, update, render, onFrame }) {
  const STEP = 1 / 60;
  let acc = 0;
  let last = 0;
  let time = 0;
  let running = false;

  function frame(now) {
    if (!running) return;
    const ms = last ? now - last : 16.7;
    last = now;
    onFrame?.(ms);
    acc += Math.min(ms / 1000, 0.1);
    let steps = 0;
    while (acc >= STEP && steps < 4) {
      time += STEP;
      update(STEP, time);
      acc -= STEP;
      steps++;
    }
    if (steps === 4) acc = 0;
    render(ms / 1000, time);
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });

  function start() {
    if (running) return;
    running = true;
    last = 0;
    renderer.setAnimationLoop(frame);
  }
  function stop() {
    running = false;
    renderer.setAnimationLoop(null);
  }
  return { start, stop, get time() { return time; } };
}
