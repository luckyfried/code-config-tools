// One requestAnimationFrame loop for the whole panel; it rests while the page is hidden.
type Tick = (dt: number, t: number) => void

const ticks = new Set<Tick>()
let frame = 0
let last = 0

function run(now: number) {
  const dt = last ? Math.min((now - last) / 1000, 0.1) : 1 / 60
  last = now
  const t = now / 1000
  for (const tick of ticks) tick(dt, t)
  frame = requestAnimationFrame(run)
}

function start() {
  if (!frame && !document.hidden) {
    last = 0
    frame = requestAnimationFrame(run)
  }
}

function stop() {
  cancelAnimationFrame(frame)
  frame = 0
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : ticks.size && start()))
}

export function onFrame(tick: Tick) {
  ticks.add(tick)
  start()
  return () => {
    ticks.delete(tick)
    if (!ticks.size) stop()
  }
}
