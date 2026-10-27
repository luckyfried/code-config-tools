// Every sound is synthesized: a rolling rumble whose pitch follows speed, the boost chime, gate chords rising
// through the three checkpoints, the countdown, landings, a fall, and the finish fanfare.
export function createSynth(enabled) {
  let ctx = null;
  let master = null;
  let rumble = null;
  let on = enabled;

  const start = () => {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14;
    comp.ratio.value = 4;
    master = ctx.createGain();
    master.gain.value = on ? 0.7 : 0;
    master.connect(comp).connect(ctx.destination);

    // Brown noise through a low-pass whose cutoff follows the speed, plus a low hum.
    const length = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let last = 0;
    for (let i = 0; i < length; i += 1) {
      const white = Math.random() * 2 - 1;
      last = (last + 0.02 * white) / 1.02;
      data[i] = last * 3.5;
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    noise.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 120;
    filter.Q.value = 0.8;
    const hum = ctx.createOscillator();
    hum.type = "triangle";
    hum.frequency.value = 40;
    const humGain = ctx.createGain();
    humGain.gain.value = 0;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    noise.connect(filter).connect(gain).connect(master);
    hum.connect(humGain).connect(master);
    noise.start();
    hum.start();
    rumble = { filter, gain, hum, humGain };
  };

  const tone = (freq, at, dur, type = "sine", level = 0.25) => {
    if (!ctx) return;
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.value = freq;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(level, at + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0008, at + dur);
    osc.connect(g).connect(master);
    osc.start(at);
    osc.stop(at + dur + 0.05);
  };

  const now = () => (ctx ? ctx.currentTime : 0);
  const note = (n) => 440 * Math.pow(2, (n - 69) / 12);

  return {
    start,
    get enabled() {
      return on;
    },
    set enabled(value) {
      on = value;
      if (master) master.gain.setTargetAtTime(on ? 0.7 : 0, now(), 0.05);
    },
    suspend() {
      if (ctx && ctx.state === "running") ctx.suspend();
    },
    resume() {
      if (ctx && ctx.state === "suspended") ctx.resume();
    },
    roll(speed, rolling) {
      if (!rumble) return;
      const t = now();
      const k = Math.min(1, speed / 46);
      rumble.filter.frequency.setTargetAtTime(90 + k * 900, t, 0.08);
      rumble.gain.gain.setTargetAtTime(rolling ? 0.05 + k * 0.22 : 0, t, 0.06);
      rumble.hum.frequency.setTargetAtTime(34 + k * 70, t, 0.1);
      rumble.humGain.gain.setTargetAtTime(rolling ? 0.02 + k * 0.05 : 0, t, 0.08);
    },
    countdown(go) {
      const t = now();
      tone(go ? 988 : 659, t, go ? 0.5 : 0.22, "triangle", 0.22);
    },
    boost() {
      const t = now();
      tone(note(84), t, 0.5, "sine", 0.2);
      tone(note(91), t + 0.05, 0.6, "sine", 0.16);
      tone(note(96), t + 0.1, 0.7, "triangle", 0.08);
    },
    gate(index) {
      const t = now();
      const root = 72 + index * 2;
      for (const [i, step] of [0, 4, 7, 12].entries()) tone(note(root + step), t + i * 0.035, 1.1, "triangle", 0.12);
    },
    land(impact) {
      if (!ctx) return;
      const t = now();
      const osc = ctx.createOscillator();
      osc.frequency.setValueAtTime(140, t);
      osc.frequency.exponentialRampToValueAtTime(48, t + 0.18);
      const g = ctx.createGain();
      g.gain.setValueAtTime(Math.min(0.45, 0.15 + impact * 0.02), t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
      osc.connect(g).connect(master);
      osc.start(t);
      osc.stop(t + 0.3);
    },
    fall() {
      if (!ctx) return;
      const t = now();
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(900, t);
      osc.frequency.exponentialRampToValueAtTime(140, t + 0.9);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.14, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 1);
      osc.connect(g).connect(master);
      osc.start(t);
      osc.stop(t + 1.05);
    },
    finish(medal) {
      const t = now();
      const seq = [72, 76, 79, 84];
      seq.forEach((n, i) => tone(note(n), t + i * 0.11, 0.5, "triangle", 0.16));
      const chord = medal === "gold" ? [84, 88, 91, 96] : medal === "silver" ? [79, 84, 88] : [76, 79, 84];
      for (const n of chord) tone(note(n), t + 0.48, 1.6, "sine", 0.12);
    },
  };
}
