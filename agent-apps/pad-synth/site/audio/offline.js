// Offline rendering: notes played through the same graph inside an OfflineAudioContext, faster than real time.
import { buildGraph, createVoices, voiceFrequency } from "./engine.js";

export const RATE = 44100;

/**
 * Renders `notes` ({time, length, voice, midi, velocity}, seconds from the start) into an AudioBuffer `seconds`
 * long. With `loop`, the reverb and release tail that runs past the end is folded back onto the start, so the
 * buffer plays round without a gap or a click.
 */
export async function render(notes, seconds, { loop = true, tail = 3, rate = RATE } = {}) {
  const frames = Math.ceil((seconds + tail) * rate);
  const ctx = new OfflineAudioContext(2, frames, rate);
  const graph = buildGraph(ctx);
  const voices = createVoices(ctx);
  for (const note of notes) {
    if (!(note.voice in voices) || note.time >= seconds + tail) continue;
    const handle = voices[note.voice].play(voiceFrequency(note.voice, note.midi), note.time, note.velocity, graph.bus);
    handle.stop(note.time + note.length);
  }
  const rendered = await ctx.startRendering();
  if (!loop) return rendered;

  const length = Math.max(1, Math.round(seconds * rate));
  const folded = new AudioBuffer({ length, numberOfChannels: 2, sampleRate: rate });
  let top = 0;
  for (let c = 0; c < 2; c += 1) {
    const from = rendered.getChannelData(c);
    const to = folded.getChannelData(c);
    to.set(from.subarray(0, length));
    for (let i = length; i < from.length; i += 1) to[(i - length) % length] += from[i];
    for (let i = 0; i < length; i += 1) top = Math.max(top, Math.abs(to[i]));
  }
  if (top > 0.98) {
    const scale = 0.98 / top;
    for (let c = 0; c < 2; c += 1) {
      const to = folded.getChannelData(c);
      for (let i = 0; i < length; i += 1) to[i] *= scale;
    }
  }
  return folded;
}

export function peakOf(buffer) {
  let top = 0;
  for (let c = 0; c < buffer.numberOfChannels; c += 1) {
    const data = buffer.getChannelData(c);
    for (let i = 0; i < data.length; i += 1) top = Math.max(top, Math.abs(data[i]));
  }
  return top;
}

/** A small picture of a buffer: `points` peak levels from 0 to 1. */
export function outline(buffer, points = 96) {
  const data = buffer.getChannelData(0);
  const size = Math.max(1, Math.floor(data.length / points));
  const shape = [];
  for (let p = 0; p < points; p += 1) {
    let top = 0;
    for (let i = p * size; i < (p + 1) * size && i < data.length; i += 1) top = Math.max(top, Math.abs(data[i]));
    shape.push(Math.round(top * 1000) / 1000);
  }
  return shape;
}
