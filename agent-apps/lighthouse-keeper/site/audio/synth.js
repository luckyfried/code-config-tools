// Every sound is made here with Web Audio: the sea bed, the foghorn, the burn, thunder, the flare, the wreck, and
// the dawn chord. Nothing plays until the person's first tap or key.
let ctx = null;
let master = null;
let burnGain = null;
let burnFilter = null;
let muted = false;

function noiseBuffer(seconds, brown) {
  const length = Math.floor(ctx.sampleRate * seconds);
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  let last = 0;
  for (let i = 0; i < length; i++) {
    const white = Math.random() * 2 - 1;
    if (brown) {
      last = (last + 0.02 * white) / 1.02;
      data[i] = last * 3.5;
    } else {
      data[i] = white;
    }
  }
  return buffer;
}

let brownBuffer = null;
let whiteBuffer = null;

function source(buffer, loop) {
  const s = ctx.createBufferSource();
  s.buffer = buffer;
  s.loop = loop;
  return s;
}

export const synth = {
  get ready() {
    return ctx !== null;
  },
  setMuted(value) {
    muted = value;
    if (master) master.gain.setTargetAtTime(muted ? 0 : 0.8, ctx.currentTime, 0.08);
  },
  // Starts the audio graph and the sea bed; called from a tap or a key so the browser lets it play.
  wake() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return;
    ctx = new Ctor();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.8;
    master.connect(ctx.destination);
    brownBuffer = noiseBuffer(4, true);
    whiteBuffer = noiseBuffer(2, false);

    const sea = source(brownBuffer, true);
    const seaFilter = ctx.createBiquadFilter();
    seaFilter.type = "lowpass";
    seaFilter.frequency.value = 420;
    const seaGain = ctx.createGain();
    seaGain.gain.value = 0.22;
    const swell = ctx.createOscillator();
    swell.frequency.value = 0.11;
    const swellDepth = ctx.createGain();
    swellDepth.gain.value = 0.12;
    swell.connect(swellDepth).connect(seaGain.gain);
    sea.connect(seaFilter).connect(seaGain).connect(master);
    sea.start();
    swell.start();

    const burn = source(whiteBuffer, true);
    burnFilter = ctx.createBiquadFilter();
    burnFilter.type = "bandpass";
    burnFilter.frequency.value = 300;
    burnFilter.Q.value = 1.4;
    burnGain = ctx.createGain();
    burnGain.gain.value = 0;
    burn.connect(burnFilter).connect(burnGain).connect(master);
    burn.start();
  },
  suspend() {
    if (ctx && ctx.state === "running") ctx.suspend();
  },
  resume() {
    if (ctx && ctx.state === "suspended") ctx.resume();
  },
  // The burn rises in pitch as the ring fills; zero when no ship is held.
  burn(level) {
    if (!ctx) return;
    const t = ctx.currentTime;
    burnGain.gain.setTargetAtTime(level > 0 ? 0.05 + level * 0.12 : 0, t, 0.06);
    burnFilter.frequency.setTargetAtTime(280 + level * 1900, t, 0.08);
  },
  foghorn() {
    if (!ctx) return;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    osc.type = "square";
    osc.frequency.setValueAtTime(58, t);
    osc.frequency.linearRampToValueAtTime(55, t + 2.4);
    const low = ctx.createBiquadFilter();
    low.type = "lowpass";
    low.frequency.value = 260;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.16, t + 0.7);
    g.gain.setValueAtTime(0.16, t + 1.6);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 3.0);
    osc.connect(low).connect(g).connect(master);
    osc.start(t);
    osc.stop(t + 3.1);
  },
  turned() {
    if (!ctx) return;
    const t = ctx.currentTime;
    const s = source(whiteBuffer, false);
    const f = ctx.createBiquadFilter();
    f.type = "bandpass";
    f.frequency.setValueAtTime(2400, t);
    f.frequency.exponentialRampToValueAtTime(500, t + 1.2);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.22, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 1.3);
    s.connect(f).connect(g).connect(master);
    s.start(t);
    s.stop(t + 1.4);
  },
  thunder(delay = 0.35) {
    if (!ctx) return;
    const t = ctx.currentTime + delay;
    const s = source(brownBuffer, false);
    const low = ctx.createBiquadFilter();
    low.type = "lowpass";
    low.frequency.setValueAtTime(900, t);
    low.frequency.exponentialRampToValueAtTime(70, t + 3.2);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.9, t + 0.08);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 3.8);
    s.connect(low).connect(g).connect(master);
    s.start(t);
    s.stop(t + 3.9);
  },
  flare() {
    if (!ctx) return;
    const t = ctx.currentTime;
    const s = source(whiteBuffer, false);
    const f = ctx.createBiquadFilter();
    f.type = "highpass";
    f.frequency.setValueAtTime(400, t);
    f.frequency.exponentialRampToValueAtTime(5000, t + 0.6);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.3, t + 0.12);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 1.6);
    s.connect(f).connect(g).connect(master);
    s.start(t);
    s.stop(t + 1.7);
  },
  wreck() {
    if (!ctx) return;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(90, t);
    osc.frequency.exponentialRampToValueAtTime(36, t + 0.9);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.5, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 1.1);
    osc.connect(g).connect(master);
    osc.start(t);
    osc.stop(t + 1.2);
    this.thunder(0);
  },
  dawn() {
    if (!ctx) return;
    const t = ctx.currentTime;
    for (const [i, hz] of [261.63, 329.63, 392.0, 523.25].entries()) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = hz;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.07, t + 0.8 + i * 0.25);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 5.5);
      osc.connect(g).connect(master);
      osc.start(t);
      osc.stop(t + 5.6);
    }
  },
};
