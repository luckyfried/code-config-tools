// Sound: the rendered WAV files played through Web Audio. The rotor loop runs through a lowpass and a pitch that
// follow the throttle; rain hisses underneath; thunder, the chime, the pickup, and the crash are one-shots.
const FILES = ["rotor", "rain", "thunder", "chime", "pickup", "crash"];
const MUTE_KEY = "rain-courier:muted";

export function createSound() {
  let ctx = null;
  let master = null;
  let buffers = null;
  let rotor = null;
  let muted = localStorage.getItem(MUTE_KEY) === "1";
  let loading = null;

  async function start() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    ctx = new Ctx();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.8;
    master.connect(ctx.destination);
    loading = Promise.all(
      FILES.map((name) =>
        fetch(`./audio/${name}.wav`)
          .then((r) => r.arrayBuffer())
          .then((b) => ctx.decodeAudioData(b))
          .then((buffer) => [name, buffer]),
      ),
    )
      .then((list) => {
        buffers = Object.fromEntries(list);
        startLoops();
      })
      .catch(() => {
        buffers = null;
      });
  }

  function startLoops() {
    const rain = ctx.createBufferSource();
    rain.buffer = buffers.rain;
    rain.loop = true;
    const rainGain = ctx.createGain();
    rainGain.gain.value = 0.32;
    rain.connect(rainGain).connect(master);
    rain.start();

    const source = ctx.createBufferSource();
    source.buffer = buffers.rotor;
    source.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 600;
    filter.Q.value = 0.9;
    const gain = ctx.createGain();
    gain.gain.value = 0.18;
    source.connect(filter).connect(gain).connect(master);
    source.start();
    rotor = { source, filter, gain };
  }

  function play(name, { volume = 1, rate = 1, delay = 0 } = {}) {
    if (!ctx || !buffers || !buffers[name]) return;
    const s = ctx.createBufferSource();
    s.buffer = buffers[name];
    s.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = volume;
    s.connect(g).connect(master);
    s.start(ctx.currentTime + delay);
  }

  return {
    start,
    get muted() {
      return muted;
    },
    setMuted(value) {
      muted = value;
      localStorage.setItem(MUTE_KEY, value ? "1" : "0");
      if (master) master.gain.setTargetAtTime(value ? 0 : 0.8, ctx.currentTime, 0.05);
    },
    throttle(t, near) {
      if (!rotor) return;
      const now = ctx.currentTime;
      rotor.filter.frequency.setTargetAtTime(500 + t * 2600 + near * 800, now, 0.08);
      rotor.source.playbackRate.setTargetAtTime(0.9 + t * 0.35, now, 0.1);
      rotor.gain.gain.setTargetAtTime(0.14 + t * 0.12, now, 0.1);
    },
    thunder(delay) {
      play("thunder", { volume: 0.9, delay, rate: 0.9 + Math.random() * 0.2 });
    },
    chime() {
      play("chime", { volume: 0.7 });
    },
    pickup() {
      play("pickup", { volume: 0.6 });
    },
    crash(strength = 1) {
      play("crash", { volume: Math.min(1, 0.5 + strength * 0.5), rate: 0.9 + Math.random() * 0.2 });
    },
    whoosh() {
      play("pickup", { volume: 0.25, rate: 0.55 });
    },
    suspend() {
      if (ctx && ctx.state === "running") ctx.suspend();
    },
    resume() {
      if (ctx && ctx.state === "suspended") ctx.resume();
    },
    ready: () => loading,
  };
}
