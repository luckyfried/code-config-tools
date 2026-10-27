// Reduced motion drops the spring and the static; a weak phone drops the glass blur.
export const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

export const weakDevice = () => {
  if (typeof navigator === 'undefined') return false
  const nav = navigator as Navigator & { deviceMemory?: number }
  const coarse = window.matchMedia('(pointer: coarse)').matches
  return coarse && ((nav.deviceMemory ?? 8) <= 2 || (nav.hardwareConcurrency ?? 8) <= 2)
}
