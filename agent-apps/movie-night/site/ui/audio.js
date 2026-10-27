// The wheel's sound: a short click for each tooth that passes the pointer and a two-note chime when it settles.
// The audio context starts on the first tap or key press, as browsers require.

let ctx = null;
let noise = null;
let last = 0;

export function unlockAudio() {
  try {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ctx = new AC();
      const len = Math.floor(ctx.sampleRate * 0.03);
      noise = ctx.createBuffer(1, len, ctx.sampleRate);
      const d = noise.getChannelData(0);
      for (let i = 0; i < len; i += 1) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 4);
    }
    if (ctx.state === "suspended") ctx.resume();
  } catch {
    ctx = null;
  }
}

export function tick(strength = 1) {
  if (!ctx || ctx.state !== "running") return;
  const now = ctx.currentTime;
  if (now - last < 0.024) return;
  last = now;
  const src = ctx.createBufferSource();
  src.buffer = noise;
  const band = ctx.createBiquadFilter();
  band.type = "bandpass";
  band.frequency.value = 2400 + Math.random() * 500;
  band.Q.value = 3.5;
  const g = ctx.createGain();
  g.gain.value = 0.28 * strength;
  src.connect(band).connect(g).connect(ctx.destination);
  src.start(now);
  const o = ctx.createOscillator();
  o.type = "triangle";
  o.frequency.value = 1500 + Math.random() * 120;
  const og = ctx.createGain();
  og.gain.setValueAtTime(0.06 * strength, now);
  og.gain.exponentialRampToValueAtTime(0.0001, now + 0.045);
  o.connect(og).connect(ctx.destination);
  o.start(now);
  o.stop(now + 0.05);
}

export function chime() {
  if (!ctx || ctx.state !== "running") return;
  const now = ctx.currentTime;
  [1046.5, 1568].forEach((f, i) => {
    const o = ctx.createOscillator();
    o.type = "sine";
    o.frequency.value = f;
    const g = ctx.createGain();
    const at = now + i * 0.11;
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.16, at + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 1.1);
    o.connect(g).connect(ctx.destination);
    o.start(at);
    o.stop(at + 1.2);
  });
}
