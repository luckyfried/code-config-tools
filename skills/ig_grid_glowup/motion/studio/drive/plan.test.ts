// The look the card's moves read carries the profile's safe area, so every word a move sets at rest stands inside the
// format's own safe lines and never on the grid's margin.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {lookOf} from './plan.ts';

/** A board as drive.py writes it, cut down to what lookOf reads, on the reel profile when `name` is given. */
const boardOf = (name?: string) => ({
  format: {width: 1080, height: 1920, fps: 30, ...(name ? {name} : {})},
  system: {
    colors: {bg: '#f4efe6', ink: '#1d1b19', paper: '#fbf8f2', accent: '#b5562d', accent2: '#2f4f4f'},
    finish: {dip: 'none', matte: 'ink', light: '#ffffff', words: 'finished'},
    photo: {ground: 'bg', grid: {cols: 4, rows: 8, margin: 0.05, rules: 'none'},
      picture: {show: true, box: [0, 0, 1, 1], rim: 0, rimColor: 'paper', tilt: 0, tape: 0, tapeColor: 'accent2', penColor: 'accent'}},
    safe: {reel: {top: 270, bottom: 670, left: 72, right: 150}, square: {top: 60, bottom: 60, left: 60, right: 60}},
  },
}) as any;

const base = {W: 1080, H: 1920} as any;
const posts = [{file: 'graded/a.jpg'}, {file: 'graded/b.jpg', peak: true}] as any;

test("the look carries the board's profile's safe area", () => {
  assert.deepEqual(lookOf(boardOf('reel'), base, posts).safe, {top: 270, bottom: 670, left: 72, right: 150});
});

test('a board that names no profile leaves the safe area to the grid margin', () => {
  assert.equal(lookOf(boardOf(), base, posts).safe, undefined);
});

test("the masked words are filled with the peak post's photograph", () => {
  assert.equal(lookOf(boardOf('reel'), base, posts).photo, '/graded/b.jpg');
});
