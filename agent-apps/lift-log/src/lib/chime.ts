/** The end of a rest: two short tones, a fifth apart. The context is made on a tap, so the browser lets it sound. */
let ctx: AudioContext | null = null

export function primeChime() {
  if (ctx || typeof AudioContext === "undefined") return
  try {
    ctx = new AudioContext()
  } catch {
    ctx = null
  }
}

export function chime() {
  if (!ctx) return
  if (ctx.state === "suspended") void ctx.resume()
  const now = ctx.currentTime + 0.02
  const tone = (freq: number, at: number, length: number) => {
    const osc = ctx!.createOscillator()
    const gain = ctx!.createGain()
    osc.type = "sine"
    osc.frequency.value = freq
    gain.gain.setValueAtTime(0.0001, at)
    gain.gain.exponentialRampToValueAtTime(0.32, at + 0.012)
    gain.gain.exponentialRampToValueAtTime(0.0001, at + length)
    osc.connect(gain).connect(ctx!.destination)
    osc.start(at)
    osc.stop(at + length + 0.05)
  }
  tone(659.25, now, 0.32)
  tone(987.77, now + 0.2, 0.6)
}
