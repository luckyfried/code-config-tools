// The rules check: a fixed six-move opening must leave the known disc count, the replay's recorded game must play
// through legally to its known result, and the engine at strength 2 must take the corner in a fixed position.
import { replay, count, parseSquare, squareName, legalMoves, initialBoard, BLACK, WHITE } from "./reversi.js";
import { chooseMove } from "./engine.js";
import { DEMO_MOVES } from "./demo.js";

export function runChecks() {
  const results = [];
  const check = (name, ok, detail) => results.push({ name, ok: Boolean(ok), detail });

  const opening = "f5 d6 c3 d3 c4 f4".split(" ").map(parseSquare);
  const six = replay(opening);
  const sixCount = six ? count(six.board) : null;
  check("Six-move opening f5 d6 c3 d3 c4 f4 leaves 5 black and 5 white, Black to move",
    six && sixCount.black === 5 && sixCount.white === 5 && six.toMove === BLACK,
    six ? `${sixCount.black} black, ${sixCount.white} white` : "an illegal move");

  check("The opening position offers Black exactly d3, c4, f5, and e6",
    legalMoves(initialBoard(), BLACK).map(squareName).join(" ") === "d3 c4 f5 e6",
    legalMoves(initialBoard(), BLACK).map(squareName).join(" "));

  const demo = replay(DEMO_MOVES);
  const demoCount = demo ? count(demo.board) : null;
  check("The recorded replay plays all 60 moves to 22 black and 42 white",
    demo && demo.toMove === null && demoCount.black === 22 && demoCount.white === 42,
    demo ? `${demoCount.black} black, ${demoCount.white} white` : "an illegal move");

  const position = replay(DEMO_MOVES.slice(0, 39));
  const answer = chooseMove(position.board, position.toMove, 2);
  check("At strength 2, White takes the h8 corner in the fixed position",
    position.toMove === WHITE && squareName(answer.square) === "h8",
    `the engine played ${squareName(answer.square)}`);

  return results;
}

if (typeof document !== "undefined") {
  const list = document.getElementById("results");
  const results = runChecks();
  for (const r of results) {
    const li = document.createElement("li");
    li.className = r.ok ? "is-ok" : "is-bad";
    li.textContent = `${r.ok ? "Pass" : "Fail"}: ${r.name} (${r.detail})`;
    list.appendChild(li);
  }
  const passed = results.filter((r) => r.ok).length;
  document.getElementById("summary").textContent = `${passed} of ${results.length} pass`;
  document.body.dataset.passed = String(passed);
  document.body.dataset.total = String(results.length);
}
