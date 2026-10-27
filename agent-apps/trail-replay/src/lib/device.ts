export const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)")

export function hasWebGL() {
  try {
    const canvas = document.createElement("canvas")
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"))
  } catch {
    return false
  }
}

export const isPhone = () => window.matchMedia("(pointer: coarse)").matches || window.innerWidth < 768

/**
 * How long a fixed piece of arithmetic takes, the quickest of three tries, in milliseconds. A current laptop or
 * flagship phone does it in about 3 ms; a phone that would miss frames over 3D terrain takes twice that or more.
 */
function cpuMs() {
  let best = Number.POSITIVE_INFINITY
  let sink = 0
  for (let k = 0; k < 3; k++) {
    const start = performance.now()
    for (let i = 0; i < 300000; i++) sink += Math.sqrt(i * 1.0001) % 7
    best = Math.min(best, performance.now() - start)
  }
  return sink < 0 ? 0 : best
}

/** A phone with few cores, little memory, or a slow processor starts with the terrain off, before the first frame. */
export function weakDevice() {
  if (!isPhone()) return false
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8
  const cores = navigator.hardwareConcurrency ?? 8
  return cores <= 4 || memory <= 2 || cpuMs() > 6
}
