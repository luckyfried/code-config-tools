// SM-2 as Piotr Wozniak published it in 1987: an E-Factor per item starting at 2.5, intervals of 1 day, 6 days, then
// the previous interval times the E-Factor rounded up, and a response below 3 that restarts the repetitions without
// touching the E-Factor. The interval uses the E-Factor this answer sets.
// Pure: the same inputs always give the same schedule.

export interface Schedule {
  ease: number
  interval: number
  reps: number
}

export const FRESH: Schedule = { ease: 2.5, interval: 0, reps: 0 }

/** The four grade buttons, as SM-2 response qualities: Again 1, Hard 3, Good 4, Easy 5. */
export const QUALITY = { 1: 1, 2: 3, 3: 4, 4: 5 } as const
export type Grade = keyof typeof QUALITY

export function nextEase(ease: number, q: number): number {
  const next = ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
  return Math.max(1.3, Math.round(next * 100) / 100)
}

export function answered(s: Schedule, q: number): Schedule {
  if (q < 3) return { ease: s.ease, interval: 1, reps: 0 }
  const ease = nextEase(s.ease, q)
  const step = (e: number) => (s.reps === 0 ? 1 : s.reps === 1 ? 6 : Math.ceil(s.interval * e))
  // Rounding up can land a 5 on the same day as a 4; a 5 always comes back at least a day after a 4 would.
  const interval = q === 5 && s.reps >= 2 ? Math.max(step(ease), step(nextEase(s.ease, 4)) + 1) : step(ease)
  return { ease, interval, reps: s.reps + 1 }
}

/** The two buttons SM-2 leaves alone get the usual flashcard spacing: Hard a short step, Easy a bonus on top. */
export const HARD_STEP = 1.2
export const EASY_BONUS = 1.3

/**
 * The schedule each button gives. Again restarts the card, Good is SM-2 at quality 4, Hard takes the lower E-Factor of
 * quality 3 and moves the interval only a short step on, and Easy is SM-2 at quality 5 with the Easy bonus applied.
 */
export function byGrade(s: Schedule, g: Grade): Schedule {
  if (g === 1) return answered(s, QUALITY[1])
  if (g === 3) return answered(s, QUALITY[3])
  if (g === 4) {
    const easy = answered(s, QUALITY[4])
    return { ...easy, interval: Math.ceil(easy.interval * EASY_BONUS) }
  }
  const interval = s.reps === 0 ? 1 : s.reps === 1 ? 3 : Math.max(s.interval + 1, Math.ceil(s.interval * HARD_STEP))
  return { ease: nextEase(s.ease, QUALITY[2]), interval, reps: s.reps + 1 }
}

/** Again brings the card back in the same day's session; every other button sends it to its interval. */
export function comesBackToday(g: Grade): boolean {
  return g === 1
}
