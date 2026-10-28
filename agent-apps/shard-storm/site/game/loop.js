// Fixed 60 Hz updates with an accumulator and a render on every animation frame; a hidden tab stops both and comes
// back without a catch-up burst.
const DT = 1 / 60;

export function startLoop({ step, render, hidden }) {
  let last = performance.now();
  let acc = 0;
  function frame(now) {
    let elapsed = (now - last) / 1000;
    last = now;
    if (elapsed > 0.25) elapsed = 0.25;
    acc += elapsed;
    let steps = 0;
    // A frame that lands a hair early still takes its step, so a 60 Hz screen never doubles or skips a tick.
    while (acc >= DT - 0.002 && steps < 4) {
      step(DT);
      acc -= DT;
      steps++;
    }
    if (steps === 4) acc = 0;
    render(elapsed);
    requestAnimationFrame(frame);
  }
  document.addEventListener("visibilitychange", () => {
    last = performance.now();
    acc = 0;
    if (document.hidden) hidden();
  });
  requestAnimationFrame(frame);
}
