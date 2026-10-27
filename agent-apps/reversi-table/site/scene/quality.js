// The quality tier, picked once and stepped down when frames run long: phone or desktop by pointer and width, then,
// after 120 drawn frames, a median frame over 20 ms drops the reflection, then the pixel ratio to 1.5, then to 1.
export function pickTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || Math.min(innerWidth, innerHeight) < 600 || innerWidth < 768 ? "phone" : "desktop";
}

export function tierSettings(tier) {
  const ratio = Math.min(devicePixelRatio || 1, 2);
  if (tier === "phone") {
    return { tier, pixelRatio: ratio, shadowMap: 1024, reflection: true, reflectionScale: 0.5, reflectionSamples: 0, iridescence: false, segments: 40 };
  }
  return { tier, pixelRatio: ratio, shadowMap: 2048, reflection: true, reflectionScale: 0.5, reflectionSamples: 4, iridescence: true, segments: 56 };
}

export class FrameWatch {
  constructor(onStep) {
    this.onStep = onStep;
    this.samples = [];
    this.steps = 0;
  }

  /** One frame's duration while the table was moving. */
  add(ms) {
    if (this.steps >= 3 || ms <= 0 || ms > 250) return;
    this.samples.push(ms);
    if (this.samples.length < 120) return;
    const sorted = this.samples.slice().sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];
    this.samples.length = 0;
    if (median > 20) {
      this.steps += 1;
      this.onStep(this.steps);
    }
  }
}
