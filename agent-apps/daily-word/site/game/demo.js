// The opening round a first visit plays on the real board: one guess, a word the game turns away, a closer guess,
// and the win, so the slabs, the keyboard's light, and the confetti are all seen before the first tap. Any key or
// tap ends it at once. Its words are never today's answer.

import { score, letterStates } from "./words.js";

const SETS = [
  { answer: "SPARK", first: "TRAIN", typo: "SHRAP", keep: 2, second: "SHARP" },
  { answer: "PLUME", first: "MOIST", typo: "FLTUE", keep: 2, second: "FLUTE" },
];

export function runDemo({ grid, keyboard, toasts, confetti, reduced, avoid, onWin }) {
  const set = SETS.find((s) => ![s.answer, s.first, s.second].includes(avoid)) || SETS[1];
  const timers = new Set();
  let stopped = false;
  const STOP = Symbol("stop");
  const wait = (ms) =>
    new Promise((resolve, reject) => {
      const id = setTimeout(() => {
        timers.delete(id);
        if (stopped) reject(STOP);
        else resolve();
      }, ms);
      timers.add(id);
    });
  const history = [];

  async function type(row, word, from = 0, gap = 72) {
    for (let c = from; c < word.length; c += 1) {
      keyboard.press(word[c]);
      grid.setLetter(row, c, word[c]);
      await wait(gap);
    }
  }

  async function reveal(row, word) {
    keyboard.press("Enter");
    const result = score(word, set.answer);
    await grid.revealRow(row, word, result, (c) => {
      keyboard.setStates(letterStates([...history, { guess: word.slice(0, c + 1), result: result.slice(0, c + 1) }]));
    });
    if (stopped) throw STOP;
    history.push({ guess: word, result });
    return result;
  }

  async function script() {
    await wait(200);
    await type(0, set.first);
    await wait(100);
    await reveal(0, set.first);
    await wait(200);

    await type(1, set.typo, 0, 66);
    await wait(130);
    keyboard.press("Enter");
    toasts.show("Not in the word list", { ms: 1100 });
    await grid.shake(1);
    await wait(160);
    for (let c = set.typo.length - 1; c >= set.keep; c -= 1) {
      keyboard.press("Backspace");
      grid.setLetter(1, c, "");
      await wait(58);
    }
    await wait(80);
    await type(1, set.second, set.keep, 66);
    await wait(100);
    await reveal(1, set.second);
    await wait(150);

    await type(2, set.answer, 0, 66);
    await wait(100);
    await reveal(2, set.answer);
    onWin?.(3);
    const rect = grid.rowRect(2);
    if (!reduced.matches) confetti.burst(rect.left + rect.width / 2, rect.top + rect.height / 2, { count: innerWidth < 700 ? 110 : 170 });
    await grid.win(2);
    await wait(2300);
  }

  const done = script().then(
    () => true,
    () => false,
  );

  return {
    done,
    stop() {
      stopped = true;
      timers.forEach((id) => clearTimeout(id));
      timers.clear();
    },
  };
}
