// Motion values shared by the bracket, the banner, and the pool. Springs are sampled into a CSS linear() easing so
// the Web Animations API plays them on the compositor with no library.

export const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)"

function sampleSpring(stiffness: number, damping: number, mass = 1, points = 48): { easing: string; ms: number } {
  const w0 = Math.sqrt(stiffness / mass)
  const zeta = damping / (2 * Math.sqrt(stiffness * mass))
  const at = (t: number) => {
    if (zeta < 1) {
      const wd = w0 * Math.sqrt(1 - zeta * zeta)
      return 1 - Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + ((zeta * w0) / wd) * Math.sin(wd * t))
    }
    return 1 - Math.exp(-w0 * t) * (1 + w0 * t)
  }
  // Settle time: the envelope falls under 0.1% of the travel.
  const settle = Math.min(2, -Math.log(0.001) / (zeta * w0))
  const values: string[] = []
  for (let i = 0; i <= points; i++) values.push(at((settle * i) / points).toFixed(4))
  values[values.length - 1] = "1"
  return { easing: `linear(${values.join(", ")})`, ms: Math.round(settle * 1000) }
}

export const SPRING = {
  slide: sampleSpring(380, 30),
  letter: sampleSpring(520, 26),
  flip: sampleSpring(260, 26),
}

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
}
