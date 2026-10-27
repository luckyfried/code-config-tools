// The bass: a saw and a slightly detuned square through a resonant lowpass that snaps open on each note and
// closes fast, a little drive for weight, and a clean sine sub an octave down underneath.
import { fadeOut, holdAt, softClip } from "./env.js";

export const id = "bass";
export const label = "Bass";
export const octave = -1;
export const look = { attack: 0.006, decay: 0.32, sustain: 0.72, release: 0.22 };

let curve = null;

export function create(ctx) {
  curve = curve || softClip(2.4);
  return {
    play(freq, time, velocity, out) {
      const { attack, decay, sustain, release } = look;
      const level = 0.3 * velocity;

      const amp = ctx.createGain();
      amp.gain.setValueAtTime(0, time);
      amp.gain.linearRampToValueAtTime(level, time + attack);
      amp.gain.setTargetAtTime(level * sustain, time + attack, decay / 3);

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.Q.value = 5;
      const floor = Math.min(freq * 2.2 + 120, 1400);
      filter.frequency.setValueAtTime(floor, time);
      filter.frequency.linearRampToValueAtTime(Math.min(floor + 2600 * velocity, 6000), time + 0.006);
      filter.frequency.setTargetAtTime(floor + 260, time + 0.006, 0.09);

      const drive = ctx.createWaveShaper();
      drive.curve = curve;
      drive.oversample = "2x";
      const trim = ctx.createGain();
      trim.gain.value = 0.55;

      const saw = ctx.createOscillator();
      saw.type = "sawtooth";
      saw.frequency.value = freq;
      const square = ctx.createOscillator();
      square.type = "square";
      square.frequency.value = freq;
      square.detune.value = 6;
      const squareLevel = ctx.createGain();
      squareLevel.gain.value = 0.45;
      saw.connect(filter);
      square.connect(squareLevel).connect(filter);
      filter.connect(drive).connect(trim).connect(amp);

      const sub = ctx.createOscillator();
      sub.type = "sine";
      sub.frequency.value = freq / 2;
      const subLevel = ctx.createGain();
      subLevel.gain.value = 0.9;
      sub.connect(subLevel).connect(amp);
      amp.connect(out);

      const sources = [saw, square, sub];
      for (const source of sources) source.start(time);
      return {
        stop(at) {
          const end = Math.max(at, time + 0.03);
          fadeOut(amp.gain, end, release / 4.6);
          holdAt(filter.frequency, end);
          filter.frequency.setTargetAtTime(floor, end, release / 3);
          for (const source of sources) source.stop(end + release + 0.1);
        },
      };
    },
  };
}
