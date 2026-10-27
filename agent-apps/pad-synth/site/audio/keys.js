// The keys: a two-operator FM electric piano. A sine modulator at the note's own pitch gives the warm body and
// fades as the note sustains; a second, much higher modulator gives the short metallic tine at the strike.
import { fadeOut } from "./env.js";

export const id = "keys";
export const label = "Keys";
export const octave = 0;
export const look = { attack: 0.004, decay: 2.2, sustain: 0.12, release: 0.45 };

export function create(ctx) {
  return {
    play(freq, time, velocity, out) {
      const level = 0.24 * velocity;

      const carrier = ctx.createOscillator();
      carrier.type = "sine";
      carrier.frequency.value = freq;

      const body = ctx.createOscillator();
      body.type = "sine";
      body.frequency.value = freq;
      const bodyDepth = ctx.createGain();
      const index = 1.6 + velocity * 2.2;
      bodyDepth.gain.setValueAtTime(freq * index, time);
      bodyDepth.gain.setTargetAtTime(freq * 0.35, time + 0.01, 0.45);
      body.connect(bodyDepth).connect(carrier.frequency);

      const tine = ctx.createOscillator();
      tine.type = "sine";
      tine.frequency.value = freq * 14;
      const tineDepth = ctx.createGain();
      tineDepth.gain.setValueAtTime(freq * 1.4 * velocity, time);
      tineDepth.gain.setTargetAtTime(0, time + 0.002, 0.025);
      tine.connect(tineDepth).connect(carrier.frequency);

      const amp = ctx.createGain();
      amp.gain.setValueAtTime(0, time);
      amp.gain.linearRampToValueAtTime(level, time + look.attack);
      amp.gain.setTargetAtTime(level * look.sustain, time + look.attack, look.decay / 3);

      const pan = ctx.createStereoPanner();
      pan.pan.value = Math.max(-0.5, Math.min(0.5, Math.log2(freq / 262) * 0.3));
      carrier.connect(amp).connect(pan).connect(out);

      const sources = [carrier, body, tine];
      for (const source of sources) source.start(time);
      return {
        stop(at) {
          const end = Math.max(at, time + 0.05);
          fadeOut(amp.gain, end, look.release / 4.6);
          for (const source of sources) source.stop(end + look.release + 0.1);
        },
      };
    },
  };
}
