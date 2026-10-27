// Scales, keys, and the isomorphic layout: one step along the long side of the grid is one scale degree, one step
// across it is a fourth in the scale, so every chord shape plays the same in every key.

export const SCALES = {
  major: { label: "Major", steps: [0, 2, 4, 5, 7, 9, 11] },
  minor: { label: "Minor", steps: [0, 2, 3, 5, 7, 8, 10] },
  dorian: { label: "Dorian", steps: [0, 2, 3, 5, 7, 9, 10] },
  mixolydian: { label: "Mixolydian", steps: [0, 2, 4, 5, 7, 9, 10] },
  lydian: { label: "Lydian", steps: [0, 2, 4, 6, 7, 9, 11] },
  phrygian: { label: "Phrygian", steps: [0, 1, 3, 5, 7, 8, 10] },
  "harmonic-minor": { label: "Harmonic minor", steps: [0, 2, 3, 5, 7, 8, 11] },
  "major-pentatonic": { label: "Major pentatonic", steps: [0, 2, 4, 7, 9] },
  "minor-pentatonic": { label: "Minor pentatonic", steps: [0, 3, 5, 7, 10] },
  blues: { label: "Blues", steps: [0, 3, 5, 6, 7, 10] },
  chromatic: { label: "Chromatic", steps: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] },
};

export const KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const FLAT_KEYS = new Set(["F", "Bb", "Eb", "Ab", "Db", "Gb"]);
const ALIASES = { Db: 1, Eb: 3, Gb: 6, Ab: 8, Bb: 10 };

export function keyIndex(name) {
  if (name in ALIASES) return ALIASES[name];
  const index = KEYS.indexOf(name);
  return index < 0 ? 0 : index;
}

/** The spelling a key prefers: flats for the flat keys, sharps for the rest. */
export function spells(keyName) {
  return FLAT_KEYS.has(keyName) ? FLAT_NAMES : KEYS;
}

/** Scale degrees per row: a fourth in the scale (3 of 7, 2 of 5, 5 of 12 semitones). */
export function rowStep(scaleId) {
  const n = SCALES[scaleId].steps.length;
  return n >= 12 ? 5 : Math.round((n * 3) / 7);
}

/** The MIDI note of scale degree `degree` (0 is the root) from the root of octave `octave`. */
export function midiOf(degree, scaleId, keyName, octave = 3) {
  const steps = SCALES[scaleId].steps;
  const n = steps.length;
  const wrap = Math.floor(degree / n);
  const within = ((degree % n) + n) % n;
  return 12 * (octave + 1) + keyIndex(keyName) + 12 * wrap + steps[within];
}

export function frequency(midi) {
  return 440 * 2 ** ((midi - 69) / 12);
}

export function noteName(midi, keyName) {
  return `${spells(keyName)[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

export function pitchClass(midi) {
  return ((midi % 12) + 12) % 12;
}

export function keyLabel(keyName, scaleId) {
  return `${keyName} ${SCALES[scaleId].label.toLowerCase()}`;
}
