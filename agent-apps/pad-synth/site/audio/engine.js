// The audio graph and the live synth. The same graph is built inside an OfflineAudioContext to render loops and
// exports, so a WAV sounds exactly like what was played.
//
//   voices -> bus -> master -> limiter -> analyser -> speakers
//              \--> send -> feedback-delay reverb --/
import * as pluck from "./pluck.js";
import * as pad from "./pad.js";
import * as bass from "./bass.js";
import * as keys from "./keys.js";
import { frequency } from "../music/scales.js";

export const VOICES = { pluck, pad, bass, keys };
export const POLYPHONY = 8;

/** Four delay lines mixed through a Householder matrix, each damped by a lowpass: a smooth, dense tail. */
function reverb(ctx) {
  const input = ctx.createGain();
  const output = ctx.createGain();
  output.gain.value = 0.55;
  const pre = ctx.createDelay(0.2);
  pre.delayTime.value = 0.021;
  const tone = ctx.createBiquadFilter();
  tone.type = "highpass";
  tone.frequency.value = 220;
  input.connect(tone).connect(pre);

  const times = [0.0831, 0.1093, 0.1297, 0.1511];
  const feedback = 0.84;
  const merge = ctx.createChannelMerger(2);
  const lines = times.map((time) => {
    const delay = ctx.createDelay(1);
    delay.delayTime.value = time;
    const damp = ctx.createBiquadFilter();
    damp.type = "lowpass";
    damp.frequency.value = 4800;
    pre.connect(delay);
    delay.connect(damp);
    return { delay, damp };
  });
  lines.forEach((from, i) => {
    lines.forEach((to, j) => {
      const mix = ctx.createGain();
      mix.gain.value = (i === j ? 0.5 : -0.5) * feedback;
      from.damp.connect(mix).connect(to.delay);
    });
    from.damp.connect(merge, 0, i % 2);
  });
  merge.connect(output);
  return { input, output };
}

/** Straight up to 0.8, then bending toward 0.98: input from -2 to 2 arrives here halved, as -1 to 1. */
function ceilingCurve(size = 2048) {
  const curve = new Float32Array(size);
  for (let i = 0; i < size; i += 1) {
    const x = ((i / (size - 1)) * 2 - 1) * 2;
    const a = Math.abs(x);
    const y = a < 0.8 ? a : 0.8 + 0.18 * Math.tanh((a - 0.8) / 0.18);
    curve[i] = Math.sign(x) * y;
  }
  return curve;
}

export function buildGraph(ctx) {
  const bus = ctx.createGain();
  const master = ctx.createGain();
  master.gain.value = 0.8;
  bus.connect(master);

  const send = ctx.createGain();
  send.gain.value = 0.32;
  const room = reverb(ctx);
  bus.connect(send).connect(room.input);
  room.output.connect(master);

  const limiter = ctx.createDynamicsCompressor();
  limiter.threshold.value = -4;
  limiter.knee.value = 2;
  limiter.ratio.value = 20;
  limiter.attack.value = 0.002;
  limiter.release.value = 0.15;
  master.connect(limiter);

  // The limiter's attack lets the first milliseconds of a strike through; the ceiling rounds them off below full scale.
  const into = ctx.createGain();
  into.gain.value = 0.5;
  const ceiling = ctx.createWaveShaper();
  ceiling.curve = ceilingCurve();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.72;
  limiter.connect(into).connect(ceiling).connect(analyser);
  analyser.connect(ctx.destination);
  return { bus, master, analyser };
}

export function createVoices(ctx) {
  const made = {};
  for (const [name, module] of Object.entries(VOICES)) made[name] = module.create(ctx);
  return made;
}

/** The note a voice sounds for a grid note: each voice sits in its own octave. */
export function voiceFrequency(voice, midi) {
  return frequency(midi + 12 * VOICES[voice].octave);
}

/**
 * The live synth: an AudioContext made on the first tap, eight voices for the pads (the oldest note gives way to
 * a ninth), and one-shot notes for the step ring and the loop recorder's playback.
 */
export class Synth {
  constructor() {
    this.ctx = null;
    this.graph = null;
    this.voices = null;
    this.held = new Map();
  }

  get running() {
    return this.ctx !== null && this.ctx.state === "running";
  }

  get now() {
    return this.ctx ? this.ctx.currentTime : 0;
  }

  /** Seconds from scheduling to sound, for lining the light up with the sound. */
  get latency() {
    if (!this.ctx) return 0;
    return (this.ctx.outputLatency || 0) + (this.ctx.baseLatency || 0);
  }

  /** Starts sound; call from inside a tap or key press. */
  start() {
    if (!this.ctx) {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return false;
      this.ctx = new Context({ latencyHint: "interactive" });
      this.graph = buildGraph(this.ctx);
      this.voices = createVoices(this.ctx);
    }
    if (this.ctx.state !== "running") this.ctx.resume();
    return true;
  }

  prepare(freqs) {
    if (this.voices) this.voices.pluck.prepare(freqs);
  }

  noteOn(id, voice, midi, velocity) {
    if (!this.ctx) return;
    this.noteOff(id);
    if (this.held.size >= POLYPHONY) {
      const [oldest] = this.held.keys();
      this.noteOff(oldest);
    }
    const time = this.ctx.currentTime;
    const handle = this.voices[voice].play(voiceFrequency(voice, midi), time, velocity, this.graph.bus);
    this.held.set(id, handle);
  }

  noteOff(id) {
    const handle = this.held.get(id);
    if (!handle) return;
    this.held.delete(id);
    handle.stop(this.ctx.currentTime);
  }

  releaseAll() {
    for (const id of [...this.held.keys()]) this.noteOff(id);
  }

  /** A scheduled note with a known length, for the ring. */
  schedule(voice, midi, velocity, time, length) {
    if (!this.ctx) return;
    const handle = this.voices[voice].play(voiceFrequency(voice, midi), time, velocity, this.graph.bus);
    handle.stop(time + length);
  }
}
