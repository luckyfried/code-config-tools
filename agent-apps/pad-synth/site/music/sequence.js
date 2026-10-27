// The step ring: sixteen steps a bar, one lane per voice, each lit step holding a scale degree. Steps are
// scheduled a little ahead of the clock they run on: the audio clock once sound has started, the page's own clock
// before, so the ring plays and lights the field even while the browser keeps sound off.
import { SCALES } from "./scales.js";

export const STEPS = 16;
/** How long each voice's step note lasts, in steps. */
export const GATES = { pluck: 1, keys: 1.5, bass: 1.6, pad: 7.5 };
export const VELOCITY = { pluck: 0.72, keys: 0.6, bass: 0.86, pad: 0.5 };
export const LANE_ORDER = ["pluck", "keys", "pad", "bass"];

/** The scale degree nearest `semitones` above the root (3.5 picks whichever third the scale has). */
export function degreeNear(semitones, scaleId) {
  const steps = SCALES[scaleId].steps;
  const octave = Math.floor(semitones / 12);
  const within = semitones - octave * 12;
  let best = 0;
  for (let i = 1; i < steps.length; i += 1) {
    if (Math.abs(steps[i] - within) < Math.abs(steps[best] - within)) best = i;
  }
  return octave * steps.length + best;
}

const DEMO = {
  bass: { 0: 0, 3: 0, 6: 12, 8: 0, 10: 7, 11: 0, 14: 10 },
  pluck: { 0: 0, 2: 7, 3: 3.5, 5: 12, 7: 7, 8: 2, 10: 3.5, 12: 7, 13: 12, 15: 10 },
  keys: { 2: 7, 6: 10, 10: 7, 14: 3.5 },
  pad: { 0: 3.5, 8: 7 },
};

export function demoLanes(scaleId) {
  const lanes = {};
  for (const voice of LANE_ORDER) {
    lanes[voice] = Array(STEPS).fill(null);
    for (const [step, semitones] of Object.entries(DEMO[voice])) {
      lanes[voice][Number(step)] = { degree: degreeNear(semitones, scaleId) };
    }
  }
  return lanes;
}

export function emptyLanes() {
  const lanes = {};
  for (const voice of LANE_ORDER) lanes[voice] = Array(STEPS).fill(null);
  return lanes;
}

export class Sequencer {
  constructor({ bpm, lanes, onStep }) {
    this.bpm = bpm;
    this.lanes = lanes;
    this.onStep = onStep;
    this.playing = false;
    this.step = 0;
    this.next = 0;
  }

  get stepSeconds() {
    return 60 / this.bpm / 4;
  }

  start(now) {
    this.playing = true;
    this.step = 0;
    this.next = now + 0.06;
  }

  stop() {
    this.playing = false;
  }

  /** Moves to another clock, keeping the step it is on. */
  rebase(now) {
    this.next = now + 0.06;
  }

  /** Schedules every step that falls before `now + ahead`. */
  tick(now, ahead) {
    if (!this.playing) return;
    if (this.next < now - 0.25) this.next = now + 0.02;
    while (this.next < now + ahead) {
      this.onStep(this.step, this.next, this.stepSeconds);
      this.next += this.stepSeconds;
      this.step = (this.step + 1) % STEPS;
    }
  }
}

/** Notes as they are heard, kept from the press of Record to its second press. */
export class Recorder {
  constructor() {
    this.active = false;
    this.notes = [];
    this.open = new Map();
    this.start = 0;
  }

  begin(now) {
    this.active = true;
    this.notes = [];
    this.open.clear();
    this.start = now;
  }

  noteOn(id, voice, midi, velocity, now) {
    if (!this.active) return;
    this.open.set(id, { voice, midi, velocity, time: now - this.start });
  }

  noteOff(id, now) {
    const note = this.open.get(id);
    if (!note) return;
    this.open.delete(id);
    this.notes.push({ ...note, length: Math.max(0.03, now - this.start - note.time) });
  }

  note(voice, midi, velocity, time, length) {
    if (!this.active || time < this.start) return;
    this.notes.push({ voice, midi, velocity, time: time - this.start, length });
  }

  /** Ends the take: whole bars from the first press, each note inside them. */
  end(now, bpm) {
    for (const id of [...this.open.keys()]) this.noteOff(id, now);
    this.active = false;
    const bar = (60 / bpm) * 4;
    const bars = Math.min(8, Math.max(1, Math.round((now - this.start) / bar)));
    const seconds = bars * bar;
    const notes = this.notes
      .filter((note) => note.time < seconds)
      .map((note) => ({ ...note, time: round(note.time), length: round(Math.min(note.length, seconds)) }))
      .sort((a, b) => a.time - b.time);
    return { notes, bars, seconds };
  }
}

function round(value) {
  return Math.round(value * 10000) / 10000;
}
