// Runs the ten fixed boards in board.test.js and lists each with its result.
import { runBoardTests } from "./board.test.js";

const results = runBoardTests();
const list = document.querySelector("[data-cases]");
for (const r of results) {
  const li = document.createElement("li");
  li.className = r.pass ? "pass" : "fail";
  li.textContent = r.pass ? `${r.name}: right.` : `${r.name}: wrong, it ${r.problems.join("; ")}.`;
  list.append(li);
}
const passed = results.filter((r) => r.pass).length;
const summary = document.querySelector("[data-summary]");
summary.textContent = `${passed} of ${results.length} boards come out right.`;
document.body.dataset.result = passed === results.length ? "pass" : "fail";
