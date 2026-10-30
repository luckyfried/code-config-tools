// Every move between two cards shows one print going home and the next coming out of the wall: a print lifts out of
// its tile over the last of the camera's move to it, and drops back into its tile over the first of the move out.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DROP, RISE, planOf, timesOf, type Card} from './plan.ts';

/** A board as the board builder writes it, on the kinetic card's tones, with `cards` and the peak at `peak`. */
const boardOf = (cards: unknown[], peak = 0) => ({
  format: {fps: 30},
  system: {
    colors: {bg: '#ec9e13', ink: '#0b3a8e', paper: '#ec9e13', accent: '#0b3a8e', accent2: '#ec9e13'},
    display: {family: 'd'}, text: {family: 't'},
    finish: {dip: 'none', matte: 'ink', light: '#ffffff', words: 'finished', bars: 0},
    photo: {ground: 'bg', grid: {cols: 2, rows: 4, margin: 0.04, rules: 'none'},
      picture: {show: true, box: [0, 0, 1, 1], rim: 0, rimColor: 'paper', tilt: 0, tape: 0, tapeColor: 'accent2', penColor: 'accent'}},
  },
  film: {W: 1080, H: 1920, pulse: 1, cards, peak, look: {}, closer: {move: 2}},
}) as any;

const card = (kind: Card['kind'], arrive: number, leave: number, travel: number, out: number) => ({kind, arrive, leave, travel, out}) as Card;

test("day one lifts out of its tile over the camera's dive and is at its station as the dive lands", () => {
  const c = card('hook', 1.5, 6, 0, 1.75);
  const [at, len] = timesOf(c).rise;
  assert.ok(at > 0);
  assert.equal(at + len, c.arrive);
});

test('a print lifts out over the last of the move to it and drops back over the first of the move out', () => {
  for (const kind of ['ordinary', 'milestone'] as const) {
    const c = card(kind, 8, 9.7, 1.25, 1.75);
    assert.deepEqual(timesOf(c).rise, [8 - RISE * 1.25, RISE * 1.25]);
    assert.deepEqual(timesOf(c).drop, [9.7, DROP * 1.75]);
  }
});

test('the next print lifts out only after the one before has started home', () => {
  const a = card('ordinary', 8, 9.7, 1.25, 1.25);
  const b = card('ordinary', 9.7 + 1.25, 12, 1.25, 1.25);
  assert.ok(timesOf(b).rise[0] > timesOf(a).drop[0]);
});

test('the latest drops into the last tile over the first of the pull back to the whole wall', () => {
  const c = card('latest', 28, 32, 1.75, 2);
  assert.deepEqual(timesOf(c).drop, [32, DROP * 2]);
});

test("the camera's move into a card is the board's path for it, never the card's move the timeline plays", () => {
  const line = (text: string) => ({text, x: 0, y: 0, size: 40});
  const path = {kind: 'reveal', arc: 0.55, pitch: 0.03, bank: 0.005, yaw: 0};
  const at = (id: string, p: unknown) => ({id, kind: 'milestone', title: [line('a')], rest: [], dateLine: line('d'), path: p, move: 'anamorphic-push',
    arrive: 9, leave: 12, travel: 3});
  const plan = planOf(boardOf([at('p01', null), at('p04', path)]));
  assert.equal(plan.cards[0].move, null);
  assert.deepEqual(plan.cards[1].move, path);
});

test("the look every move, cut and closer reads takes its tones and grid from the card and its photograph from the peak", () => {
  const line = (text: string) => ({text, x: 0, y: 0, size: 40});
  const at = (id: string, file: string) => ({id, kind: 'milestone', file, title: [line('a')], rest: [], dateLine: line('d'), path: null, arrive: 9, leave: 12, travel: 3});
  const plan = planOf(boardOf([at('p01', 'tiles/a.jpg'), at('p04', 'tiles/b.jpg')], 1));
  const look = plan.look;
  assert.deepEqual(look.tone, {ground: '#ec9e13', dip: null, matte: '#0b3a8e', light: '#ffffff', pen: '#0b3a8e', rim: '#ec9e13', tape: '#ec9e13'});
  assert.equal(look.grid.cols.length, 3);
  assert.equal(look.grid.rows.length, 5);
  assert.equal(look.grid.m, 0.04 * 1080);
  assert.equal(look.finished, true);
  assert.ok(look.photo?.endsWith('tiles/b.jpg'), String(look.photo));
  assert.deepEqual(look.print.box, [0, 0, 1080, 1920]);
});

test('a card that names a color its palette lacks stops the film with the name', () => {
  const board = boardOf([]);
  board.system.finish.matte = 'smoke';
  assert.throws(() => planOf(board), /MOVE_ERROR the card names no color smoke/);
});
