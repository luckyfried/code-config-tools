// The sound of Quick Draw, as recipes rendered offline (OfflineAudioContext, faster than real time) into WAV files
// under audio/. The page plays those files; scripts/bake_sounds.mjs renders them again after a recipe changes.
//   gunshot  a noise burst through a falling lowpass, a body thump, and a convolver reverb from a generated
//            impulse response with slapback off the storefronts and an echo off the mesas
//   click    a dry fire; jam: the cylinder rattling
//   tick, tock  the clock during the wait; crow: two caws; wind: a seamless bed of desert wind
//   draw     a struck bell; slowmo: the swell under the slow motion; hit: the bullet through the hat
//   hat      the hat landing in the dirt; stamp: the poster slapped on the board

const RATE = 44100;

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function noiseBuffer(ctx, seconds, seed, channels = 1) {
  const r = rng(seed);
  const buf = ctx.createBuffer(channels, Math.ceil(seconds * ctx.sampleRate), ctx.sampleRate);
  for (let c = 0; c < channels; c += 1) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i += 1) d[i] = r() * 2 - 1;
  }
  return buf;
}

function noise(ctx, seconds, seed) {
  const src = ctx.createBufferSource();
  src.buffer = noiseBuffer(ctx, seconds, seed);
  return src;
}

function env(ctx, at, attack, peak, decay, floor = 0.0001) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, 0);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + attack);
  g.gain.exponentialRampToValueAtTime(floor, at + attack + decay);
  return g;
}

function filter(ctx, type, freq, q = 0.7) {
  const f = ctx.createBiquadFilter();
  f.type = type;
  f.frequency.value = freq;
  f.Q.value = q;
  return f;
}

/** A street-and-canyon impulse response: slapback off the storefronts, a long tail, a late echo off the mesas. */
function streetImpulse(ctx, seconds, seed) {
  const r = rng(seed);
  const len = Math.ceil(seconds * ctx.sampleRate);
  const buf = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c += 1) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < len; i += 1) {
      const t = i / ctx.sampleRate;
      let v = (r() * 2 - 1) * Math.exp(-t * 2.6) * 0.35;
      v *= Math.min(1, t * 60);
      d[i] = v;
    }
    const taps = [
      [0.045 + c * 0.012, 0.7],
      [0.11 + c * 0.02, 0.5],
      [0.19 - c * 0.015, 0.35],
      [0.62 + c * 0.03, 0.28],
      [0.93 - c * 0.02, 0.14],
    ];
    for (const [at, gain] of taps) {
      const start = Math.floor(at * ctx.sampleRate);
      for (let k = 0; k < 900 && start + k < len; k += 1) d[start + k] += (r() * 2 - 1) * gain * Math.exp(-k / 160);
    }
  }
  return buf;
}

const RECIPES = {
  gunshot: {
    seconds: 2.8,
    channels: 2,
    build(ctx) {
      const out = ctx.createDynamicsCompressor();
      out.threshold.value = -10;
      out.ratio.value = 6;
      out.attack.value = 0.001;
      out.release.value = 0.2;
      out.connect(ctx.destination);
      const dry = ctx.createGain();
      dry.gain.value = 0.9;
      const wet = ctx.createGain();
      wet.gain.value = 0.62;
      const verb = ctx.createConvolver();
      verb.normalize = true;
      verb.buffer = streetImpulse(ctx, 2.4, 9);
      dry.connect(out);
      verb.connect(wet).connect(out);
      const bus = ctx.createGain();
      bus.connect(dry);
      bus.connect(verb);

      const blast = noise(ctx, 0.6, 1);
      const lp = filter(ctx, "lowpass", 8000, 0.8);
      lp.frequency.setValueAtTime(9000, 0);
      lp.frequency.exponentialRampToValueAtTime(1400, 0.08);
      lp.frequency.exponentialRampToValueAtTime(420, 0.45);
      blast.connect(lp).connect(env(ctx, 0.005, 0.002, 1.0, 0.42)).connect(bus);
      blast.start(0.005);

      const crack = noise(ctx, 0.05, 2);
      crack.connect(filter(ctx, "highpass", 2600, 0.7)).connect(env(ctx, 0.004, 0.001, 0.8, 0.03)).connect(bus);
      crack.start(0.004);

      const thump = ctx.createOscillator();
      thump.frequency.setValueAtTime(120, 0.005);
      thump.frequency.exponentialRampToValueAtTime(42, 0.2);
      thump.connect(env(ctx, 0.005, 0.003, 0.95, 0.3)).connect(bus);
      thump.start(0.005);
      thump.stop(0.5);
    },
  },

  click: {
    seconds: 0.4,
    build(ctx) {
      const out = ctx.destination;
      for (const [at, gain] of [[0.004, 0.9], [0.09, 0.45]]) {
        const n = noise(ctx, 0.03, 3 + at * 1000);
        n.connect(filter(ctx, "bandpass", 3600, 1.4)).connect(env(ctx, at, 0.001, gain, 0.012)).connect(out);
        n.start(at);
        const ping = ctx.createOscillator();
        ping.type = "triangle";
        ping.frequency.value = at < 0.05 ? 3150 : 2700;
        ping.connect(env(ctx, at, 0.001, gain * 0.25, 0.07)).connect(out);
        ping.start(at);
        ping.stop(at + 0.12);
      }
    },
  },

  jam: {
    seconds: 0.7,
    build(ctx) {
      const out = ctx.destination;
      const times = [0.0, 0.034, 0.07, 0.112, 0.15, 0.2, 0.26];
      times.forEach((at, i) => {
        const n = noise(ctx, 0.03, 20 + i);
        n.connect(filter(ctx, "bandpass", 2400 + (i % 3) * 700, 2)).connect(env(ctx, at + 0.005, 0.001, 0.7 * Math.pow(0.82, i), 0.018)).connect(out);
        n.start(at + 0.005);
      });
      const clunk = ctx.createOscillator();
      clunk.frequency.setValueAtTime(220, 0.31);
      clunk.frequency.exponentialRampToValueAtTime(90, 0.42);
      clunk.connect(env(ctx, 0.31, 0.002, 0.5, 0.14)).connect(out);
      clunk.start(0.31);
      clunk.stop(0.6);
      const spring = ctx.createOscillator();
      spring.type = "sawtooth";
      spring.frequency.setValueAtTime(1900, 0.33);
      spring.frequency.exponentialRampToValueAtTime(700, 0.62);
      spring.connect(filter(ctx, "bandpass", 1600, 6)).connect(env(ctx, 0.33, 0.004, 0.18, 0.28)).connect(out);
      spring.start(0.33);
      spring.stop(0.68);
    },
  },

  tick: {
    seconds: 0.18,
    build(ctx) {
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(1900, 0.003);
      o.frequency.exponentialRampToValueAtTime(1250, 0.03);
      o.connect(env(ctx, 0.003, 0.001, 0.55, 0.045)).connect(ctx.destination);
      o.start(0.003);
      o.stop(0.1);
      const n = noise(ctx, 0.03, 31);
      n.connect(filter(ctx, "bandpass", 2600, 2)).connect(env(ctx, 0.003, 0.001, 0.5, 0.012)).connect(ctx.destination);
      n.start(0.003);
    },
  },

  tock: {
    seconds: 0.2,
    build(ctx) {
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(1350, 0.003);
      o.frequency.exponentialRampToValueAtTime(880, 0.035);
      o.connect(env(ctx, 0.003, 0.001, 0.55, 0.055)).connect(ctx.destination);
      o.start(0.003);
      o.stop(0.12);
      const n = noise(ctx, 0.03, 32);
      n.connect(filter(ctx, "bandpass", 1900, 2)).connect(env(ctx, 0.003, 0.001, 0.45, 0.014)).connect(ctx.destination);
      n.start(0.003);
    },
  },

  crow: {
    seconds: 1.4,
    build(ctx) {
      const out = ctx.createGain();
      out.gain.value = 0.8;
      const verb = ctx.createConvolver();
      verb.buffer = streetImpulse(ctx, 1.2, 77);
      const wet = ctx.createGain();
      wet.gain.value = 0.25;
      out.connect(ctx.destination);
      out.connect(verb).connect(wet).connect(ctx.destination);
      const shaper = ctx.createWaveShaper();
      const curve = new Float32Array(1024);
      for (let i = 0; i < curve.length; i += 1) {
        const x = (i / (curve.length - 1)) * 2 - 1;
        curve[i] = Math.tanh(x * 3.2);
      }
      shaper.curve = curve;
      for (const [at, len, pitch] of [[0.02, 0.34, 560], [0.5, 0.3, 520]]) {
        const o = ctx.createOscillator();
        o.type = "sawtooth";
        o.frequency.setValueAtTime(pitch, at);
        o.frequency.linearRampToValueAtTime(pitch * 1.08, at + 0.05);
        o.frequency.exponentialRampToValueAtTime(pitch * 0.7, at + len);
        const vib = ctx.createOscillator();
        vib.frequency.value = 34;
        const depth = ctx.createGain();
        depth.gain.value = 26;
        vib.connect(depth).connect(o.frequency);
        const g = ctx.createGain();
        g.gain.setValueAtTime(0.0001, at);
        g.gain.exponentialRampToValueAtTime(0.7, at + 0.03);
        g.gain.setValueAtTime(0.6, at + len * 0.6);
        g.gain.exponentialRampToValueAtTime(0.0001, at + len);
        const f1 = filter(ctx, "bandpass", 1150, 1.6);
        const f2 = filter(ctx, "bandpass", 2350, 2.4);
        const mix = ctx.createGain();
        o.connect(shaper);
        shaper.connect(f1).connect(mix);
        shaper.connect(f2).connect(mix);
        mix.connect(g).connect(out);
        const breath = noise(ctx, len + 0.05, 40 + at * 10);
        breath.connect(filter(ctx, "bandpass", 1600, 1.2)).connect(env(ctx, at, 0.02, 0.18, len)).connect(out);
        breath.start(at);
        o.start(at);
        vib.start(at);
        o.stop(at + len + 0.02);
        vib.stop(at + len + 0.02);
      }
    },
  },

  wind: {
    seconds: 13,
    channels: 1,
    rate: 22050,
    loopFade: 1,
    build(ctx) {
      const n = noise(ctx, 13, 55);
      const lp = filter(ctx, "lowpass", 700, 0.5);
      const bp = filter(ctx, "bandpass", 420, 0.9);
      const r = rng(56);
      const steps = 40;
      const curve = new Float32Array(steps);
      const gust = new Float32Array(steps);
      for (let i = 0; i < steps; i += 1) {
        curve[i] = 280 + r() * 520;
        gust[i] = 0.25 + r() * 0.5;
      }
      bp.frequency.setValueCurveAtTime(curve, 0, 13);
      const g = ctx.createGain();
      g.gain.setValueCurveAtTime(gust, 0, 13);
      n.connect(lp).connect(bp).connect(g).connect(ctx.destination);
      const whistle = noise(ctx, 13, 57);
      const wf = filter(ctx, "bandpass", 1100, 14);
      const wcurve = new Float32Array(steps);
      for (let i = 0; i < steps; i += 1) wcurve[i] = 900 + r() * 500;
      wf.frequency.setValueCurveAtTime(wcurve, 0, 13);
      const wg = ctx.createGain();
      wg.gain.value = 0.12;
      whistle.connect(wf).connect(wg).connect(ctx.destination);
      n.start(0);
      whistle.start(0);
    },
  },

  draw: {
    seconds: 1.6,
    build(ctx) {
      const base = 1180;
      for (const [ratio, gain, decay] of [[1, 0.45, 1.3], [2.76, 0.22, 0.6], [5.4, 0.12, 0.3], [8.9, 0.05, 0.15]]) {
        const o = ctx.createOscillator();
        o.frequency.value = base * ratio;
        o.connect(env(ctx, 0.003, 0.002, gain, decay)).connect(ctx.destination);
        o.start(0.003);
        o.stop(1.5);
      }
      const n = noise(ctx, 0.04, 61);
      n.connect(filter(ctx, "highpass", 4000)).connect(env(ctx, 0.003, 0.001, 0.3, 0.02)).connect(ctx.destination);
      n.start(0.003);
    },
  },

  slowmo: {
    seconds: 1.6,
    channels: 2,
    build(ctx) {
      const n = noise(ctx, 1.6, 71);
      const lp = filter(ctx, "lowpass", 200, 3);
      lp.frequency.setValueAtTime(160, 0);
      lp.frequency.exponentialRampToValueAtTime(1300, 0.5);
      lp.frequency.exponentialRampToValueAtTime(220, 1.5);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, 0);
      g.gain.exponentialRampToValueAtTime(0.55, 0.35);
      g.gain.exponentialRampToValueAtTime(0.0001, 1.55);
      n.connect(lp).connect(g).connect(ctx.destination);
      n.start(0);
      const sub = ctx.createOscillator();
      sub.frequency.setValueAtTime(70, 0);
      sub.frequency.exponentialRampToValueAtTime(34, 1.3);
      sub.connect(env(ctx, 0.01, 0.12, 0.6, 1.3)).connect(ctx.destination);
      sub.start(0);
      sub.stop(1.6);
    },
  },

  hit: {
    seconds: 0.4,
    build(ctx) {
      const n = noise(ctx, 0.3, 81);
      const bp = filter(ctx, "bandpass", 3200, 3);
      bp.frequency.setValueAtTime(3600, 0.003);
      bp.frequency.exponentialRampToValueAtTime(900, 0.16);
      n.connect(bp).connect(env(ctx, 0.003, 0.002, 0.8, 0.16)).connect(ctx.destination);
      n.start(0.003);
      const thwap = noise(ctx, 0.08, 82);
      thwap.connect(filter(ctx, "lowpass", 900)).connect(env(ctx, 0.005, 0.002, 0.6, 0.06)).connect(ctx.destination);
      thwap.start(0.005);
    },
  },

  hat: {
    seconds: 0.4,
    build(ctx) {
      const n = noise(ctx, 0.25, 91);
      n.connect(filter(ctx, "lowpass", 520, 0.8)).connect(env(ctx, 0.004, 0.003, 0.9, 0.14)).connect(ctx.destination);
      n.start(0.004);
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(95, 0.004);
      o.frequency.exponentialRampToValueAtTime(55, 0.1);
      o.connect(env(ctx, 0.004, 0.002, 0.6, 0.11)).connect(ctx.destination);
      o.start(0.004);
      o.stop(0.2);
      const grit = noise(ctx, 0.2, 92);
      grit.connect(filter(ctx, "bandpass", 2400, 0.8)).connect(env(ctx, 0.01, 0.01, 0.12, 0.15)).connect(ctx.destination);
      grit.start(0.01);
    },
  },

  stamp: {
    seconds: 0.5,
    build(ctx) {
      const o = ctx.createOscillator();
      o.frequency.setValueAtTime(110, 0.004);
      o.frequency.exponentialRampToValueAtTime(48, 0.14);
      o.connect(env(ctx, 0.004, 0.002, 0.9, 0.18)).connect(ctx.destination);
      o.start(0.004);
      o.stop(0.3);
      const slap = noise(ctx, 0.1, 101);
      slap.connect(filter(ctx, "bandpass", 1700, 0.9)).connect(env(ctx, 0.004, 0.001, 0.55, 0.05)).connect(ctx.destination);
      slap.start(0.004);
    },
  },
};

export const SOUND_NAMES = Object.keys(RECIPES);

/** Renders one recipe offline into an AudioBuffer, peak-normalized; the wind is folded into a seamless loop. */
export async function renderSound(name) {
  const recipe = RECIPES[name];
  const rate = recipe.rate || RATE;
  const ctx = new OfflineAudioContext(recipe.channels || 1, Math.ceil(recipe.seconds * rate), rate);
  recipe.build(ctx);
  let buffer = await ctx.startRendering();
  if (recipe.loopFade) buffer = foldLoop(buffer, recipe.loopFade);
  let peak = 0;
  for (let c = 0; c < buffer.numberOfChannels; c += 1) {
    const d = buffer.getChannelData(c);
    for (let i = 0; i < d.length; i += 1) peak = Math.max(peak, Math.abs(d[i]));
  }
  const k = peak > 0 ? 0.92 / peak : 1;
  for (let c = 0; c < buffer.numberOfChannels; c += 1) {
    const d = buffer.getChannelData(c);
    for (let i = 0; i < d.length; i += 1) d[i] *= k;
  }
  return buffer;
}

function foldLoop(buffer, fadeSeconds) {
  const rate = buffer.sampleRate;
  const fade = Math.floor(fadeSeconds * rate);
  const len = buffer.length - fade;
  const out = new AudioBuffer({ numberOfChannels: buffer.numberOfChannels, length: len, sampleRate: rate });
  for (let c = 0; c < buffer.numberOfChannels; c += 1) {
    const src = buffer.getChannelData(c);
    const dst = out.getChannelData(c);
    for (let i = 0; i < len; i += 1) dst[i] = src[i];
    for (let i = 0; i < fade; i += 1) {
      const t = i / fade;
      dst[i] = src[i] * Math.sqrt(t) + src[len + i] * Math.sqrt(1 - t);
    }
  }
  return out;
}

/** 16-bit PCM WAV bytes of an AudioBuffer. */
export function toWav(buffer) {
  const channels = buffer.numberOfChannels;
  const rate = buffer.sampleRate;
  const frames = buffer.length;
  const bytes = 44 + frames * channels * 2;
  const view = new DataView(new ArrayBuffer(bytes));
  const text = (at, s) => [...s].forEach((ch, i) => view.setUint8(at + i, ch.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, bytes - 8, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * channels * 2, true);
  view.setUint16(32, channels * 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, frames * channels * 2, true);
  const data = [];
  for (let c = 0; c < channels; c += 1) data.push(buffer.getChannelData(c));
  let o = 44;
  for (let i = 0; i < frames; i += 1) {
    for (let c = 0; c < channels; c += 1) {
      const v = Math.max(-1, Math.min(1, data[c][i]));
      view.setInt16(o, Math.round(v * 32767), true);
      o += 2;
    }
  }
  return view.buffer;
}
