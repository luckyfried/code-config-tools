// The quality tier, picked once and stepped down if frames run long: pixel ratio first, then the flat wall.

export function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!c.getContext("webgl2");
  } catch {
    return false;
  }
}

export function pickTier() {
  const phone = matchMedia("(pointer: coarse)").matches || innerWidth < 768;
  const dpr = window.devicePixelRatio || 1;
  return phone
    ? { name: "phone", phone: true, ratio: Math.min(dpr, 2), antialias: true, dust: 120 }
    : { name: "desktop", phone: false, ratio: Math.min(dpr, 2), antialias: true, dust: 260 };
}

// Watches frame times after the scene warms up; a run of long frames lowers the ratio, and at ratio 1 asks for the flat wall.
export class FrameWatch {
  constructor(tier, onRatio, onFlat) {
    this.tier = tier;
    this.onRatio = onRatio;
    this.onFlat = onFlat;
    this.skip = 45;
    this.times = [];
    this.last = 0;
  }

  frame(now) {
    if (this.last) {
      const ms = (now - this.last) * 1000;
      if (this.skip > 0) this.skip -= 1;
      else if (ms < 250) this.times.push(ms);
    }
    this.last = now;
    if (this.times.length < 120) return;
    const mean = this.times.reduce((a, b) => a + b, 0) / this.times.length;
    this.times.length = 0;
    if (mean <= 20) return;
    if (this.tier.ratio > 1.5) {
      this.tier.ratio = 1.5;
      this.onRatio(1.5);
    } else if (this.tier.ratio > 1) {
      this.tier.ratio = 1;
      this.onRatio(1);
    } else {
      this.onFlat();
    }
  }

  resume() {
    this.last = 0;
    this.skip = 20;
  }
}
