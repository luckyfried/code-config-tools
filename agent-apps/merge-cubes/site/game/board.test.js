// Ten fixed boards and the board each move must make. Runs in the browser (test.html) and in Node:
//   node site/game/board.test.js
import { canMove, fromGrid, move, toGrid } from "./board.js";

export const CASES = [
  {
    name: "A pair merges toward the wall",
    grid: [[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    dir: "left",
    want: [[4, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    gained: 4,
  },
  {
    name: "A merged cube does not merge again in the same move",
    grid: [[2, 2, 4, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    dir: "left",
    want: [[4, 4, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    gained: 4,
  },
  {
    name: "Four equal cubes make two pairs, not one",
    grid: [[2, 2, 2, 2], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    dir: "right",
    want: [[0, 0, 4, 4], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    gained: 8,
  },
  {
    name: "Three equal cubes merge the pair nearest the wall",
    grid: [[0, 0, 0, 0], [2, 2, 2, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    dir: "right",
    want: [[0, 0, 0, 0], [0, 0, 2, 4], [0, 0, 0, 0], [0, 0, 0, 0]],
    gained: 4,
  },
  {
    name: "A column slides up past gaps",
    grid: [[0, 0, 0, 0], [4, 0, 0, 0], [0, 0, 0, 0], [4, 0, 0, 0]],
    dir: "up",
    want: [[8, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    gained: 8,
  },
  {
    name: "A column slides down and merges once",
    grid: [[8, 0, 0, 0], [8, 0, 0, 0], [16, 0, 0, 0], [0, 0, 0, 0]],
    dir: "down",
    want: [[0, 0, 0, 0], [0, 0, 0, 0], [16, 0, 0, 0], [16, 0, 0, 0]],
    gained: 16,
  },
  {
    name: "A move against a packed wall moves nothing",
    grid: [[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    dir: "left",
    want: [[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    gained: 0,
    moved: false,
  },
  {
    name: "Every row merges in one move",
    grid: [[2, 2, 0, 0], [4, 0, 4, 0], [0, 8, 0, 8], [1024, 1024, 0, 0]],
    dir: "left",
    want: [[4, 0, 0, 0], [8, 0, 0, 0], [16, 0, 0, 0], [2048, 0, 0, 0]],
    gained: 4 + 8 + 16 + 2048,
  },
  {
    name: "A full board with no equal neighbors has no move",
    grid: [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]],
    dir: "up",
    want: [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]],
    gained: 0,
    moved: false,
    stuck: true,
  },
  {
    name: "A six-wide row keeps the no-double-merge rule",
    grid: [
      [4, 4, 8, 8, 16, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
    ],
    dir: "left",
    want: [
      [8, 16, 16, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0],
    ],
    gained: 8 + 16,
  },
];

export function runBoardTests() {
  return CASES.map((t) => {
    const board = fromGrid(t.grid);
    const result = move(board, t.dir);
    const got = toGrid(result.board);
    const problems = [];
    if (JSON.stringify(got) !== JSON.stringify(t.want)) problems.push(`made ${JSON.stringify(got)}`);
    if (result.gained !== t.gained) problems.push(`scored ${result.gained}, not ${t.gained}`);
    if (result.moved !== (t.moved ?? true)) problems.push(result.moved ? "moved when it should not" : "did not move");
    if (t.stuck !== undefined && canMove(result.board) === t.stuck) problems.push("got the no-move check wrong");
    const ids = new Set(result.trace.map((e) => e.id));
    if (ids.size !== board.tiles.length) problems.push("lost a cube in the trace");
    return { name: t.name, pass: problems.length === 0, problems };
  });
}

if (typeof process !== "undefined" && process.argv?.[1]?.endsWith("board.test.js")) {
  const results = runBoardTests();
  for (const r of results) console.log(`${r.pass ? "pass" : "FAIL"}  ${r.name}${r.pass ? "" : `: ${r.problems.join("; ")}`}`);
  const failed = results.filter((r) => !r.pass).length;
  console.log(`${results.length - failed} of ${results.length} boards pass`);
  process.exitCode = failed ? 1 : 0;
}
