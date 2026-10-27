// The disc sounds: a lacquer tick for each disc that lands, its pitch rising along the wave, and a deeper knock for a
// placed disc. Web Audio starts on the first tap or key, as browsers require.
export function createAudio({ enabled = true } = {}) {
  let ctx = null;
  let buffers = null;
  let on = enabled;
  let lastTick = 0;

  async function unlock() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    ctx = new AudioContext();
    const load = async (url) => ctx.decodeAudioData(await (await fetch(url)).arrayBuffer());
    try {
      const [tick, place] = await Promise.all([load("./sound/tick.wav"), load("./sound/place.wav")]);
      buffers = { tick, place };
    } catch (error) {
      buffers = null;
    }
  }

  function play(buffer, rate, gain) {
    if (!on || !ctx || !buffers || ctx.state !== "running") return;
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = gain;
    source.connect(g).connect(ctx.destination);
    source.start();
  }

  /** `kind` is tick, place, or pass; `index` is the disc's place along its wave. */
  function sound(kind, index = 0, pace = 1) {
    if (!buffers) return;
    const now = performance.now();
    if (kind === "tick") {
      // In a fast replay the ticks would blur into a buzz; keep one in every few.
      if (pace < 1 && now - lastTick < 70) return;
      lastTick = now;
      play(buffers.tick, Math.min(2.2, 0.92 + index * 0.075), pace < 1 ? 0.35 : 0.6);
    } else if (kind === "place") {
      play(buffers.place, 1, pace < 1 ? 0.3 : 0.8);
    } else if (kind === "pass") {
      play(buffers.place, 0.62, 0.7);
      setTimeout(() => play(buffers.place, 0.58, 0.5), 110);
    }
  }

  return {
    unlock,
    sound,
    setEnabled(value) {
      on = value;
    },
    get enabled() {
      return on;
    },
  };
}
