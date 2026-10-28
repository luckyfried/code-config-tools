// The game's sounds: WAV files rendered ahead of time, played through Web Audio once the person first touches
// or types, since a page may not make sound before that.

const NAMES = ["thunk", "key", "buzz", "chime"];

export function createAudio() {
  let ctx = null;
  let enabled = true;
  const buffers = {};

  function unlock() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    ctx = new Ctx();
    for (const name of NAMES) {
      fetch(`./sound/${name}.wav`)
        .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(name))))
        .then((data) => ctx.decodeAudioData(data))
        .then((buffer) => {
          buffers[name] = buffer;
        })
        .catch(() => {});
    }
  }

  function play(name, { rate = 1, gain = 1 } = {}) {
    if (!enabled || !ctx || ctx.state !== "running" || !buffers[name]) return;
    const source = ctx.createBufferSource();
    source.buffer = buffers[name];
    source.playbackRate.value = rate;
    const level = ctx.createGain();
    level.gain.value = gain;
    source.connect(level).connect(ctx.destination);
    source.start();
  }

  return {
    unlock,
    play,
    setEnabled(on) {
      enabled = on;
    },
  };
}
