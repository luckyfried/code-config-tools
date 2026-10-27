// Pad Synth: the grid, the voices, the step ring, the loops, and the light they make.
import { SCALES, keyIndex, keyLabel, midiOf, noteName } from "./music/scales.js";
import { GATES, LANE_ORDER, Recorder, STEPS, Sequencer, VELOCITY, degreeNear, demoLanes, emptyLanes } from "./music/sequence.js";
import { Synth, VOICES, voiceFrequency } from "./audio/engine.js";
import { outline, peakOf, render } from "./audio/offline.js";
import { encodeWav } from "./audio/wav.js";
import { Sources } from "./scene/sources.js";
import { createField } from "./scene/field.js";
import { pickTier } from "./scene/quality.js";
import { cssRgb, pitchColor, readTokens } from "./scene/color.js";
import { Grid } from "./ui/grid.js";
import { Scope } from "./ui/scope.js";
import { Ring } from "./ui/ring.js";
import { LoopList } from "./ui/loops.js";
import { download, loadState, loops as loopStore, saveState } from "./store/store.js";

const KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const VOICE_IDS = ["pluck", "pad", "bass", "keys"];
const CHORDS = [
  [0, 2, 4],
  [2, 4, 6],
  [6, 8, 10],
  [3, 5, 7],
];

const $ = (id) => document.getElementById(id);
const vnow = () => performance.now() / 1000;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const wideQuery = window.matchMedia("(min-width: 640px) and (min-aspect-ratio: 1/1)");

function readConfig(raw) {
  const voices = Array.isArray(raw.voices) ? raw.voices.filter((v) => VOICE_IDS.includes(v)) : [];
  return {
    name: typeof raw.name === "string" && raw.name.trim() ? raw.name.trim() : "Pad Synth",
    scale: raw.scale in SCALES ? raw.scale : "dorian",
    key: KEY_NAMES[keyIndex(typeof raw.key === "string" ? raw.key : "D")],
    voices: voices.length ? voices : VOICE_IDS.slice(),
    grid: raw.grid === "6x10" ? "6x10" : "5x8",
    bpm: Number.isInteger(raw.bpm) ? Math.min(200, Math.max(50, raw.bpm)) : 104,
  };
}

const config = readConfig(window.__APP_CONFIG__ || {});
const signature = JSON.stringify(config);
const saved = loadState();
const state =
  saved && saved.from === signature
    ? saved
    : {
        from: signature,
        scale: config.scale,
        key: config.key,
        voice: config.voices.includes("pad") ? "pad" : config.voices[0],
        split: false,
        splitVoices: [config.voices[0], config.voices[1] || config.voices[0]],
        bpm: config.bpm,
        lanes: demoLanes(config.scale),
        last: {},
      };
let saveTimer = 0;
function persist() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveState(state), 250);
}

const app = $("app");
const synth = new Synth();
const sources = new Sources();
const recorder = new Recorder();
let tokens = readTokens();
const held = new Map();
const queue = [];
const offs = [];
const marks = [];
let noteCount = 0;
let audioClock = false;

document.title = config.name;
$("title").textContent = config.name;

// The light. Without WebGL2 the pads keep their CSS glows and the page its painted wash.
const field = createField($("field"), { tier: pickTier(), reduced });
if (field) field.setPalette(tokens);
else document.documentElement.classList.add("no-gl");

const scope = new Scope($("scope"));
scope.setTokens(tokens);

const colorOf = (midi) => pitchColor(tokens, midi, keyIndex(state.key));

const grid = new Grid($("grid"), {
  onPress: (pad, id, velocity) => press(pad, id, velocity),
  onRelease: (id) => release(id),
  onHalfVoice: (half) => {
    const list = config.voices;
    state.splitVoices[half] = list[(list.indexOf(state.splitVoices[half]) + 1) % list.length];
    layGrid();
    persist();
  },
});

function layGrid() {
  releaseAll();
  grid.configure({
    size: config.grid,
    scale: state.scale,
    key: state.key,
    split: state.split,
    voices: state.split ? state.splitVoices : [state.voice],
    voiceLabel: (voice) => VOICES[voice].label,
    labelFor: (midi, voice) => noteName(midi + 12 * VOICES[voice].octave, state.key),
    colorFor: (midi) => cssRgb(colorOf(midi)),
  });
}

// Playing a pad: sound if it is on, light always, and the recorder when it runs.
function press(pad, id, velocity, fromDemo = false) {
  if (!fromDemo) {
    startSound();
    stopDemo();
  }
  release(id);
  const voice = state.split ? state.splitVoices[pad.half] : state.voice;
  const look = VOICES[voice].look;
  held.set(id, { pad, voice });
  synth.noteOn(id, voice, pad.midi, velocity);
  recorder.noteOn(id, voice, pad.midi, velocity, synth.now);
  const at = grid.centerOf(pad) || { x: 0.5, y: 0.5 };
  sources.add({ id, x: at.x, y: at.y, freq: voiceFrequency(voice, pad.midi), color: colorOf(pad.midi), look, now: vnow(), strength: velocity + 0.15 });
  grid.light(pad, true, look);
  if (!fromDemo) state.last[voice] = pad.degree;
}

function release(id) {
  const note = held.get(id);
  if (!note) return;
  held.delete(id);
  synth.noteOff(id);
  recorder.noteOff(id, synth.now);
  sources.release(id, vnow());
  grid.light(note.pad, false, VOICES[note.voice].look);
}

function releaseAll() {
  for (const id of [...held.keys()]) release(id);
}

// Sound starts on the first tap or key, as browsers ask; until then the ring and the demo chords play as light.
let demo = null;
function startSound() {
  if (synth.ctx) {
    if (synth.ctx.state !== "running") synth.ctx.resume();
    return;
  }
  if (!synth.start()) {
    setStatus("This browser has no Web Audio, so the pads play as light only.");
    return;
  }
  const freqs = grid.pads.map((pad) => voiceFrequency("pluck", pad.midi));
  const warm = () => synth.prepare(freqs);
  if ("requestIdleCallback" in window) requestIdleCallback(warm, { timeout: 1500 });
  else setTimeout(warm, 200);
  setStatus("Hold several pads for a chord, or slide across them to glide.");
}

function startDemo() {
  demo = { index: 0, next: vnow() + 0.12, off: Infinity, keys: [] };
}

function stopDemo() {
  if (!demo) return;
  for (const id of demo.keys) release(id);
  demo = null;
}

function demoTick(now) {
  if (!demo) return;
  if (now >= demo.off) {
    for (const id of demo.keys) release(id);
    demo.keys = [];
    demo.off = Infinity;
  }
  if (now < demo.next) return;
  const voice = state.split ? state.splitVoices[0] : state.voice;
  const shape = chordPads(CHORDS[demo.index % CHORDS.length]);
  shape.forEach((pad, n) => {
    const id = `demo${n}`;
    demo.keys.push(id);
    press(pad, id, 0.8, true);
  });
  demo.index += 1;
  const hold = Math.max(2.4, VOICES[voice].look.attack * 6);
  demo.off = reduced ? Infinity : now + hold;
  demo.next = reduced ? Infinity : now + hold + 0.5;
}

/** A compact chord shape on the grid: the root near the middle, each other note on the pad nearest the root. */
function chordPads(degrees) {
  const root = grid.padFor(degrees[0]);
  if (!root) return [];
  const pads = [root];
  for (const degree of degrees.slice(1)) {
    let best = null;
    let distance = Infinity;
    for (const pad of grid.pads) {
      if (pad.half !== 0 || pad.degree !== degree) continue;
      const d = (pad.i - root.i) ** 2 + (pad.j - root.j) ** 2;
      if (d < distance) {
        best = pad;
        distance = d;
      }
    }
    if (best) pads.push(best);
  }
  return pads;
}

// The ring. It runs on the audio clock once sound is on, and on the page's clock before.
const clockNow = () => (synth.running ? synth.now : vnow());
const toVisual = (time) => (synth.running ? vnow() + (time - synth.now) + synth.latency : time);

function enabledLanes() {
  return LANE_ORDER.filter((voice) => config.voices.includes(voice));
}

const sequencer = new Sequencer({
  bpm: state.bpm,
  lanes: state.lanes,
  onStep(step, time, stepSeconds) {
    const at = toVisual(time);
    marks.push({ step, at, stepSeconds });
    if (marks.length > 8) marks.shift();
    for (const voice of enabledLanes()) {
      const cell = state.lanes[voice][step];
      if (!cell) continue;
      const midi = midiOf(cell.degree, state.scale, state.key, 3);
      const length = GATES[voice] * stepSeconds;
      if (synth.running) synth.schedule(voice, midi, VELOCITY[voice], time, length);
      if (synth.running) recorder.note(voice, midi, VELOCITY[voice], time, length);
      queue.push({ at, voice, midi, degree: cell.degree, step, length });
    }
  },
});

function ringPosition(now) {
  for (let i = marks.length - 1; i >= 0; i -= 1) {
    const mark = marks[i];
    if (mark.at <= now) return (mark.step + Math.min(0.999, (now - mark.at) / mark.stepSeconds)) % STEPS;
  }
  return 0;
}

function playVisible() {
  return wideQuery.matches || app.dataset.screen === "play";
}

function ringVisible() {
  return wideQuery.matches ? app.dataset.side === "seq" : app.dataset.screen === "seq";
}

function drain(now) {
  while (queue.length && queue[0].at <= now) {
    const note = queue.shift();
    const look = VOICES[note.voice].look;
    const pad = playVisible() ? grid.padFor(note.degree) : null;
    let at = pad ? grid.centerOf(pad) : null;
    let strength = 0.62 * VELOCITY[note.voice] + 0.2;
    if (!at && ringVisible()) {
      at = ring.stepPoint(note.voice, note.step);
      strength *= 0.6;
    }
    if (!at) at = { x: 0.5, y: 0.55 };
    noteCount += 1;
    sources.add({
      id: `step${noteCount}`,
      x: at.x,
      y: at.y,
      freq: voiceFrequency(note.voice, note.midi),
      color: colorOf(note.midi),
      look,
      now: note.at,
      strength,
      length: note.length,
    });
    if (pad) {
      grid.light(pad, true, look);
      offs.push({ at: note.at + note.length, pad, look });
    }
    ring.fire(note.voice, note.step);
  }
  for (let i = offs.length - 1; i >= 0; i -= 1) {
    if (offs[i].at <= now) {
      grid.light(offs[i].pad, false, offs[i].look);
      offs.splice(i, 1);
    }
  }
}

const shortQuery = window.matchMedia("(min-width: 640px) and (min-aspect-ratio: 1/1) and (max-height: 560px)");
const ring = new Ring($("ring"), () => document.querySelector(shortQuery.matches ? ".bpm" : ".ring-center"), {
  onToggle(voice, step) {
    const lane = state.lanes[voice];
    if (lane[step]) lane[step] = null;
    else lane[step] = { degree: state.last[voice] ?? defaultDegree(voice) };
    persist();
  },
});
ring.stepPoint = function stepPoint(voice, step) {
  if (!this.geometry) return null;
  const index = this.lanes.indexOf(voice);
  if (index < 0) return null;
  const rect = this.canvas.getBoundingClientRect();
  const { mid } = this.laneRadius(index);
  const angle = -Math.PI / 2 + this.turn + ((step + 0.5) / STEPS) * Math.PI * 2;
  return {
    x: (rect.left + this.geometry.cx + Math.cos(angle) * mid) / window.innerWidth,
    y: (rect.top + this.geometry.cy + Math.sin(angle) * mid) / window.innerHeight,
  };
};
ring.setTokens(tokens);

function defaultDegree(voice) {
  if (voice === "pad") return degreeNear(3.5, state.scale);
  if (voice === "pluck" || voice === "keys") return degreeNear(7, state.scale);
  return 0;
}

function setLanes() {
  ring.setLanes(enabledLanes(), state.lanes);
  sequencer.lanes = state.lanes;
  const list = $("lanes");
  list.replaceChildren(
    ...enabledLanes().map((voice) => {
      const item = document.createElement("li");
      item.dataset.voice = voice;
      item.textContent = VOICES[voice].label;
      return item;
    }),
  );
}

// Controls.
function setStatus(text) {
  $("status").textContent = text;
}

function readout() {
  $("readout").textContent = `${keyLabel(state.key, state.scale)}, ${state.bpm} BPM`;
  $("bpm").textContent = String(state.bpm);
}

function setTransport(on) {
  const button = $("transport");
  button.setAttribute("aria-pressed", on ? "true" : "false");
  button.setAttribute("aria-label", on ? "Stop the ring" : "Play the ring");
}

function toggleRing() {
  if (sequencer.playing) {
    sequencer.stop();
    marks.length = 0;
    setTransport(false);
  } else {
    startSound();
    sequencer.start(clockNow());
    setTransport(true);
  }
}

function buildPickers() {
  const key = $("key");
  key.replaceChildren(
    ...KEY_NAMES.map((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      return option;
    }),
  );
  key.value = state.key;
  key.addEventListener("change", () => {
    state.key = key.value;
    layGrid();
    readout();
    persist();
  });
  const scale = $("scale");
  scale.replaceChildren(
    ...Object.entries(SCALES).map(([id, { label }]) => {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = label;
      return option;
    }),
  );
  scale.value = state.scale;
  scale.addEventListener("change", () => {
    state.scale = scale.value;
    layGrid();
    readout();
    persist();
  });
}

function buildVoices() {
  const group = $("voices");
  const buttons = config.voices.map((voice) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "voice";
    button.dataset.voice = voice;
    button.setAttribute("role", "radio");
    button.textContent = VOICES[voice].label;
    button.addEventListener("click", () => chooseVoice(voice));
    return button;
  });
  group.replaceChildren(...buttons);
  group.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault();
    const at = config.voices.indexOf(state.voice);
    const by = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
    const next = config.voices[(at + by + config.voices.length) % config.voices.length];
    chooseVoice(next);
    group.querySelector(`[data-voice="${next}"]`).focus();
  });
  markVoices();
}

function markVoices() {
  for (const button of $("voices").children) {
    const on = button.dataset.voice === state.voice;
    button.setAttribute("aria-checked", on ? "true" : "false");
    button.tabIndex = on ? 0 : -1;
  }
}

function chooseVoice(voice) {
  state.voice = voice;
  if (state.split) state.splitVoices[0] = voice;
  markVoices();
  layGrid();
  persist();
}

function setScreen(screen) {
  app.dataset.screen = screen;
  if (screen !== "play") app.dataset.side = screen;
  for (const tab of document.querySelectorAll(".tab")) {
    const name = tab.id.replace("tab-", "");
    const selected = wideQuery.matches ? name === app.dataset.side : name === screen;
    tab.setAttribute("aria-selected", selected ? "true" : "false");
    tab.tabIndex = selected ? 0 : -1;
  }
  requestAnimationFrame(() => {
    sizeAll();
    loopList.refresh();
  });
}

function wireTabs() {
  const tabs = [...document.querySelectorAll(".tab")];
  for (const tab of tabs) tab.addEventListener("click", () => setScreen(tab.id.replace("tab-", "")));
  $("app").querySelector(".tabs").addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    const shown = tabs.filter((tab) => tab.offsetParent !== null);
    const at = shown.indexOf(document.activeElement);
    if (at < 0) return;
    const next = shown[(at + (event.key === "ArrowRight" ? 1 : -1) + shown.length) % shown.length];
    next.focus();
    next.click();
  });
}

let clearArmed = 0;
function wireRing() {
  $("transport").addEventListener("click", toggleRing);
  const split = $("split");
  split.setAttribute("aria-pressed", state.split ? "true" : "false");
  split.addEventListener("click", () => {
    state.split = !state.split;
    split.setAttribute("aria-pressed", state.split ? "true" : "false");
    if (state.split) state.splitVoices[0] = state.voice;
    layGrid();
    persist();
    setStatus(state.split ? "Split: two players, one half each. Tap a half's voice to change it." : "One grid again.");
  });
  const tempo = (by) => {
    state.bpm = Math.min(200, Math.max(50, state.bpm + by));
    sequencer.bpm = state.bpm;
    readout();
    persist();
  };
  $("slower").addEventListener("click", (event) => tempo(event.shiftKey ? -10 : -2));
  $("faster").addEventListener("click", (event) => tempo(event.shiftKey ? 10 : 2));
  const clear = $("ring-clear");
  clear.addEventListener("click", () => {
    if (!clearArmed) {
      clear.textContent = "Clear every step?";
      clearArmed = setTimeout(() => {
        clear.textContent = "Clear";
        clearArmed = 0;
      }, 3000);
      return;
    }
    clearTimeout(clearArmed);
    clearArmed = 0;
    clear.textContent = "Clear";
    state.lanes = emptyLanes();
    setLanes();
    persist();
    setStatus("The ring is empty. Tap a step to add a note.");
  });
  $("ring-loop").addEventListener("click", saveRingLoop);
  $("empty-ring").addEventListener("click", saveRingLoop);
  $("ring-json").addEventListener("click", () => {
    const patch = {
      app: config.name,
      kind: "patch",
      key: state.key,
      scale: state.scale,
      bpm: state.bpm,
      voice: state.voice,
      voices: config.voices,
      grid: config.grid,
      ring: Object.fromEntries(enabledLanes().map((voice) => [voice, state.lanes[voice].map((cell) => (cell ? cell.degree : null))])),
    };
    download(new Blob([JSON.stringify(patch, null, 2)], { type: "application/json" }), "pad-synth-patch.json");
    setStatus("The patch and the ring are saved as a JSON file.");
  });
}

// Loops: notes as they were heard, rendered offline through the same voices into a WAV that plays on repeat.
const loopPlayers = new Map();
const loopBuffers = new Map();
let savedLoops = [];
const loopList = new LoopList($("loop-list"), $("loops-empty"), {
  onPlay: playLoop,
  onStop: (loop) => stopLoop(loop.id),
  onWav: (loop) => download(loop.wav, `${fileName(loop.name)}.wav`),
  onJson: (loop) => {
    const { wav, outline: shape, ...rest } = loop;
    download(new Blob([JSON.stringify(rest, null, 2)], { type: "application/json" }), `${fileName(loop.name)}.json`);
  },
  onRemove: async (loop) => {
    stopLoop(loop.id);
    await loopStore.remove(loop.id).catch(() => {});
    await refreshLoops();
    setStatus(`${loop.name} is removed.`);
  },
});
loopList.setTokens(tokens);

function fileName(name) {
  return `pad-synth-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}

async function refreshLoops() {
  try {
    savedLoops = await loopStore.all();
  } catch {
    savedLoops = [];
  }
  loopList.render(savedLoops);
  for (const id of loopPlayers.keys()) loopList.setPlaying(id, true);
}

async function saveLoop(notes, bars, seconds, label) {
  setStatus("Rendering the loop.");
  const buffer = await render(notes, seconds);
  const counts = {};
  for (const note of notes) counts[note.voice] = (counts[note.voice] || 0) + 1;
  const voice = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0] || state.voice;
  const number = savedLoops.length + 1;
  const loop = {
    id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`,
    name: `${label} ${number}`,
    created: Date.now(),
    bars,
    bpm: state.bpm,
    key: state.key,
    scale: state.scale,
    scaleLabel: SCALES[state.scale].label,
    voice,
    notes,
    outline: outline(buffer),
    wav: encodeWav(buffer),
  };
  loopBuffers.set(loop.id, buffer);
  try {
    await loopStore.put(loop);
    await refreshLoops();
    setStatus(`${loop.name} is saved on this device. It is under Loops.`);
  } catch {
    savedLoops.push(loop);
    loopList.render(savedLoops);
    setStatus(`${loop.name} is ready under Loops. This browser will not keep it after the page closes.`);
  }
}

function ringNotes(bars) {
  const stepSeconds = 60 / state.bpm / 4;
  const notes = [];
  for (let bar = 0; bar < bars; bar += 1) {
    for (let step = 0; step < STEPS; step += 1) {
      for (const voice of enabledLanes()) {
        const cell = state.lanes[voice][step];
        if (!cell) continue;
        notes.push({
          voice,
          midi: midiOf(cell.degree, state.scale, state.key, 3),
          velocity: VELOCITY[voice],
          time: Math.round((bar * STEPS + step) * stepSeconds * 10000) / 10000,
          length: Math.round(GATES[voice] * stepSeconds * 10000) / 10000,
        });
      }
    }
  }
  return { notes, seconds: bars * STEPS * stepSeconds };
}

async function saveRingLoop() {
  const { notes, seconds } = ringNotes(4);
  if (!notes.length) {
    setStatus("The ring has no steps yet. Tap a step to add a note.");
    return;
  }
  await saveLoop(notes, 4, seconds, "Ring loop");
}

async function playLoop(loop) {
  startSound();
  if (!synth.ctx) return;
  let buffer = loopBuffers.get(loop.id);
  if (!buffer) {
    buffer = await synth.ctx.decodeAudioData(await loop.wav.arrayBuffer());
    loopBuffers.set(loop.id, buffer);
  }
  stopLoop(loop.id);
  const source = synth.ctx.createBufferSource();
  source.buffer = buffer;
  source.loop = true;
  source.connect(synth.graph.master);
  const start = synth.now + 0.03;
  source.start(start);
  loopPlayers.set(loop.id, { source, start, loop, seconds: buffer.duration, last: -1 });
  loopList.setPlaying(loop.id, true);
}

function stopLoop(id) {
  const player = loopPlayers.get(id);
  if (!player) return;
  try {
    player.source.stop();
  } catch {
    // Already stopped.
  }
  loopPlayers.delete(id);
  loopList.setPlaying(id, false);
}

/** A playing loop lights the field with its notes as they come round. */
function loopLight() {
  if (!synth.running) return;
  for (const player of loopPlayers.values()) {
    const position = synth.now - player.start;
    if (position < 0) continue;
    const here = position % player.seconds;
    const from = player.last;
    player.last = here;
    if (from < 0) continue;
    for (const note of player.loop.notes) {
      const inside = from <= here ? note.time > from && note.time <= here : note.time > from || note.time <= here;
      if (!inside) continue;
      const pad = playVisible() ? grid.pads.find((p) => p.midi === note.midi && p.half === 0) : null;
      const at = (pad && grid.centerOf(pad)) || { x: 0.15 + 0.7 * (((note.midi * 7) % 24) / 24), y: 0.6 };
      noteCount += 1;
      sources.add({
        id: `loop${noteCount}`,
        x: at.x,
        y: at.y,
        freq: voiceFrequency(note.voice, note.midi),
        color: colorOf(note.midi),
        look: VOICES[note.voice].look,
        now: vnow(),
        strength: 0.5 * note.velocity + 0.2,
        length: note.length,
      });
    }
  }
}

// Recording.
let recordTimer = 0;
function wireRecord() {
  const button = $("record");
  const label = $("record-label");
  button.addEventListener("click", async () => {
    if (!recorder.active) {
      startSound();
      if (!synth.ctx) return;
      stopDemo();
      recorder.begin(synth.now);
      button.setAttribute("aria-pressed", "true");
      const bar = (60 / state.bpm) * 4;
      const show = () => {
        const count = Math.floor((synth.now - recorder.start) / bar) + 1;
        label.textContent = `Bar ${Math.min(count, 8)}`;
        if (count > 8) button.click();
      };
      show();
      recordTimer = setInterval(show, 100);
      setStatus("Recording. Play, then press the button again; up to eight bars.");
      return;
    }
    clearInterval(recordTimer);
    button.setAttribute("aria-pressed", "false");
    label.textContent = "Record";
    const take = recorder.end(synth.now, state.bpm);
    if (!take.notes.length) {
      setStatus("Nothing was played, so there is no loop to save.");
      return;
    }
    await saveLoop(take.notes, take.bars, take.seconds, "Loop");
  });
}

// Keys.
function wireKeys() {
  const typing = (target) => target instanceof HTMLSelectElement || target instanceof HTMLInputElement;
  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || typing(event.target)) return;
    if (event.code === "Space" && !(event.target instanceof HTMLButtonElement)) {
      event.preventDefault();
      if (!event.repeat) toggleRing();
      return;
    }
    if (event.key === "Escape") {
      releaseAll();
      return;
    }
    if (event.repeat) {
      if (grid.maps(event.code)) event.preventDefault();
      return;
    }
    if (grid.key(event.code, true)) event.preventDefault();
  });
  document.addEventListener("keyup", (event) => {
    grid.key(event.code, false);
  });
  window.addEventListener("blur", releaseAll);
}

// Sizes and themes.
function sizeAll() {
  if (field) field.resize();
  scope.resize();
  ring.resize();
  if (grid.layout()) releaseAll();
}

function retheme() {
  tokens = readTokens();
  if (field) field.setPalette(tokens);
  scope.setTokens(tokens);
  ring.setTokens(tokens);
  loopList.setTokens(tokens);
  layGrid();
}

// The frame: schedule, light, draw.
let last = vnow();
let lastMs = performance.now();
function frame() {
  requestAnimationFrame(frame);
  const ms = performance.now();
  const now = ms / 1000;
  const dt = Math.min(0.1, Math.max(0, now - last));
  last = now;
  schedule();
  demoTick(now);
  drain(now);
  loopLight();
  sources.update(now);
  if (field) field.frame(now, dt, sources, ms - lastMs);
  lastMs = ms;
  scope.draw(synth.running ? synth.graph.analyser : null, sources, now);
  if (ringVisible()) ring.draw(ringPosition(now), sequencer.playing, dt, !reduced);
}

function schedule() {
  if (audioClock !== synth.running) {
    audioClock = synth.running;
    sequencer.rebase(clockNow());
    marks.length = 0;
  }
  sequencer.tick(clockNow(), 0.12);
}

async function selfTest() {
  const voice = config.voices[0];
  const steps = SCALES.major.steps.concat(12);
  const notes = steps.map((semitones, n) => ({
    voice,
    midi: 60 + semitones - 12 * VOICES[voice].octave,
    velocity: 0.85,
    time: n * 0.3,
    length: 0.26,
  }));
  const buffer = await render(notes, steps.length * 0.3, { loop: false, tail: 1.5 });
  const peak = peakOf(buffer);
  document.documentElement.dataset.selftest = peak.toFixed(3);
  console.log(`Self-test: a C major scale on the ${VOICES[voice].label.toLowerCase()} voice, rendered offline, peaks at ${peak.toFixed(3)}.`);
}

function init() {
  buildPickers();
  buildVoices();
  wireTabs();
  wireRing();
  wireRecord();
  wireKeys();
  setLanes();
  readout();
  setScreen("play");
  sizeAll();
  layGrid();

  document.addEventListener("pointerdown", startSound, { capture: true });
  const observer = new ResizeObserver(() => sizeAll());
  observer.observe($("grid"));
  observer.observe($("scope"));
  observer.observe($("ring-wrap"));
  window.addEventListener("resize", sizeAll);
  wideQuery.addEventListener("change", () => setScreen(app.dataset.screen));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", retheme);
  window.addEventListener("pagehide", () => saveState(state));

  startDemo();
  if (!reduced) {
    sequencer.start(clockNow());
    setTransport(true);
  }
  refreshLoops();
  requestAnimationFrame(frame);
  setInterval(schedule, 25);
  if (new URLSearchParams(location.search).get("selftest") === "1") selfTest();
}

init();
