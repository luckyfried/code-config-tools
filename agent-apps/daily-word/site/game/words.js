// The rules: which word is today's, how a guess scores, and what hard mode asks of a guess.

export const LENGTH = 5;
export const TRIES = 6;
const DAY_MS = 86400000;

/** An uppercase five-letter word, or "" when the value is not one. */
export function normalize(value) {
  const word = String(value ?? "").trim().toUpperCase();
  return /^[A-Z]{5}$/.test(word) ? word : "";
}

/** Local midnight of a "YYYY-MM-DD" date, or of today when the value does not parse. */
export function localDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value ?? ""));
  if (!match) {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

/** Whole days from the launch date to `now`, counted in local calendar days. */
export function daysSince(launchDate, now = new Date()) {
  const start = localDate(launchDate);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((today - start) / DAY_MS);
}

/** Today's word: words[daysSince(launchDate) mod words.length], and its day number (day 1 is the launch date). */
export function dailyWord(words, launchDate, now = new Date()) {
  const days = daysSince(launchDate, now);
  const index = ((days % words.length) + words.length) % words.length;
  return { word: words[index], index, day: Math.max(1, days + 1) };
}

/** Milliseconds until the next local midnight, when the next word arrives. */
export function msToNextWord(now = new Date()) {
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return next - now;
}

/**
 * Scores a guess by the standard rule: exact matches first, then each remaining letter is "present" only while
 * the answer still has an unmatched copy of it, left to right; everything else is "absent".
 */
export function score(guess, answer) {
  const result = Array(LENGTH).fill("absent");
  const left = {};
  for (let i = 0; i < LENGTH; i += 1) {
    if (guess[i] === answer[i]) result[i] = "correct";
    else left[answer[i]] = (left[answer[i]] || 0) + 1;
  }
  for (let i = 0; i < LENGTH; i += 1) {
    if (result[i] === "correct") continue;
    if (left[guess[i]] > 0) {
      result[i] = "present";
      left[guess[i]] -= 1;
    }
  }
  return result;
}

const ORDINAL = ["1st", "2nd", "3rd", "4th", "5th"];

/**
 * What a guess breaks in hard mode, in one plain sentence, or null: every green stays in its spot, and every
 * letter shown green or amber is used at least as many times as the earlier guesses showed it.
 */
export function hardModeProblem(guess, history) {
  for (const { guess: before, result } of history) {
    for (let i = 0; i < LENGTH; i += 1) {
      if (result[i] === "correct" && guess[i] !== before[i]) return `The ${ORDINAL[i]} letter must be ${before[i]}.`;
    }
    const need = {};
    for (let i = 0; i < LENGTH; i += 1) {
      if (result[i] !== "absent") need[before[i]] = (need[before[i]] || 0) + 1;
    }
    for (const [letter, count] of Object.entries(need)) {
      const have = [...guess].filter((c) => c === letter).length;
      if (have < count) return count > 1 ? `Use ${letter} ${count} times.` : `Your guess must use ${letter}.`;
    }
  }
  return null;
}

/** The best thing each letter has been shown to be: correct beats present beats absent. */
export function letterStates(history) {
  const rank = { absent: 1, present: 2, correct: 3 };
  const states = {};
  for (const { guess, result } of history) {
    for (let i = 0; i < guess.length; i += 1) {
      const now = states[guess[i]];
      if (!now || rank[result[i]] > rank[now]) states[guess[i]] = result[i];
    }
  }
  return states;
}

/** A short stable fingerprint of a word, kept with a saved game so a changed word list starts a fresh board. */
export function fingerprint(word) {
  let h = 2166136261;
  for (const c of word) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return (h >>> 0).toString(36);
}

/** The share grid: the title, the day or "Endless", tries out of six, then one row of squares per guess. */
export function shareText({ title, label, history, won, hard, highContrast }) {
  const marks = highContrast
    ? { correct: "\u{1F7E7}", present: "\u{1F7E6}", absent: "⬛" }
    : { correct: "\u{1F7E9}", present: "\u{1F7E8}", absent: "⬛" };
  const tries = won ? history.length : "X";
  const head = `${title} ${label} ${tries}/${TRIES}${hard ? "*" : ""}`;
  const rows = history.map(({ result }) => result.map((r) => marks[r]).join(""));
  return [head, "", ...rows].join("\n");
}
