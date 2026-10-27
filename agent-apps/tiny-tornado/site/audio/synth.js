// Every sound is made here, live: the roar (brown noise through a resonant lowpass whose cutoff rises with the
// storm's speed and mass), impacts keyed to what landed, a plank splinter, a cow's moo (a sawtooth through two
// formant filters), thunder, and the pulse's whoosh. The context starts on the first button press.
export function createAudio() {
  let ctx = null;
  let master = null;
  let noise = null;
  let roar = null;
  let enabled = true;
  let lastMoo = 0;

  function makeNoise(brown) {
    const length = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < length; i++) {
      const white = Math.random() * 2 - 1;
      if (brown) {
        last = (last + 0.02 * white) / 1.02;
        data[i] = last * 3.5;
      } else data[i] = white;
    }
    return buffer;
  }

  function source(buffer, loop = false) {
    const s = ctx.createBufferSource();
    s.buffer = buffer;
    s.loop = loop;
    return s;
  }

  function start() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = enabled ? 0.8 : 0;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14;
    comp.ratio.value = 4;
    master.connect(comp).connect(ctx.destination);
    noise = { white: makeNoise(false), brown: makeNoise(true) };
    const body = source(noise.brown, true);
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.Q.value = 7;
    filter.frequency.value = 160;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    const hiss = source(noise.white, true);
    const band = ctx.createBiquadFilter();
    band.type = "bandpass";
    band.frequency.value = 520;
    band.Q.value = 0.8;
    const hissGain = ctx.createGain();
    hissGain.gain.value = 0;
    body.connect(filter).connect(gain).connect(master);
    hiss.connect(band).connect(hissGain).connect(master);
    body.start();
    hiss.start();
    roar = { filter, gain, band, hissGain };
  }

  function burst({ freq = 1200, type = "lowpass", q = 1, dur = 0.3, gain = 0.4, at = 0, brown = false }) {
    const t = ctx.currentTime + at;
    const s = source(brown ? noise.brown : noise.white);
    const f = ctx.createBiquadFilter();
    f.type = type;
    f.frequency.value = freq;
    f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(gain, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    s.connect(f).connect(g).connect(master);
    s.start(t, Math.random() * 1.5);
    s.stop(t + dur + 0.05);
    return f;
  }

  function tone({ from, to, dur, gain, type = "sine", at = 0 }) {
    const t = ctx.currentTime + at;
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(from, t);
    o.frequency.exponentialRampToValueAtTime(to, t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(gain, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g).connect(master);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  const ready = () => ctx && enabled && ctx.state === "running";

  return {
    start,
    get enabled() {
      return enabled;
    },
    setEnabled(on) {
      enabled = on;
      if (master) master.gain.setTargetAtTime(on ? 0.8 : 0, ctx.currentTime, 0.05);
    },
    // speed and mass both run 0 to 1; level 0 silences the roar.
    roar(speed, mass, level) {
      if (!ctx) return;
      const t = ctx.currentTime;
      roar.filter.frequency.setTargetAtTime(120 + 520 * mass + 380 * speed, t, 0.2);
      roar.gain.gain.setTargetAtTime(level * (0.22 + 0.3 * mass + 0.12 * speed), t, 0.25);
      roar.band.frequency.setTargetAtTime(380 + 900 * speed + 400 * mass, t, 0.2);
      roar.hissGain.gain.setTargetAtTime(level * (0.03 + 0.05 * speed), t, 0.25);
    },
    impact(mass) {
      if (!ready()) return;
      const heavy = Math.min(1, mass / 6);
      burst({ freq: 2400 - heavy * 1900, dur: 0.18 + heavy * 0.5, gain: 0.18 + heavy * 0.3, brown: heavy > 0.5 });
      tone({ from: 140 - heavy * 70, to: 40, dur: 0.2 + heavy * 0.4, gain: 0.2 + heavy * 0.35 });
    },
    splinter() {
      if (!ready()) return;
      for (let i = 0; i < 9; i++) burst({ freq: 2200 + Math.random() * 2600, type: "highpass", q: 2, dur: 0.05 + Math.random() * 0.08, gain: 0.25, at: Math.random() * 0.45 });
      tone({ from: 180, to: 60, dur: 0.5, gain: 0.25, type: "triangle" });
    },
    moo() {
      if (!ready() || ctx.currentTime - lastMoo < 0.7) return;
      lastMoo = ctx.currentTime;
      const t = ctx.currentTime;
      const pitch = 0.85 + Math.random() * 0.35;
      const o = ctx.createOscillator();
      o.type = "sawtooth";
      o.frequency.setValueAtTime(120 * pitch, t);
      o.frequency.linearRampToValueAtTime(150 * pitch, t + 0.25);
      o.frequency.exponentialRampToValueAtTime(92 * pitch, t + 1.0);
      const vib = ctx.createOscillator();
      vib.frequency.value = 5.5;
      const vibGain = ctx.createGain();
      vibGain.gain.value = 3;
      vib.connect(vibGain).connect(o.frequency);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.32, t + 0.12);
      g.gain.setValueAtTime(0.3, t + 0.7);
      g.gain.exponentialRampToValueAtTime(0.001, t + 1.1);
      for (const [f, q, a] of [[620, 6, 1], [1150, 7, 0.6], [2400, 8, 0.2]]) {
        const bp = ctx.createBiquadFilter();
        bp.type = "bandpass";
        bp.frequency.setValueAtTime(f * 0.8, t);
        bp.frequency.linearRampToValueAtTime(f, t + 0.3);
        bp.Q.value = q;
        const ga = ctx.createGain();
        ga.gain.value = a;
        o.connect(bp).connect(ga).connect(g);
      }
      g.connect(master);
      o.start(t);
      vib.start(t);
      o.stop(t + 1.2);
      vib.stop(t + 1.2);
    },
    thunder(near) {
      if (!ready()) return;
      const t = ctx.currentTime;
      const s = source(noise.brown);
      const f = ctx.createBiquadFilter();
      f.type = "lowpass";
      f.frequency.setValueAtTime(1400, t);
      f.frequency.exponentialRampToValueAtTime(90, t + 2.6);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.9 * near, t + 0.03);
      g.gain.exponentialRampToValueAtTime(0.4 * near, t + 0.5);
      g.gain.exponentialRampToValueAtTime(0.001, t + 3.2);
      s.connect(f).connect(g).connect(master);
      s.start(t);
      s.stop(t + 3.3);
      burst({ freq: 3000, type: "highpass", dur: 0.12, gain: 0.35 * near });
    },
    pulse() {
      if (!ready()) return;
      const f = burst({ freq: 300, type: "bandpass", q: 1.4, dur: 0.9, gain: 0.55 });
      const t = ctx.currentTime;
      f.frequency.setValueAtTime(260, t);
      f.frequency.exponentialRampToValueAtTime(1900, t + 0.25);
      f.frequency.exponentialRampToValueAtTime(220, t + 0.85);
      tone({ from: 90, to: 38, dur: 0.6, gain: 0.35 });
    },
  };
}
