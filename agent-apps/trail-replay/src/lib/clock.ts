/** The replay's clock: activity seconds advanced on each animation frame, read by the map and the charts without React renders. */
export type ClockListener = (t: number) => void

export class ReplayClock {
  t = 0
  duration = 1
  rate = 60
  playing = false
  loop = true
  /**
   * True on the frames where the page's written numbers change: ten times a second while playing, and on every seek.
   * Every number reads it, so the replay clock and the live numbers turn over on the same frame.
   */
  fresh = true
  private freshAt = Number.NEGATIVE_INFINITY
  private listeners = new Set<ClockListener>()
  private stateListeners = new Set<() => void>()
  private frame = 0
  private last = 0
  private holdUntil = 0

  setDuration(duration: number) {
    this.duration = Math.max(1, duration)
    this.seek(Math.min(this.t, this.duration))
    this.emitState()
  }

  subscribe(fn: ClockListener) {
    this.listeners.add(fn)
    return () => {
      this.listeners.delete(fn)
    }
  }

  onState(fn: () => void) {
    this.stateListeners.add(fn)
    return () => {
      this.stateListeners.delete(fn)
    }
  }

  private emitState() {
    for (const fn of this.stateListeners) fn()
  }

  private emit() {
    for (const fn of this.listeners) fn(this.t)
  }

  play() {
    if (this.playing) return
    if (this.t >= this.duration) this.t = 0
    this.playing = true
    this.last = performance.now()
    this.frame = requestAnimationFrame(this.tick)
    this.emitState()
  }

  pause() {
    if (!this.playing) return
    this.playing = false
    cancelAnimationFrame(this.frame)
    this.emitState()
  }

  toggle() {
    if (this.playing) this.pause()
    else this.play()
  }

  seek(t: number) {
    this.t = Math.min(this.duration, Math.max(0, t))
    this.fresh = true
    this.emit()
  }

  setRate(rate: number) {
    this.rate = rate
    this.emitState()
  }

  private tick = (now: number) => {
    if (!this.playing) return
    const dt = Math.min(0.1, (now - this.last) / 1000)
    this.last = now
    if (now < this.holdUntil) {
      this.frame = requestAnimationFrame(this.tick)
      return
    }
    this.t += dt * this.rate
    this.fresh = now - this.freshAt >= 100
    if (this.fresh) this.freshAt = now
    if (this.t >= this.duration) {
      this.fresh = true
      if (this.loop) {
        this.t = this.duration
        this.emit()
        this.t = 0
        this.holdUntil = now + 1600
        this.frame = requestAnimationFrame(this.tick)
        return
      }
      this.t = this.duration
      this.emit()
      this.pause()
      return
    }
    this.emit()
    this.frame = requestAnimationFrame(this.tick)
  }

  dispose() {
    cancelAnimationFrame(this.frame)
    this.listeners.clear()
    this.stateListeners.clear()
  }
}

/** The replay speeds offered, as multiples of real time. */
export const RATES = [30, 60, 120, 240, 480]

/** The speed that replays the whole activity in about forty seconds. */
export function defaultRate(duration: number) {
  const target = duration / 40
  return RATES.reduce((best, rate) => (Math.abs(rate - target) < Math.abs(best - target) ? rate : best), RATES[0])
}
