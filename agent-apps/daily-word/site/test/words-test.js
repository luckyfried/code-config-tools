// Fixed cases for the scoring rule with repeated letters, plus hard mode and the day's word.

import { score, hardModeProblem, dailyWord, shareText } from "../game/words.js";

const C = "correct";
const P = "present";
const A = "absent";

const cases = [
  ["KEBAB against ABBEY: the second B is present, one E", () => score("KEBAB", "ABBEY"), [A, P, C, P, P]],
  ["BABES against ABBEY: one B placed, one B present", () => score("BABES", "ABBEY"), [P, P, C, C, A]],
  ["EERIE against CRANE: only the last E counts", () => score("EERIE", "CRANE"), [A, A, P, A, C]],
  ["ERASE against SPEED: both Es present, none extra", () => score("ERASE", "SPEED"), [P, A, A, P, P]],
  ["ALLAY against LLAMA: the placed L uses one of two", () => score("ALLAY", "LLAMA"), [P, C, P, P, A]],
  ["FLOOR against ROBOT: the placed O leaves one O", () => score("FLOOR", "ROBOT"), [A, A, P, C, P]],
  ["Hard mode keeps a green in its spot", () => hardModeProblem("BRINE", [{ guess: "CRANE", result: score("CRANE", "TRACE") }]), "The 3rd letter must be A."],
  ["Hard mode asks for an amber letter", () => hardModeProblem("TOAST", [{ guess: "CRANE", result: score("CRANE", "ELBOW") }]), "Your guess must use E."],
  ["Hard mode lets a fair guess through", () => hardModeProblem("TRACE", [{ guess: "CRANE", result: score("CRANE", "TRACE") }]), null],
  ["Day 1 is the launch date", () => dailyWord(["AAAAA", "BBBBB"], "2026-10-01", new Date(2026, 9, 1, 15)).day, 1],
  ["The list starts over at its end", () => dailyWord(["AAAAA", "BBBBB"], "2026-10-01", new Date(2026, 9, 3, 9)).word, "AAAAA"],
  ["The share grid never spells the word", () => !shareText({ title: "T", label: "3", history: [{ guess: "CRANE", result: score("CRANE", "CRANE") }], won: true }).includes("CRANE"), true],
];

const list = document.getElementById("list");
let failed = 0;
for (const [name, run, want] of cases) {
  let got;
  try {
    got = run();
  } catch (error) {
    got = `error: ${error.message}`;
  }
  const pass = JSON.stringify(got) === JSON.stringify(want);
  if (!pass) failed += 1;
  const item = document.createElement("li");
  item.className = pass ? "is-pass" : "is-fail";
  item.innerHTML = `<strong>${pass ? "Passed" : "Failed"}</strong> ${name}<br><code>${JSON.stringify(got)}</code>`;
  list.appendChild(item);
}
const sum = document.getElementById("sum");
sum.textContent = failed ? `${failed} of ${cases.length} failed` : `All ${cases.length} passed`;
sum.className = `test-sum ${failed ? "is-fail" : "is-pass"}`;
document.documentElement.dataset.result = failed ? "fail" : "pass";
