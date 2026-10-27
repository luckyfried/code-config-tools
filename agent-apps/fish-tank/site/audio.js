// Sound: the water bed under everything, a plop for food, a chime for pearls, and the lamp's hum at night.
// The samples load on the first tap or key, since browsers keep audio closed until then.
const FILES = { bed: "sound/water-bed.wav", plop: "sound/plop.wav", chime: "sound/chime.wav", hum: "sound/hum.wav" };

export function createAudio() {
  let ctx = null;
  let master = null;
  let humGain = null;
  let bedGain = null;
  const buffers = {};
  let on = true;
  let ready = null;
  let lastChime = 0;

  async function start() {
    if (ready) return ready;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = on ? 1 : 0;
    master.connect(ctx.destination);
    ready = Promise.all(Object.entries(FILES).map(async ([name, url]) => {
      const res = await fetch(url);
      buffers[name] = await ctx.decodeAudioData(await res.arrayBuffer());
    })).then(() => {
      bedGain = ctx.createGain();
      bedGain.gain.value = 0.16;
      bedGain.connect(master);
      loop("bed", bedGain);
      humGain = ctx.createGain();
      humGain.gain.value = 0;
      humGain.connect(master);
      loop("hum", humGain);
    }).catch(() => {});
    return ready;
  }

  function loop(name, gain) {
    const src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.loop = true;
    src.connect(gain);
    src.start();
  }

  function play(name, volume, rate = 1) {
    if (!ctx || !buffers[name] || !on) return;
    const src = ctx.createBufferSource();
    src.buffer = buffers[name];
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = volume;
    src.connect(g).connect(master);
    src.start();
  }

  return {
    start,
    unlock() {
      start();
      if (ctx && ctx.state === "suspended") ctx.resume();
    },
    setOn(value) {
      on = value;
      if (master) master.gain.setTargetAtTime(on ? 1 : 0, ctx.currentTime, 0.05);
    },
    plop() { play("plop", 0.5, 0.9 + Math.random() * 0.25); },
    chime(soft) {
      const now = performance.now();
      if (now - lastChime < 90) return;
      lastChime = now;
      const steps = [1, 1.122, 1.26, 1.335, 1.498];
      play("chime", soft ? 0.12 : 0.3, steps[Math.floor(Math.random() * steps.length)] * (soft ? 0.75 : 1));
    },
    lamp(level) {
      if (humGain) humGain.gain.setTargetAtTime(level * 0.05, ctx.currentTime, 0.4);
    },
  };
}
