// The opening: the view arrives on the night's best constellation while its lines draw on, then the sky turns two
// hours forward at about an hour a second, trails streaming, and turns back to the chosen time. Any touch, key, or
// wheel ends it where it stands; reduced motion skips it.

const HOUR = 3600e3;
const SPIN_AT = 2.5;
const OUT = 2.6;
const HOLD = 0.35;
const BACK = 2.2;
const SPAN = 2 * HOUR;

const easeInOutSine = (t) => -(Math.cos(Math.PI * t) - 1) / 2;
const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

// Constellations a person knows by shape, in the order the opening prefers them.
export const HEROES = ["Ori", "UMa", "Sco", "Cyg", "Cas", "Leo", "Sgr", "Cru", "Tau", "Gem", "Lyr", "Boo", "Peg", "Aql", "CMa", "Vir", "And", "Per", "Aur", "Cen"];

export function createIntro(reduced) {
  let t = 0;
  let active = !reduced;
  return {
    get active() {
      return active;
    },
    cancel() {
      active = false;
    },
    // Time offset from the chosen moment, in milliseconds.
    offset(dt) {
      if (!active) return 0;
      t += dt;
      const u = t - SPIN_AT;
      if (u <= 0) return 0;
      if (u < OUT) return SPAN * easeInOutSine(u / OUT);
      if (u < OUT + HOLD) return SPAN;
      if (u < OUT + HOLD + BACK) return SPAN * (1 - easeInOutCubic((u - OUT - HOLD) / BACK));
      active = false;
      return 0;
    },
  };
}
