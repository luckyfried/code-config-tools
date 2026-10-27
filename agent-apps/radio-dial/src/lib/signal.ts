// The breathing pulse that drives the meters when a stream cannot be analyzed, or before anything plays: a slow
// swell, a soft beat, and a pink slope across the spectrum, different for each station so no two look alike.

function hash(s: string) {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619)
  return (h >>> 0) / 4294967295
}

// A level in VU decibels to the needle's place on the scale (0 at the -20 stop, 1 at +3), along the printed marks.
const VU_MARKS: [number, number][] = [[-20, 0], [-10, 0.25], [-7, 0.37], [-5, 0.47], [-3, 0.59], [0, 0.8], [3, 1]]
export function vuPosition(db: number) {
  if (db <= -20) return 0
  for (let i = 1; i < VU_MARKS.length; i++) {
    const [d1, f1] = VU_MARKS[i]
    if (db <= d1) {
      const [d0, f0] = VU_MARKS[i - 1]
      return f0 + ((db - d0) / (d1 - d0)) * (f1 - f0)
    }
  }
  return 1
}

// levels[] are needle places on the VU scale; bins[] are spectrum heights, both 0 to 1.
export function synth(t: number, seed: string, strength: number, levels: Float32Array, bins: Float32Array) {
  const k = hash(seed)
  const tempo = 1.6 + k * 0.9
  const beatPhase = (t * tempo) % 1
  const beat = Math.exp(-beatPhase * 5.5)
  const swell = 0.5 + 0.5 * Math.sin(t * 0.9 + k * 6.28)
  const flutter = 0.5 + 0.5 * Math.sin(t * 7.3 + k * 11) * Math.sin(t * 3.1)
  const drift = (0.5 + 0.5 * Math.sin(t * 2.7 + k * 5)) * (0.5 + 0.5 * Math.sin(t * 1.31 + k * 2))
  // Program level in VU dB, riding between -7 and 0 with the beat and touching the red on the loudest beats; the
  // strength is a gain on it, so a quiet dial drops the needles and a silent one rests them.
  const db = -5.5 + 2.5 * swell + 4 * beat + 0.8 * flutter + 1.2 * drift + 20 * Math.log10(Math.max(strength, 1e-4))
  levels[0] = vuPosition(db + 0.9 * Math.sin(t * 5.1 + k * 3))
  levels[1] = vuPosition(db + 0.9 * Math.sin(t * 4.3 + k * 9 + 1.3) - 0.4)
  const n = bins.length
  for (let b = 0; b < n; b++) {
    const x = b / n
    const slope = 1 - x * 0.62
    const wobble = 0.5 + 0.5 * Math.sin(t * (2.2 + b * 0.37) + b * 1.7 + k * 20)
    const kick = x < 0.25 ? beat * (1 - x * 3) : 0
    const hat = x > 0.7 ? Math.exp(-((t * tempo * 2) % 1) * 9) * 0.35 : 0
    bins[b] = Math.min(1, strength * slope * (0.3 + 0.42 * wobble * (0.6 + 0.4 * swell) + 0.45 * kick + hat))
  }
}
