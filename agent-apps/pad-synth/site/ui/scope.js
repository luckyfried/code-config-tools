// The glass ribbon across the top: the spectrum as frosted columns behind, the oscilloscope as a lit ribbon in
// front. With sound on it reads the analyser; before the first tap it draws the shape of the notes the field is
// showing, so the ribbon moves with the light either way.

const LOW = 40;
const HIGH = 14000;

export class Scope {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.tokens = null;
    this.time = null;
    this.freq = null;
    this.bars = new Float32Array(0);
    this.width = 0;
    this.height = 0;
    this.ratio = 1;
  }

  setTokens(tokens) {
    this.tokens = tokens;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.ratio = Math.min(window.devicePixelRatio || 1, 2);
    this.width = Math.max(1, Math.round(rect.width));
    this.height = Math.max(1, Math.round(rect.height));
    this.canvas.width = Math.round(this.width * this.ratio);
    this.canvas.height = Math.round(this.height * this.ratio);
    const count = Math.max(24, Math.min(96, Math.round(this.width / 16)));
    if (count !== this.bars.length) this.bars = new Float32Array(count);
  }

  /** Spectrum levels 0 to 1 per column, from the analyser or from the sounding notes. */
  levels(analyser, sources, now) {
    const count = this.bars.length;
    const target = new Float32Array(count);
    if (analyser) {
      if (!this.freq || this.freq.length !== analyser.frequencyBinCount) this.freq = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(this.freq);
      const nyquist = analyser.context.sampleRate / 2;
      for (let b = 0; b < count; b += 1) {
        const f0 = LOW * (HIGH / LOW) ** (b / count);
        const f1 = LOW * (HIGH / LOW) ** ((b + 1) / count);
        const i0 = Math.floor((f0 / nyquist) * this.freq.length);
        const i1 = Math.max(i0 + 1, Math.ceil((f1 / nyquist) * this.freq.length));
        let top = 0;
        for (let i = i0; i < i1 && i < this.freq.length; i += 1) top = Math.max(top, this.freq[i]);
        target[b] = (top / 255) ** 1.6;
      }
    } else {
      for (const source of sources.list) {
        for (let h = 1; h <= 5; h += 1) {
          const at = (Math.log(source.freq * h / LOW) / Math.log(HIGH / LOW)) * count;
          const level = source.amp * (0.42 / h) * (0.9 + 0.1 * Math.sin(now * 9 + h));
          for (let b = Math.max(0, Math.floor(at - 3)); b < Math.min(count, Math.ceil(at + 3)); b += 1) {
            target[b] += level * Math.exp(-(((b - at) / 1.3) ** 2));
          }
        }
      }
    }
    for (let b = 0; b < count; b += 1) {
      const v = Math.min(1, analyser ? target[b] : 1 - Math.exp(-target[b] * 1.4));
      this.bars[b] = v > this.bars[b] ? v : this.bars[b] * 0.9;
    }
    return this.bars;
  }

  /** The scope's points, -1 to 1, `points` of them, steadied on a rising zero crossing. */
  wave(analyser, sources, now, points) {
    const out = new Float32Array(points);
    if (analyser) {
      if (!this.time || this.time.length !== analyser.fftSize) this.time = new Float32Array(analyser.fftSize);
      analyser.getFloatTimeDomainData(this.time);
      const span = Math.min(Math.floor(this.time.length / 2), Math.round(analyser.context.sampleRate * 0.014));
      let start = 0;
      for (let i = 1; i < span; i += 1) {
        if (this.time[i - 1] < 0 && this.time[i] >= 0) {
          start = i;
          break;
        }
      }
      for (let p = 0; p < points; p += 1) out[p] = Math.max(-1, Math.min(1, this.time[start + Math.floor((p / points) * span)] * 1.6));
      return out;
    }
    let total = 0;
    for (const source of sources.list) total += source.amp;
    if (total < 1e-3) return out;
    const norm = 0.75 / Math.max(1, total);
    for (const source of sources.list) {
      const cycles = 2.5 * (source.freq / 147) ** 0.5;
      const phase = now * 1.7 * (source.freq / 220);
      for (let p = 0; p < points; p += 1) {
        const x = p / points;
        const s = Math.sin(2 * Math.PI * cycles * x + phase);
        out[p] += source.amp * norm * (s + 0.3 * Math.sin(4 * Math.PI * cycles * x + phase * 2));
      }
    }
    return out;
  }

  draw(analyser, sources, now) {
    if (!this.tokens || this.width < 2) return;
    const { ctx, width: w, height: h, ratio } = this;
    const t = this.tokens;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const bars = this.levels(analyser, sources, now);
    const count = bars.length;
    const slot = w / count;
    const bar = Math.max(2, slot - 3);
    ctx.fillStyle = t.spectrum;
    for (let b = 0; b < count; b += 1) {
      const height = Math.max(2, bars[b] * h * 0.66);
      const x = b * slot + (slot - bar) / 2;
      ctx.beginPath();
      ctx.roundRect(x, h - height, bar, height + 4, Math.min(3, bar / 2));
      ctx.fill();
    }
    ctx.fillStyle = t.spectrumCap;
    for (let b = 0; b < count; b += 1) {
      if (bars[b] < 0.03) continue;
      ctx.fillRect(b * slot + (slot - bar) / 2, h - Math.max(2, bars[b] * h * 0.66), bar, 1.5);
    }

    const points = Math.max(64, Math.min(220, Math.round(w / 5)));
    const wave = this.wave(analyser, sources, now, points);
    const mid = h * 0.6;
    const reach = h * 0.3;
    ctx.globalCompositeOperation = t.blend;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    for (let p = 0; p < points; p += 1) {
      const x = (p / (points - 1)) * w;
      const y = mid - wave[p] * reach;
      if (p === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = t.scopeGlow;
    ctx.lineWidth = 9;
    ctx.stroke();
    ctx.lineWidth = 4;
    ctx.stroke();
    ctx.strokeStyle = t.scopeLine;
    ctx.lineWidth = 1.6;
    ctx.stroke();
    ctx.globalCompositeOperation = "source-over";
  }
}
