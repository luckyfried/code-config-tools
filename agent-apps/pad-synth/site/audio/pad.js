// The pad: five detuned saws spread across the stereo field, a sine an octave down for body, through a lowpass
// whose cutoff opens with the attack and settles, under a slow amplitude envelope.
import { fadeOut, holdAt } from "./env.js";

export const id = "pad";
export const label = "Pad";
export const octave = 0;
/** The envelope the glow follows, in seconds; the sound below uses the same numbers. */
export const look = { attack: 0.42, decay: 0.8, sustain: 0.78, release: 1.9 };

const DETUNE = [-17, -8, 0, 8, 17];
const PAN = [-0.7, -0.35, 0, 0.35, 0.7];

export function create(ctx) {
  return {
    play(freq, time, velocity, out) {
      const { attack, decay, sustain, release } = look;
      const level = 0.16 * velocity;

      const amp = ctx.createGain();
      amp.gain.setValueAtTime(0, time);
      amp.gain.linearRampToValueAtTime(level, time + attack);
      amp.gain.setTargetAtTime(level * sustain, time + attack, decay / 3);

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.Q.value = 1.1;
      const closed = Math.min(freq * 1.6 + 240, 4000);
      const open = Math.min(freq * 7 + 2200, 11000);
      const rest = Math.min(freq * 3.5 + 1100, 7000);
      filter.frequency.setValueAtTime(closed, time);
      filter.frequency.linearRampToValueAtTime(open, time + attack);
      filter.frequency.setTargetAtTime(rest, time + attack, decay / 2);
      filter.connect(amp);
      amp.connect(out);

      const sources = DETUNE.map((cents, index) => {
        const osc = ctx.createOscillator();
        osc.type = "sawtooth";
        osc.frequency.value = freq;
        osc.detune.value = cents;
        const mix = ctx.createGain();
        mix.gain.value = 0.2;
        const pan = ctx.createStereoPanner();
        pan.pan.value = PAN[index];
        osc.connect(mix).connect(pan).connect(filter);
        osc.start(time);
        return osc;
      });
      const sub = ctx.createOscillator();
      sub.type = "sine";
      sub.frequency.value = freq / 2;
      const subLevel = ctx.createGain();
      subLevel.gain.value = 0.45;
      sub.connect(subLevel).connect(amp);
      sub.start(time);
      sources.push(sub);

      return {
        stop(at) {
          const end = Math.max(at, time + 0.02);
          fadeOut(amp.gain, end, release / 4.6);
          holdAt(filter.frequency, end);
          filter.frequency.setTargetAtTime(closed, end, release / 3);
          for (const source of sources) source.stop(end + release + 0.1);
        },
      };
    },
  };
}
