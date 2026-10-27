// The sound side of the radio: one <audio> that asks for cross-origin reads (so the analyser can hear it), one that
// does not (for streams that send no CORS headers), the tuning static, and the analysers behind the VU meters.
import { vuPosition } from './signal'

export type Status = 'idle' | 'buffering' | 'playing' | 'failed'

type Listener = (status: Status, analysed: boolean) => void

const ANSWER_MS = 12000
const BINS = 28

function pinkNoise(ctx: AudioContext, seconds: number) {
  const length = Math.floor(ctx.sampleRate * seconds)
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate)
  const data = buffer.getChannelData(0)
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0
  for (let i = 0; i < length; i++) {
    const white = Math.random() * 2 - 1
    b0 = 0.99886 * b0 + white * 0.0555179
    b1 = 0.99332 * b1 + white * 0.0750759
    b2 = 0.969 * b2 + white * 0.153852
    b3 = 0.8665 * b3 + white * 0.3104856
    b4 = 0.55 * b4 + white * 0.5329522
    b5 = -0.7616 * b5 - white * 0.016898
    data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11
    b6 = white * 0.115926
  }
  return buffer
}

export class RadioEngine {
  private cors: HTMLAudioElement
  private plain: HTMLAudioElement
  private ctx: AudioContext | null = null
  private gain: GainNode | null = null
  private left: AnalyserNode | null = null
  private right: AnalyserNode | null = null
  private mix: AnalyserNode | null = null
  private noise: AudioBuffer | null = null
  private staticGain: GainNode | null = null
  private staticSource: AudioBufferSourceNode | null = null
  private token = 0
  private timer = 0
  private volume = 0.8
  private wave = new Float32Array(1024)
  private freq = new Uint8Array(512)
  status: Status = 'idle'
  analysed = false
  private listener: Listener = () => {}

  constructor() {
    this.cors = new Audio()
    this.cors.crossOrigin = 'anonymous'
    this.cors.preload = 'none'
    this.plain = new Audio()
    this.plain.preload = 'none'
  }

  onChange(listener: Listener) {
    this.listener = listener
  }

  private set(status: Status, analysed = this.analysed) {
    this.status = status
    this.analysed = analysed
    this.listener(status, analysed)
  }

  get canMakeSound() {
    return this.ctx !== null
  }

  private ensureContext() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') void this.ctx.resume()
      return this.ctx
    }
    const ctx = new AudioContext()
    const source = ctx.createMediaElementSource(this.cors)
    const gain = ctx.createGain()
    gain.gain.value = this.volume
    const split = ctx.createChannelSplitter(2)
    const left = ctx.createAnalyser()
    const right = ctx.createAnalyser()
    const mix = ctx.createAnalyser()
    left.fftSize = right.fftSize = 2048
    mix.fftSize = 1024
    mix.smoothingTimeConstant = 0.72
    source.connect(gain)
    gain.connect(ctx.destination)
    source.connect(split)
    source.connect(mix)
    split.connect(left, 0)
    split.connect(right, 1)
    const staticGain = ctx.createGain()
    staticGain.gain.value = 0
    staticGain.connect(ctx.destination)
    Object.assign(this, { ctx, gain, left, right, mix, staticGain, noise: pinkNoise(ctx, 2.5) })
    return ctx
  }

  setVolume(v: number) {
    this.volume = v
    this.plain.volume = v
    if (this.gain && this.ctx) this.gain.gain.setTargetAtTime(v, this.ctx.currentTime, 0.03)
  }

  // Static: pink noise through a bandpass that sweeps, the sound of the band between stations.
  private staticBurst(hold: boolean) {
    const ctx = this.ctx
    if (!ctx || !this.noise || !this.staticGain) return
    const now = ctx.currentTime
    this.staticSource?.stop()
    const src = ctx.createBufferSource()
    src.buffer = this.noise
    src.loop = true
    const band = ctx.createBiquadFilter()
    band.type = 'bandpass'
    band.Q.value = 0.8
    band.frequency.setValueAtTime(420, now)
    band.frequency.exponentialRampToValueAtTime(3400, now + 0.45)
    band.frequency.exponentialRampToValueAtTime(1100, now + 0.9)
    src.connect(band)
    band.connect(this.staticGain)
    const g = this.staticGain.gain
    g.cancelScheduledValues(now)
    g.setValueAtTime(g.value, now)
    g.linearRampToValueAtTime(0.3 * this.volume, now + 0.04)
    if (hold) g.setTargetAtTime(0.09 * this.volume, now + 0.5, 0.3)
    else g.setTargetAtTime(0, now + 0.25, 0.12)
    src.start(now)
    this.staticSource = src
  }

  private fadeStatic() {
    const ctx = this.ctx
    if (!ctx || !this.staticGain) return
    const now = ctx.currentTime
    const g = this.staticGain.gain
    g.cancelScheduledValues(now)
    g.setValueAtTime(g.value, now)
    g.setTargetAtTime(0, now, 0.28)
    const src = this.staticSource
    if (src) window.setTimeout(() => src === this.staticSource && src.stop(), 2200)
  }

  // The short burst heard when the dial moves while nothing plays.
  blip(withStatic: boolean) {
    if (withStatic && this.ctx) this.staticBurst(false)
  }

  play(url: string, withStatic: boolean, onFail: () => void) {
    const token = ++this.token
    this.ensureContext()
    this.halt()
    this.set('buffering', false)
    if (withStatic) this.staticBurst(true)
    const fail = () => {
      if (token !== this.token) return
      this.halt()
      this.fadeStatic()
      this.set('failed', false)
      onFail()
    }
    const playing = (analysed: boolean) => {
      if (token !== this.token) return
      window.clearTimeout(this.timer)
      this.fadeStatic()
      this.set('playing', analysed)
    }
    const tryPlain = () => {
      if (token !== this.token) return
      this.cors.removeAttribute('src')
      this.plain.onplaying = () => playing(false)
      this.plain.onerror = fail
      this.plain.src = url
      this.plain.volume = this.volume
      this.plain.play().catch(() => {})
    }
    this.cors.onplaying = () => playing(true)
    this.cors.onerror = tryPlain
    this.cors.src = url
    this.cors.play().catch(() => {})
    window.clearTimeout(this.timer)
    this.timer = window.setTimeout(fail, ANSWER_MS)
  }

  private halt() {
    window.clearTimeout(this.timer)
    for (const el of [this.cors, this.plain]) {
      el.onplaying = null
      el.onerror = null
      el.pause()
      if (el.getAttribute('src')) {
        el.removeAttribute('src')
        el.load()
      }
    }
  }

  stop() {
    this.token++
    this.halt()
    this.fadeStatic()
    this.set('idle', false)
  }

  // Fills levels (left, right, 0..1) and bins (0..1); false when the stream gives the analyser nothing to read.
  read(levels: Float32Array, bins: Float32Array) {
    if (!this.analysed || this.status !== 'playing' || !this.left || !this.right || !this.mix) return false
    let heard = 0
    for (const [i, node] of [this.left, this.right].entries()) {
      node.getFloatTimeDomainData(this.wave)
      let sum = 0
      for (let k = 0; k < this.wave.length; k++) sum += this.wave[k] * this.wave[k]
      const rms = Math.sqrt(sum / this.wave.length)
      levels[i] = vuPosition(20 * Math.log10(rms + 1e-6) + 14)
      heard += rms
    }
    this.mix.getByteFrequencyData(this.freq)
    const n = bins.length
    for (let b = 0; b < n; b++) {
      const lo = Math.floor(Math.pow(b / n, 2) * 180) + 1
      const hi = Math.max(lo + 1, Math.floor(Math.pow((b + 1) / n, 2) * 180) + 1)
      let m = 0
      for (let k = lo; k < hi; k++) m = Math.max(m, this.freq[k])
      bins[b] = m / 255
    }
    return heard > 0.0005
  }
}

export const SPECTRUM_BINS = BINS
