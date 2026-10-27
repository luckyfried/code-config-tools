// The pluck: Karplus–Strong. A burst of filtered noise one period long circulates through a delay line whose
// two-tap average loses a little treble every pass, so the string rings bright and darkens as it dies away.
// Each note's samples are computed once per pitch and sample rate, then played from a buffer.
import { fadeOut } from "./env.js";

export const id = "pluck";
export const label = "Pluck";
export const octave = 1;
export const look = { attack: 0.005, decay: 1.1, sustain: 0, release: 0.8 };

const SECONDS = 2.6;
const cache = new Map();

/** A seeded noise source, so every render of the same note is the same. */
function noise(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return (state / 4294967296) * 2 - 1;
  };
}

function read(y, position) {
  if (position < 0) return 0;
  const index = Math.floor(position);
  const fraction = position - index;
  return y[index] * (1 - fraction) + y[index + 1] * fraction;
}

function strike(ctx, freq) {
  const rate = ctx.sampleRate;
  const key = `${rate}:${freq.toFixed(3)}`;
  const hit = cache.get(key);
  if (hit) return hit;

  const length = Math.floor(rate * SECONDS);
  const y = new Float32Array(length + 2);
  const period = rate / freq;
  // Ring time shortens up the neck the way a real string's does.
  const ring = Math.min(4.2, Math.max(0.9, 2.6 * (196 / freq) ** 0.45));
  const loss = 0.001 ** (1 / (freq * ring));
  const random = noise(Math.round(freq * 1000));
  const burst = Math.ceil(period);
  const brightness = Math.min(0.85, 0.35 + freq / 1600);
  let smooth = 0;
  let peak = 0;
  for (let n = 0; n < length; n += 1) {
    let excite = 0;
    if (n < burst) {
      smooth += brightness * (random() - smooth);
      excite = smooth;
    }
    const back = n - period;
    y[n] = excite + loss * 0.5 * (read(y, back - 0.5) + read(y, back + 0.5));
    peak = Math.max(peak, Math.abs(y[n]));
  }
  // Remove the offset the noise burst leaves, then set the level and fade the tail to silence.
  let mean = 0;
  for (let n = 0; n < burst; n += 1) mean += y[n];
  mean /= Math.max(1, burst);
  const gain = 0.9 / Math.max(peak, 1e-6);
  const fade = Math.floor(rate * 0.25);
  const buffer = ctx.createBuffer(1, length, rate);
  const data = buffer.getChannelData(0);
  let blocked = 0;
  let previous = 0;
  for (let n = 0; n < length; n += 1) {
    const x = (y[n] - mean) * gain;
    blocked = x - previous + 0.995 * blocked;
    previous = x;
    const tail = n > length - fade ? (length - n) / fade : 1;
    data[n] = blocked * tail;
  }
  cache.set(key, buffer);
  return buffer;
}

export function create(ctx) {
  return {
    /** Computes the strings ahead of time, so the first press of each pad never waits. */
    prepare(freqs) {
      for (const freq of freqs) strike(ctx, freq);
    },
    play(freq, time, velocity, out) {
      const source = ctx.createBufferSource();
      source.buffer = strike(ctx, freq);
      const body = ctx.createBiquadFilter();
      body.type = "peaking";
      body.frequency.value = 1800;
      body.Q.value = 0.8;
      body.gain.value = 3;
      const amp = ctx.createGain();
      amp.gain.value = 0.32 * velocity;
      const pan = ctx.createStereoPanner();
      pan.pan.value = Math.max(-0.4, Math.min(0.4, Math.log2(freq / 330) * 0.25));
      source.connect(body).connect(amp).connect(pan).connect(out);
      source.start(time);
      return {
        stop(at) {
          const end = Math.max(at, time + 0.3);
          fadeOut(amp.gain, end, look.release / 4.6);
          source.stop(end + look.release + 0.05);
        },
      };
    },
  };
}
