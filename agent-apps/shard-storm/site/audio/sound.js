// Plays the sounds scripts/sounds.py rendered offline into this folder. Nothing is synthesized live: the files are
// fetched and decoded on the first tap (when the AudioContext may start), then played as buffers. The drone loops and
// rises a semitone per wave; the graze blip rises with the multiplier.
import { load, save } from "../game/storage.js";

const FILES = ["drone", "graze", "wave", "death", "start", "clear", "tick"];

export function createSound() {
  let ctx = null;
  let master = null;
  let drone = null;
  let droneGain = null;
  let droneStep = 0;
  let wantDrone = false;
  let muted = load("muted", false);
  const buffers = {};

  async function decode() {
    await Promise.all(
      FILES.map(async (name) => {
        try {
          const response = await fetch(`./audio/${name}.wav`);
          buffers[name] = await ctx.decodeAudioData(await response.arrayBuffer());
        } catch {
          // A sound that cannot load stays silent; the game plays on.
        }
      }),
    );
    if (wantDrone) startDrone();
  }

  function startDrone() {
    if (!ctx || !buffers.drone || drone) return;
    drone = ctx.createBufferSource();
    drone.buffer = buffers.drone;
    drone.loop = true;
    drone.playbackRate.value = Math.pow(2, droneStep / 12);
    droneGain = ctx.createGain();
    droneGain.gain.value = 0;
    droneGain.gain.setTargetAtTime(0.32, ctx.currentTime, 0.4);
    drone.connect(droneGain).connect(master);
    drone.start();
  }

  return {
    get muted() {
      return muted;
    },
    unlock() {
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
      decode();
    },
    setMuted(value) {
      muted = value;
      save("muted", muted);
      if (master) master.gain.setTargetAtTime(muted ? 0 : 0.8, ctx.currentTime, 0.03);
    },
    play(name, rate = 1, gain = 1) {
      if (!ctx || !buffers[name] || muted) return;
      const src = ctx.createBufferSource();
      src.buffer = buffers[name];
      src.playbackRate.value = rate;
      const g = ctx.createGain();
      g.gain.value = gain;
      src.connect(g).connect(master);
      src.start();
    },
    droneOn(step) {
      wantDrone = true;
      this.droneTo(step);
      startDrone();
    },
    droneTo(step) {
      droneStep = step;
      if (drone) drone.playbackRate.setTargetAtTime(Math.pow(2, step / 12), ctx.currentTime, 0.25);
    },
    droneOff() {
      wantDrone = false;
      if (!drone) return;
      const d = drone;
      droneGain.gain.setTargetAtTime(0, ctx.currentTime, 0.25);
      setTimeout(() => d.stop(), 1200);
      drone = null;
    },
  };
}
