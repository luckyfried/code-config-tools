// The end-of-block chime: two sine partials with a 400 ms decay, made with Web Audio.
let ctx = null;

// Browsers start audio only from a gesture, so the first tap or key press opens the context.
export function unlockAudio() {
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  if (!ctx) ctx = new AC();
  if (ctx.state === "suspended") ctx.resume().catch(() => {});
}

export function chime() {
  if (!ctx || ctx.state !== "running") return;
  const t = ctx.currentTime + 0.02;
  const out = ctx.createGain();
  out.gain.value = 0.9;
  out.connect(ctx.destination);
  for (const [freq, level] of [[659.25, 0.32], [987.77, 0.18]]) {
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(level, t + 0.008);
    env.gain.exponentialRampToValueAtTime(0.0001, t + 0.4);
    osc.connect(env).connect(out);
    osc.start(t);
    osc.stop(t + 0.45);
  }
}
