import { useSyncExternalStore } from "react"
import { createStore, useStore } from "./store"

/**
 * A timer is an end time, not a countdown, so one that runs while the phone is
 * locked is still right when the page comes back, and the chime plays then.
 */
export interface Timer {
  id: string
  recipeId: string
  step: number
  label: string
  durationMs: number
  /** When it ends; null while paused. */
  endsAt: number | null
  /** What was left when it was paused. */
  leftMs: number
  done: boolean
  rung: boolean
}

export const timersStore = createStore<Timer[]>("timers", [])

export function timerId(recipeId: string, step: number, index: number) {
  return `${recipeId}:${step}:${index}`
}

/* The clock: one interval for every pill, running only while a timer runs. */
let now = Date.now()
const clockListeners = new Set<() => void>()
let interval = 0

function tick() {
  now = Date.now()
  const timers = timersStore.get()
  let finished = false
  const next = timers.map((timer) => {
    if (!timer.done && timer.endsAt !== null && timer.endsAt <= now) {
      finished = true
      return { ...timer, done: true, rung: false }
    }
    return timer
  })
  if (finished) timersStore.set(next)
  ringWaiting()
  clockListeners.forEach((listener) => listener())
  syncInterval()
}

function syncInterval() {
  const running = timersStore.get().some((timer) => !timer.done && timer.endsAt !== null)
  if (running && !interval) interval = window.setInterval(tick, 250)
  if (!running && interval) {
    window.clearInterval(interval)
    interval = 0
  }
}

let waitingForTouch = false

function ringWaiting() {
  if (document.visibilityState !== "visible") return
  const waiting = timersStore.get().filter((timer) => timer.done && !timer.rung)
  if (waiting.length === 0) return
  // A page opened fresh may not make sound until it is touched; the chime plays at the first touch.
  if (navigator.userActivation && !navigator.userActivation.hasBeenActive) {
    if (!waitingForTouch) {
      waitingForTouch = true
      window.addEventListener("pointerdown", () => {
        waitingForTouch = false
        tick()
      }, { once: true })
    }
    return
  }
  chime()
  timersStore.set((timers) => timers.map((timer) => (timer.done ? { ...timer, rung: true } : timer)))
}

if (typeof window !== "undefined") {
  document.addEventListener("visibilitychange", tick)
  window.addEventListener("focus", tick)
  queueMicrotask(tick)
}

export function useNow() {
  return useSyncExternalStore(
    (listener) => {
      clockListeners.add(listener)
      return () => clockListeners.delete(listener)
    },
    () => now,
    () => now,
  )
}

export function useTimers() {
  return useStore(timersStore)
}

export function startTimer(input: { id: string; recipeId: string; step: number; label: string; durationMs: number }) {
  primeAudio()
  const timer: Timer = { ...input, endsAt: Date.now() + input.durationMs, leftMs: input.durationMs, done: false, rung: false }
  timersStore.set((timers) => [...timers.filter((entry) => entry.id !== input.id), timer])
  tick()
}

export function toggleTimer(id: string) {
  primeAudio()
  timersStore.set((timers) =>
    timers.map((timer) => {
      if (timer.id !== id || timer.done) return timer
      if (timer.endsAt === null) return { ...timer, endsAt: Date.now() + timer.leftMs }
      return { ...timer, endsAt: null, leftMs: Math.max(0, timer.endsAt - Date.now()) }
    }),
  )
  tick()
}

export function clearTimer(id: string) {
  timersStore.set((timers) => timers.filter((timer) => timer.id !== id))
  tick()
}

export function leftOf(timer: Timer, at: number) {
  if (timer.done) return 0
  return timer.endsAt === null ? timer.leftMs : Math.max(0, timer.endsAt - at)
}

/* The chime: two bell tones, high then low, played twice. */
let audio: AudioContext | null = null

export function primeAudio() {
  try {
    audio ??= new AudioContext()
    if (audio.state === "suspended") void audio.resume()
  } catch {
    audio = null
  }
}

function bell(context: AudioContext, frequency: number, at: number) {
  const gain = context.createGain()
  gain.gain.setValueAtTime(0.0001, at)
  gain.gain.exponentialRampToValueAtTime(0.32, at + 0.012)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + 1.1)
  gain.connect(context.destination)
  for (const [ratio, level] of [[1, 1], [2.76, 0.18]] as const) {
    const partial = context.createOscillator()
    const partialGain = context.createGain()
    partial.type = "sine"
    partial.frequency.value = frequency * ratio
    partialGain.gain.value = level
    partial.connect(partialGain).connect(gain)
    partial.start(at)
    partial.stop(at + 1.15)
  }
}

export function chime() {
  primeAudio()
  if (audio) {
    const start = audio.currentTime + 0.03
    bell(audio, 1046.5, start)
    bell(audio, 784, start + 0.3)
    bell(audio, 1046.5, start + 1.0)
    bell(audio, 784, start + 1.3)
  }
  navigator.vibrate?.([180, 90, 180])
}
