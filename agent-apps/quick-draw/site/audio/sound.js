// Plays the baked sounds under audio/. The files are fetched at load; the audio context starts on the first tap or
// key, as browsers require, and the wind bed loops under everything from then on.
import { SOUND_NAMES } from "./synth.js";

export function createSound({ muted = false } = {}) {
  const bytes = new Map();
  const buffers = new Map();
  let ctx = null;
  let master = null;
  let windGain = null;
  let isMuted = muted;

  const loading = Promise.all(
    SOUND_NAMES.map(async (name) => {
      try {
        const res = await fetch(`./audio/${name}.wav`);
        if (res.ok) bytes.set(name, await res.arrayBuffer());
      } catch {
        // a missing sound leaves the duel silent, never broken
      }
    }),
  );

  async function unlock() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC({ latencyHint: "interactive" });
    master = ctx.createGain();
    master.gain.value = isMuted ? 0 : 0.9;
    master.connect(ctx.destination);
    await loading;
    await Promise.all(
      [...bytes].map(async ([name, data]) => {
        try {
          buffers.set(name, await ctx.decodeAudioData(data.slice(0)));
        } catch {
          // undecodable: skip it
        }
      }),
    );
    startWind();
  }

  function startWind() {
    const buf = buffers.get("wind");
    if (!buf || windGain) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    windGain = ctx.createGain();
    windGain.gain.value = 0;
    windGain.gain.setTargetAtTime(0.32, ctx.currentTime, 1.2);
    src.connect(windGain).connect(master);
    src.start();
  }

  function play(name, { gain = 1, rate = 1, delay = 0, pan = 0 } = {}) {
    if (!ctx || isMuted) return;
    const buf = buffers.get(name);
    if (!buf) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = gain;
    let node = src.connect(g);
    if (pan && ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = pan;
      node = node.connect(p);
    }
    node.connect(master);
    src.start(ctx.currentTime + delay);
  }

  return {
    unlock,
    play,
    /** Ducks the wind under the slow motion and brings it back. */
    wind(level, seconds = 0.3) {
      if (windGain) windGain.gain.setTargetAtTime(level, ctx.currentTime, seconds);
    },
    get muted() {
      return isMuted;
    },
    setMuted(on) {
      isMuted = on;
      if (master) master.gain.setTargetAtTime(on ? 0 : 0.9, ctx.currentTime, 0.05);
    },
  };
}
