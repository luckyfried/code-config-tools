// Runs the fixed cases and lists each one with its result.
import { runAll } from "./rules-test.js";

const results = runAll();
const list = document.getElementById("list");
for (const r of results) {
  const li = document.createElement("li");
  li.className = r.pass ? "test-pass" : "test-fail";
  li.textContent = `${r.pass ? "Pass" : "Fail"}: ${r.name}${r.error ? ` (${r.error})` : ""}`;
  list.appendChild(li);
}
const passed = results.filter((r) => r.pass).length;
document.getElementById("summary").textContent = `${passed} of ${results.length} cases pass.`;
document.body.dataset.result = passed === results.length ? "pass" : "fail";
