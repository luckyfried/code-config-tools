export const reducedMotion = (): boolean => window.matchMedia("(prefers-reduced-motion: reduce)").matches

/** A phone with few cores or little memory skips the sheen, which repaints every frame. */
export function weakDevice(): boolean {
  const coarse = window.matchMedia("(pointer: coarse)").matches
  const cores = navigator.hardwareConcurrency || 8
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8
  return coarse && (cores <= 4 || memory <= 2)
}

export const sleep = (ms: number) => new Promise<void>((done) => window.setTimeout(done, ms))
